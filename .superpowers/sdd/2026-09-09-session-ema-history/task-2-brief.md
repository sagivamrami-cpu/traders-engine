- Continue approved master design sections5,10,12,16; no new trader thresholds.
- Local existing branch; preserve prior dirty work; no commits, push, worktree or cleanup.
- Synthetic tests only; no raw feeds, vendor calls, dataset generation, training or live effects.
- Existing strict selector remains unchanged. Calendar-aware mode is opt-in.
- Closed fixed-duration bars, microsecond-exact UTC times only. No resampling or partial bars.
- No implicit instrument conversion, holiday inference or approval. Readiness flags stay false.
- Schedules are explicit supplied research evidence, not independently verified historical truth.
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
- [ ] Write RED synthetic weekend bridge (ten closes1..10 => EMA5=8); missing interior/leading/trailing/delayed expected bars, full1600+ history gap, all closed, entire4h break, off-grid bars, coverage/unavailable, freshness equality +1us, future suffix invariance, invalidduplicate/mixed rows.
- [ ] Implement selection, opt-in adapter change and numerical/availability/hash tests. Old tests must remain unchanged and pass.
- [ ] Run focused tests, package diff with worker task and request independent task reviews.
