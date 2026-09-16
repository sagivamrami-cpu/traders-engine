# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-01T18:40:00Z

Status:
REVIEW_REQUESTED

Objective:
Take over Groq's blocked challenge-review task for D1/D3 intake and the proposed D2 session-calendar source strategy.

Reason for reroute:
Groq is unavailable because it reached its weekly quota. Claude Code should perform the challenge-review role in addition to any ordinary contract review already assigned.

Original Groq request:
`agent-exchange/inbox/groq/2026-09-01T183501Z-groq-review-d1-d3-intake-and-d2-calendar-recommendation.md`

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
- D1 approved fixed UTC 30m half-open bars with `available_at=bar_end_utc` for v1 only.
- D3 approved timestamp role interpretation for OHLCV 1s `ts_event`, order-flow `minute`, and naive order-flow UTC localization for v1 only.
- Codex D2 recommendation candidate: primary machine-readable calendar evidence from Databento when available under license, official CME docs as cross-check/source-of-truth reference, TradingView not authoritative for session calendars.

Challenge focus:
- Find any path where D1/D3 could be misread as dataset construction authorization.
- Find any path where `SESSION_CALENDAR` could be treated as satisfied without a human decision record and encoded holiday/maintenance/DST behavior.
- Challenge whether Databento+CME is sufficient for D2 and propose safer gating language if needed.
- Identify contradictions between configs, schemas, validators, reports, and status notes.

Contracts:
- No review output may be treated as human approval.
- `SESSION_CALENDAR` remains unsatisfied until a human decision record exists and implementation encodes membership/holiday/maintenance/DST behavior.
- `MISSING_BAR_POLICY` remains unsatisfied until gap detection and feature-family drop/mark behavior are implemented.
- Dataset construction and training remain disallowed.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no secrets, API keys, raw market rows, local absolute paths, or large artifacts

Deliverables:
- Write review to `agent-exchange/reviews/`.
- Verdict: `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `REJECT`.
- Findings by severity, with contradictions and unsafe paths first.
- Explicitly state that this is a rerouted Groq challenge-review replacement.
- Include any recommended changes before Codex asks the human for D2 approval.

Verification commands:
- `python -m pytest tests\research\test_gc_bar_session_timestamp_policy.py tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_pretraining_readiness.py -q`
- `python tools\validate_phase24.py`
- `python tools\validate_phase28.py`

Out of scope:
- Do not query vendors or external APIs.
- Do not construct bars, features, labels, datasets, or models.
- Do not change files.

Notes:
Prefer explicit blockers over optimistic wording. This request exists because Groq cannot complete the original challenge review.
