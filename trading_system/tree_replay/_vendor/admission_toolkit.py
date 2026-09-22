from __future__ import annotations
import numpy as np
import pandas as pd
from . import admission_indicators as I


SUPERTREND_LADDER: tuple[tuple[int, float], ...] = ((10, 1.0), (11, 2.0), (12, 3.0))


def supertrend_ladder(
    df: pd.DataFrame, settings: tuple[tuple[int, float], ...] = SUPERTREND_LADDER
) -> pd.DataFrame:
    """All three Supertrends side by side.

    Three bands at rising ATR multiples are not three signals; they are one
    trend measured at three distances. The fast band (x1) is where a pullback in
    a healthy trend stops. The slow band (x3) is where the trend itself is
    wrong. The gap between them is the room a position has to breathe.

    Columns per setting: `st_{len}_{factor}`, `dir_{len}_{factor}`,
    `age_{len}_{factor}`.
    """
    out = pd.DataFrame(index=df.index)
    for length, factor in settings:
        st = I.supertrend(df, length, factor)
        tag = f"{length}_{factor:g}"
        out[f"st_{tag}"] = st["st"]
        out[f"dir_{tag}"] = st["dir"]
        out[f"age_{tag}"] = st["bars_in_trend"]
        out[f"flip_{tag}"] = st["flip"]
    return out


def ladder_state(df: pd.DataFrame, settings=SUPERTREND_LADDER) -> dict:
    """What the ladder is saying right now, including how much it disagrees.

    `agreement` is the interesting field. All three aligned is a trend with
    conviction. Fast flipped against the other two is a pullback — which is the
    entry, not the exit. All three disagreeing is chop, and the correct response
    is to not be in the market.
    """
    lad = supertrend_ladder(df, settings)
    last = lad.iloc[-1]
    price = float(df["close"].iloc[-1])

    rows, dirs = [], []
    for length, factor in settings:
        tag = f"{length}_{factor:g}"
        d = last[f"dir_{tag}"]
        if not np.isfinite(d):
            continue
        dirs.append(int(d))
        rows.append({
            "setting": f"{length}/{factor:g}",
            "line": float(last[f"st_{tag}"]),
            "direction": "bull" if d > 0 else "bear",
            "bars_in_trend": int(last[f"age_{tag}"]),
            "distance_pct": 100.0 * (price - float(last[f"st_{tag}"])) / price,
            "just_flipped": bool(last[f"flip_{tag}"]),
        })

    if not dirs:
        return {"available": False}

    n_bull = sum(1 for d in dirs if d > 0)
    if n_bull == len(dirs):
        state, note = "aligned_bull", "all three bands below price — trend with conviction"
    elif n_bull == 0:
        state, note = "aligned_bear", "all three bands above price — trend with conviction"
    elif dirs[0] != dirs[-1] and len({*dirs[1:]}) == 1:
        state = "pullback"
        note = ("fast band flipped against the slower two — a pullback inside an "
                "intact trend, which is an entry condition, not an exit")
    else:
        state, note = "mixed", "the bands disagree — chop, no trend to trade"

    # the fast/slow gap is the practical stop-room measure
    lines = [r["line"] for r in rows]
    return {
        "available": True,
        "state": state,
        "note": note,
        "bands": rows,
        "band_spread_pct": 100.0 * (max(lines) - min(lines)) / price,
        "n_bull": n_bull,
        "n_bands": len(dirs),
    }


def vwap_bands(
    df: pd.DataFrame,
    *,
    anchor: str = "D",
    source: str = "hlc3",
    multipliers: tuple[float, ...] = (1.0, 2.0, 3.0),
) -> pd.DataFrame:
    """Anchored VWAP with volume-weighted standard-deviation bands.

    Matches the chart: `hlc3` source, bands at 1, 2 and 3 sigma. The deviation
    is **volume-weighted**, not a plain rolling std — that is what makes the
    bands sit where TradingView draws them.

    Bands are the useful part. VWAP itself is a magnet; the 2-sigma band is
    where mean reversion becomes worth a trade, and price outside 3 sigma in a
    session is genuinely rare.
    """
    src = {
        "hlc3": (df["high"] + df["low"] + df["close"]) / 3.0,
        "hl2": (df["high"] + df["low"]) / 2.0,
        "ohlc4": (df["open"] + df["high"] + df["low"] + df["close"]) / 4.0,
        "close": df["close"],
    }.get(source, (df["high"] + df["low"] + df["close"]) / 3.0)

    vol = df["volume"] if "volume" in df else pd.Series(0.0, index=df.index)
    if float(vol.sum()) == 0.0:
        vol = pd.Series(1.0, index=df.index)

    key = df.index.tz_convert("UTC").tz_localize(None).to_period(anchor)
    cum_v = vol.groupby(key).cumsum()
    vwap = (src * vol).groupby(key).cumsum() / cum_v.replace(0.0, np.nan)

    # volume-weighted variance: E[x^2] - (E[x])^2, both volume-weighted
    cum_v2 = (src.pow(2) * vol).groupby(key).cumsum()
    var = (cum_v2 / cum_v.replace(0.0, np.nan)) - vwap.pow(2)
    sigma = np.sqrt(var.clip(lower=0.0))

    out = pd.DataFrame({"vwap": vwap, "sigma": sigma}, index=df.index)
    for m in multipliers:
        out[f"upper{m:g}"] = vwap + sigma * m
        out[f"lower{m:g}"] = vwap - sigma * m
    price = df["close"]
    out["z"] = (price - vwap) / sigma.replace(0.0, np.nan)
    return out
