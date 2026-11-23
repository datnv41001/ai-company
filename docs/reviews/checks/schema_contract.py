"""Report pre-GA data-model contracts without connecting to a database."""
from app.models import Brand, Campaign, WorkTask, Deliverable, ActionRequest, Membership

def main():
    missing = []
    for model, parent in [(Brand, "client_id"), (Campaign, "brand_id"), (WorkTask, "campaign_id"),
                          (Deliverable, "campaign_id"), (ActionRequest, "campaign_id")]:
        keys = model.__table__.foreign_key_constraints
        if not any({c.name for c in key.columns} == {"tenant_id", parent} for key in keys):
            missing.append(f"{model.__tablename__} lacks a composite tenant/parent foreign key")
    if not {"client_id", "brand_id"} & set(Membership.__table__.columns.keys()):
        missing.append("memberships have no client/brand scope; check for a separate grants model")
    for message in missing:
        print("GAP", message)
    return 1 if missing else 0

if __name__ == "__main__":
    raise SystemExit(main())
