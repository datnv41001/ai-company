"""Run using pytest against the detached reviewed checkout. RED is expected on the pinned commit."""
import json
import os
from pathlib import Path
import subprocess
import sys

REVIEWED = "d79f76373af99585b6b8b720b2a60a93f882c48b"


def test_reviewed_recipient_can_recover_the_original_commission():
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == REVIEWED
    sys.path.insert(0, str(Path.cwd() / "tests"))
    from agency_fixtures import postgres_api
    from knowledge_fixtures import accepted
    from strategy_runtime_fixtures import INTENT, commission_lab, prepare_review
    from test_strategy_runtime_handoff import terms

    with postgres_api() as api, commission_lab(api) as ctx:
        prepare_review(api, ctx)
        endpoint = ctx["studio"] + "/content-handoff"
        reviewer = ctx["reviewer"]["headers"]
        ready = accepted(api.get(endpoint, headers=reviewer))
        request = terms(ready, ctx)
        signed = accepted(api.post(endpoint, headers=reviewer, json=request))
        recipient = accepted(api.get(endpoint, headers=ctx["recipient"]["headers"]))
        assert recipient["status"] == signed["status"] == "draft_for_approval"
        assert recipient["decision"]["receipt_id"] == signed["decision"]["receipt_id"]
        order = recipient["work_order"]
        required = {k: INTENT[k] for k in ("buyer_action", "editorial_style", "requirements", "exclusions", "acceptance_criteria")}
        missing = {name: value for name, value in required.items()
                   if not all(item in json.dumps(order) for item in (value if isinstance(value, list) else [value]))}
        output = Path(os.environ["AMC_RUNTIME_STRATEGY_EVIDENCE"])
        output.mkdir(parents=True, exist_ok=True)
        capture = {"head": REVIEWED, "tree":subprocess.check_output(["git","rev-parse","HEAD^{tree}"],text=True).strip(),
                   "commission": required, "revision":ready["revision"], "content_digest":ready["content_digest"],
                   "signed_receipt":signed["decision"]["receipt_id"], "signed_buying_situation":request["buying_situation"],
                   "signed_interpretation":request["interpretation"],
                   "signer_order_without_restricted_sources":{k:v for k,v in signed["work_order"].items() if k!="sources"},
                   "recipient": {"status":recipient["status"], "decision":recipient["decision"], "work_order":order},
                   "missing_commission_fields":missing}
        (output / "reviewed-handoff-red.json").write_text(json.dumps(capture,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        assert not missing, f"Recipient lost signed commissioning fields: {', '.join(missing)}"
