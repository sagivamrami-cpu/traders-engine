# Task 2: Retained-source proof and fail-closed CLI

**Files:**
- Create: `trading_system/tree_spec/lifecycle_open_ordinary_resolution_source.py`
- Create: `tools/check_lifecycle_open_ordinary_resolution_source_parity.py`
- Create: `tests/tree_spec/test_lifecycle_open_ordinary_resolution_source.py`
- Modify: `docs/architecture/LIFECYCLE-OPEN-ORDINARY-RESOLUTION-SOURCE-USAGE.md`

**Interfaces:**
- Consumes: pinned source root, baseline source-pin manifest, Task 1 runtime,
  accepted transition/outcome-shelf auditors.
- Produces: `audit_lifecycle_open_ordinary_resolution_source(source_root) -> dict`
  and a JSON CLI whose only success status is `VERIFIED` with both readiness
  flags false.

## Requirements

- Parse/read the retained source only; never import or execute it.
- Pin source `tracker.py` lines 2721–2750, commit
  `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and blob
  `b616b34022e436545d8c1daf85eced51614fd74e`.
- Parse the physical fragment in a synthetic loop wrapper only when that is
  necessary for its original `continue` syntax; validate its full ordered AST.
- Compare Task 1 runtime AST with an allowed projection. Require exactly the
  accepted transition and outcome-shelf child audit reports, with no blockers
  and false replay/training readiness.
- Every source/audit/child/report/serialization/CLI failure must return
  valid BLOCKED JSON with `ready_for_replay=false` and
  `ready_for_training=false`.
- Do not add source execution, evidence acquisition, persistence/delivery,
  economics, replay/dataset/training/model behavior or zone return.

## TDD behavior

```python
def test_audit_rejects_low_high_projection_mutation(source_root, monkeypatch):
    monkeypatch.setattr(module, "VENDOR", str(mutated_vendor))
    report = audit_lifecycle_open_ordinary_resolution_source(source_root)
    assert report["status"] == "BLOCKED"
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False
```

Also cover source commit/blob mismatch, modified physical source order,
malformed child report, missing root and CLI JSON-error behavior. The focused
runtime test suite must remain in the final combined command.

Run after implementation:

```powershell
python -m pytest -q tests/tree_replay/test_lifecycle_open_ordinary_resolution.py tests/tree_spec/test_lifecycle_open_ordinary_resolution_source.py
python -B tools/check_lifecycle_open_ordinary_resolution_source_parity.py --source-root 'C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'
```

Expected: tests PASS; CLI JSON has `status="VERIFIED"`, empty `blockers`,
`source_subset_verified=true`, `ready_for_replay=false`, and
`ready_for_training=false`.

Write report to:
`.superpowers/sdd/2026-09-14-lifecycle-open-ordinary-resolution-source/task-2-report.md`.

Report status `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`;
list changed files and exact command/result. Do not commit, push, change
unrelated files, or spawn subagents.
