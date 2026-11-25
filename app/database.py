import os
from collections.abc import Generator
from dotenv import dotenv_values
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session

# Only shared application settings cross the native API startup boundary.
for name, value in dotenv_values().items():
    if value is not None and name in ("DATABASE_URL", "APP_ENV", "JWT_SECRET", "JWT_ISSUER", "AMC_IDENTITY_TRUSTED_PROXIES",
                                      "AMC_DB_PROOF_KEY", "AMC_QUOTA_KEY", "AMC_SESSION_GENERATION","AMC_PUBLIC_ORIGIN"):
        os.environ.setdefault(name, value)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./amc_local.db")
APP_ENV = os.getenv("APP_ENV", "local")

if APP_ENV == "production" and not DATABASE_URL.startswith("postgresql"):
    raise RuntimeError("Production requires PostgreSQL; local SQLite is not multi-tenant-safe.")

args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=args)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    pass


def prepare_database(bind, *, verify_identity=True):
    if bind.dialect.name == "sqlite":
        with bind.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            inspector = inspect(conn)
            if inspector.has_table("memberships") and "client_id" not in {
                c["name"] for c in inspector.get_columns("memberships")
            }:
                conn.exec_driver_sql("ALTER TABLE memberships ADD COLUMN client_id VARCHAR(36) REFERENCES clients(id)")
            # Old SQLite files lack the composite candidate keys referenced by v3.
            first_delivery_upgrade = not inspector.has_table("portal_grants")
            if inspector.has_table("deliverables") and first_delivery_upgrade:
                conn.exec_driver_sql("ALTER TABLE deliverables ADD COLUMN last_editor_id VARCHAR(36) REFERENCES users(id)")
                for table, columns in (("memberships","tenant_id,user_id,client_id"), ("brands","tenant_id,client_id,id"),
                                       ("campaigns","tenant_id,brand_id,id"), ("deliverables","tenant_id,campaign_id,id")):
                    conn.exec_driver_sql(f"CREATE UNIQUE INDEX uq_delivery_{table} ON {table} ({columns})")
            if inspector.has_table("deliverables"):
                columns = {col["name"] for col in inspector.get_columns("deliverables")}
                if "qa_revision" not in columns:
                    conn.exec_driver_sql("ALTER TABLE deliverables ADD COLUMN qa_revision INTEGER NOT NULL DEFAULT 1")
                if "qa_approved_revision" not in columns:
                    conn.exec_driver_sql("ALTER TABLE deliverables ADD COLUMN qa_approved_revision INTEGER")
                if "qa_evidence" not in columns:
                    conn.exec_driver_sql("ALTER TABLE deliverables ADD COLUMN qa_evidence JSON")
                if "qa_approved_digest" not in columns:
                    conn.exec_driver_sql("ALTER TABLE deliverables ADD COLUMN qa_approved_digest VARCHAR(64)")
            if inspector.has_table("users") and "verified_at" not in {c["name"] for c in inspector.get_columns("users")}:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN verified_at DATETIME")
            if inspector.has_table("users") and "credential_epoch" not in {c["name"] for c in inspector.get_columns("users")}:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN credential_epoch INTEGER NOT NULL DEFAULT 1")
            invite_columns = {c["name"] for c in inspector.get_columns("portal_invitations")} if inspector.has_table("portal_invitations") else set()
            if invite_columns and "link_digest" not in invite_columns:
                columns = ",".join(c["name"] for c in inspector.get_columns("portal_invitations"))
                conn.exec_driver_sql("ALTER TABLE portal_invitations RENAME TO old_portal_invitations")
                for index in inspector.get_indexes("old_portal_invitations"):
                    conn.exec_driver_sql("DROP INDEX " + conn.dialect.identifier_preparer.quote(index["name"]))
                Base.metadata.tables["portal_invitations"].create(conn)
                conn.exec_driver_sql(f"INSERT INTO portal_invitations ({columns}) SELECT {columns} FROM old_portal_invitations")
                conn.exec_driver_sql("DROP TABLE old_portal_invitations")
            if invite_columns and "brand_name" not in invite_columns:
                conn.exec_driver_sql("""UPDATE portal_invitations AS i SET brand_name=b.name FROM brands AS b
                    WHERE i.state='pending' AND (b.tenant_id,b.client_id,b.id)=(i.tenant_id,i.client_id,i.brand_id)""")
                conn.exec_driver_sql("""UPDATE portal_invitations AS i SET campaign_name=c.name FROM campaigns AS c
                    WHERE i.state='pending' AND (c.tenant_id,c.brand_id,c.id)=(i.tenant_id,i.brand_id,i.campaign_id)""")
            from .workforce_authority import install_sqlite
            if inspector.has_table("workforce_briefs") and "origin" not in {column["name"] for column in inspector.get_columns("workforce_briefs")}:
                conn.exec_driver_sql("ALTER TABLE workforce_briefs ADD COLUMN origin VARCHAR(12) NOT NULL DEFAULT 'agency'")
                conn.exec_driver_sql("DROP TRIGGER IF EXISTS workforce_check_intake")
            Base.metadata.create_all(conn)
            from .session_state import install_epoch_trigger
            install_epoch_trigger(conn)
            for index in Base.metadata.tables["workforce_runs"].indexes:
                index.create(conn, checkfirst=True)
            if not conn.exec_driver_sql("SELECT 1 FROM sqlite_master WHERE type='trigger' AND name='workforce_check_intake'").scalar():
                install_sqlite(conn)
            for index in Base.metadata.tables["client_reviews"].indexes:
                index.create(conn, checkfirst=True)
            if first_delivery_upgrade:
                conn.exec_driver_sql("""INSERT INTO portal_grants(tenant_id,user_id,client_id,can_comment,can_decide)
                    SELECT tenant_id,user_id,client_id,0,0 FROM memberships WHERE role='client_viewer'""")
        return
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Unsupported database")
    with bind.connect() as conn:
        safe = conn.scalar(text("""SELECT current_user='amc_runtime' AND NOT (
            rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolreplication
            OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member=r.oid)
            OR EXISTS (SELECT 1 FROM pg_class WHERE relnamespace='public'::regnamespace AND relowner=r.oid)
        ) FROM pg_roles r WHERE rolname=current_user"""))
        if not safe:
            raise RuntimeError("PostgreSQL API requires the unprivileged amc_runtime login")
        enabled = set(conn.scalars(text("""SELECT relname FROM pg_class
            WHERE relnamespace='public'::regnamespace AND relrowsecurity""")))
        if not set(Base.metadata.tables).issubset(enabled):
            raise RuntimeError("Apply the PostgreSQL schema migrations before starting the API")
        versions = set(conn.scalars(text("SELECT version FROM public.amc_schema_versions")))
        if 16 in versions and 15 not in versions:
            raise RuntimeError("Isolated schema v16 is missing migration 015; restore a pre-016 backup before upgrading")
        if versions != set(range(2, 26)):
            raise RuntimeError("Apply the PostgreSQL schema migrations before starting the API")
        from migrations.combined_contract import COMMERCIAL_CURRENT, DESK_CURRENT
        if not conn.scalar(text(COMMERCIAL_CURRENT)):
            raise RuntimeError("Rerun the combined migration publisher to install the commercial authority rule")
        if not conn.scalar(text("SELECT to_regclass('amc_business.versions') IS NOT NULL")) or list(conn.scalars(text("SELECT version FROM amc_business.versions ORDER BY version"))) != [1, 2, 3]:
            raise RuntimeError("Apply the compatible business workspace migration")
        if not conn.scalar(text(DESK_CURRENT)):
            raise RuntimeError("Apply the current claim desk read capability")
        from migrations.c3_writer_contract import WRITER_FENCE
        if not conn.scalar(text(WRITER_FENCE)):
            raise RuntimeError("Apply the compatible C3 delivery writer fence")
        if not conn.scalar(text("""
            SELECT EXISTS (SELECT FROM pg_attribute WHERE attrelid='public.workforce_briefs'::regclass
                            AND attname='origin' AND NOT attisdropped)
               AND COALESCE(has_function_privilege(current_user,
                     to_regprocedure('amc_acl.lock_c3_internal_target(text,text,text,text,text)'), 'EXECUTE'), false)
        """)):
            raise RuntimeError("Run the C3 task migration publisher before starting this API")
        if not verify_identity:
            return
        from .access import set_context
        from .security import access_key, sign_actor
        access_key()
        from .session_keys import verify_config
        verify_config(conn)
        with Session(conn) as session:
            set_context(session, actor="startup")
            sign_actor(session, "startup")
            if not session.scalar(text("SELECT amc_acl.authenticated_actor()")):
                raise RuntimeError("Identity signing configuration differs between migration publisher and API")


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as db:
        yield db
