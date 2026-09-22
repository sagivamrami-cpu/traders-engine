"""Inert proof of the raw matrix/tree -> original pending-check binding."""
import ast
import hashlib
from pathlib import Path

from .tree_walk_source import audit_tree_walk_source
from .tracker_admission_source import INPUT_ERRORS, _dump, _git, _read_json, _replace_exact

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
BLOB = '28641487567c457b6922c2a63055659867bb4248'
SOURCE_IMPORTS = '''from __future__ import annotations
import sys
from dataclasses import dataclass
from pathlib import Path
from . import basis, toolkit, tr'''
SIGNATURES = '''def read_tf(symbol: str, tf: str) -> TFView: pass
def read_symbol(symbol: str, tfs: tuple[str, ...] = ('4h', '1h', '15m', '5m')) -> dict[str, TFView]: pass'''
MATRIX_IMPORTS = '''from __future__ import annotations
from . import admission_matrix as matrix
from .admission_matrix import TFView'''
MATRIX_CONSTRUCTOR = '''class MatrixReader:
    def __init__(self, source):
        self.source = source'''
SOURCE_VIEW = '''TFView(tf=tf, close=float(df["close"].iloc[-1]),
    reads=[fn(df) for fn in TOOLS.values()], basis_note=note,
    atr=_atr(df), bar_ts=_bar_ts(df))'''
# Literal binding authority, not derived from the candidate or its AST.
FACADE = '''from ._vendor.basis_operation import BasisOperation
from ._vendor.matrix_reader import MatrixReader
from ._vendor.revalidation import Revalidation
from ._vendor.tree_walk import TreeReader

class TreeRevalidation(BasisOperation):
    def __init__(self, source):
        super().__init__(source)
        self.matrix = MatrixReader(source)
        self.tree = TreeReader(source)
        self.checks = Revalidation(self)
    def read_symbol(self, symbol, tfs=('4h', '1h', '15m', '5m')):
        return self.matrix.read_symbol(symbol, tfs=tfs)
    def tree_walk(self, symbol):
        return self.tree.walk(symbol)
    def still_valid(self, t):
        return self.checks.still_valid(t)
    def revalidate_pending(self, t, *, now=None):
        return self.checks.revalidate_pending(t, now=now)
    def now_epoch(self):
        return self.source.now_epoch()
    def now_timestamp(self, *, tz):
        return self.source.now_timestamp(tz=tz)
    def deep_exists(self, key):
        return self.source.deep_exists(key)
    def deep_bytes(self, key):
        return self.source.deep_bytes(key)
    def calendar_exists(self, path):
        return self.source.calendar_exists(path)
    def calendar_text(self, path):
        return self.source.calendar_text(path)
    def ensure_shadow_parent(self, *, parents, exist_ok):
        return self.source.ensure_shadow_parent(parents=parents, exist_ok=exist_ok)
    def shadow_open(self, mode, encoding):
        return self.source.shadow_open(mode, encoding)
'''


def _projection(text):
    """Project both complete source functions using exact-count AST substitutions."""
    tree = ast.parse(text)
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    if [_dump(n) for n in imports] != [_dump(n) for n in ast.parse(SOURCE_IMPORTS).body]:
        raise ValueError('SOURCE_IMPORT_MISMATCH')
    signatures = ast.parse(SIGNATURES).body
    names = [n.name for n in signatures]
    selected = [n for n in tree.body if getattr(n, 'name', None) in names]
    if [n.name for n in selected] != names:
        raise ValueError('SOURCE_METHOD_ORDER_OR_INVENTORY')
    cls = ast.parse(MATRIX_CONSTRUCTOR).body[0]
    for node, sig in zip(selected, signatures):
        if not isinstance(node, ast.FunctionDef) or node.decorator_list or (
                _dump(node.args) != _dump(sig.args) or node.returns is None or
                _dump(node.returns) != _dump(sig.returns)):
            raise ValueError('SOURCE_SIGNATURE_MISMATCH:' + node.name)
        node.args.args.insert(0, ast.arg(arg='self'))
        if node.name == 'read_tf':
            _replace_exact(node, 'basis.fetch_corrected(symbol, tf, LOOKBACK[tf])',
                           'self.source.fetch_corrected(symbol, tf, matrix.LOOKBACK[tf])')
            _replace_exact(node, SOURCE_VIEW, 'matrix.read_frame(df, tf, note)')
        else:
            _replace_exact(node, 'read_tf(symbol, tf)', 'self.read_tf(symbol, tf)')
        cls.body.append(node)
    return ast.parse(MATRIX_IMPORTS).body + [cls]


def _facade_body(text):
    # Only documentation at module/class scope is non-executable. Preserve
    # imports, inheritance, methods, signatures and all executable body order.
    tree = ast.parse(text)
    for node in [tree] + [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        if ast.get_docstring(node) is not None:
            node.body.pop(0)
    return tree.body


def audit_tree_revalidation_source(source_root):
    """Certify source/binding identity, never historical replay or model readiness."""
    blockers, checked, dependencies = [], [], {}
    report = dict(status='BLOCKED', source_subset_verified=False, blockers=blockers,
        checked_projections=checked, dependencies=dependencies,
        source_commits={'chart-desk': COMMIT}, ready_for_replay=False, ready_for_training=False)
    try:
        parent = Path(source_root)
        root = parent / 'chart-desk'
    except INPUT_ERRORS as exc:
        blockers.append('SOURCE_ROOT_INVALID:' + type(exc).__name__)
        return report
    try:
        if Path(_git(root, '--show-toplevel')).resolve() != root.resolve():
            blockers.append('NOT_REPOSITORY_ROOT')
        if _git(root, 'HEAD') != COMMIT:
            blockers.append('SOURCE_COMMIT_MISMATCH')
        baseline = _read_json(ROOT / 'configs/trees/existing-alerts-baseline.json')
        if [r.get('commit') for r in baseline['repositories'] if r.get('name') == 'chart-desk'] != [COMMIT]:
            blockers.append('BASELINE_COMMIT_MISMATCH')
    except INPUT_ERRORS as exc:
        blockers.append('SOURCE_IDENTITY_UNREADABLE:' + type(exc).__name__)
    projections = {'tree_revalidation': ast.parse(FACADE).body}
    try:
        text = (root / 'chartdesk/matrix.py').read_text(encoding='utf-8')
        raw = text.encode('utf-8')
        if hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() != BLOB:
            blockers.append('SOURCE_BLOB_MISMATCH:matrix')
        projections = {'matrix_reader': _projection(text), **projections}
    except INPUT_ERRORS as exc:
        blockers.append('SOURCE_PROJECTION_UNREADABLE:' + type(exc).__name__ + ':' + str(exc))
    for name, expected in projections.items():
        file = '_vendor/matrix_reader.py' if name == 'matrix_reader' else 'tree_revalidation.py'
        try:
            text = (ROOT / 'trading_system/tree_replay' / file).read_text(encoding='utf-8')
            actual = ast.parse(text).body if name == 'matrix_reader' else _facade_body(text)
            if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
                blockers.append('VENDOR_AST_MISMATCH:' + name)
            else:
                checked.append(name)
        except INPUT_ERRORS as exc:
            blockers.append('VENDOR_UNREADABLE:' + name + ':' + type(exc).__name__)
    try:
        child = audit_tree_walk_source(parent)
        dependencies['tree_walk'] = child
        blockers.extend('DEPENDENCY:tree_walk:' + b for b in child['blockers'])
        if child['source_subset_verified'] is not True and not child['blockers']:
            blockers.append('DEPENDENCY:tree_walk:NOT_VERIFIED')
    except INPUT_ERRORS + (StopIteration,) as exc:
        blockers.append('DEPENDENCY:tree_walk:UNREADABLE:' + type(exc).__name__)
    if not blockers:
        report.update(status='VERIFIED', source_subset_verified=True)
    return report
