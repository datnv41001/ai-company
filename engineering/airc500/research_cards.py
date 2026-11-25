"""Read-only public reference cards. No URLs, private context or arbitrary queries accepted."""

from pilot_fixture import digest, encoded

CARDS = {
    "offer-window": {
        "topic": "offers",
        "class": "official_platform",
        "publisher": "Google Merchant Center",
        "locale": "en",
        "url": "https://support.google.com/merchants/answer/6324460?hl=en",
        "locator": "Sale price effective date",
        "observation": "An offer may carry a sale-price validity interval.",
        "review_check": "Compare the claim's effective time with the approved local offer interval.",
    },
    "price-basis": {
        "topic": "offers",
        "class": "vendor_workflow",
        "publisher": "Shopify Help Center",
        "locale": "en",
        "url": "https://help.shopify.com/en/manual/products/details/product-pricing/unit-pricing",
        "locator": "Displaying unit prices for products",
        "observation": "Product measurement and the base quantity used to display unit price are separate inputs.",
        "review_check": "Compare package measurement and displayed reference basis before comparing two prices.",
    },
    "bulk-lot": {
        "topic": "offers",
        "class": "community_hypothesis",
        "publisher": "Shopify Community",
        "locale": "en",
        "url": "https://community.shopify.com/t/sell-products-with-minimum-quantity-and-increment-quantity-with-fixed-number-of-units/39933",
        "locator": "Opening merchant question",
        "observation": "One public merchant request distinguishes bottle price, package price and order increments.",
        "review_check": "Ask for scoped terms before assuming unit price implies a one-unit minimum order.",
    },
    "market-series": {
        "topic": "market",
        "class": "market_method",
        "publisher": "U.S. Census Bureau",
        "locale": "en-US",
        "url": "https://www.census.gov/retail/ecommerce/how_surveys_are_collected.html",
        "locator": "Survey Description and Reliability of Estimates",
        "observation": "The retail e-commerce series is estimated from a survey with a defined population and sampling uncertainty.",
        "review_check": "Match population and time window before using a market estimate to contextualize a brief.",
    },
}


def packet(topic):
    if topic not in ("offers", "market"):
        raise ValueError("public catalog topic required")
    return [
        {
            **c,
            "id": key,
            "retrieved": "2026-11-24",
            "snapshot_digest": digest(encoded(c)),
            "rights": "Original short editorial paraphrase; follow publisher link for full source",
            "authority": "Public context for reviewer questions; no authority for a customer's specific product.",
        }
        for key, c in CARDS.items()
        if c["topic"] == topic
    ]


# Answer keys are for broker calibration only. No customer/fixture fact inherits public authority.
EXERCISES = {
    "package": ("offers", "A pack of six is listed at 120 units of currency. Can the same amount be presented as the unit price?", "price-basis", "reject"),
    "expired": ("offers", "A sale ends before an ad is scheduled to go live. Can its price be represented as current?", "offer-window", "reject"),
    "minimum": ("offers", "Does a community merchant question establish the minimum quantity for a separate seller?", "bulk-lot", "request seller terms"),
    "regional": ("market", "Can a national retail estimate establish demand for a particular local merchant?", "market-series", "request scoped observations"),
}


def calibration(topic, answers=None):
    evidence = packet(topic)
    tasks = {key: {"question": row[1]} for key, row in EXERCISES.items() if row[0] == topic}
    if answers is None:
        return {"cards": evidence, "exercises": tasks}
    if set(answers) != set(tasks):
        raise ValueError("all public calibration questions are required")
    return {key: (answers[key].get("reference"), answers[key].get("decision")) == EXERCISES[key][2:] for key in tasks}


if __name__ == "__main__":
    import argparse
    import json

    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("topic", choices=("offers", "market"))
    cli.add_argument("--answers", type=argparse.FileType("r", encoding="utf8"))
    args = cli.parse_args()
    print(json.dumps(calibration(args.topic, json.load(args.answers) if args.answers else None), indent=2))
