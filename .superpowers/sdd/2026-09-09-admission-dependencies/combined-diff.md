# Combined admission-dependencies component review
No commits; existing accepted components are dependencies, not changed files.
# Task1 recovered working-tree source-calculation diff
BASE and HEAD c1b6071633c55376c64f0a98ece843706f420f49; no commits. New files versus NUL.
warning: in the working copy of 'trading_system/tree_replay/_vendor/admission_matrix.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/admission_matrix.py b/trading_system/tree_replay/_vendor/admission_matrix.py
new file mode 100644
index 0000000..9e2ca7e
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/admission_matrix.py
@@ -0,0 +1,156 @@
+from __future__ import annotations
+from dataclasses import dataclass
+from . import admission_toolkit as toolkit
+from . import tr
+from . import atr as tr_atr
+
+
+WEIGHTS = {"tr": 1.0, "supertrend": 0.8, "structure": 0.8, "vwap": 0.6}
+
+
+LOOKBACK = {"4h": 240, "1h": 240, "30m": 90, "15m": 55, "5m": 55}
+
+
+@dataclass
+class ToolRead:
+    tool: str
+    direction: int          # +1 long / -1 short / 0 none
+    strength: int           # 0–100, descriptive
+    note: str
+
+    def arrow(self) -> str:
+        return {1: "▲", -1: "▼", 0: "·"}[self.direction]
+
+
+def _clip(x: float, lo: float = 0, hi: float = 100) -> int:
+    return int(max(lo, min(hi, x)))
+
+
+def _atr(df) -> float:
+    """Wilder ATR for both the read and the view that carries its scale."""
+    return float(tr_atr.atr(df, 14).iloc[-1]) or 1e-9
+
+
+def read_tr(df) -> ToolRead:
+    e = tr.emas(df)
+    n = len(df)
+    trio = [float(e[f"ema{k}"].iloc[-1]) for k in (5, 13, 50)]
+    atr = _atr(df)
+    fan_w = abs(trio[0] - trio[2]) / atr
+    close = float(df["close"].iloc[-1])
+    dev = (close - trio[2]) / atr
+
+    if trio[0] > trio[1] > trio[2]:
+        d = 1
+    elif trio[0] < trio[1] < trio[2]:
+        d = -1
+    else:
+        return ToolRead("tr", 0, _clip(20 - 10 * fan_w), "ממוצעים דחוסים — אין עניין")
+    strength = _clip(30 * fan_w + 10 * min(abs(dev), 3))
+    side = "מעל" if close > trio[2] else "מתחת"
+    return ToolRead("tr", d, strength,
+                    f"מניפה {'בול' if d>0 else 'בר'} w={fan_w:.1f}, מחיר {side} ענן ({dev:+.1f} ATR)")
+
+
+def read_supertrend(df) -> ToolRead:
+    ls = toolkit.ladder_state(df)
+    if not ls.get("available"):
+        return ToolRead("supertrend", 0, 0, "לא זמין")
+    n_bull, n = ls["n_bull"], ls["n_bands"]
+    bands = ls.get("bands", [])
+    fresh = any(b.get("just_flipped") for b in bands)
+    youngest = min((b["bars_in_trend"] for b in bands), default=99)
+    spread = ls.get("band_spread_pct", 0)
+    if n_bull == n:
+        d = 1
+    elif n_bull == 0:
+        d = -1
+    else:
+        return ToolRead("supertrend", 0, _clip(25 * max(n_bull, n - n_bull) / n),
+                        f"רצועות חלוקות {n_bull}/{n} — מעבר, לא מגמה")
+    strength = _clip(50 + 20 * min(spread, 2) + (20 if youngest <= 3 else 0))
+    note = f"3/3 רצועות {'בול' if d>0 else 'בר'}, מרווח {spread:.1f}%"
+    if fresh:
+        note += " · פליפ טרי!"
+    return ToolRead("supertrend", d, strength, note)
+
+
+def read_vwap(df) -> ToolRead:
+    vw = toolkit.vwap_bands(df)
+    z = float(vw["z"].iloc[-1])
+    if abs(z) < 0.3:
+        return ToolRead("vwap", 0, 20, f"על ה-VWAP (z={z:+.1f}) — שיווי משקל")
+    d = 1 if z > 0 else -1
+    stretched = abs(z) > 2
+    strength = _clip(30 + 25 * min(abs(z), 3) - (25 if stretched else 0))
+    note = f"{'מעל' if d>0 else 'מתחת ל'}ערך, z={z:+.1f}"
+    if stretched:
+        note += " · מתוח — סיכון חזרה לערך"
+    return ToolRead("vwap", d, strength, note)
+
+
+def read_structure(df, k: int = 3) -> ToolRead:
+    hi, lo = df["high"].values, df["low"].values
+    highs, lows = [], []
+    for i in range(k, len(df) - k):
+        if hi[i] == max(hi[i - k:i + k + 1]):
+            highs.append(float(hi[i]))
+        elif lo[i] == min(lo[i - k:i + k + 1]):
+            lows.append(float(lo[i]))
+    if len(highs) < 2 or len(lows) < 2:
+        return ToolRead("structure", 0, 0, "אין מספיק סווינגים")
+    hh, hl = highs[-1] > highs[-2], lows[-1] > lows[-2]
+    lh, ll = highs[-1] < highs[-2], lows[-1] < lows[-2]
+    if hh and hl:
+        return ToolRead("structure", 1, 70, "HH+HL — מבנה עולה")
+    if lh and ll:
+        return ToolRead("structure", -1, 70, "LH+LL — מבנה יורד")
+    return ToolRead("structure", 0, 30, "מבנה מעורב (סווינגים סותרים)")
+
+
+TOOLS = {"tr": read_tr, "supertrend": read_supertrend,
+         "vwap": read_vwap, "structure": read_structure}
+
+
+@dataclass
+class TFView:
+    tf: str
+    reads: list[ToolRead]
+    close: float
+    basis_note: str | None = None
+    atr: float = 0.0
+    bar_ts: float = 0.0     # epoch of the newest bar the reads came from
+
+    @property
+    def net(self) -> float:
+        """Weighted −100..+100. Descriptive agreement, not a probability."""
+        num = sum(r.direction * r.strength * WEIGHTS[r.tool] for r in self.reads)
+        den = sum(WEIGHTS[r.tool] for r in self.reads) or 1
+        return num / den
+
+    @property
+    def agree(self) -> tuple[int, int]:
+        longs = sum(1 for r in self.reads if r.direction > 0)
+        shorts = sum(1 for r in self.reads if r.direction < 0)
+        return longs, shorts
+
+    def label(self) -> str:
+        n = self.net
+        if n >= 55: return "לונג חזק"
+        if n >= 25: return "לונג"
+        if n <= -55: return "שורט חזק"
+        if n <= -25: return "שורט"
+        return "ניטרלי"
+
+
+def read_frame(df, tf, basis_note=None) -> TFView:
+    return TFView(tf=tf, close=float(df["close"].iloc[-1]),
+                  reads=[fn(df) for fn in TOOLS.values()], basis_note=basis_note,
+                  atr=_atr(df), bar_ts=_bar_ts(df))
+
+
+def _bar_ts(df) -> float:
+    try:
+        return float(df.index[-1].timestamp())
+    except Exception:
+        return 0.0

warning: in the working copy of 'trading_system/tree_replay/_vendor/admission_toolkit.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/admission_toolkit.py b/trading_system/tree_replay/_vendor/admission_toolkit.py
new file mode 100644
index 0000000..e1e4bcf
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/admission_toolkit.py
@@ -0,0 +1,133 @@
+from __future__ import annotations
+import numpy as np
+import pandas as pd
+from . import admission_indicators as I
+
+
+SUPERTREND_LADDER: tuple[tuple[int, float], ...] = ((10, 1.0), (11, 2.0), (12, 3.0))
+
+
+def supertrend_ladder(
+    df: pd.DataFrame, settings: tuple[tuple[int, float], ...] = SUPERTREND_LADDER
+) -> pd.DataFrame:
+    """All three Supertrends side by side.
+
+    Three bands at rising ATR multiples are not three signals; they are one
+    trend measured at three distances. The fast band (x1) is where a pullback in
+    a healthy trend stops. The slow band (x3) is where the trend itself is
+    wrong. The gap between them is the room a position has to breathe.
+
+    Columns per setting: `st_{len}_{factor}`, `dir_{len}_{factor}`,
+    `age_{len}_{factor}`.
+    """
+    out = pd.DataFrame(index=df.index)
+    for length, factor in settings:
+        st = I.supertrend(df, length, factor)
+        tag = f"{length}_{factor:g}"
+        out[f"st_{tag}"] = st["st"]
+        out[f"dir_{tag}"] = st["dir"]
+        out[f"age_{tag}"] = st["bars_in_trend"]
+        out[f"flip_{tag}"] = st["flip"]
+    return out
+
+
+def ladder_state(df: pd.DataFrame, settings=SUPERTREND_LADDER) -> dict:
+    """What the ladder is saying right now, including how much it disagrees.
+
+    `agreement` is the interesting field. All three aligned is a trend with
+    conviction. Fast flipped against the other two is a pullback — which is the
+    entry, not the exit. All three disagreeing is chop, and the correct response
+    is to not be in the market.
+    """
+    lad = supertrend_ladder(df, settings)
+    last = lad.iloc[-1]
+    price = float(df["close"].iloc[-1])
+
+    rows, dirs = [], []
+    for length, factor in settings:
+        tag = f"{length}_{factor:g}"
+        d = last[f"dir_{tag}"]
+        if not np.isfinite(d):
+            continue
+        dirs.append(int(d))
+        rows.append({
+            "setting": f"{length}/{factor:g}",
+            "line": float(last[f"st_{tag}"]),
+            "direction": "bull" if d > 0 else "bear",
+            "bars_in_trend": int(last[f"age_{tag}"]),
+            "distance_pct": 100.0 * (price - float(last[f"st_{tag}"])) / price,
+            "just_flipped": bool(last[f"flip_{tag}"]),
+        })
+
+    if not dirs:
+        return {"available": False}
+
+    n_bull = sum(1 for d in dirs if d > 0)
+    if n_bull == len(dirs):
+        state, note = "aligned_bull", "all three bands below price — trend with conviction"
+    elif n_bull == 0:
+        state, note = "aligned_bear", "all three bands above price — trend with conviction"
+    elif dirs[0] != dirs[-1] and len({*dirs[1:]}) == 1:
+        state = "pullback"
+        note = ("fast band flipped against the slower two — a pullback inside an "
+                "intact trend, which is an entry condition, not an exit")
+    else:
+        state, note = "mixed", "the bands disagree — chop, no trend to trade"
+
+    # the fast/slow gap is the practical stop-room measure
+    lines = [r["line"] for r in rows]
+    return {
+        "available": True,
+        "state": state,
+        "note": note,
+        "bands": rows,
+        "band_spread_pct": 100.0 * (max(lines) - min(lines)) / price,
+        "n_bull": n_bull,
+        "n_bands": len(dirs),
+    }
+
+
+def vwap_bands(
+    df: pd.DataFrame,
+    *,
+    anchor: str = "D",
+    source: str = "hlc3",
+    multipliers: tuple[float, ...] = (1.0, 2.0, 3.0),
+) -> pd.DataFrame:
+    """Anchored VWAP with volume-weighted standard-deviation bands.
+
+    Matches the chart: `hlc3` source, bands at 1, 2 and 3 sigma. The deviation
+    is **volume-weighted**, not a plain rolling std — that is what makes the
+    bands sit where TradingView draws them.
+
+    Bands are the useful part. VWAP itself is a magnet; the 2-sigma band is
+    where mean reversion becomes worth a trade, and price outside 3 sigma in a
+    session is genuinely rare.
+    """
+    src = {
+        "hlc3": (df["high"] + df["low"] + df["close"]) / 3.0,
+        "hl2": (df["high"] + df["low"]) / 2.0,
+        "ohlc4": (df["open"] + df["high"] + df["low"] + df["close"]) / 4.0,
+        "close": df["close"],
+    }.get(source, (df["high"] + df["low"] + df["close"]) / 3.0)
+
+    vol = df["volume"] if "volume" in df else pd.Series(0.0, index=df.index)
+    if float(vol.sum()) == 0.0:
+        vol = pd.Series(1.0, index=df.index)
+
+    key = df.index.tz_convert("UTC").tz_localize(None).to_period(anchor)
+    cum_v = vol.groupby(key).cumsum()
+    vwap = (src * vol).groupby(key).cumsum() / cum_v.replace(0.0, np.nan)
+
+    # volume-weighted variance: E[x^2] - (E[x])^2, both volume-weighted
+    cum_v2 = (src.pow(2) * vol).groupby(key).cumsum()
+    var = (cum_v2 / cum_v.replace(0.0, np.nan)) - vwap.pow(2)
+    sigma = np.sqrt(var.clip(lower=0.0))
+
+    out = pd.DataFrame({"vwap": vwap, "sigma": sigma}, index=df.index)
+    for m in multipliers:
+        out[f"upper{m:g}"] = vwap + sigma * m
+        out[f"lower{m:g}"] = vwap - sigma * m
+    price = df["close"]
+    out["z"] = (price - vwap) / sigma.replace(0.0, np.nan)
+    return out

warning: in the working copy of 'trading_system/tree_replay/_vendor/admission_indicators.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/admission_indicators.py b/trading_system/tree_replay/_vendor/admission_indicators.py
new file mode 100644
index 0000000..a54e521
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/admission_indicators.py
@@ -0,0 +1,96 @@
+from __future__ import annotations
+import numpy as np
+import pandas as pd
+from .indicators import _seeded_recursive
+
+
+def rma(src: pd.Series, length: int) -> pd.Series:
+    """Pine `ta.rma` (Wilder smoothing): SMA-seeded, alpha = 1/length."""
+    return _seeded_recursive(src, length, 1.0 / length)
+
+
+def true_range(df: pd.DataFrame) -> pd.Series:
+    prev_close = df["close"].shift(1)
+    return pd.concat(
+        [
+            df["high"] - df["low"],
+            (df["high"] - prev_close).abs(),
+            (df["low"] - prev_close).abs(),
+        ],
+        axis=1,
+    ).max(axis=1)
+
+
+def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
+    """Pine `ta.atr` = `ta.rma(ta.tr(true), length)`."""
+    return rma(true_range(df), length)
+
+
+def supertrend(
+    df: pd.DataFrame, length: int = 10, factor: float = 3.0
+) -> pd.DataFrame:
+    """Pine `ta.supertrend`, band-latching and all.
+
+    Mirrors the reference implementation in the Pine docs::
+
+        upperBand := upperBand < prevUpperBand or close[1] > prevUpperBand
+                     ? upperBand : prevUpperBand
+        lowerBand := lowerBand > prevLowerBand or close[1] < prevLowerBand
+                     ? lowerBand : prevLowerBand
+
+    Pine returns direction -1 for uptrend. That reads backwards everywhere else
+    in this codebase, so `dir` here is **+1 bullish / -1 bearish** and the Pine
+    value is kept alongside as `pine_dir` for anyone reconciling with a chart.
+
+    Returns columns: st, dir, pine_dir, upper, lower, flip (True on the bar the
+    trend changed), bars_in_trend.
+    """
+    hl2 = (df["high"] + df["low"]) / 2.0
+    a = atr(df, length)
+    upper_raw = (hl2 + factor * a).to_numpy(dtype=float)
+    lower_raw = (hl2 - factor * a).to_numpy(dtype=float)
+    close = df["close"].to_numpy(dtype=float)
+    a_arr = a.to_numpy(dtype=float)
+    n = len(df)
+
+    upper = np.full(n, np.nan)
+    lower = np.full(n, np.nan)
+    st = np.full(n, np.nan)
+    pdir = np.full(n, np.nan)
+
+    prev_upper = prev_lower = np.nan
+    prev_st = np.nan
+    for i in range(n):
+        if np.isnan(a_arr[i]):
+            continue
+        ub, lb = upper_raw[i], lower_raw[i]
+        if not np.isnan(prev_upper):
+            if not (ub < prev_upper or close[i - 1] > prev_upper):
+                ub = prev_upper
+            if not (lb > prev_lower or close[i - 1] < prev_lower):
+                lb = prev_lower
+
+        if np.isnan(prev_st):
+            d = 1.0                                  # Pine: first bar is 1
+        elif prev_st == prev_upper:
+            d = -1.0 if close[i] > ub else 1.0
+        else:
+            d = 1.0 if close[i] < lb else -1.0
+
+        s = lb if d == -1.0 else ub
+        upper[i], lower[i], st[i], pdir[i] = ub, lb, s, d
+        prev_upper, prev_lower, prev_st = ub, lb, s
+
+    direction = -pdir  # +1 bullish, -1 bearish
+    out = pd.DataFrame(
+        {"st": st, "dir": direction, "pine_dir": pdir, "upper": upper, "lower": lower},
+        index=df.index,
+    )
+    out["flip"] = out["dir"].ne(out["dir"].shift(1)) & out["dir"].notna() & out["dir"].shift(1).notna()
+
+    # how many bars the current trend has been running -- trend age is the part
+    # traders actually act on, and it is tedious to recompute at every call site
+    grp = out["flip"].cumsum()
+    out["bars_in_trend"] = out.groupby(grp).cumcount() + 1
+    out.loc[out["dir"].isna(), "bars_in_trend"] = np.nan
+    return out

warning: in the working copy of 'trading_system/tree_replay/_vendor/admission_quality.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/admission_quality.py b/trading_system/tree_replay/_vendor/admission_quality.py
new file mode 100644
index 0000000..378f11d
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/admission_quality.py
@@ -0,0 +1,181 @@
+from __future__ import annotations
+import re
+
+
+MAX_REJECTION_AGE_S = 20 * 60
+
+
+LABEL_NO_ANCHOR = "כניסה ללא עוגן"
+
+
+LABEL_NO_TRIGGER = "טריגר כיווני חסר"
+
+
+PREDICATE = "no_named_anchor_and_no_aligned_rejection_or_trigger"
+
+
+_ANCHOR_PREFIXES = ("רמה:", "כניסה בריטסט ל", "כניסה:")
+
+
+_PRICE_TAIL = re.compile(r"[\s,]*[\d,]+(?:\.\d+)?\s*$")
+
+
+_NAME_SPLIT = re.compile(r"[·/]")
+
+
+_COUNT_PREFIX = re.compile(r"^\d+\s+רמות\s*:\s*")
+
+
+def anchor_names(reasons) -> set[str] | None:
+    """The named levels a plan is ENTERED on, or None if it names none.
+
+    Names only. Two plans on one cluster carry the same names at different
+    prices, and comparing prices would call them different levels.
+
+    The line often carries more than the entry: the engine writes
+    `"כניסה: Q-WHOLE · ביטול: PSY-HI"` and the retest builder writes
+    `"כניסה בריטסט ל-Q-QUARTER, לא במחיר השוק"`. A stop is not an anchor and
+    a clause is not a level -- BTC's first live shadow row, 04.09 14:25,
+    reported `["Q-WHOLE", "ביטול: PSY-HI"]` before this cut.
+    """
+    for r in (reasons or []):
+        r = str(r).strip()
+        for pre in _ANCHOR_PREFIXES:
+            if not r.startswith(pre):
+                continue
+            body = r[len(pre):].lstrip("־- :")
+            if not body or body.startswith("אין"):
+                return None
+            body = _COUNT_PREFIX.sub("", body.split(",")[0])
+            names = set()
+            for part in _NAME_SPLIT.split(body):
+                part = _PRICE_TAIL.sub("", part).strip()
+                if not part or ":" in part:
+                    break          # a new labelled clause — the entry ended
+                names.add(part.upper())
+            return names or None
+    return None
+
+
+def aligned_trigger(reasons, direction: str | None) -> str | None:
+    """The directional trigger this plan actually has, or None.
+
+    Four readings count, and each is a fact a builder already wrote:
+    a last bar that committed WITH the direction (0.15 ATR, tree stage 10),
+    a trap or a committed extreme that resolves TO this direction, and a
+    CONFIRMED W for a long or M for a short. A forming pattern and the bare
+    presence of a vector do not: "there is a vector somewhere" is not a
+    reason to be on this side of it.
+
+    THE TREE AND THE ENGINE SAY THE SAME THINGS DIFFERENTLY. The tree writes
+    its facts as `"<name>: <value>"`; the engine writes `wm.line()`
+    ("תבנית W מאושרת (סגירה מעבר לצוואר): …") plus its own verdict line
+    ("התבנית מאשרת את כיוון העסקה (לונג)"). Reading only the tree's shape
+    put "טריגר כיווני חסר" on a BTC swing long that had a confirmed W --
+    the first engine plan the shadow ever classified, 04.09 14:52.
+    """
+    if not direction:
+        return None
+    want = "W" if direction == "לונג" else "M"
+    for r in (reasons or []):
+        r = str(r).strip()
+        if r.startswith("commitment:"):
+            v = r.split(":", 1)[1].strip()
+            if not v.startswith(("אין", "לא נקרא")):
+                return "commitment"
+        elif r.startswith("מלכודת:"):
+            v = r.split(":", 1)[1].strip()
+            if direction in v and ("היערך" in v or "⇒" in v):
+                return "trap"
+        elif r.startswith("התבנית מאשרת את כיוון העסקה"):
+            # The engine has already checked confirmed AND same-direction.
+            if direction in r:
+                return f"confirmed_{want}"
+        elif r.startswith("תבנית"):
+            v = r[len("תבנית"):].lstrip(": ")
+            if (v.startswith(want) and "מאושרת" in v
+                    and "לא מאושרת" not in v and "מתגבשת" not in v):
+                return f"confirmed_{want}"
+    return None
+
+
+def still_defending(rej: dict | None, direction: str | None, entry) -> bool:
+    """Is this rejection still ARGUING against a trade in `direction`?
+
+    A bullish rejection is support, and support only argues against a short
+    while the short is still above it. Once price has broken below and the
+    short is entered underneath, the same zone has FAILED -- it now agrees
+    with the short, and calling it "against" would be the desk telling a
+    client the opposite of what the chart says.
+    """
+    if not rej or entry is None or not direction:
+        return False
+    lo, hi = rej.get("zone_lo"), rej.get("zone_hi")
+    if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
+        return False
+    return (float(hi) <= float(entry) if direction == "שורט"
+            else float(lo) >= float(entry))
+
+
+def opposing_label(rej: dict | None) -> str | None:
+    """`נגד דחייה טרייה מ־4,461.69–4,462.54 (EMA200-1h · D3-HI)`."""
+    if not rej:
+        return None
+    lo, hi = rej.get("zone_lo"), rej.get("zone_hi")
+    if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
+        return None
+    out = f"נגד דחייה טרייה מ־{float(lo):,.2f}–{float(hi):,.2f}"
+    names = [str(n) for n in (rej.get("levels") or []) if str(n).strip()]
+    if names:
+        out += f" ({' · '.join(names[:3])})"
+    return out
+
+
+def evaluate(*, direction: str | None, entry, atr: float, reasons,
+             aligned_rejection: dict | None = None,
+             opposing_rejection: dict | None = None) -> dict:
+    """Classify one entry. Never decides anything.
+
+    `shadow_block` is the predicate a stricter desk would refuse on: no named
+    anchor, no aligned directional trigger, and no fresh rejection agreeing
+    with the trade. An OPPOSING rejection adds its label but is deliberately
+    not part of the predicate -- it is the loudest evidence on the 10:25
+    short, and a predicate that needed it would miss the 11:05 long, which
+    had nothing against it and nothing for it either.
+    """
+    names = anchor_names(reasons)
+    trigger = aligned_trigger(reasons, direction)
+    if not still_defending(opposing_rejection, direction, entry):
+        opposing_rejection = None      # broken support is not opposition
+    labels = []
+    if not names:
+        labels.append(LABEL_NO_ANCHOR)
+    if trigger is None:
+        labels.append(LABEL_NO_TRIGGER)
+    against = opposing_label(opposing_rejection)
+    if against:
+        labels.append(against)
+    return {
+        "anchor_names": sorted(names) if names else [],
+        "aligned_trigger": trigger,
+        "aligned_rejection": _rej(aligned_rejection, entry, atr),
+        "opposing_rejection": _rej(opposing_rejection, entry, atr),
+        "labels": labels,
+        "shadow_block": bool(not names and trigger is None
+                             and not aligned_rejection),
+        "predicate": PREDICATE,
+    }
+
+
+def _rej(rej: dict | None, entry, atr: float) -> dict | None:
+    if not rej:
+        return None
+    out = {k: rej.get(k) for k in
+           ("ts", "direction", "zone_lo", "zone_hi", "levels", "close",
+            "wick_atr", "age_s")}
+    gap = rej.get("gap")
+    if isinstance(gap, (int, float)) and atr:
+        out["distance_atr"] = round(float(gap) / float(atr), 2)
+    else:
+        out["distance_atr"] = None
+    return out

warning: in the working copy of 'trading_system/tree_replay/_vendor/admission_clocks.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/admission_clocks.py b/trading_system/tree_replay/_vendor/admission_clocks.py
new file mode 100644
index 0000000..464f240
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/admission_clocks.py
@@ -0,0 +1,82 @@
+from __future__ import annotations
+from datetime import datetime
+from zoneinfo import ZoneInfo
+
+
+TZ = ZoneInfo("Asia/Jerusalem")
+
+
+CLOSE_WEEKDAY, CLOSE_HOUR = 4, 23        # Monday=0 ... Friday=4
+
+
+OPEN_WEEKDAY, OPEN_HOUR = 0, 1           # Monday
+
+
+def now_il(now: datetime) -> datetime:
+    if not isinstance(now, datetime):
+        raise TypeError("now must be an aware datetime")
+    if now.tzinfo is None or now.utcoffset() is None:
+        raise ValueError("now must be an aware datetime")
+    return now.astimezone(TZ)
+
+
+def is_closed(now: datetime) -> bool:
+    """Is the market inside the weekend window right now?"""
+    t = now_il(now)
+    wd, hour = t.weekday(), t.hour
+    if wd == CLOSE_WEEKDAY:                      # Friday
+        return hour >= CLOSE_HOUR
+    if wd in (5, 6):                             # Saturday, Sunday
+        return True
+    if wd == OPEN_WEEKDAY:                       # Monday
+        return hour < OPEN_HOUR
+    return False
+
+
+WARN_MIN_BEFORE = 90     # first notice — time to decide, not to react
+
+
+def minutes_to_close(now: datetime) -> float | None:
+    """Minutes until Friday's close, or None when that is not today's story."""
+    t = now_il(now)
+    if t.weekday() != CLOSE_WEEKDAY or is_closed(t):
+        return None
+    close = t.replace(hour=CLOSE_HOUR, minute=0, second=0, microsecond=0)
+    return (close - t).total_seconds() / 60.0
+
+
+def entry_blocked(now: datetime) -> str | None:
+    """Reason a NEW trade must not be opened now, or None.
+
+    A trade opened an hour before the close cannot reach its target and cannot
+    be protected through the weekend, so it is not a trade -- it is a position
+    inherited by Monday's gap.
+    """
+    if is_closed(now):
+        return "שוק סגור"
+    m = minutes_to_close(now)
+    if m is not None and m <= WARN_MIN_BEFORE:
+        return (f"סגירת שבוע בעוד {m:.0f} דק' — לא נפתחות עסקאות חדשות "
+                "(גאפ בפתיחה לא ניתן להגנה בסטופ)")
+    return None
+
+
+HUNT_START_H = 2
+
+
+HUNT_END_H = 21
+
+
+def hunting(now: datetime) -> bool:
+    """Is the clock inside his hunting window?"""
+    h = now_il(now).hour
+    return HUNT_START_H <= h < HUNT_END_H
+
+
+def outside_reason(now: datetime) -> str | None:
+    """Why we are not hunting, or None."""
+    if hunting(now):
+        return None
+    h = now_il(now).hour
+    return (f"{h:02d}:00 — מחוץ לחלון החיפוש "
+            f"({HUNT_START_H:02d}:00-{HUNT_END_H:02d}:00)")

warning: in the working copy of 'trading_system/tree_replay/_vendor/admission_swing.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/admission_swing.py b/trading_system/tree_replay/_vendor/admission_swing.py
new file mode 100644
index 0000000..9bbf099
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/admission_swing.py
@@ -0,0 +1,22 @@
+from __future__ import annotations
+
+
+SWING_K = 3
+
+
+def _last_swing(df, up: bool, k: int = SWING_K) -> tuple[float, int] | None:
+    """Most recent confirmed swing low (for an up-extension) or high.
+
+    Confirmed means it has `k` bars either side, so the newest candidate sits at
+    index -(k+1) at the earliest. Returning an unconfirmed swing would let a
+    detector "break" a level that the next bar redefines.
+    """
+    hi, lo = df["high"].values, df["low"].values
+    n = len(df)
+    for i in range(n - k - 1, k - 1, -1):
+        window = slice(i - k, i + k + 1)
+        if up and lo[i] == min(lo[window]):
+            return float(lo[i]), n - 1 - i
+        if not up and hi[i] == max(hi[window]):
+            return float(hi[i]), n - 1 - i
+    return None

warning: in the working copy of 'trading_system/tree_spec/admission_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_spec/admission_source.py b/trading_system/tree_spec/admission_source.py
new file mode 100644
index 0000000..bf33249
--- /dev/null
+++ b/trading_system/tree_spec/admission_source.py
@@ -0,0 +1,404 @@
+"""Inert-text audit of the complete pinned admission calculation closure.
+
+The retained desks are never imported or executed. Every runtime module,
+including reused EMA/TR dependencies, is compared as a complete ordered AST.
+"""
+from __future__ import annotations
+
+import ast
+import copy
+import hashlib
+import json
+import os
+from pathlib import Path
+import subprocess
+
+
+ROOT = Path(__file__).resolve().parents[2]
+REPOSITORIES = {
+    "chart-desk": "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9",
+    "trading-floor": "d827dd792cbd1d396b4ee325879c63e57388e07a",
+}
+# Independent fixed authority: a supplied manifest cannot narrow this closure.
+FILES = [
+    {
+        "repository": "chart-desk",
+        "path": "chartdesk/matrix.py",
+        "git_blob_sha1": "28641487567c457b6922c2a63055659867bb4248",
+        "vendor_path": "trading_system/tree_replay/_vendor/admission_matrix.py",
+        "symbols": [
+            "WEIGHTS",
+            "LOOKBACK",
+            "ToolRead",
+            "_clip",
+            "_atr",
+            "read_tr",
+            "read_supertrend",
+            "read_vwap",
+            "read_structure",
+            "TOOLS",
+            "TFView",
+            "read_tf",
+            "_bar_ts"
+        ],
+        "allowed_imports": "from __future__ import annotations\nfrom dataclasses import dataclass\nfrom . import admission_toolkit as toolkit\nfrom . import tr\nfrom . import atr as tr_atr",
+        "adaptation": "matrix_frame_and_atr_import"
+    },
+    {
+        "repository": "chart-desk",
+        "path": "chartdesk/toolkit.py",
+        "git_blob_sha1": "dede9042db891d9ff2e6d6523918fe6d98b11ab0",
+        "vendor_path": "trading_system/tree_replay/_vendor/admission_toolkit.py",
+        "symbols": [
+            "SUPERTREND_LADDER",
+            "supertrend_ladder",
+            "ladder_state",
+            "vwap_bands"
+        ],
+        "allowed_imports": "from __future__ import annotations\nimport numpy as np\nimport pandas as pd\nfrom . import admission_indicators as I",
+        "adaptation": "none"
+    },
+    {
+        "repository": "chart-desk",
+        "path": "chartdesk/indicators.py",
+        "git_blob_sha1": "672f0428c3a81b86376d4f792ae40ecd174a2025",
+        "vendor_path": "trading_system/tree_replay/_vendor/admission_indicators.py",
+        "symbols": [
+            "rma",
+            "true_range",
+            "atr",
+            "supertrend"
+        ],
+        "allowed_imports": "from __future__ import annotations\nimport numpy as np\nimport pandas as pd\nfrom .indicators import _seeded_recursive",
+        "adaptation": "none"
+    },
+    {
+        "repository": "chart-desk",
+        "path": "chartdesk/entry_quality.py",
+        "git_blob_sha1": "0cd76eb8c607690610f4559e5946a60e8f7647ac",
+        "vendor_path": "trading_system/tree_replay/_vendor/admission_quality.py",
+        "symbols": [
+            "MAX_REJECTION_AGE_S",
+            "LABEL_NO_ANCHOR",
+            "LABEL_NO_TRIGGER",
+            "PREDICATE",
+            "_ANCHOR_PREFIXES",
+            "_PRICE_TAIL",
+            "_NAME_SPLIT",
+            "_COUNT_PREFIX",
+            "anchor_names",
+            "aligned_trigger",
+            "still_defending",
+            "opposing_label",
+            "evaluate",
+            "_rej"
+        ],
+        "allowed_imports": "from __future__ import annotations\nimport re",
+        "adaptation": "none"
+    },
+    {
+        "repository": "trading-floor",
+        "path": "floor/marketclock.py",
+        "git_blob_sha1": "246b01255a2203e2a04c2ef7d549f67087b4f2c9",
+        "vendor_path": "trading_system/tree_replay/_vendor/admission_clocks.py",
+        "symbols": [
+            "TZ",
+            "CLOSE_WEEKDAY,CLOSE_HOUR",
+            "OPEN_WEEKDAY,OPEN_HOUR",
+            "now_il",
+            "is_closed",
+            "WARN_MIN_BEFORE",
+            "minutes_to_close",
+            "entry_blocked"
+        ],
+        "allowed_imports": "from __future__ import annotations\nfrom datetime import datetime\nfrom zoneinfo import ZoneInfo",
+        "adaptation": "required_aware_floor_clock"
+    },
+    {
+        "repository": "chart-desk",
+        "path": "chartdesk/windows.py",
+        "git_blob_sha1": "53453b73e7f0c48647945e7d58ba6b30ed8d4102",
+        "vendor_path": "trading_system/tree_replay/_vendor/admission_clocks.py",
+        "symbols": [
+            "TZ",
+            "HUNT_START_H",
+            "HUNT_END_H",
+            "hunting",
+            "outside_reason"
+        ],
+        "allowed_imports": "",
+        "adaptation": "required_aware_hunting_clock_shared_TZ"
+    },
+    {
+        "repository": "chart-desk",
+        "path": "chartdesk/zones.py",
+        "git_blob_sha1": "92f7b99373b4f266a1d80e2d997b965f973d7698",
+        "vendor_path": "trading_system/tree_replay/_vendor/admission_swing.py",
+        "symbols": [
+            "SWING_K",
+            "_last_swing"
+        ],
+        "allowed_imports": "from __future__ import annotations",
+        "adaptation": "none"
+    },
+    {
+        "repository": "chart-desk",
+        "path": "chartdesk/indicators.py",
+        "git_blob_sha1": "672f0428c3a81b86376d4f792ae40ecd174a2025",
+        "vendor_path": "trading_system/tree_replay/_vendor/indicators.py",
+        "symbols": [
+            "_seeded_recursive",
+            "ema",
+            "stdev"
+        ],
+        "allowed_imports": "from __future__ import annotations\nimport numpy as np\nimport pandas as pd",
+        "adaptation": "none"
+    },
+    {
+        "repository": "chart-desk",
+        "path": "chartdesk/tr.py",
+        "git_blob_sha1": "8297c712d20404880d4d8949e96efbf48613909c",
+        "vendor_path": "trading_system/tree_replay/_vendor/tr.py",
+        "symbols": [
+            "TR_EMAS",
+            "emas",
+            "ema_cloud"
+        ],
+        "allowed_imports": "from __future__ import annotations\nimport pandas as pd\nfrom . import indicators as I",
+        "adaptation": "none"
+    },
+    {
+        "repository": "chart-desk",
+        "path": "chartdesk/tr.py",
+        "git_blob_sha1": "8297c712d20404880d4d8949e96efbf48613909c",
+        "vendor_path": "trading_system/tree_replay/_vendor/atr.py",
+        "symbols": [
+            "atr"
+        ],
+        "allowed_imports": "import pandas as pd",
+        "adaptation": "none"
+    }
+]
+EXPECTED_CONTRACT = {
+    "schema_version": "admission-source-contracts-v1",
+    "repositories": REPOSITORIES,
+    "files": FILES,
+    "scope": "Pure original admission calculations on supplied frames and explicit aware clocks; no outer admission, source execution, state replay or labels",
+    "ready_for_replay": False,
+    "ready_for_training": False,
+}
+INPUT_ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
+                StopIteration, subprocess.SubprocessError)
+
+
+def _dump(node):
+    return ast.dump(node, include_attributes=False)
+
+
+def _name(node):
+    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
+        return node.name
+    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
+        return node.target.id
+    if isinstance(node, ast.Assign):
+        return ",".join(n.id for target in node.targets for n in ast.walk(target)
+                        if isinstance(n, ast.Name))
+    return None
+
+
+def _no_duplicate_keys(pairs):
+    result = {}
+    for key, value in pairs:
+        if key in result:
+            raise ValueError("duplicate JSON key")
+        result[key] = value
+    return result
+
+
+def _read_json(path):
+    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys)
+
+
+def _canonical(value):
+    return json.dumps(value, sort_keys=True, allow_nan=False)
+
+
+def _replace_exact(tree, old, new, count):
+    """Replace only a declared AST expression and require the original count."""
+    old_dump = _dump(ast.parse(old, mode="eval").body)
+    replacement = ast.parse(new, mode="eval").body
+
+    class Replace(ast.NodeTransformer):
+        found = 0
+
+        def visit(self, node):
+            if _dump(node) == old_dump:
+                self.found += 1
+                return copy.deepcopy(replacement)
+            return super().visit(node)
+
+    visitor = Replace()
+    result = visitor.visit(tree)
+    if visitor.found != count:
+        raise ValueError("SPECIALIZATION_PRECONDITION_MISMATCH")
+    return result
+
+
+def _required_time(function):
+    expected = ast.parse("def f(now: datetime | None = None): pass").body[0].args
+    if _dump(function.args) != _dump(expected):
+        raise ValueError("SOURCE_CLOCK_SIGNATURE_MISMATCH")
+    function.args = ast.parse("def f(now: datetime): pass").body[0].args
+    return function
+
+
+def _project(text, row):
+    """Original ordered definitions with only explicit import/fetch/clock edits."""
+    source = ast.parse(text)
+    selected = [node for node in source.body if _name(node) in row["symbols"]]
+    if [_name(node) for node in selected] != row["symbols"]:
+        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
+    mode = row["adaptation"]
+    if mode == "matrix_frame_and_atr_import":
+        atr = selected[row["symbols"].index("_atr")]
+        _replace_exact(atr, "tr.atr(df, 14)", "tr_atr.atr(df, 14)", 1)
+        function = selected[row["symbols"].index("read_tf")]
+        signature = ast.parse("def read_tf(symbol: str, tf: str) -> TFView: pass").body[0]
+        if (_dump(function.args) != _dump(signature.args)
+                or _dump(function.returns) != _dump(signature.returns)
+                or function.decorator_list or len(function.body) != 3):
+            raise ValueError("SOURCE_READ_TF_SHAPE_MISMATCH")
+        fetch = ast.parse(
+            "df, corr = basis.fetch_corrected(symbol, tf, LOOKBACK[tf])\n"
+            "note = corr.render() if corr.show else None"
+        ).body
+        if [_dump(n) for n in function.body[:2]] != [_dump(n) for n in fetch]:
+            raise ValueError("SOURCE_FETCH_SPECIALIZATION_MISMATCH")
+        returned = function.body[2]
+        if (not isinstance(returned, ast.Return) or not isinstance(returned.value, ast.Call)
+                or _dump(returned.value.func) != _dump(ast.Name(id="TFView", ctx=ast.Load()))):
+            raise ValueError("SOURCE_TFVIEW_CONSTRUCTOR_MISSING")
+        function.name = "read_frame"
+        function.args = ast.parse("def f(df, tf, basis_note=None): pass").body[0].args
+        # Preserve the entire original constructor, tool order and all fields.
+        function.body = [_replace_exact(returned, "note", "basis_note", 1)]
+    elif mode == "required_aware_floor_clock":
+        for node in selected:
+            if isinstance(node, ast.FunctionDef):
+                _required_time(node)
+                if node.name == "now_il":
+                    original = ast.parse(
+                        "if now is None:\n    return datetime.now(TZ)\n"
+                        "return now.astimezone(TZ) if now.tzinfo else now.replace(tzinfo=TZ)"
+                    ).body
+                    if [_dump(n) for n in node.body] != [_dump(n) for n in original]:
+                        raise ValueError("SOURCE_NOW_IL_BODY_MISMATCH")
+                    node.body = ast.parse(
+                        'if not isinstance(now, datetime):\n'
+                        '    raise TypeError("now must be an aware datetime")\n'
+                        'if now.tzinfo is None or now.utcoffset() is None:\n'
+                        '    raise ValueError("now must be an aware datetime")\n'
+                        'return now.astimezone(TZ)'
+                    ).body
+    elif mode == "required_aware_hunting_clock_shared_TZ":
+        expected_tz = ast.parse('TZ = ZoneInfo("Asia/Jerusalem")').body[0]
+        if _dump(selected[0]) != _dump(expected_tz):
+            raise ValueError("SHARED_TIMEZONE_MISMATCH")
+        selected = selected[1:]  # identical TZ already projected from marketclock
+        for node in selected:
+            if isinstance(node, ast.FunctionDef):
+                _required_time(node)
+                _replace_exact(node, "(now or datetime.now(TZ)).astimezone(TZ)",
+                               "now_il(now)", 1)
+    elif mode != "none":
+        raise ValueError("UNKNOWN_SPECIALIZATION")
+    return ast.parse(row["allowed_imports"]).body + selected
+
+
+def _git(repo, *args):
+    # Local rev-parse only: no source imports, hooks, filters, status refresh,
+    # object fetches or external processes configured by the source repository.
+    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1",
+               GIT_TERMINAL_PROMPT="0")
+    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
+        env.pop(key, None)
+    result = subprocess.run(
+        ["git", "-c", "core.fsmonitor=false", "-C", str(repo), "rev-parse", *args],
+        env=env, text=True, encoding="utf-8", capture_output=True, timeout=10,
+        check=True,
+    )
+    return result.stdout.strip()
+
+
+def audit_admission_source(source_root) -> dict:
+    """Audit an explicit parent of the pinned chart-desk/trading-floor checkouts."""
+    blockers = []
+    checked = []
+    try:
+        source_root = Path(source_root)
+    except INPUT_ERRORS as exc:
+        return _report([f"SOURCE_ROOT_INVALID:{type(exc).__name__}"], checked)
+    try:
+        contract = _read_json(ROOT / "configs/trees/admission-source-contracts.json")
+        if _canonical(contract) != _canonical(EXPECTED_CONTRACT):
+            blockers.append("CONTRACT_MISMATCH")
+        baseline = _read_json(ROOT / "configs/trees/existing-alerts-baseline.json")
+        for repo, commit in REPOSITORIES.items():
+            pins = [row.get("commit") for row in baseline["repositories"]
+                    if row.get("name") == repo]
+            if pins != [commit]:
+                blockers.append(f"BASELINE_COMMIT_MISMATCH:{repo}")
+    except INPUT_ERRORS as exc:
+        blockers.append(f"CONTRACT_UNREADABLE:{type(exc).__name__}")
+    for repo, commit in REPOSITORIES.items():
+        try:
+            path = source_root / repo
+            if Path(_git(path, "--show-toplevel")).resolve() != path.resolve():
+                blockers.append(f"NOT_REPOSITORY_ROOT:{repo}")
+            if _git(path, "HEAD") != commit:
+                blockers.append(f"SOURCE_COMMIT_MISMATCH:{repo}")
+        except INPUT_ERRORS as exc:
+            blockers.append(f"SOURCE_IDENTITY_UNREADABLE:{repo}:{type(exc).__name__}")
+    expected_modules = {}
+    unavailable = set()
+    for row in FILES:
+        path = f'{row["repository"]}/{row["path"]}'
+        vendor = row["vendor_path"]
+        try:
+            text = (source_root / path).read_text(encoding="utf-8")
+            data = text.encode("utf-8")  # canonical Git LF after universal newline read
+            digest = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
+            if digest != row["git_blob_sha1"]:
+                blockers.append(f"SOURCE_BLOB_MISMATCH:{path}")
+                unavailable.add(vendor)
+                continue
+            expected_modules.setdefault(vendor, []).extend(_project(text, row))
+            checked.append({"source": path, "vendor": vendor, "symbols": list(row["symbols"])})
+        except INPUT_ERRORS as exc:
+            blockers.append(f"SOURCE_PROJECTION_UNREADABLE:{path}:{type(exc).__name__}")
+            unavailable.add(vendor)
+    for vendor in dict.fromkeys(row["vendor_path"] for row in FILES):
+        try:
+            actual = ast.parse((ROOT / vendor).read_text(encoding="utf-8"))
+            # Existing accepted modules have a descriptive module docstring.
+            # Strip at most that one string, not arbitrary top-level expressions.
+            if ast.get_docstring(actual) is not None:
+                actual.body = actual.body[1:]
+            expected = ast.Module(body=expected_modules.get(vendor, []), type_ignores=[])
+            if vendor not in unavailable and _dump(actual) != _dump(expected):
+                blockers.append(f"VENDOR_AST_MISMATCH:{vendor}")
+        except INPUT_ERRORS as exc:
+            blockers.append(f"VENDOR_UNREADABLE:{vendor}:{type(exc).__name__}")
+    return _report(blockers, checked)
+
+
+def _report(blockers, checked):
+    return {
+        "status": "BLOCKED" if blockers else "VERIFIED",
+        "source_subset_verified": not blockers,
+        "blockers": blockers,
+        "checked_projections": checked,
+        "source_commits": dict(REPOSITORIES),
+        "ready_for_replay": False,
+        "ready_for_training": False,
+    }

warning: in the working copy of 'configs/trees/admission-source-contracts.json', LF will be replaced by CRLF the next time Git touches it
diff --git a/configs/trees/admission-source-contracts.json b/configs/trees/admission-source-contracts.json
new file mode 100644
index 0000000..caf7edc
--- /dev/null
+++ b/configs/trees/admission-source-contracts.json
@@ -0,0 +1,169 @@
+{
+  "schema_version": "admission-source-contracts-v1",
+  "repositories": {
+    "chart-desk": "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9",
+    "trading-floor": "d827dd792cbd1d396b4ee325879c63e57388e07a"
+  },
+  "files": [
+    {
+      "repository": "chart-desk",
+      "path": "chartdesk/matrix.py",
+      "git_blob_sha1": "28641487567c457b6922c2a63055659867bb4248",
+      "vendor_path": "trading_system/tree_replay/_vendor/admission_matrix.py",
+      "symbols": [
+        "WEIGHTS",
+        "LOOKBACK",
+        "ToolRead",
+        "_clip",
+        "_atr",
+        "read_tr",
+        "read_supertrend",
+        "read_vwap",
+        "read_structure",
+        "TOOLS",
+        "TFView",
+        "read_tf",
+        "_bar_ts"
+      ],
+      "allowed_imports": "from __future__ import annotations\nfrom dataclasses import dataclass\nfrom . import admission_toolkit as toolkit\nfrom . import tr\nfrom . import atr as tr_atr",
+      "adaptation": "matrix_frame_and_atr_import"
+    },
+    {
+      "repository": "chart-desk",
+      "path": "chartdesk/toolkit.py",
+      "git_blob_sha1": "dede9042db891d9ff2e6d6523918fe6d98b11ab0",
+      "vendor_path": "trading_system/tree_replay/_vendor/admission_toolkit.py",
+      "symbols": [
+        "SUPERTREND_LADDER",
+        "supertrend_ladder",
+        "ladder_state",
+        "vwap_bands"
+      ],
+      "allowed_imports": "from __future__ import annotations\nimport numpy as np\nimport pandas as pd\nfrom . import admission_indicators as I",
+      "adaptation": "none"
+    },
+    {
+      "repository": "chart-desk",
+      "path": "chartdesk/indicators.py",
+      "git_blob_sha1": "672f0428c3a81b86376d4f792ae40ecd174a2025",
+      "vendor_path": "trading_system/tree_replay/_vendor/admission_indicators.py",
+      "symbols": [
+        "rma",
+        "true_range",
+        "atr",
+        "supertrend"
+      ],
+      "allowed_imports": "from __future__ import annotations\nimport numpy as np\nimport pandas as pd\nfrom .indicators import _seeded_recursive",
+      "adaptation": "none"
+    },
+    {
+      "repository": "chart-desk",
+      "path": "chartdesk/entry_quality.py",
+      "git_blob_sha1": "0cd76eb8c607690610f4559e5946a60e8f7647ac",
+      "vendor_path": "trading_system/tree_replay/_vendor/admission_quality.py",
+      "symbols": [
+        "MAX_REJECTION_AGE_S",
+        "LABEL_NO_ANCHOR",
+        "LABEL_NO_TRIGGER",
+        "PREDICATE",
+        "_ANCHOR_PREFIXES",
+        "_PRICE_TAIL",
+        "_NAME_SPLIT",
+        "_COUNT_PREFIX",
+        "anchor_names",
+        "aligned_trigger",
+        "still_defending",
+        "opposing_label",
+        "evaluate",
+        "_rej"
+      ],
+      "allowed_imports": "from __future__ import annotations\nimport re",
+      "adaptation": "none"
+    },
+    {
+      "repository": "trading-floor",
+      "path": "floor/marketclock.py",
+      "git_blob_sha1": "246b01255a2203e2a04c2ef7d549f67087b4f2c9",
+      "vendor_path": "trading_system/tree_replay/_vendor/admission_clocks.py",
+      "symbols": [
+        "TZ",
+        "CLOSE_WEEKDAY,CLOSE_HOUR",
+        "OPEN_WEEKDAY,OPEN_HOUR",
+        "now_il",
+        "is_closed",
+        "WARN_MIN_BEFORE",
+        "minutes_to_close",
+        "entry_blocked"
+      ],
+      "allowed_imports": "from __future__ import annotations\nfrom datetime import datetime\nfrom zoneinfo import ZoneInfo",
+      "adaptation": "required_aware_floor_clock"
+    },
+    {
+      "repository": "chart-desk",
+      "path": "chartdesk/windows.py",
+      "git_blob_sha1": "53453b73e7f0c48647945e7d58ba6b30ed8d4102",
+      "vendor_path": "trading_system/tree_replay/_vendor/admission_clocks.py",
+      "symbols": [
+        "TZ",
+        "HUNT_START_H",
+        "HUNT_END_H",
+        "hunting",
+        "outside_reason"
+      ],
+      "allowed_imports": "",
+      "adaptation": "required_aware_hunting_clock_shared_TZ"
+    },
+    {
+      "repository": "chart-desk",
+      "path": "chartdesk/zones.py",
+      "git_blob_sha1": "92f7b99373b4f266a1d80e2d997b965f973d7698",
+      "vendor_path": "trading_system/tree_replay/_vendor/admission_swing.py",
+      "symbols": [
+        "SWING_K",
+        "_last_swing"
+      ],
+      "allowed_imports": "from __future__ import annotations",
+      "adaptation": "none"
+    },
+    {
+      "repository": "chart-desk",
+      "path": "chartdesk/indicators.py",
+      "git_blob_sha1": "672f0428c3a81b86376d4f792ae40ecd174a2025",
+      "vendor_path": "trading_system/tree_replay/_vendor/indicators.py",
+      "symbols": [
+        "_seeded_recursive",
+        "ema",
+        "stdev"
+      ],
+      "allowed_imports": "from __future__ import annotations\nimport numpy as np\nimport pandas as pd",
+      "adaptation": "none"
+    },
+    {
+      "repository": "chart-desk",
+      "path": "chartdesk/tr.py",
+      "git_blob_sha1": "8297c712d20404880d4d8949e96efbf48613909c",
+      "vendor_path": "trading_system/tree_replay/_vendor/tr.py",
+      "symbols": [
+        "TR_EMAS",
+        "emas",
+        "ema_cloud"
+      ],
+      "allowed_imports": "from __future__ import annotations\nimport pandas as pd\nfrom . import indicators as I",
+      "adaptation": "none"
+    },
+    {
+      "repository": "chart-desk",
+      "path": "chartdesk/tr.py",
+      "git_blob_sha1": "8297c712d20404880d4d8949e96efbf48613909c",
+      "vendor_path": "trading_system/tree_replay/_vendor/atr.py",
+      "symbols": [
+        "atr"
+      ],
+      "allowed_imports": "import pandas as pd",
+      "adaptation": "none"
+    }
+  ],
+  "scope": "Pure original admission calculations on supplied frames and explicit aware clocks; no outer admission, source execution, state replay or labels",
+  "ready_for_replay": false,
+  "ready_for_training": false
+}

warning: in the working copy of 'tools/check_admission_source_parity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tools/check_admission_source_parity.py b/tools/check_admission_source_parity.py
new file mode 100644
index 0000000..79bb395
--- /dev/null
+++ b/tools/check_admission_source_parity.py
@@ -0,0 +1,26 @@
+"""Audit admission calculations from an explicit pinned checkout parent root."""
+
+import argparse
+import json
+from pathlib import Path
+import sys
+
+
+ROOT = Path(__file__).resolve().parents[1]
+if str(ROOT) not in sys.path:
+    sys.path.insert(0, str(ROOT))
+
+from trading_system.tree_spec.admission_source import audit_admission_source
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--source-root", type=Path, required=True,
+                        help="Parent of pinned chart-desk and trading-floor checkouts")
+    report = audit_admission_source(parser.parse_args().source_root)
+    print(json.dumps(report, sort_keys=True, indent=2))
+    return 0 if report["source_subset_verified"] else 2
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())

warning: in the working copy of 'tests/tree_replay/test_admission_calculations.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_admission_calculations.py b/tests/tree_replay/test_admission_calculations.py
new file mode 100644
index 0000000..57f9072
--- /dev/null
+++ b/tests/tree_replay/test_admission_calculations.py
@@ -0,0 +1,223 @@
+"""Synthetic source behavior, with expectations independent of the port."""
+
+from datetime import datetime, timezone
+from importlib import import_module
+import math
+
+import numpy as np
+import pandas as pd
+import pytest
+
+
+@pytest.fixture
+def modules():
+    # Missing modules are an explicit RED assertion, not a collection error.
+    names = ("matrix", "toolkit", "indicators", "quality", "clocks", "swing")
+    result = {}
+    for name in names:
+        try:
+            result[name] = import_module("trading_system.tree_replay._vendor.admission_" + name)
+        except ModuleNotFoundError as exc:
+            pytest.fail(f"Task1 calculation sidecar missing: {exc.name}")
+    return result
+
+
+def frame(prices, *, start="2026-09-07T02:00:00Z", volume=1.0):
+    p = np.asarray(prices, dtype=float)
+    return pd.DataFrame({"open": p, "high": p + 1, "low": p - 1,
+                         "close": p, "volume": volume},
+                        index=pd.date_range(start, periods=len(p), freq="min"))
+
+
+@pytest.mark.parametrize("stamp,reason", [
+    ("2026-09-07T01:59:00+03:00", "01:00 — מחוץ לחלון החיפוש (02:00-21:00)"),
+    ("2026-09-07T02:00:00+03:00", None),
+    ("2026-09-07T20:59:59+03:00", None),
+    ("2026-09-07T21:00:00+03:00", "21:00 — מחוץ לחלון החיפוש (02:00-21:00)"),
+    ("2026-01-05T00:00:00+00:00", None),
+    ("2026-09-06T23:00:00+00:00", None),
+    ("2026-10-25T01:30:00+03:00", "01:00 — מחוץ לחלון החיפוש (02:00-21:00)"),
+    ("2026-10-25T01:30:00+02:00", "01:00 — מחוץ לחלון החיפוש (02:00-21:00)"),
+])
+def test_hunting_exact_boundaries_dst_and_instant_equivalence(modules, stamp, reason):
+    clocks = modules["clocks"]
+    t = datetime.fromisoformat(stamp)
+    assert clocks.outside_reason(t) == reason
+    assert clocks.outside_reason(t.astimezone(timezone.utc)) == reason
+    assert clocks.hunting(t) is (reason is None)
+
+
+@pytest.mark.parametrize("stamp,closed,minutes,blocked", [
+    ("2026-09-11T21:29:59+03:00", False, 90 + 1 / 60, None),
+    ("2026-09-11T21:30:00+03:00", False, 90, "סגירת שבוע בעוד 90 דק' — לא נפתחות עסקאות חדשות (גאפ בפתיחה לא ניתן להגנה בסטופ)"),
+    ("2026-09-11T22:40:00+03:00", False, 20, "סגירת שבוע בעוד 20 דק' — לא נפתחות עסקאות חדשות (גאפ בפתיחה לא ניתן להגנה בסטופ)"),
+    ("2026-09-11T23:00:00+03:00", True, None, "שוק סגור"),
+    ("2026-09-12T12:00:00+03:00", True, None, "שוק סגור"),
+    ("2026-09-13T16:00:00+03:00", True, None, "שוק סגור"),
+    ("2026-09-14T00:59:59+03:00", True, None, "שוק סגור"),
+    ("2026-09-14T01:00:00+03:00", False, None, None),
+    ("2026-01-05T01:00:00+02:00", False, None, None),
+])
+def test_floor_weekend_preclose_and_open_boundaries(modules, stamp, closed, minutes, blocked):
+    clocks = modules["clocks"]
+    t = datetime.fromisoformat(stamp)
+    for instant in (t, t.astimezone(timezone.utc)):
+        assert clocks.is_closed(instant) is closed
+        assert clocks.minutes_to_close(instant) == pytest.approx(minutes)
+        assert clocks.entry_blocked(instant) == blocked
+
+
+@pytest.mark.parametrize("name", ["now_il", "hunting", "outside_reason", "is_closed", "minutes_to_close", "entry_blocked"])
+def test_clock_entry_points_reject_missing_naive_or_invalid_time(modules, name):
+    fn = getattr(modules["clocks"], name)
+    with pytest.raises(TypeError):
+        fn()
+    for value in (None, datetime(2026, 9, 7, 2), "2026-09-07T02:00:00Z", pd.NaT):
+        with pytest.raises((TypeError, ValueError)):
+            fn(value)
+
+
+@pytest.mark.parametrize("prices,directions,strengths,net", [
+    (np.arange(100, 160), [1, 1, 1, 0], [100, 90, 72, 0], 67.25),
+    (np.arange(160, 100, -1), [-1, -1, -1, 0], [100, 90, 72, 0], -67.25),
+    (np.full(60, 100), [0, -1, -1, 0], [20, 90, 100, 0], -41.25),
+])
+def test_matrix_golden_rising_falling_flat_nan(modules, prices, directions, strengths, net):
+    # Linear bars: TR fan=11.25 ATR, z=sqrt(3*59/61)=1.7034199.
+    # Flat VWAP's z is NaN: the source emits short strength 100, not neutral.
+    df = frame(prices)
+    before = df.copy(deep=True)
+    view = modules["matrix"].read_frame(df, "5m", basis_note="supplied")
+    assert view.tf == "5m" and view.basis_note == "supplied"
+    assert view.close == float(prices[-1])
+    assert view.atr == 2
+    assert view.bar_ts == 1788749940.0
+    assert [r.tool for r in view.reads] == ["tr", "supertrend", "vwap", "structure"]
+    assert [r.direction for r in view.reads] == directions
+    assert [r.strength for r in view.reads] == strengths
+    assert view.net == pytest.approx(net)
+    assert view.agree == (directions.count(1), directions.count(-1))
+    pd.testing.assert_frame_equal(df, before)
+
+
+@pytest.mark.parametrize("highs,lows,direction,strength", [
+    ([10, 11], [1, 2], 1, 70), ([11, 10], [2, 1], -1, 70),
+    ([10, 11], [2, 1], 0, 30),
+])
+def test_structure_confirmed_sequences(modules, highs, lows, direction, strength):
+    # Slopes between extrema avoid accidental equal-height plateau pivots.
+    df = frame(np.interp(np.arange(24), [0, 3, 9, 15, 20, 23],
+                         [5, highs[0], lows[0], highs[1], lows[1], 5]))
+    r = modules["matrix"].read_structure(df)
+    assert (r.direction, r.strength) == (direction, strength)
+
+
+def test_matrix_golden_mixed_oscillating_prices(modules):
+    df = frame([100, 102] * 30)
+    view = modules["matrix"].read_frame(df, "15m")
+    assert [r.direction for r in view.reads] == [1, -1, 1, 0]
+    assert [r.strength for r in view.reads] == [5, 90, 55, 30]
+    assert view.net == -10.625
+    assert view.agree == (2, 1)
+    assert view.label() == "ניטרלי"
+    assert view.atr == pytest.approx(3 - (13 / 14) ** 59)
+    assert view.basis_note is None
+
+
+def test_supertrend_fast_flip_keeps_slow_bands_bearish(modules):
+    df = frame([100] * 15 + [103])
+    result = modules["toolkit"].ladder_state(df)
+    assert result["state"] == "pullback"
+    assert result["n_bull"] == 1 and result["n_bands"] == 3
+    assert [b["line"] for b in result["bands"]] == pytest.approx([100.8, 104, 106])
+    assert [b["just_flipped"] for b in result["bands"]] == [True, False, False]
+    assert result["bands"][0]["bars_in_trend"] == 1
+    read = modules["matrix"].read_supertrend(df)
+    assert (read.direction, read.strength) == (0, 16)
+
+
+def test_source_short_history_nan_and_zero_range_are_preserved(modules):
+    matrix = modules["matrix"]
+    df = frame([100])
+    view = matrix.read_frame(df, "5m")
+    assert [r.strength for r in view.reads] == [100, 0, 100, 0]
+    assert [r.direction for r in view.reads] == [0, 0, -1, 0]
+    assert matrix._bar_ts(df.reset_index(drop=True)) == 0
+    df["high"] = df["low"] = 100
+    assert matrix._atr(df) == 1e-9
+    with pytest.raises(IndexError):
+        matrix.read_frame(df.iloc[:0], "5m")
+
+
+def test_vwap_volume_weighting_zero_fallback_and_utc_day_reset(modules):
+    toolkit = modules["toolkit"]
+    df = frame([10, 12, 20, 24], start="2026-09-07T23:58Z", volume=[1, 3, 2, 2])
+    got = toolkit.vwap_bands(df)
+    assert got.vwap.tolist() == [10, 11.5, 20, 22]
+    assert got.sigma.tolist() == pytest.approx([0, math.sqrt(0.75), 0, 2])
+    assert got.z.iloc[1] == pytest.approx(0.5 / math.sqrt(0.75))
+    assert got.upper3.iloc[-1] == 28 and got.lower3.iloc[-1] == 16
+    localized = df.tz_convert("Asia/Jerusalem")
+    assert toolkit.vwap_bands(localized).vwap.tolist() == got.vwap.tolist()
+    for no_vol in (df.assign(volume=0), df.drop(columns="volume")):
+        assert toolkit.vwap_bands(no_vol).vwap.tolist() == [10, 11, 20, 22]
+    df["volume"] = [0, 1, 0, 0]
+    assert toolkit.vwap_bands(df).vwap.isna().tolist() == [True, False, True, True]
+
+
+def test_seeded_supertrend_atr_is_distinct_from_matrix_atr(modules):
+    df = frame([10, 14, 14])
+    seeded = modules["indicators"].atr(df, 3)
+    assert seeded.isna().tolist() == [True, True, False]
+    assert seeded.iloc[-1] == 3
+    # Unseeded ranges [2,5,2], alpha 1/14, last = 2 + 3*13/196.
+    assert modules["matrix"]._atr(df) == pytest.approx(2 + 39 / 196)
+    assert modules["toolkit"].ladder_state(df) == {"available": False}
+
+
+@pytest.mark.parametrize("up", [True, False])
+def test_swing_requires_three_bars_to_right_and_returns_age(modules, up):
+    df = frame([5, 4, 3, 1, 3, 4, 5])
+    if not up:
+        df = frame([5, 6, 7, 9, 7, 6, 5])
+    fn = modules["swing"]._last_swing
+    assert fn(df.iloc[:-1], up) is None
+    assert fn(df, up) == (0.0 if up else 10.0, 3)
+    df.iloc[6, df.columns.get_loc("low" if up else "high")] = 0 if up else 10
+    assert fn(df, up) == (0.0 if up else 10.0, 3)  # ties qualify in source
+
+
+@pytest.mark.parametrize("reasons,names,trigger,shadow", [
+    ([], [], None, True),
+    (["רמה: אין"], [], None, True),
+    (["כניסה: Q-WHOLE · ביטול: PSY-HI"], ["Q-WHOLE"], None, False),
+    (["כניסה בריטסט ל-Q-QUARTER, לא במחיר השוק"], ["Q-QUARTER"], None, False),
+    (["רמה: 3 רמות: D4-HI/PSY-HI/Q-QUARTER"], ["D4-HI", "PSY-HI", "Q-QUARTER"], None, False),
+    (["commitment: כן"], [], "commitment", False),
+    (["תבנית W מאושרת (סגירה מעבר לצוואר)"], [], "confirmed_W", False),
+    (["תבנית W לא מאושרת"], [], None, True),
+    (["תבנית W מתגבשת"], [], None, True),
+    (["מלכודת: היערך לונג"], [], "trap", False),
+])
+def test_quality_named_anchors_and_shadow_are_annotations(modules, reasons, names, trigger, shadow):
+    result = modules["quality"].evaluate(direction="לונג", entry=100, atr=2, reasons=reasons)
+    assert result["anchor_names"] == names
+    assert result["aligned_trigger"] == trigger
+    assert result["shadow_block"] is shadow
+    assert set(result) == {"anchor_names", "aligned_trigger", "aligned_rejection",
+                           "opposing_rejection", "labels", "shadow_block", "predicate"}
+
+
+def test_quality_rejections_are_supplied_not_freshness_filtered_or_vetoes(modules):
+    rej = {"zone_lo": 90, "zone_hi": 95, "gap": 5, "age_s": 99999,
+           "levels": ["A", "B", "C", "D"]}
+    evaluate = modules["quality"].evaluate
+    against = evaluate(direction="שורט", entry=100, atr=2, reasons=[], opposing_rejection=rej)
+    assert against["shadow_block"] is True
+    assert against["opposing_rejection"]["distance_atr"] == 2.5
+    assert against["labels"][-1] == "נגד דחייה טרייה מ־90.00–95.00 (A · B · C)"
+    broken = evaluate(direction="שורט", entry=89, atr=0, reasons=[], opposing_rejection=rej)
+    assert broken["opposing_rejection"] is None
+    aligned = evaluate(direction="שורט", entry=100, atr=0, reasons=[], aligned_rejection=rej)
+    assert aligned["shadow_block"] is False
+    assert aligned["aligned_rejection"]["distance_atr"] is None

warning: in the working copy of 'tests/tree_spec/test_admission_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_spec/test_admission_source.py b/tests/tree_spec/test_admission_source.py
new file mode 100644
index 0000000..524ed8e
--- /dev/null
+++ b/tests/tree_spec/test_admission_source.py
@@ -0,0 +1,215 @@
+"""Audit must reject independent source/dependency/specialization corruption."""
+
+import importlib
+import json
+from pathlib import Path
+import shutil
+import subprocess
+import sys
+
+import pytest
+
+
+ROOT = Path(__file__).resolve().parents[2]
+SOURCE = Path("C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149")
+
+
+@pytest.fixture
+def audit():
+    try:
+        return importlib.import_module("trading_system.tree_spec.admission_source")
+    except ModuleNotFoundError as exc:
+        pytest.fail(f"Task1 source auditor missing: {exc.name}")
+
+
+@pytest.fixture
+def local_copy(tmp_path, monkeypatch, audit):
+    for sub in ("trading_system/tree_replay/_vendor", "configs/trees"):
+        shutil.copytree(ROOT / sub, tmp_path / sub)
+    monkeypatch.setattr(audit, "ROOT", tmp_path)
+    return tmp_path
+
+
+def test_complete_source_closure_is_verified_without_readiness(audit):
+    result = audit.audit_admission_source(SOURCE)
+    assert result["blockers"] == []
+    assert result["source_subset_verified"] is True
+    assert result["ready_for_replay"] is False
+    assert result["ready_for_training"] is False
+
+
+@pytest.mark.parametrize("file,old,new", [
+    ("admission_matrix.py", '"tr": 1.0', '"tr": 9.0'),
+    ("admission_matrix.py", "return num / den", "return num * den"),
+    ("admission_matrix.py", "admission_toolkit as toolkit", "admission_indicators as toolkit"),
+    ("admission_matrix.py", "basis_note=basis_note", "basis_note=None"),
+    ("admission_matrix.py", "bar_ts=_bar_ts(df)", "bar_ts=0.0"),
+    ("admission_toolkit.py", "I.supertrend(df, length, factor)", "I.supertrend(df, length, 1.0)"),
+    ("admission_indicators.py", "return rma(true_range(df), length)", "return true_range(df)"),
+    ("admission_indicators.py", "from .indicators import _seeded_recursive", "from .indicators import ema as _seeded_recursive"),
+    ("indicators.py", "prev = alpha * v[i]", "prev = 0 * v[i]"),
+    ("tr.py", "(5, 13, 50, 200, 800)", "(5, 13, 51, 200, 800)"),
+    ("atr.py", "adjust=False", "adjust=True"),
+    ("admission_clocks.py", "HUNT_START_H = 2", "HUNT_START_H = 3"),
+    ("admission_clocks.py", "now.utcoffset() is None", "False"),
+    ("admission_clocks.py", "return now.astimezone(TZ)", "return datetime.now(TZ)"),
+    ("admission_swing.py", "SWING_K = 3", "SWING_K = 2"),
+    ("admission_quality.py", "not aligned_rejection", "aligned_rejection"),
+])
+def test_vendor_mutations_independently_block(audit, local_copy, file, old, new):
+    path = local_copy / "trading_system/tree_replay/_vendor" / file
+    text = path.read_text(encoding="utf-8")
+    assert old in text, file
+    path.write_text(text.replace(old, new, 1), encoding="utf-8")
+    result = audit.audit_admission_source(SOURCE)
+    assert result["source_subset_verified"] is False
+    assert any("VENDOR_AST_MISMATCH" in b for b in result["blockers"])
+
+
+def test_reordered_vendor_definitions_block(audit, local_copy):
+    path = local_copy / "trading_system/tree_replay/_vendor/admission_matrix.py"
+    text = path.read_text(encoding="utf-8")
+    start, end = text.index("def read_tr("), text.index("def read_supertrend(")
+    text = text[:start] + text[end:] + "\n" + text[start:end]
+    path.write_text(text, encoding="utf-8")
+    assert audit.audit_admission_source(SOURCE)["source_subset_verified"] is False
+
+
+@pytest.mark.parametrize("file", ["admission_matrix.py", "admission_toolkit.py", "admission_indicators.py", "admission_quality.py", "admission_clocks.py", "admission_swing.py", "tr.py", "indicators.py", "atr.py"])
+def test_appended_code_in_every_dependency_is_rejected_without_execution(audit, local_copy, file):
+    path = local_copy / "trading_system/tree_replay/_vendor" / file
+    marker = local_copy / "must-not-exist"
+    text = path.read_text(encoding="utf-8") + f"\nopen({str(marker)!r}, 'w').write('executed')\n"
+    path.write_text(text, encoding="utf-8")
+    result = audit.audit_admission_source(SOURCE)
+    assert result["source_subset_verified"] is False
+    assert not marker.exists()
+
+
+@pytest.mark.parametrize("mutation", ["missing", "syntax", "signature"])
+def test_broken_vendor_is_a_blocked_report(audit, local_copy, mutation):
+    path = local_copy / "trading_system/tree_replay/_vendor/admission_clocks.py"
+    if mutation == "missing":
+        path.unlink()
+    elif mutation == "syntax":
+        path.write_text("def malformed:", encoding="utf-8")
+    else:
+        path.write_text(path.read_text(encoding="utf-8").replace("now: datetime)", "now: datetime = None)"), encoding="utf-8")
+    result = audit.audit_admission_source(SOURCE)
+    assert result["source_subset_verified"] is False
+    assert result["blockers"]
+
+
+@pytest.mark.parametrize("repo", ["chart-desk", "trading-floor"])
+def test_actual_source_identity_is_required(audit, monkeypatch, repo):
+    original = audit._git
+    def wrong_head(path, *args):
+        return "0" * 40 if path.name == repo and args == ("HEAD",) else original(path, *args)
+    monkeypatch.setattr(audit, "_git", wrong_head)
+    assert f"SOURCE_COMMIT_MISMATCH:{repo}" in audit.audit_admission_source(SOURCE)["blockers"]
+
+
+def test_nested_repo_cannot_masquerade_as_root(audit, monkeypatch):
+    original = audit._git
+    def nested(path, *args):
+        return str(path.parent) if args == ("--show-toplevel",) else original(path, *args)
+    monkeypatch.setattr(audit, "_git", nested)
+    result = audit.audit_admission_source(SOURCE)
+    assert "NOT_REPOSITORY_ROOT:chart-desk" in result["blockers"]
+    assert "NOT_REPOSITORY_ROOT:trading-floor" in result["blockers"]
+
+
+def test_runtime_imports_and_calculations_need_no_retained_source_or_io():
+    # A fresh process catches lazy dependencies and accidental source imports.
+    script = '''
+import sys
+import pandas as pd
+from datetime import datetime, timezone
+def guard(event, args):
+    if event == "open":
+        path = str(args[0]).replace("\\\\", "/").lower()
+        if "tr-tree-source-review" in path or "/chartdesk/" in path or "/floor/" in path:
+            raise AssertionError("live source access: " + path)
+    if event.startswith("socket.") or event == "subprocess.Popen":
+        raise AssertionError("external IO: " + event)
+sys.addaudithook(guard)
+from trading_system.tree_replay._vendor import admission_matrix as matrix
+from trading_system.tree_replay._vendor import admission_clocks as clocks
+from trading_system.tree_replay._vendor import admission_quality as quality
+from trading_system.tree_replay._vendor import admission_swing as swing
+df = pd.DataFrame({"open": [100.0]*60, "high": [101.0]*60,
+                   "low": [99.0]*60, "close": [100.0]*60},
+                  index=pd.date_range("2026-09-07", periods=60, freq="min", tz="UTC"))
+assert matrix.read_frame(df, "5m").net == -41.25
+assert clocks.outside_reason(datetime(2026, 9, 7, 12, tzinfo=timezone.utc)) is None
+assert quality.evaluate(direction=None, entry=None, atr=0, reasons=[])["shadow_block"]
+assert swing._last_swing(df, True) == (99.0, 3)
+'''
+    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
+    assert result.returncode == 0, result.stderr
+
+
+@pytest.mark.parametrize("mutation", ["constant", "function", "order", "alias", "clock"])
+def test_source_mutations_never_execute_and_block(audit, monkeypatch, mutation):
+    path = SOURCE / "chart-desk/chartdesk/matrix.py"
+    original = Path.read_text
+    text = original(path, encoding="utf-8")
+    if mutation == "constant":
+        changed = text.replace('"tr": 1.0', '"tr": 2.0')
+    elif mutation == "function":
+        changed = text.replace("return num / den", "return 99")
+    elif mutation == "alias":
+        changed = text.replace("basis, toolkit, tr", "basis, toolkit as tr, tr as toolkit")
+    elif mutation == "clock":
+        path = SOURCE / "trading-floor/floor/marketclock.py"
+        text = original(path, encoding="utf-8")
+        changed = text.replace("now.astimezone(TZ)", "datetime.now(TZ)")
+    else:
+        a, b = text.index("def read_tr("), text.index("def read_supertrend(")
+        changed = text[:a] + text[b:] + "\n" + text[a:b]
+    assert changed != text
+    def read(self, *args, **kwargs):
+        return changed if self == path else original(self, *args, **kwargs)
+    monkeypatch.setattr(Path, "read_text", read)
+    result = audit.audit_admission_source(SOURCE)
+    assert result["source_subset_verified"] is False
+    assert any("SOURCE_BLOB_MISMATCH" in b for b in result["blockers"])
+
+
+@pytest.mark.parametrize("mutation", ["drop_dependency", "blob", "readiness", "invalid_json", "missing"])
+def test_manifest_cannot_narrow_or_redefine_audit(audit, local_copy, mutation):
+    path = local_copy / "configs/trees/admission-source-contracts.json"
+    data = json.loads(path.read_text(encoding="utf-8"))
+    if mutation == "drop_dependency":
+        data["files"].pop()
+    elif mutation == "blob":
+        data["files"][0]["git_blob_sha1"] = "0" * 40
+    elif mutation == "readiness":
+        data["ready_for_replay"] = True
+    if mutation == "missing":
+        path.unlink()
+    else:
+        path.write_text("{" if mutation == "invalid_json" else json.dumps(data), encoding="utf-8")
+    assert audit.audit_admission_source(SOURCE)["source_subset_verified"] is False
+
+
+def test_wrong_root_missing_source_and_wrong_baseline_fail_closed(audit, local_copy, tmp_path):
+    assert audit.audit_admission_source(tmp_path / "missing")["source_subset_verified"] is False
+    assert audit.audit_admission_source(SOURCE / "chart-desk")["source_subset_verified"] is False
+    path = local_copy / "configs/trees/existing-alerts-baseline.json"
+    data = json.loads(path.read_text(encoding="utf-8"))
+    next(row for row in data["repositories"] if row["name"] == "trading-floor")["commit"] = "0" * 40
+    path.write_text(json.dumps(data), encoding="utf-8")
+    assert "BASELINE_COMMIT_MISMATCH:trading-floor" in audit.audit_admission_source(SOURCE)["blockers"]
+
+
+def test_cli_requires_parent_root_and_json_exit_codes(audit, tmp_path):
+    command = [sys.executable, str(ROOT / "tools/check_admission_source_parity.py")]
+    missing_arg = subprocess.run(command, capture_output=True, text=True)
+    assert missing_arg.returncode == 2
+    for root, code in ((SOURCE, 0), (tmp_path, 2)):
+        result = subprocess.run(command + ["--source-root", str(root)], capture_output=True, text=True)
+        assert result.returncode == code, result.stderr
+        report = json.loads(result.stdout)
+        assert report["source_subset_verified"] is (code == 0)
+        assert report["ready_for_replay"] is False

warning: in the working copy of 'docs/architecture/ADMISSION-CALCULATIONS-USAGE.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/docs/architecture/ADMISSION-CALCULATIONS-USAGE.md b/docs/architecture/ADMISSION-CALCULATIONS-USAGE.md
new file mode 100644
index 0000000..47a371d
--- /dev/null
+++ b/docs/architecture/ADMISSION-CALCULATIONS-USAGE.md
@@ -0,0 +1,73 @@
+# Original admission calculation dependencies
+
+Status: implemented and locally verified; independent task/combined review is
+still pending following agent usage-limit termination. This is a private pure
+calculation subset, not the outer producer gate or a replay-ready public adapter.
+
+Pinned sources: chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 and
+trading-floor d827dd792cbd1d396b4ee325879c63e57388e07a.
+
+## Interfaces
+
+Under `trading_system.tree_replay._vendor`:
+
+- `admission_matrix.read_frame(df, tf, basis_note=None)` computes the original
+  TFView, retaining close, TR/SuperTrend/VWAP/structure readings, ATR, bar timestamp,
+  weighted net agreement, label and agree counts. No feed fetch or correction
+  rendering happens. Caller supplies a validated causal frame; this private
+  function does not enforce publication cutoffs or validate a timeframe label.
+- `admission_toolkit` contains original SuperTrend ladder and UTC-day VWAP bands.
+  `admission_indicators` preserves its seeded ATR, separately from the matrix's
+  unseeded TR ATR. Existing audited EMA dependencies remain unchanged.
+- `admission_quality.evaluate` and its original parsers annotate named anchors,
+  triggers and supplied rejections. `shadow_block` is a descriptive hypothetical
+  policy, not a real veto. This function does not select fresh rejection history.
+- `admission_clocks.outside_reason(now)` and `entry_blocked(now)` require aware
+  decision time. Missing/naive time is rejected; no fallback to wall clock.
+  The former uses02:00 inclusive to21:00 exclusive Jerusalem hunting hours;
+  the latter the source weekend/preclose policy. Apply caller ordering when
+  eventually binding them. Neither is a historical market-data session calendar.
+- `admission_swing._last_swing(df, up)` preserves SWING_K3 and exact comparisons.
+  A center needs three bars on its right; its timestamp is not availability.
+
+## Source behavior that must remain visible
+
+Matrix strengths are descriptive, not success probabilities. Source weights:
+TR1.0, SuperTrend0.8, structure0.8, VWAP0.6. The net divides the weighted signed
+strength sum by the sum of included weights. The source post-stop caller and
+lifecycle higher-bias caller use different decision conditions; this module
+does not replace either caller with one generic gate.
+
+The source VWAP uses equal weights if total volume is zero/missing, groups by
+UTC date, and may yield NaN z on a zero-variance day. In `read_vwap`, source NaN
+comparisons then yield direction-1 and strength100 rather than an unavailable
+reading. A synthetic60-flat-bar frame produces net-41.25 across the full matrix.
+The one-bar warmup also retains source-specific NaN behavior. These are measured
+code behaviors, not sensible probability estimates or validated trading edge.
+They are intentionally not silently repaired in a pinned-baseline port. The
+future public frame/feature binding must expose data-quality/anomaly provenance;
+changing the source decision itself is a separately named variant.
+
+## Audit and verification
+
+`configs/trees/admission-source-contracts.json` records source blobs, ordered
+definitions, dependency modules/imports and allowed specializations. The auditor
+has an independent fixed closure, so editing the manifest cannot narrow checks.
+It reads source as inert text, checks repository roots/HEADs/blob hashes, and
+compares full ordered vendor ASTs including shared EMA/TR dependencies. It never
+imports or executes the retained live desks. Runtime calculations work without
+the retained checkout; the audit requires it explicitly.
+
+```powershell
+python -m pytest tests/tree_replay/test_admission_calculations.py tests/tree_spec/test_admission_source.py -q --tb=short
+python tools/check_admission_source_parity.py --source-root 'C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'
+```
+
+Local recovery verification:93tests passed; source_subset_verifiedtrue, empty
+blockers, readinessfalse. Worker RED evidence/report was not recovered, so no
+claim is made about its completed TDD process. See latest exchange status for
+review/acceptance rather than inferring acceptance from test counts.
+
+Still required: causal frame binding, full rejection-log prefix/tail selection,
+actual tracker/episode gates and recording, source lifecycle transitions,
+other producers/arbitration, simulator, real data, labels and trained models.




warning: in the working copy of 'trading_system/tree_replay/state.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/state.py b/trading_system/tree_replay/state.py
new file mode 100644
index 0000000..391423e
--- /dev/null
+++ b/trading_system/tree_replay/state.py
@@ -0,0 +1,263 @@
+"""Causal supplied advisory-memory evidence, not a tracker or trade simulator.
+
+Completeness and provenance are caller attestations. No disk, wall clock, feed,
+or trading service is accessed. Fixed-TP1 economic state is deliberately excluded.
+"""
+
+from dataclasses import dataclass, fields
+from datetime import datetime, timezone
+from decimal import Decimal
+import hashlib
+import json
+from math import isfinite
+
+from .bars import _utc
+
+
+_SCHEMA = 'causal-admission-memory-v1'
+_CHECKPOINT_SCHEMA = 'causal-admission-memory-checkpoint-v1'
+_ORIGIN = 'supplied_source_advisory'
+_STREAMS = ('tracker', 'episode', 'rejection')
+_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
+
+
+def _identity(value, field):
+    if type(value) is not str or not value or value != value.strip():
+        raise ValueError(f'{field} must be a nonempty trimmed string')
+
+
+def _json_text(value):
+    try:
+        text = json.dumps(value, sort_keys=True, separators=(',', ':'),
+                          ensure_ascii=False, allow_nan=False)
+        text.encode('utf-8')
+        return text
+    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
+        raise ValueError('memory must contain finite UTF-8 JSON values') from exc
+
+
+def _hash(value):
+    return hashlib.sha256(_json_text(value).encode('utf-8')).hexdigest()
+
+
+def _pairs(pairs):
+    result = {}
+    for key, value in pairs:
+        if key in result:
+            raise ValueError('duplicate JSON key')
+        result[key] = value
+    return result
+
+
+def _constant(value):
+    raise ValueError(f'nonfinite JSON constant: {value}')
+
+
+def _payload(text, stream, observed_at):
+    if type(text) is not str:
+        raise ValueError('payload_json must be text')
+    try:
+        result = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
+    except (ValueError, RecursionError) as exc:
+        raise ValueError('payload_json must be unambiguous finite JSON') from exc
+    if type(result) is not dict:
+        raise ValueError('payload_json must encode an object')
+    normalized = _json_text(result)
+    elapsed = observed_at - _EPOCH
+    elapsed_us = (elapsed.days * 86400 + elapsed.seconds) * 1_000_000 + elapsed.microseconds
+    # Decimal string construction is exact regardless of caller precision;
+    # Decimal division/addition would round under an ambient low-precision context.
+    observed_epoch = Decimal(f'{elapsed_us}e-6')
+    time_fields = ('ts', 'resolved_ts') if stream == 'tracker' else ('ts',)
+    # Compare the JSON decimal, not binary float expansion. An ordinary source
+    # timestamp ending .123456 otherwise expands just past that microsecond.
+    # Parsing original text also prevents finer future fractions being rounded
+    # down by json.loads before this causal check.
+    epoch_values = json.loads(text, parse_float=Decimal)
+    stored_epochs = json.loads(normalized, parse_float=Decimal)
+    for name in time_fields:
+        if name not in result:
+            continue
+        value = result[name]
+        if type(value) not in (int, float) or (type(value) is float and not isfinite(value)):
+            raise ValueError(f'payload {name} must be a finite numeric epoch')
+        if Decimal(epoch_values[name]) > observed_epoch:
+            raise ValueError(f'payload {name} cannot exceed observed_at')
+        if Decimal(stored_epochs[name]) != Decimal(epoch_values[name]):
+            raise ValueError(f'payload {name} loses precision during JSON normalization')
+    return normalized
+
+
+@dataclass(frozen=True, kw_only=True)
+class MemoryEvent:
+    """One fully observed source-row replacement or append-only rejection."""
+
+    event_id: str
+    sequence: int
+    stream: str
+    key: str
+    observed_at: datetime
+    available_at: datetime
+    payload_json: str
+
+    def __post_init__(self):
+        _identity(self.event_id, 'event_id')
+        _identity(self.key, 'key')
+        if type(self.sequence) is not int or self.sequence < 0:
+            raise ValueError('sequence must be a native nonnegative integer')
+        if type(self.stream) is not str or self.stream not in _STREAMS:
+            raise ValueError('stream must be tracker, episode or rejection')
+        if self.stream == 'rejection' and self.key != self.event_id:
+            raise ValueError('rejection key must equal event_id')
+        for name in ('observed_at', 'available_at'):
+            object.__setattr__(self, name, _utc(getattr(self, name), name))
+        if self.available_at < self.observed_at:
+            raise ValueError('available_at cannot precede observed_at')
+        object.__setattr__(self, 'payload_json',
+                           _payload(self.payload_json, self.stream, self.observed_at))
+
+
+@dataclass(frozen=True, kw_only=True)
+class MemoryJournal:
+    """Append-ordered evidence and explicit bounded completeness attestation."""
+
+    journal_id: str
+    origin: str
+    start_at: datetime
+    covered_through: datetime
+    complete: bool
+    events: tuple[MemoryEvent, ...]
+
+    def __post_init__(self):
+        _identity(self.journal_id, 'journal_id')
+        if type(self.origin) is not str or self.origin != _ORIGIN:
+            raise ValueError('origin must be supplied_source_advisory')
+        if type(self.complete) is not bool:
+            raise ValueError('complete must be an explicit bool')
+        for name in ('start_at', 'covered_through'):
+            object.__setattr__(self, name, _utc(getattr(self, name), name))
+        if self.covered_through < self.start_at:
+            raise ValueError('covered_through cannot precede start_at')
+        if type(self.events) is not tuple:
+            raise ValueError('events must be an immutable tuple')
+        seen = set()
+        previous = None
+        for event in self.events:
+            if type(event) is not MemoryEvent:
+                raise ValueError('events must contain exact MemoryEvent objects')
+            if event.event_id in seen:
+                raise ValueError('duplicate event_id')
+            seen.add(event.event_id)
+            if previous is not None and (event.sequence <= previous.sequence
+                    or event.available_at < previous.available_at):
+                raise ValueError('events must preserve increasing sequence/publication order')
+            if event.observed_at < self.start_at or event.available_at > self.covered_through:
+                raise ValueError('events lie outside declared journal coverage')
+            previous = event
+
+
+def _journal(value):
+    if type(value) is not MemoryJournal:
+        raise ValueError('journal must be an exact MemoryJournal')
+
+
+def _event_record(event):
+    return {field.name: (getattr(event, field.name).isoformat()
+                        if field.name in ('observed_at', 'available_at')
+                        else getattr(event, field.name)) for field in fields(MemoryEvent)}
+
+
+def memory_asof(journal: MemoryJournal, decision_time: datetime) -> dict:
+    """Project only available evidence; revisions never backdate a state row."""
+    _journal(journal)
+    decision_time = _utc(decision_time, 'decision_time')
+    blocker = None
+    if not journal.complete:
+        blocker = 'INCOMPLETE_HISTORY'
+    elif decision_time < journal.start_at:
+        blocker = 'BEFORE_COVERAGE'
+    elif decision_time > journal.covered_through:
+        blocker = 'AFTER_COVERAGE'
+    result = dict(schema=_SCHEMA, status='UNAVAILABLE' if blocker else 'AVAILABLE',
+        blocker=blocker, decision_time=decision_time.isoformat(),
+        journal_id=journal.journal_id, origin=journal.origin,
+        start_at=journal.start_at.isoformat(),
+        tracker_state=None if blocker else {}, episode_state=None if blocker else {},
+        rejection_events=None if blocker else [], selected_event_ids=[], event_trace=[],
+        tradeable=False, replay_ready=False, training_ready=False)
+    if not blocker:
+        for event in journal.events:
+            if event.available_at > decision_time:
+                break
+            value = json.loads(event.payload_json)
+            if event.stream == 'rejection':
+                result['rejection_events'].append(value)
+            else:
+                result[f'{event.stream}_state'][event.key] = value
+            result['selected_event_ids'].append(event.event_id)
+            trace = _event_record(event)
+            trace['payload_hash'] = _hash(value)
+            del trace['payload_json']
+            result['event_trace'].append(trace)
+    result['evaluation_hash'] = _hash(result)
+    return result
+
+
+def checkpoint_memory(journal: MemoryJournal) -> dict:
+    """Serialize the entire supplied journal, not an engine checkpoint."""
+    _journal(journal)
+    data = dict(journal_id=journal.journal_id, origin=journal.origin,
+                start_at=journal.start_at.isoformat(),
+                covered_through=journal.covered_through.isoformat(),
+                complete=journal.complete,
+                events=[_event_record(event) for event in journal.events])
+    result = dict(schema=_CHECKPOINT_SCHEMA, journal=data)
+    result['checksum'] = _hash(result)
+    return result
+
+
+def _keys(value, expected, name):
+    if type(value) is not dict or set(value) != set(expected):
+        raise ValueError(f'{name} has an invalid structure')
+
+
+def _parse_time(value, name):
+    if type(value) is not str:
+        raise ValueError(f'{name} must be an ISO timestamp')
+    try:
+        result = _utc(datetime.fromisoformat(value), name)
+    except (TypeError, ValueError, OverflowError) as exc:
+        raise ValueError(f'{name} must be an aware ISO timestamp') from exc
+    # Checkpoints use the exact canonical serializer. In particular, never
+    # truncate nanosecond strings accepted by datetime.fromisoformat.
+    if result.isoformat() != value:
+        raise ValueError(f'{name} must use canonical microsecond-exact UTC encoding')
+    return result
+
+
+def restore_memory(checkpoint: dict) -> MemoryJournal:
+    """Validate version/checksum/types, then reconstruct through public contracts."""
+    _keys(checkpoint, ('schema', 'journal', 'checksum'), 'checkpoint')
+    if checkpoint['schema'] != _CHECKPOINT_SCHEMA:
+        raise ValueError('unsupported memory checkpoint schema')
+    content = {key: checkpoint[key] for key in ('schema', 'journal')}
+    if type(checkpoint['checksum']) is not str or checkpoint['checksum'] != _hash(content):
+        raise ValueError('invalid memory checkpoint checksum')
+    data = checkpoint['journal']
+    _keys(data, (f.name for f in fields(MemoryJournal)), 'journal')
+    if type(data['events']) is not list:
+        raise ValueError('checkpoint events must be a list')
+    events = []
+    for row in data['events']:
+        _keys(row, (f.name for f in fields(MemoryEvent)), 'event')
+        values = dict(row)
+        for name in ('observed_at', 'available_at'):
+            values[name] = _parse_time(values[name], name)
+        events.append(MemoryEvent(**values))
+    values = dict(data, events=tuple(events))
+    for name in ('start_at', 'covered_through'):
+        values[name] = _parse_time(values[name], name)
+    restored = MemoryJournal(**values)
+    if checkpoint_memory(restored) != checkpoint:
+        raise ValueError('checkpoint must use canonical payload encoding')
+    return restored

warning: in the working copy of 'tests/tree_replay/test_state.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_state.py b/tests/tree_replay/test_state.py
new file mode 100644
index 0000000..5e39a5a
--- /dev/null
+++ b/tests/tree_replay/test_state.py
@@ -0,0 +1,311 @@
+"""Synthetic evidence-store tests: publication order, not economic simulation."""
+
+from dataclasses import FrozenInstanceError, replace
+from datetime import datetime, timedelta, timezone
+from decimal import localcontext
+import importlib
+import importlib.util
+import hashlib
+import json
+
+import pandas as pd
+import pytest
+
+
+T = datetime(2026, 9, 7, 10, tzinfo=timezone.utc)
+US = timedelta(microseconds=1)
+HOUR = timedelta(hours=1)
+
+
+def api():
+    name = 'trading_system.tree_replay.state'
+    assert importlib.util.find_spec(name) is not None, 'Missing causal memory adapter'
+    return importlib.import_module(name)
+
+
+def event(**changes):
+    return api().MemoryEvent(**(dict(event_id='e1', sequence=1, stream='tracker',
+        key='trade1', observed_at=T, available_at=T,
+        payload_json='{"state":"PENDING"}') | changes))
+
+
+def journal(events=(), **changes):
+    return api().MemoryJournal(**(dict(journal_id='j1',
+        origin='supplied_source_advisory', start_at=T, covered_through=T + HOUR,
+        complete=True, events=events) | changes))
+
+
+def test_pending_row_is_preserved_without_becoming_open_or_a_label():
+    r = api().memory_asof(journal((event(),)), T)
+    assert r['status'] == 'AVAILABLE'
+    assert r['tracker_state'] == {'trade1': {'state': 'PENDING'}}
+    assert r['episode_state'] == {}
+    assert r['rejection_events'] == []
+    assert r['selected_event_ids'] == ['e1']
+    assert r['tradeable'] is r['training_ready'] is r['replay_ready'] is False
+
+
+def test_delayed_revision_cannot_rewrite_earlier_memory_or_hash():
+    first = event()
+    later = event(event_id='e2', sequence=2, observed_at=T + US,
+                  available_at=T + HOUR, payload_json='{"state":"STOPPED"}')
+    old = api().memory_asof(journal((first,), covered_through=T), T)
+    extended = journal((first, later))
+    assert api().memory_asof(extended, T) == old
+    assert api().memory_asof(extended, T + HOUR - US)['tracker_state']['trade1']['state'] == 'PENDING'
+    assert api().memory_asof(extended, T + HOUR)['tracker_state']['trade1']['state'] == 'STOPPED'
+
+
+def test_equal_publication_instants_use_global_sequence_and_replace_full_rows():
+    a = event(payload_json='{"state":"PENDING","old":true}')
+    b = event(event_id='e2', sequence=2, payload_json='{"state":"OPEN"}')
+    r = api().memory_asof(journal((a, b)), T)
+    assert r['tracker_state'] == {'trade1': {'state': 'OPEN'}}
+    assert r['selected_event_ids'] == ['e1', 'e2']
+
+
+def test_episode_and_rejection_streams_stay_separate_and_rejections_keep_order():
+    events = (event(stream='episode', key='symbol:episode', payload_json='{"entry":10}'),
+              event(event_id='e2', sequence=2, stream='rejection', key='e2', payload_json='{"close":11}'),
+              event(event_id='e3', sequence=3, stream='rejection', key='e3', payload_json='{"close":12}'))
+    r = api().memory_asof(journal(events), T)
+    assert r['tracker_state'] == {}
+    assert r['episode_state'] == {'symbol:episode': {'entry': 10}}
+    assert r['rejection_events'] == [{'close': 11}, {'close': 12}]
+
+
+@pytest.mark.parametrize('time,complete,reason', [
+    (T - US, True, 'BEFORE_COVERAGE'),
+    (T + HOUR + US, True, 'AFTER_COVERAGE'),
+    (T, False, 'INCOMPLETE_HISTORY'),
+])
+def test_unavailable_memory_never_looks_like_usable_empty_state(time, complete, reason):
+    r = api().memory_asof(journal((event(),), complete=complete), time)
+    assert r['status'] == 'UNAVAILABLE'
+    assert r['blocker'] == reason
+    assert r['tracker_state'] is r['episode_state'] is r['rejection_events'] is None
+    assert r['selected_event_ids'] == []
+
+
+@pytest.mark.parametrize('time', [T, T + HOUR])
+def test_explicit_complete_empty_history_is_available_at_inclusive_boundaries(time):
+    r = api().memory_asof(journal(), time)
+    assert r['status'] == 'AVAILABLE'
+    assert r['tracker_state'] == {}
+
+
+def test_source_row_missing_state_remains_visible_for_fail_closed_gate():
+    r = api().memory_asof(journal((event(payload_json='{"symbol":"OANDA:XAUUSD"}'),)), T)
+    assert r['tracker_state'] == {'trade1': {'symbol': 'OANDA:XAUUSD'}}
+
+
+def test_payload_normalization_and_detachment_including_nested_values():
+    e = event(payload_json=' { "state": "OPEN", "x": [false, {"v": 0}] } ')
+    assert e.payload_json == '{"state":"OPEN","x":[false,{"v":0}]}'
+    j = journal((e,))
+    r = api().memory_asof(j, T)
+    r['tracker_state']['trade1']['x'][1]['v'] = 999
+    assert api().memory_asof(j, T)['tracker_state']['trade1']['x'] == [False, {'v': 0}]
+
+
+@pytest.mark.parametrize('payload', [
+    '[]', 'null', '1', '{broken', '{"x":NaN}', '{"x":Infinity}',
+    '{"x":1e999}', '{"x":[{"a":1,"a":2}]}', '{"x":1,"x":2}',
+])
+def test_ambiguous_or_nonfinite_json_is_rejected(payload):
+    with pytest.raises(ValueError):
+        event(payload_json=payload)
+
+
+@pytest.mark.parametrize('field,value', [
+    ('event_id', ''), ('event_id', ' x'), ('event_id', 1),
+    ('sequence', True), ('sequence', -1), ('sequence', 1.0),
+    ('stream', 'economic'), ('stream', []), ('key', ''),
+    ('payload_json', {}), ('observed_at', T.replace(tzinfo=None)),
+    ('available_at', T - US), ('observed_at', pd.Timestamp(T) + pd.Timedelta(nanoseconds=1)),
+])
+def test_invalid_event_contract_is_rejected(field, value):
+    with pytest.raises(ValueError):
+        event(**{field: value})
+
+
+@pytest.mark.parametrize('field,value', [('ts', '123'), ('ts', True),
+    ('ts', None), ('resolved_ts', '123'), ('resolved_ts', True)])
+def test_source_timestamp_fields_must_be_real_finite_epochs(field, value):
+    with pytest.raises(ValueError):
+        event(payload_json=json.dumps({field: value}))
+
+
+@pytest.mark.parametrize('stream,field', [('tracker', 'ts'), ('tracker', 'resolved_ts'),
+    ('episode', 'ts'), ('rejection', 'ts')])
+def test_source_payload_cannot_smuggle_a_future_resolution(stream, field):
+    with pytest.raises(ValueError, match='cannot exceed observed_at'):
+        event(stream=stream, key='e1' if stream == 'rejection' else 'trade1',
+              payload_json=json.dumps({field: (T + HOUR).timestamp()}))
+
+
+def test_rejection_key_must_be_its_append_only_event_id():
+    with pytest.raises(ValueError):
+        event(stream='rejection', key='shared')
+
+
+@pytest.mark.parametrize('events', ['list', 'duplicate_id', 'duplicate_sequence', 'reversed',
+    'reversed_publication', 'before_start', 'beyond_coverage', 'untyped'])
+def test_journal_rejects_corrupt_order_or_coverage_instead_of_sorting(events):
+    a = event()
+    b = event(event_id='e2', sequence=2)
+    cases = {
+        'list': [a], 'duplicate_id': (a, replace(b, event_id='e1')),
+        'duplicate_sequence': (a, replace(b, sequence=1)), 'reversed': (b, a),
+        'reversed_publication': (replace(a, available_at=T + US), b),
+        'before_start': (replace(a, observed_at=T - US),),
+        'beyond_coverage': (replace(a, available_at=T + HOUR + US),),
+        'untyped': ({'state': 'OPEN'},),
+    }
+    with pytest.raises(ValueError):
+        journal(cases[events])
+
+
+@pytest.mark.parametrize('field,value', [('journal_id', ''), ('origin', 'economic_tp1'),
+    ('complete', 1), ('complete', 'true'), ('start_at', T.replace(tzinfo=None)),
+    ('covered_through', T - US)])
+def test_journal_metadata_validation(field, value):
+    with pytest.raises(ValueError):
+        journal(**{field: value})
+
+
+def test_memory_requires_typed_journal_and_exact_aware_decision_time():
+    with pytest.raises(ValueError):
+        api().memory_asof({}, T)
+    with pytest.raises(ValueError):
+        api().memory_asof(journal(), T.replace(tzinfo=None))
+    with pytest.raises(ValueError):
+        api().memory_asof(journal(), pd.Timestamp(T) + pd.Timedelta(nanoseconds=1))
+
+
+def test_checkpoint_json_roundtrip_and_resumed_append_match_continuous_journal():
+    a = event()
+    b = event(event_id='e2', sequence=2, available_at=T + US,
+              observed_at=T + US, payload_json='{"state":"OPEN"}')
+    first = journal((a,), covered_through=T)
+    restored = api().restore_memory(json.loads(json.dumps(api().checkpoint_memory(first))))
+    assert restored == first
+    resumed = replace(restored, events=restored.events + (b,), covered_through=T + HOUR)
+    continuous = journal((a, b))
+    assert api().memory_asof(resumed, T + US) == api().memory_asof(continuous, T + US)
+    assert api().memory_asof(resumed, T) == api().memory_asof(first, T)
+
+
+@pytest.mark.parametrize('mutation', ['payload', 'schema', 'checksum', 'extra', 'missing', 'sequence'])
+def test_checkpoint_tampering_rejected(mutation):
+    c = api().checkpoint_memory(journal((event(),)))
+    if mutation == 'payload':
+        c['journal']['events'][0]['payload_json'] = '{"state":"DONE"}'
+    elif mutation == 'schema':
+        c['schema'] = 'other'
+    elif mutation == 'checksum':
+        c['checksum'] = '0' * 64
+    elif mutation == 'extra':
+        c['unknown'] = True
+    elif mutation == 'missing':
+        del c['journal']['origin']
+    else:
+        c['journal']['events'][0]['sequence'] = True
+    with pytest.raises(ValueError):
+        api().restore_memory(c)
+
+
+def test_events_and_journals_are_frozen_and_checkpoints_detached():
+    e = event()
+    j = journal((e,))
+    with pytest.raises(FrozenInstanceError):
+        e.sequence = 99
+    with pytest.raises(FrozenInstanceError):
+        j.complete = False
+    c = api().checkpoint_memory(j)
+    c['journal']['events'].clear()
+    assert api().memory_asof(j, T)['selected_event_ids'] == ['e1']
+
+
+def test_epoch_json_decimal_at_exact_microsecond_is_not_a_future_event():
+    t = T.replace(microsecond=123456)
+    e = event(observed_at=t, available_at=t,
+              payload_json='{"ts":1788775200.123456}')
+    assert api().memory_asof(journal((e,)), t)['tracker_state']['trade1']['ts'] == 1788775200.123456
+
+
+@pytest.mark.parametrize('epoch', ['1788775200.1234562', '1788775200.12345601'])
+def test_submicrosecond_future_epoch_is_not_rounded_back_into_snapshot(epoch):
+    t = T.replace(microsecond=123456)
+    with pytest.raises(ValueError):
+        event(observed_at=t, available_at=t, payload_json='{"ts":' + epoch + '}')
+
+
+@pytest.mark.parametrize('mutation', ['extra_event_field', 'extra_journal_field',
+    'nanosecond_string', 'naive_string', 'noncanonical_payload', 'bad_sequence',
+    'duplicate_id', 'out_of_coverage', 'wrong_origin', 'bad_events_container'])
+def test_restore_validates_structure_even_when_checksum_is_recomputed(mutation):
+    c = api().checkpoint_memory(journal((event(),)))
+    row = c['journal']['events'][0]
+    if mutation == 'extra_event_field':
+        row['ignored'] = True
+    elif mutation == 'extra_journal_field':
+        c['journal']['ignored'] = True
+    elif mutation == 'nanosecond_string':
+        row['observed_at'] = '2026-09-07T10:00:00.000000001+00:00'
+    elif mutation == 'naive_string':
+        row['observed_at'] = '2026-09-07T10:00:00'
+    elif mutation == 'noncanonical_payload':
+        row['payload_json'] = '{ "state" : "PENDING" }'
+    elif mutation == 'bad_sequence':
+        row['sequence'] = True
+    elif mutation == 'duplicate_id':
+        c['journal']['events'].append(dict(row, sequence=2))
+    elif mutation == 'out_of_coverage':
+        row['available_at'] = (T + HOUR + US).isoformat()
+    elif mutation == 'wrong_origin':
+        c['journal']['origin'] = 'economic_tp1'
+    else:
+        c['journal']['events'] = {}
+    unsigned = {key: c[key] for key in ('schema', 'journal')}
+    c['checksum'] = hashlib.sha256(json.dumps(unsigned, sort_keys=True,
+        separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()
+    with pytest.raises(ValueError):
+        api().restore_memory(c)
+
+
+@pytest.mark.parametrize('precision', [1, 6, 10, 16, 28, 50])
+def test_causal_epoch_boundary_does_not_depend_on_ambient_decimal_precision(precision):
+    t = T.replace(microsecond=900000)
+    with localcontext() as ctx:
+        ctx.prec = precision
+        with pytest.raises(ValueError, match='cannot exceed observed_at'):
+            event(observed_at=t, available_at=t, payload_json='{"ts":1788775200.95}')
+        e = event(observed_at=t, available_at=t, payload_json='{"ts":1788775200.9}')
+        assert e.payload_json == '{"ts":1788775200.9}'
+
+
+def test_rejection_valid_timestamp_reaches_projection():
+    e = event(stream='rejection', key='e1', payload_json='{"ts":1788775200}')
+    assert api().memory_asof(journal((e,)), T)['rejection_events'] == [{'ts': 1788775200}]
+
+
+def test_epoch_that_loses_precision_in_json_normalization_is_rejected_at_ingestion():
+    t = datetime(2255, 1, 1, microsecond=1, tzinfo=timezone.utc)
+    with pytest.raises(ValueError, match='loses precision'):
+        event(observed_at=t, available_at=t, payload_json='{"ts":8993721600.000001}')
+
+
+@pytest.mark.parametrize('precision', [1, 10, 28])
+@pytest.mark.parametrize('t,payload', [
+    (datetime(2255, 1, 1, microsecond=2, tzinfo=timezone.utc), '{"ts":8993721600.000002}'),
+    (datetime(1969, 12, 31, 23, 59, 59, 900000, tzinfo=timezone.utc), '{"ts":-0.1}'),
+])
+def test_representable_epochs_roundtrip_without_numeric_context_dependence(precision, t, payload):
+    with localcontext() as ctx:
+        ctx.prec = precision
+        e = event(observed_at=t, available_at=t, payload_json=payload)
+        j = journal((e,), start_at=t, covered_through=t)
+        restored = api().restore_memory(api().checkpoint_memory(j))
+        assert restored == j
+        assert api().memory_asof(restored, t) == api().memory_asof(j, t)

warning: in the working copy of 'docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md b/docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md
new file mode 100644
index 0000000..6e572ca
--- /dev/null
+++ b/docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md
@@ -0,0 +1,66 @@
+# Causal admission memory evidence
+
+`trading_system.tree_replay.state` is an offline evidence store, not a simulator.
+It preserves what a source-advisory tracker, episode map and rejection log said
+as of a decision. It does not generate their transitions or certify provenance.
+
+```python
+from datetime import datetime, timezone
+from trading_system.tree_replay.state import (
+    MemoryEvent, MemoryJournal, memory_asof, checkpoint_memory, restore_memory,
+)
+
+t = datetime(2026, 9, 7, 10, tzinfo=timezone.utc)
+event = MemoryEvent(
+    event_id='observation-1', sequence=1, stream='tracker', key='trade-1',
+    observed_at=t, available_at=t,
+    payload_json='{"symbol":"OANDA:XAUUSD","state":"PENDING"}',
+)
+journal = MemoryJournal(
+    journal_id='synthetic-example', origin='supplied_source_advisory',
+    start_at=t, covered_through=t, complete=True, events=(event,),
+)
+snapshot = memory_asof(journal, t)
+assert snapshot['tracker_state']['trade-1']['state'] == 'PENDING'
+assert snapshot['replay_ready'] is False
+restored = restore_memory(checkpoint_memory(journal))
+assert restored == journal
+```
+
+## Contracts
+
+- `complete=True` explicitly attests complete state history over
+  `[start_at, covered_through]`. No records plus incomplete history is not empty
+  state. Queries outside coverage return UNAVAILABLE with null state outputs.
+- Event sequence is globally unique/increasing and publication time is
+  nondecreasing. Equal-time sequence order is preserved. Wrong ordering is
+  rejected, never silently sorted. Event IDs are globally unique.
+- Tracker/episode events replace the entire row at `key`. Rejections append,
+  with `key == event_id`. No deletion command or implicit row merge exists.
+- Both timestamps must be aware, microsecond-exact and observed <= available.
+  Numeric source `ts` and tracker `resolved_ts` cannot exceed event observation.
+  Epoch comparison uses original JSON decimal tokens, avoiding binary-float
+  artifacts and rejecting finer future fractions before JSON float rounding.
+  The observation boundary is independent of ambient Decimal precision. If a
+  source epoch cannot retain its decimal value through JSON float normalization,
+  ingestion rejects it explicitly rather than producing an unrestorable journal
+  or silently moving its time. This can exclude extremely precise epoch payloads;
+  it does not infer or round a substitute timestamp.
+- Payload is immutable canonical JSON text. Duplicate keys, nonfinite numbers,
+  non-object roots and non-UTF8 text are rejected. Missing source fields remain
+  visible for downstream source gates to handle; malformed rows are not dropped.
+- Actual T selects published events only. `event_trace` carries their times,
+  sequence, keys and payload hashes. Later publications do not alter an earlier
+  snapshot or its hash. Output objects are detached from journal memory.
+- Checkpoints contain full history with schema/checksum. Restore checks fields,
+  canonical timestamps/payload, ordering and coverage even with a recomputed
+  checksum. This checksum detects corruption, not malicious forgery or false
+  provenance. It is not cryptographic authentication of market history.
+
+The only supported origin is supplied_source_advisory. Do not insert TP1 economic
+exits as source advisory transitions. This component neither evaluates the actual
+OPEN/PENDING exposure gate nor executes post-stop/same-level/episode admission.
+Those gates and source-generated lifecycle replay are the next integration work.
+No real state/log files, market data, labels, model or live service is accessed.
+
+Verification: `python -m pytest tests/tree_replay/test_state.py -q --tb=short`.

