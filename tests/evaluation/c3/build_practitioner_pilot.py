"""Package only the prespecified 01/02 fixtures. No database, model or third-party packages."""

import argparse
import copy
from hashlib import sha256
import io
import json
from pathlib import Path
import random
import re
import zipfile

HERE = Path(__file__).resolve().parent
GROUPS = ("seller", "materials", "service", "agency", "inhouse")
CASES = tuple(f"{group}-{index:02}" for group in GROUPS for index in (1, 2))
RUBRIC = ("du_kien", "pham_vi", "chung_cu", "huu_ich", "chuyen_mon", "khong_tuyen_bo_vo_can_cu")
LABELS = {"research_question":"Câu hỏi nghiên cứu","evidence_needed":"Chứng cứ cần bổ sung","segment":"Phân khúc",
          "buyer_problem":"Vấn đề cần giải quyết","positioning":"Định vị","rationale":"Lý do lựa chọn","channel_choice":"Kênh",
          "test_hypothesis":"Giả thuyết thử nghiệm","headline":"Tiêu đề","value_proposition":"Giá trị đề xuất","benefit":"Lợi ích",
          "call_to_action":"Lời mời hành động","page_title":"Tiêu đề SEO","meta_description":"Mô tả SEO","search_intent":"Ý định tìm kiếm",
          "selected_kpi":"KPI của brief","measurable_action":"Sự kiện cần đo","measurement_method":"Cách đo",
          "hypotheses":"Giả thuyết","gaps":"Khoảng trống chứng cứ"}
TECH = re.compile(
    r"\bWF-\d{2}/[\w.-]+@\d+\b|\b(?:director|research|strategy|content|seo)@\d+\b|\bn\d{2}\b|"
    r"\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b|\b[0-9a-f]{40,64}\b|"
    r"\b(?:Qwen|llama\.cpp|gguf|PRIVATE_SYNTHETIC)[\w.:-]*", re.I)
PRIVATE = re.compile(r"private locator|private document|access_token|api[_-]?key|[A-Z]:[\\/]|https?://", re.I)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def encode(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def archive(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as out:
        for path, content in sorted(files.items()):
            entry = zipfile.ZipInfo(path, (2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(entry, content.encode("utf-8") if isinstance(content, str) else content)
    return stream.getvalue()


def scrub(value):
    # Keep a visible placeholder if technical output was mistakenly used as Marketing copy.
    value = TECH.sub("[đã ẩn mã kỹ thuật]", value)
    if PRIVATE.search(value):
        raise ValueError("A candidate blind document contains a private marker or an unreviewed external reference")
    return value


def brief(case):
    lines = ["# Brief nghiệp vụ", f"\nBài làm: {case['workflow']}.",
             f"\n**Doanh nghiệp / thương hiệu** · {case['company']} / {case['brand']}",
             f"\n**Sản phẩm** · {case['product']} ({case['sku']})",
             f"\n**Phạm vi** · {case['market']} · {case['region']} · {case['locale']}",
             f"\n**Người mua** · {case['audience']}",f"\n**Mục tiêu** · {case['objective']}",
             f"\n**Kênh và hành động cần hỗ trợ** · {case['channel']} · {case['cta']}",
             "\n## Chứng cứ tổng hợp được phép dùng"]
    for i, fact in enumerate(case["facts"], 1):
        lines += [f"\n**S{i}** · {fact['wording']}",fact["qualifiers"]]
        if "price" in fact:
            p = fact["price"]
            units = {"piece":"chiếc", "m²":"m²", "service":"dịch vụ (đơn vị chung)", "box":"hộp",
                     "participant":"người", "machine":"máy", "kg":"kg", "tonne":"tấn"}
            unit = units.get(p["unit"], p["unit"])
            # Preserve the original minor units, tier AND wording; discrepancies are for the assessor.
            tax = {"included":"đã bao gồm", "excluded":"chưa bao gồm", "unknown":"chưa xác định"}[p["tax"]]
            lines += [f"Biểu giá có cấu trúc: {p['amount_minor']} đơn vị tiền nhỏ nhất của {p['currency']} cho {p['basis_quantity']} {unit}. "
                      f"Thuế: {tax}. Đơn tối thiểu: {p['moq']} {unit}. Áp dụng từ {p['tier_min']} {unit}"
                      + (f" đến {p['tier_max']} {unit}." if p.get("tier_max") is not None else "; chưa ghi trần."),
                      f"Số lượng đang xét: {fact['quantity']} {unit}.",*p["conditions"]]
    lines += ["\n## Đo lường", f"{case['kpi']} · Đơn vị: {case['kpi_unit']}. Kỳ: {case['kpi_window']}. Cách đo: {case['kpi_method']}.",
              "\n## Giả thuyết cần kiểm chứng",*case["hypotheses"],"\n## Dữ liệu còn thiếu",*case["gaps"]]
    return scrub("\n".join(lines) + "\n")


def labeled(fields):
    parts = []
    for key, value in fields.items():
        if key not in LABELS:
            raise ValueError(f"Unreviewed editorial field {key}")
        if isinstance(value, list):
            value = "\n".join("- " + item for item in value)
        if value:
            parts.append(f"**{LABELS[key]}** · {value}")
    return "\n\n".join(parts)


def candidate(row, case):
    if row["case"] != case["id"] or row["workflow"].split("/", 1)[0] != case["workflow"]:
        raise ValueError("Mismatched paired case or workflow")
    if not row.get("deliverable"):
        if row.get("state") != "needs_clarification" or "exact selling unit" not in (row.get("last_error") or ""):
            raise ValueError("Unmapped missing deliverable; review the user-facing reason before packaging")
        return "# Kết quả tiếp nhận\n\nCần xác nhận đơn vị bán chính xác trên bảng giá hoặc điều kiện áp dụng trước khi lập bản giao. Chưa có tài liệu Marketing.\n"
    doc = row["deliverable"]
    if not row.get("assets"):
        return scrub(f"# {doc['title']}\n\n{doc['body']}\n")
    a = row["assets"]
    if case["workflow"] == "WF-03":
        notes = a["research_notes"]
        sections = [("Nghiên cứu", labeled({**notes["fields"],"hypotheses":notes["hypotheses"],"gaps":notes["gaps"]})),
                    ("Quyết định chiến lược", labeled(a["strategy_decisions"])),
                    ("Kế hoạch đo lường", labeled(a["measurement_plan"]))]
    else:
        sections = [("Nội dung trang",labeled(a["buyer_copy"])),("Nội dung SEO",labeled(a["seo_fields"]))]
    proof = a["evidence_report"]
    sources = [f"[{f['handle']}] {f['text']}" for f in proof["facts"]]
    stage = {"content":"Nội dung","seo":"SEO","research":"Nghiên cứu","strategy":"Chiến lược"}
    sources.extend(f"{stage[k]} viện dẫn: {', '.join(refs)}" for k, refs in proof["suggested_handles"].items() if refs)
    sections.extend([("Chứng cứ đi kèm","\n".join(sources)),("Bản xem trước",doc["title"] + "\n\n" + doc["body"])])
    return scrub("\n\n".join("## " + title + "\n\n" + (content or "[Trống]") for title,content in sections) + "\n")


PHASES = {
    1: ("THU-CONG","Làm độc lập từ brief và nguồn. Viết bài trong tệp BAI-LAM, lưu phiếu và gửi lại trước khi nhận gói kế tiếp."),
    2: ("CO-TRO-LY","Trên các brief khác với phần thủ công, đọc bản được cấp, chấm lần đầu rồi biên tập. Ghi cả thời gian xử lý khi cần làm rõ."),
    3: ("CHAM-MU","Đọc theo THU-TU. Chấm từng bản chưa biên tập trước khi mở bản tiếp theo. Giữ nguyên điểm riêng trước khi trao đổi."),
}
GUIDE = """Các hồ sơ ở đây là tình huống tổng hợp. Mã S trong brief chỉ chứng cứ chuẩn. Mã F trong từng bài là tham chiếu cục bộ; đối chiếu nội dung và điều kiện thay vì đánh đồng hai mã cùng số. Phần [đã ẩn mã kỹ thuật] giữ vị trí một mã hệ thống đã xuất hiện trong bản gốc.

WF-03 cần vấn đề mua, định vị và lý do, kênh, giả thuyết và sự kiện/kỳ đo. WF-13 cần nội dung trang có ích cho người mua, CTA và metadata/ý định tìm kiếm nhất quán. Kiểm SKU, giá, đơn vị, thuế, ngưỡng, địa bàn, ngoại lệ và việc nguồn có thực sự hỗ trợ từng câu. Thiếu bản giao hoặc cần làm rõ vẫn giữ trong phiếu. Ghi nhận việc hỏi đúng riêng với việc có bản đạt lần đầu.

Ghi 0 hoặc 1 ở cả sáu tiêu chí (sai/đúng); nếu chưa chấm, giữ null. Với mỗi lỗi ghi trường, đoạn/câu, chứng cứ S tương ứng và việc cần sửa. first_pass_accepted là true khi sử dụng được ngay mà không cần sửa nghiệp vụ. accepted_after_editing là kết quả cuối của buổi làm việc. Ghi rõ vai trò, kinh nghiệm, xung đột lợi ích, và đã từng gặp mẫu này chưa. Giữ nhận xét riêng trước khi đối chiếu đồng nghiệp.

Nếu sau khi kiểm tra bạn xác nhận nhiệm vụ chưa có bản giao, ghi false cho first_pass_accepted và 0 cho sáu tiêu chí bản giao; tách lý do làm rõ vào observations. Không loại brief đó khỏi mẫu số.

Ở phiên có đồng hồ, ghi giờ bắt đầu/kết thúc và phút thực cho từng công đoạn planning (lập kế hoạch), drafting (soạn), source_check (đối chiếu), editing (sửa), qa (kiểm) và wait (chờ); total_elapsed là tổng thời gian thực trôi qua. Khi làm rõ chưa xong, ghi thời gian đã bỏ ra và mô tả tình trạng. Ghi đơn giá nhân công mỗi giờ cùng mã tiền, chi phí máy và nhà cung cấp theo cùng tiền tệ nếu đo được. 0 nghĩa là đã đo và bằng 0. null là chưa biết. Không điền ước lượng thay quan sát. Có thể ghi kết quả vào bản sao PHIEU.json và lưu bài cuối vào BAI-LAM/. Chỉ gửi tệp kết quả cho điều phối viên.
"""


def form(template, code, task, case, phase):
    row = copy.deepcopy(template)
    row.update(blind_asset_id=code,brief_id=task,workflow=case["workflow"],phase=phase,scores=dict.fromkeys(RUBRIC),
               accepted_after_editing=None,prior_exposure=None,session_started=None,session_ended=None,
               hourly_rate_and_currency={"amount":None,"currency":None})
    return row


def build(source, output, seed):
    output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    cases = {c["id"]: c for c in read(HERE / "holdout-v1.json")["cases"] if c["id"] in CASES}
    if set(cases) != set(CASES):
        raise ValueError("Incomplete selected briefs")
    sample = list(CASES)
    rng.shuffle(sample)
    tasks = {k:f"T{i:02}" for i,k in enumerate(sample, 1)}
    fixture_digest = sha256((HERE / "holdout-v1.json").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    cards, inputs = {}, {}
    for c in CASES:
        for arm in ("projected", "improved"):
            raw = (source / arm / c / "result.json").read_bytes()
            row = json.loads(raw)
            if row["arm"] != arm or row["cases_sha256"] != fixture_digest:
                raise ValueError("Run differs from the selected condition or frozen source brief")
            cards[c,arm] = candidate(row,cases[c])
            inputs[f"{arm}/{c}"] = sha256(raw).hexdigest()
    template = read(HERE / "pilot-form.json")
    codes = iter(rng.sample(range(10000,99999), 60))
    key = []
    master = {}
    for reviewer in range(2):
        who = "CV-" + str(reviewer+1)
        for phase, (name, instruction) in PHASES.items():
            packet = {"BAT-DAU.md":"# " + name + "\n\n" + instruction + "\n\n" + GUIDE}
            slots = []
            for pos, c in enumerate(CASES):
                group, within = divmod(pos,2)
                manual = (group + within) % 2
                if phase < 3 and (reviewer == manual) != (phase == 1):
                    continue
                if phase == 3:
                    arms = ("projected","improved") if (pos+reviewer)%2==0 else ("improved","projected")
                elif phase == 1:
                    arms = ("manual",)
                else:
                    arms = (("projected","improved")[(within + group//2)%2],)
                slots.extend((tier,c,arm) for tier,arm in enumerate(arms))
            rng.shuffle(slots)
            slots.sort(key=lambda slot:slot[0])  # First reading of every brief before the second.
            rows = []
            order = []
            for _, c, arm in slots:
                task = tasks[c]
                code = "B" + str(next(codes))
                key.append(dict(reviewer=who,phase=phase,task=task,code=code,case=c,arm=arm,workflow=cases[c]["workflow"]))
                packet["BRIEF/" + task + ".md"] = brief(cases[c])
                if arm != "manual":
                    packet["BAN-GIAO/" + code + ".md"] = cards[c,arm]
                if phase < 3:
                    packet["BAI-LAM/" + code + ".md"] = f"# Bài làm · {code}\n\nBrief {task}.\n\n"
                order.append(f"{len(order)+1}. {task} · {code}")
                rows.append(form(template,code,task,cases[c],phase))
            packet["PHIEU.json"] = encode(rows)
            packet["THU-TU.md"] = "# Thứ tự làm việc · " + who + "\n\n" + "\n".join(order) + "\n"
            master[f"{who}/{phase}-{name}.zip"] = archive(packet)
    master["DIEU-PHOI/khoa.json"] = encode({"seed":seed,"briefs_sha256":fixture_digest,"source_results":inputs,"assignments":key})
    master["DIEU-PHOI/doi_chieu.py"] = (HERE / "compare_practitioner_pilot.py").read_bytes()
    master["DIEU-PHOI/QUY-TRINH.md"] = (HERE.parents[2] / "docs/evaluation/C3-HOLDOUT-AND-PILOT.md").read_bytes()
    master["HUONG-DAN.md"] = (HERE.parents[2] / "docs/evaluation/C3-PRACTITIONER-KIT.md").read_bytes()
    generated = {name: (data if isinstance(data,bytes) else data.encode("utf8")) for name, data in master.items()}
    generated["AMC-PILOT-CHUYEN-VIEN.zip"] = archive(master)
    # Never rotate a key or change a form under an assignment already sent to a reviewer.
    if any((output / name).exists() and (output / name).read_bytes() != data for name, data in generated.items()):
        raise ValueError("The output already contains a different kit. Select a new empty directory.")
    for name, data in generated.items():
        path = output / name
        path.parent.mkdir(exist_ok=True,parents=True)
        if not path.exists():
            path.write_bytes(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paired",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--seed",type=int,required=True,help="Kept only in the coordinator package")
    args = parser.parse_args()
    build(args.paired,args.output,args.seed)
