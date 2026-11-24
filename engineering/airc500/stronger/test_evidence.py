"""Offline checks on the public, preregistered paired checkpoint package."""

import shutil
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stronger_study import DOMAINS, SEEDS, packet, pinned, replay, selected  # noqa: E402

EVIDENCE = ROOT / "stronger/evidence-v1"
PIN = "041d59f30b978ddf877320215d897760b60a7a59f57cdeda153f56a16d796fac"


class TestPairedWeights(unittest.TestCase):
    def test_blind_pair_and_stratification(self):
        cases, labels = selected()
        self.assertEqual(len(cases), 8)
        for domain in DOMAINS:
            self.assertEqual(sorted(labels[r["unit"]]["defect"] for r in cases if r["domain"] == domain), [False, True])
        for seed in SEEDS:
            small, larger = [packet(name, seed, cases) for name in ("small", "larger")]
            self.assertNotEqual(small.pop("model"), larger.pop("model"))
            self.assertEqual(small, larger)
        with self.assertRaisesRegex(ValueError, "Operator enrollment"):
            pinned(EVIDENCE, "0" * 64)

    def test_release_receipts_and_raw_copy(self):
        results = replay(EVIDENCE, PIN)
        self.assertEqual(results, json.loads((EVIDENCE / "results.json").read_bytes()))
        for by_seed in results["arms"].values():
            self.assertEqual(set(by_seed), {str(s) for s in SEEDS})
            for row in by_seed.values():
                m = row["metrics"]
                self.assertEqual(m["TP"] + m["FN"], 4)
                self.assertEqual(m["FP"] + m["TN"], 4)
                self.assertGreater(row["output_tokens"], 0)
        for decisions in results["matched_binary_decisions"].values():
            self.assertEqual(sum(map(len, decisions.values())), 8)
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / "study"
            shutil.copytree(EVIDENCE, copied)
            response = copied / "small/response-17.json"
            response.write_bytes(response.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "signed response"):
                replay(copied, PIN)
