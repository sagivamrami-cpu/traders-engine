"""Audited pure subset from sagivamrami-cpu/chart-desk, indicators.py.

Pinned commit: 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.
Function bodies retained unchanged; no live source package imports.
Original docstrings describe source intent, not independent chart certification.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _seeded_recursive(src: pd.Series, length: int, alpha: float) -> pd.Series:
    """alpha*src + (1-alpha)*prev, seeded with the SMA of the first `length`.

    This is the shape of both `ta.ema` (alpha = 2/(len+1)) and `ta.rma`
    (alpha = 1/len) in Pine.

    The seed is taken from the first *fully populated* window, not from bars
    0..length-1. Inputs derived from `diff()` start with a NaN, and seeding on
    it would poison the whole recursion -- every later value comes out NaN. Pine
    behaves the same way: `ta.sma` over a window containing `na` is `na`, so
    `ta.rsi` simply starts one bar later than `ta.ema` does.
    """
    v = src.to_numpy(dtype=float)
    n = v.size
    out = np.full(n, np.nan)
    if length < 1 or n < length:
        return pd.Series(out, index=src.index)

    ok = ~np.isnan(v)
    run = 0
    start = -1
    for i in range(n):
        run = run + 1 if ok[i] else 0
        if run == length:
            start = i
            break
    if start < 0:
        return pd.Series(out, index=src.index)

    prev = float(np.mean(v[start - length + 1 : start + 1]))
    out[start] = prev
    for i in range(start + 1, n):
        if np.isnan(v[i]):
            out[i] = prev          # Pine holds the last value through a gap
            continue
        prev = alpha * v[i] + (1.0 - alpha) * prev
        out[i] = prev
    return pd.Series(out, index=src.index)


def ema(src: pd.Series, length: int) -> pd.Series:
    """Pine `ta.ema`: SMA-seeded, alpha = 2/(length+1)."""
    return _seeded_recursive(src, length, 2.0 / (length + 1.0))


def stdev(src: pd.Series, length: int) -> pd.Series:
    """Pine `ta.stdev` uses the population standard deviation (ddof=0)."""
    return src.rolling(length, min_periods=length).std(ddof=0)
