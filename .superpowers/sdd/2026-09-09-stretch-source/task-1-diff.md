# Full untracked additions; base/HEAD c1b6071633c55376c64f0a98ece843706f420f49

diff --git a/trading_system/tree_replay/_vendor/stretch.py b/trading_system/tree_replay/_vendor/stretch.py
new file mode 100644
index 0000000..b8bb3ba
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/stretch.py
@@ -0,0 +1,128 @@
+"""Original stretch calculations over explicit local ports; not feed certification.
+
+Actual dependency uses ADR14 and open +/- ADR/2; source prose is not the formula.
+"""
+from __future__ import annotations
+from dataclasses import dataclass
+from . import tr, ranges
+BUDGET_MIN = 1.25
+BEYOND_MIN = 0.0
+BEYOND_EXTREME = 0.5
+DEV_STRETCHED = 3.0
+
+@dataclass
+class Stretch:
+    """How much of the day is already spent, measured from the open."""
+    symbol: str
+    close: float
+    day_open: float
+    adr: float
+    budget_used: float
+    rail_hi: float
+    rail_lo: float
+    beyond: float
+    side: str | None
+    devs: dict
+
+    @property
+    def is_extended(self) -> bool:
+        """Budget spent AND price outside the open-anchored range."""
+        return self.budget_used >= BUDGET_MIN and self.beyond > BEYOND_MIN
+
+    @property
+    def direction(self) -> str | None:
+        """The direction the tape has overshot in, in Sagiv's vocabulary."""
+        if not self.is_extended:
+            return None
+        return 'לונג' if self.side == 'up' else 'שורט'
+
+    @property
+    def max_dev(self) -> float:
+        return max((abs(v) for v in self.devs.values()), default=0.0)
+
+    def contradicts(self, direction: str) -> bool:
+        """Does a call in `direction` mean 'keep going' on a tape already spent?
+
+        Deliberately narrow. This is not "the trend is old" — it is the exact
+        conjunction Sagiv named: the tools say continue, in the same direction
+        the day has already overshot its own average range in.
+        """
+        return self.is_extended and direction == self.direction
+
+    def line(self) -> str:
+        """The one-line extension note that rides along with every alert."""
+        word = 'מתיחה קיצונית' if self.beyond >= BEYOND_EXTREME else 'מתוח'
+        rail = self.rail_hi if self.side == 'up' else self.rail_lo
+        parts = [f"  ⚠ {word}: {self.budget_used:.0%} מ-ADR נוצל · {self.beyond:+.2f} ADR מעבר לפס {('העליון' if self.side == 'up' else 'התחתון')} ({rail:,.2f}, מפתיחת היום {self.day_open:,.2f})"]
+        if self.max_dev >= DEV_STRETCHED:
+            worst = max(self.devs.items(), key=lambda kv: abs(kv[1]))
+            parts.append(f'     מרחק מהענן: {worst[1]:+.1f} ATR ({worst[0]}) — חלון פתוח, חוב שטרם נפרע')
+        return '\n'.join(parts)
+
+    def render(self) -> str:
+        """Standalone block, for briefs that want the state on its own."""
+        head = f"◈ {self.symbol.split(':')[-1]} — מצב מתיחה @ {self.close:,.2f}"
+        if not self.is_extended:
+            return f'{head}\n  תקציב יומי {self.budget_used:.0%} מ-ADR · בתוך הטווח מהפתיחה — אין מתיחה'
+        return f'{head}\n{self.line()}'
+
+def _atr(df, n: int=14) -> float:
+    import pandas as pd
+    prev = df['close'].shift(1)
+    rng = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
+    return float(rng.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])
+
+class StretchReader:
+
+    def __init__(self, source):
+        self.source = source
+
+    def _dev_from_cloud(self, symbol: str, tf: str, days: int) -> float | None:
+        """Distance from the EMA50 cloud in ATRs — uncapped, unlike matrix's score."""
+        try:
+            df, _ = self.source.fetch_corrected(symbol, tf, days)
+            if len(df) < 60:
+                return None
+            e = tr.emas(df)
+            cloud = float(e['ema50'].iloc[-1])
+            atr = _atr(df)
+            if not atr:
+                return None
+            return (float(df['close'].iloc[-1]) - cloud) / atr
+        except Exception:
+            return None
+
+    def state(self, symbol: str) -> Stretch | None:
+        """Current extension state, or None when the inputs cannot support one."""
+        try:
+            daily, dcorr = self.source.fetch_corrected(symbol, '1d', 400)
+            if daily.empty or not self.source.broker_shape_ok(dcorr, 20):
+                return None
+            lv = ranges.tr_levels(daily, ranges.weekly_from_daily(daily), broker_bars=True)
+        except Exception:
+            return None
+        af = lv.get('adr_from_open') or {}
+        if not (af.get('available') and af.get('verified')):
+            return None
+        adr = float(af.get('range') or 0)
+        rail_hi, rail_lo = (af.get('high'), af.get('low'))
+        if not adr or rail_hi is None or rail_lo is None:
+            return None
+        rail_hi, rail_lo = (float(rail_hi), float(rail_lo))
+        today = daily.iloc[-1]
+        day_open = float(today['open'])
+        close = float(today['close'])
+        budget = float(today['high'] - today['low']) / adr
+        if close > rail_hi:
+            beyond, side = ((close - rail_hi) / adr, 'up')
+        elif close < rail_lo:
+            beyond, side = ((rail_lo - close) / adr, 'down')
+        else:
+            beyond, side = (0.0, None)
+        devs = {}
+        for tf, days in (('15m', 20), ('1h', 60), ('4h', 240)):
+            d = self._dev_from_cloud(symbol, tf, days)
+            if d is not None:
+                devs[tf] = d
+        return Stretch(symbol=symbol, close=close, day_open=day_open, adr=adr, budget_used=budget, rail_hi=rail_hi, rail_lo=rail_lo, beyond=beyond, side=side, devs=devs)
+

diff --git a/tests/tree_replay/test_stretch.py b/tests/tree_replay/test_stretch.py
new file mode 100644
index 0000000..30c2a13
--- /dev/null
+++ b/tests/tree_replay/test_stretch.py
@@ -0,0 +1,200 @@
+"""Source-characterization tests use real ranges, seeded EMA and shape policy."""
+import importlib
+import importlib.util
+import math
+
+import pandas as pd
+import pytest
+from pandas.testing import assert_frame_equal
+
+from trading_system.tree_replay._vendor.correction import Correction, broker_shape_ok_at
+
+
+NOW = pd.Timestamp('2026-09-09T16:00:00Z')
+SYMBOL = 'OANDA:XAUUSD'
+LONG, SHORT = 'לונג', 'שורט'
+REQUESTS = [('1d', 400), ('15m', 20), ('1h', 60), ('4h', 240)]
+
+
+def api():
+    name = 'trading_system.tree_replay._vendor.stretch'
+    assert importlib.util.find_spec(name) is not None, 'stretch calculation missing'
+    return importlib.import_module(name)
+
+
+def daily(close=116., high=126., low=100., n=22):
+    # Old seven days have range200; the last14 completed days have range20.
+    # A wrong20-day average or inclusion of today's range changes the result.
+    widths = [200.] * max(0, n-15) + [20.] * min(14, n-1)
+    return pd.DataFrame({
+        'open': [100.]*n, 'high': [100.+w/2 for w in widths]+[high],
+        'low': [100.-w/2 for w in widths]+[low],
+        'close': [100.]*(n-1)+[close],
+    }, index=pd.date_range(end=NOW.normalize(), periods=n, freq='D'))
+
+
+def intraday(n=60, flat=False):
+    closes = [100.] * n if flat else [100.+i for i in range(n)]
+    width = 0. if flat else 1.
+    return pd.DataFrame({'open': closes, 'high': [c+width for c in closes],
+        'low': [c-width for c in closes], 'close': closes},
+        index=pd.date_range(end=NOW, periods=n, freq='15min'))
+
+
+class Ports:
+    def __init__(self, frame=None, *, symbol=SYMBOL, corr=None):
+        self.symbol = symbol
+        self.corr = corr if corr is not None else Correction(symbol, 0., 'tv_daily', 'high', 'fixture')
+        self.frames = dict(zip(REQUESTS, [daily() if frame is None else frame,
+                                          intraday(), intraday(), intraday()]))
+        self.calls = []
+        self.now = NOW
+        self.shape_error = None
+
+    def fetch_corrected(self, symbol, timeframe, days):
+        self.calls.append(('fetch', symbol, timeframe, days))
+        assert symbol == self.symbol
+        f = self.frames[timeframe, days]
+        if isinstance(f, Exception):
+            raise f
+        # Intraday correction is deliberately unverified; original dev ignores it.
+        c = self.corr if timeframe == '1d' else Correction(symbol, 0., 'none', 'unknown', 'fixture')
+        return f, c
+
+    def broker_shape_ok(self, correction, days):
+        self.calls.append(('shape', correction, days))
+        assert correction is self.corr
+        if self.shape_error:
+            raise self.shape_error
+        return broker_shape_ok_at(correction, days, decision_time=self.now)
+
+
+@pytest.mark.parametrize('symbol', [SYMBOL, 'OANDA:NAS100USD', 'BINANCE:BTCUSDT'])
+@pytest.mark.parametrize('close,hi,lo,side,direction', [
+    (116.,126.,100.,'up',LONG), (84.,100.,74.,'down',SHORT),
+])
+def test_full_source_uses_fourteen_prior_ranges_and_half_adr_rails(symbol, close, hi, lo, side, direction):
+    m = api()
+    p = Ports(daily(close,hi,lo), symbol=symbol)
+    originals = {k:v.copy(deep=True) for k,v in p.frames.items()}
+    s = m.StretchReader(p).state(symbol)
+    assert (s.symbol,s.close,s.day_open,s.adr) == (symbol,close,100.,20.)
+    assert (s.rail_hi,s.rail_lo,s.budget_used,s.beyond) == (110.,90.,1.3,.3)
+    assert s.side == side and s.direction == direction and s.is_extended
+    assert s.contradicts(direction)
+    assert not s.contradicts(SHORT if direction == LONG else LONG)
+    assert s.devs == pytest.approx({'15m':12.25,'1h':12.25,'4h':12.25}, rel=0, abs=1e-12)
+    assert s.max_dev == pytest.approx(12.25, rel=0, abs=1e-12)
+    assert p.calls == [('fetch',symbol,'1d',400),('shape',p.corr,20),
+        ('fetch',symbol,'15m',20),('fetch',symbol,'1h',60),('fetch',symbol,'4h',240)]
+    for k,f in originals.items():
+        assert_frame_equal(p.frames[k],f)
+
+
+@pytest.mark.parametrize('hi,close,want,side', [
+    (124.99999,116.,False,'up'), (125.,116.,True,'up'),
+    (125.,110.,False,None), (125.,110.0001,True,'up'),
+    (125.,100.,False,None),
+])
+def test_budget_and_rail_boundaries_and_nonextended_still_read_deviations(hi, close, want, side):
+    m = api()
+    p = Ports(daily(close,hi,100.))
+    s = m.StretchReader(p).state(SYMBOL)
+    assert s.is_extended == want and s.side == side
+    assert s.direction == (LONG if want else None)
+    assert bool(s.contradicts(LONG)) == want
+    assert len(s.devs) == 3
+    assert [c[2:] for c in p.calls if c[0]=='fetch'] == REQUESTS
+
+
+@pytest.mark.parametrize('fault', ['empty','none','short','zero','fetch_error','shape_error','proxy','bad_index'])
+def test_unusable_daily_blocks_before_deviation_reads(fault):
+    m = api()
+    p = Ports()
+    if fault == 'empty': p.frames['1d',400] = pd.DataFrame()
+    elif fault == 'none': p.frames['1d',400] = None
+    elif fault == 'short': p.frames['1d',400] = daily(n=14)
+    elif fault == 'zero': p.frames['1d',400] = intraday(22,flat=True)
+    elif fault == 'fetch_error': p.frames['1d',400] = OSError('offline failure')
+    elif fault == 'shape_error': p.shape_error = OSError('shape unavailable')
+    elif fault == 'proxy': p.corr = Correction(SYMBOL,0.,'cached_stale','low','proxy')
+    elif fault == 'bad_index': p.frames['1d',400] = daily().reset_index(drop=True)
+    assert m.StretchReader(p).state(SYMBOL) is None
+    assert [c[2:] for c in p.calls if c[0]=='fetch'] == [('1d',400)]
+    if fault in ('empty','none','fetch_error'):
+        assert len(p.calls) == 1  # preserve original empty-before-shape short circuit
+
+
+@pytest.mark.parametrize('microseconds,want', [(-1,False),(0,True),(1,True)])
+def test_actual_shape_policy_uses_twenty_day_horizon_not_adr_length(microseconds,want):
+    m = api()
+    c = Correction(SYMBOL,0.,'tv_spliced','high','seam',NOW-pd.Timedelta(days=20))
+    p = Ports(corr=c)
+    p.now += pd.Timedelta(microseconds=microseconds)
+    s = m.StretchReader(p).state(SYMBOL)
+    assert (s is not None) == want
+    if want:
+        assert s.adr == 20. and s.rail_hi == 110.
+
+
+def test_native_venue_shape_uses_original_policy_without_symbol_alias():
+    m = api()
+    sym='BINANCE:BTCUSDT'
+    p=Ports(symbol=sym,corr=Correction(sym,0.,'none','n/a','native'))
+    assert m.StretchReader(p).state(sym).direction == LONG
+    assert all(c[1]==sym for c in p.calls if c[0]=='fetch')
+
+
+@pytest.mark.parametrize('bad', ['short','zero','missing','error','none'])
+def test_one_bad_deviation_drops_only_its_context_not_daily_state(bad):
+    m = api()
+    p=Ports()
+    p.frames['1h',60]={'short':intraday(59),'zero':intraday(flat=True),
+        'missing':pd.DataFrame(index=range(60)),'error':OSError('offline'), 'none':None}[bad]
+    s=m.StretchReader(p).state(SYMBOL)
+    assert s.is_extended and s.devs == pytest.approx({'15m':12.25,'4h':12.25}, rel=0, abs=1e-12)
+    assert p.calls[-1] == ('fetch',SYMBOL,'4h',240)
+
+
+def test_atr_is_unseeded_not_sma_seeded():
+    m=api()
+    f=pd.DataFrame({'high':[101.,120.],'low':[99.,100.],'close':[100.,110.]})
+    assert m._atr(f) == pytest.approx(23/7)
+
+
+def test_source_nan_deviation_is_not_silently_sanitized():
+    m=api()
+    p=Ports()
+    p.frames['15m',20]['close']=float('nan')
+    s=m.StretchReader(p).state(SYMBOL)
+    assert '15m' in s.devs and math.isnan(s.devs['15m'])
+    assert s.devs['1h'] == pytest.approx(12.25, rel=0, abs=1e-12) and s.is_extended
+
+
+@pytest.mark.parametrize('close,wantword,wantrail', [
+    (116.,'מתוח','העליון'), (120.,'מתיחה קיצונית','העליון'),
+    (84.,'מתוח','התחתון'), (80.,'מתיחה קיצונית','התחתון'),
+])
+def test_render_retains_actual_extension_tier_side_and_cloud_distance(close,wantword,wantrail):
+    m=api()
+    p=Ports(daily(close,126. if close>100 else 100.,100. if close>100 else 74.))
+    s=m.StretchReader(p).state(SYMBOL)
+    line=s.line()
+    assert f'⚠ {wantword}: 130% מ-ADR נוצל' in line
+    assert f'מעבר לפס {wantrail}' in line
+    assert 'מרחק מהענן: +12.2 ATR (15m)' in line
+    assert s.render() == f'◈ XAUUSD — מצב מתיחה @ {close:,.2f}\n{line}'
+
+
+def test_render_no_extension_and_cloud_wording_threshold_do_not_change_direction():
+    m=api()
+    s=m.StretchReader(Ports(daily(100.,110.,90.))).state(SYMBOL)
+    assert s.render() == '◈ XAUUSD — מצב מתיחה @ 100.00\n  תקציב יומי 100% מ-ADR · בתוך הטווח מהפתיחה — אין מתיחה'
+    s=m.StretchReader(Ports()).state(SYMBOL)
+    s.devs={'15m':2.99999}
+    assert 'מרחק מהענן' not in s.line()
+    s.devs={'15m':2.,'4h':-3.}
+    assert 'מרחק מהענן: -3.0 ATR (4h)' in s.line()
+    assert s.direction == LONG
+    s.devs={}
+    assert s.max_dev == 0. and 'מרחק מהענן' not in s.line()

diff --git a/docs/architecture/STRETCH-SOURCE-USAGE.md b/docs/architecture/STRETCH-SOURCE-USAGE.md
new file mode 100644
index 0000000..3efb8b3
--- /dev/null
+++ b/docs/architecture/STRETCH-SOURCE-USAGE.md
@@ -0,0 +1,62 @@
+# Original daily extension-state calculation
+
+Private runtime: `trading_system.tree_replay._vendor.stretch.StretchReader`.
+Source identity and complete permitted adaptations: STRETCH-SOURCE-CONTRACT.md.
+This is the original calculated context used by later revalidation, not a new
+signal, public historical provider, economic outcome or model feature export.
+
+```python
+from trading_system.tree_replay._vendor.stretch import StretchReader
+
+# supplied_ports implements fetch_corrected(symbol, timeframe, days) and
+# broker_shape_ok(correction, days); both operate on supplied offline evidence.
+state = StretchReader(supplied_ports).state('OANDA:XAUUSD')
+if state is not None:
+    text = state.render()   # returns text only; sends nothing
+    continued_in_stretched_direction = state.contradicts('לונג')
+```
+
+The complete calculation uses real existing range and EMA implementations.
+Daily request1d/400 is checked by the supplied broker-shape predicate with20
+days. When usable, source builds tr_levels with the real weekly conversion;
+then attempts each deviation15m/20,1h/60,4h/240 in that order. Each uses>=60
+rows, seeded EMA50 and its own unseeded ATR14. Requested days identify the
+request; the runtime does not truncate the delivered history to that count.
+
+## Important executable-versus-prose discrepancy
+
+Source stretch comments describe rails as open +/- ADR and mention ADR20.
+The actual called tr_levels defaults to ADR14; average_range(from_open=True)
+returns open +/- ADR/2. These are the formulas preserved here. Twenty days in
+the shape gate is a different quantity from14 prior rows in the average.
+
+With prior14 daily ranges20 and current O100/H126/L100/C116, actual output is
+ADR20, rails110/90, budget1.3 and beyond0.3. It is extended upwards and conflicts
+with another long continuation, not automatically a short entry. Earlier old
+rows with different ranges and today's range do not change the prior14 average.
+This discrepancy is source characterization, not a silent strategy correction.
+
+is_extended requires budget>=1.25 and beyond>0. Wording thresholds0.50 and3ATR
+do not independently veto anything. Rendering returns the original Hebrew text.
+Insufficient daily/range/shape data returnsNone, distinct from a valid state
+that is not extended. A missing deviation omits only its timeframe. Original
+intraday correction-ignoring, exception and nonfinite numeric behavior remains;
+a raw NaN deviation may exist, so this is not a JSON-safe observation exporter.
+
+## Evidence boundary
+
+The caller supplies the correct instrument, available-at time, current daily
+prefix, full warmup/history and correction evidence. No source price offset is
+applied, no current-day final OHLC is constructed or inferred, no GC/spot alias
+is allowed by implication. Raw source methods do not certify these inputs.
+The existing broker_shape_ok_at can implement the shape port with explicit
+operation time, but neither its boolean nor source tags establish feed coverage.
+
+Audit CLI: `python tools/check_stretch_source_parity.py --source-root <parent-of-chart-desk>`.
+It checks literal pins, full ordered projection and actual range/strictEMA
+dependencies without importing/executing retained source or runtime. A VERIFIED
+result leaves replay/training readiness false; runtime construction does not
+automatically run the auditor. Acceptance requires recorded independent review.
+
+Remaining: causal feed binding, full revalidation and lifecycle/effects/caller,
+other branches, approved economic simulation/data and model evaluation.

