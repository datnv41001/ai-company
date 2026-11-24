"""Holdout construction, paired assignment design and conservative phase-level scoring."""

import unittest

from quality_corpus import DOMAINS, SEEDS, corpus, deterministic
from quality_eval import fix_matches, explanation_matches, phase, wilson
from quality_run import frozen, peers, prompt


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.cases, self.keys = corpus()
        self.bad = next(c for c in self.cases if deterministic(c) is True)
        self.clean = next(c for c in self.cases if deterministic(c) is False)

    def test_frozen_balanced_corpus_and_controls(self):
        self.assertEqual(corpus(), (self.cases, self.keys))
        self.assertEqual(len(self.keys), 96)
        self.assertEqual({c["domain"] for c in self.cases}, set(DOMAINS))
        for domain in DOMAINS:
            population = [v for v in self.keys.values() if v["domain"] == domain]
            self.assertEqual((len(population), sum(v["defect"] for v in population)), (8, 4))
        ident, labels = corpus("identity")
        self.assertEqual(len(ident), 16)
        self.assertEqual(sum(v["defect"] for v in labels.values()), 8)
        for c in [*self.cases, *ident]:
            if deterministic(c) is not None:
                expected = (self.keys | labels)[c["unit"]]["defect"]
                self.assertEqual(deterministic(c), expected)

    def test_paired_plan_covers_whole_holdout_before_any_inference(self):
        for cohort in ("marketing", "identity"):
            cases, _ = corpus(cohort)
            for seed in SEEDS:
                plan = frozen(cases, seed)
                for group in ("common", "repeat", "specialist", "cross", "arbitration"):
                    jobs = [a for a in plan["assignments"] if a["assignment_id"].split("-")[1] == group]
                    self.assertCountEqual([uid for a in jobs for uid in a["obligations"]], plan["required_obligations"])
                for a, b, c in zip(
                    *([r for r in plan["assignments"] if r["assignment_id"].split("-")[1] == g] for g in ("common", "repeat", "specialist")), strict=True
                ):
                    self.assertEqual(a["reviewer_id"], b["reviewer_id"])
                    self.assertNotEqual(a["reviewer_id"], c["reviewer_id"])
                    self.assertEqual(a["obligations"], c["obligations"])

    def proposal(self, c, flag=True):
        k = self.keys[c["unit"]]
        return {
            "status": "flag" if flag else "clear",
            "affected_subject": k["subject"],
            "current": k["current"],
            "expected": k["expected"],
            "operation": k["operation"],
            "evidence": k["source"],
            "regression": k["criterion"],
            "explanation": k["reason"],
        }

    def test_fix_is_directional_and_requires_all_six_fields(self):
        key = self.keys[self.bad["unit"]]
        op = self.proposal(self.bad)
        self.assertTrue(fix_matches(op, key))
        for f, bad in (
            ("operation", "forbid"),
            ("current", op["expected"]),
            ("expected", "do not use " + op["expected"]),
            ("affected_subject", "sibling"),
            ("regression", "unrelated"),
            ("evidence", "other-source"),
        ):
            with self.subTest(field=f):
                self.assertFalse(fix_matches({**op, f: bad}, key))
        self.assertFalse(explanation_matches({**op, "expected": op["current"], "current": op["expected"]}, key))

    def test_interim_candidate_addition_false_retraction_and_correction(self):
        x, y = self.bad["unit"], self.clean["unit"]
        invalid = {**self.proposal(self.clean), "operation": "forbid"}
        incomplete = {**self.proposal(self.bad), "operation": "forbid"}
        rows = []
        for step, answers in (
            ("blind", {y: invalid}),
            ("cross", {x: incomplete, y: self.proposal(self.clean, False)}),
            ("arbitration", {x: self.proposal(self.bad)}),
        ):
            rows.append({"phase": step, "assignment_id": step, "reviewer_id": "synthetic-" + step, "attempt_id": "test-" + step, "opinions": answers})
        result = phase([self.bad, self.clean], rows, {k: self.keys[k] for k in (x, y)})
        cross = result["phases"]["cross"]
        self.assertEqual((cross["added_true"], cross["removed_false"]), ([x], [y]))
        self.assertEqual(cross["scores"]["actionable_ids"], [])
        self.assertEqual(result["phases"]["arbitration"]["scores"]["actionable_ids"], [x])
        self.assertEqual(result["phases"]["verified_final"]["active"], [x])
        self.assertTrue({"candidate", "challenged", "rejected", "revised", "verified"} <= {e["state"] for e in result["lifecycle"]})

    def test_unsupported_candidate_needs_evidence_and_blind_inputs_exclude_labels(self):
        uid = self.bad["unit"]
        row = {
            "phase": "blind",
            "reviewer_id": "test",
            "assignment_id": "test",
            "attempt_id": "test",
            "opinions": {uid: {**self.proposal(self.bad), "evidence": "unrelated"}},
        }
        result = phase([self.bad], [row], {uid: self.keys[uid]})
        self.assertEqual(result["lifecycle"][-1]["state"], "unresolved")
        self.assertEqual(peers([row], self.cases, "repeat"), {})
        msg = prompt([self.bad], "MK-022", "common", [])[1]["content"]
        for k in ("provenance", "defect", "peer_signals", "keybook_pin"):
            self.assertNotIn('"' + k + '"', msg)

    def test_interval_never_treats_two_seeds_as_independent_cases(self):
        self.assertIsNone(wilson(0, 0)["rate"])
        self.assertEqual(wilson(0, 4)["interval_95"], [0, 0.4899])
        self.assertLess(wilson(0, 48)["interval_95"][1], 0.1)
