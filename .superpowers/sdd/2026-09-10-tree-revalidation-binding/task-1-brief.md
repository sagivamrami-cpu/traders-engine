# Actual tree pending-revalidation binding implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Track checkboxes.

**Goal:** Aged pending revalidation consumes the actual tree and matrix on raw inputs.
**Architecture:** Original two matrix reader functions plus a narrow shared raw-port
facade composing accepted readers outside their source modules, with complete proof.
**Tech Stack:** Python/pandas/pytest/AST.
**Spec:** docs/architecture/TREE-REVALIDATION-BINDING-CONTRACT.md

## Global constraints

- Existing approved feature checkout; no commits/pushes/cleanup/unrelated changes.
  Main inline critical path and independent review sidecars; no nested agents.
- Finish complete tree component's pending final acceptance before binding it.
- chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9; matrix.py
  28641487567c457b6922c2a63055659867bb4248. Original source read/parse only.
- No provider-final Walk/matrix/broker verdicts, altered trading rules, cached
  operation times, economic labels, data acquisition or live actions.
- Accepted tree/revalidation/basis/matrix source modules and public fixed-T
  adapters unchanged. New composition stays explicitly not causal-certified.

## Task1: Actual matrix/tree -> pending revalidation

Create `trading_system/tree_replay/_vendor/matrix_reader.py`, `trading_system/tree_replay/tree_revalidation.py`,
`tests/tree_replay/test_tree_revalidation.py`, and
`docs/architecture/TREE-REVALIDATION-BINDING-USAGE.md`.

- [ ] Read pinned matrix.read_tf/read_symbol in full and the actual
  admission_matrix.read_frame/LOOKBACK, BasisOperation, Revalidation and TreeReader
  contracts. New MatrixReader methods consume the same raw provider and preserve
  full source order; no separate synthesized TFView supplied by the fixture.
- [ ] Write lazy import RED. A raw provider can raise for the first fetch; the
  actual bound tree then produces a DATA stop, consumed by original _tree_agrees:
  ```python
  name = 'trading_system.tree_replay.tree_revalidation'
  assert importlib.util.find_spec(name) is not None, 'tree binding missing'
  bound = importlib.import_module(name).TreeRevalidation(source)
  assert source.calls == []
  ok, why = bound.checks._tree_agrees('OANDA:XAUUSD', 'לונג')
  assert ok and why == 'העץ נעצר ב-DATA: אין נתונים (LookupError)'
  ```
  Test raw matrix reads via literal rising/falling/neutral OHLCV and source
  correction rendering. Assert actual TFView directions, timeframe order and
  LOOKBACK requests, None/malformed correction/error behavior, no history trimming.
- [ ] Build full raw fixture from the documented tree/revalidation fixture recipes;
  helper reuse is allowed for raw rows only, never derive expected outputs with
  code under test. Supply every required freshness3/EMA2000/structure400/vector60
  request, daily400 and actual tree/map requests. Raw shadow_open uses an in-memory
  context manager with ordered open/write/close trace; raw news JSON has a future
  low-impact row. Final provider tree_walk/read_symbol/broker_shape_ok raise if used.
  ```python
  trade = dict(symbol='OANDA:XAUUSD', direction='לונג', entry=110., stop=99.7,
               ts=now.timestamp()-7200, bias_at_send={'4h':0.,'1h':0.})
  ok, reason, verified = bound.revalidate_pending(trade, now=now.timestamp())
  assert ok and verified and 'העץ מאשר' in reason
  ```
  Preserve neutral-at-send metadata to isolate tree opposition from an earlier
  bias-flip veto; separately test the genuine earlier veto. Matching/opposing
  raw ladder, age7199.999/7200, stopped news/data/map, opposite-before-stop and
  unavailable-still_valid flags must use actual consumers. Assert no input-trade
  mutation and no Plan/fill/label. Separate default/explicit clocks and shadow IO.
- [ ] Run `python -B -m pytest tests/tree_replay/test_tree_revalidation.py -q --tb=short -p no:cacheprovider`; confirm normal missing-module RED.
- [ ] Inertly project matrix methods exactly as spec; two actual pure functions
  remain reused. Implement TreeRevalidation(BasisOperation) with inert composition:
  ```python
  def __init__(self, source):
      super().__init__(source)
      self.matrix = MatrixReader(source)
      self.tree = TreeReader(source)
      self.checks = Revalidation(self)
  def tree_walk(self, symbol):
      return self.tree.walk(symbol)
  def read_symbol(self, symbol, tfs=('4h','1h','15m','5m')):
      return self.matrix.read_symbol(symbol, tfs=tfs)
  def revalidate_pending(self, t, *, now=None):
      return self.checks.revalidate_pending(t, now=now)
  ```
  Implement still_valid as exact delegate and the eight explicit raw forwarders
  enumerated in spec; inherited fetch/UTC/shape stay actual BasisOperation.
- [ ] GREEN `python -B -m pytest tests/tree_replay/test_tree_revalidation.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_revalidation.py tests/tree_replay/test_admission_frames.py -q --tb=short -p no:cacheprovider`.
  Document limitations, full diff/hashes and independent task spec/quality review.


