"""Approved service KPI definitions and their reconciliation against sandbox receipts."""

from datetime import timedelta
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .knowledge_store import aware, parse_time, stamp


class MeasurementDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: Literal["appointment-measurement/1"]
    business_outcome: Literal["appointment.confirmed_per_requested", "appointment.completed_per_confirmed"]
    window_days: int = Field(ge=1, le=365)
    owner_role: Literal["service_operations", "sales_operations"]


EVENTS = {
    "appointment.confirmed_per_requested": ("confirmed", "requested"),
    "appointment.completed_per_confirmed": ("completed", "confirmed"),
}
ELIGIBILITY = {
    "requested": "valid_service_request_with_consent",
    "confirmed": "staff_confirmation_with_scheduled_time",
    "completed": "service_completion_by_assignee",
}
EVENT_LABELS = {
    "vi": {"requested": "yêu cầu đặt lịch hợp lệ", "confirmed": "lịch do nhân sự xác nhận", "completed": "buổi do người được giao xác nhận hoàn tất"},
    "en": {"requested": "eligible booking requests", "confirmed": "staff-confirmed appointments", "completed": "visits completed by the assigned staff"},
}
OWNERS = {"service_operations": ("Vận hành dịch vụ", "Service operations"), "sales_operations": ("Sales", "Sales")}


def terms(definition):
    numerator, denominator = EVENTS[definition["business_outcome"]]
    return {
        **definition,
        "numerator": {"event": numerator, "eligibility": ELIGIBILITY[numerator]},
        "denominator": {"event": denominator, "eligibility": ELIGIBILITY[denominator]},
        "window": "rolling_utc_(start,end]_denominator_cohort",
        "unit": "ratio",
        "aggregation": "distinct_appointment_id",
        "cancellations": "retain_prior_eligible_events_report_separately",
        "refunds": "not_a_monetary_outcome",
        "missing_attribution": "include_and_report_separately",
        "reconciliation": "join_authorized_lifecycle_receipts_by_plan_and_appointment_id",
    }


def bind(kpi):
    if not (definition := kpi.data.get("measurement")):
        return None
    return {**terms(definition), "id": kpi.id, "revision": kpi.revision, "digest": kpi.digest}


def legacy_statement(locale):
    if locale.lower().startswith("vi"):
        return "Phép đo chính của lịch hẹn chưa có định nghĩa cấu trúc được duyệt. Cần đối soát với người phụ trách trước khi báo cáo tỷ lệ."
    return "The appointment KPI has no approved structured definition. Confirm the measure with its owner before reporting a rate."


def expected_statement(projection):
    if contract := projection.get("measurement_contract"):
        return statement(contract, projection["locale"])
    if projection.get("task_intent", {}).get("buyer_action") == "appointment":
        return legacy_statement(projection["locale"])
    return None


def secondary_statement(locale):
    if locale.lower().startswith("vi"):
        return "Chỉ số phụ: số phiên web ghi nhận trong cùng kỳ, tính theo mã phiên."
    return "Secondary metric: recorded web sessions in the same window, counted by session ID."


def editorial_method(projection, proposed):
    expected = expected_statement(projection)
    if not expected:
        return proposed
    if projection.get("measurement_contract"):
        secondary = secondary_statement(projection["locale"])
        # Keep an independently verifiable secondary clause even if another clause
        # from the same proposed method changes the primary denominator.
        if secondary in (proposed or "").splitlines():
            return expected + "\n" + secondary
    return expected


def statement(contract, locale):
    vi = locale.lower().startswith("vi")
    labels = EVENT_LABELS["vi" if vi else "en"]
    n, d = (labels[contract[key]["event"]] for key in ("numerator", "denominator"))
    days = contract["window_days"]
    owner = OWNERS[contract["owner_role"]][0 if vi else 1]
    if vi:
        return (
            f"KPI chính trong {days} ngày: số {n} trên số {d}. {owner} đối soát mỗi mã hẹn một lần. "
            "Giữ các sự kiện đủ điều kiện trước khi hủy. Tách hủy, vắng mặt và thiếu nguồn; hoàn tiền không đổi tỷ lệ."
        )
    return (
        f"Primary KPI over {days} days: {n} divided by {d}. {owner} reconciles each appointment ID once. "
        "Retain qualifying events before cancellation. Report cancellations, no-shows and missing attribution separately; refunds do not change the rate."
    )


OTHER_PRIMARY = re.compile(
    r"\b(?:kpi chính|phép đo chính|primary (?:kpi|metric)|main (?:metric|kpi))\b"
    r"|\b(?:tỷ lệ|tỉ lệ|conversion rate|confirmation rate).{0,160}\b(?:trên|chia cho|divided by|per)\b"
    r"|\b(?:lịch|booking|appointment).{0,80}\b(?:trên lượt (?:vào|xem)|per (?:page |website )?visits?)\b",
    re.I,
)


def quality_issues(groups, projection):
    expected = expected_statement(projection)
    if not expected:
        return []
    strict_fields = {("measurement", "measurement_method"), ("client_measurement", "method"), ("ad", "measurement")}
    issues = []
    for group, fields in groups.items():
        for field, value in fields.items():
            if (group, field) in strict_fields:
                accepted = {expected}
                if projection.get("measurement_contract"):
                    accepted.add(expected + "\n" + secondary_statement(projection["locale"]))
                if value not in accepted:
                    issues.append({"group": group, "field": field, "reason": "primary_measurement_mismatch"})
            elif projection.get("measurement_contract") and OTHER_PRIMARY.search(" ".join(value.split())):
                # Named rate claims belong in the signed measurement slots. Other prose and
                # unrecognized paraphrases still receive ordinary Marketing evidence review.
                issues.append({"group": group, "field": field, "reason": "unbound_measurement_definition"})
    return issues


def matched_landing(session, appointment, expected_scope):
    """Both receipts must bind the same scoped edition. Legacy receipts only recorded a package ID and digest."""
    source = session.get("landing_source")
    if not source or not expected_scope or source != appointment.get("landing_source"):
        return False
    required = ("tenant_id", "client_id", "brand_id", "campaign_id", "plan_digest", "document_id",
                "studio_revision", "package_id", "package_version", "package_digest", "file_digest")
    return (all(source.get(key) for key in required) and all(source.get(k) == v for k, v in expected_scope.items())
            and source["package_digest"] == session.get("landing_digest") == appointment.get("landing_digest")
            and source["package_id"] == session.get("landing_package") == appointment.get("landing_package"))


def evaluate(contract, plan_id, state, as_of, locale="vi-VN", *, landing_scope=None):
    """Request/confirmation cohorts include only eligible transitions observed by the cutoff."""
    end = aware(as_of)
    start = end - timedelta(days=contract["window_days"])
    numerator = denominator = cancelled = no_show = unattributed = landing_count = media_count = 0
    for row in state["appointments"].values():
        if row["plan_id"] != plan_id:
            continue
        # The journal already verified staff authority, assignment and consent at write time.
        events = {}
        for history in row["history"]:
            occurred = parse_time(history["at"])
            # Rescheduling retains the case's confirmed state. It does not establish
            # a second confirmation, even when the new slot falls inside the window.
            if occurred <= end and history.get("step") not in {"reschedule","reassign"}:
                events.setdefault(history["event"], occurred)
        anchor = events.get(contract["denominator"]["event"])
        if anchor is None or not start < anchor <= end:
            continue
        denominator += 1
        achieved = events.get(contract["numerator"]["event"])
        numerator += int(achieved is not None and achieved >= anchor)
        cancelled += int("cancelled" in events)
        no_show += int("no_show" in events)
        session = state["sessions"].get(row.get("session_id"))
        in_scope = session and session["plan_id"] == plan_id and parse_time(session["occurred_at"]) <= events["requested"]
        # Intake accepts media IDs only for already executed actions in the same plan.
        media = bool(in_scope and session.get("action_id"))
        landing = bool(in_scope and matched_landing(session, row, landing_scope))
        landing_count += int(landing)
        media_count += int(media)
        unattributed += int(not (landing or media))
    return {
        "contract": contract,
        "definition": statement(contract, locale),
        "plan_id": plan_id,
        "window_start_exclusive": stamp(start),
        "as_of_inclusive": stamp(end),
        "numerator": numerator,
        "denominator": denominator,
        "ratio": numerator / denominator if denominator else None,
        "cancelled": cancelled,
        "no_show": no_show,
        "unattributed": unattributed,
        "attributed": denominator - unattributed,
        "attribution": {"landing_asset": landing_count, "media_action": media_count,
                        "unknown_media_action": denominator - media_count, "neither": unattributed},
        "source": "sandbox_appointment_receipts",
        "secondary_metrics": [
            {
                "metric_id": "web.sessions",
                "unit": "session_count",
                "value": sum(s["plan_id"] == plan_id and start < parse_time(s["occurred_at"]) <= end for s in state["sessions"].values()),
            }
        ],
    }
