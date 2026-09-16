# Task1 full untracked additions
Base=HEAD=c1b6071633c55376c64f0a98ece843706f420f49. No task commits; full file diffs below.

warning: in the working copy of 'trading_system/tree_replay/_vendor/basis_operation.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/basis_operation.py b/trading_system/tree_replay/_vendor/basis_operation.py
new file mode 100644
index 0000000..ff82b41
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/basis_operation.py
@@ -0,0 +1,46 @@
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
+        """May a RANGE object looking `days` back trust this frame's shape?
+
+        A constant offset shifts a level but never fixes a range, so range-shaped
+        objects (ADR, RD, psy levels, session ranges, yesterday's extremes) need
+        bars that are genuinely his. Pure broker sources qualify outright; a
+        spliced frame qualifies only when its genuine-TV span reaches back at
+        least `days` -- the window being measured must lie entirely on the TV side
+        of the seam.
+        """
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
index 0000000..693a189
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/levelmap_operation.py
@@ -0,0 +1,191 @@
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
+        """LONDON-OPEN / NY-OPEN — the price the session actually opened at.
+
+        04.09 is the case that earned these. Gold's day open sat at 4,476.07 and
+        London opened at 4,462.92 -- thirteen points BELOW it, onto the
+        EMA200-1h/D3-HI/CLOUD50-4h cluster -- and price left that open for
+        4,490.9. The map had no name for where the session began, so the desk
+        could describe the cluster and not the arrival.
+
+        EXACT BAR OR NOTHING. The level is one bar's open price, so the nearest
+        bar is a different number wearing this one's name; a missing bar is
+        reported and the level is omitted. Live from the moment the opening bar
+        exists (a forming bar's open is already final) until the session closes,
+        and never carried into the next day -- yesterday's London open is a fact
+        about yesterday.
+        """
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
