"""Integration seam: real live caller plus real live resolver over one offline source."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import importlib

from trading_system.tree_replay._vendor.tracker_lock import TrackerLock


CALLER = "trading_system.tree_replay.lifecycle_caller"
RESOLVER = "trading_system.tree_replay._vendor.lifecycle_live_resolver"
SYMBOL = "OANDA:XAUUSD"
NOW = 120.0


def caller_api():
    return importlib.import_module(CALLER)


def resolver_api():
    return importlib.import_module(RESOLVER)


class _TrackerHandle:
    def __init__(self, source):
        self.source = source

    def close(self):
        self.source.events.append("close")


class OfflineSource:
    """One explicit in-memory source for the real caller, lock, gate, and resolver."""

    def __init__(self, *, lock_acquired=True):
        self.state = {
            "trade": {
                "symbol": SYMBOL,
                "direction": "LONG",
                "entry": 100.0,
                "stop": 99.0,
                "targets": [("TP1", 101.0)],
                "ts": 0.0,
                "state": "PENDING",
                "to_group": False,
            }
        }
        self.events = []
        self.saved = None
        self.journal = ""
        self.lock_acquired = lock_acquired
        self.tracker_locked = False
        self.journal_locked = False
        self.shared_lock = TrackerLock(self)
        self.append_handle = object()
        self.quote_reads = 0

    def load(self):
        self.events.append("load")
        return self.state

    def save(self, state):
        self.events.append("save")
        self.saved = deepcopy(state)

    def quote_payload(self):
        self.quote_reads += 1
        self.events.append(f"quote:{self.quote_reads}")
        return {SYMBOL: {"lp": 100.0, "ts": NOW}}

    def now_epoch(self):
        return NOW

    def fetch_corrected(self, *_args):
        raise AssertionError("fresh quote must not fetch a corrected bar")

    def ensure_lock_directory(self):
        self.events.append("lock")

    def open_lock(self):
        return _TrackerHandle(self)

    def locked(self, *, wait=None, skip_if_busy=False):
        return self.shared_lock.locked(wait=wait, skip_if_busy=skip_if_busy)

    def try_acquire(self, handle, *, timeout):
        if handle is self.append_handle:
            assert timeout is None
            self.journal_locked = True
            return True
        assert timeout == 3.0
        self.tracker_locked = self.lock_acquired
        return self.lock_acquired

    def release(self, handle):
        if handle is self.append_handle:
            assert self.journal_locked
            self.journal_locked = False
            return
        assert self.tracker_locked
        self.events.append("release")
        self.tracker_locked = False

    def clear_busy(self):
        pass

    def read_busy(self):
        return str(NOW)

    def write_busy(self, text):
        assert text == str(NOW)

    def warn(self, text):
        raise AssertionError(f"fresh LockBusy must not warn: {text}")

    def journal_exists(self):
        return bool(self.journal)

    def journal_text(self, *, encoding):
        assert encoding == "utf-8"
        return self.journal

    def park_exists(self):
        return False

    def mkdir(self, path, *, parents, exist_ok):
        assert (path, parents, exist_ok) == ("chart-desk/out", True, True)

    @contextmanager
    def open_append_lock(self, path, mode):
        assert (path, mode) == ("chart-desk/out/outbox.append.lock", "a+")
        yield self.append_handle

    def assert_offline(self):
        self.events.append("gate")

    @contextmanager
    def open_journal(self, mode, *, encoding):
        assert (mode, encoding) == ("a", "utf-8") and self.journal_locked
        source = self

        class Writer:
            def write(self, text):
                source.journal += text

        yield Writer()


def install_resolver_children(monkeypatch, source, *, transition):
    """Stub accepted resolver children, retaining the real caller/lock/gate/evidence seam."""
    module = resolver_api()

    class Pending:
        def resolve(self, trade, **_kwargs):
            source.events.append("pending")
            if transition:
                trade["state"] = "OPEN"
                trade["transition"] = "filled"
                return [("integration filled", False)], True
            return [], False

    class Postfill:
        def collect(self, *_args):
            source.events.append("postfill")
            return 100.0, 100.0, None

    class Minimum:
        def resolve(self, *_args, **_kwargs):
            source.events.append("minimum")
            return [], False, None

    class Protection:
        def resolve(self, *_args, **_kwargs):
            source.events.append("protection")
            return [], False

    class Ordinary:
        def resolve(self, *_args, **_kwargs):
            source.events.append("ordinary")
            return [], False

    class ZoneReturn:
        def resolve(self, *_args, **_kwargs):
            source.events.append("zone")
            return [], False

    monkeypatch.setattr(module, "LifecyclePendingResolution", lambda _source: Pending())
    monkeypatch.setattr(module, "LifecycleOpenPostfillEvidence", lambda _source: Postfill())
    monkeypatch.setattr(module, "LifecycleOpenMinimumSuccess", lambda _source: Minimum())
    monkeypatch.setattr(module, "LifecycleOpenProtection", lambda _source: Protection())
    monkeypatch.setattr(module, "LifecycleOpenOrdinaryResolution", lambda _source: Ordinary())
    monkeypatch.setattr(module, "LifecycleOpenZoneReturn", lambda _source: ZoneReturn())


def test_live_caller_uses_real_resolver_without_change_and_never_gates_or_saves(monkeypatch):
    """Catches a caller that persists a resolver pass solely because it ran."""
    source = OfflineSource()
    install_resolver_children(monkeypatch, source, transition=False)
    resolver = resolver_api().LifecycleLiveResolver(source)

    assert caller_api().TrackerLifecycleCaller(source).check_live(resolver.resolve) == []

    assert source.events == ["lock", "load", "quote:1", "quote:2", "pending", "release", "close"]
    assert source.saved is None
    assert source.journal == ""
    assert source.state["trade"]["state"] == "PENDING"


def test_live_caller_gates_and_saves_real_resolver_output_after_its_state_transition(monkeypatch):
    """Catches gate/save before a real resolver's changed state and output are available."""
    source = OfflineSource()
    install_resolver_children(monkeypatch, source, transition=True)
    resolver = resolver_api().LifecycleLiveResolver(source)

    assert caller_api().TrackerLifecycleCaller(source).check_live(resolver.resolve) == [
        ("integration filled", False)
    ]

    assert source.events == [
        "lock", "load", "quote:1", "quote:2", "pending", "postfill", "minimum",
        "protection", "ordinary", "zone", "gate", "save", "release", "close",
    ]
    assert source.saved == source.state
    assert source.saved["trade"]["state"] == "OPEN"
    assert source.saved["trade"]["transition"] == "filled"
    assert '"text": "integration filled"' in source.journal


def test_live_caller_lockbusy_prevents_real_resolver_load_gate_and_save(monkeypatch):
    """Catches a busy live lock that leaks into resolver or persistence effects."""
    source = OfflineSource(lock_acquired=False)
    install_resolver_children(monkeypatch, source, transition=True)
    resolver = resolver_api().LifecycleLiveResolver(source)

    assert caller_api().TrackerLifecycleCaller(source).check_live(resolver.resolve) == []

    assert source.events == ["lock", "close"]
    assert source.quote_reads == 0
    assert source.saved is None
    assert source.journal == ""
    assert source.state["trade"]["state"] == "PENDING"
