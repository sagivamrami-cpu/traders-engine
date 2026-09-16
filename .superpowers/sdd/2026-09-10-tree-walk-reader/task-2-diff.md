# Task2 complete untracked additions

BASE=HEAD=c1b6071633c55376c64f0a98ece843706f420f49; no task commits. Full threefile additions below.

warning: in the working copy of 'trading_system/tree_spec/tree_walk_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_spec/tree_walk_source.py b/trading_system/tree_spec/tree_walk_source.py
new file mode 100644
index 0000000..9b4fb89
--- /dev/null
+++ b/trading_system/tree_spec/tree_walk_source.py
@@ -0,0 +1,202 @@
+"""Inert full ordered tree projection and actual dependency-graph audit."""
+import ast
+import hashlib
+from pathlib import Path
+
+from tools.check_ema_source_parity import check_source_parity as audit_ema
+from .admission_source import audit_admission_source as audit_admission
+from .levelmap_operation_source import audit_levelmap_operation_source as audit_levelmap_operation
+from .optionswall_source import audit_optionswall_source as audit_options
+from .pattern_readers_source import audit_pattern_readers_source as audit_patterns
+from .revalidation_source import audit_revalidation_source as audit_revalidation
+from .stretch_source import audit_stretch_source as audit_stretch
+from .tree_tr_source import audit_tree_tr_source as audit_tree_tr
+from .tracker_admission_source import INPUT_ERRORS, _dump, _git, _read_json, _replace_exact
+
+ROOT = Path(__file__).resolve().parents[2]
+COMMIT = '68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
+BLOB = 'fdb439a39bbd35230e421c0319c6be0e2fbfbc1d'
+SOURCE_IMPORTS = '''from __future__ import annotations
+from dataclasses import dataclass, field
+import pandas as pd
+from . import basis, brinks, checklists, levelmap, matrix, sessions, stretch, tr, wm'''
+INVENTORY = [
+    'VECTOR_BASE', 'RECOVERY', 'MAX_MAGNET_ATR', 'AGGRESSIVE_ATR', 'AGGRESSIVE_BARS',
+    'EXTREME_LOOKBACK', 'BUY_SIDE,SELL_SIDE', 'EXTREME_PCT', 'MAX_DECISION_DRIFT_ATR',
+    'LEVEL_ZONE_ATR', 'STOP_CUSHION_ATR', 'TREE_STYLE', 'SV_BODY_MAX', 'SV_WICK_MIN',
+    'SV_VOLUME_MULT', 'LevelsUnavailable', 'FINAL_STAGE', 'STAGES', 'FINAL_STAGE',
+    '_news_stop', 'Walk', '_atr', '_stopping_volume', '_levels_ahead', '_variant_levels',
+    '_stamp_decision', '_levels_unavailable_reason', 'TREND_LADDER', 'HI_FRAMES',
+    'LO_FRAMES', '_trend_ladder', '_side', '_trend_from_ladder', '_ladder_text',
+    'trap_direction', 'walk', 'first_vector_above_50', 'levels_to_trade', 'trade_from_walk',
+]
+SIGNATURES = '''def _variant_levels(symbol: str, variant: str, missing: list | None=None) -> list | None: pass
+def _trend_ladder(symbol: str, d4h, r4) -> dict: pass
+def walk(symbol: str, variant: str='house') -> Walk: pass
+def first_vector_above_50(symbol: str, timeframe: str='5m'): pass
+def levels_to_trade(symbol: str, close: float, direction: str, atr: float, variant: str='house'): pass
+def trade_from_walk(w: Walk): pass'''
+CORE_IMPORTS = '''from __future__ import annotations
+from dataclasses import dataclass, field
+import pandas as pd'''
+SIGNALS = '''from .tr import emas, ema_cloud
+from .pvsra import pvsra
+from .tree_tr import vector_zones, daily_pivots'''
+READER_IMPORTS = '''from __future__ import annotations
+import pandas as pd
+from . import admission_matrix as matrix, map_sessions as sessions, watch_sessions
+from . import tree_signals as tr
+from .basis_operation import BasisOperation
+from .levelmap_operation import LevelmapOperation
+from .brinks import BrinksReader
+from .checklists import ChecklistReader
+from .wm import WmReader
+from .liquidity import LiquidityReader
+from .optionswall import OptionsWallReader
+from .stretch import StretchReader
+from .tree_core import VECTOR_BASE, RECOVERY, MAX_MAGNET_ATR, AGGRESSIVE_ATR, AGGRESSIVE_BARS, EXTREME_LOOKBACK, BUY_SIDE, SELL_SIDE, EXTREME_PCT, MAX_DECISION_DRIFT_ATR, LEVEL_ZONE_ATR, STOP_CUSHION_ATR, TREE_STYLE, SV_BODY_MAX, SV_WICK_MIN, SV_VOLUME_MULT, LevelsUnavailable, FINAL_STAGE, STAGES, _news_stop, Walk, _atr, _stopping_volume, _levels_ahead, _stamp_decision, _levels_unavailable_reason, TREND_LADDER, HI_FRAMES, LO_FRAMES, _side, _trend_from_ladder, _ladder_text, trap_direction'''
+CONSTRUCTOR = '''class TreeReader:
+    def __init__(self, source):
+        self.source = source
+        self.basis = BasisOperation(source)
+        self.levelmap = LevelmapOperation(source)
+        self.brinks = BrinksReader(source)
+        self.checklists = ChecklistReader(source)
+        self.wm = WmReader(source)
+        self.liquidity = LiquidityReader(source)
+        self.optionswall = OptionsWallReader(source)
+        self.stretch = StretchReader(self.basis)'''
+ALIASES = {'_variant_levels': ['basis', 'levelmap'], '_trend_ladder': ['basis'],
+    'walk': ['basis', 'brinks', 'checklists', 'wm', 'stretch'],
+    'first_vector_above_50': ['basis'], 'levels_to_trade': [], 'trade_from_walk': ['basis']}
+EXPRESSIONS = {
+    'walk': [('_trend_ladder(symbol, d4h, r4)', 'self._trend_ladder(symbol, d4h, r4)'),
+        ('_variant_levels(symbol, variant, w.missing)', 'self._variant_levels(symbol, variant, w.missing)'),
+        ('first_vector_above_50(symbol, "5m")', 'self.first_vector_above_50(symbol, "5m")'),
+        ('_repo("news-desk")', 'PurePosixPath("news-desk")'),
+        ('_dt.now(_tz.utc).timestamp()', 'self.source.now_utc().timestamp()'),
+        ('cal.read_text()', 'self.source.calendar_text(cal.as_posix())'),
+        ('sessions.current_session()', 'watch_sessions.current_session_at(decision_time=self.source.now_utc())'),
+        ('_pd.Timestamp.now(tz="UTC")', '_pd.Timestamp(self.source.now_utc())')],
+    'levels_to_trade': [('_variant_levels(symbol, variant)', 'self._variant_levels(symbol, variant)')],
+    'trade_from_walk': [('_variant_levels(w.symbol, w.variant)', 'self._variant_levels(w.symbol, w.variant)')],
+}
+STATEMENTS = {
+    '_news_stop': [('from .tradeplan import calendar_event_ts, calendar_high_impact_in_window',
+                    'from .revalidation import calendar_event_ts, calendar_high_impact_in_window')],
+    '_levels_ahead': [('from .tradeplan import distinct_targets', 'from .pricing import distinct_targets')],
+    'walk': [('from . import optionswall', 'optionswall = self.optionswall'),
+        ('from . import liquidity as _liq', '_liq = self.liquidity'),
+        ('from .workspace import repo as _repo', 'from pathlib import PurePosixPath')],
+    'levels_to_trade': [('from .tradeplan import apply_stop_band, resolve_ladder',
+                          'from .pricing import apply_stop_band, resolve_ladder')],
+    'trade_from_walk': [('from .tradeplan import MIN_RR, Plan', 'from .pricing import MIN_RR, Plan'),
+        ('from .tradeplan import apply_stop_band, resolve_ladder', 'from .pricing import apply_stop_band, resolve_ladder')],
+}
+
+
+def _identity(node):
+    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
+        return node.name
+    if isinstance(node, ast.Assign):
+        return ','.join(n.id for target in node.targets for n in ast.walk(target) if isinstance(n, ast.Name))
+    raise ValueError('UNEXPECTED_SOURCE_NODE')
+
+
+def _projection(text):
+    """Transform inert ASTs with independent inventory, signatures and site counts."""
+    tree = ast.parse(text)
+    if ast.get_docstring(tree) is None:
+        raise ValueError('SOURCE_DOCSTRING_MISSING')
+    imports = ast.parse(SOURCE_IMPORTS).body
+    if [_dump(n) for n in tree.body[1:1 + len(imports)]] != [_dump(n) for n in imports]:
+        raise ValueError('SOURCE_IMPORT_MISMATCH')
+    nodes = tree.body[1 + len(imports):]
+    if [_identity(n) for n in nodes] != INVENTORY:
+        raise ValueError('SOURCE_ORDER_OR_INVENTORY_MISMATCH')
+    signatures = {n.name: n for n in ast.parse(SIGNATURES).body}
+    core = [tree.body[0]] + ast.parse(CORE_IMPORTS).body
+    reader = ast.parse(CONSTRUCTOR).body[0]
+    for node in nodes:
+        name = _identity(node)
+        for old, new in STATEMENTS.get(name, []):
+            _replace_exact(node, old, new, statement=True)
+        if name not in signatures:
+            core.append(node)
+            continue
+        signature = signatures[name]
+        actual_return = None if node.returns is None else _dump(node.returns)
+        expected_return = None if signature.returns is None else _dump(signature.returns)
+        if not isinstance(node, ast.FunctionDef) or node.decorator_list or (
+                _dump(node.args) != _dump(signature.args) or actual_return != expected_return):
+            raise ValueError('SOURCE_SIGNATURE_MISMATCH:' + name)
+        node.args.args.insert(0, ast.arg(arg='self'))
+        for old, new in EXPRESSIONS.get(name, []):
+            _replace_exact(node, old, new)
+        aliases = ast.parse('\n'.join(a + ' = self.' + a for a in ALIASES[name])).body
+        at = int(ast.get_docstring(node) is not None)
+        node.body[at:at] = aliases
+        reader.body.append(node)
+    if [n.name for n in reader.body[1:]] != list(signatures):
+        raise ValueError('SOURCE_METHOD_ORDER')
+    return {'tree_core': core, 'tree_signals': ast.parse(SIGNALS).body,
+            'tree_walk': ast.parse(READER_IMPORTS).body + [reader]}
+
+
+def audit_tree_walk_source(source_root):
+    """Certify source projections only, not historical inputs or model readiness."""
+    blockers, checked, dependencies = [], [], {}
+    report = dict(status='BLOCKED', source_subset_verified=False, blockers=blockers,
+        checked_projections=checked, dependencies=dependencies,
+        source_commits={'chart-desk': COMMIT}, ready_for_replay=False, ready_for_training=False)
+    try:
+        parent = Path(source_root)
+        root = parent / 'chart-desk'
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
+    try:
+        text = (root / 'chartdesk/tree.py').read_text(encoding='utf-8')
+        raw = text.encode('utf-8')
+        if hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() != BLOB:
+            blockers.append('SOURCE_BLOB_MISMATCH:tree')
+        projected = _projection(text)
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_PROJECTION_UNREADABLE:' + type(exc).__name__ + ':' + str(exc))
+    else:
+        for name, expected in projected.items():
+            try:
+                actual = ast.parse((ROOT / 'trading_system/tree_replay/_vendor' / (name + '.py')).read_text(encoding='utf-8')).body
+                if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
+                    blockers.append('VENDOR_AST_MISMATCH:' + name)
+                else:
+                    checked.append(name)
+            except INPUT_ERRORS as exc:
+                blockers.append('VENDOR_UNREADABLE:' + name + ':' + type(exc).__name__)
+    for name, audit, path in [
+        ('levelmap_operation', audit_levelmap_operation, parent), ('patterns', audit_patterns, parent),
+        ('options', audit_options, parent), ('tree_tr', audit_tree_tr, parent),
+        ('stretch', audit_stretch, parent), ('admission', audit_admission, parent),
+        ('revalidation', audit_revalidation, parent), ('ema', audit_ema, root),
+    ]:
+        try:
+            result = audit(path)
+            dependencies[name] = result
+            blockers.extend('DEPENDENCY:' + name + ':' + b for b in result['blockers'])
+            if result['source_subset_verified'] is not True and not result['blockers']:
+                blockers.append('DEPENDENCY:' + name + ':NOT_VERIFIED')
+        except INPUT_ERRORS as exc:
+            blockers.append('DEPENDENCY:' + name + ':UNREADABLE:' + type(exc).__name__)
+    if not blockers:
+        report.update(status='VERIFIED', source_subset_verified=True)
+    return report

warning: in the working copy of 'tools/check_tree_walk_source_parity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tools/check_tree_walk_source_parity.py b/tools/check_tree_walk_source_parity.py
new file mode 100644
index 0000000..f39f967
--- /dev/null
+++ b/tools/check_tree_walk_source_parity.py
@@ -0,0 +1,23 @@
+"""Audit the complete original tree and its dependencies without source execution."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None, ''):
+    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.tree_walk_source import audit_tree_walk_source
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument('--source-root', type=Path, required=True,
+                        help='Explicit parent of retained source checkouts')
+    report = audit_tree_walk_source(parser.parse_args().source_root)
+    print(json.dumps(report, sort_keys=True, indent=2))
+    return 0 if report['source_subset_verified'] else 2
+
+
+if __name__ == '__main__':
+    raise SystemExit(main())

warning: in the working copy of 'tests/tree_spec/test_tree_walk_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_spec/test_tree_walk_source.py b/tests/tree_spec/test_tree_walk_source.py
new file mode 100644
index 0000000..23a7f92
--- /dev/null
+++ b/tests/tree_spec/test_tree_walk_source.py
@@ -0,0 +1,192 @@
+"""The whole tree certification must fail on source, binding and dependency drift."""
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
+ORIGINAL = SOURCE / 'chart-desk/chartdesk/tree.py'
+VENDOR = ROOT / 'trading_system/tree_replay/_vendor'
+
+
+def api():
+    name = 'trading_system.tree_spec.tree_walk_source'
+    assert importlib.util.find_spec(name) is not None, 'complete tree auditor missing'
+    return importlib.import_module(name)
+
+
+def intercept(monkeypatch, path, transform):
+    original = Path.read_text
+    def read(p, *args, **kwargs):
+        text = original(p, *args, **kwargs)
+        return transform(text) if p.resolve() == path.resolve() else text
+    monkeypatch.setattr(Path, 'read_text', read)
+
+
+def test_whole_tree_and_real_graph_are_verified_without_readiness():
+    r = api().audit_tree_walk_source(SOURCE)
+    assert r['status'] == 'VERIFIED' and r['source_subset_verified'] and r['blockers'] == []
+    assert r['checked_projections'] == ['tree_core', 'tree_signals', 'tree_walk']
+    assert set(r['dependencies']) == {'levelmap_operation', 'patterns', 'options',
+        'tree_tr', 'stretch', 'admission', 'revalidation', 'ema'}
+    assert all(d['source_subset_verified'] and not d['blockers'] for d in r['dependencies'].values())
+    assert not r['ready_for_replay'] and not r['ready_for_training']
+
+
+@pytest.mark.parametrize('file,old,new', [
+    ('tree_core', "'MEMORY',", ''),
+    ('tree_core', 'MAX_MAGNET_ATR = 5.0', 'MAX_MAGNET_ATR = 6.0'),
+    ('tree_core', 'MAX_DECISION_DRIFT_ATR = 0.33', 'MAX_DECISION_DRIFT_ATR = 0.34'),
+    ('tree_core', 'SV_BODY_MAX = 0.35', 'SV_BODY_MAX = 0.36'),
+    ('tree_core', 'STOP_CUSHION_ATR = 0.35', 'STOP_CUSHION_ATR = 0.3'),
+    ('tree_core', '15 * 60', '30 * 60'),
+    ('tree_core', "return ('שורט', 'trap')", "return ('לונג', 'trap')"),
+    ('tree_signals', 'from .tr import emas, ema_cloud', 'from .fake import emas, ema_cloud'),
+    ('tree_signals', 'from .tree_tr import vector_zones, daily_pivots', 'from .tree_tr import vector_zones'),
+    ('tree_walk', 'self.levelmap = LevelmapOperation(source)', 'self.levelmap = source'),
+    ('tree_walk', 'self.stretch = StretchReader(self.basis)', 'self.stretch = StretchReader(source)'),
+    ('tree_walk', 'self.wm = WmReader(source)', 'self.wm = source'),
+    ('tree_walk', 'self.optionswall = OptionsWallReader(source)', 'self.optionswall = source'),
+    ('tree_walk', "regime = 'UNKNOWN'", "regime = 'CONSOLIDATING'"),
+    ('tree_walk', 'tr.daily_pivots(d1).items()', '{}.items()'),
+    ('tree_walk', "d15['close'].iloc[-2]", "d15['close'].iloc[-1]"),
+    ('tree_walk', 'moved < 0.15', 'moved < 0.2'),
+    ('tree_walk', 'self.source.now_utc().timestamp()', '_dt.now(_tz.utc).timestamp()'),
+    ('tree_walk', 'self.source.calendar_text(cal.as_posix())', 'cal.read_text()'),
+    ('tree_walk', 'decision_time=self.source.now_utc()', 'decision_time=now_ts'),
+    ('tree_walk', '_pd.Timestamp(self.source.now_utc())', '_pd.Timestamp.now(tz="UTC")'),
+    ('tree_walk', 'w.refused = p', 'w.refused = None'),
+    ('tree_walk', 'if up and c <= edge_hi:', 'if up and c < edge_hi:'),
+    ('tree_walk', 'from .pricing import MIN_RR, Plan', 'from .fake import MIN_RR, Plan'),
+])
+def test_complete_candidate_projection_rejects_drift(monkeypatch, file, old, new):
+    m = api()
+    path = VENDOR / (file + '.py')
+    assert old in path.read_text(encoding='utf-8')
+    intercept(monkeypatch, path, lambda s: s.replace(old, new))
+    r = m.audit_tree_walk_source(SOURCE)
+    assert not r['source_subset_verified']
+    assert 'VENDOR_AST_MISMATCH:' + file in r['blockers']
+
+
+@pytest.mark.parametrize('fault', ['blob', 'syntax', 'missing'])
+def test_source_bytes_are_pinned(monkeypatch, fault):
+    m = api()
+    def change(s):
+        if fault == 'missing':
+            raise FileNotFoundError('source missing')
+        return s + ('\ndef broken syntax' if fault == 'syntax' else '\n# drift\n')
+    intercept(monkeypatch, ORIGINAL, change)
+    r = m.audit_tree_walk_source(SOURCE)
+    assert not r['source_subset_verified'] and any(b.startswith('SOURCE_') for b in r['blockers'])
+
+
+@pytest.mark.parametrize('fault', ['head', 'root', 'baseline'])
+def test_source_authority_cannot_be_redefined(monkeypatch, fault):
+    m = api()
+    if fault == 'baseline':
+        intercept(monkeypatch, ROOT / 'configs/trees/existing-alerts-baseline.json',
+                  lambda s: s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9', '0' * 40))
+        want = 'BASELINE_COMMIT_MISMATCH'
+    else:
+        arg, value, want = ('HEAD', '0' * 40, 'SOURCE_COMMIT_MISMATCH') if fault == 'head' else ('--show-toplevel', str(SOURCE), 'NOT_REPOSITORY_ROOT')
+        original = m._git
+        monkeypatch.setattr(m, '_git', lambda p, *a: value if a == (arg,) else original(p, *a))
+    r = m.audit_tree_walk_source(SOURCE)
+    assert not r['source_subset_verified'] and want in r['blockers']
+
+
+@pytest.mark.parametrize('fault', ['import', 'signature', 'missing', 'duplicate', 'order', 'clock_count', 'clock_site'])
+def test_projection_independently_validates_source_inventory_and_substitution_contract(fault):
+    m = api()
+    tree = ast.parse(ORIGINAL.read_text(encoding='utf-8'))
+    walk = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'walk')
+    if fault == 'import':
+        tree.body.insert(1, ast.parse('import socket').body[0])
+    elif fault == 'signature':
+        walk.args.defaults[0] = ast.Constant('different')
+    elif fault == 'missing':
+        tree.body.remove(walk)
+    elif fault == 'duplicate':
+        tree.body.append(ast.parse('FINAL_STAGE = "FAKE"').body[0])
+    elif fault == 'order':
+        a = next(i for i,n in enumerate(tree.body) if isinstance(n,ast.FunctionDef) and n.name == '_side')
+        tree.body[a], tree.body[a+1] = tree.body[a+1], tree.body[a]
+    elif fault == 'clock_count':
+        walk.body.append(ast.parse('_dt.now(_tz.utc).timestamp()').body[0])
+    else:
+        class Clock(ast.NodeTransformer):
+            def visit_Attribute(self, n):
+                if isinstance(n.value, ast.Name) and n.value.id == '_dt' and n.attr == 'now':
+                    n.attr = 'today'
+                return self.generic_visit(n)
+        Clock().visit(walk)
+    with pytest.raises(ValueError):
+        m._projection(ast.unparse(tree))
+
+
+@pytest.mark.parametrize('file', ['tree_core', 'tree_signals', 'tree_walk'])
+@pytest.mark.parametrize('fault', ['missing', 'syntax'])
+def test_each_runtime_file_is_required(monkeypatch, file, fault):
+    m = api()
+    def change(s):
+        if fault == 'missing':
+            raise FileNotFoundError('candidate missing')
+        return 'def broken syntax'
+    intercept(monkeypatch, VENDOR / (file + '.py'), change)
+    r = m.audit_tree_walk_source(SOURCE)
+    assert not r['source_subset_verified']
+    assert any(b.startswith('VENDOR_UNREADABLE:' + file) for b in r['blockers'])
+
+
+@pytest.mark.parametrize('dependency', ['levelmap_operation', 'patterns', 'options', 'tree_tr', 'stretch', 'admission', 'revalidation', 'ema'])
+@pytest.mark.parametrize('fault', ['false_empty', 'true_blocked', 'error'])
+def test_each_dependency_failure_propagates(monkeypatch, dependency, fault):
+    m = api()
+    def audit(root):
+        assert root == (SOURCE / 'chart-desk' if dependency == 'ema' else SOURCE)
+        if fault == 'error':
+            raise OSError('missing graph')
+        return {'source_subset_verified': fault == 'true_blocked',
+                'blockers': ['drift'] if fault == 'true_blocked' else []}
+    monkeypatch.setattr(m, 'audit_' + dependency, audit)
+    r = m.audit_tree_walk_source(SOURCE)
+    assert not r['source_subset_verified']
+    assert any(b.startswith('DEPENDENCY:' + dependency + ':') for b in r['blockers'])
+
+
+@pytest.mark.parametrize('file,old,new', [('tr', 'I.ema(df["close"], n)', 'I.ema(df["close"], n + 1)'),
+    ('revalidation', '30 * 60', '31 * 60')])
+def test_genuine_transitive_drift_blocks(monkeypatch, file, old, new):
+    m = api()
+    path = VENDOR / (file + '.py')
+    assert old in path.read_text(encoding='utf-8')
+    intercept(monkeypatch, path, lambda s: s.replace(old, new))
+    r = m.audit_tree_walk_source(SOURCE)
+    assert not r['source_subset_verified'] and any(b.startswith('DEPENDENCY:') for b in r['blockers'])
+
+
+def test_invalid_root_and_cli_inert_imports(tmp_path):
+    m = api()
+    assert not m.audit_tree_walk_source(None)['source_subset_verified']
+    for root, code in [(SOURCE, 0), (tmp_path, 2)]:
+        p = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/check_tree_walk_source_parity.py'),
+                            '--source-root', str(root)], cwd=tmp_path, capture_output=True, text=True, timeout=90)
+        assert p.returncode == code, p.stderr
+        r = json.loads(p.stdout)
+        assert r['source_subset_verified'] == (code == 0)
+        assert not r['ready_for_replay'] and not r['ready_for_training']
+    guard = '\n'.join(['import sys', 'class Guard:', '    def find_spec(self,fullname,*a):',
+        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')): raise AssertionError(fullname)",
+        'sys.meta_path.insert(0,Guard())',
+        'from trading_system.tree_spec.tree_walk_source import audit_tree_walk_source',
+        "assert audit_tree_walk_source(sys.argv[1])['source_subset_verified']"])
+    p = subprocess.run([sys.executable, '-B', '-c', guard, str(SOURCE)], cwd=ROOT, capture_output=True, text=True, timeout=90)
+    assert p.returncode == 0, p.stderr
