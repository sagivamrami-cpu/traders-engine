# Independent Review — Closed-Bar Causal Replay, Task 1

Status: CHANGES_REQUESTED

Scope reviewed: the Task 1 brief/report, approved plan and design, and the full
untracked `causal_replay_contracts.py` and focused test file. No retained source
was executed and no Task 1 file was modified.

## Critical findings

- **C1 — forbidden economic/outcome fields can be hidden outside `candidate`.**
  `_contains_forbidden_candidate_field()` is applied only to `candidate`
  (`trading_system/tree_replay/causal_replay_contracts.py:300-307`).
  `ReplayPassRecord.diagnostics` merely canonicalizes arbitrary nested mappings
  (`:320-329`), and `ReplayEvent.payload` does the same (`:176-181`). A direct
  probe accepted both `diagnostics=({'trace': {'net_pnl': 1}},)` and
  `diagnostics=({'trace': [{'success': True}]},)`, as well as an event payload
  containing `{'detail': {'net_R': 2}}`. This violates the approved no-hidden-
  labels boundary, including nested data.

- **C2 — sub-microsecond payload availability can be silently converted into an
  earlier selectable time.** `_payload_available_at()` parses its ISO string
  before calling `_utc` (`:99-110`). Python accepted
  `2026-01-02T09:30:00.0000001+00:00`, truncated it to the event's
  `2026-01-02T09:30:00+00:00`, and the contract accepted the event. Thus an
  availability value later than the event by 0.1 microseconds can pass the
  equality check, defeating the required microsecond-exact/future-event guard.

## Important findings

- **I1 — the focused suite does not cover either critical boundary.** It tests
  forbidden fields only in `candidate` (`tests/tree_replay/test_causal_replay_contracts.py:149-157`) and tests sub-microsecond precision only for a datetime
  object (`:104-113`), not for the serialized payload timestamp that controls
  event agreement. Consequently all 16 tests pass while the probes above are
  accepted.

## Minor findings

- None.

## Other scope checks

Static inspection found only supplied-data validation, hashing and local helper
imports; no tracker record/delivery, network, filesystem, retained-source
execution, dataset/model/readiness, or economic calculation path was found.

## Verification

- `python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider` — PASS (`16 passed in 0.08s`).
- `python -B -m py_compile trading_system/tree_replay/causal_replay_contracts.py tests/tree_replay/test_causal_replay_contracts.py` — PASS.
- Read-only adversarial probe — FAIL: accepted nested diagnostic/payload label
  fields and a seven-digit fractional payload availability timestamp, as
  described in C1 and C2.

Recommended next action: reject the forbidden field names recursively in every
structured replay surface that can be ledgered, and reject serialized payload
timestamps whose precision exceeds microseconds before parsing. Add regression
tests for each accepted probe, then rerun the focused suite.
