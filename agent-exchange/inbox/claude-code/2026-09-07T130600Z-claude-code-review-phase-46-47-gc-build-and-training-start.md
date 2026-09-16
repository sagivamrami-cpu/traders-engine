# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Status:
SUPERSEDED_BY_HUMAN_DIRECTION_CODEX_SELF_REVIEW

Created at:
2026-09-07T13:06:00Z

Objective:
Review Codex Phase 46-47 implementation: authorized GC 30m real dataset build, build manifest schema/CLI, readiness transition to training start, and research-only majority baseline training run.

Superseded:
The human asked Codex to perform this review directly instead of Claude Code.
Codex self-review result:
`agent-exchange/reviews/2026-09-07T132500Z-codex-self-review-phase-46-47-gc-build-and-training-start.md`.

Scope:
- `schemas/gc_real_dataset_build_manifest.schema.json`
- `tools/build_gc_30m_real_dataset.py`
- `trading_system/research/gc_real_dataset_build.py`
- `trading_system/research/gc_pretraining_readiness.py`
- `tools/gc_pretraining_readiness.py`
- `tools/train_gc_majority_baseline.py`
- `tests/research/test_gc_real_dataset_build.py`
- `tests/research/test_gc_pretraining_readiness.py`
- `configs/datasets/gc-30m-real-dataset-build-manifest.json`
- `configs/models/gc-majority-baseline-training-run.json`
- `configs/data/gc-session-calendar-construction-policy.yaml`
- `schemas/gc_session_calendar_construction_policy.schema.json`
- `trading_system/research/gc_session_calendar_construction_policy.py`
- `tests/research/test_gc_session_calendar_construction_policy.py`
- `agent-exchange/status/2026-09-07T130500Z-codex-phase-42-intake-phase-46-47-build-and-training-result.md`

Review questions:
- Does the build manifest schema pin the correct safety boundaries: built dataset true, training/promotion false at build time, source hashes only, no local paths?
- Does the build CLI correctly enforce D9 authorization and identity verification through `gc_real_dataset_build.build_real_dataset`?
- Does pretraining readiness correctly remain blocked without a build manifest and become `READY` only when the built rows pass training readiness?
- Is removing `TRAIN_PRODUCTION_MODEL` from `blocked_actions` only after `training_start_allowed=true` correct, while keeping model promotion/live/broker/capital blocked?
- Does the majority baseline training run remain research-only and schema-valid?
- Are there any leakage, split, label, row-selection, or order-flow variant issues before moving to the next modeling phase?

Verification requested:
- `python -m pytest tests\research\test_gc_real_dataset_build.py tests\research\test_gc_pretraining_readiness.py tests\models\test_baseline_training.py tests\models\test_training_readiness.py -q`
- `python -m pytest tests\research\test_gc_missing_bar_policy.py tests\research\test_gc_dataset_identity.py tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_real_dataset_builder.py -q`
- `python tools\validate_phase24.py`
- `python tools\validate_phase25.py`
- `python tools\validate_phase29.py`
- `python tools\validate_phase30.py`
- `python tools\gc_pretraining_readiness.py --contract configs\datasets\gc-30m-real-dataset-contract.yaml --decisions agent-exchange\decisions\databento-gc-real-data-decisions.yaml --checklist configs\research\real-data-readiness-checklist.yaml --training-policy configs\models\baseline-training-policy.yaml --groq-phase24-review agent-exchange\reviews\2026-09-01T185200Z-groq-review-phase-24-dataset-contract.md --groq-phase24-intake agent-exchange\status\2026-09-01T170300Z-codex-groq-phase-23-to-26-review-intake.md --build-manifest configs\datasets\gc-30m-real-dataset-build-manifest.json --rows-root market-data\gc-30m-real --variant order_flow`

Expected:
- Review-only markdown under `agent-exchange/reviews/`.
- Verdict `ACCEPT`, `ACCEPT_WITH_NOTES`, or `REVISION_REQUESTED`.
- Do not query vendors.
- Do not include raw market rows, local absolute paths, secrets, account identifiers, or source archive paths in the review.
- Do not commit or push.
