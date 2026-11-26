"""The sandbox can reconcile commercial outcomes without granting an advertising upload."""
import json
from pathlib import Path

import pytest

from test_api import headers, setup_campaign, sign_up


@pytest.mark.parametrize("backend", ["sqlite", "postgres"])
def test_order_count_alone_cannot_supply_an_offline_revenue_event(backend):
    root = Path(__file__).resolve().parents[1]
    source = root / "docs/evaluation/business-intake/consultation" / f"{backend}.json"
    receipt = json.loads(source.read_text(encoding="utf-8"))
    assert receipt["synthetic"] is True
    confirmed, cancelled = receipt["after_confirmation"], receipt["after_cancellation"]
    assert confirmed["contract_digest"] == cancelled["contract_digest"]
    assert confirmed["orders"] == cancelled["orders"] == 1
    assert (confirmed["confirmed_revenue_vnd"], cancelled["confirmed_revenue_vnd"]) == (5000, 0)
    # This portable receipt traces internal work. It cannot attest a data-sharing purpose, destination or event time.
    assert all({"eventTimestamp", "consent", "destinationReferences"}.isdisjoint(event) for event in receipt["events"])


def test_offline_conversion_upload_is_outside_the_action_contract(client):
    owner = sign_up(client, "synthetic-ad-measurement")
    _, _, campaign = setup_campaign(client, owner)
    result = client.post(
        f"/api/tenants/{owner['tenant_id']}/actions",
        headers=headers(owner),
        json={"campaign_id": campaign["id"], "action_kind": "upload_offline_conversion", "payload": {"validateOnly": True}},
    )
    assert result.status_code == 422
    assert any(error["loc"][-1] == "action_kind" for error in result.json()["detail"])
