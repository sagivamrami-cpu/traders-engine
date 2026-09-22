# Task 1 report — lifecycle live-resolution evidence collector

## Status

IMPLEMENTED_AWAITING_CODEX_REVIEW

## Scope completed

Implemented only the evidence collector required by Task 1. It reuses
`LifecycleLiveEvidence(source)._live_prices()`, then returns raw resolver
evidence as `(prices, bar_extremes)` for supplied `PENDING` and `OPEN` records.
It does not load or mutate state, make lifecycle decisions, or trigger any
effects.

## Changed files

- `trading_system/tree_replay/_vendor/lifecycle_live_resolution_evidence.py`
- `tests/tree_replay/test_lifecycle_live_resolution_evidence.py`
- `docs/architecture/LIFECYCLE-LIVE-RESOLUTION-EVIDENCE-SOURCE-USAGE.md`
- `.superpowers/sdd/2026-09-14-lifecycle-live-resolution-evidence-source/task-1-report.md`

## Verification

- RED: `python -B -m pytest tests/tree_replay/test_lifecycle_live_resolution_evidence.py -q`
  — expected 12 failures because the module did not exist.
- GREEN: `python -B -m pytest tests/tree_replay/test_lifecycle_live_evidence.py tests/tree_replay/test_lifecycle_live_resolution_evidence.py -q`
  — PASS, 29 passed in 2.06s.
- `git diff --check` — PASS; only pre-existing repository line-ending notices
  for unrelated `AGENTS.md` and `README.md` were printed.

## Coverage

Focused tests cover active-state filtering, the exact 120-second fallback
boundary, corrected request identity, correction rejection, strict timestamp
precedence, low/high carry-forward, sibling error isolation, top-level quote
payload failure, input immutability, and proof that transition/outcome/caller/
persistence ports are neither invoked nor needed.

## Concerns

The retained source checkout was not present at its documented temporary path
in this worker environment, so no direct text inspection was possible here.
The implementation follows the complete task brief, plan, and source intake;
Task 2 must perform the required pinned source-parity audit before acceptance.
No source was executed and no live or historical market data was accessed.
