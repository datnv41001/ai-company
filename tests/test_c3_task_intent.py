import json
from uuid import uuid4

from agency_fixtures import account
from c3_fixtures import capture, withdraw
from c3_task_fixtures import INTENT, LANDING, fixture
from knowledge_fixtures import accepted, revision
from test_workforce import DATA, workforce as workforce_fixture

workforce = workforce_fixture


def test_internal_task_pins_readiness_and_scope(api):
    actor, base, _, _, campaign, task, brief, s, guide = fixture(api)
    path = base + "/workforce/internal-tasks"

    def send(data, who=actor):
        return api.post(path, headers=who["headers"], json=data)

    assert accepted(send(task)) == brief
    assert send(task | {"intent": INTENT | {"purpose": "Mục đích cập nhật"}}).status_code == 409
    assert send(task | {"campaign_id": str(uuid4())}).status_code == 404
    assert send(task, account(api, "OtherTenant")).status_code == 404
    assert send(task | {"intent": INTENT | {"source_documents": ["private"]}}).status_code == 422

    def readiness(params):
        return accepted(api.post(s["marketing"] + "/readiness", headers=actor["headers"], json=params))

    params = s["params"]
    assert readiness(params) == {"status": "ready", "guidance": []}
    for changed, word in (({"guidelines": None}, "hướng dẫn"), ({"workflow": "WF-03/research-strategy-draft@3"}, "Loại bản giao")):
        assert word in readiness(params | changed)["guidance"][0]
    for field, word in (("audience", "nhóm khách hàng"), ("product", "sản phẩm"), ("region", "địa bàn"), ("locale", "ngôn ngữ"), ("channel", "kênh")):
        other = accepted(send(task | {"key": str(uuid4()), "intent": INTENT | {field: "Khác"}}))
        result = readiness(params | {"target": {"campaign_id": campaign, "brief_id": other["id"]}})
        assert result["status"] == "needs_input" and word in result["guidance"][0]
    snap = capture(api, actor, s)
    assert capture(api, actor, s) == snap and snap["version"] == "amc.marketing-manifest/2"
    projected = snap["projection"]
    assert projected["task_intent"] == INTENT
    assert projected["brand_guidelines"] == {
        "revision": 1,
        "digest": guide["digest"],
        "guidance": "Dùng từ ngắn và cụ thể.",
        "tone": "Điềm tĩnh",
        "prohibited_claims": ["hoàn hảo tuyệt đối"],
    }
    assert "PRIVATE_SYNTHETIC" not in json.dumps(snap)
    restricted = revision(api, actor, s["path"], "Private", "guidelines", {"guidance": "SECRET_GUIDE"}, visibility="restricted")
    assert readiness(params | {"guidelines": restricted["id"]})["status"] == "needs_input"
    assert api.post(base + "/workforce/briefs/" + brief["id"] + "/run", headers=actor["headers"], json={}).status_code == 409
    accepted(withdraw(api, actor, s, guide))
    assert readiness(params)["status"] == "needs_input"
    assert accepted(api.get(s["marketing"] + "/manifests/" + snap["id"], headers=actor["headers"])) == snap


def test_agency_requires_recipient_authorized_task_summary(api, workforce):
    owner, recipient, _, base, root, scope, _, brief = workforce
    path = root + "/briefs/" + brief["id"]
    assert (
        api.post(root + "/internal-tasks", headers=owner["headers"], json={"key": str(uuid4()), "campaign_id": scope.campaign, "intent": INTENT}).status_code
        == 404
    )
    assert api.put(path + "/task-submission", headers=owner["headers"], json=INTENT).status_code == 404
    summary = INTENT | {"product": "Fabric sample", "audience": "Independent interior shops"}
    data = DATA | {"task_intent": summary, "sources": [{"label": "PRIVATE_CUSTOMER", "excerpt": "RAW_CUSTOMER_SECRET"}]}
    accepted(api.put(path + "/submission", headers=recipient["headers"], json=data))
    from c3_fixtures import prepared

    state = prepared(api, owner, base, scope.client, scope.brand, scope.campaign, brief["id"], LANDING)
    guide = revision(api, owner, state["path"], "brand-style", "guidelines", {"guidance": "Use plain words."})
    state["params"]["guidelines"] = guide["id"]
    snap = capture(api, owner, state)
    assert snap["projection"]["task_intent"] == summary
    assert "RAW_CUSTOMER_SECRET" not in json.dumps(snap) and "PRIVATE_CUSTOMER" not in json.dumps(snap)
