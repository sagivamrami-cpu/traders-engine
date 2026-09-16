### Task 2: Source-pinned outer-pass intake and fail-closed audit

**Files:**
- Create: `trading_system/tree_spec/causal_replay_source.py`
- Create: `tools/check_causal_replay_source_parity.py`
- Create: `tests/tree_spec/test_causal_replay_source.py`
- Create: `configs/trees/causal-replay-source-contracts.json`
- Create: `docs/architecture/CAUSAL-REPLAY-SOURCE-INTAKE.md`

**Interfaces:**
- `check_source_parity(source_root: Path) -> dict` parses `scripts/market_watch.py`; it never imports it.
- Returns schema-valid `VERIFIED` only after validating commit/blob pins and the required source order; every failure returns `BLOCKED`, a nonempty string blocker list, `ready_for_replay=False`, and `ready_for_training=False`.
- The CLI requires `--source-root`, prints only JSON, and exits `0` for `VERIFIED`, `2` for `BLOCKED`.

- [ ] **Step 1: Write mutation-based source-audit tests**

```python
def test_audit_requires_lifecycle_before_level_reversal(tmp_path):
    root = copied_retained_source(tmp_path)
    mutate(root / "scripts" / "market_watch.py",
           "_msgs = tracker.closeout_check() + tracker.check()",
           "_msgs = tracker.closeout_check() + tracker.check()\n# moved")
    report = check_source_parity(root)
    assert report["status"] == "BLOCKED"
    assert "MARKET_WATCH_ORDER_MISMATCH" in report["blockers"]

def test_audit_retains_record_only_inside_alert_enabled_branch():
    report = check_source_parity(RETAINED_ROOT)
    assert report["projection"]["level_reversal_record_guard"] == "--telegram"
    assert report["ready_for_training"] is False
```

Mutate source blob/commit, state load, pre-producer state write, tracker lock
and `closeout_check()+check()` order, lifecycle gate, `level_reversal.find`,
reversal-before-tree/engine placement, `tracker.record`, alert guard and final
state write. Also mutate the runtime manifest, malformed child report and CLI
root exception path.

- [ ] **Step 2: Run the audit tests and confirm they fail**

Run: `python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider`

Expected: import failure because the audit module and CLI do not exist.

- [ ] **Step 3: Implement AST projection and manifest validation**

```python
REQUIRED_ORDER = (
    "watch_state_load", "watch_state_preproducer_save", "tracker_closed_pass",
    "tracker_gate", "level_reversal_find", "level_reversal_outer_gates",
    "level_reversal_record_alert_guard", "watch_state_final_save",
)

def check_source_parity(source_root: Path) -> dict:
    report = _empty_report()
    try:
        source = _read_pinned_market_watch(source_root)
        main = _unique_main(ast.parse(source.text))
        projection = _project_required_order(main)
    except Exception as exc:
        return _blocked(report, f"SOURCE_READ_OR_PARSE:{type(exc).__name__}")
    blockers = _validate_projection(projection)
    if blockers:
        return _blocked(report, *blockers)
    return _verified(report, projection)
```

The implementation must prove the actual retained ordering from `main()`:
state load at lines 494-495; pre-producer state write before tracker lifecycle;
the locked `closeout_check() + check()` pass and gate at lines 962-972;
`level_reversal.find` before tree/engine; all outer gates before
`tracker.record`; the `--telegram` guard enclosing record; and final state
write at line 1599. The projection must label windows, market-closed,
producer-arbitration, post-stop, occupied-slot and same-level gates as
`UNWIRED_OUTER_ADMISSION`, never replace them with booleans.

- [ ] **Step 4: Run source proof and command**

Run: `python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider`

Run: `python -B tools/check_causal_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`

Expected: PASS and `VERIFIED`; both readiness flags remain false.

