# Historical period state and source range calculations

> For agentic workers: use superpowers:subagent-driven-development and TDD.

**Goal:** Supply causal daily-period OHLC and the original range/rollover formulas
needed by historical level-map construction in the full approved model plan.
**Architecture:** Explicit caller-supplied daily boundaries and session evidence;
aggregate only complete, published lower-timeframe bars. Independently port pure
source range functions without importing live data fetchers. Full level assembly
and producer admission remain downstream, not replaced by these components.
**Tech stack:** Existing Python dataclasses, datetime, pandas, pytest and AST audits.
**Spec:** TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md sections3-5,10,12;
HISTORICAL-LEVELMAP-SOURCE-CONTRACT.md records exact pinned source dependencies.

## Global Constraints

- Preserve chart-desk commit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 semantics.
- No invented daily rollover, holiday, broker identity, price correction or costs.
- No live source execution, downloads, labels, model fitting or deployment.
- Existing dirty branch remains in place; no commits/worktrees/cleanup.
- Readiness stays false. Full master objective remains open after this slice.

## Task 1: Pure source range dependency closure (sidecar)

Create _vendor/ranges.py, _vendor/back_days.py under trading_system/tree_replay;
configs/trees/range-level-contracts.json; tools/check_range_source_parity.py;
tests/tree_replay/test_range_source.py and assigned report only.

Copy tr.daily_pivots, average_range, range_hilo, weekly_from_daily,
monthly_from_daily, tr_levels EXACTLY, with original imports required by selected
functions. Copy levelmap.BACK_DAYS and _back_day_levels exactly. Pivots are a
dependency of tr_levels, not a new emitted family. Source list/order/imports and
Git blobs independently pinned in an AST-only auditor; no source execution.
CLI --source-root supplied; readiness false regardless of audit success.

- [x] Write failing tests for means excluding current row, moving/open anchors,
  zero range and insufficient history, verified flags, RD/RW not rolling H/L,
  all tr_levels families, lweek guard, Sunday3h rollover/month boundary,
  back-days offsets and warmup, and contract/source/vendor mutation rejection.
  Literal example: two previous ranges10,20 and current O100,H115,L95,C110:
  average_range(length2) -> range15, high110,low100,used20; from_open ->107.5/92.5.
- [x] Port exact source functions and fixed auditor. Source prerequisites may
  use TR_CHARTDESK_SOURCE_ROOT override plus retained local default; audits must
  fail clearly if missing, never skip silently.
- [x] Run python -m pytest tests/tree_replay/test_range_source.py -q and CLI;
  report RED/GREEN and exact scope. No edits to prior vendor/auditor files.

## Task 2: Causal daily-period aggregation (parent critical path)

Create trading_system/tree_replay/periods.py and tests/tree_replay/test_periods.py.
New immutable DailyPeriod: instrument, period_id, opened_at, closed_at,
available_at, source, version. Exact UTC-aware microsecond timestamps, positive
duration; no forced24h (DST23/25h valid). Caller boundaries are evidence, not
inferred truth. Interface:

```python
aggregate_daily_asof(bars, *, period: DailyPeriod, decision_time,
                     base_timeframe: str, session_schedule: SessionSchedule) -> dict
```

Validate all input ClosedBars including outside selection: exact instrument/TF,
duplicate opens/revisions rejected. Select only within [period.opened_at,cutoff],
where cutoff=min(decision_time,period.closed_at), and available_at<=decision_time.
Decision cannot precede period open. Require period boundaries and cutoff on
the fixed UTC base grid. Period/calendar availability must be<=decision time and
calendar coverage must include [period.opened_at,cutoff]. Clip open intervals to
that window; every clipped session endpoint must align to the grid, otherwise
PERIOD_GRID_UNRESOLVED (do not discard straddling fragments).

Generate every expected open on the clipped session intervals. No intervals ->
NO_EXPECTED_BARS. Missing first expected -> HISTORY_INCOMPLETE; any other missing
-> HISTORY_GAP. Out-of-session selected bars excluded/count diagnostic. Do not
impose a freshness age on completed historical days: complete coverage and as-of
publication determine usability. Missing volume -> aggregate volumeNone, not0.

On usable input compute firstopen,maxhigh,minlow,lastclose,finite volume sum;
observed_at=last selected close, available_at=max(selected publications,calendar,
period publication). Output schema daily-period-asof-v1, status FORMING or CLOSED
(decision>=period.closed_at), blockerNone, ohlcv dict, observed/available ISO times,
period metadata, decision_time, expected_bars, missing_opens, excluded count,
evaluation_sha256 over selected evidence+versions+policies, readinessfalse.
Blocked output has ohlcv/observed_at/available_at null, explicit blocker and no
feature approval. Hash excludes future/unpublished bars and bars in later periods.

- [x] RED tests: O100/H105/L99/C104 then O104/H108/L102/C106 ->100,108,99,106,
  volume30 at secondclose; later high900 must not affect that snapshot. At final
  period close include final bar and markCLOSED. Late lastbar blocks then succeeds
  when actually published even after period end. Interior gaps, declared breaks,
  off-grid fragments, zero/missing volume, overflow, date validation, identity,
  future suffix invariance and23/25h periods have independent expectations.
- [x] Implement minimal pure aggregator with existing bar/time/identity validators;
  do not modify selectors or use their blocked outputs as usable history.
- [x] GREEN tests; documentation explains lower-bar-close decision precision,
  no open-only current period support yet, no period inference or full map.

## Task 3: Integration acceptance

- [x] Package actual diffs and independently review Tasks1/2; resolve findings.
- [x] Verify source CLI and period+range+prior tree integration. Test hand-derived
  aggregate output fed into real range function, with current-row future extension
  excluded at the same decision time. This is dependency integration, not a full
  historical-map acceptance claim.
- [x] Final combined review; update master/tracker/usage and exchange acceptance.
  Continue full map construction: feed/proxy evidence, original map assembly,
  session opens/PSY/EMA, then producer find/admission/arbitration and simulation.
