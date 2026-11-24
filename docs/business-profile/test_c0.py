"""Synthetic specification examples. These do not exercise the future production feature."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from design_contract import commercial_case, digest, gate, next_setup_step, preview

HERE = Path(__file__).resolve().parent
SNAPSHOT = json.loads((HERE / "synthetic-snapshot.json").read_text(encoding="utf-8"))
CASES = json.loads((HERE / "acceptance-cases.json").read_text(encoding="utf-8"))


class BusinessProfileContract(unittest.TestCase):
    def setUp(self):
        self.s = deepcopy(SNAPSHOT)
        self.c = self.s["claims"][0]
        self.ticket = preview(self.s, "2026-11-24T09:01:00Z")
        self.states = {("source", src["id"], src["revision"]): "approved" for src in self.s["sources"]}
        self.states[("claim", self.c["id"], self.c["revision"])] = "approved"

    def authorize(self, **overrides):
        request = dict(effective_at="2026-11-24T09:12:00Z", scope=self.s["scope"], use=self.c["use"],
                       qualifiers=self.c["qualifiers"], states=self.states)
        return gate(self.s, self.ticket, self.c["id"], **{**request, **overrides})

    def test_preview_queue_and_share_clocks(self):
        later = preview(self.s, "2026-11-24T09:11:00Z")
        self.assertEqual(self.ticket["snapshot_digest"], later["snapshot_digest"])
        self.assertNotEqual(self.ticket["preview_created_at"], later["preview_created_at"])
        self.assertEqual(self.authorize(), "eligible")
        self.assertEqual(self.authorize(effective_at="2026-12-01T00:00:00Z"), "claim_ineligible")
        self.assertEqual(self.authorize(authorized=False), "unavailable")

    def test_changed_snapshot_needs_preview(self):
        self.s["profile_revision"] += 1
        self.assertEqual(self.authorize(), "stale_preview")

    def test_current_evidence_authority_after_qa(self):
        before = digest(self.s)
        self.assertEqual(self.authorize(), "eligible")
        for status in ("withdrawn_false", "withdrawn_prohibited", "disputed", "superseded", "expired"):
            with self.subTest(status=status):
                self.states[("source", "catalog", 2)] = status
                self.assertEqual(self.authorize(), status)
        self.states[("source", "catalog", 2)] = "approved"
        self.states[("claim", self.c["id"], self.c["revision"])] = "withdrawn_false"
        self.assertEqual(self.authorize(), "withdrawn_false")
        self.states.clear()
        self.assertEqual(self.authorize(), "missing_authority")
        self.assertEqual(digest(self.s), before)

    def test_same_brand_different_subject_or_context(self):
        for key in ("product", "variant", "offer", "market", "channel", "locale"):
            with self.subTest(key=key):
                self.assertEqual(self.authorize(use={**self.c["use"], key: "different"}), "wrong_subject_or_use")
        self.assertEqual(self.authorize(qualifiers=[]), "claim_ineligible")
        self.assertEqual(self.authorize(scope={**self.s["scope"], "client": "other"}), "unavailable")

    def test_revision_locator_and_content_are_checked(self):
        for key, replacement, reason in (("revision", 1, "wrong_subject_or_use"),
                                         ("locator", "fixture://unrelated", "wrong_subject_or_use"),
                                         ("excerpt", "Changed excerpt", "invalid_evidence")):
            with self.subTest(key=key):
                self.setUp()
                self.s["sources"][0][key] = replacement
                self.ticket = preview(self.s, self.ticket["preview_created_at"])
                self.assertEqual(self.authorize(), reason)

    def test_marketing_cases(self):
        self.assertEqual({c["id"] for c in CASES}, {"seller", "b2b", "service", "agency", "inhouse"})
        for case in CASES:
            for probe in case["probes"]:
                with self.subTest(persona=case["id"], label=probe["label"]):
                    self.assertEqual(commercial_case(case, probe["change"]), probe["expect"])

    def test_kpi_roles_and_unknown_baselines(self):
        levels = ["business", "marketing", "campaign", "operational", "efficiency"]
        metrics = {m["id"]: m for m in self.s["objectives"]}
        self.assertEqual([m["level"] for m in metrics.values()], levels)
        for metric in metrics.values():
            parent = metric["parent"]
            if parent:
                self.assertIn(parent, metrics)
            baseline = metric["baseline"]
            if baseline["kind"] == "unknown":
                self.assertIsNone(baseline["value"])
            else:
                self.assertEqual(baseline["kind"], "historical")
                self.assertTrue(baseline["source"] and baseline["window"])
            self.assertTrue(metric["owner"] and metric["window"] and metric["method"])
            self.assertIn("target", {v["kind"] for v in metric["values"]})
            for value in metric["values"]:
                if value["kind"] == "observed":
                    self.assertTrue(value["source"] and value["window"])
                elif value["kind"] == "hypothesis":
                    self.assertEqual(value["confidence"], "unverified")
        self.assertEqual(metrics["approved"]["values"][-1]["kind"], "observed")
        self.assertEqual(metrics["cost"]["baseline"]["kind"], "unknown")

    def test_source_expires_before_claim(self):
        self.s["sources"][0]["valid_until"] = "2026-11-24T09:10:00Z"
        self.ticket = preview(self.s, "2026-11-24T09:01:00Z")
        self.assertEqual(self.authorize(effective_at="2026-11-24T09:09:59Z"), "eligible")
        self.assertEqual(self.authorize(effective_at="2026-11-24T09:10:00Z"), "expired")

    def test_commercial_records_resolve_their_own_evidence(self):
        refs = {(s["id"], s["revision"], s["locator"]): s for s in self.s["sources"]}
        for table in ("offers", "availability", "policies"):
            for record in self.s[table]:
                self.assertTrue(record["evidence"])
                for binding in record["evidence"]:
                    src = refs[(binding["id"], binding["revision"], binding["locator"])]
                    self.assertEqual(src["use"]["product"], self.c["use"]["product"])
                    self.assertIn("từ 10 khách", src["qualifiers"])
        self.s["sources"][0]["use"]["variant"] = "other@2"
        self.ticket = preview(self.s, self.ticket["preview_created_at"])
        self.assertEqual(self.authorize(), "wrong_subject_or_use")

    def test_quick_setup_and_draft_extraction(self):
        fields = dict(company="Sao", product_or_service="Tour", intended_audience="Teachers", goal="Registrations")
        self.assertEqual(next_setup_step(fields, "research_brief", "draft"), "draft_with_gaps")
        self.assertEqual(next_setup_step(fields, "commercial_copy", "extracted"), "request_claim_review")
        self.assertEqual(next_setup_step(fields, "commercial_copy", "human_approved"), "check_current_authority")
        self.assertEqual(next_setup_step({**fields, "goal": ""}, "research_brief", "draft"), "complete_quick_setup")

    def test_fixture_digest_and_source_proof(self):
        self.assertIn(digest(self.s), (HERE / "README.md").read_text(encoding="utf-8"))
        for source in self.s["sources"]:
            self.assertEqual(source["content_digest"], hashlib.sha256(source["excerpt"].encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()
