"""Rebuild a synthetic two-commit PR and broker read-only, line-addressed excerpts."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
FACTS = "brand/approved-facts.jsonl"
COPY = "campaign/published-copy.jsonl"
MODEL_DIGEST = "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"
MODEL = "Qwen2.5-0.5B-Instruct-Q4_K_M"
MODEL_VERSION = "9217f5db79a29953eb74d5343926648285ec7e67"
FAMILY = "Qwen2.5"
POLICY = {"offer": ["MK-051", "MK-052", "MK-054", "MK-055"], "editorial": ["MK-021", "MK-022", "MK-023", "MK-025"]}
# Frozen counterevidence exercise. These are authored fixture statements, never reviewer invocations.
DISPUTE = [
    {"id": "briefing-A", "status": "matches", "message": "The offer was approved at an earlier planning meeting."},
    {"id": "briefing-B", "status": "matches", "message": "An unsigned sales summary lists the copy as approved."},
    {"id": "fact-editor", "status": "conflict", "message": "Compare the two committed values on line 1.", "source_path": FACTS, "copy_path": COPY, "line": 1},
]


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_catalog():
    return {r["reviewer_id"]: r for r in map(json.loads, (ROOT / "reviewers.jsonl").read_bytes().splitlines())}


def git(repo, *args):
    clean = {k: os.environ[k] for k in ("SystemRoot", "PATH", "TMP", "TEMP", "TMPDIR") if k in os.environ}
    clean.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_TERMINAL_PROMPT="0",
        GIT_AUTHOR_NAME="Synthetic fixture",
        GIT_COMMITTER_NAME="Synthetic fixture",
        GIT_AUTHOR_EMAIL="fixture@example.invalid",
        GIT_COMMITTER_EMAIL="fixture@example.invalid",
        GIT_AUTHOR_DATE="2025-01-01T00:00:00Z",
        GIT_COMMITTER_DATE="2025-01-01T00:00:00Z",
    )
    return subprocess.check_output(
        ["git", "-c", "core.autocrlf=false", "-c", "core.hooksPath=" + os.devnull, "-C", str(repo), *args], env=clean, stderr=subprocess.PIPE
    )


def synthetic_pr():
    template = json.loads((ROOT / "fixtures" / "marketing-pr.json").read_bytes())
    with tempfile.TemporaryDirectory(prefix="airc-fixture-") as tmp:
        repo = Path(tmp)
        git(repo, "init", "--quiet", "--object-format=sha1")
        for name in (FACTS, COPY):
            (repo / name).parent.mkdir()
        for revision in ("base", "head"):
            for name, key in ((FACTS, "approved"), (COPY, revision)):
                lines = [encoded({"unit": u["id"], "domain": u["domain"], "field": u["field"], "value": u[key]}) for u in template]
                (repo / name).write_bytes(b"\n".join(lines) + b"\n")
            git(repo, "add", "--", FACTS, COPY)
            git(repo, "commit", "--quiet", "-m", revision)
            if revision == "base":
                base = git(repo, "rev-parse", "HEAD").decode().strip()
        head = git(repo, "rev-parse", "HEAD").decode().strip()
        manifest, rows = import_pr(repo, base, head)
    return manifest, rows


def import_pr(repo, base, head):
    # This pilot accepts only the fixture file allowlist. It never executes PR code.
    if (base, head) != ("6f23449c5a3467ddcb5e8e773c40768837d5bbc5", "a381db60e8b539b3cdd06c0bee343b3348f204c4"):
        raise ValueError("Only the enrolled synthetic Git pair may be read")
    if git(repo, "rev-parse", head + "^").decode().strip() != base:
        raise ValueError("head must have the submitted base parent")
    changed = git(repo, "diff", "--name-only", "-z", base, head).decode().strip("\0").split("\0")
    if not changed or set(changed) - {FACTS, COPY}:
        raise ValueError("outside pilot allowlist")
    blobs = {}
    data = {}
    for rev in (base, head):
        for path in (FACTS, COPY):
            mode, obj_type, oid = git(repo, "ls-tree", rev, "--", path).split(b"\t")[0].decode().split()
            if (mode, obj_type) != ("100644", "blob") or int(git(repo, "cat-file", "-s", oid)) > 32_768:
                raise ValueError("unexpected blob kind/size")
            raw = git(repo, "cat-file", "blob", oid)
            blobs[rev + ":" + path] = {"git_oid": oid, "sha256": digest(raw)}
            data[rev, path] = [json.loads(line) for line in raw.splitlines()]
    rows = []
    for n, (fact, copy, old_fact, old_copy) in enumerate(zip(data[head, FACTS], data[head, COPY], data[base, FACTS], data[base, COPY], strict=True), 1):
        identity = tuple(fact[k] for k in ("unit", "domain", "field"))
        if any(tuple(obj[k] for k in ("unit", "domain", "field")) != identity for obj in (copy, old_fact, old_copy)):
            raise ValueError("fixture unit identity drift")
        rows.append(
            {
                **dict(zip(("id", "domain", "field"), identity)),
                "source": fact["value"],
                "observed": copy["value"],
                "line": n,
                "changed": fact != old_fact or copy != old_copy,
            }
        )
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("duplicate unit")
    return {"repository": "fixture/marketing-exhibition", "pr_number": 1, "base_sha": base, "head_sha": head, "changed_files": changed, "blobs": blobs}, rows


def plan(rows, baseline=False):
    # Include clean controls from the same affected domain as dependency coverage.
    affected = sorted({r["domain"] for r in rows if r["changed"]})
    if not affected or set(affected) - set(POLICY):
        raise ValueError("no supported risk route")
    jobs = []
    for domain in affected:
        scope = [r for r in rows if r["domain"] == domain]
        for reviewer in POLICY[domain]:
            jobs.append(("MK-022" if baseline else reviewer, domain, scope))
    return jobs


def evidence_rows(rows):
    return [
        {"unit": r["id"], "field": r["field"], "approved_line": r["line"], "approved_value": r["source"], "copy_line": r["line"], "copy_value": r["observed"]}
        for r in rows
    ]


def admission(rows, mode):
    jobs = [(who, "blind", [r["id"] for r in scope]) for who, _, scope in plan(rows, mode == "baseline")]
    if mode == "targeted":
        jobs += [("MK-052", "cross", ["cross-editorial"]), ("MK-022", "cross", ["cross-offer"]), ("AR-002", "arbitration", ["arbitration"])]
    profiles = read_catalog()
    assignments = [
        {
            "assignment_id": f"{mode}-{i:02d}",
            "reviewer_id": who,
            "phase": phase,
            "artifact_kind": profiles[who]["output"]["artifact_kind"],
            "obligations": scope,
        }
        for i, (who, phase, scope) in enumerate(jobs, 1)
    ]
    return {"version": 1, "assignments": assignments, "required_obligations": sorted({o for j in assignments for o in j["obligations"]})}
