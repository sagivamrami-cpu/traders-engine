"""Journal source certification must reject actual behavior and authority drift."""
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
ORIGINAL = SOURCE / 'chart-desk/chartdesk/outbox.py'
VENDOR = ROOT / 'trading_system/tree_replay/_vendor/outbox_journal.py'


def api():
    name = 'trading_system.tree_spec.outbox_journal_source'
    assert importlib.util.find_spec(name) is not None, 'outbox journal auditor missing'
    return importlib.import_module(name)


def intercept(monkeypatch, path, transform):
    original = Path.read_text
    def read(p, *args, **kwargs):
        text = original(p, *args, **kwargs)
        return transform(text) if p.resolve() == path.resolve() else text
    monkeypatch.setattr(Path, 'read_text', read)


def local(monkeypatch):
    # Isolate only the new boundary's mutations; real inherited graph cases below.
    m = api()
    monkeypatch.setattr(m, 'audit_lifecycle_identity_source', lambda root: {
        'source_subset_verified': True, 'blockers': []})
    return m


def test_actual_journal_and_identity_graph_without_readiness():
    r = api().audit_outbox_journal_source(SOURCE)
    assert r['status'] == 'VERIFIED' and r['source_subset_verified'] and not r['blockers']
    assert r['checked_projections'] == ['outbox_journal']
    child = r['dependencies']['lifecycle_identity']
    assert child['source_subset_verified'] and not child['blockers']
    assert child['dependencies']['tracker_admission']['source_subset_verified']
    assert not r['ready_for_replay'] and not r['ready_for_training']


@pytest.mark.parametrize('old,new', [
    ("PurePosixPath('chart-desk/out/outbox.jsonl')", "PurePosixPath('live/outbox.jsonl')"),
    ('self.threads = LifecycleIdentity(source)', 'self.threads = source.threads'),
    ('self._BORN = {}', 'self._BORN = source.born'),
    ('int(ts // 60)', 'int(ts // 600)'),
    ("k != 'ts'", 'True'),
    ('self.source.journal_exists()', 'STORE.exists()'),
    ("self.source.journal_text(encoding='utf-8')", "'[]'"),
    ('@contextmanager', '@unsafe'),
    ("self.source.open_append_lock(_append_lock_path().as_posix(), 'a+')", "open(_append_lock_path(), 'a+')"),
    ('self.source.try_acquire(lk, timeout=None)', 'self.source.try_acquire(lk, timeout=0)'),
    ('self.source.release(lk)', 'pass'),
    ('self.source.assert_offline()', 'pass'),
    ("self.source.open_journal('a', encoding='utf-8')", "STORE.open('a', encoding='utf-8')"),
    ('ensure_ascii=False', 'ensure_ascii=True'),
    ('return _merge(self._rows())', 'return self.source.last_states()'),
    ('self._BORN.pop(text, None)', 'self._BORN.get(text)'),
    ('self.threads.context(text)', 'self.source.context(text)'),
    ("('DELIVERED', 'RESOLVED')", "('DELIVERED',)"),
    ("<= LATE_AFTER_S", '< LATE_AFTER_S'),
    ('if to_group and (not prior.get(\'to_group\')):', 'if True:'),
    ("'attempts': 0", "'attempts': 1"),
    ("if born and born < ts:", "if born:") ,
    ("and 'text' in r", "and r.get('text')"),
    ("self._mark(eid, 'RESOLVED', why=why)", "self._mark(eid, 'DELIVERED', why=why)"),
    ("if ev.get('text') == text:", 'if True:'),
])
def test_complete_runtime_projection_rejects_drift(monkeypatch, old, new):
    m = local(monkeypatch)
    assert old in VENDOR.read_text(encoding='utf-8')
    intercept(monkeypatch, VENDOR, lambda s: s.replace(old, new))
    r = m.audit_outbox_journal_source(SOURCE)
    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH:outbox_journal' in r['blockers']


@pytest.mark.parametrize('movement', ['early_clock', 'born_inside_lock', 'read_outside_lock'])
def test_operation_order_is_part_of_full_projection(monkeypatch, movement):
    m = local(monkeypatch)
    def change(text):
        tree = ast.parse(text)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'enqueue')
        if movement == 'early_clock':
            clock = next(n for n in fn.body if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == 'ts')
            fn.body.remove(clock)
            fn.body.insert(1, clock)  # before payload validation, after docstring
        else:
            lock = next(n for n in fn.body if isinstance(n, ast.With))
            if movement == 'born_inside_lock':
                born = next(n for n in fn.body if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == 'born')
                fn.body.remove(born)
                lock.body.insert(0, born)
            else:
                read = lock.body.pop(0)
                fn.body.insert(fn.body.index(lock), read)
        return ast.unparse(tree)
    intercept(monkeypatch, VENDOR, change)
    r = m.audit_outbox_journal_source(SOURCE)
    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH:outbox_journal' in r['blockers']


@pytest.mark.parametrize('path', [ORIGINAL, VENDOR])
@pytest.mark.parametrize('fault', ['missing', 'syntax', 'blob'])
def test_sources_and_runtime_must_be_readable_and_pinned(monkeypatch, path, fault):
    m = local(monkeypatch)
    if path == VENDOR and fault == 'blob':
        # An executable extra statement, not an irrelevant source comment.
        mutation = '\nsource = None\n'
    else:
        mutation = '\n# source drift\n'
    def change(text):
        if fault == 'missing':
            raise FileNotFoundError('gone')
        return 'def syntax error' if fault == 'syntax' else text + mutation
    intercept(monkeypatch, path, change)
    r = m.audit_outbox_journal_source(SOURCE)
    assert not r['source_subset_verified'] and r['blockers']


@pytest.mark.parametrize('fault', ['signature', 'decorator', 'order', 'duplicate', 'missing', 'count', 'born', 'late'])
def test_independent_source_projection_preconditions(fault):
    m = api()
    tree = ast.parse(ORIGINAL.read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'enqueue')
    if fault == 'signature':
        fn.args.args[0].arg = 'wrong'
    elif fault == 'decorator':
        lock = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_append_lock')
        lock.decorator_list = []
    elif fault == 'order':
        tree.body.remove(fn)
        tree.body.append(fn)
    elif fault == 'duplicate':
        tree.body.append(fn)
    elif fault == 'missing':
        tree.body.remove(fn)
    elif fault == 'count':
        fn.body.append(ast.parse('time.time()').body[0])
    elif fault == 'born':
        born = next(n for n in tree.body if isinstance(n, ast.AnnAssign) and ast.unparse(n.target) == '_BORN')
        born.value = ast.parse("{'shared': 1}", mode='eval').body
    else:
        late = next(n for n in tree.body if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == 'LATE_AFTER_S')
        late.value = ast.Constant(601)
    with pytest.raises(ValueError):
        m._projection(ast.unparse(tree))


@pytest.mark.parametrize('fault', ['head', 'root', 'baseline'])
def test_independent_source_authority(monkeypatch, fault):
    m = local(monkeypatch)
    if fault == 'baseline':
        intercept(monkeypatch, ROOT / 'configs/trees/existing-alerts-baseline.json',
                  lambda s: s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9', '0' * 40))
        expected = 'BASELINE_COMMIT_MISMATCH'
    else:
        arg, value, expected = ('HEAD', '0' * 40, 'SOURCE_COMMIT_MISMATCH') if fault == 'head' else ('--show-toplevel', str(SOURCE), 'NOT_REPOSITORY_ROOT')
        original = m._git
        monkeypatch.setattr(m, '_git', lambda p, *a: value if a == (arg,) else original(p, *a))
    r = m.audit_outbox_journal_source(SOURCE)
    assert not r['source_subset_verified'] and expected in r['blockers']


@pytest.mark.parametrize('fault', ['false_empty', 'true_blocked', 'error', 'missing_pin'])
def test_dependency_failure_cannot_certify(monkeypatch, fault):
    m = api()
    def audit(root):
        assert root == SOURCE
        if fault == 'error':
            raise OSError('missing graph')
        if fault == 'missing_pin':
            raise StopIteration('missing pin')
        return {'source_subset_verified': fault == 'true_blocked',
                'blockers': ['drift'] if fault == 'true_blocked' else []}
    monkeypatch.setattr(m, 'audit_lifecycle_identity_source', audit)
    r = m.audit_outbox_journal_source(SOURCE)
    assert not r['source_subset_verified']
    assert any(b.startswith('DEPENDENCY:lifecycle_identity:') for b in r['blockers'])
    assert not r['ready_for_replay'] and not r['ready_for_training']


def test_actual_inherited_identity_drift(monkeypatch):
    m = api()
    path = ROOT / 'trading_system/tree_replay/_vendor/lifecycle_identity.py'
    assert '> 0.011:' in path.read_text(encoding='utf-8')
    intercept(monkeypatch, path, lambda s: s.replace('> 0.011:', '> 0.02:'))
    r = m.audit_outbox_journal_source(SOURCE)
    assert not r['source_subset_verified']
    assert 'DEPENDENCY:lifecycle_identity:VENDOR_AST_MISMATCH:lifecycle_identity' in r['blockers']


def test_actual_missing_pin_cli_is_json_blocked(monkeypatch, capsys):
    api()
    def change(text):
        doc = json.loads(text)
        doc['repositories'] = [r for r in doc['repositories'] if r['name'] != 'chart-desk']
        return json.dumps(doc)
    intercept(monkeypatch, ROOT / 'configs/trees/existing-alerts-baseline.json', change)
    cli = importlib.import_module('tools.check_outbox_journal_source_parity')
    monkeypatch.setattr(sys, 'argv', ['check_outbox_journal_source_parity.py', '--source-root', str(SOURCE)])
    assert cli.main() == 2
    r = json.loads(capsys.readouterr().out)
    assert 'BASELINE_COMMIT_MISMATCH' in r['blockers']
    assert 'DEPENDENCY:lifecycle_identity:BASELINE_COMMIT_MISMATCH' in r['blockers']


def test_explicit_root_cli_unrelated_cwd_and_inert_import_guard(tmp_path):
    assert not api().audit_outbox_journal_source(None)['source_subset_verified']
    for root, code in [(SOURCE, 0), (tmp_path, 2)]:
        p = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/check_outbox_journal_source_parity.py'),
                            '--source-root', str(root)], cwd=tmp_path, capture_output=True, text=True, timeout=90)
        assert p.returncode == code and not p.stderr, p.stderr
        r = json.loads(p.stdout)
        assert r['source_subset_verified'] is (code == 0)
        assert not r['ready_for_replay'] and not r['ready_for_training']
    guard = '\n'.join(['import sys', 'class Guard:', '    def find_spec(self,fullname,*a):',
        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')): raise AssertionError(fullname)",
        'sys.meta_path.insert(0,Guard())',
        'from trading_system.tree_spec.outbox_journal_source import audit_outbox_journal_source',
        "assert audit_outbox_journal_source(sys.argv[1])['source_subset_verified']"])
    p = subprocess.run([sys.executable, '-B', '-c', guard, str(SOURCE)], cwd=ROOT, capture_output=True, text=True, timeout=90)
    assert p.returncode == 0 and not p.stderr, p.stderr
