"""Pure pinned chart-desk pricing subset; commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9."""

import pandas as pd


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """Canonical Wilder ATR (feature id: tr.atr.wilder.v1)."""
    prev = df["close"].shift(1)
    true_range = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev).abs(),
         (df["low"] - prev).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1 / length, adjust=False).mean()
