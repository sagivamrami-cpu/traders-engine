"""Inert source proof for the lifecycle gate, parked claims and retry policy."""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
COMMIT = '68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
BLOB = 'b616b34022e436545d8c1daf85eced51614fd74e'
VENDOR = 'trading_system/tree_replay/_vendor/lifecycle_gate.py'
SYMBOLS = ('_persist_gated_lifecycle', 'gate', 'PARK', 'PARK_MAX_AGE_S',
           '_park_key', '_park', '_unpark_text', 'replay_parked',
           '_park_lost', '_atomic_json')
SIGNATURES = (
    'def _persist_gated_lifecycle(msgs: list, state: dict) -> list: pass',
    'def gate(msgs: list, state: dict | None = None) -> tuple[list, list]: pass',
    'def _park_key(tr: dict, text: str) -> str: pass',
    'def _park(tr: dict, text: str) -> None: pass',
    'def _unpark_text(text: str) -> None: pass',
    'def replay_parked(state: dict | None = None) -> list: pass',
    'def _park_lost(rec: dict, why: str) -> None: pass',
    'def _atomic_json(path, obj) -> None: pass',
)
PREFIX = '''from __future__ import annotations
import json
import sys
from pathlib import PurePosixPath
from .claim_verifier import ClaimVerifier
from .lifecycle_identity import _match_trade_for_text
from .outbox_journal import OutboxJournal
PARK = PurePosixPath('chart-desk/out/parked_claims.json')
PARK_MAX_AGE_S = 3600.0'''
INPUT_ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError,
                SyntaxError, subprocess.SubprocessError)
CHILD_AUDITS = {
    'claim_verifier': ('trading_system.tree_spec.claim_verifier_source', 'audit_claim_verifier_source'),
    'outbox_journal': ('trading_system.tree_spec.outbox_journal_source', 'audit_outbox_journal_source'),
    'lifecycle_identity': ('trading_system.tree_spec.lifecycle_identity_source', 'audit_lifecycle_identity_source'),
}


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _git(path, arg):
    return subprocess.run(['git', '-C', str(path), 'rev-parse', arg], check=True,
                          text=True, capture_output=True).stdout.strip()


def _signature(node, expected):
    def ret(value):
        return None if value is None else _dump(value)
    if (not isinstance(node, ast.FunctionDef) or node.name != expected.name
            or _dump(node.args) != _dump(expected.args) or ret(node.returns) != ret(expected.returns)):
        raise ValueError(f'SOURCE_SIGNATURE_MISMATCH:{expected.name}')


def _child_audit(name, source_root):
    module_name, function_name = CHILD_AUDITS[name]
    module = importlib.import_module(module_name)
    audit = getattr(module, function_name)
    return audit(source_root)


def _name(node):
    if isinstance(node, ast.FunctionDef):
        return node.name
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        target = node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else getattr(node, 'target', None)
        return target.id if isinstance(target, ast.Name) else None
    return None


def _replace(tree, old, new, *, count=1, statement=False):
    before = ast.parse(old).body[0] if statement else ast.parse(old, mode='eval').body
    after = None if new is None else (ast.parse(new).body[0] if statement else ast.parse(new, mode='eval').body)

    class Replace(ast.NodeTransformer):
        seen = 0
        def visit(self, node):
            if _dump(node) == _dump(before):
                self.seen += 1
                return copy.deepcopy(after)
            return super().visit(node)

    visitor = Replace()
    result = visitor.visit(tree)
    if visitor.seen != count:
        raise ValueError(f'SUBSTITUTION_PRECONDITION:{old}:count={visitor.seen}:expected={count}')
    return result


class _RemoveDocs(ast.NodeTransformer):
    def _body(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:]
        return node
    visit_Module = _body
    visit_FunctionDef = _body
    visit_ClassDef = _body


def _without_docs(tree):
    return _RemoveDocs().visit(copy.deepcopy(tree))


def _projection(text):
    selected = [node for node in ast.parse(text).body if _name(node) in SYMBOLS]
    if tuple(_name(node) for node in selected) != SYMBOLS:
        raise ValueError('SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH')
    nodes = {_name(node): copy.deepcopy(node) for node in selected}
    if _dump(nodes['PARK_MAX_AGE_S']) != _dump(ast.parse('PARK_MAX_AGE_S = 3600.0').body[0]):
        raise ValueError('SOURCE_INITIALIZER_MISMATCH:PARK_MAX_AGE_S')
    for signature in map(lambda s: ast.parse(s).body[0], SIGNATURES):
        node = nodes[signature.name]
        if (not isinstance(node, ast.FunctionDef)
                or [_dump(row) for row in node.decorator_list] != [_dump(row) for row in signature.decorator_list]):
            raise ValueError(f'SOURCE_DECORATOR_MISMATCH:{signature.name}')
        _signature(node, signature)
    nodes['PARK'] = ast.parse("PARK = PurePosixPath('chart-desk/out/parked_claims.json')").body[0]
    statements = {
        '_persist_gated_lifecycle': ('from . import outbox', 'from .trade_threads import context'),
        'gate': ('from . import verify',),
        'replay_parked': ('from . import outbox, verify',),
        '_park_lost': ('from . import outbox',),
        '_atomic_json': ('import os', 'import tempfile'),
    }
    for name, rows in statements.items():
        for row in rows:
            nodes[name] = _replace(nodes[name], row, None, statement=True)
    edits = {
        '_persist_gated_lifecycle': (
            ('gate(msgs, state=state)', 'self.gate(msgs, state=state)', 1),
            ('outbox.enqueue(text, to_group, trade_context=context(text, state))', 'self.outbox.enqueue(text, to_group, trade_context=self.threads.context(text, state))', 1),
            ("outbox.enqueue(text, False, kind='blocked_lifecycle')", "self.outbox.enqueue(text, False, kind='blocked_lifecycle')", 1),
            ("outbox.resolve(eid, f'blocked by gate: {why}')", "self.outbox.resolve(eid, f'blocked by gate: {why}')", 1),
        ),
        'gate': (
            ('_load()', 'self.source.load()', 1),
            ('_group_has(t)', 'self.threads._group_has(t)', 1),
            ('_group_has(tr)', 'self.threads._group_has(tr)', 1),
            ('_unpark_text(text)', 'self._unpark_text(text)', 4),
            ('verify.target(tr, float(tr[\'targets\'][0][1]))', "self.verifier.target(tr, float(tr['targets'][0][1]))", 1),
            ('verify.check_message(text, tr)', 'self.verifier.check_message(text, tr)', 1),
            ('_park(tr, text)', 'self._park(tr, text)', 2),
        ),
        '_park': (
            ("PARK.read_text(encoding='utf-8')", "self.source.park_text(encoding='utf-8')", 1),
            ('PARK.exists()', 'self.source.park_exists()', 1),
            ('_park_key(tr, text)', 'self._park_key(tr, text)', 1),
            ('time.time()', 'self.source.now_epoch()', 1),
            ('_atomic_json(PARK, d)', 'self._atomic_json(PARK, d)', 1),
        ),
        '_unpark_text': (
            ('PARK.exists()', 'self.source.park_exists()', 1),
            ("PARK.read_text(encoding='utf-8')", "self.source.park_text(encoding='utf-8')", 1),
            ('_atomic_json(PARK, keep)', 'self._atomic_json(PARK, keep)', 1),
        ),
        'replay_parked': (
            ('PARK.exists()', 'self.source.park_exists()', 1),
            ("PARK.read_text(encoding='utf-8')", "self.source.park_text(encoding='utf-8')", 1),
            ('_load()', 'self.source.load()', 1),
            ('time.time()', 'self.source.now_epoch()', 1),
            ('_park_lost(rec, "הטייפ לא הכריע תוך שעה")', "self._park_lost(rec, 'הטייפ לא הכריע תוך שעה')", 1),
            ("verify.check_message(rec['text'], dict(tr, claim_ts=float(rec.get('ts') or 0)))", "self.verifier.check_message(rec['text'], dict(tr, claim_ts=float(rec.get('ts') or 0)))", 1),
            ("outbox.remember_born(rec['text'], float(rec.get('ts') or now))", "self.outbox.remember_born(rec['text'], float(rec.get('ts') or now))", 1),
            ("_park_lost(rec, f'הטייפ סותר אותה: {v.reason}')", "self._park_lost(rec, f'הטייפ סותר אותה: {v.reason}')", 1),
            ('_atomic_json(PARK, keep)', 'self._atomic_json(PARK, keep)', 1),
        ),
        '_park_lost': (
            ('_il_clock(rec.get(\'ts\') or time.time())', "self.source.format_il_clock(rec.get('ts') or self.source.now_epoch())", 1),
            ("outbox.enqueue(note, False, kind='park_lost')", "self.outbox.enqueue(note, False, kind='park_lost')", 1),
        ),
        '_atomic_json': (
            ('path.parent.mkdir(parents=True, exist_ok=True)', 'self.source.atomic_mkdir(path.parent.as_posix(), parents=True, exist_ok=True)', 1),
            ("tempfile.mkstemp(dir=str(path.parent), suffix='.tmp')", "self.source.atomic_mkstemp(path.parent.as_posix(), suffix='.tmp')", 1),
            ("os.fdopen(fd, 'w', encoding='utf-8')", "self.source.atomic_fdopen(fd, 'w', encoding='utf-8')", 1),
            ('os.fsync(fh.fileno())', 'self.source.atomic_fsync(fh)', 1),
            ('os.replace(tmp, path)', 'self.source.atomic_replace(tmp, path.as_posix())', 1),
            ('os.unlink(tmp)', 'self.source.atomic_unlink(tmp)', 1),
        ),
    }
    for name, rows in edits.items():
        for old, new, count in rows:
            nodes[name] = _replace(nodes[name], old, new, count=count)
    cls = ast.parse('''class LifecycleGate:
    def __init__(self, source):
        self.source = source
        self.verifier = ClaimVerifier(source)
        self.outbox = OutboxJournal(source)
        self.threads = self.outbox.threads
''').body[0]
    for signature in map(lambda s: ast.parse(s).body[0], SIGNATURES):
        method = nodes[signature.name]
        method.args.args.insert(0, ast.arg(arg='self'))
        cls.body.append(method)
    return ast.Module(body=ast.parse(PREFIX).body + [cls], type_ignores=[])


def audit_lifecycle_gate_park_source(source_root):
    """Inspect retained source and actual child audits without executing either."""
    blockers, checked, dependencies = [], [], {}
    report = lambda: {'status': 'BLOCKED' if blockers else 'VERIFIED',
                      'source_subset_verified': not blockers, 'blockers': blockers,
                      'checked_projections': checked, 'dependencies': dependencies,
                      'source_commits': {'chart-desk': COMMIT},
                      'ready_for_replay': False, 'ready_for_training': False}
    try:
        source_root = Path(source_root)
        baseline = _read_json(ROOT / 'configs/trees/existing-alerts-baseline.json')
        if [r.get('commit') for r in baseline['repositories'] if r.get('name') == 'chart-desk'] != [COMMIT]:
            blockers.append('BASELINE_COMMIT_MISMATCH')
        repo = source_root / 'chart-desk'
        if Path(_git(repo, '--show-toplevel')).resolve() != repo.resolve():
            blockers.append('NOT_REPOSITORY_ROOT')
        if _git(repo, 'HEAD') != COMMIT:
            blockers.append('SOURCE_COMMIT_MISMATCH')
    except INPUT_ERRORS as exc:
        blockers.append(f'SOURCE_IDENTITY_UNREADABLE:{type(exc).__name__}')
        return report()
    try:
        text = (repo / 'chartdesk/tracker.py').read_text(encoding='utf-8')
        data = text.encode('utf-8')
        if hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest() != BLOB:
            blockers.append('SOURCE_BLOB_MISMATCH:tracker.py')
        expected = _projection(text)
        actual = ast.parse((ROOT / VENDOR).read_text(encoding='utf-8'))
        if _dump(_without_docs(actual)) == _dump(_without_docs(expected)):
            checked.append('lifecycle_gate')
        else:
            blockers.append('VENDOR_AST_MISMATCH:lifecycle_gate')
    except INPUT_ERRORS as exc:
        blockers.append(f'SOURCE_PROJECTION_UNREADABLE:lifecycle_gate:{type(exc).__name__}:{exc}')
    for name in CHILD_AUDITS:
        try:
            child = _child_audit(name, source_root)
            if (not isinstance(child, dict)
                    or type(child.get('source_subset_verified')) is not bool
                    or not isinstance(child.get('blockers'), list)
                    or not all(isinstance(row, str) for row in child['blockers'])):
                raise TypeError('CHILD_REPORT_SHAPE')
            dependencies[name] = child
            blockers.extend(f'DEPENDENCY:{name}:{row}' for row in child['blockers'])
            if not child['source_subset_verified'] and not child['blockers']:
                blockers.append(f'DEPENDENCY:{name}:NOT_VERIFIED')
        except Exception as exc:
            blockers.append(f'DEPENDENCY:{name}:UNREADABLE:{type(exc).__name__}')
    return report()
