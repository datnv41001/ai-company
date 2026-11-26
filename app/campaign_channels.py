"""Customer-facing, editorial campaign assets commissioned on a real Studio run."""

from . import c3_studio
from .knowledge_store import conflict

VERSION = "amc.customer-marketing-assets/2"
FIELDS = {
    "social": ("pillar", "opening", "approved_terms", "buyer_action"),
    "ad": ("campaign", "ad_group", "intent", "headlines", "description", "buyer_action", "test", "allocation", "measurement"),
    "creative_brief": ("concept", "brand_direction", "image_spec", "video_spec", "rights", "provenance"),
    "calendar": ("channels", "sequence", "editorial_order", "owners", "release_gate"),
}
LABELS = {
    "social": ("Bài mạng xã hội", "Social post"), "ad": ("Đề xuất quảng cáo", "Advertising proposal"),
    "creative_brief": ("Brief thiết kế", "Creative brief"), "calendar": ("Lịch nội dung", "Editorial calendar"),
    "pillar": ("Trụ cột nội dung", "Content pillar"), "opening": ("Mở bài", "Opening"),
    "approved_terms": ("Dữ kiện và điều kiện", "Approved facts and terms"), "buyer_action": ("Lời mời hành động", "Buyer action"),
    "campaign": ("Đề xuất chiến dịch", "Campaign proposal"), "ad_group": ("Giả thuyết nhóm người mua", "Ad group hypothesis"),
    "intent": ("Ý định và từ khóa đề xuất", "Search intent and proposed keywords"), "headlines": ("Tiêu đề quảng cáo", "Ad headline"),
    "description": ("Lời quảng cáo", "Ad description"), "test": ("Thử nghiệm sáng tạo", "Creative test"),
    "allocation": ("Phân bổ đề xuất", "Proposed allocation"), "measurement": ("Phép đo", "Measurement"),
    "concept": ("Ý tưởng hình ảnh", "Creative concept"), "brand_direction": ("Chỉ dẫn thương hiệu", "Brand direction"),
    "image_spec": ("Đặc tả ảnh", "Image specification"), "video_spec": ("Kịch bản video", "Video specification"),
    "rights": ("Điều kiện quyền sử dụng", "Rights clearance"), "provenance": ("Nguồn tài sản", "Asset provenance"),
    "channels": ("Kênh trong kế hoạch", "Planned channels"), "sequence": ("Mốc đề xuất", "Proposed milestones"),
    "editorial_order": ("Thứ tự nội dung", "Editorial sequence"),
    "owners": ("Bộ phận nhận việc", "Handoff owners"), "release_gate": ("Điểm duyệt", "Release gate"),
}


def context(store, run):
    """Obtain the restricted commission as an approver. Editors see the saved public subset."""
    from .campaign_operations import production_bindings
    from .campaign_planner import history

    if not store.approver:
        return None
    active = next((p for p in history(store, run.campaign_id) if p["status"] == "approved"), None)
    if not active:
        return None
    primary = active["manifests"].get("landing") or active["manifests"]["strategy"]
    if primary["id"] != run.knowledge["c3_manifest"]["id"]:
        return None
    binding = production_bindings(store, run.campaign_id).get((active["id"], primary["id"]))
    if not binding or binding[0].id != run.id or primary["digest"] != run.knowledge["c3_manifest"]["digest"]:
        return None
    return {"plan_id": active["id"], "plan_revision": active["revision"], "plan_digest": active["digest"],
            "plan_receipt": active["approval"]["receipt"], "manifest": primary, "queue_receipt": binding[1],
            "channel_plan": active["channels"], "guideline_digest": active["brand_guidelines"]["digest"],
            "due_days": {p["id"]: p["due_day"] for p in active["work_packages"] if p["id"] in FIELDS}}


def require_current(store, doc, run):
    expected = doc.content["studio"].get("channel_context")
    if not expected or expected != context(store, run):
        conflict("The channel edition needs its original active plan, approval, manifest and queue receipt")
    from .campaign_planner import active_plan
    active_plan(store, run.campaign_id)  # revalidate every dependency before a new approval or share


def compose(projection, ctx):
    from . import c3_order_units

    vi = projection["locale"] == "vi-VN"
    product, buyer = projection["product"], projection["audience"]
    cta = c3_studio.buyer_action(projection)
    action = projection["task_intent"]["buyer_action"]
    def tr(local, english):
        return local if vi else english
    if action == "rfq":
        key = tr("chuẩn bị yêu cầu báo giá", "preparing a quotation request")
        open_copy = tr(f"Anh chị đang lập yêu cầu báo giá cho {product}?", f"Preparing a quotation request for {product}?")
        measure = tr("Đối soát từng yêu cầu đủ thông tin để Sales lập báo giá theo mã yêu cầu.", "Match each quote-ready request to its Sales handoff by request ID.")
    elif action in ("appointment", "choose_session", "request_assessment"):
        key = tr("chuẩn bị lịch hẹn", "planning an appointment")
        open_copy = tr(f"Anh chị muốn sắp xếp lịch cho {product}?", f"Planning an appointment for {product}?")
        measure = tr("So sánh số lịch được nhân sự xác nhận trên lượt yêu cầu. Ghi riêng ca hủy hoặc vắng mặt.", "Compare staff-confirmed bookings per request. Separate cancellations and no-shows.")
    else:
        key = tr("đối chiếu điều kiện trước khi chọn", "checking terms before choosing")
        open_copy = tr(f"Anh chị đang cân nhắc {product}?", f"Considering {product}?")
        measure = tr("Đối soát hành động hoàn tất theo mã duy nhất và ghi riêng kết quả chưa xác minh.", "Reconcile completed actions by unique ID and separate unverified results.")
    terms = "\n".join(" ".join(c3_order_units.fact_lines(f, projection)) for f in projection["facts"])
    days = ctx["due_days"]
    return {
        "social": {"pillar": key, "opening": open_copy, "approved_terms": terms, "buyer_action": cta},
        "ad": {
            "campaign": tr(f"Đề xuất thử thông điệp về {product}.", f"Test messaging about {product}."),
            "ad_group": tr(f"Giả thuyết cần thử với nhóm {buyer}.", f"Test the audience hypothesis with {buyer}."),
            "intent": tr(f"Từ khóa thử nghiệm: {product} · {key}.", f"Proposed query: {product} · {key}."),
            "headlines": product, "description": open_copy, "buyer_action": cta,
            "test": tr("So sánh hai cách mở đầu. Giữ nguyên lời mời hành động, vị trí và điều kiện.", "Compare two opening lines while holding action, placement and terms constant."),
            "allocation": tr("Đề xuất chia đều hạn mức media đã duyệt giữa hai biến thể trong mô phỏng.", "Propose an equal split of the approved media cap between the two simulated variants."),
            "measurement": measure,
        },
        "creative_brief": {
            "concept": tr(f"Phác thảo khung hình cho {product} có chỗ đặt điều kiện và lời mời hành động.", f"Storyboard {product} with space for the applicable terms and call to action."),
            "brand_direction": tr("Đối chiếu màu, giọng điệu và dấu hiệu nhận diện với bản hướng dẫn thương hiệu đã ghim.", "Check colours, tone and identifiers against the pinned brand guide."),
            "image_spec": tr("Đề xuất bố cục dọc và ngang. Giữ chủ thể, điều kiện và CTA trong vùng an toàn khi cắt.", "Brief portrait and landscape compositions. Keep the subject, terms and CTA in the crop-safe area."),
            "video_spec": tr("Kịch bản gồm cảnh nhu cầu của người mua, cảnh đối chiếu dữ kiện và cảnh chọn bước tiếp theo.", "Storyboard the buyer need, a check against approved facts, then the next action."),
            "rights": tr("Chờ kiểm tra chủ sở hữu, giấy phép, phạm vi và thời hạn trước khi dùng tư liệu.", "Verify owner, licence, scope and expiry before using any material."),
            "provenance": tr("Bản giao chỉ gồm chỉ dẫn sản xuất. Chưa có tệp hình ảnh hoặc video được cấp phép.", "Production instructions only. No licensed image or video file is attached."),
        },
        "calendar": {
            "channels": " · ".join(ctx["channel_plan"]),
            "editorial_order": tr("Mở bằng câu hỏi của người mua, tiếp đến là bài đối chiếu điều kiện, kết thúc bằng lời mời hành động.", "Lead with the buyer question, follow with a check of the terms, and close with the next action."),
            "sequence": tr(f"Ngày {days['creative_brief']}: soát brief. Ngày {days['social']}: chuẩn bị bài. Ngày {days['ad']}: duyệt mẫu quảng cáo. Ngày {days['calendar']}: đối soát lịch.", f"Day {days['creative_brief']}: check brief. Day {days['social']}: prepare post. Day {days['ad']}: review ads. Day {days['calendar']}: reconcile schedule."),
            "owners": tr("Social soạn bài, Media soạn quảng cáo, Design nhận brief và Campaign Manager đối soát lịch.", "Social drafts the post, Media drafts the ad, Design receives the brief and Campaign Manager reconciles the schedule."),
            "release_gate": tr("Chỉ đề xuất lịch. Kiểm tra nguồn, quyền sử dụng và bản QA đã duyệt trước khi mô phỏng.", "Proposed schedule. Confirm evidence, rights and approved asset revision before simulation."),
        },
    }


def issues(groups, projection, ctx):
    control = compose(projection, ctx)
    # A rights statement, schedule scope or CTA cannot be invented by editing a draft.
    pinned = {"social": ("approved_terms", "buyer_action"), "ad": ("buyer_action", "allocation"),
              "creative_brief": ("rights", "provenance"), "calendar": ("channels", "sequence")}
    return [{"group": g, "field": k, "reason": "channel_contract"}
            for g, keys in pinned.items() for k in keys if groups[g][k] != control[g][k]]
