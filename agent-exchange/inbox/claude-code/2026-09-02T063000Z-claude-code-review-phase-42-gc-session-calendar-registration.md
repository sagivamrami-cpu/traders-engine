# Agent Exchange Request

Sender:
Codex

Target:
Claude Code

Created at:
2026-09-02T06:30:00Z

Status:
REVIEW_ONLY

Objective:
Review Phase 42 GC session-calendar registration.

Scope:
- `docs/implementation-reports/phase-42-gc-session-calendar-registration.md`
- `agent-exchange/status/2026-09-02T062500Z-codex-phase-42-gc-session-calendar-registration-result.md`
- `agent-exchange/decisions/2026-09-02T061500Z-human-d2-final-databento-status-schema-skip.md`
- `configs/data/session-calendar.yaml`
- `trading_system/data_foundation/sessions.py`
- `tests/data_foundation/test_sessions.py`
- `configs/data/gc-session-calendar-construction-policy.yaml`
- `schemas/gc_session_calendar_construction_policy.schema.json`
- `tests/research/test_gc_session_calendar_construction_policy.py`
- `configs/data/gc-bar-session-timestamp-policy.yaml`
- `schemas/gc_bar_session_timestamp_policy.schema.json`
- `tests/research/test_gc_bar_session_timestamp_policy.py`
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `schemas/gc_real_dataset_contract.schema.json`
- `tests/research/test_gc_real_dataset_contract.py`
- `schemas/gc_pretraining_readiness_report.schema.json`
- `tests/research/test_gc_pretraining_readiness.py`
- `configs/research/gc-label-split-policy.yaml`
- `schemas/gc_label_split_policy.schema.json`
- `tests/research/test_gc_label_split_policy.py`
- Phase validator updates for 20/21/23/24/25/28.

Review Questions:
- Does Phase 42 close only `SESSION_CALENDAR` relative to post-Phase-41
  readiness?
- Is `cme-globex-metals-research-v1` sufficiently bounded as research-only and
  not execution truth?
- Are daily break, Sunday open, Friday close, DST via `America/Chicago`, and
  trade-date roll handled coherently by `resolve_session()`?
- Do all contracts/schemas keep dataset construction, resampling, label/split
  building, training, model promotion, live trading, broker execution, and
  capital allocation blocked?
- Is the Databento `status` schema skip record consistent with D2-final and the
  no-API-query constraint?
- Did Codex accidentally remove or weaken any unrelated gate?

Deliverables:
- Write review to `agent-exchange/reviews/`.
- Use verdict `ACCEPT`, `ACCEPT_WITH_NOTES`, or `REVISION_REQUESTED`.
- List any blocking findings first.

Verification:
- `python -m pytest tests\data_foundation\test_sessions.py tests\data_foundation\test_phase1_configs.py tests\research\test_gc_session_calendar_construction_policy.py tests\research\test_gc_bar_session_timestamp_policy.py tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_pretraining_readiness.py tests\research\test_gc_label_split_policy.py tests\research\test_databento_gc_order_flow_profile.py::test_order_flow_profile_cli_outputs_sanitized_json tests\research\test_gc_order_flow_availability_era_policy.py::test_gc_order_flow_availability_policy_cli_outputs_sanitized_json tests\research\test_gc_order_flow_era_map.py::test_gc_order_flow_era_map_cli_outputs_sanitized_json -q`
- `python tools\validate_phase1.py`
- `python tools\validate_phase39.py`
- `python tools\gc_pretraining_readiness.py --contract configs\datasets\gc-30m-real-dataset-contract.yaml --decisions agent-exchange\decisions\databento-gc-real-data-decisions.yaml --checklist configs\research\real-data-readiness-checklist.yaml --training-policy configs\models\baseline-training-policy.yaml --groq-phase24-review agent-exchange\reviews\2026-09-01T185200Z-groq-review-phase-24-dataset-contract.md --groq-phase24-intake agent-exchange\status\2026-09-01T170300Z-codex-groq-phase-23-to-26-review-intake.md`

Boundary:
Review-only. Do not query vendors. Do not read raw market rows. Do not commit
or push. Do not approve dataset construction or training.
