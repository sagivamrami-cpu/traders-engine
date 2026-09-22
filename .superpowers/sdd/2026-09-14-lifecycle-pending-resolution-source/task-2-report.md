# Task 2 report — PENDING branch source audit

## Status

`IMPLEMENTED_AWAITING_CODEX_REVIEW`

Implemented only the Task 2 retained-source auditor, its JSON CLI, its source
contract tests, and this report. No runtime resolver, original source, market
data, external system, commit, or push was changed.

## Files

- `trading_system/tree_spec/lifecycle_pending_resolution_source.py`
- `tools/check_lifecycle_pending_resolution_source_parity.py`
- `tests/tree_spec/test_lifecycle_pending_resolution_source.py`
- `.superpowers/sdd/2026-09-14-lifecycle-pending-resolution-source/task-2-report.md`

## RED evidence

Before implementation:

```text
python -m pytest -q tests/tree_spec/test_lifecycle_pending_resolution_source.py
15 failed in 1.13s
```

Every failure was expected: the auditor module and CLI did not yet exist.

The later serialization-hardening regression was also written before its fix:

```text
python -m pytest -q tests/tree_spec/test_lifecycle_pending_resolution_source.py -k "encoder_failure"
1 failed, 15 deselected in 0.14s
```

It demonstrated that an encoder failure could escape instead of emitting the
required valid blocked JSON payload.

## GREEN evidence

```text
python -m pytest -q tests/tree_replay/test_lifecycle_pending_resolution.py tests/tree_replay/test_lifecycle_outcome_shelf.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_tree_revalidation.py
72 passed in 16.75s
```

```text
python -m pytest -q tests/tree_spec/test_lifecycle_pending_resolution_source.py -k "not verifies_from_unrelated_cwd"
15 passed, 1 deselected in 27.44s

python -m pytest -q tests/tree_spec/test_lifecycle_pending_resolution_source.py -k "verifies_from_unrelated_cwd"
1 passed, 15 deselected in 8.36s
```

```text
python -B tools/check_lifecycle_pending_resolution_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

The final CLI returned exit code `0`, `status: VERIFIED`, an empty blocker list,
`checked_projections: ["lifecycle_pending_resolution"]`, and both readiness
flags explicitly `false`.

## What the audit proves

The auditor read/parses the pinned `tracker.py` only. It verifies the pinned
chart-desk commit and tracker blob, extracts exactly one nested PENDING branch,
requires its ordered source decisions, and compares the explicit offline AST
projection to `LifecyclePendingResolution`.

The checked decision sequence includes entry-band and supplied extreme fallback,
short/high and long/low touch inequalities, no-touch return, same-direction open
slot cancellation and raw fact, failed revalidation cancellation and raw fact,
successful OPEN fields, one shared fill/progress clock, and fill caveat/message.
Mutation tests reject touch, conflict, revalidation, outcome-result, timestamp,
message, and entry-band dependency drift.

The CLI requires `--source-root`, returns JSON even for argument, audit, report,
and JSON-encoder errors, and exits zero only on verified parity.

## Composed child proofs

The audit requires and validates real, currently verified child reports:

| Child | Required checked projections |
| --- | --- |
| `lifecycle_outcome_shelf` | `lifecycle_outcome_shelf` |
| `lifecycle_transitions` | `lifecycle_transitions` |
| `tree_revalidation` | `matrix_reader`, `tree_revalidation` |
| `lifecycle_primitives` | `lifecycle_bars`, `desk_success`, `lifecycle_voice` |

Each child must be `VERIFIED`, have no blockers, preserve the pinned
chart-desk commit, and keep both readiness flags false. Malformed, unserializable,
blocked, or identity-drifted child reports fail closed.

## Blockers and concerns

No implementation blocker remains for Task 2.

This is a static, offline proof of only the PENDING fill/cancel slice. It does
not run the original source, acquire prices/bars, execute the deferred OPEN
branch, persist/gate/deliver state, establish causal historical availability,
produce economic outcomes or labels, create a dataset, fit/evaluate a model, or
make replay/training readiness true.
