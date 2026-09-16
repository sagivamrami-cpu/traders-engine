"""Outcome/shelf source helpers over explicit, in-memory artifact ports."""
from contextlib import contextmanager
import importlib
import importlib.util
import io
import json

import pytest


def api():
    name = "trading_system.tree_replay._vendor.lifecycle_outcome_shelf"
    assert importlib.util.find_spec(name) is not None, "lifecycle outcome/shelf module missing"
    return importlib.import_module(name)


class Raw:
    """Only raw outcome/shelf/atomic ports; no host I/O, feeds, or delivery."""

    def __init__(self, state=None):
        self.calls = []
        self.epoch = 120.0
        self.outcomes = ""
        self.shelf = None
        self.state = {} if state is None else state
        self.atomic_failure = None
        self.unlink_failure = None
        self.temporary = None

    def now_epoch(self):
        self.calls.append(("clock",))
        return self.epoch

    def outcomes_mkdir(self, path, *, parents, exist_ok):
        assert (path, parents, exist_ok) == ("chart-desk/out", True, True)
        self.calls.append(("outcomes_mkdir", path))

    @contextmanager
    def open_outcomes(self, mode, *, encoding):
        assert (mode, encoding) == ("a", "utf-8")
        self.calls.append(("outcomes_open", mode))
        owner = self

        class Writer:
            def write(self, value):
                owner.outcomes += value

        yield Writer()

    def load(self):
        self.calls.append(("load",))
        return self.state

    def shelf_exists(self):
        self.calls.append(("shelf_exists",))
        return self.shelf is not None

    def shelf_text(self, *, encoding):
        assert encoding == "utf-8"
        self.calls.append(("shelf_text", encoding))
        return self.shelf

    def atomic_mkdir(self, path, *, parents, exist_ok):
        assert (path, parents, exist_ok) == ("chart-desk/out", True, True)
        self.calls.append(("atomic_mkdir", path))

    def atomic_mkstemp(self, path, *, suffix):
        assert (path, suffix) == ("chart-desk/out", ".tmp")
        self.calls.append(("atomic_mkstemp", path))
        return 7, "temporary.json"

    @contextmanager
    def atomic_fdopen(self, fd, mode, *, encoding):
        assert (fd, mode, encoding) == (7, "w", "utf-8")
        self.calls.append(("atomic_fdopen", fd))
        self.temporary = io.StringIO()
        yield self.temporary

    def atomic_fsync(self, handle):
        assert handle is self.temporary
        self.calls.append(("atomic_fsync",))
        if self.atomic_failure is not None:
            raise self.atomic_failure

    def atomic_replace(self, temporary, path):
        assert (temporary, path) == ("temporary.json", "chart-desk/out/shelved_trades.json")
        self.calls.append(("atomic_replace", temporary))
        self.shelf = self.temporary.getvalue()

    def atomic_unlink(self, temporary):
        assert temporary == "temporary.json"
        self.calls.append(("atomic_unlink", temporary))
        if self.unlink_failure is not None:
            raise self.unlink_failure


def trade(**changes):
    row = {
        "symbol": "OANDA:XAUUSD", "direction": "long", "entry": 110.126,
        "stop": 100.0, "targets": [["TP1", 120.0]], "style": "swing",
        "variant": "engine", "to_group": 1, "ts": 15.0,
    }
    row.update(changes)
    return row


def test_outcome_creates_parent_before_clock_then_appends_source_payload():
    raw = Raw()
    event = {"ts": 7.0, "result": "expired", "symbol": "OANDA:XAUUSD"}

    assert api().LifecycleOutcomeShelf(raw)._outcome(event, event_ts=0) is None

    assert raw.calls == [
        ("outcomes_mkdir", "chart-desk/out"), ("clock",), ("outcomes_open", "a"),
    ]
    assert json.loads(raw.outcomes) == {
        "ts": 7.0, "result": "expired", "symbol": "OANDA:XAUUSD", "event_ts": 120.0,
    }


def test_outcome_uses_nonzero_event_timestamp_but_zero_falls_back_to_operation_time():
    raw = Raw()
    helper = api().LifecycleOutcomeShelf(raw)

    helper._outcome({"result": "first"}, event_ts=17.5)
    raw.epoch = 130.0
    helper._outcome({"result": "second"}, event_ts=0)

    assert [json.loads(line) for line in raw.outcomes.splitlines()] == [
        {"ts": 120.0, "result": "first", "event_ts": 17.5},
        {"ts": 130.0, "result": "second", "event_ts": 130.0},
    ]


@pytest.mark.parametrize(("row", "want"), [
    ({"style": "scalp", "variant": "engine"}, 6.0),
    ({"style": "swing", "variant": "engine"}, 24.0),
    ({"style": "unknown", "variant": "engine"}, 24.0),
    ({"style": "swing", "variant": "tree:house"}, 8.0),
])
def test_expiry_preserves_source_tree_variant_priority(row, want):
    assert api().LifecycleOutcomeShelf(Raw())._expire_h(row) == want


def test_shelf_preserves_original_lineage_before_stamping_and_atomically_replaces_image():
    raw = Raw()
    raw.shelf = json.dumps({"old": {"entry": 99.0}})
    helper = api().LifecycleOutcomeShelf(raw)

    assert helper._shelve(trade(ts=15.0, revived_from_ts=4.0)) is None

    assert raw.calls == [
        ("shelf_exists",), ("shelf_text", "utf-8"), ("clock",),
        ("atomic_mkdir", "chart-desk/out"), ("atomic_mkstemp", "chart-desk/out"),
        ("atomic_fdopen", 7), ("atomic_fsync",), ("atomic_replace", "temporary.json"),
    ]
    assert json.loads(raw.shelf) == {
        "old": {"entry": 99.0},
        "OANDA:XAUUSD|long|110.13": {
            "symbol": "OANDA:XAUUSD", "direction": "long", "entry": 110.126,
            "stop": 100.0, "targets": [["TP1", 120.0]], "style": "swing",
            "variant": "engine", "to_group": True, "original_ts": 4.0,
            "shelved_ts": 120.0,
        },
    }


def test_shelf_malformed_existing_image_falls_back_to_empty_image():
    raw = Raw()
    raw.shelf = "{torn"

    api().LifecycleOutcomeShelf(raw)._shelve(trade())

    assert json.loads(raw.shelf) == {
        "OANDA:XAUUSD|long|110.13": {
            "symbol": "OANDA:XAUUSD", "direction": "long", "entry": 110.126,
            "stop": 100.0, "targets": [["TP1", 120.0]], "style": "swing",
            "variant": "engine", "to_group": True, "original_ts": 15.0,
            "shelved_ts": 120.0,
        },
    }


def test_atomic_json_cleans_temporary_file_but_propagates_original_write_failure():
    raw = Raw()
    raw.atomic_failure = OSError("fsync unavailable")
    raw.unlink_failure = OSError("cleanup unavailable")

    with pytest.raises(OSError, match="fsync unavailable"):
        api().LifecycleOutcomeShelf(raw)._atomic_json(api().LifecycleOutcomeShelf.SHELF, {"shelf": {}})

    assert raw.calls == [
        ("atomic_mkdir", "chart-desk/out"), ("atomic_mkstemp", "chart-desk/out"),
        ("atomic_fdopen", 7), ("atomic_fsync",), ("atomic_unlink", "temporary.json"),
    ]
    assert raw.shelf is None


def test_has_open_delegates_to_actual_accepted_tracker_admission_behavior():
    raw = Raw({
        "pending": {"state": "PENDING", "symbol": "OANDA:XAUUSD", "direction": "long"},
        "open": {"state": "OPEN", "symbol": "OANDA:XAUUSD", "direction": "short"},
    })
    helper = api().LifecycleOutcomeShelf(raw)

    assert helper.has_open("OANDA:XAUUSD", "long") is False
    assert helper.has_open("OANDA:XAUUSD", "short") is True
    assert helper.has_open("OANDA:XAUUSD") is True
    assert raw.calls == [("load",), ("load",), ("load",)]


def test_helpers_return_only_none_or_exposure_boolean_and_use_only_raw_artifact_ports():
    raw = Raw()
    helper = api().LifecycleOutcomeShelf(raw)

    assert helper._outcome({"result": "tp1"}) is None
    assert helper._shelve(trade()) is None
    assert helper.has_open("OANDA:XAUUSD", "long") is False
    assert all(call[0] in {
        "outcomes_mkdir", "clock", "outcomes_open", "shelf_exists", "atomic_mkdir",
        "atomic_mkstemp", "atomic_fdopen", "atomic_fsync", "atomic_replace", "load",
    } for call in raw.calls)
