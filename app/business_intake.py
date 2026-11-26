"""Plan-approved synthetic buyer intake. The issued schema travels with the page and CRM receipt."""
from decimal import Decimal
import re
import unicodedata
from typing import Annotated, Literal

from fastapi import HTTPException
from pydantic import Field, StrictBool

from . import c3_assets
from .knowledge_contracts import Input
from .knowledge_store import canonical, conflict, digest


class IntakeField(Input):
    id: Literal["box_count", "quantity", "destination", "need_date", "site", "receiving_shift", "preferred_time"]
    required: StrictBool = True


Selections = Annotated[list[IntakeField], Field(min_length=1, max_length=7)]
LABELS = {
    "box_count": ("số hộp", "number of boxes"), "quantity": ("số lượng", "quantity"),
    "destination": ("địa bàn", "delivery area"), "need_date": ("thời điểm cần hàng", "required delivery date"),
    "site": ("địa điểm", "location"), "receiving_shift": ("ca nhận hàng cần quan sát", "receiving shift to observe"),
    "preferred_time": ("khung giờ mong muốn", "preferred time"),
}
LOCATIONS = (("north", "Cơ sở thử A", "Test site A"), ("south", "Cơ sở thử B", "Test site B"))
DAYS = (("2", "Sau hai ngày", "In two days"), ("7", "Sau một tuần", "In one week"))
SHIFTS = (("morning", "Ca sáng", "Morning shift"), ("evening", "Ca chiều", "Evening shift"), ("night", "Ca đêm", "Night shift"))
# Mapping and choices are controlled by the server, including for API-selected fields.
FIELDS = {
    "box_count": ("quantity", ()), "quantity": ("quantity", ()),
    "destination": ("location", LOCATIONS), "site": ("location", LOCATIONS),
    "need_date": ("required_date", DAYS), "preferred_time": ("requested_for", DAYS),
    "receiving_shift": ("receiving_shift", SHIFTS),
}


BUYER_REQUEST = re.compile(
    r"\b(?:đặt lịch|hẹn lịch|yêu cầu báo giá|nhận báo giá|xin báo giá|book(?:ing)?|schedul(?:e|ing)|"
    r"request (?:a |an )?(?:quote|quotation|appointment)|get a quote)\b"
)


def submitted_fields(intent, *, strict=False):
    lookup = {label: key for key, names in LABELS.items() for label in names}
    result = []
    for item in intent.get("requirements", []):
        words = unicodedata.normalize("NFC", item).casefold().strip().rstrip(".")
        match = re.search(r"(?:^|, | và | and )(?:ghi|cung cấp|gửi kèm|include|provide) (.+)$", words)
        if match:
            values = re.split(r",\s*| và | and ", match[1])
            if all(value in lookup for value in values):
                result.extend(lookup[value] for value in values)
            elif strict and BUYER_REQUEST.search(words[:match.start()]):
                conflict("The buyer request includes an unsupported intake field. Clarify the brief before approving a plan")
    return list(dict.fromkeys(result))


def issue(plan, projection, selection, source):
    action, unit = plan["buyer_action"], plan["selling_unit"]
    vi = plan["locale"] == "vi-VN"
    brief_fields = submitted_fields(projection["task_intent"], strict=True)
    defaults = (["box_count" if unit == "box" else "quantity", "destination", "need_date"] if action == "rfq"
                else ["quantity", "site", "preferred_time"])
    allowed = set(defaults) | ({"quantity"} if action == "rfq" else {"receiving_shift"})
    chosen = selection or [IntakeField(id=k) for k in (brief_fields or defaults)]
    ids = [f.id for f in chosen]
    mappings = [FIELDS[k][0] for k in ids]
    if (not set(ids) <= allowed or len(set(mappings)) != len(ids)
            or not set(brief_fields) <= {f.id for f in chosen if f.required} or not any(f.required for f in chosen)):
        conflict("Choose distinct fields for this buyer journey and retain the required fields from the brief")
    fields = []
    for choice in chosen:
        target, options = FIELDS[choice.id]
        field = {"id": choice.id, "required": choice.required, "label": LABELS[choice.id][0 if vi else 1],
                 "maps_to": target, "type": "enum" if options else "integer"}
        if options:
            field["options"] = [{"value": value, "label": local if vi else en} for value, local, en in options]
        else:
            unit_label = c3_assets.lexicon(plan["locale"])["units"].get(unit, unit)
            if vi and unit in {"service", "visit"}:
                unit_label = {"service": "dịch vụ", "visit": "lượt"}[unit]
            field.update(unit=unit, unit_label=unit_label, minimum=1, maximum=100)
        fields.append(field)
    thresholds = {Decimal(str(f["price"]["moq"])) for f in projection["facts"]
                  if f.get("price") and f["price"].get("moq") is not None and f["price"]["unit"] == unit}
    value = {
        "version": "business-intake/1", "revision": plan["revision"], "action": action, "locale": plan["locale"],
        "plan_id": plan["id"], "subject": plan["product_id"], "unit": unit, "fields": fields,
        "source": source,
        "selection": "plan" if selection else ("brief" if brief_fields else "journey_defaults"),
        "measurement_digest": (plan.get("measurement_contract") or {}).get("digest"),
        "consent": {"purpose": "quote_request" if action == "rfq" else "appointment_request", "required": True,
                    "label": ("Tôi đồng ý gửi yêu cầu thử cho bộ phận phụ trách." if vi
                              else "I agree to send this test request to the responsible team.")},
        "qualification": {"accept_inquiries": True, "minimum_order_quantities": sorted(format(v, "f") for v in thresholds)},
    }
    return {**value, "digest": digest(canonical(value))}


def funnel(plan, state):
    if not plan or not (contract := plan.get("intake_contract")):
        return None
    def bound(source):
        return (source and source.get("plan_id") == plan["id"] and source.get("plan_digest") == plan["digest"]
                and source.get("intake_contract_digest") == contract["digest"])
    visits = {key: row for key, row in state["sessions"].items() if bound(row.get("landing_source"))}
    bucket = "leads" if contract["action"] == "rfq" else "appointments"
    entries = [r for r in state[bucket].values() if r["plan_id"] == plan["id"]]
    matched = [r for r in entries if r.get("session_id") in visits and r.get("intake", {}).get("contract_digest") == contract["digest"]
               and r.get("landing_source") == visits[r["session_id"]]["landing_source"]]
    return {"contract_digest": contract["digest"], "window": "approved_plan_lifetime", "action": contract["action"],
            "landing_visits": len(visits), "valid_submissions": len(matched),
            "manual_requests": sum(not r.get("landing_source") for r in entries),
            **({"qualified_quotes": sum(not r["missing"] for r in matched), "orders": sum(r["ordered"] for r in matched)}
               if bucket == "leads" else {"confirmed": sum(any(e["event"] == "confirmed" for e in r["history"]) for r in matched)})}


def validate_answers(contract, expected, answers, consent):
    if expected != contract["digest"]:
        raise HTTPException(412, "Reload the approved intake contract")
    if consent is not True:
        raise HTTPException(422, "Consent is required for the stated intake purpose")
    fields = {f["id"]: f for f in contract["fields"]}
    if not answers.keys() <= fields.keys() or any(f["required"] and k not in answers for k, f in fields.items()):
        raise HTTPException(422, "Send only the declared fields and include every required answer")
    mapped = {}
    for key, value in answers.items():
        field = fields[key]
        if field["type"] == "integer":
            valid = type(value) is int and field["minimum"] <= value <= field["maximum"]
        else:
            valid = isinstance(value, str) and value in {o["value"] for o in field["options"]}
        if not valid:
            raise HTTPException(422, f"Invalid selection for {key}")
        mapped[field["maps_to"]] = value
    return mapped
