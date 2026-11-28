"""Render the three R70-01 development arms through the released WF-06/1 composer."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app import product_guide_runtime as guide  # noqa: E402
from app.c3_strategy_handoff import brief_release  # noqa: E402
from app.knowledge_contracts import GuideProcedure  # noqa: E402

QUALITY = ROOT / "docs/evaluation/guide-qualification/quality"


def digest(value):
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def released_projection(case):
    """Projection-shaped fixture. No simulated signature, authority or independent QA receipt."""
    intent = {key: case[key] for key in ("purpose", "requirements", "exclusions", "acceptance_criteria")}
    intent.update(buyer_action="catalogue_download", editorial_style="concise")
    projected = dict(locale=case["locale"], product=case["product"], audience=case["audience"], objective=case["purpose"], task_intent=intent)
    brief = brief_release(projected)["fields"]
    steps = GuideProcedure.model_validate({"version": "amc.product-guide-source/1", "steps": case["steps"]}).steps
    wording = " ".join([*steps, *case["qualifiers"]])
    order = {
        "message": wording,
        "audience": case["audience"],
        "placement": "web",
        "objective": case["purpose"],
        "brief": brief,
        "guidance": {"situation": "At a work or shift handover."},
    }
    return {
        "product": "Hướng dẫn sử dụng" if case["locale"] == "vi-VN" else "Product use guide",
        "locale": case["locale"],
        "objective": case["purpose"],
        "audience": case["audience"],
        "channel": "web",
        "order": order,
        "task_intent": {**brief, "deliverable_type": "web_use_guide"},
        "procedure": {"source": "P1", "steps": steps, "limitations": case["qualifiers"], "wording": wording},
    }


def render_arm(arm, selection, case, projection):
    if arm == "controlled_model":
        sources = {"P1": {"excerpt": projection["order"]["message"]}}
        selection = guide.validate(selection, "content", [], sources, {"workflow": guide.RELEASE})["sections"]
    edition = guide.compose(projection, selection)
    page = guide.preview(edition)
    lines = page["body"].splitlines()
    numbered = [f"{i}. {step}" for i, step in enumerate(case["steps"], 1)]
    checklist = ["☐ " + step for step in case["steps"]]
    markers = numbered if selection["layout"] == "numbered" else checklist
    first = lines.index(markers[0]) if markers[0] in lines else -1
    faithful_lines = first >= 0 and lines[first : first + len(markers)] == markers
    checks = {
        "exact_step_lines_in_source_order": edition["steps"] == case["steps"] and faithful_lines,
        "exact_qualifiers_visible": edition["limitations"] == case["qualifiers"] and all(q in lines for q in case["qualifiers"]),
        "complete_wording_preserved": edition["wording"] == projection["order"]["message"],
        "approved_cta_visible": bool(edition["cta"]) and lines[-1] == edition["cta"] == projection["order"]["brief"]["cta"],
        "visible_format_meets_explicit_requirement": faithful_lines and (case["procedure_kind"] == "independent" or markers == numbered),
    }
    return {
        "arm": arm,
        "selection": selection,
        "page": page,
        "page_sha256": digest(page),
        "checks": checks,
        "status_at_generation": edition["qa_status_at_generation"],
        "source_map": edition["source_map"],
    }


def compare():
    results = []
    for case in json.loads((QUALITY / "cases.json").read_text(encoding="utf-8")):
        projection = released_projection(case)
        selections = {
            "deterministic": {"heading": "product", "layout": "numbered"},
            "editor_fixture": case["editor_choice"],
            "controlled_model": case["controlled_model_reply"],
        }
        arms = [render_arm(arm, selection, case, projection) for arm, selection in selections.items()]
        results.append(
            {
                "case_id": case["case_id"],
                "locale": case["locale"],
                "case_sha256": digest(case),
                "projection_sha256": digest(projection),
                "brief": projection["order"]["brief"],
                "arms": arms,
            }
        )
    return {
        "workflow": guide.RELEASE,
        "content_contract": guide.schema("content"),
        "model_invocations": 0,
        "observed_practitioners": 0,
        "inference_usage": None,
        "inference_latency": None,
        "cases": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    dest = parser.parse_args().output
    with dest.open("w", encoding="utf-8", newline="\n") as out:
        json.dump(compare(), out, ensure_ascii=False, indent=2)
        out.write("\n")
