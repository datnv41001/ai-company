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


def same_placement(first, second):
    def scope(placement):
        label = placement["region"]
        return placement | {"region": TERRITORY_BY_LABEL.get(label, label)}

    return scope(first) == scope(second)
