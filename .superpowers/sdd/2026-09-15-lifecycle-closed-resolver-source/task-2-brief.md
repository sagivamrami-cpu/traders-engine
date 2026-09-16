### Task 2: Static proof and fail-closed command

**Files:**
- Create: `trading_system/tree_spec/lifecycle_closed_resolver_source.py`
- Create: `tools/check_lifecycle_closed_resolver_source_parity.py`
- Create: `tests/tree_spec/test_lifecycle_closed_resolver_source.py`

**Interfaces:**
- Consumes: an explicit retained-source root and vendor text.
- Produces: JSON `VERIFIED` only on exact source/runtime projection and verified child reports; any error prints schema-valid `BLOCKED` with both readiness flags false.

- [ ] **Step 1: Write failing audit/mutation tests**

```python
def test_audit_rejects_pre_fill_extreme_leak(tmp_path, monkeypatch):
    mutate_vendor("_open_extremes(since, trade)", "(high, low)")
    report = audit(RETAINED)
    assert "VENDOR_AST_MISMATCH:lifecycle_closed_resolver" in report["blockers"]
    assert report["ready_for_replay"] is False
```

Also mutate the three-day fetch, correction gates, strict `>`, PENDING fall-through, minimum/ambiguity/ordinary ordering, `continue`, and child-report identity.

- [ ] **Step 2: Prove the audit tests are red**

Run: `python -B -m pytest tests/tree_spec/test_lifecycle_closed_resolver_source.py -q --tb=short -p no:cacheprovider`

Expected: failure because the audit module and CLI do not exist.

- [ ] **Step 3: Parse and project only `tracker.py::check`**

The auditor must locate the unique closed-bar loop, require its correction/slicing/extrema statements and the PENDING/OPEN physical branch sequence, then compare the normalized vendor AST to the precise adaptation.  It must require the closed-PENDING, lifecycle primitives, outcome shelf, transitions, revalidation, protection and ordinary-resolution audit reports.

- [ ] **Step 4: Prove audit and command behaviour**

Run: `python -B -m pytest tests/tree_spec/test_lifecycle_closed_resolver_source.py -q --tb=short -p no:cacheprovider`

Run: `python -B tools/check_lifecycle_closed_resolver_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`

Expected: all tests pass; command exits 0 and reports `VERIFIED`, `ready_for_replay=false`, `ready_for_training=false`.

