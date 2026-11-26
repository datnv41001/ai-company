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
from app.measurement_integrity import matched_landing
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


def qualify(api, base, doc, owner, buyer, other, plan, action, observe=None, predecessor=None):
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
        if kind == "landing" and predecessor:
            denied = predecessor("POST", url, owner, body)
            assert denied["sqlstate"] == "55000" and "compatible landing writer" in denied["guard"]
            assert accepted(api.get(url, headers=owner["headers"]))[0]["kind"] == "creative"
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
            pack_url = doc.split("/deliverables/")[0] + "/campaigns/" + plan["campaign_id"] + "/engine/plans/" + plan["id"] + "/content-pack"
            advertised = accepted(api.get(pack_url, headers=owner["headers"]))["advertising"]["destination"]
            assert advertised == {"kind":"sandbox_landing","status":"approved", **target}
            assert api.get(pack_url, headers=other["headers"]).status_code in (403,404)
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
            contract = item["master"]["intake_contract"]
            assert contract == plan["intake_contract"]
            selected = {"quantity": 3, "box_count": 3, "destination": "north", "site": "north",
                        "preferred_time": "7", "need_date": "7", "receiving_shift": "evening"}
            answers = {f["id"]: selected[f["id"]] for f in contract["fields"]}
            for key in answers:
                assert f'name="{key}"'.encode() in files["landing.html"]
            form = {"request_id": uuid4().hex, "visit_id": visit["entity_id"], "contract_digest": contract["digest"],
                    "consent": True, "answers": answers}
            assert post(owner, result + "/submissions", form | {"consent": False}).status_code == 422
            assert post(owner, result + "/submissions", form | {"contract_digest": "0"*64}).status_code == 412
            for field in contract["fields"]:
                if field["required"]:
                    assert post(owner, result + "/submissions", form | {"answers": {k:v for k,v in answers.items() if k != field["id"]}}).status_code == 422
            assert post(owner, result + "/submissions", form | {"answers": answers | {"undeclared": "x"}}).status_code == 422
            first = contract["fields"][0]
            wrong = str(answers[first["id"]]) if first["type"] == "integer" else False
            assert post(owner, result + "/submissions", form | {"answers": answers | {first["id"]: wrong}}).status_code == 422
            assert post(owner, result + "/submissions", {"request_id": uuid4().hex, "visit_id": visit["entity_id"],
                        "quantity": 3, "place": "north", "days": 7}).status_code == 422
            assert post(buyer, result + "/submissions", form).status_code == 404
            assert post(owner, result + "/submissions", form | {"email": "real@example.invalid"}).status_code == 422
            assert post(owner, result + "/submissions", form | {"quantity": 0}).status_code == 422
            assert post(decision, result + "/submissions", form).status_code == 409
            submitted = accepted(post(owner, result + "/submissions", form))
            assert submitted["kind"] == action and submitted["value"]["landing_digest"] == item["digest"]
            value = submitted["value"]
            assert submitted["origin"] == "landing"
            assert value["intake"]["answers"] == answers and value["intake"]["contract_digest"] == contract["digest"]
            assert value["intake"]["consent"] == {"purpose": contract["consent"]["purpose"], "granted": True}
            if "receiving_shift" in answers:
                assert value["intake"]["mapped"]["receiving_shift"] == "evening"
                assert value["requested_for"] is None and value["quantity"] is None
            if action == "rfq" and "box_count" in answers and float(contract["qualification"]["minimum_order_quantities"][0]) > 3:
                assert value["state"] == "received" and "commercial_moq" in value["missing"] and not value["ordered"]
            desk = base + "/campaigns/" + plan["campaign_id"] + "/business-desk"
            operator = reader(api, owner, "editor")
            accepted(post(owner, desk + "/grants", {"key": uuid4().hex, "subject": operator["id"],
                     "role": "marketing_operator", "enabled": True, "expected_revision": 0}))
            inbox = desk + "/marketing_operator/inbox"
            assert api.get(inbox, headers=buyer["headers"]).status_code == 404
            shown = accepted(api.get(inbox, headers=operator["headers"]))["items"]
            assert next(x["value"] for x in shown if x["value"]["id"] == submitted["entity_id"])["intake"] == value["intake"]
            sandbox = base + "/campaigns/" + plan["campaign_id"] + "/sandbox"
            metric = accepted(api.get(sandbox, headers=owner["headers"]))["intake_measurement"]
            assert metric["contract_digest"] == contract["digest"] and metric["landing_visits"] == metric["valid_submissions"] == 1
            assert metric["manual_requests"] == 0
            if "commercial_moq" in value.get("missing", []):
                assert metric["qualified_quotes"] == metric["orders"] == 0
            if action == "rfq":
                manual = {"kind": "rfq", "plan_id": plan["id"], "request_id": uuid4().hex, "rfq_id": uuid4().hex,
                          "occurred_at": submitted["recorded_at"], "product_id": plan["product_id"], "unit": plan["selling_unit"],
                          "quantity": "1", "location": "Test site A", "required_date": "2030-01-01", "contact_purpose": "quote_request"}
                if predecessor:
                    denied = predecessor("POST", sandbox + "/commands", owner, manual)
                    assert denied["sqlstate"] == "55000" and "compatible writer" in denied["guard"]
                added = accepted(post(owner, sandbox + "/commands", manual))
                assert added["origin"] == "manual" and "intake" not in added["value"]
                after = accepted(api.get(sandbox, headers=owner["headers"]))["intake_measurement"]
                assert after == metric | {"manual_requests": 1}
            if plan.get("measurement_contract"):
                source = visit["value"]["landing_source"]
                assert source == submitted["value"]["landing_source"]
                scope = {k: source[k] for k in ("tenant_id", "client_id", "brand_id", "campaign_id", "plan_id", "plan_digest")}
                assert source["studio_revision"] == view["revision"] and source["package_version"] == item["version"]
                assert source["file_digest"] == item["files"]["landing.html"]["sha256"]
                legacy_visit = {k: v for k, v in visit["value"].items() if k != "landing_source"}
                assert not matched_landing(legacy_visit, submitted["value"], scope)
                for key in ("tenant_id", "client_id", "brand_id", "campaign_id", "plan_id", "plan_digest"):
                    assert not matched_landing(visit["value"], submitted["value"], scope | {key: "foreign"})
                for key in ("package_id", "file_digest", "package_digest", "studio_revision", "package_version", "document_id"):
                    mismatched = submitted["value"] | {"landing_source": source | {key: "different"}}
                    assert not matched_landing(visit["value"], mismatched, scope)
                report = accepted(api.get(base + "/campaigns/" + plan["campaign_id"] + "/sandbox", headers=owner["headers"]))["report"]["primary_measurement"]
                assert (report["numerator"], report["denominator"], report["ratio"]) == (0, 1, 0)
                assert report["attribution"] == {"landing_asset": 1, "media_action": 0, "unknown_media_action": 1, "neither": 0}
                assert report["attributed"] == 1 and report["unattributed"] == 0
                assert report["secondary_metrics"][0]["value"] == 1
                if directory := os.getenv("AMC_PRODUCTION_EVIDENCE"):
                    dest = Path(directory) / action / "landing"
                    dest.mkdir(parents=True, exist_ok=True)
                    (dest / "attribution.json").write_text(json.dumps({"visit_receipt": visit["id"], "submission_receipt": submitted["id"],
                        "landing_source": source, "kpi": report}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
            assert accepted(post(owner, result + "/submissions", form))["id"] == submitted["id"]
            assert post(owner, result + "/submissions", form | {"request_id": uuid4().hex}).status_code == 409
            location = "site" if action == "appointment" else "destination"
            assert post(owner, result + "/submissions", form | {"answers": answers | {location: "south"}}).status_code == 409
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
    if case["id"] == "index-tray":
        case = case | {"moq": "5"}
    if case["buyer_action"] == "appointment":
        case = case | {"measurement": {"version": "appointment-measurement/1", "business_outcome": "appointment.confirmed_per_requested",
                                       "window_days": 21, "owner_role": "service_operations"}}
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
@pytest.mark.parametrize("case", CASES + json.loads((Path(__file__).parent / "evaluation/department/briefs-v1.json").read_text(encoding="utf8"))["cases"], ids=lambda c: c["id"])
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
        from intake_previous_api import previous_api
        with previous_api() as predecessor:
            packages = qualify(pool.api, base, doc, owner, buyer, other, plan, "rfq", predecessor=predecessor)
        _, foreign_owner, _, _, foreign_campaign = pool.cases[1]
        assert destination(foreign_owner, foreign_campaign, plan) is None
        reviewer = packages["landing"]["production_qa"]["reviewer"]
        pool.owner.execute("update memberships set role='editor' where tenant_id=%s and user_id=%s", (owner["tenant"], reviewer))
        assert destination(owner, plan["campaign_id"], plan) is None

    lifecycle(pool.api, base, owner, buyer, other, doc, snap, plan, editor, inspect)


@PG
def test_predecessor_can_still_serve_approved_v1(pool):  # noqa: F811
    from intake_previous_api import previous_api
    base, owner, buyer, _, cid = pool.cases[0]
    old_plan = {}
    with previous_api() as old:
        def before(snap, *_):
            root = base + "/campaigns/" + cid + "/engine/plans"
            proposed = old("POST", root, owner, {"key": uuid4().hex, "expected_revision": 0,
                "manifest_ids": [snap["id"]], "budget_vnd": 500000, "duration_days": 14})
            assert proposed["status"] == 201
            old_plan.update(proposed["body"])
            assert "intake_contract" not in old_plan
            assert old("POST", root + "/" + old_plan["id"] + "/approve", owner,
                       {"key": uuid4().hex, "expected_digest": old_plan["digest"]})["status"] == 200
        doc, _, snap = agency_draft(pool, c3_assets.LANDING, rfq=True, before_queue=before, approved_facts=facts(CASES[0]))
        reviewer, editor = reader(pool.api, owner, "admin"), reader(pool.api, owner, "editor")

        def inspect(*_):
            studio = doc + "/studio"
            v = accepted(pool.api.get(studio, headers=owner["headers"]))
            url = studio + "/production"
            args = {"kind": "landing", "expected_revision": v["revision"], "expected_plan_digest": old_plan["digest"],
                    "expected_version": 0, "expected_groups": {k:v["asset_digests"][k] for k in ("copy","seo")}}
            created = old("POST", url, owner, args)
            assert created["status"] == 200, created.get("guard", created["status"])
            pkg = created["body"]
            assert pkg["master"]["contract"] == "amc.sandbox-landing/1"
            path = url + "/" + pkg["id"]
            assert old("POST", path + "/approve", reviewer,
                       {"expected_digest":pkg["digest"], "note":"Reviewed the approved synthetic quote fields."})["status"] == 200
            visit = old("POST", path + "/visits", owner, {"request_id": uuid4().hex})["body"]
            form = {"request_id": uuid4().hex, "visit_id": visit["entity_id"], "quantity":2,"place":"north","days":2}
            submitted = old("POST", path + "/submissions", owner, form)
            assert submitted["status"] == 200
            assert accepted(pool.api.post(path + "/submissions", headers=owner["headers"],json=form)) == submitted["body"]
            frozen = old("GET", path + "/files/landing.html", owner)["body"]
            assert accepted(pool.api.get(path + "/files/landing.html",headers=owner["headers"])) == frozen
        lifecycle(pool.api, base, owner, buyer, pool.cases[1][2], doc, snap, old_plan, editor, inspect)
