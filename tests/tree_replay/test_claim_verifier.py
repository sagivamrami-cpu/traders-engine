"""Actual independent source claim routing, venue decoder and chronological boundaries."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
from types import SimpleNamespace

import pandas as pd
import pytest

from trading_system.tree_replay.clock import ReplayClock
from trading_system.tree_replay._vendor.desk_success import DeskSuccess
from trading_system.tree_replay._vendor import lifecycle_bars


T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
NOW = T + timedelta(minutes=45)


def api():
    name = "trading_system.tree_replay._vendor.claim_verifier"
    assert importlib.util.find_spec(name) is not None, "claim verifier missing"
    return importlib.import_module(name)


def tape(rows):
    return pd.DataFrame([dict(open=lo, high=hi, low=lo, close=hi) for _, hi, lo in rows],
        index=pd.DatetimeIndex([T+timedelta(minutes=m) for m, _, _ in rows]))


def trade(**changes):
    return dict(symbol="OANDA:XAUUSD", direction="לונג", trade_id="claim-one",
        ts=T.timestamp(), filled_ts=(T+timedelta(minutes=15)).timestamp(),
        entry=100., stop=90., targets=[("TP1", 120.)], state="OPEN") | changes


class Ports:
    def __init__(self, frame=None, *, now=NOW, correction=None, rows=None,
                 symbol="OANDA:XAUUSD", days=3):
        self.clock = ReplayClock(now)
        self.frame, self.correction, self.rows = frame, correction, rows
        self.symbol, self.days = symbol, days
        self.calls = []

    def now_utc(self):
        self.calls.append(("utc", self.clock.now))
        return self.clock.now

    def now_epoch(self):
        self.calls.append(("epoch", self.clock.now))
        return self.clock.now.timestamp()

    def fetch_corrected(self, symbol, timeframe, days):
        self.calls.append(("local", symbol, timeframe, days))
        assert (symbol, timeframe, days) == (self.symbol, "15m", self.days)
        if isinstance(self.frame, Exception):
            raise self.frame
        return self.frame, self.correction

    def fetch_json(self, url, *, timeout):
        self.calls.append(("json", url, timeout))
        if isinstance(self.rows, Exception):
            raise self.rows
        return self.rows


def engine(frame=None, **options):
    return api().ClaimVerifier(Ports(frame, **options))


@pytest.mark.parametrize("direction,hi,lo,target", [("לונג", 120., 99., 110.), ("שורט", 101., 80., 90.)])
def test_independent_fill_slack_and_fill_bar_target_differ_from_resolver(direction, hi, lo, target):
    df = tape([(0, hi, lo)])
    t = trade(direction=direction, state="PENDING", filled_ts=None)
    before = deepcopy(t)
    e = engine(df)
    assert lifecycle_bars._fill_on_tape(df, t) is None
    assert api()._fill_index(df, t) == pd.Timestamp(T)
    result = e.target(t, target)
    assert result.ok and not result.stale and result.claim == f"TP @ {target:,.2f}"
    assert t == before
    pd.testing.assert_frame_equal(df, tape([(0, hi, lo)]))


@pytest.mark.parametrize("send_minutes,spacing,want", [(14., 15., 0), (15., 15., 15), (29., 30., 0), (30., 30., 30)])
def test_fill_slack_uses_actual_spacing_and_strict_lower_boundary(send_minutes, spacing, want):
    api()
    df = tape([(0, 101., 99.), (spacing, 101., 99.)])
    got = api()._fill_index(df, trade(ts=(T+timedelta(minutes=send_minutes)).timestamp()))
    assert got == pd.Timestamp(T+timedelta(minutes=want))


def test_target_claim_cannot_be_repaired_by_later_touch():
    df = tape([(0, 101., 99.), (15, 103., 100.), (30, 120., 100.)])
    e = engine(df)
    t = trade(claim_ts=(T+timedelta(minutes=15)).timestamp())
    r = e.target(t, 110.)
    assert not r and not r.stale and "המחיר לא הגיע" in r.reason
    t["claim_ts"] = (T+timedelta(minutes=30)).timestamp()
    assert e.target(t, 110.)


def test_stop_uses_resolved_clock_before_claim_clock():
    df = tape([(0, 101., 99.), (15, 103., 98.), (30, 103., 89.)])
    t = trade(resolved_ts=(T+timedelta(minutes=15)).timestamp(), claim_ts=(T+timedelta(minutes=30)).timestamp())
    e = engine(df)
    r = e.stop(t)
    assert not r and not r.stale
    del t["resolved_ts"]
    assert e.stop(t)


@pytest.mark.parametrize("method", ["target", "stop"])
def test_nonreach_stale_is_distinct_from_closed_tape_contradiction(method):
    e = engine(tape([(0, 101., 99.), (15, 103., 98.)]))
    t = trade(claim_ts=NOW.timestamp(), resolved_ts=NOW.timestamp())
    args = (t, 110.) if method == "target" else (t,)
    r = getattr(e, method)(*args)
    assert not r and r.stale and r.reason == "הטייפ עוד לא מכסה את רגע הטענה — ממתין"
    e.source.frame = tape([(0, 101., 99.), (45, 103., 98.)])
    r = getattr(e, method)(*args)
    assert not r and not r.stale


@pytest.mark.parametrize("method", ["target", "stop"])
def test_missing_fill_distinguishes_unseen_from_contradicted(method):
    e = engine(tape([(0, 120., 110.), (15, 120., 110.)]))
    t = trade(filled_ts=(T+timedelta(minutes=20)).timestamp())
    args = (t, 130.) if method == "target" else (t,)
    r = getattr(e, method)(*args)
    assert not r and r.stale
    e.source.frame = tape([(0, 120., 110.), (30, 120., 110.)])
    r = getattr(e, method)(*args)
    assert not r and not r.stale


@pytest.mark.parametrize("age_seconds,want_stale", [(2699., True), (2700., False), (2701., False)])
def test_fill_grace_is_strictly_less_than_45_minutes(age_seconds, want_stale):
    e = engine(tape([(0, 120., 110.), (45, 120., 110.)]))
    t = trade(filled_ts=NOW.timestamp()-age_seconds)
    r = e.fill(t)
    assert not r and r.stale is want_stale


def test_fill_stale_when_tape_does_not_reach_filled_stamp_even_after_grace():
    e = engine(tape([(0, 120., 110.)]), now=NOW+timedelta(hours=2))
    r = e.fill(trade(filled_ts=(T+timedelta(minutes=30)).timestamp()))
    assert not r and r.stale and "לפני רגע המילוי" in r.reason


@pytest.mark.parametrize("method", ["target", "stop", "fill"])
@pytest.mark.parametrize("frame", [None, pd.DataFrame()])
def test_missing_tape_blocks_claims(method, frame):
    e = engine(frame)
    r = e.target(trade(), 110.) if method == "target" else getattr(e, method)(trade())
    assert not r and not r.stale and r.reason == "אין נתונים לאימות"


@pytest.mark.parametrize("symbol,tolerance", [("OANDA:XAUUSD", .5), ("OANDA:NAS100USD", 3.), ("BINANCE:BTCUSDT", 15.), ("OTHER", 1.)])
@pytest.mark.parametrize("short", [False, True])
def test_real_target_and_stop_comparisons_use_literal_instrument_tolerances(symbol, tolerance, short):
    # Venue decoding is real for BTC; no replacement of _bars or _fill_index.
    direction = "שורט" if short else "לונג"
    entry, target, stop = 1000., (800. if short else 1200.), (1200. if short else 800.)
    def evaluate(extra):
        hi = stop-tolerance-extra if short else target-tolerance-extra
        lo = target+tolerance+extra if short else stop+tolerance+extra
        df = tape([(0, 1001., 999.), (30, hi, lo)])
        rows = [[int(i.timestamp()*1000), r.open, r.high, r.low, r.close] for i, r in df.iterrows()]
        e = engine(df, symbol=symbol, rows=rows)
        t = trade(symbol=symbol, direction=direction, entry=entry, stop=stop, claim_ts=(T+timedelta(minutes=30)).timestamp())
        return e.target(t, target), e.stop(t)
    target_ok, stop_ok = evaluate(0.)
    assert target_ok and stop_ok
    target_miss, stop_miss = evaluate(.01)
    assert not target_miss and not target_miss.stale
    assert not stop_miss and not stop_miss.stale


def test_binance_venue_first_real_decode_exact_request_and_no_local_read():
    rows = [[1788969600000, "100", "105", "99", "104", "999"]]
    before = deepcopy(rows)
    e = engine(RuntimeError("local must not be used"), symbol="BINANCE:BTCUSDT", rows=rows)
    df = e._bars("BINANCE:BTCUSDT")
    expected = tape([(0, 105., 99.)])
    expected["open"], expected["close"] = 100., 104.
    expected.index.name = "t"
    pd.testing.assert_frame_equal(df, expected, check_dtype=False)
    assert rows == before and len(e.source.calls) == 2
    assert e.source.calls[1] == ("json", "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=15m&startTime=1788713100000&limit=1000", 15)


@pytest.mark.parametrize("rows", [None, [], ValueError("transport"), [[0, "bad", "2", "1", "2"]], [[0]]])
def test_failed_or_empty_venue_falls_back_to_original_local_fetch(rows):
    df = tape([(0, 101., 99.)])
    e = engine(df, symbol="BINANCE:BTCUSDT", rows=rows)
    assert e._bars("BINANCE:BTCUSDT") is df
    assert [c[0] for c in e.source.calls] == ["utc", "json", "local"]
    assert e.source.calls[-1] == ("local", "BINANCE:BTCUSDT", "15m", 3)


def test_custom_days_propagate_to_venue_request_and_fallback():
    e = engine(tape([(0, 101., 99.)]), symbol="BINANCE:BTCUSDT", days=2, rows=[])
    e._bars("BINANCE:BTCUSDT", 2)
    assert "startTime=1788799500000&limit=1000" in e.source.calls[1][1]
    assert e.source.calls[-1] == ("local", "BINANCE:BTCUSDT", "15m", 2)


def test_empty_venue_frame_is_not_replaced_by_local_tape():
    # The decoder returns None for empty JSON, not an empty DataFrame. Isolate
    # this distinct _bars precedence boundary; decoder tests above stay real.
    empty = pd.DataFrame(columns=["open", "high", "low", "close"])
    class EmptyVenue(api().ClaimVerifier):
        def _binance_bars(self, symbol, days):
            assert (symbol, days) == ("BINANCE:BTCUSDT", 3)
            return empty
    source = Ports(tape([(0, 120., 89.)]), symbol="BINANCE:BTCUSDT")
    e = EmptyVenue(source)
    assert e._bars("BINANCE:BTCUSDT") is empty
    result = e.target(trade(symbol="BINANCE:BTCUSDT"), 110.)
    assert not result and result.reason == "אין נתונים לאימות"
    assert source.calls == []


@pytest.mark.parametrize("correction,blocked", [(None, False), (SimpleNamespace(unverified=True), True), (SimpleNamespace(unverified=False, source="tv_stale"), False)])
def test_local_path_preserves_only_original_unverified_veto(correction, blocked):
    df = tape([(0, 101., 99.)])
    e = engine(df, correction=correction)
    got = e._bars("OANDA:XAUUSD")
    assert (got is None) if blocked else (got is df)
    assert e.source.calls == [("local", "OANDA:XAUUSD", "15m", 3)]


@pytest.mark.parametrize("text,ok,claim", [
    ("✅ XAUUSD BUY 100.00 · הושג @ 110.00", True, "TP @ 110.00"),
    ("✅ XAUUSD BUY 100.00 · הושג @ 130.00", False, "TP @ 130.00"),
    ("✅ XAUUSD BUY 100.00", False, ""),
    ("▶️ XAUUSD BUY 100.00 · נכנסה", True, "fill @ 100.00"),
    ("🛑 XAUUSD BUY 100.00", True, "stop @ 90.00"),
    ("🔒 XAUUSD BUY 100.00 · רשות", True, ""),
    ("📈 XAUUSD BUY 100.00 · +40 פיפס", True, ""),
])
def test_actual_message_router_runs_real_claim_comparisons(text, ok, claim):
    e = engine(tape([(0, 101., 99.), (45, 120., 89.)]))
    t = trade()
    before = deepcopy(t)
    r = e.check_message("  "+text+"  ", t)
    assert bool(r) is ok and r.claim == claim
    assert t == before
    if claim:
        assert e.source.calls[0] == ("local", "OANDA:XAUUSD", "15m", 3)


def test_minimum_message_uses_actual_proof_dependency_and_no_tape_fetch():
    e = engine(RuntimeError("not used"))
    t = trade()
    message = DeskSuccess(e.source).observe(t, 105., NOW.timestamp(), "exact_venue_quote")
    e.source.calls.clear()
    assert e.check_message(message, t)
    assert [c[0] for c in e.source.calls] == ["epoch"]
    t["trade_id"] = "different"
    assert not e.check_message(message, t)


@pytest.mark.parametrize("text,frame", [("▶️ XAUUSD", RuntimeError("offline read")), ("🛑 XAUUSD", tape([(0, 101., 99.)])), (None, None)])
def test_router_contains_exceptions_instead_of_blessing_claim(text, frame):
    e = engine(frame)
    t = trade()
    if text and text.startswith("🛑"):
        del t["stop"]
    r = e.check_message(text, t)
    assert not r and r.reason.startswith("האימות נכשל:")


@pytest.mark.parametrize("row,want", [({"resolved_ts": 123., "claim_ts": 456.}, 123.), ({"resolved_ts": "bad", "claim_ts": 456.}, 456.), ({"resolved_ts": 0, "claim_ts": None}, NOW.timestamp())])
def test_claim_clock_first_usable_key_and_explicit_operation_fallback(row, want):
    assert engine()._claim_clock(row, "resolved_ts", "claim_ts") == want


def test_internal_coverage_predicates_do_not_certify_missing_data():
    m = api()
    df = tape([(0, 101., 99.)])
    assert m._covers(df, (T+timedelta(minutes=15)).timestamp())
    assert not m._covers(df, (T+timedelta(minutes=15, microseconds=1)).timestamp())
    assert not m._closed_past(df, (T+timedelta(microseconds=1)).timestamp())
    assert m._closed_past(df, T.timestamp())
    assert m._covers(None, NOW.timestamp()) and m._covers(pd.DataFrame(), NOW.timestamp())
    assert m._extreme(pd.DataFrame(), "high") is None
    assert m._extreme(pd.DataFrame({"high": [float("nan")]}), "high") is None
