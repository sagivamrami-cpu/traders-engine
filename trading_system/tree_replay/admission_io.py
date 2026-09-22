"""Causal quote artifacts and byte-faithful, append-only watch logging in memory."""
from bisect import bisect_right
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime
from io import RawIOBase
import json
from operator import index

from .bars import _utc
from .clock import ReplayClock, _validate_binding
from .state import _identity
from ._vendor.watch_io import WatchLogger
from ._vendor.watch_sessions import current_session_at


class InputUnavailable(ValueError):
    """No covered, published artifact can establish the source input."""


@dataclass(frozen=True, kw_only=True)
class ArtifactSeed:
    seed_id: str
    source: str
    kind: str
    status: str
    observed_at: datetime
    available_at: datetime
    covered_through: datetime
    content: str | bytes | None

    def __post_init__(self):
        _identity(self.seed_id, "seed_id")
        _identity(self.source, "source")
        if type(self.kind) is not str or self.kind not in ("quotes", "watch_log"):
            raise ValueError("invalid artifact kind")
        if type(self.status) is not str or self.status not in ("PRESENT", "ABSENT", "UNREADABLE", "UNKNOWN"):
            raise ValueError("invalid artifact status")
        for field in ("observed_at", "available_at", "covered_through"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if not self.observed_at <= self.available_at <= self.covered_through:
            raise ValueError("artifact requires observed <= available <= covered")
        if self.status == "PRESENT":
            expected = str if self.kind == "quotes" else bytes
            if type(self.content) is not expected:
                raise ValueError("wrong artifact content type")
            if expected is str:
                try:
                    self.content.encode("utf-8")
                except UnicodeError as exc:
                    raise ValueError("quote text must be UTF-8 encodable") from exc
        elif self.content is not None:
            raise ValueError("non-PRESENT content must be None")


class _Context:
    def __init__(self, seed, decision_time, kind, clock=None):
        if type(seed) is not ArtifactSeed or seed.kind != kind:
            raise ValueError("exact seed with matching artifact kind required")
        seed.__post_init__()
        self.seed = seed
        self._decision_time = _utc(decision_time, "decision_time")
        _validate_binding(clock, self._decision_time)
        self._clock = clock
        self.events = []

    @property
    def decision_time(self):
        return self._decision_time if self._clock is None else self._clock.now

    def _advance_time(self, at):
        if self._clock is None:
            self._decision_time = at
        else:
            self._clock.advance_to(at)

    def require_available(self, at=None):
        at = self.decision_time if at is None else at
        if self.seed.status == "UNKNOWN":
            raise InputUnavailable("ARTIFACT_UNKNOWN")
        if at < self.seed.available_at:
            raise InputUnavailable("ARTIFACT_NOT_YET_AVAILABLE")
        if at > self.seed.covered_through:
            raise InputUnavailable("ARTIFACT_COVERAGE_EXPIRED")

    def call(self, operation, action):
        event = dict(operation=operation, decision_time=self.decision_time.isoformat(),
                     status="BLOCKED", exception_type=None, blocker=None)
        self.events.append(event)
        try:
            result = action()
        except Exception as exc:
            event.update(exception_type=type(exc).__name__, blocker=str(exc))
            raise
        event["status"] = "AVAILABLE"
        return result

    def now_epoch(self):
        return self.call("clock", self.decision_time.timestamp)

    @property
    def trace(self):
        return deepcopy(self.events)


class CausalQuoteReader(_Context):
    def __init__(self, *, seed: ArtifactSeed, decision_time: datetime,
                 clock: ReplayClock | None = None):
        super().__init__(seed, decision_time, "quotes", clock)

    def quote_payload(self):
        def read():
            self.require_available()
            if self.seed.status == "ABSENT":
                raise FileNotFoundError("quote artifact absent")
            if self.seed.status == "UNREADABLE":
                raise OSError("quote artifact unreadable")
            return json.loads(self.seed.content)
        return self.call("quote_payload", read)

    def snapshot(self):
        """Return the current supplied quote image, detached from caller state."""
        def snapshot():
            self.require_available()
            return replace(self.seed, status=self.seed.status,
                observed_at=self.decision_time, available_at=self.decision_time,
                content=self.seed.content)
        return self.call("snapshot", snapshot)


class _PrefixReader(RawIOBase):
    """Seek over stable append-only chunks, clipping every read at opened length."""
    def __init__(self, chunks, ends):
        super().__init__()
        self._chunks, self._ends = chunks, ends
        self._size = ends[-1] if ends else 0
        self._pos = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        self._checkClosed()
        return self._pos

    def seek(self, offset, whence=0):
        self._checkClosed()
        offset, whence = index(offset), index(whence)
        if whence not in (0, 1, 2):
            raise ValueError("invalid whence")
        pos = offset + (0 if whence == 0 else self._pos if whence == 1 else self._size)
        if pos < 0:
            raise ValueError("negative seek")
        self._pos = pos
        return pos

    def read(self, size=-1):
        self._checkClosed()
        size = -1 if size is None else index(size)
        end = self._size if size < 0 else min(self._size, self._pos+size)
        if end <= self._pos:
            return b""
        parts = []
        chunk = bisect_right(self._ends, self._pos)
        while self._pos < end:
            start = self._ends[chunk-1] if chunk else 0
            stop = min(end, self._ends[chunk])
            parts.append(self._chunks[chunk][self._pos-start:stop-start])
            self._pos = stop
            chunk += 1
        return b"".join(parts)


class _AppendWriter:
    def __init__(self, source):
        self.source = source
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.source.call("close_writer", lambda: setattr(self, "closed", True))
        return False

    def write(self, text):
        def append():
            if self.closed:
                raise ValueError("write to closed log writer")
            self.source.require_available()
            raw = text.replace("\n", self.source.newline).encode("utf-8")
            if raw:
                self.source.chunks.append(raw)
                self.source.ends.append((self.source.ends[-1] if self.source.ends else 0)+len(raw))
            return len(text)
        return self.source.call("write", append)


class _LogContext(_Context):
    def __init__(self, seed, decision_time, newline, clock=None):
        super().__init__(seed, decision_time, "watch_log", clock)
        if type(newline) is not str or newline not in ("LF", "CRLF"):
            raise ValueError("newline must be explicit LF or CRLF")
        self.newline = "\n" if newline == "LF" else "\r\n"
        self.status = seed.status
        self.chunks = [seed.content] if seed.status == "PRESENT" and seed.content else []
        self.ends = [len(seed.content)] if self.chunks else []

    def current_session(self):
        return self.call("current_session", lambda: current_session_at(decision_time=self.decision_time))

    def ensure_out(self):
        self.call("mkdir", lambda: None)  # completed virtual directory operation

    def event_log_writer(self):
        def open_writer():
            self.require_available()
            if self.status == "UNREADABLE":
                raise OSError("cannot append an unknown byte prefix")
            self.status = "PRESENT"  # source append open creates before serialization
            return _AppendWriter(self)
        return self.call("open_writer", open_writer)

    def event_log_reader(self):
        def open_reader():
            self.require_available()
            if self.status == "ABSENT":
                raise FileNotFoundError("watch log absent")
            if self.status == "UNREADABLE":
                raise OSError("watch log unreadable")
            return _PrefixReader(self.chunks, self.ends)
        return self.call("open_reader", open_reader)


class CausalWatchLog(WatchLogger):
    def __init__(self, *, seed: ArtifactSeed, decision_time: datetime, newline: str,
                 clock: ReplayClock | None = None):
        super().__init__(_LogContext(seed, decision_time, newline, clock))

    def log(self, row):
        return self.source.call("log", lambda: super(CausalWatchLog, self).log(row))

    def event_log_reader(self):
        return self.source.event_log_reader()

    def now_epoch(self):
        return self.source.now_epoch()

    def advance_to(self, decision_time):
        def advance():
            at = _utc(decision_time, "decision_time")
            if at < self.source.decision_time:
                raise ValueError("watch log cannot move backward")
            self.source.require_available(at)
            self.source._advance_time(at)
        self.source.call("advance", advance)

    def snapshot(self):
        def snapshot():
            self.source.require_available()
            return replace(self.source.seed, status=self.source.status,
                observed_at=self.source.decision_time, available_at=self.source.decision_time,
                content=b"".join(self.source.chunks) if self.source.status == "PRESENT" else None)
        return self.source.call("snapshot", snapshot)

    @property
    def trace(self):
        return self.source.trace
