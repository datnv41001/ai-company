"""Measure rebuilding the deterministic delivery on the finished study's exact frozen input."""

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter_ns, process_time_ns
import tracemalloc

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from app import c3_assets, c3_customer_assets, c3_studio  # noqa: E402
from app.campaign_planner_pack import compose_assets  # noqa: E402


def measure(folder):
    source = json.loads((folder / "approved-inputs.json").read_text(encoding="utf-8"))
    plan = json.loads((folder / "commission.json").read_text(encoding="utf-8"))["plan"]
    expected = json.loads((folder / "first-package.json").read_text(encoding="utf-8"))
    tracemalloc.start()
    start, cpu = perf_counter_ns(), process_time_ns()
    groups = {}
    for kind, snap in source.items():
        projection = snap["projection"]
        groups[kind] = c3_studio.compose(snap["workflow"], projection)
        if snap["workflow"] == c3_assets.RESEARCH:
            groups[kind].update(c3_customer_assets.strategy(projection))
    groups["assets"] = {a["kind"]: a["body"] for a in compose_assets(plan)}
    wall, cpu_ns = perf_counter_ns() - start, process_time_ns() - cpu
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert all(groups[k] == expected[k] for k in groups)
    return {
        "wall_ns": wall,
        "cpu_ns": cpu_ns,
        "peak_traced_python_bytes": peak,
        "model_attempts": 0,
        "provider_fee_usd": 0,
        "scope": "One offline deterministic rebuild only. Excludes setup, database, human work, imported interpreter memory and waiting.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    observations = {case: measure(args.results / case / "control") for case in ("index-tray", "receipt-map")}
    (args.results / "control-rebuild.json").write_text(json.dumps(observations, indent=2) + "\n", encoding="utf-8")
