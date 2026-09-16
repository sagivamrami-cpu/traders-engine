# Task 1 brief

## Global Constraints

- Approved pinned source is authoritative; no invented thresholds, calendars, feeds or GC/spot equivalence.
- Observation cutoff is not decision time. No backdating maps or rewriting publication to force availability.
- Existing default APIs, validation and result/hash behavior remain unchanged.
- All readiness flags and public tradeable remain false; selected source pricing is not external market-watch admission or execution.
- No source/feed execution, real-data access/downloads, fitting, live changes, broker operations or deployment.
- Preserve dirty in-place branch; no commits, pushes, worktrees, cleanup or nested implementer agents.
- Main owns acceptance/master/README/AGENTS/tracker. Source Task2 can run alongside controller Task1 because their files are disjoint. Task3 depends on accepted1/2.
- Full objective remains B-I, not merely this producer. Outer market-watch windows/calendar/tracker/deduplication/arbitration remain explicit next work, never silently considered done.

## Task 1: Separate observation cutoff from actual decision clock

Owner: controller. Modify periods.py, frames.py and levelmap.py under trading_system/tree_replay/; create tests/tree_replay/test_closed_prefix.py and docs/architecture/CLOSED-BASE-PREFIX-USAGE.md. Do not alter existing default test assertions.

Interfaces add keyword-only closed_base_prefix:bool=False to aggregate_daily_asof,
build_frame_asof and build_levelmap_asof. Exact bool required (0/1 rejected).
_OfflineSource gains a final optional closed_base_prefix=False argument and passes
it into build_frame_asof; existing three-argument use remains valid. FrameSpec
and MapFrameRequest constructors are unchanged.

When false, retain original strict grid rejection, schema/calculation versions,
fields and hashes. When true, permit arbitrary aware microsecond T. Use UTC
epoch-aligned floor of min(T,period.end) for daily observation; frame cutoff is
floor(T/base_step). Publication/metadata/freshness use actual T, never the floor.
No caller-selectable earlier price cutoff that can hide a missing expected bar.

Daily period boundaries remain base aligned. Expected trading bars end at the
derived cutoff; all required closed history remains mandatory. T can lie after
period end and late-published completed bars remain usable at T. Current-period
selection/ownership in the frame builder uses actual T, never yesterday. Empty
current prefixes block as before. Frame calendar coverage remains required through
actual T. Intraday grid-fragment checks stop at derived cutoff; the existing
select_session_bars receives actual T and naturally requires every whole closed
base bar while checking real publication and age. No partial bar is fabricated.

Prefix-only versions/fields:
- period schema daily-period-prefix-asof-v1; calculation closed-lower-bars-daily-period-prefix-v1.
- frame schema historical-frame-prefix-asof-v1; calculation closed-base-frame-prefix-v1.
- map schema/calculation historical-levelmap-prefix-asof-v1; generated snapshot version matches.
- period/frame add observation_cutoff in canonical result/evidence only in prefix
  mode. Map trace available frame includes that cutoff only in prefix mode.
- Prefix policy participates via version/fields in hashes, even at a grid-aligned T.

Implementation arithmetic (shared small helper is permitted in periods.py):
```python
epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
cutoff = epoch + ((min(decision_time, period.closed_at)-epoch)//step)*step
# Eligibility remains bar.available_at <= decision_time, not <= cutoff.
```

- [ ] Write tests first. Literal two5m bars O100/H103/L99/C102 and O102/H107/L101/C106, at T00:10:30 with second publication00:10:20: expected O100/H107/L99/C106. Expected observation00:10, publication00:10:20 and cutoff00:10. A third final OHLC1000 bar closing00:15 is excluded. At00:10:19 second bar is missing and prices withheld; at exact publication it becomes usable. Never use a calculator as expected oracle.
- [ ] Verify strict default still rejects off-grid T; explicitFalse equals default byte-for-byte. Capture default fixture hashes before edits and assert they remain identical. True/False/0/1/None/string policy cases; naive/nanosecond T rejected; zero-age freshness checked against real T; exact370 and370+microsecond freshness where policies allow.
- [ ] Cover daily current rollover/no observations; missing expected history; known closures vs missing; metadata published between cutoff and T; calendar coverage ending at cutoff but before T;23/25h periods;1h/4h forming prefixes; future bar/period extension invariance; source session end at actual clock with old prices; delayed bar reappears only at publication. Test all three public interfaces and actual map prefix output, not helper-only arithmetic.
- [ ] Run python -m pytest tests/tree_replay/test_closed_prefix.py -q --tb=short for RED, implement and GREEN; then existing test_periods.py/test_frames.py/test_levelmap.py suites. Document versions/default compatibility and unsupported open-only/base-partial observations. Independent task review required.
