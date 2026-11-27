"""One-shot WF-03 prompt study. No workflow dispatch, DB access or production adapter changes."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import secrets
import signal
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app import c3_assets, c3_releases, c3_skill_library, dynamic_plan, registry_adapters  # noqa: E402

BASE = "a6fa1976f9a5d4557a4e3b64ac28dec2eb0fc0a4"
MODEL = "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"
DOC = ROOT / "docs/evaluation/rs01"
MANIFEST = ROOT / "catalog/research-strategy-v3.json"
ROLES = ("director", "research", "strategy")
GUIDE = ("Organize your reasoning into supplied facts, bounded observations, hypotheses and missing evidence. "
         "Separate the decision maker from the location. State what evidence would change your choice. "
         "Distinguish a positioning choice from an objective, and the buyer action from its measurement. "
         "Express the relevant distinctions within the existing fields.")
FIRST_KEYS = ("facts", "hypotheses", "audience", "product", "task_intent", "primary_measurement")
CAP = 220


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with path.open("x", encoding="utf8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def head():
    return subprocess.check_output(["git", "-c", "safe.directory="+ROOT.as_posix(), "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def build(case, role, arm, assignment="", earlier=None):
    manifest = json.loads(MANIFEST.read_bytes())
    projection = case["projection"]
    sources = {fact["id"]: fact for fact in projection["facts"]}
    binding = {"workflow": c3_assets.RESEARCH, "contracts": manifest["contracts"], "skills": manifest["required"]}
    run = SimpleNamespace(knowledge={"registry": binding, "c3_projection": projection, "sources": sources})
    node = SimpleNamespace(skill=role, template="dynamic-v1")
    original = registry_adapters.node_request(run, "amc-local", node=node, predecessors=earlier or {}, assignment=assignment)
    body = copy.deepcopy(original)
    body.update(max_tokens=CAP, seed=42)
    if arm == "B" and role != "director":
        body["messages"][0]["content"] += " " + GUIDE
        ctx = json.loads(body["messages"][1]["content"])
        ref = ctx["reference"]
        ctx["reference"] = {k: ref[k] for k in dict.fromkeys((*FIRST_KEYS, *ref)) if k in ref}
        body["messages"][1]["content"] = json.dumps(ctx, ensure_ascii=False)
    if arm == "A":
        assert body["messages"] == original["messages"]
    assert json.loads(body["messages"][1]["content"]) == json.loads(original["messages"][1]["content"])
    assert body["response_format"] == original["response_format"]
    assert body["temperature"] == 0 and body["max_tokens"] == CAP and body["seed"] == 42
    return body


def admit(n, calls, n_in, n_out, remaining):
    if not (0 < n <= 1500 and n + CAP <= 1280 and calls < 24 and n_in + n <= 36000
            and n_out + CAP <= 5280 and remaining > 0):
        raise RuntimeError("budget_or_context_stop")


def rendered(client, body):
    result = client.post("/apply-template", json=body).raise_for_status().json()["prompt"]
    tokens = client.post("/tokenize", json={"content": result, "add_special": True, "parse_special": True}).raise_for_status().json()["tokens"]
    assert tokens and all(type(i) is int for i in tokens)
    return len(tokens), digest(result.encode())


def machine(client):
    props = client.get("/props").raise_for_status().json()
    with Path(props["model_path"]).open("rb") as f:
        weights = hashlib.file_digest(f, "sha256").hexdigest()
    assert weights == MODEL and props["total_slots"] == 1 and props["model_alias"] == "amc-local"
    assert props["default_generation_settings"]["n_ctx"] == 1280
    return dict(model_sha256=weights, template_sha256=digest(props["chat_template"].encode()),
                build=props["build_info"], context=1280, slots=1)


def input_pins():
    return {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in
            [DOC/"packets.json", DOC/"PROTOCOL.md", Path(__file__).resolve(), MANIFEST]}


def prepare(folder, client, cases):
    assert len(cases) == len({c["id"] for c in cases}) == 4
    assert head() == BASE or subprocess.run(["git","-c","safe.directory="+ROOT.as_posix(),"diff","--quiet",BASE,"HEAD","--","app","catalog","migrations"],cwd=ROOT).returncode == 0
    counts = []
    for case in cases:
        for role in ROLES:
            # Downstream calls get real earlier outputs at admission. Long synthetic text probes headroom.
            assignment = "" if role == "director" else c3_releases.DIRECTOR_ASSIGNMENTS[role][1]
            earlier = {"research": " observation" * 180} if role == "strategy" else {}
            a = build(case, role, "A", assignment, earlier)
            b = build(case, role, "B", assignment, earlier)
            assert a["response_format"] == b["response_format"]
            assert json.loads(a["messages"][1]["content"]) == json.loads(b["messages"][1]["content"])
            for arm, body in (("A", a), ("B", b)):
                n, sha = rendered(client, body)
                admit(n, 0, 0, 0, 1800)
                counts.append(dict(case=case["id"], role=role, arm=arm, tokens=n,
                                   request_sha256=digest(encoded(body)), rendered_sha256=sha,
                                   schema_sha256=digest(encoded(body["response_format"]))))
    for args in [(1501,0,0,0,1),(1061,0,0,0,1),(10,24,0,0,1),(10,0,35991,0,1),(10,0,0,5061,1),(10,0,0,0,0)]:
        try:
            admit(*args)
        except RuntimeError:
            continue
        raise AssertionError("stop guard failed")
    rng = random.SystemRandom()
    first = list("AABB")
    rng.shuffle(first)
    pairs = []
    for case, arm in zip(cases, first, strict=True):
        left = rng.choice(("A", "B"))
        pairs.append(dict(id=case["id"], first=arm, left=left))
    rng.shuffle(pairs)
    key = {"nonce": secrets.token_hex(32), "pairs": pairs}
    save(folder/"mapping.json", key)
    save(DOC/"LOCK.json", dict(baseline=BASE, sources=input_pins(), machine=machine(client),
         mapping_commitment=digest(encoded(key)), preflight=counts, calls=24, input_cap=1500, output_cap=220,
         input_total=36000, output_total=5280, seconds=1800, seed=42, temperature=0))


def validate(case, role, value, schema):
    if role == "director":
        props = schema["properties"]
        if set(value) != set(props) or any(value[k] not in props[k]["enum"] for k in props):
            raise ValueError("invalid Director assignment")
        plan = c3_skill_library.director_proposal(c3_assets.RESEARCH, value)
        dynamic_plan.compile_plan(plan, ["strategy"])
        return value
    sources = {f["id"]: f for f in case["projection"]["facts"]}
    return c3_skill_library.validate(value, role, {}, sources)


def execute(folder, client, cases, pid):
    lock = json.loads((DOC/"LOCK.json").read_bytes())
    key = json.loads((folder/"mapping.json").read_bytes())
    assert digest(encoded(key)) == lock["mapping_commitment"] and input_pins() == lock["sources"]
    assert machine(client) == lock["machine"]
    save(folder/"started.json", {"checkout":head(), "started_utc":time.time()})  # exclusive one-shot guard
    start = time.monotonic()
    def stop_server():
        os.kill(pid, signal.SIGTERM)
    timer = threading.Timer(1800, stop_server)
    timer.daemon = True
    timer.start()
    journal = []
    n_in = n_out = 0
    stop = None
    try:
        for pair in key["pairs"]:
            case = next(c for c in cases if c["id"] == pair["id"])
            for arm in (pair["first"], "B" if pair["first"] == "A" else "A"):
                assigns = {}
                earlier = {}
                for role in ROLES:
                    body = build(case, role, arm, assigns.get(role,""), earlier)
                    n, sha = rendered(client, body)
                    remaining = 1800 - (time.monotonic()-start)
                    admit(n, len(journal), n_in, n_out, remaining)
                    item = dict(case=case["id"], arm=arm, role=role, request=body, rendered_sha256=sha,
                                request_sha256=digest(encoded(body)), input_preflight=n, elapsed_start=time.monotonic()-start)
                    journal.append(item)
                    path = folder/f"call-{len(journal):02}.json"
                    save(path.with_suffix(".intent"),item)
                    result = client.post("/v1/chat/completions", json=body, timeout=min(remaining,300))
                    item["response_text"] = result.text
                    item["http_status"] = result.status_code
                    save(path.with_suffix(".raw"), item)  # preserve even if usage or format cannot be decoded
                    result.raise_for_status()
                    reply = result.json()
                    usage = reply["usage"]
                    actual, generated = usage["prompt_tokens"], usage["completion_tokens"]
                    assert type(actual) is int and type(generated) is int
                    item.update(input_tokens=actual, output_tokens=generated, elapsed_end=time.monotonic()-start)
                    n_in += actual
                    n_out += generated
                    if actual != n or not 0 <= generated <= CAP:
                        raise RuntimeError("token_meter_mismatch")
                    choice = reply["choices"][0]
                    item["first_text"] = choice["message"]["content"]
                    item["finish"] = choice["finish_reason"]
                    try:
                        if choice["finish_reason"] != "stop":
                            raise ValueError("incomplete_output")
                        val = validate(case, role, json.loads(item["first_text"]), body["response_format"]["json_schema"]["schema"])
                        if role == "director":
                            assigns = dict(research=val["primary_assignment"], strategy=val["secondary_assignment"])
                        if role == "research":
                            earlier = {"research":val["text"][:1400]}
                    except (ValueError, KeyError, RuntimeError) as exc:
                        item["error"] = str(exc) or type(exc).__name__
                        save(path,item)
                        break
                    save(path,item)
    except Exception as exc:
        stop = str(exc) or type(exc).__name__
        raise
    finally:
        timer.cancel()
        save(folder/"journal.json",dict(checkout=head(), calls=journal, input_tokens=n_in, output_tokens=n_out,
                                        wall_seconds=round(time.monotonic()-start,3),stop=stop))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=["prepare","run"])
    parser.add_argument("folder",type=Path)
    args=parser.parse_args()
    server=json.loads((args.folder/"server.json").read_text(encoding="utf-8-sig"))
    cases=json.loads((DOC/"packets.json").read_bytes())
    with httpx.Client(base_url=f"http://127.0.0.1:{int(server['port'])}",trust_env=False,timeout=15) as client:
        if args.mode=="prepare":
            prepare(args.folder,client,cases)
        else:
            execute(args.folder,client,cases,int(server["pid"]))
