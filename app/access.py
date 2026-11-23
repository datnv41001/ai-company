"""Authenticated transaction context and client-scoped read queries."""
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session

from .models import ActionRequest, Brand, Campaign, Client, Deliverable, Membership, WorkTask

_CONTEXT = text("""SELECT set_config('amc.user_id',:actor,true),
    set_config('amc.tenant_id',:tenant,true), set_config('amc.lookup_email',:email,true)""")


@event.listens_for(Session, "after_begin")
def restore_context(session, transaction, connection):
    context = session.info.get("amc_context")
    if connection.dialect.name == "postgresql" and context is not None:
        connection.execute(_CONTEXT, context)


def set_context(db, *, actor="", tenant="", email=""):
    if db.get_bind().dialect.name != "postgresql":
        return
    values = dict(actor=actor, tenant=tenant, email=email)
    if db.info.get("amc_context") != values:
        connection = db.connection()
        db.info["amc_context"] = values
        connection.execute(_CONTEXT, values)


def visible(model, membership: Membership):
    tenant = membership.tenant_id
    stmt = select(model).where(model.tenant_id == tenant)
    if membership.role != "client_viewer":
        return stmt
    client = membership.client_id
    if model is Client:
        return stmt.where(Client.id == client)
    if model is Brand:
        return stmt.where(Brand.client_id == client)
    brands = select(Brand.id).where(Brand.tenant_id == tenant, Brand.client_id == client)
    if model is Campaign:
        return stmt.where(Campaign.brand_id.in_(brands))
    if model in (WorkTask, Deliverable, ActionRequest):
        campaigns = select(Campaign.id).where(Campaign.tenant_id == tenant, Campaign.brand_id.in_(brands))
        return stmt.where(model.campaign_id.in_(campaigns))
    raise ValueError("Missing scoped read rule")
