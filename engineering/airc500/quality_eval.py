"""Versioned, event-sourced findings and paired quality scoring for synthetic holdout v2."""

from collections import Counter, defaultdict
from math import sqrt

from quality_corpus import deterministic

STATUS = ("flag", "clear", "unsure")
OPS = ("keep", "replace", "scope", "withdraw", "qualify", "redirect", "deduplicate", "forbid")
CRITERIA = ("equal", "scope", "date", "terms", "meaning", "destination", "supported", "count")
REASONS = ("consistent", "different", "wrong_scope", "expired", "missing_condition", "contradiction", "misleading", "unsupported", "duplicate", "uncertain")


def structured(case, output):
    status, subject, current, expected, operation, source, criterion, reason = output
    return {
        "status": STATUS[status],
        "affected_subject": case["subjects"][subject],
        "current": case["values"][current],
        "expected": case["values"][expected],
        "operation": OPS[operation],
        "evidence": case["sources"][source],
        "regression": CRITERIA[criterion],
        "explanation": REASONS[reason],
    }


def fix_matches(opinion, key):
    return bool(
        key["defect"]
        and opinion["status"] == "flag"
        and all(
            opinion[a] == key[b]
            for a, b in (
                ("affected_subject", "subject"),
                ("current", "current"),
                ("expected", "expected"),
                ("operation", "operation"),
                ("evidence", "source"),
                ("regression", "criterion"),
            )
        )
    )


def explanation_matches(opinion, key):
    return bool(
        opinion["explanation"] == key["reason"]
        and opinion["affected_subject"] == key["subject"]
        and opinion["current"] == key["current"]
        and opinion["expected"] == key["expected"]
        and opinion["evidence"] == key["source"]
    )


def wilson(hit, n):
    if not n:
        return {"hits": hit, "total": n, "rate": None, "interval_95": None}
    p = hit / n
    z = 1.959963984540054
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    dist = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return {"hits": hit, "total": n, "rate": round(p, 4), "interval_95": [round(max(0, mid - dist), 4), round(min(1, mid + dist), 4)]}


def score(flags, keys, opinions):
    truth = {u for u, key in keys.items() if key["defect"]}
    flags = set(flags) & set(keys)
    tp, fp = flags & truth, flags - truth
    fn, tn = truth - flags, set(keys) - flags - truth
    fixed = {uid for uid in tp if any(fix_matches(row, keys[uid]) for row in opinions.get(uid, []))}
    explained = {uid for uid in tp if any(explanation_matches(row, keys[uid]) for row in opinions.get(uid, []))}
    return {
        "TP": len(tp),
        "FP": len(fp),
        "FN": len(fn),
        "TN": len(tn),
        "precision": wilson(len(tp), len(flags)),
        "recall": wilson(len(tp), len(truth)),
        "FPR": wilson(len(fp), len(fp | tn)),
        "structured_fix": wilson(len(fixed), len(tp)),
        "explanation": wilson(len(explained), len(tp)),
        "actionable_ids": sorted(fixed),
        "correct_explanation_ids": sorted(explained),
        "missed": sorted(fn),
        "false": sorted(fp),
    }


def phase(cases, observations, keys):
    lookup = {c["unit"]: c for c in cases}
    flags = set()
    opinions = defaultdict(list)
    lifecycle = []
    proposed = defaultdict(list)

    def event(uid, row, stage, change):
        lifecycle.append(
            {
                "finding_id": "F-" + uid,
                "unit": uid,
                "state": change,
                "phase": stage,
                "assignment_id": row["assignment_id"],
                "reviewer": row["reviewer_id"],
                "attempt_id": row["attempt_id"],
                "proposed": row["opinions"][uid],
            }
        )

    marks = {}
    prev = set()
    for stage in ("blind", "cross", "arbitration", "verified_final"):
        if stage in ("cross", "arbitration") and not any(r["phase"] == stage for r in observations):
            continue
        if stage == "verified_final":
            confirmed = set()
            # A challenge may change the interim set. The verifier still inspects
            # all distinct previously proposed findings and preserves dissent.
            for uid, history in sorted(proposed.items()):
                case = lookup[uid]
                grounded = [op for op in history if op["affected_subject"] == case["subject"] and op["evidence"] == case["authoritative_source"]]
                result = deterministic(case)
                if result is None:
                    state, reason = "unresolved", "typed verifier abstained on this domain"
                elif not result:
                    state, reason = "rejected", "typed evidence agrees with the published observation"
                elif grounded:
                    state, reason = "verified", "typed discrepancy supported by scoped citation"
                else:
                    state, reason = "unresolved", "no proposed finding cited the affected subject and authoritative source"
                if state == "verified":
                    confirmed.add(uid)
                    if not opinions.get(uid):
                        opinions[uid] = grounded
                lifecycle.append(
                    {
                        "finding_id": "F-" + uid,
                        "unit": uid,
                        "state": state,
                        "phase": stage,
                        "verifier": "typed-observation-v2",
                        "source": case["authoritative_source"],
                        "reason": reason,
                    }
                )
            flags = confirmed
        else:
            for row in observations:
                if row["phase"] != stage:
                    continue
                for uid, op in row["opinions"].items():
                    old = uid in flags
                    if op["status"] == "flag":
                        proposed[uid].append(op)
                        prior = opinions[uid]
                        if not old:
                            event(uid, row, stage, "candidate")
                        elif stage != "blind" and prior and op != prior[-1]:
                            event(uid, row, stage, "revised")
                        else:
                            event(uid, row, stage, "corroborated")
                        flags.add(uid)
                        if stage == "blind":
                            opinions[uid].append(op)
                        else:
                            opinions[uid] = [op]
                    elif stage != "blind" and old:
                        event(uid, row, stage, "challenged")
                        if op["status"] == "clear":
                            flags.remove(uid)
                            opinions.pop(uid, None)
                            event(uid, row, stage, "rejected")
                        else:
                            event(uid, row, stage, "unresolved")
                    elif stage != "blind" and op["status"] == "unsure":
                        event(uid, row, stage, "unresolved")
        truth = {uid for uid, k in keys.items() if k["defect"]}
        marks[stage] = {
            "scores": score(flags, keys, opinions),
            "active": sorted(flags),
            "added_true": sorted((flags - prev) & truth),
            "removed_false": sorted((prev - flags) - truth),
            "lost_true": sorted((prev - flags) & truth),
            "added_false": sorted((flags - prev) - truth),
            "by_domain": {
                domain: score(flags, {k: v for k, v in keys.items() if v["domain"] == domain}, opinions)
                for domain in sorted({v["domain"] for v in keys.values()})
            },
        }
        prev = set(flags)
    return {"phases": marks, "lifecycle": lifecycle}


def compare(cases, records, keys):
    def of(*groups):
        return [r for r in records if r["group"] in groups]

    simple = phase(cases, of("common", "repeat"), keys)
    study = phase(cases, of("common", "specialist", "cross", "arbitration"), keys)
    direct = {r["unit"] for r in cases if deterministic(r) is True}
    # The typed verifier can also materialize a concrete repair from its pinned
    # reference. It never receives the evaluation key or handles free-form semantics.
    rule = {
        "price": ("replace", "equal", "different"),
        "currency": ("replace", "equal", "different"),
        "quantity_unit": ("replace", "equal", "different"),
        "variant": ("scope", "scope", "wrong_scope"),
        "market": ("scope", "scope", "wrong_scope"),
        "expiry": ("withdraw", "date", "expired"),
        "qualifier": ("qualify", "terms", "missing_condition"),
        "identity_tenant": ("scope", "scope", "wrong_scope"),
        "identity": ("replace", "equal", "different"),
        "concurrency": ("deduplicate", "count", "duplicate"),
    }
    repairs = {}
    for c in cases:
        uid = c["unit"]
        if uid in direct:
            op, criterion, reason = rule[c["domain"]]
            repairs[uid] = [
                {
                    "status": "flag",
                    "affected_subject": c["subject"],
                    "current": c["published"],
                    "expected": c["authorized"],
                    "operation": op,
                    "regression": criterion,
                    "explanation": reason,
                    "evidence": c["authoritative_source"],
                }
            ]
    table = {
        "deterministic_only": score(direct, keys, repairs),
        "one_reviewer": simple["phases"]["blind"]["scores"],
        "independent_reviewers": study["phases"]["blind"]["scores"],
        "one_plus_verifier": simple["phases"]["verified_final"]["scores"],
        "council_with_debate": study["phases"]["verified_final"]["scores"],
    }
    components = {
        "deterministic_only": (),
        "one_reviewer": ("common", "repeat"),
        "independent_reviewers": ("common", "specialist"),
        "one_plus_verifier": ("common", "repeat"),
        "council_with_debate": ("common", "specialist", "cross", "arbitration"),
    }
    resources = {
        k: {key: sum(r[key] for r in of(*groups)) for key in ("input_tokens", "output_tokens", "elapsed_ms")} | {"calls": len(of(*groups)), "paid_microusd": 0}
        for k, groups in components.items()
    }
    for arm, budget in resources.items():
        true_findings = table[arm]["TP"]
        budget["tokens_per_true_finding"] = round((budget["input_tokens"] + budget["output_tokens"]) / true_findings, 2) if true_findings else None
    return {
        "version": 2,
        "five_arms": table,
        "resources": resources,
        "deterministic_abstentions": dict(Counter(c["domain"] for c in cases if deterministic(c) is None)),
        "single": simple,
        "council": study,
    }
