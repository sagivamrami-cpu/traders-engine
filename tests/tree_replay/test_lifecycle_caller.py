"""Changed-only lifecycle caller behavior over one raw offline tape."""
from contextlib import contextmanager
from copy import deepcopy
import importlib
import importlib.util

import pytest

from trading_system.tree_replay._vendor.tracker_lock import LockBusy, TrackerLock


def api():
    name = "trading_system.tree_replay.lifecycle_caller"
    assert importlib.util.find_spec(name) is not None, "lifecycle caller missing"
    return importlib.import_module(name)


class RawTape:
    """In-memory ports for the real gate and lock; no ambient I/O exists here."""

    def __init__(self, *, state=None, lock_acquired=True, lock_error=None):
        self.state = {"trade": {
            "symbol": "OANDA:XAUUSD", "direction": "׳׳•׳ ׳’", "entry": 110.0,
            "stop": 99.0, "targets": [("TP1", 115.0)], "ts": 0.0,
            "state": "OPEN",
        }} if state is None else state
        self.saved = None
        self.journal = ""
        self.events = []
        self.lock_acquired = lock_acquired
        self.lock_error = lock_error
        self.tracker_locked = False
        self.tracker_depth = 0
        self.acquire_timeouts = []
        self.journal_locked = False
        self.shared_lock = TrackerLock(self)
        self.append_handle = object()

    def load(self):
        self.events.append("load")
        return self.state

    def save(self, state):
        self.events.append("save")
        self.saved = deepcopy(state)

    def now_epoch(self):
        return 120.0

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
        tape = self

        class Writer:
            def write(self, value):
                tape.journal += value

        yield Writer()

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
        assert isinstance(handle, _TrackerHandle) and timeout in (3.0, 30.0)
        if self.lock_error is not None:
            raise self.lock_error
        self.acquire_timeouts.append(timeout)
        self.tracker_depth += int(self.lock_acquired)
        self.tracker_locked = self.tracker_depth > 0
        return self.lock_acquired

    def release(self, handle):
        if handle is self.append_handle:
            assert self.journal_locked
            self.journal_locked = False
            return
        assert isinstance(handle, _TrackerHandle) and self.tracker_locked
        self.events.append("release")
        self.tracker_depth -= 1
        self.tracker_locked = self.tracker_depth > 0

    def clear_busy(self):
        pass

    def read_busy(self):
        return "120"

    def write_busy(self, text):
        assert text == "120.0"

    def warn(self, text):
        pytest.fail(f"fresh lock refusal must skip, not warn: {text}")


class _TrackerHandle:
    def __init__(self, tape):
        self.tape = tape

    def close(self):
        self.tape.events.append("close")


def test_closed_empty_state_returns_before_resolver_gate_or_save():
    tape = RawTape(state={})

    def resolve(state):
        pytest.fail(f"empty state reached resolver: {state!r}")

    assert api().TrackerLifecycleCaller(tape).check(resolve) == []
    assert tape.events == ["load"]


def test_closed_unchanged_returns_raw_output_without_gate_or_save():
    tape = RawTape()

    def resolve(state):
        tape.events.append("resolve")
        state["trade"]["seen"] = True
        return [("ordinary status", False)], False

    assert api().TrackerLifecycleCaller(tape).check(resolve) == [("ordinary status", False)]
    assert tape.events == ["load", "resolve"]
    assert tape.saved is None and tape.journal == ""


def test_closed_changed_resolves_gates_then_saves_the_mutated_state():
    tape = RawTape()

    def resolve(state):
        tape.events.append("resolve")
        state["trade"]["seen"] = True
        return [("ordinary status", False)], True

    assert api().TrackerLifecycleCaller(tape).check(resolve) == [("ordinary status", False)]
    assert tape.events == ["load", "resolve", "gate", "save"]
    assert tape.saved["trade"]["seen"] is True
    assert '"text": "ordinary status"' in tape.journal


@pytest.mark.parametrize("result", [
    [],
    ([], 1),
    ([("ordinary status", 0)], False),
    ([("ordinary status", False, "extra")], False),
])
def test_malformed_callback_result_fails_before_gate_or_save(result):
    tape = RawTape()

    def resolve(state):
        tape.events.append("resolve")
        return result

    with pytest.raises(TypeError):
        api().TrackerLifecycleCaller(tape).check(resolve)
    assert tape.events == ["load", "resolve"]
    assert tape.saved is None and tape.journal == ""


def test_closed_resolver_error_propagates_without_fake_success_or_effects():
    tape = RawTape()

    def resolve(state):
        tape.events.append("resolve")
        raise ValueError("raw resolver failed")

    with pytest.raises(ValueError, match="raw resolver failed"):
        api().TrackerLifecycleCaller(tape).check(resolve)
    assert tape.events == ["load", "resolve"]
    assert tape.saved is None and tape.journal == ""


def test_live_lock_busy_returns_empty_without_load_resolve_gate_or_save():
    tape = RawTape(lock_acquired=False)

    def resolve(state):
        pytest.fail(f"busy lock reached resolver: {state!r}")

    assert api().TrackerLifecycleCaller(tape).check_live(resolve) == []
    assert tape.events == ["lock", "close"]
    assert tape.saved is None and tape.journal == ""


def test_live_changed_holds_lock_across_load_resolve_gate_save_and_release():
    tape = RawTape()

    def resolve(state):
        tape.events.append("resolve")
        state["trade"]["live"] = True
        return [("ordinary status", False)], True

    assert api().TrackerLifecycleCaller(tape).check_live(resolve) == [("ordinary status", False)]
    assert tape.events == ["lock", "load", "resolve", "gate", "save", "release", "close"]
    assert tape.saved["trade"]["live"] is True
    assert tape.acquire_timeouts == [3.0]


def test_live_reuses_an_existing_source_lock_without_a_second_acquisition():
    tape = RawTape()

    def resolve(state):
        tape.events.append("resolve")
        return [("ordinary status", False)], True

    with tape.locked():
        assert api().TrackerLifecycleCaller(tape).check_live(resolve) == [("ordinary status", False)]
    assert tape.events == ["lock", "load", "resolve", "gate", "save", "release", "close"]
    assert tape.acquire_timeouts == [30.0]
    assert tape.tracker_depth == 0


def test_live_non_lockbusy_lock_error_propagates_without_fake_success():
    tape = RawTape(lock_error=OSError("lock port failed"))

    with pytest.raises(OSError, match="lock port failed"):
        api().TrackerLifecycleCaller(tape).check_live(lambda state: pytest.fail("must not resolve"))
    assert tape.events == ["lock", "close"]
    assert tape.saved is None and tape.journal == ""


def test_live_resolver_lock_busy_returns_empty_before_gate_or_save():
    tape = RawTape()

    def resolve(state):
        tape.events.append("resolve")
        raise LockBusy("resolver observed source lock contention")

    assert api().TrackerLifecycleCaller(tape).check_live(resolve) == []
    assert tape.events == ["lock", "load", "resolve", "release", "close"]
    assert tape.saved is None and tape.journal == ""


def test_locked_live_kernel_has_the_same_changed_only_commit_semantics():
    tape = RawTape()

    def resolve(state):
        tape.events.append("resolve")
        return [("ordinary status", False)], True

    assert api().TrackerLifecycleCaller(tape)._check_live_locked(resolve) == [("ordinary status", False)]
    assert tape.events == ["load", "resolve", "gate", "save"]
