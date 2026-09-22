"""Pinned chart-desk position geometry; caller owns tape causality. Private source projection."""
import pandas as pd

def _fill_on_tape(df, t: dict):
    """The first bar whose range touched the entry zone, or None.

    One implementation, used by both resolvers. A second copy is a second
    convention, and this bug has already come back three times because two
    code paths disagreed about when a trade became a position.
    """
    try:
        import pandas as _pd
        idx = _pd.to_datetime(df.index, utc=True)
        after = df[[x.timestamp() > float(t['ts']) for x in idx]]
        if after.empty:
            return None
        zlo, zhi = _entry_band(t)
        short = t['direction'] == 'שורט'
        hit = after['high'] >= zlo if short else after['low'] <= zhi
        return hit.idxmax() if hit.any() else None
    except Exception:
        return None

def _position_extremes(window, t: dict, *, fill_bar_first: bool) -> tuple[float, float]:
    """(hi, lo) the POSITION saw, from a window that begins at the fill.

    One implementation for the bar resolver and the live path; the convention
    they share is the pessimistic one:

    * The fill bar counts AGAINST the position and never FOR it. Within one
      bar the order of the two extremes is unknown, and on a retest entry the
      pre-fill part of that bar sits on the target side by construction --
      price came from there into the entry. 2026-09-02 17:10: gold short
      4,396.52 filled at 17:09:25; the 17:00 bar's low of 4,378.9 (printed
      before the fill) became "📈 +40 / +79 / +119 פיפס" in the group while
      the position was ten points old.
    * With nothing after the fill bar, the favourable side is the entry
      itself: nothing has been earned yet.

    `fill_bar_first` says whether window.iloc[0] IS the fill bar (located on
    the tape) or the window already starts after the fill stamp.
    """
    short = t['direction'] == 'שורט'
    e = float(t['entry'])
    adverse = float(window['high'].max()) if short else float(window['low'].min())
    fav_bars = window.iloc[1:] if fill_bar_first else window
    if fav_bars.empty:
        fav = e
    else:
        fav = float(fav_bars['low'].min()) if short else float(fav_bars['high'].max())
    return (adverse, fav) if short else (fav, adverse)

def position_bars(since, t: dict, *, include_fill_bar: bool=False):
    """(bars, fill_bar_first) for the window the POSITION owns. None = no fill.

    The one place that decides where a position's excursion begins. The bar
    resolver reads it every pass through _open_extremes; trade_admin reopen
    reads it to revive a trade the resolver closed on a false excursion, and
    trade_admin settle walks it bar by bar to close a row the tape
    contradicts -- one convention, so no repair can disagree with the next
    pass.

    Using a wall-clock filled_ts alone does not work: within a single pass the
    trade transitions PENDING->OPEN and is resolved immediately after, and
    "bars after now" is empty. The fill is a property of the tape, so it is
    located on the tape.

    `include_fill_bar` keeps the bar the fill happened IN even when later
    bars exist. The excursion readers do not want it (its pre-fill half sits
    on the target side by construction), but a walk over a position's whole
    life must see it: a stop printed on the fill bar ended the trade, and
    skipping that bar settles a stopped position as a winner (Codex,
    2026-09-04). The flag never affects what the fill bar may PAY -- that is
    fill_bar_first's job, and it stays True whenever the bar is included.
    """
    if t['state'] == 'OPEN' and t.get('filled_ts') and (not include_fill_bar):
        _fts = float(t['filled_ts'])
        _sts = [ts.timestamp() for ts in pd.to_datetime(since.index, utc=True)]
        _mask = [x >= _fts for x in _sts]
        if any(_mask):
            return (since[_mask], False)
        _i = max((i for i, x in enumerate(_sts) if x <= _fts))
        return (since.iloc[_i:], True)
    if include_fill_bar and t.get('filled_ts'):
        _fts = float(t['filled_ts'])
        _sts = [ts.timestamp() for ts in pd.to_datetime(since.index, utc=True)]
        _at = [i for i, x in enumerate(_sts) if x <= _fts]
        if not _at:
            return None
        return (since.iloc[max(_at):], True)
    _fi = _fill_on_tape(since, t)
    if _fi is None:
        return None
    return (since.loc[_fi:], True)

def _open_extremes(since, t: dict) -> tuple[float, float] | None:
    """(hi, lo) the position has seen, from the bars since the SEND. None = no fill."""
    sel = position_bars(since, t)
    if sel is None:
        return None
    bars, fill_bar_first = sel
    return _position_extremes(bars, t, fill_bar_first=fill_bar_first)

def _entry_band(t: dict) -> tuple[float, float]:
    """The price band that fills this trade. Falls back to the exact level."""
    try:
        from .pricing import entry_zone
        return entry_zone(t['symbol'], float(t['entry']))
    except Exception:
        e = float(t['entry'])
        return (e, e)
