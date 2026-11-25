"""Localize explicitly approved visit pricing while preserving historical adapter digests."""

from decimal import Decimal

from . import c3_assets


def fact_lines(fact, projection):
    price = fact.get("price")
    application = fact.get("applicability") or {}
    if application.get("unit") == "visit":
        # Price and order applicability are disjoint assertion types in C1.
        labels = c3_assets.lexicon(projection["locale"])
        rest = {k: v for k, v in application.items() if k != "unit"}
        lines = c3_assets.fact_lines({**fact, "applicability": rest}, projection)
        return [*lines, f"{labels['unit']}: {'lượt' if projection['locale'] == 'vi-VN' else 'visit'}."]
    if not price or price["unit"] != "visit":
        return c3_assets.fact_lines(fact, projection)
    locale = projection["locale"]
    labels = c3_assets.lexicon(locale)

    def quantity(value):
        unit = "lượt" if locale == "vi-VN" else ("visit" if Decimal(value) == 1 else "visits")
        return f"{c3_assets.number(value, locale)} {unit}"

    digits = 0 if price["currency"] in ("VND", "JPY") else 2
    cash = c3_assets.number(Decimal(price["amount_minor"]).scaleb(-digits), locale, digits)
    tier = f"{labels['from']} {quantity(price['tier_min'])}"
    if price.get("tier_max"):
        tier += f" {labels['to']} {quantity(price['tier_max'])}"
    lines = [
        f"{labels['price']}: {cash} {price['currency']} / {quantity(price['basis_quantity'])}, {labels['tax'][price['tax']]}.",
        f"{labels['minimum']}: {quantity(price['moq'])}.",
        tier + ".",
    ]
    if fact.get("quantity"):
        lines.append(f"{labels['quantity']}: {quantity(fact['quantity'])}.")
    return list(dict.fromkeys([*lines, *price["conditions"], *fact.get("qualifiers", [])]))


def artifacts(workflow, projection, checkpoints):
    # Only the display copy is adapted. Original typed terms remain pinned in the
    # manifest, model prompt and evidence gate for every revision and decision.
    facts = []
    for fact in projection["facts"]:
        if any((fact.get(k) or {}).get("unit") == "visit" for k in ("price", "applicability")):
            facts.append({"id": fact["id"], "wording": " ".join(fact_lines(fact, projection))})
        else:
            facts.append(fact)
    return c3_assets.artifacts(workflow, {**projection, "facts": facts}, checkpoints)


def render(workflow, projection, checkpoints):
    return artifacts(workflow, projection, checkpoints)["customer_preview"]
