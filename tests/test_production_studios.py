"""Genuine rendering, artifact QA and two typed, synthetic landing journeys."""

from base64 import b64decode
from contextlib import closing
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import text

from app import c3_assets
from app.access import set_context
from app.campaign_planner import campaign_store
from app.database import get_db
from app.main import app
from app.models import User
from app.production_studios import approved_landing_destination
from app.security import sign_actor
from campaign_planner_fixtures import CASES, facts
from knowledge_fixtures import accepted
from test_channel_editions import commission, lifecycle, pool, sqlite_channel, workforce  # noqa: F401
from test_claim_desk import reader
from test_registry import PG
from test_studio_postgres import agency_draft


def destination(owner, campaign, plan):
    dependency = app.dependency_overrides.get(get_db, get_db)
    with closing(dependency()) as resource:
        db = next(resource)
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SET TRANSACTION READ ONLY"))
            set_context(db, actor=owner["id"], tenant=owner["tenant"])
            sign_actor(db, owner["id"])
        user = db.get(User, owner["id"])
        store = campaign_store(db, user, owner["tenant"], campaign, write=False)
        return approved_landing_destination(store, user, plan)


def qualify(api, base, doc, owner, buyer, other, plan, action, observe=None):
    studio = doc + "/studio"
    url = studio + "/production"
    decision = reader(api, owner, "admin")
    view = accepted(api.get(studio, headers=owner["headers"]))

    def post(actor, target, body):
        return api.post(target, headers=actor["headers"], json=body)

    assert api.get(url, headers=buyer["headers"]).status_code == 404
    assert api.get(url, headers=other["headers"]).status_code == 404
    exports = {}
    for kind, groups in (("creative", ("copy", "creative_brief")), ("landing", ("copy", "seo"))):
        body = {
            "kind": kind,
            "expected_revision": view["revision"],
            "expected_plan_digest": plan["digest"],
            "expected_groups": {g: view["asset_digests"][g] for g in groups},
            "expected_version": 0,
        }
        assert post(owner, url, body | {"expected_revision": 1}).status_code == 412
        item = accepted(post(owner, url, body))
        assert accepted(post(owner, url, body))["id"] == item["id"]
        result = url + "/" + item["id"]
        foreign_tenant_path = result.replace("/tenants/" + owner["tenant"], "/tenants/" + other["tenant"])
        if foreign_tenant_path != result:
            assert api.get(foreign_tenant_path + "/files/master.json", headers=other["headers"]).status_code == 404
        verdict = {"expected_digest": item["digest"], "note": "Đã xem từng file, bố cục và các điều kiện tổng hợp."}
        assert post(owner, result + "/approve", verdict).status_code == 409
        assert post(decision, result + "/approve", verdict | {"expected_digest": "0" * 64}).status_code == 412
        if kind == "landing":
            assert post(owner, result + "/visits", {"request_id": uuid4().hex}).status_code == 409
            assert destination(owner, plan["campaign_id"], plan) is None
        else:
            assert post(owner, url, body | {"motif": "planes"}).status_code == 412
            assert post(owner, url, body | {"colors": ["#111111", "#121212", "#141414"], "expected_version": 1}).status_code == 422
            shifted = accepted(post(owner, url, body | {"motif": "planes", "expected_version": 1}))
            assert shifted["files"]["landscape.png"]["sha256"] != item["files"]["landscape.png"]["sha256"]
            assert post(decision, result + "/approve", verdict).status_code == 409
            item = shifted
            result = url + "/" + item["id"]
            verdict["expected_digest"] = item["digest"]
        decision_receipt = accepted(post(decision, result + "/approve", verdict))
        item["production_qa"] = {"reviewer": decision["id"], **decision_receipt}
        if kind == "landing":
            target = destination(owner, plan["campaign_id"], plan)
            assert target == {
                "deliverable_id": doc.rsplit("/", 1)[1],
                "package_id": item["id"],
                "package_digest": item["digest"],
                "studio_revision": view["revision"],
                "file_digest": item["files"]["landing.html"]["sha256"],
                "download_url": result + "/files/landing.html",
            }
            assert destination(owner, plan["campaign_id"], plan | {"digest": "f" * 64}) is None
        files = {}
        for name, meta in item["files"].items():
            path = result + "/files/" + name
            assert api.get(path, headers=other["headers"]).status_code == 404
            data = b64decode(accepted(api.get(path, headers=owner["headers"]))["base64"])
            assert sha256(data).hexdigest() == meta["sha256"] and len(data) == meta["bytes"]
            files[name] = data
        if kind == "creative":
            for name, dimensions in item["master"]["variations"].items():
                assert list(Image.open(BytesIO(files[name + ".png"])).size) == dimensions
            assert files["preview.webm"].startswith(bytes.fromhex("1a45dfa3")) and b"V_VP8" in files["preview.webm"]
            assert item["master"]["source"]["sha256"] == sha256(files["source.png"]).hexdigest()
        else:
            assert b"noindex,nofollow" in files["landing.html"] and item["master"]["kind"] == action
            visit = accepted(post(owner, result + "/visits", {"request_id": uuid4().hex}))
            form = {"request_id": uuid4().hex, "visit_id": visit["entity_id"], "quantity": 3, "place": "north", "days": 7}
            assert post(buyer, result + "/submissions", form).status_code == 404
            assert post(owner, result + "/submissions", form | {"email": "real@example.invalid"}).status_code == 422
            assert post(owner, result + "/submissions", form | {"quantity": 0}).status_code == 422
            assert post(decision, result + "/submissions", form).status_code == 409
            submitted = accepted(post(owner, result + "/submissions", form))
            assert submitted["kind"] == action and submitted["value"]["landing_digest"] == item["digest"]
            assert accepted(post(owner, result + "/submissions", form))["id"] == submitted["id"]
            assert post(owner, result + "/submissions", form | {"request_id": uuid4().hex}).status_code == 409
            assert post(owner, result + "/submissions", form | {"quantity": 4}).status_code == 409
        exports[kind] = item
        if directory := os.getenv("AMC_PRODUCTION_EVIDENCE"):
            dest = Path(directory) / action / kind
            dest.mkdir(parents=True, exist_ok=True)
            for name, data in files.items():
                (dest / name).write_bytes(data)
            (dest / "receipt.json").write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
            if kind == "landing":
                (dest / "sandbox-events.json").write_text(json.dumps([visit, submitted], ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    if observe:
        observe(owner, doc, plan, exports)
    return exports


def rehearsal(api, workforce, monkeypatch, case, observe=None):  # noqa: F811
    doc, snap, plan, editor, other, _ = sqlite_channel(api, workforce, monkeypatch, case)
    owner, buyer, _, base, *_ = workforce
    artifacts = {}

    def inspect(*_):
        artifacts.update(qualify(api, base, doc, owner, buyer, other, plan, case["buyer_action"], observe))

    lifecycle(api, base, owner, buyer, other, doc, snap, plan, editor, inspect)
    url = doc + "/studio/production/" + artifacts["landing"]["id"]
    assert api.post(url + "/visits", headers=owner["headers"], json={"request_id": uuid4().hex}).status_code == 409
    assert api.get(url + "/files/landing.html", headers=owner["headers"]).status_code == 200
    assert destination(owner, plan["campaign_id"], plan) is None


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_scoped_production(api, workforce, monkeypatch, case):  # noqa: F811
    rehearsal(api, workforce, monkeypatch, case)


@PG
@pytest.mark.parametrize("legacy_without_unit", [False, True])
def test_restricted_production(pool, legacy_without_unit):  # noqa: F811
    base, owner, buyer, _, cid = pool.cases[0]
    plan = {}

    def before(snap, *_):
        plan.update(commission(pool.api, base, owner, cid, snap))

    doc, _, snap = agency_draft(pool, c3_assets.LANDING, rfq=True, before_queue=before, approved_facts=None if legacy_without_unit else facts(CASES[0]))
    editor = reader(pool.api, owner, "editor")
    other = pool.cases[1][2]

    def inspect(*_):
        if legacy_without_unit:
            url = doc + "/studio"
            view = accepted(pool.api.get(url, headers=owner["headers"]))
            args = {
                "kind": "landing",
                "expected_revision": view["revision"],
                "expected_plan_digest": plan["digest"],
                "expected_groups": {g: view["asset_digests"][g] for g in ("copy", "seo")},
                "expected_version": 0,
            }
            response = pool.api.post(url + "/production", headers=owner["headers"], json=args)
            assert response.status_code == 409 and "selling unit" in response.json()["detail"]
            return
        packages = qualify(pool.api, base, doc, owner, buyer, other, plan, "rfq")
        _, foreign_owner, _, _, foreign_campaign = pool.cases[1]
        assert destination(foreign_owner, foreign_campaign, plan) is None
        reviewer = packages["landing"]["production_qa"]["reviewer"]
        pool.owner.execute("update memberships set role='editor' where tenant_id=%s and user_id=%s", (owner["tenant"], reviewer))
        assert destination(owner, plan["campaign_id"], plan) is None

    lifecycle(pool.api, base, owner, buyer, other, doc, snap, plan, editor, inspect)
