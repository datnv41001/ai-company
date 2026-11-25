"""Guided correction of a scoped public price card through existing immutable revision and approval APIs."""

from copy import deepcopy
from hashlib import sha256
from typing import Literal

from pydantic import Field

from . import knowledge_models as m
from .knowledge_authority import change_state, eligible, new_revision
from .knowledge_contracts import Command, EventIn, Name, Note, Ref, RevisionIn, approval_category, price_wording
from .knowledge_store import conflict, missing

UNITS = {"visit": "lượt thực hiện dịch vụ", "participant": "người tham gia", "machine": "máy"}


class Proposal(Command):
    claim: Ref
    claim_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    offer_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    unit: Literal["visit", "participant", "machine"]
    document: Name
    locator: Name
    excerpt: Note
    confirm_same_terms: Literal[True]


class Decision(Command):
    proposal: Ref
    qualification_revision: Ref | None = None
    reason: Name


def commercial_rows(s, claim_id):
    claim = s.get(m.KnowledgeRevision, claim_id)
    if claim.kind != "claim" or claim.visibility != "public":
        missing()
    a = claim.data["assertion"]
    if a["category"] != "price" or a["price"]["unit"] != "service":
        conflict("Chỉ làm rõ thẻ giá đang có đơn vị dịch vụ chung.")
    offer = s.get(m.KnowledgeRevision, a["offer"])
    if offer.kind != "offer" or offer.data["price"] != a["price"]:
        conflict("Giá đã thay đổi; cần đối chiếu bản chào giá hiện tại.")
    return claim, offer


def issues(s, ids):
    result = []
    for rid in ids:
        row = s.get(m.KnowledgeRevision, rid)
        a = row.data.get("assertion", {})
        if row.kind != "claim" or row.visibility != "public" or (a.get("price") or {}).get("unit") != "service":
            continue
        claim, offer = commercial_rows(s, rid)
        issue = {
            "field": "price.unit",
            "claim": rid,
            "claim_digest": claim.digest,
            "offer_revision": offer.revision,
            "offer_digest": offer.digest,
            "terms": offer.data["price"],
            "qualifiers": a["qualifiers"],
            "quantity": a["quantity"],
            "choices": UNITS,
            "can_amend": s.approver,
            "proposal": None,
        }
        if s.approver:
            # Shared between author and independent reviewer only within the same store scope.
            stmt = (
                s.query(m.KnowledgeCommand)
                .filter_by(operation="c3_unit_proposal")
                .where(m.KnowledgeCommand.result["original_claim"].as_string() == rid)
                .order_by(m.KnowledgeCommand.effective_at.desc())
                .limit(1)
            )
            receipt = s.db.scalar(stmt)
            if receipt is not None:
                replacement = s.get(m.KnowledgeRevision, receipt.result["claim"])
                issue["proposal"] = {
                    "id": receipt.id,
                    "claim": replacement.id,
                    "unit": replacement.data["assertion"]["price"]["unit"],
                    "state": s.summary(replacement)["state"],
                    "required_qualification": approval_category(replacement.data["assertion"]),
                    "own": replacement.author == s.actor,
                    "evidence": receipt.result["source"],
                }
                category = issue["proposal"]["required_qualification"]
                candidates = s.db.scalars(
                    s.query(m.KnowledgeRevision)
                    .filter_by(kind="qualification")
                    .where(
                        m.KnowledgeRevision.data["approver_id"].as_string() == s.actor,
                        m.KnowledgeRevision.data["category"].as_string() == category,
                    )
                )
                issue["proposal"]["qualifications"] = [row.id for row in candidates if s.summary(row)["state"] == "approved"]
        result.append(issue)
    return result


def propose(s, body, selection, check_selection):
    if not s.approver or body.claim not in selection.claims:
        missing()

    def save(at):
        claim, offer = commercial_rows(s, body.claim)
        if (claim.digest, offer.digest) != (body.claim_digest, body.offer_digest):
            conflict("Tải lại bản thương mại đang xem.")
        eligible(s, claim, at, {})
        assertion = deepcopy(claim.data["assertion"])
        assertion["price"]["unit"] = body.unit
        assertion["wording"] = price_wording(assertion["price"])
        suffix = sha256((str(s.actor) + ":" + str(body.key)).encode()).hexdigest()[:24]

        def draft(kind, subject, data, visibility, expected=0):
            rev = new_revision(s, RevisionIn(key=body.key, kind=kind, subject=subject, data=data, visibility=visibility, expected_revision=expected), at)
            return rev["id"]

        updated = draft("offer", offer.subject, {**offer.data, "price": assertion["price"]}, offer.visibility, offer.revision)
        assertion["offer"] = updated
        binding = s.get(m.KnowledgeRevision, claim.data["binding"])
        prior_source = s.get(m.KnowledgeRevision, binding.data["source"])
        # A new attestation gets its own document and locator. Do not rewrite or cite the
        # previous source as though it had supplied the corrected unit or extended expiry.
        source = draft(
            "source",
            "unit-source-" + suffix,
            {
                "publisher": "Commercial data owner",
                "document": body.document,
                "valid_from": prior_source.data.get("valid_from"),
                "valid_until": prior_source.data["valid_until"],
                "entries": [{"locator": body.locator, "excerpt": body.excerpt, "assertion": assertion}],
            },
            "restricted",
        )
        bound = draft("binding", "unit-binding-" + suffix, {"source": source, "locator": body.locator, "assertion": assertion}, "restricted")
        replacement = draft("claim", claim.subject, {**claim.data, "binding": bound, "assertion": assertion}, "public", claim.revision)
        return (
            {
                "original_claim": claim.id,
                "original_offer": offer.id,
                "offer": updated,
                "source": source,
                "binding": bound,
                "claim": replacement,
                "unit": body.unit,
                "workspace_brief_id": selection.workspace_brief_id,
                "resume": selection.model_dump(mode="json"),
            },
            "restricted",
            None,
        )

    return s.command("c3_unit_proposal", body, save, target=selection.model_dump(mode="json"), prepare=check_selection)


def approve(s, body):
    if not s.approver:
        missing()
    receipt = s.get(m.KnowledgeCommand, body.proposal)
    if receipt.operation != "c3_unit_proposal":
        missing()

    def decide(at):
        original, _ = commercial_rows(s, receipt.result["original_claim"])
        eligible(s, original, at, {})
        for kind in ("offer", "source", "binding", "claim"):
            row = s.get(m.KnowledgeRevision, receipt.result[kind])
            event = EventIn(
                key=body.key,
                expected_sequence=0,
                expected_digest=row.digest,
                state="approved",
                reason=body.reason,
                qualification_revision=body.qualification_revision if kind == "claim" else None,
            )
            change_state(s, row, event, at)
        return {"original_claim": original.id, "claim": receipt.result["claim"], "unit": receipt.result["unit"]}, "restricted", None

    return s.command("c3_unit_approval", body, decide)


def inbox(s, offset, workspace_brief=None):
    if not s.approver:
        missing()
    stmt = s.query(m.KnowledgeCommand).filter_by(operation="c3_unit_proposal")
    if workspace_brief is not None:
        stmt = stmt.where(m.KnowledgeCommand.actor == s.actor, m.KnowledgeCommand.result["workspace_brief_id"].as_string() == workspace_brief)
    rows = list(s.db.scalars(stmt.order_by(m.KnowledgeCommand.effective_at.desc(), m.KnowledgeCommand.id.desc()).offset(offset).limit(21)))
    items = []
    for receipt in rows[:20]:
        issue = issues(s, [receipt.result["original_claim"]])[0]
        if issue["proposal"]["id"] != receipt.id:
            continue
        if workspace_brief is not None:
            items.append(
                {
                    "selection": receipt.result["resume"],
                    "status": issue["proposal"]["state"],
                    "original_claim": receipt.result["original_claim"],
                    "claim": receipt.result["claim"],
                    "unit": receipt.result["unit"],
                }
            )
        elif issue["proposal"]["state"] == "draft":
            # Commercial reviewers need the price and attestation, not another person's private task.
            source = s.get(m.KnowledgeRevision, receipt.result["source"])
            offer = s.get(m.KnowledgeRevision, receipt.result["offer"])
            product = s.get(m.KnowledgeRevision, offer.data["placement"]["product"])
            items.append(
                {
                    **issue,
                    "product": product.data["name"],
                    "document": source.data["document"],
                    "excerpt": source.data["entries"][0]["excerpt"],
                    "locator": source.data["entries"][0]["locator"],
                }
            )
    return {"items": items, "next_offset": offset + 20 if len(rows) > 20 else None}
