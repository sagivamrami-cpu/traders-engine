# Task2 working-tree diff
HEAD unchanged c1b6071633c55376c64f0a98ece843706f420f49; before/after snapshots include untracked code.


diff --git a/trading_system/tree_replay/session_bars.py b/trading_system/tree_replay/session_bars.py
--- /dev/null
+++ b/trading_system/tree_replay/session_bars.py
@@ -0,0 +1,108 @@
+"""Opt-in calendar-aware closed-bar selection; supplied schedules are evidence, not approval."""
+from bisect import bisect_right
+from dataclasses import asdict, dataclass
+from datetime import datetime, timedelta, timezone
+import hashlib
+import json
+
+from .bars import BarWindow, _DURATIONS, select_closed_bars
+from .calendar import SessionSchedule
+
+
+@dataclass(frozen=True, kw_only=True)
+class SessionBarWindow(BarWindow):
+    schedule_sha256: str
+    calendar_available_at: datetime
+    expected_bars: int
+    missing_opens: tuple[datetime, ...]
+    out_of_session_bars: int
+    straddling_bars: int
+
+
+def select_session_bars(bars, *, instrument, timeframe, decision_time,
+                        history_start, max_age_seconds, session_schedule) -> SessionBarWindow:
+    """Require every expected closed bar across the entire explicitly anchored seed.
+
+    Coverage includes scheduled closures. A bar that overlaps a closure is not
+    a complete open-session bar, even when its two endpoints are open. Missing
+    expected bars are never compressed away. Freshness is elapsed wall time.
+    """
+    base = select_closed_bars(bars, instrument=instrument, timeframe=timeframe,
+                             decision_time=decision_time, history_start=history_start,
+                             max_age_seconds=max_age_seconds)
+    if not isinstance(session_schedule, SessionSchedule):
+        raise ValueError("session_schedule must be a SessionSchedule")
+    schedule = session_schedule
+    if schedule.instrument != instrument:
+        raise ValueError("schedule must match exact instrument")
+    step = _DURATIONS[timeframe]
+    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
+    if (base.history_start - epoch) % step:
+        raise ValueError("history_start must align to the fixed UTC grid")
+    if any((b.opened_at - epoch) % step for b in base.bars):
+        raise ValueError("selected bar opens must align to the fixed UTC grid")
+
+    encoded = json.dumps(asdict(schedule), sort_keys=True, separators=(",", ":"),
+                         default=lambda value: value.isoformat().replace("+00:00", "Z"))
+    schedule_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
+    expected = []
+    missing = ()
+    selected = base.bars
+    outside = straddling = 0
+
+    if schedule.available_at > base.decision_time:
+        blocker = "CALENDAR_UNAVAILABLE"
+    elif schedule.coverage_start > base.history_start or schedule.coverage_end < base.decision_time:
+        blocker = "CALENDAR_COVERAGE"
+    else:
+        intervals = schedule.intervals
+        openings = tuple(i.opened_at for i in intervals)
+
+        def membership(start, end):
+            index = bisect_right(openings, start) - 1
+            if index >= 0:
+                interval = intervals[index]
+                if end <= interval.closed_at:
+                    return "OPEN"
+                if start < interval.closed_at:
+                    return "STRADDLE"
+            if index + 1 < len(intervals) and intervals[index + 1].opened_at < end:
+                return "STRADDLE"
+            return "CLOSED"
+
+        start = base.history_start
+        # Difference comparison avoids overflowing datetime at the upper boundary.
+        while base.decision_time - start >= step:
+            end = start + step
+            if membership(start, end) == "OPEN":
+                expected.append(start)
+            start = end
+        present = {}
+        for b in base.bars:
+            kind = membership(b.opened_at, b.closed_at)
+            if kind == "OPEN":
+                present[b.opened_at] = b
+            elif kind == "STRADDLE":
+                straddling += 1
+            else:
+                outside += 1
+        selected = tuple(present[t] for t in expected if t in present)
+        missing = tuple(t for t in expected if t not in present)
+        if not expected:
+            blocker = "NO_EXPECTED_BARS"
+        elif expected[0] not in present:
+            blocker = "HISTORY_INCOMPLETE"
+        elif missing:
+            blocker = "HISTORY_GAP"
+        elif (base.decision_time - selected[-1].closed_at) // timedelta(microseconds=1) > max_age_seconds * 1_000_000:
+            blocker = "STALE"
+        else:
+            blocker = None
+
+    return SessionBarWindow(
+        instrument=instrument, timeframe=timeframe, decision_time=base.decision_time,
+        history_start=base.history_start, max_age_seconds=max_age_seconds,
+        bars=selected, blocker=blocker, schedule_sha256=schedule_hash,
+        calendar_available_at=schedule.available_at, expected_bars=len(expected),
+        missing_opens=missing, out_of_session_bars=outside, straddling_bars=straddling,
+    )

diff --git a/tests/tree_replay/test_session_bars.py b/tests/tree_replay/test_session_bars.py
--- /dev/null
+++ b/tests/tree_replay/test_session_bars.py
@@ -0,0 +1,174 @@
+"""Synthetic interval schedules; no market data or calendar inference."""
+from dataclasses import replace
+from datetime import datetime, timedelta, timezone
+
+import pandas as pd
+import pytest
+
+from trading_system.tree_replay.bars import ClosedBar
+
+UTC = timezone.utc
+T0 = datetime(2026, 9, 7, 20, 30, tzinfo=UTC)
+STEP = timedelta(minutes=5)
+
+
+def bar(t, close=128, tf="5m", **changes):
+    duration = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}[tf]
+    end = t + timedelta(minutes=duration)
+    values = dict(instrument="SYNTH:TEST", timeframe=tf, opened_at=t,
+                  closed_at=end, available_at=end, open=close, high=close+1,
+                  low=close-0.5, close=close, volume=None, source="synthetic")
+    return ClosedBar(**(values | changes))
+
+
+def schedule(intervals=None, **changes):
+    from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
+    if intervals is None:
+        intervals = ((T0, T0 + 6*STEP),
+                     (T0 + 18*STEP, T0 + 30*STEP))
+    values = dict(instrument="SYNTH:TEST", calendar_id="synthetic",
+                  version="v1", source="synthetic declared hours",
+                  coverage_start=T0, coverage_end=T0+30*STEP, available_at=T0,
+                  intervals=tuple(SessionInterval(opened_at=a, closed_at=b)
+                                  for a, b in intervals))
+    return SessionSchedule(**(values | changes))
+
+
+def select(bars, **changes):
+    from trading_system.tree_replay.session_bars import select_session_bars
+    values = dict(instrument="SYNTH:TEST", timeframe="5m", history_start=T0,
+                  decision_time=T0+20*STEP, max_age_seconds=300,
+                  session_schedule=schedule())
+    return select_session_bars(bars, **(values | changes))
+
+
+def complete_bars():
+    return tuple(bar(T0+i*STEP) for i in (*range(6), 18, 19))
+
+
+def test_scheduled_break_is_not_missing_history():
+    r = select(complete_bars())
+    assert r.blocker is None
+    assert r.expected_bars == 8
+    assert r.missing_opens == ()
+    assert len(r.bars) == 8
+
+
+@pytest.mark.parametrize("missing,blocker", [(0,"HISTORY_INCOMPLETE"),
+                                            (3,"HISTORY_GAP"),(7,"HISTORY_GAP")])
+def test_missing_leading_interior_and_latest_expected_bar_blocks(missing, blocker):
+    bars = complete_bars()
+    r = select(bars[:missing]+bars[missing+1:])
+    assert r.blocker == blocker
+    assert r.missing_opens == (bars[missing].opened_at,)
+
+
+def test_delayed_expected_bar_is_missing_until_publication():
+    bars = list(complete_bars())
+    bars[-1] = replace(bars[-1], available_at=T0+20*STEP+timedelta(microseconds=1))
+    r = select(bars)
+    assert r.blocker == "HISTORY_GAP"
+    assert r.missing_opens == (T0+19*STEP,)
+    assert select(bars, decision_time=T0+20*STEP+timedelta(microseconds=1)).blocker is None
+
+
+def test_no_observed_bars_in_open_schedule_is_incomplete_not_closed():
+    r = select([])
+    assert r.blocker == "HISTORY_INCOMPLETE"
+    assert r.expected_bars == 8
+    assert len(r.missing_opens) == 8
+
+
+def test_all_closed_schedule_is_not_unknown_or_incomplete():
+    r = select([], session_schedule=schedule(()))
+    assert r.blocker == "NO_EXPECTED_BARS"
+    assert r.expected_bars == 0
+
+
+def test_out_of_session_rows_are_counted_and_never_used():
+    r = select((*complete_bars(), bar(T0+10*STEP, close=999999)))
+    assert r.blocker is None
+    assert r.out_of_session_bars == 1
+    assert all(b.close == 128 for b in r.bars)
+
+
+def test_four_hour_bar_with_open_endpoints_but_internal_break_is_excluded():
+    start = datetime(2026, 9, 7, 20, tzinfo=UTC)
+    end = start+timedelta(hours=4)
+    sc = schedule(((start,start+timedelta(hours=1)),(start+timedelta(hours=2),end)),
+                  coverage_start=start, coverage_end=end)
+    r = select([bar(start,tf="4h")], timeframe="4h", history_start=start,
+               decision_time=end, session_schedule=sc)
+    assert r.blocker == "NO_EXPECTED_BARS"
+    assert r.straddling_bars == 1
+    assert r.out_of_session_bars == 0
+    assert r.bars == ()
+
+
+@pytest.mark.parametrize("tf", ["5m","15m","30m","1h","4h"])
+def test_full_interval_membership_and_close_boundary(tf):
+    start = datetime(2026, 9, 7, 0, tzinfo=UTC)
+    b = bar(start, tf=tf)
+    sc = schedule(((start,b.closed_at),),coverage_start=start,coverage_end=b.closed_at,
+                  available_at=start)
+    r = select([b],timeframe=tf,history_start=start,decision_time=b.closed_at,
+               session_schedule=sc)
+    assert r.blocker is None
+    assert r.expected_bars == 1
+
+
+@pytest.mark.parametrize("field,value", [
+    ("coverage_start", T0+STEP),("coverage_end",T0+19*STEP),
+    ("available_at",T0+21*STEP)])
+def test_uncovered_or_not_yet_known_calendar_blocks(field,value):
+    # Empty intervals allow independently exercising each coverage boundary.
+    sc = schedule((), **{field:value})
+    r = select(complete_bars(), session_schedule=sc)
+    assert r.blocker == ("CALENDAR_UNAVAILABLE" if field=="available_at" else "CALENDAR_COVERAGE")
+    assert r.expected_bars == 0
+
+
+def test_explicit_freshness_is_wall_clock_even_during_closure():
+    bars = complete_bars()[:6]
+    at = T0+7*STEP
+    assert select(bars,decision_time=at).blocker is None
+    assert select(bars,decision_time=at+timedelta(microseconds=1)).blocker == "STALE"
+    assert select(bars,decision_time=at,max_age_seconds=10**30).blocker is None
+
+
+@pytest.mark.parametrize("kind",["anchor","bar","identity","duplicate","schedule","nanosecond"])
+def test_invalid_metadata_is_not_silently_reinterpreted(kind):
+    bars = complete_bars()
+    changes = {}
+    if kind == "anchor": changes["history_start"] = T0+timedelta(seconds=1)
+    if kind == "bar": bars = (*bars,bar(T0+timedelta(seconds=1)))
+    if kind == "identity": changes["session_schedule"] = schedule(instrument="SYNTH:OTHER")
+    if kind == "duplicate": bars = (*bars,bars[0])
+    if kind == "schedule": changes["session_schedule"] = {}
+    if kind == "nanosecond": changes["decision_time"] = pd.Timestamp(T0+20*STEP)+pd.Timedelta(1,"ns")
+    with pytest.raises(ValueError):
+        select(bars,**changes)
+
+
+def test_future_rows_and_input_order_cannot_change_current_window():
+    original = complete_bars()
+    later = bar(T0+25*STEP,close=123456)
+    assert select((*reversed(original),later)) == select(original)
+    assert tuple(b.opened_at for b in original) == tuple(sorted(b.opened_at for b in original))
+
+
+def test_schedule_fingerprint_changes_with_provenance_not_interval_input_order():
+    a = schedule()
+    b = replace(a,intervals=tuple(reversed(a.intervals)))
+    assert select(complete_bars(),session_schedule=a) == select(complete_bars(),session_schedule=b)
+    assert select(complete_bars(),session_schedule=replace(a,source="changed evidence")).schedule_sha256 != select(complete_bars()).schedule_sha256
+
+
+def test_old_gap_outside_last_1600_bars_still_blocks_recursive_seed():
+    end = T0+1700*STEP
+    sc = schedule(((T0,end),),coverage_end=end)
+    bars = tuple(bar(T0+i*STEP) for i in range(1700) if i != 2)
+    r = select(bars,session_schedule=sc,decision_time=end)
+    assert r.blocker == "HISTORY_GAP"
+    assert r.missing_opens == (T0+2*STEP,)
+    assert r.expected_bars == 1700

diff --git a/tests/tree_replay/test_session_ema.py b/tests/tree_replay/test_session_ema.py
--- /dev/null
+++ b/tests/tree_replay/test_session_ema.py
@@ -0,0 +1,122 @@
+"""EMA integration against synthetic schedules; no actual-market performance claims."""
+from dataclasses import replace
+from datetime import timedelta, datetime, timezone
+from pathlib import Path
+
+import pytest
+
+from test_session_bars import T0, STEP, bar, schedule
+from trading_system.tree_replay.ema import ema_snapshot
+
+
+def ten_bars():
+    # Six bars, declared closure, then four bars: closes1..10 give EMA5=8.
+    return tuple(bar(T0+i*STEP, close=c)
+                 for i,c in zip((*range(6),18,19,20,21),range(1,11)))
+
+
+def test_calendar_mode_requires_a_valid_schedule_contract():
+    with pytest.raises(ValueError):
+        snapshot(ten_bars(), session_schedule={})
+
+
+def snapshot(bars, **changes):
+    params = dict(snapshot_id="synthetic-session", instrument="SYNTH:TEST", timeframe="5m",
+                  history_start=T0, decision_time=T0+22*STEP, max_age_seconds=300)
+    return ema_snapshot(bars, **(params | changes))
+
+
+def test_explicit_calendar_enables_same_formula_across_closure_without_changing_strict_default():
+    bars = ten_bars()
+    strict = snapshot(bars)
+    assert strict["window_blocker"] == "HISTORY_GAP"
+    r = snapshot(bars,session_schedule=schedule())
+    assert r["window_blocker"] is None
+    assert r["features"]["chartdesk.5m.ema5"] == pytest.approx(8)
+    assert r["features"]["chartdesk.5m.ema5_delta5"] == pytest.approx(5)
+    assert r["calendar"]["expected_bars"] == 10
+    assert r["calendar"]["missing_opens"] == []
+    assert r["coverage"]["selected_bars"] == 10
+    assert "calendar" not in strict
+    assert r["ready_for_replay"] is False
+    assert r["ready_for_training"] is False
+
+
+def test_calendar_and_all_bar_dependencies_control_feature_availability():
+    bars = list(ten_bars())
+    later = T0+22*STEP+timedelta(seconds=2)
+    bars[0] = replace(bars[0],available_at=later-timedelta(seconds=1))
+    sc = schedule(available_at=later)
+    r = snapshot(bars,session_schedule=sc,decision_time=later)
+    provenance = r["provenance"]["chartdesk.5m.ema5"]
+    assert provenance["observed_at"] == "2026-09-07T22:20:00Z"
+    assert provenance["available_at"] == "2026-09-07T22:20:02Z"
+    r2 = snapshot(bars,session_schedule=schedule(),decision_time=later)
+    assert r2["provenance"]["chartdesk.5m.ema5"]["available_at"] == "2026-09-07T22:20:01Z"
+
+
+@pytest.mark.parametrize("reason",["missing","unpublished","coverage","closed","stale"])
+def test_calendar_blockers_never_export_numerical_features(reason):
+    bars = ten_bars()
+    sc = schedule()
+    changes = {}
+    if reason=="missing": bars=bars[:2]+bars[3:]
+    if reason=="unpublished": sc=replace(sc,available_at=T0+23*STEP)
+    if reason=="coverage": sc=schedule((),coverage_end=T0+21*STEP)
+    if reason=="closed": sc=schedule(())
+    if reason=="stale":
+        sc=schedule(((T0,T0+6*STEP),(T0+18*STEP,T0+22*STEP)))
+        changes["decision_time"]=T0+23*STEP+timedelta(microseconds=1)
+    r=snapshot(bars,session_schedule=sc,**changes)
+    assert all(v is None for v in r["features"].values())
+    assert set(r["availability"].values()) == ({"STALE"} if reason=="stale" else {"UNAVAILABLE"})
+    assert r["ready_for_training"] is False
+
+
+def test_future_suffix_and_snapshot_mutation_do_not_change_current_values():
+    bars=ten_bars()
+    sc=schedule()
+    original=snapshot(bars,session_schedule=sc)
+    again=snapshot((*bars,bar(T0+26*STEP,close=999999)),session_schedule=sc)
+    assert original==again
+    again["features"]["chartdesk.5m.ema5"]=42
+    assert snapshot(bars,session_schedule=sc)==original
+
+
+def test_calendar_evidence_is_in_hash_not_model_feature_columns():
+    bars=ten_bars()
+    a=snapshot(bars,session_schedule=schedule())
+    b=snapshot(bars,session_schedule=schedule(source="different evidence"))
+    assert a["features"]==b["features"]
+    assert a["window_sha256"] != b["window_sha256"]
+    assert a["calendar"]["schedule_sha256"] != b["calendar"]["schedule_sha256"]
+
+
+def test_registered_normal_hours_bridge_connects_to_ema_without_market_inputs():
+    from trading_system.data_foundation.sessions import load_session_calendar
+    from trading_system.tree_replay.calendar import schedule_from_research_calendar
+    root=Path(__file__).resolve().parents[2]
+    template=load_session_calendar(root/"configs/data/session-calendar.yaml",
+                                   "cme-globex-metals-research-v1")
+    sc=schedule_from_research_calendar(
+        template,instrument="SYNTH:TEST",coverage_start=T0,coverage_end=T0+30*STEP,
+        available_at=T0,source="synthetic test binding; not market approval")
+    r=snapshot(ten_bars(),session_schedule=sc)
+    assert r["features"]["chartdesk.5m.ema5"]==pytest.approx(8)
+    assert r["calendar"]["calendar_id"]=="cme-globex-metals-research-v1"
+
+
+def test_weekend_does_not_reset_or_fill_ema():
+    from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
+    friday=datetime(2026,9,11,20,30,tzinfo=timezone.utc)
+    sunday=datetime(2026,9,13,22,tzinfo=timezone.utc)
+    end=sunday+4*STEP
+    sc=SessionSchedule(instrument="SYNTH:TEST",calendar_id="synthetic",version="v1",
+        coverage_start=friday,coverage_end=end,available_at=friday,source="synthetic weekend",
+        intervals=(SessionInterval(opened_at=friday,closed_at=friday+6*STEP),
+                   SessionInterval(opened_at=sunday,closed_at=end)))
+    times=[friday+i*STEP for i in range(6)]+[sunday+i*STEP for i in range(4)]
+    r=snapshot(tuple(bar(t,close=c) for t,c in zip(times,range(1,11))),
+               history_start=friday,decision_time=end,session_schedule=sc)
+    assert r["features"]["chartdesk.5m.ema5"]==pytest.approx(8)
+    assert r["calendar"]["expected_bars"]==10

diff --git a/trading_system/tree_replay/ema.py b/trading_system/tree_replay/ema.py
--- a/trading_system/tree_replay/ema.py
+++ b/trading_system/tree_replay/ema.py
@@ -1,114 +1,136 @@
-"""Closed, available-bar EMA observations; not candidate generation or live parity."""
-
-from dataclasses import asdict
-from datetime import datetime
-import hashlib
-import json
-import math
-
-import numpy as np
-import pandas as pd
-
-from trading_system.tree_spec.snapshot import FeatureDefinition, FeatureObservation, build_snapshot
-from .bars import select_closed_bars
-from ._vendor import tr
-
-
-SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
-ADAPTER_VERSION = "chartdesk-closed-ema-v1"
-
-
-def _time(value):
-    return value.isoformat().replace("+00:00", "Z")
-
-
-def _finite(value):
-    number = float(value)
-    if not math.isfinite(number):
-        raise ValueError("nonfinite numerical EMA result after warmup")
-    return number
-
-
-def ema_snapshot(bars, *, snapshot_id, instrument, timeframe, decision_time,
-                 history_start, max_age_seconds) -> dict:
-    """Use all selected dependencies; missing history never shortens an EMA seed.
-
-    The contiguous closed-bar policy is a research adapter constraint, not a new
-    live trading gate. Per-EMA 2*n warmup comes from features.draw_trend. delta5
-    is its raw slope numerator, NOT its ATR-normalized slope. Inputs require a
-    caller-defined historical anchor and freshness limit; no calendar is guessed.
-    """
-    window = select_closed_bars(bars, instrument=instrument, timeframe=timeframe,
-                                decision_time=decision_time, history_start=history_start,
-                                max_age_seconds=max_age_seconds)
-    serialized = asdict(window)
-    encoded = json.dumps(serialized, sort_keys=True, separators=(",", ":"),
-                         allow_nan=False, default=lambda x: _time(x) if isinstance(x, datetime) else x)
-    window_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
-    source = f"chart-desk@{SOURCE_COMMIT};{ADAPTER_VERSION};window={window_hash}"
-    definitions, observations = [], []
-    periods = []
-    values = {}
-
-    if window.blocker is None:
-        frame = pd.DataFrame({"close": [b.close for b in window.bars]},
-                             index=pd.DatetimeIndex([b.opened_at for b in window.bars]))
-        try:
-            with np.errstate(over="raise", invalid="raise", divide="raise"):
-                averages = tr.emas(frame)
-                for n in tr.TR_EMAS:
-                    if len(frame) >= 2 * n:
-                        current = _finite(averages[f"ema{n}"].iloc[-1])
-                        previous = _finite(averages[f"ema{n}"].iloc[-6])
-                        values[f"ema{n}"] = current
-                        values[f"above_ema{n}"] = bool(frame["close"].iloc[-1] > current)
-                        values[f"ema{n}_delta5"] = _finite(current - previous)
-                        periods.append(n)
-                if periods:
-                    ordered = sorted(periods, key=lambda n: -values[f"ema{n}"])
-                    values["ema_order"] = ">".join(str(n) for n in ordered)
-                    if len(periods) == len(tr.TR_EMAS):
-                        values["ema_stacked"] = ordered in (list(tr.TR_EMAS), list(reversed(tr.TR_EMAS)))
-                if 50 in periods:
-                    cloud = tr.ema_cloud(frame).iloc[-1]
-                    for key in ("basis", "upper", "lower", "size"):
-                        values[f"cloud50_{key}"] = _finite(cloud[key])
-                    close = float(frame["close"].iloc[-1])
-                    values["cloud50_location"] = (
-                        "ABOVE" if close > values["cloud50_upper"] else
-                        "BELOW" if close < values["cloud50_lower"] else "INSIDE"
-                    )
-        except (FloatingPointError, OverflowError) as exc:
-            raise ValueError("numeric overflow in pinned EMA calculation") from exc
-
-    fields = []
-    for n in tr.TR_EMAS:
-        fields.extend([(f"ema{n}", "number", "price"),
-                       (f"above_ema{n}", "boolean", "boolean"),
-                       (f"ema{n}_delta5", "number", "price_change_over_5_bars")])
-    fields += [("ema_order", "category", "descending_period_list"),
-               ("ema_stacked", "boolean", "boolean")]
-    fields += [(f"cloud50_{k}", "number", "price") for k in ("basis", "upper", "lower", "size")]
-    fields.append(("cloud50_location", "category", "relation"))
-    for key, dtype, unit in fields:
-        feature_id = f"chartdesk.{timeframe}.{key}"
-        definitions.append(FeatureDefinition(feature_id, dtype, unit, "PRE_ENTRY", False))
-        if key in values:
-            status, value = "KNOWN", values[key]
-            observed = window.bars[-1].closed_at
-            available = max(b.available_at for b in window.bars)
-        else:
-            status = ("STALE" if window.blocker == "STALE" else
-                      "UNAVAILABLE" if window.blocker else "UNKNOWN")
-            value = None
-            observed = available = window.decision_time
-        observations.append(FeatureObservation(feature_id, value, status, observed, available, source))
-
-    result = build_snapshot(snapshot_id, window.decision_time, definitions, observations).to_payload()
-    return {**result, "instrument": window.instrument, "timeframe": window.timeframe,
-            "window_sha256": window_hash, "window_blocker": window.blocker,
-            "history_start": _time(window.history_start), "max_age_seconds": window.max_age_seconds,
-            "coverage": {"selected_bars": len(window.bars), "available_ema_periods": periods},
-            "calculation": {"source_commit": SOURCE_COMMIT, "adapter_version": ADAPTER_VERSION,
-                            "pandas_version": pd.__version__, "numpy_version": np.__version__},
-            "ready_for_replay": False, "ready_for_training": False}
+"""Closed, available-bar EMA observations; not candidate generation or live parity."""
+
+from dataclasses import asdict
+from datetime import datetime
+import hashlib
+import json
+import math
+
+import numpy as np
+import pandas as pd
+
+from trading_system.tree_spec.snapshot import FeatureDefinition, FeatureObservation, build_snapshot
+from .bars import select_closed_bars
+from ._vendor import tr
+
+
+SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
+ADAPTER_VERSION = "chartdesk-closed-ema-v1"
+
+
+def _time(value):
+    return value.isoformat().replace("+00:00", "Z")
+
+
+def _finite(value):
+    number = float(value)
+    if not math.isfinite(number):
+        raise ValueError("nonfinite numerical EMA result after warmup")
+    return number
+
+
+def ema_snapshot(bars, *, snapshot_id, instrument, timeframe, decision_time,
+                 history_start, max_age_seconds, session_schedule=None) -> dict:
+    """Use all selected dependencies; missing history never shortens an EMA seed.
+
+    The contiguous closed-bar policy is a research adapter constraint, not a new
+    live trading gate. Per-EMA 2*n warmup comes from features.draw_trend. delta5
+    is its raw slope numerator, NOT its ATR-normalized slope. Inputs require a
+    caller-defined historical anchor and freshness limit; no calendar is guessed.
+    An explicit session_schedule opts into full-interval calendar selection.
+    """
+    params = dict(instrument=instrument, timeframe=timeframe,
+                  decision_time=decision_time, history_start=history_start,
+                  max_age_seconds=max_age_seconds)
+    calendar_metadata = {}
+    if session_schedule is None:
+        window = select_closed_bars(bars, **params)
+    else:
+        from .session_bars import select_session_bars
+        window = select_session_bars(bars, **params, session_schedule=session_schedule)
+        calendar_metadata = {"calendar": {
+            "calendar_id": session_schedule.calendar_id, "version": session_schedule.version,
+            "source": session_schedule.source, "schedule_sha256": window.schedule_sha256,
+            "available_at": _time(session_schedule.available_at),
+            "coverage_start": _time(session_schedule.coverage_start),
+            "coverage_end": _time(session_schedule.coverage_end),
+            "expected_bars": window.expected_bars,
+            "missing_opens": [_time(t) for t in window.missing_opens],
+            "out_of_session_bars": window.out_of_session_bars,
+            "straddling_bars": window.straddling_bars,
+            "adapter_version": "session-closed-history-v1",
+            "execution_truth": False,
+        }}
+    serialized = asdict(window)
+    encoded = json.dumps(serialized, sort_keys=True, separators=(",", ":"),
+                         allow_nan=False, default=lambda x: _time(x) if isinstance(x, datetime) else x)
+    window_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
+    source = f"chart-desk@{SOURCE_COMMIT};{ADAPTER_VERSION};window={window_hash}"
+    definitions, observations = [], []
+    periods = []
+    values = {}
+
+    if window.blocker is None:
+        frame = pd.DataFrame({"close": [b.close for b in window.bars]},
+                             index=pd.DatetimeIndex([b.opened_at for b in window.bars]))
+        try:
+            with np.errstate(over="raise", invalid="raise", divide="raise"):
+                averages = tr.emas(frame)
+                for n in tr.TR_EMAS:
+                    if len(frame) >= 2 * n:
+                        current = _finite(averages[f"ema{n}"].iloc[-1])
+                        previous = _finite(averages[f"ema{n}"].iloc[-6])
+                        values[f"ema{n}"] = current
+                        values[f"above_ema{n}"] = bool(frame["close"].iloc[-1] > current)
+                        values[f"ema{n}_delta5"] = _finite(current - previous)
+                        periods.append(n)
+                if periods:
+                    ordered = sorted(periods, key=lambda n: -values[f"ema{n}"])
+                    values["ema_order"] = ">".join(str(n) for n in ordered)
+                    if len(periods) == len(tr.TR_EMAS):
+                        values["ema_stacked"] = ordered in (list(tr.TR_EMAS), list(reversed(tr.TR_EMAS)))
+                if 50 in periods:
+                    cloud = tr.ema_cloud(frame).iloc[-1]
+                    for key in ("basis", "upper", "lower", "size"):
+                        values[f"cloud50_{key}"] = _finite(cloud[key])
+                    close = float(frame["close"].iloc[-1])
+                    values["cloud50_location"] = (
+                        "ABOVE" if close > values["cloud50_upper"] else
+                        "BELOW" if close < values["cloud50_lower"] else "INSIDE"
+                    )
+        except (FloatingPointError, OverflowError) as exc:
+            raise ValueError("numeric overflow in pinned EMA calculation") from exc
+
+    fields = []
+    for n in tr.TR_EMAS:
+        fields.extend([(f"ema{n}", "number", "price"),
+                       (f"above_ema{n}", "boolean", "boolean"),
+                       (f"ema{n}_delta5", "number", "price_change_over_5_bars")])
+    fields += [("ema_order", "category", "descending_period_list"),
+               ("ema_stacked", "boolean", "boolean")]
+    fields += [(f"cloud50_{k}", "number", "price") for k in ("basis", "upper", "lower", "size")]
+    fields.append(("cloud50_location", "category", "relation"))
+    for key, dtype, unit in fields:
+        feature_id = f"chartdesk.{timeframe}.{key}"
+        definitions.append(FeatureDefinition(feature_id, dtype, unit, "PRE_ENTRY", False))
+        if key in values:
+            status, value = "KNOWN", values[key]
+            observed = window.bars[-1].closed_at
+            available = max(b.available_at for b in window.bars)
+            if session_schedule is not None:
+                available = max(available, window.calendar_available_at)
+        else:
+            status = ("STALE" if window.blocker == "STALE" else
+                      "UNAVAILABLE" if window.blocker else "UNKNOWN")
+            value = None
+            observed = available = window.decision_time
+        observations.append(FeatureObservation(feature_id, value, status, observed, available, source))
+
+    result = build_snapshot(snapshot_id, window.decision_time, definitions, observations).to_payload()
+    return {**result, **calendar_metadata, "instrument": window.instrument, "timeframe": window.timeframe,
+            "window_sha256": window_hash, "window_blocker": window.blocker,
+            "history_start": _time(window.history_start), "max_age_seconds": window.max_age_seconds,
+            "coverage": {"selected_bars": len(window.bars), "available_ema_periods": periods},
+            "calculation": {"source_commit": SOURCE_COMMIT, "adapter_version": ADAPTER_VERSION,
+                            "pandas_version": pd.__version__, "numpy_version": np.__version__},
+            "ready_for_replay": False, "ready_for_training": False}
