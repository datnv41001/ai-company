"""Company-owned working data and brand preparations. Only explicit commands create revisions."""

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field, model_validator
from sqlalchemy import or_, select, text
from sqlalchemy.exc import DBAPIError

from .database import get_db
from .knowledge_contracts import Input, Key, Name
from .knowledge_store import canonical, conflict, digest, missing, signed_document, stamp
from .models import Brand, Client, new_id
from .security import current_user, require_tenant
from .workspace_records import WorkspaceRecord as Record


FIELDS = ("name", "sells", "audience", "goal")
FieldName = Literal["name", "sells", "audience", "goal"]
Content = Annotated[str, Field(min_length=1, max_length=1800)]
Counter = Annotated[int, Field(strict=True, ge=0)]
BASE = "/api/tenants/{tenant_id}/clients/{client_id}"
BRAND = "/brands/{brand_id}/business-workspace"
router = APIRouter(prefix=BASE, tags=["business workspace"])


class Command(Input):
    key: Key
    expected_revision: Counter


class SharedPatch(Command):
    fields: Annotated[dict[FieldName, Content | None], Field(min_length=1, max_length=4)]


class Adjustment(Input):
    mode: Literal["inherit", "empty", "override"]
    value: Content | None = None

    @model_validator(mode="after")
    def check_override(self):
        if (self.mode == "override") != (self.value is not None):
            raise ValueError("Only override takes a non-empty value")
        return self


class BrandCommand(Command):
    expected_company_revision: Counter


class BrandPatch(BrandCommand):
    fields: Annotated[dict[FieldName, Adjustment], Field(min_length=1, max_length=4)]


class DraftBrief(BrandCommand):
    title: Name


class Workspace:
    def __init__(self, request, user, db, *, write):
        tenant = request.path_params["tenant_id"]
        client = request.path_params["client_id"]
        brand = request.path_params.get("brand_id")
        self.db, self.actor, self.client, self.tenant, self.brand = db, user.id, client, tenant, brand
        self.postgres = db.get_bind().dialect.name == "postgresql"
        if write and not self.postgres and not db.connection().connection.driver_connection.in_transaction:
            db.execute(text("BEGIN IMMEDIATE"))
        self.role = require_tenant(db, user, tenant, "editor" if write else "viewer").role
        if self.role not in ("owner", "admin", "editor", "viewer") or db.info.get("amc_worker_scope"):
            missing()
        if not db.scalar(select(Client.id).filter_by(tenant_id=tenant, id=client)):
            missing()
        if brand is not None and not db.scalar(select(Brand.id).filter_by(tenant_id=tenant, client_id=client, id=brand)):
            missing()
        if write and self.postgres:
            try:
                db.execute(text("SELECT amc_business.lock_client(:tenant,:client)"), {"tenant": tenant, "client": client})
            except DBAPIError as exc:
                if getattr(exc.orig, "sqlstate", None) == "42501":
                    missing()
                raise
        self.rows = select(Record).filter_by(tenant_id=tenant, client_id=client)

    def profiles(self):
        # Each GET resolves both latest heads in one statement/snapshot, even at READ COMMITTED.
        def head(kind, scope):
            return (
                select(Record.id)
                .filter_by(tenant_id=self.tenant, client_id=self.client, kind=kind, scope=scope)
                .order_by(Record.revision.desc())
                .limit(1)
                .scalar_subquery()
            )

        rows = self.rows.where(or_(Record.id == head("company", "company"), Record.id == head("brand", self.brand)))
        current = {r.kind: r for r in self.db.scalars(rows)}
        return current.get("company"), current.get("brand")

    def command_record(self, key):
        return self.db.scalar(self.rows.filter_by(scope=self.brand or "company", actor=self.actor, command_key=key))

    def owned_briefs(self):
        return self.rows.filter_by(scope=self.brand, kind="brief", actor=self.actor)

    def save(self, body, kind):
        signature = digest(canonical([kind, body.model_dump(mode="json")]))
        old = self.command_record(body.key)
        if old:
            if old.request_digest != signature:
                conflict("This command key was already used for different inputs")
            return result(old)
        company, brand = self.profiles()
        cn, bn = sequence(company), sequence(brand)
        if body.expected_revision != (cn if kind == "company" else bn) or kind != "company" and body.expected_company_revision != cn:
            conflict("The profile changed. Reload the current fields and reconcile your draft.")
        if kind == "brief":
            fields = resolved(company, brand)
            payload = dict(
                title=body.title,
                state="internal_draft",
                fields=fields,
                company_revision=cn,
                brand_revision=bn,
                missing=completion(fields)["missing"],
                pending_checks=["source_validation", "kpi_baseline", "kpi_target", "kpi_actual"],
            )
            revision = 1
        else:
            previous = company if kind == "company" else brand
            revision = sequence(previous) + 1
            payload = dict(previous.payload if previous else {})
            for key, item in body.fields.items():
                value = {"value": item} if kind == "company" else item.model_dump()
                payload[key] = {**value, "revision": revision}
        now = self.db.scalar(text("SELECT clock_timestamp()")) if self.postgres else datetime.now(timezone.utc)
        values = dict(
            id=new_id(),
            tenant_id=self.tenant,
            client_id=self.client,
            brand_id=self.brand,
            scope=self.brand or "company",
            kind=kind,
            actor=self.actor,
            command_key=body.key,
            request_digest=signature,
            payload=payload,
            revision=revision,
            created_at=now,
        )
        if self.postgres:
            self.db.execute(text("SELECT amc_business.append_record(:doc,:proof)"), signed_document(self.db, self.actor, Record.__tablename__, values))
        else:
            self.db.execute(Record.__table__.insert().values(**values))
        self.db.commit()
        return result(Record(**values))


def sequence(row):
    return row.revision if row else 0


def resolved(company, brand):
    output = {}
    for field in FIELDS:
        common = (company.payload if company else {}).get(field, {})
        adjust = (brand.payload if brand else {}).get(field, {})
        mode = adjust.get("mode", "inherit")
        source = common if mode == "inherit" else adjust
        output[field] = dict(
            mode=mode,
            value=source.get("value"),
            source="company" if mode == "inherit" else "brand",
            source_revision=source.get("revision", 0),
            override_revision=adjust.get("revision"),
            company_source_revision=common.get("revision", 0),
        )
    return output


def completion(fields):
    missing_keys = [field for field in FIELDS if fields[field]["value"] is None]
    return dict(filled=len(FIELDS) - len(missing_keys), total=len(FIELDS), missing=missing_keys)


def result(row):
    metadata = dict(id=row.id, revision=row.revision, created_at=stamp(row.created_at))
    return {**metadata, **row.payload} if row.kind == "brief" else metadata


def reader(request: Request, user=Depends(current_user), db=Depends(get_db)):
    return Workspace(request, user, db, write=False)


def writer(request: Request, user=Depends(current_user), db=Depends(get_db)):
    return Workspace(request, user, db, write=True)


@router.get(BRAND)
def overview(s=Depends(reader)):
    company, brand = s.profiles()
    fields = resolved(company, brand)
    briefs = s.db.scalars(s.owned_briefs().order_by(Record.created_at.desc(), Record.id.desc()).limit(50))
    return dict(
        company_revision=sequence(company),
        brand_revision=sequence(brand),
        company={k: v["value"] for k, v in resolved(company, None).items()},
        fields=fields,
        completion=completion(fields),
        can_edit=s.role != "viewer",
        briefs=[{"id": r.id, "title": r.payload["title"], "created_at": stamp(r.created_at)} for r in briefs],
    )


@router.post("/business-profile", status_code=201)
def update_company(body: SharedPatch, s=Depends(writer)):
    return s.save(body, "company")


@router.get("/business-profile/revisions/{revision}")
@router.get(BRAND + "/overrides/revisions/{revision}")
def profile_revision(revision: int, s=Depends(reader)):
    kind = "brand" if s.brand else "company"
    row = s.db.scalar(s.rows.filter_by(scope=s.brand or "company", kind=kind, revision=revision))
    if not row:
        missing()
    return {**result(row), "kind": kind, "fields": row.payload}


@router.post(BRAND + "/overrides", status_code=201)
def update_brand(body: BrandPatch, s=Depends(writer)):
    return s.save(body, "brand")


@router.post(BRAND + "/briefs", status_code=201)
def draft(body: DraftBrief, s=Depends(writer)):
    return s.save(body, "brief")


@router.get(BRAND + "/briefs/{brief_id}")
def get_brief(brief_id: str, s=Depends(reader)):
    row = s.db.scalar(s.owned_briefs().filter_by(id=brief_id))
    if not row:
        missing()
    return result(row)


@router.get(BRAND + "/commands/{key}")
@router.get("/business-profile/commands/{key}")
def get_command(key: str, s=Depends(reader)):
    row = s.command_record(key)
    if not row:
        raise HTTPException(404, "Command not found")
    return result(row)
