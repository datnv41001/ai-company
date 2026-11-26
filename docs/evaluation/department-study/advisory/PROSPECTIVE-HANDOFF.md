# Buyer clarification before Sales or Service handoff

## Decision under test

A Sales coordinator triaging a request for quotation and a Service coordinator preparing an appointment both need an answer to the same question. Does the latest buyer message and the approved brief support handoff, one focused question, or internal escalation? Asking for information already supplied wastes a contact. Marking a stale value as ready can send an incomplete request downstream. The study compares three ways to recommend the next step. A person retains authority for CRM changes, quotes, terms and confirmations.

## Evidence and population

The first [specialist obligation study](REPLAY.md) recorded 24/36 obligations for its control and 17/36 for Qwen rewrite. The original [handoff study](HANDOFF-BENCHMARK.md) recorded 14/24 exact and eight false-ready decisions for the existing rules. The two studies measure different tasks. Their denominators and earlier results are kept separate.

The new [cohort and protocol](../../../../tests/evaluation/department/handoff-v2/PROTOCOL.md) concern twelve AI-authored synthetic situations with matched Vietnamese and English versions. Each has a buyer message, an approved requirement, and a structured CRM projection. The separate custodian sealed the inputs and gold, then released only the public inputs after commit `cf65816334b4a25a0fd368f9e66387308acc3e17` froze both rule sets, the model prompt, scorer, criteria and cap. The archived predictions were sealed before the answer key was released. Twelve scenario pairs permit descriptive comparisons. There are zero practitioner observations, no measured time saved with actual buyers and no evidence of conversion lift or operating ROI.

## Results and decision

**Keep advisory inference out of the product handoff.** Qwen identified five additional required questions but lost six correct ready decisions, for a net loss of one. Its Vietnamese exact-match count fell by one. The minimum improvement was four, with no locale regression. The revised deterministic rules produced byte-identical answers to the old rules. Neither alternative earns promotion on this evidence.

| New synthetic holdout | Existing rules | Revised rules | Local Qwen |
| --- | ---: | ---: | ---: |
| Exact decision and field, full contract | 8/24 | 8/24 | 7/24 |
| Exact VI / EN (12 each) | 4 / 4 | 4 / 4 | 3 / 4 |
| Pairs exact in both languages | 4/12 | 4/12 | 3/12 |
| Exact when the reference requires asking | 2/8 | 2/8 | 7/8 |
| Exact when internal policy clarification is required | 0/8 | 0/8 | 0/8 |
| Exact when ready | 6/8 | 6/8 | 0/8 |
| False-ready / cases requiring caution | 14/16 | 14/16 | 0/16 |
| Malformed decision contracts / attempted | 0/24 | 0/24 | 13/24 |

All 24 Qwen replies returned with the correct source ID and JSON. Twelve emitted `clarify_policy` with a field and a buyer-facing question, and one did the same for `ready`. The contract requires empty field and question for both decisions. Six of eight actual escalation cases had the right raw decision but failed that contract. The model also proposed six raw escalations for cases needing another action. Its single raw ready answer was on a genuinely ready case. The zero false-ready count therefore coexists with zero usable ready decisions. Source snapshots were never updated by a prediction.

Both rules correctly handled ordinary missing fields and correctly classified the two ready pairs with an explicit replacement or superseded schedule. The latter success measures disposition only; neither structured control emitted the new value. Both carried stale fields through in the withdrawn and expired pairs and missed all four policy/authority pairs. Qwen gained the withdrawn and ambiguous pairs and the English expired case, but failed the complete-information and corrected-ready cases. [All case, locale, decision and phenomenon strata](../../../../tests/evaluation/department/handoff-v2/metrics.json)

The [first-pass archive](../../../../tests/evaluation/department/handoff-v2/FIRST-RUN.zip) at commit `1b34b81a57770c6f43461fe90649199e7f52043b` has SHA-256 `743453b38d7738aca5931494cf1d204a3c610e7c5ce5af297538013a9bba51a3`. It contains 24 attempted calls, no retries, 5,536 input and 1,043 output tokens. The largest call used 248 input and 75 output tokens. Elapsed time was 235.75 s including model startup, median per-card 7.97 s, maximum 17.66 s. Provider fees were zero. The study did not meter electricity or staff time. Rule inference makes zero model calls.

For the next separately proposed design, let a coordinator inspect the previous value, the latest buyer statement, the extracted replacement (if present), and the owner responsible for any policy exception. Test separate customer-question and internal-escalation outputs, including explicit rejection of unexpected buyer text on internal actions. A design trial needs fresh holdouts, field-level source attribution, practitioner-adjudicated labels and measured edits/time before considering product integration. Commercial GA remains NO-GO.

## Offline replay

Install the development requirements with Python 3.12. From repository root, replay the whole receipt and score check with:

```sh
python -m pytest -q tests/test_market_handoff_evidence.py tests/test_market_handoff_study.py tests/test_department_handoff_benchmark.py
```

To inspect the per-case comparison and regenerate the report into a fresh directory:

```sh
python -m zipfile -e tests/evaluation/department/handoff-v2/FIRST-RUN.zip handoff-replay
python tests/evaluation/department/handoff_comparison.py score tests/evaluation/department/handoff-v2/inputs.json handoff-replay tests/evaluation/department/handoff-v2/gold.json
```

The [frozen local runner](../../../../tests/evaluation/department/handoff_infer.py) counts explicit ChatML tokens before requesting a completion and archives every attempt. The recorded Windows CPU run uses two threads, one worker, temperature zero, seed 42 and llama.cpp build 12649 (`1f8baae28`). The [pinned model file](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/91cad51170dc346986eccefdc2dd33a9da36ead9) and executable digests are recorded in the archive. Native kernels and compiler differences can affect a new inference pass. The first pass consumed the single-run authorization. Independent prospective replication needs a fresh sealed cohort and separate budget approval. The replay commands above run entirely offline without loading model weights.

The optional tooling lives under `tests/evaluation/department`. Omitting it removes the experiment without changing product routes, jobs, roles or data. No write-capable CRM integration is part of the study.
