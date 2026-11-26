# Buyer handoff triage · first structured control

On 12 independently authored synthetic VI/EN pairs the frozen control returned the correct next step and field on **14/24 cards**. It marked eight cards ready while a buyer field or an owner policy decision was still outstanding. This result qualifies the baseline and its failure cases for further research. There were **zero new model calls**, zero external spend and zero practitioner judgments. Expert labor, question quality, saved time and cost per business-accepted item are unmeasured.

| Criterion | Vietnamese | English | Total |
|---|---:|---:|---:|
| Correct action and field | 7/12 | 7/12 | 14/24 |
| Ask the buyer | 3/5 | 3/5 | 6/10 |
| Ready for handoff | 3/4 | 3/4 | 6/8 |
| Escalate conflicting/unclear policy | 1/3 | 1/3 | 2/6 |
| Unsafe ready decisions | 4 | 4 | 8 |
| Missing or malformed outputs | 0 | 0 | 0 |

Seven pairs were correct in both languages and five failed in both. Each pair uses the same structured state and field IDs. Parity is expected from a baseline that does not read the narrative and cannot establish equal quality of buyer-facing wording. The study did not score whether a proposed translated question sounds natural.

- In pair `p2` (EN `e70cedc`), the CRM retains “4” meters while the buyer expressly withdraws that count. The control accepted the obsolete value. In `p3` (EN `54deda37`), a workshop confirmation placeholder counted as a finished choice.
- In `p8` (EN `2e006dcc`), the buyer supplied the access window in prose. The structured snapshot omitted it, so the control asked the buyer to repeat it.
- Pairs `p9` and `p11` have conflicting active requirements. Required structured values alone were present, so the control passed four policy cards as ready. Together with the four stale or pending value cards, this accounts for all eight false-ready decisions. A coordinator must route the policy cases to the owner. Conversely in `p7` the question decision is correctly ready even though the CRM still shows an old depot. This decision-only rubric does not certify that the stored destination has been updated.

## First-run custody and replay

The custodian authored these original synthetic situations and labels separately from the researcher implementing the baseline. Both products are AI-authored and subject to professional challenge. Cards are purpose-built, paired translations rather than independently sampled field traffic. Labels include a sample question for the held-out case; other accurate phrasings may be valid. No private customer material or mapping for a practitioner pilot was used. This public, retrospective benchmark must not be advertised as confidential or unseen by a future model.

| Stage | Bound evidence |
|---|---|
| Custodian seals input and gold | [Inputs](../../../../tests/evaluation/department/handoff-v1/inputs.json) SHA-256 `8165c72fe3db8352c2654c1cd8e675391cfe08346d117277d23a4f0eec0fb29e`; [labels](../../../../tests/evaluation/department/handoff-v1/labels.json) SHA-256 `cbe3c76f563abe4f91a2c24efb5e324a7a05c69a2200024874e90b8c5a4b4cf8` |
| Scope, control, model proposal and budget frozen | [Protocol commit](https://github.com/datnv41001/ai-company/commit/540d4433261b3330593da82944955400c9008f71) |
| Only input released, baseline evaluated and sealed | [First predictions before gold](https://github.com/datnv41001/ai-company/commit/e81333dc61df426b8d2a11d2b46d75c0cf258b56), SHA-256 `1db95d8754cd76515511a92cebd9f1658ca3c2e200b595a17809d658e15ac5b1` |
| Gold released; full scoring | [Score breakdown with all IDs](../../../../tests/evaluation/department/handoff-v1/scores.json) · [Comparison and cost rules](../../../../tests/evaluation/department/handoff-v1/PROTOCOL.md) |

Run from the repository root using Python 3.12. Choose a new output path for predictions. The scoring command also checks that the frozen control still reproduces the published predictions.

```sh
python tests/evaluation/department/handoff_baseline.py tests/evaluation/department/handoff-v1/inputs.json fresh-baseline.json
python tests/evaluation/department/handoff_score.py tests/evaluation/department/handoff-v1
python -m pytest -q tests/test_department_handoff_benchmark.py
```

No release, runtime promotion or model selection decision follows from this control. Before any prospective inference, replace the now-public cohort with newly sealed equivalent pairs and independently validate the labels. Keep the ordered stage commitments and byte hashes with the result.
