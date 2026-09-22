## Task 1: Closed-bar as-of boundary (delegated sidecar)

Files: create only `trading_system/tree_replay/bars.py`, `tests/tree_replay/test_bars.py`, and assigned worker report. Parent owns package initializer.

Interfaces (frozen keyword-only dataclasses):

```python
class ClosedBar:
    instrument: str
    timeframe: str                  # 5m, 15m, 30m, 1h, 4h only
    opened_at: datetime
    closed_at: datetime
    available_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None             # explicit None allowed, never replaced by 0
    source: str

class BarWindow:
    instrument: str
    timeframe: str
    decision_time: datetime
    history_start: datetime
    max_age_seconds: int
    bars: tuple[ClosedBar, ...]
    blocker: str | None

def select_closed_bars(bars, *, instrument, timeframe, decision_time,
                       history_start, max_age_seconds) -> BarWindow:
    ...
```

- [ ] Write behavior tests first and run RED: future-close and future-availability exclusions; equality at T included; metadata validation and timezone/DST normalization; exact fixed duration; finite positive OHLC with low<=open/close<=high; finite nonnegative volume or None; bool/non-numeric rejection; explicit positive integer freshness; exact instrument/frame matching; duplicate opens rejected, out-of-order input deterministically sorted.
- [ ] Implement UTC-normalized ClosedBar validation; require nonempty trimmed source and exact non-whitespace venue:symbol. Accept native int/float prices and normalize to float; reject other numeric types/nonfinite overflow. All fields required.
- [ ] Selector consumes only ClosedBar inputs; validate request fields and history_start<=T. Reject mixed instrument/frame and duplicate opens, including unsupported revisions. Filter opened_at>=history_start, closed_at<=T and available_at<=T before calculation. No market calendar/resampling or latest-revision selection.
- [ ] Assign blockers in precedence: NO_HISTORY if empty; HISTORY_INCOMPLETE if first open != history_start; HISTORY_GAP if adjacent close != next open; STALE if T-last close exceeds max_age_seconds; otherwise None. Equality at freshness bound is permitted. Missing planned opening bars and delayed interior observations therefore cannot silently produce a compressed history. This strict contiguous-segment policy is intentionally not weekend-aware.
- [ ] Run `python -m pytest tests/tree_replay/test_bars.py -q`, self-review, report RED/GREEN. No subagents, outside files or commits.

Literal scenario: 5m bars 12:00-12:05 and 12:05-12:10, second available at12:11. At12:10 only first is available; freshness300 permits it. At12:11 both are available. At12:10:00.000001 with freshness300 the first is stale. Removing an interior bar from a longer window yields HISTORY_GAP, never a valid shorter rolling history.

