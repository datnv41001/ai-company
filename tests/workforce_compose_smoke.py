"""Real local-model acceptance on the disposable Compose project in CI. No billable requests."""

import os
import secrets
import subprocess
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from identity_fixtures import start_registration, verify_registration, invite_member
import httpx


def exercise():
    project = "amc-workforce-test"
    compose = ["docker", "compose", "-p", project, "-f", "compose.yaml", "-f", "tests/compose_pool_database.yaml"]
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=15, trust_env=False) as api:

        def request(method, path, user=None, body=None):
            response = api.request(method, path, json=body, headers={"Authorization": "Bearer " + user["access_token"]} if user else {})
            response.raise_for_status()
            return response.json()

        def account(name):
            email = f"{name}-{uuid4().hex}@example.com"
            registration = start_registration(api,email,secrets.token_urlsafe(24),organization_name=name,mode="agency")
            registration["email"] = email
            verify_registration(api,email,registration,project)
            return registration

        admin, worker, client = [account(s) for s in ("Agency", "Worker", "Client")]
        t = admin["tenant_id"]
        base = "/api/tenants/" + t
        c = request("POST", base + "/clients", admin, {"name": "Paper Street"})
        b = request("POST", base + "/brands", admin, {"client_id": c["id"], "name": "Paper Street", "product_truth": "A5 notebook with 80 lined pages."})
        campaign = request(
            "POST",
            base + "/campaigns",
            admin,
            {"brand_id": b["id"], "name": "Notebook launch", "brief": "Invite students to visit the store.", "objective": "Store visits"},
        )
        invite_member(api, base, {"Authorization":"Bearer "+admin["access_token"]}, {"Authorization":"Bearer "+worker["access_token"]}, **{"email": worker["email"], "role": "editor"})
        invite_member(api, base, {"Authorization":"Bearer "+admin["access_token"]}, {"Authorization":"Bearer "+client["access_token"]}, **{"email": client["email"], "role": "client_viewer", "client_id": c["id"]})
        request("PUT", base + "/members/" + client["user_id"] + "/review-rights", admin, {"can_comment": True, "can_decide": True})
        root = base + "/workforce"
        brief = request("POST", root + "/briefs", admin, {"campaign_id": campaign["id"], "recipient_id": client["user_id"], "title": "Notebook launch"})
        request(
            "PUT",
            root + "/briefs/" + brief["id"] + "/submission",
            client,
            {
                "audience": "Local university students",
                "objective": "Ask students to visit the store.",
                "offer": "See the A5 notebook in store.",
                "sources": [{"label": "Product card", "excerpt": "A5 notebook with 80 lined pages."}],
            },
        )
        run = request("POST", root + "/briefs/" + brief["id"] + "/run", admin, {"budget_microusd": 0})
        env = {
            **os.environ,
            "AMC_WORKER_TENANT": t,
            "AMC_WORKER_CLIENT": c["id"],
            "AMC_WORKER_BRAND": b["id"],
            "AMC_WORKER_CAMPAIGN": campaign["id"],
            "AMC_WORKER_OPERATOR": worker["user_id"],
            "AMC_MODEL_TIMEOUT": "180",
            "AMC_WORKFORCE_PROVIDER": "local",
            "AMC_LOCAL_MODEL_URL": "http://model:8080/v1",
            "AMC_WORKFORCE_MODEL": "amc-local",
        }
        subprocess.run([*compose, "--profile", "workforce", "up", "-d", "worker"], env=env, check=True)
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            report = request("GET", root + "/runs/" + run["id"], admin)
            if report["state"] in ("failed", "awaiting_qa"):
                break
            time.sleep(2)
        journal = report["journal"]
        first = [j for j in journal if j["attempt"] == 1]
        print("Qwen single-campaign measurements", {
            "state": report["state"], "first_ok": sum(j["outcome"] == "ok" for j in first),
            "first_total": len(first), "attempts": len(journal),
            "stages": [(j["skill"], j["outcome"], j.get("input_tokens"), j.get("output_tokens")) for j in journal],
        }, flush=True)
        assert report["state"] == "awaiting_qa", (report["state"], report["last_error"], [(j["skill"], j["outcome"]) for j in report["journal"]])
        assert [p["skill"] for p in report["checkpoints"]] == ["director", "research", "strategy", "content"]
        assert all(j["provider"] == "local" for j in report["journal"])
        assert all(p["quality"]["ruleset"] == "marketing-evidence-2" for p in report["checkpoints"])
        assert report["reserved_microusd"] == 0 and all(p["output"]["source_ids"] for p in report["checkpoints"])
        doc = base + "/deliverables/" + report["deliverable_id"]
        assert request("GET", base + "/reviews", client) == []
        # Synthetic identities exercise the acceptance mechanism. Copy quality needs separate human review.
        assessment = request("GET", doc, admin)["qa_evidence"]
        assert assessment["state"] == "current"
        request("POST", doc + "/review", admin, {"decision": "approved", "expected_qa_revision": assessment["qa_revision"], "expected_content_digest": assessment["content_digest"], "note": "Synthetic end-to-end acceptance"})
        shared = request("POST", doc + "/share", admin, {"expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()})
        request("POST", base + "/reviews/" + shared["id"] + "/events", client, {"kind": "approved", "digest": shared["digest"], "request_key": uuid4().hex})
        assert shared["digest"] == assessment["content_digest"]
        archive = request("GET", root + "/runs/" + run["id"], admin)["approved_assets"]
        assert archive == [{"id": shared["id"], "version": 1, "digest": shared["digest"]}]
        print("PASS real local model: brief, 4 specialist checkpoints, independent QA, exact client-approved archive; attempts:", len(report["journal"]))


if __name__ == "__main__":
    exercise()
