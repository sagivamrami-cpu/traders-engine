from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd
from . import map_tr as tr, quarters, map_sessions as sessions
from .back_days import _back_day_levels


@dataclass
class NamedLevel:
    name: str
    price: float
    kind: str          # level | ema | psy | quarter

    def __repr__(self):
        return f"{self.name}@{self.price:,.1f}"


SESSION_OPEN_LEVELS = (("london", "LONDON-OPEN"), ("newyork", "NY-OPEN"))


def _session_open_levels_at(symbol: str, missing: list | None = None,
                            *, source, decision_time) -> list[NamedLevel]:
    """LONDON-OPEN / NY-OPEN — the price the session actually opened at.

    04.09 is the case that earned these. Gold's day open sat at 4,476.07 and
    London opened at 4,462.92 -- thirteen points BELOW it, onto the
    EMA200-1h/D3-HI/CLOUD50-4h cluster -- and price left that open for
    4,490.9. The map had no name for where the session began, so the desk
    could describe the cluster and not the arrival.

    EXACT BAR OR NOTHING. The level is one bar's open price, so the nearest
    bar is a different number wearing this one's name; a missing bar is
    reported and the level is omitted. Live from the moment the opening bar
    exists (a forming bar's open is already final) until the session closes,
    and never carried into the next day -- yesterday's London open is a fact
    about yesterday.
    """
    basis = source
    out: list[NamedLevel] = []
    try:
        df, corr = basis.fetch_corrected(symbol, "5m", 3)
    except Exception:
        return out
    if df is None or df.empty:
        return out
    # A session open is a precise price, and a basis correction that could not
    # be established would put a fabricated one on the map under a real name.
    if corr is None or corr.source == "none":
        if missing is not None:
            missing.append("פתיחות סשן לא זמינות — בסיס המחיר לא אומת")
        return out
    idx = pd.to_datetime(df.index, utc=True)
    now = pd.Timestamp(decision_time)
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    for key, name in SESSION_OPEN_LEVELS:
        spec = sessions.SESSIONS[key]
        local = now.tz_convert(spec.tz)
        if local.weekday() not in spec.weekdays:
            continue
        sh, sm = sessions._hm(spec.start)
        eh, em = sessions._hm(spec.end)
        # Built in the VENUE's clock, so the UTC time moves with that venue's
        # DST and never with Israel's -- London opens 07:00 UTC in summer and
        # 08:00 UTC in winter, and the two do not switch on the same weekend.
        day = local.date()
        start = pd.Timestamp(year=day.year, month=day.month, day=day.day,
                             hour=sh, minute=sm, tz=spec.tz)
        end = pd.Timestamp(year=day.year, month=day.month, day=day.day,
                           hour=eh, minute=em, tz=spec.tz)
        if not (start <= local < end):
            continue
        at = start.tz_convert("UTC")
        hit = df[idx == at]
        if hit.empty:
            if missing is not None:
                missing.append(f"{name} לא זמינה — נר הפתיחה לא בקלטת")
            continue
        # ON A SPLICED FRAME, PROVENANCE IS PER BAR. Bars before `tv_from`
        # are corrected proxy: right in LEVEL, not guaranteed right in
        # SHAPE -- and a session open IS one bar's shape. If collection
        # started at 07:05, the 07:00 London bar is the proxy's, and
        # publishing it as LONDON-OPEN would put a number on the map that
        # his chart never printed. Rejecting the whole splice instead would
        # also throw away the exact TV-side bars, so the test is per bar.
        if getattr(corr, "source", "") == "tv_spliced" and corr.tv_from is not None:
            if at < pd.Timestamp(corr.tv_from).tz_convert("UTC"):
                if missing is not None:
                    missing.append(f"{name} לא זמינה — נר הפתיחה מהפרוקסי, "
                                   "לא מהצ'ארט")
                continue
        out.append(NamedLevel(name, float(hit["open"].iloc[0]), "level"))
    return out


def _ema_levels(symbol: str, missing: list | None = None, *, source) -> list[NamedLevel]:
    """EMA levels with the history to earn them; the rest are REPORTED absent.

    An EMA800-1h needs 1,600 hourly bars and gold has ~1,150, so that level
    silently never existed -- a map of 26 levels that looked whole while a
    level the swing TARGETS aim at was missing. The gold swing that closed
    at "TP3 EMA800-1h" today aimed at a level whose reading is unearned.
    `missing`, when given, receives one line per absent level so the walk can
    say so instead of presenting a smaller map as a complete one.
    """
    basis = source
    out = []
    for tf, lengths in (("1h", (200, 800)), ("4h", (50, 200))):
        try:
            df, _ = basis.fetch_corrected(symbol, tf, 240)
        except Exception as exc:
            if missing is not None:
                missing.append(f"רמות EMA-{tf} לא נקראו ({type(exc).__name__})")
            continue
        e = tr.emas(df)
        for n in lengths:
            col = f"ema{n}"
            label = f"CLOUD50-{tf}" if n == 50 else f"EMA{n}-{tf}"
            if col in e.columns and len(df) >= 2 * n and not pd.isna(e[col].iloc[-1]):
                out.append(NamedLevel(label, float(e[col].iloc[-1]), "ema"))
            elif missing is not None:
                missing.append(f"רמת {label} לא קיימת — "
                               f"{len(df)} נרות, נדרשים {2 * n}")
    return out


def build_at(symbol: str, missing: list | None = None,
             *, source, decision_time) -> tuple[list[NamedLevel], "basis.Correction | None"]:
    basis = source
    levels: list[NamedLevel] = []
    try:
        daily, corr = basis.fetch_corrected(symbol, "1d", 400)
    except Exception:
        return levels, None
    weekly = tr.weekly_from_daily(daily)
    monthly = tr.monthly_from_daily(daily)

    # Real broker bars make the ADR/RD family trustworthy; a futures proxy
    # does not -- see tr.average_range(). A SPLICED frame qualifies only when
    # its genuine-TV span covers the ~15-day windows these levels measure --
    # that judgment lives in basis.broker_shape_ok(), added with the splice.
    broker = basis.broker_shape_ok(corr, 20)
    lv = tr.tr_levels(daily, weekly, monthly, broker_bars=broker)

    # Floor pivots (PP/R/S/M) intentionally not surfaced -- see module docstring.

    # ADR-HI/LO and RD-HI/LO are surfaced only on broker bars. Verified
    # against his live chart 2026-08-12 once tv_daily was feeding them:
    # Hi-ADR 4,455.1 vs ~4,456 rendered, Lo-ADR 4,332.0 vs ~4,331.
    adr = lv.get("adr") or {}
    if adr.get("available") and adr.get("verified"):
        levels.append(NamedLevel("ADR-HI", float(adr["high"]), "level"))
        levels.append(NamedLevel("ADR-LO", float(adr["low"]), "level"))
    # THE WEEKLY AND MONTHLY FAMILIES, gate 5 of the launch plan. tr_levels
    # computed AWR/RW/AMR from the day it was written and the map never
    # consumed them -- while the spec aims swing TARGETS at exactly these:
    # "swing -> AWR/RW". A swing ladder built from a map without its weekly
    # rails reaches for whatever else is far enough, which is how a target
    # can end up on a level nobody would draw. The "50%" rails are the
    # from_open variant -- the MT4 convention tr.average_range documents:
    # anchor on the period open, split the range evenly (open ± range/2).
    for fam, label in (("awr", "AWR"), ("rw", "RW"), ("amr", "AMR")):
        d_ = lv.get(fam) or {}
        if d_.get("available", True) and "high" in d_:
            levels.append(NamedLevel(f"{label}-HI", float(d_["high"]), "level"))
            levels.append(NamedLevel(f"{label}-LO", float(d_["low"]), "level"))
        elif missing is not None:
            missing.append(f"רמות {label} לא זמינות — "
                           f"{d_.get('n', 0)} נרות בלבד")
    for fam, label in (("adr_from_open", "ADR50"),
                       ("awr_from_open", "AWR50"),
                       ("amr_from_open", "AMR50")):
        d_ = lv.get(fam) or {}
        if d_.get("available", True) and "high" in d_:
            levels.append(NamedLevel(f"{label}-HI", float(d_["high"]), "level"))
            levels.append(NamedLevel(f"{label}-LO", float(d_["low"]), "level"))
    rd = lv.get("rd") or {}
    if rd.get("verified"):
        for key, nm in (("high", "RD-HI"), ("low", "RD-LO")):
            if isinstance(rd.get(key), (int, float)):
                levels.append(NamedLevel(nm, float(rd[key]), "level"))

    if (y := lv.get("yday")):
        levels.append(NamedLevel("YDAY-HI", y["high"], "level"))
        levels.append(NamedLevel("YDAY-LO", y["low"], "level"))
        levels.append(NamedLevel("YDAY-CLOSE", y["close"], "level"))

    # The back days -- see _back_day_levels for why. These are the levels that
    # explain a stop a few pips short of a famous one.
    for nm, px in _back_day_levels(daily):
        levels.append(NamedLevel(nm, px, "level"))
    if (lw := lv.get("lweek")):
        levels.append(NamedLevel("LWEEK-HI", lw["high"], "level"))
        levels.append(NamedLevel("LWEEK-LO", lw["low"], "level"))

    levels.append(NamedLevel("DAY-OPEN", float(daily["open"].iloc[-1]), "level"))
    levels.append(NamedLevel("WEEK-OPEN", float(weekly["open"].iloc[-1]), "level"))
    levels += _session_open_levels_at(symbol, missing, source=source, decision_time=decision_time)

    # Psy levels are the high/low of the week's first Asian session -- a
    # WINDOW RANGE, so they fail on a futures proxy for exactly the reason
    # ADR did: GC=F prints the COMEX session, his OANDA feed prints 24h spot,
    # and a constant price offset shifts the level without ever fixing the
    # range. Surfaced only on his own TradingView bars; 1h is preferred over
    # 15m because 300 captured bars reach ~12 days back at 1h but barely 3 at
    # 15m, and the window being measured can sit several days behind.
    try:
        intraday = None
        for tf, lookback in (("1h", 20), ("15m", 20)):
            cand, ccorr = basis.fetch_corrected(symbol, tf, lookback)
            if ccorr and basis.broker_shape_ok(ccorr, 7) and not cand.empty:
                # On a spliced frame, hand psy_levels ONLY the genuine bars --
                # the window it measures must never straddle the seam.
                if ccorr.source == "tv_spliced" and ccorr.tv_from is not None:
                    cand = cand[cand.index >= ccorr.tv_from]
                intraday = cand
                break
        if intraday is not None:
            mode = "crypto" if "BTC" in symbol.upper() else "forex"
            ps = sessions.psy_levels(intraday, mode=mode)
            if ps.get("available"):
                levels.append(NamedLevel("PSY-HI", float(ps["psy_high"]), "psy"))
                levels.append(NamedLevel("PSY-LO", float(ps["psy_low"]), "psy"))
    except Exception:
        pass

    levels += _ema_levels(symbol, missing, source=source)

    close = float(daily["close"].iloc[-1])
    for l in quarters.nearest(symbol, close, count=2):
        levels.append(NamedLevel(f"Q-{l.kind.upper()}", l.price, "quarter"))
    return levels, corr
