from __future__ import annotations


SWING_K = 3


def _last_swing(df, up: bool, k: int = SWING_K) -> tuple[float, int] | None:
    """Most recent confirmed swing low (for an up-extension) or high.

    Confirmed means it has `k` bars either side, so the newest candidate sits at
    index -(k+1) at the earliest. Returning an unconfirmed swing would let a
    detector "break" a level that the next bar redefines.
    """
    hi, lo = df["high"].values, df["low"].values
    n = len(df)
    for i in range(n - k - 1, k - 1, -1):
        window = slice(i - k, i + k + 1)
        if up and lo[i] == min(lo[window]):
            return float(lo[i]), n - 1 - i
        if not up and hi[i] == max(hi[window]):
            return float(hi[i]), n - 1 - i
    return None
