"""Source policy behavior with explicit low-level IO, never operating-system locks."""
from copy import deepcopy
import importlib
import importlib.util
from types import SimpleNamespace

import pytest

from trading_system.tree_replay._vendor.pricing import Plan
from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission


def api():
    name = "trading_system.tree_replay._vendor.tracker_lock"
    assert importlib.util.find_spec(name) is not None, "tracker lock policy missing"
    return importlib.import_module(name)


class IO:
    """Deterministic external-operation fixture; the policy under test is real."""
    def __init__(self, *, acquired=True, marker="900", fail=()):
        self.acquired, self.marker, self.fail = acquired, marker, set(fail)
        self.calls, self.now, self.after_acquire = [], 1000.0, None
        self.handle = SimpleNamespace(close=lambda: self.call("close"))

    def call(self, name, *args):
        self.calls.append((name, *args))
        if name in self.fail:
            raise OSError(name)

    def now_epoch(self):
        self.call("clock", self.now)
        return self.now

    def read_busy(self):
        self.call("read")
        if self.marker is None:
            raise FileNotFoundError("busy marker absent")
        return self.marker

    def write_busy(self, text):
        self.call("write", text)
        self.marker = text

    def clear_busy(self):
        self.call("clear")
        self.marker = None

    def ensure_lock_directory(self):
        self.call("mkdir")

    def open_lock(self):
        self.call("open")
        return self.handle

    def try_acquire(self, handle, *, timeout):
        assert handle is self.handle
        self.call("acquire", timeout)
        if self.after_acquire:
            self.after_acquire()
        return self.acquired

    def release(self, handle):
        assert handle is self.handle
        self.call("release")

    def warn(self, text):
        self.call("warn", text)


@pytest.mark.parametrize("kwargs,wait", [({}, 30.0), ({"skip_if_busy": True}, 3.0),
    ({"skip_if_busy": True, "wait": 30.0}, 30.0), ({"wait": 0}, 0),
    ({"wait": -2}, -2)])
def test_success_keeps_wait_choice_and_original_operation_order(kwargs, wait):
    io = IO()
    policy = api().TrackerLock(io)
    with policy.locked(**kwargs):
        io.call("body", policy.held["depth"])
    assert io.calls == [("mkdir",), ("open",), ("acquire", wait), ("clear",),
                        ("body", 1), ("release",), ("close",)]
    assert policy.held == {"depth": 0} and io.marker is None


@pytest.mark.parametrize("marker,entered", [
    ("880.001", False), ("880", True), ("879", True), ("1001", False),
    ("nan", True), ("inf", False), ("-inf", True)])
def test_resolver_busy_age_boundary_preserves_source_float_semantics(marker, entered):
    io = IO(acquired=False, marker=marker)
    policy = api().TrackerLock(io)
    bodies = []
    if entered:
        with policy.locked(skip_if_busy=True):
            bodies.append(policy.held["depth"])
        assert bodies == [1]
        assert any(c[0] == "warn" for c in io.calls)
    else:
        with pytest.raises(api().LockBusy, match="held elsewhere for 3s"):
            with policy.locked(skip_if_busy=True):
                bodies.append("must not enter")
        assert bodies == [] and not any(c[0] == "warn" for c in io.calls)
    assert io.calls[-1] == ("close",)
    assert ("release",) not in io.calls and ("clear",) not in io.calls
    assert policy.held["depth"] == 0


def test_writer_proceeds_without_lock_and_without_touching_busy_marker():
    io = IO(acquired=False, fail={"read", "write"})
    policy = api().TrackerLock(io)
    with policy.locked():
        io.call("body")
    assert io.calls == [("mkdir",), ("open",), ("acquire", 30.0), ("body",), ("close",)]


@pytest.mark.parametrize("marker,fail", [(None, ()), ("broken", ()),
    ("broken", ("write",)), ("900", ("read",))])
def test_missing_bad_or_unreadable_marker_stamps_current_time_then_skips(marker, fail):
    io = IO(acquired=False, marker=marker, fail=fail)
    policy = api().TrackerLock(io)
    with pytest.raises(api().LockBusy):
        with policy.locked(skip_if_busy=True):
            pytest.fail("fresh refusal must skip")
    assert ("write", "1000.0") in io.calls
    assert io.marker == (marker if "write" in fail else "1000.0")
    assert io.calls[-1] == ("close",) and policy.held["depth"] == 0


def test_failed_clock_in_busy_read_and_stamp_is_best_effort_then_skip():
    io = IO(acquired=False, fail={"clock"})
    with pytest.raises(api().LockBusy):
        with api().TrackerLock(io).locked(skip_if_busy=True):
            pytest.fail("clock failure must not fabricate old refusal")
    assert io.calls.count(("clock", 1000.0)) == 2
    assert not any(c[0] in {"read", "write", "warn"} for c in io.calls)


def test_failed_marker_clear_does_not_prevent_body_or_release():
    io = IO(fail={"clear"})
    with api().TrackerLock(io).locked():
        io.call("body")
    assert io.calls[-3:] == [("body",), ("release",), ("close",)]


@pytest.mark.parametrize("acquired", [True, False])
def test_nested_resolver_bypasses_second_acquire_even_inside_unlocked_writer(acquired):
    io = IO(acquired=acquired)
    policy = api().TrackerLock(io)
    with policy.locked():
        before = list(io.calls)
        with pytest.raises(ValueError, match="nested body"):
            with policy.locked(wait=99, skip_if_busy=True):
                assert policy.held["depth"] == 2
                raise ValueError("nested body")
        assert io.calls == before and policy.held["depth"] == 1
    assert policy.held["depth"] == 0 and io.calls[-1] == ("close",)
    assert len([c for c in io.calls if c[0] == "acquire"]) == 1


@pytest.mark.parametrize("failure,last", [("mkdir", "mkdir"), ("open", "open"),
    ("acquire", "close"), ("release", "close"), ("close", "close")])
def test_original_failure_boundaries_restore_depth_and_close_only_opened_handle(failure, last):
    io = IO(fail={failure})
    policy = api().TrackerLock(io)
    entered = []
    with pytest.raises(OSError, match=failure):
        with policy.locked():
            entered.append(True)
    assert io.calls[-1][0] == last and policy.held["depth"] == 0
    assert bool(entered) is (failure in {"release", "close"})
    if failure in {"mkdir", "open"}:
        assert ("close",) not in io.calls


def test_body_failure_is_not_swallowed_and_release_close_still_run():
    io = IO()
    policy = api().TrackerLock(io)
    with pytest.raises(ValueError, match="body failed"):
        with policy.locked():
            raise ValueError("body failed")
    assert io.calls[-2:] == [("release",), ("close",)]
    assert policy.held["depth"] == 0


def test_warning_failure_still_closes_and_does_not_enter_body():
    io = IO(acquired=False, marker="880", fail={"warn"})
    policy = api().TrackerLock(io)
    with pytest.raises(OSError, match="warn"):
        with policy.locked(skip_if_busy=True):
            pytest.fail("source diagnostic failure propagates")
    assert io.calls[-1] == ("close",) and policy.held["depth"] == 0


def test_continuous_busy_marker_survives_passes_until_success_clears_it():
    io = IO(acquired=False, marker=None)
    policy = api().TrackerLock(io)
    for now in (1000.0, 1119.999):
        io.now = now
        with pytest.raises(api().LockBusy):
            with policy.locked(skip_if_busy=True):
                pytest.fail("not yet stalled")
    io.now = 1120.0
    with policy.locked(skip_if_busy=True):
        io.call("stalled_body")
    assert io.marker == "1000.0"
    io.acquired = True
    with policy.locked():
        pass
    assert io.marker is None
    io.acquired = False
    with pytest.raises(api().LockBusy):
        with policy.locked(skip_if_busy=True):
            pytest.fail("new refusal starts a new interval")
    assert io.marker == "1120.0"


class RecordIO(IO):
    def __init__(self):
        super().__init__()
        self.rows = {}

    def read_symbol(self, symbol, tfs):
        self.call("matrix", self.now)
        return {tf: SimpleNamespace(net=0.0) for tf in tfs}

    def quote_payload(self):
        self.call("quotes", self.now)
        return {"OANDA:XAUUSD": {"lp": 100.0, "ts": self.now}}

    def load(self):
        self.call("load", self.now)
        return deepcopy(self.rows)

    def save(self, rows):
        self.call("save", self.now)
        self.rows = deepcopy(rows)


@pytest.mark.parametrize("new_exposure", [False, True])
def test_actual_record_uses_prelock_evidence_but_postacquire_state_and_clock(new_exposure):
    io = RecordIO()
    lock = api().TrackerLock(io)
    io.locked = lock.locked
    def acquired():
        io.now = 1002.0  # Supplied fixture elapsed time, NOT configured30s timeout.
        if new_exposure:
            io.rows["other"] = {"symbol": "OANDA:XAUUSD", "direction": "לונג", "state": "OPEN"}
    io.after_acquire = acquired
    plan = Plan("OANDA:XAUUSD", 100.0, "reversal", "לונג", entry=100.0,
                stop=90.0, targets=[("TP1", 120.0)])
    assert TrackerAdmission(io).record(plan) is not new_exposure
    assert io.calls[:3] == [("matrix", 1000.0), ("matrix", 1000.0), ("quotes", 1000.0)]
    assert ("load", 1002.0) in io.calls
    assert io.calls[-2:] == [("release",), ("close",)]
    if new_exposure:
        assert list(io.rows) == ["other"] and not any(c[0] == "save" for c in io.calls)
    else:
        row = next(iter(io.rows.values()))
        assert row["ts"] == row["filled_ts"] == 1002.0 and row["state"] == "OPEN"
        assert row["revalidation_verified"] is False  # Advisory OPEN, not broker fill.
