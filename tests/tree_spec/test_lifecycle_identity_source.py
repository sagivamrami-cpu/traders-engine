"""Identity certification must fail on source, cache, matching and graph drift."""
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
TRACKER = SOURCE / 'chart-desk/chartdesk/tracker.py'
THREADS = SOURCE / 'chart-desk/chartdesk/trade_threads.py'
VENDOR = ROOT / 'trading_system/tree_replay/_vendor/lifecycle_identity.py'


def api():
    name = 'trading_system.tree_spec.lifecycle_identity_source'
    assert importlib.util.find_spec(name) is not None, 'lifecycle identity auditor missing'
    return importlib.import_module(name)


def intercept(monkeypatch, path, transform):
    original = Path.read_text
    def read(p, *args, **kwargs):
        text = original(p, *args, **kwargs)
        return transform(text) if p.resolve() == path.resolve() else text
    monkeypatch.setattr(Path, 'read_text', read)


def local_audit(monkeypatch):
    # Only local mutations bypass the already tested expensive child graph.
    # Real graph success/drift and subprocess tests below keep actual audits.
    m = api()
    monkeypatch.setattr(m, 'audit_tracker_admission_source', lambda root: {
        'source_subset_verified': True, 'blockers': []})
    return m


def test_full_identity_and_actual_geometry_graph_are_verified_without_readiness():
    r = api().audit_lifecycle_identity_source(SOURCE)
    assert r['status'] == 'VERIFIED' and r['source_subset_verified'] and r['blockers'] == []
    assert r['checked_projections'] == ['lifecycle_identity']
    child = r['dependencies']['tracker_admission']
    assert child['source_subset_verified'] and not child['blockers']
    assert 'trading_system/tree_replay/_vendor/tracker_admission.py' in child['checked_projections']
    assert not r['ready_for_replay'] and not r['ready_for_training']


@pytest.mark.parametrize('old,new', [
    ("return sym.split(':')[-1]", 'return sym'),
    ("if ' SELL' in text:", "if ' BUY' in text:"),
    ('tol: float=0.02', 'tol: float=0.2'),
    ('live or pending or fallback', 'pending or live or fallback'),
    ('return (None, level_matches)', 'return (level_matches[0], [])'),
    ("t.get('state') not in ('CANCELLED',)", "t.get('state') not in ('CANCELLED', 'DONE')"),
    ("if core.startswith('⏰'):", "if False:"),
    ("self._receipt_cache = {'mtime': 0, 'keys': set()}", "self._receipt_cache = source.cache"),
    ("st.st_mtime_ns != self._receipt_cache['mtime']", 'True'),
    ("self._receipt_cache['mtime'] = st.st_mtime_ns", "self._receipt_cache['mtime'] = 0"),
    ("self._receipt_cache['keys'] = keys", "self._receipt_cache['keys'] = set()"),
    ("for folder in ('done', ''):", "for folder in ('', 'done'):"),
    ("for style in ('scalp', 'intraday', 'swing'):", "for style in ('intraday',):"),
    ('self.source.queue_exists(f.as_posix())', 'f.exists()'),
    ("self.source.queue_text(f.as_posix(), encoding='utf-8')", "f.read_text(encoding='utf-8')"),
    ('self.source.receipt_stat()', 'self.source.final_receipt_stat()'),
    ("self.source.receipt_text(encoding='utf-8')", "'[]'"),
    ('rts >= sent_ts - 120.0', 'rts > sent_ts - 120.0'),
    ('if trade_id != want_id:', 'if False:'),
    ('from .tracker_admission import _trade_identity', 'from .fake import _trade_identity'),
    ('self.source.load() if state is None else state', 'self.source.load()'),
    ('> 0.011:', '> 0.02:'),
    ("'event_ts': self.source.now_epoch()", "'event_ts': 0."),
    ('_match_trade_for_text(text, state)', 'self.source.match_trade(text, state)'),
])
def test_complete_candidate_projection_rejects_changed_behavior(monkeypatch, old, new):
    m = local_audit(monkeypatch)
    assert old in VENDOR.read_text(encoding='utf-8')
    intercept(monkeypatch, VENDOR, lambda s: s.replace(old, new))
    r = m.audit_lifecycle_identity_source(SOURCE)
    assert not r['source_subset_verified']
    assert 'VENDOR_AST_MISMATCH:lifecycle_identity' in r['blockers']


@pytest.mark.parametrize('path', [TRACKER, THREADS])
@pytest.mark.parametrize('fault', ['blob', 'missing', 'syntax'])
def test_both_source_files_are_required_and_pinned(monkeypatch, path, fault):
    m = local_audit(monkeypatch)
    def change(text):
        if fault == 'missing':
            raise FileNotFoundError('source missing')
        return text + '\n# drift\n' if fault == 'blob' else 'def invalid syntax'
    intercept(monkeypatch, path, change)
    r = m.audit_lifecycle_identity_source(SOURCE)
    assert not r['source_subset_verified'] and any(b.startswith('SOURCE_') for b in r['blockers'])


@pytest.mark.parametrize('fault', ['missing', 'syntax'])
def test_missing_runtime_never_certifies(monkeypatch, fault):
    m = local_audit(monkeypatch)
    def change(text):
        if fault == 'missing':
            raise FileNotFoundError('runtime missing')
        return 'def invalid syntax'
    intercept(monkeypatch, VENDOR, change)
    r = m.audit_lifecycle_identity_source(SOURCE)
    assert not r['source_subset_verified']
    assert any(b.startswith('VENDOR_UNREADABLE:lifecycle_identity') for b in r['blockers'])


@pytest.mark.parametrize('fault', ['head', 'root', 'baseline'])
def test_independent_authority_is_not_redefined(monkeypatch, fault):
    m = local_audit(monkeypatch)
    if fault == 'baseline':
        intercept(monkeypatch, ROOT / 'configs/trees/existing-alerts-baseline.json',
                  lambda s: s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9', '0' * 40))
        expected = 'BASELINE_COMMIT_MISMATCH'
    else:
        arg, value, expected = ('HEAD', '0' * 40, 'SOURCE_COMMIT_MISMATCH') if fault == 'head' else ('--show-toplevel', str(SOURCE), 'NOT_REPOSITORY_ROOT')
        original = m._git
        monkeypatch.setattr(m, '_git', lambda p, *a: value if a == (arg,) else original(p, *a))
    r = m.audit_lifecycle_identity_source(SOURCE)
    assert not r['source_subset_verified'] and expected in r['blockers']


@pytest.mark.parametrize('group', ['tracker', 'threads'])
@pytest.mark.parametrize('fault', ['signature', 'missing', 'duplicate', 'order', 'substitution'])
def test_projection_rejects_independently_wrong_source_contract(group, fault):
    m = api()
    first = ast.parse(TRACKER.read_text(encoding='utf-8'))
    second = ast.parse(THREADS.read_text(encoding='utf-8'))
    tree = first if group == 'tracker' else second
    name = '_receipt_from_queue_file' if group == 'tracker' else 'identity'
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    if fault == 'signature':
        fn.args.args[0].arg = 'wrong'
    elif fault == 'missing':
        tree.body.remove(fn)
    elif fault == 'duplicate':
        tree.body.append(fn)
    elif fault == 'order':
        tree.body.remove(fn)
        tree.body.append(fn)
    elif group == 'tracker':
        fn.body.append(ast.parse('f.exists()').body[0])
    else:
        context = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'context')
        context.body.append(ast.parse('time.time()').body[0])
    with pytest.raises(ValueError):
        m._projection(ast.unparse(first), ast.unparse(second))


def test_source_cache_site_count_and_thread_imports_are_independent():
    m = api()
    tracker = TRACKER.read_text(encoding='utf-8')
    threads = THREADS.read_text(encoding='utf-8')
    with pytest.raises(ValueError):
        m._projection(tracker.replace('if st.st_mtime_ns != _receipt_cache["mtime"]:', 'if True:'), threads)
    with pytest.raises(ValueError):
        m._projection(tracker, threads + '\nimport socket\n')


@pytest.mark.parametrize('fault', ['false_empty', 'true_blocked', 'error', 'missing_pin'])
def test_child_failure_propagates(monkeypatch, fault):
    m = api()
    def audit(root):
        assert root == SOURCE
        if fault == 'error':
            raise OSError('missing graph')
        if fault == 'missing_pin':
            raise StopIteration('missing pin')
        return {'source_subset_verified': fault == 'true_blocked',
                'blockers': ['drift'] if fault == 'true_blocked' else []}
    monkeypatch.setattr(m, 'audit_tracker_admission_source', audit)
    r = m.audit_lifecycle_identity_source(SOURCE)
    assert not r['source_subset_verified']
    assert any(b.startswith('DEPENDENCY:tracker_admission:') for b in r['blockers'])
    assert not r['ready_for_replay'] and not r['ready_for_training']


def test_genuine_geometry_dependency_drift_blocks(monkeypatch):
    m = api()
    path = ROOT / 'trading_system/tree_replay/_vendor/tracker_admission.py'
    assert 'round(float(entry), 8)' in path.read_text(encoding='utf-8')
    intercept(monkeypatch, path, lambda s: s.replace('round(float(entry), 8)', 'round(float(entry), 2)'))
    r = m.audit_lifecycle_identity_source(SOURCE)
    assert not r['source_subset_verified']
    assert any('DEPENDENCY:tracker_admission:VENDOR_AST_MISMATCH:' in b for b in r['blockers'])


def test_missing_pin_actual_cli_is_blocked_json(monkeypatch, capsys):
    api()
    def change(text):
        doc = json.loads(text)
        doc['repositories'] = [r for r in doc['repositories'] if r['name'] != 'chart-desk']
        return json.dumps(doc)
    intercept(monkeypatch, ROOT / 'configs/trees/existing-alerts-baseline.json', change)
    cli = importlib.import_module('tools.check_lifecycle_identity_source_parity')
    monkeypatch.setattr(sys, 'argv', ['check_lifecycle_identity_source_parity.py', '--source-root', str(SOURCE)])
    assert cli.main() == 2
    r = json.loads(capsys.readouterr().out)
    assert 'BASELINE_COMMIT_MISMATCH' in r['blockers']
    assert 'DEPENDENCY:tracker_admission:BASELINE_COMMIT_MISMATCH:chart-desk' in r['blockers']
    assert not r['ready_for_replay'] and not r['ready_for_training']


def test_cli_and_full_audit_do_not_import_runtime_or_original_source(tmp_path):
    m = api()
    assert not m.audit_lifecycle_identity_source(None)['source_subset_verified']
    for root, code in [(SOURCE, 0), (tmp_path, 2)]:
        p = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/check_lifecycle_identity_source_parity.py'),
                            '--source-root', str(root)], cwd=tmp_path, capture_output=True, text=True, timeout=90)
        assert p.returncode == code and not p.stderr, p.stderr
        r = json.loads(p.stdout)
        assert r['source_subset_verified'] is (code == 0)
        assert not r['ready_for_replay'] and not r['ready_for_training']
    guard = '\n'.join(['import sys', 'class Guard:', '    def find_spec(self,fullname,*a):',
        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')): raise AssertionError(fullname)",
        'sys.meta_path.insert(0,Guard())',
        'from trading_system.tree_spec.lifecycle_identity_source import audit_lifecycle_identity_source',
        "assert audit_lifecycle_identity_source(sys.argv[1])['source_subset_verified']"])
    p = subprocess.run([sys.executable, '-B', '-c', guard, str(SOURCE)], cwd=ROOT, capture_output=True, text=True, timeout=90)
    assert p.returncode == 0 and not p.stderr, p.stderr
