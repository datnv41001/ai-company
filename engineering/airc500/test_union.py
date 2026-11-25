import unittest

from union_cases import holdout
from union_eval import decide, summarize


class UnionTests(unittest.TestCase):
    def test_silence_and_false_citation_preserve_scan(self):
        rows, _ = holdout()
        typed = next(r for r in rows if r["kind"] == "typed" and r["authorized"] != r["observation"])
        missing = next(r for r in rows if r["kind"] == "semantic")
        decisions = decide([typed, missing], [{missing["id"]: {"verdict": "clean", "citation": "nonexistent", "reason": "agrees", "operation": "keep"}}])
        self.assertEqual(decisions[typed["id"]]["state"], "verified_defect")
        self.assertEqual(decisions[typed["id"]]["provider"], "deterministic")
        self.assertEqual(decisions[missing["id"]]["state"], "unresolved")
        metrics = summarize([typed, missing], decisions)
        self.assertEqual(metrics["release"], "inconclusive")
        self.assertEqual(metrics["ai_actionable"], 0)
