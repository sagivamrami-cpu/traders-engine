"""Original tracker consumers over shared-time, explicitly published evidence."""
from collections.abc import Mapping
import base64
from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
import re

from .admission_frames import AdmissionFrameRequest, AdmissionFrameSource
from .admission_io import ArtifactSeed, CausalQuoteReader, CausalWatchLog
from .bars import _number, _utc
from .bars import ClosedBar
from .calendar import SessionInterval, SessionSchedule
from .clock import ReplayClock
from .corrections import CorrectionEvidence
from .frames import FrameSpec, LabeledDailyPeriod
from .periods import DailyPeriod
from .state import _identity
from .tracker_storage import TrackerStateSeed, CausalTrackerStorage, _MemoryBackend
from ._vendor.tracker_admission import TrackerAdmission
from ._vendor.tracker_lock import TrackerLock


class OperationUnavailable(ValueError):
    """The supplied operation evidence does not establish this attempted action."""


@dataclass(frozen=True, kw_only=True)
class BusyMarkerSeed(TrackerStateSeed):
    """Distinct artifact identity, sharing the validated causal text seed schema."""


@dataclass(frozen=True, kw_only=True)
class Publication:
    publication_id: str
    source: str
    available_at: datetime
    sequence: int
    channel: str
    payload: object

    def __post_init__(self):
        _identity(self.publication_id, "publication_id")
        _identity(self.source, "source")
        object.__setattr__(self, "available_at", _utc(self.available_at, "available_at"))
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("publication sequence must be a native nonnegative integer")
        if type(self.channel) is not str or self.channel not in ("tracker", "quotes", "watch_log", "busy", "frames"):
            raise ValueError("unsupported publication channel")
        if self.channel == "frames":
            if type(self.payload) is not tuple or any(type(r) is not AdmissionFrameRequest for r in self.payload):
                raise ValueError("frames publication requires exact request tuple")
            for request in self.payload:
                request.__post_init__()
        else:
            cls = {"tracker": TrackerStateSeed, "busy": BusyMarkerSeed}.get(self.channel, ArtifactSeed)
            if type(self.payload) is not cls:
                raise ValueError("publication payload type does not match channel")
            self.payload.__post_init__()
            if cls is ArtifactSeed and self.payload.kind != self.channel:
                raise ValueError("artifact kind does not match publication channel")
            if self.payload.available_at != self.available_at:
                raise ValueError("artifact publication time must equal seed availability")


@dataclass(frozen=True, kw_only=True)
class LockStep:
    step_id: str
    source: str
    operation: str
    started_at: datetime
    completed_at: datetime
    timeout: float | None
    acquired: bool | None
    error: str | None

    def __post_init__(self):
        _identity(self.step_id, "step_id")
        _identity(self.source, "source")
        for field in ("started_at", "completed_at"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if self.completed_at < self.started_at:
            raise ValueError("lock completion precedes start")
        if type(self.operation) is not str or self.operation not in ("prepare", "open", "acquire", "release", "close", "warn"):
            raise ValueError("unsupported lock operation")
        if self.error is not None:
            if type(self.error) is not str:
                raise ValueError("lock error must be exact text or None")
            try:
                self.error.encode("utf-8")
            except UnicodeError as exc:
                raise ValueError("lock error must be UTF-8 encodable") from exc
        if self.operation == "acquire":
            _number(self.timeout, "timeout")
            if (self.error is None and type(self.acquired) is not bool) or (self.error is not None and self.acquired is not None):
                raise ValueError("acquire requires bool success or None with supplied error")
        elif self.timeout is not None or self.acquired is not None:
            raise ValueError("non-acquire step cannot supply timeout or acquired")


class _Handle:
    def __init__(self, owner):
        self.owner, self.closed, self.acquired = owner, False, False

    def close(self):
        self.owner._step("close", handle=self)


class CausalAdmissionContext:
    def __init__(self, *, instrument: str, decision_time: datetime,
                 tracker_seed: TrackerStateSeed, quote_seed: ArtifactSeed,
                 log_seed: ArtifactSeed, busy_seed: BusyMarkerSeed, newline: str,
                 frame_requests: tuple[AdmissionFrameRequest, ...],
                 publications: tuple[Publication, ...], lock_steps: tuple[LockStep, ...],
                 clock: ReplayClock | None = None):
        at = _utc(decision_time, "decision_time")
        if clock is None:
            clock = ReplayClock(at)
        from .clock import _validate_binding
        _validate_binding(clock, at)
        self._clock = clock
        self._pass_anchor = self._clock.now
        self.instrument, self._newline = instrument, newline
        self._validate_frames(frame_requests)
        if type(busy_seed) is not BusyMarkerSeed:
            raise ValueError("busy seed must be exact BusyMarkerSeed")
        busy_seed.__post_init__()
        if type(publications) is not tuple or any(type(p) is not Publication for p in publications):
            raise ValueError("publications must be an exact tuple of Publication")
        previous = None
        ids = set()
        for p in publications:
            p.__post_init__()
            key = (p.available_at, p.sequence)
            if p.available_at < self.decision_time or (previous is not None and key <= previous) or p.publication_id in ids:
                raise ValueError("publication schedule must have unique IDs and increasing time/sequence")
            if p.channel == "frames":
                self._validate_frames(p.payload)
            previous = key
            ids.add(p.publication_id)
        if type(lock_steps) is not tuple or any(type(s) is not LockStep for s in lock_steps):
            raise ValueError("lock steps must be exact tuple of LockStep")
        end, ids = self.decision_time, set()
        for s in lock_steps:
            s.__post_init__()
            if s.started_at < end or s.step_id in ids:
                raise ValueError("lock steps must be nonoverlapping with unique IDs")
            end = s.completed_at
            ids.add(s.step_id)
        self._publications, self._steps = publications, lock_steps
        self._replay_baseline = {
            "decision_time": at.isoformat(), "instrument": instrument, "newline": newline,
            "tracker": _pack(tracker_seed), "quotes": _pack(quote_seed),
            "watch_log": _pack(log_seed), "busy": _pack(busy_seed),
            "frame_requests": _pack(frame_requests), "publications": _pack(publications),
            "lock_steps": _pack(lock_steps),
        }
        self._publication_index = self._step_index = 0
        self._events, self._artifacts, self._frame_reads = [], [], []
        self._handle = None
        self._frame_requests = frame_requests
        for channel, payload in (("tracker", tracker_seed), ("quotes", quote_seed),
                                 ("watch_log", log_seed), ("busy", busy_seed)):
            self._install(channel, payload)
        self._lock = TrackerLock(self)
        self.tracker = TrackerAdmission(self)
        self._advance(self.decision_time)

    @property
    def decision_time(self):
        return self._clock.now

    @property
    def pass_anchor(self):
        return self._pass_anchor

    def _validate_frames(self, requests):
        # Constructor validation is structural; no future prices are calculated.
        AdmissionFrameSource(instrument=self.instrument, decision_time=self.decision_time, requests=requests)

    def _install(self, channel, payload):
        at = self.decision_time
        if channel == "frames":
            self._frame_requests = payload
            return
        if channel == "tracker":
            obj = CausalTrackerStorage(seed=payload, decision_time=at, clock=self._clock)
            self._storage = obj
        elif channel == "quotes":
            obj = CausalQuoteReader(seed=payload, decision_time=at, clock=self._clock)
            self._quotes = obj
        elif channel == "watch_log":
            obj = CausalWatchLog(seed=payload, decision_time=at, newline=self._newline, clock=self._clock)
            self._log = obj
        else:
            obj = _MemoryBackend(payload, at, self._clock)
            self._busy = obj
        self._artifacts.append(dict(channel=channel, seed_id=payload.seed_id, source=payload.source, instance=obj))

    def _call(self, operation, action, **details):
        event = dict(sequence=len(self._events), operation=operation,
                     started_at=self.decision_time.isoformat(), status="BLOCKED",
                     exception_type=None, blocker=None, **details)
        self._events.append(event)
        try:
            result = action()
        except Exception as exc:
            event.update(exception_type=type(exc).__name__, blocker=str(exc))
            raise
        else:
            event["status"] = "AVAILABLE"
            return result
        finally:
            event["completed_at"] = self.decision_time.isoformat()

    def _advance(self, at):
        at = _utc(at, "decision_time")
        if at < self.decision_time:
            raise ValueError("context cannot move backward")
        while self._publication_index < len(self._publications):
            p = self._publications[self._publication_index]
            if p.available_at > at:
                break
            self._clock.advance_to(p.available_at)
            self._call("publication", lambda: self._install(p.channel, p.payload),
                       publication_id=p.publication_id, source=p.source, channel=p.channel,
                       publication_sequence=p.sequence)
            self._publication_index += 1
        self._clock.advance_to(at)

    def advance_to(self, decision_time):
        return self._call("advance", lambda: self._advance(decision_time))

    def replay_publications_through(self, at: datetime) -> tuple[Publication, ...]:
        """Return the immutable scheduled prefix without moving this provider clock."""
        through = _utc(at, "publication schedule through")
        return tuple(publication for publication in self._publications if publication.available_at <= through)

    def now_epoch(self):
        return self._call("clock", lambda: self.decision_time.timestamp())

    def load(self):
        return self._call("load", self._storage.load)

    def save(self, rows, *, allow_shrink=False):
        return self._call("save", lambda: self._storage.save(rows, allow_shrink=allow_shrink))

    def quote_payload(self):
        return self._call("quote_payload", self._quotes.quote_payload)

    def event_log_reader(self):
        return self._call("event_log_reader", self._log.event_log_reader)

    def log(self, row):
        return self._call("log", lambda: self._log.log(row))

    def _frame_call(self, operation, action):
        source = AdmissionFrameSource(instrument=self.instrument, decision_time=self.decision_time,
                                      requests=self._frame_requests)
        self._frame_reads.append((self.decision_time, source))
        return self._call(operation, lambda: action(source))

    def read_symbol(self, symbol, tfs=("4h", "1h", "15m", "5m")):
        return self._frame_call("read_symbol", lambda s: s.read_symbol(symbol, tfs))

    def fetch_corrected(self, symbol, timeframe, lookback_days):
        return self._frame_call("fetch_corrected", lambda s: s.fetch_corrected(symbol, timeframe, lookback_days))

    def locked(self, *, wait=None, skip_if_busy=False):
        return self._lock.locked(wait=wait, skip_if_busy=skip_if_busy)

    def _step(self, operation, *, handle=None, timeout=None, message=None):
        def consume():
            if self._step_index == len(self._steps):
                raise OperationUnavailable("LOCK_STEP_MISSING")
            step = self._steps[self._step_index]
            if step.operation != operation or step.started_at != self.decision_time:
                raise OperationUnavailable("LOCK_STEP_OPERATION_OR_TIME_MISMATCH")
            if operation == "acquire" and (type(timeout) not in (int, float) or step.timeout != timeout):
                raise OperationUnavailable("LOCK_STEP_TIMEOUT_MISMATCH")
            if operation in ("acquire", "release", "close"):
                if handle is not self._handle or handle is None or handle.closed:
                    raise OperationUnavailable("LOCK_HANDLE_MISMATCH")
                if operation == "release" and not handle.acquired:
                    raise OperationUnavailable("LOCK_NOT_ACQUIRED")
            elif operation in ("prepare", "open") and self._handle is not None:
                raise OperationUnavailable("LOCK_HANDLE_ALREADY_OPEN")
            self._events[-1].update(step_id=step.step_id, evidence_source=step.source)
            self._step_index += 1
            self._advance(step.completed_at)
            if operation == "close":
                # A matched close attempt ends this local handle, even on supplied
                # OSError. This says nothing about a historical OS descriptor.
                handle.closed = True
                self._handle = None
            if step.error is not None:
                raise OSError(step.error)
            if operation == "open":
                self._handle = _Handle(self)
                return self._handle
            if operation == "acquire":
                handle.acquired = step.acquired
                return step.acquired
            if operation == "release":
                handle.acquired = False
        return self._call("lock."+operation, consume, timeout=timeout, message=message)

    def ensure_lock_directory(self):
        return self._step("prepare")

    def open_lock(self):
        return self._step("open")

    def try_acquire(self, handle, *, timeout):
        return self._step("acquire", handle=handle, timeout=timeout)

    def release(self, handle):
        return self._step("release", handle=handle)

    def warn(self, text):
        return self._step("warn", message=text)

    def read_busy(self):
        return self._call("busy.read", self._busy.read_text)

    def write_busy(self, text):
        return self._call("busy.write", lambda: self._busy.atomic_write(text))

    def clear_busy(self):
        def clear():
            self._busy.status, self._busy.text = "ABSENT", None
        return self._call("busy.clear", lambda: self._busy.call("clear", clear))

    def replay_snapshot(self):
        """Return a detached, checksummed resume image of still-legal evidence only."""
        if any(step.started_at < self.decision_time for step in self._steps[self._step_index:]):
            raise ValueError("cannot checkpoint an unconsumed lock step from the past")
        tracker = self._storage.snapshot()
        quotes = self._quotes.snapshot()
        watch_log = self._log.snapshot()
        busy = replace(self._busy.seed, observed_at=self.decision_time,
                       available_at=self.decision_time, status=self._busy.status,
                       text=self._busy.text)
        state = {
            "decision_time": self.decision_time.isoformat(), "instrument": self.instrument,
            "newline": self._newline, "tracker": _pack(tracker), "quotes": _pack(quotes),
            "watch_log": _pack(watch_log), "busy": _pack(busy),
            "frame_requests": _pack(self._frame_requests),
            "publications": _pack(self._publications[self._publication_index:]),
            "lock_steps": _pack(self._steps[self._step_index:]),
        }
        return deepcopy({"schema_version": "causal-admission-replay-snapshot-v1",
                         "state": state, "checksum": _snapshot_digest(state)})

    def _replay_provider_baseline(self):
        """Detached initial provider evidence for an externally retained checkpoint trust anchor."""
        return deepcopy(self._replay_baseline)

    @classmethod
    def from_replay_snapshot(cls, snapshot: dict, *, clock: ReplayClock):
        if type(snapshot) is not dict or set(snapshot) != {"schema_version", "state", "checksum"}:
            raise ValueError("replay snapshot must have the canonical schema")
        if snapshot["schema_version"] != "causal-admission-replay-snapshot-v1":
            raise ValueError("unsupported replay snapshot schema")
        state = snapshot["state"]
        if type(state) is not dict or type(snapshot["checksum"]) is not str:
            raise ValueError("replay snapshot has invalid state or checksum")
        if _snapshot_digest(state) != snapshot["checksum"]:
            raise ValueError("replay snapshot checksum does not match state")
        required = {"decision_time", "instrument", "newline", "tracker", "quotes", "watch_log",
                    "busy", "frame_requests", "publications", "lock_steps"}
        if set(state) != required:
            raise ValueError("replay snapshot state is not canonical")
        at = _parse_time(state["decision_time"], "snapshot decision_time")
        from .clock import _validate_binding
        _validate_binding(clock, at)
        try:
            values = {key: _unpack(state[key]) for key in required - {"decision_time", "instrument", "newline"}}
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError(f"replay snapshot contains invalid provider evidence: {exc}") from exc
        if (type(values["tracker"]) is not TrackerStateSeed or type(values["quotes"]) is not ArtifactSeed
                or type(values["watch_log"]) is not ArtifactSeed or type(values["busy"]) is not BusyMarkerSeed
                or type(values["frame_requests"]) is not tuple or type(values["publications"]) is not tuple
                or type(values["lock_steps"]) is not tuple):
            raise ValueError("replay snapshot contains mismatched provider evidence")
        if any(publication.available_at <= at for publication in values["publications"]):
            raise ValueError("replay snapshot resurrects a consumed publication")
        if any(step.started_at < at for step in values["lock_steps"]):
            raise ValueError("replay snapshot resurrects a consumed lock step")
        return cls(instrument=state["instrument"], decision_time=at, tracker_seed=values["tracker"],
                   quote_seed=values["quotes"], log_seed=values["watch_log"], busy_seed=values["busy"],
                   newline=state["newline"], frame_requests=values["frame_requests"],
                   publications=values["publications"], lock_steps=values["lock_steps"], clock=clock)

    def report(self):
        artifacts = []
        for epoch in self._artifacts:
            obj = epoch["instance"]
            item = {k: epoch[k] for k in ("channel", "seed_id", "source")}
            item["trace"] = obj.trace
            if epoch["channel"] == "tracker":
                item.update(creation_effects=obj.creation_effects, quarantines=obj.quarantine_artifacts)
            artifacts.append(item)
        return deepcopy(dict(pass_anchor=self.pass_anchor.isoformat(),
            decision_time=self.decision_time.isoformat(), events=self._events, artifacts=artifacts,
            frames=[dict(decision_time=at.isoformat(), fetch_trace=s.fetch_trace,
                         matrix_trace=s.matrix_trace) for at, s in self._frame_reads],
            publications_consumed=self._publication_index, lock_steps_consumed=self._step_index,
            ready_for_replay=False, ready_for_training=False))


_SNAPSHOT_TYPES = {
    cls.__name__: cls for cls in (
        TrackerStateSeed, ArtifactSeed, BusyMarkerSeed, AdmissionFrameRequest,
        FrameSpec, ClosedBar, SessionSchedule, SessionInterval, LabeledDailyPeriod,
        DailyPeriod, CorrectionEvidence, Publication, LockStep,
    )
}


def _pack(value):
    if isinstance(value, datetime):
        return {"__type__": "datetime", "value": value.isoformat()}
    if type(value) is tuple:
        return {"__type__": "tuple", "items": [_pack(item) for item in value]}
    if type(value) is bytes:
        return {"__type__": "bytes", "base64": base64.b64encode(value).decode("ascii")}
    if is_dataclass(value) and type(value).__name__ in _SNAPSHOT_TYPES:
        return {"__type__": type(value).__name__, "fields": {
            field.name: _pack(getattr(value, field.name)) for field in fields(value)}}
    if type(value) is list:
        return [_pack(item) for item in value]
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("snapshot mappings require string keys")
        return {key: _pack(item) for key, item in value.items()}
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise ValueError("snapshot contains unsupported value")


def _unpack(value):
    if type(value) is list:
        return [_unpack(item) for item in value]
    if type(value) is not dict:
        return value
    marker = value.get("__type__")
    if marker is None:
        return {key: _unpack(item) for key, item in value.items()}
    if marker == "datetime" and set(value) == {"__type__", "value"}:
        return _parse_time(value["value"], "snapshot datetime")
    if marker == "tuple" and set(value) == {"__type__", "items"} and type(value["items"]) is list:
        return tuple(_unpack(item) for item in value["items"])
    if marker == "bytes" and set(value) == {"__type__", "base64"} and type(value["base64"]) is str:
        try:
            return base64.b64decode(value["base64"], validate=True)
        except ValueError as exc:
            raise ValueError("snapshot contains invalid bytes") from exc
    cls = _SNAPSHOT_TYPES.get(marker)
    if cls is None or set(value) != {"__type__", "fields"} or type(value["fields"]) is not dict:
        raise ValueError("snapshot contains unsupported typed value")
    expected = {field.name for field in fields(cls)}
    if set(value["fields"]) != expected:
        raise ValueError("snapshot typed fields are not canonical")
    return cls(**{key: _unpack(item) for key, item in value["fields"].items()})


def _parse_time(value, field):
    if type(value) is not str:
        raise ValueError(f"{field} must be an ISO timestamp")
    fraction = re.match(r"^\d{4}(?:-\d{2}-\d{2}|\d{4})[Tt ]\d{2}:?\d{2}:?\d{2}[.,](\d+)", value)
    if fraction is not None and len(fraction.group(1)) > 6:
        raise ValueError(f"{field} must be microsecond-exact")
    try:
        return _utc(datetime.fromisoformat(value.replace("Z", "+00:00")), field)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc


def _snapshot_digest(state):
    from .causal_replay_contracts import canonical_digest
    return canonical_digest(state)
