# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-07T13:50:09Z

Status:
SUPERSEDED_BY_HUMAN_DIRECTION_CODEX_TAKEOVER

Objective:
Review Phase 48 first real GC model implementation before Codex plans Phase 49.

Scope:
- `trading_system/models/first_real_gc_model.py`
- `tools/train_gc_first_real_model.py`
- `tools/validate_phase48.py`
- `schemas/gc_first_real_model_run.schema.json`
- `configs/models/gc-first-real-model-run.json`
- `docs/implementation-reports/phase-48-first-real-gc-model.md`
- `tests/models/test_first_real_gc_model.py`
- `tests/models/test_train_gc_first_real_model_cli.py`
- `tests/research/test_phase48_validator.py`

Required inputs:
- `configs/datasets/gc-30m-real-dataset-build-manifest.json`
- `configs/models/gc-majority-baseline-training-run.json`
- `docs/implementation-reports/phase-46-47-gc-real-dataset-build-and-training-start.md`
- `docs/superpowers/plans/2026-09-07-phase-48-first-real-gc-model.md`

Contracts:
- Phase 48 is research-only.
- Model promotion remains blocked.
- Live trading, broker execution, and capital allocation remain blocked.
- TRAIN-only transform fitting is required.
- VALIDATION-only threshold selection is required.
- TEST-only final metric reporting is required.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation

Deliverables:
- Write a review to `agent-exchange/reviews/YYYY-MM-DDTHHMMSSZ-claude-code-review-phase-48-first-real-gc-model.md`.
- Use verdict `ACCEPT`, `ACCEPT_WITH_NOTES`, `ACCEPT_WITH_FIXES`, or `REJECT`.
- Specifically address leakage risk, split handling, threshold selection, metric
  interpretation, and whether Phase 49 should focus on features/diagnostics
  rather than promotion.

Verification commands:
- `python -m pytest tests\models\test_first_real_gc_model.py tests\models\test_train_gc_first_real_model_cli.py tests\research\test_phase48_validator.py -q`
- `python tools\validate_phase48.py`

Out of scope:
- Do not change code.
- Do not retrain the model.
- Do not query vendor APIs.
- Do not claim edge.
- Do not approve promotion, live trading, broker execution, or capital
  allocation.

Notes:
- Groq is unavailable due to quota, so this review replaces the usual
  Groq-plus-Claude second opinion.
- Current result: validation expected R is slightly positive, but TEST expected
  R is slightly negative.
- Superseded after the human reported Claude Code is currently unavailable and
  asked Codex to perform the remaining work directly.
