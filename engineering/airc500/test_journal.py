"""SQLite recovery and genuine asymmetric signature tests, using synthetic model fixtures."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from receipt_auth import digest
from review_journal import Journal, Signer, stamp, verify_signature
from test_wire import fixtures


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "events.sqlite"
        self.now = 1800000000
        self.j = Journal(self.path, clock=lambda: self.now)
        self.signer = Signer.generate("test-adapter")
        self.key = self.signer.key_id
        self.trust = {
            self.key: {
                "public_key": self.signer.public_key,
                "adapter_identity": "test-adapter",
                "model": "receipt-unit-test",
                "model_version": "local-test-1",
                "family": "test",
                "model_digest": "a" * 64,
            }
        }
        self.run = fixtures()["run"]
        self.run["budget"]["deadline_utc"] = stamp(self.now + 600)
        self.rid = self.run["run_id"]
        self.j.start(self.run, self.trust)
        self.ass = fixtures()["assignment"]
        self.raw = b"synthetic unit-test observation"

    def reserve(self, **changes):
        return self.j.reserve({**self.ass, **changes}, self.key)["attempt_id"]

    def dispatch(self, **changes):
        attempt = self.reserve(**changes)
        self.j.dispatch(attempt)
        return attempt

    def receipt(self, attempt, **changes):
        body = dict(
            self.j.receipt_template(attempt),
            ended_utc=stamp(self.now),
            outcome="completed",
            output_digest=digest(self.raw),
            input_tokens=10,
            output_tokens=5,
            usage_known=True,
            cost_microusd=0,
            provider_request_or_local_execution_id="exec-" + attempt,
        )
        return self.signer.sign({**body, **changes})

    def test_signed_bindings_and_raw_output(self):
        a = self.dispatch()
        signed = self.receipt(a)
        verify_signature(signed, self.trust)
        with self.assertRaises(ValueError):
            self.j.ingest(signed, b"different")
        for field, value in {
            "model_version": "not-pinned",
            "model_digest": "e" * 64,
            "context_digest": "c" * 64,
            "assignment_id": "another",
            "head_sha": "c" * 40,
            "lease_epoch": 999,
            "reviewer_id": "MK-023",
        }.items():
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.j.ingest(self.receipt(a, **{field: value}), self.raw)
        for field, value in {"algorithm": "other", "key_id": "0" * 64, "signature_version": 2}.items():
            tampered = deepcopy(signed)
            tampered["signature"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.j.ingest(tampered, self.raw)
        impostor = Signer.generate("test-adapter")
        with self.assertRaises(ValueError):
            self.j.ingest(impostor.sign(signed), self.raw)
        with self.assertRaises(ValueError):
            self.j.ingest({**signed, "output_tokens": 6}, self.raw)
        self.assertEqual(self.j.summary(self.rid)["rejected_receipts"], 13)
        self.assertEqual(self.j.ingest(signed, self.raw), "accepted")
        self.assertEqual(self.j.ingest(signed, self.raw), "duplicate")
        report = self.j.summary(self.rid)
        self.assertEqual((report["accepted_receipts"], report["input_tokens"], report["output_tokens"]), (1, 10, 5))

    def test_key_window_and_manifest_immutable(self):
        a = self.dispatch()
        signed = self.receipt(a)
        for pin in ({"not_before": stamp(self.now + 1)}, {"not_after": stamp(self.now - 1)}):
            with self.assertRaises(ValueError):
                verify_signature(signed, {self.key: {**self.trust[self.key], **pin}})
        self.j.start(self.run, self.trust)
        with self.assertRaises(ValueError):
            self.j.start({**self.run, "head_sha": "f" * 40}, self.trust)
        with self.assertRaises(ValueError):
            self.reserve(principal="writer")

    def test_future_completion_does_not_settle_usage(self):
        a = self.dispatch()
        with self.assertRaises(ValueError):
            self.j.ingest(self.receipt(a, ended_utc=stamp(self.now + 60)), self.raw)
        self.assertEqual(self.j.summary(self.rid)["held_tokens"], 4000)
        self.assertEqual(self.j.ingest(self.receipt(a), self.raw), "accepted")

    def test_two_runs_share_the_host_slot_limit(self):
        other = "parallel-run"
        self.j.start({**self.run, "run_id": other}, self.trust)
        self.reserve(assignment_id="first")
        self.reserve(assignment_id="second")
        with self.assertRaises(ValueError):
            self.reserve(run_id=other)
        self.j.cancel(self.rid)
        self.reserve(run_id=other)
        self.assertEqual(self.j.summary(other)["attempts"], 1)

    def test_checkpoint_recovers_predispatch_and_inflight_differently(self):
        open_ = self.reserve()
        active = self.dispatch(assignment_id="other")
        cp = self.j.checkpoint(self.rid)
        self.assertEqual(len(cp["open_reservations"]), 2)
        j = Journal(self.path, clock=lambda: self.now)
        with self.assertRaises(ValueError):
            j.recover(self.rid, {**cp, "run_epoch": 999})
        j.recover(self.rid, cp)
        j.recover(self.rid, cp)
        with self.assertRaises(ValueError):
            j.dispatch(open_)
        with self.assertRaises(ValueError):
            self.reserve(assignment_id="other")
        summary = j.summary(self.rid)
        self.assertEqual((summary["dispatches"], summary["held_tokens"], summary["uncertain_attempts"]), (1, 4000, 1))
        j.dispatch(self.reserve())
        self.assertEqual(j.ingest(self.receipt(active), self.raw), "ledger_only")
        self.assertEqual(j.summary(self.rid)["accepted_receipts"], 0)

    def test_cancel_fences_late_usage_and_preserves_seal(self):
        blind = self.dispatch()
        self.j.ingest(self.receipt(blind), self.raw)
        seal = self.j.seal(self.rid)
        late = self.dispatch(phase="cross", round=1, assignment_id="peer")
        waiting = self.reserve(phase="arbitration", round=1, assignment_id="arb", reviewer_id="AR-002")
        cp = self.j.checkpoint(self.rid)
        self.j.cancel(self.rid)
        self.j.cancel(self.rid)
        reopened = Journal(self.path, clock=lambda: self.now)
        reopened.recover(self.rid, cp)
        with self.assertRaises(ValueError):
            reopened.dispatch(waiting)
        with self.assertRaises(ValueError):
            self.reserve(phase="cross", round=1, assignment_id="new")
        signed = self.receipt(late)
        self.assertEqual(reopened.ingest(signed, self.raw), "ledger_only")
        self.assertEqual(reopened.ingest(signed, self.raw), "duplicate")
        self.assertEqual(reopened.seal(self.rid), seal)
        cp = reopened.checkpoint(self.rid)
        self.assertTrue(cp["cancelled"])
        self.assertEqual((cp["run_epoch"], cp["open_reservations"]), (2, []))
        self.assertEqual(reopened.coverage(self.rid, [self.ass["assignment_id"]]), "inconclusive")
        summary = reopened.summary(self.rid)
        self.assertEqual((summary["accepted_receipts"], summary["input_tokens"], summary["output_tokens"]), (1, 20, 10))

    def test_unknown_usage_keeps_exposure_until_known(self):
        a = self.dispatch()
        self.j.timeout(a)
        unknown = self.receipt(a, outcome="unknown", usage_known=False, input_tokens=None, output_tokens=None, cost_microusd=None, output_digest=None)
        self.assertEqual(self.j.ingest(unknown, None), "ledger_only")
        with self.assertRaises(ValueError):
            self.reserve()
        self.assertEqual(self.j.summary(self.rid)["held_tokens"], 4000)
        self.assertEqual(self.j.ingest(self.receipt(a), self.raw), "ledger_only")
        self.assertEqual(self.j.summary(self.rid)["held_tokens"], 0)
        b = self.dispatch()
        self.assertNotEqual(a, b)
        self.assertEqual(self.j.ingest(self.receipt(b), self.raw), "accepted")
        with self.assertRaises(ValueError):
            self.j.ingest(self.receipt(a, output_tokens=99), self.raw)
        self.assertEqual(self.j.summary(self.rid)["accepted_receipts"], 1)

    def test_barrier_and_missing_coverage(self):
        with self.assertRaises(ValueError):
            self.reserve(phase="cross", round=1)
        a = self.dispatch()
        with self.assertRaises(ValueError):
            self.j.seal(self.rid)
        self.j.ingest(self.receipt(a), self.raw)
        self.j.seal(self.rid)
        with self.assertRaises(ValueError):
            self.reserve(assignment_id="late-blind")
        with self.assertRaises(ValueError):
            self.reserve(phase="cross", round=3, assignment_id="peer")
        self.assertEqual(self.j.coverage(self.rid, [self.ass["assignment_id"]]), "complete")
        self.assertEqual(self.j.coverage(self.rid, ["missing"]), "inconclusive")

    def test_concurrent_last_reservation(self):
        def take(i):
            try:
                return self.reserve(assignment_id=f"A{i}", token_reservation=88000)
            except ValueError:
                return None

        with ThreadPoolExecutor(2) as pool:
            leases = list(pool.map(take, range(2)))
        self.assertEqual(sum(a is not None for a in leases), 1)
        self.assertEqual(self.j.summary(self.rid)["held_tokens"], 88000)

    def test_expiry_and_overbudget(self):
        a = self.dispatch()
        self.now += 91
        self.assertEqual(self.j.ingest(self.receipt(a), self.raw), "ledger_only")
        b = self.dispatch(assignment_id="second")
        self.assertEqual(self.j.ingest(self.receipt(b, input_tokens=4001), self.raw), "ledger_only")
        self.assertTrue(self.j.summary(self.rid)["over_budget"])
        with self.assertRaises(ValueError):
            self.reserve(assignment_id="third")

    def test_corrupted_log_fails_recovery(self):
        self.reserve()
        cp = self.j.checkpoint(self.rid)
        with self.j.connection() as db:
            db.execute("UPDATE events SET hash=? WHERE seq=2", ("0" * 64,))
        with self.assertRaises(ValueError):
            self.j.recover(self.rid, cp)

    def test_receipt_execution_id_cannot_be_counted_twice(self):
        a = self.dispatch()
        self.j.ingest(self.receipt(a), self.raw)
        b = self.dispatch(assignment_id="second")
        with self.assertRaises(ValueError):
            self.j.ingest(self.receipt(b, provider_request_or_local_execution_id="exec-" + a), self.raw)
        self.assertEqual(self.j.summary(self.rid)["accepted_receipts"], 1)

    def test_portable_replay_checks_receipt_bindings_cancel_and_seal(self):
        a = self.dispatch()
        self.j.ingest(self.receipt(a), self.raw)
        self.j.seal(self.rid)
        late = self.dispatch(assignment_id="peer", phase="cross", round=1)
        self.j.cancel(self.rid)
        self.j.ingest(self.receipt(late), self.raw)
        cp = self.j.checkpoint(self.rid)
        events = self.j.export_events(self.rid)
        verified = Journal.verify_events(self.rid, events, cp, self.trust)
        self.assertEqual(verified.pop("run"), self.run)
        self.assertEqual(set(verified.pop("accepted_attempts")), {a})
        self.assertEqual(verified, self.j.summary(self.rid))
        for field, value in (("event_root", "f" * 64), ("cancelled", False)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                Journal.verify_events(self.rid, events, {**cp, field:value}, self.trust)
        # Rehashing unsigned events cannot turn a late signature into an accepted output.
        edited = deepcopy(events)
        edited[-1]["data"]["state"] = "accepted"
        edited[-1]["digest"] = Journal.event_hash(self.rid, edited[-1]["sequence"], "receipt",
                                                  edited[-1]["data"], edited[-1]["parent"])
        with self.assertRaisesRegex(ValueError, "receipt acceptance"):
            Journal.verify_events(self.rid, edited, {**cp, "event_root":edited[-1]["digest"]}, self.trust)
