"""Construct scoped C3 business knowledge through the signed editorial APIs."""
from uuid import uuid4

from app import c3_marketing
from app.knowledge_contracts import approval_category, price_wording
from knowledge_fixtures import accepted, call, revision
from test_claim_desk import reader
from test_business_workspace import post
from test_company_objectives import decision


def prepared(api, admin, base, client, brand, campaign, bid, workflow=c3_marketing.LANDING, *, case=None):
    company = base + "/clients/" + client
    scope = company + "/brands/" + brand
    ui, path = scope + "/business-workspace", scope + "/knowledge"
    marketing = ui + "/marketing"
    info = {"company":"Material House", "brand":"Sample surface studio", "product":"Fabric sample",
            "sku":"MAT-2", "market":"Vietnam", "locale":"vi-VN", "region":"HN", "channel":"web",
            "audience":"Independent interior shops", "objective":"Increase sample-kit requests", "kpi":"Completed request forms",
            "facts":[{"wording":"Matte surface","qualifiers":[]}]}
    info.update(case or {})
    post(api, company+"/business-profile", admin, expected_revision=0,
         fields={"name":info["company"],"sells":info["product"],"audience":info["audience"],"goal":info["objective"]})
    post(api, ui+"/overrides", admin, expected_revision=0, expected_company_revision=1,
         fields={"name":{"mode":"override","value":info["brand"]}})
    shared = post(api, company+"/company-objectives", admin, name="Qualified internal demand", owner="Sales", expected_revision=0)
    shared = decision(api, company+"/company-objectives", admin, shared)

    def make(subject, kind, data, **opts):
        return revision(api, admin, path, subject, kind, data, **opts)

    parent = make("brand-goal","objective",{"level":"brand","name":"Request samples","owner":"Planner","company_parent":shared["id"]})
    goal = make("campaign-goal","objective",{"level":"campaign","name":info["objective"],"owner":"Planner","parent":parent["id"],"campaign_id":campaign})
    product = make("catalog-item","product",{"name":info["product"],"sku":info["sku"]})
    market = make("market-vn","market",{"name":info["market"],"locales":[info["locale"]]})
    audience = make("buyer","icp",{"name":info["audience"],"description":" ".join(info.get("hypotheses",["Buyer needs require interviews"])),"basis":"hypothesis","market":market["id"]})
    placement = {"product":product["id"],"variant":None,"market":market["id"],**{k:info[k] for k in ("locale","channel","region")}}
    method = info.get("kpi_method","Count completed request forms")
    protocol = {"placement":placement,"category":"description","wording":method,"qualifiers":[]}
    kpi_source = make("measurement-protocol","source",{"publisher":"Synthetic agency measurement team",
        "document":"Definition of the event and observation period", "valid_until":"2099-01-01T00:00:00Z",
        "entries":[{"locator":"Measurement protocol, event definition","excerpt":method,"assertion":protocol}]})
    kpi = make("north-star","kpi",{"name":info["kpi"],"objective":goal["id"],"owner":"Analyst","source":kpi_source["id"],
        "unit":info.get("kpi_unit","requests"),"method":method,"window":info.get("kpi_window","30 days")})
    claims, sources = [], []
    reviewer = None
    mandates = {}
    commercial = {}
    for i, fact in enumerate(info["facts"]):
        statement = {"placement":placement,"category":fact.get("category","description"),"wording":fact["wording"],"qualifiers":fact["qualifiers"]}
        if statement["category"] == "price":
            price = fact["price"]
            policy = make(f"terms-{i}","policy",{"placement":placement,"payment":"Payment on confirmation"})
            offer_data = {"placement":placement,"price":price,"policy":policy["id"]}
            if fact.get("offer_valid_until"):
                offer_data["valid_until"] = fact["offer_valid_until"]
            offer = make(f"quote-{i}","offer",offer_data)
            statement.update(offer=offer["id"],price=price,quantity=fact["quantity"],wording=price_wording(price))
            commercial = {"currency":price["currency"],"quantity":fact["quantity"]}
        if statement["category"] == "availability":
            observed = make(f"stock-{i}","availability",{"placement":placement,"status":statement["wording"],"observed_at":"2020-01-01T00:00:00Z","valid_until":"2099-01-01T00:00:00Z"})
            statement["availability"] = observed["id"]
        source = make(f"source-{i}","source",{"publisher":"PRIVATE_SYNTHETIC_SUPPLIER","document":"PRIVATE_SYNTHETIC_DOCUMENT","valid_until":"2099-01-01T00:00:00Z",
                          "entries":[{"locator":"private locator", "excerpt":"PRIVATE_SYNTHETIC_EXCERPT","assertion":statement}]},visibility="restricted")
        binding = make(f"binding-{i}","binding",{"source":source["id"],"locator":"private locator","assertion":statement},visibility="restricted")
        category = approval_category(statement)
        claim = make(f"fact-{i}","claim",{"binding":binding["id"],"assertion":statement},approve=not category)
        if category:
            if reviewer is None:
                reviewer = reader(api,admin,"admin")
            if category not in mandates:
                mandate = make(f"mandate-{i}","qualification",{"approver_id":reviewer["id"],"category":category,
                    "basis":"Synthetic domain qualification","valid_until":"2099-01-01T00:00:00Z"},visibility="restricted")
                mandates[category] = mandate["id"]
            accepted(call(api,reviewer,path,"/revisions/" + claim["id"] + "/events",expected_digest=claim["digest"],
                expected_sequence=0,state="approved",reason="Reviewed synthetic source and qualifiers",qualification_revision=mandates[category]))
        claims.append(claim["id"])
        sources.append(source)
    selections = {"product":product["id"], "audience":audience["id"], "objective":goal["id"]}
    brief = post(api, ui+"/briefs", admin, title="Internal scoped Marketing brief", expected_revision=1, expected_company_revision=1, selections=selections)
    params = {"key":uuid4().hex, "workspace_brief_id":brief["id"],"target":{"campaign_id":campaign,"brief_id":bid}, "workflow":workflow,
              "market":market["id"],"kpi":kpi["id"],"claims":claims,**{k:info[k] for k in ("locale","channel","region")},**commercial}
    return {"marketing":marketing,"path":path,"ui":ui,"params":params,"root":shared,"company":company,
            "sources":sources,"selections":selections,"placement":placement,"mandates":mandates}


def capture(api, admin, prepared):
    return accepted(api.post(prepared["marketing"]+"/manifests",headers=admin["headers"],json=prepared["params"]))


def withdraw(api, admin, data, source=None):
    source = source or data["sources"][0]
    return call(api, admin, data["path"], f"/revisions/{source['id']}/events", state="withdrawn",
                expected_sequence=1, expected_digest=source["digest"], reason="Synthetic evidence withdrawn")
