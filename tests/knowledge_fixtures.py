"""Create synthetic, approved marketing declarations through the normal C1 commands."""

from uuid import uuid4

from agency_fixtures import account, create


def scope(api, owner, label):
    tenant = owner["tenant"]
    base = "/api/tenants/" + tenant
    client = create(api, base + "/clients", owner, {"name": label})
    brand = create(api, base + "/brands", owner, {"client_id": client["id"], "name": label})
    return base + f"/clients/{client['id']}/brands/{brand['id']}/knowledge"


def call(api, owner, path, suffix, **data):
    return api.post(path + suffix, headers=owner["headers"], json={"key": uuid4().hex, **data})


def accepted(response):
    assert response.status_code in (200, 201), response.text
    return response.json()


def revision(api, actor, path, subject, kind, data, visibility="public", approve=True):
    row = accepted(call(api, actor, path, "/revisions", subject=subject, kind=kind, expected_revision=0, visibility=visibility, data=data))
    if approve:
        accepted(
            call(
                api,
                actor,
                path,
                f"/revisions/{row['id']}/events",
                expected_digest=row["digest"],
                expected_sequence=0,
                state="approved",
                reason="Compared with synthetic approved facts",
            )
        )
    return row


def bundle(api, owner=None, path=None):
    owner = owner or account(api, "KnowledgeRace")
    path = path or scope(api, owner, "Synthetic catalogue")

    def write(subject, kind, data):
        return revision(api, owner, path, subject, kind, data)

    product = write("ceramic", "product", {"name": "Tile", "sku": "T"})
    market = write("vn", "market", {"name": "Vietnam", "locales": ["vi-VN"]})
    placement = dict(product=product["id"], variant=None, market=market["id"], locale="vi-VN", channel="web", region="HN")
    statement = dict(placement=placement, category="description", wording="Matte surface", qualifiers=[])
    source = write(
        "datasheet",
        "source",
        {
            "publisher": "Synthetic lab",
            "document": "Test sheet",
            "valid_until": "2099-01-01T00:00:00Z",
            "entries": [{"locator": "row 2", "excerpt": "Matte surface", "assertion": statement}],
        },
    )
    binding = write("surface-evidence", "binding", {"source": source["id"], "locator": "row 2", "assertion": statement})
    claim = write("surface", "claim", {"binding": binding["id"], "assertion": statement})
    preview = accepted(call(api, owner, path, "/previews", claims=[claim["id"]]))
    return owner, path, source, claim, preview
