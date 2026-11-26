"""Fixed local destinations and exact group approvals for sandbox placement."""
from . import c3_boundaries, c3_customer_assets
from .c3_studio_routes import asset_digest, signoffs
from .knowledge_store import canonical, conflict, digest


CAPABILITIES = {
    ("render_preview","website","sandbox_page"): {"copy"},
    ("render_preview","organic_search","sandbox_search"): {"seo"},
    ("render_preview","internal","sandbox_review"): {"client_strategy","client_measurement","creative_brief","calendar"},
    ("render_preview","organic_social","sandbox_social"): {"social"},
    ("rehearse_placement","paid_media","sandbox_ad_slot"): {"copy","ad"},
}


def projection(store,doc):
    studio = doc.content.get("studio") or {}
    run = c3_boundaries.run_for(store.db,doc)
    workflow = run.knowledge["registry"]["workflow"]
    if studio.get("delivery_version") == c3_customer_assets.VERSION:
        return run, c3_customer_assets.project(workflow,studio["groups"])
    channels = getattr(c3_customer_assets,"campaign_channels",None)
    if channels and studio.get("delivery_version")==channels.VERSION:
        channels.require_current(store,doc,run)
        return run, c3_customer_assets.project(workflow,studio["groups"],studio["channel_context"])
    conflict("This customer delivery contract does not provide authorized sandbox asset groups")


def bind(store, doc, target):
    if target.group not in CAPABILITIES.get((target.action_type,target.channel,target.destination),set()):
        conflict("This action, channel and group do not have the requested local capability")
    run, visible = projection(store,doc)
    if target.group not in visible:
        conflict("This customer edition does not contain the requested public asset group")
    fields = visible[target.group]
    sig = asset_digest(doc,run,target.group,fields)
    approvals = signoffs(store.db,doc,run,lock_reviewers=True)
    if sig != target.group_digest or target.group not in approvals:
        conflict("The exact asset group needs a current independent approval")
    contract = target.model_dump() | {"approval_receipt":approvals[target.group]["receipt"], "run_id":run.id}
    return contract | {"capability_digest":digest(canonical(contract))}


def perform(store,doc,target):
    _, visible = projection(store,doc)
    fields = visible[target["group"]]
    return {"type":target["action_type"],"destination":target["destination"],"group":target["group"],"fields":fields,
            "group_digest":target["group_digest"],"content_sha256":digest(canonical(fields)),"external_writes":0}
