# Prospective evidence index

The evidence package did not calculate or inspect meter scores. Root owns fidelity judgments and later analysis. Recording integrity does not imply that an authored pattern was realized.

Frozen construction: `construction.json` (SHA256 `2800bbee151319b0c10c08a14f72473c807f3544f02b9cdf3eef66571c4a4769`). Frozen formulas: `formulas.json` (SHA256 `42611164905d84c7a76b94d66d88ed14a101f4cba950c2de750a9d1c2160ff18`). Runtime/source inspection: `runtime_preflight.json`. Integrity receipt: `evidence_validation.json`. Call ceiling and spending: `budget.json` and `call_budget_ledger.json`.

| Stage | Accepted exchanges | Normal calls | Rejections | State |
|---|---:|---:|---:|---|
| preflight | 6 | 16 | 0 | unchanged |
| main | 87 | 254 | 2 | unchanged |
| replacement1 | 10 | 29 | 0 | unchanged |
| replacement2 | 10 | 29 | 0 | unchanged |

Main attempted all nine planned trajectories. Baking F-new stopped after nine accepted exchanges when Quinn failed the turn-ten factual gate. Baking F-same stopped after eight accepted exchanges when Quinn omitted the turn-nine facts. Failed participants were never sent to Gemma. The two complete replacement attempts were the first two invalid main trajectories in frozen order, network F-new then network F-same; no replacement targeted a score.

Total: **328 normal calls**, reserving **357376 output tokens** against the fixed 335-call / 366208-token ceilings. Actual known output tokens: Gemma **50076**, Quinn **3343**; the nonautoregressive specialist exposes no output-token usage. There were **zero capped Gemma responses** and **zero additional pair removals for headroom** beyond the normal last-two-pair policy. All accepted source text fit the verified GLiNER word-token limit. Semantic coverage is often partial because of adapter capacity, unsupported relationships, or parser omissions; it is recorded separately.

Each stage directory contains:

- `transcripts.md`: all accepted exchanges; `trajectory_transcripts/`: per-trajectory readable files with explicit accepted and rejection counts.
- `records.json.gz`: full raw accepted records; `meter_inputs.json.gz`: strictly projected, condition-blind inputs. Small exports may use `.json`; `read_json` handles both.
- `condition_manifest.json`: condition/domain/attempt mapping, never meter input.
- `calls/` and `calls_index.json`: original provider requests/results, timestamps, statuses and call paths.
- `contexts/`: native serialized prompts, token counts, prior-pair omissions and sizing trials.
- `coverage.csv` / `coverage_summary.json`: input coverage, semantic coverage, actual lengths, finish reasons and missing information.
- `rejections.json`: every failed pre-Gemma attempt and reason, without splicing or replay.
- `state_before.json` / `run_receipt.json`: immutable initial state and after-run proof.

The zero-score preflight review is `preflight_review.md`; whole-exchange fidelity judgments are in `fidelity_review.md`. No model judge or extra semantic call was made. Retained private prompts are audit evidence, never meter inputs.

The earlier ENOSPC event preceded the first call and is documented in `construction_recovery.json`. The restored runner passed focused checks before launch; deterministic compression and disk-reserve guards then protected the bounded recording. Interrupted/uncertain attempts fail closed rather than resume; no uncertain call was replayed.
