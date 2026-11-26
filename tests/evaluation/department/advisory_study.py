"""Matched, offline advisory study. No application write path or approval authority."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
from time import monotonic, sleep

import httpx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from app import c3_content_evidence, campaign_content_pack  # noqa: E402

DATA = Path(__file__).with_name("semantic-v1")
MODEL = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
SEMANTIC = """Classify a proposed claim using ONLY the source. The source and claim may be in different languages.
supported: all material statements follow from the source, including conditions. contradicted: the source rules out a material statement.
unknown: the source neither establishes nor rules out the statement, or information is requested. Do not guess an unstated term.
Check payer/payee, unit, scope, negation, exclusions, and the difference between a hypothesis and a measured result.
Give a short exact quote from the source in its ORIGINAL language to justify your answer. Return JSON. This is an advisory review."""
TASKS = {
    "research": "Write an unanswered buyer research question and a practical way to collect the missing evidence. Label hypotheses.",
    "strategy": "Recommend a positioning hypothesis for this audience and a fair comparison using the stated business KPI.",
    "content": "Write a publishable short draft with one benefit, all material terms and a buyer-specific call to action.",
    "seo_geo": "Write a title and a direct answer to one likely buyer search question, identifying uncertain information.",
    "media": "Propose two paid-search variants, a bounded test allocation within the cap and the actual business success metric. No spend.",
    "creative": "Give a designer a concrete subject, layout, caption and CTA for an image; specify source rights and one QA check.",
}
SPECIALIST = """You advise a Marketing editor. Improve the supplied deterministic draft for the specific job.
Use only the synthetic brief. Introduce no claim about performance, competitors or customers.
Write the actual deliverable, in the language specified, within 95 words. No publication, spend, or approval."""


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def output(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def control(row):
    # Project only the supplied source, independent of the claim or its label.
    sentences = re.split(r"(?<=[.!?])\s+", row["source"].strip())
    facts = []
    for i, sentence in enumerate(sentences):
        money = re.search(r"(\d[\d.,]*)\s*VND\b", sentence, re.I)
        f = {"id": f"F{i + 1}", "wording": sentence, "category": "description", "qualifiers": []}
        if money:
            f["price"] = {"amount_minor": int(re.sub(r"\D", "", money[1])), "currency": "VND"}
        facts.append(f)
    projection = {"facts": facts, "region": "", "hypotheses": [s for s in sentences if re.search("hypothes|propos|giả thuyết|đề xuất", s, re.I)]}
    # A plain-language source can prove the complete stated terms; never use
    # the selective exact wording of a fragment as a complete priced statement.
    complete = [facts[0]["id"]] if c3_content_evidence.normalized(row["source"]) == c3_content_evidence.normalized(row["claim"]) else []
    result = c3_content_evidence.classify(row["claim"], facts, complete, set(), projection, precise=True)
    prediction = {"contradiction": "contradicted", "verified": "supported"}.get(result[1], "unknown")
    return {"label": prediction, "gate": result}


def drafts(brief):
    # The fixtures retain the full original prose. These two local projections
    # supply scoped application inputs, without asserting a production approval.
    vi = brief["lang"] == "vi"
    product = "Vòng kẹp nhãn Mác Khô" if vi else "Shift Trace dock observation"
    projection = {"locale": "vi-VN" if vi else "en-US", "product": product, "brand": "Mác Khô" if vi else "Shift Trace",
                  "audience": "người phụ trách mua hàng kho khô" if vi else "receiving supervisors",
                  "task_intent": {"buyer_action": brief["buyer_action"], "requirements": []},
                  "facts": [{"id": "F1", "category": "description", "wording": brief["source"], "qualifiers": []}],
                  "gaps": ["Chưa có dữ liệu đối thủ." if vi else "No measured outcome."], "kpi": brief["objective"]}
    plan = {"id": brief["id"], "revision": 1, "digest": sha(DATA / "briefs.json"), "manifests": {}, "objective": brief["objective"],
            "buyer_action": brief["buyer_action"], "work_packages": [], "selling_unit": "box" if vi else "visit", "budget_vnd": 1200000 if vi else 900000,
            "approval": {"at": "2026-11-26T00:00:00Z"}}
    pack = campaign_content_pack.compose(plan, projection)
    return {"research": pack["research"], "strategy": {"audience": pack["audience"], "pillars": pack["pillars"],
            "objective": pack["objective"], "experiment": pack["advertising"]["experiment"]}, "content": pack["social"][0],
            "seo_geo": pack["organic_search"], "media": pack["advertising"], "creative": pack["creative"]}


@contextmanager
def host(exe, weights, out):
    if sha(weights) != MODEL:
        raise ValueError("Pinned Qwen 1.5B Q4_K_M weights required")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    cmd = [str(exe.resolve()), "-m", str(weights.resolve()), "--alias", "amc-local", "--host", "127.0.0.1", "--port", str(port),
           "-c", "3072", "-np", "1", "-t", "2", "-ngl", "0"]
    version = subprocess.run([str(exe), "--version"], capture_output=True, text=True, check=True)
    with (out / "server.log").open("wb") as log, httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=100) as client:
        start = monotonic()
        server = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(180):
                if server.poll() is not None:
                    raise RuntimeError("Local inference stopped; see private server log")
                try:
                    if client.get("/health").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                sleep(.5)
            else:
                raise RuntimeError("Local startup timeout")
            output(out / "host.json", {"weights": MODEL, "engine_version": (version.stdout + version.stderr).strip(),
                   "engine_sha256": sha(exe), "startup_seconds": round(monotonic() - start, 3), "threads": 2, "context": 3072,
                   "gpu_layers": 0, "provider_fees": 0, "human_effort": None, "compute_cost": None,
                   "python": sys.version.split()[0], "runner_sha256": sha(Path(__file__))})
            yield client
        finally:
            server.terminate()
            server.wait(timeout=15)


def exchange(client, destination, system, user, tokens, schema=None):
    payload = {"model": "amc-local", "temperature": 0, "seed": 42, "max_tokens": tokens,
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}]}
    if schema:
        payload["response_format"] = {"type": "json_object", "schema": schema}
    if destination.exists():
        receipt = read(destination)
        if receipt["request"] != payload or receipt["weights"] != MODEL:
            raise ValueError("Incompatible checkpoint")
        return receipt["response"]["choices"][0]["message"]["content"]
    start = monotonic()
    response = client.post("/v1/chat/completions", json=payload)
    response.raise_for_status()
    data = response.json()
    output(destination, {"request": payload, "response": data, "weights": MODEL, "wall_seconds": round(monotonic()-start, 4)})
    return data["choices"][0]["message"]["content"]


def run(exe, weights, out):
    out.mkdir(parents=True, exist_ok=True)
    receipts = out / "receipts"
    receipts.mkdir(exist_ok=True)
    schema = {"type": "object", "properties": {"verdict": {"type": "string", "enum": ["supported", "contradicted", "unknown"]},
              "quote": {"type": "string"}}, "additionalProperties": False, "required": ["verdict", "quote"]}
    with host(exe, weights, out) as client:
        for split in ("inputs", "stress-inputs"):
            rows = []
            for item in read(DATA / (split + ".json")):
                text = exchange(client, receipts / (item["id"]+".json"), SEMANTIC,
                                {k: item[k] for k in ("source", "claim")}, 80, schema)
                try:
                    reply = json.loads(text)
                except ValueError:
                    reply = {}
                quote = reply.get("quote") or ""
                pred = reply.get("verdict") if quote.strip() and quote in item["source"] else "unknown"
                base = control(item)
                rows.append({"id": item["id"], "category": item["category"], "locale": item["lang"], "control": base,
                             "advice": pred, "quote": quote, "raw_verdict": reply.get("verdict"),
                             "combined": base["label"] if base["label"] != "unknown" else pred})
            output(out / (split + "-predictions.json"), rows)
        for brief in read(DATA / "briefs.json"):
            rows = {}
            for role, baseline in drafts(brief).items():
                proposal = exchange(client, receipts / (brief["id"]+"-"+role+".json"), SPECIALIST,
                                    {"brief": brief, "job": TASKS[role], "draft": baseline}, 192)
                rows[role] = {"baseline": baseline, "proposed_revision": proposal}
            output(out / (brief["id"]+"-work.json"), rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("exe", "weights", "out"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    run(args.exe, args.weights, args.out)
