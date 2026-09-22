from __future__ import annotations

import pandas as pd


def daily_pivots(daily: pd.DataFrame, include_m: bool = True) -> dict[str, float]:
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
    h, l, c = float(prev["high"]), float(prev["low"]), float(prev["close"])

    pp = (h + l + c) / 3.0
    r1, s1 = 2 * pp - l, 2 * pp - h
    r2, s2 = pp - s1 + r1, pp - r1 + s1
    r3 = 2 * pp + h - 2 * l
    s3 = 2 * pp - (2 * h - l)

    out = {"PP": pp, "R1": r1, "R2": r2, "R3": r3, "S1": s1, "S2": s2, "S3": s3}
    if include_m:
        ladder = [s3, s2, s1, pp, r1, r2, r3]
        out |= {f"M{i}": (ladder[i] + ladder[i + 1]) / 2.0 for i in range(6)}
    return out


def average_range(
    bars: pd.DataFrame, length: int, *, from_open: bool = False,
    broker_bars: bool = False,
) -> dict[str, float]:
    """ADR / AWR / AMR projection. **reconstructed** (MT4 convention, which TR
    states it takes its defaults from).

    TR ships ADR=14 days, AWR=4 weeks, AMR=6 months.

    Two ways to place the band, both offered by the indicator:

    * default -- anchor on the period's realised extreme, so the band moves as
      the period extends: ``high = low + adr``, ``low = high - adr``.
    * `from_open` -- anchor on the period open and split the range evenly, so
      the band is static for the whole period: ``open ± adr/2``.

    The static version is the more useful one for planning a day in advance; the
    default is the more useful one for asking "how much is left in the tank".
    """
    if len(bars) < length + 1:
        return {"available": False, "n": len(bars)}

    rng = (bars["high"] - bars["low"]).iloc[-(length + 1):-1]
    ar = float(rng.mean())
    cur = bars.iloc[-1]

    if from_open:
        o = float(cur["open"])
        hi, lo = o + ar / 2.0, o - ar / 2.0
    else:
        hi, lo = float(cur["low"]) + ar, float(cur["high"]) - ar
        # THE FORMULA HERE IS FINE. The INPUT BARS were what was wrong.
        #
        # CONFIRMED CORRECT 2026-08-12 once fed his own broker's daily bars
        # (captured by scripts/tv_daily_capture.py). Against his live chart:
        #     yday high/low : 4,435.245 / 4,356.700  -- exact match, 3dp
        #     ADR(14)       : 92.47     vs 92.1-95.7 back-solved from his lines
        #     Hi-ADR        : 4,455.1   vs ~4,456 rendered
        #     Lo-ADR        : 4,332.0   vs ~4,331 rendered
        # The residual is screenshot-reading precision, not formula error.
        #
        # It only goes wrong on a futures PROXY. GC=F prints the COMEX
        # session, his OANDA feed prints 24h spot, so proxy daily ranges came
        # out ~half size (43.5 vs his 78.55 on the same day) and dragged ADR
        # down to 58.4. basis.py's constant offset cannot fix that by
        # construction -- it shifts the level, never the range. Hence
        # `broker_bars`: callers that know the frame came from tv_daily or
        # mt5_broker pass True, and only then are hi/lo/used_pct publishable.
        #
        # Solved 2026-08-12 against Sagiv's real chart. His Hi-ADR/RD-Hi sat
        # ~$36 above our output. Back-solving his two rendered lines
        # independently gave ADR = 95.7 (from his Hi) and 92.1 (from his Lo)
        # -- they agree, which confirms `hi = todayLow + ar` / `lo = todayHigh
        # - ar` is the right construction. What disagrees is `ar` itself:
        # we compute 58.4, his chart implies ~94.
        #
        # Root cause: the Yahoo GC=F daily bars feeding this are the wrong
        # SHAPE, not merely the wrong level. Measured on the same day --
        #     his YDay Hi/Lo : 4,435.245 / 4,356.700  (range 78.55)
        #     our yday Hi/Lo : 4,347.5   / 4,304.0    (range 43.5)
        # GC=F prints the COMEX session, his OANDA feed prints 24h spot, so
        # every daily range comes out roughly half-size and the 14-day mean
        # of them comes out small. basis.py's constant price offset cannot
        # fix this by construction -- it shifts the level, never the range.
        #
        # So the real fix is real broker daily bars (scripts/ExportHistory.mq5
        # into data/mt5/, which basis.fetch_corrected already prefers when
        # present), NOT a different formula here. `verified` stays False
        # while the input is a futures proxy; it should flip to True once
        # the daily bars come from his own broker.

    # transcribed, and applied in both modes exactly as TR_MAIN does:
    #     dayAdrHigh50 = dayAdrHigh - (dayAdr / 2)
    #     dayAdrLow50  = dayAdrLow  + (dayAdr / 2)
    hi50, lo50 = hi - ar / 2.0, lo + ar / 2.0

    note = None
    if from_open and abs(hi50 - lo50) < ar * 1e-9:
        # the two half-lines land on the open together. That follows from the
        # transcribed formula, but whether the chart really draws it that way
        # depends on adrHiLo() inside Traders_Reality_Lib, which is not public.
        note = ("50% lines collapse onto the period open in from-open mode — "
                "verify against the chart before using them as levels")

    used = float(cur["high"] - cur["low"])
    return {
        "available": True, "length": length, "range": ar,
        "high": hi, "low": lo, "high50": hi50, "low50": lo50,
        "used": used, "used_pct": 100.0 * used / ar if ar else None,
        "from_open": from_open, "note": note,
        # True once the bars are his broker's own (tv_daily / mt5_broker).
        # from_open mode is anchored on the open rather than the running
        # extreme, but its width is still the average range, so it needs real
        # bars too. Callers (levelmap.py, tr_scan.py) must not surface
        # high/low/used_pct when this is False.
        "verified": bool(broker_bars),
    }


def range_hilo(bars: pd.DataFrame, length: int, *, from_open: bool = False,
               broker_bars: bool = False) -> dict:
    """RD / RW ("Range Daily / Weekly Hi-Lo"). **transcribed**

    The name misleads: despite "Hi/Lo" these are *not* the highest high and
    lowest low of the window. TR_MAIN computes them with the same library call
    as ADR, only with a different lookback::

        [dayRd,  dayRangeHigh,  dayRangeLow]  = adrHiLo(rdRange, 1, showRDDO)
        [weekRd, weekRangeHigh, weekRangeLow] = adrHiLo(rwRange, 1, showRWWO)

    So RD is the 15-day average range projected exactly like ADR, and RW is the
    13-week equivalent. The shipped lengths differ from ADR/AWR (14 and 4)
    because they come from the Trader At Home PVSRA documentation rather than
    from the MT4 defaults -- two conventions for the same construction, kept
    apart on purpose so you can see when they disagree.
    """
    return average_range(bars, length, from_open=from_open, broker_bars=broker_bars)


def weekly_from_daily(daily: pd.DataFrame) -> pd.DataFrame:
    """Resample daily bars into weekly OHLC, bucketed by the broker's trading
    week, not the raw calendar week.

    Bug caught live 2026-08-13: Sagiv flagged LWEEK-HI on gold as wrong
    (4,395.39 shown vs a real last-completed-week high of 4,371.84). Root
    cause -- broker daily bars are timestamped at the day ROLLOVER (21:00 or
    22:00 UTC, DST-dependent, verified against 301 real bars), so the bar
    that opens the new trading week (Sunday evening) is calendar-dated the
    OLD week's Sunday. A plain ``daily.resample("W")`` buckets by raw
    calendar-Sunday-midnight boundaries and glues that reopening bar onto the
    already-closed previous week, inflating its high/low with a session that
    market-wise belongs to the week that just started.

    Fix: shift every timestamp 3 hours forward before resampling -- enough to
    clear both the 21:00 and 22:00 rollover past calendar midnight into the
    next day, never enough to cross a whole extra day -- so the reopening bar
    lands in the correct (new) week's bucket. The shift only affects which
    bin a bar is grouped into; it is never used as a real timestamp.

    Verified against real OANDA:XAUUSD bars (2026-08-13): fixes lweek high
    4,395.385 -> 4,371.840, matching the true week-of-2026-08-02 high.
    """
    shifted = daily.set_axis(daily.index + pd.Timedelta(hours=3))
    return shifted.resample("W").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()


def monthly_from_daily(daily: pd.DataFrame) -> pd.DataFrame:
    """Resample daily bars into monthly OHLC, same rollover-shift fix as
    ``weekly_from_daily`` -- only matters for the rare bar that lands on the
    last day of a month, but it is the identical bug shape, so it gets the
    identical fix rather than a second silent gap.
    """
    shifted = daily.set_axis(daily.index + pd.Timedelta(hours=3))
    return shifted.resample("MS").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()


def tr_levels(
    daily: pd.DataFrame,
    weekly: pd.DataFrame | None = None,
    monthly: pd.DataFrame | None = None,
    *,
    adr_len: int = 14, awr_len: int = 4, amr_len: int = 6,
    rd_len: int = 15, rw_len: int = 13,
    broker_bars: bool = False,
) -> dict:
    """Every horizontal TR draws, in one dict, with TR's shipped defaults."""
    out: dict = {
        "pivots": daily_pivots(daily),
        "adr": average_range(daily, adr_len, broker_bars=broker_bars),
        "adr_from_open": average_range(daily, adr_len, from_open=True, broker_bars=broker_bars),
        "rd": range_hilo(daily, rd_len, broker_bars=broker_bars),
    }
    if len(daily) >= 2:
        out["yday"] = {
            "high": float(daily["high"].iloc[-2]), "low": float(daily["low"].iloc[-2]),
            "close": float(daily["close"].iloc[-2]),
        }
    if weekly is not None and len(weekly) > awr_len:
        out["awr"] = average_range(weekly, awr_len, broker_bars=broker_bars)
        out["awr_from_open"] = average_range(weekly, awr_len, from_open=True, broker_bars=broker_bars)
        out["rw"] = range_hilo(weekly, rw_len, broker_bars=broker_bars)
        if len(weekly) >= 2:
            out["lweek"] = {
                "high": float(weekly["high"].iloc[-2]),
                "low": float(weekly["low"].iloc[-2]),
            }
    if monthly is not None and len(monthly) > amr_len:
        out["amr"] = average_range(monthly, amr_len)
        out["amr_from_open"] = average_range(monthly, amr_len, from_open=True)
    return out
