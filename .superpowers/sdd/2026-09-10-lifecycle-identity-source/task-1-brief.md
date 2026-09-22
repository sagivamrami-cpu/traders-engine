# Lifecycle identity and receipt source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Track checkboxes.

**Goal:** Compute original lifecycle matching, group receipt evidence and thread context from raw ports.
**Architecture:** Pure original text matching and one process-scoped receipt/thread reader; independent source projection and inherited identity proof.
**Tech Stack:** Python, pandas, pytest, AST; no live imports.
**Spec:** docs/architecture/LIFECYCLE-IDENTITY-SOURCE-CONTRACT.md

## Global constraints

- Existing feature checkout; main inline critical path and independent review
  sidecars. No commits/pushes/cleanup/unrelated changes or nested agents.
- chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9; tracker.py
  b616b34022e436545d8c1daf85eced51614fd74e; trade_threads.py
  b05cfcf45cb420c40254154e80d3792a7b1685b9. Original read/parse only.
- All exact interfaces/substitutions in spec are binding. Existing accepted
  modules unchanged, no supplied final match/receipt/context, no domain changes.
- Source receipt cache is per simulated process and depends on raw mtime only.
  No historical-feed, actual delivery, OS durability or economic label claim.

## Task1: Actual matching, receipt cache and thread reader

Create `trading_system/tree_replay/_vendor/lifecycle_identity.py`,
`tests/tree_replay/test_lifecycle_identity.py`,
`docs/architecture/LIFECYCLE-IDENTITY-SOURCE-USAGE.md`.

- [ ] Read both complete selected source groups and actual _trade_identity/
  canonicalization dependencies before edits; follow spec's source order and
  method signatures. Read intake for subsequent gate/caller distinctions.
- [ ] Lazy import RED and literal pure matching test:
  ```python
  name = 'trading_system.tree_replay._vendor.lifecycle_identity'
  assert importlib.util.find_spec(name) is not None, 'lifecycle identity missing'
  m = importlib.import_module(name)
  first = dict(symbol='OANDA:XAUUSD', direction='לונג', entry=110., stop=99.7,
               targets=[('target', 115.)], state='OPEN')
  second = dict(first, stop=98., targets=[('target', 116.)])
  trade, ambiguous = m._match_trade_for_text(
      '✅ XAUUSD BUY 110.00 · TP1 @ 115.00', {'first':first, 'second':second})
  assert trade is first and ambiguous == []
  ```
  Add literal cases for every matching/thread branch named in spec, including
  decimal regex, late identity, no load/clock on no-match and0.011 boundary.
- [ ] Raw receipt source fixture records stat/read/queue/load/clock operations;
  absent stat raisesOSError, text uses actual JSONL and logical queue text.
  Assert real geometry match, exact120second delivery slack, mtime0/unchanged/
  changed/error cache behavior and separate instances. Legacy queue test must
  use actual three-style geometry calculation, done/root ordering and malformed
  content rules. Include parsed malformed row error, not just invalid JSON.
- [ ] Run `python -B -m pytest tests/tree_replay/test_lifecycle_identity.py -q --tb=short -p no:cacheprovider`; confirm normal missingmodule RED.
- [ ] Inertly project selected source functions into pure helpers and class;
  add only constructor and exact port substitutions specified. Constructor:
  ```python
  def __init__(self, source):
      self.source = source
      self._receipt_cache = {'mtime': 0, 'keys': set()}
  ```
  Preserve source match precedence/cache behavior/errors and return types.
- [ ] GREEN `python -B -m pytest tests/tree_replay/test_lifecycle_identity.py tests/tree_replay/test_tracker_admission.py -q --tb=short -p no:cacheprovider`.
  Document required raw ports, process scope, unchanged cache semantics,
  limits and full task diff/hashes; independent spec/quality review.


