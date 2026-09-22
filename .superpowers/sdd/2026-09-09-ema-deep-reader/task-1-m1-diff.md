# Task1 M1 supplement: full current runtime test file

Supersedes only the runtime-test section of task-1-diff.md. Two tests added, runtime unchanged.

```diff
diff --git a/tests/tree_replay/test_ema_windows.py b/tests/tree_replay/test_ema_windows.py
new file mode 100644
index 0000000..67dc545
--- /dev/null
+++ b/tests/tree_replay/test_ema_windows.py
@@ -0,0 +1,327 @@
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
+
+
+def test_even_slope_strength_averages_two_unequal_middle_magnitudes():
+    # Choosing either central value or signed median would misstate strength.
+    m=api()
+    s=m.EmaState(SYMBOL,'1h',100.,2.,[
+        m.Window(5,100.,0.,2.,1.),m.Window(7,100.,0.,2.,-9.),
+        m.Window(13,100.,0.,2.,3.),m.Window(50,100.,0.,2.,-7.)])
+    assert s.slope_strength==5.
+
+
+def test_generated_descending_tape_has_strict_downtrend_and_negative_slope():
+    # A copied uptrend test alone cannot expose a broken all-negative branch.
+    m=api()
+    s=m.EmaReader(Ports(frame(1600,start=2000.,step=-1.))).read(SYMBOL,'1h')
+    assert s.close==401. and s.unconverged==[]
+    assert s.trend_strict=='יורד' and s.trend_loose=='יורד (מבחן רופף)'
+    assert s.lost==[50,200,800] and s.cascade_next is None
+    assert s.window(800).value==pytest.approx(800.5,rel=0,abs=1e-9)
+    assert all(w.distance<0. and w.rising is False for w in s.windows)
+    assert s.slope_agreement==-1. and s.slope_coverage==1.
+    assert s.slope_strength==pytest.approx(1.5,rel=0,abs=1e-9)
```
