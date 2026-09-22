# Shared causal admission context implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans or superpowers:subagent-driven-development. Track checkbox steps.

**Goal:** Bind real accepted tracker consumers to shared-time causal providers.
**Architecture:** Optional shared clock preserves standalone APIs; an in-memory
coordinator applies ordered publications and explicit lock-operation evidence.
**Tech Stack:** Python dataclasses/datetime, accepted source projections, pytest.
**Spec:** docs/architecture/CAUSAL-ADMISSION-CONTEXT-CONTRACT.md

## Global constraints

- Keep all original source functions/thresholds and existing API defaults unchanged.
- Exact symbols, microsecond UTC, no invented history/acquisition/elapsed times.
- No live IO/data, commits, cleanup or worktree changes; apply_patch edits.
- Current approved feature checkout, main critical-path implementation inline;
  independent task/final reviewers use disjoint report write sets, no nesting.
- Full master A-J remains; this is not complete caller/checkpoint/training.

## Task1: Shared clock and compatible artifact bindings

Create trading_system/tree_replay/clock.py and tests/tree_replay/test_shared_clock.py.
Document optional API in docs/architecture/SHARED-REPLAY-CLOCK-USAGE.md.
Modify trading_system/tree_replay/tracker_storage.py and admission_io.py only to
add optional exact shared clock, leaving standalone behavior intact.

- [x] Read accepted implementations, run existing artifact baseline tests.
- [x] Write failing behavior tests before implementation:
  ```python
  clock = ReplayClock(T)
  storage = CausalTrackerStorage(seed=seed, decision_time=T, clock=clock)
  storage.save({'x': {'state': 'PENDING'}})
  clock.advance_to(T + timedelta(seconds=2))
  assert storage.load() == {'x': {'state': 'PENDING'}}
  assert storage.snapshot().available_at == T + timedelta(seconds=2)
  ```
  Include quote/log source timestamps and freshness, reader isolation, rejected
  bindings/backward/precision, unavailable data after independent clock advance,
  unchanged standalone behavior and shared log.advance coverage boundary.
- [x] Run `python -m pytest tests/tree_replay/test_shared_clock.py -q --tb=short`
  RED, then implement ReplayClock and optional constructors/properties. Artifact
  backend reads clock.now dynamically; no per-tick snapshot copying or state reset.
- [x] Run tests plus test_tracker_storage/test_admission_io/test_admission_frames;
  source audits remain unchanged. Report/package and independent task review.

## Task2: Ordered publications, lock evidence and full provider composition

Create trading_system/tree_replay/admission_context.py,
tests/tree_replay/test_admission_context.py and
docs/architecture/CAUSAL-ADMISSION-CONTEXT-USAGE.md. Consume Task1 ReplayClock and
exact accepted providers/source classes; expose CausalAdmissionContext with
tracker, pass_anchor, decision_time, advance_to, report and source port methods.
BusyMarkerSeed/Publication/LockStep provide exact contracts from the spec.

- [x] Write behavioral tests using real existing frame fixture construction and
  original Plan/TrackerAdmission; no synthetic net-score stubs. First RED must
  fail for the missing context module, not an import/fixture error.
  ```python
  assert context.tracker.record(plan)
  assert context.pass_anchor == T
  assert context.decision_time == T + timedelta(seconds=2)
  assert next(iter(context.load().values()))['ts'] == (T + timedelta(seconds=2)).timestamp()
  ```
  Table-driven schedules cover external OPEN arriving during acquire (record
  false), unavailable inputs, strict step names/times/timeout, cleanup/failures,
  same-time publication ordering and prior-reader/state preservation.
- [x] Run `python -m pytest tests/tree_replay/test_admission_context.py -q --tb=short`
  RED; implement validated in-memory coordinator and explicit lock ports.
- [x] Run focused GREEN and self-review mutation boundaries: future data, wrong
  sequence, loss of generated state, stale clock, hidden caught failures.
- [x] Run `python -m pytest tests/tree_replay/test_admission_context.py tests/tree_replay/test_shared_clock.py tests/tree_replay/test_tracker_lock.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_admission_frames.py -q --tb=short`.
- [x] Run unchanged tracker/storage/watch/lock source audit CLIs against retained
  parent; inspect diffs/whitespace, write usage/report and task review package.
- [x] Resolve review findings with RED/GREEN; independent final combined review,
  acceptance and memory/tracker update. No whole-goal completion claim.

## Continuation

Original watch caller/state/resolver lifecycle and mixed-clock producer binding,
then full remaining branches and economic/dataset/model/evaluation requirements.
