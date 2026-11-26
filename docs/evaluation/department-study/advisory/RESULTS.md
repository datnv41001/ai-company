# R52 — Commercial meaning and six Marketing specialists

**Decision: retain deterministic QA and human review.** Qwen found 20 additional contradicted statements across 84 synthetic cases, and introduced 14 additional false contradiction flags. Both splits missed the prespecified false-positive threshold. No model output was applied to an asset, campaign, QA decision or published channel. Professional utility, editing cost and commercial readiness remain unverified.

## What was compared

Product base `eff86cda2f99dd10244dc8127451e941bb546a3c`; [frozen protocol and source projection](../../../../tests/evaluation/department/semantic-v1/PROTOCOL.md) at `5998840`; role rubric frozen at `f3bc2a3`. A separate engineering AI authored the source pairs, expected labels and briefs before invocation. The main split contains EN source records with Vietnamese and English claims. The supplementary split contains Vietnamese sources and declarative unknowns. This matters because all twelve main-split unknowns were formulated as questions. Neither the model nor the deterministic classifier received gold labels, category or case identifiers. Only source text was used to project production facts, VND amounts and hypotheses. This experiment covers plain-text pairs; production can receive a richer typed brief, authorizations, and reviewer resolutions.

All 96 responses were archived at `5adcbce` before copying either answer key into the evaluation checkout. [First-run evidence](FIRST-RUN.zip) has SHA-256 `0d8683f94beee9ea81eaa2f32b50e9eed72389c3f4ee940056032eedfaec065c`. It includes complete requests, returned text, usage and elapsed time, the original deterministic verdicts, six substantive control drafts per brief, and every specialist revision. All material is synthetic. [Score file with holdout hashes and matrices](SCORES.json) · [Replay and custody](REPLAY.md)

## Commercial claim triage

A **true positive** is a source-contradicted claim flagged as contradicted. A missed contradiction includes abstentions. A false positive is a supported or genuinely unresolved claim flagged as contradicted. An exact quote from the source is required for model advice, but does not prove the relationship. The combined arm keeps definite deterministic decisions and accepts a model suggestion only in a baseline abstention. Every suggestion remains advisory.

| Split and arm | Contradictions caught | Missed contradictions | False alarms / all non-contradictions | False alarms / supported statements | Abstentions / all cases |
|---|---:|---:|---:|---:|---:|
| Main, deterministic | 1/24 | 23 | 0/36 | 0/24 | 59/60 |
| Main, model alone | 14/24 | 10 | 7/36 | 6/24 | 29/60 |
| Main, combined | 15/24 | 9 | 7/36 | 6/24 | 28/60 |
| Stress, deterministic | 0/6 | 6 | 1/18 | 0/6 | 23/24 |
| Stress, model alone | 6/6 | 0 | 7/18 | 1/6 | 9/24 |
| Stress, combined | 6/6 | 0 | 8/18 | 1/6 | 8/24 |

On both splits no gold contradiction or gold unknown was labeled supported by any arm. The advance rule also limited added false contradictions to one per split. Seven additional false flags on each split fail that rule. The combined precision of contradiction flags was 15/22 on main and 6/14 on stress. An editor would spend time checking erroneous flags. This run contains no practitioner time measurements.

| Claim language, combined arm | Caught | False alarms | Abstentions |
|---|---:|---:|---:|
| Main English | 11/12 | 6/18 | 7/30 |
| Main Vietnamese | 4/12 | 1/18 | 21/30 |
| Stress English | 6/6 | 3/6 | 3/12 |
| Stress Vietnamese | zero gold contradictions | 5/12 | 5/12 |

The diagnostic deliberately varies source language and sentence form. Stress has no Vietnamese-claim contradictions, so it cannot estimate recall for that cell. Both splits are small constructed samples with related cases and a single model family. The twelve scope categories are availability, channel/region/time, exceptions, hypothesis vs observation, minimum quantity, negation, part vs whole, payment direction, performance, price vs refund, tax/unit and warranty. The JSON reports all 12 in each split for every arm.

| Receipt ID | Observed behavior and business consequence |
|---|---|
| `case-1c398b` | A January East district online rate was extended to every district. The baseline abstained; combined correctly warned an editor about the new geography. |
| `case-85260e` | The source allows weekday pickup except Wednesday. Combined objected to Thursday. Following this warning could suppress a legitimate collection option. |
| `case-14573b` | Vietnamese copy reported completed interviews and a confirmed cause. The English record only proposed night-shift interviews. Both arms abstained, so a reviewer must still distinguish plans from actual research. |
| `case-1fba3e` | No refund deadline was published. Combined called a five-day processing claim contradicted. The safe action is to request a policy source before using that service promise. |
| `case-509398` | February pricing was undecided. The deterministic projection flagged a February discount as contradicted; the combined rule retained it. The earlier terms address another period. |

For further research, test typed offer boundaries on new native-language records with balanced negative and unknown assertions in each language. Preserve fail-closed approval and exact evidence. Any expert annotation should independently establish whether a term is contradicted or missing, and a new preregistered cohort should measure the burden of false flags before a runtime proposal.

## Six role-specific edits

The two new briefs cover an RFQ for 24-piece boxes sold excluding VAT and a staff-confirmed dock observation sold per visit including VAT. Both define a useful business outcome and restrict external spend. The normal campaign composer generated each control; the model was asked for a concrete role-specific revision against that exact draft and brief. [Role contracts, recipients and repair criteria](SPECIALISTS.md) · [Frozen rubric](../../../../tests/evaluation/department/semantic-v1/SPECIALIST-RUBRIC.md)

| Role | Observed comparison and required correction |
|---|---|
| Research | RFQ control preserves the gap in competitor evidence; the revision repeats the same RFQ data-collection sentence twice. The service revision repeats sources and ends mid-link. Design one buyer-specific interview question and a collection step first. |
| Strategy | Both controls specify a needs-led versus terms-led test with fixed audience, CTA and landing page. RFQ revision discusses a sales KPI before quoting the approved RFQ outcome; service revision turns the confirmed/valid ratio into “or”. Preserve numerator and denominator and state an actual positioning proposition. |
| Content | RFQ revision retains price, unit, tax and MOQ but starts by requesting location instead of SKU and includes internal fixture notes. Service revision retains price and staff confirmation but asks for location and preferred time instead of explicitly requesting site and shift. Reconcile the CTA with the Sales/Service intake fields and remove internal measurement language. |
| SEO/GEO | The service revision directly answers the buyer using “receiving site and shift” and expressly keeps staff confirmation. It omits the West district boundary. RFQ revision keeps commercial terms but places code/date in a separate internal-sounding sentence instead of its opening CTA. Use the service answer as an editorial example pending review. |
| Performance Media | Both revisions split the planned caps (600k/600k or 450k/450k VND) but both cut off. RFQ pivots toward click-through rates; service introduces unsupported format diagnostics and stops at “Compare”. Keep the complete deterministic experiment and verify the actual commercial KPI before editing variants. |
| Creative Direction | Both revisions repeat the subject, terms, caption and a rights gate. Neither gives a composeable layout or specifies a visual test that would catch the wrong product or scope. Add scene, hierarchy, source/license evidence and an inspectable QA check. No image was generated in this writing comparison. |

## Independent read of Marketing deliverables

A separate AI reader received the shuffled 24 texts, the two briefs and the rubric. It had no source mapping or prior run history. Formatting can still hint at authorship. After the reader submitted all 24 decisions, the custodian checked every card against its exact sealed draft and then joined arm labels. Each arm has six binary obligations per job (three per brief). The engineering reading is a small diagnostic, not a survey of Marketing experts.

| Role | Deterministic obligations met / 6 | AI revision obligations met / 6 | AI prompt / output tokens | Request seconds |
|---|---:|---:|---:|---:|
| Research | 3 | 4 | 892 / 283 | 41.031 |
| Strategy | 4 | 2 | 767 / 306 | 37.047 |
| Content | 3 | 1 | 869 / 226 | 30.015 |
| SEO/GEO | 6 | 6 | 877 / 196 | 25.374 |
| Performance Media | 6 | 2 | 1,180 / 384 | 48.812 |
| Creative Direction | 2 | 2 | 842 / 273 | 33.641 |
| Total | 24/36 | 17/36 | 5,427 / 1,668 | 215.920 |

The reader credited a test RFQ as a minimal evidence collection step. The study editor regarded the repeated research instruction as requiring substantial work. The reader accepted SEO fields anywhere in the answer, but applied the stricter explicit buyer CTA standard to Content. Thus 6/6 for the SEO arm can coexist with a missing service-area warning or an awkward RFQ CTA. Creative copy received caption/CTA credit but failed the concrete layout and QA criteria in both arms. These distinctions remain visible in the [24 assessments, supporting passages and required edits](SPECIALIST-READ.json). The [shuffled cards, unaltered verdicts and revealed custodian key](BLIND-READ.zip) reproduce the mapping. The observed gains support exploring a better buyer-research question and clearer service FAQ; they do not support a default AI rewrite or a larger worker pool.

## Inference usage and cost

CPU-only llama.cpp build 12649, git `1f8baae28`, Qwen2.5-1.5B-Instruct Q4_K_M, two threads, concurrency one, 3,072 context tokens, seed 42 and temperature zero. Startup took 7.344 s. Frozen caps allowed 80 output tokens per semantic and 192 per specialist request. The run retained every first attempt and performed no selection across retries.

| Work | Calls | Prompt / output tokens | Sum of request wall seconds | Returned length stops |
|---|---:|---:|---:|---:|
| Main commercial | 60 | 10,791 / 2,502 | 375.028 | 0 |
| Stress commercial | 24 | 4,469 / 1,143 | 144.423 | 0 |
| Six specialists × two briefs | 12 | 5,427 / 1,668 | 215.920 | 3 |
| Total | 96 | 20,687 / 5,313 | 735.371 | 3 |

Recorded provider fee and media spend are zero. The archive reports model and executable hashes and actual measured tokens per call. Compute electricity, cost of capital, human correction time, professional acceptance, and revenue remain unknown. The [matched four-arm practitioner pilot](../PILOT-ABCD/README.md) retains two work orders for each of manual, deterministic, AI-assisted and AI-assisted plus independent QA. At preparation it has zero practitioner forms and zero verified business acceptances. Its estimator requires complete cost and decision records; it cannot yet give VND per accepted campaign. Commercial GA remains NO-GO.
