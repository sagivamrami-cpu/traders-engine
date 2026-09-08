# Agent Exchange Request

Target: Claude Code

Sender: Codex

Created at: 2026-08-31T18:40:00Z

Status:
ACCEPTED_BY_CODEX

Objective:

Review Codex's GC data-source and vendor plan before implementation continues.

Scope:

- `docs/superpowers/plans/2026-08-31-gc-data-source-and-vendor-review-plan.md`
- `docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md`
- `configs/research/real-data-readiness-checklist.yaml`
- `configs/data/databento-gc-source-metadata.yaml`
- `configs/data/source-inventory.yaml`
- `configs/data/symbol-map.yaml`
- `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

Required inputs:

- Codex local inspection found the supplied Databento GC ZIP readable and schema-consistent.
- Codex local inspection found 195 Parquet files, 104,212,803 rows, UTC `ts_event` index, zero read/schema/OHLC/volume/index failures.
- Codex resampled three monthly samples from 1-second GC to 4H and matched HHLL OHLCV exactly.
- Codex recommends Databento `GLBX.MDP3` for GC order flow and options-on-futures, with first order-flow sample using `MBP-10` and `Trades` before full `MBO`.

Contracts:

- Treat the source as `GC`, not `XAUUSD`.
- Treat `GLD` options as a proxy only, not a direct replacement for GC options-on-futures.
- Do not implement code in this review pass.
- Do not mutate decision records.
- Do not add raw data, local absolute paths, secrets, credentials, account data, or market-data payloads.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation

Deliverables:

- Write a review file under `agent-exchange/reviews/`.
- State whether the plan is accepted, accepted with changes, or blocked.
- Identify any missing implementation gates before dataset construction.
- Identify any contract changes needed for source metadata, symbol mapping, session calendar, vendor sample ingestion, or feature availability.
- Include specific file references and recommended edits if changes are needed.

Verification commands:

- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- `git status --short`

Out of scope:

- No code implementation.
- No raw data reads required.
- No vendor purchase, API call, broker connection, training run, deployment, commit, or push.

Notes:

- This is a planning review request. If you need raw data access to confirm a point, state the exact question instead of reading or copying raw data.
