"""Check archived, synthetic evidence offline without loading weights or contacting a server."""

import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent / "evaluation/department"))
from handoff_comparison import DATA, digest, load, predictions, results  # noqa: E402
from handoff_infer import INPUT_CAP, OUTPUT_CAP, REQUEST_CAP, WALL_CAP, render  # noqa: E402
from advisory_study import MODEL  # noqa: E402


def test_receipts_and_scores_replay_without_inference(tmp_path):
    inputs = DATA / "inputs.json"
    labels = DATA / "gold.json"
    assert digest(inputs) == "b379f81b22aafec959403e78f9b2768f32c08647667c8c6a1746d140efd3eda7"
    assert digest(labels) == "d76a2bf2daacc6bb85cf3b1b8849cde10f7aac3d3c342295c9154435dd3b4c0f"
    cards = load(inputs)
    output = tmp_path / "replay"
    predictions(inputs, output)
    with zipfile.ZipFile(DATA / "FIRST-RUN.zip") as saved:
        names = {"control.json", "rules.json", "qwen.json", "run.json", "host.json"} | {"receipts/" + c["id"] + ".json" for c in cards}
        assert set(saved.namelist()) == names and len(saved.namelist()) == len(names)
        for arm in ("control", "rules"):
            assert load(output / (arm + ".json")) == json.loads(saved.read(arm + ".json"))
        frozen_run = json.loads(saved.read("run.json"))
        assert frozen_run["cohort_sha256"] == digest(inputs)
        assert frozen_run["wall_seconds"] <= WALL_CAP and frozen_run["new_provider_fee"] == 0
        assert json.loads(saved.read("host.json"))["weights"] == MODEL
        replies = []
        attempted = 0
        for card in cards:
            receipt = json.loads(saved.read("receipts/" + card["id"] + ".json"))
            assert receipt["id"] == card["id"]
            if receipt["attempted"]:
                attempted += 1
                assert receipt["weights_sha256"] == MODEL and receipt["prompt"] == render(card)
                assert receipt["input_tokens"] == len(receipt["request"]["prompt"]) <= INPUT_CAP
                assert receipt["request"]["n_predict"] == OUTPUT_CAP and receipt.get("output_tokens", 0) <= OUTPUT_CAP
            if receipt["status"] == "returned":
                answer = json.loads(receipt["raw_output"])
                assert answer["id"] == card["id"]
                replies.append(answer)
        assert attempted <= REQUEST_CAP and replies == json.loads(saved.read("qwen.json"))
        (output / "qwen.json").write_bytes(saved.read("qwen.json"))
    assert results(inputs, labels, output) == load(DATA / "metrics.json")
