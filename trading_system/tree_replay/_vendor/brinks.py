"""The Brinks Box — the strategy Tino ranks above everything else.

> "If I were to pick one strategy from the Hybrid system, not use anything else
> and not trade any other time… it would be the Brinks Box Strategy."
> [Checklist-8 @ p1]

Until 2026-08-26 this existed on the floor only as text in the PDF database —
the corpus's own headline, uncoded. This is the mechanical core:

**The box** forms **14:00–15:00 GMT** (banks open 09:00 ET; the bell 09:30) —
always one hour wide, variable height, same start for all common assets
[Checklist-8 @ p2]. High and low of the completed hour, body AND wick.

**The read, after completion** [Checklist-8 @ p14-p15]:
- unrecovered vectors INSIDE the box are the strategy's core — what the MM
  printed and still owes a recovery;
- the MIDPOINT is the gate: a long needs price holding above it, a short below;
- external vectors away from the box are the destinations.

**What is deliberately left to the human/agent:** which vector to lean on and
the entry itself. Tino calls the whole method discretionary [17 @ 00m50s]; this
module reports the box's facts so the trade engine and the tr-agent can cite
them, and logs a SILENT firing so the family accumulates a sample — his own
build-don't-send rule from 2026-08-13 applies to his favourite strategy too."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import pandas as pd
from . import pattern_tr as tr
BOX_START_H, BOX_END_H = (14, 15)
RELEVANT_UNTIL_H = 20

@dataclass
class Box:
    symbol: str
    hi: float
    lo: float
    close: float
    open_vectors_inside: int | None
    formed_at: str

    @property
    def mid(self) -> float:
        return (self.hi + self.lo) / 2.0

    @property
    def side(self) -> str:
        """Which side of the midpoint price holds — the checklist's gate."""
        if self.close > self.mid:
            return 'לונג'
        if self.close < self.mid:
            return 'שורט'
        return 'על האמצע'

    def line(self) -> str:
        if self.open_vectors_inside is None:
            vec = ' · הווקטורים בתוכה לא נקראו'
        elif self.open_vectors_inside:
            vec = f' · {self.open_vectors_inside} וקטורים לא-משוחזרים בתוכה'
        else:
            vec = ''
        return f"קופסת ברינקס {self.lo:,.2f}–{self.hi:,.2f} · המחיר {('מעל' if self.close > self.mid else 'מתחת ל')}אמצע ({self.mid:,.2f}) ⇒ נטיית {self.side}{vec} [Checklist-8]"

class BrinksReader:

    def __init__(self, source):
        self.source = source

    def today_box(self, symbol: str, now: datetime | None=None) -> Box | None:
        """Today's completed Brinks box, while it is still the session's context.

    None before 15:00 GMT (the box is still forming — rule 1: wait), and after
    20:00 GMT (the session it set up is over)."""
        now = now or self.source.now_utc()
        if not BOX_END_H <= now.hour < RELEVANT_UNTIL_H or now.weekday() >= 5:
            return None
        try:
            df, corr = self.source.fetch_corrected(symbol, '5m', 2)
            if corr and getattr(corr, 'unverified', False):
                return None
        except Exception:
            return None
        if df.empty:
            return None
        idx = pd.to_datetime(df.index, utc=True)
        day = now.date()
        start = pd.Timestamp(datetime(day.year, day.month, day.day, BOX_START_H, tzinfo=timezone.utc))
        end = start + timedelta(hours=1)
        seg = df[(idx >= start) & (idx < end)]
        if len(seg) < 8:
            return None
        hi, lo = (float(seg['high'].max()), float(seg['low'].min()))
        open_inside = None
        try:
            pv = tr.pvsra(seg)
            zones_ = tr.vector_zones(seg, pv)
            open_inside = int(zones_['open'].sum()) if len(zones_) else 0
        except Exception:
            open_inside = None
        return Box(symbol=symbol, hi=hi, lo=lo, close=float(df['close'].iloc[-1]), open_vectors_inside=open_inside, formed_at=f'{day} {BOX_START_H:02d}:00-{BOX_END_H:02d}:00 GMT')

