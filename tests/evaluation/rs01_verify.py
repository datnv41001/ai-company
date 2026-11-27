"""Verify exported evidence offline. Add a private directory only after authorized unsealing."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

import rs01_study as study


def file_hash(data):
    return hashlib.sha256(data).hexdigest()


def main(private=None):
    doc = study.DOC
    report = json.loads((doc/"RESULTS.json").read_bytes())
    lock = json.loads((doc/"LOCK.json").read_bytes())
    packets = {c["id"]:c for c in json.loads((doc/"packets.json").read_bytes())}
    def blob(sha,path):
        return subprocess.check_output(["git","-c","safe.directory="+study.ROOT.as_posix(),"show",sha+":"+path],cwd=study.ROOT)
    for path, expected in lock["sources"].items():
        data = blob(report["checkout"],path)
        # The immutable lock hashed the Windows working copy. Only the existing catalog used CRLF.
        if path == "catalog/research-strategy-v3.json":
            data = data.replace(b"\n", b"\r\n")
        assert file_hash(data) == expected
    assert lock["baseline"] == report["baseline"] == study.BASE
    assert report["model_sha256"] == lock["machine"]["model_sha256"] == study.MODEL
    assert len(lock["preflight"]) == 24
    for item in lock["preflight"]:
        study.admit(item["tokens"],0,0,0,1)
    assert file_hash((doc/"REVIEW-BLIND.zip").read_bytes())==report["blind_pack_sha256"]
    with zipfile.ZipFile(doc/"REVIEW-BLIND.zip") as z:
        assert z.testzip() is None
        expected_names = {"SCORES.json","START-HERE.md","SHA256SUMS.txt"} | {
            f"{case}/{name}.json" for case in packets for name in ("sources","Left","Right")}
        assert len(z.namelist()) == len(expected_names) and set(z.namelist()) == expected_names
        for line in z.read("SHA256SUMS.txt").decode().splitlines():
            h,p=line.split("  ",1)
            assert file_hash(z.read(p))==h
        assert len(z.read("SHA256SUMS.txt").splitlines()) == len(expected_names)-1
        sheet=json.loads(z.read("SCORES.json"))
        assert {p["case"] for p in sheet["pairs"]} == set(packets)
        for p in sheet["pairs"]:
            assert json.loads(z.read(p["case"]+"/sources.json")) == packets[p["case"]]
            for name,scores in p["sides"].items():
                assert len(scores["scores"])==6 and scores["rateable"] is None
                assert all(s["score"] is None for s in scores["scores"].values())
                stages=json.loads(z.read(p["case"]+"/"+name+".json"))
                assert set(stages)==set(study.ROLES)
                for role,output in stages.items():
                    assert set(output)=={"first_output","status"}
        if private:
            key=json.loads((private/"mapping.json").read_bytes())
            assert study.digest(study.encoded(key))==lock["mapping_commitment"]
            calls=json.loads((private/"journal.json").read_bytes())["calls"]
            assert len(calls)==len(list(private.glob("call-*.intent")))==report["calls"]==24
            assert len({(c["case"],c["arm"],c["role"]) for c in calls})==24
            assert sum(c["input_tokens"] for c in calls)==report["input_tokens"]<=36000
            assert sum(c["output_tokens"] for c in calls)==report["output_tokens"]<=5280
            assert 0<report["wall_seconds"]<=1800 and report["unmetered"]==0
            for i,c in enumerate(calls,1):
                raw=json.loads((private/f"call-{i:02}.raw").read_bytes())
                actual=json.loads(raw["response_text"])
                assert c["response_text"]==raw["response_text"] and c["request_sha256"]==study.digest(study.encoded(raw["request"]))
                assert actual["usage"]["prompt_tokens"]==c["input_preflight"]==c["input_tokens"]<=1500
                assert actual["usage"]["completion_tokens"]==c["output_tokens"]<=220
            for pair in key["pairs"]:
                case=packets[pair["id"]]
                for arm in ("A","B"):
                    label="Left" if pair["left"]==arm else "Right"
                    blind=json.loads(z.read(f"{case['id']}/{label}.json"))
                    chain=[c for c in calls if (c["case"],c["arm"])==(case["id"],arm)]
                    assert [c["role"] for c in chain]==list(study.ROLES)
                    assignments={}
                    earlier={}
                    for c in chain:
                        role=c["role"]
                        expected=study.build(case,role,arm,assignments.get(role,""),earlier)
                        assert expected==c["request"]
                        assert blind[role]["first_output"]==json.loads(c["response_text"])["choices"][0]["message"]["content"]
                        value=study.validate(case,role,json.loads(blind[role]["first_output"]),expected["response_format"]["json_schema"]["schema"])
                        if role=="director":
                            assignments={"research":value["primary_assignment"],"strategy":value["secondary_assignment"]}
                        if role=="research":
                            earlier={"research":value["text"][:1400]}
    for path in ("app","catalog","migrations",".github/workflows"):
        subprocess.run(["git","-c","safe.directory="+study.ROOT.as_posix(),"diff","--exit-code",study.BASE,"--",path],
                       cwd=study.ROOT,check=True,stdout=subprocess.DEVNULL)
    print("PASS: frozen sources, 4 source packets, 8 dossiers, blind manifest, 6 criteria, runtime scope.")
    if private:
        print("PASS: all 24 first responses, prompt replay, schema/source parity, actual token meters, aggregate caps and assignment commitment.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private",type=Path)
    main(parser.parse_args().private)
