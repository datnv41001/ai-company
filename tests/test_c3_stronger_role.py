"""Resource gates and source pairing use invented evidence; no model or study file is opened."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent / "evaluation/c3"))
import stronger_role as stronger  # noqa: E402
from migrations.runtime_bundle import canonical_hash  # noqa: E402


def test_available_resources_include_context_and_workspace():
    high = 16 * stronger.GIB
    ok = stronger.resource_gate(high, high)
    assert ok["error"] is None and ok["fp16_kv_bytes"] == 448 * 2**20
    assert "RAM" in stronger.resource_gate(ok["ram_required_bytes"] - 1, high)["error"]
    assert "disk" in stronger.resource_gate(high, ok["disk_required_bytes"] - 1)["error"]


def synthetic_pair():
    workflow = stronger.WF["WF-03"]
    body = {
        "model": "amc-local",
        "temperature": 0,
        "max_tokens": 640,
        "messages": [{"role": "system", "content": "synthetic method"}, {"role": "user", "content": "synthetic brief"}],
        "response_format": {"json_schema": {"name": "c3_skills_strategy"}},
    }
    receipt = stronger.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    attempt = {"attempt_id": "synthetic", "request_sha256": receipt, "schema": "c3_skills_strategy", "raw_output": {"field": "demo"}}
    pair = {
        "case": "synthetic",
        "workflow": workflow,
        "role": "strategy",
        "request": body,
        "request_sha256": receipt,
        "projection": {"facts": []},
        "attempt_id": "synthetic",
        "checkpoints": {"strategy": {"raw_reply": attempt["raw_output"]}},
        "treatment_groups": {"strategy": {"field": "demo"}},
    }
    record = {
        "origin": "internal",
        "arm": "improved",
        "provider": "llama.cpp loopback",
        "model_sha256": stronger.WEIGHTS,
        "cases_sha256": stronger.FROZEN,
        "worker_concurrency": 1,
        "checkout": "a" * 40,
        "case": "synthetic",
        "workflow": workflow,
        "attempts": [attempt],
        "projection_digest": canonical_hash(pair["projection"]),
        "composed": {"groups": pair["treatment_groups"]},
        "matched_instruction_control": {
            "paired_treatment_attempt_id": "synthetic",
            "treatment_request_digest": canonical_hash(body),
            "treatment_attempt_request_sha256": receipt,
        },
    }
    return record, pair, attempt


def test_roles_pair_against_real_worker_format():
    record, pair, attempt = synthetic_pair()
    assert stronger.source_pair("synthetic", "WF-03", record, pair, "a" * 40) == attempt


@pytest.mark.parametrize("field", ["request", "projection", "checkpoints", "treatment_groups", "attempt_id"])
def test_altered_source_rejected(field):
    record, pair, _ = synthetic_pair()
    pair = deepcopy(pair)
    if field == "request":
        pair["request"]["messages"][0]["content"] = "different method"
    elif field == "projection":
        pair[field]["facts"].append({"id": "wrong"})
    elif field == "checkpoints":
        pair[field]["strategy"]["raw_reply"]["field"] = "altered"
    else:
        pair[field] = "wrong"
    with pytest.raises(ValueError):
        stronger.source_pair("synthetic", "WF-03", record, pair, "a" * 40)
