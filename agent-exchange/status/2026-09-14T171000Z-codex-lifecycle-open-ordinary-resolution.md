# Codex acceptance — lifecycle OPEN ordinary-resolution source projection

Request: direct implementation continuation under
`docs/superpowers/plans/2026-09-14-lifecycle-open-ordinary-resolution-source.md`.

Created at: 2026-09-14T17:10:00Z

Status: ACCEPTED_BY_CODEX

## Accepted scope

The private offline `LifecycleOpenOrdinaryResolution` projection is accepted
only for the pinned ordinary OPEN fragment in `tracker.py` lines 2721–2750 at
chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`.

After the caller has obtained a non-changing result from accepted
`LifecycleOpenProtection`, this component consumes caller-supplied
`(low, high, minimum_message)`. It preserves source order: progress gating,
ordinal target message/raw-fact writes, protective recomputation, then
all-target or protective terminal handling. Source zero-target `DONE` behavior
is preserved.

## Codex verification

Read both task reports, both task reviews and final review:
`agent-exchange/reviews/2026-09-14T170000Z-lifecycle-open-ordinary-resolution-final-review.md`.
Inspected the current dirty worktree before acceptance; scoped artifacts are
untracked project work, with no unrelated tracked diff attributed here.

Passed independently:

```powershell
python -m pytest -q tests/tree_replay/test_lifecycle_open_ordinary_resolution.py tests/tree_spec/test_lifecycle_open_ordinary_resolution_source.py
# 20 passed in 15.88s

python -B tools/check_lifecycle_open_ordinary_resolution_source_parity.py --source-root 'C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'
# VERIFIED; blockers=[]; source_subset_verified=true;
# ready_for_replay=false; ready_for_training=false
```

The source audit pins the physical AST fragment and exact runtime projection.
It rejects directional low/high, target/outcome, terminal and protective
mutations, source identity/order drift and malformed child/CLI reports.

## Explicitly not accepted

This slice excludes minimum-success outcome handling, live-spot zone return,
bar/quote acquisition, full resolver composition, persistence/gate/delivery,
economic P&L, simulation, replay, datasets, training, model promotion and live
trading.
