"""Merge returned blind forms offline without treating a blank as a result or cost."""

import argparse
import json
import math
from pathlib import Path
from statistics import median


def nonnegative(v):
    return type(v) in (int,float) and math.isfinite(v) and v >= 0


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def duration(form):
    value = form.get("task_minutes", {}).get("total_elapsed")
    return value if nonnegative(value) else None


def labor_cost(form):
    rate = form.get("hourly_rate_and_currency") or {}
    minutes = form.get("task_minutes", {})
    phases = ["planning","drafting","source_check","editing","qa"]
    # Preserve older returned forms. New forms must explicitly record zero or measured time.
    phases.extend(k for k in ("clarification","commercial_correction") if k in minutes)
    times = [minutes.get(k) for k in phases]
    amounts = [rate.get("amount"),form.get("compute_cost"),form.get("provider_cost"),*times]
    if not all(nonnegative(v) for v in amounts) or not rate.get("currency"):
        return None
    return rate["currency"], sum(times) * rate["amount"] / 60 + form["compute_cost"] + form["provider_cost"]


def weighted(forms, passed, total):
    if any(not nonnegative(f.get(k)) for f in forms for k in (passed,total)):
        return None
    if any(f[passed]>f[total] for f in forms):
        raise ValueError(f"Numerator larger than denominator for {passed}")
    return ratio(sum(f[passed] for f in forms),sum(f[total] for f in forms))


def compare(key, returned):
    schedule = {r["code"]:r for r in key["assignments"]}
    data = {}
    for form in returned:
        code = form["blind_asset_id"]
        if code not in schedule or code in data:
            raise ValueError("Unknown or duplicate sheet " + str(code))
        slot = schedule[code]
        if (form["brief_id"],form["phase"],form["workflow"]) != (slot["task"],slot["phase"],slot["workflow"]):
            raise ValueError("Returned sheet does not match its assigned brief and phase")
        data[code] = form
    quality = {}
    for arm in ("projected","improved"):
        slots = [s for s in schedule.values() if s["phase"]==3 and s["arm"]==arm]
        keyed = {s["code"]:data.get(s["code"],{}) for s in slots}
        valid = []
        for code,f in keyed.items():
            if f.get("first_pass_accepted") is None:
                continue
            scores = f.get("scores",{})
            if (type(f["first_pass_accepted"]) is not bool or set(scores)!={"du_kien","pham_vi","chung_cu","huu_ich","chuyen_mon","khong_tuyen_bo_vo_can_cu"}
                    or any(type(v) is not int or v not in (0,1) for v in scores.values())):
                raise ValueError("Invalid or incomplete rubric for " + code)
            if f["first_pass_accepted"] and (not all(scores.values()) or f.get("severe_scope_or_claim_errors")):
                raise ValueError("First-pass acceptance contradicts a recorded unmet criterion: " + code)
            valid.append(f)
        complete = len(valid)==len(slots)
        quality[arm] = {
            "assigned_readings":len(slots),"rated":len(valid),
            "first_pass_rate":ratio(sum(f["first_pass_accepted"] for f in valid),len(slots)) if complete else None,
            "structured_value_accuracy":weighted(valid,"correct_structured_values","total_structured_values") if complete else None,
            "material_source_support":weighted(valid,"valid_material_citations","total_material_claims") if complete else None,
            "severe_error_readings":sum(f["severe_scope_or_claim_errors"]>0 for f in valid)
                if complete and all(nonnegative(f.get("severe_scope_or_claim_errors")) for f in valid) else None,
            "disagreements":[],
        }
        for case in sorted({s["case"] for s in slots}):
            a,b = [keyed[s["code"]] for s in slots if s["case"]==case]
            if a.get("first_pass_accepted") is not None and b.get("first_pass_accepted") is not None:
                if a["first_pass_accepted"] != b["first_pass_accepted"] or a["scores"] != b["scores"]:
                    quality[arm]["disagreements"].append({"case":case,"review_forms":[a["blind_asset_id"],b["blind_asset_id"]]})
    timed = {s["code"]:s for s in schedule.values() if s["phase"]<3}
    pairs = []
    for case in sorted({s["case"] for s in timed.values()}):
        manual,assisted = sorted((s for s in timed.values() if s["case"]==case),key=lambda v:v["phase"])
        left,right = (duration(data.get(s["code"],{})) for s in (manual,assisted))
        pairs.append({"brief":manual["task"],"assisted_arm":assisted["arm"],
                      "manual_minutes":left,"assisted_minutes":right,
                      "phase_minutes":{s["arm"]:data.get(s["code"],{}).get("task_minutes") for s in (manual,assisted)},
                      "time_saving_fraction":1-right/left if left and right is not None else None})
    complete = all(p["manual_minutes"] is not None and p["assisted_minutes"] is not None for p in pairs)
    denominator = sum(p["manual_minutes"] for p in pairs) if complete else 0
    timing = {"pairs":pairs, "total_time_saving_fraction":1-sum(p["assisted_minutes"] for p in pairs)/denominator if denominator else None}
    for condition in ("manual","assisted"):
        mins = [r[condition+"_minutes"] for r in pairs]
        timing[condition] = {"median":median(mins),"range":[min(mins),max(mins)]} if all(t is not None for t in mins) else None
    costs = {}
    for arm in ("manual","projected","improved"):
        forms = [data.get(code,{}) for code,s in timed.items() if s["arm"]==arm]
        amounts = [labor_cost(f) for f in forms]
        accepted = [f.get("accepted_after_editing") for f in forms]
        costs[arm] = None
        if all(a is not None for a in amounts) and all(type(v) is bool for v in accepted) and sum(accepted):
            if len({a[0] for a in amounts})==1:
                costs[arm] = {"currency":amounts[0][0], "per_accepted":sum(a[1] for a in amounts)/sum(accepted)}
    return {"assigned_sheets":len(schedule),"received_sheets":len(data),"quality":quality,"timed_comparison":timing,"cost":costs}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("key",type=Path)
    cli.add_argument("returned",type=Path,help="Directory containing only returned PHIEU.json files, under separate subdirectories.")
    opts = cli.parse_args()
    forms = []
    for path in sorted(opts.returned.rglob("PHIEU.json")):
        forms.extend(json.loads(path.read_text(encoding="utf-8-sig")))
    print(json.dumps(compare(json.loads(opts.key.read_text(encoding="utf-8")),forms),ensure_ascii=False,indent=2,allow_nan=False))
