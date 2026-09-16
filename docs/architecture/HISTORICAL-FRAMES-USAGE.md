# Historical frames for the original level map

`trading_system.tree_replay.frames` builds source-shaped daily and intraday
frames from supplied `ClosedBar` observations, calendars and grid/period metadata.
It does not load real data, infer broker calendars, substitute instruments or
certify historical vendor provenance. Both readiness flags remain false.

## Inputs and precision

`FrameSpec` is immutable. Provide a frame ID, exact venue:symbol, target/base
timeframes, explicit history start, source/version/metadata publication time,
a tuple of closed base bars, a supplied `SessionSchedule`, and an integer
nonnegative maximum elapsed age. Targets are 5m/15m/30m/1h/4h or1d; bases use the
existing fixed-duration ClosedBar contract. No upsampling is allowed.

Each frame is rebuilt at an explicit UTC-aware, microsecond-exact decision time
on the base grid. Only base bars closed and published by that time contribute.
Input types, identities and duplicate opens are checked even outside the selected
window. Input order is canonicalized; revisions must be resolved explicitly
before constructing a FrameSpec. Missing volume remains missing, not zero.

For intraday frames, supply `grid_anchor` aligned to the base grid and start
history on a target-grid boundary. This can represent, for example, an explicit
four-hour origin at22:00 UTC; midnight is not assumed. Higher-timeframe bars are
rebuilt from the available base prefix, including a final FORMING row when its
scheduled close lies after the decision. Every expected base bar must be present
under the supplied calendar. An unresolved fragment of an active session blocks
the frame; known closures do not create fake bars. The inherited selector requires
all selected base opens to align to the fixed UTC base grid.

The inherited bar selector accepts only positive freshness budgets. Internally
the adapter passes at least one second to that selector and then enforces the
exact supplied frame budget, including zero. No one-second relaxation of the
output contract occurs. This is compatibility plumbing, not a trading threshold.

## Daily sequence and labels

For1d, leave grid_anchor unset and provide a tuple of `LabeledDailyPeriod` objects.
Each contains an existing `DailyPeriod` and a separate `source_index_at` label.
Periods have unique IDs, nonoverlapping chronological intervals and strictly
increasing unique source labels. Variable elapsed durations such as23/25 hours
are supported when representable on the selected base grid.

The period containing the decision under [open,close) must be supplied. At a new
period's exact open, an empty prefix is unavailable; yesterday is never reused
as the current day. History starts at the first selected period open. Every
active calendar fragment through the decision must have a period owner. Omitting
an actual trading day blocks with PERIOD_SEQUENCE_GAP. Completed periods declared
fully closed by the calendar may be skipped without inventing OHLC. A current
period with no known observations remains blocked.

Each day uses the accepted `aggregate_daily_asof` algorithm. Bars are partitioned
once after structural validation rather than rescanned across every period.
One missing/delayed required bar blocks the entire frame, including an otherwise
valid current row. Metadata availability, full calendar coverage and the final
observation's age are also checked.

Source labels are bucket identities for the original weekly/monthly resampling;
they are not bar publication timestamps. A label may lie after the decision
when its meaning was supplied by metadata already available at the decision.
Actual period bounds, latest observed base close and publication remain separate
fields. Supplying an invented label or dishonest provenance is not made valid by
passing structural checks.

## Output and evidence

Call `build_frame_asof(spec, decision_time=...)`.

AVAILABLE results contain ordered JSON rows with source_index_at, opened_at,
closed_at, observed_at, available_at, state, open/high/low/close/volume. A future
scheduled close on a FORMING row is not future price information. BLOCKED results
contain no rows and null observation/publication fields, with a specific blocker.
Diagnostics preserve period/selection evidence for research audit, not an
automatic model feature allowlist.

The SHA256 covers selected evidence, policies, supplied metadata/calendar and
calculation version `closed-base-frame-v1`. Future/unpublished base payloads and
later daily periods do not affect an earlier selected frame. A calendar, label,
policy or selected price revision can legitimately change its hash. Missing
history is not compressed into a shorter supposedly complete EMA or range seed.

Run:

```powershell
python -m pytest tests/tree_replay/test_frames.py -q --tb=short
```

Supported precision stops at a completed base bar. An opening tick alone or a
partly observed base bar is not reconstructed from its eventual final values.
For example, with5m history alone, an exact newly opened session price may stay
unavailable until the first5m bar closes. That limitation must remain visible to
map consumers and full replay acceptance, not be reported as a trading failure.
Full source producer admission/arbitration, simulation, dataset generation and
training are separate requirements in the master plan.
