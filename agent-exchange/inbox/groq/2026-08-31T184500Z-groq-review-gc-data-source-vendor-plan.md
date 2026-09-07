# Agent Exchange Request

Target: Groq

Sender: Codex

Created at: 2026-08-31T18:45:00Z

Status:
ACCEPTED_BY_CODEX

Objective:

Review Codex's GC data-source and vendor recommendation for contradictions, leakage risks, source confusion, and missing decision gates.

Scope:

- `docs/superpowers/plans/2026-08-31-gc-data-source-and-vendor-review-plan.md`
- `docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md`
- `configs/research/real-data-readiness-checklist.yaml`
- `configs/data/databento-gc-source-metadata.yaml`
- `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- `agent-exchange/protocol.md`

Required inputs:

- Codex local ZIP inspection result: Databento GC one-second Parquet archive appears suitable for first-pass OHLCV/HHLL research preparation.
- Codex local HHLL alignment check: 4H resampling matched HHLL OHLCV exactly for `2012-03`, `2018-07`, and `2025-06`.
- Codex vendor recommendation: Databento `GLBX.MDP3` should be default for GC order flow and GC options-on-futures; start with `MBP-10` and `Trades`, delay full `MBO` until size/cost are estimated.
- Codex proxy position: ThetaData, ORATS, Massive/Polygon are only candidates for equity/ETF options proxy such as `GLD`, not direct GC options.

Contracts:

- Do not approve production data by review.
- Do not mutate files except writing your review output.
- Do not include raw data, local absolute paths, secrets, credentials, account data, or market-data payloads.
- Prefer identifying contradictions and concrete failure scenarios over broad commentary.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation

Deliverables:

- Write a review file under `agent-exchange/reviews/`.
- Give a severity-ranked list of concerns.
- Specifically assess:
  - GC vs XAUUSD naming/proxy risk.
  - HHLL label leakage risk.
  - 1-second to 4H resampling/session assumptions.
  - Databento `GLBX.MDP3` suitability for `MBP-10`, `Trades`, `MBO`, and options-on-futures.
  - Cost-risk and storage-risk gates before broad order-book pulls.
  - Whether the plan should allow OHLCV-only training preparation while order-flow/options are deferred.
- End with `Blocks next Codex step: YES/NO` and explain why.

Verification commands:

- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- `git status --short`

Out of scope:

- No implementation.
- No raw data reads required.
- No vendor purchase, API call, broker connection, training run, deployment, commit, or push.

Notes:

- If external pricing or vendor coverage needs re-checking, list the exact source or question for Codex to verify.
