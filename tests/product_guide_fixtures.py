"""Synthetic source, real signed Strategy work order and the ordinary guide worker mailbox."""

import json
from time import monotonic, sleep
from contextlib import contextmanager

from app import product_guide_runtime as guide
from app.pool_worker import report, run_job
from knowledge_fixtures import accepted
from migrations.apply import publish_registry
from strategy_runtime_fixtures import INTENT, commission_lab, prepare_review
from test_strategy_runtime_handoff import terms

STEPS = ["Place the batch card in the front slot.", "Insert the reference card in the rear slot."]
LIMIT = "Use dry cards only."
OBS = "One supervisor put the batch card into the index stand at shift handover."


@contextmanager
def guide_case(api, *, instructions=True):
    if instructions:
        product, audience, observation, locale = "Index Stand", "Shift supervisors", OBS, "en-US"
        fact = {"wording": " ".join(STEPS), "qualifiers": [LIMIT], "guide_procedure": {"version": "amc.product-guide-source/1", "steps": STEPS}}
    else:
        product, audience, locale = "Bảng bàn giao", "Trưởng ca", "vi-VN"
        observation = "Một trưởng ca xem bảng bàn giao tại quầy."
        fact = {"wording": "Bảng bàn giao có hai ô.", "qualifiers": ["Chỉ dùng trong nhà."]}
    complete = " ".join([fact["wording"], *fact["qualifiers"]])
    intent = INTENT | {"product": product, "audience": audience, "locale": locale}
    if not instructions:
        intent.update(
            purpose="Chuẩn bị hướng dẫn tại thời điểm bàn giao ca.",
            requirements=["Giữ nguyên điều kiện sử dụng."],
            exclusions=["theo dõi nhân viên"],
            acceptance_criteria=["Đối chiếu nội dung với nguồn đã duyệt."],
        )
    facts = [{"wording": observation, "excerpt": observation, "qualifiers": []}, {**fact, "excerpt": complete}]
    with commission_lab(api, intent=intent, observation=observation, product_statement=fact["wording"], source_facts=facts) as ctx:
        view = prepare_review(api, ctx, problem=observation, positioning=complete)
        endpoint = ctx["studio"] + "/content-handoff"
        qa = ctx["reviewer"]["headers"]
        prior = accepted(api.get(endpoint, headers=qa))
        decision = accepted(api.post(endpoint, headers=qa, json=terms(prior, ctx, observation, complete)))
        assert decision["work_order"], decision["reasons"]
        received = accepted(api.get(endpoint, headers=ctx["recipient"]["headers"]))
        assert received["work_order"]["message"] == complete
        ctx.update(
            start_guide=endpoint + "/product-guide",
            guide_request={"receipt_id": received["decision"]["receipt_id"]},
            order=received["work_order"],
            strategy_review=view,
        )
        yield ctx


def activate_guide(api, ctx):
    manifest = guide.release_manifest()
    with ctx["lab"].owner.transaction():
        publish_registry(ctx["lab"].owner, manifest)
    return accepted(
        api.put(
            ctx["base"] + "/workforce/registry/" + ctx["scope"]["campaign_id"],
            headers=ctx["owner"]["headers"],
            json={"workflow": guide.RELEASE, "action": "activate", "skills": manifest["required"]},
        )
    )


def advance_guide(ctx, *, fail_first=False, before_report=None):
    lab = ctx["lab"]
    worker = lab.workers[0]
    attempts = []
    for stage in ["director", "content", "content"] if fail_first else ["director", "content"]:
        assert worker.take() is None
        deadline = monotonic() + 12
        while not lab.dispatch():
            assert monotonic() < deadline, f"No eligible {stage} attempt after {len(attempts)} closed attempts"
            sleep(0.2)
        job = worker.take()
        assert job
        if stage == "director":
            assert job["body"].get("local_adapter") == guide.DIRECTOR
            result = run_job(lab.config, job["body"])
        else:
            if before_report:
                before_report()
            raw = {"heading": "product", "layout": "numbered"}
            if fail_first and len(attempts) == 1:
                raw = {"heading": "unsupported claim", "layout": "numbered"}
            assert "private locator" not in json.dumps(job["body"]) and "PRIVATE_SYNTHETIC" not in json.dumps(job["body"])
            result = (raw, 110, 12)
        assert report(worker.conn, job, result) and lab.consume()
        attempts.append({"stage": stage, "id": str(job["id"]), "raw": result[0], "input_tokens": result[1], "output_tokens": result[2]})
    return attempts
