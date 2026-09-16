# Task1 new-file working-tree diff
HEAD c1b6071633c55376c64f0a98ece843706f420f49 unchanged; no commits.

diff --git a/trading_system/tree_replay/calendar.py b/trading_system/tree_replay/calendar.py
new file mode 100644
index 0000000..01c256d
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
+        # Equality hides float weekday values and the time.fold attribute.
+        if isinstance(actual, time) and actual.fold != expected.fold:
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

diff --git a/tests/tree_replay/test_calendar.py b/tests/tree_replay/test_calendar.py
new file mode 100644
index 0000000..dc4f12d
--- /dev/null
+++ b/tests/tree_replay/test_calendar.py
@@ -0,0 +1,354 @@
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
