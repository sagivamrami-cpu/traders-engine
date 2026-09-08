# Agent Exchange Review

Reviewer:
Codex

Target request:
agent-exchange/inbox/claude-code/2026-09-07T130600Z-claude-code-review-phase-46-47-gc-build-and-training-start.md

Created at:
2026-09-07T13:25:00Z

Status:
REVIEW_READY_FOR_HUMAN

Verdict:
ACCEPT_WITH_FIXES

Summary:
Codex performed the Phase 46-47 review directly after the human asked to replace
the Claude Code review. The review found one blocker in the readiness/training
trust boundary. It was fixed and reverified.

Findings:

F1 (blocking, fixed): `candidate_rows_from_build_manifest()` trusted
`rows.parquet` after loading a valid build manifest but did not verify that the
local rows file still matched `rows_sha256`, `rows_count`, or `rows_columns`.
This allowed a locally modified rows file to pass readiness/training under a
previous valid manifest. Fixed in
`trading_system/research/gc_pretraining_readiness.py` by verifying parquet file
hash, row count, and column order before converting rows to training objects.
Regression coverage added in `tests/research/test_gc_pretraining_readiness.py`.

Non-blocking notes:
- Build manifest validation remains strict enough for Phase 46: dataset id,
  source hashes, build stats, rows hash, rows location, safety booleans, and
  promotion/live/broker/capital blocked actions are schema-pinned.
- The build CLI enforces construction authorization indirectly through
  `gc_real_dataset_build.build_real_dataset`, which recomputes local archive
  identity and checks D9 authorization before writing rows.
- Readiness remains blocked without a build manifest and reaches `READY` only
  with a valid manifest, valid rows parquet, accepted review intake, and passing
  training-readiness counts.
- Majority baseline training remains research-only. `promotion_allowed` stays
  `false`; model promotion, live trading, broker execution, and capital
  allocation remain blocked.

Verification:
- `python -m pytest tests\research\test_gc_pretraining_readiness.py -q`: PASS,
  `8 passed`.
- `python -m pytest tests\research\test_gc_real_dataset_build.py tests\research\test_gc_real_dataset_builder.py tests\models\test_baseline_training.py tests\models\test_training_readiness.py -q`:
  PASS, `24 passed`.
- `python tools\gc_pretraining_readiness.py ... --build-manifest configs\datasets\gc-30m-real-dataset-build-manifest.json --rows-root market-data\gc-30m-real --variant order_flow`:
  PASS, `status: READY`, `training_start_allowed: true`,
  `required_pretraining_gates: []`.
- `python tools\train_gc_majority_baseline.py ... --variant order_flow --run-out configs\models\gc-majority-baseline-training-run.json`:
  PASS, `status: TRAINED`, `baseline_class: STOP_FIRST`,
  `promotion_allowed: false`.

Current built dataset:
- dataset_id: `f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966`
- rows_count: `380362`
- order_flow included rows: `341056`
- readiness split summary:
  - TRAIN: `238398`
  - VALIDATION: `45074`
  - TEST: `57584`
- class distribution:
  - EXPIRED: `47922`
  - STOP_FIRST: `146567`
  - TARGET_FIRST: `146567`
- latest majority-baseline validation accuracy: `0.4223499134756179`
- latest majority-baseline test accuracy: `0.4404522089469297`

Boundary statement:
- No commit or push was performed.
- No vendor API was queried.
- No raw rows, source archive paths, local absolute paths, secrets, or account
  identifiers are included in this review.
- Full `python -m pytest tests -q` was attempted and manually stopped after a
  prolonged run; it had no visible failures before interruption. Focused
  verification above is the authoritative verification for this review.
