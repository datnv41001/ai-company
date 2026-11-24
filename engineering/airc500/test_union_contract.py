"""The profile, source, tool grant and model must agree with the approved plan before a lease."""

from copy import deepcopy
import gzip
import json
import unittest
from pathlib import Path

from review_journal import Journal, State
from review_plan import plan_digest, validate_plan
from research_cards import packet
from union_cases import SEMANTICS, holdout
from union_eval import decide
from union_release import ENROLLMENT
from union_study import open_enrollment

EVIDENCE = Path(__file__).parent / "evidence/union-v3"


class BoundPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e, _, _, cls.key, cls.p = open_enrollment(EVIDENCE, ENROLLMENT, "smol")
        package = json.loads(gzip.decompress((EVIDENCE / "smol.json.gz").read_bytes()))
        cls.spec = package["run"]
        cls.ass = next(ev["data"]["assignment"] for ev in package["events"] if ev["kind"] == "reserved")

    def test_re_signed_bad_source_template_is_not_authorized(self):
        for change in ("template", "source_manifest", "model_digest", "runtime_digest", "obligations", "principal"):
            p = deepcopy(self.p)
            j = p["assignments"][0]
            if change == "template":
                j[change]["messages"][1]["content"] = "another unrelated fixture"
            elif change == "obligations":
                j[change] = ["other"]
            else:
                j[change] = "f" * 64
            with self.subTest(field=change), self.assertRaises(ValueError):
                validate_plan({**self.spec, "policy_digest": plan_digest(p)}, p, self.e["verifier_key"], self.e["trust"]["smol"])

    def test_lease_rejects_caller_substitution(self):
        s = State(manifest=self.spec, trust=self.e["trust"]["smol"], plan=self.p)
        Journal._admit(s, self.ass, self.key)
        for key, val in (("context_digest", "1" * 64), ("tool_grant_digest", "2" * 64), ("principal", "unbound-reader")):
            with self.subTest(field=key), self.assertRaises(ValueError):
                Journal._admit(s, {**self.ass, key: val}, self.key)
        with self.assertRaises(ValueError):
            Journal._admit(s, self.ass, "3" * 64)

    def test_scoped_semantics_and_unresolved_do_not_become_verified_clean(self):
        rows, labels = holdout()
        opinions = {}
        for c in rows:
            if c["kind"] == "semantic":
                uid = c["id"]
                truth = labels[uid]
                opinions[uid] = dict(
                    verdict="clean" if truth == "unresolved" else truth,
                    citation=c["sources"][0]["ref"],
                    reason="contradicts" if truth == "defect" else "agrees",
                    operation=SEMANTICS[c["domain"]][4] if truth == "defect" else "keep",
                )
        d = decide(rows, [opinions])
        self.assertTrue(all(d[u]["state"] == ("unresolved" if t == "unresolved" else "verified_" + t) for u, t in labels.items()))
        wrong = deepcopy(opinions)
        for c in rows:
            if c["kind"] == "semantic":
                wrong[c["id"]]["citation"] = c["sources"][1]["ref"]
        result = decide(rows, [wrong])
        for c in rows:
            self.assertEqual(result[c["id"]]["state"], d[c["id"]]["state"] if c["kind"] == "typed" else "unresolved")

    def test_public_research_is_topic_scoped_and_provenanced(self):
        with self.assertRaises(ValueError):
            packet("unapproved text or private URL")
        self.assertEqual({c["class"] for c in packet("offers")}, {"community_hypothesis", "official_platform", "vendor_workflow"})
        self.assertEqual(len(packet("market")), 1)
        for c in packet("offers") + packet("market"):
            self.assertTrue(c["url"].startswith("https://"))
            self.assertIn("no authority", c["authority"])
            self.assertEqual(len(c["snapshot_digest"]), 64)
