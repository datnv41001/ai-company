"""SQLite counterparts of migration 006. Its single writer serializes enqueue and revocation."""

from sqlalchemy import event
from .workforce_models import WorkforceRun

MATCH = """SELECT 1 FROM workforce_briefs b JOIN portal_grants g
    ON g.tenant_id=b.tenant_id AND g.user_id=b.recipient_id AND g.client_id=b.client_id
    WHERE b.id={brief} AND (g.brand_id IS NULL OR g.brand_id=b.brand_id)
    AND (g.campaign_id IS NULL OR g.campaign_id=b.campaign_id)"""

CANCEL = (
    """UPDATE workforce_runs SET state='failed',lease=NULL,last_error='recipient_revoked',
    journal=CASE WHEN state='running' THEN json_set(journal,'$[#-1].outcome','recipient_revoked',
        '$[#-1].usage_unconfirmed',json('true'),'$[#-1].finished_at',strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        ELSE journal END WHERE state IN ('queued','running') AND NOT EXISTS ("""
    + MATCH.format(brief="workforce_runs.brief_id")
    + ")"
)


def install_sqlite(conn):
    for verb, name in (("DELETE", "deleted"), ("UPDATE OF brand_id,campaign_id", "changed")):
        conn.exec_driver_sql(f"""CREATE TRIGGER IF NOT EXISTS workforce_grant_{name} AFTER {verb} ON portal_grants
          BEGIN {CANCEL} AND tenant_id=OLD.tenant_id AND brief_id IN
          (SELECT id FROM workforce_briefs WHERE tenant_id=OLD.tenant_id AND recipient_id=OLD.user_id); END""")
    conn.exec_driver_sql(
        """CREATE TRIGGER IF NOT EXISTS workforce_check_intake BEFORE INSERT ON workforce_runs
        WHEN NOT EXISTS ("""
        + MATCH.format(brief="NEW.brief_id")
        + """)
        BEGIN SELECT RAISE(ABORT,'workforce_recipient_required'); END"""
    )
    conn.exec_driver_sql("""CREATE TRIGGER IF NOT EXISTS workforce_audit_withdrawal AFTER UPDATE OF last_error ON workforce_runs
        WHEN NEW.last_error='recipient_revoked' AND OLD.last_error IS NOT NEW.last_error
        BEGIN INSERT INTO audit_events(id,tenant_id,user_id,event,subject_id,details,occurred_at) VALUES
        (lower(hex(randomblob(16))), NEW.tenant_id,'workforce-policy','workforce.recipient_revoked',NEW.id,
         json_object('previous_state',OLD.state,'reserved_microusd',NEW.reserved_microusd),CURRENT_TIMESTAMP); END""")
    conn.exec_driver_sql(CANCEL)


@event.listens_for(WorkforceRun.__table__, "after_create")
def install_when_created(table, conn, **kwargs):
    if conn.dialect.name == "sqlite":
        install_sqlite(conn)
