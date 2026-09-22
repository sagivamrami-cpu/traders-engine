# Session-aware EMA history

This opt-in offline extension distinguishes scheduled closures from missing bars.
It does not certify full tree replay, trading schedules across ten years, dataset
construction or a trained model. Existing strict contiguous calls are unchanged.

## Contracts and usage

`SessionInterval` represents a half-open open-market interval: [opened_at, closed_at).
`SessionSchedule` supplies the exact instrument, calendar/version/source, declared
coverage, publication time and open intervals. Intervals are normalized to UTC,
sorted and merged when adjacent; overlaps and out-of-coverage intervals are errors.
The complement of the intervals INSIDE coverage is explicitly declared closed.
An empty interval list therefore means closed, not unknown. Do not supply empty
intervals as a substitute for missing calendar evidence.

```python
from datetime import datetime, timezone
from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
from trading_system.tree_replay.ema import ema_snapshot

utc = timezone.utc
start = datetime(2026, 9, 7, 20, 30, tzinfo=utc)
end = datetime(2026, 9, 7, 22, 20, tzinfo=utc)
schedule = SessionSchedule(
    instrument="SYNTH:TEST", calendar_id="synthetic-example", version="v1",
    coverage_start=start, coverage_end=end, available_at=start,
    source="synthetic declared hours; not market evidence",
    intervals=(
        SessionInterval(opened_at=start, closed_at=datetime(2026, 9, 7, 21, tzinfo=utc)),
        SessionInterval(opened_at=datetime(2026, 9, 7, 22, tzinfo=utc), closed_at=end),
    ),
)
# bars must be supplied ClosedBar objects with matching instrument/timeframe,
# actual close/publication times and explicit provenance; no download occurs.
# result = ema_snapshot(
#     bars, snapshot_id="example", instrument="SYNTH:TEST", timeframe="5m",
#     history_start=start, decision_time=end, max_age_seconds=300,
#     session_schedule=schedule,
# )
```

The example times are synthetic and are not a claim about holiday trading hours.
Without `session_schedule`, the adapter retains the original strict contiguous policy.

## Selection rules

- Explicit history_start and eligible bar opens must align to a fixed UTC grid
  (epoch alignment at 5m, 15m, 30m, 1h or 4h). No broker bar alignment is inferred.
- Decision-time filtering uses BOTH bar close time and availability time.
- The schedule must have been available by the decision and cover the entire
  interval from history_start through the decision, including any current partial slot.
- A completed bar is expected only if its WHOLE interval is open. A four-hour
  bar crossing a one-hour break is excluded even if its endpoints are both open.
- Eligible rows outside sessions or straddling a closure are excluded and counted
  separately. Nothing is forward-filled or synthesized.
- Every expected bar from the seed anchor through the latest completed slot
  must be present and available. A late or missing last slot is a gap, even if
  the previous price remains within the freshness budget.
- Scheduled closures do not reset the EMA seed or introduce synthetic bars.
  Fixed-duration bars crossing closures are dropped, not shortened.
- Freshness remains wall-clock elapsed time. A complete window can still be
  STALE during a long closure. No trading-time freshness budget is inferred.

The entire recursive seed history matters: checking only the last15 bars, or even
only the last1600, can miss an earlier gap that changes the EMA. The existing
2*period visibility warmup remains unchanged (EMA800 needs1600 accepted bars).
History selection is not permission to reinterpret the original desk's partial
bars, session anchoring or instrument.

## Blockers and provenance

Blocker precedence is CALENDAR_UNAVAILABLE, CALENDAR_COVERAGE, NO_EXPECTED_BARS,
HISTORY_INCOMPLETE (first expected bar missing), HISTORY_GAP (any other missing),
STALE, or no blocker. Invalid metadata raises ValueError before that classification.
Unavailable/coverage failures do not calculate membership; zero counts in those
reports mean not evaluated, not confirmed zero missing bars.

All feature values are null on a blocker (STALE or UNAVAILABLE); warmup remains
UNKNOWN. None of these optional observations becomes an entry veto. The inherited
eligible flag is still only required-field completeness, never readiness.

Calendar-mode snapshots add a metadata-only calendar object: identity, version,
source, coverage, availability, schedule hash, expected bars, all missing opens,
and eligible out-of-session/straddling row counts. The window hash includes this
schedule fingerprint and selected bar inputs. Known feature availability is the
latest of ALL selected bar publication times and the schedule's publication time.
Observed time remains the last selected bar close. Valid future bar suffixes do
not change the output at the same decision.

The schedule fingerprint covers the complete supplied schedule, not just today's
open slots. Freeze the selected schedule version/coverage for reproducible replay.
Callers must select the historically available schedule version; this is not an
announcement/revision ledger. Evidence text and metadata are NOT ML features.
A content hash records identity, not the truth or licensing of the supplied data.

## Bridge to the existing registered calendar

`schedule_from_research_calendar(calendar, *, instrument, coverage_start,
coverage_end, available_at, source)` reuses `data_foundation.sessions.resolve_session`.
Its only supported input is the registered GC normal-hours template:
America/Chicago, Sunday-Friday,17:00 open/16:00 close with16:00-17:00 daily break.
It enumerates UTC minutes and builds explicit intervals, preserving timezone/DST
handling through the existing resolver. Coverage endpoints must be whole minutes.

Unsupported represented SessionCalendar settings and nonempty holidays/early_closes are
rejected, not silently ignored. It does not apply holiday overlays, halts, special
hours or verify historical eras. Use separately justified explicit intervals for
those cases; no such historical interval table is supplied by this change.
The source records the caller reference, calendar-content hash and the marker
RESEARCH_NORMAL_HOURS_NOT_EXECUTION_TRUTH. The passed instrument is an explicit
caller binding, not proof of GC/CFD or venue equivalence.

The existing YAML loader does not retain every raw configuration field (for
example special_sessions). This bridge validates the supplied SessionCalendar,
not the original YAML or evidence manifest. Its calendar hash covers dataclass
fields only. A future production loader must validate raw overlays before any
lossy conversion; this bridge cannot discover fields the caller discarded.

Existing calendar/missing-bar policies and data approvals are NOT changed. The
old30m builder and its15-bar lookback are not imported into this pipeline.
The bridge is a bounded research helper, not an optimized multi-year schedule
service. Neither it nor repeated full-window EMA calculation provides checkpoint/
resume or incremental performance guarantees.

## Verification and next step

Synthetic tests cover normal breaks, weekends, DST openings, all five timeframes,
an internal4h closure, old seed gaps, publication boundaries, hashes and numerics.
Both ready_for_replay and ready_for_training remain false; execution_truth is false.
Before real data: reconcile historical schedule/feed/era coverage, actual bar
alignment and partial-bar behavior with the selected candidate producer. Continue
the source-family/consumer mapping; do not label generic per-bar directions as
tree-generated trade candidates.
