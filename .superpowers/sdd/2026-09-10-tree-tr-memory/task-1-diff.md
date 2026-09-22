# Task1 untracked additions against HEAD c1b6071

diff --git a/trading_system/tree_replay/_vendor/tree_tr.py b/trading_system/tree_replay/_vendor/tree_tr.py
new file mode 100644
index 0000000..9bbda99
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/tree_tr.py
@@ -0,0 +1,73 @@
+"""Original TR vector zones (default non-auction) and daily pivots."""
+import pandas as pd
+from .pvsra import pvsra
+
+def vector_zones(df: pd.DataFrame, pv: pd.DataFrame | None=None, *, zone_from: str='body', cleared_by: str='wick', max_zones: int=500) -> pd.DataFrame:
+    """Zones left behind by vector (climax) candles, and whether price cleared them.
+
+    **reconstructed** -- TR draws these from the vector candles; the clearing
+    rule is a user setting there ("Body only" / "Body with wicks"), mirrored
+    here by `zone_from` and `cleared_by`.
+
+    A zone is the body (or full range) of a climax candle. It stays "open" until
+    a later bar trades back through it. Open zones below price are demand,
+    open zones above are supply -- and an untested one matters more than a
+    retested one, so `touches` is counted.
+    """
+    pv = pvsra(df) if pv is None else pv
+    if not bool(pv.get('available', pd.Series([False])).iloc[0]):
+        return pd.DataFrame(columns=['top', 'bottom', 'kind', 'open', 'touches', 'time'])
+    vec = pv.index[pv['climax'].to_numpy()]
+    vec = vec[-max_zones:]
+    if len(vec) == 0:
+        return pd.DataFrame(columns=['top', 'bottom', 'kind', 'open', 'touches', 'time'])
+    o, c = (df['open'], df['close'])
+    top = (o.combine(c, max) if zone_from == 'body' else df['high']).loc[vec]
+    bottom = (o.combine(c, min) if zone_from == 'body' else df['low']).loc[vec]
+    hi = df['high'] if cleared_by == 'wick' else o.combine(c, max)
+    lo = df['low'] if cleared_by == 'wick' else o.combine(c, min)
+    rows = []
+    for t, tp, bt in zip(vec, top.to_numpy(), bottom.to_numpy()):
+        after = df.index > t
+        if not after.any():
+            rows.append((t, tp, bt, pv.loc[t, 'kind'], True, 0))
+            continue
+        overlaps = ((hi[after] >= bt) & (lo[after] <= tp)).to_numpy()
+        departed = ~overlaps
+        if departed.any():
+            first_out = int(departed.argmax())
+            returns = overlaps[first_out:]
+            n_touch = int(returns.sum())
+        else:
+            n_touch = 0
+        rows.append((t, float(tp), float(bt), pv.loc[t, 'kind'], n_touch == 0, n_touch))
+    out = pd.DataFrame(rows, columns=['time', 'top', 'bottom', 'kind', 'open', 'touches'])
+    return out.set_index('time')
+
+def daily_pivots(daily: pd.DataFrame, include_m: bool=True) -> dict[str, float]:
+    """Classic floor pivots off the previous daily bar. **transcribed**::
+
+        pivotPoint = (dayHigh + dayLow + dayClose) / 3
+        pivR1 = 2 * PP - dayLow          pivS1 = 2 * PP - dayHigh
+        pivR2 = PP - pivS1 + pivR1       pivS2 = PP - pivR1 + pivS1
+        pivR3 = 2 * PP + dayHigh - 2 * dayLow
+        pivS3 = 2 * PP - (2 * dayHigh - dayLow)
+
+    M levels are the midpoints between adjacent levels -- M0 between S3 and S2
+    up to M5 between R2 and R3. **reconstructed** (drawn by TR_MAIN, computed in
+    the library).
+    """
+    if len(daily) < 2:
+        return {}
+    prev = daily.iloc[-2]
+    h, l, c = (float(prev['high']), float(prev['low']), float(prev['close']))
+    pp = (h + l + c) / 3.0
+    r1, s1 = (2 * pp - l, 2 * pp - h)
+    r2, s2 = (pp - s1 + r1, pp - r1 + s1)
+    r3 = 2 * pp + h - 2 * l
+    s3 = 2 * pp - (2 * h - l)
+    out = {'PP': pp, 'R1': r1, 'R2': r2, 'R3': r3, 'S1': s1, 'S2': s2, 'S3': s3}
+    if include_m:
+        ladder = [s3, s2, s1, pp, r1, r2, r3]
+        out |= {f'M{i}': (ladder[i] + ladder[i + 1]) / 2.0 for i in range(6)}
+    return out

diff --git a/tests/tree_replay/test_tree_tr.py b/tests/tree_replay/test_tree_tr.py
new file mode 100644
index 0000000..312e13e
--- /dev/null
+++ b/tests/tree_replay/test_tree_tr.py
@@ -0,0 +1,108 @@
+"""Behavioral oracles for original TR vector-zone memory and daily pivots."""
+import importlib
+import importlib.util
+
+import pandas as pd
+import pytest
+
+
+def api():
+    name = 'trading_system.tree_replay._vendor.tree_tr'
+    assert importlib.util.find_spec(name) is not None, 'tree TR memory missing'
+    return importlib.import_module(name)
+
+
+def tape(rows):
+    return pd.DataFrame(rows, columns=['open', 'high', 'low', 'close'],
+        index=pd.date_range('2026-09-01', periods=len(rows), freq='5min', tz='UTC'))
+
+
+def evidence(df, *, climax=(0,)):
+    return pd.DataFrame({'available': True, 'kind': 'green',
+        'climax': [i in climax for i in range(len(df))]}, index=df.index)
+
+
+@pytest.mark.parametrize('tail,opened,touches', [
+    ([], True, 0), ([(12,13,11,12)], True, 0),
+    ([(12,13,11,12),(14,15,13,14)], True, 0),
+    ([(14,15,13,14),(12,13,12,12)], False, 1),
+    ([(14,15,13,14),(12,13,12,12),(11,12,10,11)], False, 2),
+    ([(12,13,11,12),(11,12,10,11)], True, 0),
+])
+def test_departure_must_precede_returns_and_each_overlap_counts(tail,opened,touches):
+    df = tape([(10,13,9,12)]+tail)
+    zones = api().vector_zones(df, evidence(df))
+    assert list(zones.index) == [df.index[0]] and zones.index.name == 'time'
+    row = zones.iloc[0]
+    assert (row['top'],row['bottom'],bool(row['open']),row['touches'],row['kind']) == (
+        12.,10.,opened,touches,'green')
+
+
+@pytest.mark.parametrize('zone_from,cleared_by,top,bottom,opened', [
+    ('body','wick',12.,10.,False), ('body','body',12.,10.,True),
+    ('wick','wick',13.,9.,False), ('wick','body',13.,9.,True),
+])
+def test_zone_and_return_geometry_are_independent(zone_from,cleared_by,top,bottom,opened):
+    df=tape([(10,13,9,12),(15,16,14,15),(15,16,11,15)])
+    z=api().vector_zones(df,evidence(df),zone_from=zone_from,cleared_by=cleared_by).iloc[0]
+    assert (z['top'],z['bottom'],bool(z['open'])) == (top,bottom,opened)
+
+
+@pytest.mark.parametrize('limit,want', [(1,[2]),(2,[1,2]),(0,[0,1,2]),(-1,[1,2])])
+def test_zone_cap_retains_raw_source_slice_semantics(limit,want):
+    df=tape([(10,13,9,12),(14,17,13,16),(18,21,17,20)])
+    zones=api().vector_zones(df,evidence(df,climax=(0,1,2)),max_zones=limit)
+    assert list(zones.index)==[df.index[i] for i in want]
+
+
+@pytest.mark.parametrize('fault', ['first_unavailable','missing_available','no_climax'])
+def test_unavailable_or_nonclimax_evidence_has_original_empty_schema(fault):
+    df=tape([(10,13,9,12),(14,17,13,16)])
+    pv=evidence(df)
+    if fault=='first_unavailable': pv.iloc[0,pv.columns.get_loc('available')]=False
+    elif fault=='missing_available': pv=pv.drop(columns='available')
+    else: pv['climax']=False; pv['kind']='blue'
+    z=api().vector_zones(df,pv)
+    assert z.empty and list(z.columns)==['top','bottom','kind','open','touches','time']
+
+
+def test_raw_empty_available_series_is_not_fabricated_as_absence():
+    df=tape([])
+    with pytest.raises(IndexError): api().vector_zones(df,evidence(df))
+
+
+def test_returns_are_selected_by_timestamp_not_position():
+    df=tape([(10,13,9,12),(14,15,13,14),(11,12,10,11)])
+    df.index=[df.index[1],df.index[0],df.index[2]]
+    z=api().vector_zones(df,evidence(df)).iloc[0]
+    # Positional row1 is a departure, but occurred BEFORE the zone's timestamp.
+    assert bool(z['open']) and z['touches']==0
+
+
+def test_actual_pvsra_composition_generates_the_climax_zone_and_return():
+    df=tape([(10,11,9,10)]*10+[(10,13,9,12),(14,15,13,14),(11,12,10,11)])
+    df['volume']=[1.]*10+[3.,1.,1.]
+    z=api().vector_zones(df)
+    assert list(z.index)==[df.index[10]]
+    assert z.iloc[0]['kind']=='green' and z.iloc[0]['top']==12.
+    assert z.iloc[0]['bottom']==10. and not bool(z.iloc[0]['open'])
+    assert z.iloc[0]['touches']==1
+
+
+@pytest.mark.parametrize('volume', [None,0.])
+def test_actual_pvsra_missing_or_zero_volume_yields_no_zones(volume):
+    df=tape([(10,13,9,12)]*15)
+    if volume is not None: df['volume']=volume
+    assert api().vector_zones(df).empty
+
+
+def test_daily_pivots_use_previous_bar_and_exact_named_ladder():
+    df=tape([(10,12,8,10),(999,1000,998,999)])
+    assert api().daily_pivots(df)=={'PP':10.,'R1':12.,'R2':14.,'R3':16.,
+        'S1':8.,'S2':6.,'S3':4.,'M0':5.,'M1':7.,'M2':9.,'M3':11.,'M4':13.,'M5':15.}
+    assert list(api().daily_pivots(df,include_m=False))==['PP','R1','R2','R3','S1','S2','S3']
+
+
+@pytest.mark.parametrize('rows',[[],[(10,12,8,10)]])
+def test_daily_pivots_need_a_previous_row(rows):
+    assert api().daily_pivots(tape(rows))=={}

diff --git a/docs/architecture/TREE-TR-MEMORY-USAGE.md b/docs/architecture/TREE-TR-MEMORY-USAGE.md
new file mode 100644
index 0000000..29cd7bc
--- /dev/null
+++ b/docs/architecture/TREE-TR-MEMORY-USAGE.md
@@ -0,0 +1,35 @@
+# Original TR vector memory and daily pivot helpers
+
+Private functions in trading_system.tree_replay._vendor.tree_tr:
+
+```python
+zones = vector_zones(frame)
+zones = vector_zones(frame, supplied_pvsra, zone_from='body',
+                     cleared_by='wick', max_zones=500)
+pivots = daily_pivots(daily, include_m=True)
+```
+
+Runtime and tests exist; source audit and independent reviews remain required
+before component acceptance. See TREE-TR-MEMORY-SOURCE-CONTRACT.md and plan
+2026-09-10-tree-tr-memory.md. No IO, clocks or external data loading here.
+
+vector_zones uses actual accepted default non-auction PVSRA when none supplied.
+Only climax candles create zones. Source first-row availability is retained.
+Initial overlap does not clear a zone: price must first leave entirely, then
+return. Each later overlapping bar after departure counts as a touch. Wick or
+body geometry is selected independently for zone and clearing. Nonempty result
+has time index and top,bottom,kind,open,touches; source empty result includes an
+empty time column instead. Arbitrary supplied frames are not validated or sorted.
+
+The private API omits auction/session_tz parameters; customauction/seasonality
+is not supported or certified. Source max_zones slicing remains literal,
+including zero/negative semantics. Raw pandas/input errors are not swallowed.
+
+daily_pivots reads the penultimate delivered row; last row is not used. This
+does not infer completed daily candles or reconstruct session boundaries.
+It returns seven standard pivots and optionally six M midpoints, in source order.
+
+These numerical outputs do not certify causal availability, historical source
+coverage, trades or outcomes. Full tree must still assemble the actual readers
+and preserve its forming/closed-row conventions and state. No GC/XAU alias,
+marketdata acquisition, model fitting or live behavior is enabled.

