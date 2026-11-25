"""Approved territory aliases and mutually exclusive order options used by C1 selectors."""

from typing import Literal, get_args

# Keep the supplied label in immutable evidence and snapshots; use these IDs only for comparison.
TERRITORIES = {"VN-HN": ("HN", "Hà Nội"), "VN-SG": ("HCM", "TP.HCM"), "VN-DN": ("Đà Nẵng",)}
TERRITORY_BY_LABEL = {label: code for code, labels in TERRITORIES.items() for label in (code, *labels)}

OrderChannel = Literal["retail", "wholesale"]
PaymentOption = Literal["prepaid", "credit"]
ServiceLevel = Literal["standard", "extended"]
CommercialOption = OrderChannel | PaymentOption | ServiceLevel
OPTION_AXES = tuple(get_args(axis) for axis in get_args(CommercialOption))
ORDER_AXES = dict(zip(("buyer", "payment_type", "service_level"), OPTION_AXES, strict=True))
CONDITION_LABELS = {
    "prepaid": ("Prepaid", "Trả trước"),
    "cash_on_delivery": ("Cash on delivery", "Thanh toán khi nhận hàng"),
    "pickup": ("Pickup", "Nhận tại cửa hàng"),
    "delivery": ("Delivery", "Giao hàng"),
}
CONDITION_BY_LABEL = {label: key for key, labels in CONDITION_LABELS.items() for label in labels}


def condition_keys(labels):
    # Opaque prose can match only itself. A canonical ID cannot collide with a free-text value.
    return {("condition", CONDITION_BY_LABEL[x]) if x in CONDITION_BY_LABEL else ("literal", x) for x in labels}


def commercial_basis(data):
    values = dict(data or {})
    option = values.pop("option", None)
    if option:
        axis = next(key for key, choices in ORDER_AXES.items() if option in choices)
        values[axis] = option
    return {key: value for key, value in values.items() if value is not None}


def same_placement(first, second):
    def scope(placement):
        label = placement["region"]
        return placement | {"region": TERRITORY_BY_LABEL.get(label, label)}

    return scope(first) == scope(second)
