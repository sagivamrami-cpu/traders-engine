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
- [ ] Write failing behavior tests; use local function imports if module missing. RED must demonstrate missing feature, not a bad fixture.
```python
# Literal UTC expectation, Sept7 2026:
# coverage20:30..22:30 -> open intervals20:30..21:00 and22:00..22:30.
# FridaySept11 21:00..SundaySept13 22:00 -> empty; at22:00 reopens.
# SundayMar8 2026 opens22:00 UTC, Nov1 opens23:00 UTC (DST).
```
- [ ] Implement smallest contract/bridge matching requirements. Tests: naive/submicrosecond rejection, timezone normalization, empty/invalid metadata, reversed coverage, outside/overlapping/adjacent intervals, tuple immutability, unsupported overlays/template fields; actual local config fixture bridge with no external calls.
- [ ] Run python -m pytest tests/tree_replay/test_calendar.py -q; self-review; report RED/GREEN exact outputs and limitations. No other files or subagents.
