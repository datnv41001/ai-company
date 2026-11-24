# B4 paired checkpoint comparison

This is a local measurement of Marketing claim review on eight synthetic cases drawn from the quality study's Marketing fixture. The two checkpoints are members of the same Qwen2.5 Instruct family. One catalog profile, MK-022, reads the approved evidence and published text. There are two calls per checkpoint and eight decisions per call.

## Measured outcome

Both checkpoints flagged every case on both seeds. Each detected the four planted defects and raised four false alarms on the four clean cases. Binary decisions matched item-for-item on both seeds. Increasing from 0.5B to 1.5B yielded no measured improvement under this prompt. [Replayable results](evidence-v1/results.json)

| Checkpoint | Seed | TP / FP / FN / TN | Exact fixes among TP | Exact explanations among TP | Input / output tokens | Seconds |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| 0.5B | 17 | 4 / 4 / 0 / 0 | 0 / 4 | 0 / 4 | 938 / 119 | 10.32 |
| 0.5B | 43 | 4 / 4 / 0 / 0 | 0 / 4 | 0 / 4 | 938 / 119 | 9.68 |
| 1.5B | 17 | 4 / 4 / 0 / 0 | 0 / 4 | 0 / 4 | 938 / 90 | 15.71 |
| 1.5B | 43 | 4 / 4 / 0 / 0 | 0 / 4 | 0 / 4 | 938 / 115 | 15.40 |

Precision is 4/8 (50%), recall 4/4 (100%) and false-positive rate 4/4 (100%) in every row. Neither checkpoint abstained. Applied as an automatic gate on these cases, this rule would stop all four correct Marketing claims. Four accepted adapter receipts account for 4,195 tokens and zero provider charge. This small comparison establishes neither population performance nor the effect of changing model family, role or prompt.

## Registered design

The operator recorded enrollment SHA-256 `041d59f30b978ddf877320215d897760b60a7a59f57cdeda153f56a16d796fac` before starting the two model arms. The [enrollment](evidence-v1/enrollment.json) commits to the synthetic Git source, catalog, label digest, assignment plan, public signing keys, models, runtime bundle manifest and all four rendered request digests. Fixture base is `8648be3e92e68e486bae9bd35b0d445f884e7ab9`. Fixture head is `2ca0e9a9493b03e2a38c9fd9ac9f501878cb9d68`.

Within each of four strata (price, variant, qualifier, negation), select the smallest opaque case ID with a known defect and the smallest ID with a clean label. Sort the eight selected IDs. Both checkpoints receive the same case order, task, menus, schema and sampling settings. Only the server model alias differs within each matched seed. The author of the experiment used synthetic labels for sampling and scoring. The model sees the approved claims, published copy and task. Labels and another model's verdicts stay outside the prompt. Reusing cases from the larger Marketing study limits generalization.

The two seeds are 17 and 43, temperature 0.45, output ceiling 220 tokens, zero retries and a 90-second call deadline. Each arm runs sequentially in one inference slot, under the existing host-wide cap of two. Independent sample size is eight cases. Two seeds measure sensitivity to sampling. The observations share a reviewer prompt, authorship, model family, host and source.

| Arm | Revision | Weight SHA-256 | Weight bytes |
| --- | --- | --- | ---: |
| [Qwen2.5-0.5B-Instruct Q4_K_M](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/blob/9217f5db79a29953eb74d5343926648285ec7e67/qwen2.5-0.5b-instruct-q4_k_m.gguf) | `9217f5db79a29953eb74d5343926648285ec7e67` | `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db` | 491,400,032 |
| [Qwen2.5-1.5B-Instruct Q4_K_M](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/blob/91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q4_k_m.gguf) | `91cad51170dc346986eccefdc2dd33a9da36ead9` | `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e` | 1,117,320,736 |

Each arm uses the [enrolled runtime bundle](../runtime-pins/windows-x64.json). After verifying the staged binaries and weight hash, the operator-owned adapter talks to a private loopback model process, then signs the hash of the actual HTTP response, usage, checkpoint, seed-specific request hash, assignment and fixture revisions. The public evidence directories contain the exact requests, raw responses, signed receipts, chronological journal, checkpoint and runtime record. These records attest to local invocations under the enrolled operator's trust. Model execution and signing share one machine. Commercial GA remains **NO-GO**.

## Replay from a checkout

Run the commands below from the repository root with Python 3.12 and Git. Replay rebuilds the synthetic source, verifies the enrollment and both journals, decodes the original outputs and recomputes scores offline. It needs the released public files and Python dependencies. Model weights are required only for new inference.

~~~shell
python -m pip install -r engineering/airc500/requirements-pilot.txt
python engineering/airc500/stronger_study.py replay --out engineering/airc500/stronger/evidence-v1 --expected-enrollment 041d59f30b978ddf877320215d897760b60a7a59f57cdeda153f56a16d796fac
python -m unittest discover -s engineering/airc500/stronger -p test_evidence.py
~~~

For an independent run, obtain the exact GGUF objects from the two linked publisher revisions and use a matching Windows runtime directory. Keep weights and operator keys outside the checkout. Use new directories. Replace `PUBLIC_DIR`, `PRIVATE_DIR`, `NEW_PIN`, `SERVER_EXE`, `SMALL_GGUF` and `LARGER_GGUF` with values for the new run. Record the printed enrollment hash before invoking either model. Start each arm after the previous command completes.

~~~shell
python engineering/airc500/stronger_study.py enroll --out PUBLIC_DIR --private PRIVATE_DIR
python engineering/airc500/stronger_study.py run --out PUBLIC_DIR --private PRIVATE_DIR --expected-enrollment NEW_PIN --server SERVER_EXE --arm small --model SMALL_GGUF
python engineering/airc500/stronger_study.py run --out PUBLIC_DIR --private PRIVATE_DIR --expected-enrollment NEW_PIN --server SERVER_EXE --arm larger --model LARGER_GGUF
python engineering/airc500/stronger_study.py replay --out PUBLIC_DIR --expected-enrollment NEW_PIN
~~~

The replay reports TP, FP, FN and TN by seed. An unsure decision counts as an unflagged item for the binary metrics and is also listed explicitly. Structured fixes and explanations use exact matching on actual subjects, values and source references. Their denominator is detected true defects, which can be zero. Precision likewise has no numeric estimate when a checkpoint emits no flags. The matched comparison lists the IDs that each model got right or wrong on each seed.

Provider charge is zero for these local calls. Timing covers each dispatched inference. A separate experiment can share the host, so timing is descriptive. Overall system and hardware costs are unmeasured.
