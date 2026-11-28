"""Issue a guide QA approval with the pinned #70 binary, then read and replay it with this checkout."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

CANDIDATE = Path(__file__).resolve().parents[1]
REVIEWED_TREE = "85a92d483ce84c72b243b1f49b7579f3ea737258"


def git(root, *args):
    return subprocess.check_output(["git", "-c", "safe.directory=" + root.as_posix(), *args], cwd=root, text=True).strip()


def receipt_proof(observer, manifest, document):
    # Compare the entire committed rows. Only publish IDs and digests; SELECT cannot alter signoff.
    rows = observer.execute(
        """SELECT id,request_digest,result,to_jsonb(q)::text FROM knowledge_commands q
           WHERE snapshot_id=%s AND operation='c3_qa'""",
        (manifest,),
    ).fetchall()
    assert len(rows) == 1
    rid, request_digest, result, serialized = rows[0]
    assert result["document_id"] == document and "guide_review" not in result
    doc = observer.execute("SELECT status, to_jsonb(d)::text FROM deliverables d WHERE id=%s", (document,)).fetchone()
    assert doc[0] == "approved"
    return {
        "qa_receipt_id": rid,
        "request_digest": request_digest,
        "content_digest": result["content_digest"],
        "qa_revision": result["qa_revision"],
        "release_digest": result["release_digest"],
        "guide_digest": result["guide_digest"],
        "complete_receipt_row_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
        "complete_document_row_sha256": hashlib.sha256(doc[1].encode()).hexdigest(),
    }


def use_checkout(root):
    sys.path[:0] = [str(root), str(root / "tests")]
    from app import product_guide_studio
    from product_guide_fixtures import guide_case
    from migrations.runtime_bundle import source_fingerprint

    assert Path(product_guide_studio.__file__).resolve() == root / "app/product_guide_studio.py"
    assert Path(sys.modules[guide_case.__module__].__file__).resolve() == root / "tests/product_guide_fixtures.py"
    return source_fingerprint()


def candidate(report_path):
    candidate_sources = use_checkout(CANDIDATE)
    from agency_fixtures import postgres_api
    from knowledge_fixtures import accepted
    from product_guide_fixtures import order_assessment

    seed = json.load(sys.stdin)
    # Fingerprint/registry refresh is an ordinary migration publisher on the same synthetic DB.
    subprocess.run([sys.executable, "-m", "migrations.apply"], cwd=CANDIDATE, check=True)
    doc, reviewer, editor = seed["doc_url"], seed["reviewer"], seed["editor"]
    old = seed["proof"]
    with postgres_api() as api, psycopg.connect(os.environ["AMC_MIGRATION_DSN"], autocommit=True) as observer:
        observer.execute("SET default_transaction_read_only=on")
        after_publish = receipt_proof(observer, seed["manifest"], seed["document"])
        assert old == after_publish
        for reader in (editor, reviewer):
            view = accepted(api.get(doc + "/studio/product-guide", headers=reader))
            assert view["status"] == "approved" and view["qa_receipt"] == old["qa_receipt_id"]
            assert view["guide_review"] is None and view["order_review_receipt"] is None
            assert (view["revision"], view["content_digest"]) == (old["qa_revision"], old["content_digest"])
        replay = api.post(doc + "/review", headers=reviewer, json=seed["decision"])
        returned = accepted(replay)
        assert (returned["qa_approved_revision"], returned["qa_approved_digest"]) == (old["qa_revision"], old["content_digest"])
        alteration = api.post(doc + "/review", headers=reviewer, json=seed["decision"] | {"guide_review": order_assessment(view, "ordered")})
        assert alteration.status_code == 409
        final = receipt_proof(observer, seed["manifest"], seed["document"])
        assert old == final
        proof = {
            "writer_head": seed["writer_head"],
            "writer_tree": REVIEWED_TREE,
            "writer_runtime_sources": seed["writer_sources"],
            "reader_runtime_sources": candidate_sources,
            "postgres_version_num": observer.info.server_version,
            "run": seed["run"],
            "guide_document": seed["document"],
            "guide_manifest": seed["manifest"],
            "issuer": "PR70 signed HTTP API, assigned editor submits, separate signer approves",
            "before_cutover": old,
            "after_candidate_publish_read_replay_and_refusal": final,
            "reader_checks": {
                "assigned_editor_and_signer_saw_original_approval": True,
                "historical_itemized_assessment": None,
                "historical_itemized_assessment_receipt": None,
                "identical_decision_http": replay.status_code,
                "attempt_to_add_assessment_http": alteration.status_code,
                "qa_receipts_on_manifest": 1,
            },
            "worker_output": "controlled fixture",
            "service_inference_calls": 0,
        }
    report_path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")


def run(previous, report_path):
    assert git(previous, "rev-parse", "HEAD^{tree}") == REVIEWED_TREE
    inputs = ["app", "migrations", "catalog", "tests", "requirements.txt", "requirements-registry.txt"]
    assert not git(previous, "status", "--porcelain", "--", *inputs)
    old_sources = use_checkout(previous)
    from agency_fixtures import postgres_api
    from knowledge_fixtures import accepted
    from product_guide_fixtures import activate_guide, advance_guide, guide_case
    from test_product_guide_studio import version

    with postgres_api() as api, guide_case(api) as ctx:
        activate_guide(api, ctx)
        editor, reviewer = (ctx[role]["headers"] for role in ("recipient", "reviewer"))
        task = accepted(api.post(ctx["start_guide"], headers=editor, json=ctx["guide_request"]))
        advance_guide(ctx)
        guide_run = accepted(api.get(ctx["base"] + "/workforce/runs/" + task["run_id"], headers=editor))
        did = guide_run["deliverable_id"]
        doc = ctx["base"] + "/deliverables/" + did
        draft = accepted(api.get(doc + "/studio/product-guide", headers=reviewer))
        step = draft["guide"]["steps"][0]
        changed = accepted(
            api.patch(
                doc + "/studio/product-guide",
                headers=editor,
                json=version(draft)
                | {
                    "layout": "numbered",
                    "heading": "source",
                    "custom_title": step,
                },
            )
        )
        assert changed["revision"] == draft["revision"] + 1
        accepted(api.post(doc + "/submit", headers=editor, json=version(changed)))
        decision = version(changed) | {"decision": "approved", "note": "Reviewed the current authorized guide and source."}
        accepted(api.post(doc + "/review", headers=reviewer, json=decision))
        historical = accepted(api.get(doc + "/studio/product-guide", headers=reviewer))
        before = receipt_proof(ctx["lab"].owner, task["manifest_id"], did)
        assert historical["qa_receipt"] == before["qa_receipt_id"]
        # Transfer only between two local test processes over stdin. Credentials never enter the receipt or CLI arguments.
        seed = {
            "writer_head": git(previous, "rev-parse", "HEAD"),
            "writer_sources": old_sources,
            "doc_url": doc,
            "document": did,
            "manifest": task["manifest_id"],
            "run": task["run_id"],
            "editor": editor,
            "reviewer": reviewer,
            "decision": decision,
            "proof": before,
        }
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--read-candidate", "--report", str(report_path)],
            cwd=CANDIDATE,
            check=True,
            input=json.dumps(seed),
            text=True,
            timeout=90,
            env=os.environ | {"PYTHONPATH": str(CANDIDATE), "PYTHONDONTWRITEBYTECODE": "1"},
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    phases = parser.add_mutually_exclusive_group(required=True)
    phases.add_argument("--previous-checkout", type=Path, help="Clean #70 checkout pointing to the reviewed tree")
    phases.add_argument("--read-candidate", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    params = conninfo_to_dict(os.environ["AMC_MIGRATION_DSN"])
    assert os.environ.get("AMC_TEST_PG") == "1" and params["host"] in {"localhost", "127.0.0.1", "::1"} and params["dbname"].startswith("amc_test")
    if args.read_candidate:
        candidate(args.report.resolve())
    else:
        run(args.previous_checkout.resolve(), args.report.resolve())
        print("PASS: PR #70 approval remains unchanged through candidate publisher, read, replay and refusal.")
