"""Synthetic internal Marketing assignments through the same registration and catalog APIs as a customer."""

from uuid import uuid4

from agency_fixtures import create
from c3_fixtures import prepared
from identity_fixtures import start_registration, verify_registration
from knowledge_fixtures import revision

LANDING = "WF-13/landing-seo-draft@6"
INTENT = {
    "purpose": "Giới thiệu bộ mẫu cho cửa hàng nội thất",
    "deliverable_type": "landing_page",
    "product": "Bộ mẫu vải",
    "audience": "Cửa hàng nội thất độc lập",
    "channel": "web",
    "region": "HN",
    "locale": "vi-VN",
    "requirements": ["Giúp người đọc chọn bộ mẫu để xem trực tiếp."],
    "exclusions": ["chắc chắn sinh lời"],
    "acceptance_criteria": ["Có lời mời đăng ký xem mẫu."],
}


def internal_workspace(api, project=None):
    email, password = f"c3-author-{uuid4().hex}@example.com", uuid4().hex
    auth = start_registration(api, email, password, organization_name="Xưởng mẫu An Nhiên", mode="inhouse")
    verify_registration(api, email, auth, project)
    actor = dict(
        **auth, id=auth["user_id"], tenant=auth["tenant_id"], email=email, password=password, headers={"Authorization": "Bearer " + auth["access_token"]}
    )
    base = "/api/tenants/" + actor["tenant"]
    clients = api.get(base + "/clients", headers=actor["headers"]).json()
    assert len(clients) == 1
    client = clients[0]["id"]
    brand = create(api, base + "/brands", actor, {"client_id": client, "name": "An Nhiên"})["id"]
    campaign = create(
        api,
        base + "/campaigns",
        actor,
        {"brand_id": brand, "name": "Bộ mẫu tháng tư", "brief": "Giới thiệu bộ mẫu tới cửa hàng", "objective": "Tăng đăng ký xem mẫu"},
    )["id"]
    return actor, base, client, brand, campaign


def fixture(api, project=None):
    actor, base, client, brand, campaign = internal_workspace(api, project)
    task = {"key": uuid4().hex, "campaign_id": campaign, "intent": INTENT}
    brief = create(api, base + "/workforce/internal-tasks", actor, task)
    state = prepared(
        api,
        actor,
        base,
        client,
        brand,
        campaign,
        brief["id"],
        LANDING,
        case={
            "product": INTENT["product"],
            "audience": INTENT["audience"],
            "company": "Xưởng mẫu An Nhiên",
            "brand": "An Nhiên",
            "objective": "Tăng đăng ký xem mẫu",
            "kpi": "Số lượt đăng ký xem mẫu",
            "facts": [{"wording": "Bề mặt mờ", "qualifiers": []}],
        },
    )
    guide = revision(
        api,
        actor,
        state["path"],
        "giong-an-nhien",
        "guidelines",
        {"guidance": "Dùng từ ngắn và cụ thể.", "tone": "Điềm tĩnh", "prohibited_claims": ["hoàn hảo tuyệt đối"]},
    )
    state["params"]["guidelines"] = guide["id"]
    return actor, base, client, brand, campaign, task, brief, state, guide
