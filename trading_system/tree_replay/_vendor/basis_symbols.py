"""Pure pinned chart-desk pricing subset; commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9."""

from __future__ import annotations


_BARE_ALIASES = {
    "XAUUSD": "OANDA:XAUUSD",
    "GOLD": "OANDA:XAUUSD",
    "XAU": "OANDA:XAUUSD",
    "NAS100": "OANDA:NAS100USD",
    "NAS100USD": "OANDA:NAS100USD",
    "US100": "OANDA:NAS100USD",
    "NAS": "OANDA:NAS100USD",
    "NQ": "OANDA:NAS100USD",
    "BTCUSD": "BINANCE:BTCUSDT",
    "BTCUSDT": "BINANCE:BTCUSDT",
    "BTC": "BINANCE:BTCUSDT",
    "VIX": "TVC:VIX",
    "DXY": "TVC:DXY",
}


def canonical_symbol(symbol: str) -> str:
    """The fully qualified name for one of Sagiv's instruments.

    Anything already exchange-qualified, and any ticker not in the table
    (equities, ETFs -- which legitimately come from Yahoo), passes through
    untouched.
    """
    s = (symbol or "").strip()
    if ":" in s:
        return s
    return _BARE_ALIASES.get(s.upper(), s)
