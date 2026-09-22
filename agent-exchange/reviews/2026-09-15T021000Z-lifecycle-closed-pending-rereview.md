# Closed-bar PENDING M1 re-review

Reviewer: Codex

Target request: Scoped M1-only re-review of `LifecycleClosedPendingResolution`.

Created at: 2026-09-15T02:10:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict: **PASS — M1 ADDRESSED**

## Finding disposition

The original review (`2026-09-15T020000Z`) found that the projection stamped
`filled_ts` and `progress_ts` with the caller-supplied pass anchor.  That is
now corrected at
`trading_system/tree_replay/_vendor/lifecycle_closed_pending_resolution.py:72`:

```python
trade["filled_ts"] = trade["progress_ts"] = self.source.now_epoch()
```

This matches the retained source's distinct fill-time clock call at
`chartdesk/tracker.py:1249`.  The supplied `now` remains restricted to the
earlier expiry predicate and `revalidate_pending(..., now=now)` call, matching
the pass-level source clock at line 1123 and the revalidation call at 1239.

The new regression
`test_successful_fill_uses_fresh_source_clock_not_supplied_pass_anchor` is
discriminatory: it supplies `now=NOW`, has `source.now_epoch()` return
`NOW + 37.0`, asserts revalidation received `NOW`, and asserts both fill fields
equal `NOW + 37.0`.  Thus restoring the prior pass-anchor assignment fails the
test; the Task 1 report records that mutation as `1 failed, 7 deselected`.

## Scope

This is only a closure of M1.  It does not accept or assess a source auditor,
caller binding, bar acquisition, OPEN progression, persistence/gating,
delivery, replay, economics, dataset construction, training, model inference,
or live trading.

## Verification reviewed

- Read original failing review, Task 1 report tail, runtime, focused tests, and
  usage contract.
- Read retained source as text at pinned `chartdesk/tracker.py:1123,1239,1246-1250`.
- Re-ran:

```text
python -m pytest -q tests\\tree_replay\\test_lifecycle_closed_pending_resolution.py \\
  tests\\tree_replay\\test_lifecycle_pending_resolution.py \\
  tests\\tree_replay\\test_lifecycle_outcome_shelf.py \\
  tests\\tree_replay\\test_lifecycle_transitions.py \\
  tests\\tree_replay\\test_tree_revalidation.py
80 passed in 10.21s
```

Recommended next action: M1 is closed.  Resume the normal component acceptance
sequence; a full task/final review is still separate from this scoped re-review.
