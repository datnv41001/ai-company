"""Deterministic harness checks. These unit tests do not issue inference receipts."""

from pathlib import Path
import tempfile
import unittest

from pilot import messages, parse_answer
from pilot_archive import public_index, verify_index
from pilot_fixture import COPY, FACTS, digest, encoded, plan, read_catalog, synthetic_pr
from pilot_report import evaluate


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.rows = synthetic_pr()

    def test_git_fixture_and_blast_radius(self):
        again, _ = synthetic_pr()
        self.assertEqual(again, self.manifest)
        self.assertNotEqual(again["head_sha"], again["base_sha"])
        self.assertEqual(again["changed_files"], [COPY])
        self.assertIn(again["head_sha"] + ":" + FACTS, again["blobs"])
        one_scope = [r for r in self.rows if r["domain"] == "offer"]
        jobs = plan(one_scope)
        self.assertEqual(len(jobs), 4)
        self.assertTrue(all(len(scope) == 4 for _, _, scope in jobs))
        self.assertEqual(len({rid for rid, _, _ in plan(self.rows)}), 8)
        self.assertEqual(len({rid for rid, _, _ in plan(self.rows, baseline=True)}), 1)

    def test_blind_context_excludes_answer_key_and_peers(self):
        profile = read_catalog()["MK-022"]
        content = messages(profile, self.rows, "Seal.", [])[1]["content"]
        for inaccessible in ("severity", "changed", "sealed_peer_opinions", "present", "fixture-verifier"):
            self.assertNotIn(inaccessible, content)

    def test_only_evidenced_minority_can_prevail(self):
        unit = self.rows[0]
        clean = self.rows[1]

        def opinion(i, status, line):
            return {
                "assignment_id": "synthetic-test-" + str(i),
                "reviewer_id": "MK-0" + str(21 + i),
                "attempt_id": "unit-test-no-inference-" + str(i),
                "phase": "blind",
                "answer": {
                    unit["id"]: {"status": status, "reason": "test observation", "action": "Use USD 18", "approved_line": line, "copy_line": line},
                    clean["id"]: {"status": "conflict", "reason": "unsupported", "action": "check", "approved_line": clean["line"], "copy_line": clean["line"]},
                },
            }

        group = [opinion(0, "matches", 1), opinion(1, "matches", 1), opinion(2, "conflict", 1)]
        report = evaluate(self.rows, group, self.manifest, "test-fixture")
        self.assertEqual(report["verified_units"], [unit["id"]])
        self.assertEqual(report["dissent"]["minority_overrules"][0]["blind_counts"], {"matches": 2, "conflict": 1})
        group[2] = opinion(2, "conflict", 7)
        self.assertEqual(evaluate(self.rows, group, self.manifest, "test-fixture")["verified_units"], [])

    def test_empty_truncated_result_or_missing_mandate_is_rejected(self):
        for finish, answer in (("length", {}), ("stop", {}), ("stop", {"H01": {"status": "conflict"}})):
            import json

            body = encoded({"choices": [{"finish_reason": finish, "message": {"content": json.dumps(answer)}}]})
            with self.subTest(finish=finish, answer=answer), self.assertRaises(ValueError):
                parse_answer(body, ["H01"])

    def test_measured_archive_portable_replay(self):
        from pilot_archive import assemble, load
        from pilot_fixture import ROOT

        archive = ROOT / "evidence" / "qwen-marketing-01"
        verify_index(archive, "dacc572f1d25c18c491c0c6364111603a2038dab13e8d89df0d6997f147a6167")
        assemble(archive, "400f86483df5c4521ace9c26c5f83975f2e45415d56c8af1a6e684e259948ca9")
        result = load(archive / "results.json")
        self.assertEqual(result["targeted"]["participation"]["actual_calls"], 11)
        self.assertEqual(result["baseline"]["participation"]["actual_calls"], 8)
        self.assertEqual(result["targeted"]["evaluation"]["verified_units"], ["H01", "H04"])
        self.assertEqual(result["targeted"]["evaluation"]["actionability"]["numerator"], 0)
        self.assertEqual(result["targeted"]["evaluation"]["counterevidence_exercise"]["arbiter_opinion"]["status"], "insufficient")

    def test_reviewed_index_detects_different_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for file in ("adapter.json", "trust.json", "source-manifest.json", "results.json", "REPORT.md"):
                (out / file).write_bytes(b"{}\n")
            for mode in ("baseline", "targeted"):
                (out / mode).mkdir()
                for file in ("run.json", "calls.jsonl", "checkpoint.json", "blind-seal.json", "events.json", "normalized.jsonl"):
                    (out / mode / file).write_bytes(b"{}\n")
            index = encoded(public_index(out))
            (out / "index.json").write_bytes(index)
            verify_index(out, digest(index))
            (out / "REPORT.md").write_bytes(b"unexpected decision\n")
            with self.assertRaises(ValueError):
                verify_index(out, digest(index))
