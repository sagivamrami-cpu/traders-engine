## Task 1: Original admission calculation closure

**Files:** Create `_vendor/admission_matrix.py`, `_vendor/admission_toolkit.py`,
`_vendor/admission_indicators.py` as needed, `_vendor/admission_quality.py`,
`_vendor/admission_clocks.py`, `_vendor/admission_swing.py` under
`trading_system/tree_replay/`; `trading_system/tree_spec/admission_source.py`;
`configs/trees/admission-source-contracts.json`; `tools/check_admission_source_parity.py`;
`tests/tree_replay/test_admission_calculations.py`,
`tests/tree_spec/test_admission_source.py`; `docs/architecture/ADMISSION-CALCULATIONS-USAGE.md`.

**Consumes:** Pinned source chartdesk/{matrix,toolkit,indicators,tr,entry_quality,windows,zones}.py
and floor/marketclock.py. Retained root:
`C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
Inspect existing vendor tr/indicators and audit modules before reuse; no modifications
to previous accepted source modules/manifests. Add own dependency projection if needed.

**Produces:** `admission_matrix.read_frame(df, tf, basis_note=None) -> TFView`,
original matrix tool functions/types/constants, `admission_quality.evaluate(...)`
and helpers with source signatures, `admission_swing._last_swing(df, up)`,
`admission_clocks.outside_reason(now)` / `entry_blocked(now)` with required aware time,
and `audit_admission_source(source_root) -> dict` with source_subset_verified,
blockers and false readiness. CLI accepts `--source-root` explicit parent root.

- [ ] Write failing calculation/clock/quality/swing and source-audit tests.
  Example boundary expectation (UTC equivalent of Monday Jerusalem 02:00):

  ```python
  from datetime import datetime
  from zoneinfo import ZoneInfo
  def test_hunting_starts_at_two():
      t = datetime(2026, 9, 7, 2, tzinfo=ZoneInfo('Asia/Jerusalem'))
      assert clocks.outside_reason(t) is None
      assert clocks.outside_reason(t.replace(hour=1, minute=59)) is not None
  ```

  Test exact 21:00 exclusion; Friday 21:30 preclose; Friday23/Sunday/Monday01;
  timezone-equivalent instants and DST, naive/missing time rejection. Golden matrix
  read outputs for synthetic rising/falling/mixed prices; source zero-volume VWAP
  fallback and NaN behavior. Quality named anchors vs shadow flag without veto.
  Swing needs three bars to the right. Audit mutations must independently corrupt
  a constant, function, order, dependency alias and clock specialization.
- [ ] Run `python -m pytest tests/tree_replay/test_admission_calculations.py tests/tree_spec/test_admission_source.py -q --tb=short`; record RED.
- [ ] Port only full required source definitions, preserving their AST except
  declared import/clock/fetch specialization. For read_frame, copy TFView constructor
  expression from read_tf, using its supplied df/tf/basis_note. Audit the expression
  against source rather than merely asserting that the new function exists.
  Pin complete ordered dependency closure and blobs. Do not execute live source.
- [ ] Run the same suite GREEN and the explicit-root source CLI; document edge
  behavior and scope. Self-review imports and no hidden source access.
- [ ] Write exchange result; parent generates task diff, independent spec/quality
  review, re-verifies and records acceptance before dependent binding work.

