"""Live Studio decisions retain the authority of each relied-on reviewer through commit."""

from sqlalchemy import select, text

from .models import Membership


def active_approver(db, tenant, reviewer, *, lock=False):
    if lock and db.get_bind().dialect.name == "postgresql":
        return db.scalar(text("SELECT amc_acl.lock_c3_reviewer(:tenant,:reviewer)"), {"tenant": tenant, "reviewer": reviewer})
    role = db.scalar(select(Membership.role).filter_by(tenant_id=tenant, user_id=reviewer))
    return role in ("admin", "owner")
