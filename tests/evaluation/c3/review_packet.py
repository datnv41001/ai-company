"""Produce labeled-by-case but arm-masked packets from actual completed local runs."""
import argparse
from hashlib import sha256
import json
from pathlib import Path


def write_packet(root):
    cases_path = Path(__file__).with_name("cases.json")
    cases = json.loads(cases_path.read_text(encoding="utf8"))["cases"]
    conditions = [json.loads((root / f"{arm}-conditions.json").read_text(encoding="utf8")) for arm in ("legacy","projected")]
    for field in ("model_sha256","build","case_file_sha256","seed","workers_per_case","provider"):
        if conditions[0][field] != conditions[1][field]:
            raise ValueError(f"Comparison conditions differ at {field}")
    if conditions[0]["case_file_sha256"] != sha256(cases_path.read_bytes()).hexdigest():
        raise ValueError("Case file differs from recorded conditions")
    out = root / "review"
    packet_dir = out / "packets"
    packet_dir.mkdir(parents=True, exist_ok=True)
    key = {}
    for case in cases:
        for workflow in ("WF-03","WF-13"):
            for arm in ("legacy","projected"):
                folder = root / arm / case["id"] / workflow
                record = json.loads((folder/"result.json").read_text(encoding="utf8"))
                assert record["arm"] == arm and record["case"] == case["id"] and record["workflow"].startswith(workflow + "/")
                pid = sha256(("AMC-C3-" + record["run_id"]).encode()).hexdigest()[:12]
                assert pid not in key
                draft = record.get("deliverable")
                body = draft["title"] + "\n\n" + draft["body"] if draft else "(Không có bản giao)"
                file = packet_dir / (pid + ".md")
                file.write_text(f"# {pid} · {case['id']} · {workflow}\n\n" + body + "\n", encoding="utf8")
                key[pid] = {"case":case["id"],"release":record["workflow"],"arm":arm,
                            "run":record["run_id"],"packet_sha256":sha256(file.read_bytes()).hexdigest()}
    (out/"key.json").write_text(json.dumps(key,indent=2)+"\n",encoding="utf8")
    return len(key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    print("Review packets:", write_packet(parser.parse_args().root))
