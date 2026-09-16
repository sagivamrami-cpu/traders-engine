# Tracker lock policy implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans or superpowers:subagent-driven-development. Track checkbox steps.

**Goal:** Preserve original lock policy and reentrance for offline tracker callers.
**Architecture:** Complete original policy over explicit IO/time/acquisition ports;
one object per source process. Independent inert AST auditor; no fabricated lock
history or replacement of timeout with elapsed time.
**Tech Stack:** Python contextlib/ast/pytest, existing tracker admission.
**Spec:** docs/architecture/TRACKER-LOCK-SOURCE-CONTRACT.md

## Global constraints

- Existing pinned source and all its exception boundaries; no new thresholds.
- Existing dirty feature checkout, no commits/pushes/worktree changes/cleanup.
- apply_patch only; synthetic tests, no original program execution or OS locking.
- Main implements critical-path task inline; reviewers independent and no nesting.
- Existing user-approved architecture/continued implementation authority applies;
  no new domain choice. This closure does not assert causal full-loop readiness.

## Task1: Complete source policy and audit

Create `_vendor/tracker_lock.py` under trading_system/tree_replay;
`trading_system/tree_spec/tracker_lock_source.py`;
`tools/check_tracker_lock_source_parity.py`;
`tests/tree_replay/test_tracker_lock.py`, `tests/tree_spec/test_tracker_lock_source.py`;
`docs/architecture/TRACKER-LOCK-SOURCE-USAGE.md`.
Consumes actual TrackerAdmission.record via `source.locked`; produces
TrackerLock(source).locked and original LockBusy, with exact ports in spec.

- [x] Read original full _busy_for/_locked/filelock and existing source auditor;
  verify source HEAD/blob and baseline tracker tests.
- [x] Write tests with in-test missing-module assertion before runtime:
  ```python
  with policy.locked(skip_if_busy=True):
      events.append('body')
  # failed acquire, marker atT-120: body entered; no release; close always
  assert events[-2:] == ['body', 'close']
  ```
  Cover120/119.999, default/explicitwait, nested skip bypass, marker read/write/
  clear failures, open/acquire/body/release errors, depth restoration. Actual
  record consumer uses pre-acquire prices and post-acquire time/state.
- [x] Run `python -m pytest tests/tree_replay/test_tracker_lock.py -q --tb=short`
  observe missing-feature RED. Then port complete source bodies:
  ```python
  got = self.source.try_acquire(f, timeout=wait)
  if got:
      try:
          self.source.clear_busy()
      except Exception:
          pass
  ```
  Remaining flow is exact source; only external expressions are replaced.
- [x] Run runtime GREEN; inspect errors/cleanup and real-record ordering.
- [x] Write auditor mutation/identity/CLI tests; run
  `python -m pytest tests/tree_spec/test_tracker_lock_source.py -q --tb=short`
  RED before adding auditor. Adapt full-module audited projection pattern from
  tracker_storage_source; require source constants and original held initializer.
- [x] Implement independent exact substitution audit and CLI0/2; run
  `python -m pytest tests/tree_replay/test_tracker_lock.py tests/tree_spec/test_tracker_lock_source.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_io.py -q --tb=short`.
- [x] Run new CLI with explicit retained source parent and existing tracker audit;
  inspect full package and whitespace. Write usage/report and request task review.
- [x] Resolve findings using RED/GREEN, rerun applicable verification; final
  component review, acceptance and project memory. No inferred full-goal completion.

## Continuation

Bind policy to actual shared historical scheduler/ports, then caller and lifecycle.
Preserve master A-J; dataset/model and economic approvals remain separate gates.
