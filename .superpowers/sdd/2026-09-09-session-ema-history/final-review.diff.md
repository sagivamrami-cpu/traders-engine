# Final session-EMA slice review package
Base=Head=c1b6071633c55376c64f0a98ece843706f420f49; changes are local/untracked.
Includes every new code/test file, full old/new EMA wrapper and user-facing usage.
Prior baseline/tree_spec/vendored calculations are unchanged this turn.


diff --git a/trading_system/tree_replay/calendar.py b/trading_system/tree_replay/calendar.py
--- /dev/null
+++ b/trading_system/tree_replay/calendar.py
@@ -0,0 +1,156 @@
+"""Explicit research session evidence, never verified historical execution truth.
+
+Coverage and open intervals are half-open. Empty intervals declare closed
+coverage; they do not describe unknown coverage. Publication evidence is supplied
+by the caller and may precede or follow the period to which a schedule applies.
+"""
+
+from dataclasses import asdict, dataclass, replace
+from datetime import datetime, time, timedelta
+from hashlib import sha256
+import json
+
+from trading_system.data_foundation import sessions
+from trading_system.data_foundation.sessions import SessionCalendar
+
+from .bars import _utc, _validate_identity
+
+
+def _validate_text(value: str, field: str) -> None:
+    if not isinstance(value, str) or not value or value != value.strip():
+        raise ValueError(f"{field} must be a nonempty trimmed string")
+
+
+@dataclass(frozen=True, kw_only=True)
+class SessionInterval:
+    """An explicitly open half-open interval [opened_at, closed_at)."""
+
+    opened_at: datetime
+    closed_at: datetime
+
+    def __post_init__(self) -> None:
+        for field in ("opened_at", "closed_at"):
+            object.__setattr__(self, field, _utc(getattr(self, field), field))
+        if self.opened_at >= self.closed_at:
+            raise ValueError("opened_at must precede closed_at")
+
+
+@dataclass(frozen=True, kw_only=True)
+class SessionSchedule:
+    """Immutable supplied evidence with sorted, disjoint, nonadjacent intervals."""
+
+    instrument: str
+    calendar_id: str
+    version: str
+    coverage_start: datetime
+    coverage_end: datetime
+    available_at: datetime
+    source: str
+    intervals: tuple[SessionInterval, ...]
+
+    def __post_init__(self) -> None:
+        _validate_identity(self.instrument, "5m")
+        for field in ("calendar_id", "version", "source"):
+            _validate_text(getattr(self, field), field)
+        for field in ("coverage_start", "coverage_end", "available_at"):
+            object.__setattr__(self, field, _utc(getattr(self, field), field))
+        if self.coverage_start >= self.coverage_end:
+            raise ValueError("coverage_start must precede coverage_end")
+        if not isinstance(self.intervals, tuple) or any(
+            not isinstance(item, SessionInterval) for item in self.intervals
+        ):
+            raise ValueError("intervals must be a tuple of SessionInterval inputs")
+
+        canonical: list[SessionInterval] = []
+        for item in sorted(self.intervals, key=lambda item: item.opened_at):
+            if item.opened_at < self.coverage_start or item.closed_at > self.coverage_end:
+                raise ValueError("every interval must lie inside schedule coverage")
+            if canonical:
+                previous = canonical[-1]
+                if item.opened_at < previous.closed_at:
+                    raise ValueError("overlapping or duplicate intervals are unsupported")
+                if item.opened_at == previous.closed_at:
+                    canonical[-1] = SessionInterval(
+                        opened_at=previous.opened_at, closed_at=item.closed_at,
+                    )
+                    continue
+            canonical.append(item)
+        object.__setattr__(self, "intervals", tuple(canonical))
+
+
+def schedule_from_research_calendar(
+    calendar: SessionCalendar, *, instrument: str, coverage_start: datetime,
+    coverage_end: datetime, available_at: datetime, source: str,
+) -> SessionSchedule:
+    """Resolve only the registered normal-hours template into explicit minutes.
+
+    No calendar is loaded here. Holidays, early closes and changed templates are
+    rejected. The caller binds the instrument; this establishes no GC/CFD
+    equivalence. Current resolver/timezone rules are research inputs, not proof
+    of historical truth. Exact returned intervals can be fingerprinted by users.
+
+    Provenance hashes all calendar dataclass fields as sorted compact JSON,
+    with times encoded by ISO format and tuples encoded as JSON arrays.
+    """
+    if type(calendar) is not SessionCalendar:
+        raise ValueError("calendar must be a supplied SessionCalendar")
+    template = {
+        "calendar_id": "cme-globex-metals-research-v1",
+        "timezone": "America/Chicago",
+        "session_model": "cme_globex_daily_break",
+        "regular_open": time(17),
+        "regular_close": time(16),
+        "daily_break_start": time(16),
+        "daily_break_end": time(17),
+        "closed_weekdays": (5,),
+        "holidays": (),
+        "early_closes": (),
+    }
+    for field, expected in template.items():
+        actual = getattr(calendar, field)
+        if type(actual) is not type(expected) or actual != expected:
+            raise ValueError(f"unsupported research calendar field: {field}")
+        # Equality hides float weekdays, time.fold and date-dependent tzinfo.
+        if isinstance(actual, time) and (actual.tzinfo is not None or actual.fold != expected.fold):
+            raise ValueError(f"unsupported research calendar field: {field}")
+        if field == "closed_weekdays" and any(type(day) is not int for day in actual):
+            raise ValueError("closed_weekdays must contain exact integers")
+    _validate_text(calendar.version, "version")
+
+    # Validate caller evidence before resolving any minutes or decorating source.
+    schedule = SessionSchedule(
+        instrument=instrument, calendar_id=calendar.calendar_id,
+        version=calendar.version, coverage_start=coverage_start,
+        coverage_end=coverage_end, available_at=available_at,
+        source=source, intervals=(),
+    )
+    for field in ("coverage_start", "coverage_end"):
+        value = getattr(schedule, field)
+        if value.second or value.microsecond:
+            raise ValueError(f"{field} must be a whole-minute UTC endpoint")
+
+    intervals: list[SessionInterval] = []
+    opened_at = None
+    minute = schedule.coverage_start
+    while minute < schedule.coverage_end:
+        if sessions.resolve_session(minute, calendar).in_session:
+            if opened_at is None:
+                opened_at = minute
+        elif opened_at is not None:
+            intervals.append(SessionInterval(opened_at=opened_at, closed_at=minute))
+            opened_at = None
+        minute += timedelta(minutes=1)
+    if opened_at is not None:
+        intervals.append(SessionInterval(opened_at=opened_at, closed_at=schedule.coverage_end))
+
+    calendar_fields = {
+        field: value.isoformat() if isinstance(value, time) else value
+        for field, value in asdict(calendar).items()
+    }
+    digest = sha256(json.dumps(
+        calendar_fields, sort_keys=True, separators=(",", ":"),
+    ).encode("utf-8")).hexdigest()
+    return replace(
+        schedule, intervals=tuple(intervals),
+        source=f"{source}; calendar_sha256={digest}; RESEARCH_NORMAL_HOURS_NOT_EXECUTION_TRUTH",
+    )

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

diff --git a/tests/tree_replay/test_calendar.py b/tests/tree_replay/test_calendar.py
--- /dev/null
+++ b/tests/tree_replay/test_calendar.py
@@ -0,0 +1,364 @@
+"""Synthetic schedule contracts and literal registered normal-hours scenarios."""
+
+from dataclasses import FrozenInstanceError, fields, replace
+from datetime import datetime, time, timedelta, timezone
+from hashlib import sha256
+from pathlib import Path
+import re
+from zoneinfo import ZoneInfo
+
+import pandas as pd
+import pytest
+
+from trading_system.data_foundation.sessions import load_session_calendar
+
+
+START = datetime(2026, 9, 7, 20, 30, tzinfo=timezone.utc)
+END = datetime(2026, 9, 7, 22, 30, tzinfo=timezone.utc)
+ROOT = Path(__file__).resolve().parents[2]
+
+
+def interval(opened_at=START, closed_at=END):
+    from trading_system.tree_replay.calendar import SessionInterval
+
+    return SessionInterval(opened_at=opened_at, closed_at=closed_at)
+
+
+def schedule(**changes):
+    from trading_system.tree_replay.calendar import SessionSchedule
+
+    values = dict(
+        instrument="SYNTH:TEST", calendar_id="synthetic:calendar", version="v1",
+        coverage_start=START, coverage_end=END, available_at=START - timedelta(days=1),
+        source="synthetic:declared-schedule", intervals=(),
+    )
+    values.update(changes)
+    return SessionSchedule(**values)
+
+
+@pytest.fixture
+def research_calendar():
+    return load_session_calendar(
+        ROOT / "configs/data/session-calendar.yaml", "cme-globex-metals-research-v1",
+    )
+
+
+def bridge(calendar, **changes):
+    from trading_system.tree_replay.calendar import schedule_from_research_calendar
+
+    values = dict(
+        instrument="SYNTH:TEST", coverage_start=START, coverage_end=END,
+        available_at=START - timedelta(days=1), source="synthetic:calendar-evidence",
+    )
+    values.update(changes)
+    return schedule_from_research_calendar(calendar, **values)
+
+
+def bounds(result):
+    return tuple((item.opened_at, item.closed_at) for item in result.intervals)
+
+
+def test_interval_normalizes_dst_fold_before_comparing_endpoints():
+    chicago = ZoneInfo("America/Chicago")
+    item = interval(
+        datetime(2026, 11, 1, 1, 55, 17, 123456, tzinfo=chicago, fold=0),
+        datetime(2026, 11, 1, 1, 5, 17, 123457, tzinfo=chicago, fold=1),
+    )
+    assert item.opened_at == datetime(2026, 11, 1, 6, 55, 17, 123456, tzinfo=timezone.utc)
+    assert item.closed_at == datetime(2026, 11, 1, 7, 5, 17, 123457, tzinfo=timezone.utc)
+    assert item.opened_at.tzinfo is item.closed_at.tzinfo is timezone.utc
+
+
+@pytest.mark.parametrize("closed_at", [START, START - timedelta(microseconds=1)])
+def test_interval_requires_strictly_increasing_times(closed_at):
+    from trading_system.tree_replay.calendar import SessionInterval
+
+    with pytest.raises(ValueError):
+        SessionInterval(opened_at=START, closed_at=closed_at)
+
+
+@pytest.mark.parametrize("field", ["opened_at", "closed_at", "coverage_start", "coverage_end", "available_at"])
+@pytest.mark.parametrize("value", [None, "2026-09-07", START.replace(tzinfo=None), pd.Timestamp(START) + pd.Timedelta(nanoseconds=1)])
+def test_times_reject_naive_non_datetime_and_submicrosecond_values(field, value):
+    from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
+
+    record = interval() if field in ("opened_at", "closed_at") else schedule()
+    with pytest.raises(ValueError):
+        replace(record, **{field: value})
+
+
+def test_schedule_normalizes_all_times_preserving_microseconds_and_publication():
+    zone = timezone(timedelta(hours=3))
+    values = dict(
+        coverage_start=START + timedelta(microseconds=1),
+        coverage_end=END + timedelta(microseconds=2),
+        available_at=START - timedelta(days=10, microseconds=3),
+    )
+    result = schedule(**{key: pd.Timestamp(value.astimezone(zone)) for key, value in values.items()})
+    for key, value in values.items():
+        assert getattr(result, key) == value
+        assert type(getattr(result, key)) is datetime
+        assert getattr(result, key).tzinfo is timezone.utc
+    assert replace(result, available_at=END + timedelta(days=1)).available_at > result.coverage_end
+
+
+@pytest.mark.parametrize("field", ["calendar_id", "version", "source"])
+@pytest.mark.parametrize("value", [None, 123, "", " \t", " padded", "padded "])
+def test_schedule_rejects_missing_or_untrimmed_metadata(field, value):
+    from trading_system.tree_replay.calendar import SessionSchedule
+
+    with pytest.raises(ValueError):
+        schedule(**{field: value})
+
+
+@pytest.mark.parametrize("value", [None, 123, "", "TEST", ":TEST", "SYNTH:", "SYNTH:TEST:X", " SYNTH:TEST", "SYNTH:TE ST"])
+def test_schedule_requires_exact_venue_symbol(value):
+    from trading_system.tree_replay.calendar import SessionSchedule
+
+    with pytest.raises(ValueError):
+        schedule(instrument=value)
+
+
+def test_schedule_preserves_caller_instrument_without_conversion():
+    assert schedule(instrument="synth:Test").instrument == "synth:Test"
+
+
+@pytest.mark.parametrize("coverage_end", [START, START - timedelta(microseconds=1)])
+def test_schedule_rejects_empty_or_reversed_coverage(coverage_end):
+    from trading_system.tree_replay.calendar import SessionSchedule
+
+    with pytest.raises(ValueError):
+        schedule(coverage_end=coverage_end)
+
+
+def test_empty_tuple_declares_fully_closed_bounded_coverage():
+    result = schedule()
+    assert result.intervals == ()
+    assert (result.coverage_start, result.coverage_end) == (START, END)
+
+
+@pytest.mark.parametrize("kind", ["list", "generator", "none", "dict", "tuple-of-dicts"])
+def test_schedule_accepts_only_tuple_of_intervals(kind):
+    item = interval()
+    values = {"list": [item], "generator": iter((item,)), "none": None, "dict": {}, "tuple-of-dicts": ({"opened_at": START, "closed_at": END},)}
+    with pytest.raises(ValueError):
+        schedule(intervals=values[kind])
+
+
+@pytest.mark.parametrize("opened_at,closed_at", [
+    (START - timedelta(microseconds=1), END),
+    (START, END + timedelta(microseconds=1)),
+    (END, END + timedelta(minutes=1)),
+])
+def test_schedule_rejects_intervals_outside_coverage(opened_at, closed_at):
+    item = interval(opened_at, closed_at)
+    with pytest.raises(ValueError):
+        schedule(intervals=(item,))
+
+
+@pytest.mark.parametrize("kind", ["duplicate", "overlap", "nested"])
+def test_schedule_rejects_duplicate_or_overlapping_intervals(kind):
+    first = interval(START, START + timedelta(hours=1))
+    other = {
+        "duplicate": first,
+        "overlap": interval(START + timedelta(minutes=30), END),
+        "nested": interval(START + timedelta(minutes=10), START + timedelta(minutes=20)),
+    }[kind]
+    with pytest.raises(ValueError):
+        schedule(intervals=(other, first))
+
+
+def test_schedule_sorts_and_merges_adjacent_chain_without_mutating_input():
+    first = interval(START, START + timedelta(minutes=30))
+    middle = interval(first.closed_at, START + timedelta(minutes=60))
+    last = interval(middle.closed_at, END)
+    supplied = (last, first, middle)
+    result = schedule(intervals=supplied)
+    assert bounds(result) == ((START, END),)
+    assert supplied == (last, first, middle)
+    assert first.closed_at == datetime(2026, 9, 7, 21, tzinfo=timezone.utc)
+    assert result == schedule(intervals=(interval(),))
+    assert hash(result) == hash(schedule(intervals=(interval(),)))
+
+
+def test_one_microsecond_gap_is_preserved_not_merged():
+    left = interval(START, START + timedelta(minutes=30))
+    right = interval(left.closed_at + timedelta(microseconds=1), END)
+    assert schedule(intervals=(right, left)).intervals == (left, right)
+
+
+def test_contracts_are_frozen_keyword_only_and_all_fields_required():
+    for record in (interval(), schedule(intervals=(interval(),))):
+        values = {field.name: getattr(record, field.name) for field in fields(record)}
+        with pytest.raises(FrozenInstanceError):
+            setattr(record, next(iter(values)), None)
+        with pytest.raises(TypeError):
+            type(record)(*values.values())
+        for missing in values:
+            with pytest.raises(TypeError):
+                type(record)(**{key: value for key, value in values.items() if key != missing})
+    with pytest.raises(TypeError):
+        schedule(intervals=(interval(),)).intervals[0] = interval()
+
+
+@pytest.mark.parametrize("start,end,want", [
+    ("2026-09-07T20:30:00+00:00", "2026-09-07T22:30:00+00:00", (
+        ("2026-09-07T20:30:00+00:00", "2026-09-07T21:00:00+00:00"),
+        ("2026-09-07T22:00:00+00:00", "2026-09-07T22:30:00+00:00"),
+    )),
+    ("2026-09-11T21:00:00+00:00", "2026-09-13T22:00:00+00:00", ()),
+    ("2026-09-13T21:59:00+00:00", "2026-09-13T22:01:00+00:00", (
+        ("2026-09-13T22:00:00+00:00", "2026-09-13T22:01:00+00:00"),
+    )),
+    ("2026-03-08T21:00:00+00:00", "2026-03-08T23:00:00+00:00", (
+        ("2026-03-08T22:00:00+00:00", "2026-03-08T23:00:00+00:00"),
+    )),
+    ("2026-11-01T22:00:00+00:00", "2026-11-02T00:00:00+00:00", (
+        ("2026-11-01T23:00:00+00:00", "2026-11-02T00:00:00+00:00"),
+    )),
+    ("2026-09-07T20:59:00+00:00", "2026-09-07T21:00:00+00:00", (
+        ("2026-09-07T20:59:00+00:00", "2026-09-07T21:00:00+00:00"),
+    )),
+    ("2026-09-07T21:00:00+00:00", "2026-09-07T22:00:00+00:00", ()),
+])
+def test_bridge_literal_half_open_normal_hours(research_calendar, start, end, want):
+    result = bridge(research_calendar, coverage_start=datetime.fromisoformat(start), coverage_end=datetime.fromisoformat(end))
+    assert tuple((a.isoformat(), b.isoformat()) for a, b in bounds(result)) == want
+
+
+@pytest.mark.parametrize("changes", [
+    {"calendar_id": "other"}, {"timezone": "UTC"}, {"session_model": "regular_intraday"},
+    {"regular_open": time(18)}, {"regular_close": time(15)},
+    {"daily_break_start": time(15)}, {"daily_break_end": time(18)},
+    {"daily_break_start": None}, {"daily_break_end": None},
+    {"regular_open": time(17, 0, 0, 1)}, {"regular_close": time(16, tzinfo=timezone.utc)},
+    {"closed_weekdays": (5, 6)}, {"closed_weekdays": ()}, {"closed_weekdays": [5]},
+    {"holidays": ("2026-09-07",)}, {"early_closes": ("2026-09-07",)},
+    {"holidays": []}, {"early_closes": []},
+    {"version": ""}, {"version": " v1"}, {"version": None},
+])
+def test_bridge_rejects_any_changed_template_or_overlay(research_calendar, changes):
+    from trading_system.tree_replay.calendar import schedule_from_research_calendar
+
+    with pytest.raises(ValueError):
+        bridge(replace(research_calendar, **changes))
+
+
+@pytest.mark.parametrize("field", ["coverage_start", "coverage_end"])
+@pytest.mark.parametrize("offset", [timedelta(seconds=1), timedelta(microseconds=1)])
+def test_bridge_requires_whole_minute_coverage(research_calendar, field, offset):
+    from trading_system.tree_replay.calendar import schedule_from_research_calendar
+
+    value = START if field == "coverage_start" else END
+    with pytest.raises(ValueError):
+        bridge(research_calendar, **{field: value + offset})
+
+
+@pytest.mark.parametrize("changes", [
+    {"instrument": "TEST"}, {"source": ""}, {"source": " evidence"},
+    {"coverage_end": START}, {"coverage_end": START - timedelta(minutes=1)},
+    {"coverage_start": START.replace(tzinfo=None)},
+    {"coverage_end": END.replace(tzinfo=None)}, {"available_at": START.replace(tzinfo=None)},
+    {"coverage_start": pd.Timestamp(START) + pd.Timedelta(nanoseconds=1)},
+    {"coverage_end": pd.Timestamp(END) + pd.Timedelta(nanoseconds=1)},
+    {"available_at": pd.Timestamp(START) + pd.Timedelta(nanoseconds=1)},
+])
+def test_bridge_validates_explicit_request_evidence(research_calendar, changes):
+    from trading_system.tree_replay.calendar import schedule_from_research_calendar
+
+    with pytest.raises(ValueError):
+        bridge(research_calendar, **changes)
+
+
+def test_bridge_normalizes_utc_and_retains_exact_publication_time(research_calendar):
+    zone = timezone(timedelta(hours=3))
+    published = START - timedelta(days=3, microseconds=7)
+    result = bridge(
+        research_calendar, instrument="synth:Test", coverage_start=START.astimezone(zone),
+        coverage_end=END.astimezone(zone), available_at=published.astimezone(zone),
+    )
+    assert result.coverage_start == START
+    assert result.coverage_end == END
+    assert result.available_at == published
+    assert result.available_at.tzinfo is timezone.utc
+    assert result.instrument == "synth:Test"
+    assert result == bridge(research_calendar, instrument="synth:Test", available_at=published)
+
+
+def test_bridge_provenance_retains_caller_source_and_calendar_version(research_calendar):
+    result = bridge(research_calendar)
+    assert result.version == research_calendar.version
+    assert result.calendar_id == research_calendar.calendar_id
+    assert "synthetic:calendar-evidence" in result.source
+    assert "RESEARCH_NORMAL_HOURS_NOT_EXECUTION_TRUTH" in result.source
+    assert re.search(r"[0-9a-f]{64}", result.source)
+    assert result == bridge(research_calendar)
+    revised = bridge(replace(research_calendar, version="research-revision-2"))
+    assert bounds(revised) == bounds(result)
+    assert revised.version == "research-revision-2"
+    assert re.search(r"[0-9a-f]{64}", revised.source)[0] != re.search(r"[0-9a-f]{64}", result.source)[0]
+    assert bridge(research_calendar, source="synthetic:other-evidence").source != result.source
+
+
+@pytest.mark.parametrize("value", [None, {}, "cme-globex-metals-research-v1"])
+def test_bridge_requires_supplied_calendar_object(value):
+    from trading_system.tree_replay.calendar import schedule_from_research_calendar
+
+    with pytest.raises(ValueError):
+        bridge(value)
+
+
+@pytest.mark.parametrize("changes", [
+    {"closed_weekdays": (5.0,)},
+    {"regular_open": time(17, fold=1)},
+    {"regular_close": time(16, fold=1)},
+    {"daily_break_start": time(16, fold=1)},
+    {"daily_break_end": time(17, fold=1)},
+])
+def test_bridge_rejects_template_values_hidden_by_python_equality(research_calendar, changes):
+    with pytest.raises(ValueError):
+        bridge(replace(research_calendar, **changes))
+
+
+@pytest.mark.parametrize("field,hour", [
+    ("regular_open", 17), ("regular_close", 16),
+    ("daily_break_start", 16), ("daily_break_end", 17),
+])
+def test_bridge_rejects_timezone_bearing_template_times(research_calendar, field, hour):
+    value = time(hour, tzinfo=ZoneInfo("America/Chicago"))
+    with pytest.raises(ValueError, match=field):
+        bridge(replace(research_calendar, **{field: value}))
+
+
+def test_bridge_hash_covers_every_calendar_field_with_literal_serialization(research_calendar):
+    result = bridge(replace(research_calendar, version="synthetic-v1"))
+    # Independent literal payload: dropping a field from provenance must fail.
+    serialized = (
+        '{"calendar_id":"cme-globex-metals-research-v1","closed_weekdays":[5],'
+        '"daily_break_end":"17:00:00","daily_break_start":"16:00:00",'
+        '"early_closes":[],"holidays":[],"regular_close":"16:00:00",'
+        '"regular_open":"17:00:00","session_model":"cme_globex_daily_break",'
+        '"timezone":"America/Chicago","version":"synthetic-v1"}'
+    )
+    assert sha256(serialized.encode("utf-8")).hexdigest() in result.source
+
+
+def test_bridge_delegates_every_utc_minute_start_to_existing_resolver(research_calendar, monkeypatch):
+    from trading_system.data_foundation import sessions
+
+    original = sessions.resolve_session
+    calls = []
+
+    def recording_resolver(timestamp, calendar):
+        calls.append((timestamp, calendar))
+        return original(timestamp, calendar)
+
+    monkeypatch.setattr(sessions, "resolve_session", recording_resolver)
+    start = datetime(2026, 9, 7, 20, 59, tzinfo=timezone.utc)
+    end = datetime(2026, 9, 7, 21, 1, tzinfo=timezone.utc)
+    result = bridge(research_calendar, coverage_start=start, coverage_end=end)
+    assert bounds(result) == ((start, datetime(2026, 9, 7, 21, tzinfo=timezone.utc)),)
+    assert calls == [
+        (datetime(2026, 9, 7, 20, 59, tzinfo=timezone.utc), research_calendar),
+        (datetime(2026, 9, 7, 21, tzinfo=timezone.utc), research_calendar),
+    ]

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

diff --git a/docs/architecture/SESSION-EMA-ADAPTER-USAGE.md b/docs/architecture/SESSION-EMA-ADAPTER-USAGE.md
--- /dev/null
+++ b/docs/architecture/SESSION-EMA-ADAPTER-USAGE.md
@@ -0,0 +1,134 @@
+# Session-aware EMA history
+
+This opt-in offline extension distinguishes scheduled closures from missing bars.
+It does not certify full tree replay, trading schedules across ten years, dataset
+construction or a trained model. Existing strict contiguous calls are unchanged.
+
+## Contracts and usage
+
+`SessionInterval` represents a half-open open-market interval: [opened_at, closed_at).
+`SessionSchedule` supplies the exact instrument, calendar/version/source, declared
+coverage, publication time and open intervals. Intervals are normalized to UTC,
+sorted and merged when adjacent; overlaps and out-of-coverage intervals are errors.
+The complement of the intervals INSIDE coverage is explicitly declared closed.
+An empty interval list therefore means closed, not unknown. Do not supply empty
+intervals as a substitute for missing calendar evidence.
+
+```python
+from datetime import datetime, timezone
+from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
+from trading_system.tree_replay.ema import ema_snapshot
+
+utc = timezone.utc
+start = datetime(2026, 9, 7, 20, 30, tzinfo=utc)
+end = datetime(2026, 9, 7, 22, 20, tzinfo=utc)
+schedule = SessionSchedule(
+    instrument="SYNTH:TEST", calendar_id="synthetic-example", version="v1",
+    coverage_start=start, coverage_end=end, available_at=start,
+    source="synthetic declared hours; not market evidence",
+    intervals=(
+        SessionInterval(opened_at=start, closed_at=datetime(2026, 9, 7, 21, tzinfo=utc)),
+        SessionInterval(opened_at=datetime(2026, 9, 7, 22, tzinfo=utc), closed_at=end),
+    ),
+)
+# bars must be supplied ClosedBar objects with matching instrument/timeframe,
+# actual close/publication times and explicit provenance; no download occurs.
+# result = ema_snapshot(
+#     bars, snapshot_id="example", instrument="SYNTH:TEST", timeframe="5m",
+#     history_start=start, decision_time=end, max_age_seconds=300,
+#     session_schedule=schedule,
+# )
+```
+
+The example times are synthetic and are not a claim about holiday trading hours.
+Without `session_schedule`, the adapter retains the original strict contiguous policy.
+
+## Selection rules
+
+- Explicit history_start and eligible bar opens must align to a fixed UTC grid
+  (epoch alignment at 5m, 15m, 30m, 1h or 4h). No broker bar alignment is inferred.
+- Decision-time filtering uses BOTH bar close time and availability time.
+- The schedule must have been available by the decision and cover the entire
+  interval from history_start through the decision, including any current partial slot.
+- A completed bar is expected only if its WHOLE interval is open. A four-hour
+  bar crossing a one-hour break is excluded even if its endpoints are both open.
+- Eligible rows outside sessions or straddling a closure are excluded and counted
+  separately. Nothing is forward-filled or synthesized.
+- Every expected bar from the seed anchor through the latest completed slot
+  must be present and available. A late or missing last slot is a gap, even if
+  the previous price remains within the freshness budget.
+- Scheduled closures do not reset the EMA seed or introduce synthetic bars.
+  Fixed-duration bars crossing closures are dropped, not shortened.
+- Freshness remains wall-clock elapsed time. A complete window can still be
+  STALE during a long closure. No trading-time freshness budget is inferred.
+
+The entire recursive seed history matters: checking only the last15 bars, or even
+only the last1600, can miss an earlier gap that changes the EMA. The existing
+2*period visibility warmup remains unchanged (EMA800 needs1600 accepted bars).
+History selection is not permission to reinterpret the original desk's partial
+bars, session anchoring or instrument.
+
+## Blockers and provenance
+
+Blocker precedence is CALENDAR_UNAVAILABLE, CALENDAR_COVERAGE, NO_EXPECTED_BARS,
+HISTORY_INCOMPLETE (first expected bar missing), HISTORY_GAP (any other missing),
+STALE, or no blocker. Invalid metadata raises ValueError before that classification.
+Unavailable/coverage failures do not calculate membership; zero counts in those
+reports mean not evaluated, not confirmed zero missing bars.
+
+All feature values are null on a blocker (STALE or UNAVAILABLE); warmup remains
+UNKNOWN. None of these optional observations becomes an entry veto. The inherited
+eligible flag is still only required-field completeness, never readiness.
+
+Calendar-mode snapshots add a metadata-only calendar object: identity, version,
+source, coverage, availability, schedule hash, expected bars, all missing opens,
+and eligible out-of-session/straddling row counts. The window hash includes this
+schedule fingerprint and selected bar inputs. Known feature availability is the
+latest of ALL selected bar publication times and the schedule's publication time.
+Observed time remains the last selected bar close. Valid future bar suffixes do
+not change the output at the same decision.
+
+The schedule fingerprint covers the complete supplied schedule, not just today's
+open slots. Freeze the selected schedule version/coverage for reproducible replay.
+Callers must select the historically available schedule version; this is not an
+announcement/revision ledger. Evidence text and metadata are NOT ML features.
+A content hash records identity, not the truth or licensing of the supplied data.
+
+## Bridge to the existing registered calendar
+
+`schedule_from_research_calendar(calendar, *, instrument, coverage_start,
+coverage_end, available_at, source)` reuses `data_foundation.sessions.resolve_session`.
+Its only supported input is the registered GC normal-hours template:
+America/Chicago, Sunday-Friday,17:00 open/16:00 close with16:00-17:00 daily break.
+It enumerates UTC minutes and builds explicit intervals, preserving timezone/DST
+handling through the existing resolver. Coverage endpoints must be whole minutes.
+
+Unsupported represented SessionCalendar settings and nonempty holidays/early_closes are
+rejected, not silently ignored. It does not apply holiday overlays, halts, special
+hours or verify historical eras. Use separately justified explicit intervals for
+those cases; no such historical interval table is supplied by this change.
+The source records the caller reference, calendar-content hash and the marker
+RESEARCH_NORMAL_HOURS_NOT_EXECUTION_TRUTH. The passed instrument is an explicit
+caller binding, not proof of GC/CFD or venue equivalence.
+
+The existing YAML loader does not retain every raw configuration field (for
+example special_sessions). This bridge validates the supplied SessionCalendar,
+not the original YAML or evidence manifest. Its calendar hash covers dataclass
+fields only. A future production loader must validate raw overlays before any
+lossy conversion; this bridge cannot discover fields the caller discarded.
+
+Existing calendar/missing-bar policies and data approvals are NOT changed. The
+old30m builder and its15-bar lookback are not imported into this pipeline.
+The bridge is a bounded research helper, not an optimized multi-year schedule
+service. Neither it nor repeated full-window EMA calculation provides checkpoint/
+resume or incremental performance guarantees.
+
+## Verification and next step
+
+Synthetic tests cover normal breaks, weekends, DST openings, all five timeframes,
+an internal4h closure, old seed gaps, publication boundaries, hashes and numerics.
+Both ready_for_replay and ready_for_training remain false; execution_truth is false.
+Before real data: reconcile historical schedule/feed/era coverage, actual bar
+alignment and partial-bar behavior with the selected candidate producer. Continue
+the source-family/consumer mapping; do not label generic per-bar directions as
+tree-generated trade candidates.
