"""Evidence adjudication for the synthetic literal-field fixture only."""

from collections import Counter
from calibration import score
from pilot_fixture import COPY, DISPUTE, FACTS, FAMILY, MODEL, MODEL_VERSION, digest, encoded


def pinpoint(reply, unit):
    return reply["approved_line"] == unit["line"] and reply["copy_line"] == unit["line"]


def choose_dispute(rows, blind):
    # Send the strongest actual disagreement to cross-review (stable tie-break).
    def rank(row):
        opinions = [a["answer"][row["id"]]["status"] for a in blind if row["id"] in a["answer"]]
        counts = Counter(opinions)
        minority = len(opinions) - max(counts.values(), default=0)
        return (-minority, -int("conflict" in counts), row["id"])

    return min(rows, key=rank)


def evaluate(rows, records, manifest, run_id):
    lookup = {u["id"]: u for u in rows}
    judgments = {}
    candidates = []
    for entry in records:
        if entry["phase"] != "blind":
            continue
        for uid, reply in entry["answer"].items():
            row = lookup[uid]
            judgments.setdefault(uid, []).append(
                {"assignment": entry["assignment_id"], "reviewer": entry["reviewer_id"], "status": reply["status"], "note": reply["reason"]}
            )
            if reply["status"] != "conflict":
                continue
            located = pinpoint(reply, row)
            true = row["source"] != row["observed"]
            fix = reply["action"]
            actionable = located and true and row["source"].casefold() in fix.casefold()
            reason = reply["reason"].casefold()
            reversed_roles = true and ("copy value of " + row["source"].casefold()) in reason and ("required value of " + row["observed"].casefold()) in reason
            submitted = []
            visible = {lookup[member]["line"]: lookup[member] for member in entry["answer"]}
            for line_key, path, field in (("approved_line", FACTS, "source"), ("copy_line", COPY, "observed")):
                number = reply[line_key]
                if number in visible:
                    submitted.append(
                        {
                            "id": line_key + "-" + uid,
                            "kind": "pinned_blob",
                            "locator": f"{path}#L{number}",
                            "digest": manifest["blobs"][manifest["head_sha"] + ":" + path]["sha256"],
                            "excerpt_or_observation": visible[number][field],
                            "provenance": "Reference as supplied by model",
                        }
                    )
                else:
                    submitted.append(
                        {
                            "id": line_key + "-" + uid,
                            "kind": "sealed_artifact",
                            "locator": entry["attempt_id"],
                            "digest": digest(encoded(entry["answer"])),
                            "excerpt_or_observation": f"Claimed out-of-scope line {number}",
                            "provenance": "Canonical decoded signed response, citation unresolved",
                        }
                    )
            candidates.append(
                {
                    "unit": uid,
                    "finding_id": entry["assignment_id"] + "-" + uid,
                    "run_id": run_id,
                    "reviewer_id": entry["reviewer_id"],
                    "attempt_id": entry["attempt_id"],
                    "model": MODEL,
                    "model_version": MODEL_VERSION,
                    "family": FAMILY,
                    "base_sha": manifest["base_sha"],
                    "head_sha": manifest["head_sha"],
                    "severity": "P1" if uid in ("H01", "H02", "H03", "H04", "H05") else "P2",
                    "location": (
                        {"side": "head", "path": COPY, "start_line": reply["copy_line"], "end_line": reply["copy_line"]}
                        if reply["copy_line"] in visible
                        else None
                    ),
                    "location_note": None if reply["copy_line"] in visible else "Claimed line is outside assigned scope",
                    "submitted_evidence": submitted,
                    "expected": row["source"],
                    "actual": row["observed"],
                    "business_impact": "Visitors rely on the published " + row["field"] + " when booking.",
                    "evidence": [
                        {
                            "id": kind + "-" + uid,
                            "kind": "pinned_blob",
                            "locator": f"{path}#L{row['line']}",
                            "digest": manifest["blobs"][manifest["head_sha"] + ":" + path]["sha256"],
                            "excerpt_or_observation": row[key],
                            "provenance": "Git blob at submitted head",
                        }
                        for kind, path, key in (("source", FACTS, "source"), ("copy", COPY, "observed"))
                    ],
                    "reproduction": ["Read the two cited values for the same named field at the pinned fixture head."],
                    "proposed_fix": fix,
                    "acceptance_criteria": ["The published " + row["field"] + " equals " + row["source"] + "."],
                    "verification_status": "verified" if located and true else "rejected",
                    "verifier": "fixture-verifier/literal-marketing-fields-v1",
                    "verification_reason": "Pinned fields differ" if located and true else "Incorrect line reference" if not located else "Pinned values agree",
                    "original_model_reason": reply["reason"],
                    "claimed_lines": {"approved": reply["approved_line"], "copy": reply["copy_line"]},
                    "reason_explicitly_reverses_field_roles": reversed_roles,
                    "evidence_valid": located and true,
                    "actionable": actionable,
                    "counterarguments": [],
                    "unresolved_disagreements": [],
                }
            )
    verified = sorted({c["unit"] for c in candidates if c["verification_status"] == "verified"})
    for c in candidates:
        other = [
            a["answer"][c["unit"]]["reason"]
            for a in records
            if a["phase"] != "blind" and c["unit"] in a["answer"] and a["answer"][c["unit"]]["status"] != "conflict"
        ]
        c["counterarguments"] = other
    labels = [
        {"id": u["id"], "present": u["source"] != u["observed"], "severity": ("P1" if u["id"] in ("H01", "H02", "H03", "H04", "H05") else "P2")} for u in rows
    ]
    proposals = sorted({c["unit"] for c in candidates})
    # This synthetic PR has an empty, fixed implementer findings ledger at intake.
    stats = score(labels, proposals, [])
    confirmed = score(labels, verified, [])
    valid_count = sum(c["evidence_valid"] for c in candidates)
    actionable_units = {c["unit"] for c in candidates if c["actionable"]}
    minority = []
    for uid in verified:
        counts = Counter(j["status"] for j in judgments[uid])
        if counts["conflict"] < counts["matches"] and counts["matches"] >= 2:
            minority.append(
                {
                    "unit": uid,
                    "blind_counts": dict(counts),
                    "disposition": "verified",
                    "basis": "At least one candidate cites both correct lines; literal values differ.",
                }
            )
    exercise = None
    if any(a["phase"] == "arbitration" for a in records):
        unit = lookup["H01"]
        cited = [
            p
            for p in DISPUTE
            if p.get("line") == unit["line"]
            and p.get("source_path") == FACTS
            and p.get("copy_path") == COPY
            and p["status"] == ("matches" if unit["source"] == unit["observed"] else "conflict")
        ]
        arbiter = next(a for a in records if a["phase"] == "arbitration")
        exercise = {
            "kind": "authored fixture supplied after blind seal; not additional model opinions",
            "unit": "H01",
            "positions": DISPUTE,
            "admitted_position_ids": [p["id"] for p in cited],
            "observation": [unit["source"], unit["observed"]],
            "arbiter_opinion": arbiter["answer"]["H01"],
            "independent_disposition": "verified" if len(cited) == 1 and cited[0]["status"] == "conflict" else "unresolved",
        }
    return {
        "counterevidence_exercise": exercise,
        "oracle": "deterministic pinned typed marketing fields; no human or AI-adjudicated labels",
        "case_count": len(labels),
        "positive_count": sum(x["present"] for x in labels),
        "judgments": judgments,
        "candidates": candidates,
        "verified_units": verified,
        "missed": [u["id"] for u in labels if u["present"] and u["id"] not in verified],
        "dissent": {"minority_overrules": minority, "cross_and_arbitration": [r for r in records if r["phase"] != "blind"]},
        "raw_candidate_metrics": stats,
        "after_verification_metrics": confirmed,
        "evidence_validity": {
            "numerator": valid_count,
            "denominator": len(candidates),
            "criterion": "Both correct line locators and a binary conflict confirmed by independent lookup. Does not validate model reasoning.",
        },
        "explicit_role_inversions": [c["finding_id"] for c in candidates if c["reason_explicitly_reverses_field_roles"]],
        "duplicate_rate": {"numerator": len(candidates) - len(proposals), "denominator": len(candidates)},
        "actionability": {
            "numerator": len(actionable_units),
            "denominator": len(verified),
            "criterion": "At least one verified proposal names the expected replacement value; criterion and owner in assignment.",
        },
        "cost_per_verified_finding_usd": 0 if verified else None,
        "claim": "insufficient sample for release or independent expertise certification",
    }


def write_report(result):
    scorecard = result["targeted"]["evaluation"]
    baseline = result["baseline"]["evaluation"]

    def metrics(group):
        return " · ".join(f"{k}={group[k]}" for k in ("TP", "FP", "FN", "TN", "critical_detected", "critical_total"))

    def fraction(pair):
        return f"{pair['numerator']}/{pair['denominator']}" if pair["denominator"] else "N/A (0 observations)"

    target = result["targeted"]
    counts = target["participation"]
    candidates = scorecard["candidates"]
    rows = [
        "# AIRC-500 · kết quả pilot Qwen local",
        "## 1. Tóm tắt",
        "Đã chạy pipeline trên cặp Git commit tổng hợp về điều khoản vé và thông tin triển lãm. "
        "Bằng chứng là raw response Qwen, bundle đầu vào, public key và receipt Ed25519.",
        "## 2. Phạm vi",
        f"Base `{result['manifest']['base_sha']}`, head `{result['manifest']['head_sha']}`. "
        "Tám đơn vị gồm bốn lỗi đã gieo và bốn ca sạch. Cùng holdout cho hai cấu hình.",
        "## 3. Người tham gia",
        f"Targeted: {counts['distinct_reviewers']} ID, {counts['assignments']} assignments, "
        f"{counts['actual_calls']} calls, {counts['accepted_receipts']} receipt được chấp nhận, "
        f"{counts['rejected_receipts']} receipt bị từ chối. "
        "Hai người phản biện được phân lại sang miền khác. Tất cả dùng cùng checkpoint Qwen. "
        "Baseline dùng một reviewer, tám lượt mù, cùng phân vùng và giới hạn mẫu với tám lượt mù của targeted.",
        "## 4. Bằng chứng và chi phí",
        f"Targeted sử dụng {counts['input_tokens']} input, {counts['output_tokens']} output, concurrency 1. "
        f"Baseline dùng {result['baseline']['participation']['input_tokens']} input và "
        f"{result['baseline']['participation']['output_tokens']} output. Chi phí API trả phí 0 USD. "
        "Chưa đo điện và giá giờ máy. Tử số/mẫu số evidence validity: " + fraction(scorecard["evidence_validity"]) + ".",
        "## 5. Finding đã xác minh",
        ", ".join(scorecard["verified_units"]) or "Không có.",
        "## 6. Finding bị bác",
        ", ".join(c["finding_id"] for c in candidates if c["verification_status"] == "rejected") or "Không có.",
        "## 7. Bất đồng",
        (
            "Thiểu số đúng được giữ: " + ", ".join(c["unit"] for c in scorecard["dissent"]["minority_overrules"])
            if scorecard["dissent"]["minority_overrules"]
            else "Không ghi nhận ca thiểu số đúng thắng từ hai ý kiến sai trở lên trong lượt này. "
            "Test deterministic riêng kiểm chứng quy tắc; xem raw verdict từng người trong results.json."
        )
        + " Verifier đối chiếu độc lập với hai Git blob, ý kiến trọng tài được lưu cùng mọi phản đối.",
        "Ca phản chứng đưa vào lượt Qwen phân xử thật: hai nhận định biên soạn cho fixture nói giá khớp, "
        "một nhận định trỏ tới hai dòng Git. Đối chiếu USD 18 với USD 12 xác nhận kết luận thiểu số. "
        "Ba lập luận đầu vào này là dữ liệu tổng hợp. Ý kiến Qwen thực về H01: "
        + scorecard["counterevidence_exercise"]["arbiter_opinion"]["status"]
        + ". Disposition của verifier độc lập: "
        + scorecard["counterevidence_exercise"]["independent_disposition"]
        + ".",
        "## 8. Nghiệp vụ",
        "Baseline raw: "
        + metrics(baseline["raw_candidate_metrics"])
        + ". Targeted raw: "
        + metrics(scorecard["raw_candidate_metrics"])
        + ". Sau xác minh: "
        + metrics(scorecard["after_verification_metrics"])
        + ". Duplicate rate: "
        + fraction(scorecard["duplicate_rate"])
        + ". Actionability: "
        + fraction(scorecard["actionability"])
        + ". Mẫu quá nhỏ để kết luận về chất lượng Marketing thực tế.",
        "Các finding khớp vị trí nhưng model đảo giá trị nguồn và bản viết trong lời giải thích: "
        + (", ".join(scorecard["explicit_role_inversions"]) or "chưa phát hiện bằng mẫu từ khóa hẹp")
        + ". Evidence validity ở trên chấm đúng dòng và có chênh lệch thực. Độ chính xác của lời giải thích là phép kiểm riêng.",
        "## 9. Kỹ thuật",
        "Đọc source qua immutable Git blob; mỗi lượt blind nhận context chuyên môn riêng. "
        "Tất cả output blind đã niêm phong trước khi trao đổi. Archive lưu checksum của adapter binary và GGUF.",
        "## 10. Bảo mật",
        "Adapter riêng chỉ nghe loopback, context là dữ liệu fixture tổng hợp, inference không có tool. "
        "Danh tính chứng thực là adapter local. Public key phải so với fingerprint đã duyệt qua kênh tin cậy.",
        "## 11. Release blockers",
        "Thiếu ground truth nghiệp vụ độc lập và cỡ mẫu; commercial GA NO-GO.",
        "## 12. Quyết định",
        "Kết luận cho PR fixture: " + target["decision"] + ". Chỉ đánh giá các field được ghim.",
        "## 13. Đầu việc Codex",
        "Chủ nội dung đối chiếu từng giá trị trong verified_units với nguồn tại head, sửa đúng trường và giữ nguồn đã duyệt.",
        "## 14. Hồi quy",
        "Chạy lại kiểm chữ ký, Git blob, phản chứng thiểu số, giữ ca sạch và chấm lại đầu ra trên một head mới.",
        "## 15. Ưu tiên tiếp theo",
        "Tăng corpus theo domain, khóa holdout kín, phê duyệt ngưỡng trước khi mở rộng 25–50, 100–150 rồi 500 ID. "
        "Thử thêm family model thực sự độc lập. Nguồn hiện tại là fixture engineering deterministic.",
    ]
    return "\n\n".join(rows) + "\n"
