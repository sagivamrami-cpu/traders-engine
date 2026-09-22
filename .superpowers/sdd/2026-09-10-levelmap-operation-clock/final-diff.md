# Complete operation-clock component additions
Base=HEAD=c1b6071633c55376c64f0a98ece843706f420f49. No commits or tracked runtime edits.

warning: in the working copy of 'trading_system/tree_replay/_vendor/basis_operation.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/basis_operation.py b/trading_system/tree_replay/_vendor/basis_operation.py
new file mode 100644
index 0000000..3d6ee51
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/basis_operation.py
@@ -0,0 +1,38 @@
+import pandas as pd
+from .correction import EXCHANGE_NATIVE
+
+
+class BasisOperation:
+    def __init__(self, source):
+        self.source = source
+
+    def fetch_corrected(self, symbol, timeframe, lookback):
+        return self.source.fetch_corrected(symbol, timeframe, lookback)
+
+    def now_utc(self):
+        return self.source.now_utc()
+
+    def broker_shape_ok(self, corr, days: float) -> bool:
+        "May a RANGE object looking `days` back trust this frame's shape?\n\n    A constant offset shifts a level but never fixes a range, so range-shaped\n    objects (ADR, RD, psy levels, session ranges, yesterday's extremes) need\n    bars that are genuinely his. Pure broker sources qualify outright; a\n    spliced frame qualifies only when its genuine-TV span reaches back at\n    least `days` -- the window being measured must lie entirely on the TV side\n    of the seam.\n    "
+        if corr is None:
+            return False
+        if corr.source in ("tv_daily", "mt5_broker"):
+            return True
+        # Exchange-native instruments are exempt, and this is not a loosening.
+        #
+        # The guard exists because gold and the Nasdaq are traded here as OTC CFDs
+        # while their fallback bars come from COMEX/CME futures -- a genuinely
+        # different instrument, measured at ~75% of spot's daily range, which no
+        # constant offset repairs. BTC has no such gap: Binance IS the venue, its
+        # bars ARE the tape, and there is no "his broker" version to prefer.
+        #
+        # Found 2026-08-24: with the MT5 export 90h stale, this returned False for
+        # BTC and silently disabled `stretch.state()` and `rails.check()` on the one
+        # instrument whose data is authoritative -- so the over-extension detector
+        # Sagiv asked for could not speak about BTC at all.
+        if corr.symbol in EXCHANGE_NATIVE:
+            return True
+        if corr.source == "tv_spliced" and corr.tv_from is not None:
+            age_days = (pd.Timestamp(self.source.now_utc()) - corr.tv_from).total_seconds() / 86400.0
+            return age_days >= days
+        return False

warning: in the working copy of 'trading_system/tree_replay/_vendor/levelmap_operation.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/levelmap_operation.py b/trading_system/tree_replay/_vendor/levelmap_operation.py
new file mode 100644
index 0000000..bb6c5e8
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/levelmap_operation.py
@@ -0,0 +1,177 @@
+from __future__ import annotations
+import pandas as pd
+from . import map_tr as tr, quarters, map_sessions as sessions
+from .back_days import _back_day_levels
+from .levelmap_build import NamedLevel, SESSION_OPEN_LEVELS, _ema_levels
+from .basis_operation import BasisOperation
+
+
+class LevelmapOperation:
+    def __init__(self, source):
+        self.source = BasisOperation(source)
+
+    def _session_open_levels(self, symbol: str, missing: list | None = None,
+                             now=None) -> list[NamedLevel]:
+        "LONDON-OPEN / NY-OPEN — the price the session actually opened at.\n\n    04.09 is the case that earned these. Gold's day open sat at 4,476.07 and\n    London opened at 4,462.92 -- thirteen points BELOW it, onto the\n    EMA200-1h/D3-HI/CLOUD50-4h cluster -- and price left that open for\n    4,490.9. The map had no name for where the session began, so the desk\n    could describe the cluster and not the arrival.\n\n    EXACT BAR OR NOTHING. The level is one bar's open price, so the nearest\n    bar is a different number wearing this one's name; a missing bar is\n    reported and the level is omitted. Live from the moment the opening bar\n    exists (a forming bar's open is already final) until the session closes,\n    and never carried into the next day -- yesterday's London open is a fact\n    about yesterday.\n    "
+        basis = self.source
+        out: list[NamedLevel] = []
+        try:
+            df, corr = basis.fetch_corrected(symbol, "5m", 3)
+        except Exception:
+            return out
+        if df is None or df.empty:
+            return out
+        # A session open is a precise price, and a basis correction that could not
+        # be established would put a fabricated one on the map under a real name.
+        if corr is None or corr.source == "none":
+            if missing is not None:
+                missing.append("פתיחות סשן לא זמינות — בסיס המחיר לא אומת")
+            return out
+        idx = pd.to_datetime(df.index, utc=True)
+        now = pd.Timestamp(self.source.now_utc()) if now is None else pd.Timestamp(now)
+        now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
+        for key, name in SESSION_OPEN_LEVELS:
+            spec = sessions.SESSIONS[key]
+            local = now.tz_convert(spec.tz)
+            if local.weekday() not in spec.weekdays:
+                continue
+            sh, sm = sessions._hm(spec.start)
+            eh, em = sessions._hm(spec.end)
+            # Built in the VENUE's clock, so the UTC time moves with that venue's
+            # DST and never with Israel's -- London opens 07:00 UTC in summer and
+            # 08:00 UTC in winter, and the two do not switch on the same weekend.
+            day = local.date()
+            start = pd.Timestamp(year=day.year, month=day.month, day=day.day,
+                                 hour=sh, minute=sm, tz=spec.tz)
+            end = pd.Timestamp(year=day.year, month=day.month, day=day.day,
+                               hour=eh, minute=em, tz=spec.tz)
+            if not (start <= local < end):
+                continue
+            at = start.tz_convert("UTC")
+            hit = df[idx == at]
+            if hit.empty:
+                if missing is not None:
+                    missing.append(f"{name} לא זמינה — נר הפתיחה לא בקלטת")
+                continue
+            # ON A SPLICED FRAME, PROVENANCE IS PER BAR. Bars before `tv_from`
+            # are corrected proxy: right in LEVEL, not guaranteed right in
+            # SHAPE -- and a session open IS one bar's shape. If collection
+            # started at 07:05, the 07:00 London bar is the proxy's, and
+            # publishing it as LONDON-OPEN would put a number on the map that
+            # his chart never printed. Rejecting the whole splice instead would
+            # also throw away the exact TV-side bars, so the test is per bar.
+            if getattr(corr, "source", "") == "tv_spliced" and corr.tv_from is not None:
+                if at < pd.Timestamp(corr.tv_from).tz_convert("UTC"):
+                    if missing is not None:
+                        missing.append(f"{name} לא זמינה — נר הפתיחה מהפרוקסי, "
+                                       "לא מהצ'ארט")
+                    continue
+            out.append(NamedLevel(name, float(hit["open"].iloc[0]), "level"))
+        return out
+
+    def build(self, symbol: str, missing: list | None = None
+              ) -> tuple[list[NamedLevel], "basis.Correction | None"]:
+        basis = self.source
+        levels: list[NamedLevel] = []
+        try:
+            daily, corr = basis.fetch_corrected(symbol, "1d", 400)
+        except Exception:
+            return levels, None
+        weekly = tr.weekly_from_daily(daily)
+        monthly = tr.monthly_from_daily(daily)
+
+        # Real broker bars make the ADR/RD family trustworthy; a futures proxy
+        # does not -- see tr.average_range(). A SPLICED frame qualifies only when
+        # its genuine-TV span covers the ~15-day windows these levels measure --
+        # that judgment lives in basis.broker_shape_ok(), added with the splice.
+        broker = basis.broker_shape_ok(corr, 20)
+        lv = tr.tr_levels(daily, weekly, monthly, broker_bars=broker)
+
+        # Floor pivots (PP/R/S/M) intentionally not surfaced -- see module docstring.
+
+        # ADR-HI/LO and RD-HI/LO are surfaced only on broker bars. Verified
+        # against his live chart 2026-08-12 once tv_daily was feeding them:
+        # Hi-ADR 4,455.1 vs ~4,456 rendered, Lo-ADR 4,332.0 vs ~4,331.
+        adr = lv.get("adr") or {}
+        if adr.get("available") and adr.get("verified"):
+            levels.append(NamedLevel("ADR-HI", float(adr["high"]), "level"))
+            levels.append(NamedLevel("ADR-LO", float(adr["low"]), "level"))
+        # THE WEEKLY AND MONTHLY FAMILIES, gate 5 of the launch plan. tr_levels
+        # computed AWR/RW/AMR from the day it was written and the map never
+        # consumed them -- while the spec aims swing TARGETS at exactly these:
+        # "swing -> AWR/RW". A swing ladder built from a map without its weekly
+        # rails reaches for whatever else is far enough, which is how a target
+        # can end up on a level nobody would draw. The "50%" rails are the
+        # from_open variant -- the MT4 convention tr.average_range documents:
+        # anchor on the period open, split the range evenly (open ± range/2).
+        for fam, label in (("awr", "AWR"), ("rw", "RW"), ("amr", "AMR")):
+            d_ = lv.get(fam) or {}
+            if d_.get("available", True) and "high" in d_:
+                levels.append(NamedLevel(f"{label}-HI", float(d_["high"]), "level"))
+                levels.append(NamedLevel(f"{label}-LO", float(d_["low"]), "level"))
+            elif missing is not None:
+                missing.append(f"רמות {label} לא זמינות — "
+                               f"{d_.get('n', 0)} נרות בלבד")
+        for fam, label in (("adr_from_open", "ADR50"),
+                           ("awr_from_open", "AWR50"),
+                           ("amr_from_open", "AMR50")):
+            d_ = lv.get(fam) or {}
+            if d_.get("available", True) and "high" in d_:
+                levels.append(NamedLevel(f"{label}-HI", float(d_["high"]), "level"))
+                levels.append(NamedLevel(f"{label}-LO", float(d_["low"]), "level"))
+        rd = lv.get("rd") or {}
+        if rd.get("verified"):
+            for key, nm in (("high", "RD-HI"), ("low", "RD-LO")):
+                if isinstance(rd.get(key), (int, float)):
+                    levels.append(NamedLevel(nm, float(rd[key]), "level"))
+
+        if (y := lv.get("yday")):
+            levels.append(NamedLevel("YDAY-HI", y["high"], "level"))
+            levels.append(NamedLevel("YDAY-LO", y["low"], "level"))
+            levels.append(NamedLevel("YDAY-CLOSE", y["close"], "level"))
+
+        # The back days -- see _back_day_levels for why. These are the levels that
+        # explain a stop a few pips short of a famous one.
+        for nm, px in _back_day_levels(daily):
+            levels.append(NamedLevel(nm, px, "level"))
+        if (lw := lv.get("lweek")):
+            levels.append(NamedLevel("LWEEK-HI", lw["high"], "level"))
+            levels.append(NamedLevel("LWEEK-LO", lw["low"], "level"))
+
+        levels.append(NamedLevel("DAY-OPEN", float(daily["open"].iloc[-1]), "level"))
+        levels.append(NamedLevel("WEEK-OPEN", float(weekly["open"].iloc[-1]), "level"))
+        levels += self._session_open_levels(symbol, missing)
+
+        # Psy levels are the high/low of the week's first Asian session -- a
+        # WINDOW RANGE, so they fail on a futures proxy for exactly the reason
+        # ADR did: GC=F prints the COMEX session, his OANDA feed prints 24h spot,
+        # and a constant price offset shifts the level without ever fixing the
+        # range. Surfaced only on his own TradingView bars; 1h is preferred over
+        # 15m because 300 captured bars reach ~12 days back at 1h but barely 3 at
+        # 15m, and the window being measured can sit several days behind.
+        try:
+            intraday = None
+            for tf, lookback in (("1h", 20), ("15m", 20)):
+                cand, ccorr = basis.fetch_corrected(symbol, tf, lookback)
+                if ccorr and basis.broker_shape_ok(ccorr, 7) and not cand.empty:
+                    # On a spliced frame, hand psy_levels ONLY the genuine bars --
+                    # the window it measures must never straddle the seam.
+                    if ccorr.source == "tv_spliced" and ccorr.tv_from is not None:
+                        cand = cand[cand.index >= ccorr.tv_from]
+                    intraday = cand
+                    break
+            if intraday is not None:
+                mode = "crypto" if "BTC" in symbol.upper() else "forex"
+                ps = sessions.psy_levels(intraday, mode=mode)
+                if ps.get("available"):
+                    levels.append(NamedLevel("PSY-HI", float(ps["psy_high"]), "psy"))
+                    levels.append(NamedLevel("PSY-LO", float(ps["psy_low"]), "psy"))
+        except Exception:
+            pass
+
+        levels += _ema_levels(symbol, missing, source=self.source)
+
+        close = float(daily["close"].iloc[-1])
+        for l in quarters.nearest(symbol, close, count=2):
+            levels.append(NamedLevel(f"Q-{l.kind.upper()}", l.price, "quarter"))
+        return levels, corr

warning: in the working copy of 'tests/tree_replay/test_levelmap_operation.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_levelmap_operation.py b/tests/tree_replay/test_levelmap_operation.py
new file mode 100644
index 0000000..6391e5a
--- /dev/null
+++ b/tests/tree_replay/test_levelmap_operation.py
@@ -0,0 +1,259 @@
+"""Literal market-map outcomes over raw frame and advancing clock ports."""
+
+import importlib
+import importlib.util
+
+import pandas as pd
+import pytest
+
+from trading_system.tree_replay._vendor.correction import Correction
+
+
+SYMBOL = 'OANDA:XAUUSD'
+NOW = pd.Timestamp('2026-09-09T14:00Z')
+
+
+def api(name='levelmap_operation'):
+    path = 'trading_system.tree_replay._vendor.' + name
+    assert importlib.util.find_spec(path) is not None, f'Missing operation reader: {path}'
+    return importlib.import_module(path)
+
+
+def bars(count=1, end='2026-09-09T07:00Z', freq='5min', row=(103, 110, 90, 100)):
+    return pd.DataFrame([row] * count, columns=['open', 'high', 'low', 'close'],
+                        index=pd.date_range(end=end, periods=count, freq=freq))
+
+
+def corr(source='tv_daily', seam=None, symbol=SYMBOL):
+    return Correction(symbol, 0, source, 'n/a', 'synthetic', seam)
+
+
+class RawSource:
+    def __init__(self, frames=None, now=NOW, after=None):
+        self.frames = {} if frames is None else frames
+        self.now = now
+        self.after = {} if after is None else after
+        self.calls = []
+
+    def fetch_corrected(self, symbol, timeframe, lookback):
+        self.calls.append(('fetch', symbol, timeframe, lookback))
+        key = (timeframe, lookback)
+        if key in self.after:
+            self.now = self.after[key]
+        value = self.frames.get(key, LookupError('no synthetic frame'))
+        if isinstance(value, Exception):
+            raise value
+        return value
+
+    def now_utc(self):
+        self.calls.append(('clock',))
+        if isinstance(self.now, Exception):
+            raise self.now
+        return self.now
+
+
+def named(levels):
+    return [(x.name, x.price) for x in levels]
+
+
+def test_session_uses_time_after_fetch_crosses_open():
+    s = RawSource({('5m', 3): (bars(), corr())},
+                  pd.Timestamp('2026-09-09T06:59:59Z'),
+                  {('5m', 3): pd.Timestamp('2026-09-09T07:00Z')})
+    assert named(api().LevelmapOperation(s)._session_open_levels(SYMBOL)) == [('LONDON-OPEN', 103)]
+    assert s.calls == [('fetch', SYMBOL, '5m', 3), ('clock',)]
+
+
+@pytest.mark.parametrize('now,opening,want', [
+    ('2026-09-09T06:59:59Z', '2026-09-09T07:00Z', []),
+    ('2026-09-09T07:00Z', '2026-09-09T07:00Z', [('LONDON-OPEN', 103)]),
+    ('2026-09-09T15:29:59Z', '2026-09-09T07:00Z', [('LONDON-OPEN', 103)]),
+    ('2026-09-09T15:30Z', '2026-09-09T07:00Z', []),
+    ('2026-09-09T13:30Z', '2026-09-09T13:30Z', [('NY-OPEN', 103)]),
+    ('2026-09-09T19:59:59Z', '2026-09-09T13:30Z', [('NY-OPEN', 103)]),
+    ('2026-09-09T20:00Z', '2026-09-09T13:30Z', []),
+    ('2026-01-07T07:59:59Z', '2026-01-07T08:00Z', []),
+    ('2026-01-07T08:00Z', '2026-01-07T08:00Z', [('LONDON-OPEN', 103)]),
+    ('2026-01-07T14:30Z', '2026-01-07T14:30Z', [('NY-OPEN', 103)]),
+    ('2026-09-12T08:00Z', '2026-09-12T07:00Z', []),
+    ('2026-09-13T08:00Z', '2026-09-13T07:00Z', []),
+    ('2026-09-10T08:00Z', '2026-09-09T07:00Z', []),
+])
+def test_venue_boundaries_and_no_yesterday_carry(now, opening, want):
+    s = RawSource({('5m', 3): (bars(end=opening), corr())}, pd.Timestamp(now))
+    assert named(api().LevelmapOperation(s)._session_open_levels(SYMBOL)) == want
+
+
+@pytest.mark.parametrize('value,missing', [
+    (OSError('unavailable'), []), (None, []), ('empty', []),
+    ('no_corr', ['פתיחות סשן לא זמינות — בסיס המחיר לא אומת']),
+    ('none', ['פתיחות סשן לא זמינות — בסיס המחיר לא אומת']),
+])
+def test_early_returns_do_not_read_clock(value, missing):
+    if value is None:
+        value = (None, corr())
+    elif isinstance(value, str):
+        value = (bars(0), corr()) if value == 'empty' else (bars(), None if value == 'no_corr' else corr('none'))
+    s = RawSource({('5m', 3): value}, RuntimeError('clock must not be read'))
+    absent = []
+    assert api().LevelmapOperation(s)._session_open_levels(SYMBOL, absent) == []
+    assert absent == missing
+    assert s.calls == [('fetch', SYMBOL, '5m', 3)]
+
+
+@pytest.mark.parametrize('now', ['2026-09-09T07:00', '2026-09-09T10:00+03:00'])
+def test_explicit_time_bypasses_clock_but_not_fetch(now):
+    s = RawSource({('5m', 3): (bars(), corr())}, RuntimeError('not called'))
+    assert named(api().LevelmapOperation(s)._session_open_levels(SYMBOL, now=now)) == [('LONDON-OPEN', 103)]
+    assert s.calls == [('fetch', SYMBOL, '5m', 3)]
+    s.frames = {}
+    assert api().LevelmapOperation(s)._session_open_levels(SYMBOL, now=now) == []
+
+
+def test_missing_exact_open_is_not_nearest_and_duplicate_uses_first():
+    s = RawSource({('5m', 3): (bars(end='2026-09-09T07:05Z'), corr())},
+                  pd.Timestamp('2026-09-09T08:00Z'))
+    missing = []
+    reader = api().LevelmapOperation(s)
+    assert reader._session_open_levels(SYMBOL, missing) == []
+    assert missing == ['LONDON-OPEN לא זמינה — נר הפתיחה לא בקלטת']
+    duplicate = pd.concat([bars(), bars(row=(199, 200, 90, 100))])
+    s.frames[('5m', 3)] = (duplicate, corr())
+    assert named(reader._session_open_levels(SYMBOL)) == [('LONDON-OPEN', 103)]
+
+
+@pytest.mark.parametrize('seam,want', [
+    ('2026-09-09T07:00Z', [('LONDON-OPEN', 103)]),
+    ('2026-09-09T07:00:00.000001Z', []),
+])
+def test_session_splice_is_per_opening_bar(seam, want):
+    s = RawSource({('5m', 3): (bars(), corr('tv_spliced', pd.Timestamp(seam)))},
+                  pd.Timestamp('2026-09-09T08:00Z'))
+    missing = []
+    assert named(api().LevelmapOperation(s)._session_open_levels(SYMBOL, missing)) == want
+    assert missing == ([] if want else ["LONDON-OPEN לא זמינה — נר הפתיחה מהפרוקסי, לא מהצ'ארט"])
+
+
+def test_native_btc_session_still_rejects_source_none():
+    symbol = 'BINANCE:BTCUSDT'
+    s = RawSource({('5m', 3): (bars(), corr('none', symbol=symbol))}, RuntimeError('unused'))
+    assert api().LevelmapOperation(s)._session_open_levels(symbol) == []
+    assert s.calls == [('fetch', symbol, '5m', 3)]
+
+
+@pytest.mark.parametrize('failure', ['clock', 'index', 'open'])
+def test_post_fetch_failures_are_not_silently_swallowed(failure):
+    frame = bars()
+    now = pd.Timestamp('2026-09-09T08:00Z')
+    if failure == 'clock':
+        now = RuntimeError('raw clock')
+    elif failure == 'index':
+        frame.index = ['not a date']
+    else:
+        frame = frame.drop(columns='open')
+    s = RawSource({('5m', 3): (frame, corr())}, now)
+    with pytest.raises({'clock': RuntimeError, 'index': ValueError, 'open': KeyError}[failure]):
+        api().LevelmapOperation(s)._session_open_levels(SYMBOL)
+    assert s.calls == [('fetch', SYMBOL, '5m', 3)] + ([] if failure == 'index' else [('clock',)])
+
+
+@pytest.mark.parametrize('source,symbol,seam,want', [
+    (None, SYMBOL, None, False), ('tv_daily', SYMBOL, None, True),
+    ('mt5_broker', SYMBOL, None, True), ('none', SYMBOL, None, False),
+    ('tv_live', SYMBOL, None, False), ('tv_spliced', SYMBOL, None, False),
+    ('none', 'BINANCE:BTCUSDT', None, True),
+    ('tv_spliced', 'BINANCE:BTCUSDT', NOW, True),
+])
+def test_shape_early_branches_never_read_clock(source, symbol, seam, want):
+    s = RawSource(now=RuntimeError('unneeded clock'))
+    c = None if source is None else corr(source, seam, symbol)
+    assert api('basis_operation').BasisOperation(s).broker_shape_ok(c, 20) is want
+    assert s.calls == []
+
+
+@pytest.mark.parametrize('days', [7, 20])
+@pytest.mark.parametrize('offset,want', [(-1, False), (0, True), (1, True)])
+def test_shape_splice_threshold_uses_current_operation_time(days, offset, want):
+    s = RawSource(now=NOW + pd.Timedelta(microseconds=offset))
+    c = corr('tv_spliced', NOW - pd.Timedelta(days=days))
+    assert api('basis_operation').BasisOperation(s).broker_shape_ok(c, days) is want
+    assert s.calls == [('clock',)]
+
+
+def full_source():
+    daily = bars(220, end='2026-09-09T00:00Z', freq='1D', row=(100, 110, 90, 100))
+    daily.iloc[-1] = [100, 115, 95, 110]
+    opening = pd.concat([bars(), bars(end='2026-09-09T13:30Z', row=(107, 110, 90, 100))])
+    return RawSource({
+        ('1d', 400): (daily, corr()), ('5m', 3): (opening, corr()),
+        ('1h', 20): (bars(33, end='2026-09-07T06:00Z', freq='1h', row=(100, 150, 80, 100)), corr()),
+        ('1h', 240): (bars(1600, freq='1h', row=(100, 110, 90, 100)), corr()),
+        ('4h', 240): (bars(400, freq='4h', row=(100, 110, 90, 100)), corr()),
+    })
+
+
+def test_full_map_real_calculations_prices_identity_and_operation_order():
+    s = full_source()
+    missing = []
+    levels, c = api().LevelmapOperation(s).build(SYMBOL, missing)
+    assert named(levels) == [
+        ('ADR-HI', 115), ('ADR-LO', 95), ('AWR-HI', 110), ('AWR-LO', 95),
+        ('RW-HI', 110), ('RW-LO', 95), ('AMR-HI', 110), ('AMR-LO', 95),
+        ('ADR50-HI', 110), ('ADR50-LO', 90), ('AWR50-HI', 110), ('AWR50-LO', 90),
+        ('AMR50-HI', 110), ('AMR50-LO', 90), ('RD-HI', 115), ('RD-LO', 95),
+        ('YDAY-HI', 110), ('YDAY-LO', 90), ('YDAY-CLOSE', 100),
+        ('D2-HI', 110), ('D2-LO', 90), ('D3-HI', 110), ('D3-LO', 90),
+        ('D4-HI', 110), ('D4-LO', 90), ('LWEEK-HI', 110), ('LWEEK-LO', 90),
+        ('DAY-OPEN', 100), ('WEEK-OPEN', 100), ('LONDON-OPEN', 103), ('NY-OPEN', 107),
+        ('PSY-HI', 150), ('PSY-LO', 80), ('EMA200-1h', pytest.approx(100, abs=1e-10)),
+        ('EMA800-1h', pytest.approx(100, abs=1e-10)), ('CLOUD50-4h', 100),
+        ('EMA200-4h', pytest.approx(100, abs=1e-10)),
+        ('Q-WHOLE', 100), ('Q-QUARTER', 125), ('Q-QUARTER', 75), ('Q-HALF', 150),
+    ]
+    from trading_system.tree_replay._vendor.levelmap_build import NamedLevel
+    assert all(type(x) is NamedLevel for x in levels)
+    assert [x.kind for x in levels] == ['level'] * 31 + ['psy'] * 2 + ['ema'] * 4 + ['quarter'] * 4
+    assert c is s.frames[('1d', 400)][1]
+    assert missing == []
+    assert s.calls == [('fetch', SYMBOL, '1d', 400), ('fetch', SYMBOL, '5m', 3), ('clock',),
+                       ('fetch', SYMBOL, '1h', 20), ('fetch', SYMBOL, '1h', 240), ('fetch', SYMBOL, '4h', 240)]
+
+
+def test_daily_fetch_failure_stops_build():
+    s = RawSource()
+    missing = []
+    assert api().LevelmapOperation(s).build(SYMBOL, missing) == ([], None)
+    assert missing == []
+    assert s.calls == [('fetch', SYMBOL, '1d', 400)]
+
+
+def test_late_shape_clocks_and_separate_family_gates():
+    s = full_source()
+    before = pd.Timestamp('2026-09-09T06:59:59Z')
+    opened = pd.Timestamp('2026-09-09T07:00Z')
+    s.now = before
+    s.frames[('1d', 400)] = (s.frames[('1d', 400)][0], corr('tv_spliced', opened - pd.Timedelta(days=20)))
+    s.frames[('1h', 20)] = (s.frames[('1h', 20)][0], corr('tv_spliced', opened - pd.Timedelta(days=7)))
+    s.after = {('5m', 3): opened}
+    levels, _ = api().LevelmapOperation(s).build(SYMBOL)
+    prices = dict(named(levels))
+    assert 'ADR-HI' not in prices and 'RD-HI' not in prices
+    assert prices['ADR50-HI'] == 110 and prices['LONDON-OPEN'] == 103
+    assert prices['PSY-HI'] == 150 and prices['PSY-LO'] == 80
+    assert 'NY-OPEN' not in prices
+    assert s.calls == [('fetch', SYMBOL, '1d', 400), ('clock',), ('fetch', SYMBOL, '5m', 3),
+                       ('clock',), ('fetch', SYMBOL, '1h', 20), ('clock',),
+                       ('fetch', SYMBOL, '1h', 240), ('fetch', SYMBOL, '4h', 240)]
+
+
+@pytest.mark.parametrize('first,fallback', [('proxy', True), ('empty', True), ('error', False)])
+def test_psy_fallback_preserves_original_outer_catch(first, fallback):
+    s = full_source()
+    frame, c = s.frames[('1h', 20)]
+    s.frames[('15m', 20)] = (frame, c)
+    s.frames[('1h', 20)] = {'proxy': (frame, corr('none')), 'empty': (frame.iloc[:0], c),
+                           'error': OSError('failed hourly fetch')}[first]
+    levels, _ = api().LevelmapOperation(s).build(SYMBOL)
+    assert [(x.name, x.price) for x in levels if x.kind == 'psy'] == ([('PSY-HI', 150), ('PSY-LO', 80)] if fallback else [])
+    assert (('fetch', SYMBOL, '15m', 20) in s.calls) is fallback
+    assert [x.name for x in levels if x.kind == 'ema'] == ['EMA200-1h', 'EMA800-1h', 'CLOUD50-4h', 'EMA200-4h']

warning: in the working copy of 'docs/architecture/LEVELMAP-OPERATION-CLOCK-USAGE.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/docs/architecture/LEVELMAP-OPERATION-CLOCK-USAGE.md b/docs/architecture/LEVELMAP-OPERATION-CLOCK-USAGE.md
new file mode 100644
index 0000000..3c7186c
--- /dev/null
+++ b/docs/architecture/LEVELMAP-OPERATION-CLOCK-USAGE.md
@@ -0,0 +1,37 @@
+# Private operation-clock level map
+
+Implementation under review; not full-tree or historical replay certification.
+
+`BasisOperation(source)` forwards `fetch_corrected(symbol,timeframe,lookback)`
+and `now_utc()` without caching, validation or added catches. Its
+`broker_shape_ok(corr,days)` is the original predicate, not a source-supplied
+verdict. Only a non-native tv_spliced correction with tv_from reads the clock.
+
+`LevelmapOperation(source).build(symbol,missing=None)` uses that facade with
+the actual accepted range, back-day, session, EMA and quarter calculations.
+It returns original `NamedLevel` instances and the fetched daily correction.
+No pivots are added. The raw source must supply actual Correction-compatible
+objects and pandas OHLC frames, not computed levels or readiness decisions.
+
+The session helper `_session_open_levels(symbol,missing=None,now=None)` first
+fetches 5m/3, then checks nonempty data and correction provenance. Only then
+does it read the operation clock. Explicit now bypasses that read but not the
+fetch or gates. Venue DST/weekdays, exact opening bar, first duplicate and
+the splice seam are retained; exceptions outside the original fetch catch
+remain visible. A raw fetch can advance time, so a session opening during
+that operation is visible to the subsequent check.
+
+Daily shape qualification (20 days), session-open eligibility and PSY shape
+qualification (7 days) remain distinct. Full build order is daily/ranges,
+session opens, preferred hourly PSY with original conditional fallback,
+converged hourly/four-hour EMAs, then quarters. Earlier frames are not fetched
+again or retroactively updated when time advances.
+
+The existing fixed-T public map and its audit are unchanged. This private
+variant is for future actual tree/caller composition, not a replacement API.
+Raw ports do not prove publication cutoffs, calendar/feed coverage, full
+lifecycle, execution, economic labels, a dataset or training readiness.
+No acquisition, live alert, deployment or trading permissions are implied.
+
+Source authority and exact projection: LEVELMAP-OPERATION-CLOCK-CONTRACT.md.
+Source-audit CLI and independent acceptance are pending Task2/final review.

warning: in the working copy of 'trading_system/tree_spec/levelmap_operation_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_spec/levelmap_operation_source.py b/trading_system/tree_spec/levelmap_operation_source.py
new file mode 100644
index 0000000..805c4a2
--- /dev/null
+++ b/trading_system/tree_spec/levelmap_operation_source.py
@@ -0,0 +1,143 @@
+"""Inert audit of operation-clock map projections and their actual source graph."""
+
+import ast
+import hashlib
+from pathlib import Path
+
+from tools.check_levelmap_source_parity import check_source_parity as audit_levelmap
+from .tracker_admission_source import (
+    INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _selected, _without_doc,
+)
+
+ROOT = Path(__file__).resolve().parents[2]
+COMMIT = '68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
+BLOBS = {
+    'basis': 'f3396f3a9fefd71f0f71422001a5521af0a05cd2',
+    'levelmap': '01fc9fe098aa7a5991ce62c3a83e870e4f0d5a2e',
+}
+SOURCE_IMPORTS = {
+    'basis': '''from __future__ import annotations
+import json
+import sys
+import time
+from dataclasses import dataclass
+from pathlib import Path
+import pandas as pd
+from . import symbols''',
+    'levelmap': '''from __future__ import annotations
+from dataclasses import dataclass, field
+import pandas as pd
+from . import basis, data, quarters, sessions, tr''',
+}
+IMPORTS = {
+    'basis': '''import pandas as pd
+from .correction import EXCHANGE_NATIVE''',
+    'levelmap': '''from __future__ import annotations
+import pandas as pd
+from . import map_tr as tr, quarters, map_sessions as sessions
+from .back_days import _back_day_levels
+from .levelmap_build import NamedLevel, SESSION_OPEN_LEVELS, _ema_levels
+from .basis_operation import BasisOperation''',
+}
+SIGNATURES = {
+    'basis': 'def broker_shape_ok(corr, days: float) -> bool: pass',
+    'levelmap': '''def _session_open_levels(symbol: str, missing: list | None = None, now=None) -> list[NamedLevel]: pass
+def build(symbol: str, missing: list | None = None) -> tuple[list[NamedLevel], "basis.Correction | None"]: pass''',
+}
+CLASSES = {
+    'basis': '''class BasisOperation:
+    def __init__(self, source):
+        self.source = source
+    def fetch_corrected(self, symbol, timeframe, lookback):
+        return self.source.fetch_corrected(symbol, timeframe, lookback)
+    def now_utc(self):
+        return self.source.now_utc()''',
+    'levelmap': '''class LevelmapOperation:
+    def __init__(self, source):
+        self.source = BasisOperation(source)''',
+}
+REPLACEMENTS = {
+    'broker_shape_ok': [('pd.Timestamp.now("UTC")', 'pd.Timestamp(self.source.now_utc())')],
+    '_session_open_levels': [('pd.Timestamp.now("UTC")', 'pd.Timestamp(self.source.now_utc())')],
+    'build': [('_session_open_levels(symbol, missing)', 'self._session_open_levels(symbol, missing)'),
+              ('_ema_levels(symbol, missing)', '_ema_levels(symbol, missing, source=self.source)')],
+}
+
+
+def _projection(file, text):
+    """Selected bodies remain intact except for independently enumerated ports."""
+    tree = ast.parse(text)
+    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
+    if [_dump(n) for n in imports] != [_dump(n) for n in ast.parse(SOURCE_IMPORTS[file]).body]:
+        raise ValueError('SOURCE_IMPORT_MISMATCH:' + file)
+    signatures = ast.parse(SIGNATURES[file]).body
+    selected = _selected(text, [n.name for n in signatures])
+    cls = ast.parse(CLASSES[file]).body[0]
+    for node, signature in zip(selected, signatures):
+        if not isinstance(node, ast.FunctionDef) or node.decorator_list or (
+            _dump(node.args) != _dump(signature.args) or _dump(node.returns) != _dump(signature.returns)
+        ):
+            raise ValueError('SOURCE_SIGNATURE_MISMATCH:' + signature.name)
+        node.args.args.insert(0, ast.arg(arg='self'))
+        for old, new in REPLACEMENTS[node.name]:
+            _replace_exact(node, old, new)
+        if file == 'levelmap':
+            first = node.body[0]
+            has_doc = isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)
+            node.body.insert(int(has_doc), ast.parse('basis = self.source').body[0])
+        cls.body.append(node)
+    return ast.parse(IMPORTS[file]).body + [cls]
+
+
+def audit_levelmap_operation_source(source_root):
+    """Source parity is not certification of historical inputs or replay readiness."""
+    blockers, checked, dependencies = [], [], {}
+    report = dict(status='BLOCKED', source_subset_verified=False, blockers=blockers,
+                  checked_projections=checked, dependencies=dependencies,
+                  source_commits={'chart-desk': COMMIT}, ready_for_replay=False, ready_for_training=False)
+    try:
+        root = Path(source_root) / 'chart-desk'
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_ROOT_INVALID:' + type(exc).__name__)
+        return report
+    try:
+        if Path(_git(root, '--show-toplevel')).resolve() != root.resolve():
+            blockers.append('NOT_REPOSITORY_ROOT')
+        if _git(root, 'HEAD') != COMMIT:
+            blockers.append('SOURCE_COMMIT_MISMATCH')
+        baseline = _read_json(ROOT / 'configs/trees/existing-alerts-baseline.json')
+        if [r.get('commit') for r in baseline['repositories'] if r.get('name') == 'chart-desk'] != [COMMIT]:
+            blockers.append('BASELINE_COMMIT_MISMATCH')
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_IDENTITY_UNREADABLE:' + type(exc).__name__)
+    for file, blob in BLOBS.items():
+        runtime = file + '_operation'
+        try:
+            text = (root / ('chartdesk/' + file + '.py')).read_text(encoding='utf-8')
+            raw = text.encode('utf-8')
+            if hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() != blob:
+                blockers.append('SOURCE_BLOB_MISMATCH:' + file)
+            expected = _projection(file, text)
+        except INPUT_ERRORS as exc:
+            blockers.append('SOURCE_PROJECTION_UNREADABLE:' + file + ':' + type(exc).__name__)
+            continue
+        try:
+            path = ROOT / ('trading_system/tree_replay/_vendor/' + runtime + '.py')
+            actual = _without_doc(ast.parse(path.read_text(encoding='utf-8')))
+            if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
+                blockers.append('VENDOR_AST_MISMATCH:' + runtime)
+            else:
+                checked.append(runtime)
+        except INPUT_ERRORS as exc:
+            blockers.append('VENDOR_UNREADABLE:' + runtime + ':' + type(exc).__name__)
+    try:
+        result = audit_levelmap(root)
+        dependencies['levelmap'] = result
+        blockers.extend('DEPENDENCY:levelmap:' + b for b in result['blockers'])
+        if result['source_subset_verified'] is not True and not result['blockers']:
+            blockers.append('DEPENDENCY:levelmap:NOT_VERIFIED')
+    except INPUT_ERRORS as exc:
+        blockers.append('DEPENDENCY:levelmap:UNREADABLE:' + type(exc).__name__)
+    if not blockers:
+        report.update(status='VERIFIED', source_subset_verified=True)
+    return report

warning: in the working copy of 'tools/check_levelmap_operation_source_parity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tools/check_levelmap_operation_source_parity.py b/tools/check_levelmap_operation_source_parity.py
new file mode 100644
index 0000000..fac3fe9
--- /dev/null
+++ b/tools/check_levelmap_operation_source_parity.py
@@ -0,0 +1,23 @@
+"""Read-only audit of operation-clock map source and inherited calculations."""
+
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None, ''):
+    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.levelmap_operation_source import audit_levelmap_operation_source
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument('--source-root', type=Path, required=True)
+    result = audit_levelmap_operation_source(parser.parse_args().source_root)
+    print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
+    return 0 if result['source_subset_verified'] else 2
+
+
+if __name__ == '__main__':
+    raise SystemExit(main())

warning: in the working copy of 'tests/tree_spec/test_levelmap_operation_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_spec/test_levelmap_operation_source.py b/tests/tree_spec/test_levelmap_operation_source.py
new file mode 100644
index 0000000..cb461cd
--- /dev/null
+++ b/tests/tree_spec/test_levelmap_operation_source.py
@@ -0,0 +1,216 @@
+"""Projection certification fails closed on semantic, authority and graph drift."""
+
+import ast
+import importlib
+import importlib.util
+import json
+import os
+from pathlib import Path
+import subprocess
+import sys
+
+import pytest
+
+ROOT = Path(__file__).resolve().parents[2]
+SOURCE = Path(os.environ.get('TR_TREE_SOURCE_ROOT', 'C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'))
+VENDOR = ROOT / 'trading_system/tree_replay/_vendor'
+
+
+def api():
+    name = 'trading_system.tree_spec.levelmap_operation_source'
+    assert importlib.util.find_spec(name) is not None, 'operation map auditor missing'
+    return importlib.import_module(name)
+
+
+def intercept(monkeypatch, path, transform):
+    original = Path.read_text
+    def read(p, *args, **kw):
+        text = original(p, *args, **kw)
+        return transform(text) if p.resolve() == path.resolve() else text
+    monkeypatch.setattr(Path, 'read_text', read)
+
+
+def test_exact_projection_and_actual_inherited_graph_verified_not_ready():
+    r = api().audit_levelmap_operation_source(SOURCE)
+    assert r['status'] == 'VERIFIED' and r['source_subset_verified'] and r['blockers'] == []
+    assert r['checked_projections'] == ['basis_operation', 'levelmap_operation']
+    assert r['dependencies']['levelmap']['source_subset_verified']
+    assert not r['ready_for_replay'] and not r['ready_for_training']
+
+
+@pytest.mark.parametrize('file,old,new', [
+    ('basis_operation', 'self.source = source', 'self.source = None'),
+    ('basis_operation', 'return self.source.fetch_corrected(symbol, timeframe, lookback)', 'return self.source.fetch_corrected(symbol, timeframe, 1)'),
+    ('basis_operation', 'return self.source.now_utc()', 'return None'),
+    ('basis_operation', 'days: float', 'days: int'),
+    ('basis_operation', 'corr.symbol in EXCHANGE_NATIVE', 'True'),
+    ('basis_operation', 'age_days >= days', 'age_days > days'),
+    ('basis_operation', 'pd.Timestamp(self.source.now_utc())', 'pd.Timestamp.now("UTC")'),
+    ('levelmap_operation', 'self.source = BasisOperation(source)', 'self.source = source'),
+    ('levelmap_operation', 'from .basis_operation import BasisOperation', 'from .basis_operation import BasisOperation\nimport socket'),
+    ('levelmap_operation', 'from .levelmap_build import NamedLevel, SESSION_OPEN_LEVELS, _ema_levels', 'from .fake import NamedLevel, SESSION_OPEN_LEVELS, _ema_levels'),
+    ('levelmap_operation', 'now=None', 'now=0'),
+    ('levelmap_operation', 'start <= local < end', 'start <= local <= end'),
+    ('levelmap_operation', 'idx == at', 'idx >= at'),
+    ('levelmap_operation', 'hit["open"].iloc[0]', 'hit["open"].iloc[-1]'),
+    ('levelmap_operation', 'at < pd.Timestamp(corr.tv_from)', 'at <= pd.Timestamp(corr.tv_from)'),
+    ('levelmap_operation', 'pd.Timestamp(self.source.now_utc())', 'pd.Timestamp.now("UTC")'),
+    ('levelmap_operation', 'basis.broker_shape_ok(corr, 20)', 'True'),
+    ('levelmap_operation', 'basis.broker_shape_ok(ccorr, 7)', 'True'),
+    ('levelmap_operation', 'cand.index >= ccorr.tv_from', 'cand.index < ccorr.tv_from'),
+    ('levelmap_operation', 'self._session_open_levels(symbol, missing)', '[]'),
+    ('levelmap_operation', '_ema_levels(symbol, missing, source=self.source)', '[]'),
+])
+def test_candidate_drift_blocks(monkeypatch, file, old, new):
+    m = api()
+    path = VENDOR / (file + '.py')
+    assert old in path.read_text(encoding='utf-8')
+    intercept(monkeypatch, path, lambda s: s.replace(old, new))
+    r = m.audit_levelmap_operation_source(SOURCE)
+    assert not r['source_subset_verified']
+    assert 'VENDOR_AST_MISMATCH:' + file in r['blockers']
+
+
+@pytest.mark.parametrize('file', ['basis', 'levelmap'])
+@pytest.mark.parametrize('fault', ['blob', 'syntax', 'missing'])
+def test_both_source_files_are_required(monkeypatch, file, fault):
+    m = api()
+    def change(s):
+        if fault == 'missing':
+            raise FileNotFoundError('source missing')
+        return s + ('\ndef syntax error' if fault == 'syntax' else '\n# drift\n')
+    intercept(monkeypatch, SOURCE / ('chart-desk/chartdesk/' + file + '.py'), change)
+    r = m.audit_levelmap_operation_source(SOURCE)
+    assert not r['source_subset_verified'] and r['blockers']
+    assert any(file in b for b in r['blockers'])
+
+
+@pytest.mark.parametrize('fault', ['head', 'root', 'baseline'])
+def test_identity_is_not_redefined_by_candidate(monkeypatch, fault):
+    m = api()
+    if fault == 'baseline':
+        intercept(monkeypatch, ROOT / 'configs/trees/existing-alerts-baseline.json',
+                  lambda s: s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9', '0' * 40))
+        want = 'BASELINE_COMMIT_MISMATCH'
+    else:
+        arg, value, want = ('HEAD', '0' * 40, 'SOURCE_COMMIT_MISMATCH') if fault == 'head' else ('--show-toplevel', str(SOURCE), 'NOT_REPOSITORY_ROOT')
+        original = m._git
+        monkeypatch.setattr(m, '_git', lambda p, *a: value if a == (arg,) else original(p, *a))
+    r = m.audit_levelmap_operation_source(SOURCE)
+    assert not r['source_subset_verified'] and want in r['blockers']
+
+
+@pytest.mark.parametrize('file,old,new', [
+    ('basis', 'import pandas as pd', 'import pandas as altered'),
+    ('basis', 'days: float', 'days: int'),
+    ('basis', 'pd.Timestamp.now("UTC")', 'pd.Timestamp.now()'),
+    ('basis', 'def broker_shape_ok(', 'def removed_broker_shape_ok('),
+    ('levelmap', 'from . import basis, data, quarters, sessions, tr', 'from . import basis, quarters, sessions, tr'),
+    ('levelmap', 'now=None', 'now=0'),
+    ('levelmap', 'pd.Timestamp.now("UTC")', 'pd.Timestamp.now()'),
+    ('levelmap', 'def build(', 'def removed_build('),
+    ('levelmap', 'levels += _ema_levels(symbol, missing)', 'levels += []'),
+])
+def test_source_projection_has_independent_signature_import_and_count_contract(file, old, new):
+    m = api()
+    s = (SOURCE / ('chart-desk/chartdesk/' + file + '.py')).read_text(encoding='utf-8')
+    assert old in s
+    with pytest.raises(ValueError):
+        m._projection(file, s.replace(old, new))
+
+
+@pytest.mark.parametrize('file,addition', [
+    ('basis', '\ndef broker_shape_ok(corr, days: float) -> bool: return False\n'),
+    ('levelmap', '\ndef build(symbol: str, missing: list | None = None): return [], None\n'),
+])
+def test_duplicate_selected_source_nodes_rejected(file, addition):
+    m = api()
+    s = (SOURCE / ('chart-desk/chartdesk/' + file + '.py')).read_text(encoding='utf-8')
+    with pytest.raises(ValueError):
+        m._projection(file, s + addition)
+
+
+@pytest.mark.parametrize('result,want', [
+    ({'source_subset_verified': False, 'blockers': []}, 'DEPENDENCY:levelmap:NOT_VERIFIED'),
+    ({'source_subset_verified': True, 'blockers': ['real drift']}, 'DEPENDENCY:levelmap:real drift'),
+    (OSError('unreadable'), 'DEPENDENCY:levelmap:UNREADABLE:OSError'),
+])
+def test_inherited_failure_propagates(monkeypatch, result, want):
+    m = api()
+    def dependency(root):
+        assert root == SOURCE / 'chart-desk'
+        if isinstance(result, Exception):
+            raise result
+        return result
+    monkeypatch.setattr(m, 'audit_levelmap', dependency)
+    r = m.audit_levelmap_operation_source(SOURCE)
+    assert not r['source_subset_verified'] and want in r['blockers']
+
+
+def test_real_inherited_ema_drift_blocks(monkeypatch):
+    m = api()
+    path = VENDOR / 'levelmap_build.py'
+    intercept(monkeypatch, path, lambda s: s.replace('len(df) >= 2 * n', 'len(df) >= n'))
+    r = m.audit_levelmap_operation_source(SOURCE)
+    assert not r['source_subset_verified']
+    assert any(b.startswith('DEPENDENCY:levelmap:') for b in r['blockers'])
+
+
+def test_invalid_root_and_missing_candidate_block(tmp_path, monkeypatch):
+    m = api()
+    for root in [None, tmp_path]:
+        r = m.audit_levelmap_operation_source(root)
+        assert not r['source_subset_verified'] and r['blockers']
+    intercept(monkeypatch, VENDOR / 'levelmap_operation.py', lambda s: 'def invalid syntax')
+    r = m.audit_levelmap_operation_source(SOURCE)
+    assert 'VENDOR_UNREADABLE:levelmap_operation:SyntaxError' in r['blockers']
+
+
+@pytest.mark.parametrize('file', ['basis_operation', 'levelmap_operation'])
+def test_missing_either_candidate_blocks(monkeypatch, file):
+    m = api()
+    def unavailable(text):
+        raise FileNotFoundError('candidate unavailable')
+    intercept(monkeypatch, VENDOR / (file + '.py'), unavailable)
+    r = m.audit_levelmap_operation_source(SOURCE)
+    assert not r['source_subset_verified']
+    assert 'VENDOR_UNREADABLE:' + file + ':FileNotFoundError' in r['blockers']
+
+
+@pytest.mark.parametrize('file,method', [('basis', 'broker_shape_ok'), ('levelmap', '_session_open_levels')])
+def test_duplicate_clock_expression_rejected_by_count(file, method):
+    m = api()
+    tree = ast.parse((SOURCE / ('chart-desk/chartdesk/' + file + '.py')).read_text(encoding='utf-8'))
+    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == method)
+    node.body.append(ast.parse('pd.Timestamp.now("UTC")').body[0])
+    with pytest.raises(ValueError, match='count=2'):
+        m._projection(file, ast.unparse(tree))
+
+
+def test_selected_source_order_is_not_silently_reordered():
+    m = api()
+    tree = ast.parse((SOURCE / 'chart-desk/chartdesk/levelmap.py').read_text(encoding='utf-8'))
+    indices = [i for i, n in enumerate(tree.body) if isinstance(n, ast.FunctionDef) and n.name in ('_session_open_levels', 'build')]
+    assert len(indices) == 2
+    a, b = indices
+    tree.body[a], tree.body[b] = tree.body[b], tree.body[a]
+    with pytest.raises(ValueError, match='SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH'):
+        m._projection('levelmap', ast.unparse(tree))
+
+
+def test_cli_from_unrelated_directory_and_inert_imports(tmp_path):
+    api()
+    for root, status in [(SOURCE, 0), (tmp_path, 2)]:
+        p = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/check_levelmap_operation_source_parity.py'),
+                            '--source-root', str(root)], cwd=tmp_path, capture_output=True, text=True, timeout=90)
+        assert p.returncode == status, p.stderr
+        r = json.loads(p.stdout)
+        assert r['source_subset_verified'] == (status == 0)
+        assert not r['ready_for_replay'] and not r['ready_for_training']
+    code = '\n'.join(['import sys', 'class Guard:', '    def find_spec(self,fullname,*a):',
+        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')): raise AssertionError(fullname)",
+        'sys.meta_path.insert(0,Guard())',
+        'from trading_system.tree_spec.levelmap_operation_source import audit_levelmap_operation_source',
+        "assert audit_levelmap_operation_source(sys.argv[1])['source_subset_verified']"])
+    p = subprocess.run([sys.executable, '-B', '-c', code, str(SOURCE)], cwd=ROOT, capture_output=True, text=True, timeout=90)
+    assert p.returncode == 0, p.stderr
