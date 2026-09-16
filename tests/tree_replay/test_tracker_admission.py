"""Behavioral source-contract tests; all state, frames, quotes and bytes synthetic."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from io import BytesIO
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from trading_system.tree_replay._vendor.pricing import Plan

NOW = 1788775200.0
SYM = "OANDA:XAUUSD"
LONG, SHORT = "לונג", "שורט"


def module():
    try:
        return importlib.import_module("trading_system.tree_replay._vendor.tracker_admission")
    except ModuleNotFoundError as exc:
        pytest.fail(f"tracker admission implementation missing: {exc}")


class MemoryPorts:
    def __init__(self, rows=None):
        self.rows = deepcopy(rows if rows is not None else {})
        self.calls = []
        self.nets = {tf: 0.0 for tf in ("4h", "1h", "30m", "15m", "5m")}
        self.frame = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        self.quotes = {}
        self.raw = b""
        self.on_lock = None
        self.fail = set()

    def load(self):
        self.calls.append("load")
        if "load" in self.fail:
            raise OSError("state unavailable")
        return deepcopy(self.rows)

    def save(self, rows):
        self.calls.append("save")
        if "save" in self.fail:
            raise OSError("sink failed")
        self.rows = deepcopy(rows)

    def now_epoch(self):
        return NOW

    @contextmanager
    def locked(self):
        self.calls.append("lock")
        if self.on_lock:
            self.on_lock()
        yield
        self.calls.append("unlock")

    def event_log_reader(self):
        self.calls.append("log")
        if "log" in self.fail:
            raise OSError("log unavailable")
        if self.raw is None:
            raise OSError("log unavailable")
        return BytesIO(self.raw)

    def quote_payload(self):
        self.calls.append("quotes")
        if "quotes" in self.fail:
            raise OSError("quotes unavailable")
        return self.quotes

    def read_symbol(self, symbol, tfs):
        self.calls.append(("matrix", symbol, tfs))
        if "matrix" in self.fail:
            raise OSError("matrix unavailable")
        return {tf: SimpleNamespace(net=self.nets[tf], bar_ts=NOW) if tf in self.nets else None
                for tf in tfs}

    def fetch_corrected(self, symbol, timeframe, lookback_days):
        self.calls.append(("frame", symbol, timeframe, lookback_days))
        if "frame" in self.fail:
            raise OSError("frame unavailable")
        return self.frame.copy(), None


def plan(**kw):
    return replace(Plan(SYM, 110.0, "reversal", LONG, entry=100.0, stop=90.0,
                        targets=[("TP1", 120.0), ("TP2", 130.0)],
                        reasons=["רמה: DAY-OPEN"], obstacles=[("near", 105.0)]), **kw)


def stopped(**kw):
    return dict(symbol=SYM, direction=LONG, state="STOPPED", ts=NOW-7200,
                resolved_ts=NOW-3600, stop=90.0, entry=100.0, **kw)


@pytest.mark.parametrize("rows,want", [({}, False), ({"x": {"state": "PENDING"}}, False),
    ({"x": {"state": "OPEN", "symbol": SYM, "direction": LONG}}, True),
    ({"x": {"state": "OPEN", "symbol": SYM, "direction": SHORT}}, False),
    ({"x": {}}, True), ({"x": None}, True), ([], True),
    ({"x": {"state": "OPEN"}}, True)])
def test_exposure_is_open_only_and_corruption_fails_closed(rows, want):
    assert module().TrackerAdmission(MemoryPorts(rows)).has_open(SYM, LONG) is want


def test_record_persists_complete_pending_row_and_calculates_before_lock():
    p, ports = plan(), MemoryPorts()
    assert module().TrackerAdmission(ports).record(p, variant="test", to_group=True)
    assert p.born_open is False
    key, row = next(iter(ports.rows.items()))
    assert key.startswith(SYM + ":" + LONG + ":100.0:intraday:")
    assert len(row["trade_id"]) == 16 and key.endswith(row["trade_id"])
    assert row == dict(symbol=SYM, direction=LONG, entry=100.0, stop=90.0,
        targets=[["TP1", 120.0], ["TP2", 130.0]], obstacles=[["near", 105.0]],
        reasons=["רמה: DAY-OPEN"], variant="test", to_group=True, style="intraday",
        trade_id=row["trade_id"], kind="reversal", state="PENDING", hit=[], ts=NOW,
        thesis_state="held", thesis_warned=False, bias_at_send={"4h": 0.0, "1h": 0.0})
    assert ports.calls == [("matrix", SYM, ("4h", "1h")),
        ("matrix", SYM, ("4h", "1h", "30m", "15m", "5m")), "lock", "load", "save", "unlock"]


def test_record_born_open_is_not_broker_verified():
    ports, p = MemoryPorts(), plan(close=100.0)
    assert module().TrackerAdmission(ports).record(p)
    row = next(iter(ports.rows.values()))
    assert p.born_open is True and row["state"] == "OPEN"
    assert row["born_in_zone"] is True and row["revalidation_verified"] is False
    assert row["fill_verification_reason"] == "born_open_not_broker_verified"
    assert row["ts"] == row["filled_ts"] == row["progress_ts"] == NOW


def test_record_duplicate_geometry_and_resolved_archive_collision():
    ports = MemoryPorts()
    tracker = module().TrackerAdmission(ports)
    assert tracker.record(plan())
    original = deepcopy(ports.rows)
    assert tracker.record(plan()) is False and ports.rows == original
    key = next(iter(ports.rows))
    ports.rows[key]["state"] = "DONE"
    ports.rows[key]["ts"] = 123.75
    old = deepcopy(ports.rows[key])
    ports.rows[key + "@123"] = {"state": "CANCELLED"}
    assert tracker.record(plan())
    assert ports.rows[key + "@123"] == old
    assert ports.rows[key]["state"] == "PENDING"


@pytest.mark.parametrize("change", [dict(style="swing"), dict(stop=89.0),
    dict(targets=[("TP1", 120.0), ("TP2", 131.0)]), dict(entry=100.00001)])
def test_pending_distinct_geometry_coexists(change):
    ports = MemoryPorts()
    tracker = module().TrackerAdmission(ports)
    assert tracker.record(plan()) and tracker.record(plan(**change))
    assert len(ports.rows) == 2


def test_record_reloads_and_rechecks_open_inside_lock():
    ports = MemoryPorts()
    ports.on_lock = lambda: ports.rows.update(x={"state": "OPEN", "symbol": SYM, "direction": LONG})
    assert module().TrackerAdmission(ports).record(plan()) is False
    assert ports.calls[-3:] == ["lock", "load", "unlock"]
    assert list(ports.rows) == ["x"]


def test_save_failure_propagates_without_persisting_success():
    ports = MemoryPorts()
    ports.fail.add("save")
    with pytest.raises(OSError, match="sink failed"):
        module().TrackerAdmission(ports).record(plan())
    assert ports.rows == {}


@pytest.mark.parametrize("side,net,want", [(SHORT, 25, True), (SHORT, 24.999, False),
    (LONG, -25, True), (LONG, -24.999, False), (LONG, 25, False), (SHORT, -25, False)])
def test_post_stop_signed_sum_boundary_precedes_structure(side, net, want):
    row = stopped(); row["direction"] = side
    ports = MemoryPorts({"x": row}); ports.nets.update({"4h": net+5, "1h": -5})
    result = module().TrackerAdmission(ports).blocked_after_stop(SYM, side)
    assert (result is None) is want
    assert ports.calls[:2] == ["load", ("matrix", SYM, ("4h", "1h"))]
    assert (("frame", SYM, "15m", 5) in ports.calls) is not want


@pytest.mark.parametrize("age,released", [(14400, True), (14399.999, False)])
def test_stop_age_boundary_before_dependencies(age, released):
    row = stopped(); row["resolved_ts"] = NOW-age
    ports = MemoryPorts({"x": row})
    assert (module().TrackerAdmission(ports).blocked_after_stop(SYM, LONG) is None) is released
    if released:
        assert ports.calls == ["load"]


@pytest.mark.parametrize("side,n,want", [(LONG, 8, True), (SHORT, 8, True), (LONG, 7, False), (SHORT, 7, False)])
def test_post_stop_uses_actual_confirmed_swing(side, n, want):
    row = stopped(); row.update(direction=side, stop=90 if side == LONG else 110)
    ports = MemoryPorts({"x": row})
    highs = [80,80,80,85,80,80,80,80] if side == LONG else [140]*8
    lows = [60]*8 if side == LONG else [130,130,130,120,130,130,130,130]
    ports.frame = pd.DataFrame({"high": highs[:n], "low": lows[:n]},
        index=pd.to_datetime([row["resolved_ts"] + 60*(i+1) for i in range(n)], unit="s", utc=True))
    assert (module().TrackerAdmission(ports).blocked_after_stop(SYM, side) is None) is want


@pytest.mark.parametrize("side,entry,released", [(LONG, 89.99, True), (LONG, 89.991, False),
    (SHORT, 90.01, True), (SHORT, 90.009, False)])
@pytest.mark.parametrize("anchors", [False, True])
def test_entry_crosses_by_source_pip_with_optional_unchanged_anchor(side, entry, released, anchors):
    row = stopped(); row["direction"] = side
    if anchors:
        row["reasons"] = ["רמה: DAY-OPEN"]
    ports, p = MemoryPorts({"x": row}), plan(entry=entry, direction=side)
    assert (module().TrackerAdmission(ports).blocked_after_stop(SYM, side, p) is None) is released
    if released:
        assert p.cooldown_release["boundary_margin"] == .01
        assert p.cooldown_release["anchor_changed"] is (False if anchors else None)
        assert p.cooldown_release["recent_rejection"] is None
    else:
        assert p.cooldown_release is None


@pytest.mark.parametrize("state,age,entry,blocked", [("DONE", 7199, 98, True),
    ("CANCELLED", 7199, 102, True), ("DONE", 7200, 100, False),
    ("DONE", 10, 102.001, False), ("STOPPED", 10, 100, False),
    ("PENDING", 10, 100, False), ("DONE", -1, 100, True)])
def test_same_level_state_age_and_inclusive_band(state, age, entry, blocked):
    row = stopped(); row.update(state=state, resolved_ts=NOW-age)
    result = module().TrackerAdmission(MemoryPorts({"x": row})).blocked_same_level(SYM, LONG, entry)
    assert (result is not None) is blocked


@pytest.mark.parametrize("age,price,valid", [(0, 100, True), (420,100,True),
    (420.0001,100,False), (-.001,100,False), (0,0,False), (0,-1,False),
    (0,float("nan"),False), (0,float("inf"),False)])
def test_quote_freshness_and_price_validation(age, price, valid):
    ports = MemoryPorts(); ports.quotes = {SYM: {"lp": price, "ts": NOW-age}}
    assert module().TrackerAdmission(ports)._live_prices() == ({SYM: price} if valid else {})


@pytest.mark.parametrize("side,close,spot,age,born", [(LONG,100,90,0,True),
    (SHORT,100,110,0,True), (LONG,100,103,0,False), (SHORT,100,97,0,False),
    (LONG,100,103,421,True), (LONG,103,100,0,False), (LONG,98,100,0,True),
    (LONG,102,100,0,True)])
def test_born_requires_build_band_then_one_sided_quote(side, close, spot, age, born):
    ports = MemoryPorts(); ports.quotes = {SYM: {"lp": spot, "ts": NOW-age}}
    assert module().TrackerAdmission(ports)._born_in_zone(plan(direction=side, close=close), SYM) is born


@pytest.mark.parametrize("side,lo,want", [(LONG,-25,"broken"),(LONG,-24.99,None),
    (LONG,0,"held"),(SHORT,25,"broken"),(SHORT,24.99,None),(SHORT,0,"held")])
def test_thesis_hysteresis(side, lo, want):
    assert module().thesis_verdict(lo, side) == want


def rejection(**kw):
    row = dict(kind="rejection", symbol=SYM, direction=LONG, ts=NOW-20,
               zone_lo=99, zone_hi=101, levels=["first"], close=100, wick_atr=1.5)
    row.update(kw)
    return json.dumps(row, ensure_ascii=False).encode() + b"\n"


def test_rejection_equal_timestamp_keeps_first_and_ignores_trailing_malformed():
    ports = MemoryPorts()
    ports.raw = b'junk\xff\n' + rejection() + rejection(levels=["second"]) + b'{"kind":"rejection",'
    result = module().TrackerAdmission(ports)._recent_rejection(SYM, LONG, NOW-100, NOW, 100)
    assert result == dict(ts=NOW-20, direction=LONG, zone_lo=99, zone_hi=101,
        levels=["first"], close=100, wick_atr=1.5, age_s=20.0, gap=0.0)


@pytest.mark.parametrize("age,gap,overlap,max_dist,want", [(1200,0,True,None,True),
    (1200.001,0,True,None,False), (0,0,True,None,True), (-1,0,True,None,False),
    (10,1,True,None,False), (10,1,False,1,True), (10,1.001,False,1,False)])
def test_rejection_age_overlap_distance_boundaries(age,gap,overlap,max_dist,want):
    ports = MemoryPorts(); ports.raw = rejection(ts=NOW-age, zone_lo=102+gap, zone_hi=104+gap)
    result = module().TrackerAdmission(ports)._recent_rejection(SYM,LONG,NOW-1200,NOW,100,
        require_overlap=overlap,max_distance=max_dist)
    assert (result is not None) is want


def test_tail_expands_huge_last_line_and_preserves_partial_trailing_line():
    tail = module()._tail_bytes
    assert tail(b"first\nsecond\nthird", window=10) == b"third"
    raw = b"evidence\n" + b"x"*100 + b"\n"
    assert tail(raw, window=4, cap=16) == raw
    assert tail(None) is None
    assert tail(b"") == b""


def test_non_rejection_bytes_eject_old_rejection_from_original_tail():
    ports = MemoryPorts(); ports.raw = rejection() + (b'{"kind":"other"}\n'*26000)
    assert module().TrackerAdmission(ports)._recent_rejection(SYM,LONG,NOW-100,NOW,100) is None


def test_port_errors_retain_asymmetric_source_outcomes():
    ports = MemoryPorts(); ports.fail.add("load")
    tracker = module().TrackerAdmission(ports)
    assert tracker.has_open(SYM,LONG) is True
    assert tracker.blocked_after_stop(SYM,LONG) is None
    assert tracker.blocked_same_level(SYM,LONG,100) is None
    with pytest.raises(OSError,match="state unavailable"):
        tracker.record(plan())
    ports.fail = {"matrix", "quotes"}
    assert tracker._higher_bias(SYM) is None and tracker._thesis_baseline(SYM,LONG) == "held"
    assert tracker._born_in_zone(plan(close=100),SYM) is True


def test_thesis_actual_frames_and_incomplete_higher_reading():
    ports = MemoryPorts(); ports.nets.update({"4h":40,"1h":20,"30m":-90,"15m":0,"5m":0})
    tracker = module().TrackerAdmission(ports)
    assert tracker.thesis_now(SYM) == (30,-30,NOW)
    assert tracker._thesis_baseline(SYM,LONG) == "broken"
    del ports.nets["1h"]
    assert tracker._higher_bias(SYM) is None and tracker.thesis_now(SYM) is None


def test_reader_opens_lazily_and_catches_open_failure():
    ports = MemoryPorts(); ports.fail.add("log")
    assert module().TrackerAdmission(ports)._recent_rejection(SYM,LONG,NOW-100,NOW,100) is None
    assert ports.calls == ["log"]


def test_reader_consumes_tail_bytes_not_full_historical_prefix():
    # A virtual ten-billion-byte prefix: the spy never allocates that prefix.
    class Reader:
        size = 10_000_000_000
        def __init__(self):
            self.pos = 0; self.consumed = 0; self.seeks = []; self.closed = False
        def __enter__(self):
            return self
        def __exit__(self,*args):
            self.closed = True
        def seek(self,offset,whence=0):
            self.seeks.append((offset,whence))
            self.pos = offset + (self.size if whence == 2 else 0)
        def tell(self):
            return self.pos
        def read(self):
            n = self.size-self.pos
            assert n <= 400000, "source tail eagerly read the entire historical prefix"
            self.consumed += n; self.pos = self.size
            return b"x\n"*(n//2)
    reader = Reader()
    result = module()._tail_reader(lambda: reader)
    assert result == b"x\n"*199999
    assert reader.consumed == 400000 and reader.closed
    assert reader.seeks == [(0,2),(9_999_600_000,0)]


def test_private_closure_isolated_import_and_run_has_no_hidden_io():
    script = r'''
import sys, time, json
from pathlib import Path
from io import BytesIO
from copy import deepcopy
from contextlib import nullcontext
from types import SimpleNamespace
import pandas as pd
import numpy.rec
from trading_system.tree_replay._vendor.pricing import Plan
import trading_system.tree_replay._vendor.admission_quality
import trading_system.tree_replay._vendor.admission_swing
sys.dont_write_bytecode = True
violations = []
importing = True
def audit(event,args):
    if event == 'open':
        path = str(args[0]).replace('\\','/')
        if importing and '/trading_system/tree_replay/_vendor/' in path and path.endswith(('.py','.pyc')):
            return
        violations.append((event,path))
        raise RuntimeError('hidden filesystem access')
    if event.startswith(('socket.','subprocess.','os.system')):
        violations.append((event,''))
        raise RuntimeError('hidden external I/O')
def wall():
    violations.append(('wall-clock',''))
    raise RuntimeError('hidden wall clock')
sys.addaudithook(audit)
time.time = wall
from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission
from trading_system.tree_replay._vendor import tracker_symbols
importing = False
class Ports:
    def __init__(self): self.rows = {}
    def load(self): return deepcopy(self.rows)
    def save(self,rows): self.rows = deepcopy(rows)
    def locked(self): return nullcontext()
    def now_epoch(self): return 1788775200.0
    def read_symbol(self,symbol,tfs): return {tf:SimpleNamespace(net=0.,bar_ts=1788775200.) for tf in tfs}
    def fetch_corrected(self,*args): return pd.DataFrame(columns=['high','low']),None
    def event_log_reader(self): return BytesIO(b'')
    def quote_payload(self): return {}
p = Ports(); t = TrackerAdmission(p)
long = '\u05dc\u05d5\u05e0\u05d2'; sym = 'OANDA:XAUUSD'
plan = Plan(sym,100.,'reversal',long,entry=100.,stop=90.,targets=[('TP1',120.)])
assert not t.has_open(sym,long)
assert t.record(plan) and t.has_open(sym,long)
row = next(iter(p.rows.values())); row.update(state='STOPPED',resolved_ts=1788771600.)
plan.entry = 89.99
assert t.blocked_after_stop(sym,long,plan) is None and plan.cooldown_release is not None
row['state'] = 'DONE'
assert t.blocked_same_level(sym,long,100.) is not None
assert violations == [], violations
print('isolated tracker closure: no hidden I/O')
'''
    result = subprocess.run([sys.executable,"-B","-c",script],capture_output=True,text=True,
                            cwd=Path(__file__).resolve().parents[2],timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "no hidden I/O" in result.stdout


def test_latest_same_side_stop_controls_gate_and_missing_ts_preserves_source_catch():
    old = stopped(); old["resolved_ts"] = NOW-20000
    recent = stopped(); recent["resolved_ts"] = NOW-100
    ports = MemoryPorts({"old": old,"new": recent})
    tracker = module().TrackerAdmission(ports)
    assert tracker.blocked_after_stop(SYM,LONG) is not None
    # Source evaluates t['ts'] as the get default even with resolved_ts present.
    del ports.rows["new"]["ts"]
    assert tracker.blocked_after_stop(SYM,LONG) is None


def test_swing_excludes_bar_exactly_at_stop_time():
    row = stopped(); ports = MemoryPorts({"x": row})
    ports.frame = pd.DataFrame({"high": [80,80,80,85,80,80,80,80], "low": [60]*8},
        index=pd.to_datetime([row["resolved_ts"]+60*i for i in range(8)],unit="s",utc=True))
    assert module().TrackerAdmission(ports).blocked_after_stop(SYM,LONG) is not None


@pytest.mark.parametrize("rows,want", [
    ({"x": {"state":"OPEN","symbol":SYM}}, True),
    ({"x": {"state":"OTHER"}}, False),
    ({"x": {"state":"OPEN","symbol":"other"}}, False),
])
def test_exposure_direction_none_and_source_unknown_state(rows,want):
    assert module().TrackerAdmission(MemoryPorts()).has_open(SYM,state=rows) is want


@pytest.mark.parametrize("resolved,want", [(0,False),(None,False),("bad",False),(float("nan"),False)])
def test_same_level_unreadable_or_legacy_clock(resolved,want):
    row = stopped(); row.update(state="DONE",resolved_ts=resolved)
    assert (module().TrackerAdmission(MemoryPorts({"x":row})).blocked_same_level(SYM,LONG,100) is not None) is want


def test_same_level_first_match_and_malformed_row_abort():
    a = stopped(); a.update(state="DONE",entry=100,resolved_ts=NOW-60)
    b = stopped(); b.update(state="CANCELLED",entry=101,resolved_ts=NOW-30)
    ports = MemoryPorts({"a":a,"b":b}); tracker = module().TrackerAdmission(ports)
    assert "100.00" in tracker.blocked_same_level(SYM,LONG,101)
    del ports.rows["a"]["entry"]
    assert tracker.blocked_same_level(SYM,LONG,101) is None


@pytest.mark.parametrize("change", [dict(entry=0),dict(stop=0),dict(entry=None),dict(stop=None)])
def test_record_missing_geometry_does_not_read_dependencies(change):
    ports = MemoryPorts()
    assert module().TrackerAdmission(ports).record(plan(**change)) is False
    assert ports.rows == {} and ports.calls == []


def test_record_unread_matrix_omits_optional_bias_and_defaults_thesis():
    ports = MemoryPorts(); ports.fail.add("matrix")
    assert module().TrackerAdmission(ports).record(plan())
    row = next(iter(ports.rows.values()))
    assert "bias_at_send" not in row and row["thesis_state"] == "held"


def test_identity_canonical_rounding_target_names_and_style_case():
    identity = module()._trade_identity
    a = identity("GOLD",LONG,100,90,[("one",120),("two",130)],"INTRADAY")
    b = identity(SYM,LONG,100.000000001,90,[("renamed",120),("two",130)],"intraday")
    assert a == b
    assert identity("GC",LONG,100,90,[("one",120),("two",130)],"intraday") != a
    assert identity(SYM,LONG,100,90,[("two",130),("one",120)],"intraday") != a


@pytest.mark.parametrize("fault", ["seek","tell","read","enter","exit"])
def test_reader_all_original_io_errors_return_none(fault):
    class Broken(BytesIO):
        def seek(self,*args):
            if fault == "seek": raise OSError("seek")
            return super().seek(*args)
        def tell(self):
            if fault == "tell": raise OSError("tell")
            return super().tell()
        def read(self,*args):
            if fault == "read": raise OSError("read")
            return super().read(*args)
        def __enter__(self):
            if fault == "enter": raise OSError("enter")
            return super().__enter__()
        def __exit__(self,*args):
            super().__exit__(*args)
            if fault == "exit": raise OSError("exit")
    assert module()._tail_reader(lambda:Broken(b"hello\n")) is None


def test_rejection_inclusive_stop_time_newest_not_last_and_gap_rounding():
    ports = MemoryPorts()
    ports.raw = rejection(ts=NOW-10, levels=["newest"],zone_lo=103.234567,zone_hi=104) + rejection(ts=NOW-20)
    result = module().TrackerAdmission(ports)._recent_rejection(SYM,LONG,NOW-10,NOW,100,
        require_overlap=False,max_distance=2)
    assert result["levels"] == ["newest"] and result["gap"] == 1.2346


def test_rejection_missing_zone_fields_retains_source_permissive_selection():
    ports = MemoryPorts(); ports.raw = rejection(zone_lo=None,zone_hi=None)
    result = module().TrackerAdmission(ports)._recent_rejection(SYM,LONG,NOW-100,NOW,100)
    assert result["gap"] == 0.0


def test_rejection_bad_numeric_timestamp_propagates_outside_json_catch():
    ports = MemoryPorts(); ports.raw = rejection(ts="bad")
    with pytest.raises(ValueError):
        module().TrackerAdmission(ports)._recent_rejection(SYM,LONG,NOW-100,NOW,100)


def test_cooldown_uses_explicit_asof_and_survives_missing_log_telemetry():
    ports = MemoryPorts({"x": stopped()}); ports.raw = rejection(ts=NOW,zone_lo=88,zone_hi=90)
    tracker = module().TrackerAdmission(ports); p = plan(entry=89.99)
    rel = tracker._cooldown_release(SYM,LONG,p,stopped(),NOW-3600,1,asof=NOW-1)
    assert rel["recent_rejection"] is None
    ports.fail.add("log")
    assert tracker.blocked_after_stop(SYM,LONG,p) is None
    assert p.cooldown_release["recent_rejection"] is None
