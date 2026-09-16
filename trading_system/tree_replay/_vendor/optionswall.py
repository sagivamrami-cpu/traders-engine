"""Options positioning bridge with an explicit freshness and mapping contract.

The options desk works in ETF strikes (GLD/QQQ/IBIT), while subscribers trade
XAUUSD/NAS100USD/BTCUSDT. A wall is context, never an executable price. The
conversion ratio is frozen from the report ETF spot and the underlying's
TradingView close at the same market timestamp. It must not be recomputed from
the current spot: doing that made every wall move with price and made a crossing
mathematically impossible.

Fail closed: missing quote timestamps, delayed/historical entitlements, stale
quotes, expired front expiries or an unsynchronised TradingView anchor all
produce None. Options are an optional prior and never block the TR tree.
"""
from __future__ import annotations
import datetime as dt
import json
import math
from dataclasses import dataclass
from zoneinfo import ZoneInfo
import pandas as pd
from io import StringIO
MAX_QUOTE_AGE_MIN = 45.0
MAX_ANCHOR_GAP_MIN = 75.0
ETF_OF = {'OANDA:XAUUSD': 'GLD', 'OANDA:NAS100USD': 'QQQ', 'BINANCE:BTCUSDT': 'IBIT'}
TV_FILE_OF = {'OANDA:XAUUSD': 'XAUUSD_M15.csv', 'OANDA:NAS100USD': 'NAS100_M15.csv', 'BINANCE:BTCUSDT': 'BTCUSD_M15.csv'}

@dataclass(frozen=True)
class Walls:
    symbol: str
    etf: str
    regime: str
    flip: float
    call_wall: float
    put_wall: float
    max_pain: float | None
    positive_gamma: float | None
    negative_gamma: float | None
    ratio: float
    mapped_at: str
    market_asof: str
    age_h: float
    stale: bool = False
    level_source: str = 'open_interest'
    mapping_quality: str = 'approximate_etf_to_underlying'

    def regime_he(self) -> str:
        if self.regime == 'long_gamma':
            return 'גמא ארוכה — הדילרים מרסנים תנועות (טווח/פין)'
        if self.regime == 'short_gamma':
            return 'גמא קצרה — הדילרים מגבירים תנועות (מגמות רצות)'
        return self.regime

    def line(self) -> str:
        value = f'אופציות ({self.etf}, מיפוי מקורב): {self.regime_he()} · קיר OI קולים ~{self.call_wall:,.0f} · קיר OI פוטים ~{self.put_wall:,.0f}'
        if self.flip:
            value += f' · פליפ גמא ~{self.flip:,.0f}'
        return value

@dataclass(frozen=True)
class OptionsStatus:
    usable: bool
    reason: str
    walls: Walls | None = None

def _timestamp(value) -> pd.Timestamp | None:
    if not value:
        return None
    try:
        out = pd.Timestamp(value)
        if out.tzinfo is None:
            return None
        return out.tz_convert('UTC')
    except Exception:
        return None

def _finite(value) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None

def _front_expiry(entry: dict, market_asof: pd.Timestamp) -> dict | None:
    market_day = market_asof.tz_convert(ZoneInfo('America/New_York')).date()
    for expiry in entry.get('expiries') or []:
        try:
            if dt.date.fromisoformat(str(expiry.get('expiry'))) >= market_day:
                return expiry
        except (TypeError, ValueError):
            continue
    return None

class OptionsWallReader:

    def __init__(self, source):
        self.source = source

    def _anchor(self, symbol: str, market_asof: pd.Timestamp) -> tuple[float, pd.Timestamp] | None:
        path = TV_FILE_OF[symbol]
        try:
            frame = pd.read_csv(StringIO(self.source.read_tv_csv(path)))
            idx = pd.to_datetime(frame['time'], utc=True, errors='coerce')
            src = frame.get('src')
            mask = idx.notna() & (idx <= market_asof)
            if src is not None:
                mask &= src.fillna('').astype(str).eq(symbol)
            usable = frame.loc[mask].copy()
            if usable.empty:
                return None
            usable['_ts'] = idx[mask]
            row = usable.sort_values('_ts').iloc[-1]
            stamp = pd.Timestamp(row['_ts'])
            gap = (market_asof - stamp).total_seconds() / 60.0
            price = _finite(row.get('close'))
            if price is None or gap < 0 or gap > MAX_ANCHOR_GAP_MIN:
                return None
            return (price, stamp)
        except (OSError, KeyError, ValueError, pd.errors.ParserError):
            return None

    def status(self, symbol: str, _current_spot: float | None=None, *, now: pd.Timestamp | None=None) -> OptionsStatus:
        """Return a usable prior or a precise fail-closed reason.

    _current_spot is accepted for compatibility but is never used in mapping.
    This is the invariant that lets price cross a fixed wall.
    """
        etf = ETF_OF.get(symbol)
        if not etf:
            return OptionsStatus(False, 'unsupported_symbol')
        files = sorted(self.source.list_reports())
        if not files:
            return OptionsStatus(False, 'no_report')
        try:
            report = json.loads(self.source.read_report(files[-1]))
        except (json.JSONDecodeError, OSError):
            return OptionsStatus(False, 'invalid_report')
        entry = next((item for item in report.get('symbols', []) if item.get('symbol') == etf and (not item.get('degraded'))), None)
        if not entry:
            return OptionsStatus(False, 'missing_or_degraded_symbol')
        market_asof = _timestamp(entry.get('data_asof'))
        if market_asof is None:
            return OptionsStatus(False, 'missing_market_asof')
        permission = str(entry.get('quote_permission') or '')
        if permission != 'realtime_permission':
            return OptionsStatus(False, f"non_realtime_permission:{permission or 'unknown'}")
        clock = pd.Timestamp(self.source.now_utc()) if now is None else pd.Timestamp(now)
        clock = clock.tz_localize('UTC') if clock.tzinfo is None else clock.tz_convert('UTC')
        age_min = (clock - market_asof).total_seconds() / 60.0
        if age_min < -2 or age_min > MAX_QUOTE_AGE_MIN:
            return OptionsStatus(False, f'stale_market_data:{age_min:.1f}m')
        etf_spot = _finite(entry.get('spot'))
        anchor = self._anchor(symbol, market_asof)
        if etf_spot is None or etf_spot <= 0 or anchor is None:
            return OptionsStatus(False, 'missing_synchronised_mapping_anchor')
        under_spot, mapped_at = anchor
        ratio = under_spot / etf_spot
        front = _front_expiry(entry, market_asof)
        if front is None:
            return OptionsStatus(False, 'no_live_expiry')
        oi = front.get('walls') or {}
        calls, puts = (oi.get('call_walls') or [], oi.get('put_walls') or [])
        call = _finite(calls[0].get('strike') if calls else None)
        put = _finite(puts[0].get('strike') if puts else None)
        if call is None or put is None:
            return OptionsStatus(False, 'missing_oi_walls')
        gex = entry.get('gex') or {}
        flip = _finite(gex.get('flip_level'))
        positive = _finite((gex.get('largest_positive') or {}).get('strike'))
        negative = _finite((gex.get('largest_negative') or {}).get('strike'))
        max_pain = _finite(front.get('max_pain'))
        walls = Walls(symbol=symbol, etf=etf, regime=str(gex.get('regime') or 'unknown'), flip=(flip or 0.0) * ratio, call_wall=call * ratio, put_wall=put * ratio, max_pain=max_pain * ratio if max_pain is not None else None, positive_gamma=positive * ratio if positive is not None else None, negative_gamma=negative * ratio if negative is not None else None, ratio=ratio, mapped_at=mapped_at.isoformat(), market_asof=market_asof.isoformat(), age_h=age_min / 60.0)
        return OptionsStatus(True, 'ok', walls)

    def load(self, symbol: str, spot: float) -> Walls | None:
        """Compatibility API used by the tree and trade plan."""
        return self.status(symbol, spot).walls

