"""Inert whole-reader audit, including the real ordered seeded-EMA dependency."""
import ast
import hashlib
from pathlib import Path

from tools.check_levelmap_source_parity import _audit_strict_ema
from .tracker_admission_source import (
    INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _selected, _without_doc,
)


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'trading_system/tree_replay/_vendor/ema_windows.py'
COMMIT = '68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
BLOBS = {'emawin.py': 'e4ce74f49973ce7aeea8e33ec1c64ea86e8181e8',
         'basis.py': 'f3396f3a9fefd71f0f71422001a5521af0a05cd2'}
SYMBOLS = ['LENGTHS', 'FAST', 'SLOW', 'OPEN_ATR', 'GLUED_ATR', 'SLOPE_BARS',
           'Window', 'EmaState', '_atr', 'read', '_read_with_deep', 'read_stack']
IMPORTS = '''from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd
from io import BytesIO
from pathlib import PurePosixPath
from . import indicators as I'''
EXPRESSIONS = {
    'read': [('basis.fetch_corrected(symbol, timeframe, lookback)',
              'self.source.fetch_corrected(symbol, timeframe, lookback)'),
             ('basis.TV_DIR', "PurePosixPath('.')"),
             ("basis.MT5_SYMBOL_MAP.get(symbol, '')", "MT5_SYMBOL_MAP.get(symbol, '')"),
             ('_dp.exists()', 'self.source.deep_exists(_dp.as_posix())'),
             ('pd.read_csv(_dp)', 'pd.read_csv(BytesIO(self.source.deep_bytes(_dp.as_posix())))')],
    'read_stack': [('read(symbol, tf)', 'self.read(symbol, tf)')],
}


def _projection(emawin_text, basis_text):
    nodes = _selected(emawin_text, SYMBOLS)
    mapping = _selected(basis_text, ['MT5_SYMBOL_MAP'])
    cls = ast.parse('class EmaReader:\n    def __init__(self, source):\n        self.source = source').body[0]
    pure = []
    for node in nodes:
        if isinstance(node, ast.FunctionDef) and node.name in EXPRESSIONS:
            if node.decorator_list or any(arg.arg == 'self' for arg in node.args.args):
                raise ValueError('METHOD_SHAPE_MISMATCH:' + node.name)
            for old, new in EXPRESSIONS[node.name]:
                _replace_exact(node, old, new)
            node.args.args.insert(0, ast.arg(arg='self'))
            cls.body.append(node)
        else:
            pure.append(node)
    if [n.name for n in cls.body] != ['__init__', 'read', 'read_stack']:
        raise ValueError('METHOD_SHAPE_MISMATCH')
    return ast.parse(IMPORTS).body + mapping + pure + [cls]


def audit_ema_windows_source(source_root):
    """Parse source and candidate only; a pass is not causal replay certification."""
    blockers, checked, dependencies = [], [], {}
    report = dict(status='BLOCKED', source_subset_verified=False, blockers=blockers,
        checked_projections=checked, dependencies=dependencies,
        source_commits={'chart-desk': COMMIT}, ready_for_replay=False, ready_for_training=False)
    try:
        root = Path(source_root) / 'chart-desk'
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
    texts = {}
    for filename, pin in BLOBS.items():
        try:
            text = (root / 'chartdesk' / filename).read_text(encoding='utf-8')
            raw = text.encode('utf-8')
            if hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() != pin:
                blockers.append('SOURCE_BLOB_MISMATCH:' + filename)
            texts[filename] = text
        except INPUT_ERRORS as exc:
            blockers.append(f'SOURCE_UNREADABLE:{filename}:{type(exc).__name__}')
    if len(texts) == len(BLOBS):
        try:
            expected = _projection(texts['emawin.py'], texts['basis.py'])
        except INPUT_ERRORS as exc:
            blockers.append(f'SOURCE_PROJECTION_UNREADABLE:{type(exc).__name__}:{exc}')
        else:
            try:
                actual = _without_doc(ast.parse(RUNTIME.read_text(encoding='utf-8')))
                if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
                    blockers.append('VENDOR_AST_MISMATCH')
                else:
                    checked.append('ema_windows')
            except INPUT_ERRORS as exc:
                blockers.append('VENDOR_UNREADABLE:' + type(exc).__name__)
    try:
        ema_blockers = []
        _audit_strict_ema(root, ema_blockers)
        dependencies['ema'] = dict(source_subset_verified=not ema_blockers,
                                   blockers=ema_blockers)
        blockers.extend('DEPENDENCY:ema:' + b for b in ema_blockers)
    except INPUT_ERRORS as exc:
        blockers.append('DEPENDENCY:ema:UNREADABLE:' + type(exc).__name__)
    if not blockers:
        report.update(status='VERIFIED', source_subset_verified=True)
    return report
