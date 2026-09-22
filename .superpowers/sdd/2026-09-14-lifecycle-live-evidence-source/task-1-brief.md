### Task 1: Live-evidence runtime

**Files:**
- Create: `trading_system/tree_replay/_vendor/lifecycle_live_evidence.py`
- Create: `tests/tree_replay/test_lifecycle_live_evidence.py`
- Create: `docs/architecture/LIFECYCLE-LIVE-EVIDENCE-SOURCE-USAGE.md`

- [ ] Start with normal missing-module RED tests for exact quote age boundaries,
  non-finite/malformed sibling isolation, raw operation clock use, OPEN-only
  replay safety, correction/timestamp rejection and no-state-effect behavior.
- [ ] Project the full selected source set in physical order and adapt only
  quote-file read plus wall clock to `source.quote_payload()` and
  `source.now_epoch()`.
- [ ] Prove historical replay safety is evidence-only: it cannot make a stale
  quote fresh, fill PENDING, choose an entry/target/stop or create any label.
- [ ] Run focused tests against pandas inputs and obtain independent Task 1
  review.
