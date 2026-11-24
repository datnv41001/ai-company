import copy
import json
import unittest
from collections import Counter

import calibration
import catalog


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = json.loads((catalog.ROOT / "disciplines.json").read_text(encoding="utf-8"))
        cls.rows = catalog.build(cls.groups)

    def test_checked_in_bytes_match_source(self):
        actual = (catalog.ROOT / "reviewers.jsonl").read_text(encoding="utf-8")
        self.assertEqual(actual.encode(), catalog.encoded_catalog())

    def test_exact_ids_and_allocations(self):
        ids = [r["reviewer_id"] for r in self.rows]
        expected = {f"{code}-{i:03d}" for code, n in catalog.COUNTS.items()
                    for i in range(1, n + 1)}
        self.assertEqual(set(ids), expected)
        self.assertEqual(len(ids), 500)
        self.assertEqual(Counter(r.split("-")[0] for r in ids), catalog.COUNTS)

    def test_individual_contracts_and_rubrics(self):
        obligations = set()
        for row in self.rows:
            output = row["output"]
            obligations.add((output["proof_obligation"], output["required_method"]))
            self.assertEqual(sum(rule["points"] for rule in row["rubric"]), 10)
            self.assertIn(row["scope"]["invariant"], output["proof_obligation"])
            contract = "arbitration.v1" if row["reviewer_id"].startswith("AR-") else "review.v1"
            self.assertEqual(output["contract"], contract)
        self.assertEqual(len(obligations), 500)

    def test_read_only_surface(self):
        allowed = {"read_excerpt", "read_trace", "read_blob", "read_test_attestation",
                   "read_render", "read_case"}
        for row in self.rows:
            self.assertTrue(set(row["tools"]) <= allowed)
            self.assertEqual(set(row["tools"]), {catalog.TOOLS[s] for s in row["sources"]})

    def test_bad_catalog_rejected(self):
        for mutation in ("lost", "duplicate", "new_source"):
            with self.subTest(mutation=mutation):
                groups = copy.deepcopy(self.groups)
                if mutation == "lost":
                    groups[0]["subjects"].pop()
                elif mutation == "duplicate":
                    groups[0]["lenses"][1] = groups[0]["lenses"][0]
                else:
                    groups[0]["sources"].append("repository_write")
                with self.assertRaises((ValueError, KeyError)):
                    catalog.build(groups)


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.units = json.loads((calibration.FIXTURES / "units.json").read_text(encoding="utf-8"))
        self.example = json.loads((calibration.FIXTURES / "scoring-example.json").read_text(encoding="utf-8"))

    def test_synthetic_example(self):
        result = calibration.score(self.units, self.example["flagged_units"],
                                   self.example["implementer_flagged_units"])
        self.assertEqual(result, {"TP": 3, "FP": 1, "FN": 1, "TN": 3,
                                  "precision": .75, "recall": .75, "false_positive_rate": .25,
                                  "critical_detected": 3, "critical_total": 3,
                                  "recovered_author_misses": 2, "total_author_misses": 2})

    def test_empty_rates_are_undefined(self):
        results = calibration.score([], [], [])
        for key in ("precision", "recall", "false_positive_rate"):
            self.assertIsNone(results[key])

    def test_invalid_matching_is_rejected(self):
        for flagged in (["unknown"], ["B-1", "B-1"]):
            with self.subTest(flagged=flagged), self.assertRaises(ValueError):
                calibration.score(self.units, flagged, [])
