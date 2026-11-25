"""PostgreSQL dispatcher/worker integration; deterministic role replies intentionally isolate the product contract."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app import c3_skill_library as skills
from app.main import app
from app.pool_worker import report
from app.security import check_password
from c3_fixtures import capture
from c3_task_fixtures import LANDING, fixture
from knowledge_fixtures import accepted, revision
from test_business_workspace import post
from migrations.apply import publish_registry
from pool_lab import Lab, Worker, lab_client
from scripts.provision_pool import internal_route
from test_c3_authority import doc_and_decision
from test_claim_desk import reader
from test_registry import PG


class InternalPool(Lab):
    def setup(self, api):
        _, dispatch_dsn = self.login("amc_dispatch")
        self.bind = create_engine("postgresql+psycopg://", creator=lambda: psycopg.connect(dispatch_dsn), poolclass=NullPool)
        self.worker_name, worker_dsn = self.login("amc_pool_worker")
        self.workers.append(Worker(psycopg.connect(worker_dsn, autocommit=True)))


def public_employee_brief(api, owner, author, state):
    # A staff author can prepare an entire brief against sources available to their role.
    assertion = {"placement": state["placement"], "category": "description", "wording": "Bề mặt mờ", "qualifiers": []}
    path = state["path"]
    source = revision(
        api,
        owner,
        path,
        "public-spec",
        "source",
        {
            "document": "Thẻ thông số công khai",
            "publisher": "Xưởng mẫu An Nhiên",
            "valid_until": "2099-01-01T00:00:00Z",
            "entries": [{"locator": "Mục bề mặt", "excerpt": "Bề mặt mờ", "assertion": assertion}],
        },
    )
    binding = revision(api, owner, path, "public-binding", "binding", {"source": source["id"], "locator": "Mục bề mặt", "assertion": assertion})
    claim = revision(api, owner, path, "public-surface", "claim", {"binding": binding["id"], "assertion": assertion})
    brief = post(
        api, state["ui"] + "/briefs", author, title="Brief của nhân viên", expected_revision=1, expected_company_revision=1, selections=state["selections"]
    )
    state["params"].update(workspace_brief_id=brief["id"], claims=[claim["id"]])


def complete(lab, rid):
    for stage in ("director", "content", "seo"):
        worker = lab.workers[0]
        assert worker.take() is None
        assert lab.dispatch()
        job = worker.take()
        assert job and job["run"] == rid
        spec = job["body"]["response_format"]["json_schema"]
        assert spec["name"] == "c3_skills_" + stage
        if stage == "director":
            raw = {key: "Chuẩn bị nội dung theo đúng dữ kiện của bộ mẫu." for key in skills.ASSIGNMENTS}
        else:
            raw = {key: value for method in skills.PACKS[stage] for key, value in skills.method(method)["examples"]["good"].items()}
            raw["source_ids"] = ["F1"]
        assert report(worker.conn, job, [raw, 100, 35]) and lab.consume()


@PG
@pytest.mark.parametrize("persona", ["solo", "business"])
def test_postgres_internal_task_to_editable_draft(persona):
    with lab_client(app) as api:
        lab = InternalPool(api, os.environ["AMC_MIGRATION_DSN"])
        try:
            owner, base, client, brand, campaign, task, brief, state, _ = fixture(api)
            author = owner
            if persona == "business":
                author = reader(api, owner, "editor")
                brief = accepted(api.post(base + "/workforce/internal-tasks", headers=author["headers"], json=task | {"key": str(uuid4())}))
                state["params"]["target"]["brief_id"] = brief["id"]
                public_employee_brief(api, owner, author, state)
            admin = owner["headers"]
            lab.configure(owner, 10000)
            with lab.owner.transaction():
                operator = internal_route(lab.owner, lab.worker_name, owner["tenant"], client, brand, campaign)
                assert internal_route(lab.owner, lab.worker_name, owner["tenant"], client, brand, campaign) == operator
                assert operator != author["id"] and operator != owner["id"]
                manifest = json.loads((Path(skills.__file__).resolve().parents[1] / "catalog/landing-seo-v6.json").read_text(encoding="utf8"))
                publish_registry(lab.owner, manifest)
            password, verified = lab.owner.execute("select password_hash,verified_at from users where id=%s", (operator,)).fetchone()
            assert verified is None and not check_password("!amc-worker", password)
            assert lab.owner.execute("select count(*) from portal_grants where tenant_id=%s", (owner["tenant"],)).fetchone() == (0,)
            assert lab.owner.execute("select count(*) from memberships where tenant_id=%s", (owner["tenant"],)).fetchone() == (2 if persona == "solo" else 3,)
            api.put(
                base + "/workforce/registry/" + campaign, headers=admin, json={"workflow": LANDING, "action": "activate", "skills": manifest["required"]}
            ).raise_for_status()
            snap = capture(api, author, state)
            uri = base + "/workforce/briefs/" + brief["id"] + "/run"
            terms = {
                "registry_workflow": LANDING,
                "workflow": "dynamic-v1",
                "budget_microusd": 10000,
                "knowledge_manifest": {"id": snap["id"], "digest": snap["digest"]},
            }
            run = accepted(api.post(uri, headers=author["headers"], json=terms))
            complete(lab, run["id"])
            doc, qa = doc_and_decision(lab, base, owner, run["id"])
            report_url = base + "/workforce/runs/" + run["id"]
            staff_report = accepted(api.get(report_url, headers=author["headers"]))
            assert staff_report["state"] == "awaiting_qa"
            sections = staff_report["marketing_artifacts"]["sections"]
            original = sections["customer_preview"]["generated"]
            assert original["body"] == sections["customer_preview"]["current"]["body"] and sections["seo_fields"]
            assert staff_report["marketing_artifacts"]["editorial_status"] == "unreviewed_suggestions"
            if persona == "business":
                assert api.get("/api/tenants/" + author["tenant"] + "/workforce/runs/" + run["id"], headers=author["headers"]).status_code == 404
            accepted(api.patch(doc + "/draft", headers=author["headers"], json={"title": "Bộ mẫu vải", "client_preview": "Bề mặt mờ"}))
            accepted(api.post(doc + "/submit", headers=author["headers"]))
            doc, qa = doc_and_decision(lab, base, owner, run["id"])
            assert accepted(api.get(doc, headers=admin))["content"]["client_preview"] == "Bề mặt mờ"
            edited = accepted(api.get(report_url, headers=admin))["marketing_artifacts"]
            current = edited["sections"]["customer_preview"]["current"]
            assert (current["body"],current["revision"],current["digest"]) == ("Bề mặt mờ",qa["expected_qa_revision"],qa["expected_content_digest"])
            assert original != {"title":current["title"], "body":current["body"]}
            assert edited["sections"]["customer_preview"]["generated"] == original
            assert edited["sections"]["seo_fields"] == sections["seo_fields"]
            assert edited["evidence_coverage"] == {"fields":["title","client_preview"], "current_assessment":True}
            assert api.post(doc + "/review", headers=author["headers"], json=qa).status_code in (403, 404, 409)
            if persona == "business":
                evidence = accepted(api.get(doc + "/content-evidence", headers=admin))
                assert evidence["ready"], evidence["statements"]
                accepted(api.post(doc + "/review", headers=admin, json=qa))
            share = {k: qa[k] for k in ("expected_qa_revision", "expected_content_digest")}
            share["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            assert api.post(doc + "/share", headers=admin, json=share).status_code == 409
            assert api.get(base + "/reviews", headers=admin).json() == []
            if persona == "business":
                pending = accepted(api.post(base + "/workforce/internal-tasks", headers=author["headers"], json=task | {"key": str(uuid4())}))
                state["params"].update(key=str(uuid4()), target={"campaign_id": campaign, "brief_id": pending["id"]})
                refreshed = capture(api, author, state)
                terms["knowledge_manifest"] = {"id": refreshed["id"], "digest": refreshed["digest"]}
                queued = accepted(api.post(base + "/workforce/briefs/" + pending["id"] + "/run", headers=author["headers"], json=terms))
                lab.owner.execute("UPDATE memberships SET role='viewer' WHERE tenant_id=%s AND user_id=%s", (owner["tenant"], author["id"]))
                assert lab.owner.execute("SELECT state,last_error FROM workforce_runs WHERE id=%s", (queued["id"],)).fetchone() == (
                    "failed",
                    "recipient_revoked",
                )
                assert not lab.dispatch()
        finally:
            lab.release_connections()
