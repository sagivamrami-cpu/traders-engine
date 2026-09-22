# Task 1 review — tracker lifecycle caller

Request: `docs/superpowers/plans/2026-09-14-tracker-lifecycle-caller-source.md`, Task 1.

## Verdict

**Spec compliance: NEEDS_REVISION. Task quality: NEEDS_FIXES.**

Critical finding: `TrackerLifecycleCaller` constructs a separate
`TrackerLock(source)` even though `CausalAdmissionContext` already owns the
process-shared lock policy and exposes `source.locked()`. As `TrackerLock.held`
is instance-local, the live caller can lose the source reentrant section and
incorrectly attempt/acquire a second lock. See
`trading_system/tree_replay/lifecycle_caller.py:11`,
`trading_system/tree_replay/admission_context.py:144,243`, and
`trading_system/tree_replay/_vendor/tracker_lock.py:14`.

Required fix: route the live wrapper through `source.locked(skip_if_busy=True)`
and add an integration regression showing a caller inside an existing source
lock reuses the same policy without second acquire. Do not broaden scope.

Reviewer also noted that broad `except LockBusy` can return `[]` if a callback
raises that exception. Ruling: retain it and document/test it if relevant: the
pinned public source wrapper has the same broad `try/with/except LockBusy`
boundary. Changing it would be a source-semantic change, not a caller fix.

## Re-review

The lock fix is correct: current `check_live` calls `source.locked`, and the
nested regression proves one acquisition. Two medium findings remain before
acceptance: update the contract's stale claim that caller owns a new
`TrackerLock`, and explicitly document plus regress the intentional broad
`LockBusy` catch for a callback-raised `LockBusy`.
