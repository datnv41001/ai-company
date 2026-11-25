"""Generation fences, reviewed artifacts and durable local delivery on synthetic metadata."""

from hashlib import sha256
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from event_intake import Inbox, SYNTHETIC_REPO
from generation_inbox import V1_INDEX, V1_TRUST
from pilot_fixture import synthetic_pr


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "inbox.sqlite"
        self.key = b"k" * 32
        m, _ = synthetic_pr()
        self.base, self.a = m["base_sha"], m["head_sha"]
        self.meta = ("open", self.base, self.a, "main")
        self.box = self.reopen()

    def reopen(self):
        return Inbox(self.path, self.key, lookup=lambda *_: self.meta)

    def send(self, delivery, action):
        status, base, head, ref = self.meta
        obj = dict(
            action=action,
            number=1,
            repository=dict(full_name=SYNTHETIC_REPO),
            pull_request=dict(number=1, base=dict(sha=base, ref=ref, repo=dict(full_name=SYNTHETIC_REPO)), head=dict(sha=head)),
        )
        if action == "edited":
            obj["changes"] = {"base": {"ref": {"from": "main"}}}
        raw = json.dumps(obj).encode()
        return self.box.ingest(raw, "sha256=" + hmac.new(self.key, raw, sha256).hexdigest(), delivery, "pull_request")

    def draft(self, delivery, **kwargs):
        return self.box.handoff(delivery, Path(__file__).parent / "evidence/qwen-marketing-01", kwargs.get("index", V1_INDEX), V1_TRUST)

    def test_aba_preserves_new_generation_and_caps_repairs(self):
        self.assertEqual(self.send("first", "opened")["generation"], 1)
        self.meta = ("open", self.base, "d" * 40, "main")
        self.assertEqual(self.send("second", "synchronize")["generation"], 2)
        self.meta = ("open", self.base, self.a, "main")
        event = self.send("third", "synchronize")
        self.assertEqual((event["generation"], event["decision"]), (3, "human_escalation"))
        with self.assertRaisesRegex(ValueError, "stale generation"):
            self.draft("first")

    def test_close_reopen_fences_even_with_same_sha(self):
        self.send("first", "opened")
        self.meta = ("closed", self.base, self.a, "main")
        self.assertEqual(self.send("closed", "closed")["decision"], "closed")
        self.meta = ("open", self.base, self.a, "main")
        reopened = self.send("back", "reopened")
        self.assertEqual((reopened["generation"], reopened["cycle"]), (3, 2))
        with self.assertRaises(ValueError):
            self.draft("first")
        self.meta = ("open", self.base, self.a, "release")
        retarget = self.send("base-change", "edited")
        self.assertEqual(retarget["generation"], 4)
        with self.assertRaises(ValueError):
            self.draft("back")

    def test_reopened_edge_fences_old_work_even_when_close_delivery_was_missing(self):
        self.send("first", "opened")
        self.assertEqual(self.send("reopen", "reopened")["generation"], 2)
        self.assertEqual(self.send("redelivery", "reopened")["decision"], "duplicate_revision")
        with self.assertRaises(ValueError):
            self.draft("first")

    def test_retry_and_ack_after_restart(self):
        self.send("first", "opened")
        with self.assertRaisesRegex(ValueError, "not enrolled"):
            self.draft("first", index="f" * 64)
        a = self.draft("first")
        self.box = self.reopen()
        self.assertEqual(self.draft("first"), a)
        for _ in range(2):
            self.assertEqual(self.box.acknowledge("first", a["outbox_key"])["state"], "acknowledged")
        self.assertEqual(self.draft("first")["outbox_state"], "acknowledged")
        self.meta = ("closed", self.base, self.a, "main")
        self.send("stop", "closed")
        with self.assertRaises(ValueError):
            self.box.acknowledge("first", a["outbox_key"])

    def test_current_revision_rechecked_after_verified_archive(self):
        self.send("first", "opened")

        def race(*_args):
            self.meta = ("closed", self.base, self.a, "main")
            self.send("closed", "closed")
            return [], []

        with patch("generation_inbox.replay_package", side_effect=race), self.assertRaisesRegex(ValueError, "stale generation"):
            self.draft("first")
