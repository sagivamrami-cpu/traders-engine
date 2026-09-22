"""Inert audit of complete extension calculation and actual range/EMA closure."""
import ast
import hashlib
from pathlib import Path

from tools.check_levelmap_source_parity import _audit_strict_ema
from tools.check_range_source_parity import check_source_parity as audit_ranges
from .tracker_admission_source import (
    INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _selected, _without_doc,
)


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'trading_system/tree_replay/_vendor/stretch.py'
COMMIT = '68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
BLOBS = {'stretch.py': 'a74a591d9f3e014543e4023c694eab7eac845d43',
         'rails.py': '614920678bc58f1b920ebd145b1a4b0b5a159dff'}
SYMBOLS = ['BEYOND_MIN', 'BEYOND_EXTREME', 'DEV_STRETCHED', 'Stretch', '_atr',
           '_dev_from_cloud', 'state']
EXPRESSIONS = {
    '_dev_from_cloud': [('basis.fetch_corrected(symbol, tf, days)',
                         'self.source.fetch_corrected(symbol, tf, days)')],
    'state': [('basis.fetch_corrected(symbol, "1d", 400)',
               'self.source.fetch_corrected(symbol, "1d", 400)'),
              ('basis.broker_shape_ok(dcorr, 20)', 'self.source.broker_shape_ok(dcorr, 20)'),
              ('tr.weekly_from_daily(daily)', 'ranges.weekly_from_daily(daily)'),
              ('tr.tr_levels(daily, ranges.weekly_from_daily(daily), broker_bars=True)',
               'ranges.tr_levels(daily, ranges.weekly_from_daily(daily), broker_bars=True)'),
              ('_dev_from_cloud(symbol, tf, days)', 'self._dev_from_cloud(symbol, tf, days)')],
}


def _projection(stretch_text, rails_text):
    nodes = _selected(stretch_text, SYMBOLS)
    budget = _selected(rails_text, ['BUDGET_MIN'])
    cls = ast.parse('class StretchReader:\n    def __init__(self, source):\n        self.source = source').body[0]
    for node in nodes[-2:]:
        if not isinstance(node, ast.FunctionDef) or node.decorator_list or any(
                arg.arg == 'self' for arg in node.args.args):
            raise ValueError('METHOD_SHAPE_MISMATCH')
        for old, new in EXPRESSIONS[node.name]:
            _replace_exact(node, old, new)
        node.args.args.insert(0, ast.arg(arg='self'))
        cls.body.append(node)
    imports = ast.parse('from __future__ import annotations\nfrom dataclasses import dataclass\nfrom . import tr, ranges').body
    return imports + budget + nodes[:-2] + [cls]


def audit_stretch_source(source_root):
    """Only parse source/candidate ASTs; never import their executable modules."""
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
            expected = _projection(texts['stretch.py'], texts['rails.py'])
        except INPUT_ERRORS as exc:
            blockers.append(f'SOURCE_PROJECTION_UNREADABLE:{type(exc).__name__}:{exc}')
        else:
            try:
                actual = _without_doc(ast.parse(RUNTIME.read_text(encoding='utf-8')))
                if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
                    blockers.append('VENDOR_AST_MISMATCH')
                else:
                    checked.append('stretch')
            except INPUT_ERRORS as exc:
                blockers.append('VENDOR_UNREADABLE:' + type(exc).__name__)
    try:
        ranges = audit_ranges(root)
        dependencies['range'] = ranges
        if not ranges['source_subset_verified']:
            blockers.extend('DEPENDENCY:range:' + b for b in ranges['blockers'])
            if not ranges['blockers']:
                blockers.append('DEPENDENCY:range:NOT_VERIFIED')
    except INPUT_ERRORS as exc:
        blockers.append('DEPENDENCY:range:UNREADABLE:' + type(exc).__name__)
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
