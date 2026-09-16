# Task2 untracked additions against HEAD c1b6071

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

diff --git a/tests/tree_spec/test_tree_tr_source.py b/tests/tree_spec/test_tree_tr_source.py
new file mode 100644
index 0000000..d87aa8c
--- /dev/null
+++ b/tests/tree_spec/test_tree_tr_source.py
@@ -0,0 +1,140 @@
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

