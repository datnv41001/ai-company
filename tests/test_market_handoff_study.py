"""Synthetic, non-holdout contracts for an offline handoff experiment."""

import asyncio
from pathlib import Path
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent / "evaluation/department"))
from handoff_comparison import improved  # noqa: E402
from handoff_infer import INPUT_CAP, predict_one  # noqa: E402


def card(**updates):
    return {
        "id": "example",
        "journey": "rfq",
        "locale": "en",
        "brief": "Delivery point is required.",
        "buyer_message": "",
        "required_fields": [{"id": "drop", "label": "delivery point"}],
        "received_fields": {"drop": "pending"},
        **updates,
    }


def test_notes_override_fields_without_mutating_snapshot():
    c = card(buyer_message="Delivery point: outlet 9.")
    assert improved(c)["decision"] == "ready"
    assert c["received_fields"] == {"drop": "pending"}
    assert improved(card(received_fields={"drop": "outlet 9"}, buyer_message="Delivery point is no longer valid."))["field"] == "drop"
    assert improved(card(brief="Conflicting approval schedules."))["decision"] == "clarify_policy"


def test_input_cap_skips_inference():
    calls = []

    def route(request):
        calls.append(request.url.path)
        if request.url.path == "/tokenize":
            return httpx.Response(200, json={"tokens": [1] * (INPUT_CAP + 1)})
        raise AssertionError("Unexpected inference after input cap")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(route), base_url="http://127.0.0.1") as client:
            rec = {"attempted": False}
            assert await predict_one(client, card(), rec) == {} and rec["status"] == "input_cap" and not rec["attempted"]

    asyncio.run(run())
    assert calls == ["/tokenize"]
