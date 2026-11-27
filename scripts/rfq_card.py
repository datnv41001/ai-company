"""Export portable RFQ cards from the two pinned, repository-owned synthetic sources."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import tempfile

from scripts.rfq_evidence import archived_khe_gon, build_card, with_plan_provenance


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/rfq_evidence"
LINEAGE_SHA = "ed9f793aeef37236957536cc9fc1068eceeeca8d206cf373ae8b357b3738ecea"
CASES = ("khe-gon", "before", "after")


def field(value):
    return escape(str(value)) if value is not None else "Chưa có bằng chứng"


def facts(items):
    return "<dl>" + "".join(f"<div><dt>{field(k)}</dt><dd>{field(v)}</dd></div>" for k, v in items) + "</dl>"


def audit(value):
    return "<pre>" + escape(json.dumps(value, indent=2, ensure_ascii=False)) + "</pre>"


def report(card, key):
    request, rule, commercial = (card[k] for k in ("request", "rule", "commercial"))
    below = commercial["status"] == "below_minimum"
    statuses = {"below_minimum": "Dưới mức đặt tối thiểu", "meets_recorded_minimum": "Đạt mức đặt tối thiểu đã ghi"}
    title = statuses.get(commercial["status"], commercial["status"])
    unit = {"box": "hộp"}.get(request["unit"], request["unit"])
    quantity = f'{request["quantity"]} {unit}'
    minimums = ", ".join(map(str, commercial["recorded_minimums"])) or "Chưa rõ"
    subtitle = {"khe-gon": "Khe Gọn · Hồ sơ lưu trữ", "before": "Hồ sơ đối chiếu · Trước bổ sung",
                "after": "Hồ sơ đối chiếu · Sau bổ sung"}[key]
    missing = ", ".join(rule["missing"])
    stages = {"sales_acceptance": "Sales tiếp nhận", "quote": "Báo giá", "order": "Đơn hàng",
              "confirmed_revenue": "Doanh thu xác nhận"}
    outcomes = [(name, "Chưa có receipt" if card["milestones"][k]["receipt_id"] is None else
                 "Đã ghi nhận trong sandbox") for k, name in stages.items()]
    sales = ("Chủ offer và Sales Operations kiểm tra nguồn MOQ và thẩm quyền xét ngoại lệ trước khi chuyển yêu cầu."
             if below else "Sales Operations kiểm tra hồ sơ và chuyển qua Business Desk cho người được phân công.")
    marketing = ("Có thể khách cần mẫu thử hoặc cách ghi MOQ trên form chưa rõ. Đối chiếu bản form đã phát hành, "
                 "các inquiry cùng revision và phản hồi được phép sử dụng." if below else
                 "Chưa có bằng chứng về động cơ mua. Đối chiếu các inquiry cùng revision và ghi nhận lý do nếu được phép.")
    history = "".join("<li>" + facts([("Revision", h["revision"]), ("Sequence", h["sequence"]),
                                      ("Receipt", h["receipt_id"]), ("Thời điểm nghiệp vụ", h["occurred_at"]),
                                      ("Thời điểm ghi nhận", h["recorded_at"])]) + "</li>" for h in card["history"])
    stylesheet = (Path(__file__).with_name("rfq_card.css")).read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>{field(subtitle)} | AMC</title><style>{stylesheet}</style></head>
<body><main><header><span>AMC / Business Desk</span><span>Sandbox · Chỉ đọc</span></header>
<section class="hero"><p>{field(subtitle)}</p><h1>{field(title)}</h1><p>Khách yêu cầu <b>{field(quantity)}</b>.
Mức tối thiểu ghi trong hồ sơ là <b>{field(minimums)} {field(unit)}</b>.</p></section>
<section><h2>Yêu cầu của khách</h2>{facts([("Sản phẩm", request.get("product_name") or request["product_id"]),
("SKU", request["sku"]), ("Mục đích", request["contact_purpose"]), ("Địa điểm", request["location"]),
("Ngày cần hàng", request["required_date"]), ("Điểm cắt ghi nhận (UTC)", card["recorded_as_of"])])}</section>
<section><h2>Bước xử lý đề xuất</h2><p>{field(sales)}</p>
{facts([("Kiểm đủ dữ kiện", "Còn thiếu · " + missing if missing else "Đủ trường theo rule"),
("Xác nhận qualification", "Chưa có receipt từ người có thẩm quyền"), ("Người được phân công", card["assignment"]["assignee_id"]),
("Người có thẩm quyền xác nhận", card["qualification"]["decision_owner"])])}</section>
<section><h2>Các mốc thương mại</h2>{facts(outcomes)}</section>
<section><h2>Phản hồi cho Marketing</h2><p><b>Quan sát.</b> Số lượng tại revision {field(card["revision"])} là {field(quantity)}.</p>
<p><b>Giả thuyết và cách kiểm chứng.</b> {field(marketing)}</p><p>Phụ trách đối chiếu · Marketing cùng chủ offer.</p></section>
<section><h2>Nguồn và phạm vi</h2>{facts([("Inquiry",card["inquiry_id"]),("Revision",card["revision"]),
("Thời điểm lập báo cáo (UTC)",card["generated_at"]),("Thời gian hiệu lực policy", None),
("Nguồn MOQ",commercial["receipt_id"]),("Contract revision",commercial["contract_revision"]),
("Mức liên kết attribution", card["attribution"]["status"])])}
<details><summary>Lịch sử và thời điểm nghiệp vụ</summary><ol>{history}</ol></details>
<details><summary>Phạm vi, nguồn và liên kết</summary>{audit({k:card[k] for k in ("scope","evidence_source","attribution","commercial")})}</details>
<details><summary>Dữ kiện chưa biết</summary><ul>{''.join('<li>'+field(s)+'</li>' for s in card["unknowns"])}</ul></details>
<a href="{key}.json" download>Tải JSON kiểm toán</a></section></main></body></html>"""


def cards():
    now = datetime.now(timezone.utc)
    archive = archived_khe_gon((FIXTURES / "khe-gon.json").read_bytes(), generated_at=now)
    data = (FIXTURES / "lineage.json").read_bytes()
    if sha256(data).hexdigest() != LINEAGE_SHA:
        raise ValueError("Synthetic revision fixture digest mismatch")
    source = json.loads(data)
    result = {"khe-gon": archive}
    for key, revision in (("before", "revision_1"), ("after", "revision_2")):
        card = build_card(scope=source["scope"], inquiry_id=source["inquiry_id"], events=source["events"],
                          recorded_as_of=source["cutoffs"][revision], generated_at=now)
        card = with_plan_provenance(card, source["provenance"])
        card["archived_measurement"] = {"intake_funnel": source["measurement"][revision],
                                        "primary_measurement": source["measurement"]["primary_measurement"]}
        card["evidence_source"] = {"path": "tests/fixtures/rfq_evidence/lineage.json", "sha256": LINEAGE_SHA}
        result[key] = card
    return result


def export(destination):
    items = cards()
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("Choose a new output directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        stage = Path(tmp) / "cards"
        stage.mkdir()
        for key, card in items.items():
            (stage / (key + ".json")).write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (stage / (key + ".html")).write_text(report(card, key), encoding="utf-8")
        stage.rename(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New directory for three HTML/JSON pairs")
    try:
        export(parser.parse_args().output)
    except (OSError, LookupError, ValueError) as exc:
        parser.exit(1, f"RFQ export: {exc}\n")
