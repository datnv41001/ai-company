"""Reviewed package replay and the end-to-end local handoff at the enrolled generation."""

import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path

from event_intake import Inbox
from generation_inbox import V3_REPO
from union_release import ENROLLMENT, INDEX, verify_release
from union_cases import holdout, manifest

PATH = Path(__file__).parent / "evidence/union-v3"


class PublishedUnionTests(unittest.TestCase):
    def test_verified_arms_and_zero_api_cost(self):
        study = verify_release(PATH)
        self.assertEqual([study[k]["calls"] for k in ("q05", "q15", "smol")], [32, 4, 4])
        for model in study.values():
            self.assertEqual(model["failed"] + model["cost_microusd"], 0)
            for seed in model["seeds"].values():
                for arm in seed["arms"].values():
                    typed = [d for d in arm["decisions"].values() if d["provider"] == "deterministic"]
                    self.assertEqual(len(typed), 12)
                    self.assertEqual(sum(d["state"] == "verified_defect" for d in typed), 6)
                    self.assertEqual(arm["union"]["ai_actionable"], 0)
                    self.assertEqual(arm["union"]["release"], "inconclusive")
        common = study["q05"]["seeds"]["19"]["arms"]
        self.assertEqual(common["one_repeated"]["calls"], common["two_independent"]["calls"])
        self.assertEqual(common["one_repeated"]["output_ceiling"], common["two_independent"]["output_ceiling"])
        with self.assertRaises(ValueError):
            verify_release(PATH, "f" * 64, ENROLLMENT)

    def test_release_becomes_only_actionable_local_outbox_entries(self):
        src = manifest(holdout()[0])
        key = b"x" * 32
        with tempfile.TemporaryDirectory() as tmp:
            box = Inbox(Path(tmp) / "events.db", key, lookup=lambda *_: ("open", src["base"], src["head"], "main"))
            body = json.dumps(
                dict(
                    action="opened",
                    repository=dict(full_name=V3_REPO),
                    number=1,
                    pull_request=dict(number=1, base=dict(sha=src["base"], ref="main", repo=dict(full_name=V3_REPO)), head=dict(sha=src["head"])),
                )
            ).encode()
            ev = box.ingest(body, "sha256=" + hmac.new(key, body, hashlib.sha256).hexdigest(), "signed-d1", "pull_request")
            out = box.handoff("signed-d1", PATH, INDEX, ENROLLMENT)
            self.assertEqual(out["plan_digest"], ev["plan_digest"])
            self.assertEqual(len(out["assignments"]), 6)
            self.assertEqual(len(out["unresolved"]), 12)
            self.assertEqual(len({i["unit"] for i in out["assignments"]}), 6)
            self.assertTrue(all(i["provider"] == "deterministic" and i["actual"] != i["expected"] for i in out["assignments"]))
            self.assertEqual(box.acknowledge("signed-d1", out["outbox_key"])["state"], "acknowledged")
