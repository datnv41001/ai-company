"""Audit frozen C3 holdout receipts without loading the application or model.

Pass one or more --arm NAME=DIR. DIR contains <case-id>/result.json. The same
case can occur once in each arm. Missing cases stay in the assigned denominator.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from statistics import median, pstdev
import unicodedata

HOLDOUT = "c497ff707c986acaa3c48ba799ab1a378f194d3e7cd4262834d41a4aae0fe477"
WEIGHTS = "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"
NUMBER = r"\d+(?:[.,]\d{3})*"
MONEY = r"(?<!\w)(?:VND|VNĐ|USD|EUR|JPY|GBP|đồng|₫|đ)(?![a-zà-ỹ])"
# Currency may directly follow a digit, e.g. "210.000đ".
PRICE = re.compile(rf"(?<![\w.,])(?P<before>{NUMBER})\s*(?P<curr>VND|VNĐ|USD|EUR|JPY|GBP|đồng|₫|đ)(?!\w)|(?P<lead>{MONEY})\s*(?P<after>{NUMBER})(?![\d.,]\d)", re.I)
PHONE = re.compile(r"(?<!\w)(?:0|\+84)(?:[ .-]?\d){8,10}(?!\d)")
PROMISE = re.compile(r"rẻ nhất|toàn quốc|cam kết|đảm bảo chất lượng|khuyến mãi|miễn phí|bảo hành|100\s*%", re.I)
FOREIGN_SKU = re.compile(r"\b[A-Z]{2}H-\d{3}\b", re.I)
INTERNAL = ("mục tiêu chiến dịch:", "giả thuyết cần kiểm chứng", "dữ liệu cần bổ sung", "định nghĩa kpi:")


def norm(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest_doc(doc):
    payload = json.dumps({"title":doc["title"], "preview":doc["body"]}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf8")).hexdigest()


def examine(case, row):
    """Independent literal checks; ratios never equate substring matches with entailment."""
    doc = row["deliverable"]
    text = doc["title"] + "\n" + doc["body"]
    assets = row.get("assets", {})
    # Audit additional buyer surfaces, e.g. SEO snippets, even when they are not in the preview.
    audience_texts = [text, *assets.get("seo_fields", {}).values(), *assets.get("buyer_copy", {}).values()]
    audience = "\n".join(dict.fromkeys(audience_texts))
    price_fact = next(f for f in case["facts"] if "price" in f)
    price = price_fact["price"]
    expected_value = price["amount_minor"]
    # All frozen briefs give the intended trading unit explicitly in the source sheet.
    # Keeping this separate from the signed generic service code reveals lost specificity.
    unit = price_fact["wording"].rsplit("/", 1)[1].strip(". ")
    tax = {"included":"đã gồm thuế","excluded":"chưa gồm thuế"}[price["tax"]]
    term = rf"\b{re.escape(str(price['basis_quantity']))}\s+{re.escape(unit)}\b"
    minimum = rf"đơn tối thiểu\s+{re.escape(str(price['moq']))}\s+{re.escape(unit)}\b"
    tier = rf"(?:áp dụng từ|mức giá áp dụng từ)\s+{re.escape(str(price['tier_min']))}\s+{re.escape(unit)}\b"
    amounts = []
    for match in PRICE.finditer(audience):
        val = int(re.sub(r"[.,]", "", match["before"] or match["after"]))
        currency = (match["curr"] or match["lead"]).upper()
        amounts.append((val, "VND" if currency in ("ĐỒNG", "Đ", "₫", "VNĐ") else currency))

    signals = {
        "product_name_and_sku_present": norm(case["product"]) in norm(text),
        "price_seen_and_all_parsed_amounts_match": bool(amounts) and all(amount == (expected_value, price["currency"]) for amount in amounts),
        "localized_selling_basis_in_preview": bool(re.search(r"/\s*" + term, norm(text))),
        "approved_tax_in_preview": tax in norm(text),
        "moq_and_tier_with_exact_unit_in_preview": bool(re.search(minimum, norm(text)) and re.search(tier, norm(text))),
        "exact_region_and_required_price_qualifier_present": norm(case["region"]) in norm(text) and norm(price_fact["qualifiers"]) in norm(text),
        "source_description_present": all(norm(f["wording"]) in norm(text) for f in case["facts"] if "price" not in f),
        "unexpected_sku_token": any(s.upper() != case["sku"] for s in FOREIGN_SKU.findall(audience)),
        "unprovided_phone_pattern": bool(PHONE.search(audience)),
        "promise_or_expansion_pattern": bool(PROMISE.search(audience)),
        "internal_label_in_buyer_preview": any(s in norm(text) for s in INTERNAL),
    }
    assessment = doc.get("assessment", {}).get("content_evidence")
    outcomes = Counter()
    if assessment is not None:
        require((assessment["content_digest"], assessment["qa_revision"], assessment["manifest_digest"]) ==
                (doc["digest"], doc["qa_revision"], row["manifest"]["digest"]), f"Stale content assessment {case['id']}")
        fields = {"title":doc["title"], "client_preview":doc["body"]}
        for statement in assessment["statements"]:
            source = fields[statement["field"]]
            a, b = statement["start"], statement["end"]
            require(0 <= a < b <= len(source) and source[a:b] == statement["text"], f"Invalid assessment span {case['id']}")
            outcomes[statement["outcome"]] += 1
    return signals, outcomes


def audit(folder, cases, expected_arm=None):
    require(folder.is_dir(), f"Unknown result directory {folder}")
    data = []
    identifiers = set()
    arm_info = set()
    for path in sorted(folder.glob("*/result.json")):
        row = json.loads(path.read_text(encoding="utf8"))
        key = row["case"]
        require(key in cases and path.parent.name == key, f"Unknown case {path}")
        require(row["cases_sha256"] == HOLDOUT and row["model_sha256"] == WEIGHTS, f"Foreign inputs in {path}")
        require(re.fullmatch(r"[a-f0-9]{40}", row["checkout"]), f"Invalid revision {path}")
        require(expected_arm is None or row["arm"] == expected_arm, f"Wrong arm {path}")
        arm_info.add((row["checkout"], row["arm"]))
        case = cases[key]
        require(row["workflow"].split("/")[0] == case["workflow"], f"Wrong workflow for {key}")
        item = {"case":key, "persona":case["persona"], "workflow":case["workflow"], "state":row["state"],
                "input_tokens":row["input_tokens"], "output_tokens":row["output_tokens"], "runtime_s":row["runtime_s"],
                "provider_fee_usd":row["provider_fee_usd"], "technical_first_pass":bool(row.get("first_pass_runtime")),
                "unmetered_attempts":row.get("unmetered_attempts", 0), "invocations":len(row["attempts"])}
        require(row["input_tokens"] == sum(x.get("input_tokens", 0) for x in row["attempts"]) and
                row["output_tokens"] == sum(x.get("output_tokens", 0) for x in row["attempts"]), f"Usage mismatch for {key}")
        for attempt in row["attempts"]:
            aid = attempt["attempt_id"]
            require(aid not in identifiers and re.fullmatch(r"[a-f0-9]{64}", attempt["request_sha256"]), f"Reused or malformed invocation {key}")
            identifiers.add(aid)
        doc = row.get("deliverable")
        if doc:
            require(row["run_id"] not in identifiers and doc["id"] not in identifiers and row["run_id"] != doc["id"], f"Reused delivery {key}")
            identifiers.update((row["run_id"], doc["id"]))
            require(doc["digest"] == digest_doc(doc), f"Damaged draft {key}")
            require(any("raw_output" in a and a.get("output_tokens", 0) > 0 for a in row["attempts"]), f"No real generation for {key}")
            signals, outcomes = examine(case, row)
            item.update(deliverable_id=doc["id"], digest=doc["digest"], signals=signals, application_gate_outcomes=dict(outcomes))
        data.append(item)
    require(len(arm_info) <= 1, f"Mixed revisions or arms in {folder}")
    drafts = [r for r in data if "signals" in r]
    latencies = [r["runtime_s"] for r in data if r["invocations"]]
    signal_counts = Counter()
    gate_counts = Counter()
    for entry in drafts:
        signal_counts.update({k:int(v) for k,v in entry["signals"].items()})
        gate_counts.update(entry["application_gate_outcomes"])
    return {
        "checkout_and_arm":sorted(arm_info), "assigned":len(cases), "recorded":len(data), "no_receipt":len(cases)-len(data),
        "states":dict(Counter(r["state"] for r in data)), "actual_drafts":len(drafts),
        "technical_first_pass":sum(r["technical_first_pass"] for r in data),
        "actual_invocations":sum(r["invocations"] for r in data),
        "unmetered_attempts":sum(r["unmetered_attempts"] for r in data),
        "input_tokens":sum(r["input_tokens"] for r in data), "output_tokens":sum(r["output_tokens"] for r in data),
        "provider_fee_usd":sum(r["provider_fee_usd"] for r in data), "accepted_by_human":None,
        "generation_seconds":{"n":len(latencies),"median":median(latencies),"min":min(latencies),"max":max(latencies),
                              "between_task_sd":round(pstdev(latencies), 3)} if latencies else None,
        "independent_literal_signals_on_drafts":dict(signal_counts), "application_gate_statement_outcomes":dict(gate_counts),
        "assessed_drafts":sum(bool(r["application_gate_outcomes"]) for r in drafts),
        "per_case":data,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cases", type=Path, default=Path(__file__).with_name("holdout-v1.json"))
    p.add_argument("--arm", action="append", metavar="NAME=DIR", required=True)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    require(hashlib.sha256(args.cases.read_bytes()).hexdigest() == HOLDOUT, "Holdout digest mismatch")
    cases = {c["id"]: c for c in json.loads(args.cases.read_text(encoding="utf8"))["cases"]}
    require(len(cases) == 50 and set(Counter((c["persona"],c["workflow"]) for c in cases.values()).values()) == {5}, "Unbalanced holdout")
    combined = {}
    for arg in args.arm:
        name, folder = arg.split("=", 1)
        require(name and name not in combined, f"Duplicate arm name {name}")
        combined[name] = audit(Path(folder), cases, name if name in {"projected","improved"} else None)
    by_arm = [set(d["case"] for d in arm["per_case"]) for arm in combined.values()]
    complete_pairs = sorted(set.intersection(*by_arm)) if len(combined) > 1 else []
    output = json.dumps({"holdout_sha256":HOLDOUT, "arms":combined,"cases_recorded_in_all_arms":complete_pairs},
                        ensure_ascii=False,indent=2)
    if args.out:
        args.out.write_text(output + "\n", encoding="utf8")
    else:
        print(output)


if __name__ == "__main__":
    main()
