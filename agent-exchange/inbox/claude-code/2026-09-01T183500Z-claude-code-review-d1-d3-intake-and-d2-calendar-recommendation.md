# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-01T18:35:00Z

Status:
REVIEW_REQUESTED

Objective:
Review Codex intake of human-approved D1/D3 policy decisions and critique the proposed D2 session-calendar next step.

Scope:
- `agent-exchange/decisions/2026-09-01T181000Z-human-d3-timestamp-policy-v1.md`
- `agent-exchange/decisions/2026-09-01T182500Z-human-d1-bar-boundary-available-at-v1.md`
- `agent-exchange/status/2026-09-01T182000Z-codex-d3-timestamp-decision-intake.md`
- `agent-exchange/status/2026-09-01T183000Z-codex-d1-bar-boundary-decision-intake.md`
- `configs/data/gc-bar-session-timestamp-policy.yaml`
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `schemas/gc_bar_session_timestamp_policy.schema.json`
- `schemas/gc_real_dataset_contract.schema.json`
- `trading_system/research/gc_bar_session_timestamp_policy.py`
- `trading_system/research/gc_real_dataset_contract.py`
- `tools/validate_phase24.py`
- `tools/validate_phase28.py`
- `docs/implementation-reports/phase-24-gc-dataset-contract.md`
- `docs/implementation-reports/phase-28-gc-bar-session-timestamp-policy.md`

Required inputs:
- Treat D1 and D3 as v1 policy approvals only, not dataset-construction authorization.
- Codex next-step recommendation for D2: use Databento session/status evidence as the primary machine-readable source when available under license, cross-check against official CME GC/Globex trading-hours documents, and do not use TradingView as the authoritative session-calendar source.

Contracts:
- D1 resolves only `BAR_BOUNDARY` and `AVAILABLE_AT_POLICY`.
- D3 resolves only timestamp role interpretation for v1 inputs.
- `SESSION_CALENDAR`, `MISSING_BAR_POLICY`, and `DATASET_CONSTRUCTION_AUTHORIZATION` must remain blocked.
- Dataset construction and training must remain disallowed.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no secrets, API keys, raw market rows, local absolute paths, or large artifacts

Deliverables:
- Write a review to `agent-exchange/reviews/`.
- State verdict: `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `REJECT`.
- List blocking findings first with file references.
- Explicitly confirm whether D1/D3 gate removal is correctly scoped.
- Critique the D2 recommendation and note any better authoritative source strategy.

Verification commands:
- `python -m pytest tests\research\test_gc_bar_session_timestamp_policy.py tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_pretraining_readiness.py -q`
- `python tools\validate_phase24.py`
- `python tools\validate_phase28.py`

Out of scope:
- Do not query vendors or external APIs.
- Do not construct bars, features, labels, datasets, or models.
- Do not change files unless Codex sends a separate implementation request.

Notes:
Focus on contract correctness and whether future D2 implementation would be auditable.
