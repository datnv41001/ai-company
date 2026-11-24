"""Frozen synthetic evaluation set and capability-limited verifier for literal business facts."""

import hashlib
import random
import tempfile
from pathlib import Path

from pilot_fixture import digest, encoded, git

SEEDS = (17, 43)
FIXTURE_SEED = 91367
DOMAINS = (
    "price",
    "currency",
    "quantity_unit",
    "variant",
    "market",
    "expiry",
    "qualifier",
    "negation",
    "cta",
    "unsupported_claim",
    "identity_tenant",
    "concurrency",
)
PRODUCTS = ("Maple mug", "Indigo tote", "Linen wrap", "Amber lamp", "Juniper box", "Aster notebook", "Elm tray", "Blue stool")
SOURCE = "knowledge/authorized.jsonl"
COPY = "campaign/candidate.jsonl"


def example(domain, n):
    """The expected label is explicitly authored outside the operational verifier."""
    seller = PRODUCTS[n]
    variants = ("large", "mini", "standard", "small", "wide", "tall", "compact", "slim")
    market = ("VN", "CA", "JP", "AU", "UK", "US", "DE", "FR")
    currency = ("VND", "CAD", "JPY", "AUD", "GBP", "USD", "EUR", "EUR")
    other = (n + 1) % 8
    facts = {
        "price": (f"Unit price in {currency[n]}", str(18 + 4 * n), str(12 + 3 * n), "replace", "equal", "different"),
        "currency": (
            "Currency of approved offer",
            currency[n],
            ("CHF", "USD", "GBP")[n % 3] if currency[n] != "GBP" else "JPY",
            "replace",
            "equal",
            "different",
        ),
        "quantity_unit": ("Pack quantity and unit", f"{4 + n} pieces", f"{4 + n} kilograms", "replace", "equal", "different"),
        "variant": (f"Only variant covered by {seller} warranty", variants[n], variants[other], "scope", "scope", "wrong_scope"),
        "market": ("Market in which this offer can be advertised", market[n], market[other], "scope", "scope", "wrong_scope"),
        "expiry": (f"Offer ends 2027-03-{n + 10:02d}; publication date is 2027-03-{n + 11:02d}", "expired", "active", "withdraw", "date", "expired"),
        "qualifier": (f"Discount eligibility for {seller}", f"orders of {3 + n}+ units", "all purchases", "qualify", "terms", "missing_condition"),
        "negation": (f"Authorized copy about {seller} machine washing", "hand wash only", "machine washable", "replace", "meaning", "contradiction"),
        "cta": (f"Available customer action for {seller}", "request a quotation", "buy now", "redirect", "destination", "misleading"),
        "unsupported_claim": (
            f"Approved evidence for {seller} finish",
            "matte finish",
            "guaranteed lifetime performance",
            "withdraw",
            "supported",
            "unsupported",
        ),
        "identity_tenant": (
            f"Synthetic sample B{n}: authorized recipient scope summary",
            f"workspace-{n}/client-A",
            f"workspace-{n}/client-B",
            "scope",
            "scope",
            "wrong_scope",
        ),
        "concurrency": (
            f"Approved count after two deliveries of the same synthetic order receipt {25 + n}",
            "one fulfillment",
            "two fulfillments",
            "deduplicate",
            "count",
            "duplicate",
        ),
    }
    return facts[domain]


def identity_corpus():
    cases = []
    keys = {}
    rng = random.Random(41017)
    variants = [
        ("unverified signup", "await verification", "membership granted"),
        ("expired proof", "request fresh proof", "identity verified"),
        ("mismatched invitation email", "decline invitation", "membership granted"),
        ("invitation already used", "one accepted invitation", "second grant created"),
        ("verified active invitation", "grant listed scope", "deny all access"),
        ("withdrawn invitation", "decline invitation", "membership granted"),
        ("verified workspace owner", "allow owner dashboard", "deny all access"),
        ("signed out session", "require sign-in", "allow dashboard"),
    ]
    for n, (rule, approved, incorrect) in enumerate(variants):
        for bad in (False, True):
            uid = hashlib.sha256(f"identity-holdout-{n}-{bad}".encode()).hexdigest()[:8]
            subject = f"Synthetic onboarding account {n + 1}"
            current = incorrect if bad else approved
            menu = [approved, incorrect, "ignore the account state"]
            subjects = [subject, "Unrelated synthetic account"]
            refs = [f"S-{uid}", f"D-{uid}"]
            for arr in (menu, subjects, refs):
                rng.shuffle(arr)
            case = {
                "unit": uid,
                "domain": "identity",
                "subject": subject,
                "policy": f"Fixture policy for {rule}",
                "authorized": approved,
                "published": current,
                "values": menu,
                "subjects": subjects,
                "sources": refs,
                "authoritative_source": f"S-{uid}",
                "other_source": f"D-{uid}",
            }
            cases.append(case)
            keys[uid] = {
                "unit": uid,
                "domain": "identity",
                "defect": bad,
                "subject": subject,
                "current": current,
                "expected": approved,
                "operation": "replace",
                "criterion": "equal",
                "source": f"S-{uid}",
                "reason": "different" if bad else "consistent",
                "provenance": "synthetic_regression",
            }
    rng.shuffle(cases)
    return cases, keys


def corpus(cohort="marketing"):
    if cohort == "identity":
        return identity_corpus()
    if cohort != "marketing":
        raise ValueError("unknown frozen cohort")
    rng = random.Random(FIXTURE_SEED)
    cases = []
    keys = []
    for d, domain in enumerate(DOMAINS):
        deficient = {*rng.sample(range(8), 4)}
        for n in range(8):
            rule, approved, bad, operation, criterion, reason = example(domain, n)
            uid = hashlib.sha256(f"{FIXTURE_SEED}-{domain}-{n}".encode()).hexdigest()[:8]
            if domain == "price" and n >= 4:
                approved, bad = bad, approved
            failed = n in deficient
            current = bad if failed else approved
            # Include clear clean paraphrases in the semantic cells, evaluated on meaning.
            paraphrases = {"negation": "wash solely by hand", "cta": "ask for a price quote", "unsupported_claim": "has a matte surface"}
            if not failed and domain in paraphrases and n % 2 == 0:
                current = paraphrases[domain]
            options = list(dict.fromkeys([approved, current, bad, "do not use " + approved]))
            rng.shuffle(options)
            subject = f"{PRODUCTS[n]} / {domain}"
            subjects = [subject, f"{PRODUCTS[(n + 1) % 8]} / {domain}"]
            rng.shuffle(subjects)
            refs = [f"S-{uid}", f"D-{uid}"]
            rng.shuffle(refs)
            item = {
                "unit": uid,
                "domain": domain,
                "subject": subject,
                "policy": rule,
                "authorized": approved,
                "published": current,
                "values": options,
                "subjects": subjects,
                "sources": refs,
                "authoritative_source": f"S-{uid}",
                "other_source": f"D-{uid}",
            }
            cases.append(item)
            keys.append(
                {
                    "unit": uid,
                    "domain": domain,
                    "defect": failed,
                    "subject": subject,
                    "current": current,
                    "expected": approved,
                    "operation": operation,
                    "criterion": criterion,
                    "reason": reason if failed else "consistent",
                    "source": f"S-{uid}",
                    "provenance": "synthetic_regression" if domain in ("identity_tenant", "concurrency") else "deterministic_fixture",
                }
            )
    rng.shuffle(cases)
    return cases, {k["unit"]: k for k in keys}


def deterministic(case):
    """Scoped production-like adapter covers typed fields; open-ended semantics abstain."""
    domain = case["domain"]
    if domain in {"negation", "cta", "unsupported_claim"}:
        return None
    if domain == "expiry":
        from datetime import date

        ends = case["policy"].split("ends ")[1].split(";")[0]
        at = case["policy"].split("date is ")[1]
        effective = "expired" if date.fromisoformat(at) > date.fromisoformat(ends) else "active"
        return effective != case["published"]
    return case["authorized"] != case["published"]


def git_fixture(cases):
    with tempfile.TemporaryDirectory(prefix="airc-holdout-") as tmp:
        repo = Path(tmp)
        git(repo, "init", "--quiet", "--object-format=sha1")
        for name in (SOURCE, COPY):
            (repo / name).parent.mkdir()
        for revision in ("base", "head"):
            for name in (SOURCE, COPY):
                lines = []
                for c in cases:
                    if name == SOURCE:
                        obj = {k: c[k] for k in ("unit", "domain", "subject", "policy", "authorized", "authoritative_source")}
                    else:
                        obj = {"unit": c["unit"], "subject": c["subject"], "published": c["authorized"] if revision == "base" else c["published"]}
                    lines.append(encoded(obj))
                (repo / name).write_bytes(b"\n".join(lines) + b"\n")
            git(repo, "add", "--", SOURCE, COPY)
            git(repo, "commit", "--quiet", "-m", revision)
            sha = git(repo, "rev-parse", "HEAD").decode().strip()
            if revision == "base":
                base = sha
        blobs = {path: digest(git(repo, "show", sha + ":" + path)) for path in (SOURCE, COPY)}
        if git(repo, "rev-parse", sha + "^").decode().strip() != base:
            raise ValueError("invalid fixture ancestry")
    return {"base_sha": base, "head_sha": sha, "blobs": blobs, "bundle_sha256": digest(encoded(cases))}
