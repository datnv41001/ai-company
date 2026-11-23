import os
from collections.abc import Generator
from dotenv import dotenv_values
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session

# Only shared application settings cross the native API startup boundary.
for name, value in dotenv_values().items():
    if value is not None and name in ("DATABASE_URL", "APP_ENV", "JWT_SECRET", "JWT_ISSUER"):
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


def prepare_database(bind):
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
            from .workforce_authority import install_sqlite
            Base.metadata.create_all(conn)
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
        if not set(Base.metadata.tables).issubset(enabled) or not conn.scalar(
            text("SELECT EXISTS (SELECT FROM public.amc_schema_versions WHERE version=10)")
        ):
            raise RuntimeError("Apply the PostgreSQL schema migrations before starting the API")


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as db:
        yield db
