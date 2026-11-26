"""An approved materials unit must survive both RFQ writes and journal readback."""
from datetime import datetime, timedelta, timezone
from typing import get_args
from uuid import uuid4

import pytest

from app import c3_assets
from app.campaign_operations_crm import DETAIL_UNITS
from app.knowledge_contracts import Unit
from campaign_planner_fixtures import CASES, prepare_inputs
from knowledge_fixtures import accepted


def test_material_units_belong_to_the_knowledge_contract():
    assert DETAIL_UNITS["materials_v1"] == {"piece", "box", "m²", "tonne", "kg"}
    assert all(units <= set(get_args(Unit)) for units in DETAIL_UNITS.values())


@pytest.mark.parametrize(("unit", "quantity"), [("m²", "12.375"), ("piece", "12"), ("box", "12"), ("tonne", "12.375"), ("kg", "12.375")])
def test_approved_materials_rfq_creation_and_completion(api, agency, unit, quantity):
    owner, base, ((buyer, scope), _) = agency
    campaign = next(iter(scope["campaigns"]))
    root = base + "/campaigns/" + campaign
    brand = next(c["brand_id"] for c in accepted(api.get(base + "/campaigns", headers=owner["headers"])) if c["id"] == campaign)
    case = CASES[0] | {"unit": unit, "cta": "Gửi yêu cầu báo giá theo đơn vị trong bảng đã duyệt."}
    snapshots, _ = prepare_inputs(api, owner, buyer, next(iter(scope["clients"])), brand, campaign, case, workflows=(c3_assets.LANDING,))
    plans = root + "/engine/plans"
    draft = accepted(api.post(plans, headers=owner["headers"], json={
        "key": uuid4().hex, "expected_revision": 0, "target_outcome": case["kpi"],
        "budget_vnd": 30000, "duration_days": 30, "manifest_ids": [s["id"] for s in snapshots],
    }))
    accepted(api.post(plans + "/" + draft["id"] + "/approve", headers=owner["headers"], json={
        "key": uuid4().hex, "expected_digest": draft["digest"],
    }))
    assert draft["selling_unit"] == unit

    def send(kind, **data):
        return api.post(root + "/sandbox/commands", headers=owner["headers"], json={
            "kind": kind, "plan_id": draft["id"], "request_id": uuid4().hex, **data,
        })

    now = datetime.now(timezone.utc)
    details = {"schema_id": "materials_v1", "application": "Acoustic lining", "delivery_access": "Ground-floor loading bay"}
    common = {"product_id": draft["product_id"], "occurred_at": now.isoformat()}
    filled = {"quantity": quantity, "location": "Synthetic site", "required_date": (now.date() + timedelta(days=7)).isoformat(),
              "contact_purpose": "quote_request", "details": details}
    # CompleteRFQ derives its unit from the original journal entry. Exercise it even if direct RFQ fails.
    accepted(send("rfq", rfq_id="follow-up", unit=unit, contact_purpose="none", **common))
    finished = send("complete_rfq", rfq_id="follow-up", expected_revision=1, **filled)
    direct = send("rfq", rfq_id="direct", unit=unit, **common, **filled)
    assert (direct.status_code, finished.status_code) == (200, 200), (direct.text, finished.text)

    invalid_unit = "m²".encode("utf-8").decode("latin-1")
    assert send("rfq", rfq_id="invalid", unit=invalid_unit, **common, **filled).status_code == 422
    if unit in {"piece", "box"}:
        assert send("rfq", rfq_id="fraction", unit=unit, **common, **(filled | {"quantity": "1.5"})).status_code == 409
    rows = {row["id"]: row for row in accepted(api.get(root + "/sandbox", headers=owner["headers"]))["leads"]}
    assert set(rows) == {"direct", "follow-up"}
    for lead_id, revision in (("direct", 1), ("follow-up", 2)):
        row = rows[lead_id]
        assert (row["state"], row["revision"], row["unit"]) == ("qualified", revision, unit)
        assert {k: row[k] for k in filled} == filled
