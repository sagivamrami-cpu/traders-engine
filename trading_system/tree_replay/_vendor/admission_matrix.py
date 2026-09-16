from __future__ import annotations
from dataclasses import dataclass
from . import admission_toolkit as toolkit
from . import tr
from . import atr as tr_atr


WEIGHTS = {"tr": 1.0, "supertrend": 0.8, "structure": 0.8, "vwap": 0.6}


LOOKBACK = {"4h": 240, "1h": 240, "30m": 90, "15m": 55, "5m": 55}


@dataclass
class ToolRead:
    tool: str
    direction: int          # +1 long / -1 short / 0 none
    strength: int           # 0–100, descriptive
    note: str

    def arrow(self) -> str:
        return {1: "▲", -1: "▼", 0: "·"}[self.direction]


def _clip(x: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, x)))


def _atr(df) -> float:
    """Wilder ATR for both the read and the view that carries its scale."""
    return float(tr_atr.atr(df, 14).iloc[-1]) or 1e-9


def read_tr(df) -> ToolRead:
    e = tr.emas(df)
    n = len(df)
    trio = [float(e[f"ema{k}"].iloc[-1]) for k in (5, 13, 50)]
    atr = _atr(df)
    fan_w = abs(trio[0] - trio[2]) / atr
    close = float(df["close"].iloc[-1])
    dev = (close - trio[2]) / atr

    if trio[0] > trio[1] > trio[2]:
        d = 1
    elif trio[0] < trio[1] < trio[2]:
        d = -1
    else:
        return ToolRead("tr", 0, _clip(20 - 10 * fan_w), "ממוצעים דחוסים — אין עניין")
    strength = _clip(30 * fan_w + 10 * min(abs(dev), 3))
    side = "מעל" if close > trio[2] else "מתחת"
    return ToolRead("tr", d, strength,
                    f"מניפה {'בול' if d>0 else 'בר'} w={fan_w:.1f}, מחיר {side} ענן ({dev:+.1f} ATR)")


def read_supertrend(df) -> ToolRead:
    ls = toolkit.ladder_state(df)
    if not ls.get("available"):
        return ToolRead("supertrend", 0, 0, "לא זמין")
    n_bull, n = ls["n_bull"], ls["n_bands"]
    bands = ls.get("bands", [])
    fresh = any(b.get("just_flipped") for b in bands)
    youngest = min((b["bars_in_trend"] for b in bands), default=99)
    spread = ls.get("band_spread_pct", 0)
    if n_bull == n:
        d = 1
    elif n_bull == 0:
        d = -1
    else:
        return ToolRead("supertrend", 0, _clip(25 * max(n_bull, n - n_bull) / n),
                        f"רצועות חלוקות {n_bull}/{n} — מעבר, לא מגמה")
    strength = _clip(50 + 20 * min(spread, 2) + (20 if youngest <= 3 else 0))
    note = f"3/3 רצועות {'בול' if d>0 else 'בר'}, מרווח {spread:.1f}%"
    if fresh:
        note += " · פליפ טרי!"
    return ToolRead("supertrend", d, strength, note)


def read_vwap(df) -> ToolRead:
    vw = toolkit.vwap_bands(df)
    z = float(vw["z"].iloc[-1])
    if abs(z) < 0.3:
        return ToolRead("vwap", 0, 20, f"על ה-VWAP (z={z:+.1f}) — שיווי משקל")
    d = 1 if z > 0 else -1
    stretched = abs(z) > 2
    strength = _clip(30 + 25 * min(abs(z), 3) - (25 if stretched else 0))
    note = f"{'מעל' if d>0 else 'מתחת ל'}ערך, z={z:+.1f}"
    if stretched:
        note += " · מתוח — סיכון חזרה לערך"
    return ToolRead("vwap", d, strength, note)


def read_structure(df, k: int = 3) -> ToolRead:
    hi, lo = df["high"].values, df["low"].values
    highs, lows = [], []
    for i in range(k, len(df) - k):
        if hi[i] == max(hi[i - k:i + k + 1]):
            highs.append(float(hi[i]))
        elif lo[i] == min(lo[i - k:i + k + 1]):
            lows.append(float(lo[i]))
    if len(highs) < 2 or len(lows) < 2:
        return ToolRead("structure", 0, 0, "אין מספיק סווינגים")
    hh, hl = highs[-1] > highs[-2], lows[-1] > lows[-2]
    lh, ll = highs[-1] < highs[-2], lows[-1] < lows[-2]
    if hh and hl:
        return ToolRead("structure", 1, 70, "HH+HL — מבנה עולה")
    if lh and ll:
        return ToolRead("structure", -1, 70, "LH+LL — מבנה יורד")
    return ToolRead("structure", 0, 30, "מבנה מעורב (סווינגים סותרים)")


TOOLS = {"tr": read_tr, "supertrend": read_supertrend,
         "vwap": read_vwap, "structure": read_structure}


@dataclass
class TFView:
    tf: str
    reads: list[ToolRead]
    close: float
    basis_note: str | None = None
    atr: float = 0.0
    bar_ts: float = 0.0     # epoch of the newest bar the reads came from

    @property
    def net(self) -> float:
        """Weighted −100..+100. Descriptive agreement, not a probability."""
        num = sum(r.direction * r.strength * WEIGHTS[r.tool] for r in self.reads)
        den = sum(WEIGHTS[r.tool] for r in self.reads) or 1
        return num / den

    @property
    def agree(self) -> tuple[int, int]:
        longs = sum(1 for r in self.reads if r.direction > 0)
        shorts = sum(1 for r in self.reads if r.direction < 0)
        return longs, shorts

    def label(self) -> str:
        n = self.net
        if n >= 55: return "לונג חזק"
        if n >= 25: return "לונג"
        if n <= -55: return "שורט חזק"
        if n <= -25: return "שורט"
        return "ניטרלי"


def read_frame(df, tf, basis_note=None) -> TFView:
    return TFView(tf=tf, close=float(df["close"].iloc[-1]),
                  reads=[fn(df) for fn in TOOLS.values()], basis_note=basis_note,
                  atr=_atr(df), bar_ts=_bar_ts(df))


def _bar_ts(df) -> float:
    try:
        return float(df.index[-1].timestamp())
    except Exception:
        return 0.0
