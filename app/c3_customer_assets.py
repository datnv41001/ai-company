"""A deliberately selected, independently approved edition for the Agency customer.

The portal keeps its immutable title/body wire format. The private QA/share receipt
records the typed fields behind those same bytes, alongside the existing source chain.
"""

from . import c3_assets, c3_studio, campaign_channels
from .knowledge_store import canonical, conflict, digest

VERSION = "amc.customer-marketing-assets/1"
PUBLIC = {
    c3_assets.RESEARCH: {
        "client_strategy": ("target", "decision", "activation", "next_decision"),
        "client_measurement": ("hypothesis", "conversion", "method"),
    },
    c3_assets.LANDING: {key: c3_studio.FIELDS[c3_assets.LANDING][key] for key in ("copy", "seo")},
}
LABELS = {
    "client_strategy": ("Chiến lược Marketing", "Marketing strategy"),
    "client_measurement": ("Kế hoạch đo lường", "Measurement plan"),
    "target": ("Đối tượng", "Target buyer"),
    "decision": ("Lựa chọn chiến lược", "Strategic choice"),
    "activation": ("Triển khai trên kênh", "Channel activation"),
    "next_decision": ("Quyết định tiếp theo", "Decision after the test"),
    "hypothesis": ("Giả thuyết cần thử", "Test hypothesis"),
    "conversion": ("Hành động của người mua", "Buyer action"),
    "method": ("Phương pháp đo", "Measurement method"),
    "copy": ("Nội dung trang đích", "Landing page copy"),
    "seo": ("Thông tin SEO", "SEO metadata"),
    "headline": ("Tiêu đề", "Headline"),
    "value_proposition": ("Giá trị cho người mua", "Value proposition"),
    "benefit": ("Lợi ích", "Benefit"),
    "commercial_terms": ("Điều kiện thương mại", "Commercial terms"),
    "call_to_action": ("Lời mời hành động", "Call to action"),
    "page_title": ("Tiêu đề SEO", "Page title"),
    "meta_description": ("Mô tả tìm kiếm", "Meta description"),
    "search_intent": ("Ý định tìm kiếm", "Search intent"),
}


def labels(locale):
    return {key: pair[0 if locale == "vi-VN" else 1] for key, pair in (LABELS | campaign_channels.LABELS).items()}


def strategy(projection):
    """Compose delivery suggestions from disclosable dimensions, never staff checkpoints."""
    vi = projection["locale"] == "vi-VN"
    product, buyer, channel = (projection[key] for key in ("product", "audience", "channel"))
    action = c3_studio.buyer_action(projection)
    choice = projection.get("task_intent", {}).get("buyer_action")
    if choice == "rfq":
        position = (f"Đề xuất giúp {buyer} đối chiếu quy cách của {product} trước khi gửi yêu cầu báo giá.",
                    f"Help {buyer} check the specifications of {product} before requesting a quote.")
        activate = (f"Trên {channel}, đặt điều kiện áp dụng cạnh lời mời báo giá. Chuyển yêu cầu đủ thông tin cho Sales.",
                    f"On {channel}, place applicable terms beside the quote request. Route complete requests to Sales.")
        hypothesis = ("Thử đặt quy cách trước biểu mẫu để người mua có thể gửi yêu cầu đủ thông tin hơn.",
                      "Test whether showing specifications before the form makes more requests complete.")
        method = ("Đối soát mã yêu cầu duy nhất với yêu cầu Sales đủ thông tin để báo giá. So sánh trên lượt vào trang cùng nhóm khách.",
                  "Match each unique request to one Sales can quote. Compare complete requests per visit within the same audience.")
        decision = ("Nếu nhiều người gửi nhưng Sales còn phải hỏi lại, ưu tiên sửa trường thông tin thiếu trước khi mở rộng kênh.",
                    "If Sales must repeatedly request missing details, revise the form before expanding the channel.")
    elif choice in {"sample_request", "colour_card_request", "select_sample", "submit_reference"}:
        position = (f"Cho {buyer} đối chiếu đặc điểm đã công bố của {product} khi chọn mẫu.", f"Help {buyer} compare the declared characteristics of {product} when selecting a sample.")
        activate = (f"Trên {channel}, trình bày quy cách cạnh bước chọn mẫu và chuyển lựa chọn cho người xử lý.", f"On {channel}, place specifications beside sample selection and pass the choice to the handler.")
        hypothesis = ("Thử trình bày quy cách trước bước chọn mẫu.", "Test presenting specifications before sample selection.")
        method = ("Đối chiếu lựa chọn mẫu với mã yêu cầu duy nhất. So tỷ lệ chọn mẫu trên lượt vào đủ điều kiện.", "Match sample selections to unique requests. Compare selections per eligible visit.")
        decision = ("Nếu phải liên hệ lại để xác định mẫu, chỉnh cách mô tả lựa chọn trước khi tăng phân phối.", "If handlers must clarify the sample, revise the selection labels before expanding distribution.")
    else:
        position = (f"Đề xuất giúp {buyer} đối chiếu điều kiện của {product} khi cân nhắc hành động tiếp theo.", f"Help {buyer} check the terms for {product} when considering the next step.")
        activate = (f"Trên {channel}, thử đặt phần điều kiện trước lời mời hành động rồi so với cách sắp xếp hiện tại.", f"On {channel}, test placing the terms before the call to action against the current order.")
        hypothesis = ("Thử xem thứ tự trình bày có giúp người mua hoàn tất bước đã chọn.", "Test whether presentation order helps buyers complete the chosen step.")
        method = ("Đối soát mỗi sự kiện hoàn tất theo mã duy nhất. So tỷ lệ hoàn tất trên lượt vào cùng nhóm khách.", "Reconcile each completion using a unique identifier. Compare completions per visit for the same audience.")
        decision = ("Nếu hành động tăng, kiểm tra chất lượng kết quả với người tiếp nhận trước khi mở rộng.", "If completions rise, confirm their quality with the receiving team before expanding.")
    i = 0 if vi else 1
    return {
        "client_strategy": {"target": buyer, "decision": position[i], "activation": activate[i], "next_decision": decision[i]},
        "client_measurement": {"hypothesis": hypothesis[i], "conversion": action, "method": method[i]},
    }


def schema(workflow, channel_context):
    return PUBLIC[workflow] | campaign_channels.FIELDS if channel_context else PUBLIC[workflow]


def project(workflow, groups, channel_context=None):
    return {group: {key: groups[group][key] for key in keys} for group, keys in schema(workflow, channel_context).items()}


def preview(workflow, groups, projection, channel_context=None):
    named = labels(projection["locale"])
    blocks = []
    for group, fields in project(workflow, groups, channel_context).items():
        blocks.append(named[group])
        blocks.extend(named[key] + "\n" + value for key, value in fields.items())
    title = groups["copy"]["headline"] if workflow == c3_assets.LANDING else projection["product"]
    return {"title": title, "body": "\n\n".join(blocks)}


def issues(workflow, groups, projection, channel_context=None):
    intent = projection.get("task_intent", {})
    style = projection.get("brand_guidelines", {})
    private = [intent.get("purpose"), projection.get("objective"), projection.get("kpi"), style.get("guidance"),
               *intent.get("requirements", []), *intent.get("exclusions", []), *intent.get("acceptance_criteria", []),
               *projection.get("hypotheses", []), *projection.get("gaps", [])]
    public = project(workflow, groups, channel_context)
    result = campaign_channels.issues(groups, projection, channel_context) if channel_context else []
    seen = set()
    for group, fields in public.items():
        for field, value in fields.items():
            norm = c3_assets.normalized(value)
            reason = None
            if not norm:
                reason = "missing"
            elif any(c3_assets.normalized(term) in norm for term in private if term and len(term.strip()) >= 5):
                reason = "private_context"
            elif group.startswith("client_") and field not in ("target", "conversion") and norm in {
                c3_assets.normalized(projection[k]) for k in ("product", "audience", "channel", "region")
            }:
                reason = "entity_only"
            elif group.startswith("client_") and norm in seen:
                reason = "repetition"
            elif field == "conversion" and norm != c3_assets.normalized(c3_studio.buyer_action(projection)):
                reason = "buyer_action"
            if reason:
                result.append({"group": group, "field": field, "reason": reason})
            seen.add(norm)
    return result


def manifest(doc, run, approvals):
    workflow = run.knowledge["registry"]["workflow"]
    groups = doc.content["studio"]["groups"]
    projection = run.knowledge["c3_projection"]
    ctx = doc.content["studio"].get("channel_context")
    version = doc.content["studio"]["delivery_version"]
    output = preview(workflow, groups, projection, ctx)
    if (doc.title, doc.content["client_preview"]) != (output["title"], output["body"]) or issues(workflow, groups, projection, ctx):
        conflict("Save and review the current customer edition before delivery")
    return {
        "contract": version,
        **({"channel_context": ctx} if ctx else {}),
        "scope": {key: getattr(run, key) for key in ("tenant_id", "client_id", "brand_id", "campaign_id")},
        "revision": doc.qa_revision,
        "assets": {
            group: {"fields": fields, "digest": digest(canonical([version, group, fields])), "approval_receipt": approvals[group]}
            for group, fields in project(workflow, groups, ctx).items()
        },
    }
