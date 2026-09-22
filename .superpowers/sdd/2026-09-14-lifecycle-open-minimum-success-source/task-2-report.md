# Task 2 report — lifecycle OPEN minimum-success source audit

Status: IMPLEMENTED_AWAITING_CODEX_REVIEW

## Scope completed

- Added the read-only retained-source auditor:
  `trading_system/tree_spec/lifecycle_open_minimum_success_source.py`.
- Added the required explicit-root JSON CLI:
  `tools/check_lifecycle_open_minimum_success_source_parity.py`.
- Added focused static-audit and CLI tests:
  `tests/tree_spec/test_lifecycle_open_minimum_success_source.py`.

The auditor pins `chartdesk/tracker.py` lines 2690–2704 to chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and blob
`b616b34022e436545d8c1daf85eced51614fd74e`. It reads and parses the retained
file only; it never imports or executes it.

It proves the retained physical branch order and compares the Task 1 runtime
against the only allowed supplied-evidence projection. It requires verified,
blocker-free, JSON-serializable, source-pinned child reports for
`lifecycle_open_postfill_evidence`, `lifecycle_transitions`, and
`lifecycle_outcome_shelf`, each with both readiness flags false. Any identity,
blob, physical-source, projection, child-report, root, audit, or CLI-report
failure returns `BLOCKED` with both readiness flags false.

## TDD evidence

### RED

Before either Task 2 artifact existed, the new test suite failed as expected:

```text
python -m pytest -q tests/tree_spec/test_lifecycle_open_minimum_success_source.py
14 failed in 0.67s
AssertionError: OPEN minimum-success source auditor missing
FileNotFoundError: check_lifecycle_open_minimum_success_source_parity.py
```

The failures were specifically caused by the absent auditor and CLI.

### GREEN

After the minimal auditor and CLI implementation, the first run had one test
fixture defect: its generic message/outcome replacement mutated an earlier
`minimum_success` branch at retained line 1276 rather than the pinned slice.
The implementation was not changed. The fixture was narrowed to start at
`SOURCE_START_LINE`, so it mutates physical lines 2690–2704 only.

```text
python -m pytest -q tests/tree_spec/test_lifecycle_open_minimum_success_source.py
14 passed in 25.10s
```

The explicit mutation coverage rejects:

- reordering the quote guard;
- low/high protective-touch reversal;
- directional progress-extreme reversal;
- incorrect source minimum points or raw-fact payload;
- source directional-progress drift;
- physical message-before-outcome reorder;
- source commit or blob drift;
- missing explicit root and malformed child reports; and
- malformed, contradictory, and non-serializable CLI audit reports.

## Final verification

The Task 1 runtime suite and the new Task 2 source-audit suite were run
together:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_open_minimum_success.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_lifecycle_outcome_shelf.py tests/tree_spec/test_lifecycle_open_minimum_success_source.py
110 passed in 26.95s
```

The required explicit-root CLI was run separately:

```text
python tools/check_lifecycle_open_minimum_success_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

It exited `0` with `status: VERIFIED`,
`checked_projections: ["lifecycle_open_minimum_success"]`, the required three
verified child reports, the pinned chart-desk commit, and
`ready_for_replay: false` / `ready_for_training: false`.

## Boundaries retained

This task adds static source proof and a CLI only. It does not alter Task 1
runtime behavior, import or execute the retained tracker source, acquire data,
compose a resolver, persist or deliver tracker state, or make any fill, P&L,
economic, replay, dataset, training, model, or trading-readiness claim. No
commit, push, subagent work, or unrelated artifact modification occurred.
