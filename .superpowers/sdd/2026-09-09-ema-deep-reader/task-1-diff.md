# EMA task 1 review package

Base/head: c1b6071633c55376c64f0a98ece843706f420f49 (uncommitted additive files; no commits).

## trading_system/tree_replay/_vendor/ema_windows.py

```diff
diff --git a/trading_system/tree_replay/_vendor/ema_windows.py b/trading_system/tree_replay/_vendor/ema_windows.py
new file mode 100644
index 0000000..e1b7aa4
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/ema_windows.py
@@ -0,0 +1,288 @@
+"""Complete source EMA windows and reader over local inputs; not causal certification."""
+from __future__ import annotations
+from dataclasses import dataclass, field
+import pandas as pd
+from io import BytesIO
+from pathlib import PurePosixPath
+from . import indicators as I
+MT5_SYMBOL_MAP = {'OANDA:XAUUSD': 'XAUUSD', 'OANDA:NAS100USD': 'NAS100', 'BINANCE:BTCUSDT': 'BTCUSD', 'TVC:VIX': 'VIX', 'TVC:DXY': 'DXY'}
+LENGTHS = (5, 7, 13, 50, 200, 800)
+FAST = (5, 7, 13)
+SLOW = (50, 200, 800)
+OPEN_ATR = 0.75
+GLUED_ATR = 0.2
+SLOPE_BARS = 3
+
+@dataclass
+class Window:
+    length: int
+    value: float
+    distance: float
+    atr: float
+    slope_atr: float | None = None
+
+    @property
+    def atr_distance(self) -> float:
+        return self.distance / self.atr if self.atr else 0.0
+
+    @property
+    def rising(self) -> bool | None:
+        """Sign only, for callers that genuinely need a direction."""
+        return None if self.slope_atr is None else self.slope_atr > 0
+
+    @property
+    def is_open(self) -> bool:
+        return abs(self.atr_distance) >= OPEN_ATR
+
+    @property
+    def side(self) -> str:
+        return 'מעל' if self.distance > 0 else 'מתחת'
+
+    def render(self) -> str:
+        state = 'פתוח' if self.is_open else 'סגור'
+        return f'EMA{self.length}: {self.value:,.1f} · {abs(self.distance):,.1f} {self.side} ({abs(self.atr_distance):.1f} ATR) — חלון {state}'
+
+@dataclass
+class EmaState:
+    symbol: str
+    timeframe: str
+    close: float
+    atr: float
+    windows: list[Window]
+    unconverged: list[int] = field(default_factory=list)
+    source: str = ''
+
+    def window(self, length: int) -> Window | None:
+        return next((w for w in self.windows if w.length == length), None)
+
+    @property
+    def trend_strict(self) -> str:
+        """Price above 50 AND 200 AND 800 (his long test, stated with AND)."""
+        need = [self.window(n) for n in SLOW]
+        if any((w is None for w in need)):
+            return 'לא ידוע'
+        if all((w.distance > 0 for w in need)):
+            return 'עולה'
+        if all((w.distance < 0 for w in need)):
+            return 'יורד'
+        return 'מעורב'
+
+    @property
+    def trend_loose(self) -> str:
+        """His short test as spoken: below the 50, the 200 OR the 800."""
+        need = [self.window(n) for n in SLOW]
+        if any((w is None for w in need)):
+            return 'לא ידוע'
+        if any((w.distance < 0 for w in need)):
+            return 'יורד (מבחן רופף)'
+        return 'עולה'
+
+    @property
+    def lost(self) -> list[int]:
+        """Slow averages price is currently below — the cascade map (F-S08)."""
+        return [n for n in SLOW if (w := self.window(n)) is not None and w.distance < 0]
+
+    @property
+    def cascade_next(self) -> int | None:
+        """The next average DOWN the ladder after the ones already lost.
+
+        Furman's rule (F-S08) is that losing an average hands price to the NEXT
+        one, and the 800's reaction is the strong one. So the destination is
+        the first slow EMA below everything already lost -- not the lost one
+        itself, which is where a naive min() over `lost` lands and reads as
+        "you lost the 50, so the target is the 50".
+        """
+        if not self.lost:
+            return None
+        deepest = max(self.lost)
+        remaining = [n for n in SLOW if n > deepest]
+        return remaining[0] if remaining else None
+
+    @property
+    def next_magnet(self) -> Window | None:
+        """The nearest OPEN window — where the unfinished business sits."""
+        opens = [w for w in self.windows if w.is_open]
+        return min(opens, key=lambda w: abs(w.atr_distance)) if opens else None
+
+    @property
+    def slope_agreement(self) -> float | None:
+        """How much of the fan is sloping the SAME way, from -1 to +1.
+
+        Sagiv, 2026-08-31, reading BTC: *"הממוצעים עם שיפוע אגרסיבי למטה ויש
+        גם סדר של 4 ממוצעים לשורט."* Order and slope are two different facts —
+        a fan can be stacked for a short while every average is turning up
+        under it — and the desk only ever had the order. null when no average
+        could be measured, never 0.0, which would read as "perfectly split".
+
+        MAGNITUDE-WEIGHTED, on GPT's finding: counting signs let slopes of
+        [+10.0, -0.01, -0.01] report -0.33 while `slope_strength` reported
+        0.01, so between them neither output mentioned the +10 that was
+        actually driving the fan. Weighting by size makes one decisive average
+        outweigh two that have barely moved, and a genuinely flat average
+        contributes nothing instead of counting as a vote against.
+        """
+        vals = [w.slope_atr for w in self.windows if w.slope_atr is not None]
+        if not vals:
+            return None
+        total = sum((abs(v) for v in vals))
+        return sum(vals) / total if total else 0.0
+
+    @property
+    def slope_coverage(self) -> float:
+        """Share of the fan whose slope could actually be measured.
+
+        Without it an agreement of -1.0 read the same whether six averages
+        agreed or one was measured and five were unconverged -- and 4h/1h are
+        exactly where the 800 goes missing. The reading and its confidence
+        travel together.
+        """
+        return len([w for w in self.windows if w.slope_atr is not None]) / len(LENGTHS)
+
+    @property
+    def slope_strength(self) -> float | None:
+        """Median absolute slope across the fan, in ATRs.
+
+        The magnitude half of the same reading: `slope_agreement` says whether
+        the averages point one way, this says how hard. Kept continuous — ?4
+        forbids freezing a threshold for "aggressive" before it is calibrated
+        walk-forward, so nothing here labels the number.
+        """
+        vals = sorted((abs(w.slope_atr) for w in self.windows if w.slope_atr is not None))
+        if not vals:
+            return None
+        mid = len(vals) // 2
+        return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2
+
+    @property
+    def cascade_gap(self) -> tuple[int, float] | None:
+        """(length, ATRs) of the gap to the cascade's next average.
+
+        His thesis on BTC: four averages stacked for a short, only the 800
+        below, so price goes and closes the distance to it. `cascade_next`
+        already named that destination; nothing measured how far away it was,
+        which is the number that decides whether the move is worth a trade.
+        """
+        n = self.cascade_next
+        if n is None:
+            return None
+        w = self.window(n)
+        if w is None or not self.atr or self.atr <= 0:
+            return None
+        return (n, w.atr_distance)
+
+    def glued(self, fast_length: int=5) -> tuple[bool, float]:
+        """Are the fast EMAs stacked on top of each other? (F-S12)
+
+        `fast_length` is 5 for Tino's set, 7 for Furman's -- the answer can
+        legitimately differ between them, which is why the caller chooses.
+        """
+        a, b = (self.window(fast_length), self.window(13))
+        if a is None or b is None or (not self.atr):
+            return (False, 0.0)
+        gap = abs(a.value - b.value) / self.atr
+        return (gap <= GLUED_ATR, gap)
+
+    @property
+    def stack_order(self) -> str:
+        """Are the slow averages themselves in trend order?
+
+        This is YS2's state variable: 50 above 200 above 800 means every
+        horizon agrees, and the last crossing completing that order is the
+        regime flip itself.
+
+        The label names the EMAs that were ACTUALLY compared. Caught 2026-08-13
+        on gold 4h: EMA800 sat in `unconverged`, only 50 and 200 were compared,
+        and the string still read "(50>200>800)" -- a two-EMA fact printed as a
+        three-EMA claim. Any bias taken from that string rested on an average
+        that does not exist yet. `trend_strict` had the gap right all along;
+        only this label lied.
+        """
+        vals = [(n, w.value) for n in SLOW if (w := self.window(n)) is not None]
+        if len(vals) < 2:
+            return 'לא ידוע'
+        names = [n for n, _ in vals]
+        order = [v for _, v in vals]
+        partial = '' if len(vals) == len(SLOW) else ' — חלקית'
+        if all((order[i] > order[i + 1] for i in range(len(order) - 1))):
+            return f"מסודרת שורית ({'>'.join((str(n) for n in names))}){partial}"
+        if all((order[i] < order[i + 1] for i in range(len(order) - 1))):
+            return f"מסודרת דובית ({'<'.join((str(n) for n in names))}){partial}"
+        return 'לא מסודרת — הערימה מעורבבת'
+
+    def render(self) -> str:
+        lines = [f"◈ {self.symbol.split(':')[-1]} {self.timeframe} @ {self.close:,.1f}"]
+        lines.append(f'  מגמה (מבחן קפדני): {self.trend_strict} · ערימה: {self.stack_order}')
+        for w in self.windows:
+            lines.append('  ' + w.render())
+        if self.unconverged:
+            lines.append(f"  ⚠ לא התכנסו (אין מספיק היסטוריה): {', '.join((f'EMA{n}' for n in self.unconverged))}")
+        return '\n'.join(lines)
+
+def _atr(df: pd.DataFrame, n: int=14) -> float:
+    prev = df['close'].shift(1)
+    trng = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
+    return float(trng.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])
+
+def _read_with_deep(df, deep, symbol: str, timeframe: str, source: str='') -> EmaState:
+    """Build the state from bars already in hand — the testable half.
+
+    Split out of read() so the window and slope arithmetic can be driven with
+    constructed frames. Every other test injects a finished Window, so before
+    this existed the whole slope block could have been deleted and the suite
+    would still have reported OK (GPT, reviewing a1fa0c8).
+    """
+    close = float(df['close'].iloc[-1])
+    atr = _atr(df)
+    windows, unconverged = ([], [])
+    for n in LENGTHS:
+        src = df
+        if len(df) < 2 * n and deep is not None:
+            head = deep[deep.index < df.index[0]]
+            if len(head):
+                src = pd.concat([head, df])
+                src = src[~src.index.duplicated(keep='last')].sort_index()
+        if len(src) < 2 * n:
+            unconverged.append(n)
+            continue
+        series = I.ema(src['close'], n)
+        val = float(series.iloc[-1])
+        if val != val:
+            unconverged.append(n)
+            continue
+        slope = None
+        if len(series) > SLOPE_BARS:
+            prev = float(series.iloc[-1 - SLOPE_BARS])
+            span_atr = _atr(src.tail(2 * SLOPE_BARS + 14)) if len(src) > 20 else atr
+            if prev == prev and span_atr and (span_atr > 0):
+                slope = (val - prev) / span_atr
+        windows.append(Window(n, val, close - val, atr, slope_atr=slope))
+    return EmaState(symbol=symbol, timeframe=timeframe, close=close, atr=atr, windows=windows, unconverged=unconverged, source=source)
+
+class EmaReader:
+
+    def __init__(self, source):
+        self.source = source
+
+    def read(self, symbol: str, timeframe: str, lookback: int | None=None) -> EmaState:
+        """Mechanical EMA state for one symbol on one timeframe."""
+        lookback = lookback or {'1d': 2200, '4h': 2000, '1h': 2000, '15m': 2000, '5m': 2000}.get(timeframe, 2000)
+        df, corr = self.source.fetch_corrected(symbol, timeframe, lookback)
+        deep = None
+        try:
+            _dp = PurePosixPath('.') / 'deep' / f"{MT5_SYMBOL_MAP.get(symbol, '')}_{ {'4h': 'H4', '1h': 'H1', '15m': 'M15'}.get(timeframe, '')}.csv"
+            if _dp.name.startswith('_') is False and self.source.deep_exists(_dp.as_posix()):
+                _d = pd.read_csv(BytesIO(self.source.deep_bytes(_dp.as_posix())))
+                _d['time'] = pd.to_datetime(_d['time'], utc=True)
+                deep = _d.set_index('time').sort_index()
+        except Exception:
+            deep = None
+        return _read_with_deep(df, deep, symbol, timeframe, source=corr.source if corr else '')
+
+    def read_stack(self, symbol: str, timeframes=('4h', '1h', '15m', '5m')) -> dict[str, EmaState]:
+        out = {}
+        for tf in timeframes:
+            try:
+                out[tf] = self.read(symbol, tf)
+            except Exception:
+                continue
+        return out
```

## tests/tree_replay/test_ema_windows.py

```diff
diff --git a/tests/tree_replay/test_ema_windows.py b/tests/tree_replay/test_ema_windows.py
new file mode 100644
index 0000000..3c672ac
--- /dev/null
+++ b/tests/tree_replay/test_ema_windows.py
@@ -0,0 +1,305 @@
+"""Full source EMA reader: real CSV, prehistory splice, windows and slopes."""
+import importlib
+import importlib.util
+from types import SimpleNamespace
+
+import pandas as pd
+import pytest
+from pandas.testing import assert_frame_equal
+
+
+SYMBOL='OANDA:XAUUSD'
+END=pd.Timestamp('2026-09-09T16:00:00Z')
+
+
+def api():
+    name='trading_system.tree_replay._vendor.ema_windows'
+    assert importlib.util.find_spec(name) is not None, 'EMA reader missing'
+    return importlib.import_module(name)
+
+
+def frame(n=1600, *, start=100., step=1., end=END, width=1.):
+    c=[start+step*i for i in range(n)]
+    return pd.DataFrame({'open':c,'high':[x+width for x in c],
+        'low':[x-width for x in c],'close':c},
+        index=pd.date_range(end=end,periods=n,freq='1h',name='time'))
+
+
+class Ports:
+    def __init__(self, live=None, deep=None):
+        self.live=frame() if live is None else live
+        self.corr=SimpleNamespace(source='tv_daily',unverified=True)
+        self.deep=None if deep is None else deep.to_csv().encode('utf-8')
+        self.calls=[]
+        self.exists_error=None
+        self.bytes_error=None
+        self.fetch_errors=set()
+
+    def fetch_corrected(self,symbol,timeframe,lookback):
+        self.calls.append(('fetch',symbol,timeframe,lookback))
+        if timeframe in self.fetch_errors:
+            raise OSError('captured fetch failure')
+        return self.live,self.corr
+
+    def deep_exists(self,key):
+        self.calls.append(('exists',key))
+        if self.exists_error: raise self.exists_error
+        return self.deep is not None
+
+    def deep_bytes(self,key):
+        self.calls.append(('bytes',key))
+        if self.bytes_error: raise self.bytes_error
+        return self.deep
+
+
+def test_real_reader_converges_all_six_windows_with_continuous_three_bar_slope():
+    m=api()
+    p=Ports()
+    before=p.live.copy(deep=True)
+    s=m.EmaReader(p).read(SYMBOL,'1h')
+    assert (s.symbol,s.timeframe,s.source,s.close,s.atr)==(SYMBOL,'1h','tv_daily',1699.,2.)
+    assert s.unconverged==[] and [w.length for w in s.windows]==[5,7,13,50,200,800]
+    for n,value in [(5,1697.),(7,1696.),(13,1693.),(50,1674.5),(200,1599.5),(800,1299.5)]:
+        w=s.window(n)
+        assert w.value==pytest.approx(value,rel=0,abs=1e-9)
+        assert w.slope_atr==pytest.approx(1.5,rel=0,abs=1e-9)
+        assert w.rising is True and w.is_open
+    assert s.window(800).distance==pytest.approx(399.5,rel=0,abs=1e-9)
+    assert s.trend_strict=='עולה' and s.trend_loose=='עולה'
+    assert s.slope_agreement==1. and s.slope_coverage==1.
+    assert s.slope_strength==pytest.approx(1.5,rel=0,abs=1e-9)
+    assert s.lost==[] and s.cascade_next is None and s.cascade_gap is None
+    assert s.next_magnet.length==5
+    assert p.calls==[('fetch',SYMBOL,'1h',2000),('exists','deep/XAUUSD_H1.csv')]
+    assert_frame_equal(p.live,before)
+
+
+@pytest.mark.parametrize('n,want',[ (9,[]),(10,[5]),(14,[5,7]),(26,[5,7,13]),
+    (99,[5,7,13]),(100,[5,7,13,50]),(399,[5,7,13,50]),(400,[5,7,13,50,200]),
+    (1599,[5,7,13,50,200]),(1600,[5,7,13,50,200,800])])
+def test_each_window_enforces_its_own_twice_length_convergence(n,want):
+    m=api()
+    s=m.EmaReader(Ports(frame(n))).read(SYMBOL,'1h')
+    assert [w.length for w in s.windows]==want
+    assert s.unconverged==[x for x in (5,7,13,50,200,800) if x not in want]
+
+
+def test_actual_csv_deep_prefix_extends_only_unconverged_windows_and_live_endpoint_wins():
+    m=api()
+    live=frame(100)
+    head=frame(1500,step=0.,end=live.index[0]-pd.Timedelta(hours=1),width=20.)
+    # Poison overlaps and later deep rows: none are eligible prehistory.
+    overlaps=frame(110,start=100000.,end=END+pd.Timedelta(hours=10))
+    deep=pd.concat([head,overlaps]).iloc[::-1]
+    p=Ports(live,deep)
+    s=m.EmaReader(p).read(SYMBOL,'1h')
+    assert s.unconverged==[] and s.close==199. and s.atr==2.
+    assert s.window(50).value==pytest.approx(174.5,rel=0,abs=1e-10)
+    # Independent closed-form recursion for 99 rising updates after100.
+    assert s.window(800).value==pytest.approx(199.-399.5*(1.-(799/801)**99),rel=0,abs=1e-9)
+    assert s.window(800).atr==2.
+    assert p.calls[-2:]==[('exists','deep/XAUUSD_H1.csv'),('bytes','deep/XAUUSD_H1.csv')]
+    assert_frame_equal(live,p.live)
+
+
+def test_overlap_at_first_live_stamp_does_not_add_a_convergence_row():
+    m=api()
+    live=frame(99)
+    deep=live.iloc[:1].copy()
+    deep['close']=99999.
+    s=m.EmaReader(Ports(live,deep)).read(SYMBOL,'1h')
+    assert s.window(50) is None and 50 in s.unconverged
+
+
+@pytest.mark.parametrize('symbol,stem',[(SYMBOL,'XAUUSD'),('OANDA:NAS100USD','NAS100'),
+    ('BINANCE:BTCUSDT','BTCUSD'),('TVC:VIX','VIX'),('TVC:DXY','DXY')])
+def test_exact_original_filename_mapping_without_alias(symbol,stem):
+    m=api()
+    p=Ports(frame(100))
+    m.EmaReader(p).read(symbol,'15m')
+    assert p.calls==[('fetch',symbol,'15m',2000),('exists',f'deep/{stem}_M15.csv')]
+
+
+@pytest.mark.parametrize('tf,lookback,want,suffix',[
+    ('1d',None,2200,''),('5m',None,2000,''),('unknown',None,2000,''),
+    ('4h',0,2000,'H4'),('1h',23,23,'H1'),('1h',-1,-1,'H1')])
+def test_original_defaults_truthiness_and_unknown_timeframe_filename(tf,lookback,want,suffix):
+    m=api()
+    p=Ports(frame(100))
+    m.EmaReader(p).read(SYMBOL,tf,lookback)
+    assert p.calls==[('fetch',SYMBOL,tf,want),('exists',f'deep/XAUUSD_{suffix}.csv')]
+
+
+def test_unknown_or_bare_symbol_skips_deep_lookup_instead_of_normalizing():
+    m=api()
+    p=Ports(frame(100))
+    m.EmaReader(p).read('XAUUSD','1h')
+    assert p.calls==[('fetch','XAUUSD','1h',2000)]
+
+
+@pytest.mark.parametrize('fault',['exists','bytes','empty','bad_time','no_time'])
+def test_optional_deep_io_or_parse_failure_keeps_real_live_calculations(fault):
+    m=api()
+    p=Ports(frame(100),frame(100))
+    if fault=='exists': p.exists_error=OSError('captured')
+    elif fault=='bytes': p.bytes_error=OSError('captured')
+    elif fault=='empty': p.deep=b''
+    elif fault=='bad_time': p.deep=b'time,close\ninvalid,100\n'
+    elif fault=='no_time': p.deep=b'close\n100\n'
+    s=m.EmaReader(p).read(SYMBOL,'1h')
+    assert s.window(50).value==pytest.approx(174.5,rel=0,abs=1e-10)
+    assert s.unconverged==[200,800]
+
+
+def test_fetch_failure_propagates_but_stack_omits_only_failed_timeframe_and_repeats_reads():
+    m=api()
+    p=Ports(frame(100))
+    p.fetch_errors={'4h'}
+    reader=m.EmaReader(p)
+    with pytest.raises(OSError): reader.read(SYMBOL,'4h')
+    p.calls.clear()
+    out=reader.read_stack(SYMBOL,('1h','4h','15m','1h'))
+    assert list(out)==['1h','15m']
+    assert [c[2] for c in p.calls if c[0]=='fetch']==['1h','4h','15m','1h']
+
+
+def test_full_live_still_attempts_deep_bytes_but_does_not_need_deep_columns():
+    m=api()
+    p=Ports()
+    p.corr=None
+    p.deep=b'time,unrelated\n2020-01-01,100\n'
+    s=m.EmaReader(p).read(SYMBOL,'1h')
+    assert s.source=='' and s.window(800).value==pytest.approx(1299.5,rel=0,abs=1e-9)
+    assert p.calls[-1]==('bytes','deep/XAUUSD_H1.csv')
+
+
+def test_constant_prices_keep_flat_slope_distinct_from_unknown_and_zero_atr():
+    m=api()
+    # Power-of-two constant gives exact equality through the source recursion;
+    # a constant100 may retain tiny EMA200 seed rounding with strict comparisons.
+    s=m.EmaReader(Ports(frame(1600,start=128.,step=0.))).read(SYMBOL,'1h')
+    assert all(w.slope_atr==0. and w.rising is False for w in s.windows)
+    assert s.slope_agreement==0. and s.slope_strength==0. and s.slope_coverage==1.
+    assert s.trend_strict=='מעורב' and s.trend_loose=='עולה'
+    assert s.next_magnet is None and s.glued()==(True,0.)
+    z=m.EmaReader(Ports(frame(1600,start=128.,step=0.,width=0.))).read(SYMBOL,'1h')
+    assert z.atr==0. and all(w.slope_atr is None for w in z.windows)
+    assert z.slope_agreement is None and z.slope_strength is None and z.slope_coverage==0.
+
+
+def test_source_weighted_slope_cascade_signed_gap_and_partial_stack_are_not_simplified():
+    m=api()
+    s=m.EmaState(SYMBOL,'1h',100.,2.,[
+        m.Window(50,110.,-10.,2.,10.),m.Window(200,120.,-20.,2.,-.01),
+        m.Window(800,80.,20.,2.,-.01)])
+    assert s.slope_agreement==pytest.approx(499/501)
+    assert s.slope_strength==.01 and s.slope_coverage==.5
+    assert s.trend_strict=='מעורב' and s.trend_loose=='יורד (מבחן רופף)'
+    assert s.lost==[50,200] and s.cascade_next==800 and s.cascade_gap==(800,10.)
+    assert s.next_magnet.length==50
+    s.windows.pop()
+    assert s.trend_strict=='לא ידוע' and s.trend_loose=='לא ידוע'
+    assert s.cascade_gap is None and s.stack_order=='מסודרת דובית (50<200) — חלקית'
+    s.atr=0.
+    assert s.cascade_gap is None
+
+
+def test_five_and_seven_glued_readings_and_window_boundary_rendering():
+    m=api()
+    s=m.EmaState(SYMBOL,'1h',101.,1.,[
+        m.Window(5,100.,1.,1.),m.Window(7,100.5,.5,1.),m.Window(13,100.125,.875,1.)])
+    assert s.glued(5)==(True,.125) and s.glued(7)==(False,.375)
+    w=m.Window(50,100.,1.5,2.)
+    assert w.is_open and w.rising is None
+    assert w.render()=='EMA50: 100.0 · 1.5 מעל (0.8 ATR) — חלון פתוח'
+    w.distance=1.4999
+    assert not w.is_open
+    partial=m.EmaReader(Ports(frame(100))).read(SYMBOL,'1h')
+    assert 'EMA200, EMA800' in partial.render()
+    assert 'לא התכנסו' in partial.render()
+
+
+def test_independent_unseeded_atr_uses_original_formula():
+    m=api()
+    f=pd.DataFrame({'high':[101.,120.],'low':[99.,100.],'close':[100.,110.]})
+    assert m._atr(f)==pytest.approx(23/7)
+
+
+def test_slope_divisor_uses_twenty_row_span_not_full_live_atr():
+    m=api()
+    live=frame(30)
+    live.loc[live.index[:10],'high']=live['close'].iloc[:10]+10.
+    live.loc[live.index[:10],'low']=live['close'].iloc[:10]-10.
+    s=m.EmaReader(Ports(live)).read(SYMBOL,'1h')
+    assert s.atr==pytest.approx(2.+18.*(13/14)**20)
+    assert s.atr>2.
+    assert s.window(5).slope_atr==pytest.approx(1.5,rel=0,abs=1e-10)
+
+
+def test_short_live_keeps_window_atr_live_but_slope_atr_includes_deep_span():
+    m=api()
+    live=frame(6,start=128.)
+    head=frame(1594,start=128.,step=0.,width=10.,end=live.index[0]-pd.Timedelta(hours=1))
+    s=m.EmaReader(Ports(live,head)).read(SYMBOL,'1h')
+    assert s.unconverged==[] and s.atr==2. and s.window(5).atr==2.
+    assert s.window(5).value==pytest.approx(131.+64/243,rel=0,abs=1e-10)
+    span_atr=2.+18.*(13/14)**6
+    assert s.window(5).slope_atr==pytest.approx((577/243)/span_atr,rel=0,abs=1e-10)
+
+
+def test_splice_deduplicates_before_convergence_but_live_only_is_not_normalized():
+    # Removing splice dedup would manufacture the 100th row for EMA50.
+    m=api()
+    live=frame(99)
+    stamps=list(live.index)
+    stamps[1]=stamps[0]
+    live.index=pd.DatetimeIndex(stamps,name='time')
+    head=frame(1,end=live.index[0]-pd.Timedelta(hours=1))
+    s=m.EmaReader(Ports(live,head)).read(SYMBOL,'1h')
+    assert s.window(50) is None and 50 in s.unconverged
+    # Without a splice the source deliberately counts delivered rows as-is.
+    live=frame(100,start=128.,step=0.)
+    stamps=list(live.index)
+    stamps[1]=stamps[0]
+    live.index=pd.DatetimeIndex(stamps,name='time')
+    s=m.EmaReader(Ports(live)).read(SYMBOL,'1h')
+    assert s.window(50).value==128.
+
+
+def test_splice_keeps_last_duplicate_live_close_for_long_window():
+    # keep='first' must not discard the latest value for the repeated timestamp.
+    m=api()
+    live=frame(2,start=128.,step=2.)
+    live.index=pd.DatetimeIndex([END,END],name='time')
+    head=frame(1599,start=128.,step=0.,end=END-pd.Timedelta(hours=1))
+    s=m.EmaReader(Ports(live,head)).read(SYMBOL,'1h')
+    assert s.close==130. and s.unconverged==[]
+    assert s.window(800).value==pytest.approx(128.+4/801,rel=0,abs=1e-10)
+
+
+def test_parsed_but_nonnumeric_deep_raises_outside_optional_io_catch():
+    # Widening read's catch would silently turn calculation failure into live fallback.
+    m=api()
+    live=frame(99)
+    head=frame(301,end=live.index[0]-pd.Timedelta(hours=1))
+    head['close']='not-a-price'
+    reader=m.EmaReader(Ports(live,head))
+    with pytest.raises(ValueError):
+        reader.read(SYMBOL,'1h')
+    assert reader.read_stack(SYMBOL,('1h',))=={}
+
+
+def test_nearzero_source_rounding_is_not_reclassified_using_epsilon():
+    # Introducing an epsilon would change the source's loose trend/cascade.
+    m=api()
+    s=m.EmaReader(Ports(frame(1600,start=100.,step=0.))).read(SYMBOL,'1h')
+    assert -1e-10<s.window(200).distance<0.
+    assert 200 in s.lost and s.trend_loose=='יורד (מבחן רופף)'
+
+
+def test_nearest_open_tie_retains_supplied_window_order():
+    # Sorting tied windows by EMA length would choose the wrong first magnet.
+    m=api()
+    first=m.Window(200,102.,-2.,2.)
+    s=m.EmaState(SYMBOL,'1h',100.,2.,[first,m.Window(50,98.,2.,2.)])
+    assert s.next_magnet is first
```

## docs/architecture/EMA-DEEP-READER-USAGE.md

```diff
diff --git a/docs/architecture/EMA-DEEP-READER-USAGE.md b/docs/architecture/EMA-DEEP-READER-USAGE.md
new file mode 100644
index 0000000..64f1e5b
--- /dev/null
+++ b/docs/architecture/EMA-DEEP-READER-USAGE.md
@@ -0,0 +1,71 @@
+# Original EMA windows and optional deep prehistory
+
+Private module: trading_system.tree_replay._vendor.ema_windows.
+Source authority and exact adaptations: EMA-DEEP-READER-CONTRACT.md.
+Runtime, tests and source auditor exist; independent review is still required.
+This is not the existing public ema_snapshot and does not change that adapter.
+
+EmaReader(source).read(symbol,timeframe,lookback=None) runs real original EMA
+state calculation. read_stack(symbol,timeframes=('4h','1h','15m','5m')) reads
+each in order and omits only reads that raise, preserving repeated requests.
+
+The supplied local source has exactly these methods:
+
+```python
+fetch_corrected(symbol, timeframe, lookback)  # -> (DataFrame, correction or None)
+deep_exists(logical_path)                    # -> bool
+deep_bytes(logical_path)                     # -> bytes
+```
+
+No default source is supplied. These must be offline evidence readers, not live
+API or file fetches. Logical paths identify captured inputs, not paths this
+runtime opens. Original symbol mapping and timeframe suffix yield names such
+as deep/XAUUSD_H1.csv. A bare XAUUSD is not normalized for this lookup and skips
+the leading-underscore filename. A known symbol with5m/unknown timeframe still
+probes deep/XAUUSD_.csv, matching source. Do not infer a valid feed from a name.
+
+Default request lookback is2200 for daily,2000 otherwise; source truthiness
+means0 uses the default. Delivered history is not trimmed. Correction flags do
+not veto this reader; corr.source is an annotation only. Frame fetch failures
+propagate from read. Optional deep exists/bytes/CSV/time parsing failures are
+caught and leave deepNone. DataFrame calculations after that try may still raise.
+
+Deep CSV is parsed by pandas from supplied bytes, time converted to UTC and
+rows sorted. For each of5/7/13/50/200/800, only insufficient live history (<2*n)
+allows strict pre-live deep rows to seed the EMA. Overlap/newer deep rows cannot
+replace the live endpoint. Duplicate removal and sorting of the combined frame
+occur only on that splice branch, not as global normalization of all live data.
+
+EmaState exposes actual windows, unconverged lengths, source, trends, stack,
+glued5vs7, cascade, open-window magnet and weighted continuous slope summaries.
+Window ATR and current close come from the supplied live frame. Slope spans3
+EMA bars and uses ATR of the final20 source rows for histories longer than20;
+that span can include deep rows if the live segment is short. It is not the
+old adapter's5bar delta or a necessarily live-only slope denominator.
+
+Source numerical behavior is retained. No floating epsilon is inserted into
+trend comparisons: even constant100 can give EMA200100.0000000000001 and a
+negative tiny distance. Exact-flat tests use128 to isolate true zero/None
+semantics from rounding. Zero ATR can leave slope unknown; neither NaN nor
+unconverged windows are certified numerical model features by this raw reader.
+
+All history availability, current-bar policy, period calendars, ordering,
+warmup, price basis, deep splice identity and observed/available times are
+caller obligations until real causal binding is implemented. GC prehistory is
+not automatically approved as spot history, and deep bars must not feed ADR or
+range calculations. Rendering returns text only; there are no sends or trades.
+
+Run tests/tree_replay/test_ema_windows.py for current synthetic behavior and
+tests/tree_spec/test_ema_windows_source.py for inert source/dependency drift checks.
+The explicit source audit is:
+
+```text
+python -B tools/check_ema_windows_source_parity.py --source-root <retained-parent>
+```
+
+It requires the pinned chart-desk checkout under that parent and returns JSON,
+exit0 for VERIFIED or exit2 for BLOCKED, never replay/training readiness. It
+parses the entire projected module and the real ordered seeded-EMA dependency;
+it does not import the reader or execute retained source. Independent acceptance
+is still pending; see2026-09-09-ema-deep-reader.md and latest exchange status. Full
+revalidation/caller/lifecycle/economic dataset/model work remains beyond it.
```
