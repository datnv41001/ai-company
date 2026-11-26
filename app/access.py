"""Authenticated transaction context and client-scoped read queries."""
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session

from .models import Client, Membership

_CONTEXT = text("""SELECT set_config('amc.sandbox_protocol','ops/2',true), set_config('amc.delivery_protocol','c3/5',true),
    set_config('amc.user_id',:actor,true),
    set_config('amc.tenant_id',:tenant,true), set_config('amc.lookup_email',:email,true)""")


_WORKER = text("""SELECT set_config('amc.worker_client',:client,true),set_config('amc.worker_brand',:brand,true),
    set_config('amc.worker_campaign',:campaign,true)""")


def set_worker_scope(db, client, brand, campaign):
    values = {"client":client,"brand":brand,"campaign":campaign}
    db.info["amc_worker_scope"] = values
    if db.get_bind().dialect.name == "postgresql":
        db.execute(_WORKER, values)


@event.listens_for(Session, "after_begin")
def restore_context(session, transaction, connection):
    context = session.info.get("amc_context")
    if connection.dialect.name == "postgresql" and context is not None:
        connection.execute(_CONTEXT, context)
        if "amc_worker_scope" in session.info:
            connection.execute(_WORKER, session.info["amc_worker_scope"])


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
    # Raw agency rows can contain internal briefs, notes, budgets and draft content.
    return stmt.where(False)
