# Whole memory component review

Base/HEAD c1b6071633c55376c64f0a98ece843706f420f49; six untracked additions, no commits.

warning: in the working copy of 'trading_system/tree_replay/_vendor/tree_tr.py', LF will be replaced by CRLF the next time Git touches it
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

warning: in the working copy of 'tests/tree_replay/test_tree_tr.py', LF will be replaced by CRLF the next time Git touches it
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

warning: in the working copy of 'docs/architecture/TREE-TR-MEMORY-USAGE.md', LF will be replaced by CRLF the next time Git touches it
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

warning: in the working copy of 'trading_system/tree_spec/tree_tr_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_spec/tree_tr_source.py b/trading_system/tree_spec/tree_tr_source.py
new file mode 100644
index 0000000..93b85c6
--- /dev/null
+++ b/trading_system/tree_spec/tree_tr_source.py
@@ -0,0 +1,81 @@
+"""Inert whole-module audit of TR vector memory and daily pivots."""
+import ast
+import hashlib
+from pathlib import Path
+
+from tools.check_reversal_source_parity import check_source_parity as audit_pvsra
+from .tracker_admission_source import (
+    INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _selected, _without_doc,
+)
+
+ROOT=Path(__file__).resolve().parents[2]
+RUNTIME=ROOT/'trading_system/tree_replay/_vendor/tree_tr.py'
+COMMIT='68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
+BLOB='8297c712d20404880d4d8949e96efbf48613909c'
+SIGNATURE="""def vector_zones(df: pd.DataFrame, pv: pd.DataFrame | None = None, *,
+    zone_from: str = 'body', cleared_by: str = 'wick', max_zones: int = 500,
+    auction: bool | pd.Series = False, session_tz: str = A.DEFAULT_TZ) -> pd.DataFrame: pass"""
+
+
+def _projection(text):
+    nodes=_selected(text,['vector_zones','daily_pivots'])
+    node=nodes[0]
+    signature=ast.parse(SIGNATURE).body[0]
+    if not isinstance(node,ast.FunctionDef) or node.decorator_list or (
+        _dump(node.args)!=_dump(signature.args) or _dump(node.returns)!=_dump(signature.returns)):
+        raise ValueError('SOURCE_VECTOR_SIGNATURE_MISMATCH')
+    node.args.kwonlyargs=node.args.kwonlyargs[:-2]
+    node.args.kw_defaults=node.args.kw_defaults[:-2]
+    _replace_exact(node,'pvsra(df, auction=auction, session_tz=session_tz)','pvsra(df)')
+    return ast.parse('import pandas as pd\nfrom .pvsra import pvsra').body+nodes
+
+
+def audit_tree_tr_source(source_root):
+    """Verify pinned source and actual PVSRA closure; do not execute either."""
+    blockers,checked,dependencies=[],[],{}
+    report=dict(status='BLOCKED',source_subset_verified=False,blockers=blockers,
+        checked_projections=checked,dependencies=dependencies,
+        source_commits={'chart-desk':COMMIT},ready_for_replay=False,ready_for_training=False)
+    try:
+        root=Path(source_root)/'chart-desk'
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_ROOT_INVALID:'+type(exc).__name__)
+        return report
+    try:
+        if Path(_git(root,'--show-toplevel')).resolve()!=root.resolve():
+            blockers.append('NOT_REPOSITORY_ROOT')
+        if _git(root,'HEAD')!=COMMIT:
+            blockers.append('SOURCE_COMMIT_MISMATCH')
+        baseline=_read_json(ROOT/'configs/trees/existing-alerts-baseline.json')
+        if [r.get('commit') for r in baseline['repositories'] if r.get('name')=='chart-desk']!=[COMMIT]:
+            blockers.append('BASELINE_COMMIT_MISMATCH')
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_IDENTITY_UNREADABLE:'+type(exc).__name__)
+    try:
+        text=(root/'chartdesk/tr.py').read_text(encoding='utf-8')
+        raw=text.encode('utf-8')
+        if hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()!=BLOB:
+            blockers.append('SOURCE_BLOB_MISMATCH:tr.py')
+        expected=_projection(text)
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_PROJECTION_UNREADABLE:'+type(exc).__name__)
+    else:
+        try:
+            actual=_without_doc(ast.parse(RUNTIME.read_text(encoding='utf-8')))
+            if [_dump(n) for n in actual]!=[_dump(n) for n in expected]:
+                blockers.append('VENDOR_AST_MISMATCH')
+            else:
+                checked.append('tree_tr')
+        except INPUT_ERRORS as exc:
+            blockers.append('VENDOR_UNREADABLE:'+type(exc).__name__)
+    try:
+        result=audit_pvsra(root)
+        dependencies['pvsra']=result
+        blockers.extend('DEPENDENCY:pvsra:'+b for b in result['blockers'])
+        if not result['source_subset_verified'] and not result['blockers']:
+            blockers.append('DEPENDENCY:pvsra:NOT_VERIFIED')
+    except INPUT_ERRORS as exc:
+        blockers.append('DEPENDENCY:pvsra:UNREADABLE:'+type(exc).__name__)
+    if not blockers:
+        report.update(status='VERIFIED',source_subset_verified=True)
+    return report

warning: in the working copy of 'tools/check_tree_tr_source_parity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tools/check_tree_tr_source_parity.py b/tools/check_tree_tr_source_parity.py
new file mode 100644
index 0000000..10eba77
--- /dev/null
+++ b/tools/check_tree_tr_source_parity.py
@@ -0,0 +1,23 @@
+"""Audit original TR vector memory and daily pivots without execution."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None,''):
+    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.tree_tr_source import audit_tree_tr_source
+
+
+def main():
+    parser=argparse.ArgumentParser(description=__doc__)
+    parser.add_argument('--source-root',type=Path,required=True,
+                        help='Explicit parent of retained source checkouts')
+    report=audit_tree_tr_source(parser.parse_args().source_root)
+    print(json.dumps(report,sort_keys=True,indent=2))
+    return 0 if report['source_subset_verified'] else 2
+
+
+if __name__=='__main__':
+    raise SystemExit(main())

warning: in the working copy of 'tests/tree_spec/test_tree_tr_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_spec/test_tree_tr_source.py b/tests/tree_spec/test_tree_tr_source.py
new file mode 100644
index 0000000..9d17c24
--- /dev/null
+++ b/tests/tree_spec/test_tree_tr_source.py
@@ -0,0 +1,167 @@
+"""Whole source/dependency audit must reject changed vector memory and pivots."""
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
+ROOT=Path(__file__).resolve().parents[2]
+SOURCE=Path(os.environ.get('TR_TREE_SOURCE_ROOT',
+    'C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'))
+RUNTIME=ROOT/'trading_system/tree_replay/_vendor/tree_tr.py'
+
+
+def api():
+    name='trading_system.tree_spec.tree_tr_source'
+    assert importlib.util.find_spec(name) is not None, 'tree TR auditor missing'
+    return importlib.import_module(name)
+
+
+def intercept(monkeypatch,path,transform):
+    original=Path.read_text
+    def read(p,*args,**kwargs):
+        text=original(p,*args,**kwargs)
+        return transform(text) if p.resolve()==path.resolve() else text
+    monkeypatch.setattr(Path,'read_text',read)
+
+
+def test_real_source_and_pvsra_verify_without_readiness():
+    r=api().audit_tree_tr_source(SOURCE)
+    assert r['source_subset_verified'] and r['status']=='VERIFIED' and not r['blockers']
+    assert r['checked_projections']==['tree_tr']
+    assert r['dependencies']['pvsra']['source_subset_verified']
+    assert not r['ready_for_replay'] and not r['ready_for_training']
+
+
+@pytest.mark.parametrize('old,new',[
+    ('from .pvsra import pvsra','from .pvsra import pvsra\nimport urllib.request'),
+    ('pvsra(df) if pv is None else pv','pvsra(df)'),
+    ("pd.Series([False])).iloc[0]", "pd.Series([False])).iloc[-1]"),
+    ("pv['climax'].to_numpy()", "pv['rising'].to_numpy()"),
+    ('vec[-max_zones:]', 'vec[:max_zones]'),
+    ("zone_from == 'body'", "zone_from == 'wick'"),
+    ("cleared_by == 'wick'", "cleared_by == 'body'"),
+    ('after = df.index > t','after = df.index >= t'),
+    ('hi[after] >= bt','hi[after] > bt'),
+    ('lo[after] <= tp','lo[after] < tp'),
+    ('departed = ~overlaps','departed = overlaps'),
+    ('if departed.any():','if True:'),
+    ('returns = overlaps[first_out:]','returns = overlaps'),
+    ('int(returns.sum())','int(returns.any())'),
+    ('n_touch == 0','n_touch > 0'),
+    ("out.set_index('time')",'out'),
+    ('max_zones: int=500','max_zones: int=50'),
+    ('daily.iloc[-2]','daily.iloc[-1]'),
+    ('len(daily) < 2','len(daily) < 3'),
+    ('(h + l + c) / 3.0','(h + l) / 2.0'),
+    ('2 * pp - l','2 * pp - h'),
+    ('pp - s1 + r1','pp - r1 + s1'),
+    ('2 * pp + h - 2 * l','2 * pp + h - l'),
+    ('2 * pp - (2 * h - l)','2 * pp - (h - l)'),
+    ('if include_m:','if True:'),
+    ('range(6)','range(5)'),
+])
+def test_candidate_numerical_or_structure_drift_blocks(monkeypatch,old,new):
+    m=api()
+    assert old in RUNTIME.read_text(encoding='utf-8'),old
+    intercept(monkeypatch,RUNTIME,lambda s:s.replace(old,new))
+    r=m.audit_tree_tr_source(SOURCE)
+    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH' in r['blockers']
+
+
+def test_actual_pvsra_drift_blocks(monkeypatch):
+    m=api()
+    intercept(monkeypatch,RUNTIME.parent/'pvsra.py',lambda s:s+'\nDRIFT=True\n')
+    r=m.audit_tree_tr_source(SOURCE)
+    assert not r['source_subset_verified']
+    assert any(b.startswith('DEPENDENCY:pvsra:') for b in r['blockers'])
+
+
+@pytest.mark.parametrize('fault,want',[
+    ('false_empty','DEPENDENCY:pvsra:NOT_VERIFIED'),
+    ('exception','DEPENDENCY:pvsra:UNREADABLE:OSError'),
+    ('true_blocked','DEPENDENCY:pvsra:TEST_BLOCKER'),
+])
+def test_dependency_failure_cannot_certify_parent(monkeypatch,fault,want):
+    # Catch accepting a failed dependency merely because its blocker list is empty,
+    # dropping its exception, or trusting a contradictory success flag.
+    m=api()
+    original=m.audit_pvsra
+    def dependency(root):
+        result=original(root)
+        assert result['source_subset_verified'] and not result['blockers']
+        if fault=='exception':
+            raise OSError('dependency evidence became unreadable')
+        if fault=='false_empty':
+            result['source_subset_verified']=False
+        else:
+            result['blockers']=['TEST_BLOCKER']
+        return result
+    monkeypatch.setattr(m,'audit_pvsra',dependency)
+    r=m.audit_tree_tr_source(SOURCE)
+    assert r['status']=='BLOCKED' and not r['source_subset_verified']
+    assert want in r['blockers']
+    assert not r['ready_for_replay'] and not r['ready_for_training']
+
+
+@pytest.mark.parametrize('fault',['head','root','baseline','blob'])
+def test_literal_authority_cannot_be_redefined(monkeypatch,fault):
+    m=api()
+    if fault=='blob':
+        intercept(monkeypatch,SOURCE/'chart-desk/chartdesk/tr.py',lambda s:s+'\n# drift\n')
+        want='SOURCE_BLOB_MISMATCH:tr.py'
+    elif fault=='baseline':
+        intercept(monkeypatch,ROOT/'configs/trees/existing-alerts-baseline.json',
+            lambda s:s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9','0'*40))
+        want='BASELINE_COMMIT_MISMATCH'
+    else:
+        arg,value,want=('HEAD','0'*40,'SOURCE_COMMIT_MISMATCH') if fault=='head' else (
+            '--show-toplevel',str(SOURCE),'NOT_REPOSITORY_ROOT')
+        original=m._git
+        monkeypatch.setattr(m,'_git',lambda p,*a:value if a==(arg,) else original(p,*a))
+    r=m.audit_tree_tr_source(SOURCE)
+    assert not r['source_subset_verified'] and want in r['blockers']
+
+
+@pytest.mark.parametrize('fault',['count','signature','order','duplicate','missing','syntax'])
+def test_projection_requires_exact_source_shape(fault):
+    m=api()
+    text=(SOURCE/'chart-desk/chartdesk/tr.py').read_text(encoding='utf-8')
+    if fault=='count': text=text.replace('pvsra(df, auction=auction, session_tz=session_tz)','pvsra(df)')
+    elif fault=='signature': text=text.replace('max_zones: int = 500','max_zones: int = 501')
+    elif fault=='order': text=text.replace('def vector_zones(', 'def temporary(').replace('def daily_pivots(', 'def vector_zones(').replace('def temporary(', 'def daily_pivots(')
+    elif fault=='duplicate': text+='\ndef daily_pivots(daily): return {}\n'
+    elif fault=='missing': text=text.replace('def vector_zones(', 'def other_zones(')
+    else: text+='\ndef invalid syntax'
+    with pytest.raises((ValueError,SyntaxError)): m._projection(text)
+
+
+def test_missing_invalid_source_and_candidate_block(tmp_path,monkeypatch):
+    m=api()
+    for root in [tmp_path,None]:
+        r=m.audit_tree_tr_source(root)
+        assert not r['source_subset_verified'] and r['blockers']
+    monkeypatch.setattr(m,'RUNTIME',tmp_path/'missing.py')
+    r=m.audit_tree_tr_source(SOURCE)
+    assert not r['source_subset_verified'] and any(b.startswith('VENDOR_UNREADABLE:') for b in r['blockers'])
+
+
+def test_cli_from_unrelated_cwd_and_fresh_import_guard(tmp_path):
+    api()
+    for root,code,status in [(SOURCE,0,'VERIFIED'),(tmp_path,2,'BLOCKED')]:
+        p=subprocess.run([sys.executable,'-B',str(ROOT/'tools/check_tree_tr_source_parity.py'),
+            '--source-root',str(root)],cwd=tmp_path,capture_output=True,text=True,timeout=45)
+        assert p.returncode==code,p.stderr
+        r=json.loads(p.stdout)
+        assert r['status']==status and not r['ready_for_replay'] and not r['ready_for_training']
+    code='\n'.join(['import sys','class Guard:','    def find_spec(self,fullname,*args):',
+        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')): raise AssertionError(fullname)",
+        'sys.meta_path.insert(0,Guard())',
+        'from trading_system.tree_spec.tree_tr_source import audit_tree_tr_source',
+        "assert audit_tree_tr_source(sys.argv[1])['source_subset_verified']"])
+    p=subprocess.run([sys.executable,'-B','-c',code,str(SOURCE)],cwd=ROOT,capture_output=True,text=True,timeout=45)
+    assert p.returncode==0,p.stderr

