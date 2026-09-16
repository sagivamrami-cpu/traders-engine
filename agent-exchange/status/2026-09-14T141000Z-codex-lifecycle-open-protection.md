# Codex acceptance — lifecycle OPEN protection source prerequisite

Request: direct implementation continuation under
`docs/superpowers/plans/2026-09-14-lifecycle-open-protection-source.md`.

Created at: 2026-09-14T14:10:00Z

Status: ACCEPTED_BY_CODEX

## Accepted scope

The private, offline `LifecycleOpenProtection` projection is accepted only for
the pinned `tracker.py` OPEN ambiguity branch (lines 2690–2715) at
`chart-desk` commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, blob
`b616b34022e436545d8c1daf85eced51614fd74e`.

For a caller-supplied post-fill `(low, high)` window, an ambiguous simultaneous
protective/unhit-target touch becomes `STOPPED` before a hit and `DONE` after a
hit. It composes the accepted transition and raw-outcome-shelf components.
It returns no effect and mutates nothing if the window is not ambiguous.

## Codex verification

Read the implementation, source auditor, usage contract, both task reports,
and final independent review:
`agent-exchange/reviews/2026-09-14T140000Z-lifecycle-open-protection-final-review.md`.
Inspected the dirty worktree before acceptance; the scoped artifacts are
untracked project work, with no unrelated tracked diff attributed to this
acceptance.

Passed independently:

```powershell
python -m pytest -q tests/tree_replay/test_lifecycle_open_protection.py tests/tree_spec/test_lifecycle_open_protection_source.py
# 27 passed in 24.97s

python -B tools/check_lifecycle_open_protection_source_parity.py --source-root 'C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'
# VERIFIED; blockers=[]; source_subset_verified=true;
# ready_for_replay=false; ready_for_training=false
```

The test suite includes a physical low/high mutation: reversing the
directional extrema eliminates resolution, state mutation, clock use and raw
outcome write. The CLI also verified the outcome-shelf and transition child
proofs with false readiness.

## Explicitly not accepted

This is not the ordinary OPEN target/progress/protection ordering, zone-return
logic, bar or quote acquisition, persistence, delivery, economic P&L,
simulation, replay, dataset creation, model training, model promotion or live
trading authorization.

Next source slice: the ordinary OPEN progress/target/protective ordering after
the ambiguity `continue`, with its own intake, tests, source audit and review.
