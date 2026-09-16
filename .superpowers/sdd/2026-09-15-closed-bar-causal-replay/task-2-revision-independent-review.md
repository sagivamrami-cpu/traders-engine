# Task 2 corrective revision independent review

Status: APPROVED

## Scope reviewed

Corrective revision only for Task 2 source-pinned outer-pass intake. Read the
Task 2 plan/spec/brief, prior independent review, revision report, and complete
current `causal_replay_source.py` plus `test_causal_replay_source.py`. The
retained `market_watch.py` was read as text and AST-parsed only by the local
auditor tests; it was never imported, compiled, or executed.

## Critical

None.

## Important

None.

## Minor

None.

## Corrective-flaw adjudication and exact evidence

- The former flaw is closed. `OUTER_GATE_CONTROL_LINES` and
  `OUTER_GATE_PREDICATES` define all six required controls at
  `causal_replay_source.py:64-80`: `windows`, `market_closed`, `post_stop`,
  `occupied_slot`, `same_level`, and `producer_arbitration`.
- `_validate_outer_gate_controls()` (`causal_replay_source.py:291-301`) finds
  each fixed-line `if`, requires its exact retained predicate, and requires a
  direct rejection `continue`. `_rejects_before_record()`
  (`causal_replay_source.py:281-288`) further verifies that the gate is before
  `_trk.record` and that its `continue` targets the same enclosing reversal
  loop as that record. This covers the producer-arbitration assignment's actual
  `st.get(state_key)` duplicate-rejection branch without exposing an invented
  public admission boolean.
- Retained source text confirms the six actual controls and direct rejection
  paths at `market_watch.py:1035-1054` and `:1060-1063`; it also confirms
  reversal precedes `_tree.walk` (`:1014`, `:1239`) and
  `tradeplan.build_all` (`:1449`).
- `test_audit_rejects_disabled_outer_gate_predicate_while_preserving_gate_call_and_line`
  (`test_causal_replay_source.py:143-168`) independently mutates every one of
  the six predicates while retaining its gate call/line and pin-adjusts the
  in-memory blob. `test_audit_rejects_outer_gate_when_its_rejection_continue_is_replaced`
  (`:171-186`) does the same for each rejecting `continue`. Both assert a
  schema-valid `BLOCKED` response through `assert_blocked()` (`:74-80`):
  nonempty string blockers, false source subset verification, and both
  readiness flags false.
- The required direct engine-before-reversal mutation is present at
  `test_audit_requires_level_reversal_before_engine` (`:199-206`), alongside
  the tree counterpart (`:189-196`), and asserts the same fail-closed result.
- Public projection remains deliberately unwired: it emits every named gate as
  `UNWIRED_OUTER_ADMISSION` (`causal_replay_source.py:343-345`) and validates
  that exact public value set (`:374-376`). `_empty_report()` and `_verified()`
  retain `ready_for_replay=False` and `ready_for_training=False`
  (`:84-114`). The declared contract scope remains static source intake only,
  excluding replay runtime, registration, delivery, economics, dataset,
  training, and model behavior (`:38-51`); no scope expansion was found.

## Verification run

```text
python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider
38 passed in 6.65s

python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider -k "disabled_outer_gate_predicate or rejection_continue_is_replaced or requires_level_reversal_before_engine"
13 passed, 25 deselected in 3.12s
```

No retained source was executed or imported by these checks.
