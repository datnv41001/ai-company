"""Deterministic B2B RFQ lab. All inputs, signers and destinations belong to a fixture."""
import json
from pathlib import Path
from time import perf_counter_ns

from .campaign_lab_measurement import reconcile
from .campaign_work_units import measure_lab_units
from .knowledge_store import canonical, digest
from .revision_qa import content_digest
from .services.marketing import WORKFLOW_STEPS

CATALOG = Path(__file__).resolve().parents[1] / "catalog"
VERSION = "campaign-execution-lab/rfq@1"
SCENARIO = CATALOG / "labs" / "b2b-rfq-v1.json"
REVIEWS = CATALOG / "labs" / "b2b-rfq-v1-approvals.json"
WORKFLOWS = ("WF-06", "WF-07", "WF-17", "WF-18", "WF-19", "WF-20")


def fingerprint(value):
    return digest(canonical(value))


def propose(scenario):
    goal, facts = scenario["goal"], scenario["knowledge"]
    catalog = json.loads((CATALOG / "workflows.json").read_text(encoding="utf-8"))
    packages = [
        {"id": key, "owner": owner, "acceptance": output, "milestone_day": day}
        for (key, _, owner, output), day in zip(WORKFLOW_STEPS, (1, 1, 2, 2, 2, 3, 12), strict=True)
    ]
    return {
        "status": "proposed", "revision": 1, "objective": goal["objective"], "buyer": goal["buyer"],
        "product": facts["product"], "offer": goal["offer"], "budget_vnd": goal["budget_vnd"],
        "missing_information": facts["unknown"],
        "channels": ["Trang yêu cầu báo giá", "Quảng cáo tìm kiếm", "Bài đăng mạng xã hội"],
        "strategy": "Ưu tiên người phụ trách thu mua đã có công trình. Dùng tìm kiếm để tiếp cận "
                    "nhu cầu báo giá, dẫn về một biểu mẫu ngắn và chuyển yêu cầu đủ thông tin cho Sales.",
        "hypothesis": "Hỏi diện tích, địa bàn và thời điểm cần hàng ngay trên trang có thể giảm số lần Sales phải hỏi lại.",
        "budget_proposal": "Dành 1.200.000 VND chi phí mô phỏng cho thử nghiệm tìm kiếm. Giữ phần còn lại chờ đối soát RFQ.",
        "work_packages": packages, "knowledge_digest": fingerprint(facts), "goal_digest": fingerprint(goal),
        "workflow_contracts": [row for row in catalog if row["id"].split()[0] in WORKFLOWS],
    }


def asset_pack(scenario, plan):
    facts = scenario["knowledge"]
    product, buyer, offer = plan["product"], plan["buyer"], plan["offer"]
    cta = "Gửi diện tích (m²), quận/huyện giao hàng và ngày cần hàng để nhận báo giá."
    items = [
        ("landing", "landing_page", f"Yêu cầu báo giá {product.lower()}",
         f"{buyer}: đang lập dự toán cho công trình? {offer}. Hãy chọn mã {facts['sku']}. "
         f"{cta} Sales sẽ cần xác nhận tồn kho theo lô và phí giao trước khi chốt báo giá."),
        ("social", "social_content", "Chuẩn bị yêu cầu báo giá cho công trình",
         f"Anh/chị phụ trách thu mua đang so sánh phương án {product.lower()} tại {facts['market']}? "
         f"Chuẩn bị ba thông tin để Sales trao đổi đúng công trình. {cta}"),
        ("ad", "advertising_copy", "Gửi RFQ gạch ốp công trình",
         f"{product} cho dự án tại {facts['market']}. {cta}"),
        ("seo", "seo_metadata", f"Báo giá {product.lower()} cho nhà thầu tại {facts['market']}",
         f"Mô tả tìm kiếm: Chuẩn bị yêu cầu báo giá {product.lower()} theo diện tích và kế hoạch giao. {cta}"),
        ("creative", "creative_brief", "Brief hình minh họa cho trang báo giá",
         f"Đối tượng: {buyer}. Hình chính: bố cục mô tả quy cách {product.lower()} và vị trí biểu mẫu. "
         f"Chỉ dùng ảnh có quyền, giữ mã {facts['sku']} đọc được ở kích thước di động. "
         "Bàn giao brief cho thiết kế. Hình ảnh cần sản xuất và duyệt riêng."),
        ("calendar", "content_calendar", "Lịch nội dung và điểm duyệt",
         "Ngày 2: Copywriter hoàn tất bản trang, SEO và quảng cáo. Ngày 3: QA đối chiếu quy cách và duyệt CTA, "
         "mở trang mô phỏng. Ngày 4: Media chạy quảng cáo tìm kiếm mô phỏng. Ngày 5: rà soát bài mạng xã hội "
         "trước khi phát. Ngày 12: Analytics đối soát đơn bị hủy rồi đề xuất thử nghiệm."),
    ]
    return [
        {"id": key, "kind": kind, "title": title, "body": body, "revision": 1,
         "digest": content_digest(title, body), "status": "generated",
         "context_digest": fingerprint({"goal": scenario["goal"], "knowledge": facts, "plan": plan}),
         "sku": facts["sku"], "buyer": buyer, "offer": offer, "objective": plan["objective"]}
        for key, kind, title, body in items
    ]


def review_record(reviews, key, subject, actor):
    expected = {"subject": key, "digest": fingerprint(subject), "reviewer": actor, "synthetic": True}
    if reviews.get(key) != expected:
        raise ValueError(f"Missing or stale synthetic approval for {key}")
    return expected


class SyntheticAdapter:
    """A per-replay adapter with a fixture clock. A completed slot always returns its original receipt."""

    def __init__(self, plan, assets, reviews):
        self.plan = plan
        self.assets = {asset["id"]: asset for asset in assets}
        self.reviews = reviews
        self.actions = {}
        self.spent = 0

    def schedule(self, slot):
        key = slot["id"]
        if key in self.actions:
            if self.actions[key]["slot"] != slot:
                raise ValueError("Slot key reused with different terms")
            return self.actions[key]
        asset = self.assets[slot["asset_id"]]
        if slot["day"] < 1 or type(slot["cost_vnd"]) is not int or slot["cost_vnd"] < 0:
            raise ValueError("Invalid simulation schedule or cost")
        action = {"id": key, "asset_id": asset["id"], "slot": dict(slot), "state": "scheduled",
                  "history": ["scheduled"], "attempts": 0, "receipt": None}
        self.actions[key] = action
        return action

    @staticmethod
    def transition(action, state):
        action["state"] = state
        action["history"].append(state)

    def authorize(self, key):
        action = self.actions[key]
        if action["state"] != "scheduled":
            raise ValueError("Only scheduled actions can be authorized")
        self.check_reviews(action)
        self.transition(action, "authorized")

    def check_reviews(self, action):
        asset = self.assets[action["asset_id"]]
        review_record(self.reviews, "plan", self.plan, "fixture:budget-owner")
        review_record(self.reviews, asset["id"], asset, "fixture:marketing-qa")
        review_record(self.reviews, action["id"], {"slot": action["slot"], "asset_digest": asset["digest"],
                      "plan_digest": fingerprint(self.plan)}, "fixture:channel-approver")

    def cancel(self, key):
        action = self.actions[key]
        if action["state"] not in {"scheduled", "authorized", "failed"}:
            raise ValueError("This slot cannot be cancelled")
        self.transition(action, "cancelled")

    def execute(self, key, *, day, fail=False):
        action = self.actions[key]
        if action["state"] == "executed":
            return action["receipt"]
        if action["state"] not in {"authorized", "failed"} or day < action["slot"]["day"]:
            raise ValueError("Action must be authorized and due")
        self.check_reviews(action)
        if action["attempts"] >= 2:
            raise ValueError("Retry limit exhausted")
        cost = action["slot"]["cost_vnd"]
        if self.spent + cost > self.plan["budget_vnd"]:
            raise ValueError("Synthetic budget ceiling exceeded")
        action["attempts"] += 1
        if fail:
            self.transition(action, "failed")
            return None
        self.spent += cost
        receipt = {"adapter": "synthetic-only", "slot_id": key, "cost_vnd": cost, "day": day,
                   "asset_digest": self.assets[action["asset_id"]]["digest"],
                   "approval_digest": self.reviews[key]["digest"]}
        action["receipt"] = {"id": fingerprint(receipt), **receipt}
        self.transition(action, "executed")
        return action["receipt"]


def replay():
    start = perf_counter_ns()
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    reviews = json.loads(REVIEWS.read_text(encoding="utf-8"))
    for key in ("goal", "knowledge"):
        review_record(reviews, key, scenario[key], "fixture:business-owner")
    plan = propose(scenario)
    review_record(reviews, "plan", plan, "fixture:budget-owner")
    assets = asset_pack(scenario, plan)
    for asset in assets:
        review_record(reviews, asset["id"], asset, "fixture:marketing-qa")
    adapter = SyntheticAdapter(plan, assets, reviews)
    for slot in scenario["actions"]:
        adapter.schedule(slot)
        adapter.authorize(slot["id"])
        if slot["id"] == "social-slot":
            adapter.cancel(slot["id"])
            continue
        if slot["id"] == "ad-slot":
            adapter.execute(slot["id"], day=slot["day"], fail=True)
        adapter.execute(slot["id"], day=slot["day"])
        adapter.execute(slot["id"], day=slot["day"])
    report, leads, exceptions = reconcile(scenario["events"], adapter.actions)
    recommendation = (
        f"Đối chiếu nguồn cho {report['missing_attribution']} RFQ và làm rõ "
        f"{report['incomplete_rfqs']} yêu cầu thiếu thông tin trước khi xin thêm ngân sách. "
        f"Dùng doanh thu có nguồn {report['attributed_revenue_vnd']:,} VND làm mốc của bộ dữ liệu mô phỏng."
    )
    return {"contract_version": VERSION, "synthetic": True, "scenario_id": scenario["scenario_id"],
            "scenario_digest": fingerprint(scenario), "goal": scenario["goal"], "knowledge": scenario["knowledge"],
            "plan": {**plan, "status": "approved", "proposal_digest": fingerprint(plan)},
            "assets": [{**a, "status": "approved"} for a in assets], "actions": list(adapter.actions.values()),
            "report": report, "leads": leads, "exceptions": exceptions, "recommendation": recommendation,
            "approvals": list(reviews.values()), "runtime_ms": (perf_counter_ns() - start) / 1_000_000,
            "work_units": measure_lab_units(scenario["scenario_id"], assets, reviews),
            "model_invocations": 0, "manual_minutes": None, "real_spend_vnd": 0}
