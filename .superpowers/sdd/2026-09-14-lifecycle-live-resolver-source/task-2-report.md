# Task 2 report: lifecycle live resolver source

## Scope completed

Implemented only Task 2 from
`docs/superpowers/plans/2026-09-14-lifecycle-live-resolver-source.md` against
`docs/architecture/LIFECYCLE-LIVE-RESOLVER-SOURCE-INTAKE.md`.

The new auditor parses retained `tracker.py` text and Task 1 runtime text only.
It does not import or execute the retained source. It pins the configured
chart-desk baseline commit, retained repository `HEAD`, tracker blob, complete
physical source kernel AST, explicit Task 1 runtime projection, and the seven
accepted direct-child audit reports. The new CLI requires `--source-root`,
emits JSON only, and fails closed with both readiness flags false.

## Changed paths

- `trading_system/tree_spec/lifecycle_live_resolver_source.py` — retained-source
  identity/kernel auditor and accepted-child proof graph.
- `tools/check_lifecycle_live_resolver_source_parity.py` — explicit-root,
  fail-closed JSON CLI.
- `tests/tree_spec/test_lifecycle_live_resolver_source.py` — test-first source,
  runtime, child report, root/blob, and CLI tests.
- `.superpowers/sdd/2026-09-14-lifecycle-live-resolver-source/task-2-report.md`
  — this report.

No Task 1 runtime/tests/usage, accepted child module, caller, persistence,
gate, delivery, or retained source path was modified.

## TDD evidence

### RED

The audit/CLI tests were written before either production file existed, then
run with:

```powershell
python -B -m pytest tests/tree_spec/test_lifecycle_live_resolver_source.py -q --tb=short -p no:cacheprovider
```

Result: `27 failed in 1.65s`.

The audit tests failed at the intended missing-module boundary:

```text
AssertionError: lifecycle live-resolver source auditor missing
```

The CLI tests simultaneously failed because
`tools/check_lifecycle_live_resolver_source_parity.py` did not exist. No Task 2
production auditor or CLI existed during this RED run.

### GREEN

After adding only the auditor and CLI, correcting the detected NUL blob-input
escaping and test-local mutation targeting, the full focused suite was run:

```powershell
python -B -m pytest tests/tree_spec/test_lifecycle_live_resolver_source.py -q --tb=short -p no:cacheprovider
```

Result: `27 passed in 136.79s (0:02:16)`.

The valid-path parent proof was separately rerun:

```powershell
python -B -m pytest tests/tree_spec/test_lifecycle_live_resolver_source.py::test_complete_live_resolver_projection_and_child_graph_verify_without_readiness -q --tb=short -p no:cacheprovider
```

Result: `1 passed in 32.09s`.

## Mutation evidence

The source-kernel mutations cover quote-order and raw-read fallback, inclusive
force age, strict bar freshness, `(low, high)` carry, close selection,
`list(d.items())`, terminal/missing-price skip, PENDING-before-OPEN order,
ambiguity continuation, and ordinary-terminal zone suppression. Runtime
mutations cover a third quote read, raw-quote loss before minimum success,
cancellation fall-through, child order, zone-return guard, and a direct save
effect. The mutation-focused command was:

```powershell
python -B -m pytest tests/tree_spec/test_lifecycle_live_resolver_source.py::test_source_kernel_rejects_quote_fallback_scan_and_branch_precedence_mutations tests/tree_spec/test_lifecycle_live_resolver_source.py::test_runtime_rejects_observation_raw_quote_order_and_effect_boundary_drift -q --tb=short -p no:cacheprovider
```

Result: `17 passed in 1.31s`.

Each mutated physical source kernel raises
`SOURCE_LIVE_RESOLVER_KERNEL_MISMATCH`; every mutated Task 1 runtime yields
`VENDOR_AST_MISMATCH:lifecycle_live_resolver`. The focused full suite also
proves source-root/commit/blob rejection, configured child identity drift,
malformed child reports, missing `--source-root`, invalid root, contradictory
or unserializable audit reports, audit exceptions, and serialization exceptions
all emit schema-valid `BLOCKED` JSON with both readiness flags false.

## Regression and CLI evidence

Task 1 plus all direct child runtime suites were run unchanged:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_live_resolver.py tests/tree_replay/test_lifecycle_live_evidence.py tests/tree_replay/test_lifecycle_live_resolution_evidence.py tests/tree_replay/test_lifecycle_pending_resolution.py tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_replay/test_lifecycle_open_minimum_success.py tests/tree_replay/test_lifecycle_open_protection.py tests/tree_replay/test_lifecycle_open_ordinary_resolution.py tests/tree_replay/test_lifecycle_open_zone_return.py -q --tb=short -p no:cacheprovider
```

Result: `119 passed in 1.25s`.

The standalone explicit-root CLI was run from the repository against the
retained source root:

```powershell
python -B tools/check_lifecycle_live_resolver_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

Result: exit `0`; JSON `status=VERIFIED`,
`source_subset_verified=true`, `blockers=[]`,
`ready_for_replay=false`, and `ready_for_training=false`.

## Scope caveats

This is a static retained-source proof and supplied-port runtime projection
only. It does not establish a causal feed, source execution, load/save/lock,
gate/persistence, delivery, broker execution, fills/P&L, replay, datasets,
training, model readiness, model promotion, or live-trading readiness.
Accepted child reports are checked for false readiness, but inherited child
effects are not asserted to be effect-free.
