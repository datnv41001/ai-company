"""Closed command vocabulary for the local campaign sandbox. Times carry explicit offsets."""
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, field_validator

from .knowledge_contracts import Amount, Input, Unit

Id = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")]
Money = Annotated[int, Field(strict=True, ge=0, le=9_000_000_000_000)]
Positive = Annotated[int, Field(strict=True, ge=1, le=2_147_483_647)]
Note = Annotated[str, Field(min_length=1, max_length=480)]
Seconds = Annotated[int, Field(strict=True, ge=0, le=604800)]


class Command(Input):
    request_id: Id
    plan_id: Id


class ActionTarget(Input):
    contract: Literal["sandbox-capability/1"]
    action_type: Literal["render_preview", "rehearse_placement"]
    channel: Literal["website", "organic_search", "organic_social", "paid_media", "internal"]
    destination: Literal["sandbox_page", "sandbox_search", "sandbox_social", "sandbox_ad_slot", "sandbox_review"]
    group: Literal["copy", "seo", "client_strategy", "client_measurement", "social", "ad", "creative_brief", "calendar"]
    group_digest: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    mode: Literal["manual", "scheduled"]


class Schedule(Command):
    kind: Literal["schedule"]
    action_id: Id
    deliverable_id: Id
    expected_revision: Positive
    expected_digest: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    cost_vnd: Money
    due_at: AwareDatetime
    target: ActionTarget | None = None


class DecideAction(Command):
    kind: Literal["authorize", "cancel"]
    action_id: Id


class Execute(Command):
    kind: Literal["execute"]
    action_id: Id
    outcome: Literal["success", "temporary_failure"] = "success"


class Observation(Command):
    occurred_at: AwareDatetime

    @field_validator("occurred_at", mode="before")
    @classmethod
    def explicit_time(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("Send an explicit ISO timestamp with timezone")
        return value


class SessionEvent(Observation):
    kind: Literal["session"]
    session_id: Id
    actor_key: Id  # Synthetic anonymous visitor key; no email or tracking cookie.
    action_id: Id | None = None


class Appointment(Observation):
    kind: Literal["appointment"]
    contract: Literal["service-appointment/1"]
    appointment_id: Id
    product_id: Id
    unit: Unit
    quantity: Amount
    requested_for: AwareDatetime
    service_scope: Note
    location: Note
    contact_purpose: Literal["appointment_request"]
    session_id: Id | None = None


class IntakeAppointment(Appointment):
    """Internal request whose approved brief can ask for a shift before booking a time."""

    contract: Literal["service-intake/2"]
    quantity: Amount | None
    requested_for: AwareDatetime | None
    location: Note | None


class AppointmentDecision(Observation):
    kind: Literal["appointment_decision"]
    appointment_id: Id
    expected_revision: Positive
    step: Literal["confirm","assign","reassign","reschedule","complete","cancel","no_show"]
    assignee_id: Id | None = None
    confirmed_for: AwareDatetime | None = None
    feedback: Note | None = None


class MaterialsRequest(Input):
    schema_id: Literal["materials_v1"]
    application: Note
    delivery_access: Note | None = None


class ServiceRequest(Input):
    schema_id: Literal["service_v1"]
    service_scope: Note
    equipment_type: Note | None = None


class SeatsRequest(Input):
    schema_id: Literal["seats_v1"]
    program: Note
    delivery_mode: Literal["onsite", "online", "hybrid"]


CommercialDetails = Annotated[MaterialsRequest | ServiceRequest | SeatsRequest, Field(discriminator="schema_id")]


class RFQ(Observation):
    kind: Literal["rfq"]
    rfq_id: Id
    product_id: Id
    unit: Unit
    quantity: Amount | None = None
    location: Note | None = None
    required_date: date | None = None
    contact_purpose: Literal["quote_request", "none"]
    session_id: Id | None = None
    details: CommercialDetails | None = None


class CompleteRFQ(Command):
    kind: Literal["complete_rfq"]
    rfq_id: Id
    expected_revision: Positive
    quantity: Amount
    location: Note
    required_date: date
    contact_purpose: Literal["quote_request"]
    details: CommercialDetails | None = None


class Sales(Observation):
    kind: Literal["sales"]
    rfq_id: Id
    expected_revision: Positive
    step: Literal["assign", "reassign", "accept", "reject", "quote", "order", "confirm", "refund", "cancel", "correct"]
    assignee_id: Id | None = None
    amount_vnd: Money | None = None
    reason: Note | None = None


class Labor(Command):
    kind: Literal["labor"]
    package_id: Id
    phase: Literal["clarification", "editing", "qa", "production"]
    seconds: Seconds
    allocated_cost_vnd: Money | None = None
    observation: Note


class UnitReceipt(Command):
    kind: Literal["unit_receipt"]
    package_id: Id
    review_id: Id


class CostClose(Command):
    kind: Literal["close_unit_cost"]
    package_id: Id
    nonlabor_vnd: Money
    manual_baseline_seconds: Seconds | None = None
    basis: Note


class MeterLine(Input):
    category: Literal["model","compute","tools","human"]
    allocation_id: Id
    amount_vnd: Money


class ReconcileCost(Command):
    kind: Literal["verify_unit_cost"]
    package_id: Id
    inventory_digest: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    lines: Annotated[list[MeterLine], Field(min_length=4,max_length=4)]
    signature: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class Optimization(Command):
    kind: Literal["propose_optimization", "approve_optimization"]
    proposal_id: Id


SandboxCommand = Annotated[
    Schedule | DecideAction | Execute | SessionEvent | RFQ | CompleteRFQ | Sales | Labor | UnitReceipt | CostClose | ReconcileCost | Optimization | Appointment | AppointmentDecision,
    Field(discriminator="kind"),
]
