"""Audited pure subset from sagivamrami-cpu/chart-desk, tr.py.

Pinned commit: 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.
Function bodies retained unchanged; no live source package imports.
Original docstrings describe source intent, not independent chart certification.
"""

from __future__ import annotations

import pandas as pd

from . import indicators as I

TR_EMAS: tuple[int, ...] = (5, 13, 50, 200, 800)


def emas(df: pd.DataFrame, lengths: tuple[int, ...] = TR_EMAS) -> pd.DataFrame:
    """The five TR EMAs. **transcribed** (`ta.ema(close, 5|13|50|200|800)`)."""
    return pd.DataFrame(
        {f"ema{n}": I.ema(df["close"], n) for n in lengths}, index=df.index
    )


def ema_cloud(df: pd.DataFrame, length: int = 50) -> pd.DataFrame:
    """The 50-EMA cloud. **transcribed**::

        cloudSize = ta.stdev(close, threeEmaLength * 2) / 4
        upper = ema50 + cloudSize
        lower = ema50 - cloudSize

    Note the stdev window is *double* the EMA length (100 for the 50 EMA) and
    the quarter divisor -- both are easy to get wrong from memory.
    """
    basis = I.ema(df["close"], length)
    size = I.stdev(df["close"], length * 2) / 4.0
    return pd.DataFrame(
        {"basis": basis, "upper": basis + size, "lower": basis - size, "size": size}
    )
