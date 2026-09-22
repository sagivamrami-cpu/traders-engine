"""RVC/GVC, Block Trade and Brinks — from Tino's own checklist PDFs.

These three sat marked ❌ in the tree-coverage audit with the verdict "no
source defines them". **That verdict was wrong, and Sagiv was right to push
back.** I had searched the extracted markdown corpus and stopped there. The
definitions were in the PDF library all along, each with a DEDICATED
checklist:

    Checklist-6-RVC-GVC-Strategy.pdf          (14p)
    Checklist-7-The-Block-Trade-Principle.pdf (11p)
    Checklist-8-The-Brinks-Box-Strategy.pdf   (15p)

The lesson is written into the coverage doc: "not in the corpus" is a claim
about a SEARCH, and a search that covered one of two archives has not earned
that claim.

Citations here are `[C6 p]`, `[C7 p]`, `[C8 p]` — the checklist and its point.
"""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from . import map_sessions as sessions, pattern_tr as tr
from .brinks import BrinksReader
WICK_SYMMETRY_MAX = 2.0
BLOCK_BODY_MIN = 0.6
BLOCK_RANGE_MIN_ATR = 1.0

@dataclass
class RvcGvc:
    """A red-then-green (long) or green-then-red (short) vector formation."""
    direction: str
    name: str
    first_kind: str
    second_kind: str
    recovered: bool
    wick_ok: bool
    bars_ago: int
    price: float

    def line(self) -> str:
        s = f'{self.name} — {self.first_kind}→{self.second_kind} ⇒ {self.direction}'
        if not self.recovered:
            s += ' · השני לא כיסה את הראשון'
        if not self.wick_ok:
            s += ' · פתילים לא סימטריים'
        return s + f'  [C6]'

@dataclass
class Block:
    """A candle whose body says commitment — market memory to retrigger."""
    direction: str
    price_hi: float
    price_lo: float
    body_pct: float
    range_atr: float
    quality: str
    bars_ago: int

    def line(self) -> str:
        return f'בלוק {self.direction} {self.price_lo:,.2f}-{self.price_hi:,.2f} · גוף {self.body_pct * 100:.0f}% · {self.range_atr:.1f} ATR · איכות {self.quality}  [C7]'

def block_quality(df, i: int, atr: float) -> tuple[str, float, float]:
    """Grade one candle as a block. [C7 pt1] big candle, small wicks."""
    h, l = (float(df['high'].iloc[i]), float(df['low'].iloc[i]))
    o, c = (float(df['open'].iloc[i]), float(df['close'].iloc[i]))
    rng = max(h - l, 1e-09)
    body_pct = abs(c - o) / rng
    range_atr = rng / max(atr, 1e-09)
    if body_pct >= BLOCK_BODY_MIN and range_atr >= BLOCK_RANGE_MIN_ATR:
        q = 'טוב'
    elif body_pct >= 0.45:
        q = 'גבולי'
    else:
        q = 'גרוע'
    return (q, body_pct, range_atr)

@dataclass
class BrinksRead:
    """The Brinks Box strategy checklist, walked. [C8]"""
    formed: bool
    box_hi: float | None
    box_lo: float | None
    internal_vectors: list | None
    external_vectors: list | None
    swept_asia: bool | None
    note: str = ''

    def render(self) -> str:
        if not self.formed:
            return f'קופסת ברינקס — {self.note}  [C8 pt1]'
        L = [f'קופסת ברינקס {self.box_lo:,.2f}-{self.box_hi:,.2f}  [C8]']
        if self.internal_vectors is None or self.external_vectors is None:
            L.append('  וקטורים בתוך/מחוץ לקופסה: לא נקראו  [C8 pt2-3]')
        else:
            L.append(f'  וקטורים לא מכוסים בתוך הקופסה: {len(self.internal_vectors)}  [C8 pt2]')
            L.append(f'  וקטורים לא מכוסים מחוץ לקופסה: {len(self.external_vectors)}  [C8 pt3]')
        if self.swept_asia is None:
            L.append('  סחיפת אסיה: לא נקראה  [C8 pt4]')
        elif self.swept_asia:
            L.append('  ⚠ הקופסה סחפה את קצה אסיה — מלכודת נזילות  [C8 pt4]')
        return '\n'.join(L)

class ChecklistReader:

    def __init__(self, source):
        self.source = source
        self.brinks = BrinksReader(source)

    def rvc_gvc(self, symbol: str, timeframe: str='15m') -> RvcGvc | None:
        """The formation on the last two COMPLETED candles, or None.

    Only the last two: [C6 pt6] makes this a same-moment setup — the candle
    after the vector must itself close as a vector. Scanning further back
    would report formations whose trade is long gone.
    """
        try:
            df, corr = self.source.fetch_corrected(symbol, timeframe, 5)
            if corr and getattr(corr, 'unverified', False) or len(df) < 30:
                return None
            pv = tr.pvsra(df)
        except Exception:
            return None
        i = len(df) - 2
        j = i - 1
        if j < 0:
            return None
        a, b = (str(pv['kind'].iloc[j]), str(pv['kind'].iloc[i]))
        reds, greens = (('red', 'violet'), ('green', 'blue'))
        if a in reds and b in greens:
            direction, name = ('לונג', 'RVC')
        elif a in greens and b in reds:
            direction, name = ('שורט', 'GVC')
        else:
            return None
        o1, c1 = (float(df['open'].iloc[j]), float(df['close'].iloc[j]))
        c2 = float(df['close'].iloc[i])
        recovered = c2 >= max(o1, c1) if direction == 'לונג' else c2 <= min(o1, c1)
        h, l = (float(df['high'].iloc[i]), float(df['low'].iloc[i]))
        o2 = float(df['open'].iloc[i])
        up_w, dn_w = (h - max(o2, c2), min(o2, c2) - l)
        lo_w, hi_w = (min(up_w, dn_w), max(up_w, dn_w))
        wick_ok = hi_w <= WICK_SYMMETRY_MAX * lo_w if lo_w > 1e-09 else False
        return RvcGvc(direction, name, a, b, recovered, wick_ok, 1, c2)

    def blocks(self, symbol: str, timeframe: str='15m', lookback: int=60) -> list[Block]:
        """Vector candles that qualify as blocks, newest first. [C7]"""
        try:
            df, corr = self.source.fetch_corrected(symbol, timeframe, 10)
            if corr and getattr(corr, 'unverified', False) or len(df) < 40:
                return []
            pv = tr.pvsra(df)
        except Exception:
            return []
        prev = df['close'].shift(1)
        trng = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
        atr = float(trng.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]) or 1e-09
        out: list[Block] = []
        n = len(df)
        for i in range(max(1, n - lookback), n - 1):
            kind = str(pv['kind'].iloc[i])
            if kind not in ('green', 'red', 'blue', 'violet'):
                continue
            q, body, ratr = block_quality(df, i, atr)
            if q == 'גרוע':
                continue
            out.append(Block('לונג' if kind in ('green', 'blue') else 'שורט', float(df['high'].iloc[i]), float(df['low'].iloc[i]), body, ratr, q, n - 1 - i))
        out.sort(key=lambda b: b.bars_ago)
        return out

    def brinks_read(self, symbol: str, timeframe: str='5m') -> BrinksRead:
        """Walk Tino's four Brinks checklist points.

    [C8 pt1] wait until the box is FORMED (14:00-15:00 GMT). He allows an
             exception for traders who know their asset's box behaviour; we
             do not take it -- an exception granted to experience is not one
             a detector gets to grant itself.
    [C8 pt2] unrecovered vectors INSIDE the box, on 1m/5m/15m.
    [C8 pt3] unrecovered vectors OUTSIDE it -- the targets beyond.
    [C8 pt4] did the box sweep the Asia extreme? Then it is a trap, and the
             read inverts.
    """
        try:
            box = self.brinks.today_box(symbol)
        except Exception:
            return BrinksRead(False, None, None, [], [], False, 'לא ניתן לחשב')
        if box is None:
            return BrinksRead(False, None, None, [], [], False, 'טרם נסגרה — ממתינים (14:00-15:00 GMT)')
        hi, lo = (float(box.hi), float(box.lo))
        inside = outside = None
        try:
            df, _c = self.source.fetch_corrected(symbol, timeframe, 10)
            zones = tr.vector_zones(df)
            inside, outside = ([], [])
            for t, z in zones[zones['open']].iterrows():
                mid = (float(z['top']) + float(z['bottom'])) / 2.0
                rec = {'price': mid, 'kind': str(z['kind']), 'top': float(z['top']), 'bottom': float(z['bottom'])}
                (inside if lo <= mid <= hi else outside).append(rec)
        except Exception:
            inside = outside = None
        swept = None
        try:
            d15, _c = self.source.fetch_corrected(symbol, '15m', 3)
            idx = pd.to_datetime(d15.index, utc=True)
            day = pd.Timestamp(box.formed_at).tz_convert('UTC').date()
            m = [t.date() == day and 0 <= t.hour < 7 for t in idx]
            asia = d15[m]
            if len(asia):
                swept = hi > float(asia['high'].max()) or lo < float(asia['low'].min())
        except Exception:
            swept = None
        return BrinksRead(True, hi, lo, inside, outside, swept)

