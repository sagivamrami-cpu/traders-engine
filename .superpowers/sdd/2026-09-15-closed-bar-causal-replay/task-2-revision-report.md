# Task 2 corrective revision report: outer-gate control flow

## Finding addressed

The independent review correctly found that the source audit previously proved
only named gate call presence and line ordering. A source pin update could have
preserved those calls while disabling the rejecting predicate or its
`continue`, and still have produced `VERIFIED`.

## RED evidence

After adding the mutation tests and before changing the auditor, this command
failed exactly as expected:

```text
python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider -k "disabled_outer_gate_predicate or rejection_continue_is_replaced or requires_level_reversal_before_engine"
12 failed, 1 passed, 25 deselected in 2.95s
```

Each of the following mutations retained the source gate call and its line but
the audit returned `VERIFIED`: disabled predicates for windows, market-closed,
post-stop, occupied-slot, same-level, and producer-arbitration/dedup; and
replaced rejecting `continue`s for those same six paths. The standalone direct
engine-before-reversal mutation already blocked, and remains covered.

## Revision

- `trading_system/tree_spec/causal_replay_source.py`
  - Added private AST control-flow validation for all six named outer-admission
    paths. It requires each exact source predicate and a direct `continue`
    whose target is the same reversal symbol loop containing `_trk.record`.
  - Preserved actual source forms: assignment-result guards for windows,
    market-closed, post-stop, and same-level; direct-call guard for occupied
    slot; and the producer-arbitration assignment plus its actual
    duplicate-state rejection path.
  - Kept public outer-gate projection values exclusively
    `UNWIRED_OUTER_ADMISSION`; no gate behavior boolean was added.
- `tests/tree_spec/test_causal_replay_source.py`
  - Added six disabled-predicate and six replaced-`continue` source-text
    mutations, each pin-adjusted only in memory and asserted schema-valid
    `BLOCKED` with both readiness flags false.
  - Added the direct engine-before-level-reversal mutation case.

## GREEN evidence

Focused regression cases after the implementation:

```text
python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider -k "disabled_outer_gate_predicate or rejection_continue_is_replaced or requires_level_reversal_before_engine"
13 passed, 25 deselected in 2.97s
```

Full focused Task 2 suite:

```text
python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider
38 passed in 6.37s
```

Pinned CLI:

```text
python -B tools/check_causal_replay_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
exit 0; JSON status VERIFIED; blockers []; ready_for_replay false; ready_for_training false
```

## Scope and boundary confirmation

Only the two authorized Task 2 implementation/test files and this revision
report were changed. The retained checkout was read and AST-parsed as text
only; it was not imported, compiled, or executed. The commit/blob source pin,
parse-only reader, JSON-only CLI behavior, false readiness, and excluded
replay, tracker registration, delivery, economic, dataset, training, and model
behavior remain unchanged. No commit, push, source-retained checkout change,
or prohibited feature was performed.
