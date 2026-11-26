"""Run one authorized, CPU-only Qwen pass and retain every attempt, including invalid or unfinished cases."""

import argparse
import asyncio
import json
from pathlib import Path
from time import monotonic

import httpx

from advisory_study import MODEL, host
from handoff_comparison import DATA, PROMPT, check_cards, digest, load, save

REQUEST_CAP = 24
INPUT_CAP = 700
OUTPUT_CAP = 80
WALL_CAP = 1200
PER_CARD_CAP = 45
SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "decision": {"type": "string", "enum": ["ask", "clarify_policy", "ready"]},
        "field": {"type": "string"},
        "question": {"type": "string"},
    },
    "required": ["id", "decision", "field", "question"],
    "additionalProperties": False,
}


def render(card):
    # Explicit Qwen2.5 ChatML; passing the counted IDs directly eliminates a second template or implicit BOS.
    user = json.dumps(card, ensure_ascii=False, separators=(",", ":"))
    return f"<|im_start|>system\n{PROMPT}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"


async def predict_one(client, card, receipt):
    prompt = render(card)
    receipt["prompt"] = prompt
    tokenized = await client.post("/tokenize", json={"content": prompt, "add_special": False, "parse_special": True})
    tokenized.raise_for_status()
    tokens = tokenized.json()["tokens"]
    receipt["input_tokens"] = len(tokens)
    if not tokens or len(tokens) > INPUT_CAP:
        receipt["status"] = "input_cap"
        return {}
    request = {
        "prompt": tokens,
        "n_predict": OUTPUT_CAP,
        "seed": 42,
        "temperature": 0,
        "json_schema": SCHEMA,
        "stream": False,
        "cache_prompt": False,
        "stop": ["<|im_end|>", "<|endoftext|>"],
    }
    receipt.update(request=request, attempted=True, weights_sha256=MODEL)
    response = await client.post("/completion", json=request)
    response.raise_for_status()
    body = response.json()
    content = body["content"]
    receipt.update(
        raw_output=content,
        output_tokens=body["tokens_predicted"],
        tokens_evaluated=body["tokens_evaluated"],
        stop=body.get("stop_type"),
        timings=body.get("timings"),
        model=body.get("model"),
    )
    if receipt["output_tokens"] > OUTPUT_CAP or receipt["tokens_evaluated"] > INPUT_CAP:
        raise RuntimeError("Engine token usage exceeded its preflight")
    if body.get("stop_type") == "limit" or body.get("truncated") or body.get("stopped_limit"):
        receipt["status"] = "length"
        return {}
    try:
        answer = json.loads(content)
    except ValueError:
        answer = {}
    receipt["status"] = "returned" if isinstance(answer, dict) and answer.get("id") == card["id"] else "invalid"
    return answer if receipt["status"] == "returned" else {}


async def exchange_cards(url, cards, out, start):
    answers = []
    halt = None
    receipts = out / "receipts"
    receipts.mkdir()
    async with httpx.AsyncClient(base_url=url, trust_env=False, timeout=PER_CARD_CAP) as client:
        for card in cards:
            begin = monotonic()
            receipt = {"id": card["id"], "attempted": False, "status": halt or "pending"}
            time_left = WALL_CAP - (begin - start)
            if time_left <= 0:
                halt = receipt["status"] = "total_timeout"
            if not halt:
                try:
                    answer = await asyncio.wait_for(predict_one(client, card, receipt), timeout=min(PER_CARD_CAP, time_left))
                    if answer:
                        answers.append(answer)
                except (TimeoutError, httpx.HTTPError, RuntimeError, ValueError, KeyError) as err:
                    # Terminate the run on a transport/budget failure. Never retry the possibly executed request.
                    receipt.update(status="failed", error=type(err).__name__)
                    halt = "unstarted_after_failure"
            receipt["wall_seconds"] = round(monotonic() - begin, 4)
            save(receipts / (card["id"] + ".json"), receipt)
    save(out / "qwen.json", answers)


def run(exe, weights, input_path, expected_hash, out):
    if digest(input_path) != expected_hash:
        raise ValueError("Cohort must match the custodian's preregistered digest")
    cards = load(input_path)
    check_cards(cards)
    out.mkdir(exist_ok=False, parents=True)
    start = monotonic()
    with host(exe, weights, out) as client:
        details = load(out / "host.json")
        if "1f8baae28" not in details["engine_version"]:
            raise ValueError("Study requires the previously used llama.cpp revision")
        asyncio.run(exchange_cards(str(client.base_url), cards, out, start))
    save(
        out / "run.json",
        {
            "cohort_sha256": expected_hash,
            "protocol_sha256": digest(DATA / "PROTOCOL.md"),
            "runner_sha256": digest(Path(__file__)),
            "wall_seconds": round(monotonic() - start, 4),
            "input_cap": INPUT_CAP,
            "output_cap": OUTPUT_CAP,
            "request_cap": REQUEST_CAP,
            "new_provider_fee": 0,
            "energy_cost": None,
            "professional_labor_cost": None,
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("exe", "weights", "cards", "out"):
        p.add_argument(key, type=Path)
    p.add_argument("--cohort-sha256", required=True)
    p.add_argument("--authorized-local-run", action="store_true", required=True, help="Only when the new local 24-call budget is separately approved")
    args = p.parse_args()
    run(args.exe, args.weights, args.cards, args.cohort_sha256, args.out)
