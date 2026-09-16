# Task2 full untracked additions
Base=HEAD=c1b6071633c55376c64f0a98ece843706f420f49. No commits.

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
