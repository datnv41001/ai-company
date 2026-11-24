"""Durable, single-host coordinator for the zero-API-cost AIRC pilot.

Each command obtains a SQLite write transaction, replays the small run and appends
its decision before returning. No SDK retries or warm in-memory authority.
"""

import base64
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import sqlite3
import uuid

import rfc8785

from receipt_auth import BINDINGS, Signer, digest, instant, validate, verify_signature
import review_plan

__all__ = ["Journal", "Signer", "verify_signature"]


def stamp(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class State:
    manifest: dict = field(default_factory=dict)
    trust: dict = field(default_factory=dict)
    attempts: dict = field(default_factory=dict)
    rejected: int = 0
    epoch: int = 1
    cancelled: bool = False
    overspent: bool = False
    seal: str | None = None
    sequence: int = 0
    previous: str | None = None
    root: str | None = None
    plan: dict | None = None
    verifier_key: str | None = None
    observations: dict = field(default_factory=dict)

    def apply(self, kind, data):
        if kind == "start":
            self.manifest, self.trust = data["run"], data["trust"]
            self.plan, self.verifier_key = data.get("plan"), data.get("verifier_key")
        elif kind == "evidence":
            self.observations[data["assignment_id"], data["obligation_id"]] = data
        elif kind == "reserved":
            self.attempts[data["attempt_id"]] = {**data, "state": "reserved"}
        elif kind == "dispatched":
            self.attempts[data["attempt_id"]].update(state="dispatched", started_utc=data["started_utc"])
        elif kind == "fenced":
            self.attempts[data["attempt_id"]]["state"] = data["state"]
        elif kind == "cancel":
            self.cancelled = True
            self.epoch += 1
        elif kind == "receipt":
            attempt = self.attempts[data["attempt_id"]]
            attempt.update(state=data["state"], receipt=data["receipt"], output=data["output"])
            self.overspent |= data["overspent"]
        elif kind == "rejected":
            self.rejected += 1
        elif kind == "seal":
            self.seal = data["seal"]
        else:
            raise ValueError("unrecognized journal event")

    def ledger(self):
        totals = {"input_tokens": 0, "output_tokens": 0, "settled_microusd": 0, "held_tokens": 0, "held_microusd": 0, "uncertain_attempts": 0}
        for a in self.attempts.values():
            if a["state"] in ("reserved", "dispatched", "uncertain"):
                totals["held_tokens"] += a["assignment"]["token_reservation"]
                totals["held_microusd"] += a["assignment"]["cost_reservation_microusd"]
                totals["uncertain_attempts"] += a["state"] == "uncertain"
            elif a["state"] in ("accepted", "settled"):
                receipt = a["receipt"]
                for key in ("input_tokens", "output_tokens"):
                    totals[key] += receipt[key]
                totals["settled_microusd"] += receipt["cost_microusd"]
        return totals


class Journal:
    def __init__(self, path, *, clock=None):
        self.path = str(path)
        self.clock = clock or (lambda: datetime.now(timezone.utc).timestamp())
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS events(
                run TEXT NOT NULL, seq INTEGER NOT NULL, kind TEXT NOT NULL,
                body BLOB NOT NULL, parent TEXT, hash TEXT NOT NULL,
                PRIMARY KEY(run,seq))""")
            db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS unique_attempt ON events(
                json_extract(CAST(body AS TEXT),'$.attempt_id')) WHERE kind='reserved'""")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            db.execute("PRAGMA synchronous=FULL")
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    @staticmethod
    def event_hash(run_id, seq, kind, data, parent):
        return digest(rfc8785.dumps([run_id, seq, kind, data, parent]))

    def load(self, db, run_id, through=None):
        state = State()
        for seq, kind, body, parent, event_hash in db.execute(
            "SELECT seq,kind,body,parent,hash FROM events WHERE run=? AND (? IS NULL OR seq<=?) ORDER BY seq", (run_id, through, through)
        ):
            data = json.loads(body)
            if parent != state.root or seq != state.sequence + 1 or self.event_hash(run_id, seq, kind, data, parent) != event_hash:
                raise ValueError("journal integrity failure")
            state.apply(kind, data)
            state.sequence, state.previous, state.root = seq, parent, event_hash
        if not state.manifest:
            raise ValueError("unknown run")
        return state

    def append(self, db, state, run_id, kind, data):
        seq = state.sequence + 1
        event_hash = self.event_hash(run_id, seq, kind, data, state.root)
        db.execute("INSERT INTO events VALUES(?,?,?,?,?,?)", (run_id, seq, kind, rfc8785.dumps(data), state.root, event_hash))
        state.apply(kind, data)
        state.sequence, state.previous, state.root = seq, state.root, event_hash

    def start_planned(self, run_record, trust, plan, verifier_key):
        review_plan.validate_plan(run_record, plan, verifier_key, trust)
        self._start(run_record, trust, {"plan": plan, "verifier_key": verifier_key})

    def start(self, run_record, trust):
        raise ValueError("A frozen plan and separate evidence verifier are required at admission")

    def _start(self, run_record, trust, planning):
        validate("run", run_record)
        budget = run_record["budget"]
        if budget["max_cost_microusd"] or budget["max_concurrency"] > 2:
            raise ValueError("pilot admits local zero-API-cost runs with at most two slots")
        if not trust:
            raise ValueError("operator trust required")
        for kid, adapter in trust.items():
            if not all(adapter.get(f) for f in BINDINGS) or kid != digest(base64.b64decode(adapter["public_key"], validate=True)):
                raise ValueError("invalid operator trust pin")
        rid = run_record["run_id"]
        with self.transaction() as db:
            if db.execute("SELECT 1 FROM events WHERE run=?", (rid,)).fetchone():
                current = self.load(db, rid)
                if (
                    current.manifest != run_record
                    or current.trust != trust
                    or current.plan != planning.get("plan")
                    or current.verifier_key != planning.get("verifier_key")
                ):
                    raise ValueError("cannot change pinned manifest or trust")
                return
            self.append(db, State(), rid, "start", {"run": run_record, "trust": trust, **planning})

    @staticmethod
    def runnable(state, now):
        if state.cancelled or state.overspent or now >= instant(state.manifest["budget"]["deadline_utc"]):
            raise ValueError("run fenced, over budget or deadline reached")

    @staticmethod
    def _admit(state, ass, key_id):
        validate("assignment", ass)
        if state.plan:
            review_plan.planned_job(state.plan, ass)
        budget = state.manifest["budget"]
        if (
            key_id not in state.trust
            or any(state.manifest[k] != ass[k] for k in ("run_id", "base_sha", "head_sha"))
            or ass["principal"] in state.manifest["implementer_principals"]
        ):
            raise ValueError("assignment identity, revision or trust mismatch")
        if (ass["phase"] == "blind") != (state.seal is None):
            raise ValueError("blind barrier phase mismatch")
        if ass["phase"] == "cross" and not 1 <= ass["round"] <= budget["max_debate_rounds"]:
            raise ValueError("debate limit")
        previous = [a for a in state.attempts.values() if a["assignment"]["assignment_id"] == ass["assignment_id"]]
        if previous and (
            previous[-1]["assignment"] != ass or previous[-1]["state"] not in ("released", "settled") or len(previous) >= budget["max_retries"] + 1
        ):
            raise ValueError("assignment already active, complete, uncertain or retry limit reached")

        ledger = state.ledger()
        if (
            ledger["input_tokens"] + ledger["output_tokens"] + ledger["held_tokens"] + ass["token_reservation"] > budget["max_tokens"]
            or ass["cost_reservation_microusd"]
        ):
            raise ValueError("budget limit")

    def reserve(self, assignment_record, key_id):
        validate("assignment", assignment_record)
        ass = assignment_record
        rid = ass["run_id"]
        with self.transaction() as db:
            state = self.load(db, rid)
            if not state.plan:
                raise ValueError("historical unplanned run is read-only")
            now = self.clock()
            self.runnable(state, now)
            budget = state.manifest["budget"]
            self._admit(state, ass, key_id)

            # Include other runs using this journal in the host-wide slot cap.
            def active(s):
                return sum(a["state"] in ("reserved", "dispatched") for a in s.attempts.values())

            other = [self.load(db, r) for (r,) in db.execute("SELECT run FROM events WHERE kind='start' AND run<>?", (rid,))]
            if active(state) >= budget["max_concurrency"] or active(state) + sum(map(active, other)) >= 2:
                raise ValueError("worker slot limit")
            expiry = min(now + budget["attempt_timeout_seconds"], instant(budget["deadline_utc"]))
            lease = {
                "assignment": ass,
                "attempt_id": str(uuid.uuid4()),
                "key_id": key_id,
                "lease_epoch": state.sequence + 1,
                "run_epoch": state.epoch,
                "expires_utc": stamp(expiry),
            }
            self.append(db, state, rid, "reserved", lease)
            return lease

    def find(self, db, attempt_id):
        row = db.execute(
            """SELECT run FROM events WHERE kind='reserved'
                            AND json_extract(CAST(body AS TEXT),'$.attempt_id')=?""",
            (attempt_id,),
        ).fetchone()
        if not row:
            raise ValueError("unknown attempt")
        state = self.load(db, row[0])
        return row[0], state, state.attempts[attempt_id]

    def dispatch(self, attempt_id):
        with self.transaction() as db:
            rid, state, a = self.find(db, attempt_id)
            if not state.plan:
                raise ValueError("historical unplanned run is read-only")
            now = self.clock()
            self.runnable(state, now)
            if a["state"] != "reserved" or now >= instant(a["expires_utc"]):
                raise ValueError("lease spent or expired")
            self.append(db, state, rid, "dispatched", {"attempt_id": attempt_id, "started_utc": stamp(now)})

    @staticmethod
    def template(state, a):
        if "started_utc" not in a:
            raise ValueError("no durable dispatch")
        record = {k: a["assignment"][k] for k in ("run_id", "assignment_id", "reviewer_id", "phase", "round", "base_sha", "head_sha", "context_digest")}
        record.update({k: state.trust[a["key_id"]][k] for k in BINDINGS})
        return {**record, "type": "receipt.v1", "attempt_id": a["attempt_id"], "started_utc": a["started_utc"], "lease_epoch": a["lease_epoch"]}

    def receipt_template(self, attempt_id):
        with self.connection() as db:
            _, state, a = self.find(db, attempt_id)
            return self.template(state, a)

    def ingest(self, signed, raw_output_bytes):
        with self.transaction() as db:
            rid, state, a = self.find(db, signed.get("attempt_id"))
            try:
                decision = self._ingest(db, rid, state, a, signed, raw_output_bytes)
            except ValueError as exc:
                self.append(db, state, rid, "rejected", {"attempt_id": a["attempt_id"], "reason": str(exc), "at": stamp(self.clock())})
                reason = str(exc)
            else:
                return decision
        raise ValueError(reason)

    @classmethod
    def _receipt_is_new(cls, state, a, receipt, raw):
        verify_signature(receipt, state.trust)
        if receipt["signature"]["key_id"] != a["key_id"] or any(receipt[k] != v for k, v in cls.template(state, a).items()):
            raise ValueError("receipt and lease bindings differ")
        if raw is not None and not isinstance(raw, bytes):
            raise ValueError("output must be raw bytes")
        observed = digest(raw) if raw is not None else None
        if receipt["output_digest"] != observed:
            raise ValueError("raw output digest mismatch")
        past = a.get("receipt")
        if past == receipt:
            return False
        if past and (
            past["usage_known"]
            or not receipt["usage_known"]
            or past["provider_request_or_local_execution_id"] != receipt["provider_request_or_local_execution_id"]
        ):
            raise ValueError("conflicting receipt")
        if any(
            item.get("receipt", {}).get("provider_request_or_local_execution_id") == receipt["provider_request_or_local_execution_id"]
            and item["attempt_id"] != a["attempt_id"]
            and item["key_id"] == a["key_id"]
            for item in state.attempts.values()
        ):
            raise ValueError("execution ID previously attributed")
        if a["state"] not in ("dispatched", "uncertain"):
            raise ValueError("receipt for inactive attempt")
        return True

    def _ingest(self, db, rid, state, a, receipt, raw):
        if not self._receipt_is_new(state, a, receipt, raw):
            return "duplicate"
        now = self.clock()
        if instant(receipt["ended_utc"]) > now:
            raise ValueError("execution completion is in the future")
        known = receipt["usage_known"]
        over = known and (
            receipt["cost_microusd"] > a["assignment"]["cost_reservation_microusd"]
            or receipt["input_tokens"] + receipt["output_tokens"] > a["assignment"]["token_reservation"]
        )
        active = (
            not state.cancelled
            and not state.overspent
            and not over
            and a["state"] == "dispatched"
            and a["run_epoch"] == state.epoch
            and now < instant(a["expires_utc"])
            and (a["assignment"]["phase"] != "blind" or state.seal is None)
        )
        accepted = active and receipt["outcome"] == "completed" and known
        new_state = "accepted" if accepted else ("settled" if known else "uncertain")
        self.append(
            db,
            state,
            rid,
            "receipt",
            {
                "attempt_id": a["attempt_id"],
                "receipt": receipt,
                "state": new_state,
                "overspent": over,
                "output": base64.b64encode(raw).decode("ascii") if raw is not None else None,
            },
        )
        return "accepted" if accepted else "ledger_only"

    def _fence(self, db, rid, state, a):
        if a["state"] in ("reserved", "dispatched"):
            self.append(db, state, rid, "fenced", {"attempt_id": a["attempt_id"], "state": "released" if a["state"] == "reserved" else "uncertain"})

    def timeout(self, attempt_id):
        with self.transaction() as db:
            rid, state, a = self.find(db, attempt_id)
            self._fence(db, rid, state, a)

    def recover(self, run_id, checkpoint=None):
        """Call only after the operator has stopped the prior coordinator."""
        with self.transaction() as db:
            if checkpoint is not None:
                validate("checkpoint", checkpoint)
                prefix = self.load(db, run_id, checkpoint["sequence"])
                if checkpoint != self._checkpoint(prefix):
                    raise ValueError("checkpoint differs from the durable journal prefix")
            state = self.load(db, run_id)
            for a in state.attempts.values():
                self._fence(db, run_id, state, a)

    def cancel(self, run_id):
        with self.transaction() as db:
            state = self.load(db, run_id)
            if not state.cancelled:
                self.append(db, state, run_id, "cancel", {})
                for a in state.attempts.values():
                    self._fence(db, run_id, state, a)

    def seal(self, run_id):
        with self.transaction() as db:
            state = self.load(db, run_id)
            if state.seal:
                return state.seal
            self.runnable(state, self.clock())
            blind = [a for a in state.attempts.values() if a["assignment"]["phase"] == "blind"]
            if not blind or any(a["state"] in ("reserved", "dispatched") for a in blind):
                raise ValueError("blind barrier open")
            sealed = [[a["attempt_id"], a["state"], a.get("receipt", {}).get("output_digest")] for a in blind]
            root = digest(rfc8785.dumps(sealed))
            self.append(db, state, run_id, "seal", {"seal": root, "attempts": sealed})
            return root

    def checkpoint(self, run_id):
        with self.connection() as db:
            return self._checkpoint(self.load(db, run_id))

    @staticmethod
    def _checkpoint(state):
        open_ = [a for a in state.attempts.values() if a["state"] in ("reserved", "dispatched", "uncertain")]
        holds = [
            {k: a[k] for k in ("attempt_id", "state", "lease_epoch", "expires_utc")}
            | {k: a["assignment"][k] for k in ("token_reservation", "cost_reservation_microusd")}
            for a in open_
        ]
        result = {
            "type": "checkpoint.v1",
            **{k: state.manifest[k] for k in ("run_id", "base_sha", "head_sha")},
            "sequence": state.sequence,
            "previous_digest": state.previous,
            "event_root": state.root,
            "reservation_root": digest(rfc8785.dumps(holds)),
            "open_reservations": holds,
            "run_epoch": state.epoch,
            "deadline_utc": state.manifest["budget"]["deadline_utc"],
            "blind_seal_digest": state.seal,
            "cancelled": state.cancelled,
        }
        validate("checkpoint", result)
        return result

    def summary(self, run_id):
        with self.connection() as db:
            state = self.load(db, run_id)
            return self._summary(state)

    @staticmethod
    def _summary(state):
        items = list(state.attempts.values())
        dispatched = [a for a in items if "started_utc" in a]
        accepted = [a for a in items if a["state"] == "accepted"]
        return {
            "run_id": state.manifest["run_id"],
            "assignments": len({a["assignment"]["assignment_id"] for a in items}),
            "attempts": len(items),
            "dispatches": len(dispatched),
            "accepted_receipts": len(accepted),
            "rejected_receipts": state.rejected,
            "accepted_reviewer_ids": sorted({a["assignment"]["reviewer_id"] for a in accepted}),
            "families": sorted({a["receipt"]["family"] for a in accepted}),
            "cancelled": state.cancelled,
            "over_budget": state.overspent,
            "blind_seal_digest": state.seal,
            **state.ledger(),
        }

    def record_evidence(self, observation):
        rid = observation["run_id"]
        with self.transaction() as db:
            state = self.load(db, rid)
            if not state.plan:
                raise ValueError("no admitted evidence plan")
            review_plan.verify_evidence(state, observation)
            self.append(db, state, rid, "evidence", observation)

    def coverage_report(self, run_id):
        with self.connection() as db:
            return review_plan.coverage_report(self.load(db, run_id))

    def coverage(self, run_id, required_assignment_ids=None):
        """Compatibility view. A caller cannot grant coverage by supplying a subset."""
        with self.connection() as db:
            state = self.load(db, run_id)
            if not state.plan or (
                required_assignment_ids is not None and set(required_assignment_ids) != {j["assignment_id"] for j in state.plan["assignments"]}
            ):
                return "inconclusive"
            return "complete" if review_plan.coverage_report(state)["decision"] == "covered" else "inconclusive"

    def export_events(self, run_id):
        with self.transaction() as db:
            self.load(db, run_id)
            return [
                {"run_id": run_id, "sequence": seq, "kind": kind, "data": json.loads(body), "parent": parent, "digest": h}
                for seq, kind, body, parent, h in db.execute("SELECT seq,kind,body,parent,hash FROM events WHERE run=? ORDER BY seq", (run_id,))
            ]

    @classmethod
    def verify_events(cls, run_id, events, checkpoint, trust, *, expected_plan_digest=None, verifier_key=None):
        """Replay exported bytes offline. Pin the checkpoint or bundle digest out of band."""
        state = State()
        for event in events:
            seq, kind, data = event["sequence"], event["kind"], event["data"]
            h = cls.event_hash(run_id, seq, kind, data, state.root)
            if event["run_id"] != run_id or seq != state.sequence + 1 or event["parent"] != state.root or event["digest"] != h:
                raise ValueError("invalid portable journal chain")
            if kind == "start":
                validate("run", data["run"])
                if "plan" in data:
                    if expected_plan_digest != review_plan.plan_digest(data["plan"]) or verifier_key != data.get("verifier_key"):
                        raise ValueError("portable plan or verifier differs from trusted admission")
                    review_plan.validate_plan(data["run"], data["plan"], verifier_key, trust)
                elif expected_plan_digest is not None or verifier_key is not None:
                    raise ValueError("missing pinned admission plan")
                if (
                    seq != 1
                    or data["run"]["run_id"] != run_id
                    or data["trust"] != trust
                    or data["run"]["budget"]["max_cost_microusd"] != 0
                    or data["run"]["budget"]["max_concurrency"] > 2
                ):
                    raise ValueError("invalid portable run manifest")
            elif not state.manifest:
                raise ValueError("missing initial manifest")
            elif kind == "evidence":
                if not state.plan:
                    raise ValueError("observation without admission")
                review_plan.verify_evidence(state, data)
            elif kind == "reserved":
                cls._admit(state, data["assignment"], data["key_id"])
                budget = state.manifest["budget"]
                if (
                    state.cancelled
                    or state.overspent
                    or data["attempt_id"] in state.attempts
                    or data["lease_epoch"] != seq
                    or data["run_epoch"] != state.epoch
                    or instant(data["expires_utc"]) > instant(budget["deadline_utc"])
                    or sum(a["state"] in ("reserved", "dispatched") for a in state.attempts.values()) >= budget["max_concurrency"]
                ):
                    raise ValueError("invalid portable reservation")
            elif kind in ("dispatched", "fenced", "receipt", "rejected"):
                a = state.attempts.get(data["attempt_id"])
                if a is None:
                    raise ValueError("event does not reference a reservation")
                if kind == "dispatched" and (
                    state.cancelled or state.overspent or a["state"] != "reserved" or instant(data["started_utc"]) >= instant(a["expires_utc"])
                ):
                    raise ValueError("invalid portable dispatch")
                if kind == "fenced" and (a["state"], data["state"]) not in (("reserved", "released"), ("dispatched", "uncertain")):
                    raise ValueError("invalid portable fence")
                if kind == "receipt":
                    r = data["receipt"]
                    raw = base64.b64decode(data["output"], validate=True) if data["output"] is not None else None
                    if not cls._receipt_is_new(state, a, r, raw):
                        raise ValueError("duplicate receipt event in the journal")
                    known = r["usage_known"]
                    over = known and (
                        r["input_tokens"] + r["output_tokens"] > a["assignment"]["token_reservation"]
                        or r["cost_microusd"] > a["assignment"]["cost_reservation_microusd"]
                    )
                    if over != data["overspent"]:
                        raise ValueError("portable reservation exposure differs")
                    accepted = data["state"] == "accepted"
                    if accepted and (
                        state.cancelled
                        or state.overspent
                        or over
                        or not known
                        or a["state"] != "dispatched"
                        or r["outcome"] != "completed"
                        or instant(r["ended_utc"]) >= instant(a["expires_utc"])
                        or (a["assignment"]["phase"] == "blind" and state.seal is not None)
                    ):
                        raise ValueError("invalid portable receipt acceptance")
                    if not accepted and data["state"] != ("settled" if known else "uncertain"):
                        raise ValueError("invalid portable receipt settlement")
            elif kind == "seal":
                blind = [a for a in state.attempts.values() if a["assignment"]["phase"] == "blind"]
                expected = [[a["attempt_id"], a["state"], a.get("receipt", {}).get("output_digest")] for a in blind]
                if (
                    state.cancelled
                    or state.seal
                    or not blind
                    or any(a["state"] in ("reserved", "dispatched") for a in blind)
                    or data["attempts"] != expected
                    or data["seal"] != digest(rfc8785.dumps(expected))
                ):
                    raise ValueError("invalid portable blind seal")
            elif kind == "cancel" and state.cancelled:
                raise ValueError("duplicate portable cancellation")
            state.apply(kind, data)
            state.sequence, state.previous, state.root = seq, state.root, h
        validate("checkpoint", checkpoint)
        if not state.manifest or cls._checkpoint(state) != checkpoint:
            raise ValueError("portable checkpoint differs from journal")
        return {
            **cls._summary(state),
            **({"coverage_report": review_plan.coverage_report(state)} if state.plan else {}),
            "run": state.manifest,
            "accepted_attempts": {k: {"receipt": a["receipt"], "assignment": a["assignment"]} for k, a in state.attempts.items() if a["state"] == "accepted"},
        }

    def close(self):
        # Connections are per command so close/reopen is identical to a new process.
        pass
