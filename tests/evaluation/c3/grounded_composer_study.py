"""Recompose pinned synthetic v2 receipts offline. This experiment issues no QA approvals."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

from buyer_journey_playbooks import journey_for
from product_qualification_summary import FROZEN, ROOT, WF, digest, plan, read, require
from structured_fact_audit import audit_surface, expected_facts


CHECKOUT = "a2dbe4566415fe28226b014ffb8785a1cc2cd9d6"
VERSION = "buyer-journey-composer/1"
FIELD_TYPES = {
    "research": {"buyer_problem": "research_question", "research_question": "research_question",
                 "evidence": "source_declarations", "hypothesis": "hypothesis"},
    "strategy": {"positioning": "recommendation", "channel_choice": "recommendation",
                 "rationale": "recommendation", "execution": "experiment_design"},
    "measurement": {"test_hypothesis": "hypothesis", "measurable_action": "approved_action",
                    "measurement_method": "measurement_proposal"},
    "copy": {"headline": "brief_identity", "value_proposition": "buyer_guidance",
             "benefit": "source_declaration", "commercial_terms": "source_declarations", "call_to_action": "approved_action"},
    "seo": {"page_title": "brief_identity", "meta_description": "source_and_buyer_guidance", "search_intent": "hypothesis"},
}


def flat(groups):
    return {group + "." + key: value for group, fields in groups.items() for key, value in fields.items()}


def compose(case, receipt):
    """Authoring-only projection. The caller authenticates the synthetic source receipt first."""
    intent = receipt["task_intent"]
    require(intent["locale"] == "vi-VN" and all(intent[k] == case[k] for k in
            ("buyer_action", "locale", "audience", "channel", "region", "product")), "Task origin mismatch")
    original = receipt["deterministic"]["groups"]
    candidate = deepcopy(original)
    wf = case["workflow"]
    require(receipt["workflow"] == WF[wf], "Unreviewed workflow version")
    expected = ("research", "strategy", "measurement") if wf == "WF-03" else ("copy", "seo")
    require(set(original) == set(expected) and all(original[g].keys() == FIELD_TYPES[g].keys() for g in expected),
            "Field contract changed; review required")
    protected = original["research"]["evidence"] if wf == "WF-03" else original["copy"]["commercial_terms"]
    material, price = case["facts"]
    declaration = material["wording"] + " " + material["qualifiers"]
    require(declaration in protected.splitlines() and price.get("price"), "Missing scoped material or price declaration")
    journey = journey_for(intent["buyer_action"], price["price"]["unit"])
    product, audience, channel, region = (intent[k] for k in ("product", "audience", "channel", "region"))
    correction = None
    if wf == "WF-03":
        candidate["research"].update(
            buyer_problem=f"Khi cân nhắc {product}, {audience} gặp vướng mắc nào khi cần {journey.decision}?",
            research_question=f"Hỏi về lần chọn mua gần nhất: khi nào anh/chị cần {journey.decision}, "
                              "đã dựa vào tài liệu nào và còn phải hỏi lại ai?",
            hypothesis=f"Giả thuyết cần thử: {journey.comparison} giúp người đọc chọn bước tiếp theo.",
        )
        candidate["strategy"].update(
            positioning=f"Đề xuất giới thiệu {product} cho {audience} theo nhu cầu {journey.decision}. "
                        "Đặt điều kiện áp dụng cạnh thông tin sản phẩm.",
            channel_choice=channel,
            rationale=f"Trên {channel}, thử {journey.comparison} trước khi dẫn tới hành động. "
                      f"Chuyển kết quả cho {journey.recipient} đối soát.",
            execution=f"Giữ nguyên sản phẩm và điều kiện cho hai nhóm. Bản A trình bày thông tin như hiện tại. "
                      f"Bản B thêm {journey.comparison}. Gắn mã biến thể vào sự kiện rồi kiểm tra khả năng truy về phiên.",
        )
        candidate["measurement"].update(
            test_hypothesis=f"Kiểm tra xem bản B có nhiều {journey.event} hơn trên mỗi phiên đủ điều kiện so với A hay không.",
            measurement_method=f"Trong {case['kpi_window']}, chia số {journey.event} duy nhất cho số phiên đủ điều kiện "
                               f"của từng biến thể. Nhờ {journey.recipient} {journey.reconciliation}. "
                               "Ghi riêng sự kiện thiếu nguồn trước khi diễn giải kết quả.",
        )
    else:
        # One bounded correction for the factual benefit slot. A valid handle alone does not verify a paraphrase.
        model = receipt.get("composed", {}).get("groups", {}).get("copy", {})
        benefit = model.get("benefit", original["copy"]["benefit"])
        if benefit != declaration:
            correction = {"field": "copy.benefit", "attempts": 1, "reason": "scoped_declaration_required",
                          "original": benefit, "replacement_source": material["id"]}
            benefit = declaration
        require(benefit == declaration, "Correction failed; retain staff draft")
        candidate["copy"].update(
            headline=product,
            value_proposition=f"Bạn cần {journey.decision} cho {product}? {journey.prompt}",
            benefit=benefit,
        )
        candidate["seo"].update(
            page_title=f"{product} tại {region} | {original['copy']['call_to_action']}",
            meta_description=f"{declaration} {journey.prompt}",
            search_intent=f"Giả thuyết: người tìm {product} tại {region} muốn {journey.decision}.",
        )
    require(flat(candidate).keys() == flat(original).keys() and all(v.strip() for v in flat(candidate).values()),
            "Missing candidate field")
    return {
        "groups": candidate, "field_types": {k: FIELD_TYPES[k] for k in expected}, "correction": correction,
        "protected_field": "research.evidence" if wf == "WF-03" else "copy.commercial_terms",
        "protected_sha256": hashlib.sha256(protected.encode()).hexdigest(),
        "source_bindings": {f["id"]: {"wording": f["wording"], "qualifiers": f["qualifiers"]} for f in case["facts"]},
        "action": {"code": intent["buyer_action"], "buyer_step": journey.prompt, "event": journey.event,
                   "receiving_team": journey.recipient, "reconciliation": journey.reconciliation},
        "scope": "staff-only synthetic candidate; all user-facing uses require current source authorization and QA",
    }


def compare_groups(before, after):
    old, new = flat(before), flat(after)
    return {"before_fields": len(old), "after_fields": len(new),
            "changed": sorted(key for key in old.keys() & new.keys() if old[key] != new[key]),
            "removed": sorted(old.keys() - new), "empty": sorted(key for key in new if not new[key].strip())}


def evaluate(folder, root=ROOT):
    assignments, fixture_sha = plan(root, "study")
    cases = read(root / "tests/evaluation/c3/qualification-v2.json")["cases"]
    require(fixture_sha == FROZEN, "Unpinned study")
    observations = json.loads(gzip.decompress((root / "docs/evaluation/c3-product-v2/OBSERVATIONS.json.gz").read_bytes()))
    pins = observations["commercial"]["study"]["cases"]
    history = observations["qualification"]["series"]["study"]["cases"]
    rows = []
    for case in cases:
        cid = case["id"]
        blob = (folder / cid / "result.json").read_bytes()
        sha = hashlib.sha256(blob).hexdigest()
        require(sha == pins[cid]["result_file_sha256"], "Unrecognized result bytes: " + cid)
        record = json.loads(blob)
        require((record["case"], record["checkout"], record["cases_sha256"], record["run_id"], record["workflow"]) ==
                (cid, CHECKOUT, fixture_sha, history[cid]["run"], WF[assignments[cid]]), "Receipt origin mismatch")
        candidate = compose(case, record)
        terms = flat(candidate["groups"])[candidate["protected_field"]]
        # The scorer matches the frozen SKU's two declarations. No runtime handle is inferred for a failed run.
        checked = audit_surface(terms, expected_facts(case, None), {}, case["locale"])
        statuses = Counter(item["status"] for fact in checked["facts"].values() for item in fact["checks"].values())
        candidate["protected_term_checks"] = dict(statuses)
        candidate["needs_commercial_reconciliation"] = bool(set(statuses) - {"matched"} or checked["additional_commercial_text_for_review"])
        before = record["deterministic"]["groups"]
        model = record.get("composed", {}).get("groups")
        base_comp = compare_groups(before, candidate["groups"])
        model_comp = compare_groups(model, candidate["groups"]) if model else None
        rows.append({
            "case": cid, "workflow": record["workflow"], "source_sha256": sha, "run": record["run_id"],
            "projection_digest": record["projection_digest"], "historical_state": record["state"],
            "historical_model_attempt_count": len(record["attempts"]), "historical_model_failure": record["last_error"],
            "original_groups": {"deterministic": before, "model_assisted": model},
            "baseline_digest": digest(before), "model_assisted_digest": digest(model) if model else None,
            "baseline_comparison": base_comp, "model_assisted_comparison": model_comp, "candidate": candidate,
        })
    return {
        "contract": VERSION, "source_checkout": CHECKOUT, "synthetic_fixture_digest": fixture_sha,
        "assigned": len(assignments), "offline_candidates": len(rows),
        "historical_states": dict(Counter(row["historical_state"] for row in rows)), "rows": rows,
        "historical_model_pairs": sum(row["model_assisted_comparison"] is not None for row in rows),
        "bounded_field_corrections": sum(bool(row["candidate"]["correction"]) for row in rows),
        "new_model_invocations": 0, "new_provider_fees": 0, "human_acceptance": None, "commercial_qa": "not_run",
        "manual_baseline_minutes": None, "clarification_minutes": None, "editing_minutes": None,
        "qa_minutes": None, "cost_per_accepted_unit": None,
    }


def save_study(folder, out, root=ROOT):
    path = out.resolve()
    require(not path.is_relative_to(folder.resolve()) and not path.is_relative_to((root / "docs/evaluation/c3-product-v2").resolve()),
            "Refusing to overwrite historical evidence")
    report = evaluate(folder, root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", type=Path, help="Original c3-product-v2 directory from run 45582688602")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    save_study(args.receipts, args.out)
