"""Pure pinned chart-desk pricing subset; commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9."""

from __future__ import annotations
from dataclasses import dataclass


GRID = {
    "gold": 25.0,
    "nasdaq": 125.0,
    "btc": 2500.0,
}


def _asset(symbol: str) -> str | None:
    s = symbol.upper()
    if "XAU" in s or s in {"GC", "GLD", "GOLD"}:
        return "gold"
    if any(k in s for k in ("NQ", "NAS", "USTEC", "US100")):
        return "nasdaq"
    if "BTC" in s:
        return "btc"
    return None


@dataclass
class Level:
    price: float
    kind: str          # whole | half | quarter
    distance: float    # signed, level - close

    def render(self) -> str:
        tag = {"whole": "WHOLE", "half": "HALF", "quarter": "Q"}[self.kind]
        side = "מעל" if self.distance > 0 else "מתחת"
        return f"{self.price:,.0f} [{tag}] {abs(self.distance):,.1f} {side}"


def _kind(price: float, step: float) -> str:
    whole = 4 * step
    r = round(price / step) % 4
    if abs(price % whole) < step / 2 or abs(price % whole - whole) < step / 2:
        return "whole"
    return "half" if r == 2 else "quarter"


def nearest(symbol: str, close: float, count: int = 2) -> list[Level]:
    """The nearest `count` grid levels above and below the price."""
    asset = _asset(symbol)
    if asset is None:
        return []
    step = GRID[asset]
    base = (close // step) * step
    out = []
    for i in range(-count + 1, count + 1):
        px = base + i * step
        out.append(Level(price=px, kind=_kind(px, step), distance=px - close))
    return sorted(out, key=lambda l: abs(l.distance))
