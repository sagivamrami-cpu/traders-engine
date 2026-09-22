# Causal quote and watch IO implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development. Track checkbox steps.

**Goal:** Feed original tracker quote/rejection reads and original watch logging
from causal supplied artifacts, retaining exact byte prefixes and source sessions.
**Architecture:** Typed seeds, read-only quote context, append-only chunked log,
source logger/session projections, independent inert source audit.
**Tech Stack:** Python stdlib/pandas/numpy, existing tracker/UTC helpers, pytest.
**Spec:** docs/architecture/CAUSAL-QUOTE-WATCH-IO-CONTRACT.md

## Global constraints

- Existing pinned source behavior, no new thresholds/aliases/data/notifications.
- Explicit publication/coverage/newline; no guessed empty history or quote price.
- Preserve unsorted source log bytes and all event kinds; no future reader exposure.
- No real files/network/wall clock at runtime. No source program executed in audit.
- Existing dirty feature checkout, no worktree change/commits/pushes/cleanup.
- apply_patch edits; independent reviewers do not dispatch nested agents.

## Task 1: Causal quote/log ports with actual source logger

Create trading_system/tree_replay/admission_io.py (ArtifactSeed/InputUnavailable/
CausalQuoteReader/CausalWatchLog and private chunk reader/backend);
_vendor/watch_io.py (WatchLogger), _vendor/watch_sessions.py (source session
mask/current_session_at), trading_system/tree_spec/watch_io_source.py (auditor),
tools/check_watch_io_source_parity.py (CLI), tests/tree_replay/test_admission_io.py,
tests/tree_spec/test_watch_io_source.py and docs/architecture/CAUSAL-QUOTE-WATCH-IO-USAGE.md.
No accepted runtime/manifest edits. Consumes bars._utc/state._identity, existing
map_sessions tables, tracker_admission._tail_reader/_recent_rejection/_live_prices.
Produces exact interfaces in spec; newline is required LF/CRLF, log advance only.

- [x] Read full source session_mask/current_session/_log and next-input intake;
  run existing tracker/storage/frame baseline tests before adding runtime.
- [x] Write behavioral tests with in-test missing-module assertion; literal quote
  age420accepted/420.001rejected and log at2026-09-09T16Z expected sessionsnewyork.
  ```python
  log = make_log(status="ABSENT", newline="LF")
  row = {"kind": "rejection"}
  log.log(row)
  assert row == {"kind": "rejection", "sessions": ["newyork"]}
  assert log.snapshot().content == b'{"ts": 1788969600.0, "kind": "rejection", "sessions": ["newyork"]}\n'
  ```
  Add all spec families, real original quote/born and raw rejection consumers.
- [x] Run `python -m pytest tests/tree_replay/test_admission_io.py -q --tb=short`
  and observe missing-feature RED. Implement only after that evidence.
- [x] Add private source projections, required source-clock adaptation and typed
  contexts. Source log shape remains:
  ```python
  row.setdefault("sessions", sorted(self.source.current_session()))
  self.source.ensure_out()
  with self.source.event_log_writer() as f:
      f.write(json.dumps({"ts": self.source.now_epoch(), **row}, ensure_ascii=False)+"\n")
  ```
  Append opens/creates before serialization. Keep log coverage guard at artifact
  open, not before independent session calculation. Quote failures stay traced.
- [x] Add append chunks with cumulative ends; reader captures current size, uses
  bisect/seek/read without full join at open. advance_to reuses chunk storage,
  rejects backwards/invalid/expired times atomically; snapshot is explicit full export.
- [x] Run focused GREEN; review prefix mutation, newline/torn-byte and source catch cases.
- [x] Write auditor tests first; real source verification, wrong commit/blob,
  changed logger order/clock/serialization/session table/extra code must block.
  Run `python -m pytest tests/tree_spec/test_watch_io_source.py -q --tb=short` RED.
- [x] Implement auditor/CLI0verified/2blocked. Exact substitutions, complete module
  comparison, explicit retained source parent and baseline pin. Inherit no mutable
  manifest as source authority. Audit current map_sessions full original projection.
- [x] Run `python -m pytest tests/tree_replay/test_admission_io.py tests/tree_spec/test_watch_io_source.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_frames.py -q --tb=short`.
- [x] Run new watch IO audit and existing tracker admission audit with explicit
  retained-source-parent; confirm false readiness. Inspect diffs/whitespace.
- [x] Self-review/report/usage, independent task and final reviews, acceptance.

## Full-plan continuation

Original source lock/caller order and full watch state/lifecycle remain next,
then all producers, execution outcomes, dataset/models/evaluation. No narrowed goal.
