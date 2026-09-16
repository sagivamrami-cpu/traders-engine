"""Symbol identity: TradingView tickers in, Yahoo tickers and asset facts out.

The bridge reads whatever symbol the user has open in TradingView Desktop
("OANDA:XAUUSD", "BINANCE:BTCUSDT", "NASDAQ:AAPL"). The analysis engine needs
Yahoo tickers. This module is the translation layer, and it also answers the
questions every downstream module asks about an instrument: what asset class is
it, what is a pip worth, how many decimals do I print, does it trade weekends.

Getting the asset class right matters more than it looks. Session logic,
psychological-level spacing and range statistics all behave differently for a
24/7 crypto pair than for a US equity with a 6.5-hour cash session.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict

__all__ = ["Instrument", "resolve", "to_yahoo", "asset_class"]


# ======================================================================
# tables
# ======================================================================

# TradingView index / CFD tickers that have no mechanical mapping.
_INDEX_MAP = {
    "SPX": "^GSPC", "SPX500": "^GSPC", "SPX500USD": "^GSPC", "US500": "^GSPC",
    "ES1!": "ES=F", "MES1!": "ES=F",
    "NDX": "^NDX", "NAS100": "NQ=F", "NAS100USD": "NQ=F", "US100": "NQ=F",
    "NQ1!": "NQ=F", "MNQ1!": "NQ=F",
    "DJI": "^DJI", "US30": "^DJI", "YM1!": "YM=F",
    "RUT": "^RUT", "US2000": "^RUT", "RTY1!": "RTY=F",
    "VIX": "^VIX", "VX1!": "^VIX",
    "DXY": "DX-Y.NYB", "USDX": "DX-Y.NYB", "DX1!": "DX=F",
    "DAX": "^GDAXI", "GER40": "^GDAXI", "DE40": "^GDAXI", "FDAX1!": "^GDAXI",
    "UKX": "^FTSE", "UK100": "^FTSE",
    "NI225": "^N225", "JP225": "^N225",
    "HSI": "^HSI", "HK50": "^HSI",
    "CAC40": "^FCHI", "FRA40": "^FCHI",
    "STOXX50E": "^STOXX50E", "EU50": "^STOXX50E",
    "TA35": "^TA125.TA", "TA125": "^TA125.TA",
    "US10Y": "^TNX", "US02Y": "^IRX", "US30Y": "^TYX",
}

# Metals and energy quoted as FX-style pairs in TradingView.
_COMMODITY_PAIR_MAP = {
    "XAUUSD": "GC=F", "GOLD": "GC=F", "GC1!": "GC=F", "MGC1!": "GC=F",
    "XAGUSD": "SI=F", "SILVER": "SI=F", "SI1!": "SI=F",
    "XPTUSD": "PL=F", "XPDUSD": "PA=F",
    "USOIL": "CL=F", "WTICOUSD": "CL=F", "CL1!": "CL=F", "MCL1!": "CL=F",
    "UKOIL": "BZ=F", "BCOUSD": "BZ=F", "BRENT": "BZ=F",
    "NATGAS": "NG=F", "NGAS": "NG=F", "NG1!": "NG=F",
    "COPPER": "HG=F", "HG1!": "HG=F",
    "XCUUSD": "HG=F",
    "ZC1!": "ZC=F", "ZW1!": "ZW=F", "ZS1!": "ZS=F",
}

_FIAT = {
    "USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "SEK", "NOK",
    "DKK", "PLN", "HUF", "CZK", "TRY", "ZAR", "MXN", "SGD", "HKD", "CNH",
    "CNY", "ILS", "INR", "KRW", "BRL", "RUB",
}

_STABLE = {"USDT", "USDC", "BUSD", "TUSD", "DAI", "FDUSD", "USDD"}

# Crypto bases we accept without a stablecoin suffix hint.
_CRYPTO_BASES = {
    "BTC", "XBT", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE", "DOT",
    "MATIC", "LINK", "LTC", "BCH", "ATOM", "UNI", "TRX", "ETC", "XLM", "NEAR",
    "APT", "ARB", "OP", "SUI", "INJ", "TIA", "SEI", "FIL", "ICP", "HBAR",
    "RNDR", "IMX", "AAVE", "MKR", "SHIB", "PEPE", "WIF", "TON", "KAS",
}

# Exchange prefixes that tell us the class outright.
_CRYPTO_EXCHANGES = {
    "BINANCE", "BINANCEUS", "COINBASE", "BITSTAMP", "BITFINEX", "KRAKEN",
    "BYBIT", "OKX", "KUCOIN", "GEMINI", "HUOBI", "MEXC", "BITGET", "CRYPTO",
    "BITMEX", "DERIBIT", "PHEMEX", "GATEIO", "UPBIT", "CRYPTOCAP",
}
_FX_EXCHANGES = {"OANDA", "FX", "FX_IDC", "FOREXCOM", "SAXO", "PEPPERSTONE",
                 "ICMARKETS", "EIGHTCAP", "VANTAGE", "CURRENCYCOM", "ACTIVTRADES"}
_EQUITY_EXCHANGES = {"NASDAQ", "NYSE", "AMEX", "ARCA", "BATS", "OTC", "CBOE",
                     "LSE", "XETR", "FWB", "TSX", "TSXV", "ASX", "TASE", "EURONEXT"}


@dataclass(frozen=True)
class Instrument:
    """Everything downstream code needs to know about one instrument."""

    tv_symbol: str          # as typed / as read from TradingView, e.g. OANDA:XAUUSD
    yahoo: str              # Yahoo Finance ticker, e.g. GC=F
    base: str               # symbol without the exchange prefix
    exchange: str | None    # exchange prefix, if there was one
    asset_class: str        # equity | index | fx | crypto | commodity | rates
    quote_ccy: str          # currency the price is quoted in
    pip: float              # one pip in price units (FX convention; else one tick)
    digits: int             # sensible display precision
    trades_weekends: bool   # crypto true, everything else false
    session: str            # 24h | fx_week | rth  -- how the clock behaves

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def is_24h(self) -> bool:
        return self.session in ("24h", "fx_week")


# ======================================================================
# resolution
# ======================================================================

def _split(symbol: str) -> tuple[str | None, str]:
    """'BINANCE:BTCUSDT' -> ('BINANCE', 'BTCUSDT'); 'AAPL' -> (None, 'AAPL')."""
    s = symbol.strip().upper().replace(" ", "")
    if ":" in s:
        ex, _, base = s.partition(":")
        return ex or None, base
    return None, s


def _fx_pair(base: str) -> tuple[str, str] | None:
    """Return (base_ccy, quote_ccy) if this looks like a 6-letter fiat pair."""
    if len(base) != 6:
        return None
    a, b = base[:3], base[3:]
    return (a, b) if a in _FIAT and b in _FIAT else None


def _crypto_pair(base: str, exchange: str | None) -> tuple[str, str] | None:
    """Return (coin, quote) for crypto tickers like BTCUSDT / ETHUSD / SOLUSDT.PERP."""
    b = re.sub(r"(\.P|PERP|\.PERP|_PERP)$", "", base)
    for q in sorted(_STABLE | {"USD", "EUR", "BTC", "ETH"}, key=len, reverse=True):
        if b.endswith(q) and len(b) > len(q):
            coin = b[: -len(q)]
            known = coin in _CRYPTO_BASES or (exchange in _CRYPTO_EXCHANGES)
            if known:
                return coin, q
    if b in _CRYPTO_BASES:
        return b, "USD"
    return None


def _digits_for(price_class: str, quote: str) -> int:
    if price_class == "fx":
        return 3 if quote == "JPY" else 5
    if price_class == "crypto":
        return 2
    if price_class in ("index", "rates"):
        return 2
    return 2


def resolve(symbol: str) -> Instrument:
    """Turn any TradingView-style or plain ticker into a full Instrument.

    Unknown symbols fall through to 'equity' with the base used as the Yahoo
    ticker, which is right for the overwhelming majority of stock tickers.
    """
    exchange, base = _split(symbol)
    tv = symbol.strip().upper()

    # 1. explicit index / commodity tables
    if base in _INDEX_MAP:
        y = _INDEX_MAP[base]
        cls = "rates" if base.startswith("US") and base.endswith("Y") else "index"
        return Instrument(tv, y, base, exchange, cls, "USD", 0.01,
                          _digits_for(cls, "USD"), False, "rth")

    if base in _COMMODITY_PAIR_MAP:
        y = _COMMODITY_PAIR_MAP[base]
        pip = 0.01 if base in ("XAUUSD", "GOLD", "GC1!", "MGC1!") else 0.001
        return Instrument(tv, y, base, exchange, "commodity", "USD", pip,
                          2 if pip == 0.01 else 3, False, "fx_week")

    # 2. crypto
    cp = _crypto_pair(base, exchange)
    if cp and (exchange in _CRYPTO_EXCHANGES or cp[0] in _CRYPTO_BASES):
        coin, quote = cp
        coin = "BTC" if coin == "XBT" else coin
        fiat = "USD" if quote in _STABLE or quote == "USD" else quote
        return Instrument(tv, f"{coin}-{fiat}", base, exchange, "crypto", fiat,
                          0.01, 2, True, "24h")

    # 3. fx
    fp = _fx_pair(base)
    if fp and (exchange in _FX_EXCHANGES or exchange is None or exchange == "TVC"):
        a, b = fp
        pip = 0.01 if b == "JPY" else 0.0001
        return Instrument(tv, f"{a}{b}=X", base, exchange, "fx", b, pip,
                          _digits_for("fx", b), False, "fx_week")

    # 4. continuous futures written as ROOT1!
    m = re.fullmatch(r"([A-Z]{1,3})[12]!", base)
    if m:
        return Instrument(tv, f"{m.group(1)}=F", base, exchange, "commodity",
                          "USD", 0.01, 2, False, "fx_week")

    # 5. anything else is an equity
    y = base
    if exchange in ("LSE",):
        y = f"{base}.L"
    elif exchange in ("XETR", "FWB"):
        y = f"{base}.DE"
    elif exchange == "TSX":
        y = f"{base}.TO"
    elif exchange == "ASX":
        y = f"{base}.AX"
    elif exchange == "TASE":
        y = f"{base}.TA"
    return Instrument(tv, y, base, exchange, "equity", "USD", 0.01, 2, False, "rth")


def to_yahoo(symbol: str) -> str:
    """Convenience: just the Yahoo ticker."""
    return resolve(symbol).yahoo


def asset_class(symbol: str) -> str:
    return resolve(symbol).asset_class

