"""Render the measured comparison from replayed public metrics. No model calls."""

import argparse
from pathlib import Path

from pilot_fixture import MODEL_DIGEST, MODEL_VERSION, digest
from quality_corpus import SEEDS
from quality_run import read

ARMS = {
    "deterministic_only": "Verifier",
    "one_reviewer": "Một reviewer, hai lượt",
    "independent_reviewers": "Hai reviewer độc lập",
    "one_plus_verifier": "Một reviewer + verifier",
    "council_with_debate": "Hội đồng + verifier",
}
STAGES = {"blind": "Mù", "cross": "Phản biện", "arbitration": "Trọng tài", "verified_final": "Xác minh cuối"}


def pct(measure):
    return "—" if measure["rate"] is None else f"{measure['rate'] * 100:.1f}%"


def ratio(measure):
    return f"{measure['hits']}/{measure['total']}"


def interval(measure):
    bounds = measure["interval_95"]
    return "—" if bounds is None else f"{100 * bounds[0]:.1f}–{100 * bounds[1]:.1f}%"


def section(root, cohort, title):
    path = root / cohort
    metrics = read(path / "metrics.json")
    fixture = metrics["fixture"]
    ids = set()
    totals = {"accepted_receipts": 0, "input_tokens": 0, "output_tokens": 0, "settled_microusd": 0}
    for row in metrics["seeds"].values():
        participation = row["participation"]
        ids.update(participation["distinct_reviewers"])
        for k in totals:
            totals[k] += participation[k]

    lines = [
        f"## {title}",
        "",
        f"Git fixture `{fixture['base_sha']}` → `{fixture['head_sha']}`. "
        f"Hai seed dùng {len(ids)} ID thực sự nhận receipt ({', '.join(sorted(ids))}), "
        f"{totals['accepted_receipts']} lượt ký hợp lệ, {totals['input_tokens']:,} token đầu vào và "
        f"{totals['output_tokens']:,} token đầu ra. Chi phí API trả ngoài bằng {totals['settled_microusd']} µUSD.",
        "",
        f"[Số liệu đầy đủ]({cohort}/metrics.json) · [Lịch sử từng finding và domain]({cohort}/trace.json.gz) · "
        f"[Journal seed 17]({cohort}/seed-17.json.gz) · [Journal seed 43]({cohort}/seed-43.json.gz)",
        "",
        "| Seed | Cấu hình | TP / FP / FN / TN | Precision | Recall | FPR | Giải thích đúng / TP | Hướng sửa đúng / TP | Lượt | Input / output token | Tổng giây gọi model |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for seed in SEEDS:
        row = metrics["seeds"][str(seed)]
        for name, label in ARMS.items():
            scores = row["five_arms"][name]
            budget = row["resources"][name]
            counts = " / ".join(str(scores[k]) for k in ("TP", "FP", "FN", "TN"))
            lines.append(
                f"| {seed} | {label} | {counts} | {pct(scores['precision'])} | {pct(scores['recall'])} | {pct(scores['FPR'])} | "
                f"{ratio(scores['explanation'])} | {ratio(scores['structured_fix'])} | {budget['calls']} | "
                f"{budget['input_tokens']:,} / {budget['output_tokens']:,} | {budget['elapsed_ms'] / 1000:.1f} |"
            )
    lines.extend(
        (
            "",
            "| Seed | Giai đoạn hội đồng | TP / FP | TP thêm / mất | FP bỏ / thêm | Chưa phát hiện |",
            "|---:|---|---:|---:|---:|---:|",
        )
    )
    for seed in SEEDS:
        row = metrics["seeds"][str(seed)]
        for stage, label in STAGES.items():
            p = row["phase_metrics"][stage]
            lines.append(
                f"| {seed} | {label} | {p['scores']['TP']} / {p['scores']['FP']} | "
                f"{len(p['added_true'])} / {len(p['lost_true'])} | {len(p['removed_false'])} / {len(p['added_false'])} | {p['scores']['FN']} |"
            )
    lines.extend(
        (
            "",
            "| Seed | Execution | Evidence trọng tài | Quyết định coverage | Wilson 95% cho recall cuối | Wilson 95% cho FPR cuối |",
            "|---:|---:|---:|---|---:|---:|",
        )
    )
    for seed in SEEDS:
        row = metrics["seeds"][str(seed)]
        c = row["coverage"]
        exe, ev = c["execution"], c["evidence"]
        final = row["five_arms"]["council_with_debate"]
        lines.append(
            f"| {seed} | {exe['accepted']}/{exe['required']} | {ev['verified']}/{ev['required']} | {c['decision']} | "
            f"{interval(final['recall'])} | {interval(final['FPR'])} |"
        )
    enroll = digest((path / "enrollment.json").read_bytes())
    index = digest((path / "index.json").read_bytes())
    lines.extend(
        (
            "",
            "Từ gốc repo, kiểm chứng enrollment, archive và tái dựng kết quả bằng lệnh sau.",
            "",
            "```sh",
            f"python engineering/airc500/quality_study.py verify --out engineering/airc500/evidence/quality-v2/{cohort} --enrollment-pin {enroll} --archive-pin {index}",
            "```",
            "",
        )
    )
    return lines


def render(root):
    lines = [
        "# Kết quả 100 lượt review Qwen 0.5B trên fixture",
        "",
        "Bảng điểm dùng hai cohort tổng hợp, một checkpoint Qwen2.5-0.5B-Instruct Q4_K_M và hai seed 17/43. "
        "Mỗi case chạy lại với seed khác có cùng nhãn. Mỗi nhánh tái dùng lượt mù chung, nên chỉ số participation đếm theo receipt duy nhất. "
        "So sánh một reviewer với hai reviewer ở cùng số lượt. Vòng tranh luận cần thêm thời gian và token. "
        "[Thiết kế, nguồn nhãn và giới hạn mẫu](../../QUALITY-EVALUATION.md).",
        "",
        f"GGUF SHA-256 `{MODEL_DIGEST}`, revision model `{MODEL_VERSION}`. "
        "Mỗi cohort dùng một key adapter và một key verifier theo hai vai trò trên cùng host tin cậy. Chữ ký cho phép kiểm tra nguồn output.",
        "",
        "Trong bảng, TP là lỗi được phát hiện đúng, FP là cảnh báo nhầm, FN là lỗi bỏ sót và TN là ca sạch được giữ. "
        "Giải thích và hướng sửa chấm riêng trên các TP. Tổng giây gọi model cộng thời gian thực của từng attempt. Cột thời gian chỉ tính các lượt gọi model. Hai cohort có thể chạy song song trên cùng máy.",
        "",
    ]
    unique = set()
    for cohort in ("marketing", "identity"):
        rows = read(root / cohort / "metrics.json")["seeds"].values()
        unique.update(reviewer for row in rows for reviewer in row["participation"]["distinct_reviewers"])
    lines.extend((f"Hai cohort có tổng cộng {len(unique)} ID reviewer khác nhau. Các lượt mù bao gồm cả lượt lặp cùng ID cho nhánh đối chứng.", ""))
    for cohort, name in (("marketing", "Marketing"), ("identity", "Danh tính")):
        result = read(root / cohort / "metrics.json")
        findings = []
        for seed in SEEDS:
            row = result["seeds"][str(seed)]
            full = row["five_arms"]["council_with_debate"]
            direct = row["five_arms"]["deterministic_only"]
            stage_add = sum(len(row["phase_metrics"][s]["added_true"]) for s in ("cross", "arbitration"))
            findings.append(
                f"seed {seed} có {direct['TP']} TP với verifier thuần, hội đồng cuối đạt {full['TP']} TP và {full['FP']} FP, "
                f"{ratio(full['structured_fix'])} hướng sửa đúng, hai vòng trao đổi ghi nhận {stage_add} lượt TP chuyển vào tập đang xét"
            )
        lines.extend((f"**{name}.** " + ". ".join(findings) + ".", ""))
    lines.extend(section(root, "marketing", "96 ca Marketing, scope và đếm trùng"))
    lines.extend(section(root, "identity", "16 ca chính sách danh tính"))
    lines.extend(
        (
            "## Diễn giải và phạm vi tin cậy",
            "",
            "Verifier định kiểu tự kiểm được giá trị và phạm vi trên nguồn fixture. Verifier abstain với 24 ca ngữ nghĩa Marketing thuộc phủ định, CTA và claim thiếu nguồn. "
            "Điểm hướng sửa của verifier thuần phản ánh khả năng tạo operation theo field định kiểu. Nhánh có AI chỉ xác minh candidate từng được reviewer nêu kèm đúng subject và nguồn. "
            "Vì vậy hai nhánh có thể đạt số lỗi cuối khác nhau dù dùng lại cùng quy tắc typed.",
            "",
            "Execution đếm receipt hợp lệ. Evidence yêu cầu trọng tài đưa đúng verdict, đúng subject, đúng nguồn và thuộc miền verifier có thể kiểm. "
            "Số finding cuối còn xét lịch sử candidate và ý kiến thiểu số từ các vòng trước. Các obligation thiếu khiến coverage ở trạng thái `inconclusive`. "
            "Chỉ số P/R/FPR và Wilson 95% của mọi phase/domain, danh sách ca bỏ sót, FP, giải thích và hướng sửa đã chấm đều có trong trace.",
            "",
            "Ví dụ từ seed 17, finding `F-970c36d8`. Nguồn của Indigo tote quy định CAD, nội dung ghi USD. Lượt mù `s17-common-0` (MK-022) báo có lỗi nhưng trỏ Linen wrap, chọn cả current và expected là “do not use CAD”, operation `keep` và nguồn D. Bộ chấm cho điểm phát hiện đúng đối với unit, điểm hướng sửa và giải thích bằng 0. [Journal chứa output gốc](marketing/seed-17.json.gz).",
        "",
        "Giao thức Marketing dùng tám chỉ số lựa chọn cho mỗi unit. Cohort identity dùng JSON với tên field và giá trị đầy đủ. "
            "Cả hai giao thức đặt verdict flag ở vị trí đầu. Hiệu ứng thứ tự lựa chọn còn chưa được kiểm soát. Thay đổi đồng thời miền và encoding ngăn suy luận kiểu trả lời nào tốt hơn từ phép so giữa hai cohort. "
            "Mỗi miền Marketing chỉ có bốn ca dương và bốn ca âm. Mẫu tổng hợp nhỏ chưa xác lập năng lực nghiệp vụ hoặc khả năng tổng quát hóa.",
            "",
            "Trước phép đo, một dispatch dùng JSON schema không được bản llama-server hiện tại hỗ trợ. Server trả HTTP 400, 0 receipt được chấp nhận, "
            "1 attempt không rõ usage và 4.000 token dự phòng vẫn bị giữ. [Checkpoint đã hủy](preflight-unsupported-schema.json). "
            "Các bảng chỉ dùng lần chạy với schema đã được hỗ trợ; 100 lượt đo đều có output ký và pin riêng.",
            "",
            "Qwen trong báo cáo này chạy native Windows trên fixture, trả phí ngoài bằng 0. Bằng chứng probe container Linux độc lập với các receipt đó. "
            "Bước kế tiếp cần hội đồng đủ căn cứ trước khi tăng số reviewer, xác nhận hiệu quả trên tập mới và có nhãn nghiệp vụ độc lập. "
            "Đọc source repository thực bằng reviewer tự động tiếp tục HOLD. Commercial GA tiếp tục NO-GO.",
            "",
        )
    )
    return "\n".join(lines)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory", type=Path)
    args = cli.parse_args()
    print(render(args.directory), end="")
