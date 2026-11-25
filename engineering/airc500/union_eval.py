"""Three-state, source-scoped verification. The hidden scoring labels are never inputs here."""

from collections import Counter, defaultdict

from union_cases import SEMANTICS

STATES = ("verified_defect", "verified_clean", "unresolved")
REASON = {"defect": "contradicts", "clean": "agrees", "unresolved": "insufficient"}


def verify_semantic(case, answer):
    """Only the finite enrolled phrase equivalences have an independent semantic proof."""
    sources = [s for s in case["sources"] if s["ref"] == answer.get("citation") and s["subject"] == case["subject"]]
    if len(sources) != 1:
        return None
    first, second, a, b, repair = SEMANTICS[case["domain"]]
    source = sources[0]["text"]
    copy = case["observation"]
    if source not in (first, second) or copy not in a + b:
        return None
    truth = "clean" if (source == first) == (copy in a) else "defect"
    if answer.get("verdict") != truth or answer.get("reason") != REASON[truth]:
        return None
    action = truth == "defect" and answer.get("operation") == repair
    return dict(
        state="verified_" + truth,
        provider="AI + scoped phrase verifier",
        source=sources[0]["ref"],
        observation=copy,
        expected=source,
        operation=repair if action else None,
        actionable=action,
    )


def decide(rows, opinions):
    decisions = {}
    for case in rows:
        uid = case["id"]
        if case["kind"] == "typed":
            bad = case["observation"] != case["authorized"]
            decisions[uid] = dict(
                state="verified_defect" if bad else "verified_clean",
                provider="deterministic",
                source=case["locator"],
                observation=case["observation"],
                expected=case["authorized"],
                operation="Restore scoped published value" if bad else None,
                actionable=bad,
            )
            continue
        outcomes = [result for opinion in opinions if uid in opinion and (result := verify_semantic(case, opinion[uid]))]
        decisions[uid] = next(
            (r for r in outcomes if r["actionable"]),
            outcomes[0] if outcomes else dict(state="unresolved", provider=None, source=None, operation=None, actionable=False),
        )
    for case in rows:
        decisions[case["id"]].update(subject=case["subject"], domain=case["domain"], severity=case["severity"])
    return decisions


def summarize(rows, decisions):
    scopes = defaultdict(Counter)
    for c in rows:
        scopes[(c["domain"], c["severity"])][decisions[c["id"]]["state"]] += 1
    missing = [c["id"] for c in rows if c["mandatory"] and decisions[c["id"]]["state"] == "unresolved"]
    return dict(
        states={s: sum(d["state"] == s for d in decisions.values()) for s in STATES},
        by_domain_severity={k + "/" + v: {s: count[s] for s in STATES} for (k, v), count in sorted(scopes.items())},
        mandatory_gaps=missing,
        release="inconclusive" if missing else "covered_fixture",
        deterministic_actionable=sum(d["actionable"] and d["provider"] == "deterministic" for d in decisions.values()),
        hybrid_actionable=sum(d["actionable"] and d["provider"] != "deterministic" for d in decisions.values()),
        # The model selects a scoped operation. Concrete before/after values come from pinned evidence.
        ai_actionable=0,
    )


def raw_scores(rows, labels, opinions):
    """Disagreement and silence both abstain. Matched branches use the same aggregation."""
    counts = Counter()
    for c in rows:
        uid = c["id"]
        seen = [op[uid] for op in opinions if uid in op]
        votes = {a["verdict"] for a in seen}
        verdict = next(iter(votes)) if len(votes) == 1 else "unresolved"
        truth = labels[uid]
        counts["cases"] += 1
        counts["raw_abstained"] += verdict == "unresolved"
        counts["raw_flags"] += verdict == "defect"
        counts["true_flags"] += verdict == truth == "defect"
        counts["false_flags"] += verdict == "defect" and truth == "clean"
        counts["flagged_despite_missing_truth"] += verdict == "defect" and truth == "unresolved"
        counts["cleared_despite_missing_truth"] += verdict == "clean" and truth == "unresolved"
        counts["correct_abstentions"] += verdict == truth == "unresolved"
        counts["wrong_clean"] += verdict == "clean" and truth == "defect"
        counts["correct_reason"] += bool(seen) and all(a["reason"] == REASON[truth] for a in seen)
        counts["correct_attribution"] += bool(seen) and all(any(s["subject"] == c["subject"] and a["citation"] == s["ref"] for s in c["sources"]) for a in seen)
        if truth == "defect":
            counts["defects"] += 1
            counts["correct_operation"] += bool(seen) and all(a["operation"] == SEMANTICS[c["domain"]][4] for a in seen)
        counts["clean"] += truth == "clean"
        counts["truth_unresolved"] += truth == "unresolved"
    return dict(counts)
