"""The published capability comparison is reproducible without contacting a model or provider."""

from copy import deepcopy
import json
import unittest

from joint_study import BUDGET, REPOSITORY, ROOT, fixture, open_trial, score, validate_fixture
from local_adapter import file_digest
from pilot_fixture import digest, encoded


class JointEvaluationTests(unittest.TestCase):
    def test_replay_matches_signed_archive_and_scores(self):
        release = json.loads((ROOT / "release.json").read_text(encoding="utf8"))
        for name, checksum in release["archives"].items():
            self.assertEqual(file_digest(ROOT / name), checksum)
        measured = score(release["enrollment"])
        self.assertEqual(measured, json.loads((ROOT / "results.json").read_bytes()))
        for result in measured.values():
            self.assertEqual(result["actual_calls"], 10)
            self.assertEqual(len(result["reviewers"]), 2)
            for arm in result["arms"].values():
                self.assertEqual(arm["logical_calls"], 6)
                self.assertEqual(arm["measured"], 8)
                self.assertLessEqual(len(arm["joint"]), min(arm["component"].values()))

    def test_source_and_peer_context_bound_to_experiment(self):
        release = json.loads((ROOT / "release.json").read_bytes())
        enroll, _, recipe = open_trial(release["enrollment"], "q15")
        src = fixture()[1]
        budget = dict(max_concurrency=1, max_tokens=BUDGET, max_cost_microusd=0, max_retries=0, max_debate_rounds=1, attempt_timeout_seconds=180)
        run = dict(budget=budget, repository=REPOSITORY, base_sha=src["base"], head_sha=src["head"], source_manifest_digest=digest(encoded(src)))
        validate_fixture(run, recipe, enroll["trust"]["q15"])
        with self.assertRaisesRegex(ValueError, "budget"):
            validate_fixture({**run, "budget": {**budget, "max_tokens": BUDGET + 1}}, recipe, enroll["trust"]["q15"])
        altered = deepcopy(recipe)
        altered["assignments"][-1]["peer_assignments"] = []
        with self.assertRaises(ValueError):
            validate_fixture(run, altered, enroll["trust"]["q15"])
        with self.assertRaises(ValueError):
            validate_fixture({**run, "repository": "unspecified/source"}, recipe, enroll["trust"]["q15"])
