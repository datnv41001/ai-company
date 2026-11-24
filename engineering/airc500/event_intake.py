"""Read authenticated PR metadata. Only the approved synthetic source can enter a review."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import urllib.request

from pilot_fixture import admission, synthetic_pr
from review_plan import plan_digest

PRODUCT_REPO = "datnv41001/ai-company"
SYNTHETIC_REPO = "fixture/marketing-exhibition"
LIMIT = 256_000
SHA = re.compile("[0-9a-f]{40}")
DELIVERY = re.compile("[A-Za-z0-9-]{1,100}")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def github_head(repo, number):
    """Read only public PR metadata from GitHub. No redirects, proxies, token or source URLs."""
    if repo != PRODUCT_REPO or type(number) is not int or number < 1:
        raise ValueError("unsupported metadata lookup")
    url = f"https://api.github.com/repos/{PRODUCT_REPO}/pulls/{number}"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "AMC-AIRC-intake"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=8) as response:
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError("metadata too large")
    result = json.loads(data)
    if result["number"] != number or result["base"]["repo"]["full_name"] != repo:
        raise ValueError("unrelated metadata")
    return result["state"], result["base"]["sha"], result["head"]["sha"]


def current_head(repo, number):
    if repo == SYNTHETIC_REPO and number == 1:
        manifest, _ = synthetic_pr()
        return "open", manifest["base_sha"], manifest["head_sha"]
    return github_head(repo, number)


class Inbox:
    def __init__(self, file, secret, *, lookup=current_head, clock=time.time):
        if not isinstance(secret, bytes) or len(secret) < 32:
            raise ValueError("a separately provisioned webhook secret is required")
        self.file, self.secret, self.lookup, self.clock = str(file), secret, lookup, clock
        with closing(sqlite3.connect(self.file)) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS deliveries(id TEXT PRIMARY KEY, digest TEXT NOT NULL,result TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tickets(repo TEXT NOT NULL, pr INTEGER NOT NULL,
                   base TEXT NOT NULL, head TEXT NOT NULL, cycle INTEGER NOT NULL, deadline REAL NOT NULL,
                   state TEXT NOT NULL, PRIMARY KEY(repo,pr));
            """)

    def ingest(self, body, signature, delivery, event):
        if not isinstance(body, bytes) or len(body) > LIMIT or not DELIVERY.fullmatch(delivery):
            raise ValueError("invalid delivery")
        correct = "sha256=" + hmac.new(self.secret, body, hashlib.sha256).hexdigest()
        if not isinstance(signature, str) or not hmac.compare_digest(signature, correct):
            raise ValueError("invalid webhook signature")
        obj = json.loads(body)
        if event != "pull_request" or obj.get("action") not in ("opened", "synchronize", "reopened"):
            raise ValueError("unsupported event")
        repo, pr = obj["repository"]["full_name"], obj["number"]
        pull = obj["pull_request"]
        if repo not in (SYNTHETIC_REPO, PRODUCT_REPO) or type(pr) is not int or not 1 <= pr <= 2**31 - 1:
            raise ValueError("outside intake allowlist")
        base, head = pull["base"]["sha"], pull["head"]["sha"]
        if pull["base"]["repo"]["full_name"] != repo or pull["number"] != pr or not all(SHA.fullmatch(s) for s in (base, head)):
            raise ValueError("invalid PR identity")
        body_digest = hashlib.sha256(body).hexdigest()
        with closing(sqlite3.connect(self.file, timeout=15)) as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT digest,result FROM deliveries WHERE id=?", (delivery,)).fetchone()
            if prior:
                if prior[0] != body_digest:
                    raise ValueError("delivery ID conflict")
                # A replay cannot dispatch work; never return an obsolete actionable package.
                return {"decision": "duplicate", "original_state": json.loads(prior[1])["decision"]}
            status, latest_base, latest_head = self.lookup(repo, pr)
            previous = db.execute("SELECT base,head,cycle,deadline,state FROM tickets WHERE repo=? AND pr=?", (repo, pr)).fetchone()
            result = {"repo": repo, "pr": pr, "base_sha": base, "head_sha": head, "paid_microusd": 0}
            now = self.clock()
            if (status, latest_base, latest_head) != ("open", base, head):
                result["decision"] = "stale"
            elif previous and previous[:2] == (base, head) and now >= previous[3]:
                result["decision"] = "human_escalation"
                db.execute("UPDATE tickets SET state='human_escalation' WHERE repo=? AND pr=?", (repo, pr))
            elif previous and previous[:2] == (base, head):
                result["decision"] = "duplicate_revision"
            else:
                cycle = previous[2] + 1 if previous else 1
                deadline = previous[3] if previous else now + 2700
                decision = "metadata_only" if repo != SYNTHETIC_REPO else "fixture_plan_ready"
                if cycle > 2 or now >= deadline:
                    decision = "human_escalation"
                result.update(decision=decision, cycle=cycle, deadline=datetime.fromtimestamp(deadline, timezone.utc).isoformat())
                if previous:
                    result["superseded_head"] = previous[1]
                if decision == "fixture_plan_ready":
                    reviewed, rows = synthetic_pr()
                    if (base, head) != (reviewed["base_sha"], reviewed["head_sha"]):
                        raise ValueError("source differs from independently approved synthetic fixture")
                    plan = admission(rows, "targeted")
                    result.update(changed_files=reviewed["changed_files"], review_plan=plan, plan_digest=plan_digest(plan))
                db.execute("INSERT OR REPLACE INTO tickets VALUES(?,?,?,?,?,?,?)", (repo, pr, base, head, cycle, deadline, decision))
            db.execute("INSERT INTO deliveries VALUES(?,?,?)", (delivery, body_digest, json.dumps(result, sort_keys=True)))
            db.commit()
            return result

    def handoff(self, delivery, directory, archive_pin, trust_pin):
        """Local draft only; publishing and repository writes are outside this process."""
        from pilot_archive import assemble, verify_index

        with closing(sqlite3.connect(self.file)) as db:
            got = db.execute("SELECT result FROM deliveries WHERE id=?", (delivery,)).fetchone()
            if not got:
                raise ValueError("unknown delivery")
            event = json.loads(got[0])
            repo, pr = event["repo"], event["pr"]

            def current():
                record = db.execute("SELECT base,head,deadline,state FROM tickets WHERE repo=? AND pr=?", (repo, pr)).fetchone()
                if (
                    event["decision"] != "fixture_plan_ready"
                    or repo != SYNTHETIC_REPO
                    or not record
                    or record[:2] != (event["base_sha"], event["head_sha"])
                    or record[3] != "fixture_plan_ready"
                    or self.clock() >= record[2]
                    or self.lookup(repo, pr) != ("open", *record[:2])
                ):
                    raise ValueError("no active authorized synthetic review")

            current()
            verify_index(directory, archive_pin)
            assemble(directory, trust_pin)
            results = json.loads((Path(directory) / "results.json").read_bytes())
            if (results["manifest"]["base_sha"], results["manifest"]["head_sha"]) != (event["base_sha"], event["head_sha"]):
                raise ValueError("evidence is for another revision")
            units = results["targeted"]["evaluation"]["candidates"]
            current()
            return {
                "kind": "draft_for_authorized_implementer",
                "repo": repo,
                "pr": pr,
                "base_sha": event["base_sha"],
                "head_sha": event["head_sha"],
                "evidence_archive_sha256": archive_pin,
                "cycle": event["cycle"],
                "release_authority": "human",
                "assignments": [
                    {"id": f["finding_id"], "unit": f["unit"], "acceptance": f["acceptance_criteria"], "evidence": f["evidence"]}
                    for f in units
                    if f["verification_status"] == "verified"
                ],
            }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--db", required=True)
    cli.add_argument("--delivery", required=True)
    sub = cli.add_subparsers(dest="action", required=True)
    event = sub.add_parser("receive")
    event.add_argument("--body", required=True)
    event.add_argument("--signature", required=True)
    draft = sub.add_parser("handoff")
    draft.add_argument("--directory", required=True)
    draft.add_argument("--archive-sha256", required=True)
    draft.add_argument("--trust-sha256", required=True)
    args = cli.parse_args()
    box = Inbox(args.db, os.environ["AIRC_WEBHOOK_SECRET"].encode())
    if args.action == "receive":
        with Path(args.body).open("rb") as source:
            result = box.ingest(source.read(LIMIT + 1), args.signature, args.delivery, "pull_request")
    else:
        result = box.handoff(args.delivery, args.directory, args.archive_sha256, args.trust_sha256)
    print(json.dumps(result, indent=2))
