"""Pinned movement proof over explicit clocks; not economic success or feed certification."""
from __future__ import annotations
import math
import pandas as pd
from . import lifecycle_voice as voice
VERSION = 'desk-minimum-2026-09-07'
FLOOR = {'OANDA:XAUUSD': ('פיפס', 40.0, 10.0, '{:,.0f} פיפס'), 'OANDA:NAS100USD': ('נק׳', 70.0, 1.0, '{:,.0f} נק׳'), 'BINANCE:BTCUSDT': ('דולר', 200.0, 1.0, '${:,.0f}')}

def minimum(symbol):
    from .basis_symbols import canonical_symbol
    row = FLOOR.get(canonical_symbol(symbol))
    return row[1] / row[2] if row else None

class DeskSuccess:

    def __init__(self, source):
        self.source = source

    def reached(self, t, *, as_of=None):
        """Only this version's identity-bound, chronological proof is sticky."""
        p = t.get('minimum_success') or {}
        try:
            return p['version'] == VERSION and p['trade_id'] == t['trade_id'] and (p['trade_ts'] == float(t['ts'])) and (p['symbol'] == t['symbol']) and (p['minimum_points'] == minimum(t['symbol'])) and (p['source'] in ('verified_post_fill_bars', 'exact_venue_quote')) and (float(t['ts']) <= p['observed_ts'] <= (as_of or self.source.now_epoch())) and (not t.get('resolved_ts') or p['observed_ts'] <= t['resolved_ts']) and math.isfinite(p['price']) and (p['price'] > 0) and ((float(t['entry']) - p['price'] if t['direction'] == 'שורט' else p['price'] - float(t['entry'])) + 1e-09 >= p['minimum_points'])
        except (KeyError, TypeError, ValueError):
            return False

    def observe(self, t, price, observed_ts, source):
        """Caller certifies post-fill ordering and venue; no financial state changes."""
        floor = minimum(t['symbol'])
        if self.reached(t) or floor is None or (not t.get('trade_id')) or (t.get('state') != 'OPEN'):
            return None
        if not all((math.isfinite(float(v)) for v in (price, observed_ts))):
            return None
        moved = float(t['entry']) - price if t['direction'] == 'שורט' else price - float(t['entry'])
        if price <= 0 or moved + 1e-09 < floor:
            return None
        if t.get('targets'):
            final = float(t['targets'][-1][1])
            final_gain = float(t['entry']) - final if t['direction'] == 'שורט' else final - float(t['entry'])
            if final_gain < floor:
                return None
        level = float(t['entry']) + (-floor if t['direction'] == 'שורט' else floor)
        proof = dict(version=VERSION, trade_id=t['trade_id'], trade_ts=float(t['ts']), symbol=t['symbol'], minimum_points=floor, price=level, observed_price=float(price), observed_ts=float(observed_ts), detected_ts=self.source.now_epoch(), source=source)
        candidate = {**t, 'minimum_success': proof}
        if not self.reached(candidate):
            return None
        t['minimum_success'] = proof
        return voice.head('📈', t['symbol'], t['direction'], t['entry'], 'הושג הסף המינימלי · ' + voice.move(t['symbol'], floor)) + f'\n\nרמת הסף: {level:,.2f}\nהעסקה עמדה בסף ההצלחה של הדסק.' + '\n\nקידום סטופ לכניסה וניהול העסקה לשיקולכם.' + '\nהסטופ המקורי והיעדים נשארים במעקב.'

    def observe_bars(self, t, df):
        """Verified caller tape: exclude fill bar and everything from first stop."""
        from . import lifecycle_bars as tracker
        if self.reached(t) or df is None or df.empty:
            return None
        got = tracker.position_bars(df, t, include_fill_bar=True)
        if got is None:
            return None
        bars, first = got
        bars = bars[bars.index <= pd.Timestamp(self.source.now_utc())]
        paying = bars.iloc[1:] if first else bars
        short = t['direction'] == 'שורט'
        stopped = bars['high'] >= float(t['stop']) if short else bars['low'] <= float(t['stop'])
        if stopped.any():
            paying = paying[paying.index < stopped[stopped].index[0]]
        floor = minimum(t['symbol'])
        if floor is None or paying.empty:
            return None
        if t.get('targets'):
            final = float(t['targets'][-1][1])
            final_gain = float(t['entry']) - final if short else final - float(t['entry'])
            if final_gain < floor:
                return None
        column = 'low' if short else 'high'
        gain = float(t['entry']) - paying[column] if short else paying[column] - float(t['entry'])
        hits = paying[gain + 1e-09 >= floor]
        if hits.empty:
            return None
        at = hits.index[0]
        return self.observe(t, float(hits.loc[at, column]), self.source.now_epoch(), 'verified_post_fill_bars')

    def classification(self, t, measurement=None):
        """success / loss / unknown / open / not_entered / other."""
        if self.reached(t):
            return 'success'
        m = measurement or {}
        floor = minimum(t.get('symbol', t.get('canon', '')))
        peak = m.get('peak')
        if floor is not None and peak is not None and math.isfinite(peak):
            if peak + 1e-09 >= floor:
                return 'success'
            if m.get('threshold_ambiguous'):
                return 'unknown'
            if str(t.get('result') or t.get('terminal_result', '')).startswith(('stopped', 'published_stop')) or t.get('state') == 'STOPPED':
                return 'loss'
            if t.get('state') in ('DONE', 'BE', 'CLOSED'):
                return 'below_floor'
        elif t.get('state') in ('STOPPED', 'DONE', 'BE'):
            return 'unknown'
        if t.get('state') == 'OPEN':
            return 'open'
        if t.get('state') in ('PENDING', 'CANCELLED', 'לא נכנסה'):
            return 'not_entered'
        return 'other'

    def stop_note(self, t):
        if not self.reached(t):
            return ''
        return f"\nניתן היה לקדם סטופ לכניסה לאחר {voice.dist(t['symbol'], minimum(t['symbol']))}."
