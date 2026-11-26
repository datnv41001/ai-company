"""Replay actual model text against the unchanged Studio field and document gates."""

from copy import deepcopy

from knowledge_fixtures import accepted


# WF-03 uses different field names for the client-facing edition.
CUSTOMER_FIELDS = {
    ("client_strategy", "target"): ("research", "segment"),
    ("client_strategy", "decision"): ("strategy", "positioning"),
    ("client_measurement", "hypothesis"): ("strategy", "test_hypothesis"),
    ("client_measurement", "method"): ("strategy", "measurement_method"),
}


def reviewed_edition(api, path, editor, reviewer, proposal, baseline, record):
    revision = proposal["revision"]
    edition = proposal["customer_edition"]
    groups = deepcopy(baseline)
    attempts = (record or {}).get("attempts", [])
    source = {}
    for entry in attempts:
        role = entry["schema"].removeprefix("c3_skills_")
        for field, text in (entry.get("raw_output") or {}).items():
            if isinstance(text, str):
                source[role, field] = (text, entry)
    preferred = {"copy": "content", "seo": "seo", "research": "research", "strategy": "strategy", "measurement": "strategy"}

    def persist(value):
        return api.patch(
            path + "/studio", headers=editor["headers"], json={"expected_revision": revision, "delivery_version": edition["version"], "groups": value}
        )

    trail = {}
    for group, fields in baseline.items():
        for field, fallback in fields.items():
            role, worker_field = CUSTOMER_FIELDS.get((group, field), (preferred.get(group), field))
            model_field = source.get((role, worker_field))
            decision = {
                "customer_visible": field in edition["fields"].get(group, []),
                "control": fallback,
                "before": proposal["groups"].get(group, {}).get(field),
                "after": fallback,
                "decision": "grounded_composer",
                "model_candidate": None,
            }
            trail[group + "." + field] = decision
            if not model_field:
                continue
            candidate, log = model_field
            decision.update(model_candidate=candidate, worker_field=worker_field, role=role, attempt=log["attempt_id"], request_sha256=log["request_sha256"])
            if candidate == fallback:
                decision["decision"] = "coincides_with_control"
                continue
            trial = deepcopy(groups)
            trial[group][field] = candidate
            response = persist(trial)
            if response.status_code == 422:
                decision.update(decision="retained_control", quality_issues=[response.json().get("detail")])
                continue
            saved = accepted(response)
            revision = saved["revision"]
            assessment = accepted(api.get(path + "/content-evidence", headers=reviewer["headers"]))
            pending = [
                dict(field=s["field"], text=s["text"], outcome=s["outcome"], reason=s["reason"])
                for s in assessment["statements"]
                if s["outcome"] not in ("verified", "reviewed", "editorial")
            ]
            decision.update(tested_revision=revision, quality_issues=saved["quality_issues"], unresolved=pending)
            if saved["quality_issues"] or pending or not assessment["ready"]:
                decision["decision"] = "retained_control"
                continue
            groups = trial
            decision.update(after=candidate, decision="retained_model_verbatim")
    # A rejected trial can be the last working copy. Persist exactly the reviewed
    # selection, then submit/sign the new current revision through the ordinary API.
    result = accepted(persist(groups))
    return groups, result, trail
