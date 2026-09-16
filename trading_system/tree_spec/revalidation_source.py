"""Inert audit of original pending checks and all consumed calculation readers."""
import ast
import hashlib
from pathlib import Path

from tools.check_reversal_source_parity import check_source_parity as audit_pvsra
from .admission_source import audit_admission_source, _replace_exact as _replace_counted
from .ema_windows_source import audit_ema_windows_source
from .lifecycle_primitives_source import audit_lifecycle_primitives_source
from .stretch_source import audit_stretch_source
from .tracker_admission_source import (
    INPUT_ERRORS, _dump, _git, _name, _read_json, _replace_exact, _selected,
    _without_doc, audit_tracker_admission_source,
)
from .watch_io_source import audit_watch_io_source

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'trading_system/tree_replay/_vendor/revalidation.py'
COMMIT = '68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
BLOBS = {'tracker.py': 'b616b34022e436545d8c1daf85eced51614fd74e',
         'tradeplan.py': 'd09e9be39ce8dadf1674029e0c03751c70502135'}
CONSTANTS = ['AGED_PENDING_RECHECK_H', '_BIAS_AGAINST_AS_SENT',
    '_BIAS_AGAINST_FLAT_AT_SEND', '_BIAS_AGAINST_UNREAD', 'SOFT_STALE_MIN', 'HARD_STALE_MIN']
METHODS = ['_tree_agrees', 'revalidate_pending', '_shadow', 'still_valid']
TRACKER_ORDER = CONSTANTS[:4] + METHODS[:2] + CONSTANTS[4:] + METHODS[2:] + ['_bias_against']
IMPORTS = '''from __future__ import annotations
import json
import pandas as pd
from pathlib import PurePosixPath
from . import lifecycle_voice as voice
from . import admission_matrix, pvsra, watch_sessions
from .tracker_admission import TrackerAdmission
from .stretch import StretchReader
from .ema_windows import EmaReader'''
REMOVE_IMPORTS = {
    '_tree_agrees': ['from . import tree'],
    'still_valid': ['from . import stretch', 'from . import basis',
        'from . import emawin', 'from . import sessions',
        'from . import basis as _b, matrix as _mx',
        'from . import basis as _b2, tr as _tr',
        'from .workspace import repo as _repo',
        'from .tradeplan import calendar_high_impact_in_window'],
}
EXPRESSIONS = {
    '_tree_agrees': [('tree.walk(symbol)', 'self.source.tree_walk(symbol)')],
    'revalidate_pending': [('still_valid(t)', 'self.still_valid(t)'),
        ('time.time()', 'self.source.now_epoch()'),
        ("_tree_agrees(t['symbol'], t['direction'])", "self._tree_agrees(t['symbol'], t['direction'])")],
    '_shadow': [('SHADOW_LOG.parent.mkdir(parents=True, exist_ok=True)',
                 'self.source.ensure_shadow_parent(parents=True, exist_ok=True)'),
        ("SHADOW_LOG.open('a', encoding='utf-8')", "self.source.shadow_open('a', encoding='utf-8')"),
        ('time.time()', 'self.source.now_epoch()')],
    'still_valid': [('_higher_bias(symbol)', 'self.admission._higher_bias(symbol)'),
        ('stretch.state(symbol)', 'self.stretch.state(symbol)'),
        ('basis.fetch_corrected(symbol, tf, 3)', 'self.source.fetch_corrected(symbol, tf, 3)'),
        ('pd.Timestamp.now(tz=last.tz)', 'self.source.now_timestamp(tz=last.tz)'),
        ("emawin.read_stack(symbol, timeframes=('1h', '15m'))", "self.ema.read_stack(symbol, timeframes=('1h', '15m'))"),
        ('sessions.current_session()', "watch_sessions.current_session_at(decision_time=self.source.now_timestamp(tz='UTC'))"),
        ("_b.fetch_corrected(symbol, '4h', 400)", "self.source.fetch_corrected(symbol, '4h', 400)"),
        ('_mx.read_structure(_d4)', 'admission_matrix.read_structure(_d4)'),
        ("_b2.fetch_corrected(symbol, '15m', 60)", "self.source.fetch_corrected(symbol, '15m', 60)"),
        ('_tr.pvsra(_d15)', 'pvsra.pvsra(_d15)'),
        ("_repo('news-desk')", "PurePosixPath('news-desk')"),
        ('_cal.exists()', 'self.source.calendar_exists(_cal.as_posix())'),
        ('_dt.now(_tz.utc)', 'self.source.now_utc()'),
        ('_cal.read_text()', 'self.source.calendar_text(_cal.as_posix())')],
}


def _projection(tracker_text, tradeplan_text):
    nodes = {_name(n): n for n in _selected(tracker_text, TRACKER_ORDER)}
    calendar = _selected(tradeplan_text, ['calendar_event_ts', 'calendar_high_impact_in_window'])
    cls = ast.parse('''class Revalidation:
    def __init__(self, source):
        self.source = source
        self.admission = TrackerAdmission(source)
        self.stretch = StretchReader(source)
        self.ema = EmaReader(source)''').body[0]
    for name in METHODS:
        node = nodes[name]
        if not isinstance(node, ast.FunctionDef) or node.decorator_list or any(
                arg.arg == 'self' for arg in node.args.args):
            raise ValueError('METHOD_SHAPE_MISMATCH:' + name)
        for statement in REMOVE_IMPORTS.get(name, []):
            _replace_exact(node, statement, None, statement=True)
        for old, new in EXPRESSIONS[name]:
            _replace_exact(node, old, new)
        if name == 'still_valid':
            _replace_counted(node, '_shadow', 'self._shadow', 15)
        node.args.args.insert(0, ast.arg(arg='self'))
        cls.body.append(node)
    return ast.parse(IMPORTS).body + [nodes[n] for n in CONSTANTS] + calendar + [nodes['_bias_against'], cls]


def audit_revalidation_source(source_root):
    """Verify source identity and whole projection; no execution or readiness grant."""
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
            expected = _projection(texts['tracker.py'], texts['tradeplan.py'])
        except INPUT_ERRORS as exc:
            blockers.append(f'SOURCE_PROJECTION_UNREADABLE:{type(exc).__name__}:{exc}')
        else:
            try:
                actual = _without_doc(ast.parse(RUNTIME.read_text(encoding='utf-8')))
                if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
                    blockers.append('VENDOR_AST_MISMATCH')
                else:
                    checked.append('revalidation')
            except INPUT_ERRORS as exc:
                blockers.append('VENDOR_UNREADABLE:' + type(exc).__name__)
    audits = [('tracker_admission', audit_tracker_admission_source, parent),
        ('stretch', audit_stretch_source, parent), ('ema_windows', audit_ema_windows_source, parent),
        ('admission', audit_admission_source, parent), ('watch_io', audit_watch_io_source, parent),
        ('lifecycle_primitives', audit_lifecycle_primitives_source, parent), ('pvsra', audit_pvsra, root)]
    for name, audit, path in audits:
        try:
            result = audit(path)
            dependencies[name] = result
            blockers.extend('DEPENDENCY:' + name + ':' + b for b in result['blockers'])
            if not result['source_subset_verified'] and not result['blockers']:
                blockers.append('DEPENDENCY:' + name + ':NOT_VERIFIED')
        except INPUT_ERRORS as exc:
            blockers.append('DEPENDENCY:' + name + ':UNREADABLE:' + type(exc).__name__)
    if not blockers:
        report.update(status='VERIFIED', source_subset_verified=True)
    return report
