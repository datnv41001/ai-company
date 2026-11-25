import copy
import unittest

from research_assessment import CAPABILITIES, qualify
from research_study import ROOT, RUN_REPO, enrolled_context, opened, validate_fixture
from pilot_fixture import digest, encoded
from review_plan import plan_digest


class ResearchPlanTest(unittest.TestCase):
    def setUp(self):
        self.e, self.kid, self.plan = opened(ROOT / "evidence", "0ad84af4a344e25a1b493835f3072dc1f3e55f0d8a9b6b32b195378bb6cc4fba")
        src = self.e["source"]
        self.run = dict(
            repository=RUN_REPO, base_sha=src["base"], head_sha=src["head"], source_manifest_digest=digest(encoded(src)), policy_digest=plan_digest(self.plan)
        )
        self.trust = self.e["trust"]["q15"]

    def test_admitted_scope_has_no_customer_or_external_model_tools(self):
        validate_fixture(self.run, self.plan, self.trust)
        with self.assertRaises(ValueError):
            invalid = copy.deepcopy(self.plan)
            invalid["assignments"][0]["template"]["messages"][1]["content"] = "unreviewed"
            validate_fixture(self.run, invalid, self.trust)
        with self.assertRaises(ValueError):
            validate_fixture({**self.run, "head_sha": "0" * 40}, self.plan, self.trust)

    def test_exact_signed_release_report_and_blind_assessments(self):
        from research_release import verify

        result = verify()
        self.assertEqual(result["calls"], 10)
        self.assertEqual(result["paid_microusd"], 0)
        self.assertEqual(result["reviewer_ids"], ["MK-022"])
        self.assertEqual(result["treatment_without_fresh_sources"], ["L5", "L6"])
        self.assertEqual(sum(g["input_tokens"] for g in result["arms"].values()), 3282)
        self.assertEqual(sum(g["output_tokens"] for g in result["arms"].values()), 1081)
        for arm in result["arms"].values():
            self.assertEqual(sum(sum(counts.values()) for counts in arm["confusion"].values()), 10)

    def test_paired_packets_differ_only_in_public_evidence(self):
        import json

        jobs = {j["assignment_id"]: j["template"] for j in self.plan["assignments"]}
        cases, cards, _ = enrolled_context()
        self.assertEqual((len(cases), len(jobs)), (10, 10))
        for topic, observed in cards.items():
            a, b = (copy.deepcopy(jobs[topic + "-" + arm]) for arm in ("without", "with"))
            pa, pb = (json.loads(req["messages"][1].pop("content")) for req in (a, b))
            self.assertEqual(a, b)
            self.assertEqual(pa.pop("public_evidence"), [])
            self.assertEqual(pb.pop("public_evidence"), observed)
            self.assertEqual(pa, pb)
        self.assertEqual(cards["market"], [])
        self.assertTrue(all(cards[t] for t in cards if t != "market"))

    def test_unmeasured_capabilities_and_small_holdout_do_not_qualify(self):
        caps = qualify(
            {
                "A": {
                    "topic": "catalog",
                    "gold": "flag",
                    "verdict_correct": True,
                    "scope_reason_valid": True,
                    "attribution_valid": True,
                    "recommendation_useful": True,
                }
            }
        )
        self.assertEqual(set(caps), set(CAPABILITIES))
        self.assertEqual(caps["security_and_regression"]["status"], "unmeasured")
        self.assertEqual(caps["code_logic"]["measured"], 0)
        self.assertFalse(any(v["promotion"] for v in caps.values()))
