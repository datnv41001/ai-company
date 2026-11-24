"""Validate synthetic message shapes only. No signature or inference is produced."""
import json
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / "contracts.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def fixtures():
    digest = "f" * 64
    stamp = "2026-11-24T00:00:00Z"
    run = dict(run_id="fixture-only", base_sha="a" * 40, head_sha="b" * 40)
    actor = dict(**run, reviewer_id="MK-022")
    model = dict(model="synthetic-test", model_version="fixture-version", family="fixture")
    ev = dict(id="ev", kind="pinned_blob", locator="fixture.txt", digest=digest,
              excerpt_or_observation="Only a replica is touchable.", provenance="synthetic source")
    return {
        "run": dict(type="run.v1", **run, repository="fixture/repo", pr_number=1,
                    merge_base=run["base_sha"], integration_sha=None, catalog_digest=digest,
                    policy_digest=digest, source_manifest_digest=digest, dependency_map_digest=digest,
                    mode="targeted", risk="medium", implementer_principals=["writer"],
                    budget=dict(max_concurrency=2, max_tokens=88000, max_cost_microusd=0,
                                deadline_utc=stamp, attempt_timeout_seconds=90, max_retries=1,
                                max_debate_rounds=2, paid_approval_id=None, tariff_digest=None)),
        "assignment": dict(type="assignment.v1", **actor, assignment_id="assignment",
                           principal="reader", phase="blind", round=0, topic="claims",
                           reason="copy changed", context_digest=digest, tool_grant_digest=digest,
                           output_contract="review.v1", artifact_kind="claim_source_pairs",
                           token_reservation=4000, cost_reservation_microusd=0),
        "receipt": dict(type="receipt.v1", **actor, **model, assignment_id="assignment",
                        attempt_id="attempt", phase="blind", round=0, context_digest=digest,
                        started_utc=stamp, ended_utc=stamp, outcome="completed", output_digest=digest,
                        usage_known=True, input_tokens=5, output_tokens=3, cost_microusd=0,
                        adapter_identity="fixture", provider_request_or_local_execution_id="fixture",
                        signature="synthetic placeholder for shape tests"),
        "finding": dict(type="finding.v1", **actor, **model, attempt_id="attempt", finding_id="F",
                        severity="P1", location=None, location_note="Synthetic marketing copy",
                        expected="Describe a replica", actual="Copy describes the original",
                        business_impact="Misleading visitor expectation", reproduction=None,
                        evidence=[ev], proposed_fix="Name the replica",
                        acceptance_criteria=["Subject matches source"], verification_status="candidate",
                        counterarguments=[], unresolved_disagreements=[]),
        "review": dict(type="review.v1", **actor, assignment_id="assignment", attempt_id="attempt",
                       phase="blind", artifact_kind="claim_source_pairs",
                       proof_observation="Subject changed", scope_reviewed=["copy"],
                       gaps=[], finding_ids=["F"], evidence=[ev]),
        "exchange": dict(type="exchange.v1", **dict(actor, reviewer_id="MK-025"),
                         attempt_id="peer-attempt", message_id="M", target_finding_id="F",
                         round=1, kind="request_evidence", reason="Confirm subject",
                         evidence=[], supersedes=None),
        "arbitration": dict(type="arbitration.v1", **dict(actor, reviewer_id="AR-002"),
                            attempt_id="referee-attempt", finding_ids=["F"],
                            competing_positions=["Reference means replica", "Reference means original"],
                            artifact_kind="evidence_ruling", proof_observation="Source names replica",
                            evidence=[ev], disposition="verified", reason="Subject differs",
                            remaining_dissent=[], owner="copy editor", next_observation=None),
        "checkpoint": dict(type="checkpoint.v1", **run, sequence=1, previous_digest=None,
                           event_root=digest, reservation_root=digest, blind_seal_digest=None,
                           cancelled=False),
    }


class WireTests(unittest.TestCase):
    def test_schema_and_record_examples(self):
        Draft202012Validator.check_schema(SCHEMA)
        for kind, sample in fixtures().items():
            with self.subTest(kind=kind):
                VALIDATOR.validate(sample)

    def test_incomplete_or_malformed_records(self):
        changes = [
            ("run", "head_sha", "short"),
            ("finding", "verification_status", "majority_approved"),
            ("finding", "evidence", []),
            ("finding", "location_note", None),
            ("arbitration", "reviewer_id", "MK-022"),
            ("receipt", "output_digest", None),
            ("receipt", "usage_known", False),
            ("receipt", "input_tokens", None),
            ("exchange", "round", 0),
            ("checkpoint", "sequence", -1),
        ]
        for kind, key, value in changes:
            with self.subTest(kind=kind, key=key):
                record = deepcopy(fixtures()[kind])
                record[key] = value
                self.assertFalse(VALIDATOR.is_valid(record))

    def test_policy_limits_and_extra_authority(self):
        for key, value in (("max_retries", 2), ("max_debate_rounds", 3),
                           ("max_cost_microusd", -1), ("max_concurrency", 0)):
            with self.subTest(key=key):
                record = fixtures()["run"]
                record["budget"][key] = value
                self.assertFalse(VALIDATOR.is_valid(record))
        review = fixtures()["review"]
        review["can_merge"] = True
        self.assertFalse(VALIDATOR.is_valid(review))

    def test_full_mode_coverage_without_a_finding(self):
        record = fixtures()["arbitration"]
        record.update(finding_ids=[], competing_positions=["Coverage sufficient"],
                      reason="No gaps in the assigned fixture", disposition="verified")
        VALIDATOR.validate(record)
