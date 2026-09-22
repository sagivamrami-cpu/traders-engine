# Agent Exchange Result

Target:
Project memory, Roee, Sagiv and future Codex continuations

Sender:
Codex controller

Created at:
2026-09-09T11:35:12Z

Request:
agent-exchange/inbox/codex/2026-09-09T112000Z-historical-levelmap.md
Combined review:agent-exchange/inbox/codex/2026-09-09T113200Z-levelmap-final-review.md

Status:
ACCEPTED_BY_CODEX

Summary:
All three tasks of docs/superpowers/plans/2026-09-09-historical-levelmap-core.md
accepted. Original complete map calculations consume reconstructed causal frames
and as-of correction evidence; actual synthetic map output feeds reversal/pricing.
This is component acceptance, not full-tree/model completion or production approval.

Changed files:
- frames.py and levelmap.py under trading_system/tree_replay/.
- _vendor/levelmap_build.py, map_sessions.py and map_tr.py.
- tools/check_levelmap_source_parity.py and levelmap-source-contracts.json.
- test_frames.py, test_levelmap.py and test_levelmap_source.py.
- Three usage documents:HISTORICAL-FRAMES, LEVELMAP-SOURCE, HISTORICAL-LEVELMAP.
- Component plan, AGENTS/README/master/tracker and scoped exchange records.

Verification results:
- Parent python -m pytest tests/tree_replay/test_frames.py
  tests/tree_replay/test_levelmap_source.py -q --tb=short:
  215passed96.46s exit0.
- Parent python -m pytest tests/tree_replay/test_levelmap.py -q --tb=short:
  40passed5.59s exit0.
- Parent python -m pytest tests/tree_replay tests/tree_spec
  tests/data_foundation/test_sessions.py -q --tb=short:
  1597passed182.72s exit0.
- Parent python -m pytest -q --ignore-glob='*validator*' --tb=short:
  1969passed247.11s exit0. Old validator tests excluded, not certified.
  Counts overlap;255 component tests are included, not additional to the totals.
- All six source audit CLIs final PASS exit0, blockers=[], readiness false.
  range/correction/levelmap tools used their retained default root;
  ema/reversal/pricing tools used --source-root
  C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk.
  Initial missing-root usage errors on the older tools were corrected by passing
  the required argument, not by modifying code. Exact commands in final review.
- Task source/frame/fix/adapter and final combined reviews accepted. Final
  review2026-09-09T113200Z-levelmap-final-review.md:specPASS, qualityAPPROVED,
  no Critical/Important/Minor findings; no parked findings or domain rulings.
- Read worker reports/results and original requests; inspected actual untracked
  diffs, git status and code; independently ran verification. Final reviewer
  confirmed all13 new file hashes matched the package. Reviewers did not rerun
  routine suites or independently recertify historical RED chronology.
- Tracked git diff --check exit0. Per13 new-file no-index --check returned1 for
  additions with LF/CRLF advisories only, no whitespace errors. Not reported as
  zero-exit checks. No runtime files changed after completed verification.

Implementation evidence:
Explicit calendar-backed period ownership/source labels and intraday grids;
published closed-base prefixes, no compressed missing history or future OHLC.
Exact original families/order/gates; independently pinned/ordered EMA dependency
audit. Lazy fetches and separate temporal preflight versus actual20/7-day shape
checks. Stable repeated-name IDs and map timestamps=T, with actual price times
in traces. No offsets reapplied. Synthetic41-level fixture and genuine map-derived
reversal/pricing, plus future/unused-fallback invariance and real error handling.
No mathematical calculation dependency mocked.

Decisions needed:
Existing GC versus OANDA source-variant request remains ACTIONABLE under
2026-09-09T102100Z-gc-versus-source-gold.md. No futures/spot alias inferred.
Applicable fill/cost/pending-expiry/time-exit and ambiguity policies before labels;
acceptance criteria/holdout before evaluation; existing data/retention/promotion/
shadow/deployment/live-trading approvals remain binding.

Blockers:
None for this component or next safe synthetic engineering. This turn made
concrete progress; no repeated no-progress/blocking streak. Full master objective
remains active and incomplete, not narrowed to this map.

Recommended next action:
Implement original level-reversal producer find/admission and M5/M15 selection/
arbitration with correction gates and explicit decision times. A map evaluated
at T must not be backdated to bypass the detector's prior-confirmation guard;
validate delayed/asynchronous behavior before claiming that path. Continue B/D
registry/branches/memory, E simulator, F approved dataset, G models, H evaluation,
I explicitly gated shadow. J remains separate research.

Notes:
Closed-base observations and known higher-frame prefixes only: no open-only or
partial base bars. Source lookbacks are request identities, not independent proof
of history. Calendars/labels/price-basis consistency are supplied attestations,
not vendor certification. Built maps may omit families and remain UNADMITTED.
Runtime construction does not run source audits; future replay/CI must retain
mandatory pinned-source verification. No fills, labels or training readiness.
No real data/downloads, live changes, new outcome dataset, fitting, broker calls,
deployment, commits, pushes, worktrees or cleanup. Existing dirty work preserved;
scratch evidence retained because no committed recovery record exists.
