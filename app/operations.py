"""Internal agency operations. Work items and finance remain private to each tenant."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import current_user, require_tenant

router = APIRouter(prefix="/api/tenants/{tenant_id}/operations", tags=["Agency operations"])


class Budget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ceiling: int = Field(ge=0, le=10**14)
    capacity: int = Field(ge=1, le=64)
    enabled: bool


class Receipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: int = Field(ge=0, le=10**14)
    receipt: str = Field(min_length=1, max_length=160, pattern=r"\S")


def require_operations(db, user, tenant):
    require_tenant(db, user, tenant, "admin")
    if db.get_bind().dialect.name != "postgresql":
        raise HTTPException(409, "Agency pooling requires PostgreSQL")


@router.get("")
def overview(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    if db.get_bind().dialect.name != "postgresql":
        return {"available": False}
    return {"available": True, **db.scalar(text("select amc_ops.summary(:t)"), {"t": tenant_id})}


@router.put("/budget")
def configure(tenant_id: str, body: Budget, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_operations(db, user, tenant_id)
    try:
        db.execute(text("select amc_ops.configure(:t,:ceiling,:capacity,:enabled)"), {"t": tenant_id, **body.model_dump()})
    except IntegrityError as exc:
        if exc.orig.diag.constraint_name == "pool_cutover_pending":
            raise HTTPException(409, "Drain active legacy runs before enrollment") from None
        raise
    db.commit()
    return overview(tenant_id, user, db)


@router.post("/attempts/{attempt}/receipts")
def reconcile(tenant_id: str, attempt: UUID, body: Receipt, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_operations(db, user, tenant_id)
    accepted = db.scalar(text("select amc_ops.bill(:t,:i,:amount,:receipt)"), {"t": tenant_id, "i": attempt, **body.model_dump()})
    if not accepted:
        raise HTTPException(409, "Receipt requires a collected, closed attempt and a consistent receipt key")
    db.commit()
    return {"recorded": True}
