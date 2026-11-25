"""Durable local generation, outbox and acknowledgement protocol for approved fixtures."""

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3

from pilot_fixture import admission, digest, encoded, synthetic_pr
from review_plan import plan_digest

V3_REPO = "fixture/meridian-offers"
V1_INDEX = "dacc572f1d25c18c491c0c6364111603a2038dab13e8d89df0d6997f147a6167"
V1_TRUST = "400f86483df5c4521ace9c26c5f83975f2e45415d56c8af1a6e684e259948ca9"


def frozen_package(repo):
    from event_intake import SYNTHETIC_REPO

    if repo == SYNTHETIC_REPO:
        m, rows = synthetic_pr()
        p = admission(rows, "targeted")
        return m["base_sha"], m["head_sha"], p, V1_INDEX, V1_TRUST
    if repo == V3_REPO:
        from union_release import ENROLLMENT, INDEX
        from union_cases import holdout, manifest
        from union_study import ROOT, open_enrollment

        r, _ = holdout()
        m = manifest(r)
        _, _, _, _, p = open_enrollment(ROOT / "evidence/union-v3", ENROLLMENT, "q05")
        return m["base"], m["head"], p, INDEX, ENROLLMENT
    return None


def replay_package(repo, path, index, trust):
    from event_intake import SYNTHETIC_REPO

    if repo == SYNTHETIC_REPO:
        from pilot_archive import verify_index, assemble

        verify_index(path, index)
        assemble(path, trust)
        ev = json.loads((Path(path) / "results.json").read_bytes())["targeted"]["evaluation"]
        # The historical accepted archive had no actionable verified repairs.
        assignments = [
            dict(id=f["finding_id"], unit=f["unit"], evidence=f["evidence"], acceptance=f["acceptance_criteria"])
            for f in ev["candidates"]
            if f["verification_status"] == "verified" and f["actionable"] and f["evidence_valid"]
        ]
        exported = {a["unit"] for a in assignments}
        return assignments, sorted(set(ev["missed"]) | {f["unit"] for f in ev["candidates"] if f["unit"] not in exported})
    if repo != V3_REPO:
        raise ValueError("no authorized source")
    from union_release import verify_release

    study = verify_release(Path(path), index, trust)
    # Enrollment chooses this seed and arm before intake. No selection by observed score.
    d = study["q05"]["seeds"]["19"]["arms"]["full_union"]["decisions"]
    tasks = [
        dict(
            id="F-" + uid,
            unit=uid,
            evidence={"path": "sources.jsonl", "unit": uid, "subject": r["subject"], "record": r["source"]},
            provider=r["provider"],
            expected=r["expected"],
            actual=r["observation"],
            operation=r["operation"],
            acceptance="Scoped draft matches approved source at " + r["source"],
        )
        for uid, r in d.items()
        if r["state"] == "verified_defect" and r["actionable"]
    ]
    return tasks, sorted(uid for uid, r in d.items() if r["state"] == "unresolved" or (r["state"] == "verified_defect" and not r["actionable"]))


class GenerationInbox:
    def initialize(self):
        with closing(sqlite3.connect(self.file)) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS deliveries(id TEXT PRIMARY KEY,digest TEXT NOT NULL,result TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tickets(repo TEXT NOT NULL,pr INTEGER NOT NULL,base TEXT NOT NULL,head TEXT NOT NULL,
                    cycle INTEGER NOT NULL,deadline REAL NOT NULL,state TEXT NOT NULL,PRIMARY KEY(repo,pr));
                CREATE TABLE IF NOT EXISTS draft_outbox(key TEXT PRIMARY KEY,repo TEXT NOT NULL,pr INTEGER NOT NULL,generation INTEGER NOT NULL,
                    payload TEXT NOT NULL,state TEXT NOT NULL,UNIQUE(repo,pr,generation));
            """)
            db.execute("BEGIN IMMEDIATE")
            cols = {r[1] for r in db.execute("PRAGMA table_info(tickets)")}
            for col, kind in (("generation", "INTEGER NOT NULL DEFAULT 0"), ("base_ref", "TEXT"), ("lifecycle", "TEXT"), ("transition_digest", "TEXT")):
                if col not in cols:
                    db.execute(f"ALTER TABLE tickets ADD COLUMN {col} {kind}")
            db.commit()

    def ingest(self, body, signature, delivery, event):
        from event_intake import DELIVERY, LIMIT, PRODUCT_REPO, SYNTHETIC_REPO, SHA

        if not isinstance(body, bytes) or len(body) > LIMIT or not DELIVERY.fullmatch(delivery):
            raise ValueError("invalid delivery")
        correct = "sha256=" + hmac.new(self.secret, body, hashlib.sha256).hexdigest()
        if not isinstance(signature, str) or not hmac.compare_digest(signature, correct):
            raise ValueError("invalid signature")
        obj = json.loads(body)
        action = obj.get("action")
        pull = obj["pull_request"]
        repo = obj["repository"]["full_name"]
        pr = obj["number"]
        if event != "pull_request" or action not in ("opened", "closed", "synchronize", "edited", "reopened"):
            raise ValueError("unsupported event")
        if action == "edited" and "base" not in obj.get("changes", {}):
            raise ValueError("only retarget edits are accepted")
        if (
            repo not in (V3_REPO, SYNTHETIC_REPO, PRODUCT_REPO)
            or type(pr) is not int
            or not 1 <= pr <= 2**31 - 1
            or pull["number"] != pr
            or pull["base"]["repo"]["full_name"] != repo
        ):
            raise ValueError("invalid identity")
        base, head, ref = pull["base"]["sha"], pull["head"]["sha"], pull["base"].get("ref", "main")
        if not all(SHA.fullmatch(s) for s in (base, head)) or not isinstance(ref, str) or not 0 < len(ref) <= 255:
            raise ValueError("invalid revision")
        state = "closed" if action == "closed" else "open"
        with closing(sqlite3.connect(self.file, timeout=15)) as db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE")
            same = db.execute("SELECT * FROM deliveries WHERE id=?", (delivery,)).fetchone()
            if same:
                if same["digest"] != digest(body):
                    raise ValueError("delivery conflict")
                return dict(decision="duplicate", original_state=json.loads(same["result"])["decision"])
            current = self.lookup(repo, pr)
            before = db.execute("SELECT * FROM tickets WHERE repo=? AND pr=?", (repo, pr)).fetchone()
            out = dict(repo=repo, pr=pr, base_sha=base, head_sha=head, base_ref=ref, paid_microusd=0)
            now = self.clock()
            same_revision = before and tuple(before[x] for x in ("base", "head", "base_ref", "lifecycle")) == (base, head, ref, state)
            # A signed lifecycle edge can prove an intervening transition even if its
            # earlier delivery was missed. Identical redeliveries keep their generation.
            edge = action in ("reopened", "edited") or (action == "synchronize" and obj.get("before") not in (None, head))
            new_edge = edge and before is not None and before["transition_digest"] != digest(body)
            if (
                tuple(current[:3]) != (state, base, head)
                or (len(current) >= 4 and current[3] != ref)
                or (len(current) >= 5 and pull.get("updated_at") != current[4])
            ):
                out["decision"] = "stale"
            elif same_revision and now >= before["deadline"] and state == "open":
                out["decision"] = "human_escalation"
                db.execute("UPDATE tickets SET state='human_escalation' WHERE repo=? AND pr=?", (repo, pr))
                db.execute("UPDATE draft_outbox SET state='superseded' WHERE repo=? AND pr=? AND state='pending'", (repo, pr))
            elif same_revision and not new_edge:
                out["decision"] = "duplicate_revision"
            else:
                gen = before["generation"] + 1 if before else 1
                cycle = (before["cycle"] if before else 0) + int(state == "open")
                deadline = before["deadline"] if before else now + 2700
                decision = "closed" if state == "closed" else "human_escalation" if cycle > 2 or now >= deadline else "metadata_only"
                if decision == "metadata_only" and repo != PRODUCT_REPO:
                    approved_base, approved_head, p, index, trust = frozen_package(repo)
                    if (base, head) == (approved_base, approved_head) and ref == "main":
                        decision = "fixture_plan_ready"
                        out.update(review_plan=p, plan_digest=plan_digest(p), package_index=index, trust_pin=trust)
                if len(current) >= 5:
                    out["metadata_version"] = current[4]
                if before:
                    out["superseded_head"] = before["head"]
                out.update(decision=decision, generation=gen, cycle=cycle, deadline=datetime.fromtimestamp(deadline, timezone.utc).isoformat())
                db.execute("UPDATE draft_outbox SET state='superseded' WHERE repo=? AND pr=? AND state='pending'", (repo, pr))
                db.execute(
                    "INSERT OR REPLACE INTO tickets(repo,pr,base,head,cycle,deadline,state,generation,base_ref,lifecycle,transition_digest) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (repo, pr, base, head, cycle, deadline, decision, gen, ref, state, digest(body)),
                )
            db.execute("INSERT INTO deliveries VALUES(?,?,?)", (delivery, digest(body), encoded(out).decode()))
            db.commit()
            return out

    def current(self, db, delivery):
        result = db.execute("SELECT result FROM deliveries WHERE id=?", (delivery,)).fetchone()
        if not result:
            raise ValueError("unknown delivery")
        event = json.loads(result[0])
        if event.get("decision") != "fixture_plan_ready" or not event.get("generation"):
            raise ValueError("no active admitted generation")
        repo, pr = event["repo"], event["pr"]
        t = db.execute("SELECT generation,base,head,base_ref,deadline,state FROM tickets WHERE repo=? AND pr=?", (repo, pr)).fetchone()
        if (
            not t
            or t[:4] != (event["generation"], event["base_sha"], event["head_sha"], event["base_ref"])
            or self.clock() >= t[4]
            or t[5] != "fixture_plan_ready"
        ):
            raise ValueError("stale generation or deadline")
        latest = self.lookup(repo, pr)
        if (
            tuple(latest[:3]) != ("open", t[1], t[2])
            or (len(latest) >= 4 and latest[3] != t[3])
            or (len(latest) >= 5 and latest[4] != event.get("metadata_version"))
        ):
            raise ValueError("PR no longer current")
        return event

    def handoff(self, delivery, directory, archive_pin, trust_pin):
        with closing(sqlite3.connect(self.file, timeout=15)) as db:
            event = self.current(db, delivery)
            if (archive_pin, trust_pin) != (event["package_index"], event["trust_pin"]):
                raise ValueError("package not enrolled for generation")
            tasks, gaps = replay_package(event["repo"], directory, archive_pin, trust_pin)
            db.execute("BEGIN IMMEDIATE")
            event = self.current(db, delivery)
            payload = {k: event[k] for k in ("repo", "pr", "generation", "cycle", "base_sha", "head_sha", "base_ref", "plan_digest")}
            payload.update(
                kind="draft_for_authorized_implementer", evidence_archive_sha256=archive_pin, release_authority="human", assignments=tasks, unresolved=gaps
            )
            key = digest(encoded(payload))
            payload["outbox_key"] = key
            db.execute(
                "INSERT OR IGNORE INTO draft_outbox VALUES(?,?,?,?,?,'pending')",
                (key, event["repo"], event["pr"], event["generation"], encoded(payload).decode()),
            )
            row = db.execute("SELECT payload,state FROM draft_outbox WHERE key=?", (key,)).fetchone()
            if not row or row[1] == "superseded":
                raise ValueError("immutable outbox conflict")
            db.commit()
            return dict(**json.loads(row[0]), outbox_state=row[1])

    def acknowledge(self, delivery, key):
        with closing(sqlite3.connect(self.file, timeout=15)) as db:
            db.execute("BEGIN IMMEDIATE")
            event = self.current(db, delivery)
            row = db.execute(
                "SELECT state FROM draft_outbox WHERE key=? AND repo=? AND pr=? AND generation=?", (key, event["repo"], event["pr"], event["generation"])
            ).fetchone()
            if not row or row[0] not in ("pending", "acknowledged"):
                raise ValueError("unknown or superseded acknowledgement")
            db.execute("UPDATE draft_outbox SET state='acknowledged' WHERE key=?", (key,))
            db.commit()
            return {"outbox_key": key, "state": "acknowledged", "generation": event["generation"]}
