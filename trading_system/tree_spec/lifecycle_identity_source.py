"""Inert, independently pinned proof of lifecycle identity and receipt reads.

Only source syntax trees are read/transformed. No original or replay runtime
module is imported, compiled or executed by this auditor.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from .tracker_admission_source import (
    INPUT_ERRORS, _dump, _git, _read_json, _replace_exact,
    audit_tracker_admission_source,
)

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
BLOBS = {
    'chartdesk/tracker.py': 'b616b34022e436545d8c1daf85eced51614fd74e',
    'chartdesk/trade_threads.py': 'b05cfcf45cb420c40254154e80d3792a7b1685b9',
}
VENDOR = 'trading_system/tree_replay/_vendor/lifecycle_identity.py'
ERRORS = INPUT_ERRORS + (StopIteration,)
SIGNATURES = (
    'def _fmt(sym: str) -> str: pass',
    'def _side_from_text(text: str) -> str | None: pass',
    'def _prices_in_text(text: str) -> list[float]: pass',
    'def _text_has_price(text: str, price: float, tol: float=0.02) -> bool: pass',
    'def _trade_has_named_level_in_text(trade: dict, text: str) -> bool: pass',
    'def _match_trade_for_text(text: str, state: dict) -> tuple[dict | None, list[dict]]: pass',
    'def _receipt_from_queue_file(r: dict) -> dict: pass',
    'def _group_has(t: dict) -> bool: pass',
)
THREAD_SIGNATURES = ('def identity(text): pass', 'def context(text, state=None): pass')
IMPORTS = '''from __future__ import annotations
import json
import re
import pandas as pd
from pathlib import PurePosixPath
from . import basis_symbols as basis
from .tracker_admission import _trade_identity'''
EXPRESSIONS = {
    '_receipt_from_queue_file': (
        ('ROOT', "PurePosixPath('chart-desk')"),
        ('f.exists()', 'self.source.queue_exists(f.as_posix())'),
        ("f.read_text(encoding='utf-8')", "self.source.queue_text(f.as_posix(), encoding='utf-8')"),
    ),
    '_group_has': (
        ('_RECEIPTS.stat()', 'self.source.receipt_stat()'),
        ("_RECEIPTS.read_text(encoding='utf-8')", "self.source.receipt_text(encoding='utf-8')"),
        ('_receipt_from_queue_file(r)', 'self._receipt_from_queue_file(r)'),
    ),
    'context': (
        ('tracker._load()', 'self.source.load()'),
        ('tracker._match_trade_for_text(text, state)', '_match_trade_for_text(text, state)'),
        ('time.time()', 'self.source.now_epoch()'),
    ),
}


def _signature(node, expected):
    """Full arguments/annotations/defaults/decorators, including absent returns."""
    def returns(n):
        return None if n.returns is None else _dump(n.returns)
    if (not isinstance(node, ast.FunctionDef) or node.name != expected.name
            or _dump(node.args) != _dump(expected.args)
            or returns(node) != returns(expected) or node.decorator_list
            or node.type_comment or getattr(node, 'type_params', [])):
        raise ValueError(f'SOURCE_SIGNATURE_MISMATCH:{expected.name}')


def _projection(tracker_text, threads_text):
    signatures = [ast.parse(s).body[0] for s in SIGNATURES]
    names = [n.name for n in signatures]
    nodes = [n for n in ast.parse(tracker_text).body if getattr(n, 'name', None) in names]
    if [n.name for n in nodes] != names:
        raise ValueError('SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH:tracker')
    for node, signature in zip(nodes, signatures):
        _signature(node, signature)

    threads = ast.parse(threads_text)
    body = threads.body[1:] if ast.get_docstring(threads) is not None else threads.body
    imports = ast.parse('import re\nimport time').body
    if len(body) != 5 or [_dump(n) for n in body[:2]] != [_dump(n) for n in imports]:
        raise ValueError('SOURCE_MODULE_SHAPE_MISMATCH:threads')
    head = body[2]
    if (not isinstance(head, ast.Assign) or len(head.targets) != 1
            or not isinstance(head.targets[0], ast.Name) or head.targets[0].id != 'HEAD'):
        raise ValueError('SOURCE_HEAD_SHAPE_MISMATCH')
    for node, signature in zip(body[3:], THREAD_SIGNATURES):
        _signature(node, ast.parse(signature).body[0])
    by_name = {n.name: n for n in nodes + body[3:]}
    by_name['context'] = _replace_exact(
        by_name['context'], 'from . import tracker', None, statement=True)
    for name, edits in EXPRESSIONS.items():
        for old, new in edits:
            by_name[name] = _replace_exact(by_name[name], old, new)

    class Cache(ast.NodeTransformer):
        count = 0

        def visit_Name(self, node):
            if node.id == '_receipt_cache':
                self.count += 1
                return ast.Attribute(value=ast.Name(id='self', ctx=ast.Load()),
                                     attr='_receipt_cache', ctx=node.ctx)
            return node

    cache = Cache()
    by_name['_group_has'] = cache.visit(by_name['_group_has'])
    if cache.count != 4:
        raise ValueError(f'SOURCE_CACHE_SITE_COUNT:{cache.count}')
    cls = ast.parse('''class LifecycleIdentity:
    def __init__(self, source):
        self.source = source
        self._receipt_cache = {'mtime': 0, 'keys': set()}
''').body[0]
    for name in ('_receipt_from_queue_file', '_group_has', 'context'):
        method = by_name[name]
        method.args.args.insert(0, ast.arg(arg='self'))
        cls.body.append(method)
    return ast.Module(body=ast.parse(IMPORTS).body + nodes[:6]
                      + [head, by_name['identity'], cls], type_ignores=[])


def _report(blockers, checked, dependencies):
    return {
        'status': 'BLOCKED' if blockers else 'VERIFIED',
        'source_subset_verified': not blockers, 'blockers': blockers,
        'checked_projections': checked, 'dependencies': dependencies,
        'source_commits': {'chart-desk': COMMIT},
        'ready_for_replay': False, 'ready_for_training': False,
    }


def audit_lifecycle_identity_source(source_root):
    """Require explicit retained parent, independent pins and real child proof."""
    blockers, checked, dependencies = [], [], {}
    try:
        source_root = Path(source_root)
    except ERRORS as exc:
        return _report([f'SOURCE_ROOT_INVALID:{type(exc).__name__}'], checked, dependencies)
    try:
        baseline = _read_json(ROOT / 'configs/trees/existing-alerts-baseline.json')
        if [r.get('commit') for r in baseline['repositories']
                if r.get('name') == 'chart-desk'] != [COMMIT]:
            blockers.append('BASELINE_COMMIT_MISMATCH')
    except ERRORS as exc:
        blockers.append(f'BASELINE_UNREADABLE:{type(exc).__name__}')
    path = source_root / 'chart-desk'
    try:
        if Path(_git(path, '--show-toplevel')).resolve() != path.resolve():
            blockers.append('NOT_REPOSITORY_ROOT')
        if _git(path, 'HEAD') != COMMIT:
            blockers.append('SOURCE_COMMIT_MISMATCH')
    except ERRORS as exc:
        blockers.append(f'SOURCE_IDENTITY_UNREADABLE:{type(exc).__name__}')
    sources = {}
    for name, blob in BLOBS.items():
        try:
            text = (path / name).read_text(encoding='utf-8')
            data = text.encode('utf-8')  # read_text normalizes checkout CRLF to Git LF
            actual = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
            if actual != blob:
                blockers.append(f'SOURCE_BLOB_MISMATCH:{name}')
            else:
                sources[name] = text
        except ERRORS as exc:
            blockers.append(f'SOURCE_UNREADABLE:{name}:{type(exc).__name__}')
    try:
        expected = _projection(sources['chartdesk/tracker.py'], sources['chartdesk/trade_threads.py'])
    except ERRORS as exc:
        blockers.append(f'SOURCE_PROJECTION_UNREADABLE:lifecycle_identity:{type(exc).__name__}:{exc}')
    else:
        try:
            actual = ast.parse((ROOT / VENDOR).read_text(encoding='utf-8'))
            if _dump(actual) != _dump(expected):
                blockers.append('VENDOR_AST_MISMATCH:lifecycle_identity')
            else:
                checked.append('lifecycle_identity')
        except ERRORS as exc:
            blockers.append(f'VENDOR_UNREADABLE:lifecycle_identity:{type(exc).__name__}')
    try:
        child = audit_tracker_admission_source(source_root)
        dependencies['tracker_admission'] = child
        for blocker in child['blockers']:
            blockers.append(f'DEPENDENCY:tracker_admission:{blocker}')
        if not child['source_subset_verified'] and not child['blockers']:
            blockers.append('DEPENDENCY:tracker_admission:NOT_VERIFIED')
    except ERRORS as exc:
        blockers.append(f'DEPENDENCY:tracker_admission:UNREADABLE:{type(exc).__name__}')
    return _report(blockers, checked, dependencies)
