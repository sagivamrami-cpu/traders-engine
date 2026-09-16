# Task 2 report: lifecycle OPEN ordinary-resolution source proof

Status: DONE

## Changed files

- `trading_system/tree_spec/lifecycle_open_ordinary_resolution_source.py`
- `tools/check_lifecycle_open_ordinary_resolution_source_parity.py`
- `tests/tree_spec/test_lifecycle_open_ordinary_resolution_source.py`
- `docs/architecture/LIFECYCLE-OPEN-ORDINARY-RESOLUTION-SOURCE-USAGE.md`
- `.superpowers/sdd/2026-09-14-lifecycle-open-ordinary-resolution-source/task-2-report.md`

Task 1 runtime and runtime tests were not modified.

## TDD evidence

RED command:

```powershell
python -m pytest -q tests/tree_spec/test_lifecycle_open_ordinary_resolution_source.py
```

RED output: `13 failed in 0.64s`. The failures were expected: the retained-source
auditor module and parity CLI did not exist.

GREEN command:

```powershell
python -m pytest -q tests/tree_spec/test_lifecycle_open_ordinary_resolution_source.py
```

GREEN output: `13 passed in 16.28s`.

The post-GREEN fixture correction was test-only: an initial physical-order
mutation selected an earlier identical source block at line 1306. It now targets
the pinned line-2721 block. No Task 1 runtime compatibility correction was
needed.

## Exact verification

```powershell
python -m pytest -q tests/tree_replay/test_lifecycle_open_ordinary_resolution.py tests/tree_spec/test_lifecycle_open_ordinary_resolution_source.py
```

PASS: `20 passed in 15.72s`.

```powershell
python -B tools/check_lifecycle_open_ordinary_resolution_source_parity.py --source-root 'C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'
```

PASS (exit 0): JSON reported `status: "VERIFIED"`,
`source_subset_verified: true`, `blockers: []`, checked projection
`lifecycle_open_ordinary_resolution`, and
`ready_for_replay: false` / `ready_for_training: false`.

## Scope and concerns

The auditor reads retained source text and parses ASTs only; it never imports or
executes retained source. It pins `tracker.py` lines 2721-2750, the required
commit/blob, the exact allowed private runtime projection, and accepted
transition/outcome-shelf child proof reports. All source, child, audit-report,
and CLI/JSON failures fail closed with both readiness flags false.

No ambiguity or zone-return recovery, evidence acquisition, persistence,
delivery, economics, replay, dataset, training, model, or live-trading behavior
was added. No commit or push was made.
