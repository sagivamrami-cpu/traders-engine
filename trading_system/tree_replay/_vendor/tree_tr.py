"""Original TR vector zones (default non-auction) and daily pivots."""
import pandas as pd
from .pvsra import pvsra

def vector_zones(df: pd.DataFrame, pv: pd.DataFrame | None=None, *, zone_from: str='body', cleared_by: str='wick', max_zones: int=500) -> pd.DataFrame:
    """Zones left behind by vector (climax) candles, and whether price cleared them.

    **reconstructed** -- TR draws these from the vector candles; the clearing
    rule is a user setting there ("Body only" / "Body with wicks"), mirrored
    here by `zone_from` and `cleared_by`.

    A zone is the body (or full range) of a climax candle. It stays "open" until
    a later bar trades back through it. Open zones below price are demand,
    open zones above are supply -- and an untested one matters more than a
    retested one, so `touches` is counted.
    """
    pv = pvsra(df) if pv is None else pv
    if not bool(pv.get('available', pd.Series([False])).iloc[0]):
        return pd.DataFrame(columns=['top', 'bottom', 'kind', 'open', 'touches', 'time'])
    vec = pv.index[pv['climax'].to_numpy()]
    vec = vec[-max_zones:]
    if len(vec) == 0:
        return pd.DataFrame(columns=['top', 'bottom', 'kind', 'open', 'touches', 'time'])
    o, c = (df['open'], df['close'])
    top = (o.combine(c, max) if zone_from == 'body' else df['high']).loc[vec]
    bottom = (o.combine(c, min) if zone_from == 'body' else df['low']).loc[vec]
    hi = df['high'] if cleared_by == 'wick' else o.combine(c, max)
    lo = df['low'] if cleared_by == 'wick' else o.combine(c, min)
    rows = []
    for t, tp, bt in zip(vec, top.to_numpy(), bottom.to_numpy()):
        after = df.index > t
        if not after.any():
            rows.append((t, tp, bt, pv.loc[t, 'kind'], True, 0))
            continue
        overlaps = ((hi[after] >= bt) & (lo[after] <= tp)).to_numpy()
        departed = ~overlaps
        if departed.any():
            first_out = int(departed.argmax())
            returns = overlaps[first_out:]
            n_touch = int(returns.sum())
        else:
            n_touch = 0
        rows.append((t, float(tp), float(bt), pv.loc[t, 'kind'], n_touch == 0, n_touch))
    out = pd.DataFrame(rows, columns=['time', 'top', 'bottom', 'kind', 'open', 'touches'])
    return out.set_index('time')

def daily_pivots(daily: pd.DataFrame, include_m: bool=True) -> dict[str, float]:
    """Classic floor pivots off the previous daily bar. **transcribed**::

        pivotPoint = (dayHigh + dayLow + dayClose) / 3
        pivR1 = 2 * PP - dayLow          pivS1 = 2 * PP - dayHigh
        pivR2 = PP - pivS1 + pivR1       pivS2 = PP - pivR1 + pivS1
        pivR3 = 2 * PP + dayHigh - 2 * dayLow
        pivS3 = 2 * PP - (2 * dayHigh - dayLow)

    M levels are the midpoints between adjacent levels -- M0 between S3 and S2
    up to M5 between R2 and R3. **reconstructed** (drawn by TR_MAIN, computed in
    the library).
    """
    if len(daily) < 2:
        return {}
    prev = daily.iloc[-2]
    h, l, c = (float(prev['high']), float(prev['low']), float(prev['close']))
    pp = (h + l + c) / 3.0
    r1, s1 = (2 * pp - l, 2 * pp - h)
    r2, s2 = (pp - s1 + r1, pp - r1 + s1)
    r3 = 2 * pp + h - 2 * l
    s3 = 2 * pp - (2 * h - l)
    out = {'PP': pp, 'R1': r1, 'R2': r2, 'R3': r3, 'S1': s1, 'S2': s2, 'S3': s3}
    if include_m:
        ladder = [s3, s2, s1, pp, r1, r2, r3]
        out |= {f'M{i}': (ladder[i] + ladder[i + 1]) / 2.0 for i in range(6)}
    return out
