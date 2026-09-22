## Task 2: Causal frame construction for every map request

Owner: controller, parallel with Task 1 source work; independent task review required. Files: trading_system/tree_replay/frames.py; tests/tree_replay/test_frames.py; docs/architecture/HISTORICAL-FRAMES-USAGE.md.

**Interfaces (frozen keyword-only dataclasses):**

```python
class LabeledDailyPeriod:
    period: DailyPeriod
    source_index_at: datetime

class FrameSpec:
    frame_id: str
    instrument: str
    timeframe: str                 # 1d or existing fixed timeframe
    base_timeframe: str            # existing ClosedBar timeframe
    history_start: datetime
    available_at: datetime         # frame/grid metadata publication
    source: str
    version: str
    bars: tuple[ClosedBar, ...]
    session_schedule: SessionSchedule
    max_age_seconds: int           # explicit caller policy
    grid_anchor: datetime | None = None
    periods: tuple[LabeledDailyPeriod, ...] = ()

def build_frame_asof(spec: FrameSpec, *, decision_time: datetime) -> dict: ...
```

Reuse existing text/numeric/UTC/exact-symbol/bar/calendar validators. Reject wrong types, malformed metadata, duplicate base opens, identity/timeframe mismatches, non-integer/nonnegative age policy, and finer-than-microsecond timestamps. Validate all input bars, including future bars, but never include unavailable/future prices in selected rows/hash. Daily periods must have distinct IDs, disjoint chronological intervals and strictly increasing distinct source labels; canonicalize tuple order by period open. Validate every period's exact instrument. Intraday requires empty periods, target duration >= base duration, base-aligned explicit grid_anchor and history_start aligned to that target grid. Daily requires grid_anchor None and nonempty periods. history_start and decision_time must align to base UTC grid; decision_time cannot precede history_start. Calendar identity/coverage and metadata availability are mandatory.

Result: schema_version historical-frame-asof-v1; calculation_version closed-base-frame-v1; frame_id/instrument/timeframe/base_timeframe/decision_time; status AVAILABLE or BLOCKED; blocker; rows; observed_at; available_at; diagnostics; evaluation_sha256; both readiness flags false. Rows are canonical JSON dictionaries with source_index_at, opened_at, closed_at, observed_at, available_at, state FORMING/CLOSED, open/high/low/close/volume. Blocked rows=[] and observation/publication null. Include policy/selected metadata/base bars/diagnostics in hash, excluding future base payloads and future daily periods. Metadata source_index_at is a label, not observation/publication time, and may be a future bucket label known under published metadata. Source interval labels must not be substituted for actual availability.

Daily algorithm: select the period containing T under [open,close); absent -> CURRENT_PERIOD_UNCOVERED. history_start must equal the first selected period's open. Coverage from history_start through T must be fully covered by calendar evidence, and every active session fragment must belong to the selected period union; an omitted trading period -> PERIOD_SEQUENCE_GAP, not compressed history. For each selected period use existing aggregate_daily_asof with only that bucket's bars after global validation. Skip a completed all-closed calendar period with NO_EXPECTED_BARS; a current period with no observations remains blocked. Propagate any other missing/delayed/unresolved period blocker and withhold the whole frame. Last row must belong to the actual current period, never yesterday masquerading as today. Enforce max_age against final selected observed_at. Assign each row's supplied source label separately from actual period boundaries/observation/publication. Distinguish future-extension invariance from calendar/provenance revisions.

Intraday algorithm: use select_session_bars to require every expected available base bar from history_start through T. Before selection reject/withhold unresolved active session fragments not aligned to base grid (FRAME_GRID_UNRESOLVED); do not compress gaps. Group selected base bars by `grid_anchor + ((open-grid_anchor)//target_duration)*target_duration`. Per group derive firstopen/maxhigh/minlow/lastclose; volume remains None if any input volume missing, otherwise finite sum (overflow raises ValueError). Only final bucket can be FORMING, and uses only its closed base prefix. Omit buckets with no scheduled/observed bars, not fabricate OHLC. Keep source index at bucket open; scheduled close is not its observation time. Inherit supplied schedule selector's fixed base-grid requirement. No silent lower-frame upsampling or default daily rollover.

- [ ] Write literal tests for daily current OHLC110/115/95 etc versus future1000; late availability; omitted trading day vs known closure; future period/bar extension hash invariance; current period boundary/no observation; labels crossing UTC day/month independent from availability; 23/25h periods; full coverage/instrument/type/duplicate errors; 5m->15m/1h/4h forming/final rows and non-UTC-offset grid; closure/gap/freshness/missing-volume/overflow; metadata unavailable. Run RED before implementing.
- [ ] Implement and run python -m pytest tests/tree_replay/test_frames.py -q --tb=short. Avoid quadratic rescanning of all base bars per period: partition after one structural-validation pass.
- [ ] Document actual supported precision and source evidence boundaries; independent task review and controller verification, no commits.

