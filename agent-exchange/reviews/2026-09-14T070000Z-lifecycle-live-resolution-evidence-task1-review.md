# Agent Exchange Review

Reviewer: Codex (independent Task 1 reviewer)

Target request: `.superpowers/sdd/2026-09-14-lifecycle-live-resolution-evidence-source/task-1-brief.md`

Created at: 2026-09-14T07:00:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
FINDINGS

Findings:

1. **M1 — a falsy per-symbol raw quote does not retain the source fallback
   behavior.** The retained source computes the age as
   `float((_q.get(_s) or {}).get("ts", 0))`; therefore a valid top-level
   payload containing, for example, `{"X": null}` normalizes that symbol to
   `{}` and proceeds to `fetch_corrected`. The runtime uses
   `raw_quotes.get(symbol, {}).get("ts", 0)`. For `{"X": None}`, that
   raises `AttributeError` inside the broad per-symbol block and skips the
   symbol completely, so no corrected-bar evidence is collected. An
   independent in-memory probe returned `({}, {})` where the source semantics
   require the supplied corrected close and extrema. This violates the
   permitted-substitution and exact per-symbol evidence requirements.

2. **The focused suite does not cover this source-normalization case.** It
   covers top-level payload failure and absent symbols, but not a present,
   falsy per-symbol quote record. Add a regression test for `{"X": None}`
   (and, if desired, other falsy records accepted by `or {}`) that proves the
   corrected-bar fallback still occurs.

Evidence:

- Read `AGENTS.md`, `agent-exchange/README.md`, `agent-exchange/protocol.md`,
  Codex inbox, the Task 1 brief, plan, intake, report, runtime, tests and
  usage artifact.
- Read and parsed only the retained source function
  `_check_live_locked` in
  `C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk/chartdesk/tracker.py`;
  it was not executed. Its leading evidence block otherwise matches the
  collector's active-state filtering, 120-second inclusive skip boundary,
  `fetch_corrected(symbol, "15m", 2)` identity, correction rejection,
  strict timestamp winner, `(low, high)` carry-forward and broad per-symbol
  failure boundary.
- The collector remains evidence-only: it has no resolver transition, fill,
  revalidation, outcome, gate/save, delivery, replay, economics, dataset,
  training, model or readiness effect.
- Fresh focused command:
  `python -B -m pytest tests/tree_replay/test_lifecycle_live_evidence.py tests/tree_replay/test_lifecycle_live_resolution_evidence.py -q`
  -> `29 passed in 1.94s`.
- Independent in-memory malformed-row probe with `quote_payload()` returning
  `{"X": None}` and a valid corrected frame -> runtime returned `({}, {})`,
  demonstrating Finding 1.

Recommended next action:

- Revise only the raw quote-age normalization and add the missing regression;
  then rerun the focused suite and request a Task 1 re-review. This review
  does not assess the later source auditor or any resolver body.
