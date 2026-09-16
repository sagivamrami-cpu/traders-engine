"""Inert audit of operation-clock map projections and their actual source graph."""

import ast
import hashlib
from pathlib import Path

from tools.check_levelmap_source_parity import check_source_parity as audit_levelmap
from .tracker_admission_source import (
    INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _selected, _without_doc,
)

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
BLOBS = {
    'basis': 'f3396f3a9fefd71f0f71422001a5521af0a05cd2',
    'levelmap': '01fc9fe098aa7a5991ce62c3a83e870e4f0d5a2e',
}
SOURCE_IMPORTS = {
    'basis': '''from __future__ import annotations
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
from . import symbols''',
    'levelmap': '''from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd
from . import basis, data, quarters, sessions, tr''',
}
IMPORTS = {
    'basis': '''import pandas as pd
from .correction import EXCHANGE_NATIVE''',
    'levelmap': '''from __future__ import annotations
import pandas as pd
from . import map_tr as tr, quarters, map_sessions as sessions
from .back_days import _back_day_levels
from .levelmap_build import NamedLevel, SESSION_OPEN_LEVELS, _ema_levels
from .basis_operation import BasisOperation''',
}
SIGNATURES = {
    'basis': 'def broker_shape_ok(corr, days: float) -> bool: pass',
    'levelmap': '''def _session_open_levels(symbol: str, missing: list | None = None, now=None) -> list[NamedLevel]: pass
def build(symbol: str, missing: list | None = None) -> tuple[list[NamedLevel], "basis.Correction | None"]: pass''',
}
CLASSES = {
    'basis': '''class BasisOperation:
    def __init__(self, source):
        self.source = source
    def fetch_corrected(self, symbol, timeframe, lookback):
        return self.source.fetch_corrected(symbol, timeframe, lookback)
    def now_utc(self):
        return self.source.now_utc()''',
    'levelmap': '''class LevelmapOperation:
    def __init__(self, source):
        self.source = BasisOperation(source)''',
}
REPLACEMENTS = {
    'broker_shape_ok': [('pd.Timestamp.now("UTC")', 'pd.Timestamp(self.source.now_utc())')],
    '_session_open_levels': [('pd.Timestamp.now("UTC")', 'pd.Timestamp(self.source.now_utc())')],
    'build': [('_session_open_levels(symbol, missing)', 'self._session_open_levels(symbol, missing)'),
              ('_ema_levels(symbol, missing)', '_ema_levels(symbol, missing, source=self.source)')],
}


def _projection(file, text):
    """Selected bodies remain intact except for independently enumerated ports."""
    tree = ast.parse(text)
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    if [_dump(n) for n in imports] != [_dump(n) for n in ast.parse(SOURCE_IMPORTS[file]).body]:
        raise ValueError('SOURCE_IMPORT_MISMATCH:' + file)
    signatures = ast.parse(SIGNATURES[file]).body
    selected = _selected(text, [n.name for n in signatures])
    cls = ast.parse(CLASSES[file]).body[0]
    for node, signature in zip(selected, signatures):
        if not isinstance(node, ast.FunctionDef) or node.decorator_list or (
            _dump(node.args) != _dump(signature.args) or _dump(node.returns) != _dump(signature.returns)
        ):
            raise ValueError('SOURCE_SIGNATURE_MISMATCH:' + signature.name)
        node.args.args.insert(0, ast.arg(arg='self'))
        for old, new in REPLACEMENTS[node.name]:
            _replace_exact(node, old, new)
        if file == 'levelmap':
            first = node.body[0]
            has_doc = isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)
            node.body.insert(int(has_doc), ast.parse('basis = self.source').body[0])
        cls.body.append(node)
    return ast.parse(IMPORTS[file]).body + [cls]


def audit_levelmap_operation_source(source_root):
    """Source parity is not certification of historical inputs or replay readiness."""
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
    for file, blob in BLOBS.items():
        runtime = file + '_operation'
        try:
            text = (root / ('chartdesk/' + file + '.py')).read_text(encoding='utf-8')
            raw = text.encode('utf-8')
            if hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() != blob:
                blockers.append('SOURCE_BLOB_MISMATCH:' + file)
            expected = _projection(file, text)
        except INPUT_ERRORS as exc:
            blockers.append('SOURCE_PROJECTION_UNREADABLE:' + file + ':' + type(exc).__name__)
            continue
        try:
            path = ROOT / ('trading_system/tree_replay/_vendor/' + runtime + '.py')
            actual = _without_doc(ast.parse(path.read_text(encoding='utf-8')))
            if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
                blockers.append('VENDOR_AST_MISMATCH:' + runtime)
            else:
                checked.append(runtime)
        except INPUT_ERRORS as exc:
            blockers.append('VENDOR_UNREADABLE:' + runtime + ':' + type(exc).__name__)
    try:
        result = audit_levelmap(root)
        dependencies['levelmap'] = result
        blockers.extend('DEPENDENCY:levelmap:' + b for b in result['blockers'])
        if result['source_subset_verified'] is not True and not result['blockers']:
            blockers.append('DEPENDENCY:levelmap:NOT_VERIFIED')
    except INPUT_ERRORS as exc:
        blockers.append('DEPENDENCY:levelmap:UNREADABLE:' + type(exc).__name__)
    if not blockers:
        report.update(status='VERIFIED', source_subset_verified=True)
    return report
