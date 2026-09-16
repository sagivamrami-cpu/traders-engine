# Codex acceptance — lifecycle OPEN post-fill evidence source prerequisite

Request: direct implementation continuation under
`docs/superpowers/plans/2026-09-14-lifecycle-open-postfill-evidence-source.md`.

Created at: 2026-09-14T11:10:00Z

Status: ACCEPTED_BY_CODEX

## Accepted scope

`LifecycleOpenPostfillEvidence` is accepted as a private, offline collector
for the pinned `tracker.py` OPEN evidence fragment (lines 2647–2689) at
chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`.

It begins with caller-supplied spot, applies the source correction gates to a
supplied corrected-tape port, locates the fill, preserves the fill-bar-first
extrema convention and returns `(low, high, minimum_message)`. Unsafe,
unlocatable or unreadable tape leaves the window spot-only.

## Codex verification

Read the task report and independent final review:
`agent-exchange/reviews/2026-09-14T110000Z-lifecycle-open-postfill-evidence-final-review.md`.
Inspected the current dirty worktree before acceptance; the scoped artifacts
are untracked project work and no unrelated tracked diff is attributed here.

Passed independently:

```powershell
python -m pytest -qq tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_spec/test_lifecycle_open_postfill_evidence_source.py tests/tree_spec/test_lifecycle_live_evidence_source.py tests/tree_spec/test_lifecycle_primitives_source.py
# 70 tests; exit 0

python -B tools/check_lifecycle_open_postfill_evidence_source_parity.py --source-root 'C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'
# VERIFIED; blockers=[]; source_subset_verified=true;
# ready_for_replay=false; ready_for_training=false
```

## Explicitly not accepted

The collector does not mutate a trade or decide protection, targets, terminal
state, persistence, gate, delivery, economic P&L, simulation, replay, dataset
creation, training, model promotion or live trading.
