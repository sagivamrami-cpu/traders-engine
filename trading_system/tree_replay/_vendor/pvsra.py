"""Default non-auction PVSRA specialization from chart-desk tr.py.

Source commit: 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.
Only numpy/pandas are imported. The source's auction=False default makes
auction.resolve_slots return None, leaving vol_x/sv_x unchanged and skipping
both auction/seasonal branches. Those branches, their unused setup, and their
keyword-only parameters are omitted; all retained statement ASTs are exact.
This preserves the source's documented formula, not independent chart parity.
"""

import numpy as np
import pandas as pd


def pvsra(df: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
    """Classify using the pinned source's default non-auction branch only."""
    if "volume" not in df or float(df["volume"].sum()) == 0.0:
        out = pd.DataFrame(index=df.index)
        out["kind"] = np.where(df["close"] >= df["open"], "up", "down")
        out["climax"] = False
        out["rising"] = False
        out["available"] = False
        return out

    vol = df["volume"].astype(float)
    spread = df["high"] - df["low"]
    sv = spread * vol

    avg10 = vol.shift(1).rolling(lookback, min_periods=lookback).mean()
    max_sv10 = sv.shift(1).rolling(lookback, min_periods=lookback).max()
    vol_x, sv_x = vol, sv

    climax = (vol_x >= 2.0 * avg10) | (sv_x >= max_sv10)
    rising = (~climax) & (vol_x >= 1.5 * avg10)
    bull = df["close"] >= df["open"]

    kind = pd.Series("up", index=df.index, dtype=object)
    kind[~bull] = "down"
    kind[climax & bull] = "green"
    kind[climax & ~bull] = "red"
    kind[rising & bull] = "blue"
    kind[rising & ~bull] = "violet"

    out = {
        "kind": kind, "climax": climax.fillna(False), "rising": rising.fillna(False),
        "bull": bull, "volume": vol, "avg_volume_10": avg10,
        "vol_ratio": vol_x / avg10, "spread_volume": sv, "max_sv_10": max_sv10,
        "available": True,
    }

    return pd.DataFrame(out, index=df.index)
