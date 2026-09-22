# Task2 options source proof

Base/HEAD c1b6071633c55376c64f0a98ece843706f420f49; three untracked full additions.

warning: in the working copy of 'trading_system/tree_spec/optionswall_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_spec/optionswall_source.py b/trading_system/tree_spec/optionswall_source.py
new file mode 100644
index 0000000..ba78387
--- /dev/null
+++ b/trading_system/tree_spec/optionswall_source.py
@@ -0,0 +1,123 @@
+"""Inert full-source audit of options artifacts, fixed mapping and clock ports."""
+import ast
+import hashlib
+from pathlib import Path
+
+from .tracker_admission_source import INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _without_doc
+
+ROOT=Path(__file__).resolve().parents[2]
+RUNTIME=ROOT/'trading_system/tree_replay/_vendor/optionswall.py'
+COMMIT='68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
+BLOB='c7d27ca396c162f6997b2a72bbd035ed6477e05b'
+SOURCE_IMPORTS='''from __future__ import annotations
+import datetime as dt
+import glob
+import json
+import math
+from dataclasses import dataclass
+from pathlib import Path
+from zoneinfo import ZoneInfo
+import pandas as pd
+from .workspace import repo'''
+IMPORTS='''from __future__ import annotations
+import datetime as dt
+import json
+import math
+from dataclasses import dataclass
+from zoneinfo import ZoneInfo
+import pandas as pd
+from io import StringIO'''
+PHYSICAL_GLOBALS='''REPORTS = str(repo("options-desk") / "out" / "report-*.json")
+TV_DIR = Path(__file__).resolve().parent.parent / "data" / "tv"'''
+INVENTORY=['REPORTS','TV_DIR','MAX_QUOTE_AGE_MIN','MAX_ANCHOR_GAP_MIN','ETF_OF','TV_FILE_OF',
+    'Walls','OptionsStatus','_timestamp','_finite','_anchor','_front_expiry','status','load']
+SIGNATURES='''def _anchor(symbol: str, market_asof: pd.Timestamp) -> tuple[float, pd.Timestamp] | None: pass
+def status(symbol: str, _current_spot: float | None=None, *, now: pd.Timestamp | None=None) -> OptionsStatus: pass
+def load(symbol: str, spot: float) -> Walls | None: pass'''
+REPLACEMENTS={
+    '_anchor':[
+        ('TV_DIR / TV_FILE_OF[symbol]','TV_FILE_OF[symbol]'),
+        ('pd.read_csv(path)','pd.read_csv(StringIO(self.source.read_tv_csv(path)))')],
+    'status':[
+        ('glob.glob(REPORTS)','self.source.list_reports()'),
+        ("Path(files[-1]).read_text(encoding='utf-8')",'self.source.read_report(files[-1])'),
+        ("pd.Timestamp.now(tz='UTC')",'pd.Timestamp(self.source.now_utc())'),
+        ('_anchor(symbol, market_asof)','self._anchor(symbol, market_asof)')],
+    'load':[('status(symbol, spot)','self.status(symbol, spot)')],
+}
+
+
+def _name(node):
+    if isinstance(node,(ast.ClassDef,ast.FunctionDef)):
+        return node.name
+    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
+        return node.targets[0].id
+    raise ValueError('UNEXPECTED_SOURCE_NODE')
+
+
+def _projection(text):
+    nodes=_without_doc(ast.parse(text))
+    imports=ast.parse(SOURCE_IMPORTS).body
+    if [_dump(n) for n in nodes[:len(imports)]]!=[_dump(n) for n in imports]:
+        raise ValueError('SOURCE_IMPORT_MISMATCH')
+    nodes=nodes[len(imports):]
+    if [_name(n) for n in nodes]!=INVENTORY:
+        raise ValueError('SOURCE_INVENTORY_MISMATCH')
+    if [_dump(n) for n in nodes[:2]]!=[_dump(n) for n in ast.parse(PHYSICAL_GLOBALS).body]:
+        raise ValueError('SOURCE_PHYSICAL_GLOBAL_MISMATCH')
+    signatures={n.name:n for n in ast.parse(SIGNATURES).body}
+    pure,methods=[],[]
+    for node in nodes[2:]:
+        if not isinstance(node,ast.FunctionDef) or node.name not in signatures:
+            pure.append(node)
+            continue
+        sig=signatures[node.name]
+        if node.decorator_list or _dump(node.args)!=_dump(sig.args) or _dump(node.returns)!=_dump(sig.returns):
+            raise ValueError('SOURCE_SIGNATURE_MISMATCH:'+node.name)
+        node.args.args.insert(0,ast.arg(arg='self'))
+        for old,new in REPLACEMENTS[node.name]:
+            _replace_exact(node,old,new)
+        methods.append(node)
+    if [n.name for n in methods]!=list(signatures):
+        raise ValueError('SOURCE_METHOD_ORDER')
+    ctor=ast.parse('def __init__(self, source):\n    self.source = source').body
+    reader=ast.ClassDef(name='OptionsWallReader',bases=[],keywords=[],body=ctor+methods,decorator_list=[])
+    return ast.parse(IMPORTS).body+pure+[reader]
+
+
+def audit_optionswall_source(source_root):
+    """Certify projection only; no historical artifact or feed readiness claim."""
+    blockers,checked=[],[]
+    report=dict(status='BLOCKED',source_subset_verified=False,blockers=blockers,
+        checked_projections=checked,source_commits={'chart-desk':COMMIT},
+        ready_for_replay=False,ready_for_training=False)
+    try:
+        root=Path(source_root)/'chart-desk'
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_ROOT_INVALID:'+type(exc).__name__)
+        return report
+    try:
+        if Path(_git(root,'--show-toplevel')).resolve()!=root.resolve(): blockers.append('NOT_REPOSITORY_ROOT')
+        if _git(root,'HEAD')!=COMMIT: blockers.append('SOURCE_COMMIT_MISMATCH')
+        baseline=_read_json(ROOT/'configs/trees/existing-alerts-baseline.json')
+        if [r.get('commit') for r in baseline['repositories'] if r.get('name')=='chart-desk']!=[COMMIT]:
+            blockers.append('BASELINE_COMMIT_MISMATCH')
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_IDENTITY_UNREADABLE:'+type(exc).__name__)
+    try:
+        text=(root/'chartdesk/optionswall.py').read_text(encoding='utf-8')
+        raw=text.encode('utf-8')
+        if hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()!=BLOB:
+            blockers.append('SOURCE_BLOB_MISMATCH')
+        expected=_projection(text)
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_PROJECTION_UNREADABLE:'+type(exc).__name__)
+    else:
+        try:
+            actual=_without_doc(ast.parse(RUNTIME.read_text(encoding='utf-8')))
+            if [_dump(n) for n in actual]!=[_dump(n) for n in expected]: blockers.append('VENDOR_AST_MISMATCH')
+            else: checked.append('optionswall')
+        except INPUT_ERRORS as exc:
+            blockers.append('VENDOR_UNREADABLE:'+type(exc).__name__)
+    if not blockers: report.update(status='VERIFIED',source_subset_verified=True)
+    return report

warning: in the working copy of 'tests/tree_spec/test_optionswall_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_spec/test_optionswall_source.py b/tests/tree_spec/test_optionswall_source.py
new file mode 100644
index 0000000..1483c27
--- /dev/null
+++ b/tests/tree_spec/test_optionswall_source.py
@@ -0,0 +1,123 @@
+"""Original options-wall projection must fail closed on source/candidate drift."""
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
+SOURCE=Path(os.environ.get('TR_TREE_SOURCE_ROOT','C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'))
+RUNTIME=ROOT/'trading_system/tree_replay/_vendor/optionswall.py'
+
+
+def api():
+    name='trading_system.tree_spec.optionswall_source'
+    assert importlib.util.find_spec(name) is not None,'options auditor missing'
+    return importlib.import_module(name)
+
+
+def intercept(monkeypatch,path,transform):
+    original=Path.read_text
+    def read(p,*a,**kw):
+        s=original(p,*a,**kw)
+        return transform(s) if p.resolve()==path.resolve() else s
+    monkeypatch.setattr(Path,'read_text',read)
+
+
+def test_original_module_verified_with_false_readiness():
+    r=api().audit_optionswall_source(SOURCE)
+    assert r['source_subset_verified'] and r['status']=='VERIFIED' and r['blockers']==[]
+    assert r['checked_projections']==['optionswall']
+    assert not r['ready_for_replay'] and not r['ready_for_training']
+
+
+@pytest.mark.parametrize('old,new',[
+    ('from io import StringIO','from io import StringIO\nimport urllib.request'),
+    ('MAX_QUOTE_AGE_MIN = 45.0','MAX_QUOTE_AGE_MIN = 60.0'),
+    ('MAX_ANCHOR_GAP_MIN = 75.0','MAX_ANCHOR_GAP_MIN = 90.0'),
+    ("'OANDA:XAUUSD': 'GLD'","'GC': 'GLD'"),
+    ('@dataclass(frozen=True)','@dataclass(frozen=False)'),
+    ('math.isfinite(result)','True'),
+    ('self.source = source','self.source = None'),
+    ("spot: float)","spot: int)"),
+    ('files = sorted(self.source.list_reports())','files = list(self.source.list_reports())'),
+    ('self.source.read_report(files[-1])','self.source.read_report(files[0])'),
+    ("permission != 'realtime_permission'","permission != 'delayed'"),
+    ('pd.Timestamp(self.source.now_utc())',"pd.Timestamp.now(tz='UTC')"),
+    ('age_min < -2','age_min <= -2'),
+    ('age_min > MAX_QUOTE_AGE_MIN','age_min >= MAX_QUOTE_AGE_MIN'),
+    ('idx <= market_asof','idx < market_asof'),
+    ("src.fillna('').astype(str).eq(symbol)",'True'),
+    ("usable.sort_values('_ts').iloc[-1]","usable.sort_values('_ts').iloc[0]"),
+    ('gap > MAX_ANCHOR_GAP_MIN','gap >= MAX_ANCHOR_GAP_MIN'),
+    ('ratio = under_spot / etf_spot','ratio = _current_spot / etf_spot'),
+    ('>= market_day','> market_day'),
+    ("ZoneInfo('America/New_York')","ZoneInfo('UTC')"),
+    ("calls[0].get('strike')","calls[-1].get('strike')"),
+    ('except (json.JSONDecodeError, OSError):','except Exception:'),
+    ('self.status(symbol, spot).walls','None'),
+])
+def test_candidate_semantic_changes_block(monkeypatch,old,new):
+    m=api(); assert old in RUNTIME.read_text(encoding='utf-8')
+    intercept(monkeypatch,RUNTIME,lambda s:s.replace(old,new))
+    r=m.audit_optionswall_source(SOURCE)
+    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH' in r['blockers']
+
+
+@pytest.mark.parametrize('fault',['head','root','baseline','blob'])
+def test_identity_not_redefined_by_candidate(monkeypatch,fault):
+    m=api()
+    if fault=='blob':
+        intercept(monkeypatch,SOURCE/'chart-desk/chartdesk/optionswall.py',lambda s:s+'\n# drift\n')
+        want='SOURCE_BLOB_MISMATCH'
+    elif fault=='baseline':
+        intercept(monkeypatch,ROOT/'configs/trees/existing-alerts-baseline.json',lambda s:s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9','0'*40))
+        want='BASELINE_COMMIT_MISMATCH'
+    else:
+        arg,value,want=('HEAD','0'*40,'SOURCE_COMMIT_MISMATCH') if fault=='head' else ('--show-toplevel',str(SOURCE),'NOT_REPOSITORY_ROOT')
+        original=m._git
+        monkeypatch.setattr(m,'_git',lambda p,*a:value if a==(arg,) else original(p,*a))
+    r=m.audit_optionswall_source(SOURCE)
+    assert not r['source_subset_verified'] and want in r['blockers']
+
+
+@pytest.mark.parametrize('fault',['global','import','signature','duplicate','order','substitution','syntax'])
+def test_projection_has_literal_source_contract(fault):
+    m=api(); text=(SOURCE/'chart-desk/chartdesk/optionswall.py').read_text(encoding='utf-8')
+    if fault=='global': text=text.replace('report-*.json','different-*.json')
+    elif fault=='import': text=text.replace('import glob','import glob as changed')
+    elif fault=='signature': text=text.replace('spot: float)', 'spot: int)')
+    elif fault=='duplicate': text+='\ndef load(symbol, spot): pass\n'
+    elif fault=='order': text=text.replace('MAX_QUOTE_AGE_MIN = 45.0','EXTRA = 1\nMAX_QUOTE_AGE_MIN = 45.0')
+    elif fault=='substitution': text=text.replace('glob.glob(REPORTS)','glob.glob(OTHER)')
+    else: text+='\ndef syntax error'
+    with pytest.raises((ValueError,SyntaxError)): m._projection(text)
+
+
+def test_missing_source_and_candidate_block(tmp_path,monkeypatch):
+    m=api()
+    for root in [None,tmp_path]:
+        r=m.audit_optionswall_source(root)
+        assert not r['source_subset_verified'] and r['blockers']
+    monkeypatch.setattr(m,'RUNTIME',tmp_path/'missing.py')
+    assert 'VENDOR_UNREADABLE:FileNotFoundError' in m.audit_optionswall_source(SOURCE)['blockers']
+
+
+def test_cli_and_forbidden_imports(tmp_path):
+    api()
+    for root,code in [(SOURCE,0),(tmp_path,2)]:
+        p=subprocess.run([sys.executable,'-B',str(ROOT/'tools/check_optionswall_source_parity.py'),'--source-root',str(root)],cwd=tmp_path,capture_output=True,text=True,timeout=45)
+        assert p.returncode==code,p.stderr
+        r=json.loads(p.stdout)
+        assert r['source_subset_verified']==(code==0)
+        assert not r['ready_for_replay'] and not r['ready_for_training']
+    code='\n'.join(['import sys','class Guard:','    def find_spec(self,fullname,*a):',
+        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')): raise AssertionError(fullname)",
+        'sys.meta_path.insert(0,Guard())','from trading_system.tree_spec.optionswall_source import audit_optionswall_source',
+        "assert audit_optionswall_source(sys.argv[1])['source_subset_verified']"])
+    p=subprocess.run([sys.executable,'-B','-c',code,str(SOURCE)],cwd=ROOT,capture_output=True,text=True,timeout=45)
+    assert p.returncode==0,p.stderr

warning: in the working copy of 'tools/check_optionswall_source_parity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tools/check_optionswall_source_parity.py b/tools/check_optionswall_source_parity.py
new file mode 100644
index 0000000..33e6bba
--- /dev/null
+++ b/tools/check_optionswall_source_parity.py
@@ -0,0 +1,23 @@
+"""Read-only full options context source projection audit."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None,''):
+    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.optionswall_source import audit_optionswall_source
+
+
+def main():
+    parser=argparse.ArgumentParser(description=__doc__)
+    parser.add_argument('--source-root',type=Path,required=True)
+    args=parser.parse_args()
+    result=audit_optionswall_source(args.source_root)
+    print(json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2))
+    return 0 if result['source_subset_verified'] else 2
+
+
+if __name__=='__main__':
+    raise SystemExit(main())

