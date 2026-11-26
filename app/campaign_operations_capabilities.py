"""Fixed local destinations and exact group approvals for sandbox placement."""
from . import c3_boundaries, c3_customer_assets
from .c3_studio_routes import asset_digest, signoffs
from .knowledge_store import canonical, conflict, digest


CAPABILITIES = {
    ("render_preview","website","sandbox_page"): {"copy"},
    ("render_preview","organic_search","sandbox_search"): {"seo"},
    ("render_preview","internal","sandbox_review"): {"client_strategy","client_measurement"},
    ("rehearse_placement","paid_media","sandbox_ad_slot"): {"copy"},
}


def bind(db, doc, target):
    if target.group not in CAPABILITIES.get((target.action_type,target.channel,target.destination),set()):
        conflict("This action, channel and group do not have the requested local capability")
    studio = doc.content.get("studio") or {}
    if studio.get("delivery_version") != c3_customer_assets.VERSION or target.group not in studio["groups"]:
        conflict("This document has no reviewed customer asset group for the selected capability")
    run = c3_boundaries.run_for(db,doc)
    fields = c3_customer_assets.project(run.knowledge["registry"]["workflow"],studio["groups"])[target.group]
    sig = asset_digest(doc,run,target.group,fields)
    approvals = signoffs(db,doc,run,lock_reviewers=True)
    if sig != target.group_digest or target.group not in approvals:
        conflict("The exact asset group needs a current independent approval")
    contract = target.model_dump() | {"approval_receipt":approvals[target.group]["receipt"], "run_id":run.id}
    return contract | {"capability_digest":digest(canonical(contract))}


def perform(db,doc,target):
    run = c3_boundaries.run_for(db,doc)
    fields = c3_customer_assets.project(run.knowledge["registry"]["workflow"],doc.content["studio"]["groups"])[target["group"]]
    return {"type":target["action_type"],"destination":target["destination"],"group":target["group"],"fields":fields,
            "group_digest":target["group_digest"],"content_sha256":digest(canonical(fields)),"external_writes":0}
