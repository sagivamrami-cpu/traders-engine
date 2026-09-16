# Task 2 report — lifecycle live-resolution evidence source audit

## Scope

Implemented only the inert retained-source auditor, its explicit-root JSON CLI,
and its contract tests. The retained chart-desk source was read and parsed only;
it was never imported or executed. No runtime, resolver, market-data, lifecycle,
outcome, replay, dataset, model, training, commit, push, or agent action was
performed.

## TDD evidence

- RED: `python -m pytest -q tests/tree_spec/test_lifecycle_live_resolution_evidence_source.py`
  initially produced 18 expected failures because the auditor and CLI did not
  exist.
- GREEN: `31 passed in 11.55s` for the Task 2 source-audit tests plus the
  existing focused Task 1 runtime tests.

## Implemented files

- `trading_system/tree_spec/lifecycle_live_resolution_evidence_source.py`
- `tools/check_lifecycle_live_resolution_evidence_source_parity.py`
- `tests/tree_spec/test_lifecycle_live_resolution_evidence_source.py`

## Result and concern

The explicit-root CLI correctly fails closed against the retained source:

```json
{
  "status": "BLOCKED",
  "source_subset_verified": false,
  "blockers": ["VENDOR_AST_MISMATCH:lifecycle_live_resolution_evidence"],
  "ready_for_replay": false,
  "ready_for_training": false
}
```

This is a meaningful parity finding, not a CLI failure. The existing runtime
moves quote-age parsing and the early fresh-quote skip into the broad
per-symbol `try`, whereas the retained source performs them before that
boundary. It also differs in local projection structure. Since Task 2 was
explicitly prohibited from changing runtime, the auditor preserves the block
instead of normalizing or hiding it. The component therefore cannot be
accepted as source-parity verified until a separately scoped runtime decision
and repair (or an explicit source-equivalence decision) is made.
