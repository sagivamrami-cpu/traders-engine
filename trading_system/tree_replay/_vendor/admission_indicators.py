from __future__ import annotations
import numpy as np
import pandas as pd
from .indicators import _seeded_recursive


def rma(src: pd.Series, length: int) -> pd.Series:
    """Pine `ta.rma` (Wilder smoothing): SMA-seeded, alpha = 1/length."""
    return _seeded_recursive(src, length, 1.0 / length)


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    return pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """Pine `ta.atr` = `ta.rma(ta.tr(true), length)`."""
    return rma(true_range(df), length)


def supertrend(
    df: pd.DataFrame, length: int = 10, factor: float = 3.0
) -> pd.DataFrame:
    """Pine `ta.supertrend`, band-latching and all.

    Mirrors the reference implementation in the Pine docs::

        upperBand := upperBand < prevUpperBand or close[1] > prevUpperBand
                     ? upperBand : prevUpperBand
        lowerBand := lowerBand > prevLowerBand or close[1] < prevLowerBand
                     ? lowerBand : prevLowerBand

    Pine returns direction -1 for uptrend. That reads backwards everywhere else
    in this codebase, so `dir` here is **+1 bullish / -1 bearish** and the Pine
    value is kept alongside as `pine_dir` for anyone reconciling with a chart.

    Returns columns: st, dir, pine_dir, upper, lower, flip (True on the bar the
    trend changed), bars_in_trend.
    """
    hl2 = (df["high"] + df["low"]) / 2.0
    a = atr(df, length)
    upper_raw = (hl2 + factor * a).to_numpy(dtype=float)
    lower_raw = (hl2 - factor * a).to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    a_arr = a.to_numpy(dtype=float)
    n = len(df)

    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)
    st = np.full(n, np.nan)
    pdir = np.full(n, np.nan)

    prev_upper = prev_lower = np.nan
    prev_st = np.nan
    for i in range(n):
        if np.isnan(a_arr[i]):
            continue
        ub, lb = upper_raw[i], lower_raw[i]
        if not np.isnan(prev_upper):
            if not (ub < prev_upper or close[i - 1] > prev_upper):
                ub = prev_upper
            if not (lb > prev_lower or close[i - 1] < prev_lower):
                lb = prev_lower

        if np.isnan(prev_st):
            d = 1.0                                  # Pine: first bar is 1
        elif prev_st == prev_upper:
            d = -1.0 if close[i] > ub else 1.0
        else:
            d = 1.0 if close[i] < lb else -1.0

        s = lb if d == -1.0 else ub
        upper[i], lower[i], st[i], pdir[i] = ub, lb, s, d
        prev_upper, prev_lower, prev_st = ub, lb, s

    direction = -pdir  # +1 bullish, -1 bearish
    out = pd.DataFrame(
        {"st": st, "dir": direction, "pine_dir": pdir, "upper": upper, "lower": lower},
        index=df.index,
    )
    out["flip"] = out["dir"].ne(out["dir"].shift(1)) & out["dir"].notna() & out["dir"].shift(1).notna()

    # how many bars the current trend has been running -- trend age is the part
    # traders actually act on, and it is tedious to recompute at every call site
    grp = out["flip"].cumsum()
    out["bars_in_trend"] = out.groupby(grp).cumcount() + 1
    out.loc[out["dir"].isna(), "bars_in_trend"] = np.nan
    return out
