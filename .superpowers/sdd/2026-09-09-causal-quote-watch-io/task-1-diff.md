# Full causal quote/watch IO review package

Base/HEAD c1b6071633c55376c64f0a98ece843706f420f49; eight untracked new files.

```diff
warning: in the working copy of 'trading_system/tree_replay/admission_io.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/admission_io.py b/trading_system/tree_replay/admission_io.py
new file mode 100644
index 0000000..e757f0c
--- /dev/null
+++ b/trading_system/tree_replay/admission_io.py
@@ -0,0 +1,247 @@
+"""Causal quote artifacts and byte-faithful, append-only watch logging in memory."""
+from bisect import bisect_right
+from copy import deepcopy
+from dataclasses import dataclass, replace
+from datetime import datetime
+from io import RawIOBase
+import json
+from operator import index
+
+from .bars import _utc
+from .state import _identity
+from ._vendor.watch_io import WatchLogger
+from ._vendor.watch_sessions import current_session_at
+
+
+class InputUnavailable(ValueError):
+    """No covered, published artifact can establish the source input."""
+
+
+@dataclass(frozen=True, kw_only=True)
+class ArtifactSeed:
+    seed_id: str
+    source: str
+    kind: str
+    status: str
+    observed_at: datetime
+    available_at: datetime
+    covered_through: datetime
+    content: str | bytes | None
+
+    def __post_init__(self):
+        _identity(self.seed_id, "seed_id")
+        _identity(self.source, "source")
+        if type(self.kind) is not str or self.kind not in ("quotes", "watch_log"):
+            raise ValueError("invalid artifact kind")
+        if type(self.status) is not str or self.status not in ("PRESENT", "ABSENT", "UNREADABLE", "UNKNOWN"):
+            raise ValueError("invalid artifact status")
+        for field in ("observed_at", "available_at", "covered_through"):
+            object.__setattr__(self, field, _utc(getattr(self, field), field))
+        if not self.observed_at <= self.available_at <= self.covered_through:
+            raise ValueError("artifact requires observed <= available <= covered")
+        if self.status == "PRESENT":
+            expected = str if self.kind == "quotes" else bytes
+            if type(self.content) is not expected:
+                raise ValueError("wrong artifact content type")
+            if expected is str:
+                try:
+                    self.content.encode("utf-8")
+                except UnicodeError as exc:
+                    raise ValueError("quote text must be UTF-8 encodable") from exc
+        elif self.content is not None:
+            raise ValueError("non-PRESENT content must be None")
+
+
+class _Context:
+    def __init__(self, seed, decision_time, kind):
+        if type(seed) is not ArtifactSeed or seed.kind != kind:
+            raise ValueError("exact seed with matching artifact kind required")
+        seed.__post_init__()
+        self.seed = seed
+        self.decision_time = _utc(decision_time, "decision_time")
+        self.events = []
+
+    def require_available(self, at=None):
+        at = self.decision_time if at is None else at
+        if self.seed.status == "UNKNOWN":
+            raise InputUnavailable("ARTIFACT_UNKNOWN")
+        if at < self.seed.available_at:
+            raise InputUnavailable("ARTIFACT_NOT_YET_AVAILABLE")
+        if at > self.seed.covered_through:
+            raise InputUnavailable("ARTIFACT_COVERAGE_EXPIRED")
+
+    def call(self, operation, action):
+        event = dict(operation=operation, decision_time=self.decision_time.isoformat(),
+                     status="BLOCKED", exception_type=None, blocker=None)
+        self.events.append(event)
+        try:
+            result = action()
+        except Exception as exc:
+            event.update(exception_type=type(exc).__name__, blocker=str(exc))
+            raise
+        event["status"] = "AVAILABLE"
+        return result
+
+    def now_epoch(self):
+        return self.call("clock", self.decision_time.timestamp)
+
+    @property
+    def trace(self):
+        return deepcopy(self.events)
+
+
+class CausalQuoteReader(_Context):
+    def __init__(self, *, seed: ArtifactSeed, decision_time: datetime):
+        super().__init__(seed, decision_time, "quotes")
+
+    def quote_payload(self):
+        def read():
+            self.require_available()
+            if self.seed.status == "ABSENT":
+                raise FileNotFoundError("quote artifact absent")
+            if self.seed.status == "UNREADABLE":
+                raise OSError("quote artifact unreadable")
+            return json.loads(self.seed.content)
+        return self.call("quote_payload", read)
+
+
+class _PrefixReader(RawIOBase):
+    """Seek over stable append-only chunks, clipping every read at opened length."""
+    def __init__(self, chunks, ends):
+        super().__init__()
+        self._chunks, self._ends = chunks, ends
+        self._size = ends[-1] if ends else 0
+        self._pos = 0
+
+    def readable(self):
+        return True
+
+    def seekable(self):
+        return True
+
+    def tell(self):
+        self._checkClosed()
+        return self._pos
+
+    def seek(self, offset, whence=0):
+        self._checkClosed()
+        offset, whence = index(offset), index(whence)
+        if whence not in (0, 1, 2):
+            raise ValueError("invalid whence")
+        pos = offset + (0 if whence == 0 else self._pos if whence == 1 else self._size)
+        if pos < 0:
+            raise ValueError("negative seek")
+        self._pos = pos
+        return pos
+
+    def read(self, size=-1):
+        self._checkClosed()
+        size = -1 if size is None else index(size)
+        end = self._size if size < 0 else min(self._size, self._pos+size)
+        if end <= self._pos:
+            return b""
+        parts = []
+        chunk = bisect_right(self._ends, self._pos)
+        while self._pos < end:
+            start = self._ends[chunk-1] if chunk else 0
+            stop = min(end, self._ends[chunk])
+            parts.append(self._chunks[chunk][self._pos-start:stop-start])
+            self._pos = stop
+            chunk += 1
+        return b"".join(parts)
+
+
+class _AppendWriter:
+    def __init__(self, source):
+        self.source = source
+        self.closed = False
+
+    def __enter__(self):
+        return self
+
+    def __exit__(self, exc_type, exc, tb):
+        self.source.call("close_writer", lambda: setattr(self, "closed", True))
+        return False
+
+    def write(self, text):
+        def append():
+            if self.closed:
+                raise ValueError("write to closed log writer")
+            self.source.require_available()
+            raw = text.replace("\n", self.source.newline).encode("utf-8")
+            if raw:
+                self.source.chunks.append(raw)
+                self.source.ends.append((self.source.ends[-1] if self.source.ends else 0)+len(raw))
+            return len(text)
+        return self.source.call("write", append)
+
+
+class _LogContext(_Context):
+    def __init__(self, seed, decision_time, newline):
+        super().__init__(seed, decision_time, "watch_log")
+        if type(newline) is not str or newline not in ("LF", "CRLF"):
+            raise ValueError("newline must be explicit LF or CRLF")
+        self.newline = "\n" if newline == "LF" else "\r\n"
+        self.status = seed.status
+        self.chunks = [seed.content] if seed.status == "PRESENT" and seed.content else []
+        self.ends = [len(seed.content)] if self.chunks else []
+
+    def current_session(self):
+        return self.call("current_session", lambda: current_session_at(decision_time=self.decision_time))
+
+    def ensure_out(self):
+        self.call("mkdir", lambda: None)  # completed virtual directory operation
+
+    def event_log_writer(self):
+        def open_writer():
+            self.require_available()
+            if self.status == "UNREADABLE":
+                raise OSError("cannot append an unknown byte prefix")
+            self.status = "PRESENT"  # source append open creates before serialization
+            return _AppendWriter(self)
+        return self.call("open_writer", open_writer)
+
+    def event_log_reader(self):
+        def open_reader():
+            self.require_available()
+            if self.status == "ABSENT":
+                raise FileNotFoundError("watch log absent")
+            if self.status == "UNREADABLE":
+                raise OSError("watch log unreadable")
+            return _PrefixReader(self.chunks, self.ends)
+        return self.call("open_reader", open_reader)
+
+
+class CausalWatchLog(WatchLogger):
+    def __init__(self, *, seed: ArtifactSeed, decision_time: datetime, newline: str):
+        super().__init__(_LogContext(seed, decision_time, newline))
+
+    def log(self, row):
+        return self.source.call("log", lambda: super(CausalWatchLog, self).log(row))
+
+    def event_log_reader(self):
+        return self.source.event_log_reader()
+
+    def now_epoch(self):
+        return self.source.now_epoch()
+
+    def advance_to(self, decision_time):
+        def advance():
+            at = _utc(decision_time, "decision_time")
+            if at < self.source.decision_time:
+                raise ValueError("watch log cannot move backward")
+            self.source.require_available(at)
+            self.source.decision_time = at
+        self.source.call("advance", advance)
+
+    def snapshot(self):
+        def snapshot():
+            self.source.require_available()
+            return replace(self.source.seed, status=self.source.status,
+                observed_at=self.source.decision_time, available_at=self.source.decision_time,
+                content=b"".join(self.source.chunks) if self.source.status == "PRESENT" else None)
+        return self.source.call("snapshot", snapshot)
+
+    @property
+    def trace(self):
+        return self.source.trace

```

```diff
warning: in the working copy of 'trading_system/tree_replay/_vendor/watch_io.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/watch_io.py b/trading_system/tree_replay/_vendor/watch_io.py
new file mode 100644
index 0000000..1c60dc5
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/watch_io.py
@@ -0,0 +1,13 @@
+"""Original watch logger on explicit local ports; no live imports."""
+import json
+
+
+class WatchLogger:
+    def __init__(self, source):
+        self.source = source
+
+    def log(self, row: dict) -> None:
+        row.setdefault("sessions", sorted(self.source.current_session()))
+        self.source.ensure_out()
+        with self.source.event_log_writer() as f:
+            f.write(json.dumps({"ts": self.source.now_epoch(), **row}, ensure_ascii=False) + "\n")

```

```diff
warning: in the working copy of 'trading_system/tree_replay/_vendor/watch_sessions.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/watch_sessions.py b/trading_system/tree_replay/_vendor/watch_sessions.py
new file mode 100644
index 0000000..6325918
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/watch_sessions.py
@@ -0,0 +1,36 @@
+"""Original session clock with a required explicit decision time."""
+from __future__ import annotations
+from zoneinfo import ZoneInfo
+import numpy as np
+import pandas as pd
+from .map_sessions import SessionSpec, SESSIONS, _hm
+
+
+def session_mask(
+    index: pd.DatetimeIndex, spec: SessionSpec, *, include_weekends: bool = False
+) -> pd.Series:
+    """Boolean mask over a UTC index for bars inside `spec`.
+
+    Sessions that wrap midnight local time (Sydney does not, but a custom one
+    might) are handled by comparing against minutes-since-local-midnight with a
+    wrap-aware test.
+    """
+    local = index.tz_convert(ZoneInfo(spec.tz))
+    minutes = local.hour * 60 + local.minute
+    s_h, s_m = _hm(spec.start)
+    e_h, e_m = _hm(spec.end)
+    start, end = s_h * 60 + s_m, e_h * 60 + e_m
+    inside = (minutes >= start) & (minutes < end) if start < end else \
+             (minutes >= start) | (minutes < end)
+    if not include_weekends:
+        inside &= np.isin(local.dayofweek, list(spec.weekdays))
+    return pd.Series(inside, index=index)
+
+
+def current_session_at(*, decision_time: pd.Timestamp, **kw) -> list[str]:
+    """Which sessions are open right now (UTC)."""
+    ts = pd.Timestamp(decision_time)
+    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
+    idx = pd.DatetimeIndex([ts])
+    return [k for k, spec in SESSIONS.items()
+            if bool(session_mask(idx, spec, **kw).iloc[0])]

```

```diff
warning: in the working copy of 'trading_system/tree_spec/watch_io_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_spec/watch_io_source.py b/trading_system/tree_spec/watch_io_source.py
new file mode 100644
index 0000000..8ca6a70
--- /dev/null
+++ b/trading_system/tree_spec/watch_io_source.py
@@ -0,0 +1,100 @@
+"""Inert independent audit of watch logger, session clock and inherited tables."""
+import ast
+import hashlib
+import json
+from pathlib import Path
+import subprocess
+
+from .tracker_admission_source import _dump, _git, _replace_exact, _selected, _without_doc
+
+
+ROOT = Path(__file__).resolve().parents[2]
+VENDOR = ROOT / "trading_system/tree_replay/_vendor"
+COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
+BLOBS = {"chartdesk/sessions.py": "2f44d322178feb14b0488abda51b40581db5b31f",
+         "scripts/market_watch.py": "f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b"}
+ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
+          subprocess.SubprocessError)
+
+
+def _logger_projection(text):
+    method, = _selected(text, ["_log"])
+    for old, new in [("sessions.current_session()", "self.source.current_session()"),
+                     ("OUT.mkdir(exist_ok=True)", "self.source.ensure_out()"),
+                     ('EVENTS.open("a", encoding="utf-8")', "self.source.event_log_writer()"),
+                     ("time.time()", "self.source.now_epoch()")]:
+        _replace_exact(method, old, new)
+    method.name = "log"
+    method.args.args.insert(0, ast.arg(arg="self"))
+    tree = ast.parse("import json\nclass WatchLogger:\n    def __init__(self, source):\n        self.source = source")
+    tree.body[1].body.append(method)
+    return tree.body
+
+
+def _session_projections(text):
+    mask, current = _selected(text, ["session_mask", "current_session"])
+    signature = ast.parse("def current_session(now: pd.Timestamp | None = None, **kw) -> list[str]: pass").body[0]
+    if _dump(current.args) != _dump(signature.args) or current.decorator_list:
+        raise ValueError("SOURCE_CLOCK_SIGNATURE_MISMATCH")
+    _replace_exact(current, 'pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz="UTC")',
+                   "pd.Timestamp(decision_time)")
+    current.name = "current_session_at"
+    current.args = ast.parse("def current_session_at(*, decision_time: pd.Timestamp, **kw): pass").body[0].args
+    imports = ast.parse("from __future__ import annotations\nfrom zoneinfo import ZoneInfo\n"
+        "import numpy as np\nimport pandas as pd\nfrom .map_sessions import SessionSpec, SESSIONS, _hm").body
+    inherited_imports = ast.parse("from __future__ import annotations\nfrom dataclasses import dataclass, field\n"
+        "from zoneinfo import ZoneInfo\nimport numpy as np\nimport pandas as pd").body
+    # The earlier tracker selector handles plain assignments, but SESSIONS is
+    # an annotated assignment. Preserve all four nodes in their actual order.
+    names = ["SessionSpec", "SESSIONS", "_hm", "psy_levels"]
+    inherited, found = [], []
+    for node in ast.parse(text).body:
+        name = (node.name if isinstance(node, (ast.ClassDef, ast.FunctionDef)) else
+                node.target.id if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) else None)
+        if name in names:
+            inherited.append(node)
+            found.append(name)
+    if found != names:
+        raise ValueError("SOURCE_SESSION_DEPENDENCY_ORDER_OR_SET_MISMATCH")
+    return {"watch_sessions.py": imports+[mask, current],
+            "map_sessions.py": inherited_imports+inherited}
+
+
+def audit_watch_io_source(source_root):
+    blockers = []
+    report = dict(status="BLOCKED", source_subset_verified=False, blockers=blockers,
+                  checked_projections=[], source_commits={"chart-desk": COMMIT},
+                  ready_for_replay=False, ready_for_training=False)
+    try:
+        root = Path(source_root) / "chart-desk"
+        if Path(_git(root, "--show-toplevel")).resolve() != root.resolve():
+            blockers.append("NOT_REPOSITORY_ROOT")
+        if _git(root, "HEAD") != COMMIT:
+            blockers.append("SOURCE_COMMIT_MISMATCH")
+        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
+        if [r.get("commit") for r in baseline["repositories"] if r.get("name") == "chart-desk"] != [COMMIT]:
+            blockers.append("BASELINE_COMMIT_MISMATCH")
+        sources = {}
+        for path, blob in BLOBS.items():
+            text = (root / path).read_text(encoding="utf-8")
+            data = text.encode("utf-8")  # universal newline read matches Git LF
+            if hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest() != blob:
+                blockers.append(f"SOURCE_BLOB_MISMATCH:{path}")
+            sources[path] = text
+        expected = {"watch_io.py": _logger_projection(sources["scripts/market_watch.py"])}
+        expected.update(_session_projections(sources["chartdesk/sessions.py"]))
+    except ERRORS as exc:
+        blockers.append(f"SOURCE_UNREADABLE:{type(exc).__name__}:{exc}")
+        return report
+    for file, nodes in expected.items():
+        try:
+            actual = _without_doc(ast.parse((VENDOR / file).read_text(encoding="utf-8")))
+            if [_dump(n) for n in actual] != [_dump(n) for n in nodes]:
+                blockers.append(f"VENDOR_AST_MISMATCH:{file}")
+        except ERRORS as exc:
+            blockers.append(f"VENDOR_UNREADABLE:{file}:{type(exc).__name__}")
+    if not blockers:
+        report.update(status="VERIFIED", source_subset_verified=True,
+                      checked_projections=["watch._log", "sessions.session_mask",
+                                           "sessions.current_session", "map_sessions_dependency"])
+    return report

```

```diff
warning: in the working copy of 'tools/check_watch_io_source_parity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tools/check_watch_io_source_parity.py b/tools/check_watch_io_source_parity.py
new file mode 100644
index 0000000..bfcb1bf
--- /dev/null
+++ b/tools/check_watch_io_source_parity.py
@@ -0,0 +1,22 @@
+"""Audit offline watch IO source projections without importing original source."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None, ""):
+    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.watch_io_source import audit_watch_io_source
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--source-root", type=Path, required=True)
+    report = audit_watch_io_source(parser.parse_args().source_root)
+    print(json.dumps(report, sort_keys=True, indent=2))
+    return 0 if report["source_subset_verified"] else 2
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())

```

```diff
warning: in the working copy of 'tests/tree_replay/test_admission_io.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_admission_io.py b/tests/tree_replay/test_admission_io.py
new file mode 100644
index 0000000..d8e8c4a
--- /dev/null
+++ b/tests/tree_replay/test_admission_io.py
@@ -0,0 +1,300 @@
+"""Actual quote/rejection consumers and original logger on causal artifacts."""
+from dataclasses import FrozenInstanceError, replace
+from datetime import datetime, timedelta, timezone
+import importlib
+import importlib.util
+import json
+
+import pandas as pd
+import pytest
+
+from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission, _tail_reader
+
+
+T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
+SYM, LONG, SHORT = "OANDA:XAUUSD", "לונג", "שורט"
+
+
+def api():
+    name = "trading_system.tree_replay.admission_io"
+    assert importlib.util.find_spec(name) is not None, "causal quote/watch IO missing"
+    return importlib.import_module(name)
+
+
+def seed(kind="watch_log", status="PRESENT", content=b"", *, at=T, **kw):
+    return api().ArtifactSeed(**(dict(seed_id="artifact-1", source="synthetic",
+        kind=kind, status=status, content=content if status == "PRESENT" else None,
+        observed_at=at-timedelta(hours=1), available_at=at-timedelta(minutes=30),
+        covered_through=at+timedelta(hours=1)) | kw))
+
+
+def make_log(*, status="PRESENT", content=b"", at=T, newline="LF", **kw):
+    return api().CausalWatchLog(seed=seed(status=status, content=content, at=at, **kw),
+                              decision_time=at, newline=newline)
+
+
+def quotes(payload=None, *, status="PRESENT", text=None, **kw):
+    return api().CausalQuoteReader(seed=seed("quotes", status,
+        json.dumps(payload if payload is not None else {}) if text is None else text, **kw), decision_time=T)
+
+
+@pytest.mark.parametrize("age,price,want", [(0, 100, {SYM: 100.}),
+    (420, 100, {SYM: 100.}), (420.001, 100, {}), (-.001, 100, {}),
+    (0, 0, {}), (0, -1, {}), (0, float("nan"), {}), (0, float("inf"), {})])
+def test_actual_source_quote_freshness_not_file_or_metadata_age(age, price, want):
+    r = quotes({SYM: {"lp": price, "ts": T.timestamp()-age,
+                      "metadata_ts": T.timestamp(), "bid": 99}})
+    assert TrackerAdmission(r)._live_prices() == want
+
+
+@pytest.mark.parametrize("status,text,error", [("ABSENT", None, "FileNotFoundError"),
+    ("UNREADABLE", None, "OSError"), ("UNKNOWN", None, "InputUnavailable"),
+    ("PRESENT", "{torn", "JSONDecodeError")])
+def test_quote_read_failure_survives_original_empty_price_fallback(status, text, error):
+    r = quotes(status=status, text=text)
+    assert TrackerAdmission(r)._live_prices() == {}
+    assert any(e["exception_type"] == error for e in r.trace)
+
+
+def test_valid_nonobject_quote_json_keeps_source_consumer_error_boundary():
+    r = quotes(text="[]")
+    assert r.quote_payload() == []
+    with pytest.raises(AttributeError):
+        TrackerAdmission(r)._live_prices()
+
+
+def test_quote_payload_is_detached_and_symbols_are_not_aliased():
+    r = quotes({"XAUUSD": {"lp": 100, "ts": T.timestamp()}})
+    first = r.quote_payload()
+    first["XAUUSD"]["lp"] = 999
+    assert TrackerAdmission(r)._live_prices() == {"XAUUSD": 100.}
+    assert r.quote_payload()["XAUUSD"]["lp"] == 100
+
+
+@pytest.mark.parametrize("kw", [dict(available_at=T+timedelta(microseconds=1)),
+                               dict(covered_through=T-timedelta(microseconds=1))])
+def test_unpublished_or_expired_quotes_never_reach_consumer(kw):
+    r = quotes({SYM: {"lp": 100, "ts": T.timestamp()}}, **kw)
+    assert TrackerAdmission(r)._live_prices() == {}
+    assert any(e["exception_type"] == "InputUnavailable" for e in r.trace)
+
+
+@pytest.mark.parametrize("side,price,age,want", [(LONG, 103, 0, False),
+    (SHORT, 97, 0, False), (LONG, 90, 0, True), (SHORT, 110, 0, True),
+    (LONG, 103, 421, True)])
+def test_original_born_state_uses_supplied_quote_with_source_fallback(side, price, age, want):
+    from test_tracker_admission import plan
+    r = quotes({SYM: {"lp": price, "ts": T.timestamp()-age}})
+    assert TrackerAdmission(r)._born_in_zone(plan(close=100., direction=side), SYM) is want
+
+
+@pytest.mark.parametrize("newline,ending", [("LF", b"\n"), ("CRLF", b"\r\n")])
+def test_original_log_literal_bytes_and_input_mutation(newline, ending):
+    log = make_log(status="ABSENT", newline=newline)
+    row = {"kind": "rejection"}
+    log.log(row)
+    assert row == {"kind": "rejection", "sessions": ["newyork"]}
+    assert log.snapshot().content == (
+        b'{"ts": 1788969600.0, "kind": "rejection", "sessions": ["newyork"]}'+ending)
+    operations = [e["operation"] for e in log.trace]
+    assert operations.index("current_session") < operations.index("open_writer") < operations.index("clock") < operations.index("write")
+
+
+def test_caller_timestamp_sessions_and_key_order_are_not_overwritten():
+    log = make_log()
+    log.log({"z": "שלום", "sessions": ["custom"], "ts": 12, "a": 1})
+    assert log.snapshot().content == '{"ts": 12, "z": "שלום", "sessions": ["custom"], "a": 1}\n'.encode()
+    assert any(e["operation"] == "clock" for e in log.trace)
+
+
+def test_session_default_is_eager_even_when_caller_supplies_sessions(monkeypatch):
+    log = make_log(status="ABSENT")
+    def fail():
+        raise ArithmeticError("session failed")
+    monkeypatch.setattr(log.source, "current_session", fail)
+    row = {"sessions": ["custom"]}
+    with pytest.raises(ArithmeticError):
+        log.log(row)
+    assert row == {"sessions": ["custom"]} and log.snapshot().status == "ABSENT"
+    assert not any(e["operation"] == "open_writer" for e in log.trace)
+
+
+def test_bad_serialization_still_mutates_row_and_creates_empty_append_file():
+    log = make_log(status="ABSENT")
+    row = {"bad": object()}
+    with pytest.raises(TypeError):
+        log.log(row)
+    assert row["sessions"] == ["newyork"]
+    snap = log.snapshot()
+    assert snap.status == "PRESENT" and snap.content == b""
+    assert any(e["exception_type"] == "TypeError" for e in log.trace)
+
+
+@pytest.mark.parametrize("status", ["UNKNOWN", "UNREADABLE"])
+def test_unknown_log_prefix_is_not_silently_replaced_on_append(status):
+    log = make_log(status=status)
+    row = {}
+    with pytest.raises((api().InputUnavailable, OSError)):
+        log.log(row)
+    assert row == {"sessions": ["newyork"]}
+    assert _tail_reader(log.event_log_reader) is None
+    assert any(e["status"] == "BLOCKED" for e in log.trace)
+
+
+@pytest.mark.parametrize("kw", [dict(available_at=T+timedelta(seconds=1)),
+                               dict(covered_through=T-timedelta(seconds=1))])
+def test_log_publication_and_coverage_guard_reads_appends_and_snapshot(kw):
+    log = make_log(content=b"supplied\n", **kw)
+    row = {}
+    with pytest.raises(api().InputUnavailable):
+        log.log(row)
+    assert row == {"sessions": ["newyork"]}
+    assert _tail_reader(log.event_log_reader) is None
+    with pytest.raises(api().InputUnavailable):
+        log.snapshot()
+    if "available_at" in kw:
+        log.advance_to(T+timedelta(seconds=1))
+        assert log.snapshot().content == b"supplied\n"
+
+
+def test_encoding_failure_preserves_existing_prefix_and_remains_traced():
+    log = make_log(content=b"previous\n")
+    row = {"bad": "\ud800"}
+    with pytest.raises(UnicodeError):
+        log.log(row)
+    assert log.snapshot().content == b"previous\n"
+    assert row["sessions"] == ["newyork"]
+    assert any(e["operation"] == "write" and e["exception_type"] == "UnicodeEncodeError" for e in log.trace)
+
+
+def test_absent_log_read_and_empty_present_log_are_distinct():
+    absent = make_log(status="ABSENT")
+    assert _tail_reader(absent.event_log_reader) is None
+    assert any(e["exception_type"] == "FileNotFoundError" for e in absent.trace)
+    assert _tail_reader(make_log().event_log_reader) == b""
+
+
+@pytest.mark.parametrize("prefix", [b"\xff\xfe\n", b'{"torn": ', b"earlier\r\n"])
+def test_raw_prefix_is_not_decoded_repaired_or_reserialized(prefix):
+    log = make_log(content=prefix)
+    log.log({"kind": "nontrade"})
+    assert log.snapshot().content == prefix + b'{"ts": 1788969600.0, "kind": "nontrade", "sessions": ["newyork"]}\n'
+
+
+def test_reader_captures_prefix_and_seek_spans_real_append_chunks():
+    log = make_log(content=b"start\n")
+    first = log.event_log_reader()
+    log.log({"kind": "one"})
+    second = log.event_log_reader()
+    log.advance_to(T+timedelta(seconds=1))
+    log.log({"kind": "two"})
+    assert first.read() == b"start\n"
+    second.seek(4)
+    assert second.read(5) == b't\n{"t'
+    second.seek(-3, 2)
+    assert second.read() == b']}\n'
+    assert first.seek(1000) == 1000 and first.read() == b""
+    first.close()
+    with pytest.raises(ValueError):
+        first.read()
+    assert b'"two"' not in second.read()  # already at captured end
+    second.seek(0)
+    assert b'"two"' not in second.read()
+    with log.event_log_reader() as third:
+        assert b'"two"' in third.read()
+
+
+def test_source_tail_reads_small_suffix_and_widens_without_dropping_prior_lines():
+    log = make_log(content=b"older\n"+b"x"*1000000+b"\nlast\n")
+    reader = log.event_log_reader()
+    sizes = []
+    original = reader.read
+    def read(size=-1):
+        result = original(size)
+        sizes.append(len(result))
+        return result
+    reader.read = read
+    assert _tail_reader(lambda: reader, window=16) == b"last\n"
+    assert sizes == [16]  # original source seeks before requesting bytes
+    small = make_log(content=b"first\n"+b"x"*30+b"\n")
+    assert _tail_reader(small.event_log_reader, window=8, cap=64) == b"x"*30+b"\n"
+    assert _tail_reader(small.event_log_reader, window=8, cap=8) == b"first\n"+b"x"*30+b"\n"
+
+
+def test_real_recent_rejection_sees_same_pass_append_but_not_later_reader_bytes():
+    log = make_log()
+    tracker = TrackerAdmission(log)
+    def recent():
+        return tracker._recent_rejection(SYM, LONG, T.timestamp()-60, T.timestamp(), 100.)
+    assert recent() is None
+    before = log.event_log_reader()
+    log.log({"kind": "level_reversal_detected", "symbol": SYM})
+    assert recent() is None
+    log.log({"kind": "rejection", "symbol": SYM, "direction": LONG,
+             "zone_lo": 98, "zone_hi": 102, "levels": ["PSY"], "close": 100, "wick_atr": .5})
+    assert recent() == dict(ts=1788969600., direction=LONG, zone_lo=98, zone_hi=102,
+                           levels=["PSY"], close=100, wick_atr=.5, age_s=0., gap=0.)
+    assert before.read() == b""
+    log.log({"kind": "rejection", "symbol": SYM, "direction": LONG,
+             "zone_lo": 98, "zone_hi": 102, "levels": ["tie-later"]})
+    assert recent()["levels"] == ["PSY"]  # same-ts source tie keeps first row
+
+
+@pytest.mark.parametrize("stamp,want", [("2026-09-09T16:00Z", ["newyork"]),
+    ("2026-01-09T14:00Z", ["frankfurt", "london", "us_brinks"]),
+    ("2026-03-20T13:45Z", ["frankfurt", "london", "newyork", "us_brinks"]),
+    ("2026-09-06T16:00Z", [])])
+def test_original_source_sessions_on_actual_clock(stamp, want):
+    at = pd.Timestamp(stamp).to_pydatetime()
+    log = make_log(at=at)
+    row = {}
+    log.log(row)
+    assert row["sessions"] == want
+
+
+@pytest.mark.parametrize("advance", [T-timedelta(microseconds=1), T+timedelta(hours=1,microseconds=1),
+    T.replace(tzinfo=None), pd.Timestamp(T)+pd.Timedelta(1, "ns")])
+def test_invalid_advance_is_atomic(advance):
+    log = make_log()
+    with pytest.raises(ValueError):
+        log.advance_to(advance)
+    assert log.now_epoch() == T.timestamp()
+    assert log.snapshot().content == b""
+
+
+def test_snapshot_handoff_is_detached_and_has_current_publication_time():
+    log = make_log()
+    log.log({"kind": "first"})
+    old = log.snapshot()
+    log.advance_to(T+timedelta(minutes=1))
+    log.log({"kind": "second"})
+    new = log.snapshot()
+    assert new.observed_at == new.available_at == T+timedelta(minutes=1)
+    assert old.content != new.content and new.content.startswith(old.content)
+    assert new.seed_id == old.seed_id and new.covered_through == old.covered_through
+    detached = log.trace
+    detached[0]["status"] = "bad"
+    assert log.trace[0]["status"] == "AVAILABLE"
+
+
+@pytest.mark.parametrize("kw", [dict(seed_id=""), dict(source=" bad "), dict(seed_id="\ud800"),
+    dict(kind="other"), dict(kind="quotes", content=b"{}"), dict(content=""),
+    dict(status="ABSENT", content=b""), dict(status="present"),
+    dict(observed_at=T.replace(tzinfo=None)), dict(observed_at=T),
+    dict(available_at=pd.Timestamp(T)+pd.Timedelta(1,"ns")),
+    dict(covered_through=T-timedelta(days=2))])
+def test_bad_seed_rejected(kw):
+    with pytest.raises(ValueError):
+        replace(seed(), **kw)
+
+
+def test_exact_seed_kind_newline_and_frozen_inputs():
+    s = seed()
+    with pytest.raises(FrozenInstanceError):
+        s.content = b"changed"
+    with pytest.raises(ValueError):
+        api().CausalQuoteReader(seed=s, decision_time=T)
+    with pytest.raises(ValueError):
+        api().CausalWatchLog(seed={}, decision_time=T, newline="LF")
+    with pytest.raises(ValueError):
+        make_log(newline="platform_default")

```

```diff
warning: in the working copy of 'tests/tree_spec/test_watch_io_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_spec/test_watch_io_source.py b/tests/tree_spec/test_watch_io_source.py
new file mode 100644
index 0000000..d19ea3b
--- /dev/null
+++ b/tests/tree_spec/test_watch_io_source.py
@@ -0,0 +1,87 @@
+"""Source identity and whole-module mutation tests for watch IO projections."""
+import importlib
+import importlib.util
+import json
+import os
+from pathlib import Path
+import subprocess
+import sys
+
+import pytest
+
+
+ROOT = Path(__file__).resolve().parents[2]
+SOURCE = Path(os.environ.get("TR_TREE_SOURCE_ROOT",
+    "C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149"))
+VENDOR = ROOT / "trading_system/tree_replay/_vendor"
+
+
+def api():
+    name = "trading_system.tree_spec.watch_io_source"
+    assert importlib.util.find_spec(name) is not None, "watch IO auditor missing"
+    return importlib.import_module(name)
+
+
+def test_actual_pins_logger_sessions_and_inherited_tables_verify():
+    r = api().audit_watch_io_source(SOURCE)
+    assert r["source_subset_verified"] and r["blockers"] == []
+    assert r["checked_projections"] == ["watch._log", "sessions.session_mask",
+                                        "sessions.current_session", "map_sessions_dependency"]
+    assert not r["ready_for_replay"] and not r["ready_for_training"]
+
+
+@pytest.mark.parametrize("file,old,new", [
+    ("watch_io.py", "import json", "import json\nimport os"),
+    ("watch_io.py", 'row.setdefault("sessions", sorted(self.source.current_session()))',
+     'row.setdefault("sessions", [])'),
+    ("watch_io.py", 'row.setdefault("sessions", sorted(self.source.current_session()))\n        self.source.ensure_out()',
+     'self.source.ensure_out()\n        row.setdefault("sessions", sorted(self.source.current_session()))'),
+    ("watch_io.py", "self.source.now_epoch()", "0.0"),
+    ("watch_io.py", "ensure_ascii=False", "ensure_ascii=False, sort_keys=True"),
+    ("watch_sessions.py", "pd.Timestamp(decision_time)", 'pd.Timestamp.now(tz="UTC")'),
+    ("watch_sessions.py", "minutes < end", "minutes <= end"),
+    ("watch_sessions.py", "if not include_weekends:", "if False:"),
+    ("map_sessions.py", '"09:30", "16:00"', '"09:31", "16:00"'),
+])
+def test_changed_order_clock_boundaries_or_extra_code_block(monkeypatch, file, old, new):
+    target = VENDOR / file
+    original_read = Path.read_text
+    original = original_read(target, encoding="utf-8")
+    assert old in original
+    def read(path, *args, **kw):
+        return original.replace(old, new) if path.resolve() == target.resolve() else original_read(path, *args, **kw)
+    monkeypatch.setattr(Path, "read_text", read)
+    r = api().audit_watch_io_source(SOURCE)
+    assert not r["source_subset_verified"]
+    assert f"VENDOR_AST_MISMATCH:{file}" in r["blockers"]
+
+
+def test_wrong_commit_is_blocked(monkeypatch):
+    module = api()
+    original_git = module._git
+    monkeypatch.setattr(module, "_git", lambda path, *args:
+        "0"*40 if args == ("HEAD",) else original_git(path, *args))
+    assert "SOURCE_COMMIT_MISMATCH" in module.audit_watch_io_source(SOURCE)["blockers"]
+
+
+def test_changed_source_blob_is_blocked(monkeypatch):
+    original_read = Path.read_text
+    target = SOURCE / "chart-desk/scripts/market_watch.py"
+    def read(path, *args, **kw):
+        content = original_read(path, *args, **kw)
+        return content+"\n# source drift\n" if path.resolve() == target.resolve() else content
+    monkeypatch.setattr(Path, "read_text", read)
+    r = api().audit_watch_io_source(SOURCE)
+    assert "SOURCE_BLOB_MISMATCH:scripts/market_watch.py" in r["blockers"]
+
+
+def test_cli_success_and_missing_source_failure(tmp_path):
+    api()
+    cmd = [sys.executable, str(ROOT / "tools/check_watch_io_source_parity.py"), "--source-root"]
+    for path, code in [(SOURCE, 0), (tmp_path, 2)]:
+        result = subprocess.run(cmd+[str(path)], cwd=tmp_path, text=True,
+                                capture_output=True, encoding="utf-8", timeout=30)
+        assert result.returncode == code, result.stderr
+        report = json.loads(result.stdout)
+        assert report["source_subset_verified"] is (code == 0)
+        assert not report["ready_for_training"]

```

```diff
warning: in the working copy of 'docs/architecture/CAUSAL-QUOTE-WATCH-IO-USAGE.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/docs/architecture/CAUSAL-QUOTE-WATCH-IO-USAGE.md b/docs/architecture/CAUSAL-QUOTE-WATCH-IO-USAGE.md
new file mode 100644
index 0000000..2c1955d
--- /dev/null
+++ b/docs/architecture/CAUSAL-QUOTE-WATCH-IO-USAGE.md
@@ -0,0 +1,104 @@
+# Causal quote and watch-log ports
+
+`trading_system.tree_replay.admission_io` supplies `ArtifactSeed`,
+`CausalQuoteReader` and `CausalWatchLog`. They use in-memory supplied evidence,
+not live quote files, notifications or broker data. No source threshold changed.
+
+## Evidence and quote reads
+
+ArtifactSeed has seed_id/source, kind (quotes/watch_log), status, observed_at,
+available_at, covered_through and content. All clocks must be aware/microsecond-
+exact; observed<=available<=covered. Coverage is an explicit attestation of no
+unrepresented external updates through its end, not automatic historical proof.
+
+PRESENT quotes require original UTF-8 text; PRESENT watch_log requires exact bytes.
+ABSENT, UNREADABLE and UNKNOWN requireNone and mean different things. Invalid
+JSON may be faithfully supplied as text; invalid UTF-8/torn lines remain raw log
+bytes. Neither is silently repaired. Quote payload timestamps are not rewritten.
+
+```python
+quotes = CausalQuoteReader(seed=quote_seed, decision_time=T)
+payload = quotes.quote_payload()
+```
+
+Each quote read reparses the original text, so returned mutations do not leak.
+Absent/unreadable files raise, unknown/unpublished/expired evidence raises
+InputUnavailable. Read/JSON failures stay in trace even if original tracker
+returns no prices. Valid nonobject JSON stays nonobject: the original consumer's
+d.items error is not transformed into a provider empty-dict fallback. Original
+tracker still owns price/age conversion,420s inclusive freshness and born state.
+Metadata-only updates and file publication cannot rejuvenate an old payload ts;
+bare symbols are not aliased and candles do not substitute for supplied quotes.
+
+## Original logging and byte prefixes
+
+```python
+log = CausalWatchLog(seed=watch_seed, decision_time=T, newline="LF")
+log.log({"symbol": symbol, "kind": "rejection", "direction": direction})
+with log.event_log_reader() as reader:
+    reader.seek(0, 2)
+    size_at_open = reader.tell()
+log.advance_to(next_T)
+```
+
+newline must explicitly be LF or CRLF; no platform default is assumed. The
+source logger calculates original current sessions at the context clock, mutates
+row.setdefault before mkdir/open, and serializes unsorted/default-separator
+JSON with ensure_asciiFalse. Existing sessions are retained, but calculation is
+eager even when supplied. An existing row.ts overrides generated ts; its clock
+call still occurs. Payload time and actual append/publication time differ.
+
+Append opening creates an empty PRESENT file from known ABSENT before JSON
+serialization. A later serialization failure leaves that empty file and caller
+session mutation, with a failed log trace. Encoding failure never appends invented
+bytes. Unknown/unreadable prefix blocks faithful append after the independent
+session step. This is missing historical evidence, not proof an original live
+writer would have failed. Real OS permissions/partial writes are not simulated.
+
+Every original byte is retained, including non-rejection events and malformed
+lines. Appending does not insert a separator before a torn final line. Original
+tracker _tail_reader remains responsible for windows, line-boundary widening and
+fallback read-all. The provider never substitutes a semantic rejection-only view.
+
+The log is held in append-only chunks with cumulative byte ends. Each reader
+captures the current length and reads requested spans by seek/bisection. Opening
+or taking a short tail does not concatenate the whole prefix. Old readers never
+see later appends, including after advance_to. This models ordered single-writer
+replay snapshots, not concurrent OS file-descriptor behavior. Source read-all
+fallback still materializes its requested bytes; memory use includes all retained
+chunks. This component is not a disk-backed ten-year archive or retention approval.
+
+advance_to is monotonic and requires covered/publication-valid time. Invalid
+advances do not change the clock. It retains chunks without full-prefix copies.
+snapshot explicitly materializes a complete watch ArtifactSeed at currentT with
+the same source/id/coverage. Snapshot is one artifact handoff, not a full replay
+checkpoint; effects, input cursors, state/locks/lifecycle need whole-loop ownership.
+Trace is a detached ordered list of operation times, statuses and failure reasons.
+Do not mutate backend internals or use a later prefix as an earlier source seed.
+
+## Verification and scope
+
+Private watch logger/current-session/mask projections and the inherited
+map_sessions table/helper module are audited against pinned repo/commit/blobs.
+The logger's exact port substitutions and clock signature adaptation are checked
+as whole modules, including imports. The audit never executes retained source.
+The existing tracker audit separately covers quote/rejection consumers. Source
+timezone behavior depends on the environment's IANA database; full replay must
+record that dependency and certify its actual historical feed/publication inputs.
+
+```text
+python -m pytest tests/tree_replay/test_admission_io.py tests/tree_spec/test_watch_io_source.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_frames.py -q --tb=short
+python tools/check_watch_io_source_parity.py --source-root <retained-source-parent>
+python tools/check_tracker_admission_source_parity.py --source-root <retained-source-parent>
+```
+
+Tests use TR_TREE_SOURCE_ROOT to override the retained parent, never silently
+skip a missing audit. They exercise real original quote/born/rejection consumers,
+source log bytes and sessions, publication/coverage, partial creation failures,
+reader cutoffs, chunk boundaries, source tail widening and same-time rejection ties.
+Fault injection is scoped to independent failures, not supplied net/born decisions.
+
+State and frames remain separate accepted components. Original locks, main caller
+order, heterogeneous watch state, generated lifecycle, all producers, economic
+simulation, dataset/models and full shadow gates are still required. No full
+replay/readiness claim, real-data acquisition, notifications, deployment or trading.

```


