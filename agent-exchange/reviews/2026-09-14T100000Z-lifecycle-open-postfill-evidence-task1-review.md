# Agent Exchange Review

Reviewer: Codex (read-only independent Task 1 review)

Target request: direct user request — review only of lifecycle OPEN post-fill evidence Task 1

Created at: 2026-09-14T10:00:00Z

Status: REVIEW_READY_FOR_CODEX

## Verdict

**PASS — spec: PASS; quality: PASS.**

`LifecycleOpenPostfillEvidence.collect()` is a deliberately bounded offline
projection of the retained `chartdesk/tracker.py::_check_live_locked` OPEN
evidence block, lines 2647–2689. The retained source was read/parsed only;
it was not imported or executed.

## Findings

- **Post-fill safety: PASS.** The collector starts at `(spot, spot)`, locates
  the fill with the accepted `_fill_on_tape`, and only then contributes tape
  extrema. It calls `_position_extremes(..., fill_bar_first=True)`, so the
  fill bar may be adverse but cannot earn favourable movement. An
  unreadable, unsafe, or unlocatable tape remains spot-only. This preserves
  the source protection against using a pre-fill window to announce a target.
- **Correction semantics: PASS.** The source order is preserved: fetch exact
  `("15m", 2)`, reject `unverified` or `tv_stale`, and allow a stale tape only
  through the accepted `_historical_replay_safe(tape, correction, trade)`
  exception for recovered OPEN lifecycle facts. The corrected tape never
  replaces the supplied current spot.
- **Extrema ordering: PASS.** Runtime retains the source `(high, low)` output
  contract from `_position_extremes`, assigning `tape_high, tape_low` and
  combining them as `min(spot, tape_low), max(spot, tape_high)`. Focused long
  and short tests distinguish the asymmetric fill-bar behaviour and would
  fail if low/high were swapped.
- **Detached trade behavior: PASS.** The source invokes `observe_bars(t, df)`
  as part of its resolver. This raw-evidence component intentionally invokes
  it on `copy(trade)`: `DeskSuccess` writes only the top-level
  `minimum_success` proof, so the shallow detached copy prevents mutation of
  the supplied OPEN record while retaining the source-style provisional
  message. Tests prove the supplied trade, tape, and correction remain
  unchanged.
- **No effects/readiness: PASS.** The component contains no state transition,
  persistence, delivery, outcome, protection/target resolution, economics,
  replay, dataset, training, model, or readiness claim. Tests provide effect
  ports that fail if called and confirm none is invoked.
- **Scope note: PASS.** `_protective(t, short)` at retained source line 2648
  belongs to subsequent OPEN resolution and is intentionally not included in
  this evidence-only collector. No state/economic behavior was introduced in
  its place.

## Open questions

None for Task 1. A fail-closed source auditor/CLI and final component
acceptance remain Task 2 work; neither is implied by this review.

## Recommended next action

Proceed to Task 2 source audit, mutation coverage, and CLI verification. Keep
this component explicitly limited to raw post-fill evidence; it is not OPEN
resolution, replay, economic labeling, dataset construction, training, model,
or live-trading readiness.

## Verification reviewed

```text
python -m pytest -q tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_replay/test_lifecycle_bars.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_live_evidence.py
98 passed in 0.59s
```

No implementation, test, usage, source, commit, push, or subagent action was
performed by this review. This review file is the sole requested artifact.
