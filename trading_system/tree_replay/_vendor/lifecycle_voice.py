"""The client voice of TR-Trade: one vocabulary for every message the desk sends.

2026-09-02, after the first full client-visible trade (gold SELL 4,373.35:
entry, +39/+79 pips, a break-even option, eight thesis flip/return alerts in
95 minutes, stop), Sagiv chose direction א of the message redesign -- keep the
flow the clients already know, make each message identity-first, one marker
one meaning, one unit per instrument -- and asked for the signal's detail
block as a checklist, "עץ ההחלטות ✅ · הסטופ הורחב ❗️", one item per line.

Rules this module carries so that no renderer re-derives them:

IDENTITY. Every lifecycle message opens `{marker} {NAME} {SIDE} {entry}`.
The tracker gate matches a message to its trade by the symbol name, the side
word and the entry price it finds in the text (tracker._match_trade_for_text)
and the outbox reads the FIRST price-looking token to catch a stale message
(outbox._stale_price). Both parse the identity line, so it stays first and
the entry stays the first price.

UNITS. Gold is counted in pips (a point is ten pips -- his convention);
the Nasdaq and BTC in points. One unit per instrument, in every message: the
📈 ladder said "פיפס" while the ⚠️ warning said "נק'" for the same trade.

MARKERS. One meaning each, never reused:
    🔴 🟢  new trade (SELL / BUY)      👀  approaching the entry
    ▶️  entry reached                   📈  progress in the trade's favour
    🔒  protection can be taken         ✅  target reached
    ⚠️  thesis weakened (a warning)     🔄  back in the trade's direction
    🛑  stop reached                    🏁  closed at entry / trailed stop
    ✖️  cancelled or expired before entry   ⏳  time in position
    🔧  correction

FOOTER. The desk reports direction and never closes a trade (Sagiv,
2026-08-31: BE is "רשות, לא חובה"). The footer says so in one sentence.

Everything here is pure: strings in, strings out. Telegram receives plain
text (floor/notify.py sends no parse_mode), so the design is carried by
structure -- identity line, one fact per line, a checklist -- not by markup.
"""
from __future__ import annotations

import re

FOOTER = "הדסק לא סוגר עסקאות. המצב לפניכם, ההחלטה שלכם."
OPTIONAL = "רשות, לא חובה."
TARGETS_NOTE = "היעדים הם רמות דיווח · מימוש וניהול לפי החלטת הסוחר"

OK, MISSING = "✅", "❗️"


def name(symbol: str) -> str:
    return str(symbol).split(":")[-1]


def side(direction: str | None) -> str:
    return "SELL" if direction == "שורט" else "BUY"


def dot(direction: str | None) -> str:
    return "🔴" if direction == "שורט" else "🟢"


def is_gold(symbol: str) -> bool:
    return "XAU" in str(symbol).upper()


def unit(symbol: str) -> str:
    return "פיפס" if is_gold(symbol) else "נק'"


def _scale(symbol: str) -> float:
    return 10.0 if is_gold(symbol) else 1.0


def move(symbol: str, points: float) -> str:
    """A signed distance in the instrument's own unit: '+79 פיפס', '-660 נק''."""
    return f"{points * _scale(symbol):+,.0f} {unit(symbol)}"


def dist(symbol: str, points: float) -> str:
    """An unsigned distance: '42 פיפס', '25 נק''."""
    return f"{abs(points) * _scale(symbol):,.0f} {unit(symbol)}"


def price(x: float) -> str:
    return f"{float(x):,.2f}"


def head(marker: str, symbol: str, direction: str | None, entry: float,
         what: str = "") -> str:
    """The identity line: `📈 XAUUSD SELL 4,373.35 · +79 פיפס`."""
    line = f"{marker} {name(symbol)} {side(direction)} {price(entry)}"
    return f"{line} · {what}" if what else line


def check(text: str, ok: bool) -> str:
    """One checklist line: `עץ ההחלטות ✅` or `וקטור — חסר ❗️`."""
    return f"{text} {OK if ok else MISSING}"


def moved_from_entry(symbol: str, direction: str | None, entry: float,
                     px: float) -> str:
    """Where price stands relative to the entry, signed by the trade's side."""
    d = (float(entry) - float(px)) if direction == "שורט" else (float(px) - float(entry))
    return move(symbol, d) if abs(d) >= 0.5 / _scale(symbol) else "בכניסה"


def rung_points(entry: float, pct: float, step: int) -> float:
    """Distance of progress rung `step` from the entry, in points."""
    return float(entry) * (float(pct) / 100.0) * int(step)


_RESOLUTION_WIDEN = re.compile(r"הורחב ל-([\d,]+(?:\.\d+)?)")


def widen_line(symbol: str, warning: str) -> str | None:
    """`הסטופ הורחב ל-8 מקצה טווח הכניסה — …` → `הסטופ הורחב ל-80 פיפס מקצה האזור`.

    The engine writes the widening in points. A gold reader counts pips, and
    "8" on a gold signal read as eight pips (Sagiv, 2026-09-02) when it meant
    eighty.
    """
    m = _RESOLUTION_WIDEN.search(warning)
    if not m:
        return None
    pts = float(m.group(1).replace(",", ""))
    return f"הסטופ הורחב ל-{dist(symbol, pts)} מקצה האזור"
