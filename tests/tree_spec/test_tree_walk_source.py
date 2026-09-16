"""The whole tree certification must fail on source, binding and dependency drift."""
import ast
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get('TR_TREE_SOURCE_ROOT', Path(__file__).resolve().parents[2] / ".source-checkouts"))
ORIGINAL = SOURCE / 'chart-desk/chartdesk/tree.py'
VENDOR = ROOT / 'trading_system/tree_replay/_vendor'


def api():
    name = 'trading_system.tree_spec.tree_walk_source'
    assert importlib.util.find_spec(name) is not None, 'complete tree auditor missing'
    return importlib.import_module(name)


def intercept(monkeypatch, path, transform):
    original = Path.read_text
    def read(p, *args, **kwargs):
        text = original(p, *args, **kwargs)
        return transform(text) if p.resolve() == path.resolve() else text
    monkeypatch.setattr(Path, 'read_text', read)


def test_whole_tree_and_real_graph_are_verified_without_readiness():
    r = api().audit_tree_walk_source(SOURCE)
    assert r['status'] == 'VERIFIED' and r['source_subset_verified'] and r['blockers'] == []
    assert r['checked_projections'] == ['tree_core', 'tree_signals', 'tree_walk']
    assert set(r['dependencies']) == {'levelmap_operation', 'patterns', 'options',
        'tree_tr', 'stretch', 'admission', 'revalidation', 'ema'}
    assert all(d['source_subset_verified'] and not d['blockers'] for d in r['dependencies'].values())
    assert not r['ready_for_replay'] and not r['ready_for_training']


@pytest.mark.parametrize('file,old,new', [
    ('tree_core', "'MEMORY',", ''),
    ('tree_core', 'MAX_MAGNET_ATR = 5.0', 'MAX_MAGNET_ATR = 6.0'),
    ('tree_core', 'MAX_DECISION_DRIFT_ATR = 0.33', 'MAX_DECISION_DRIFT_ATR = 0.34'),
    ('tree_core', 'SV_BODY_MAX = 0.35', 'SV_BODY_MAX = 0.36'),
    ('tree_core', 'STOP_CUSHION_ATR = 0.35', 'STOP_CUSHION_ATR = 0.3'),
    ('tree_core', '15 * 60', '30 * 60'),
    ('tree_core', "return ('שורט', 'trap')", "return ('לונג', 'trap')"),
    ('tree_signals', 'from .tr import emas, ema_cloud', 'from .fake import emas, ema_cloud'),
    ('tree_signals', 'from .tree_tr import vector_zones, daily_pivots', 'from .tree_tr import vector_zones'),
    ('tree_walk', 'self.levelmap = LevelmapOperation(source)', 'self.levelmap = source'),
    ('tree_walk', 'self.stretch = StretchReader(self.basis)', 'self.stretch = StretchReader(source)'),
    ('tree_walk', 'self.wm = WmReader(source)', 'self.wm = source'),
    ('tree_walk', 'self.optionswall = OptionsWallReader(source)', 'self.optionswall = source'),
    ('tree_walk', "regime = 'UNKNOWN'", "regime = 'CONSOLIDATING'"),
    ('tree_walk', 'tr.daily_pivots(d1).items()', '{}.items()'),
    ('tree_walk', "d15['close'].iloc[-2]", "d15['close'].iloc[-1]"),
    ('tree_walk', 'moved < 0.15', 'moved < 0.2'),
    ('tree_walk', 'self.source.now_utc().timestamp()', '_dt.now(_tz.utc).timestamp()'),
    ('tree_walk', 'self.source.calendar_text(cal.as_posix())', 'cal.read_text()'),
    ('tree_walk', 'decision_time=self.source.now_utc()', 'decision_time=now_ts'),
    ('tree_walk', '_pd.Timestamp(self.source.now_utc())', '_pd.Timestamp.now(tz="UTC")'),
    ('tree_walk', 'w.refused = p', 'w.refused = None'),
    ('tree_walk', 'if up and c <= edge_hi:', 'if up and c < edge_hi:'),
    ('tree_walk', 'from .pricing import MIN_RR, Plan', 'from .fake import MIN_RR, Plan'),
])
def test_complete_candidate_projection_rejects_drift(monkeypatch, file, old, new):
    m = api()
    path = VENDOR / (file + '.py')
    assert old in path.read_text(encoding='utf-8')
    intercept(monkeypatch, path, lambda s: s.replace(old, new))
    r = m.audit_tree_walk_source(SOURCE)
    assert not r['source_subset_verified']
    assert 'VENDOR_AST_MISMATCH:' + file in r['blockers']


@pytest.mark.parametrize('fault', ['blob', 'syntax', 'missing'])
def test_source_bytes_are_pinned(monkeypatch, fault):
    m = api()
    def change(s):
        if fault == 'missing':
            raise FileNotFoundError('source missing')
        return s + ('\ndef broken syntax' if fault == 'syntax' else '\n# drift\n')
    intercept(monkeypatch, ORIGINAL, change)
    r = m.audit_tree_walk_source(SOURCE)
    assert not r['source_subset_verified'] and any(b.startswith('SOURCE_') for b in r['blockers'])


@pytest.mark.parametrize('fault', ['head', 'root', 'baseline'])
def test_source_authority_cannot_be_redefined(monkeypatch, fault):
    m = api()
    if fault == 'baseline':
        intercept(monkeypatch, ROOT / 'configs/trees/existing-alerts-baseline.json',
                  lambda s: s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9', '0' * 40))
        want = 'BASELINE_COMMIT_MISMATCH'
    else:
        arg, value, want = ('HEAD', '0' * 40, 'SOURCE_COMMIT_MISMATCH') if fault == 'head' else ('--show-toplevel', str(SOURCE), 'NOT_REPOSITORY_ROOT')
        original = m._git
        monkeypatch.setattr(m, '_git', lambda p, *a: value if a == (arg,) else original(p, *a))
    r = m.audit_tree_walk_source(SOURCE)
    assert not r['source_subset_verified'] and want in r['blockers']


@pytest.mark.parametrize('via_cli', [False, True])
def test_missing_baseline_pin_returns_blocked_report_with_actual_ema(monkeypatch, capsys, via_cli):
    m = api()
    def missing_pin(text):
        doc = json.loads(text)
        doc['repositories'] = [r for r in doc['repositories'] if r['name'] != 'chart-desk']
        return json.dumps(doc)
    intercept(monkeypatch, ROOT / 'configs/trees/existing-alerts-baseline.json', missing_pin)
    if via_cli:
        cli = importlib.import_module('tools.check_tree_walk_source_parity')
        monkeypatch.setattr(sys, 'argv', ['check_tree_walk_source_parity.py', '--source-root', str(SOURCE)])
        assert cli.main() == 2
        r = json.loads(capsys.readouterr().out)
    else:
        r = m.audit_tree_walk_source(SOURCE)
    assert r['status'] == 'BLOCKED' and not r['source_subset_verified']
    assert 'BASELINE_COMMIT_MISMATCH' in r['blockers']
    assert 'DEPENDENCY:ema:UNREADABLE:StopIteration' in r['blockers']
    assert not r['ready_for_replay'] and not r['ready_for_training']


@pytest.mark.parametrize('fault', ['import', 'signature', 'missing', 'duplicate', 'order', 'clock_count', 'clock_site'])
def test_projection_independently_validates_source_inventory_and_substitution_contract(fault):
    m = api()
    tree = ast.parse(ORIGINAL.read_text(encoding='utf-8'))
    walk = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'walk')
    if fault == 'import':
        tree.body.insert(1, ast.parse('import socket').body[0])
    elif fault == 'signature':
        walk.args.defaults[0] = ast.Constant('different')
    elif fault == 'missing':
        tree.body.remove(walk)
    elif fault == 'duplicate':
        tree.body.append(ast.parse('FINAL_STAGE = "FAKE"').body[0])
    elif fault == 'order':
        a = next(i for i,n in enumerate(tree.body) if isinstance(n,ast.FunctionDef) and n.name == '_side')
        tree.body[a], tree.body[a+1] = tree.body[a+1], tree.body[a]
    elif fault == 'clock_count':
        walk.body.append(ast.parse('_dt.now(_tz.utc).timestamp()').body[0])
    else:
        class Clock(ast.NodeTransformer):
            def visit_Attribute(self, n):
                if isinstance(n.value, ast.Name) and n.value.id == '_dt' and n.attr == 'now':
                    n.attr = 'today'
                return self.generic_visit(n)
        Clock().visit(walk)
    with pytest.raises(ValueError):
        m._projection(ast.unparse(tree))


@pytest.mark.parametrize('file', ['tree_core', 'tree_signals', 'tree_walk'])
@pytest.mark.parametrize('fault', ['missing', 'syntax'])
def test_each_runtime_file_is_required(monkeypatch, file, fault):
    m = api()
    def change(s):
        if fault == 'missing':
            raise FileNotFoundError('candidate missing')
        return 'def broken syntax'
    intercept(monkeypatch, VENDOR / (file + '.py'), change)
    r = m.audit_tree_walk_source(SOURCE)
    assert not r['source_subset_verified']
    assert any(b.startswith('VENDOR_UNREADABLE:' + file) for b in r['blockers'])


@pytest.mark.parametrize('dependency', ['levelmap_operation', 'patterns', 'options', 'tree_tr', 'stretch', 'admission', 'revalidation', 'ema'])
@pytest.mark.parametrize('fault', ['false_empty', 'true_blocked', 'error'])
def test_each_dependency_failure_propagates(monkeypatch, dependency, fault):
    m = api()
    def audit(root):
        assert root == (SOURCE / 'chart-desk' if dependency == 'ema' else SOURCE)
        if fault == 'error':
            raise OSError('missing graph')
        return {'source_subset_verified': fault == 'true_blocked',
                'blockers': ['drift'] if fault == 'true_blocked' else []}
    monkeypatch.setattr(m, 'audit_' + dependency, audit)
    r = m.audit_tree_walk_source(SOURCE)
    assert not r['source_subset_verified']
    assert any(b.startswith('DEPENDENCY:' + dependency + ':') for b in r['blockers'])


@pytest.mark.parametrize('file,old,new', [('tr', 'I.ema(df["close"], n)', 'I.ema(df["close"], n + 1)'),
    ('revalidation', '30 * 60', '31 * 60')])
def test_genuine_transitive_drift_blocks(monkeypatch, file, old, new):
    m = api()
    path = VENDOR / (file + '.py')
    assert old in path.read_text(encoding='utf-8')
    intercept(monkeypatch, path, lambda s: s.replace(old, new))
    r = m.audit_tree_walk_source(SOURCE)
    assert not r['source_subset_verified'] and any(b.startswith('DEPENDENCY:') for b in r['blockers'])


def test_invalid_root_and_cli_inert_imports(tmp_path):
    m = api()
    assert not m.audit_tree_walk_source(None)['source_subset_verified']
    for root, code in [(SOURCE, 0), (tmp_path, 2)]:
        p = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/check_tree_walk_source_parity.py'),
                            '--source-root', str(root)], cwd=tmp_path, capture_output=True, text=True, timeout=90)
        assert p.returncode == code, p.stderr
        r = json.loads(p.stdout)
        assert r['source_subset_verified'] == (code == 0)
        assert not r['ready_for_replay'] and not r['ready_for_training']
    guard = '\n'.join(['import sys', 'class Guard:', '    def find_spec(self,fullname,*a):',
        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')): raise AssertionError(fullname)",
        'sys.meta_path.insert(0,Guard())',
        'from trading_system.tree_spec.tree_walk_source import audit_tree_walk_source',
        "assert audit_tree_walk_source(sys.argv[1])['source_subset_verified']"])
    p = subprocess.run([sys.executable, '-B', '-c', guard, str(SOURCE)], cwd=ROOT, capture_output=True, text=True, timeout=90)
    assert p.returncode == 0, p.stderr
