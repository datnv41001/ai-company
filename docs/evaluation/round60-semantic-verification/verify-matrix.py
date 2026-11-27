"""Build a receipt-backed comparison of real WF-08 PostgreSQL cases from two independent DB runs."""

import argparse
import hashlib
import json
from pathlib import Path


def fingerprint(value):
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf8")).hexdigest()


def load_case(folder, action, style):
    path = folder / f"{action}-{style}.json"
    case = json.loads(path.read_text(encoding="utf8"))
    assert (case["action"], case["style"]) == (action, style)
    receipt = case["edit_receipt"]
    comparison = receipt["comparison"]
    assert comparison["changed_variables"] == ["hook"] and comparison["baseline_holds"] == comparison["candidate_holds"]
    content = case["content"]
    raw, edit = case["original"], case["alternate"]
    assert raw["content_handoff_digest"] == edit["content_handoff_digest"] == fingerprint(content)
    assert raw["hook"] == content["channel_copy"]["opening"]
    source = case["manifest"]
    assert source == raw["source_refs"]["manifest"] == edit["source_refs"]["manifest"] == content["manifest"]
    assert case["run"] == receipt["run_id"] and case["provenance"]["manifest_digest"] == source["digest"]
    assert [step["skill"] for step in case["worker_journal"]] == ["director", "content", "storyboard"]
    assert all(step["input_tokens"] == step["output_tokens"] == 0 for step in case["worker_journal"])
    first, second = case["qa"]
    assert first[1] == second[1] and first[0] != second[0]
    for (_identifier, _actor, record), board, revision_key, digest_key in (
        (first, raw, "baseline_revision", "baseline_content_digest"), (second, edit, "revision", "content_digest")
    ):
        assert record["manifest_digest"] == source["digest"] and record["document_id"] == receipt["document_id"]
        assert record["storyboard_digest"] == fingerprint(board) and record["run_id"] == case["run"]
        assert record["qa_revision"] == receipt[revision_key] and record["content_digest"] == receipt[digest_key]
    assert second[2]["edition_receipt_digest"] == fingerprint(receipt)
    return dict(
        source_file=path.name, file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        run_id=case["run"], manifest=source, original=raw["hook"], alternate=edit["hook"], cta=edit["cta"],
        release_digest=second[2]["release_digest"], verified_qa_commands=[first[0], second[0]],
        revisions=[first[2]["qa_revision"], second[2]["qa_revision"]], changed_variables=comparison["changed_variables"],
    )


def generate(old, new):
    matrix = []
    lines = [
        "# WF-08/2 semantic review matrix", "",
        "Every cell comes from a signed synthetic brief through the PostgreSQL queue, the scoped editor, submission and independent QA. "
        "Each side is a separate database run; compare wording and within-run receipts. "
        "Both original and edited content revisions received approval. The matched RED assertions document why approvals on the historical wording were insufficient.",
        "", "| Action | Style | Reviewed opening | Reviewed alternate | Corrected opening | Corrected alternate | CTA |",
        "|---|---|---|---|---|---|---|",
    ]
    for action in ("rfq", "appointment", "choose_session"):
        for style in ("plain", "concise", "formal", "friendly"):
            a, b = (load_case(folder, action, style) for folder in (old, new))
            assert a["cta"] == b["cta"]
            matrix.append(dict(action=action, style=style, reviewed=a, corrected=b))
            lines.append(f"| {action} | {style} | {a['original']} | {a['alternate']} | {b['original']} | {b['alternate']} | {b['cta']} |")
    terms = []
    for action in ("appointment", "choose_session"):
        a, b = [json.loads((folder / f"terms-{action}.json").read_text(encoding="utf8")) for folder in (old, new)]
        for record in (a, b):
            assert record["manifest"] == record["board"]["source_refs"]["manifest"]
            assert record["content"]["channel_copy"]["opening"] == record["board"]["hook"]
        terms.append({"action":action, "reviewed":a["qa_status"], "corrected":b["qa_status"],
                      "reviewed_angle":a["content"]["angle"],"corrected_angle":b["content"]["angle"],
                      "original":a["board"]["hook"],"corrected_opening":b["board"]["hook"]})
    lines += ["", "## Explicit quote-condition instruction", "",
              "| Signed conversion | Old angle | Current angle | Current hook | QA (old → current HTTP) |",
              "|---|---|---|---|---|"]
    for row in terms:
        lines.append(f"| {row['action']} | {row['reviewed_angle']} | {row['corrected_angle']} | {row['corrected_opening']} | {row['reviewed']} → {row['corrected']} |")
    return {"matrix":matrix,"commercial_information":terms}, "\n".join(lines) + "\n"


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("reviewed_outputs", type=Path)
    p.add_argument("corrected_outputs", type=Path)
    p.add_argument("destination", type=Path)
    args=p.parse_args()
    data, markdown=generate(args.reviewed_outputs, args.corrected_outputs)
    args.destination.mkdir(parents=True, exist_ok=True)
    (args.destination / "matrix.md").write_text(markdown, encoding="utf8", newline="\n")
    (args.destination / "matrix.json").write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf8", newline="\n")
