"""Replay the reviewed holdouts, including public trust roots, with no network or models."""

import unittest
from pathlib import Path

from pilot_fixture import digest
from quality_report import render
from quality_study import summarize, verify_index

ROOT = Path(__file__).resolve().parent / "evidence" / "quality-v2"
# These pins live in reviewed source outside the evidence package.
PINS = {
    "marketing": ("1ea5a98f97c21a08bfc19cfd058ea7f93e0f30da19dc3f5685b7852ce7aeed2b", "e5f05c3b92bcef739fe2d683728f303e1049c4b85d5636bc2cff19d95568faeb"),
    "identity": ("548266dc5cb792cfcc480fa2513b19c70c782c71a5f5018f73d6489765e6b191", "b43cf9c34ca8986f291ec7f87869d872f8c1044182033f5c619db89100c1b616"),
}


class PublishedQualityTests(unittest.TestCase):
    def test_paired_studies_replay_all_planned_calls_and_public_scores(self):
        for cohort, (enrollment, package) in PINS.items():
            with self.subTest(cohort=cohort):
                directory = ROOT / cohort
                self.assertEqual(digest((directory / "enrollment.json").read_bytes()), enrollment)
                verify_index(directory, package)
                results = summarize(directory)
                self.assertEqual(set(results["seeds"]), {"17", "43"})
                count = 40 if cohort == "marketing" else 10
                for row in results["seeds"].values():
                    participation = row["participation"]
                    self.assertEqual([participation[k] for k in ("attempts", "dispatches", "accepted_receipts")], [count] * 3)
                    self.assertEqual(participation["settled_microusd"], 0)
                    self.assertEqual(participation["rejected_receipts"] + participation["uncertain_attempts"], 0)
                    self.assertEqual(row["coverage"]["execution"]["accepted"], count)
                    self.assertEqual(row["coverage"]["decision"], "inconclusive")
                    self.assertEqual(len(row["five_arms"]), 5)
                if cohort == "marketing":
                    first = results["seeds"]["17"]["five_arms"]
                    self.assertEqual((first["deterministic_only"]["TP"], first["independent_reviewers"]["FP"]), (36, 48))

    def test_handoff_tables_are_generated_from_the_measured_archives(self):
        self.assertEqual((ROOT / "README.md").read_text(encoding="utf-8"), render(ROOT))
