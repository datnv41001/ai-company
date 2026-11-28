"""Development-only token count using the pinned GGUF vocabulary. No generation or network."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from rs01_study import build
from app import c3_assets, c3_order_units, c3_skill_library, c3_studio

HERE = Path(__file__).resolve().parents[2] / "docs/evaluation/research-instruction"
MODEL = "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"
CUE = "State two rival explanations, what to observe, and when to switch or hold."


def count(exe, model, text, folder):
    path = folder / "text.txt"
    path.write_text(text, encoding="utf8")
    result = subprocess.run([exe, "-m", model, "-f", str(path), "--ids", "--no-bos"], capture_output=True, check=True, text=True, encoding="utf8")
    return len(json.loads(result.stdout.strip()))


def measure(exe, model):
    with Path(model).open("rb") as source:
        assert hashlib.file_digest(source, "sha256").hexdigest() == MODEL
    dev = json.loads((HERE / "development.json").read_bytes())
    projection, reply = dev["projection"], dev["reply"]
    sources = {f["id"]: f for f in projection["facts"]}
    validated = c3_skill_library.validate(reply, "research", {}, sources)
    checkpoints = {"research": validated}
    studio = c3_studio.compose(c3_assets.RESEARCH, projection, checkpoints)
    notes = c3_order_units.artifacts(c3_assets.RESEARCH, projection, checkpoints)["research_notes"]["fields"]
    assert notes["evidence_needed"] == reply["evidence_needed"] and reply["evidence_needed"] not in studio["research"].values()
    assert studio["research"]["buyer_problem"] == reply["buyer_problem"] and studio["research"]["research_question"] == reply["research_question"]
    request = build({"projection":projection}, "research", "A", assignment="Compare two barriers in this synthetic shift.")
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        output = count(exe, model, json.dumps(reply,ensure_ascii=False,separators=(",",":")), folder)
        text = [m["content"] for m in request["messages"]]
        # Counts of literal message bodies. Template and renderer overhead must be preflighted at the future lock.
        inputs = {arm:count(exe,model,"\n".join([text[0]+extra,*text[1:]]),folder) for arm,extra in (("A",""),("C"," "+CUE))}
    assert output < 220
    return {"gguf_sha256":MODEL,"scope":"one public development fixture, no holdout, no generation",
            "field_characters":{k:len(v) for k,v in validated["sections"].items()},
            "output_json_tokens":output,"remaining_before_220":220-output,"message_body_tokens":inputs,
            "source_handles":reply["source_ids"],"visible_in_studio":["buyer_problem","research_question"],
            "staff_notes_only":["evidence_needed"],"exact_templated_request_preflight":"pending for the authorized protocol",
            "research_performed":False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", required=True)
    parser.add_argument("--gguf",required=True)
    args = parser.parse_args()
    print(json.dumps(measure(args.tokenizer,args.gguf),ensure_ascii=False,indent=2))
