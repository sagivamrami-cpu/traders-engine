"""Actual quote/rejection consumers and original logger on causal artifacts."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
import json

import pandas as pd
import pytest

from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission, _tail_reader


T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
SYM, LONG, SHORT = "OANDA:XAUUSD", "לונג", "שורט"


def api():
    name = "trading_system.tree_replay.admission_io"
    assert importlib.util.find_spec(name) is not None, "causal quote/watch IO missing"
    return importlib.import_module(name)


def seed(kind="watch_log", status="PRESENT", content=b"", *, at=T, **kw):
    return api().ArtifactSeed(**(dict(seed_id="artifact-1", source="synthetic",
        kind=kind, status=status, content=content if status == "PRESENT" else None,
        observed_at=at-timedelta(hours=1), available_at=at-timedelta(minutes=30),
        covered_through=at+timedelta(hours=1)) | kw))


def make_log(*, status="PRESENT", content=b"", at=T, newline="LF", **kw):
    return api().CausalWatchLog(seed=seed(status=status, content=content, at=at, **kw),
                              decision_time=at, newline=newline)


def quotes(payload=None, *, status="PRESENT", text=None, **kw):
    return api().CausalQuoteReader(seed=seed("quotes", status,
        json.dumps(payload if payload is not None else {}) if text is None else text, **kw), decision_time=T)


@pytest.mark.parametrize("age,price,want", [(0, 100, {SYM: 100.}),
    (420, 100, {SYM: 100.}), (420.001, 100, {}), (-.001, 100, {}),
    (0, 0, {}), (0, -1, {}), (0, float("nan"), {}), (0, float("inf"), {})])
def test_actual_source_quote_freshness_not_file_or_metadata_age(age, price, want):
    r = quotes({SYM: {"lp": price, "ts": T.timestamp()-age,
                      "metadata_ts": T.timestamp(), "bid": 99}})
    assert TrackerAdmission(r)._live_prices() == want


@pytest.mark.parametrize("status,text,error", [("ABSENT", None, "FileNotFoundError"),
    ("UNREADABLE", None, "OSError"), ("UNKNOWN", None, "InputUnavailable"),
    ("PRESENT", "{torn", "JSONDecodeError")])
def test_quote_read_failure_survives_original_empty_price_fallback(status, text, error):
    r = quotes(status=status, text=text)
    assert TrackerAdmission(r)._live_prices() == {}
    assert any(e["exception_type"] == error for e in r.trace)


def test_valid_nonobject_quote_json_keeps_source_consumer_error_boundary():
    r = quotes(text="[]")
    assert r.quote_payload() == []
    with pytest.raises(AttributeError):
        TrackerAdmission(r)._live_prices()


def test_quote_payload_is_detached_and_symbols_are_not_aliased():
    r = quotes({"XAUUSD": {"lp": 100, "ts": T.timestamp()}})
    first = r.quote_payload()
    first["XAUUSD"]["lp"] = 999
    assert TrackerAdmission(r)._live_prices() == {"XAUUSD": 100.}
    assert r.quote_payload()["XAUUSD"]["lp"] == 100


@pytest.mark.parametrize("kw", [dict(available_at=T+timedelta(microseconds=1)),
                               dict(covered_through=T-timedelta(microseconds=1))])
def test_unpublished_or_expired_quotes_never_reach_consumer(kw):
    r = quotes({SYM: {"lp": 100, "ts": T.timestamp()}}, **kw)
    assert TrackerAdmission(r)._live_prices() == {}
    assert any(e["exception_type"] == "InputUnavailable" for e in r.trace)


@pytest.mark.parametrize("side,price,age,want", [(LONG, 103, 0, False),
    (SHORT, 97, 0, False), (LONG, 90, 0, True), (SHORT, 110, 0, True),
    (LONG, 103, 421, True)])
def test_original_born_state_uses_supplied_quote_with_source_fallback(side, price, age, want):
    from test_tracker_admission import plan
    r = quotes({SYM: {"lp": price, "ts": T.timestamp()-age}})
    assert TrackerAdmission(r)._born_in_zone(plan(close=100., direction=side), SYM) is want


@pytest.mark.parametrize("newline,ending", [("LF", b"\n"), ("CRLF", b"\r\n")])
def test_original_log_literal_bytes_and_input_mutation(newline, ending):
    log = make_log(status="ABSENT", newline=newline)
    row = {"kind": "rejection"}
    log.log(row)
    assert row == {"kind": "rejection", "sessions": ["newyork"]}
    assert log.snapshot().content == (
        b'{"ts": 1788969600.0, "kind": "rejection", "sessions": ["newyork"]}'+ending)
    operations = [e["operation"] for e in log.trace]
    assert operations.index("current_session") < operations.index("open_writer") < operations.index("clock") < operations.index("write")


def test_caller_timestamp_sessions_and_key_order_are_not_overwritten():
    log = make_log()
    log.log({"z": "שלום", "sessions": ["custom"], "ts": 12, "a": 1})
    assert log.snapshot().content == '{"ts": 12, "z": "שלום", "sessions": ["custom"], "a": 1}\n'.encode()
    assert any(e["operation"] == "clock" for e in log.trace)


def test_session_default_is_eager_even_when_caller_supplies_sessions(monkeypatch):
    log = make_log(status="ABSENT")
    def fail():
        raise ArithmeticError("session failed")
    monkeypatch.setattr(log.source, "current_session", fail)
    row = {"sessions": ["custom"]}
    with pytest.raises(ArithmeticError):
        log.log(row)
    assert row == {"sessions": ["custom"]} and log.snapshot().status == "ABSENT"
    assert not any(e["operation"] == "open_writer" for e in log.trace)


def test_bad_serialization_still_mutates_row_and_creates_empty_append_file():
    log = make_log(status="ABSENT")
    row = {"bad": object()}
    with pytest.raises(TypeError):
        log.log(row)
    assert row["sessions"] == ["newyork"]
    snap = log.snapshot()
    assert snap.status == "PRESENT" and snap.content == b""
    assert any(e["exception_type"] == "TypeError" for e in log.trace)


@pytest.mark.parametrize("status", ["UNKNOWN", "UNREADABLE"])
def test_unknown_log_prefix_is_not_silently_replaced_on_append(status):
    log = make_log(status=status)
    row = {}
    with pytest.raises((api().InputUnavailable, OSError)):
        log.log(row)
    assert row == {"sessions": ["newyork"]}
    assert _tail_reader(log.event_log_reader) is None
    assert any(e["status"] == "BLOCKED" for e in log.trace)


@pytest.mark.parametrize("kw", [dict(available_at=T+timedelta(seconds=1)),
                               dict(covered_through=T-timedelta(seconds=1))])
def test_log_publication_and_coverage_guard_reads_appends_and_snapshot(kw):
    log = make_log(content=b"supplied\n", **kw)
    row = {}
    with pytest.raises(api().InputUnavailable):
        log.log(row)
    assert row == {"sessions": ["newyork"]}
    assert _tail_reader(log.event_log_reader) is None
    with pytest.raises(api().InputUnavailable):
        log.snapshot()
    if "available_at" in kw:
        log.advance_to(T+timedelta(seconds=1))
        assert log.snapshot().content == b"supplied\n"


def test_encoding_failure_preserves_existing_prefix_and_remains_traced():
    log = make_log(content=b"previous\n")
    row = {"bad": "\ud800"}
    with pytest.raises(UnicodeError):
        log.log(row)
    assert log.snapshot().content == b"previous\n"
    assert row["sessions"] == ["newyork"]
    assert any(e["operation"] == "write" and e["exception_type"] == "UnicodeEncodeError" for e in log.trace)


def test_absent_log_read_and_empty_present_log_are_distinct():
    absent = make_log(status="ABSENT")
    assert _tail_reader(absent.event_log_reader) is None
    assert any(e["exception_type"] == "FileNotFoundError" for e in absent.trace)
    assert _tail_reader(make_log().event_log_reader) == b""


@pytest.mark.parametrize("prefix", [b"\xff\xfe\n", b'{"torn": ', b"earlier\r\n"])
def test_raw_prefix_is_not_decoded_repaired_or_reserialized(prefix):
    log = make_log(content=prefix)
    log.log({"kind": "nontrade"})
    assert log.snapshot().content == prefix + b'{"ts": 1788969600.0, "kind": "nontrade", "sessions": ["newyork"]}\n'


def test_reader_captures_prefix_and_seek_spans_real_append_chunks():
    log = make_log(content=b"start\n")
    first = log.event_log_reader()
    log.log({"kind": "one"})
    second = log.event_log_reader()
    log.advance_to(T+timedelta(seconds=1))
    log.log({"kind": "two"})
    assert first.read() == b"start\n"
    second.seek(4)
    assert second.read(5) == b't\n{"t'
    second.seek(-3, 2)
    assert second.read() == b']}\n'
    assert first.seek(1000) == 1000 and first.read() == b""
    first.close()
    with pytest.raises(ValueError):
        first.read()
    assert b'"two"' not in second.read()  # already at captured end
    second.seek(0)
    assert b'"two"' not in second.read()
    with log.event_log_reader() as third:
        assert b'"two"' in third.read()


def test_source_tail_reads_small_suffix_and_widens_without_dropping_prior_lines():
    log = make_log(content=b"older\n"+b"x"*1000000+b"\nlast\n")
    reader = log.event_log_reader()
    sizes = []
    original = reader.read
    def read(size=-1):
        result = original(size)
        sizes.append(len(result))
        return result
    reader.read = read
    assert _tail_reader(lambda: reader, window=16) == b"last\n"
    assert sizes == [16]  # original source seeks before requesting bytes
    small = make_log(content=b"first\n"+b"x"*30+b"\n")
    assert _tail_reader(small.event_log_reader, window=8, cap=64) == b"x"*30+b"\n"
    assert _tail_reader(small.event_log_reader, window=8, cap=8) == b"first\n"+b"x"*30+b"\n"


def test_real_recent_rejection_sees_same_pass_append_but_not_later_reader_bytes():
    log = make_log()
    tracker = TrackerAdmission(log)
    def recent():
        return tracker._recent_rejection(SYM, LONG, T.timestamp()-60, T.timestamp(), 100.)
    assert recent() is None
    before = log.event_log_reader()
    log.log({"kind": "level_reversal_detected", "symbol": SYM})
    assert recent() is None
    log.log({"kind": "rejection", "symbol": SYM, "direction": LONG,
             "zone_lo": 98, "zone_hi": 102, "levels": ["PSY"], "close": 100, "wick_atr": .5})
    assert recent() == dict(ts=1788969600., direction=LONG, zone_lo=98, zone_hi=102,
                           levels=["PSY"], close=100, wick_atr=.5, age_s=0., gap=0.)
    assert before.read() == b""
    log.log({"kind": "rejection", "symbol": SYM, "direction": LONG,
             "zone_lo": 98, "zone_hi": 102, "levels": ["tie-later"]})
    assert recent()["levels"] == ["PSY"]  # same-ts source tie keeps first row


@pytest.mark.parametrize("stamp,want", [("2026-09-09T16:00Z", ["newyork"]),
    ("2026-01-09T14:00Z", ["frankfurt", "london", "us_brinks"]),
    ("2026-03-20T13:45Z", ["frankfurt", "london", "newyork", "us_brinks"]),
    ("2026-09-06T16:00Z", [])])
def test_original_source_sessions_on_actual_clock(stamp, want):
    at = pd.Timestamp(stamp).to_pydatetime()
    log = make_log(at=at)
    row = {}
    log.log(row)
    assert row["sessions"] == want


@pytest.mark.parametrize("advance", [T-timedelta(microseconds=1), T+timedelta(hours=1,microseconds=1),
    T.replace(tzinfo=None), pd.Timestamp(T)+pd.Timedelta(1, "ns")])
def test_invalid_advance_is_atomic(advance):
    log = make_log()
    with pytest.raises(ValueError):
        log.advance_to(advance)
    assert log.now_epoch() == T.timestamp()
    assert log.snapshot().content == b""


def test_snapshot_handoff_is_detached_and_has_current_publication_time():
    log = make_log()
    log.log({"kind": "first"})
    old = log.snapshot()
    log.advance_to(T+timedelta(minutes=1))
    log.log({"kind": "second"})
    new = log.snapshot()
    assert new.observed_at == new.available_at == T+timedelta(minutes=1)
    assert old.content != new.content and new.content.startswith(old.content)
    assert new.seed_id == old.seed_id and new.covered_through == old.covered_through
    detached = log.trace
    detached[0]["status"] = "bad"
    assert log.trace[0]["status"] == "AVAILABLE"


@pytest.mark.parametrize("kw", [dict(seed_id=""), dict(source=" bad "), dict(seed_id="\ud800"),
    dict(kind="other"), dict(kind="quotes", content=b"{}"), dict(content=""),
    dict(status="ABSENT", content=b""), dict(status="present"),
    dict(observed_at=T.replace(tzinfo=None)), dict(observed_at=T),
    dict(available_at=pd.Timestamp(T)+pd.Timedelta(1,"ns")),
    dict(covered_through=T-timedelta(days=2))])
def test_bad_seed_rejected(kw):
    with pytest.raises(ValueError):
        replace(seed(), **kw)


def test_exact_seed_kind_newline_and_frozen_inputs():
    s = seed()
    with pytest.raises(FrozenInstanceError):
        s.content = b"changed"
    with pytest.raises(ValueError):
        api().CausalQuoteReader(seed=s, decision_time=T)
    with pytest.raises(ValueError):
        api().CausalWatchLog(seed={}, decision_time=T, newline="LF")
    with pytest.raises(ValueError):
        make_log(newline="platform_default")
