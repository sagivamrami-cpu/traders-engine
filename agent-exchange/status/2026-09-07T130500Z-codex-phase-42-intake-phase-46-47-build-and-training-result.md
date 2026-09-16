# Agent Exchange Status

Sender:
Codex

Status:
IMPLEMENTED_AWAITING_CLAUDE_CODE_REVIEW

Created at:
2026-09-07T13:05:00Z

Scope:
- Intake of Claude Code Phase 42 recheck.
- Phase 46 GC real dataset build CLI and manifest schema.
- Phase 47 pretraining readiness with build manifest, plus research-only majority baseline training run.

Summary:
- Accepted Claude Code Phase 42 recheck verdict `ACCEPT_WITH_NOTES`.
- Verified Claude Code's Phase 29/30 validator retargeting:
  - `python tools\validate_phase29.py`: PASS.
  - `python tools\validate_phase30.py`: PASS.
  - `python -m pytest tests\research\test_phase29_validator.py tests\research\test_phase30_validator.py -q`: PASS, `2 passed in 235.64s`.
- Linked the Phase 42 scope amendment decision into the session-calendar construction policy through `scope_amendment_decision_ref`.
- Added `schemas/gc_real_dataset_build_manifest.schema.json`.
- Added `tools/build_gc_30m_real_dataset.py`.
- Built the authorized GC 30m real research dataset from the local Databento archives.
- Added build-manifest consumption to GC pretraining readiness.
- Added `tools/train_gc_majority_baseline.py`.
- Trained the research-only order-flow majority-class baseline after readiness reached `READY`.
- Per human direction, Codex replaced the Claude Code review with a direct self-review:
  `agent-exchange/reviews/2026-09-07T132500Z-codex-self-review-phase-46-47-gc-build-and-training-start.md`.
- Self-review found and fixed one readiness/training trust-boundary issue: rows parquet hash, row count, and columns are now verified against the build manifest before readiness/training.

Built dataset:
- dataset_id: `f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966`
- build_manifest_ref: `configs/datasets/gc-30m-real-dataset-build-manifest.json`
- rows_relative_dir: `f9d3c1b0d02da255`
- rows_file: `rows.parquet`
- rows_sha256: `6b5045fbfff060748aae1e39d93308d801f35afacb0a6c8f46d466a45b77d0a0`
- rows_count: `380362`
- first_bar_start: `2010-06-07T00:00:00Z`
- last_bar_start: `2026-08-05T23:30:00Z`
- expected_session_bars: `194028`
- present_session_bars: `190181`
- missing_expected_bars: `3847`
- ohlcv_only included rows: `355150`
- order_flow included rows: `341056`

Pretraining readiness with built dataset:
- command: `python tools\gc_pretraining_readiness.py ... --build-manifest configs\datasets\gc-30m-real-dataset-build-manifest.json --rows-root market-data\gc-30m-real --variant order_flow`
- status: `READY`
- training_start_allowed: `true`
- dataset_construction_allowed: `true`
- model_promotion_allowed: `false`
- required_pretraining_gates: `[]`
- blocking_reviews: `[]`
- order_flow split_summary:
  - TRAIN: `238398`
  - VALIDATION: `45074`
  - TEST: `57584`
- order_flow class_distribution:
  - EXPIRED: `47922`
  - STOP_FIRST: `146567`
  - TARGET_FIRST: `146567`

Training run:
- run_manifest_ref: `configs/models/gc-majority-baseline-training-run.json`
- status: `TRAINED`
- model_type: `MAJORITY_CLASS_BASELINE`
- model_version: `majority-class-baseline-0.1.0`
- baseline_class: `STOP_FIRST`
- validation_accuracy: `0.4223499134756179`
- test_accuracy: `0.4404522089469297`
- promotion_allowed: `false`
- run_id: `9e6150e844b0a1cd107e01bf609be0d06bd3ed4bbf2c5eb90f597c6fae49adfe`

Verification:
- `python -m pytest tests\research\test_gc_real_dataset_build.py -q`: PASS, `5 passed`.
- `python -m pytest tests\research\test_gc_session_calendar_construction_policy.py -q`: PASS, `4 passed`.
- `python -m pytest tests\research\test_gc_missing_bar_policy.py tests\research\test_gc_dataset_identity.py tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_pretraining_readiness.py tests\research\test_gc_real_dataset_builder.py tests\research\test_gc_real_dataset_build.py -q`: PASS, `38 passed`.
- `python -m pytest tests\research\test_gc_real_dataset_build.py tests\research\test_gc_pretraining_readiness.py tests\models\test_baseline_training.py tests\models\test_training_readiness.py -q`: PASS, `19 passed`.
- `python -m pytest tests\models\test_model_contracts.py tests\governance\test_model_card.py tests\evaluation\test_promotion_gate.py -q`: PASS, `6 passed`.
- `python -m pytest tests\research\test_gc_pretraining_readiness.py -q`: PASS, `8 passed` after the self-review hash/count/columns guard.
- `python -m pytest tests\research\test_gc_real_dataset_build.py tests\research\test_gc_real_dataset_builder.py tests\models\test_baseline_training.py tests\models\test_training_readiness.py -q`: PASS, `24 passed`.
- `python tools\validate_phase24.py`: PASS.
- `python tools\validate_phase25.py`: PASS.
- `python tools\validate_phase29.py`: PASS.
- `python tools\validate_phase30.py`: PASS.
- Sanitization check on build and training manifests: PASS; no local absolute paths, Desktop paths, source ZIP names, or user data paths found.

Boundary statement:
- No commit or push was performed.
- No vendor API was queried.
- Local raw market archives were read only by the authorized Phase 46 build.
- Raw market rows and local absolute data paths were not written to `agent-exchange`.
- Model promotion, live trading, broker execution, and capital allocation remain blocked.
