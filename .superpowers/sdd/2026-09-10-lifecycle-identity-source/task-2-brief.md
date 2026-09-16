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

## Task2: Complete source proof and final acceptance

Create `trading_system/tree_spec/lifecycle_identity_source.py`,
`tools/check_lifecycle_identity_source_parity.py`,
`tests/tree_spec/test_lifecycle_identity_source.py`.

- [ ] Missing-auditor RED and real graph case:
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
- [ ] Run `python -B -m pytest tests/tree_spec/test_lifecycle_identity_source.py -q --tb=short -p no:cacheprovider`; confirm normal RED.
- [ ] Implement full independent literal projection with exact-count scoped
  substitutions, comparing complete runtime AST including method signatures.
  Use actual `audit_tracker_admission_source(parentroot)` dependency. Match
  repo root/HEAD/baseline pin, normalize input failures into blockers.
- [ ] Add explicit-root CLI (argparse, JSON report, exit0 verified/2 blocked)
  and subprocess tests from unrelated cwd. Inert import guard rejects original
  chartdesk/floor and tree_replay imports while auditing retained source.
- [ ] GREEN `python -B -m pytest tests/tree_replay/test_lifecycle_identity.py tests/tree_spec/test_lifecycle_identity_source.py tests/tree_replay/test_tracker_admission.py -q --tb=short -p no:cacheprovider`;
  run `python -B tools/check_lifecycle_identity_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
  Record terminal results/hashes, independent task/final reviews and accepted
  scope in usage/master/tracker/AGENTS. Then gate/park/outbox source closure,
  actual resolver/caller and full causal provider work remain; no new labels.
