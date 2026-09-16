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

- [x] Read both complete selected source groups and actual _trade_identity/
  canonicalization dependencies before edits; follow spec's source order and
  method signatures. Read intake for subsequent gate/caller distinctions.
- [x] Lazy import RED and literal pure matching test:
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
- [x] Raw receipt source fixture records stat/read/queue/load/clock operations;
  absent stat raisesOSError, text uses actual JSONL and logical queue text.
  Assert real geometry match, exact120second delivery slack, mtime0/unchanged/
  changed/error cache behavior and separate instances. Legacy queue test must
  use actual three-style geometry calculation, done/root ordering and malformed
  content rules. Include parsed malformed row error, not just invalid JSON.
- [x] Run `python -B -m pytest tests/tree_replay/test_lifecycle_identity.py -q --tb=short -p no:cacheprovider`; confirm normal missingmodule RED.
- [x] Inertly project selected source functions into pure helpers and class;
  add only constructor and exact port substitutions specified. Constructor:
  ```python
  def __init__(self, source):
      self.source = source
      self._receipt_cache = {'mtime': 0, 'keys': set()}
  ```
  Preserve source match precedence/cache behavior/errors and return types.
- [x] GREEN `python -B -m pytest tests/tree_replay/test_lifecycle_identity.py tests/tree_replay/test_tracker_admission.py -q --tb=short -p no:cacheprovider`.
  Document required raw ports, process scope, unchanged cache semantics,
  limits and full task diff/hashes; independent spec/quality review.

## Task2: Complete source proof and final acceptance

Create `trading_system/tree_spec/lifecycle_identity_source.py`,
`tools/check_lifecycle_identity_source_parity.py`,
`tests/tree_spec/test_lifecycle_identity_source.py`.

- [x] Missing-auditor RED and real graph case:
  ```python
  r = api().audit_lifecycle_identity_source(SOURCE)
  assert r['source_subset_verified'] and r['blockers'] == []
  assert not r['ready_for_replay'] and not r['ready_for_training']
  ```
  Source mutations cover each blob/signature/missing/duplicate/ordered symbol
  and substitution count. Candidate mutations cover cache scope/mtime/delivery
  slack, matching order, context tolerance/clock/load, pure imports and constructor.
  Actual inherited _trade_identity drift must block, not only a fake child error.
  Child falseempty/trueblocked/OSError/StopIteration report blocked.
- [x] Run `python -B -m pytest tests/tree_spec/test_lifecycle_identity_source.py -q --tb=short -p no:cacheprovider`; confirm normal RED.
- [x] Implement full independent literal projection with exact-count scoped
  substitutions, comparing complete runtime AST including method signatures.
  Use actual `audit_tracker_admission_source(parentroot)` dependency. Match
  repo root/HEAD/baseline pin, normalize input failures into blockers.
- [x] Add explicit-root CLI (argparse, JSON report, exit0 verified/2 blocked)
  and subprocess tests from unrelated cwd. Inert import guard rejects original
  chartdesk/floor and tree_replay imports while auditing retained source.
- [x] GREEN `python -B -m pytest tests/tree_replay/test_lifecycle_identity.py tests/tree_spec/test_lifecycle_identity_source.py tests/tree_replay/test_tracker_admission.py -q --tb=short -p no:cacheprovider`;
  run `python -B tools/check_lifecycle_identity_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
  Record terminal results/hashes, independent task/final reviews and accepted
  scope in usage/master/tracker/AGENTS. Then gate/park/outbox source closure,
  actual resolver/caller and full causal provider work remain; no new labels.
