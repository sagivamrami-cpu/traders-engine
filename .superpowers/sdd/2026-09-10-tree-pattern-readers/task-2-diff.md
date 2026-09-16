# Task2 full additions

Base/HEAD c1b6071633c55376c64f0a98ece843706f420f49; untracked three-file additions.

warning: in the working copy of 'trading_system/tree_spec/pattern_readers_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_spec/pattern_readers_source.py b/trading_system/tree_spec/pattern_readers_source.py
new file mode 100644
index 0000000..0d05b43
--- /dev/null
+++ b/trading_system/tree_spec/pattern_readers_source.py
@@ -0,0 +1,148 @@
+"""Inert full-module proof for original pattern readers and actual dependencies."""
+import ast
+import hashlib
+from pathlib import Path
+
+from tools.check_reversal_source_parity import check_source_parity as audit_pvsra
+from .tree_tr_source import audit_tree_tr_source as audit_tree_tr
+from .tracker_admission_source import INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _without_doc
+
+ROOT=Path(__file__).resolve().parents[2]
+VENDOR=ROOT/'trading_system/tree_replay/_vendor'
+COMMIT='68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
+BLOBS={
+    'wm':'d04a462eb0692ed991f25ea2633d8c81783db877',
+    'liquidity':'d73f06f323d39142932cb218935c15455244ce8b',
+    'brinks':'5c69c3367221e818a2b82f3ca559e1c5a36af675',
+    'checklists':'5c78955a6bb58d88c8117274606409fced65e22c',
+}
+COMMON='from __future__ import annotations\n'
+SOURCE_IMPORTS={
+    'wm':COMMON+'from dataclasses import dataclass\nimport pandas as pd\nfrom . import basis, tr',
+    'liquidity':COMMON+'from dataclasses import dataclass, field\nimport pandas as pd\nfrom . import basis',
+    'brinks':COMMON+'from dataclasses import dataclass, field\nfrom datetime import datetime, timedelta, timezone\nimport pandas as pd\nfrom . import basis, tr',
+    'checklists':COMMON+'from dataclasses import dataclass\nimport pandas as pd\nfrom . import basis, sessions, tr',
+}
+IMPORTS={
+    'wm':COMMON+'from dataclasses import dataclass\nimport pandas as pd\nfrom . import pattern_tr as tr',
+    'liquidity':COMMON+'from dataclasses import dataclass, field\nimport pandas as pd',
+    'brinks':COMMON+'from dataclasses import dataclass, field\nfrom datetime import datetime, timedelta, timezone\nimport pandas as pd\nfrom . import pattern_tr as tr',
+    'checklists':COMMON+'from dataclasses import dataclass\nimport pandas as pd\nfrom . import map_sessions as sessions, pattern_tr as tr\nfrom .brinks import BrinksReader',
+}
+INVENTORIES={
+    'wm':['SWING_K','LEG_TOLERANCE_ATR','MIN_HEIGHT_ATR','MAX_AGE_BARS','Formation','_swings','_dedup_pivots','detect'],
+    'liquidity':['EQ_TOL_ATR','LOOKBACK','SWING_K','RUN_ATR','RUN_BARS','Pool','Run','_atr','_swings','pools','run'],
+    'brinks':['BOX_START_H,BOX_END_H','RELEVANT_UNTIL_H','Box','today_box'],
+    'checklists':['WICK_SYMMETRY_MAX','BLOCK_BODY_MIN','BLOCK_RANGE_MIN_ATR','RvcGvc','rvc_gvc','Block','block_quality','blocks','BrinksRead','brinks_read'],
+}
+CLASSES={'wm':'WmReader','liquidity':'LiquidityReader','brinks':'BrinksReader','checklists':'ChecklistReader'}
+SIGNATURES={
+    'wm':"def detect(symbol: str, timeframe: str='15m') -> Formation | None: pass",
+    'liquidity':"def pools(symbol: str, timeframe: str='15m') -> list[Pool]: pass\ndef run(symbol: str, timeframe: str='15m') -> Run: pass",
+    'brinks':"def today_box(symbol: str, now: datetime | None=None) -> Box | None: pass",
+    'checklists':"def rvc_gvc(symbol: str, timeframe: str='15m') -> RvcGvc | None: pass\ndef blocks(symbol: str, timeframe: str='15m', lookback: int=60) -> list[Block]: pass\ndef brinks_read(symbol: str, timeframe: str='5m') -> BrinksRead: pass",
+}
+SHIM='from .pvsra import pvsra\nfrom .tree_tr import vector_zones'
+
+
+def _identity(node):
+    if isinstance(node,(ast.FunctionDef,ast.ClassDef)):
+        return node.name
+    if isinstance(node,ast.Assign):
+        return ','.join(n.id for target in node.targets for n in ast.walk(target) if isinstance(n,ast.Name))
+    raise ValueError('UNEXPECTED_SOURCE_NODE')
+
+
+def _projection(name,text):
+    nodes=_without_doc(ast.parse(text))
+    imports=ast.parse(SOURCE_IMPORTS[name]).body
+    if [_dump(n) for n in nodes[:len(imports)]]!=[_dump(n) for n in imports]:
+        raise ValueError('SOURCE_IMPORT_MISMATCH')
+    nodes=nodes[len(imports):]
+    if [_identity(n) for n in nodes]!=INVENTORIES[name]:
+        raise ValueError('SOURCE_ORDER_OR_INVENTORY_MISMATCH')
+    signatures={n.name:n for n in ast.parse(SIGNATURES[name]).body}
+    pure,methods=[],[]
+    for node in nodes:
+        if not isinstance(node,ast.FunctionDef) or node.name not in signatures:
+            pure.append(node)
+            continue
+        signature=signatures[node.name]
+        if node.decorator_list or _dump(node.args)!=_dump(signature.args) or _dump(node.returns)!=_dump(signature.returns):
+            raise ValueError('SOURCE_SIGNATURE_MISMATCH:'+node.name)
+        node.args.args.insert(0,ast.arg(arg='self'))
+        if node.name=='brinks_read':
+            target=ast.parse('from . import brinks as _bx').body[0]
+            matches=[n for n in node.body if _dump(n)==_dump(target)]
+            if len(matches)!=1:
+                raise ValueError('SOURCE_BRINKS_IMPORT_COUNT')
+            node.body.remove(matches[0])
+            _replace_exact(node,'_bx.today_box(symbol)','self.brinks.today_box(symbol)')
+            _replace_exact(node,"basis.fetch_corrected(symbol, '15m', 3)","self.source.fetch_corrected(symbol, '15m', 3)")
+        if node.name=='today_box':
+            _replace_exact(node,"basis.fetch_corrected(symbol, '5m', 2)","self.source.fetch_corrected(symbol, '5m', 2)")
+            _replace_exact(node,'datetime.now(timezone.utc)','self.source.now_utc()')
+        else:
+            days=5 if node.name=='rvc_gvc' else 10
+            _replace_exact(node,f'basis.fetch_corrected(symbol, timeframe, {days})',f'self.source.fetch_corrected(symbol, timeframe, {days})')
+        if node.name=='run':
+            _replace_exact(node,'pools(symbol, timeframe)','self.pools(symbol, timeframe)')
+        methods.append(node)
+    if [n.name for n in methods]!=list(signatures):
+        raise ValueError('SOURCE_METHOD_ORDER')
+    ctor=ast.parse('def __init__(self, source):\n    self.source = source\n'+
+        ('    self.brinks = BrinksReader(source)\n' if name=='checklists' else '')).body[0]
+    reader=ast.ClassDef(name=CLASSES[name],bases=[],keywords=[],body=[ctor]+methods,decorator_list=[])
+    return ast.parse(IMPORTS[name]).body+pure+[reader]
+
+
+def audit_pattern_readers_source(source_root):
+    """Only certify the pinned private projections, never input/replay readiness."""
+    blockers,checked,dependencies=[],[],{}
+    report=dict(status='BLOCKED',source_subset_verified=False,blockers=blockers,
+        checked_projections=checked,dependencies=dependencies,
+        source_commits={'chart-desk':COMMIT},ready_for_replay=False,ready_for_training=False)
+    try:
+        parent=Path(source_root); root=parent/'chart-desk'
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
+    for name in [*BLOBS,'pattern_tr']:
+        try:
+            if name=='pattern_tr':
+                expected=ast.parse(SHIM).body
+            else:
+                text=(root/'chartdesk'/(name+'.py')).read_text(encoding='utf-8')
+                raw=text.encode('utf-8')
+                if hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()!=BLOBS[name]:
+                    blockers.append('SOURCE_BLOB_MISMATCH:'+name)
+                expected=_projection(name,text)
+        except INPUT_ERRORS as exc:
+            blockers.append('SOURCE_PROJECTION_UNREADABLE:'+name+':'+type(exc).__name__)
+            continue
+        try:
+            actual=_without_doc(ast.parse((VENDOR/(name+'.py')).read_text(encoding='utf-8')))
+            if [_dump(n) for n in actual]!=[_dump(n) for n in expected]:
+                blockers.append('VENDOR_AST_MISMATCH:'+name)
+            else: checked.append(name)
+        except INPUT_ERRORS as exc:
+            blockers.append('VENDOR_UNREADABLE:'+name+':'+type(exc).__name__)
+    for name,audit,arg in [('tree_tr',audit_tree_tr,parent),('pvsra',audit_pvsra,root)]:
+        try:
+            result=audit(arg)
+            dependencies[name]=result
+            blockers.extend('DEPENDENCY:'+name+':'+b for b in result['blockers'])
+            if not result['source_subset_verified'] and not result['blockers']:
+                blockers.append('DEPENDENCY:'+name+':NOT_VERIFIED')
+        except INPUT_ERRORS as exc:
+            blockers.append('DEPENDENCY:'+name+':UNREADABLE:'+type(exc).__name__)
+    if not blockers: report.update(status='VERIFIED',source_subset_verified=True)
+    return report

warning: in the working copy of 'tests/tree_spec/test_pattern_readers_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_spec/test_pattern_readers_source.py b/tests/tree_spec/test_pattern_readers_source.py
new file mode 100644
index 0000000..4900469
--- /dev/null
+++ b/tests/tree_spec/test_pattern_readers_source.py
@@ -0,0 +1,165 @@
+"""Reject reader, dependency or pinned source drift without executing source."""
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
+VENDOR=ROOT/'trading_system/tree_replay/_vendor'
+
+
+def api():
+    name='trading_system.tree_spec.pattern_readers_source'
+    assert importlib.util.find_spec(name) is not None,'pattern source auditor missing'
+    return importlib.import_module(name)
+
+
+def intercept(monkeypatch,path,transform):
+    original=Path.read_text
+    def read(p,*a,**kw):
+        text=original(p,*a,**kw)
+        return transform(text) if p.resolve()==path.resolve() else text
+    monkeypatch.setattr(Path,'read_text',read)
+
+
+def test_real_source_graph_verified_not_replay_or_training():
+    r=api().audit_pattern_readers_source(SOURCE)
+    assert r['status']=='VERIFIED' and r['source_subset_verified'] and r['blockers']==[]
+    assert r['checked_projections']==['wm','liquidity','brinks','checklists','pattern_tr']
+    assert set(r['dependencies'])=={'tree_tr','pvsra'}
+    assert all(d['source_subset_verified'] for d in r['dependencies'].values())
+    assert not r['ready_for_replay'] and not r['ready_for_training']
+
+
+@pytest.mark.parametrize('module,old,new',[
+    ('wm','SWING_K = 3','SWING_K = 2'),
+    ('wm','MAX_AGE_BARS = 40','MAX_AGE_BARS = 41'),
+    ('wm','self.source = source','self.source = None'),
+    ('wm',"timeframe: str='15m'","timeframe: str='5m'"),
+    ('wm','m.bars_since_leg2 < best.bars_since_leg2','m.bars_since_leg2 <= best.bars_since_leg2'),
+    ('wm','confirmed=close > neck','confirmed=close >= neck'),
+    ('wm','elif hi[i]','if hi[i]'),
+    ('wm','except Exception:','except OSError:'),
+    ('liquidity','LOOKBACK = 120','LOOKBACK = 121'),
+    ('liquidity','EQ_TOL_ATR = 0.25','EQ_TOL_ATR = 0.5'),
+    ('liquidity','RUN_BARS = 4','RUN_BARS = 5'),
+    ('liquidity','self.pools(symbol, timeframe)','[]'),
+    ('liquidity','newest + 1:','newest:'),
+    ('liquidity','abs(jpx - px) <= tol','abs(jpx - px) < tol'),
+    ('brinks','BOX_START_H, BOX_END_H = (14, 15)','BOX_START_H, BOX_END_H = (13, 15)'),
+    ('brinks','self.source.now_utc()','datetime.now(timezone.utc)'),
+    ('brinks','len(seg) < 8','len(seg) < 12'),
+    ('brinks',"tr.vector_zones(seg, pv)",'tr.vector_zones(seg)'),
+    ('checklists','self.brinks = BrinksReader(source)','self.brinks = source'),
+    ('checklists',"timeframe, 5)","timeframe, 10)"),
+    ('checklists','i = len(df) - 2','i = len(df) - 1'),
+    ('checklists','c2 >= max(o1, c1)','c2 > max(o1, c1)'),
+    ('checklists','hi_w <= WICK_SYMMETRY_MAX','hi_w < WICK_SYMMETRY_MAX'),
+    ('checklists','if q ==','if False and q =='),
+    ('checklists','lo <= mid <= hi','lo < mid < hi'),
+    ('checklists',"self.source.fetch_corrected(symbol, '15m', 3)","self.source.fetch_corrected(symbol, '15m', 5)"),
+    ('pattern_tr','from .tree_tr import vector_zones','from .tree_tr import daily_pivots as vector_zones'),
+])
+def test_candidate_mutations_block(monkeypatch,module,old,new):
+    m=api(); path=VENDOR/(module+'.py')
+    assert old in path.read_text(encoding='utf-8')
+    intercept(monkeypatch,path,lambda s:s.replace(old,new))
+    r=m.audit_pattern_readers_source(SOURCE)
+    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH:'+module in r['blockers']
+
+
+@pytest.mark.parametrize('module',['wm','liquidity','brinks','checklists','pattern_tr'])
+def test_extra_executable_or_import_blocks(monkeypatch,module):
+    m=api(); intercept(monkeypatch,VENDOR/(module+'.py'),lambda s:s+'\nimport urllib.request\n')
+    r=m.audit_pattern_readers_source(SOURCE)
+    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH:'+module in r['blockers']
+
+
+@pytest.mark.parametrize('module',['tree_tr','pvsra'])
+def test_actual_dependency_drift_blocks(monkeypatch,module):
+    m=api(); intercept(monkeypatch,VENDOR/(module+'.py'),lambda s:s+'\nDRIFT=True\n')
+    r=m.audit_pattern_readers_source(SOURCE)
+    assert not r['source_subset_verified'] and any(b.startswith('DEPENDENCY:') for b in r['blockers'])
+
+
+@pytest.mark.parametrize('dependency',['tree_tr','pvsra'])
+@pytest.mark.parametrize('fault',['false_empty','exception','true_blocked'])
+def test_dependency_failures_block(monkeypatch,dependency,fault):
+    m=api(); attr='audit_'+dependency; original=getattr(m,attr)
+    def damaged(root):
+        r=original(root)
+        assert r['source_subset_verified'] and not r['blockers']
+        if fault=='exception': raise OSError('read failed')
+        if fault=='false_empty': r['source_subset_verified']=False
+        else: r['blockers']=['TEST_BLOCKER']
+        return r
+    monkeypatch.setattr(m,attr,damaged)
+    r=m.audit_pattern_readers_source(SOURCE)
+    suffix={'false_empty':'NOT_VERIFIED','exception':'UNREADABLE:OSError','true_blocked':'TEST_BLOCKER'}[fault]
+    assert 'DEPENDENCY:'+dependency+':'+suffix in r['blockers']
+    assert not r['source_subset_verified'] and not r['ready_for_replay'] and not r['ready_for_training']
+
+
+@pytest.mark.parametrize('module',['wm','liquidity','brinks','checklists'])
+def test_each_source_blob_is_pinned(monkeypatch,module):
+    m=api(); intercept(monkeypatch,SOURCE/'chart-desk/chartdesk'/(module+'.py'),lambda s:s+'\n# drift\n')
+    r=m.audit_pattern_readers_source(SOURCE)
+    assert 'SOURCE_BLOB_MISMATCH:'+module in r['blockers'] and not r['source_subset_verified']
+
+
+@pytest.mark.parametrize('fault',['head','root','baseline'])
+def test_source_identity_blocks(monkeypatch,fault):
+    m=api()
+    if fault=='baseline':
+        intercept(monkeypatch,ROOT/'configs/trees/existing-alerts-baseline.json',lambda s:s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9','0'*40))
+        want='BASELINE_COMMIT_MISMATCH'
+    else:
+        arg,value,want=('HEAD','0'*40,'SOURCE_COMMIT_MISMATCH') if fault=='head' else ('--show-toplevel',str(SOURCE),'NOT_REPOSITORY_ROOT')
+        original=m._git
+        monkeypatch.setattr(m,'_git',lambda p,*a:value if a==(arg,) else original(p,*a))
+    r=m.audit_pattern_readers_source(SOURCE)
+    assert want in r['blockers'] and not r['source_subset_verified']
+
+
+@pytest.mark.parametrize('fault',['duplicate','order','signature','substitution','import','syntax'])
+def test_projection_rejects_unexpected_source_shape(fault):
+    m=api(); text=(SOURCE/'chart-desk/chartdesk/wm.py').read_text(encoding='utf-8')
+    if fault=='duplicate': text+='\ndef detect(symbol): pass\n'
+    elif fault=='order': text=text.replace('SWING_K = 3','EXTRA = 3\nSWING_K = 3')
+    elif fault=='signature': text=text.replace('timeframe: str = "15m"','timeframe: str = "5m"')
+    elif fault=='substitution': text=text.replace('basis.fetch_corrected(symbol, timeframe, 10)','basis.fetch_corrected(symbol, timeframe, 9)')
+    elif fault=='import': text=text.replace('from . import basis, tr','from . import basis')
+    else: text+='\ndef syntax error'
+    with pytest.raises((ValueError,SyntaxError)): m._projection('wm',text)
+
+
+def test_missing_source_and_candidate_block(tmp_path,monkeypatch):
+    m=api()
+    for root in [None,tmp_path]:
+        r=m.audit_pattern_readers_source(root)
+        assert not r['source_subset_verified'] and r['blockers']
+    monkeypatch.setattr(m,'VENDOR',tmp_path)
+    r=m.audit_pattern_readers_source(SOURCE)
+    assert 'VENDOR_UNREADABLE:wm:FileNotFoundError' in r['blockers']
+
+
+def test_cli_and_import_guard(tmp_path):
+    api()
+    for root,exitcode in [(SOURCE,0),(tmp_path,2)]:
+        p=subprocess.run([sys.executable,'-B',str(ROOT/'tools/check_pattern_readers_source_parity.py'),'--source-root',str(root)],cwd=tmp_path,capture_output=True,text=True,timeout=60)
+        assert p.returncode==exitcode,p.stderr
+        r=json.loads(p.stdout)
+        assert r['source_subset_verified']==(exitcode==0)
+        assert not r['ready_for_training'] and not r['ready_for_replay']
+    code='\n'.join(['import sys','class Guard:','    def find_spec(self,fullname,*args):',
+        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')): raise AssertionError(fullname)",
+        'sys.meta_path.insert(0,Guard())','from trading_system.tree_spec.pattern_readers_source import audit_pattern_readers_source',
+        "assert audit_pattern_readers_source(sys.argv[1])['source_subset_verified']"])
+    p=subprocess.run([sys.executable,'-B','-c',code,str(SOURCE)],cwd=ROOT,capture_output=True,text=True,timeout=60)
+    assert p.returncode==0,p.stderr

warning: in the working copy of 'tools/check_pattern_readers_source_parity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tools/check_pattern_readers_source_parity.py b/tools/check_pattern_readers_source_parity.py
new file mode 100644
index 0000000..ae04d00
--- /dev/null
+++ b/tools/check_pattern_readers_source_parity.py
@@ -0,0 +1,23 @@
+"""Read-only CLI for the pinned pattern-reader graph."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None,''):
+    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.pattern_readers_source import audit_pattern_readers_source
+
+
+def main():
+    parser=argparse.ArgumentParser(description=__doc__)
+    parser.add_argument('--source-root',type=Path,required=True)
+    args=parser.parse_args()
+    result=audit_pattern_readers_source(args.source_root)
+    print(json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2))
+    return 0 if result['source_subset_verified'] else 2
+
+
+if __name__=='__main__':
+    raise SystemExit(main())

