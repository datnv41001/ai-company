"""Bounded C1 command payloads. All foreign IDs in a payload name exact immutable revisions."""

from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, StrictInt, field_validator, model_validator

from .commercial_scope import CommercialOption, TERRITORY_BY_LABEL, OrderChannel, PaymentOption, ServiceLevel, ORDER_AXES, CONDITION_BY_LABEL

Key = Annotated[str, Field(min_length=1, max_length=96)]
Name = Annotated[str, Field(min_length=1, max_length=160)]
Note = Annotated[str, Field(min_length=1, max_length=1800)]
Subject = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")]
Ref = Annotated[str, Field(min_length=36, max_length=36)]
ListNotes = Annotated[list[Name], Field(max_length=12)]
Amount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3), PlainSerializer(lambda v: format(v.normalize(), "f"), when_used="json")]
Money = Annotated[StrictInt, Field(ge=0, le=9_000_000_000_000_000)]
Unit = Literal["piece", "box", "m²", "tonne", "kg", "service", "machine", "participant", "subscription_month", "subscription_year"]
Currency = Literal["VND", "USD", "EUR", "JPY", "GBP", "AUD", "CAD", "SGD", "THB"]
Visibility = Literal["public", "internal", "restricted"]
Kind = Literal[
    "profile",
    "product",
    "service",
    "variant",
    "offer",
    "availability",
    "policy",
    "market",
    "icp",
    "segment",
    "objective",
    "kpi",
    "guidelines",
    "source",
    "binding",
    "claim",
    "qualification",
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class Window(Input):
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    @field_validator("valid_from", "valid_until")
    @classmethod
    def utc(cls, value):
        if value is not None and value.utcoffset() is None:
            raise ValueError("A timezone is required")
        return value.astimezone(timezone.utc) if value else None

    @model_validator(mode="after")
    def ordered(self):
        if self.valid_from and self.valid_until and self.valid_until <= self.valid_from:
            raise ValueError("Empty validity interval")
        return self


class Profile(Input):
    name: Name
    sells: Note
    audience: Note
    goal: Note


Code = Annotated[str, Field(pattern=r"^[A-Z0-9][A-Z0-9._-]{0,39}$")]
Measure = Annotated[Decimal, Field(max_digits=18, decimal_places=6), PlainSerializer(lambda x: format(x, "f"), when_used="json")]


class Master(Input):
    catalog_code: Code | None = Field(default=None, exclude_if=lambda v: v is None)


class Product(Master):
    name: Name
    sku: Name | None = None


class Variant(Product):
    product: Ref
    sku: Name


class Market(Master):
    name: Name
    locales: Annotated[list[Name], Field(min_length=1, max_length=12)]


class Segment(Input):
    name: Name
    description: Note
    basis: Literal["hypothesis", "fact"]
    source: Ref | None = None
    market: Ref | None = Field(default=None, exclude_if=lambda v: v is None)
    needs: Note | None = Field(default=None, exclude_if=lambda v: v is None)

    @model_validator(mode="after")
    def factual(self):
        if self.basis == "fact" and not self.source:
            raise ValueError("Factual segment requires evidence")
        return self


class Objective(Input):
    name: Name
    level: Literal["company", "brand", "campaign"]
    parent: Ref | None = None
    company_parent: Ref | None = Field(default=None, exclude_if=lambda v: v is None)
    campaign_id: Ref | None = None
    owner: Name

    @model_validator(mode="after")
    def has_scope(self):
        parents = int(bool(self.parent)) + int(bool(self.company_parent))
        if (self.level == "campaign") != bool(self.campaign_id) or parents != int(self.level != "company") or (self.company_parent and self.level != "brand"):
            raise ValueError("Check the objective's parent and campaign scope")
        return self


class KPI(Input):
    objective: Ref | None = Field(default=None, exclude_if=lambda v: v is None)
    company_objective: Ref | None = Field(default=None, exclude_if=lambda v: v is None)
    name: Name
    unit: Name
    method: Note
    window: Name
    source: Ref | None = Field(default=None, exclude_if=lambda v: v is None)
    owner: Name
    baseline: Measure | None = Field(default=None, exclude_if=lambda v: v is None)
    target: Measure | None = Field(default=None, exclude_if=lambda v: v is None)
    actual: Measure | None = Field(default=None, exclude_if=lambda v: v is None)

    @model_validator(mode="after")
    def objective_scope(self):
        if bool(self.objective) == bool(self.company_objective):
            raise ValueError("Select one exact brand, campaign or shared company objective")
        return self


class Guidelines(Input):
    guidance: Note
    tone: Note | None = Field(default=None, exclude_if=lambda v: v is None)


class Placement(Input):
    product: Ref
    variant: Ref | None = None
    market: Ref
    locale: Name
    channel: Name
    region: Name


class Price(Input):
    amount_minor: Money
    currency: Currency
    unit: Unit
    basis_quantity: Amount
    moq: Amount
    tier_min: Amount
    tier_max: Amount | None = None
    tax: Literal["included", "excluded", "unknown"]
    conditions: ListNotes

    @model_validator(mode="after")
    def valid_tier(self):
        if self.tier_max is not None and self.tier_max < max(self.moq, self.tier_min):
            raise ValueError("Empty quantity tier")
        if len(set(self.conditions)) != len(self.conditions):
            raise ValueError("Duplicate commercial conditions")
        self.conditions.sort()
        return self


def price_wording(price):
    """Canonical, unlocalized quotation for C1; C2 can render these fields by locale."""
    decimals = 0 if price["currency"] in ("VND", "JPY") else 2
    amount = Decimal(price["amount_minor"]).scaleb(-decimals)
    return f"{price['currency']} {amount:.{decimals}f} / {price['basis_quantity']} {price['unit']} (tax {price['tax']})"


class Offer(Window):
    placement: Placement
    price: Price | None = None
    policy: Ref
    availability: Ref | None = None


class CommercialApplicability(Input):
    """A published promise covers every order inside its declared range."""

    option: CommercialOption | None = None
    buyer: OrderChannel | None = Field(default=None, exclude_if=lambda v: v is None)
    payment_type: PaymentOption | None = Field(default=None, exclude_if=lambda v: v is None)
    service_level: ServiceLevel | None = Field(default=None, exclude_if=lambda v: v is None)
    unit: Unit | None = None
    minimum: Amount | None = None
    maximum: Amount | None = None

    @model_validator(mode="after")
    def defined(self):
        if (self.minimum is not None or self.maximum is not None) and not self.unit:
            raise ValueError("Quantity conditions require a unit")
        if self.maximum is not None and self.minimum is not None and self.maximum < self.minimum:
            raise ValueError("Empty commercial quantity range")
        for axis, choices in ORDER_AXES.items():
            if self.option in choices and getattr(self, axis) not in (None, self.option):
                raise ValueError("A legacy order option conflicts with the typed dimension")
        if not self.option and not self.unit and not any(getattr(self, axis) for axis in ORDER_AXES):
            raise ValueError("Declare an option or a selling unit")
        return self


class ScopedDeclaration(Window):
    # Missing values retain the original v22 bytes and mean all order conditions.
    applicability: CommercialApplicability | None = Field(default=None, exclude_if=lambda v: v is None)


class Policy(ScopedDeclaration):
    placement: Placement
    warranty: Note | None = None
    payment: Note | None = None
    shipping: Note | None = None


class Availability(ScopedDeclaration):
    placement: Placement
    status: Literal["available", "unavailable", "unknown"]
    observed_at: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def fresh(self):
        if not self.observed_at.utcoffset() and self.observed_at.tzinfo is None:
            raise ValueError("Supply observation timezone")
        if self.observed_at >= self.valid_until:
            raise ValueError("Observation must precede expiry")
        return self


class Assertion(Input):
    applicability: CommercialApplicability | None = Field(default=None, exclude_if=lambda v: v is None)
    placement: Placement
    category: Literal["description", "price", "availability", "warranty", "payment", "comparison", "regulated", "performance"]
    wording: Note
    qualifiers: ListNotes
    offer: Ref | None = None
    price: Price | None = None
    quantity: Amount | None = None
    availability: Ref | None = None
    policy: Ref | None = None

    @model_validator(mode="after")
    def basis(self):
        if self.applicability and self.category not in ("availability", "warranty", "payment"):
            raise ValueError("Commercial applicability belongs to stock and policy declarations")
        if self.category == "price":
            if not self.offer or not self.price or not self.quantity or self.price.tax == "unknown":
                raise ValueError("Price claims require an offer, quantity and known tax basis")
        elif self.offer or self.price or self.quantity:
            raise ValueError("Use the price assertion type")
        if (self.category == "availability") != bool(self.availability) or (self.category in ("payment", "warranty")) != bool(self.policy):
            raise ValueError("Use an exact applicable policy or availability revision")
        if len(set(self.qualifiers)) != len(self.qualifiers):
            raise ValueError("Duplicate qualifiers")
        self.qualifiers.sort()
        return self


class Entry(Input):
    locator: Name
    excerpt: Note
    assertion: Assertion


class Source(Window):
    publisher: Name
    document: Name
    valid_until: datetime
    entries: Annotated[list[Entry], Field(max_length=12)]
    legacy_text: Note | None = None

    @model_validator(mode="after")
    def distinct_locators(self):
        if len({e.locator for e in self.entries}) != len(self.entries):
            raise ValueError("Disambiguate each line or region")
        return self


class Binding(Input):
    source: Ref
    locator: Name
    assertion: Assertion


class Claim(Window):
    binding: Ref
    assertion: Assertion


class Qualification(Window):
    approver_id: Ref
    category: Literal["comparison", "regulated", "performance", "unclassified"]
    basis: Note
    valid_until: datetime


TYPES = {
    "profile": Profile,
    "product": Product,
    "service": Product,
    "variant": Variant,
    "offer": Offer,
    "availability": Availability,
    "policy": Policy,
    "market": Market,
    "icp": Segment,
    "segment": Segment,
    "objective": Objective,
    "kpi": KPI,
    "guidelines": Guidelines,
    "source": Source,
    "binding": Binding,
    "claim": Claim,
    "qualification": Qualification,
}
SENSITIVE = {"comparison", "regulated", "performance"}

# The Solo path covers exact structured values and legacy spellings of those
# values. Other markets and prose remain usable after independent review.
COMMERCIAL_CONDITIONS = set(CONDITION_BY_LABEL)
PLACEMENT_CHANNELS = {"web", "store", "email", "retail", "wholesale", "search", "social", "marketplace"}


def approval_category(assertion):
    category = assertion["category"]
    if category in SENSITIVE:
        # The grant and approval bind the complete immutable assertion, including
        # qualifiers. A domain reviewer must assess all accompanying language.
        return category
    place = assertion["placement"]
    terms = (assertion.get("price") or {}).get("conditions", [])
    free_context = (
        place["channel"] not in PLACEMENT_CHANNELS
        or (place["region"] not in TERRITORY_BY_LABEL and not re.fullmatch(r"[A-Z]{2}(?:-[A-Z0-9]{1,3})?", place["region"]))
        or not re.fullmatch(r"[a-z]{2}(?:-[A-Z]{2})?", place["locale"])
        or any(value not in COMMERCIAL_CONDITIONS for value in [*assertion["qualifiers"], *terms])
    )
    if free_context:
        return "unclassified"
    # Solo may declare a finite set of neutral attributes. Open prose goes to a
    # second reviewer even when its author labels it an ordinary description.
    neutral = {
        "Matte surface",
        "Glossy surface",
        "Rounded",
        "On-site service",
        "Online service",
        "Bề mặt mờ",
        "Bề mặt bóng",
        "Bo tròn",
        "Dịch vụ tại chỗ",
        "Dịch vụ trực tuyến",
    }
    if category == "description" and (assertion["wording"] not in neutral or assertion["qualifiers"]):
        return "unclassified"
    if category == "warranty" and not re.fullmatch(r"[1-9][0-9]? (?:months|tháng)", assertion["wording"]):
        return "unclassified"
    if category == "payment" and assertion["wording"] not in {"Prepaid", "Cash on delivery", "Trả trước", "Thanh toán khi nhận hàng"}:
        return "unclassified"
    if category == "availability" and assertion["wording"] not in {"available", "unavailable"}:
        return "unclassified"
    if category == "price" and assertion["wording"] != price_wording(assertion["price"]):
        return "unclassified"
    return None


class Command(Input):
    key: Key


class RevisionIn(Command):
    subject: Subject
    kind: Kind
    expected_revision: Annotated[int, Field(ge=0)]
    visibility: Visibility
    data: dict


class EventIn(Command):
    preferred_revision: Ref | None = Field(default=None, exclude_if=lambda v: v is None)
    expected_sequence: Annotated[int, Field(ge=0)]
    expected_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    state: Literal["approved", "withdrawn", "disputed", "superseded"]
    reason: Name
    qualification_revision: Ref | None = None


class Target(Input):
    campaign_id: Ref
    brief_id: Ref


class PreviewIn(Command):
    target: Target | None = None
    claims: Annotated[list[Ref], Field(min_length=1, max_length=24)]
    ttl_seconds: Annotated[int, Field(ge=1, le=900)] = 300


class AuthorizeIn(Command):
    target: Target | None = None
    operation: Literal["queue", "qa", "share"]
    snapshot_id: Ref
    digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    previous_receipt: Ref | None = None
