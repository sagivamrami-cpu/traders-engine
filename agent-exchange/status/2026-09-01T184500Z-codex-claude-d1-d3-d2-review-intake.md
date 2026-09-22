# Agent Exchange Status

Sender:
Codex

Status:
ACCEPTED_BY_CODEX

Scope:
Claude Code reviews for D1/D3 intake and the D2 session-calendar recommendation.

Reviews:
- `agent-exchange/reviews/2026-09-01T224500Z-claude-code-review-d1-d3-intake-and-d2-calendar-recommendation.md`
- `agent-exchange/reviews/2026-09-01T231500Z-claude-code-groq-takeover-d1-d3-d2-challenge-review.md`

Codex Evaluation:
- Accepted: D1/D3 gate removal is correctly scoped and does not authorize dataset construction or training.
- Accepted: D2 must be stronger than "Databento plus current CME docs"; it needs era-versioned evidence, observed-activity reconciliation, and scheduled-vs-observed closure separation.
- Accepted: Databento `status` schema use would be a new vendor request and must go through Phase 21/22-style cost/source approval before querying.
- Accepted: TradingView must remain non-authoritative for D2.

Implemented Changes:
- Added Phase 1 fail-closed guard: `cme-globex-metals-research-pending-v1` cannot be registered in `configs/data/session-calendar.yaml` before D2.
- Updated Phase 28 top-level status to `POLICY_REVIEWED_PARTIAL_HUMAN_APPROVALS_REMAIN_BLOCKED`.
- Added `non_closed_bar_feature_policy=UNDEFINED_BLOCKED_PENDING_NEW_HUMAN_DECISION` to the GC dataset contract.
- Reconciled D1-approved timeframe status across order-flow and label/split policy artifacts.
- Removed resolved D1/D3 gates from Phase 29 required remaining gates.

Verification:
- `python -m pytest tests\data_foundation\test_phase1_configs.py tests\research\test_gc_bar_session_timestamp_policy.py tests\research\test_gc_real_dataset_contract.py tests\research\test_databento_gc_order_flow_profile.py tests\research\test_gc_label_split_policy.py -q`: PASS, 23 passed.
- `python tools\validate_phase1.py`: PASS.
- `python tools\validate_phase23.py`: PASS.
- `python tools\validate_phase24.py`: PASS.
- `python tools\validate_phase25.py`: PASS.
- `python tools\validate_phase28.py`: PASS.
- `python tools\validate_phase29.py`: PASS.
- `python tools\validate_phase30.py`: PASS.

Remaining Human-Dependent Gate:
D2 session calendar. Codex should ask the human to approve or reject an era-versioned GC session-calendar strategy before any calendar registration, Databento status pull, real resampling, dataset construction, or training.
