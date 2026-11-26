"""Cross-check the two signed campaign journeys and the populated browser artifact."""
import argparse
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify(directory, checkout=None, screens=None):
    scopes = []
    totals = {"worker_runs": 0, "model_attempts": 0, "input_tokens": 0, "output_tokens": 0}
    run_ids = set()
    for case, expected in (("acoustic-panel", {"strategy", "landing"}), ("pump-service", {"landing"})):
        folder = directory / case
        journey = read(folder / "journey.json")
        plan, production = journey["plan"], journey["production"]
        scope = plan["scope"]
        scopes.append(scope)
        assert journey["case"] == case and plan["status"] == "approved" and plan["approval"]["receipt"]
        assert production["plan_digest"] == plan["digest"] and production["plan_id"] == plan["id"]
        if checkout:
            assert journey["conditions"]["checkout"] == checkout, "Receipts were created on a different checkout"
        assert {r["kind"] for r in production["runs"]} == expected
        assert {r["id"] for r in production["runs"]} == {r["run_id"] for r in journey["runs"]}
        for run in production["runs"]:
            worker = read(folder / run["kind"] / "worker.json")
            assert worker["run_id"] == run["id"] and run["id"] not in run_ids
            assert worker["state"] == "awaiting_qa" and run["manifest"] == plan["manifests"][run["kind"]]
            run_ids.add(run["id"])
            assert any(a.get("raw_output") and a.get("output_tokens", 0) > 0 for a in worker["attempts"])
            editorial = read(folder / run["kind"] / "editor-review.json")
            attempts = {a["attempt_id"]: a for a in worker["attempts"]}
            for field, trace in editorial["field_history"].items():
                if trace["decision"] == "retained_model_verbatim":
                    attempt = attempts[trace["attempt"]]
                    assert trace["request_sha256"] == attempt["request_sha256"]
                    group, key = field.split(".")
                    assert editorial["groups"][group][key] == trace["after"] == attempt["raw_output"][trace["worker_field"]]
                    assert trace["after"] != trace["control"] and not trace["quality_issues"] and not trace["unresolved"]
            totals["worker_runs"] += 1
            totals["model_attempts"] += len(worker["attempts"])
            for key in ("input_tokens", "output_tokens"):
                totals[key] += worker[key]
        assert len(journey["accepted_editions"]) == len(expected)
        for edition in journey["accepted_editions"]:
            assert edition["snapshot"]["status"] == "approved" and edition["snapshot"]["digest"] == edition["approval_terms"]["expected_content_digest"]
        assert all(a["manifest"] in plan["manifests"].values() and a["plan_id"] == plan["id"] for a in production["assets"])
        if case == "acoustic-panel":
            assert {a["kind"] for a in production["assets"]} == {"strategy", "measurement", "landing", "seo", "creative_brief", "calendar", "social", "ad"}
            state = journey["operating_result"]["state"]
            assert state["synthetic"] and state["business_accepted_units"] == 0 and state["cost_per_business_accepted_vnd"] is None
            assert all(u["scope"] == scope for u in state["work_units"])
            events = state["receipts"]
            assert len({e["id"] for e in events}) == len(events)
            assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
            assert state["report"]["rfqs"] == 2 and state["report"]["confirmed_orders"] == 1
            assert state["proposals"][0]["status"] == "approved"
            if screens:
                sessions = read(screens / "sessions.json")
                assert {s["viewport"][0] for s in sessions} == {390, 820, 1280}
                for session in sessions:
                    assert session["campaign_id"] == scope["campaign_id"] and set(session["run_ids"]) == {r["id"] for r in production["runs"]}
                    for surface in ("workspace", "funnel", "editor"):
                        for suffix in ("", "-dark"):
                            file = screens / f"{surface}-{session['viewport'][0]}{suffix}.png"
                            assert file.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert all(scopes[0][key] != scopes[1][key] for key in ("tenant_id", "client_id", "brand_id", "campaign_id"))
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--checkout")
    parser.add_argument("--screens", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.checkout, args.screens)))
