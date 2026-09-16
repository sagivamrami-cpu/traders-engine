"""Binding certification rejects altered dataflow and missing source authority."""
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
ORIGINAL = SOURCE / 'chart-desk/chartdesk/matrix.py'
MATRIX = ROOT / 'trading_system/tree_replay/_vendor/matrix_reader.py'
FACADE = ROOT / 'trading_system/tree_replay/tree_revalidation.py'


def api():
    name = 'trading_system.tree_spec.tree_revalidation_source'
    assert importlib.util.find_spec(name) is not None, 'tree revalidation auditor missing'
    return importlib.import_module(name)


def intercept(monkeypatch, path, transform):
    original = Path.read_text
    def read(p, *args, **kwargs):
        text = original(p, *args, **kwargs)
        return transform(text) if p.resolve() == path.resolve() else text
    monkeypatch.setattr(Path, 'read_text', read)


def local_audit(monkeypatch):
    # Isolate new boundary mutation checks from the expensive unchanged graph.
    # Separate tests below run the actual graph, including genuine nested drift.
    m = api()
    monkeypatch.setattr(m, 'audit_tree_walk_source', lambda root: {
        'source_subset_verified': True, 'blockers': []})
    return m


def test_actual_full_binding_graph_is_verified_but_not_replay_or_training():
    r = api().audit_tree_revalidation_source(SOURCE)
    assert r['status'] == 'VERIFIED' and r['source_subset_verified']
    assert r['blockers'] == []
    assert r['checked_projections'] == ['matrix_reader', 'tree_revalidation']
    tree = r['dependencies']['tree_walk']
    assert tree['checked_projections'] == ['tree_core', 'tree_signals', 'tree_walk']
    assert set(tree['dependencies']) == {'levelmap_operation', 'patterns', 'options',
        'tree_tr', 'stretch', 'admission', 'revalidation', 'ema'}
    assert all(x['source_subset_verified'] and not x['blockers'] for x in tree['dependencies'].values())
    assert not r['ready_for_replay'] and not r['ready_for_training']


@pytest.mark.parametrize('path,old,new,label', [
    (MATRIX, 'matrix.LOOKBACK[tf]', '55', 'matrix_reader'),
    (MATRIX, 'self.source.fetch_corrected', 'self.source.fetch_final', 'matrix_reader'),
    (MATRIX, 'corr.render() if corr.show else None', 'None', 'matrix_reader'),
    (MATRIX, 'matrix.read_frame(df, tf, note)', 'matrix.read_frame(df.tail(55), tf, note)', 'matrix_reader'),
    (MATRIX, 'matrix.read_frame(df, tf, note)', 'self.source.read_tf(symbol, tf)', 'matrix_reader'),
    (MATRIX, 'for tf in tfs', 'for tf in reversed(tfs)', 'matrix_reader'),
    (MATRIX, 'self.read_tf(symbol, tf)', 'self.read_tf(symbol, "5m")', 'matrix_reader'),
    (MATRIX, 'from .admission_matrix import TFView', 'from .fake import TFView', 'matrix_reader'),
    (FACADE, 'self.matrix = MatrixReader(source)', 'self.matrix = source', 'tree_revalidation'),
    (FACADE, 'self.tree = TreeReader(source)', 'self.tree = source', 'tree_revalidation'),
    (FACADE, 'self.checks = Revalidation(self)', 'self.checks = Revalidation(source)', 'tree_revalidation'),
    (FACADE, 'super().__init__(source)', 'self.source = None', 'tree_revalidation'),
    (FACADE, 'return self.matrix.read_symbol(symbol, tfs=tfs)', 'return self.source.read_symbol(symbol, tfs=tfs)', 'tree_revalidation'),
    (FACADE, 'return self.tree.walk(symbol)', 'return self.source.tree_walk(symbol)', 'tree_revalidation'),
    (FACADE, 'return self.tree.walk(symbol)', 'return self.tree.walk(symbol, variant="strict")', 'tree_revalidation'),
    (FACADE, 'return self.checks.revalidate_pending(t, now=now)', 'return self.checks.revalidate_pending(t)', 'tree_revalidation'),
    (FACADE, 'return self.checks.still_valid(t)', 'return (True, "", True)', 'tree_revalidation'),
    (FACADE, 'return self.source.now_epoch()', 'return 0.', 'tree_revalidation'),
    (FACADE, 'return self.source.now_timestamp(tz=tz)', 'return self.source.now_timestamp(tz="UTC")', 'tree_revalidation'),
    (FACADE, 'return self.source.deep_bytes(key)', 'return b""', 'tree_revalidation'),
    (FACADE, 'return self.source.calendar_text(path)', 'return "[]"', 'tree_revalidation'),
    (FACADE, 'return self.source.shadow_open(mode, encoding)', 'return self.source.shadow_open(mode, encoding).__enter__()', 'tree_revalidation'),
    (FACADE, 'exist_ok=exist_ok', 'exist_ok=False', 'tree_revalidation'),
    (FACADE, 'class TreeRevalidation(BasisOperation):', 'class TreeRevalidation:', 'tree_revalidation'),
])
def test_binding_dataflow_drift_blocks(monkeypatch, path, old, new, label):
    m = local_audit(monkeypatch)
    assert old in path.read_text(encoding='utf-8')
    intercept(monkeypatch, path, lambda s: s.replace(old, new))
    r = m.audit_tree_revalidation_source(SOURCE)
    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH:' + label in r['blockers']


@pytest.mark.parametrize('fault', ['head', 'root', 'baseline', 'missing_pin'])
def test_independent_source_identity_is_required(monkeypatch, fault):
    m = local_audit(monkeypatch)
    want = {'head': 'SOURCE_COMMIT_MISMATCH', 'root': 'NOT_REPOSITORY_ROOT',
            'baseline': 'BASELINE_COMMIT_MISMATCH', 'missing_pin': 'BASELINE_COMMIT_MISMATCH'}[fault]
    if fault in ('baseline', 'missing_pin'):
        def change(text):
            doc = json.loads(text)
            if fault == 'missing_pin':
                doc['repositories'] = [r for r in doc['repositories'] if r['name'] != 'chart-desk']
            else:
                for row in doc['repositories']:
                    if row['name'] == 'chart-desk':
                        row['commit'] = '0' * 40
            return json.dumps(doc)
        intercept(monkeypatch, ROOT / 'configs/trees/existing-alerts-baseline.json', change)
    else:
        original = m._git
        arg = 'HEAD' if fault == 'head' else '--show-toplevel'
        monkeypatch.setattr(m, '_git', lambda p, *a: ('0' * 40 if fault == 'head' else str(SOURCE)) if a == (arg,) else original(p, *a))
    r = m.audit_tree_revalidation_source(SOURCE)
    assert not r['source_subset_verified'] and want in r['blockers']


@pytest.mark.parametrize('path,label', [(ORIGINAL, 'SOURCE_'), (MATRIX, 'VENDOR_UNREADABLE:matrix_reader'),
                                       (FACADE, 'VENDOR_UNREADABLE:tree_revalidation')])
@pytest.mark.parametrize('fault', ['missing', 'syntax'])
def test_missing_or_unparseable_required_file_blocks(monkeypatch, path, label, fault):
    m = local_audit(monkeypatch)
    def change(text):
        if fault == 'missing':
            raise FileNotFoundError('required file missing')
        return 'def invalid syntax'
    intercept(monkeypatch, path, change)
    r = m.audit_tree_revalidation_source(SOURCE)
    assert not r['source_subset_verified'] and any(b.startswith(label) for b in r['blockers'])


def test_source_blob_is_not_replaced_by_ast_similarity(monkeypatch):
    m = local_audit(monkeypatch)
    intercept(monkeypatch, ORIGINAL, lambda s: s + '\n# source drift\n')
    r = m.audit_tree_revalidation_source(SOURCE)
    assert not r['source_subset_verified'] and 'SOURCE_BLOB_MISMATCH:matrix' in r['blockers']


@pytest.mark.parametrize('fault', ['import', 'signature', 'return', 'missing', 'duplicate', 'order', 'substitution_count', 'substitution_site'])
def test_projection_enforces_independent_signatures_and_exact_adaptation_sites(fault):
    m = api()
    tree = ast.parse(ORIGINAL.read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'read_tf')
    if fault == 'import':
        tree.body.append(ast.parse('import socket').body[0])
    elif fault == 'signature':
        fn.args.args[0].arg = 'ticker'
    elif fault == 'return':
        fn.returns = None
    elif fault == 'missing':
        tree.body.remove(fn)
    elif fault == 'duplicate':
        tree.body.append(fn)
    elif fault == 'order':
        tree.body.remove(fn)
        tree.body.append(fn)
    elif fault == 'substitution_count':
        fn.body.append(ast.parse('basis.fetch_corrected(symbol, tf, LOOKBACK[tf])').body[0])
    else:
        fn.body[0].value.func.attr = 'fetch_other'
    with pytest.raises(ValueError):
        m._projection(ast.unparse(tree))


@pytest.mark.parametrize('fault', ['false_empty', 'true_blocked', 'error', 'missing_pin'])
def test_child_failure_never_becomes_a_clean_parent(monkeypatch, fault):
    m = api()
    def audit(root):
        assert root == SOURCE
        if fault == 'error':
            raise OSError('missing source')
        if fault == 'missing_pin':
            raise StopIteration('missing pin')
        return {'source_subset_verified': fault == 'true_blocked',
                'blockers': ['drift'] if fault == 'true_blocked' else []}
    monkeypatch.setattr(m, 'audit_tree_walk_source', audit)
    r = m.audit_tree_revalidation_source(SOURCE)
    assert not r['source_subset_verified']
    assert any(b.startswith('DEPENDENCY:tree_walk:') for b in r['blockers'])
    assert not r['ready_for_replay'] and not r['ready_for_training']


def test_actual_nested_tree_drift_blocks_binding(monkeypatch):
    m = api()
    path = ROOT / 'trading_system/tree_replay/_vendor/tree_core.py'
    assert 'MAX_DECISION_DRIFT_ATR = 0.33' in path.read_text(encoding='utf-8')
    intercept(monkeypatch, path, lambda s: s.replace('MAX_DECISION_DRIFT_ATR = 0.33', 'MAX_DECISION_DRIFT_ATR = 0.34'))
    r = m.audit_tree_revalidation_source(SOURCE)
    assert not r['source_subset_verified']
    assert 'DEPENDENCY:tree_walk:VENDOR_AST_MISMATCH:tree_core' in r['blockers']


def test_actual_missing_pin_cli_returns_json_blocked(monkeypatch, capsys):
    api()
    def change(text):
        doc = json.loads(text)
        doc['repositories'] = [r for r in doc['repositories'] if r['name'] != 'chart-desk']
        return json.dumps(doc)
    intercept(monkeypatch, ROOT / 'configs/trees/existing-alerts-baseline.json', change)
    cli = importlib.import_module('tools.check_tree_revalidation_source_parity')
    monkeypatch.setattr(sys, 'argv', ['check_tree_revalidation_source_parity.py', '--source-root', str(SOURCE)])
    assert cli.main() == 2
    r = json.loads(capsys.readouterr().out)
    assert 'BASELINE_COMMIT_MISMATCH' in r['blockers']
    assert 'DEPENDENCY:tree_walk:DEPENDENCY:ema:UNREADABLE:StopIteration' in r['blockers']
    assert not r['ready_for_replay'] and not r['ready_for_training']


def test_cli_unrelated_cwd_and_audit_imports_are_inert(tmp_path):
    m = api()
    assert not m.audit_tree_revalidation_source(None)['source_subset_verified']
    for root, code in [(SOURCE, 0), (tmp_path, 2)]:
        p = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/check_tree_revalidation_source_parity.py'),
                            '--source-root', str(root)], cwd=tmp_path, capture_output=True, text=True, timeout=90)
        assert p.returncode == code and not p.stderr, p.stderr
        r = json.loads(p.stdout)
        assert r['source_subset_verified'] is (code == 0)
        assert not r['ready_for_replay'] and not r['ready_for_training']
    guard = '\n'.join(['import sys', 'class Guard:', '    def find_spec(self,fullname,*a):',
        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')): raise AssertionError(fullname)",
        'sys.meta_path.insert(0,Guard())',
        'from trading_system.tree_spec.tree_revalidation_source import audit_tree_revalidation_source',
        "assert audit_tree_revalidation_source(sys.argv[1])['source_subset_verified']"])
    p = subprocess.run([sys.executable, '-B', '-c', guard, str(SOURCE)], cwd=ROOT, capture_output=True, text=True, timeout=90)
    assert p.returncode == 0 and not p.stderr, p.stderr
