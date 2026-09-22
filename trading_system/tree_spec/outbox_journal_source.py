"""Inert complete source projection for the private offline journal kernel."""
from __future__ import annotations

import ast
import copy
import hashlib
from pathlib import Path

from .lifecycle_identity_source import (
    ERRORS, _signature, audit_lifecycle_identity_source,
)
from .tracker_admission_source import _dump, _git, _read_json, _replace_exact

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
BLOB = '1cf608f81e30c82ddd83b211a0ca743133699e45'
VENDOR = 'trading_system/tree_replay/_vendor/outbox_journal.py'
SIGNATURES = (
    'def _eid(text: str, ts: float) -> str: pass',
    'def _rows() -> list: pass',
    'def _append_lock_path() -> Path: pass',
    '@contextmanager\ndef _append_lock(): pass',
    'def _write(row: dict) -> None: pass',
    'def _append(row: dict) -> None: pass',
    'def _merge(rows: list) -> dict: pass',
    'def _last_states() -> dict: pass',
    'def remember_born(text: str, ts: float) -> None: pass',
    "def enqueue(text: str, to_group: bool, kind: str='lifecycle', *, trade_context=None) -> str: pass",
    'def _mark(eid: str, state: str, **extra) -> None: pass',
    'def pending() -> list: pass',
    'def resolve(eid: str, why: str) -> None: pass',
    'def resolve_text(text: str, why: str) -> int: pass',
)
SYMBOLS = ('LATE_AFTER_S', '_eid', '_rows', '_append_lock_path', '_append_lock',
           '_write', '_append', '_merge', '_last_states', '_BORN', 'remember_born',
           'enqueue', '_mark', 'pending', 'resolve', 'resolve_text')
PREFIX = '''from __future__ import annotations
import hashlib
import json
from contextlib import contextmanager
import sys
from pathlib import Path, PurePosixPath
from .lifecycle_identity import LifecycleIdentity, identity
STORE = PurePosixPath('chart-desk/out/outbox.jsonl')'''
EXPRESSIONS = {
    '_rows': (
        ('STORE.exists()', 'self.source.journal_exists()'),
        ("STORE.read_text(encoding='utf-8')", "self.source.journal_text(encoding='utf-8')"),
    ),
    '_append_lock': (
        ('STORE.parent.mkdir(parents=True, exist_ok=True)', 'self.source.mkdir(STORE.parent.as_posix(), parents=True, exist_ok=True)'),
        ("open(_append_lock_path(), 'a+')", "self.source.open_append_lock(_append_lock_path().as_posix(), 'a+')"),
        ('filelock.try_acquire(lk, timeout=None)', 'self.source.try_acquire(lk, timeout=None)'),
        ('filelock.release(lk)', 'self.source.release(lk)'),
    ),
    '_write': (
        ('_refuse_live_store_from_tests()', 'self.source.assert_offline()'),
        ('STORE.parent.mkdir(parents=True, exist_ok=True)', 'self.source.mkdir(STORE.parent.as_posix(), parents=True, exist_ok=True)'),
        ("STORE.open('a', encoding='utf-8')", "self.source.open_journal('a', encoding='utf-8')"),
    ),
    '_append': (('_append_lock()', 'self._append_lock()'), ('_write(row)', 'self._write(row)')),
    '_last_states': (('_rows()', 'self._rows()'),),
    'remember_born': (('_BORN', 'self._BORN'),),
    'enqueue': (
        ('time.time()', 'self.source.now_epoch()'),
        ('trade_threads.identity(text)', 'identity(text)'),
        ('trade_threads.context(text)', 'self.threads.context(text)'),
        ('_BORN', 'self._BORN'),
        ('_append_lock()', 'self._append_lock()'),
        ('_last_states()', 'self._last_states()'),
        ("_write({'id': eid, 'ts': ts, 'state': 'PENDING', 'to_group': True})",
         "self._write({'id': eid, 'ts': ts, 'state': 'PENDING', 'to_group': True})"),
        ("_write({'id': old_id, 'ts': ts, 'state': 'PENDING', 'to_group': True})",
         "self._write({'id': old_id, 'ts': ts, 'state': 'PENDING', 'to_group': True})"),
        ('_write(row)', 'self._write(row)'),
    ),
    '_mark': (('time.time()', 'self.source.now_epoch()'), ('_append(row)', 'self._append(row)')),
    'pending': (('_last_states()', 'self._last_states()'),),
    'resolve': (("_mark(eid, 'RESOLVED', why=why)", "self._mark(eid, 'RESOLVED', why=why)"),),
    'resolve_text': (('pending()', 'self.pending()'), ("resolve(ev['id'], why)", "self.resolve(ev['id'], why)")),
}


def _name(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None


def _projection(text):
    selected = [n for n in ast.parse(text).body if _name(n) in SYMBOLS]
    if tuple(_name(n) for n in selected) != SYMBOLS:
        raise ValueError('SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH')
    nodes = {_name(n): n for n in selected}
    for literal in ('LATE_AFTER_S = 10 * 60', '_BORN: dict[str, float] = {}'):
        expected = ast.parse(literal).body[0]
        if _dump(nodes[_name(expected)]) != _dump(expected):
            raise ValueError(f'SOURCE_INITIALIZER_MISMATCH:{_name(expected)}')
    signatures = [ast.parse(s).body[0] for s in SIGNATURES]
    for expected in signatures:
        node = copy.deepcopy(nodes[expected.name])
        if not isinstance(node, ast.FunctionDef) or (
                [_dump(d) for d in node.decorator_list] != [_dump(d) for d in expected.decorator_list]):
            raise ValueError(f'SOURCE_DECORATOR_MISMATCH:{expected.name}')
        node.decorator_list = []  # validated above; shared signature check disallows decorators
        _signature(node, expected)
    for name, statement in (('_append_lock', 'from . import filelock'),
                            ('enqueue', 'from . import trade_threads')):
        nodes[name] = _replace_exact(nodes[name], statement, None, statement=True)
    for name, pairs in EXPRESSIONS.items():
        for old, new in pairs:
            nodes[name] = _replace_exact(nodes[name], old, new)
    cls = ast.parse('''class OutboxJournal:
    def __init__(self, source):
        self.source = source
        self.threads = LifecycleIdentity(source)
        self._BORN = {}
''').body[0]
    pure = ('_eid', '_append_lock_path', '_merge')
    for signature in signatures:
        if signature.name not in pure:
            method = nodes[signature.name]
            method.args.args.insert(0, ast.arg(arg='self'))
            cls.body.append(method)
    return ast.Module(body=ast.parse(PREFIX).body + [nodes['LATE_AFTER_S']]
                      + [nodes[n] for n in pure] + [cls], type_ignores=[])


def audit_outbox_journal_source(source_root):
    """Inspect a retained checkout and actual dependencies; never execute either."""
    blockers, checked, dependencies = [], [], {}

    def result():
        return {'status': 'BLOCKED' if blockers else 'VERIFIED',
                'source_subset_verified': not blockers, 'blockers': blockers,
                'checked_projections': checked, 'dependencies': dependencies,
                'source_commits': {'chart-desk': COMMIT},
                'ready_for_replay': False, 'ready_for_training': False}

    try:
        source_root = Path(source_root)
    except ERRORS as exc:
        blockers.append(f'SOURCE_ROOT_INVALID:{type(exc).__name__}')
        return result()
    try:
        baseline = _read_json(ROOT / 'configs/trees/existing-alerts-baseline.json')
        pins = [r.get('commit') for r in baseline['repositories'] if r.get('name') == 'chart-desk']
        if pins != [COMMIT]:
            blockers.append('BASELINE_COMMIT_MISMATCH')
    except ERRORS as exc:
        blockers.append(f'BASELINE_UNREADABLE:{type(exc).__name__}')
    repo = source_root / 'chart-desk'
    try:
        if Path(_git(repo, '--show-toplevel')).resolve() != repo.resolve():
            blockers.append('NOT_REPOSITORY_ROOT')
        if _git(repo, 'HEAD') != COMMIT:
            blockers.append('SOURCE_COMMIT_MISMATCH')
    except ERRORS as exc:
        blockers.append(f'SOURCE_IDENTITY_UNREADABLE:{type(exc).__name__}')
    try:
        text = (repo / 'chartdesk/outbox.py').read_text(encoding='utf-8')
        data = text.encode('utf-8')  # read_text normalizes checkout CRLF to Git LF
        digest = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
        if digest != BLOB:
            blockers.append('SOURCE_BLOB_MISMATCH:outbox.py')
        expected = _projection(text)
    except ERRORS as exc:
        blockers.append(f'SOURCE_UNREADABLE:outbox.py:{type(exc).__name__}:{exc}')
    else:
        try:
            actual = ast.parse((ROOT / VENDOR).read_text(encoding='utf-8'))
            if _dump(actual) == _dump(expected):
                checked.append('outbox_journal')
            else:
                blockers.append('VENDOR_AST_MISMATCH:outbox_journal')
        except ERRORS as exc:
            blockers.append(f'VENDOR_UNREADABLE:outbox_journal:{type(exc).__name__}')
    try:
        child = audit_lifecycle_identity_source(source_root)
        dependencies['lifecycle_identity'] = child
        blockers.extend(f'DEPENDENCY:lifecycle_identity:{b}' for b in child['blockers'])
        if not child['source_subset_verified'] and not child['blockers']:
            blockers.append('DEPENDENCY:lifecycle_identity:NOT_VERIFIED')
    except ERRORS as exc:
        blockers.append(f'DEPENDENCY:lifecycle_identity:UNREADABLE:{type(exc).__name__}')
    return result()
