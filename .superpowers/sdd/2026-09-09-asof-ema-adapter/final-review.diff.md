# Final slice review package

Base/head c1b6071633c55376c64f0a98ece843706f420f49 unchanged; no commits requested.
Review only the 2026-09-09 as-of EMA slice. Older changes preserved, not reimplemented.

```diff
warning: in the working copy of 'trading_system/tree_replay/__init__.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/__init__.py b/trading_system/tree_replay/__init__.py
new file mode 100644
index 0000000..37c18a9
--- /dev/null
+++ b/trading_system/tree_replay/__init__.py
@@ -0,0 +1 @@
+"""Offline calculation adapters; no complete tree replay or training authorization."""

```
```diff
warning: in the working copy of 'trading_system/tree_replay/bars.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/bars.py b/trading_system/tree_replay/bars.py
new file mode 100644
index 0000000..3de4924
--- /dev/null
+++ b/trading_system/tree_replay/bars.py
@@ -0,0 +1,172 @@
+"""Explicit closed-bar contracts for offline as-of research.
+
+Only fixed-duration, contiguous histories are supported. Metadata validation is
+not proof of historical availability; callers must supply that evidence.
+Timestamps must be microsecond-exact; finer precision is rejected, never rounded.
+"""
+
+from collections.abc import Iterable
+from dataclasses import dataclass
+from datetime import datetime, timedelta, timezone
+from math import isfinite
+
+
+_DURATIONS = {
+    "5m": timedelta(minutes=5),
+    "15m": timedelta(minutes=15),
+    "30m": timedelta(minutes=30),
+    "1h": timedelta(hours=1),
+    "4h": timedelta(hours=4),
+}
+
+
+def _validate_identity(instrument: str, timeframe: str) -> None:
+    if (
+        not isinstance(instrument, str)
+        or instrument.count(":") != 1
+        or not all(instrument.split(":"))
+        or any(character.isspace() for character in instrument)
+    ):
+        raise ValueError("instrument must be an exact non-whitespace venue:symbol")
+    if not isinstance(timeframe, str) or timeframe not in _DURATIONS:
+        raise ValueError("timeframe must be 5m, 15m, 30m, 1h or 4h")
+
+
+def _utc(value: datetime, field: str) -> datetime:
+    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
+        raise ValueError(f"{field} must be a timezone-aware datetime")
+    # pandas Timestamp is a datetime subclass with a nanosecond remainder.
+    # Check before conversion so no finer input precision can disappear.
+    if getattr(value, "nanosecond", 0) != 0:
+        raise ValueError(f"{field} must be microsecond-exact")
+    utc = value.astimezone(timezone.utc)
+    native = datetime(
+        utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second,
+        utc.microsecond, tzinfo=timezone.utc,
+    )
+    if utc != native:
+        raise ValueError(f"{field} must be microsecond-exact")
+    return native
+
+
+def _number(value: float, field: str) -> float:
+    if type(value) not in (int, float):
+        raise ValueError(f"{field} must be a native int or float, not bool")
+    try:
+        result = float(value)
+    except OverflowError as exc:
+        raise ValueError(f"{field} exceeds finite float range") from exc
+    if not isfinite(result):
+        raise ValueError(f"{field} must be finite")
+    return result
+
+
+@dataclass(frozen=True, kw_only=True)
+class ClosedBar:
+    """A completed observation, with explicit source and publication time."""
+
+    instrument: str
+    timeframe: str
+    opened_at: datetime
+    closed_at: datetime
+    available_at: datetime
+    open: float
+    high: float
+    low: float
+    close: float
+    volume: float | None
+    source: str
+
+    def __post_init__(self) -> None:
+        _validate_identity(self.instrument, self.timeframe)
+        if not isinstance(self.source, str) or not self.source or self.source != self.source.strip():
+            raise ValueError("source must be a nonempty trimmed string")
+        for field in ("opened_at", "closed_at", "available_at"):
+            object.__setattr__(self, field, _utc(getattr(self, field), field))
+        if self.closed_at - self.opened_at != _DURATIONS[self.timeframe]:
+            raise ValueError("bar elapsed duration must match timeframe exactly")
+        if self.available_at < self.closed_at:
+            raise ValueError("available_at cannot precede closed_at")
+        for field in ("open", "high", "low", "close"):
+            value = _number(getattr(self, field), field)
+            if value <= 0:
+                raise ValueError(f"{field} must be positive")
+            object.__setattr__(self, field, value)
+        if not (self.low <= self.open <= self.high and self.low <= self.close <= self.high):
+            raise ValueError("open and close must lie between low and high")
+        if self.volume is not None:
+            volume = _number(self.volume, "volume")
+            if volume < 0:
+                raise ValueError("volume must be nonnegative or None")
+            object.__setattr__(self, "volume", volume)
+
+
+@dataclass(frozen=True, kw_only=True)
+class BarWindow:
+    """Selector result; a non-null blocker forbids using it as usable history."""
+
+    instrument: str
+    timeframe: str
+    decision_time: datetime
+    history_start: datetime
+    max_age_seconds: int
+    bars: tuple[ClosedBar, ...]
+    blocker: str | None
+
+
+def select_closed_bars(
+    bars: Iterable[ClosedBar], *, instrument: str, timeframe: str,
+    decision_time: datetime, history_start: datetime, max_age_seconds: int,
+) -> BarWindow:
+    """Validate every input, then select closed and available bars as of T.
+
+    Duplicate opens (including revisions) and mixed identities are invalid even
+    outside the selected window. No calendar, resampling or revision policy is
+    inferred. Blocked results retain selected bars for diagnostics only.
+    """
+    _validate_identity(instrument, timeframe)
+    decision_time = _utc(decision_time, "decision_time")
+    history_start = _utc(history_start, "history_start")
+    if history_start > decision_time:
+        raise ValueError("history_start cannot be after decision_time")
+    if type(max_age_seconds) is not int or max_age_seconds <= 0:
+        raise ValueError("max_age_seconds must be an explicit positive integer")
+
+    selected = []
+    seen_opens = set()
+    for bar in bars:
+        if not isinstance(bar, ClosedBar):
+            raise ValueError("bars must contain only ClosedBar inputs")
+        if bar.instrument != instrument or bar.timeframe != timeframe:
+            raise ValueError("every bar must match the exact instrument and timeframe")
+        if bar.opened_at in seen_opens:
+            raise ValueError("duplicate bar opens and revisions are unsupported")
+        seen_opens.add(bar.opened_at)
+        if (
+            bar.opened_at >= history_start
+            and bar.closed_at <= decision_time
+            and bar.available_at <= decision_time
+        ):
+            selected.append(bar)
+    selected.sort(key=lambda bar: bar.opened_at)
+
+    blocker = None
+    if not selected:
+        blocker = "NO_HISTORY"
+    elif selected[0].opened_at != history_start:
+        blocker = "HISTORY_INCOMPLETE"
+    elif any(previous.closed_at != following.opened_at for previous, following in zip(selected, selected[1:])):
+        blocker = "HISTORY_GAP"
+    else:
+        age = decision_time - selected[-1].closed_at
+        # Integer arithmetic preserves microseconds even over long histories,
+        # and accepts explicit budgets larger than timedelta's representable range.
+        age_microseconds = (age.days * 86400 + age.seconds) * 1_000_000 + age.microseconds
+        if age_microseconds > max_age_seconds * 1_000_000:
+            blocker = "STALE"
+
+    return BarWindow(
+        instrument=instrument, timeframe=timeframe, decision_time=decision_time,
+        history_start=history_start, max_age_seconds=max_age_seconds,
+        bars=tuple(selected), blocker=blocker,
+    )

```
```diff
warning: in the working copy of 'trading_system/tree_replay/_vendor/__init__.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/__init__.py b/trading_system/tree_replay/_vendor/__init__.py
new file mode 100644
index 0000000..133a90c
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/__init__.py
@@ -0,0 +1 @@
+"""Small attributed, pinned pure source subsets; never the live desk package."""

```
```diff
warning: in the working copy of 'trading_system/tree_replay/_vendor/indicators.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/indicators.py b/trading_system/tree_replay/_vendor/indicators.py
new file mode 100644
index 0000000..151f3d6
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/indicators.py
@@ -0,0 +1,62 @@
+"""Audited pure subset from sagivamrami-cpu/chart-desk, indicators.py.
+
+Pinned commit: 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.
+Function bodies retained unchanged; no live source package imports.
+Original docstrings describe source intent, not independent chart certification.
+"""
+
+from __future__ import annotations
+
+import numpy as np
+import pandas as pd
+
+
+def _seeded_recursive(src: pd.Series, length: int, alpha: float) -> pd.Series:
+    """alpha*src + (1-alpha)*prev, seeded with the SMA of the first `length`.
+
+    This is the shape of both `ta.ema` (alpha = 2/(len+1)) and `ta.rma`
+    (alpha = 1/len) in Pine.
+
+    The seed is taken from the first *fully populated* window, not from bars
+    0..length-1. Inputs derived from `diff()` start with a NaN, and seeding on
+    it would poison the whole recursion -- every later value comes out NaN. Pine
+    behaves the same way: `ta.sma` over a window containing `na` is `na`, so
+    `ta.rsi` simply starts one bar later than `ta.ema` does.
+    """
+    v = src.to_numpy(dtype=float)
+    n = v.size
+    out = np.full(n, np.nan)
+    if length < 1 or n < length:
+        return pd.Series(out, index=src.index)
+
+    ok = ~np.isnan(v)
+    run = 0
+    start = -1
+    for i in range(n):
+        run = run + 1 if ok[i] else 0
+        if run == length:
+            start = i
+            break
+    if start < 0:
+        return pd.Series(out, index=src.index)
+
+    prev = float(np.mean(v[start - length + 1 : start + 1]))
+    out[start] = prev
+    for i in range(start + 1, n):
+        if np.isnan(v[i]):
+            out[i] = prev          # Pine holds the last value through a gap
+            continue
+        prev = alpha * v[i] + (1.0 - alpha) * prev
+        out[i] = prev
+    return pd.Series(out, index=src.index)
+
+
+def ema(src: pd.Series, length: int) -> pd.Series:
+    """Pine `ta.ema`: SMA-seeded, alpha = 2/(length+1)."""
+    return _seeded_recursive(src, length, 2.0 / (length + 1.0))
+
+
+def stdev(src: pd.Series, length: int) -> pd.Series:
+    """Pine `ta.stdev` uses the population standard deviation (ddof=0)."""
+    return src.rolling(length, min_periods=length).std(ddof=0)
+

```
```diff
warning: in the working copy of 'trading_system/tree_replay/_vendor/tr.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/tr.py b/trading_system/tree_replay/_vendor/tr.py
new file mode 100644
index 0000000..a3386f7
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/tr.py
@@ -0,0 +1,39 @@
+"""Audited pure subset from sagivamrami-cpu/chart-desk, tr.py.
+
+Pinned commit: 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.
+Function bodies retained unchanged; no live source package imports.
+Original docstrings describe source intent, not independent chart certification.
+"""
+
+from __future__ import annotations
+
+import pandas as pd
+
+from . import indicators as I
+
+TR_EMAS: tuple[int, ...] = (5, 13, 50, 200, 800)
+
+
+def emas(df: pd.DataFrame, lengths: tuple[int, ...] = TR_EMAS) -> pd.DataFrame:
+    """The five TR EMAs. **transcribed** (`ta.ema(close, 5|13|50|200|800)`)."""
+    return pd.DataFrame(
+        {f"ema{n}": I.ema(df["close"], n) for n in lengths}, index=df.index
+    )
+
+
+def ema_cloud(df: pd.DataFrame, length: int = 50) -> pd.DataFrame:
+    """The 50-EMA cloud. **transcribed**::
+
+        cloudSize = ta.stdev(close, threeEmaLength * 2) / 4
+        upper = ema50 + cloudSize
+        lower = ema50 - cloudSize
+
+    Note the stdev window is *double* the EMA length (100 for the 50 EMA) and
+    the quarter divisor -- both are easy to get wrong from memory.
+    """
+    basis = I.ema(df["close"], length)
+    size = I.stdev(df["close"], length * 2) / 4.0
+    return pd.DataFrame(
+        {"basis": basis, "upper": basis + size, "lower": basis - size, "size": size}
+    )
+

```
```diff
warning: in the working copy of 'trading_system/tree_replay/ema.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/ema.py b/trading_system/tree_replay/ema.py
new file mode 100644
index 0000000..62bd637
--- /dev/null
+++ b/trading_system/tree_replay/ema.py
@@ -0,0 +1,114 @@
+"""Closed, available-bar EMA observations; not candidate generation or live parity."""
+
+from dataclasses import asdict
+from datetime import datetime
+import hashlib
+import json
+import math
+
+import numpy as np
+import pandas as pd
+
+from trading_system.tree_spec.snapshot import FeatureDefinition, FeatureObservation, build_snapshot
+from .bars import select_closed_bars
+from ._vendor import tr
+
+
+SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
+ADAPTER_VERSION = "chartdesk-closed-ema-v1"
+
+
+def _time(value):
+    return value.isoformat().replace("+00:00", "Z")
+
+
+def _finite(value):
+    number = float(value)
+    if not math.isfinite(number):
+        raise ValueError("nonfinite numerical EMA result after warmup")
+    return number
+
+
+def ema_snapshot(bars, *, snapshot_id, instrument, timeframe, decision_time,
+                 history_start, max_age_seconds) -> dict:
+    """Use all selected dependencies; missing history never shortens an EMA seed.
+
+    The contiguous closed-bar policy is a research adapter constraint, not a new
+    live trading gate. Per-EMA 2*n warmup comes from features.draw_trend. delta5
+    is its raw slope numerator, NOT its ATR-normalized slope. Inputs require a
+    caller-defined historical anchor and freshness limit; no calendar is guessed.
+    """
+    window = select_closed_bars(bars, instrument=instrument, timeframe=timeframe,
+                                decision_time=decision_time, history_start=history_start,
+                                max_age_seconds=max_age_seconds)
+    serialized = asdict(window)
+    encoded = json.dumps(serialized, sort_keys=True, separators=(",", ":"),
+                         allow_nan=False, default=lambda x: _time(x) if isinstance(x, datetime) else x)
+    window_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
+    source = f"chart-desk@{SOURCE_COMMIT};{ADAPTER_VERSION};window={window_hash}"
+    definitions, observations = [], []
+    periods = []
+    values = {}
+
+    if window.blocker is None:
+        frame = pd.DataFrame({"close": [b.close for b in window.bars]},
+                             index=pd.DatetimeIndex([b.opened_at for b in window.bars]))
+        try:
+            with np.errstate(over="raise", invalid="raise", divide="raise"):
+                averages = tr.emas(frame)
+                for n in tr.TR_EMAS:
+                    if len(frame) >= 2 * n:
+                        current = _finite(averages[f"ema{n}"].iloc[-1])
+                        previous = _finite(averages[f"ema{n}"].iloc[-6])
+                        values[f"ema{n}"] = current
+                        values[f"above_ema{n}"] = bool(frame["close"].iloc[-1] > current)
+                        values[f"ema{n}_delta5"] = _finite(current - previous)
+                        periods.append(n)
+                if periods:
+                    ordered = sorted(periods, key=lambda n: -values[f"ema{n}"])
+                    values["ema_order"] = ">".join(str(n) for n in ordered)
+                    if len(periods) == len(tr.TR_EMAS):
+                        values["ema_stacked"] = ordered in (list(tr.TR_EMAS), list(reversed(tr.TR_EMAS)))
+                if 50 in periods:
+                    cloud = tr.ema_cloud(frame).iloc[-1]
+                    for key in ("basis", "upper", "lower", "size"):
+                        values[f"cloud50_{key}"] = _finite(cloud[key])
+                    close = float(frame["close"].iloc[-1])
+                    values["cloud50_location"] = (
+                        "ABOVE" if close > values["cloud50_upper"] else
+                        "BELOW" if close < values["cloud50_lower"] else "INSIDE"
+                    )
+        except (FloatingPointError, OverflowError) as exc:
+            raise ValueError("numeric overflow in pinned EMA calculation") from exc
+
+    fields = []
+    for n in tr.TR_EMAS:
+        fields.extend([(f"ema{n}", "number", "price"),
+                       (f"above_ema{n}", "boolean", "boolean"),
+                       (f"ema{n}_delta5", "number", "price_change_over_5_bars")])
+    fields += [("ema_order", "category", "descending_period_list"),
+               ("ema_stacked", "boolean", "boolean")]
+    fields += [(f"cloud50_{k}", "number", "price") for k in ("basis", "upper", "lower", "size")]
+    fields.append(("cloud50_location", "category", "relation"))
+    for key, dtype, unit in fields:
+        feature_id = f"chartdesk.{timeframe}.{key}"
+        definitions.append(FeatureDefinition(feature_id, dtype, unit, "PRE_ENTRY", False))
+        if key in values:
+            status, value = "KNOWN", values[key]
+            observed = window.bars[-1].closed_at
+            available = max(b.available_at for b in window.bars)
+        else:
+            status = ("STALE" if window.blocker == "STALE" else
+                      "UNAVAILABLE" if window.blocker else "UNKNOWN")
+            value = None
+            observed = available = window.decision_time
+        observations.append(FeatureObservation(feature_id, value, status, observed, available, source))
+
+    result = build_snapshot(snapshot_id, window.decision_time, definitions, observations).to_payload()
+    return {**result, "instrument": window.instrument, "timeframe": window.timeframe,
+            "window_sha256": window_hash, "window_blocker": window.blocker,
+            "history_start": _time(window.history_start), "max_age_seconds": window.max_age_seconds,
+            "coverage": {"selected_bars": len(window.bars), "available_ema_periods": periods},
+            "calculation": {"source_commit": SOURCE_COMMIT, "adapter_version": ADAPTER_VERSION,
+                            "pandas_version": pd.__version__, "numpy_version": np.__version__},
+            "ready_for_replay": False, "ready_for_training": False}

```
```diff
warning: in the working copy of 'configs/trees/ema-feature-contracts.json', LF will be replaced by CRLF the next time Git touches it
diff --git a/configs/trees/ema-feature-contracts.json b/configs/trees/ema-feature-contracts.json
new file mode 100644
index 0000000..50436bd
--- /dev/null
+++ b/configs/trees/ema-feature-contracts.json
@@ -0,0 +1,46 @@
+{
+  "schema_version": "chartdesk-ema-contracts-v1",
+  "repository": "chart-desk",
+  "commit": "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9",
+  "files": [
+    {
+      "path": "chartdesk/indicators.py",
+      "git_blob_sha1": "672f0428c3a81b86376d4f792ae40ecd174a2025",
+      "vendor_path": "trading_system/tree_replay/_vendor/indicators.py",
+      "symbols": ["_seeded_recursive", "ema", "stdev"],
+      "allowed_imports": "from __future__ import annotations\nimport numpy as np\nimport pandas as pd"
+    },
+    {
+      "path": "chartdesk/tr.py",
+      "git_blob_sha1": "8297c712d20404880d4d8949e96efbf48613909c",
+      "vendor_path": "trading_system/tree_replay/_vendor/tr.py",
+      "symbols": ["TR_EMAS", "emas", "ema_cloud"],
+      "allowed_imports": "from __future__ import annotations\nimport pandas as pd\nfrom . import indicators as I"
+    },
+    {
+      "path": "chartdesk/features.py",
+      "git_blob_sha1": "ba37083e54b2e37ca745fd4a51a63ca39c90d9b4",
+      "vendor_path": null,
+      "symbols": [],
+      "allowed_imports": ""
+    }
+  ],
+  "consumer": {"path": "chartdesk/features.py", "function": "draw_trend", "line_start": 156, "line_end": 265, "role": "observational_drawer_not_entry_gate"},
+  "observations": [
+    {"suffix": "ema<n>", "source": "tr.emas; draw_trend T1", "periods": [5,13,50,200,800], "unit": "price", "minimum_bars": "2*n"},
+    {"suffix": "above_ema<n>", "source": "draw_trend T2", "formula": "close > ema[n]; equality is false", "unit": "boolean", "minimum_bars": "2*n"},
+    {"suffix": "ema<n>_delta5", "source": "draw_trend T3 numerator only", "formula": "ema[n][-1] - ema[n][-6]", "unit": "price_change_over_5_bars", "minimum_bars": "2*n"},
+    {"suffix": "ema_order", "source": "draw_trend T5", "formula": "stable descending value sort of supported EMA periods", "unit": "descending_period_list", "minimum_bars": 10},
+    {"suffix": "ema_stacked", "source": "draw_trend T5", "formula": "all periods supported and sorted order equals periods or reversed periods; ties retain stable order", "unit": "boolean", "minimum_bars": 1600},
+    {"suffix": "cloud50_<basis|upper|lower|size>", "source": "tr.ema_cloud; draw_trend T9", "formula": "SMA-seeded EMA50 +/- population_stdev(close,100)/4", "unit": "price", "minimum_bars": 100},
+    {"suffix": "cloud50_location", "source": "draw_trend T9", "formula": "close>upper ABOVE; close<lower BELOW; otherwise INSIDE", "unit": "relation", "minimum_bars": 100}
+  ],
+  "timeframes": ["5m", "15m", "30m", "1h", "4h"],
+  "limitations": [
+    "Closed available bars within an explicit contiguous history only; no live unfinished-bar parity or calendar inference.",
+    "Delta5 is the T3 numerator, not ATR-normalized slope. ATR, compression, levels, vectors and candidate producers remain outside this slice.",
+    "These are optional observations, not vetoes or trade-selection rules.",
+    "Source bodies and consumer mapping do not certify a complete historical replay or actual deployment.",
+    "Neither snapshot eligibility nor source subset identity is training readiness."
+  ]
+}

```
```diff
warning: in the working copy of 'tests/tree_replay/test_bars.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_bars.py b/tests/tree_replay/test_bars.py
new file mode 100644
index 0000000..541d10d
--- /dev/null
+++ b/tests/tree_replay/test_bars.py
@@ -0,0 +1,328 @@
+"""Synthetic boundary scenarios; no market data or source-repository imports."""
+
+from dataclasses import FrozenInstanceError, fields, replace
+from datetime import datetime, timedelta, timezone
+from decimal import Decimal
+from fractions import Fraction
+from zoneinfo import ZoneInfo
+
+import pytest
+import pandas as pd
+
+
+START = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
+
+
+@pytest.fixture
+def api():
+    import trading_system.tree_replay.bars as bars
+
+    return bars
+
+
+def make_bar(api, minute=0, **changes):
+    values = dict(
+        instrument="SYNTH:TEST", timeframe="5m",
+        opened_at=START + timedelta(minutes=minute),
+        closed_at=START + timedelta(minutes=minute + 5),
+        available_at=START + timedelta(minutes=minute + 5),
+        open=100, high=103, low=99, close=102, volume=None,
+        source="synthetic:fixture",
+    )
+    values.update(changes)
+    return api.ClosedBar(**values)
+
+
+def select(api, bars=(), **changes):
+    request = dict(
+        instrument="SYNTH:TEST", timeframe="5m", history_start=START,
+        decision_time=START + timedelta(minutes=10), max_age_seconds=300,
+    )
+    request.update(changes)
+    return api.select_closed_bars(bars, **request)
+
+
+def test_closed_bar_retains_missing_volume_and_normalizes_native_prices(api):
+    bar = make_bar(api)
+    assert (bar.open, bar.high, bar.low, bar.close) == (100.0, 103.0, 99.0, 102.0)
+    assert all(type(getattr(bar, name)) is float for name in ("open", "high", "low", "close"))
+    assert bar.volume is None
+
+
+@pytest.mark.parametrize("volume", [0, 0.0, 12, 12.5])
+def test_finite_nonnegative_volume_is_preserved(api, volume):
+    assert make_bar(api, volume=volume).volume == volume
+
+
+@pytest.mark.parametrize("field", ["open", "high", "low", "close", "volume"])
+@pytest.mark.parametrize("value", [True, False, "100", [], {}, Decimal("100"), Fraction(100), float("nan"), float("inf"), -float("inf"), 10**400])
+def test_invalid_numeric_values_are_rejected(api, field, value):
+    with pytest.raises(ValueError):
+        make_bar(api, **{field: value})
+
+
+@pytest.mark.parametrize("field", ["open", "high", "low", "close"])
+@pytest.mark.parametrize("value", [None, 0, -1])
+def test_prices_must_be_positive(api, field, value):
+    with pytest.raises(ValueError):
+        make_bar(api, **{field: value})
+
+
+def test_negative_volume_is_rejected(api):
+    with pytest.raises(ValueError):
+        make_bar(api, volume=-0.1)
+
+
+@pytest.mark.parametrize("changes", [{"open": 104}, {"open": 98}, {"close": 104}, {"close": 98}, {"low": 104}, {"high": 98}])
+def test_ohlc_geometry_is_validated(api, changes):
+    with pytest.raises(ValueError):
+        make_bar(api, **changes)
+
+
+def test_flat_bar_and_boundary_prices_are_valid(api):
+    assert make_bar(api, open=100, high=100, low=100, close=100).close == 100.0
+    assert make_bar(api, open=99, close=103).close == 103.0
+
+
+@pytest.mark.parametrize("field,values", [
+    ("instrument", [None, 123, "", "TEST", ":TEST", "SYNTH:", "SYNTH:TEST:X", " SYNTH:TEST", "SYNTH:TEST ", "SYN TH:TEST", "SYNTH:TE\tST", "SYNTH:\u00a0TEST"]),
+    ("timeframe", [None, 5, [], "", "1m", "1d", "60m", "5M", " 5m"]),
+    ("source", [None, 123, "", " \t", " fixture", "fixture "]),
+])
+def test_invalid_bar_metadata_is_rejected(api, field, values):
+    for value in values:
+        with pytest.raises(ValueError):
+            make_bar(api, **{field: value})
+
+
+@pytest.mark.parametrize("frame,minutes", [("5m", 5), ("15m", 15), ("30m", 30), ("1h", 60), ("4h", 240)])
+def test_supported_frames_require_exact_elapsed_duration(api, frame, minutes):
+    close = START + timedelta(minutes=minutes)
+    bar = make_bar(api, timeframe=frame, closed_at=close, available_at=close)
+    assert select(api, [bar], timeframe=frame, decision_time=close).blocker is None
+    for delta in (-1, 1):
+        with pytest.raises(ValueError):
+            replace(bar, closed_at=close + timedelta(microseconds=delta), available_at=close + timedelta(seconds=1))
+
+
+@pytest.mark.parametrize("field", ["opened_at", "closed_at", "available_at"])
+@pytest.mark.parametrize("value", [None, "2026-09-09T12:00:00Z", START.replace(tzinfo=None)])
+def test_bar_times_must_be_aware_datetimes(api, field, value):
+    with pytest.raises(ValueError):
+        make_bar(api, **{field: value})
+
+
+def test_availability_cannot_precede_close(api):
+    with pytest.raises(ValueError):
+        make_bar(api, available_at=START + timedelta(minutes=5, microseconds=-1))
+
+
+def test_utc_normalization_precedes_dst_fold_duration_and_order_checks(api):
+    ny = ZoneInfo("America/New_York")
+    bar = make_bar(
+        api, opened_at=datetime(2026, 11, 1, 1, 55, tzinfo=ny, fold=0),
+        closed_at=datetime(2026, 11, 1, 1, 0, tzinfo=ny, fold=1),
+        available_at=datetime(2026, 11, 1, 1, 1, tzinfo=ny, fold=1),
+    )
+    assert bar.opened_at == datetime(2026, 11, 1, 5, 55, tzinfo=timezone.utc)
+    assert bar.closed_at == datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc)
+    assert bar.available_at == datetime(2026, 11, 1, 6, 1, tzinfo=timezone.utc)
+    assert all(getattr(bar, name).tzinfo is timezone.utc for name in ("opened_at", "closed_at", "available_at"))
+    window = select(api, [bar], history_start=datetime(2026, 11, 1, 1, 55, tzinfo=ny, fold=0), decision_time=datetime(2026, 11, 1, 1, 1, tzinfo=ny, fold=1))
+    assert window.blocker is None
+    assert window.history_start.tzinfo is timezone.utc
+    assert window.decision_time == datetime(2026, 11, 1, 6, 1, tzinfo=timezone.utc)
+    with pytest.raises(ValueError):
+        replace(bar, available_at=datetime(2026, 11, 1, 1, 59, tzinfo=ny, fold=0))
+
+
+@pytest.mark.parametrize("minute,microseconds,expected_count,blocker", [(10, 0, 1, None), (10, 1, 1, "STALE"), (11, 0, 2, None)])
+def test_literal_delayed_bar_and_exact_freshness_boundary(api, minute, microseconds, expected_count, blocker):
+    first = make_bar(api)
+    delayed = make_bar(api, 5, available_at=START + timedelta(minutes=11))
+    window = select(api, [first, delayed], decision_time=START + timedelta(minutes=minute, microseconds=microseconds))
+    assert window.bars == (first, delayed)[:expected_count]
+    assert window.blocker == blocker
+
+
+def test_future_close_and_availability_are_excluded_and_equality_is_included(api):
+    first, second = make_bar(api), make_bar(api, 5)
+    future_close = make_bar(api, 10)
+    assert select(api, [first, second, future_close]).bars == (first, second)
+    assert select(api, [first], decision_time=first.closed_at).bars == (first,)
+    assert select(api, [second], decision_time=second.closed_at - timedelta(microseconds=1)).blocker == "NO_HISTORY"
+
+
+def test_history_start_excludes_older_bars_without_mutating_caller_order(api):
+    first, second, older = make_bar(api), make_bar(api, 5), make_bar(api, -5)
+    inputs = [second, older, first]
+    window = select(api, inputs)
+    assert window.bars == (first, second)
+    assert inputs == [second, older, first]
+    inputs.clear()
+    assert window.bars == (first, second)
+    assert window.instrument == "SYNTH:TEST"
+    assert window.timeframe == "5m"
+    assert window.max_age_seconds == 300
+    assert window.blocker is None
+
+
+def test_generator_input_is_sorted_deterministically(api):
+    first, second = make_bar(api), make_bar(api, 5)
+    assert select(api, (bar for bar in [second, first])) == select(api, [first, second])
+
+
+@pytest.mark.parametrize("kind", ["empty", "old", "future", "delayed"])
+def test_no_eligible_bars_means_no_history(api, kind):
+    inputs = {"empty": [], "old": [make_bar(api, -5)], "future": [make_bar(api, 10)], "delayed": [make_bar(api, available_at=START + timedelta(hours=1))]}
+    window = select(api, inputs[kind])
+    assert window.bars == ()
+    assert window.blocker == "NO_HISTORY"
+
+
+def test_missing_anchor_precedes_gap_and_staleness(api):
+    assert select(api, [make_bar(api, 5), make_bar(api, 15)], decision_time=START + timedelta(hours=1)).blocker == "HISTORY_INCOMPLETE"
+
+
+def test_history_start_inside_bar_does_not_round_to_next_open(api):
+    assert select(api, [make_bar(api), make_bar(api, 5)], history_start=START + timedelta(seconds=1)).blocker == "HISTORY_INCOMPLETE"
+
+
+@pytest.mark.parametrize("second_minute", [4, 10, 2880])
+def test_gap_overlap_and_weekend_are_not_compressed_and_precede_staleness(api, second_minute):
+    first, second = make_bar(api), make_bar(api, second_minute)
+    window = select(api, [first, second], decision_time=START + timedelta(days=3))
+    assert window.bars == (first, second)
+    assert window.blocker == "HISTORY_GAP"
+
+
+def test_delayed_interior_bar_blocks_until_it_is_available(api):
+    first, middle, last = make_bar(api), make_bar(api, 5, available_at=START + timedelta(minutes=20)), make_bar(api, 10)
+    assert select(api, [first, middle, last], decision_time=START + timedelta(minutes=15)).blocker == "HISTORY_GAP"
+    recovered = select(api, [first, middle, last], decision_time=START + timedelta(minutes=20))
+    assert recovered.bars == (first, middle, last)
+    assert recovered.blocker is None
+
+
+@pytest.mark.parametrize("field,value", [("instrument", "synth:TEST"), ("instrument", "OTHER:TEST"), ("timeframe", "15m")])
+def test_exact_identity_mismatch_is_rejected_even_outside_window(api, field, value):
+    bar = make_bar(api, -5)
+    with pytest.raises(ValueError):
+        select(api, [bar], **{field: value})
+
+
+@pytest.mark.parametrize("revision", [False, True])
+@pytest.mark.parametrize("minute", [-5, 0, 10])
+def test_duplicate_opens_and_revisions_are_rejected_before_filtering(api, revision, minute):
+    bar = make_bar(api, minute)
+    other = replace(bar, close=101, source="synthetic:revision", available_at=START + timedelta(days=1)) if revision else bar
+    with pytest.raises(ValueError):
+        select(api, [bar, other])
+
+
+def test_same_instant_in_different_timezones_is_duplicate(api):
+    first = make_bar(api)
+    other = replace(first, opened_at=first.opened_at.astimezone(timezone(timedelta(hours=3))))
+    with pytest.raises(ValueError):
+        select(api, [first, other])
+
+
+@pytest.mark.parametrize("value", [None, {}, "bar", 1, True, object()])
+def test_selector_rejects_non_closed_bar_items(api, value):
+    with pytest.raises(ValueError):
+        select(api, [value])
+
+
+@pytest.mark.parametrize("field,values", [
+    ("instrument", [None, "", "TEST", "SYNTH: TEST", "SYNTH:TEST:EXTRA"]),
+    ("timeframe", [None, [], "1m", "60m", " 5m"]),
+    ("history_start", [None, "2026-09-09", START.replace(tzinfo=None), START + timedelta(hours=1)]),
+    ("decision_time", [None, "2026-09-09", START.replace(tzinfo=None)]),
+    ("max_age_seconds", [None, True, False, 0, -1, 300.0, "300", Decimal(300)]),
+])
+def test_request_validation_applies_even_when_input_is_empty(api, field, values):
+    for value in values:
+        with pytest.raises(ValueError):
+            select(api, **{field: value})
+
+
+def test_freshness_is_explicit_and_has_no_arbitrary_upper_bound(api):
+    assert select(api, [make_bar(api)], max_age_seconds=10**100).blocker is None
+    with pytest.raises(TypeError):
+        api.select_closed_bars([], instrument="SYNTH:TEST", timeframe="5m", decision_time=START, history_start=START)
+
+
+def test_contracts_are_frozen_keyword_only_and_require_all_fields(api):
+    bar = make_bar(api)
+    window = select(api, [bar])
+    for record in (bar, window):
+        with pytest.raises(FrozenInstanceError):
+            record.instrument = "OTHER:TEST"
+        values = {field.name: getattr(record, field.name) for field in fields(record)}
+        with pytest.raises(TypeError):
+            type(record)(*values.values())
+        for missing in values:
+            with pytest.raises(TypeError):
+                type(record)(**{name: value for name, value in values.items() if name != missing})
+
+
+def test_one_nanosecond_past_freshness_boundary_is_rejected_not_rounded(api):
+    last = make_bar(api)
+    decision_time = pd.Timestamp(last.closed_at) + pd.Timedelta(seconds=300, nanoseconds=1)
+    with pytest.raises(ValueError, match="microsecond"):
+        select(api, [last], decision_time=decision_time, max_age_seconds=300)
+
+
+@pytest.mark.parametrize("field", ["opened_at", "closed_at", "available_at"])
+@pytest.mark.parametrize("nanoseconds", [-1, 1, 999])
+def test_bar_timestamp_submicrosecond_remainders_are_rejected(api, field, nanoseconds):
+    bar = make_bar(api)
+    unaligned = pd.Timestamp(getattr(bar, field)) + pd.Timedelta(nanoseconds=nanoseconds)
+    with pytest.raises(ValueError, match="microsecond"):
+        replace(bar, **{field: unaligned})
+
+
+@pytest.mark.parametrize("field", ["decision_time", "history_start"])
+@pytest.mark.parametrize("nanoseconds", [-1, 1, 999])
+def test_request_timestamp_submicrosecond_remainders_are_rejected(api, field, nanoseconds):
+    unaligned = pd.Timestamp(START) + pd.Timedelta(nanoseconds=nanoseconds)
+    with pytest.raises(ValueError, match="microsecond"):
+        select(api, **{field: unaligned})
+
+
+def test_equal_submicrosecond_offsets_cannot_hide_in_exact_bar_duration(api):
+    offset = pd.Timedelta(nanoseconds=1)
+    with pytest.raises(ValueError, match="microsecond"):
+        make_bar(
+            api, opened_at=pd.Timestamp(START) + offset,
+            closed_at=pd.Timestamp(START) + pd.Timedelta(minutes=5) + offset,
+            available_at=pd.Timestamp(START) + pd.Timedelta(minutes=5) + offset,
+        )
+
+
+@pytest.mark.parametrize("timestamp_class", [pd.Timestamp, type("ResearchDatetime", (datetime,), {})])
+@pytest.mark.parametrize("zone", [timezone.utc, timezone(timedelta(hours=3)), ZoneInfo("America/New_York")])
+def test_aligned_datetime_subclasses_become_native_utc_without_losing_fields(api, timestamp_class, zone):
+    opened = datetime(2026, 11, 1, 5, 55, 17, 123456, tzinfo=timezone.utc)
+    closed = datetime(2026, 11, 1, 6, 0, 17, 123456, tzinfo=timezone.utc)
+    available = datetime(2026, 11, 1, 6, 1, 18, 654321, tzinfo=timezone.utc)
+
+    def as_subclass(value):
+        local = value.astimezone(zone)
+        return timestamp_class(
+            year=local.year, month=local.month, day=local.day,
+            hour=local.hour, minute=local.minute, second=local.second,
+            microsecond=local.microsecond, tzinfo=zone, fold=local.fold,
+        )
+
+    bar = make_bar(api, opened_at=as_subclass(opened), closed_at=as_subclass(closed), available_at=as_subclass(available))
+    window = select(api, [bar], history_start=as_subclass(opened), decision_time=as_subclass(available))
+    assert window.blocker is None
+    for actual, expected in (
+        (bar.opened_at, opened), (bar.closed_at, closed),
+        (bar.available_at, available), (window.history_start, opened),
+        (window.decision_time, available),
+    ):
+        assert actual == expected
+        assert actual.tzinfo is timezone.utc
+        assert type(actual) is datetime

```
```diff
warning: in the working copy of 'tests/tree_replay/test_ema.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_ema.py b/tests/tree_replay/test_ema.py
new file mode 100644
index 0000000..91c8021
--- /dev/null
+++ b/tests/tree_replay/test_ema.py
@@ -0,0 +1,260 @@
+"""Synthetic bars and hand-derived numbers; no market feed or live source imports."""
+
+from dataclasses import replace
+from datetime import datetime, timedelta, timezone
+import json
+import hashlib
+import math
+from pathlib import Path
+import subprocess
+import sys
+
+import pandas as pd
+import pytest
+
+
+START = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)
+ROOT = Path(__file__).resolve().parents[2]
+MINUTES = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}
+
+
+def make_bars(closes, tf="5m"):
+    from trading_system.tree_replay.bars import ClosedBar
+    step = timedelta(minutes=MINUTES[tf])
+    return tuple(ClosedBar(
+        instrument="SYNTH:TEST", timeframe=tf, opened_at=START + i * step,
+        closed_at=START + (i + 1) * step, available_at=START + (i + 1) * step,
+        open=float(c), high=float(c) + 1, low=max(float(c) - 1, 0.5),
+        close=float(c), volume=None, source="synthetic closes",
+    ) for i, c in enumerate(closes))
+
+
+def report(bars, **kwargs):
+    from trading_system.tree_replay.ema import ema_snapshot
+    params = dict(snapshot_id="synthetic-snapshot", instrument="SYNTH:TEST",
+                  timeframe="5m", decision_time=bars[-1].closed_at if bars else START,
+                  history_start=START, max_age_seconds=300)
+    return ema_snapshot(bars, **(params | kwargs))
+
+
+def test_pinned_ema_uses_full_sma_seed_not_first_price():
+    from trading_system.tree_replay._vendor import indicators
+    result = indicators.ema(pd.Series(range(1, 11)), 5)
+    assert result.iloc[:4].isna().all()
+    assert result.iloc[4] == 3.0
+    assert result.iloc[-1] == pytest.approx(8.0)
+
+
+def test_pinned_cloud_uses_population_stdev_and_double_window():
+    from trading_system.tree_replay._vendor import tr
+    cloud = tr.ema_cloud(pd.DataFrame({"close": range(1, 101)}))
+    assert cloud["size"].iloc[:99].isna().all()
+    assert cloud["basis"].iloc[-1] == pytest.approx(75.5)
+    assert cloud["size"].iloc[-1] == pytest.approx(math.sqrt(833.25) / 4)
+
+
+@pytest.mark.parametrize("tf", MINUTES)
+def test_each_timeframe_exports_raw_numbers_and_partial_warmup(tf):
+    r = report(make_bars(range(1, 11), tf), timeframe=tf)
+    p = f"chartdesk.{tf}."
+    assert r["features"][p + "ema5"] == pytest.approx(8)
+    assert r["features"][p + "ema5_delta5"] == pytest.approx(5)
+    assert r["features"][p + "above_ema5"] is True
+    assert r["features"][p + "ema_order"] == "5"
+    assert r["features"][p + "ema13"] is None
+    assert r["availability"][p + "ema13"] == "UNKNOWN"
+    assert r["coverage"]["available_ema_periods"] == [5]
+    assert r["ready_for_replay"] is False
+    assert r["ready_for_training"] is False
+
+
+def test_source_drawer_warmup_requires_twice_length():
+    r = report(make_bars(range(1, 10)))
+    assert r["features"]["chartdesk.5m.ema5"] is None
+    assert r["availability"]["chartdesk.5m.ema5"] == "UNKNOWN"
+
+
+@pytest.mark.parametrize("falling,order", [(False, "5>13>50>200>800"), (True, "800>200>50>13>5")])
+def test_full_ema_order_preserves_both_directions(falling, order):
+    closes = [2000 - i if falling else i + 1 for i in range(1600)]
+    r = report(make_bars(closes))
+    assert r["features"]["chartdesk.5m.ema_order"] == order
+    assert r["features"]["chartdesk.5m.ema_stacked"] is True
+    assert r["coverage"]["available_ema_periods"] == [5, 13, 50, 200, 800]
+
+
+def test_equal_values_preserve_zero_false_and_source_stable_tie_order():
+    # Power-of-two price gives exact tied recursions; decimal 100 accumulates
+    # a tiny EMA200 rounding difference in the pinned implementation.
+    r = report(make_bars([128] * 1600))
+    f = r["features"]
+    assert f["chartdesk.5m.ema5_delta5"] == 0
+    assert f["chartdesk.5m.above_ema5"] is False
+    assert f["chartdesk.5m.cloud50_size"] == 0
+    assert f["chartdesk.5m.cloud50_location"] == "INSIDE"
+    assert f["chartdesk.5m.ema_order"] == "5>13>50>200>800"
+    # This is the source's stable-sort behavior, not proof of strict alignment.
+    assert f["chartdesk.5m.ema_stacked"] is True
+
+
+def test_mixed_order_is_not_reported_as_full_alignment():
+    r = report(make_bars(list(range(1, 1600)) + [1550]))
+    assert r["features"]["chartdesk.5m.ema_order"] == "13>5>50>200>800"
+    assert r["features"]["chartdesk.5m.ema_stacked"] is False
+
+
+def test_source_floating_precision_is_not_silently_rounded_before_sorting():
+    r = report(make_bars([100] * 1600))
+    assert r["features"]["chartdesk.5m.ema200"] > r["features"]["chartdesk.5m.ema5"]
+    assert r["features"]["chartdesk.5m.ema_order"] == "200>5>13>50>800"
+    assert r["features"]["chartdesk.5m.ema_stacked"] is False
+
+
+@pytest.mark.parametrize("closes,location", [(list(range(1, 101)), "ABOVE"), (list(range(200, 100, -1)), "BELOW")])
+def test_cloud_relationship_and_numeric_width(closes, location):
+    r = report(make_bars(closes))
+    assert r["features"]["chartdesk.5m.cloud50_location"] == location
+    assert r["features"]["chartdesk.5m.cloud50_size"] == pytest.approx(math.sqrt(833.25) / 4)
+
+
+def test_future_suffix_and_unavailable_final_close_cannot_change_snapshot():
+    bars = make_bars(range(1, 102))
+    decision = bars[99].closed_at
+    original = report(bars[:100], decision_time=decision)
+    future = replace(bars[100], close=1e8, high=1e8, open=1e8)
+    assert report(bars[:100] + (future,), decision_time=decision) == original
+    late = replace(bars[99], available_at=decision + timedelta(minutes=2))
+    assert report(bars[:99] + (late,), decision_time=decision) == report(bars[:99], decision_time=decision)
+
+
+def test_earlier_late_dependency_controls_feature_availability():
+    bars = list(make_bars(range(1, 101)))
+    decision = bars[-1].closed_at + timedelta(seconds=2)
+    bars[0] = replace(bars[0], available_at=decision)
+    r = report(bars, decision_time=decision)
+    prov = r["provenance"]["chartdesk.5m.ema5"]
+    assert prov["observed_at"] == "2026-09-08T20:20:00Z"
+    assert prov["available_at"] == "2026-09-08T20:20:02Z"
+
+
+@pytest.mark.parametrize("case,blocker,status", [
+    ("empty", "NO_HISTORY", "UNAVAILABLE"),
+    ("gap", "HISTORY_GAP", "UNAVAILABLE"),
+    ("head", "HISTORY_INCOMPLETE", "UNAVAILABLE"),
+    ("stale", "STALE", "STALE"),
+])
+def test_bad_history_is_not_a_compressed_or_zero_feature(case, blocker, status):
+    bars = make_bars(range(1, 101))
+    decision = bars[-1].closed_at
+    if case == "empty":
+        bars = ()
+    elif case == "gap":
+        bars = bars[:40] + bars[41:]
+    elif case == "head":
+        bars = bars[1:]
+    else:
+        decision += timedelta(seconds=301)
+    r = report(bars, decision_time=decision)
+    assert r["window_blocker"] == blocker
+    assert set(r["availability"].values()) == {status}
+    assert all(v is None for v in r["features"].values())
+
+
+def test_payload_has_independent_provenance_and_is_copy_safe():
+    bars = make_bars(range(1, 101))
+    original = report(bars)
+    other = report(bars)
+    other["features"]["chartdesk.5m.ema5"] = -10
+    assert report(bars) == original
+    assert bars[0].close == 1
+    assert original["calculation"]["source_commit"] == "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
+    assert all(p["phase"] == "PRE_ENTRY" and not p["required"] for p in original["provenance"].values())
+    assert len(original["window_sha256"]) == 64
+    revised = list(bars)
+    revised[0] = replace(revised[0], source="different explicit source")
+    assert report(revised)["window_sha256"] != original["window_sha256"]
+    json.dumps(original, allow_nan=False)
+
+
+def test_extreme_numerical_overflow_is_not_reported_as_warmup():
+    with pytest.raises(ValueError, match="finite|overflow|numeric"):
+        report(make_bars([1e308] * 100))
+
+
+def test_parity_cli_missing_source_fails_closed(tmp_path):
+    r = subprocess.run([sys.executable, str(ROOT / "tools/check_ema_source_parity.py"),
+                        "--source-root", str(tmp_path)], capture_output=True, text=True)
+    assert r.returncode == 2
+    result = json.loads(r.stdout)
+    assert result["source_subset_verified"] is False
+    assert result["ready_for_replay"] is False
+
+
+@pytest.fixture
+def parity_fixture(tmp_path, monkeypatch):
+    # Small real source/vendor files exercise the verifier, not a mocked AST.
+    from tools import check_ema_source_parity as checker
+    source = "def ema(x):\n    return x * 2\n"
+    src = tmp_path / "source"
+    src.mkdir()
+    (src / "calc.py").write_text(source, encoding="utf-8")
+    vendor = tmp_path / "copied.py"
+    vendor.write_text(source, encoding="utf-8")
+    config = tmp_path / "configs/trees"
+    config.mkdir(parents=True)
+    (config / "existing-alerts-baseline.json").write_text(json.dumps({
+        "repositories": [{"name": "chart-desk", "commit": "1" * 40}]
+    }), encoding="utf-8")
+    data = source.encode()
+    contract = tmp_path / "fixture-contract.json"
+    contract.write_text(json.dumps({"commit": "1" * 40, "files": [{
+        "path": "calc.py", "git_blob_sha1": hashlib.sha1(b"blob 29\0" + data).hexdigest(),
+        "vendor_path": "copied.py", "symbols": ["ema"], "allowed_imports": ""
+    }]}), encoding="utf-8")
+    assert len(data) == 29  # Hand-counted source bytes for the Git blob fixture.
+    monkeypatch.setattr(checker, "ROOT", tmp_path)
+    monkeypatch.setattr(checker, "CONTRACT", contract)
+    return checker, src, vendor
+
+
+def test_source_parity_accepts_identical_subset_without_executing_it(parity_fixture):
+    checker, src, _ = parity_fixture
+    assert checker.check_source_parity(src)["source_subset_verified"] is True
+
+
+@pytest.mark.parametrize("case,prefix", [
+    ("source", "SOURCE_BLOB_MISMATCH"), ("body", "FUNCTION_MISMATCH"),
+    ("import", "IMPORT_MISMATCH"), ("top", "UNEXPECTED_TOP_LEVEL"),
+    ("duplicate", "SYMBOL_SET_MISMATCH"), ("missing", "SOURCE_UNREADABLE"),
+])
+def test_source_parity_blocks_changed_source_or_vendor(parity_fixture, case, prefix):
+    checker, src, vendor = parity_fixture
+    if case == "source":
+        (src / "calc.py").write_text("def ema(x):\n    return x * 3\n", encoding="utf-8")
+    elif case == "missing":
+        src = src / "not-present"
+    else:
+        text = vendor.read_text(encoding="utf-8")
+        if case == "body":
+            text = text.replace("* 2", "* 3")
+        elif case == "import":
+            text = "import os\n" + text
+        elif case == "top":
+            text += "raise RuntimeError('must never execute')\n"
+        else:
+            text += text
+        vendor.write_text(text, encoding="utf-8")
+    r = checker.check_source_parity(src)
+    assert r["source_subset_verified"] is False
+    assert any(b.startswith(prefix) for b in r["blockers"])
+
+
+def test_parity_cli_invalid_contract_reports_no_readiness(parity_fixture, monkeypatch, capsys):
+    checker, src, _ = parity_fixture
+    checker.CONTRACT.write_text("{broken", encoding="utf-8")
+    monkeypatch.setattr(sys, "argv", ["check_ema_source_parity", "--source-root", str(src)])
+    assert checker.main() == 1
+    result = json.loads(capsys.readouterr().out)
+    assert result["source_subset_verified"] is False
+    assert result["ready_for_replay"] is False
+    assert result["ready_for_training"] is False

```
```diff
warning: in the working copy of 'tools/check_ema_source_parity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tools/check_ema_source_parity.py b/tools/check_ema_source_parity.py
new file mode 100644
index 0000000..ebb8e7a
--- /dev/null
+++ b/tools/check_ema_source_parity.py
@@ -0,0 +1,85 @@
+"""Verify the audited EMA subset against pinned source text; never import that repo."""
+
+import argparse
+import ast
+import hashlib
+import json
+from pathlib import Path
+
+
+ROOT = Path(__file__).resolve().parents[1]
+CONTRACT = ROOT / "configs/trees/ema-feature-contracts.json"
+
+
+def _name(node):
+    if isinstance(node, ast.FunctionDef):
+        return node.name
+    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
+        return node.target.id
+    return None
+
+
+def _dump(node):
+    return ast.dump(node, include_attributes=False)
+
+
+def check_source_parity(source_root: Path) -> dict:
+    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
+    baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
+    pin = next(row["commit"] for row in baseline["repositories"] if row["name"] == "chart-desk")
+    blockers = []
+    if contract["commit"] != pin:
+        blockers.append("CONTRACT_COMMIT_MISMATCH")
+    for row in contract["files"]:
+        try:
+            # read_text normalizes checkout CRLF; Git blob identity is computed
+            # against the canonical LF text, including its final newline.
+            source = (Path(source_root) / row["path"]).read_text(encoding="utf-8")
+            data = source.encode("utf-8")
+            blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
+            if blob != row["git_blob_sha1"]:
+                blockers.append(f"SOURCE_BLOB_MISMATCH:{row['path']}")
+                continue
+            if row["vendor_path"] is None:
+                continue
+            original = ast.parse(source)
+            vendor = ast.parse((ROOT / row["vendor_path"]).read_text(encoding="utf-8"))
+            symbols = set(row["symbols"])
+            originals = {name: node for node in original.body if (name := _name(node)) in symbols}
+            copied = [node for node in vendor.body if _name(node) in symbols]
+            if len(copied) != len(symbols) or {_name(n) for n in copied} != symbols:
+                blockers.append(f"SYMBOL_SET_MISMATCH:{row['vendor_path']}")
+            for node in copied:
+                if _name(node) not in originals or _dump(node) != _dump(originals[_name(node)]):
+                    blockers.append(f"FUNCTION_MISMATCH:{row['path']}:{_name(node)}")
+            allowed_imports = {_dump(n) for n in ast.parse(row["allowed_imports"]).body}
+            actual_imports = {_dump(n) for n in vendor.body if isinstance(n, (ast.Import, ast.ImportFrom))}
+            if allowed_imports != actual_imports:
+                blockers.append(f"IMPORT_MISMATCH:{row['vendor_path']}")
+            for node in vendor.body:
+                if (_name(node) in symbols or isinstance(node, (ast.Import, ast.ImportFrom)) or
+                    isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
+                    continue
+                blockers.append(f"UNEXPECTED_TOP_LEVEL:{row['vendor_path']}")
+        except (OSError, ValueError, SyntaxError) as exc:
+            blockers.append(f"SOURCE_UNREADABLE:{row['path']}:{type(exc).__name__}")
+    return {"source_commit": pin, "source_subset_verified": not blockers,
+            "blockers": blockers, "ready_for_replay": False, "ready_for_training": False}
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--source-root", type=Path, required=True, help="Pinned chart-desk checkout")
+    args = parser.parse_args()
+    try:
+        report = check_source_parity(args.source_root)
+    except (OSError, ValueError, KeyError, StopIteration) as exc:
+        print(json.dumps({"error": str(exc), "source_subset_verified": False,
+                          "ready_for_replay": False, "ready_for_training": False}))
+        return 1
+    print(json.dumps(report, sort_keys=True, indent=2))
+    return 0 if report["source_subset_verified"] else 2
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())

```
```diff
warning: in the working copy of 'docs/architecture/ASOF-EMA-ADAPTER-USAGE.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/docs/architecture/ASOF-EMA-ADAPTER-USAGE.md b/docs/architecture/ASOF-EMA-ADAPTER-USAGE.md
new file mode 100644
index 0000000..4818f13
--- /dev/null
+++ b/docs/architecture/ASOF-EMA-ADAPTER-USAGE.md
@@ -0,0 +1,129 @@
+# Historical EMA observation adapter
+
+This is an offline calculation slice of the approved tree-learning plan. It
+does not create trade candidates, simulate fills, label market trades or train
+a model. The existing live alert system is unchanged.
+
+Implementation plan: `docs/superpowers/plans/2026-09-09-asof-ema-adapter.md`.
+Source/consumer mapping: `configs/trees/ema-feature-contracts.json`.
+
+## What is reused
+
+Pure function bodies from chart-desk commit
+`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` are preserved in
+`trading_system/tree_replay/_vendor/`. Only numpy/pandas and the local pure
+subset are imported. The live desk package is not imported or executed.
+
+- EMA5/13/50/200/800 use the original full-window SMA seed and recursion.
+- EMA50 cloud uses population stdev of the last100 closes divided by4.
+- Observation availability follows `features.draw_trend`: each EMA requires
+  twice its period in history, not merely a computable seed.
+- Exported `ema<n>_delta5` is the signed five-bar difference, the numerator of
+  source T3. It is NOT the original ATR-normalized slope. ATR, fan width,
+  compression, vectors, levels and the remaining drawer fields are not covered.
+- Price-above, descending EMA order, full-fan stacked status and cloud location
+  preserve source comparisons. Equal cloud boundaries count as INSIDE; equality
+  with an EMA is not above. Tied EMAs retain stable period order.
+
+No rounding is introduced. The source's floating-point effects remain: a constant
+price100 can give EMA200=100.0000000000001 and therefore a different sorted order.
+An exact power-of-two constant128 provides a genuinely tied synthetic fixture.
+Neither stacked status nor any other observation is an entry rule here.
+
+## Input boundary
+
+Supply `ClosedBar` objects from `trading_system.tree_replay.bars` with all required
+fields: exact venue:symbol, timeframe, opening/closing/availability timestamps,
+OHLC, volume (explicit None permitted), and source identity. Values must be finite
+native int/float; OHLC positive with valid geometry. None volume is not zero.
+
+Supported fixed durations are5m,15m,30m,1h,4h. Timestamps are normalized to native
+UTC datetime. Aligned datetime subclasses are accepted; sub-microsecond timestamps
+are explicitly unsupported, never rounded. Nanosecond feed ingestion needs a
+separate exact-time contract before using this adapter with such data.
+
+Every call requires a decision time, history anchor and positive integer freshness
+budget in seconds. Only bars opening at/after the anchor, closing at/before the
+decision, and available at/before it may enter the calculation. The latest usable
+bar need not be the most recent chronological bar if publication was delayed;
+the caller's explicit freshness budget decides whether the older window is stale.
+
+Input order is normalized; duplicate opens/revisions and mixed identities are
+rejected. Missing anchored first bars, interior gaps and stale endings are
+reported explicitly. Even invalid excluded records are rejected, not silently
+interpreted as a revision policy.
+
+This first boundary accepts contiguous segments only: it does not know weekends,
+holidays, session breaks or broker bar alignment. Do not use it to claim a
+multi-year market replay; calendar-aware history and the existing feed policies
+must be reconciled next. Partial higher-timeframe bars are not supported either.
+
+## Synthetic example
+
+```python
+from datetime import datetime, timedelta, timezone
+from trading_system.tree_replay.bars import ClosedBar
+from trading_system.tree_replay.ema import ema_snapshot
+
+start = datetime(2026, 9, 9, tzinfo=timezone.utc)
+bars = [ClosedBar(
+    instrument="SYNTH:TEST", timeframe="5m",
+    opened_at=start + timedelta(minutes=5*i),
+    closed_at=start + timedelta(minutes=5*(i+1)),
+    available_at=start + timedelta(minutes=5*(i+1)),
+    open=i+1, high=i+2, low=i+1, close=i+1,
+    volume=None, source="synthetic demonstration",
+) for i in range(10)]
+result = ema_snapshot(
+    bars, snapshot_id="demo", instrument="SYNTH:TEST", timeframe="5m",
+    decision_time=bars[-1].closed_at, history_start=start,
+    max_age_seconds=300,  # synthetic choice, NOT an approved market policy
+)
+assert abs(result["features"]["chartdesk.5m.ema5"] - 8) < 1e-12
+assert result["availability"]["chartdesk.5m.ema13"] == "UNKNOWN"
+assert result["ready_for_replay"] is False
+```
+
+Each frame produces22 typed observations. Call separately for each supported
+frame at the SAME explicit decision time; no multi-frame join or producer
+arbitration is implemented yet. Prefixes such as `chartdesk.5m.` prevent an
+accidental join of different timeframes or legacy layer IDs.
+
+## Output and provenance
+
+The payload extends the existing pre-entry snapshot with exact instrument/frame,
+history anchor, freshness limit, selected-bar count, per-EMA history coverage,
+window blocker, source commit, adapter version and installed pandas/numpy versions.
+`window_sha256` identifies selected bars and their metadata plus window settings.
+Valid excluded future rows do not affect the payload at a fixed decision time.
+
+Known observations carry the last selected bar's close time and the maximum
+availability of ALL selected dependencies, including late earlier bars. Missing
+and warmup observations record the evaluation time and explicit status. Unknown,
+unavailable and stale values remain null; legitimate false and zero remain values.
+
+All fields are optional PRE_ENTRY observations. The inherited snapshot `eligible`
+flag is only required-field completeness and can be true even when this optional
+observation set is missing. Never treat it as candidate, replay or training
+readiness. Both `ready_for_replay` and `ready_for_training` remain false.
+
+The caller owns persistence; this adapter does not yet append an immutable dataset.
+The input hash is not a substitute for pinning the eventual research-code revision,
+dependency environment and contract manifest in a dataset/experiment manifest.
+Repeated full-window computation is for fidelity testing, not a claimed optimized
+ten-year engine. Checkpoint/resume equivalence remains separate work.
+
+## Verify source reuse
+
+```powershell
+python tools/check_ema_source_parity.py --source-root C:/research/chart-desk
+```
+
+The directory is an example path; the command does not download it. It compares
+canonical LF Git blob identities for indicators/tr/features and the selected
+function/constant ASTs against the local audited subset, including its allowed
+imports/top-level nodes. Nothing from the input directory is executed.
+
+Exit0 means source subset identity verified, exit2 means missing/mismatched
+source or subset, exit1 means invalid local contract/input configuration. This
+is source reuse evidence, not deployed-service or full-tree replay parity.

```

