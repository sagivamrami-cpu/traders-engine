### Task 1: Outcome/shelf helper runtime

**Files:**
- Create: `trading_system/tree_replay/_vendor/lifecycle_outcome_shelf.py`
- Create: `tests/tree_replay/test_lifecycle_outcome_shelf.py`
- Create: `docs/architecture/LIFECYCLE-OUTCOME-SHELF-SOURCE-USAGE.md`

- [ ] Start with normal missing-module RED tests for source ordering of clock,
  outcome payload and append, expiry priority, shelf lineage, malformed shelf
  fallback, atomic cleanup/propagation and actual accepted `has_open` behavior.
- [ ] Project the complete selected source set in exact order. Adapt only
  logical artifact/clock/atomic I/O expressions to supplied offline ports;
  preserve `event_ts` truthiness and source error boundaries.
- [ ] Prove no helper creates a label, reads a market feed, delivers a message,
  returns a fill/economic assertion or establishes replay/training readiness.
- [ ] Run focused tests against real tracker-admission and lifecycle-gate
  dependency implementations; obtain independent Task 1 review and close
  findings.
