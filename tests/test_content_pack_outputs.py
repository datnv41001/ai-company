"""Generate both matched departmental packs through the authenticated application."""
from pathlib import Path
import json
import os
from time import perf_counter, process_time
from uuid import uuid4

import pytest

from campaign_planner_fixtures import prepare_inputs
from knowledge_fixtures import accepted
from app.c3_studio import buyer_action


CASES = json.loads((Path(__file__).parent / "evaluation/department/briefs-v1.json").read_text(encoding="utf-8"))["cases"]


def test_ad_copy_limits():
    from app.campaign_content_pack import search_ad_checks

    assert search_ad_checks(["Gửi yêu cầu", "先" * 15, "b" * 30], ["d" * 90, "c" * 90]) == []
    assert [i["field"] for i in search_ad_checks(["先" * 16, "b", "c"], ["d" * 91, "e"])] == ["headline", "description"]
    assert search_ad_checks(["a", "a", "b", "c"], ["e", "f"])[0]["reason"] == "count_or_duplicates"


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_department_pack_for_approved_study_case(api, agency, case):
    owner, base, ((customer, scope), _) = agency
    cid = next(iter(scope["campaigns"]))
    brands = accepted(api.get(base + "/campaigns", headers=owner["headers"]))
    brand = next(c["brand_id"] for c in brands if c["id"] == cid)
    snapshots, _ = prepare_inputs(api, owner, customer, next(iter(scope["clients"])), brand, cid, case)
    root = base + "/campaigns/" + cid + "/engine/plans"
    plan = accepted(api.post(root, headers=owner["headers"], json={
        "key": uuid4().hex, "expected_revision": 0, "manifest_ids": [s["id"] for s in snapshots],
        "duration_days": 14, "budget_vnd": 300001}))
    url = root + "/" + plan["id"]
    accepted(api.post(url + "/approve", headers=owner["headers"],
                      json={"expected_digest": plan["digest"], "key": uuid4().hex}))
    started, cpu_start = perf_counter(), process_time()
    response = api.get(url + "/content-pack", headers=owner["headers"])
    elapsed, cpu = perf_counter() - started, process_time() - cpu_start
    pack = accepted(response)
    assert pack["plan_digest"] == plan["digest"]
    assert case["wording"] in pack["website"]["commercial_terms"]
    assert case["qualifier"] in pack["organic_search"]["answer"]
    public_cta = buyer_action(snapshots[0]["projection"])
    assert public_cta and pack["website"]["cta"] == public_cta
    assert all(case["product"] in post["copy"] and public_cta in post["copy"] for post in pack["social"])
    assert all(term in pack["website"]["body"] for term in case["must_ask"])
    if case["id"] == "receipt-map":
        assert pack["buyer_fields"] == ["site", "receiving_shift"]
        assert all("ca nhận hàng cần quan sát" in post["copy"] for post in pack["social"])
    else:
        assert "receiving_shift" not in pack["buyer_fields"]
    assert [g["budget_vnd"] for g in pack["advertising"]["ad_groups"]] == [150000, 150001]
    assert pack["advertising"]["publication_receipt"] is None
    assert not pack["advertising"]["format_issues"]
    if pack["advertising"]["measurement"].get("status") == "requires_measurement_contract":
        assert " · " not in pack["advertising"]["measurement"]["approved_label"]
    if destination := os.getenv("AMC_CONTENT_PACK_EVIDENCE"):
        out = Path(destination)
        out.mkdir(parents=True, exist_ok=True)
        (out / (case["id"] + ".json")).write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        measurements = {"case": case["id"], "plan_digest": plan["digest"], "wall_seconds": round(elapsed, 4),
                        "api_process_cpu_seconds": round(cpu, 4), "response_bytes": len(response.content),
                        "model_invocations": 0, "provider_fees": 0, "human_labor_cost": None,
                        "electricity_cost": None, "accepted_work_cost": None}
        (out / (case["id"] + "-resources.json")).write_text(json.dumps(measurements, indent=2) + "\n", encoding="utf-8")
