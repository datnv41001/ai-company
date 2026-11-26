# Reproduce the bounded local comparison

The product under comparison is commit `eff86cda2f99dd10244dc8127451e941bb546a3c`. Protocol commit `5998840` includes that product and the frozen runner. For a new independent replication use a fresh worktree, newly custodied holdouts and a new output directory. For a direct replay retain the supplied inputs. Processing prior calls from the same directory resumes compatible checkpoints, so a replay must use a different output directory.

1. Install Python 3.12 and the repository development requirements. Follow the repository instructions for the isolated test environment.
2. Obtain the native llama.cpp server corresponding to build 12649, commit `1f8baae28`, and the pinned [Qwen GGUF file](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/91cad51170dc346986eccefdc2dd33a9da36ead9). Use the original file with SHA-256 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`. The runner checks the weights and records the executable digest. Different CPU kernels, compiler settings or binaries can affect exact reproduction.
3. On the checkout containing the published results, verify the retained archive and regenerate its complete score without contacting a model. The current runner imports the repository's product classifier and composer, so install the normal development dependencies even for scoring.

```sh
python -m pip install -r requirements-dev.txt
python tests/evaluation/department/advisory_score.py docs/evaluation/department-study/advisory/FIRST-RUN.zip replay-scores.json
```

4. To repeat inference against the original code, switch to protocol commit `5998840` in the separate worktree, then run the command below. Replace the server and weights paths with your local files. The server binds an ephemeral loopback port with proxy use disabled. Use a synthetic output path writable by your account. On Windows the executable is `llama-server.exe`.

```sh
python tests/evaluation/department/advisory_study.py /path/to/llama-server /path/to/weights.gguf /path/to/fresh-run
```

5. From the results checkout, run the packaging and scoring helpers below. The allowlist archives the 96 request/response receipts and five synthetic output files. The private server log is excluded. Compare first runs without overwriting the original archive, tuning on the published labels or retrying an inconvenient prediction.

```sh
python tests/evaluation/department/pack_advisory.py pack /path/to/fresh-run local-first-run.zip
python tests/evaluation/department/advisory_score.py local-first-run.zip local-first-scores.json
python tests/evaluation/department/pack_advisory.py anonymize local-first-run.zip reviewer-cards.json custodian-key.json
python tests/evaluation/department/pack_advisory.py reconcile local-first-run.zip reviewer-cards.json custodian-key.json returned-verdicts.json reconciled-read.json
```

Give the independent reader only the card bundle, the original briefs and [role rubric](../../../../tests/evaluation/department/semantic-v1/SPECIALIST-RUBRIC.md). The custodian keeps the source mapping. Deterministic fields and generated prose can be recognizable even after shuffling. The role read is a technical inspection of writing, separate from the [four-arm practitioner pilot](../PILOT-ABCD/README.md). No role can approve an AMC snapshot through these scripts. Rollback consists of omitting this optional study tooling. It installs no runtime worker, migration or provider integration.
