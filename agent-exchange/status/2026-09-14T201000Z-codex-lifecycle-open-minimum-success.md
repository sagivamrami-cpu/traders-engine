# Codex acceptance — lifecycle OPEN minimum-success source projection

Request: direct implementation continuation under `docs/superpowers/plans/2026-09-14-lifecycle-open-minimum-success-source.md`.

Created at: 2026-09-14T20:10:00Z

Status: ACCEPTED_BY_CODEX

## Accepted scope

The private offline `LifecycleOpenMinimumSuccess` is accepted only for pinned `tracker.py` OPEN source lines 2690–2704 at chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob `b616b34022e436545d8c1daf85eced51614fd74e`.

It consumes caller-supplied post-fill window, spot, raw quote, forming-bar membership and provisional bar minimum message. It preserves bar-minimum precedence, exact quote eligibility, directional progress, message-before-outcome order and one raw `minimum_success` fact.

## Codex verification

Read both task reports, Task 1 review/re-review, Task 2 review and final review at `agent-exchange/reviews/2026-09-14T200000Z-lifecycle-open-minimum-success-final-review.md`. Inspected the current dirty worktree; scoped files are untracked project artifacts and no unrelated tracked diff is attributed to this acceptance.

Passed independently:

```powershell
python -m pytest -q tests/tree_replay/test_lifecycle_open_minimum_success.py tests/tree_spec/test_lifecycle_open_minimum_success_source.py
# 26 passed in 26.52s

python -B tools/check_lifecycle_open_minimum_success_source_parity.py --source-root 'C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'
# VERIFIED; blockers=[]; source_subset_verified=true;
# ready_for_replay=false; ready_for_training=false
```

The final independent review reran 110 runtime/helper/audit tests. Its M1 finding was closed by a precedence regression: removing only `not minimum_message` fails while the original runtime passes.

## Explicitly not accepted

`minimum_success` is a raw tracker fact, not a fill, P&L/economic label, replay row, dataset/training target or model signal. Ambiguity, targets, ordinary or terminal resolution, zone return, persistence/gate/delivery, full resolver composition, economics, simulation, replay, datasets, training, model promotion and live trading remain excluded.
