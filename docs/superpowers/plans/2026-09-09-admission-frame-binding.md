# Causal admission frame binding implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Track checkbox steps.

**Goal:** Drive original admission matrix/swing frame reads from actual causal bars.
**Architecture:** Typed original request pairs over accepted _OfflineSource;
original ordered matrix calculations, per-call missing/error traces, no I/O.
**Tech Stack:** Python, pandas, existing FrameSpec/correction/matrix, pytest.
**Spec:** docs/architecture/ADMISSION-FRAME-BINDING-CONTRACT.md

## Global Constraints

- Preserve pinned chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 behavior.
- No live imports, network, downloads, source threshold changes or GC spot alias.
- Source matrix has no producer correction veto or closed-target-only filter.
- LOOKBACK identifies requests, not guaranteed delivered days; no implicit trim/backfill.
- Missing or failed data remains traced through tracker catches; no ready/approved claim.
- Existing dirty checkout/feature branch stays in place. No commits/pushes/cleanup.
- File edits via apply_patch; implementer/reviewer may not spawn subagents.

## Task 1: Actual causal frame and matrix provider

**Files:** Create trading_system/tree_replay/admission_frames.py,
tests/tree_replay/test_admission_frames.py,
docs/architecture/ADMISSION-FRAME-BINDING-USAGE.md.
Do not change MapFrameRequest, _OfflineSource, FrameSpec, correction or source vendors.

**Consumes:** FrameSpec/build_frame_asof, CorrectionEvidence, _OfflineSource,
_DataUnavailable; private admission_matrix.LOOKBACK/read_frame and Correction.
Actual TrackerAdmission consumers and selected-Plan handoff are integration clients.
**Produces:** AdmissionFrameRequest and AdmissionFrameSource exact interfaces in
spec, read_symbol/fetch_corrected, fetch_trace/matrix_trace. No report hash API.

- [x] Read contract and latest source intake depth/ordering section; inspect
  actual matrix.read_tf/read_symbol inert pinned source, existing _OfflineSource
  and admission_matrix.read_frame. Source source-files are never executed.
- [x] Build new synthetic request fixtures from ClosedBar, SessionSchedule and
  FrameSpec. Characterize an independently audited source matrix fixture before
  provider implementation, recording literal tool reads/net/ATR/bar_ts as expected
  values. Use explicit grids and history_start, not pretended240day history.
- [x] Write behavioral RED tests using in-test module lookup so missing module
  fails tests rather than stopping collection. Core real-data-flow assertion:
  ```python
  source = module().AdmissionFrameSource(
      instrument=SYMBOL, decision_time=T, requests=requests)
  views = source.read_symbol(SYMBOL, ("4h", "1h"))
  assert list(views) == ["4h", "1h"]
  assert [(r["timeframe"], r["lookback_days"]) for r in source.fetch_trace] == [
      ("4h", 240), ("1h", 240)]
  assert views["4h"].close == 100.0  # constant-price fixture
  assert views["4h"].atr == 4.0     # high102, low98, prior close100
  ```
  Include numeric source tool/net literals from the characterized fixture so
  replacing calculations with a constant cannot pass. Exercise distinct15m55
  and15m5 frames with different known last closes and both fetch traces.
- [x] Run `python -m pytest tests/tree_replay/test_admission_frames.py -q --tb=short`
  and record expected missing-feature RED before adding runtime.
- [x] Implement exact immutable request validation and source initialization,
  validating all bindings before lazy calls. Keep new allowed key set distinct
  from map keys; source class delegates causal fetching to accepted machinery.
  Ordered matrix control-flow shape:
  ```python
  def read_symbol(self, symbol, tfs=("4h", "1h", "15m", "5m")):
      return {tf: self._read_tf(symbol, tf) for tf in tfs}

  def _read_tf(self, symbol, tf):
      trace = {"timeframe": tf, "fetch_index": len(self.fetch_trace),
               "status": "BLOCKED", "blocker": None, "exception_type": None}
      self.matrix_trace.append(trace)
      try:
          frame, corr = self.fetch_corrected(symbol, tf, matrix.LOOKBACK[tf])
          note = corr.render() if corr.show else None
          result = matrix.read_frame(frame, tf, note)
      except Exception as exc:
          trace["blocker"] = (str(exc) if isinstance(exc, _DataUnavailable)
                              else "MATRIX_CALCULATION_ERROR")
          trace["exception_type"] = type(exc).__name__
          raise
      trace["status"] = "AVAILABLE"
      return result
  ```
  Use explicit subclass/composition of _OfflineSource, preserve all inherited
  fetch evidence and actual-T closed-base-prefix=True. Constructor validation
  rejects unsupported instruments and duplicate identities. A source method
  request for another instrument must raise and leave an error trace, so a
  tracker catch cannot erase that unexpected binding failure. Direct missing
  requests are traced by inherited fetch. Do not swallow failures or return
  partial matrix mappings, and do not insert a new source unverified veto.
- [x] Cover typed invalid bindings, wrong timeframe/key, wrong instrument, missing
  first tf with no later fetch, default tf ordering, repeated reads and detached
  frame/view mutation. All six key pairs must be exercised through real fetches.
- [x] Cover delayed/future/stale/missing correction, assessed none/unknown and
  none/n-a reaching calculation, corr.show/render notes, missing expected bars,
  forming target row from closed base prefix, original bar_ts, future-only input
  invariance and submicrosecond rejection. Keep source NaN quirks explicit, not
  transformed into a new score/veto. Future values must never enter readings.
- [x] Add real TrackerAdmission higher-bias/thesis integration and actual post-stop
  frame-path scenario. Test-only state/quote/log ports delegate frame methods to
  this provider; do not supply precomputed net scores. Assert original outputs,
  actual request order and source caught-error trace. Inject a named matrix
  numerical error only for the error case, asserting _higher_bias returnsNone
  while provider still reports that failed calculation. No full admission claim.
- [x] Run `python -m pytest tests/tree_replay/test_admission_frames.py tests/tree_replay/test_admission_calculations.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_reversal_handoff.py tests/tree_replay/test_frames.py tests/tree_replay/test_corrections.py -q --tb=short`.
  Confirm filenames exist before running; if a named file differs, record the
  exact corrected command rather than silently omitting coverage.
- [x] Run `python tools/check_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
  This verifies inherited original formulas; also inspect the thin read_tf port
  against source order in review. Do not infer source parity from tests alone.
- [x] Self-review and report commands/RED/GREEN/limits, then independent task and
  full component review. Record acceptance before whole caller uses this provider.

## Subsequent full-plan work

Remaining tracker ports need bounded advisory state, lock/save, causal quotes and
lazy exact raw-log prefixes. Full watch state includes scalar/object/deletion
and original persistence boundaries. Preserve branch-specific caller ordering,
advisory lifecycle and separate economic TP1 simulation. Complete all producers,
dataset coverage/labels/model/evaluation; this provider does not close master C.
