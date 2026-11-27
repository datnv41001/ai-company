"""Export first outputs without treatment, ordering or token-length side channels."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/evaluation/rs01"
DIMENSIONS = ["segment_decision_maker","facts_observations_hypotheses","research_evidence",
              "positioning_rationale_action","action_measurement","cross_stage_brief_consistency"]
FLAGS = ["contradicted_source","unauthorized_action","altered_terms","lost_constraint"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2)+"\n").encode()


def write_zip(path, members):
    with zipfile.ZipFile(path,"x",compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(members.items()):
            info = zipfile.ZipInfo(name, (2026,1,1,0,0,0))
            archive.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None


def main(private):
    lock = read(DOC/"LOCK.json")
    journal = read(private/"journal.json")
    key = read(private/"mapping.json")
    canonical = json.dumps(key,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    assert sha(canonical) == lock["mapping_commitment"]
    protocol = (DOC/"PROTOCOL.md").read_text(encoding="utf8")
    scoring = protocol.split("## Scoring contract\n",1)[1].split("## Blinding and evidence",1)[0]
    scoring = scoring.split("Once all first judgments are locked")[0].strip()
    intro = """# Independent AI review · Research and Strategy first drafts

Read the source packet for each pair. Score both drafts independently using the rubric below. The recorded Director choices supply context; the two specialist stages are the editing unit. Source packets and outputs are synthetic. Keep the original response texts, including unusual phrasing. Missing downstream work is identified explicitly. Fill SCORES.json, cite each meaningful correction and avoid counting two corrections to one field twice. Indicate AI reviewer status and potential uncertainty. Lock the returned file (SHA-256) before requesting the assignment key. No paid service, external action or practitioner time measurement is part of this packet.

"""
    members = {"START-HERE.md":(intro+scoring+"\n").encode()}
    sheet = {"reviewer_type":"Independent AI Reviewer","reviewer_session":None,"pairs":[]}
    paired = []
    full = 0
    calls=journal["calls"]
    for case in read(DOC/"packets.json"):
        pair = next(p for p in key["pairs"] if p["id"]==case["id"])
        pair_id = case["id"]
        members[f"{pair_id}/sources.json"]=json_bytes(case)
        row = {"case":pair_id, "sides":{}}
        evaluation={"case":pair_id,"sides":{},"pair_note":None}
        for label,arm in (("Left",pair["left"]),("Right","B" if pair["left"]=="A" else "A")):
            items=[c for c in calls if c["case"]==pair_id and c["arm"]==arm]
            stages={}
            for role in ("director","research","strategy"):
                receipt=next((c for c in items if c["role"]==role),None)
                if receipt is None:
                    stages[role]={"status":"not_run","first_output":None}
                    continue
                body=json.loads(receipt["response_text"]) if receipt.get("response_text") else {}
                choices=body.get("choices",[])
                first=choices[0]["message"]["content"] if choices else None
                ok=("finish" in receipt and receipt["finish"]=="stop" and "error" not in receipt and
                    (private/f"call-{calls.index(receipt)+1:02}.json").is_file())
                stages[role]={"status":"contract_valid" if ok else "incomplete_or_invalid","first_output":first}
            members[f"{pair_id}/{label}.json"]=json_bytes(stages)
            complete=all(stage["status"]=="contract_valid" for stage in stages.values())
            row["sides"][label]={"complete":complete,"edit_count":None,"hard_failures":None}
            evaluation["sides"][label]={"rateable":None,"scores":{d:{"score":None,"evidence":None} for d in DIMENSIONS},
                  "meaningful_edits":[],"hard_failures":{k:None for k in FLAGS},"unsupported_claims":None}
        row["complete"]=all(s["complete"] for s in row["sides"].values())
        full+=int(row["complete"])
        paired.append(row)
        sheet["pairs"].append(evaluation)
    members["SCORES.json"]=json_bytes(sheet)
    members["SHA256SUMS.txt"]="".join(f"{sha(data)}  {name}\n" for name,data in sorted(members.items())).encode()
    write_zip(DOC/"REVIEW-BLIND.zip",members)
    # This intermediate is NEVER published in plaintext.
    source_files=[private/"mapping.json",private/"started.json",private/"journal.json"]
    source_files+=sorted(private.glob("call-*"))
    write_zip(private/"ordered-evidence.zip",{p.name:p.read_bytes() for p in source_files})
    usage={r:dict(calls=sum(c["role"]==r for c in calls),
                  input_tokens=sum(c.get("input_tokens",0) for c in calls if c["role"]==r),
                  output_tokens=sum(c.get("output_tokens",0) for c in calls if c["role"]==r))
           for r in ("director","research","strategy")}
    report=dict(checkout=journal["checkout"],baseline=lock["baseline"],model_sha256=lock["machine"]["model_sha256"],
                calls=len(calls),usage_by_role=usage,unmetered=sum("input_tokens" not in c for c in calls),
                input_tokens=journal["input_tokens"],output_tokens=journal["output_tokens"],
                wall_seconds=journal["wall_seconds"],provider_fee_usd=0,hardware_energy_editor_cost=None,
                stop=journal["stop"],complete_pairs=full,pairs=paired,locked_independent_scores=0,
                exploratory_threshold="pending independent scores" if full==4 else "not evaluable: incomplete pairs",
                request_digests_verified=all(c["request_sha256"] == sha(json.dumps(c["request"],ensure_ascii=False,
                         sort_keys=True,separators=(",",":")).encode()) for c in calls),
                blind_pack_sha256=sha((DOC/"REVIEW-BLIND.zip").read_bytes()),
                ordered_evidence_plaintext_sha256=sha((private/"ordered-evidence.zip").read_bytes()),
                mapping_commitment=lock["mapping_commitment"])
    assert len(calls)<=24 and journal["input_tokens"]<=36000 and journal["output_tokens"]<=5280
    assert report["request_digests_verified"]
    (DOC/"RESULTS.json").write_bytes(json_bytes(report))
    print(json.dumps({k:report[k] for k in ("calls","input_tokens","output_tokens","wall_seconds","complete_pairs","unmetered","stop")}))


if __name__=="__main__":
    main(Path(sys.argv[1]))
