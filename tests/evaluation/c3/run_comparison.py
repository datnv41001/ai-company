"""Synthetic Marketing comparison via normal API, dispatcher, worker and deliverable.

Run in a fresh, migrated, local amc_test database. This lab uses no paid provider.
"""
# ruff: noqa: E402 -- standalone lab loads the repository and its synthetic API fixtures.
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic, sleep
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from agency_fixtures import account, create
from identity_fixtures import invite_member
from pool_lab import Lab, lab_client
from app.main import app
from app.pool_worker import report
from app.workforce_gateway import GatewayError, infer
from migrations.apply import publish_registry
from scripts.provision_pool import route

CASES = Path(__file__).with_name("cases.json")
LEGACY = {"WF-03": "research-strategy-v1.json", "WF-13": "landing-seo-v4.json"}


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


class MarketingLab(Lab):
    def __init__(self, api, dsn, case):
        self.case = case
        super().__init__(api, dsn, workflow="dynamic-v1")

    def seed(self, label, admin):
        if label != "A":
            return
        c = self.case
        base = "/api/tenants/" + admin["tenant"]
        self.reader = account(self.api, "Reader")
        editor = account(self.api, "Operator")
        self.client = create(self.api, base + "/clients", admin, {"name": c["company"]})["id"]
        self.brand = create(self.api, base + "/brands", admin, {
            "client_id": self.client, "name": c["brand"], "product_truth": c["product"],
            "brand_guidelines": "Viết bằng tiếng Việt. Chỉ dùng thông tin đã cung cấp.",
        })["id"]
        self.campaign = create(self.api, base + "/campaigns", admin, {
            "brand_id": self.brand, "name": c["sku"], "brief": c["product"], "objective": c["objective"],
        })["id"]
        for actor, role, scope in [(editor, "editor", {}), (self.reader, "client_viewer", {"client_id": self.client})]:
            invite_member(self.api, base, admin["headers"], actor["headers"], email=actor["email"], role=role, **scope)
        for worker, _ in self.logins[1:]:
            route(self.owner, worker, admin["tenant"], self.client, self.brand, self.campaign, editor["id"])
        self.cases.append((base, admin, self.reader, self.client, self.campaign))


def queue_legacy(lab, kind):
    c = lab.case
    base, admin, reader, _, campaign = lab.cases[0]
    manifest = json.loads((ROOT / "catalog" / LEGACY[kind]).read_text(encoding="utf8"))
    workflow = f"{manifest['workflow_id']}@{manifest['workflow_version']}" if "workflow_version" in manifest else f"{manifest['workflow_id']}@{manifest['version']}"
    with lab.owner.transaction():
        publish_registry(lab.owner, manifest)
    lab.api.put(base + "/workforce/registry/" + campaign, headers=admin["headers"], json={
        "action": "activate", "workflow": workflow, "skills": manifest["required"],
    }).raise_for_status()
    brief = create(lab.api, base + "/workforce/briefs", admin, {
        "title": c["objective"], "recipient_id": reader["id"], "campaign_id": campaign,
    })
    uri = base + "/workforce/briefs/" + brief["id"]
    refs = [{"label": f["id"], "excerpt": f["wording"] + " " + f["qualifiers"]} for f in c["facts"]]
    refs.append({"label": "Giả thuyết và khoảng trống", "excerpt": c["hypotheses"][0] + " " + c["gaps"][0]})
    lab.api.put(uri + "/submission", headers=reader["headers"], json={
        "objective": c["objective"] + ". KPI: " + c["kpi"] + ". Kênh: " + c["channel"],
        "audience": c["audience"], "offer": c["product"] + ". CTA: " + c["cta"], "sources": refs,
    }).raise_for_status()
    queued = lab.api.post(uri + "/run", headers=admin["headers"], json={
        "registry_workflow": workflow, "max_parallel_nodes": 1, "budget_microusd": 10000, "workflow": "dynamic-v1",
    })
    queued.raise_for_status()
    return queued.json()["id"], workflow


def run_one(lab, kind, arm, folder):
    if arm == "legacy":
        rid, release = queue_legacy(lab, kind)
    else:
        from candidate_fixture import queue_projected
        rid, release = queue_projected(lab, kind, improved=arm == "improved")
    base, admin, *_ = lab.cases[0]
    lab.runs = [rid]
    started = monotonic()
    attempts = []
    while lab.states()[0] in ("queued", "running") and monotonic() - started < 540:
        if lab.consume() or lab.dispatch():
            continue
        job = lab.workers[0].take()
        if not job:
            job = lab.workers[1].take()
            worker = lab.workers[1]
        else:
            worker = lab.workers[0]
        if not job:
            sleep(0.1)
            continue
        assert job["run"] == rid
        body = job["body"]
        entry = {"attempt_id": job["id"], "schema": body["response_format"]["json_schema"]["name"],
                 "request_sha256": hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
        try:
            output, inputs, outputs = infer(lab.config, body)
            assert report(worker.conn, job, [output, inputs, outputs])
            entry.update(input_tokens=inputs, output_tokens=outputs, raw_output=output)
        except GatewayError as exc:
            assert report(worker.conn, job, result=exc.usage, error=str(exc))
            entry["error"] = str(exc)
            if exc.usage:
                entry.update(input_tokens=exc.usage[1], output_tokens=exc.usage[2])
        attempts.append(entry)
    data = lab.api.get(base + "/workforce/runs/" + rid, headers=admin["headers"])
    data.raise_for_status()
    value = data.json()
    journal = value["journal"]
    record = {"case": lab.case["id"], "workflow": release, "arm": arm, "run_id": rid,
              "state": value["state"], "last_error": value.get("last_error"), "runtime_s": round(monotonic()-started, 3),
              "provider_fee_usd": 0, "unmetered_attempts": sum("input_tokens" not in a for a in attempts),
              "input_tokens": sum(a.get("input_tokens", 0) for a in attempts),
              "output_tokens": sum(a.get("output_tokens", 0) for a in attempts), "attempts": attempts,
              "first_pass_runtime": bool(value.get("deliverable_id")) and all(a["outcome"] == "ok" for a in journal),
              "journal": [{k:a.get(k) for k in ("skill","attempt","outcome","input_tokens","output_tokens")} for a in journal]}
    if value.get("deliverable_id"):
        doc = lab.api.get(base + "/deliverables/" + value["deliverable_id"], headers=admin["headers"])
        doc.raise_for_status()
        draft = doc.json()
        record["deliverable"] = {"id": value["deliverable_id"], "title": draft["title"], "body": draft["content"]["client_preview"],
                                 "qa_revision": draft["qa_revision"], "digest": draft["qa_evidence"]["content_digest"]}
        record["deliverable"].update(status=draft["status"], assessment=draft["qa_evidence"])
        if arm != "legacy":
            from migrations.runtime_bundle import runtime_fingerprint
            knowledge = lab.owner.execute("select knowledge from workforce_runs where id=%s", (rid,)).fetchone()[0]
            record.update(runtime_fingerprint=runtime_fingerprint(), manifest=knowledge["c3_manifest"],
                          binding=knowledge["registry"])
            if arm == "improved":
                from app.c3_assets import artifacts
                nodes = {c["skill"]: c["output"] for c in value["checkpoints"]}
                record["assets"] = artifacts(release, knowledge["c3_projection"], nodes)
        (folder / "deliverable.md").write_text("# " + draft["title"] + "\n\n" + draft["content"]["client_preview"] + "\n", encoding="utf8")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arm", choices=["legacy", "projected"])
    parser.add_argument("out", type=Path)
    parser.add_argument("--case", choices=[c["id"] for c in json.loads(CASES.read_text(encoding="utf8"))["cases"]])
    args = parser.parse_args()
    url = os.environ["AMC_LOCAL_MODEL_URL"].rstrip("/")
    if urlsplit(url).hostname not in ("127.0.0.1", "localhost", "::1") or not url.endswith("/v1"):
        raise ValueError("Set AMC_LOCAL_MODEL_URL to a loopback llama.cpp /v1 endpoint.")
    from app.database import engine
    if engine.url.host not in ("127.0.0.1", "localhost", "::1") or not engine.url.database.startswith("amc_test"):
        raise ValueError("This comparison requires a disposable local amc_test database.")
    with httpx.Client(trust_env=False) as http:
        res = http.get(url[:-3] + "/props")
        res.raise_for_status()
        props = res.json()
    model_path = Path(props["model_path"])
    with Path(os.environ.get("AMC_EVAL_MODEL_FILE", str(model_path))).open("rb") as handle:
        model_digest = hashlib.file_digest(handle, "sha256").hexdigest()
    args.out.mkdir(parents=True, exist_ok=True)
    settings = {"model_sha256": model_digest, "build": props.get("build_info"), "provider": "llama.cpp loopback",
                "case_file_sha256": hashlib.sha256(CASES.read_bytes()).hexdigest(), "seed": 42, "workers_per_case": 1,
                "code": subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT, text=True).strip()}
    run_meta = args.out / (args.arm + "-conditions.json")
    if run_meta.exists() and json.loads(run_meta.read_text()) != settings:
        raise ValueError("Result directory already belongs to different experimental conditions.")
    dump(run_meta, settings)
    for c in json.loads(CASES.read_text(encoding="utf8"))["cases"]:
        if args.case and args.case != c["id"]:
            continue
        with lab_client(app) as api:
            lab = MarketingLab(api, os.environ["AMC_MIGRATION_DSN"], c)
            lab.config = replace(lab.config, model=os.getenv("AMC_WORKFORCE_MODEL", "amc-local"), url=url)
            try:
                for kind in LEGACY:
                    folder = args.out / args.arm / c["id"] / kind
                    folder.mkdir(parents=True, exist_ok=True)
                    if (folder/"result.json").exists():
                        continue
                    record = run_one(lab, kind, args.arm, folder)
                    dump(folder / "result.json", record)
                    print(c["id"], kind, record["state"], record["runtime_s"], flush=True)
            finally:
                lab.close()


if __name__ == "__main__":
    main()


