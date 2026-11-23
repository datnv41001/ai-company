def test_internal_work_is_private(api, agency):
    _, base, ((alice, resources), _) = agency
    for name in ("deliverables", "actions", "brands", "campaigns"):
        reply = api.get(base + "/" + name, headers=alice["headers"])
        assert reply.status_code == 200
        assert reply.json() == []
    draft_path = base + "/deliverables/" + next(iter(resources["deliverables"]))
    assert api.get(draft_path, headers=alice["headers"]).status_code == 404
    cid = next(iter(resources["campaigns"]))
    assert api.get(base + f"/campaigns/{cid}/tasks", headers=alice["headers"]).status_code == 404
