"""Pinned independent verifier over explicit offline ports; no transport or economic fills."""
from __future__ import annotations
import re
from dataclasses import dataclass
import pandas as pd
from .desk_success import DeskSuccess
TOL = {'XAU': 0.5, 'NAS': 3.0, 'BTC': 15.0}

@dataclass
class Verdict:
    ok: bool
    reason: str = ''
    claim: str = ''
    stale: bool = False

    def __bool__(self) -> bool:
        return self.ok

def _tol(symbol: str) -> float:
    u = symbol.upper()
    for k, v in TOL.items():
        if k in u:
            return v
    return 1.0

def _covers(df, when: float | None) -> bool:
    """Does this tape extend past `when`? Unknown times count as covered."""
    if when is None or df is None or df.empty:
        return True
    try:
        last = pd.to_datetime(df.index, utc=True)[-1].timestamp()
    except Exception:
        return True
    return last + 900 >= float(when)

def _fill_index(df, trade: dict):
    """The first bar that touched the entry, located independently.

    Re-derived rather than read from `trade["filled_ts"]`, because a wrong
    fill time is exactly one of the bugs this gate exists to catch.
    """
    try:
        from .pricing import entry_zone
        zlo, zhi = entry_zone(trade['symbol'], float(trade['entry']))
    except Exception:
        e = float(trade['entry'])
        zlo = zhi = e
    idx = pd.to_datetime(df.index, utc=True)
    bar_s = 900.0
    try:
        if len(idx) >= 2:
            bar_s = float((idx[1] - idx[0]).total_seconds()) or 900.0
    except Exception:
        pass
    after = df[[t.timestamp() > float(trade['ts']) - bar_s for t in idx]]
    if after.empty:
        return None
    short = trade['direction'] == 'שורט'
    hit = after['high'] >= zlo if short else after['low'] <= zhi
    return hit.idxmax() if hit.any() else None
_NOT_YET = 'הטייפ עוד לא מכסה את רגע הטענה — ממתין'

def _closed_past(df, when: float) -> bool:
    """Has a bar STAMPED at or after `when` been printed?

    Stricter than _covers on purpose: a contradiction needs the bar that
    contains the moment to be closed, and the only proof of that is the
    next bar. _covers' one-bar slack is right for "has the tape reached the
    fill" and wrong here -- it would call a bar still forming "seen".
    """
    try:
        last = pd.to_datetime(df.index, utc=True)[-1].timestamp()
    except Exception:
        return True
    return last >= float(when)

def _fill_unseen(df, trade: dict) -> bool:
    """No fill on the tape -- but could the tape have shown it yet?

    Codex (2026-09-03): a fill at 04:00:15 and its stop seconds later both
    live in the 04:00 bar. With that bar still forming, _covers says the
    tape reaches the fill (04:00 + 15 min) while the bar has not printed the
    touch -- and the missing fill became a firm "no". The fill bar has to be
    closed before its absence means anything.
    """
    f_ts = trade.get('filled_ts')
    if not _covers(df, f_ts):
        return True
    return bool(f_ts) and (not _closed_past(df, float(f_ts)))

def _frame(df, fill, when: float):
    """Bars from the fill up to the bar that contains `when`, inclusive.

    Codex (2026-09-03): a claim scanned from the fill to the END of the tape,
    so a false 10:00 claim parked as stale was released at 10:20 by a real
    touch that happened twenty minutes after the desk announced it. The
    claim is about a moment; bars opened after that moment cannot have
    caused it.
    """
    aft = df.loc[fill:]
    idx = pd.to_datetime(aft.index, utc=True)
    return aft[[t.timestamp() <= float(when) for t in idx]]

def _extreme(frame, col: str) -> float | None:
    """min of `low` / max of `high` over the frame; None when it is empty."""
    if frame is None or frame.empty:
        return None
    v = float(frame[col].min() if col == 'low' else frame[col].max())
    return None if v != v else v

class ClaimVerifier:

    def __init__(self, source):
        self.source = source
        self.movement = DeskSuccess(source)

    def _bars(self, symbol: str, days: int=3):
        """A fresh, independent fetch. Never the caller's frame.

    VENUE FALLBACK for Binance symbols, added 2026-08-31 after a real
    incident: subscribers got a BTC BUY at 00:22, it filled at 02:28 and
    stopped at 02:36 — and the stop message was BLOCKED here with "הכניסה לא
    מומשה", because the local bar files were gappy (the collector was in a
    reconnect loop dropping short batches) and this verifier saw a tape on
    which the zone was never touched. The gate did exactly what it promises —
    fail closed — but it stayed closed for hours because its ONLY evidence
    source was the broken one. For BINANCE:* the exchange itself publishes
    the identical series (measured 0.00 diff on 1,124 overlapping bars), so
    when the local tape does not cover the claim window, the verifier asks
    the venue directly instead of blocking a true message on our own gap.
    """
        if symbol.upper().startswith('BINANCE:'):
            venue = self._binance_bars(symbol, days)
            if venue is not None:
                return venue
        df, corr = self.source.fetch_corrected(symbol, '15m', days)
        if corr is not None and getattr(corr, 'unverified', False):
            return None
        return df

    def _binance_bars(self, symbol: str, days: int):
        """15m klines straight from the venue — same series as the chart."""
        try:
            sym = symbol.split(':')[-1]
            start = int((pd.Timestamp(self.source.now_utc()) - pd.Timedelta(days=days)).timestamp() * 1000)
            url = f'https://api.binance.com/api/v3/klines?symbol={sym}&interval=15m&startTime={start}&limit=1000'
            rows = self.source.fetch_json(url, timeout=15)
            if not rows:
                return None
            df = pd.DataFrame([[r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4])] for r in rows], columns=['t', 'open', 'high', 'low', 'close'])
            df.index = pd.to_datetime(df['t'], unit='ms', utc=True)
            return df.drop(columns=['t'])
        except Exception:
            return None

    def target(self, trade: dict, price: float) -> Verdict:
        """Did price actually trade through `price` AFTER the entry filled?"""
        claim = f'TP @ {price:,.2f}'
        df = self._bars(trade['symbol'])
        if df is None or df.empty:
            return Verdict(False, 'אין נתונים לאימות', claim)
        fill = _fill_index(df, trade)
        if fill is None:
            if _fill_unseen(df, trade):
                return Verdict(False, 'הטייפ טרם מגיע לרגע המילוי — אי אפשר לאמת עדיין', claim, stale=True)
            return Verdict(False, 'הכניסה לא מומשה בטייפ — לא ייתכן יעד', claim)
        when = self._claim_clock(trade, 'claim_ts')
        aft = _frame(df, fill, when)
        short = trade['direction'] == 'שורט'
        t = _tol(trade['symbol'])
        best = _extreme(aft, 'low' if short else 'high')
        reached = best is not None and (best <= price + t if short else best >= price - t)
        if not reached:
            if not _closed_past(df, when):
                return Verdict(False, _NOT_YET, claim, stale=True)
            seen = f'הקיצון היה {best:,.2f}' if best is not None else 'אין נר'
            return Verdict(False, f'המחיר לא הגיע ל-{price:,.2f} אחרי המילוי ({fill:%H:%M}) — {seen}', claim)
        return Verdict(True, claim=claim)

    def _claim_clock(self, trade: dict, *keys: str) -> float:
        """The moment a claim is about: the first stamped key, else now."""
        for k in keys:
            try:
                v = float(trade.get(k) or 0)
            except (TypeError, ValueError):
                v = 0.0
            if v:
                return v
        return pd.Timestamp(self.source.now_utc()).timestamp()

    def fill(self, trade: dict) -> Verdict:
        """Did price actually reach the entry since the trade was sent?"""
        claim = f"fill @ {float(trade['entry']):,.2f}"
        df = self._bars(trade['symbol'])
        if df is None or df.empty:
            return Verdict(False, 'אין נתונים לאימות', claim)
        if _fill_index(df, trade) is None:
            if not _covers(df, trade.get('filled_ts')):
                last = pd.to_datetime(df.index, utc=True)[-1]
                return Verdict(False, f'הטייפ מסתיים ב-{last:%H:%M} — לפני רגע המילוי. אי אפשר לאמת עדיין', claim, stale=True)
            f_ts = float(trade.get('filled_ts') or trade.get('ts') or 0)
            if f_ts and pd.Timestamp(self.source.now_utc()).timestamp() - f_ts < 45 * 60:
                return Verdict(False, 'הטייפ עוד לא מראה את הנגיעה — ממתין', claim, stale=True)
            return Verdict(False, 'המחיר לא נגע בטווח הכניסה', claim)
        return Verdict(True, claim=claim)

    def stop(self, trade: dict) -> Verdict:
        """Did price actually reach the stop after the fill?"""
        claim = f"stop @ {float(trade['stop']):,.2f}"
        df = self._bars(trade['symbol'])
        if df is None or df.empty:
            return Verdict(False, 'אין נתונים לאימות', claim)
        fill_i = _fill_index(df, trade)
        if fill_i is None:
            if _fill_unseen(df, trade):
                return Verdict(False, 'הטייפ טרם מגיע לרגע המילוי — אי אפשר לאמת עדיין', claim, stale=True)
            return Verdict(False, 'הכניסה לא מומשה — לא ייתכן סטופ', claim)
        when = self._claim_clock(trade, 'resolved_ts', 'claim_ts')
        aft = _frame(df, fill_i, when)
        s = float(trade['stop'])
        short = trade['direction'] == 'שורט'
        t = _tol(trade['symbol'])
        worst = _extreme(aft, 'high' if short else 'low')
        reached = worst is not None and (worst >= s - t if short else worst <= s + t)
        if not reached:
            if not _closed_past(df, when):
                return Verdict(False, _NOT_YET, claim, stale=True)
            return Verdict(False, f'המחיר לא הגיע לסטופ {s:,.2f} אחרי המילוי', claim)
        return Verdict(True, claim=claim)

    def check_message(self, text: str, trade: dict) -> Verdict:
        """Verify an outgoing outcome message against the tape. Never raises.

    Returns ok=True for messages that make no factual claim about a price
    being reached -- a proximity alert or a break-even note describes a state,
    not an event, and there is nothing on the tape to disagree with.
    """
        try:
            t = text.strip()
            if t.startswith('📈') and '· הושג הסף המינימלי ·' in t.splitlines()[0]:
                return Verdict(self.movement.reached(trade), 'minimum requires a valid identity-bound proof')
            if t.startswith('✅'):
                m = re.search('הושג @ ([\\d,]+\\.?\\d*)', t)
                if not m:
                    return Verdict(False, 'טענת יעד ללא מחיר — לא ניתן לאמת')
                return self.target(trade, float(m.group(1).replace(',', '')))
            if t.startswith('▶️'):
                return self.fill(trade)
            if t.startswith('🛑'):
                return self.stop(trade)
            return Verdict(True, 'no factual claim')
        except Exception as e:
            return Verdict(False, f'האימות נכשל: {type(e).__name__}')
