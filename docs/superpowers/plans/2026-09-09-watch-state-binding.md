# Causal watch-state persistence implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans or superpowers:subagent-driven-development. Track checkbox steps.

**Goal:** Preserve original heterogeneous watch-state load and both save boundaries.
**Architecture:** A small audited source projection delegates completed in-memory
IO to causal text guards with optional accepted shared clock. Caller st and saved
image stay separate; no source policy changes or full-loop claims.
**Tech Stack:** Python dataclasses/json/ast, existing guard/clock, pytest.
**Spec:** docs/architecture/WATCH-STATE-BINDING-CONTRACT.md

## Global constraints

- Existing approved feature checkout; preserve dirty changes, no worktree move.
- Exact source commit/blob/IO semantics; no live files/network or invented rules.
- All edits apply_patch. No commits, cleanup, real-data labels or training.
- Main critical-path implementation inline; independent reviewers write reports
  only. Full master A-J and currently pending admission-context acceptance remain.

## Task1: Original persistence and causal artifact

Create trading_system/tree_replay/_vendor/watch_storage.py and
trading_system/tree_replay/watch_storage.py; tests/tree_replay/test_watch_storage.py;
docs/architecture/WATCH-STATE-BINDING-USAGE.md. Interfaces exactly match the spec.

- [x] Write tests then run normal RED for missing module, not collection errors:
  ```python
  s = store('{"cooldown": 7, "episode": {"ts": 8}, "remove": true}')
  working = s.load()
  working.pop("remove")
  working["cooldown"] = 9
  assert s.load()["cooldown"] == 7
  s.save_before_producers(working)
  assert s.snapshot().text == '{"cooldown": 9, "episode": {"ts": 8}}'
  ```
  Cover null/list/scalar roots, root insertion order and Unicode escaping, all
  temporal/status failures, >half deletion, unsaved post-first-save changes,
  invalid serialization and first/final directory effect difference, shared
  clock binding/persistence/expiry and detached trace/snapshot restore.
- [x] Project exact source statements into WatchStorage, using `self.source`
  exists/read_text/ensure_directory/write_text. Add backend using accepted call
  guards; direct write updates text/status only after UTF8 validation. Wrap
  source load/saves for outer error trace and validate exact WatchStateSeed/clock.
- [x] Run `python -m pytest tests/tree_replay/test_watch_storage.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_shared_clock.py -q --tb=short`;
  write usage/report/full new-file package and request independent Task1 review.

## Task2: Independent source audit and integration acceptance

Create trading_system/tree_spec/watch_storage_source.py,
tools/check_watch_storage_source_parity.py and tests/tree_spec/test_watch_storage_source.py.

- [x] Write normal RED source tests (module missing), drift mutations and CLI:
  ```python
  report = api().audit_watch_storage_source(SOURCE)
  assert report["status"] == "VERIFIED"
  assert report["checked_projections"] == ["watch.load", "watch.save_before_producers", "watch.save_final"]
  assert not report["ready_for_training"]
  ```
  Source mutation, wrong HEAD/baseline, missing source/runtime, extra imports,
  default JSON changes, lost mkdir, swapped/omitted save/load body must be blocked.
- [x] Extract unique main then exact top-level load assign and both identical
  write expressions; require first immediately preceded by mkdir and second
  final write before return0. Port replacements only, expected full module AST.
  Pin independent commit/blob; compare normalized whole candidate with no extra
  code. CLI calls audit and exits according to source_subset_verified.
- [x] Run focused tests then `python -m pytest tests/tree_replay/test_watch_storage.py tests/tree_spec/test_watch_storage_source.py tests/tree_replay/test_admission_context.py tests/tree_replay/test_shared_clock.py tests/tree_replay/test_tracker_storage.py -q --tb=short`.
  Run CLI against retained parent; inspect diff/whitespace. Independent task and
  combined final review; fixes require RED/GREEN, record acceptance/memory.

## Continuation

Full separate watch lock/caller and generated tracker lifecycle, mixed-time
producer IO, other branches, economics/coverage/dataset/models/evaluation. A
successful state component does not itself satisfy these remaining requirements.
