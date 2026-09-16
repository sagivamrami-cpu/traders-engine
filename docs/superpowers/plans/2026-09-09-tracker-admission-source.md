# Tracker admission source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Track steps with checkboxes.

**Goal:** Execute original tracker admission/recording through offline ports,
with independent source parity, as a dependency of full causal producer binding.
**Architecture:** Per-instance original-source method projection; explicit time,
state/lock, frame, full-log and quote ports. Keep decisions and all source catches.
**Tech Stack:** Python, pandas, stdlib BytesIO/dataclasses/json/AST, pytest.
**Spec:** docs/architecture/TRACKER-ADMISSION-SOURCE-CONTRACT.md

## Global Constraints

- Pin chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 and trading-floor d827dd792cbd1d396b4ee325879c63e57388e07a.
- Never import/execute retained live source. No network, market-data download, broker, Telegram, live state reads or training.
- Keep original exception behavior, but do not equate a swallowed dependency failure with verified replay readiness.
- Original advisory state is not economic TP1 state; quality/anchor/rejection telemetry is not a new veto.
- Preserve dirty existing in-place branch. No commits, pushes, new worktree, cleanup or edits to prior accepted runtime files.
- All edits via apply_patch. Source tests synthetic; mandatory source-root evidence never silently skipped.

## Task 1: Complete source gate and recording closure

**Files:** Create trading_system/tree_replay/_vendor/tracker_admission.py,
trading_system/tree_replay/_vendor/tracker_symbols.py,
trading_system/tree_spec/tracker_admission_source.py,
configs/trees/tracker-admission-source-contracts.json,
tools/check_tracker_admission_source_parity.py,
tests/tree_replay/test_tracker_admission.py,
tests/tree_spec/test_tracker_admission_source.py,
docs/architecture/TRACKER-ADMISSION-SOURCE-USAGE.md.

**Consumes:** Full spec named above, pinned tracker.py, tradeplan.py, symbols.py,
accepted private pricing/basis_symbols/admission_quality/admission_swing modules.
Confirm exactly required inherited definitions and imports from source, rather
than assume passing unrelated audits cover this closure. Existing source patterns
are in trading_system/tree_spec/admission_source.py. Do not edit that auditor.

**Produces:** TrackerAdmission(source) and all methods/ports in spec; pure
_tail_reader, _tail_bytes, _trade_identity, _anchor_names, thesis_verdict; source symbols
resolve closure; audit_tracker_admission_source(source_root)->dict with
status/source_subset_verified/blockers and false ready_for_replay/training;
explicit --source-root CLI. Source is a per-instance offline port object, never
a class that discovers files/services from the host environment.

- [x] Write real behavioral failing tests. Start with exposure and actual record
  mutations, then post-stop and raw-log cases. Representative fixtures:

  ```python
  class MemoryPorts:
      def __init__(self, rows):
          self.rows = deepcopy(rows)
          self.calls = []
      def load(self):
          self.calls.append('load')
          return deepcopy(self.rows)
      def save(self, rows):
          self.calls.append('save')
          self.rows = deepcopy(rows)
      def now_epoch(self):
          return 1788775200.0
      def locked(self):
          return nullcontext()
      def event_log_reader(self):
          return BytesIO(b'')
      def quote_payload(self):
          return {}
      def read_symbol(self, symbol, tfs):
          self.calls.append(('matrix', symbol, tfs))
          return {tf: SimpleNamespace(net=0.0, bar_ts=1788775200.0) for tf in tfs}
      def fetch_corrected(self, symbol, timeframe, lookback_days):
          self.calls.append(('frame', symbol, timeframe, lookback_days))
          return pd.DataFrame(columns=['open','high','low','close','volume']), None

  def test_pending_is_not_open_exposure():
      ports = MemoryPorts({'x': {'state':'PENDING'}})
      tracker = TrackerAdmission(ports)
      assert tracker.has_open('OANDA:XAUUSD', 'לונג') is False
      ports.rows['x'] = {'state':'OPEN', 'symbol':'OANDA:XAUUSD', 'direction':'לונג'}
      assert tracker.has_open('OANDA:XAUUSD', 'לונג') is True

  def test_expired_stop_does_not_request_structure():
      ports = MemoryPorts({'x': {'symbol':'OANDA:XAUUSD', 'direction':'לונג',
          'state':'STOPPED', 'ts':1788760000.0, 'resolved_ts':1788760800.0, 'stop':90.0}})
      assert TrackerAdmission(ports).blocked_after_stop('OANDA:XAUUSD','לונג') is None
      assert ports.calls == ['load']
  ```

  Fixture imports deepcopy/nullcontext/BytesIO/SimpleNamespace/pandas belong in tests.
  Add opposite sides at exact +/-25 bias, just below/at4hours, actual swing with
  right confirmation and insufficient8rows, entry beyond old stop by0.01 with
  attachment and unchanged/absent anchors. Same-level7200boundary and bandedges;
  corrupt/missing fields, epoch quirks preserve actual source outcomes.
  For record use pricing.Plan with complete geometry: pending creation, born
  open with explicit unverified flags, duplicate pending refusal, geometry/style
  differences, resolved archive, rechecked OPEN, raised save failure.
  Assert stored source rows, not only return values. Assert matrix before lock
  and current state reloaded in lock using a controlled changing-state port.
  Quote age0/420/420+epsilon/future, missing/stale/external-band one-sided cases.
  Tail full bytes with tiny window and huge last line, malformed trailing JSON,
  non-rejection bytes ejecting old evidence, equal timestamps retaining first,
  exact max-age and gap-boundary selection. Missing-source files must yield
  descriptive failure rather than collection crash/skip.
- [x] Run `python -m pytest tests/tree_replay/test_tracker_admission.py tests/tree_spec/test_tracker_admission_source.py -q --tb=short`; preserve RED before implementation.
  Historical RED used prior colliding filename/importlib workaround; exact
  evidence retained in worker report. New name runs in default mode.
- [x] Port entire named definitions, not paraphrased decisions. Class adaptation:

  ```python
  class TrackerAdmission:
      def __init__(self, source):
          self.source = source
      # Each named source function is copied as a method, adds self, and uses
      # exactly the spec's explicit port/internal-call substitutions.
  ```

  Retain original seek/read tail with a reader factory; opening errors stay
  caught inside _tail_reader. _tail_bytes wraps a BytesIO factory for small
  fixtures only. Add a read/seek spy over a multi-window prefix proving the
  ordinary case consumes at most the original tail window, not the full prefix;
  independently verify output bytes. Keep original lock
  boundary through source.locked(). No runtime AST exec/generation. Auditor
  parses inert source, applies separately enumerated exact transformations,
  compares whole ordered output/imports and inherited dependencies. Verify every
  expected removed/replaced source statement exists; unexpected source shape
  blocks, never silently removes arbitrary imports or exception bodies.
  Verify source blobs, repo roots/commits and fixed independent manifest authority.
- [x] Run focused GREEN, then full two-file suite and
  `python tools/check_tracker_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
  Mutation tests change gate boundary/call order, source blob/pin, injected port
  target, dependent pip/pricing/quality/swing body and narrowed manifest. Hidden
  I/O test runs only the new private closure with supplied memory ports.
- [x] Self-review, document exact interfaces/source quirks and unfinished full
  binding. Write task report with commands/counts/RED/GREEN and concerns. No commit.
- [x] Parent packages full diff, dispatches independent task spec/quality review,
  reruns applicable commands, records acceptance. No dependency binding before
  Critical/Important issues are resolved.

## Component completion and full-plan continuation

- [x] Full component review, including inherited source closure and false readiness.
- [x] Update source usage, master tracker and exchange acceptance with exact scope.
- [ ] Continue to causal gate/record binding and original full-log state generation;
  other producers/lifecycle/simulation/dataset/model remain mandatory master work.
