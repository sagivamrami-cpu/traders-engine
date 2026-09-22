# Session-aware EMA History Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development with TDD and independent task/final reviews.

**Goal:** Distinguish scheduled closures from missing expected bars before the existing EMA adapter consumes history.
**Architecture:** An immutable supplied half-open session schedule has explicit instrument, coverage and publication evidence. A restricted bridge reuses the registered GC normal-hours resolver; an opt-in selector enforces whole-bar membership and complete seed history. Existing contiguous-only calls and vendored formulas remain unchanged.
**Tech Stack:** Existing Python dataclasses, zoneinfo/session resolver, pandas/numpy and pytest.
**Spec:** docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md sections5,10,12,16. User explicitly continued the previously described calendar/missing-history integration.

## Global Constraints
- Continue approved master design sections5,10,12,16; no new trader thresholds.
- Local existing branch; preserve prior dirty work; no commits, push, worktree or cleanup.
- Synthetic tests only; no raw feeds, vendor calls, dataset generation, training or live effects.
- Existing strict selector remains unchanged. Calendar-aware mode is opt-in.
- Closed fixed-duration bars, microsecond-exact UTC times only. No resampling or partial bars.
- No implicit instrument conversion, holiday inference or approval. Readiness flags stay false.
- Schedules are explicit supplied research evidence, not independently verified historical truth.

## Task 1: Explicit schedule and registered normal-hours bridge (worker)
Files: create trading_system/tree_replay/calendar.py and tests/tree_replay/test_calendar.py only; assigned report.
Use existing bars._utc and bars._validate_identity(instrument,"5m") for shared normalization.
Interfaces (frozen keyword-only dataclasses):
```python
SessionInterval(opened_at: datetime, closed_at: datetime)
SessionSchedule(instrument: str, calendar_id: str, version: str,
    coverage_start: datetime, coverage_end: datetime, available_at: datetime,
    source: str, intervals: tuple[SessionInterval, ...])
schedule_from_research_calendar(calendar: SessionCalendar, *, instrument: str,
    coverage_start: datetime, coverage_end: datetime, available_at: datetime,
    source: str) -> SessionSchedule
```
SessionInterval: normalize UTC exactly; require start<end; interval is half-open.
SessionSchedule: all fields required; validate trimmed nonempty calendar_id/version/source, exact instrument; normalize times; coverage_start<coverage_end; available_at has no artificial relation to coverage (schedule may be published before it applies).
Only tuple of SessionInterval accepted. All intervals must lie inside coverage. Sort by opening, reject overlaps/duplicates; merge exactly adjacent intervals canonically. Empty tuple means declared fully closed covered period, NOT unknown coverage. Input must not mutate; output immutable.
Bridge reuses existing data_foundation.sessions.resolve_session, never copies its business logic. Restrict to exact registered normal-hours template: calendar_id cme-globex-metals-research-v1, timezone America/Chicago, session_model cme_globex_daily_break, regular_open17:00, regular_close16:00, break_start16:00/break_end17:00, closed_weekdays(5,), holidays(), early_closes(). Require nonempty version. Any unsupported/changed fields raise ValueError, never ignore overlays. No implicit file load or network. Require whole-minute coverage endpoints, and iterate UTC minutes in [start,end), grouping adjacent in-session minutes using resolver at minute start. This preserves DST via existing resolver. Return version from calendar, source containing explicit caller source plus hash of all calendar dataclass fields and marker RESEARCH_NORMAL_HOURS_NOT_EXECUTION_TRUTH; record exact resolved intervals in returned schedule, so behavior is hashable without claiming current timezone db is historical truth. Caller binds instrument explicitly; not proof GC/CFD equivalence.
- [x] Write failing behavior tests; use local function imports if module missing. RED must demonstrate missing feature, not a bad fixture.
```python
# Literal UTC expectation, Sept7 2026:
# coverage20:30..22:30 -> open intervals20:30..21:00 and22:00..22:30.
# FridaySept11 21:00..SundaySept13 22:00 -> empty; at22:00 reopens.
# SundayMar8 2026 opens22:00 UTC, Nov1 opens23:00 UTC (DST).
```
- [x] Implement smallest contract/bridge matching requirements. Tests: naive/submicrosecond rejection, timezone normalization, empty/invalid metadata, reversed coverage, outside/overlapping/adjacent intervals, tuple immutability, unsupported overlays/template fields; actual local config fixture bridge with no external calls.
- [x] Run python -m pytest tests/tree_replay/test_calendar.py -q; self-review; report RED/GREEN exact outputs and limitations. No other files or subagents.

## Task 2: Session-aware selection and EMA integration (parent)
Create trading_system/tree_replay/session_bars.py and tests/tree_replay/test_session_bars.py; modify ema.py minimally; add tests/tree_replay/test_session_ema.py.
```python
@dataclass(frozen=True, kw_only=True)
class SessionBarWindow(BarWindow):
    schedule_sha256: str
    calendar_available_at: datetime
    expected_bars: int
    missing_opens: tuple[datetime, ...]
    out_of_session_bars: int
    straddling_bars: int

select_session_bars(bars, *, instrument, timeframe, decision_time,
                    history_start, max_age_seconds, session_schedule) -> SessionBarWindow
# ema_snapshot adds optional session_schedule=None; old call behavior unchanged.
```
Use strict selector for ALL input validation and selection, not its contiguous-history blocker. Require schedule type and instrument match. history_start is explicit fixed UTC grid anchor and must align with epoch modulo timeframe; eligible input opens must align to same grid. No anchor or seed inferred from observed rows.
Blocker precedence: CALENDAR_UNAVAILABLE if schedule.available_at>T; CALENDAR_COVERAGE if not covering [history_start,T]; NO_EXPECTED_BARS if no fully open completed grid bars; HISTORY_INCOMPLETE if first expected open missing; HISTORY_GAP if any other expected open missing (including latest/delayed); otherwise wall-clock STALE after original freshness budget; elseNone.
Generate grid start=history_start while end<=T; expected iff WHOLE [start,end) contained in one canonical open interval. Whole closed bars excluded; overlapping-but-not-contained bars straddle and excluded. Both endpoints open does not suffice. Filter unavailable/future rows before classification/counting; report eligible excluded counts. No forward fill, reset, or skip of in-session holes. Missing_opens records all expected misses across entire seed history, not last15 or1600 (recursive seed depends on earlier history too). Retain expected observed bars for diagnostics even blocked. Coverage/unavailable blockers must not compute schedule membership.
Fingerprint canonical complete supplied schedule (dataclass JSON datetimeUTC; stable order) in window; original window hashing then covers schedule, selected prices/times and diagnostics. Supplied future schedule versions are caller responsibility; unavailable schedule blocks features. Calendar evidence refs/times not ML feature columns.
Known observations available_at=max(all selected bar availability,schedule.available_at). observed_at stays last selected close. Add calendar metadata with id/version/source/hash/expected/missing/excluded counts in calendar mode only; no source of default values for existing calls.
- [x] Write RED synthetic weekend bridge (ten closes1..10 => EMA5=8); missing interior/leading/trailing/delayed expected bars, full1600+ history gap, all closed, entire4h break, off-grid bars, coverage/unavailable, freshness equality +1us, future suffix invariance, invalidduplicate/mixed rows.
- [x] Implement selection, opt-in adapter change and numerical/availability/hash tests. Old tests must remain unchanged and pass.
- [x] Run focused tests, package diff with worker task and request independent task reviews.

## Task 3: Final verification and durable handoff
- [x] Independent combined review, source parity CLI, python -m pytest tests/tree_replay tests/tree_spec tests/data_foundation/test_sessions.py -q and python -m pytest -q --ignore-glob='*validator*'. No claim for excluded legacy validators.
- [x] Add docs/architecture/SESSION-EMA-ADAPTER-USAGE.md, update master section17 and AGENTS/README, exchange review/result. Record actual scope, synthetic evidence, source provenance and blockers.
- [x] Keep branch/local changes and scratch; no commit, push, merge or cleanup.
