"""Internal decision support for curated, synthetic WF-03@3 evaluation packets.

Use through scripts.strategy_study. The packet is editor-coded research material,
not an authorization token. This offline projection owns no customer writer or model.
"""
from datetime import datetime
import json
from pathlib import Path

from app import c3_assets, c3_skill_library, registry_adapters
from migrations.runtime_bundle import canonical_hash


CATALOG = Path(__file__).resolve().parents[1] / "catalog/research-strategy-v3.json"
# Published manifest_digest in the archived WF-03 @3 campaign journey.
REVIEWED_RELEASE = "cf9078f2aa283cc7a9e9c273abd3077338c94ebe0f51a65e0a30c33254d94969"
SCOPE_KEYS = {"tenant_id", "client_id", "brand_id", "campaign_id"}
ROLES = ("research", "strategy")
SOURCE_KINDS = {"observation", "product_fact", "channel", "measurement"}


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("Expected an offset-aware timestamp")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.utcoffset() is None:
        raise ValueError("Expected an offset-aware timestamp")
    return timestamp


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def coding_digest(observation):
    """Fingerprint the exact synthetic row the fixture author coded, including its verbatim text."""
    return canonical_hash({k: v for k, v in observation.items() if k != "coding_digest"})


def eligible_sources(packet):
    """Resolve one revision per scoped source at the cutoff before checking its rights.

    A withdrawn, superseding or unpermitted revision cannot revive an older copy.
    Foreign rows are discarded before inspecting or reporting their content.
    """
    scope, brief = packet["scope"], packet["brief"]
    if set(scope) != SCOPE_KEYS or not all(_text(v) for v in scope.values()) or not _text(brief.get("product")):
        raise ValueError("A complete work order scope and product are required")
    if packet["workflow"] != c3_assets.RESEARCH:
        raise ValueError("This workpaper requires WF-03 Research to Strategy @3")
    cutoff = _instant(packet["as_of"])
    revisions = {}
    for row in packet["sources"]:
        if row.get("scope") != scope or row.get("product") != brief["product"]:
            continue
        if _instant(row["recorded_at"]) > cutoff:
            continue
        key, rev = row["id"], row["revision"]
        if not _text(key) or type(rev) is not int or rev < 1:
            raise ValueError("Invalid source identity or revision")
        history = revisions.setdefault(key, {})
        if rev in history and row != history[rev]:
            raise ValueError("Conflicting copies of a source revision")
        history[rev] = row
    visible = []
    for ident in sorted(revisions):
        history = revisions[ident]
        row = history[max(history)]
        if (row.get("permitted_use") != "internal_strategy" or row.get("kind") not in SOURCE_KINDS
                or not row.get("valid_from") or _instant(row["valid_from"]) > cutoff
                or (row.get("valid_until") and _instant(row["valid_until"]) <= cutoff)
                or (row.get("revoked_at") and _instant(row["revoked_at"]) <= cutoff)):
            continue
        if not all(_text(row.get(k)) for k in ("excerpt", "sample", "segment", "situation")):
            raise ValueError("An observation needs its source text, population, episode and sampling limit")
        if "quote" in row and (not _text(row["quote"]) or row["quote"] not in row["excerpt"]):
            raise ValueError("The evidence span must occur verbatim in the source")
        visible.append(row)
    return visible


def _case_brief(packet):
    brief = packet["brief"]
    if not all(_text(brief.get(k)) for k in ("decision", "objective")):
        raise ValueError("Specify the commission and decision to support")
    options = brief["options"]
    if (not options or any(not all(_text(o.get(k)) for k in ("id", "label", "tradeoff", "asset")) for o in options)
            or len({o["id"] for o in options}) != len(options)):
        raise ValueError("Each proposed option needs a distinct identifier, label, trade-off and asset")
    if not isinstance(brief["constraints"], list) or not all(_text(x) for x in brief["constraints"]):
        raise ValueError("Claim constraints must be a list of text entries")
    return brief


def _checkpoints(packet, checkpoints, sources):
    # This is release compatibility and integrity for our synthetic replay, not a live run signature.
    catalog = json.loads(CATALOG.read_bytes())
    if canonical_hash(catalog) != REVIEWED_RELEASE:
        raise ValueError("WF-03 release differs from the reviewed catalog")
    binding = checkpoints["binding"]
    if (f'{catalog["workflow_id"]}@{catalog["workflow_version"]}' != packet["workflow"]
            or binding["workflow"] != packet["workflow"] or binding["scope"] != packet["scope"]
            or binding["packet_sha256"] != canonical_hash(packet)):
        raise ValueError("Checkpoint and packet binding mismatch")
    refs, revs = binding["source_refs"], binding["source_revisions"]
    if (set(refs) != set(revs) or set(refs) != set(sources)
            or any(key != ident or type(revs[key]) is not int or sources[ident]["revision"] != revs[key]
                   for key, ident in refs.items())):
        raise ValueError("Checkpoint source revision mismatch")
    reviews, pins = [], {}
    for role in ROLES:
        contract, checkpoint = catalog["contracts"][role], checkpoints[role]
        adapter = registry_adapters.resolve(contract)
        if (adapter is None or adapter.version != 4 or adapter.skill != role
                or contract["marketing_methods"] != c3_skill_library.skill_pins(role)):
            raise ValueError("Installed adapter does not match the approved WF-03 release")
        validated = adapter.validate(checkpoint["raw_reply"], role, [], refs)
        if any(validated[k] != checkpoint.get(k) for k in ("sections", "source_ids", "marketing_skills")):
            raise ValueError("Checkpoint differs from the validated role output")
        pins[role] = {"adapter": contract["adapter"], "digest": adapter.digest,
                      "checkpoint_sha256": canonical_hash(checkpoint), "qa_policy": contract["qa_policy"]}
        cited = [sources[refs[handle]] for handle in validated["source_ids"]]
        for field, sentence in validated["sections"].items():
            # Only whole-source echoes are marked literal. An unrelated true sentence
            # or a negated fragment can still appear inside a valid source.
            literal = [s["id"] for s in cited if sentence.strip() == s["excerpt"].strip()]
            reviews.append({"role": role, "field": field, "text_sha256": canonical_hash(sentence),
                            "status": "literal_source_text" if literal else "needs_editor_review",
                            "literal_sources": literal, "cited_sources": list(validated["source_ids"])})
    return {"workflow": packet["workflow"], "catalog_sha256": REVIEWED_RELEASE, "roles": pins,
            "packet_sha256": binding["packet_sha256"]}, reviews


def _source_view(row):
    return {"source_id": row["id"], "revision": row["revision"], "quote": row.get("quote", row["excerpt"]),
            "excerpt": row["excerpt"], "sample": row["sample"], "kind": row["kind"],
            "segment": row["segment"], "situation": row["situation"], "recorded_at": row["recorded_at"],
            "valid_from": row["valid_from"], "valid_until": row.get("valid_until")}


def _applicable(row, brief):
    return all(row[key] in ("*", brief.get(key)) for key in ("segment", "situation"))


def _decision_input(kind, rows, selected, options):
    matched = []
    unverified = []
    role, prefix = {"channel": ("channel_owner", "Available for an internal draft: "),
                    "measurement": ("measurement_owner", "Feasible pilot measurement: ")}[kind]
    for row in rows:
        if row["kind"] != kind:
            continue
        targets = row.get("applies_to", [])
        if not isinstance(targets, list) or any(t not in {"*", *options} for t in targets):
            raise ValueError("A channel or measurement refers to an unknown strategy option")
        if selected and (selected in targets or "*" in targets):
            # The two affirmative record forms are explicit synthetic owner decisions.
            # A channel name inside a negative note or an operator's guess proves no availability.
            value = row.get("value")
            if (_text(value) and row.get("authority_role") == role
                    and row["excerpt"] == prefix + value + "."):
                matched.append(row)
            else:
                unverified.append(row["id"])
    values = {row["value"] for row in matched}
    evidence = [row["id"] for row in matched]
    status = "conflicting" if len(values) > 1 else "unknown"
    if len(values) == 1 and not unverified:
        status = "supported"
    return {"status": status, "value": next(iter(values)) if status == "supported" else None,
            "sources": evidence, "needs_owner_verification": unverified}


def build_workpaper(packet, checkpoints):
    """Project observations and commissioned alternatives into an internal Content work order."""
    brief = _case_brief(packet)
    sources = {s["id"]: s for s in eligible_sources(packet)}
    provenance, claim_review = _checkpoints(packet, checkpoints, sources)
    eligible = [s for s in sources.values() if _applicable(s, brief)]
    observations, context, unreviewed = [], [], []
    options = {o["id"]: {**o, "used": [], "declined": [], "asked": []} for o in brief["options"]}
    evidence_by_episode = {}
    for row in sources.values():
        if row["kind"] != "observation":
            continue
        obs = _source_view(row)
        if (row["segment"], row["situation"]) != (brief.get("segment"), brief.get("situation")):
            context.append(obs)
            continue
        # These classifications are supplied by the synthetic observer. A text, action
        # or scope amendment requires a fresh coding pass. A digest cannot establish truth.
        if row.get("coding_digest") != coding_digest(row):
            unreviewed.append(obs)
            continue
        option, action = row.get("option"), row.get("observed_action")
        if option not in options or action not in ("used", "declined", "asked"):
            raise ValueError("Observed behavior must identify a commissioned option and a documented action")
        episode = row.get("record_id") or row["id"]
        if not _text(episode):
            raise ValueError("Invalid observation record")
        obs.update(record_id=episode, option=option, observed_action=action)
        observations.append(obs)
        # A duplicated observation from one episode is still one qualitative event.
        evidence_by_episode.setdefault((episode, option, action), []).append(row["id"])
        options[option][action].append(row["id"])
    used = {opt for _, opt, act in evidence_by_episode if act == "used"}
    declined = {opt for _, opt, act in evidence_by_episode if act == "declined"}
    selected = None
    missing = [k for k in ("segment", "situation", "owner") if not _text(brief.get(k))]
    if missing or len(options) < 2:
        status = "needs_clarification"
        if len(options) < 2:
            missing.append("second commissioned alternative")
    elif unreviewed:
        status = "insufficient_evidence"
        missing.append("review the coding of the amended observation")
    elif len(used) > 1 or used.intersection(declined):
        status = "conflicting_evidence"
    elif used:
        selected, = used
        status = "proposed"
    else:
        status = "insufficient_evidence"
    channel = _decision_input("channel", eligible, selected, options)
    measurement = _decision_input("measurement", eligible, selected, options)
    facts = [_source_view(s) for s in eligible if s["kind"] == "product_fact"]
    # Free-text formulations may concern the same product property. Until an editor
    # reconciles them, never concatenate distinct wordings into a Content claim.
    multiple_wordings = len({fact["excerpt"] for fact in facts}) > 1
    for key, item in (("channel", channel), ("measurement", measurement)):
        if item["status"] != "supported":
            missing.append(key)
    if not facts:
        missing.append("permitted product statement")
    elif multiple_wordings:
        missing.append("owner reconciliation of competing product wording")
    assumption = brief.get("assumption_option")
    if assumption is not None and assumption not in options:
        raise ValueError("The working assumption refers to an unknown option")
    contrary = [obs for obs in observations if obs["observed_action"] == "declined"
                or (assumption and obs["observed_action"] == "used" and obs["option"] != assumption)]
    chosen = options.get(selected)
    selected_sources = chosen["used"] if chosen else []
    basis = ([f"{ident} · {sources[ident]['excerpt']}" for ident in selected_sources]
             if chosen else ["Obtain another matched observation or clarify the commission before selecting a direction."])
    positioning = (f"For {brief['segment']} facing {brief['situation']}, lead the internal draft with: {chosen['label']}."
                   if chosen else None)
    decision = {"status": status, "selected_option": selected, "options": list(options.values()),
                "rationale": basis, "basis_sources": selected_sources, "owner": brief.get("owner"),
                "positioning": positioning, "tradeoff": chosen["tradeoff"] if chosen else None,
                "conditions": {"segment": brief.get("segment"), "episode": brief.get("situation"),
                               "as_of": packet["as_of"], "claim_limits": brief["constraints"]},
                "channel": channel, "measurement": measurement,
                "test_hypothesis": (f"In another {brief['segment']} episode of {brief['situation']}, "
                                    f"the buyer uses {chosen['label']}." if chosen else None),
                "reconsider_if": "A comparable buyer declines the selected approach or uses another, or its source rights change.",
                "approval": "Owner reviews the alternatives and signed claim wording before any external use."}
    limits = [*brief["constraints"], "Describe the product only with the permitted fact text and its qualifiers.",
              "Do not present one observed choice as buyer preference across the segment or as measured lift."]
    concept_ready = bool(chosen and facts and not multiple_wordings)
    placed = concept_ready and channel["status"] == "supported"
    handoff = {"status": "draft_for_approval" if placed else "hold",
               "recipient": "Content lead", "objective": brief["objective"], "audience": brief.get("segment"),
               "situation": brief.get("situation"), "asset": chosen["asset"] if placed else None,
               "internal_concept": ({"type": "unplaced internal concept for editor review", "option": selected,
                                     "permitted_product_wording": facts[0]["excerpt"]}
                                    if concept_ready and not placed else None),
               "message": ({"direction": chosen["label"], "product_wording": [fact["excerpt"] for fact in facts]}
                           if placed else None),
               "sources": list(dict.fromkeys([*selected_sources, *(fact["source_id"] for fact in facts)])),
               "claim_limits": limits, "channel": channel["value"],
               "approval": {"role": brief.get("owner"), "action": "Review the internal draft and source rights before distribution."}}
    research = {"decision": brief["decision"], "segment": brief.get("segment"), "buying_episode": brief.get("situation"),
                "observations": observations, "context_only": context, "awaiting_observation_review": unreviewed,
                "counterevidence": contrary, "product_facts": facts,
                "working_assumption": brief.get("assumption"), "missing": missing,
                "questions": ["Walk me through the last time you faced this buying decision. What happened?",
                              "What alternatives did you consider, and what changed your decision?"],
                "interpretation": (f"Test whether this episode merits a draft about {chosen['label']}. "
                                   "The observation establishes the recorded action; the buyer's reason remains unknown."
                                   if chosen else "The available records do not distinguish a preferred direction."),
                "limitations": list(dict.fromkeys(s["sample"] for s in sources.values())),
                "evidence_matrix": [_source_view(s) for s in eligible],
                "checkpoint_field_review": claim_review}
    return {"scope": packet["scope"], "as_of": packet["as_of"], "provenance": provenance, "research": research,
            "strategy": decision, "department_handoff": handoff, "level": "internal_synthetic_workpaper"}
