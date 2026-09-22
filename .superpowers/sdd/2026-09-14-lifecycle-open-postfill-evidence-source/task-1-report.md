# Task 1 report — OPEN post-fill evidence runtime

Status: IMPLEMENTED_AWAITING_CODEX_REVIEW

## Scope completed

- Added `trading_system/tree_replay/_vendor/lifecycle_open_postfill_evidence.py`.
- Added focused behavior tests at
  `tests/tree_replay/test_lifecycle_open_postfill_evidence.py`.
- Added usage documentation at
  `docs/architecture/LIFECYCLE-OPEN-POSTFILL-EVIDENCE-SOURCE-USAGE.md`.

The collector receives one caller-supplied OPEN record, spot, and the supplied
corrected-tape port. It mirrors the source slice: initialize from spot; fetch
`15m, 2`; apply the correction gate with the accepted historical-safety
exception; locate the fill with the accepted helper; use
`fill_bar_first=True`; combine extrema with spot; recover only a provisional
minimum message; and contain every tape-path failure as spot-only evidence.

`DeskSuccess.observe_bars` is run on a detached shallow copy so this raw
evidence slice cannot mutate the supplied OPEN record. No state transition,
effect, persistence, readiness, economic, replay, dataset, training or model
behavior was added.

## TDD evidence

RED, before the runtime module existed:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_open_postfill_evidence.py
6 failed in 0.60s
AssertionError: OPEN post-fill evidence module missing
```

GREEN after the minimal runtime implementation, fixture correction for the
source's fill-containing-bar convention, and a naming-only tuple refactor:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_replay/test_lifecycle_bars.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_live_evidence.py
98 passed in 0.92s
```

Focused cases cover long and short tuple ordering; spot inclusion; fill-bar
adverse-only treatment; unverified and unsafe `tv_stale` fallback; safe stale
historical recovery; unlocatable and failing-tape fallback; exact corrected
request identity; no mutation of supplied records/tape/correction; and no
effect-port invocation.

## Blockers

None for Task 1. Task 2 source audit, CLI, mutation tests and independent
review remain outside this task's authorized scope.
