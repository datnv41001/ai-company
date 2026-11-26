"""Exercise the same synthetic business case through the compatible pre-desk and current APIs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import text

from agency_fixtures import account
from check_c3_cutover import unpack
from check_sandbox_journal import host
from knowledge_fixtures import accepted
from test_campaign_appointments import service_campaign
from test_campaign_role_desk import change_fixture_membership
from test_claim_desk import reader


PRE_DESK = "0498949e64f4d030cc9ba2f0f961ab4dfc2e2ab0"


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_compatible_business_writers_share_authority_and_revision(api, agency, tmp_path):
    from app.database import engine

    with engine.connect() as conn:
        assert conn.execute(text("SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user")).one() == (
            "amc_runtime", False, False
        )
        assert conn.scalar(text("SELECT relrowsecurity FROM pg_class WHERE oid='public.knowledge_commands'::regclass"))
    owner, root, plan, second_client, other_root = service_campaign(api, agency, secondary=True)
    old_coordinator = reader(api, owner, "admin")
    reviewer = reader(api, owner, "viewer")
    outside = account(api, "IndependentBusiness")
    base = {"plan_id": plan["id"]}
    desk = root + "/business-desk"

    def grant(role, enabled=True, revision=0):
        return accepted(api.post(desk + "/grants", headers=owner["headers"], json={
            "key": uuid4().hex, "subject": reviewer["id"], "role": role,
            "enabled": enabled, "expected_revision": revision,
        }))

    def decision(role, body):
        return api.post(desk + "/" + role + "/decisions", headers=reviewer["headers"], json=body)

    grant("reviewer")
    t = datetime.now(timezone.utc) - timedelta(days=1)
    issue = {**base, "kind": "appointment", "contract": "service-appointment/1", "request_id": uuid4().hex,
             "appointment_id": "scoped-desk-rehearsal", "product_id": plan["product_id"], "unit": "machine",
             "quantity": "1", "location": "Synthetic workshop", "service_scope": "Synthetic inspection",
             "contact_purpose": "appointment_request", "occurred_at": t.isoformat(), "requested_for": (t+timedelta(hours=3)).isoformat()}
    confirm = {**base, "kind": "appointment_decision", "appointment_id": issue["appointment_id"],
               "step": "confirm", "expected_revision": 1, "occurred_at": (t+timedelta(hours=1)).isoformat(),
               "confirmed_for": issue["requested_for"], "request_id": uuid4().hex}
    source = unpack(PRE_DESK, tmp_path)
    with host(source, {**os.environ, "PYTHONPATH": str(source)}) as (writer, rpc):
        assert writer == "campaign_sandbox_v2"

        def legacy(actor, body, campaign=root):
            return rpc({"method": "POST", "url": campaign + "/sandbox/commands", "headers": actor["headers"], "json": body})

        original = legacy(old_coordinator, issue)
        assert original["status"] == 200 and original["data"]["value"]["revision"] == 1
        assert legacy(reviewer, confirm)["status"] == 404
        assert decision("reviewer", confirm).status_code == 404
        assert decision("marketing_operator", confirm).status_code == 404
        assert legacy(second_client, confirm)["status"] == 404
        assert legacy(outside, confirm)["status"] in (403, 404)
        assert api.get(desk + "/reviewer/inbox", headers=outside["headers"]).status_code in (403, 404)
        assert api.post(other_root + "/business-desk/reviewer/decisions", headers=reviewer["headers"], json=confirm).status_code == 404
        grant("marketing_operator")
        roles = accepted(api.get(desk + "/access", headers=reviewer["headers"]))["roles"]
        assert set(roles) == {"reviewer", "marketing_operator"}
        assert decision("reviewer", confirm).status_code == 404
        both = Barrier(2)

        def desk_confirm():
            both.wait(timeout=10)
            return decision("marketing_operator", confirm).status_code

        def org_confirm():
            both.wait(timeout=10)
            return legacy(owner, confirm | {"request_id": uuid4().hex})["status"]

        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = [pool.submit(f) for f in (desk_confirm, org_confirm)]
            assert sorted(f.result(timeout=25) for f in attempts) == [200, 409]
        state = accepted(api.get(desk + "/reviewer/inbox", headers=reviewer["headers"]))["items"]
        assert [x["value"] for x in state] == [{"id":issue["appointment_id"], "revision":2,"plan_id":plan["id"],"state":"confirmed"}]
        feedback = {**base, "kind":"review_feedback","entity":"appointments","entity_id":issue["appointment_id"],
                    "expected_revision":2,"note":"Synthetic assessment","request_id":uuid4().hex}
        recorded = accepted(decision("reviewer", feedback))
        grant("marketing_operator", False, 1)
        assert decision("marketing_operator", confirm).status_code == 404
        assert legacy(reviewer, confirm)["status"] == 404
        assert accepted(decision("reviewer", feedback)) == recorded
        # Remove only the synthetic reviewer from this agency. Its personal fixture tenant still exists.
        with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as db:
            assert db.info.host in {"127.0.0.1", "localhost", "::1"} and db.info.dbname.startswith("amc_test")
            assert db.execute("DELETE FROM memberships WHERE tenant_id=%s AND user_id=%s",
                              (owner["tenant"], reviewer["id"])).rowcount == 1
        assert decision("reviewer", feedback).status_code in (403, 404)
        assert legacy(reviewer, confirm)["status"] in (403, 404)
        assert legacy(old_coordinator, issue)["data"] == original["data"]
        change_fixture_membership(api, owner["tenant"], old_coordinator["id"], "viewer")
        assert legacy(old_coordinator, issue)["status"] == 404
        assert api.post(root + "/sandbox/commands", headers=old_coordinator["headers"], json=issue).status_code == 404
        stable = accepted(api.get(root + "/sandbox", headers=owner["headers"]))
        assert original["data"]["id"] in {r["id"] for r in stable["receipts"]}
