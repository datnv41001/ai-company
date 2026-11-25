"""Offline replay of the reviewed v4 package, using pins outside its evidence directory."""

import argparse
import json

from local_adapter import file_digest
from public_research import ROOT, dump
from research_assessment import scoring
from research_study import SNAPS, replay

ENROLLMENT = "0ad84af4a344e25a1b493835f3072dc1f3e55f0d8a9b6b32b195378bb6cc4fba"
ARCHIVE = "90821852eb36d40e2ae9c96def75dd2dc0d086fe383e0279aaebba04f65d6503"
GRADES = "42593a7167d970ba0fb15fa1a8aa32d13afa182a3d55d2572e18467ba3ae2b2f"
LABELS = {
    "verdict_correct": "Đúng verdict (flag, keep, insufficient)",
    "relevant_source_choice": "Chọn đúng họ nguồn từ bibliography",
    "source_in_context": "Chọn nguồn đúng thực sự có trong context",
    "literal_repair_match": "Khớp nguyên văn mẫu sửa",
    "scope_reason_valid": "Lý do đúng phạm vi (chấm mù)",
    "attribution_valid": "Quy kết nguồn hợp lệ (chấm mù)",
    "recommendation_useful": "Khuyến nghị có thể dùng trong ca (chấm mù)",
}
CAPS = {
    "marketing_reasoning": "Lập luận Marketing",
    "source_attribution": "Quy kết đúng nguồn",
    "semantic_contradiction": "Claim sai hoặc khẳng định thiếu căn cứ",
    "product_scope": "Phạm vi tính năng sản phẩm",
    "actionable_repairs": "Hành động hữu ích cho claim sai",
    "code_logic": "Logic mã nguồn",
    "security_and_regression": "Phân tích bảo mật và hồi quy",
}


def report(res):
    a, b = res["arms"]["without"], res["arms"]["with"]
    lines = [
        "# Holdout năng lực Marketing với nguồn công khai · v4",
        "",
        "Mười ca mới, một reviewer MK-022, Qwen2.5-1.5B-Instruct Q4_K_M chạy native trên Windows. Một agent khác tác giả bộ ca gán nhãn độc lập trước inference. Cùng agent này chấm 20 câu trả lời tự do sau khi đã ẩn arm và điểm số. Đây là đối chiếu do AI thực hiện, chưa có người chấm nghiệp vụ độc lập.",
        "",
        "| Chỉ số | Chỉ có bibliography | Có thêm packet | Gain / loss theo ca |",
        "|---|---:|---:|---|",
    ]

    def ids(seq):
        return ", ".join(seq) or "∅"

    for key, label in LABELS.items():
        pair = res["paired"][key]
        lines.append(f"| {label} | {a['exact'][key]}/10 | {b['exact'][key]}/10 | {ids(pair['gain'])} / {ids(pair['loss'])} |")
    lines += [
        "",
        f"Trong bốn claim phải flag, arm đối chứng phát hiện {len(a['correct_findings'])}/4 ({ids(a['correct_findings'])}); arm có packet phát hiện {len(b['correct_findings'])}/4 ({ids(b['correct_findings'])}). Cờ sai lần lượt là {len(a['false_findings'])} và {len(b['false_findings'])}. Các claim được flag đúng đồng thời có đề xuất hữu ích lần lượt là {ids(a['useful_correct_findings'])} và {ids(b['useful_correct_findings'])}.",
        "",
        "| Năng lực trong arm có packet | Ca có verdict đúng và đạt tiêu chí / đã đo | Kết luận |",
        "|---|---:|---|",
    ]
    for name, row in res["qualification"].items():
        lines.append(f"| {CAPS[name]} | {row['correct']}/{row['measured']} | " + ("Chưa đo" if not row["measured"] else "Mẫu nhỏ") + " |")
    lines += ["", "| Arm | Call đã ký | Input token | Output token | Chi phí provider |", "|---|---:|---:|---:|---:|"]
    for arm, data in res["arms"].items():
        lines.append(f"| {arm} | {data['calls']} | {data['input_tokens']} | {data['output_tokens']} | 0 |")
    lines += ["", "Các nguồn thực sự truy xuất được và giới hạn của chúng:", ""]
    for s in SNAPS:
        snap = json.loads(s.read_bytes())
        for o in snap["observations"]:
            lines.append(f"- {o['id']} · {o['quality']}. {o['limitations']} [{o['publisher']}]({o['url']})")
        for gap in snap["gaps"]:
            lines.append(f"- Gap {gap['source']} · {gap['reason']}.")
    lines += [
        "",
        "Hai ca L5/L6 về thị trường không nhận trích đoạn ở cả hai arm. Prompt chấm giữ nguyên. ID nguồn trên bibliography có thể được chọn kể cả khi chưa đọc trang. Điểm quy kết được chấm theo lời giải thích và phạm vi nguồn. Không cộng một citation chưa truy xuất vào độ phủ nguồn.",
        "",
        "Tần suất phát hiện và khuyến nghị hữu ích là số liệu mô tả trên những ca này. Cùng một model và một seed, hai ca tương quan trong từng call. Mức tăng hoặc giảm trên một cặp không xác lập hiệu quả ngoài holdout. Chưa có căn cứ để mở rộng số reviewer, bật review source thực hay thay đổi commercial GA.",
        "",
        "[Kết quả từng ca và ma trận nhầm lẫn](results.json) · [Nhãn trước inference](independent-labels.json) · [Phiếu chấm prose đã làm mù](semantic-grades.json) · [Hướng dẫn sử dụng và các gate](../PUBLIC-RESEARCH.md).",
        "",
        f"Enrollment SHA-256 `{ENROLLMENT}`. Archive SHA-256 `{ARCHIVE}`. Semantic grades SHA-256 `{GRADES}`.",
        "",
    ]
    return "\n".join(lines)


def checked(root=ROOT):
    out = root / "evidence"
    gradefile = root / "semantic-grades.json"
    if file_digest(out / "q15.json.gz") != ARCHIVE or file_digest(gradefile) != GRADES:
        raise ValueError("Snapshot of signed outputs or frozen semantic grading differs")
    return scoring(replay(out, ENROLLMENT), json.loads(gradefile.read_bytes()))


def verify():
    result = checked()
    if json.loads((ROOT / "results.json").read_bytes()) != result or (ROOT / "REPORT.md").read_text(encoding="utf8") != report(result):
        raise ValueError("Published report differs from evidence replay")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--render", action="store_true", help="Regenerate results and report from independently pinned inputs")
    args = p.parse_args()
    if args.render:
        result = checked()
        dump(ROOT / "results.json", result)
        (ROOT / "REPORT.md").write_text(report(result), encoding="utf8", newline="\n")
    else:
        result = verify()
        print(json.dumps({"calls": result["calls"], "arms": result["arms"], "qualification": result["qualification"]}, indent=2))
