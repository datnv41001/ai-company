"""Pin target facts and their durable generations without changing legacy application rows."""

from sqlalchemy import event, select, text

from .database import Base
from .delivery_models import PortalGrant
from .knowledge_store import conflict, digest, canonical, missing
from .models import Campaign, Membership, Tenant
from .workforce_models import WorkforceBrief


def install_sqlite_target_epochs(conn):
    conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS knowledge_target_epochs(kind TEXT NOT NULL,id TEXT NOT NULL,epoch INTEGER NOT NULL,PRIMARY KEY(kind,id))")
    for table, kind, fields in (
        ("campaigns", "campaign", "tenant_id,brand_id,name,brief,objective,status"),
        ("workforce_briefs", "brief", "tenant_id,client_id,brand_id,campaign_id,recipient_id,title,payload"),
    ):
        conn.exec_driver_sql(f"""CREATE TRIGGER IF NOT EXISTS knowledge_epoch_{kind} AFTER UPDATE OF {fields} ON {table}
                BEGIN INSERT INTO knowledge_target_epochs VALUES('{kind}',NEW.id,1)
                ON CONFLICT(kind,id) DO UPDATE SET epoch=epoch+1; END""")


@event.listens_for(Base.metadata, "after_create")
def fresh_database(metadata, conn, **kwargs):
    if conn.dialect.name == "sqlite" and {"campaigns", "workforce_briefs"} <= set(conn.dialect.get_table_names(conn)):
        install_sqlite_target_epochs(conn)


def describe(store, target, *, lock):
    if target is None:
        return {"kind": "brand_foundation"}
    db = store.db
    t, c, b = (store.scope[k] for k in ("tenant_id", "client_id", "brand_id"))
    k, i = target.campaign_id, target.brief_id
    brief = db.scalar(select(WorkforceBrief).filter_by(tenant_id=t, client_id=c, brand_id=b, campaign_id=k, id=i))
    if not brief:
        missing()
    internal = brief.origin == "internal"
    if store.postgres and lock:
        statement = ("SELECT amc_acl.lock_c3_internal_target(:t,:c,:b,:k,:i)" if internal
                     else "SELECT amc_acl.lock_knowledge_target(:t,:c,:b,:k,:i)")
        if not db.scalar(text(statement), dict(t=t, c=c, b=b, k=k, i=i)):
            missing()
        db.refresh(brief)
    campaign = db.scalar(select(Campaign).filter_by(tenant_id=t, brand_id=b, id=k))
    if not campaign:
        missing()
    member = db.get(Membership, (t, brief.recipient_id))
    if internal:
        tenant = db.get(Tenant,t)
        if not tenant or tenant.mode != "inhouse" or not member or member.role not in ("owner","admin","editor"):
            conflict("Người giao nhiệm vụ nội bộ không còn quyền trong workspace.")
    else:
        grant = db.get(PortalGrant, (t, brief.recipient_id))
        if (not member or member.role != "client_viewer" or member.client_id != c or not grant or grant.client_id != c
                or grant.brand_id not in (None,b) or grant.campaign_id not in (None,k)):
            conflict("Brief recipient no longer has this scope")
    if store.postgres:
        epochs = list(db.scalar(text("SELECT amc_acl.knowledge_target_epoch(:t,:c,:b,:k,:i)"), dict(t=t, c=c, b=b, k=k, i=i)))
    else:
        epochs = [
            db.scalar(text("SELECT epoch FROM knowledge_target_epochs WHERE kind=:kind AND id=:id"), dict(kind=g, id=id_)) or 0
            for g, id_ in (("campaign", k), ("brief", i))
        ]
    return {
        "kind": "internal_task" if internal else "campaign_brief",
        "campaign_id": k,
        "brief_id": i,
        "campaign_generation": epochs[0],
        "brief_generation": epochs[1],
        "campaign_digest": digest(canonical([campaign.name, campaign.brief, campaign.objective, campaign.status])),
        "brief_digest": digest(canonical([brief.title, brief.recipient_id, brief.payload])),
        "submitted": brief.payload is not None,
    }
