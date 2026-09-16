# Daily-period as-of observations

This component reconstructs a single supplied daily period's OHLCV from closed
lower-timeframe bars. It does not define a broker day, fetch prices, construct
the complete historical level map or certify replay/training readiness.

```python
from trading_system.tree_replay.periods import DailyPeriod, aggregate_daily_asof

period = DailyPeriod(
    instrument="OANDA:XAUUSD", period_id="historical-period-reference",
    opened_at=day_open, closed_at=day_end, available_at=boundary_publication,
    source="period-boundary-evidence", version="boundary-policy-version",
)
result = aggregate_daily_asof(
    lower_bars, period=period, decision_time=decision_time,
    base_timeframe="5m", session_schedule=supplied_schedule,
)
```

All variables above require historical evidence supplied by the caller. Period
and calendar identity must match every input ClosedBar. Boundaries and times are
UTC-aware and microsecond-exact; a daily period need not last24 elapsed hours.
No rollover, timezone, holiday, correction, broker or GC/spot equivalence is
inferred. Metadata does not independently prove the evidence is genuine.

## Time and missing-data contract

The price cutoff is min(decision_time,period.closed_at); publication cutoff is
decision_time. Thus a closed historical day's final bar published late is missing
at the day's end, but may be consumed at a later decision with its true publication
time. Historical completed days do not expire just because they are old.

Period endpoints and the price cutoff must align to the base timeframe's fixed
UTC grid. Only decisions at complete lower-bar boundaries are supported while
the day is forming. This is not support for partly observed5m bars or an exact
open-only tick at the start of a new day. A period with no completed expected bar
returns unavailable, not a manufactured current open or zero-valued OHLC.

Every open session interval is clipped to the price window. If a clipped interval
has an off-grid edge, PERIOD_GRID_UNRESOLVED blocks output: a straddling fragment
cannot be silently omitted from the day's high/low. Every expected bar must be
present and published by decision time. Scheduled closures do not count as gaps;
known out-of-session bars are excluded and counted, not added to OHLCV.

Malformed inputs raise ValueError, including duplicate opens/revisions or mixed
bar identities even outside price selection. Missing volume produces null volume;
genuine zero volume remains0. Overflow is an error, never infinity or null.

## Results

FORMING and CLOSED contain the first open, maximum high, minimum low, final close
and sum of known volumes. observed_at is the final selected lower-bar close;
available_at is the maximum publication of used bars, period metadata and calendar.
BLOCKED has null ohlcv, observed_at and available_at. Its blocker distinguishes
PERIOD_UNAVAILABLE, CALENDAR_UNAVAILABLE, CALENDAR_COVERAGE,
PERIOD_GRID_UNRESOLVED, NO_EXPECTED_BARS, HISTORY_INCOMPLETE and HISTORY_GAP.
The first applicable blocker is returned, not every possible issue.

The payload retains period identity, base timeframe, decision time, expected-bar
count, missing opens, excluded-bar count and evaluation_sha256. The hash binds
selected price evidence, period/calendar metadata, decision and calculation
version; it excludes future/unpublished bars and bars belonging to later periods.
Metadata and hashes are for audit, not model feature columns. Both readiness flags
remain false for all results. JSON output contains no nonfinite numeric values.

These outputs are inputs toward original daily/weekly/monthly range calculations.
They do not prove the source period sequence is complete, reconstruct source
corrected broker frames or approve direct use as a LevelSnapshot. Complete source
map assembly, other feature families, admission and outcomes are still required.
Run `python -m pytest tests/tree_replay/test_periods.py -q` for synthetic coverage.
