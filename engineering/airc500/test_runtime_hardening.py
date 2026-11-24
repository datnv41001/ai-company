"""Controlled local fixtures for admission, source gating, event intake and OS process capacity."""

from contextlib import ExitStack
import hashlib
import hmac
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import host_capacity
from event_intake import Inbox, PRODUCT_REPO, SYNTHETIC_REPO
from local_adapter import stage_runtime
from pilot_fixture import import_pr
from receipt_auth import Signer, digest
from review_journal import Journal, stamp
from review_plan import EvidenceSigner, catalog, plan_digest
from test_wire import fixtures


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = 1800000000
        self.j = Journal(Path(self.temp.name) / "run.sqlite", clock=lambda: self.now)
        self.manifest = fixtures()["run"]
        self.manifest["catalog_digest"] = catalog()[0]
        self.manifest["budget"]["deadline_utc"] = stamp(self.now + 300)
        self.rid = self.manifest["run_id"]
        self.adapter = Signer.generate("owned-fixture")
        self.verifier = EvidenceSigner.generate()
        self.trust = {
            self.adapter.key_id: {
                "public_key": self.adapter.public_key,
                "adapter_identity": "owned-fixture",
                "model": "fixture",
                "model_version": "1",
                "model_digest": "a" * 64,
                "family": "fixture",
            }
        }
        self.plan = {
            "version": 1,
            "required_obligations": ["fee", "terms"],
            "assignments": [
                {
                    "assignment_id": "blind",
                    "reviewer_id": "MK-022",
                    "phase": "blind",
                    "artifact_kind": catalog()[1]["MK-022"]["artifact_kind"],
                    "obligations": ["fee"],
                },
                {
                    "assignment_id": "arb",
                    "reviewer_id": "AR-002",
                    "phase": "arbitration",
                    "artifact_kind": catalog()[1]["AR-002"]["artifact_kind"],
                    "obligations": ["terms"],
                },
            ],
        }
        self.j.start_planned(self.manifest, self.trust, self.plan, self.verifier.public_key)

    def assignment(self, index):
        job = self.plan["assignments"][index]
        return {
            **fixtures()["assignment"],
            **{k: v for k, v in job.items() if k != "obligations"},
            "output_contract": catalog()[1][job["reviewer_id"]]["contract"],
        }

    def execute(self, index):
        a = self.assignment(index)
        attempt = self.j.reserve(a, self.adapter.key_id)["attempt_id"]
        self.j.dispatch(attempt)
        raw = a["assignment_id"].encode()
        r = self.adapter.sign(
            {
                **self.j.receipt_template(attempt),
                "ended_utc": stamp(self.now),
                "outcome": "completed",
                "output_digest": digest(raw),
                "input_tokens": 10,
                "output_tokens": 1,
                "usage_known": True,
                "cost_microusd": 0,
                "provider_request_or_local_execution_id": attempt,
            }
        )
        self.assertEqual(self.j.ingest(r, raw), "accepted")
        return r

    def proof(self, r, obligation, status, signer=None):
        return (signer or self.verifier).attest(self.rid, plan_digest(self.plan), r["assignment_id"], obligation, r["output_digest"], "c" * 64, status)

    def test_predeclared_scope_and_independent_evidence(self):
        r = self.execute(0)
        self.j.seal(self.rid)
        self.j.record_evidence(self.proof(r, "fee", "verified"))
        missing = self.j.coverage_report(self.rid)
        self.assertEqual(missing["execution"]["missing"], ["arb"])
        self.assertEqual(missing["evidence"]["missing"], ["terms"])
        self.assertEqual(self.j.coverage(self.rid, ["blind"]), "inconclusive")
        a = self.execute(1)
        self.j.record_evidence(self.proof(a, "terms", "insufficient"))
        report = self.j.coverage_report(self.rid)
        self.assertEqual((report["decision"], report["execution"]["accepted"], report["evidence"]["verified"]), ("inconclusive", 2, 1))
        cp = self.j.checkpoint(self.rid)
        events = self.j.export_events(self.rid)
        replay = Journal.verify_events(self.rid, events, cp, self.trust, expected_plan_digest=plan_digest(self.plan), verifier_key=self.verifier.public_key)
        self.assertEqual(replay["coverage_report"], report)
        for diff in (
            {"expected_plan_digest": "f" * 64, "verifier_key": self.verifier.public_key},
            {"expected_plan_digest": plan_digest(self.plan), "verifier_key": EvidenceSigner.generate().public_key},
        ):
            with self.assertRaises(ValueError):
                Journal.verify_events(self.rid, events, cp, self.trust, **diff)

    def test_no_self_evidence_or_wrong_scope(self):
        with self.assertRaises(ValueError):
            self.j.start(self.manifest, self.trust)
        with self.assertRaises(ValueError):
            self.j.start_planned(self.manifest, self.trust, self.plan, self.adapter.public_key)
        for key, val in (("reviewer_id", "MK-999"), ("phase", "cross"), ("artifact_kind", "unplanned"), ("assignment_id", "missing")):
            with self.assertRaises(ValueError):
                self.j.reserve({**self.assignment(0), key: val}, self.adapter.key_id)
        r = self.execute(0)
        for record in (
            self.proof(r, "terms", "verified"),
            self.proof(r, "fee", "verified", EvidenceSigner.generate()),
            {**self.proof(r, "fee", "verified"), "plan_digest": "a" * 64},
        ):
            with self.assertRaises(ValueError):
                self.j.record_evidence(record)
        self.j.record_evidence(self.proof(r, "fee", "verified"))
        with self.assertRaises(ValueError):
            self.j.record_evidence(self.proof(r, "fee", "verified"))

    def test_bad_catalog_or_plan_cannot_replace_admission(self):
        for bad in (
            {**self.plan, "required_obligations": ["fee"]},
            {**self.plan, "assignments": [{**self.plan["assignments"][0], "reviewer_id": "MK-999"}, self.plan["assignments"][1]]},
        ):
            with self.assertRaises(ValueError):
                self.j.start_planned(self.manifest, self.trust, bad, self.verifier.public_key)
        with self.assertRaises(ValueError):
            self.j.start_planned({**self.manifest, "catalog_digest": "0" * 64}, self.trust, self.plan, self.verifier.public_key)

    def test_complete_coverage_requires_both_obligations_and_still_has_no_quality_verdict(self):
        note = self.execute(0)
        self.j.seal(self.rid)
        arbiter = self.execute(1)
        for receipt, oid in ((note, "fee"), (arbiter, "terms")):
            self.j.record_evidence(self.proof(receipt, oid, "verified"))
        report = self.j.coverage_report(self.rid)
        self.assertEqual(report["decision"], "covered")
        self.assertEqual(report["quality"], "separately_measured")
        self.assertEqual(self.j.coverage(self.rid, ["blind"]), "inconclusive")


class PhysicalCapacityTests(unittest.TestCase):
    def test_child_holds_physical_slot_after_supervisor_releases_handle(self):
        with ExitStack() as registration:
            sockets = [registration.enter_context(socket.socket()) for _ in range(2)]
            for s in sockets:
                s.bind(("127.0.0.1", 0))
            ports = tuple(s.getsockname()[1] for s in sockets)
        with patch.object(host_capacity, "PORTS", ports):
            with host_capacity.machine_slot() as slot:
                port = slot.getsockname()[1]
                child = host_capacity.spawn_with_slot(
                    slot,
                    [sys.executable, "-c", "import sys;print('ready',flush=True);sys.stdin.readline()"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    text=True,
                )
                self.assertEqual(child.stdout.readline().strip(), "ready")
            try:
                with host_capacity.machine_slot() as second:
                    self.assertNotEqual(second.getsockname()[1], port)
                    with self.assertRaisesRegex(RuntimeError, "in use"), host_capacity.machine_slot():
                        pass
            finally:
                child.terminate()
                child.wait(timeout=5)
                child.stdin.close()
                child.stdout.close()
            # Windows may finish releasing kernel socket handles just after the
            # child process object is signaled. Capacity remains conservative.
            deadline = time.monotonic() + 5
            while True:
                with host_capacity.machine_slot() as released:
                    if released.getsockname()[1] == port:
                        break
                self.assertLess(time.monotonic(), deadline, "terminated child still owns its physical slot")
                time.sleep(0.01)

    def test_substituted_binary_or_library_or_weights_fails_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exe = root / "model-host"
            shim = root / "helper.dll"
            weights = root / "model.gguf"
            for src, value in ((exe, b"host"), (shim, b"library"), (weights, b"weights")):
                src.write_bytes(value)
            pin = root / "pins.json"
            pin.write_text(json.dumps({"format": 1, "executable": exe.name, "files": {exe.name: digest(b"host"), shim.name: digest(b"library")}}))
            for i, path in enumerate((exe, shim, weights)):
                with self.subTest(path=path.name):
                    original = path.read_bytes()
                    path.write_bytes(b"substituted")
                    tmpdir = root / str(i)
                    tmpdir.mkdir()
                    with self.assertRaisesRegex(ValueError, "digest mismatch|Unexpected model"):
                        stage_runtime(exe, weights, tmpdir, pin, digest(b"host"), digest(b"weights"))
                    path.write_bytes(original)

    def test_unenrolled_source_is_rejected_before_git(self):
        with self.assertRaisesRegex(ValueError, "enrolled synthetic"):
            import_pr(Path("/unopened"), "a" * 40, "b" * 40)


class EventTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.secret = os.urandom(32)
        self.base = "a" * 40
        self.head = "b" * 40
        self.state = "open"
        self.now = 1800000000
        self.box = Inbox(Path(self.tmp.name) / "inbox.sqlite", self.secret, lookup=lambda repo, pr: (self.state, self.base, self.head), clock=lambda: self.now)

    def send(self, delivery, head=None, repo=PRODUCT_REPO, wrong=False):
        data = json.dumps(
            {
                "action": "synchronize",
                "repository": {"full_name": repo},
                "number": 1,
                "pull_request": {"number": 1, "base": {"sha": self.base, "repo": {"full_name": repo}}, "head": {"sha": head or self.head}},
            }
        ).encode()
        sig = "sha256=" + hmac.new(self.secret, data, hashlib.sha256).hexdigest()
        return self.box.ingest(data, "sha256=invalid" if wrong else sig, delivery, "pull_request")

    def test_signature_current_head_and_idempotency(self):
        with self.assertRaises(ValueError):
            self.send("a", wrong=True)
        self.assertEqual(self.send("a")["decision"], "metadata_only")
        self.assertEqual(self.send("a")["decision"], "duplicate")
        self.assertEqual(self.send("b")["decision"], "duplicate_revision")
        self.assertEqual(self.send("c", "c" * 40)["decision"], "stale")
        with self.assertRaises(ValueError):
            self.send("a", "c" * 40)
        with self.assertRaises(ValueError):
            self.box.handoff("a", Path("unopened"), "dummy", "dummy")

    def test_revisions_and_deadline_are_bounded(self):
        self.send("initial")
        previous = self.head
        self.head = "c" * 40
        self.assertEqual(self.send("second")["superseded_head"], previous)
        self.head = "d" * 40
        self.assertEqual(self.send("third")["decision"], "human_escalation")
        self.now += 2701
        self.head = "e" * 40
        self.assertEqual(self.send("expired")["decision"], "human_escalation")

    def test_synthetic_event_generates_scoped_plan_and_verified_local_handoff(self):
        from pilot_fixture import synthetic_pr

        manifest, _ = synthetic_pr()
        self.base, self.head = manifest["base_sha"], manifest["head_sha"]
        result = self.send("fixture", repo=SYNTHETIC_REPO)
        self.assertEqual(result["decision"], "fixture_plan_ready")
        self.assertEqual(len(result["review_plan"]["assignments"]), 11)
        path = Path(__file__).parent / "evidence/qwen-marketing-01"
        draft = self.box.handoff(
            "fixture",
            path,
            "dacc572f1d25c18c491c0c6364111603a2038dab13e8d89df0d6997f147a6167",
            "400f86483df5c4521ace9c26c5f83975f2e45415d56c8af1a6e684e259948ca9",
        )
        self.assertEqual({x["unit"] for x in draft["assignments"]}, {"H01", "H04"})
        self.head = "a" * 40
        with self.assertRaises(ValueError):
            self.box.handoff("fixture", path, "dummy", "dummy")
