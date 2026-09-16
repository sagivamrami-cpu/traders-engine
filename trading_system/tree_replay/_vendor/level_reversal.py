"""Pure detector subset from chart-desk commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.

Copied constants, dataclass and detector helpers retain their source ASTs.
Pricing, live reads and producer arbitration are outside this subset.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import pvsra as tr

# The first production scope is explicit.  Higher-timeframe TR averages are
# now included because Sagiv explicitly added MA reactions as valid reversal
# locations on 07.09.  Quarters and arbitrary session opens remain
# observations until measured.
ELIGIBLE_LEVELS = frozenset({
    "PSY-HI", "PSY-LO",
    "YDAY-HI", "YDAY-LO",
    "LWEEK-HI", "LWEEK-LO",
    "DAY-OPEN",
    "RD-HI", "RD-LO",
    "ADR-HI", "ADR-LO",
})
ELIGIBLE_MA_PREFIXES = (
    "CLOUD50-1h", "CLOUD50-4h",
    "EMA200-1h", "EMA200-4h", "EMA800-1h", "EMA800-4h",
)

SELL_VECTORS = frozenset({"red", "violet"})
BUY_VECTORS = frozenset({"green", "blue"})
TF_MINUTES = {"5m": 5, "15m": 15}
# The five-minute periodic watch is the failover for the close watcher.  Six
# minutes keeps one 300-second fallback pass possible (plus startup/lock
# jitter), while still refusing an old collector backlog.
LIVE_MAX_AGE_S = {"5m": 370.0, "15m": 370.0}


@dataclass(frozen=True)
class Reversal:
    symbol: str
    timeframe: str
    direction: str
    level_name: str
    level_price: float
    approach: str
    pattern: str
    vector_kind: str
    vector_open_time: pd.Timestamp
    confirmation_open_time: pd.Timestamp
    confirmed_at: pd.Timestamp
    sweep_extreme: float
    close: float
    event_id: str


def _utc(value) -> pd.Timestamp:
    out = pd.Timestamp(value)
    return out.tz_localize("UTC") if out.tzinfo is None else out.tz_convert("UTC")


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.index = pd.to_datetime(out.index, utc=True)
    return out[~out.index.duplicated(keep="last")].sort_index()


def is_eligible_level(name: str) -> bool:
    """Approved static or higher-timeframe moving-average location."""
    return str(name) in ELIGIBLE_LEVELS or str(name) in ELIGIBLE_MA_PREFIXES


def _eligible(levels) -> list[tuple[str, float]]:
    rows = []
    for item in levels or []:
        if hasattr(item, "name"):
            name, price = item.name, item.price
        else:
            name, price = item[0], item[1]
        if is_eligible_level(str(name)):
            rows.append((str(name), float(price)))
    return rows


def _episode(symbol: str, direction: str,
             vector_time: pd.Timestamp) -> str:
    # M5 and M15 can describe the same turn.  A 15-minute episode gives both
    # views one identity, so it is published once and still available to the
    # producer-conflict arbiter on the following pass.
    bucket = _utc(vector_time).floor("15min").isoformat()
    return f"{symbol}|{direction}|{bucket}"


def two_bar_signal(prior, vector, confirmation, kind: str,
                   level_price: float) -> tuple[str, str] | None:
    """Pure M5 climax-through-level then commitment rule.

    The M15 one-bar form may use the 150% violet/blue tier because the entire
    15-minute rejection is visible in that bar.  M5 needs the stronger
    red/green climax plus a second commitment candle; accepting ordinary
    rising-volume M5 bars made this net much wider than the observed setup.
    """
    price = float(level_price)
    midpoint = (float(vector.high) + float(vector.low)) / 2.0
    if (kind == "red" and float(prior.close) > price
            and float(vector.low) <= price and float(vector.close) < price
            and float(confirmation.close) > price
            and float(confirmation.close) >= midpoint):
        return "לונג", "two_bar_reclaim"
    if (kind == "green" and float(prior.close) < price
            and float(vector.high) >= price and float(vector.close) > price
            and float(confirmation.close) < price
            and float(confirmation.close) <= midpoint):
        return "שורט", "two_bar_reject"
    return None


def single_bar_signal(prior, bar, kind: str,
                      level_price: float) -> tuple[str, str] | None:
    """Pure M15 sweep-and-reclaim/reject rule."""
    price = float(level_price)
    midpoint = (float(bar.high) + float(bar.low)) / 2.0
    if (kind in SELL_VECTORS and float(prior.close) > price
            and float(bar.low) <= price <= float(bar.close)
            and float(bar.close) >= midpoint):
        return "לונג", "single_bar_reclaim"
    if (kind in BUY_VECTORS and float(prior.close) < price
            and float(bar.high) >= price >= float(bar.close)
            and float(bar.close) <= midpoint):
        return "שורט", "single_bar_reject"
    return None


def detect_frame(symbol: str, timeframe: str, df: pd.DataFrame, levels,
                 *, now=None, max_age_s: float | None = None) -> list[Reversal]:
    """Return every causally confirmed candidate in ``df``.

    ``max_age_s=None`` is the replay/research form.  Live callers pass the
    timeframe's freshness bound so a collector restart cannot resurrect an
    old reversal and publish it as new.
    """
    if timeframe not in TF_MINUTES or df is None or len(df) < 12:
        return []
    frame = _normalise(df)
    now = _utc(pd.Timestamp.now(tz="UTC") if now is None else now)
    delta = pd.Timedelta(minutes=TF_MINUTES[timeframe])
    frame = frame[frame.index + delta <= now]
    if len(frame) < 12:
        return []
    vectors = tr.pvsra(frame)
    candidates: list[Reversal] = []

    def fresh(at: pd.Timestamp) -> bool:
        if max_age_s is None:
            return True
        age = (now - at).total_seconds()
        return 0 <= age <= max_age_s

    def add(direction, level_name, level_price, vector_i, confirm_i,
            pattern, sweep):
        at = frame.index[confirm_i] + delta
        if not fresh(at):
            return
        candidates.append(Reversal(
            symbol=symbol, timeframe=timeframe, direction=direction,
            level_name=level_name, level_price=level_price,
            approach="מלמעלה" if direction == "לונג" else "מלמטה",
            pattern=pattern,
            vector_kind=str(vectors.iloc[vector_i]["kind"]),
            vector_open_time=frame.index[vector_i],
            confirmation_open_time=frame.index[confirm_i],
            confirmed_at=at, sweep_extreme=float(sweep),
            close=float(frame.iloc[confirm_i]["close"]),
            event_id=_episode(symbol, direction, frame.index[vector_i])))

    for name, price in _eligible(levels):
        # Two-stage absorption/sweep then reclaim/rejection.  The vector must
        # actually close through the level; the next bar is the commitment.
        if timeframe == "5m":
            for i in range(2, len(frame)):
                # Missing bars are not adjacent evidence.  A collector gap
                # cannot turn two unrelated prints into a two-candle setup.
                if not (frame.index[i] - frame.index[i - 1] == delta
                        and frame.index[i - 1] - frame.index[i - 2] == delta):
                    continue
                prev, vec, conf = frame.iloc[i - 2], frame.iloc[i - 1], frame.iloc[i]
                kind = str(vectors.iloc[i - 1]["kind"])
                signal = two_bar_signal(prev, vec, conf, kind, price)
                if signal:
                    direction, pattern = signal
                    sweep = vec.low if direction == "לונג" else vec.high
                    add(direction, name, price, i - 1, i, pattern, sweep)

        # A full M15 candle can contain the sweep and reclaim internally.  We
        # accept both climax (red/green) and rising-volume (violet/blue) PVSRA
        # vectors, but still require direction of arrival and a midpoint close.
        if timeframe == "15m":
            for i in range(1, len(frame)):
                if frame.index[i] - frame.index[i - 1] != delta:
                    continue
                prev, bar = frame.iloc[i - 1], frame.iloc[i]
                kind = str(vectors.iloc[i]["kind"])
                signal = single_bar_signal(prev, bar, kind, price)
                if signal:
                    direction, pattern = signal
                    sweep = bar.low if direction == "לונג" else bar.high
                    add(direction, name, price, i, i, pattern, sweep)

    # A confluence can put several eligible names in one candle.  Keep one
    # candidate per episode: the level nearest the confirming close is the
    # actual entry anchor.  Newest decision first for a live caller.
    candidates.sort(key=lambda x: (
        x.confirmed_at,
        -abs(x.close - x.level_price),
        1 if x.timeframe == "5m" else 0,
    ), reverse=True)
    seen, out = set(), []
    for c in candidates:
        key = (c.symbol, c.direction, c.confirmed_at.floor("15min"))
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out
