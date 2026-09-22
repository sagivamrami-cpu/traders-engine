# Task 2 uncommitted review package

Base/head c1b6071633c55376c64f0a98ece843706f420f49 unchanged.
Only parent-owned new files included. Task1 BarWindow API is a dependency.

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

