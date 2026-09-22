# Agent Exchange Request

Target: Groq

Sender: Codex

Created at: 2026-09-01T13:11:01Z

Status:
REVIEW_ONLY

Objective:

Challenge-review the latest human-confirmed GC dataset-planning decisions before Codex starts Phase 24 dataset-contract implementation.

Scope:

- Human has approved proceeding with the clarified decision set, but Codex wants an independent Groq review before codifying Phase 24.
- Focus on contradictions, leakage paths, false readiness, invalid assumptions, missing approvals, and future backtest contamination.
- Treat this as a risk review, not an implementation task.

Required inputs:

- `agent-exchange/protocol.md`
- `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- `agent-exchange/decisions/2026-09-01T153800Z-human-gc-order-flow-source.md`
- `agent-exchange/decisions/2026-09-01T153801Z-human-gc-order-flow-2017-exclusion.md`
- `agent-exchange/decisions/2026-09-01T153802Z-human-first-baseline-timeframe-30m.md`
- `agent-exchange/decisions/2026-09-01T153803Z-human-options-v2-deferred.md`
- `agent-exchange/decisions/2026-09-01T153804Z-human-macro-features-leakage-gated.md`
- `docs/superpowers/plans/2026-09-01-phase-23-gc-order-flow-profile.md`
- `configs/data/gc-order-flow-quality-gates.yaml`
- `schemas/databento_gc_order_flow_profile.schema.json`
- `tools/validate_phase23.py`

Contracts:

- Codex remains architecture owner and final acceptance owner.
- Human approvals are recorded only in `agent-exchange/decisions/`.
- Phase 24 must be a dataset-contract phase only unless a later explicit human decision authorizes actual dataset construction.
- `ORDER_FLOW_SOURCE_DECISION` must remain open unless a later explicit human decision approves source readiness for features/datasets.
- `OPTIONS_SOURCE_DECISION` is deferred to v2 and must not authorize options queries or features in v1.
- 30m is a first baseline candidate, not a frozen training timeframe.
- Macro features are research-open but blocked until per-source point-in-time and leakage gates exist.
- The 2017 damaged-aggressor interval is a known exclusion for affected order-flow features, not the complete order-flow era policy.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no secrets, API keys, raw market-data payloads, or local absolute data paths in the response

Deliverables:

Write a review file under `agent-exchange/reviews/` using `agent-exchange/templates/review.md`.

Please answer:

- What are the top blockers that could make Phase 24 unsafe or misleading?
- Does the current decision set still permit accidental leakage through CVD, macro timestamps, HHLL labels, 4H reference CSVs, or resampling?
- Are the source-readiness boundaries strict enough for order flow and options?
- Which Phase 24 fields should be mandatory and fail-closed?
- Should Codex wait for any extra human decision before writing a contract-only skeleton?

Verification commands:

- `python tools/validate_phase23.py`
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

Out of scope:

- Do not modify source code.
- Do not query Databento or any external vendor.
- Do not read or copy raw market-data rows.
- Do not create datasets, features, labels, or models.

Notes:

The newest human message said both clarified pending decisions are approved and asked Codex to ask Claude Code and Groq for opinions first. If "both" is ambiguous, call that out and recommend a minimal clarification, but still evaluate the decision bundle as written.
