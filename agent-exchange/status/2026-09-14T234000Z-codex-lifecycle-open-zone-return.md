# Codex acceptance — lifecycle OPEN zone-return source projection

Request: direct implementation continuation under
`docs/superpowers/plans/2026-09-14-lifecycle-open-zone-return-source.md`.

Created at: 2026-09-14T23:40:00Z

Status: ACCEPTED_BY_CODEX

## Accepted scope

The private supplied-spot `LifecycleOpenZoneReturn` is accepted only for the
pinned live OPEN zone-return helper in `chart-desk/chartdesk/tracker.py` lines
1046–1106 and its caller boundary lines 2751–2759, at chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`.

It preserves zero-excursion silence, malformed-marker fallback, exact
target-only rearm, long/short entry-band conditions, message order and the
caller’s append-then-changed behavior.  Its direct behavior is advisory: after
emitting a message it sets only `zone_return_at`; it does not directly create a
terminal state, outcome, persistence or delivery effect.

The actual `Revalidation(source).still_valid(trade)` child is retained, not
replaced with a precomputed label. Its accepted offline ports can fetch
corrected evidence and its shadow path can attempt source-owned shadow writes.
That inherited boundary is intentionally documented; this acceptance does not
claim the composition is feed-free or effect-free. The recheck remains an
advisory message label, never a veto or lifecycle decision.

## Codex verification

Read both task reports, the Task 1 review/re-review, Task 2 review and final
review at
`agent-exchange/reviews/2026-09-14T233000Z-lifecycle-open-zone-return-final-review.md`.
Inspected the scoped dirty/untracked worktree artifacts and retained source as
text/AST only; no unrelated tracked diff is attributed to this acceptance.

Passed independently:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_open_zone_return.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_revalidation.py tests/tree_spec/test_lifecycle_open_zone_return_source.py -q --tb=short -p no:cacheprovider
# 189 passed in 26.27s

python -B tools/check_lifecycle_open_zone_return_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
# VERIFIED; blockers=[]; source_subset_verified=true;
# ready_for_replay=false; ready_for_training=false
```

The final independent review was PASS and additionally verified source
identity, the physical helper/caller boundaries, runtime AST, child-proof graph
and fail-closed JSON CLI behavior.

## Explicitly not accepted

This is not a full OPEN resolver or caller, causal market acquisition,
persistence/delivery, fills/economics, simulation, replay, dataset generation,
training/model readiness, model promotion or live trading. All corresponding
readiness claims remain false.
