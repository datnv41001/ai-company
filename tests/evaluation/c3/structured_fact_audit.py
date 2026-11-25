"""Score the rendering of frozen commercial facts in existing local artifacts. No model or service calls."""

import argparse
from collections import Counter
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import unicodedata

PINS = {
    "study": ("993f93551657734fbea73f6c8898633a18df9dd573fcd0ff78b5e01653bc3346", 10),
    "recovery": ("c497ff707c986acaa3c48ba799ab1a378f194d3e7cd4262834d41a4aae0fe477", 20),
}
RELEASES = {"WF-03": "WF-03/research-strategy-draft@3", "WF-13": "WF-13/landing-seo-draft@6"}
SURFACES = ("before.preview", "before.terms", "after.preview", "after.terms")
UNITS = {
    "piece": ("chiếc", "piece", "pieces"),
    "box": ("hộp", "box", "boxes"),
    "m²": ("m²", "m²", "m²"),
    "machine": ("máy", "machine", "machines"),
    "participant": ("người", "person", "people"),
    "kg": ("kg", "kg", "kg"),
    "tonne": ("tấn", "tonne", "tonnes"),
    "visit": ("lượt", "visit", "visits"),
    "subscription_month": ("tháng thuê bao", "subscription month", "subscription months"),
    "subscription_year": ("năm thuê bao", "subscription year", "subscription years"),
}
LABELS = {
    "vi-VN": ("giá tham khảo", "đơn tối thiểu", "áp dụng từ", "đến", "số lượng đối chiếu"),
    "en-US": ("indicative price", "minimum order", "applies from", "to", "quoted quantity"),
}
TAX = {
    "included": ("đã gồm thuế", "tax included"),
    "excluded": ("chưa gồm thuế", "tax excluded"),
    "unknown": ("chưa xác định thuế", "tax treatment unconfirmed"),
}
APPLICATION = {
    "option": ("phương án", "option"),
    "buyer": ("nhóm mua", "buyer"),
    "payment_type": ("thanh toán", "payment"),
    "service_level": ("mức dịch vụ", "service level"),
    "unit": ("đơn vị", "unit"),
    "minimum": ("đơn tối thiểu", "minimum order"),
    "maximum": ("tối đa", "maximum"),
}
VALUES = {
    "retail": ("bán lẻ", "retail"),
    "wholesale": ("bán sỉ", "wholesale"),
    "prepaid": ("trả trước", "prepaid"),
    "credit": ("trả sau", "credit"),
    "standard": ("tiêu chuẩn", "standard"),
    "extended": ("mở rộng", "extended"),
}
COMMERCIAL = re.compile(r"\b(?:vnd|usd|eur|jpy|giá tham khảo|indicative price)\b|[₫$€¥]")


def require(test, message):
    if not test:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value, *, ascii_only=False):
    return sha(json.dumps(value, ensure_ascii=ascii_only, sort_keys=True, separators=(",", ":")).encode())


def norm(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def constraints(fact):
    sources = {}
    for key, values in (("condition", (fact.get("price") or {}).get("conditions", [])), ("qualifier", fact["qualifiers"])):
        for index, value in enumerate(values, 1):
            if value.strip():
                sources.setdefault(norm(value), []).append(f"{key}.{index}")
    return {"|".join(keys): value for value, keys in sources.items()}


def rule_names(fact):
    names = (
        [
            "amount_minor",
            "currency",
            "basis_quantity",
            "price_unit",
            "tax",
            "moq_with_unit",
            "tier_min_with_unit",
            "tier_max_with_unit" if fact["price"].get("tier_max") is not None else "open_upper_tier",
        ]
        if fact.get("price")
        else ["declaration"]
    )
    if fact.get("quantity") is not None and fact.get("price"):
        names.append("quoted_quantity_with_unit")
    names.extend(constraints(fact))
    names.extend("applicability." + k for k, v in (fact.get("applicability") or {}).items() if v is not None)
    return names


def check(status, expected=None, observed=None):
    return {"status": status, "expected": expected, "observed": observed}


def number(raw, locale):
    grouping, point = (".", ",") if locale == "vi-VN" else (",", ".")
    expression = rf"(?:[0-9]{{1,3}}(?:{re.escape(grouping)}[0-9]{{3}})+|[0-9]+)(?:{re.escape(point)}[0-9]+)?"
    if not re.fullmatch(expression, raw):
        return None
    return Decimal(raw.replace(grouping, "").replace(point, "."))


def number_string(value):
    decimal = Decimal(str(value))
    return str(int(decimal)) if decimal == decimal.to_integral_value() else format(decimal.normalize(), "f")


def numeric(raw, expected, locale, scale=0):
    parsed = number(raw, locale)
    if parsed is None:
        return check("inconclusive", str(expected), raw)
    value = parsed.scaleb(scale)
    return check("matched" if value == Decimal(str(expected)) else "mismatch", number_string(expected), number_string(value))


def unit(raw, code, amount, locale):
    if code not in UNITS:
        return check("inconclusive", code, raw)
    expected = UNITS[code][0 if locale == "vi-VN" else (1 if Decimal(str(amount)) == 1 else 2)]
    return check("matched" if norm(raw) == expected else "mismatch", expected, raw)


def measure(raw, quantity, code, locale):
    token = re.fullmatch(r"([0-9][0-9.,]*) (.+)", raw)
    if not token:
        return check("inconclusive", f"{quantity} {code}", raw)
    values = [numeric(token[1], quantity, locale), unit(token[2], code, quantity, locale)]
    states = [v["status"] for v in values]
    return check("mismatch" if "mismatch" in states else "inconclusive" if "inconclusive" in states else "matched", f"{quantity} {code}", raw)


def clause(line, value):
    # Matching at a sentence boundary prevents a second fact, or a negated substring,
    # from certifying the current fact. Dot-separated decimals remain intact.
    text = norm(value).rstrip(".")
    return bool(text and re.search(r"(?:^|(?<=\. ))" + re.escape(text) + r"(?:\.(?= |$)|$)", line))


def score_line(fact, line, locale):
    rows = {r: check("inconclusive") for r in rule_names(fact)}
    if line is None or locale not in LABELS:
        return rows
    line = norm(line)
    price = fact.get("price")
    if price:
        label, minimum, start, end, selected = LABELS[locale]
        # The amount, currency, basis, price unit and tax must be in the same quotation.
        # The upper bound is read only from that quotation's tier sentence.
        match = re.match(re.escape(label) + r": ([0-9][0-9.,]*) ([a-z]{3}) / ([0-9][0-9.,]*) ([^,]+), ([^.]+)\.(?: |$)", line)
        if match:
            amount, currency, basis, code, tax = match.groups()
            rows["amount_minor"] = numeric(amount, price["amount_minor"], locale, 0 if price["currency"] in ("VND", "JPY") else 2)
            rows["currency"] = check("matched" if currency.upper() == price["currency"] else "mismatch", price["currency"], currency.upper())
            rows["basis_quantity"] = numeric(basis, price["basis_quantity"], locale)
            rows["price_unit"] = unit(code, price["unit"], price["basis_quantity"], locale)
            expect = TAX[price["tax"]][locale == "en-US"]
            rows["tax"] = check("matched" if tax == expect else "mismatch", expect, tax)
        phrases = re.split(r"\.(?: +|$)", line)

        def labeled(label):
            matches = [p[len(label) :] for p in phrases if p.startswith(label)]
            return matches[0] if len(matches) == 1 else None

        for key, field, label in (("moq_with_unit", "moq", minimum), ("quoted_quantity_with_unit", "quantity", selected)):
            observed = labeled(label + ": ")
            if key in rows and observed:
                rows[key] = measure(observed, price.get(field, fact.get(field)), price["unit"], locale)
        tier = labeled(start + " ")
        if tier:
            parts = tier.split(" " + end + " ")
            rows["tier_min_with_unit"] = measure(parts[0], price["tier_min"], price["unit"], locale)
            if price.get("tier_max") is not None:
                rows["tier_max_with_unit"] = (
                    measure(parts[1], price["tier_max"], price["unit"], locale) if len(parts) == 2 else check("mismatch", str(price["tier_max"]), tier)
                )
            else:
                rows["open_upper_tier"] = check("matched" if len(parts) == 1 else "mismatch", "unbounded", tier)
    else:
        rows["declaration"] = check("matched" if clause(line, fact["wording"]) else "unconfirmed", fact["wording"], line)
    for k, value in constraints(fact).items():
        rows[k] = check("matched" if clause(line, value) else "unconfirmed", value, line)
    english = locale == "en-US"
    for k, value in (fact.get("applicability") or {}).items():
        if value is None or k not in APPLICATION:
            continue
        label = APPLICATION[k][english] + ": "
        matches = [v[len(label) :] for v in re.split(r"\.(?: +|$)", line) if v.startswith(label)]
        if len(matches) == 1:
            if k in ("minimum", "maximum"):
                rows["applicability." + k] = numeric(matches[0], value, locale)
            elif k == "unit":
                rows["applicability." + k] = unit(matches[0], value, 1, locale)
            elif value in VALUES:
                expected = VALUES[value][english]
                rows["applicability." + k] = check("matched" if expected == matches[0] else "mismatch", expected, matches[0])
    return rows


def expected_facts(case, correction):
    facts = []
    for idx, source in enumerate(case["facts"], 1):
        fact = deepcopy(source)
        fact["handle"] = f"F{idx}"
        if isinstance(fact["qualifiers"], str):
            fact["qualifiers"] = [fact["qualifiers"]] if fact["qualifiers"] else []
        if correction and (fact.get("price") or {}).get("unit") == "service":
            require(correction["unit_before"] == "service" and correction["source_excerpt"] == fact["wording"], "Corrected source differs from frozen card")
            allowed = {"/lượt.": "visit", "/người.": "participant"}
            require(
                any(fact["wording"].endswith(text) and code == correction["unit_confirmed"] for text, code in allowed.items()), "Unit not attested by source"
            )
            require(
                all(correction.get(k) for k in ("source", "binding", "claim", "offer", "original_offer", "original_claim")), "Missing correction provenance"
            )
            fact["price"]["unit"] = correction["unit_confirmed"]
        facts.append(fact)
    return facts


def fact_signature(fact):
    # Compare immutable fields only. Public price wording is canonicalized by C1.
    price = deepcopy(fact.get("price"))
    if price:
        for k in ("amount_minor", "basis_quantity", "moq", "tier_min", "tier_max"):
            price[k] = number_string(price[k]) if price.get(k) is not None else None
    return (
        fact.get("category", "description"),
        price,
        number_string(fact["quantity"]) if fact.get("quantity") is not None else None,
        fact.get("qualifiers", []),
        None if price else fact.get("wording"),
        {k: v for k, v in (fact.get("applicability") or {}).items() if v is not None},
    )


def audit_surface(text, facts, references, locale):
    lines = [norm(line) for line in (text or "").splitlines() if line.strip()]
    label = LABELS[locale][0] + ":"
    prices = [line for line in lines if line.startswith(label)]
    priced = [f for f in facts if f.get("price")]
    results = {}
    consumed = set()
    extra = []
    for f in facts:
        ref = references.get(f["handle"])
        if f.get("price"):
            exact = [line for line in prices if ref and line == norm(ref)]
            # A unique expected receipt line identifies the correct commercial subject.
            # With several quotation cards, a modified line cannot safely be assigned
            # by amount alone; assigning it to a different source would inflate coverage.
            line = exact[0] if len(exact) == 1 else (prices[0] if len(priced) == len(prices) == 1 else None)
            if line and len(priced) > 1 and sum(norm(v) == line for v in references.values()) != 1:
                line = None
            if line and len(priced) > 1:
                fingerprint = score_line(f, ref, locale)
                if any(fingerprint[k]["status"] != "matched" for k in ("amount_minor", "currency", "basis_quantity", "price_unit")):
                    line = None
        else:
            matches = [line for line in lines if clause(line, f["wording"])]
            exact = [line for line in matches if ref and line == norm(ref)]
            line = exact[0] if exact else next(iter(set(matches))) if len(set(matches)) == 1 else None
        if line:
            consumed.add(line)
            if ref and line.startswith(norm(ref)) and COMMERCIAL.search(line[len(norm(ref)) :]):
                extra.append(line[len(norm(ref)) :].strip())
        checks = score_line(f, line, locale)
        results[f["handle"]] = {
            "fixture_fact": f["id"],
            "declaration_observed": line,
            "checks": checks,
            "matches_recorded_reference": bool(line and ref and line == norm(ref)),
        }
    # Flag additional native-format quotes and mentions elsewhere. They cannot
    # disappear merely because the mandatory approved declaration was also present.
    other = extra + [line for line in lines if line not in consumed and COMMERCIAL.search(line)]
    return {"text_sha256": sha(text.encode()) if isinstance(text, str) else None, "facts": results, "additional_commercial_text_for_review": other}


def hash_pin(value, length=64):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{" + str(length) + r"}", value) is not None


def bind_handles(facts, locale, references, projection=None):
    # The database assigns F1, F2, ... in immutable claim-ID order. Fixture
    # enumeration order does not establish a relationship with a source.
    available = {r["handle"]: r["text"] for r in references}
    require(len(available) == len(references) == len(facts), "Wrong reference population")
    bound = set()
    for fact in facts:
        if projection is not None:
            candidates = [f["id"] for f in projection["facts"] if fact_signature(f) == fact_signature(fact)]
        elif fact.get("price"):
            candidates = [handle for handle, text in available.items() if norm(text).startswith(LABELS[locale][0] + ":")]
            if len(candidates) > 1:
                candidates = [h for h in candidates if all(v["status"] == "matched" for v in score_line(fact, available[h], locale).values())]
        else:
            candidates = [handle for handle, text in available.items() if clause(norm(text), fact["wording"])]
        require(
            len(candidates) == 1 and candidates[0] in available and candidates[0] not in bound,
            "Projected facts differ from frozen fixture or have an ambiguous reference",
        )
        fact["handle"] = candidates[0]
        bound.add(candidates[0])
    if projection is not None:
        require(len(projection["facts"]) == len(facts), "Extra projected facts")


def audit_case(case, record, paired, checkout, fixture_sha, mode):
    require(record["case"] == case["id"] and record["checkout"] == checkout and record["cases_sha256"] == fixture_sha, "Case, checkout or fixture SHA mismatch")
    require(record["workflow"] == RELEASES[case["workflow"]] and record["arm"] == "improved" and record["origin"] == "internal", "Unexpected release/role")
    require(
        record.get("run_id") and record["manifest"].get("id") and hash_pin(record["manifest"]["digest"]) and hash_pin(record["projection_digest"]),
        "Missing run/manifest identity",
    )
    correction = record.get("correction")
    require(bool(correction) == (mode == "recovery"), "Incorrect correction mode")
    facts = expected_facts(case, correction)
    projection = None
    if mode == "study":
        require(paired and paired["case"] == case["id"] and paired["workflow"] == record["workflow"], "Missing matching paired artifact")
        projection = paired["projection"]
        require(digest(projection, ascii_only=True) == record["projection_digest"], "Projection digest mismatch")
        require(projection["locale"] == case["locale"] and projection["product"] == case["product"], "Wrong product/locale")
    doc, edit = record["deliverable"], record["edited_example"]
    bind_handles(facts, case["locale"], edit["before"]["references"], projection)
    output = {
        "run": record["run_id"],
        "manifest": record["manifest"],
        "projection_digest": record["projection_digest"],
        "authority": "pinned projection and frozen fixture" if paired else "frozen fixture and scoped correction receipt",
        "surfaces": {},
        "product_qa": {},
    }
    for phase in ("before", "after"):
        state = edit[phase]
        preview = state["preview"]
        revision = state["revision"]
        expected_sha = digest({"title": preview["title"], "preview": preview["body"]})
        if phase == "before":
            require(
                preview == {"body": doc["body"], "title": doc["title"]} and revision == doc["qa_revision"] and expected_sha == doc["digest"],
                "Draft preview or revision not bound",
            )
        else:
            require(revision == doc["qa_revision"] + 1 and expected_sha == edit["qa_evidence"]["content_digest"], "Edited preview or revision not bound")
        refs = {r["handle"]: r["text"] for r in state["references"]}
        require(len(refs) == len(state["references"]) and refs.keys() == {f["handle"] for f in facts}, "Reference handle set mismatch")
        groups = state["groups"]
        terms = groups["research"]["evidence"] if case["workflow"] == "WF-03" else groups["copy"]["commercial_terms"]
        for name, text in (("preview", preview["body"]), ("terms", terms)):
            result = audit_surface(text, facts, refs, case["locale"])
            result.update(revision=revision, preview_content_digest=expected_sha)
            output["surfaces"][phase + "." + name] = result
        output["product_qa"][phase] = {
            "studio_issues": dict(Counter(v["reason"] for v in state["quality_issues"])),
            "statement_outcomes": dict(Counter(v["outcome"] for v in state["findings"])),
            "studio_issues_n": len(state["quality_issues"]),
            "statements_n": len(state["findings"]),
            "statements_with_recorded_handles": sum(bool(v.get("handles")) for v in state["findings"]),
            "unrecognized_handle_mentions": sum(sum(h not in refs for h in v.get("handles", [])) for v in state["findings"]),
        }
    return output


def audit_series(root, fixture, mode, checkout):
    raw = fixture.read_bytes()
    fixture_sha, count = PINS[mode]
    require(sha(raw) == fixture_sha or sha(raw.replace(b"\r\n", b"\n")) == fixture_sha, "Unrecognized frozen input file")
    require(hash_pin(checkout, 40), "Expected a full checkout SHA")
    cases = json.loads(raw)["cases"]
    if mode == "recovery":
        cases = [c for c in cases if c["persona"] in ("service", "inhouse")]
    require(len(cases) == len({c["id"] for c in cases}) == count, "Wrong case population")
    rows = {}
    for case in cases:
        cid = case["id"]
        path = root / cid / "result.json"
        paired_path = path.with_name("paired-role.json")
        plans = Counter(k.split(".")[0] for f in expected_facts(case, None) for k in rule_names(f))
        row = {"planned_checks_per_surface": sum(plans.values()), "planned_fields": dict(plans)}
        rows[cid] = row
        try:
            data = path.read_bytes()
            row["result_file_sha256"] = sha(data)
            pair = None
            if mode == "study":
                pair_data = paired_path.read_bytes()
                row["paired_file_sha256"] = sha(pair_data)
                pair = json.loads(pair_data)
            row.update(audit_case(case, json.loads(data), pair, checkout, fixture_sha, mode))
        except (OSError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
            row["error"] = str(exc)
    summary = {}
    for surface in SURFACES:
        counts = Counter()
        by_field = {}
        extra = 0
        for row in rows.values():
            if "surfaces" not in row:
                counts["inconclusive"] += row["planned_checks_per_surface"]
                for k, n in row["planned_fields"].items():
                    by_field.setdefault(k, Counter())["inconclusive"] += n
                continue
            detail = row["surfaces"][surface]
            extra += len(detail["additional_commercial_text_for_review"])
            counts.update(c["status"] for f in detail["facts"].values() for c in f["checks"].values())
            for f in detail["facts"].values():
                for k, v in f["checks"].items():
                    by_field.setdefault(k.split(".")[0], Counter())[v["status"]] += 1
        summary[surface] = {
            "expected_checks": sum(r["planned_checks_per_surface"] for r in rows.values()),
            "outcomes": dict(counts),
            "fields": {k: {"expected_checks": sum(v.values()), "outcomes": dict(v)} for k, v in by_field.items()},
            "additional_commercial_lines_for_review": extra,
        }
    qa = {}
    for phase in ("before", "after"):
        items = [r["product_qa"][phase] for r in rows.values() if "product_qa" in r]
        qa[phase] = {"covered_cases": len(items), "expected_cases": len(rows)}
        for key in ("studio_issues_n", "statements_n", "statements_with_recorded_handles", "unrecognized_handle_mentions"):
            qa[phase][key] = sum(item[key] for item in items)
        for key in ("studio_issues", "statement_outcomes"):
            counts = Counter()
            for item in items:
                counts.update(item[key])
            qa[phase][key] = dict(counts)
    return {
        "mode": mode,
        "reviewed_checkout": checkout,
        "scorer_file_sha256": sha(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
        "fixture_sha256": fixture_sha,
        "expected_cases": count,
        "cases_with_valid_inputs": sum("error" not in r for r in rows.values()),
        "unexpected_case_folders": sorted(p.parent.name for p in root.glob("*/result.json") if p.parent.name not in rows),
        "coverage": summary,
        "product_qa": qa,
        "cases": rows,
        "scope": "Automated scoped rendering checks on frozen synthetic facts. Free prose, truth of sources, professional acceptance and human time are unmeasured.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--mode", required=True, choices=PINS)
    parser.add_argument("--checkout", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = audit_series(args.artifact, args.fixture, args.mode, args.checkout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    return 0 if report["expected_cases"] == report["cases_with_valid_inputs"] and not report["unexpected_case_folders"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
