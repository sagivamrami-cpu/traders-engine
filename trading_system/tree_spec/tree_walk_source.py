"""Inert full ordered tree projection and actual dependency-graph audit."""
import ast
import hashlib
from pathlib import Path

from tools.check_ema_source_parity import check_source_parity as audit_ema
from .admission_source import audit_admission_source as audit_admission
from .levelmap_operation_source import audit_levelmap_operation_source as audit_levelmap_operation
from .optionswall_source import audit_optionswall_source as audit_options
from .pattern_readers_source import audit_pattern_readers_source as audit_patterns
from .revalidation_source import audit_revalidation_source as audit_revalidation
from .stretch_source import audit_stretch_source as audit_stretch
from .tree_tr_source import audit_tree_tr_source as audit_tree_tr
from .tracker_admission_source import INPUT_ERRORS, _dump, _git, _read_json, _replace_exact

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
BLOB = 'fdb439a39bbd35230e421c0319c6be0e2fbfbc1d'
SOURCE_IMPORTS = '''from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd
from . import basis, brinks, checklists, levelmap, matrix, sessions, stretch, tr, wm'''
INVENTORY = [
    'VECTOR_BASE', 'RECOVERY', 'MAX_MAGNET_ATR', 'AGGRESSIVE_ATR', 'AGGRESSIVE_BARS',
    'EXTREME_LOOKBACK', 'BUY_SIDE,SELL_SIDE', 'EXTREME_PCT', 'MAX_DECISION_DRIFT_ATR',
    'LEVEL_ZONE_ATR', 'STOP_CUSHION_ATR', 'TREE_STYLE', 'SV_BODY_MAX', 'SV_WICK_MIN',
    'SV_VOLUME_MULT', 'LevelsUnavailable', 'FINAL_STAGE', 'STAGES', 'FINAL_STAGE',
    '_news_stop', 'Walk', '_atr', '_stopping_volume', '_levels_ahead', '_variant_levels',
    '_stamp_decision', '_levels_unavailable_reason', 'TREND_LADDER', 'HI_FRAMES',
    'LO_FRAMES', '_trend_ladder', '_side', '_trend_from_ladder', '_ladder_text',
    'trap_direction', 'walk', 'first_vector_above_50', 'levels_to_trade', 'trade_from_walk',
]
SIGNATURES = '''def _variant_levels(symbol: str, variant: str, missing: list | None=None) -> list | None: pass
def _trend_ladder(symbol: str, d4h, r4) -> dict: pass
def walk(symbol: str, variant: str='house') -> Walk: pass
def first_vector_above_50(symbol: str, timeframe: str='5m'): pass
def levels_to_trade(symbol: str, close: float, direction: str, atr: float, variant: str='house'): pass
def trade_from_walk(w: Walk): pass'''
CORE_IMPORTS = '''from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd'''
SIGNALS = '''from .tr import emas, ema_cloud
from .pvsra import pvsra
from .tree_tr import vector_zones, daily_pivots'''
READER_IMPORTS = '''from __future__ import annotations
import pandas as pd
from . import admission_matrix as matrix, map_sessions as sessions, watch_sessions
from . import tree_signals as tr
from .basis_operation import BasisOperation
from .levelmap_operation import LevelmapOperation
from .brinks import BrinksReader
from .checklists import ChecklistReader
from .wm import WmReader
from .liquidity import LiquidityReader
from .optionswall import OptionsWallReader
from .stretch import StretchReader
from .tree_core import VECTOR_BASE, RECOVERY, MAX_MAGNET_ATR, AGGRESSIVE_ATR, AGGRESSIVE_BARS, EXTREME_LOOKBACK, BUY_SIDE, SELL_SIDE, EXTREME_PCT, MAX_DECISION_DRIFT_ATR, LEVEL_ZONE_ATR, STOP_CUSHION_ATR, TREE_STYLE, SV_BODY_MAX, SV_WICK_MIN, SV_VOLUME_MULT, LevelsUnavailable, FINAL_STAGE, STAGES, _news_stop, Walk, _atr, _stopping_volume, _levels_ahead, _stamp_decision, _levels_unavailable_reason, TREND_LADDER, HI_FRAMES, LO_FRAMES, _side, _trend_from_ladder, _ladder_text, trap_direction'''
CONSTRUCTOR = '''class TreeReader:
    def __init__(self, source):
        self.source = source
        self.basis = BasisOperation(source)
        self.levelmap = LevelmapOperation(source)
        self.brinks = BrinksReader(source)
        self.checklists = ChecklistReader(source)
        self.wm = WmReader(source)
        self.liquidity = LiquidityReader(source)
        self.optionswall = OptionsWallReader(source)
        self.stretch = StretchReader(self.basis)'''
ALIASES = {'_variant_levels': ['basis', 'levelmap'], '_trend_ladder': ['basis'],
    'walk': ['basis', 'brinks', 'checklists', 'wm', 'stretch'],
    'first_vector_above_50': ['basis'], 'levels_to_trade': [], 'trade_from_walk': ['basis']}
EXPRESSIONS = {
    'walk': [('_trend_ladder(symbol, d4h, r4)', 'self._trend_ladder(symbol, d4h, r4)'),
        ('_variant_levels(symbol, variant, w.missing)', 'self._variant_levels(symbol, variant, w.missing)'),
        ('first_vector_above_50(symbol, "5m")', 'self.first_vector_above_50(symbol, "5m")'),
        ('_repo("news-desk")', 'PurePosixPath("news-desk")'),
        ('_dt.now(_tz.utc).timestamp()', 'self.source.now_utc().timestamp()'),
        ('cal.read_text()', 'self.source.calendar_text(cal.as_posix())'),
        ('sessions.current_session()', 'watch_sessions.current_session_at(decision_time=self.source.now_utc())'),
        ('_pd.Timestamp.now(tz="UTC")', '_pd.Timestamp(self.source.now_utc())')],
    'levels_to_trade': [('_variant_levels(symbol, variant)', 'self._variant_levels(symbol, variant)')],
    'trade_from_walk': [('_variant_levels(w.symbol, w.variant)', 'self._variant_levels(w.symbol, w.variant)')],
}
STATEMENTS = {
    '_news_stop': [('from .tradeplan import calendar_event_ts, calendar_high_impact_in_window',
                    'from .revalidation import calendar_event_ts, calendar_high_impact_in_window')],
    '_levels_ahead': [('from .tradeplan import distinct_targets', 'from .pricing import distinct_targets')],
    'walk': [('from . import optionswall', 'optionswall = self.optionswall'),
        ('from . import liquidity as _liq', '_liq = self.liquidity'),
        ('from .workspace import repo as _repo', 'from pathlib import PurePosixPath')],
    'levels_to_trade': [('from .tradeplan import apply_stop_band, resolve_ladder',
                          'from .pricing import apply_stop_band, resolve_ladder')],
    'trade_from_walk': [('from .tradeplan import MIN_RR, Plan', 'from .pricing import MIN_RR, Plan'),
        ('from .tradeplan import apply_stop_band, resolve_ladder', 'from .pricing import apply_stop_band, resolve_ladder')],
}


def _identity(node):
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign):
        return ','.join(n.id for target in node.targets for n in ast.walk(target) if isinstance(n, ast.Name))
    raise ValueError('UNEXPECTED_SOURCE_NODE')


def _projection(text):
    """Transform inert ASTs with independent inventory, signatures and site counts."""
    tree = ast.parse(text)
    if ast.get_docstring(tree) is None:
        raise ValueError('SOURCE_DOCSTRING_MISSING')
    imports = ast.parse(SOURCE_IMPORTS).body
    if [_dump(n) for n in tree.body[1:1 + len(imports)]] != [_dump(n) for n in imports]:
        raise ValueError('SOURCE_IMPORT_MISMATCH')
    nodes = tree.body[1 + len(imports):]
    if [_identity(n) for n in nodes] != INVENTORY:
        raise ValueError('SOURCE_ORDER_OR_INVENTORY_MISMATCH')
    signatures = {n.name: n for n in ast.parse(SIGNATURES).body}
    core = [tree.body[0]] + ast.parse(CORE_IMPORTS).body
    reader = ast.parse(CONSTRUCTOR).body[0]
    for node in nodes:
        name = _identity(node)
        for old, new in STATEMENTS.get(name, []):
            _replace_exact(node, old, new, statement=True)
        if name not in signatures:
            core.append(node)
            continue
        signature = signatures[name]
        actual_return = None if node.returns is None else _dump(node.returns)
        expected_return = None if signature.returns is None else _dump(signature.returns)
        if not isinstance(node, ast.FunctionDef) or node.decorator_list or (
                _dump(node.args) != _dump(signature.args) or actual_return != expected_return):
            raise ValueError('SOURCE_SIGNATURE_MISMATCH:' + name)
        node.args.args.insert(0, ast.arg(arg='self'))
        for old, new in EXPRESSIONS.get(name, []):
            _replace_exact(node, old, new)
        aliases = ast.parse('\n'.join(a + ' = self.' + a for a in ALIASES[name])).body
        at = int(ast.get_docstring(node) is not None)
        node.body[at:at] = aliases
        reader.body.append(node)
    if [n.name for n in reader.body[1:]] != list(signatures):
        raise ValueError('SOURCE_METHOD_ORDER')
    return {'tree_core': core, 'tree_signals': ast.parse(SIGNALS).body,
            'tree_walk': ast.parse(READER_IMPORTS).body + [reader]}


def audit_tree_walk_source(source_root):
    """Certify source projections only, not historical inputs or model readiness."""
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
    try:
        text = (root / 'chartdesk/tree.py').read_text(encoding='utf-8')
        raw = text.encode('utf-8')
        if hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() != BLOB:
            blockers.append('SOURCE_BLOB_MISMATCH:tree')
        projected = _projection(text)
    except INPUT_ERRORS as exc:
        blockers.append('SOURCE_PROJECTION_UNREADABLE:' + type(exc).__name__ + ':' + str(exc))
    else:
        for name, expected in projected.items():
            try:
                actual = ast.parse((ROOT / 'trading_system/tree_replay/_vendor' / (name + '.py')).read_text(encoding='utf-8')).body
                if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
                    blockers.append('VENDOR_AST_MISMATCH:' + name)
                else:
                    checked.append(name)
            except INPUT_ERRORS as exc:
                blockers.append('VENDOR_UNREADABLE:' + name + ':' + type(exc).__name__)
    for name, audit, path in [
        ('levelmap_operation', audit_levelmap_operation, parent), ('patterns', audit_patterns, parent),
        ('options', audit_options, parent), ('tree_tr', audit_tree_tr, parent),
        ('stretch', audit_stretch, parent), ('admission', audit_admission, parent),
        ('revalidation', audit_revalidation, parent), ('ema', audit_ema, root),
    ]:
        try:
            result = audit(path)
            dependencies[name] = result
            blockers.extend('DEPENDENCY:' + name + ':' + b for b in result['blockers'])
            if result['source_subset_verified'] is not True and not result['blockers']:
                blockers.append('DEPENDENCY:' + name + ':NOT_VERIFIED')
        except INPUT_ERRORS + (StopIteration,) as exc:
            # The retained EMA auditor uses next() for the baseline pin. A
            # missing row is unavailable authority, not an unhandled CLI error.
            blockers.append('DEPENDENCY:' + name + ':UNREADABLE:' + type(exc).__name__)
    if not blockers:
        report.update(status='VERIFIED', source_subset_verified=True)
    return report
