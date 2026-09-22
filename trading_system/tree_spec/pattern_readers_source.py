"""Inert full-module proof for original pattern readers and actual dependencies."""
import ast
import hashlib
from pathlib import Path

from tools.check_reversal_source_parity import check_source_parity as audit_pvsra
from .tree_tr_source import audit_tree_tr_source as audit_tree_tr
from .tracker_admission_source import INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _without_doc

ROOT=Path(__file__).resolve().parents[2]
VENDOR=ROOT/'trading_system/tree_replay/_vendor'
COMMIT='68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
BLOBS={
    'wm':'d04a462eb0692ed991f25ea2633d8c81783db877',
    'liquidity':'d73f06f323d39142932cb218935c15455244ce8b',
    'brinks':'5c69c3367221e818a2b82f3ca559e1c5a36af675',
    'checklists':'5c78955a6bb58d88c8117274606409fced65e22c',
}
COMMON='from __future__ import annotations\n'
SOURCE_IMPORTS={
    'wm':COMMON+'from dataclasses import dataclass\nimport pandas as pd\nfrom . import basis, tr',
    'liquidity':COMMON+'from dataclasses import dataclass, field\nimport pandas as pd\nfrom . import basis',
    'brinks':COMMON+'from dataclasses import dataclass, field\nfrom datetime import datetime, timedelta, timezone\nimport pandas as pd\nfrom . import basis, tr',
    'checklists':COMMON+'from dataclasses import dataclass\nimport pandas as pd\nfrom . import basis, sessions, tr',
}
IMPORTS={
    'wm':COMMON+'from dataclasses import dataclass\nimport pandas as pd\nfrom . import pattern_tr as tr',
    'liquidity':COMMON+'from dataclasses import dataclass, field\nimport pandas as pd',
    'brinks':COMMON+'from dataclasses import dataclass, field\nfrom datetime import datetime, timedelta, timezone\nimport pandas as pd\nfrom . import pattern_tr as tr',
    'checklists':COMMON+'from dataclasses import dataclass\nimport pandas as pd\nfrom . import map_sessions as sessions, pattern_tr as tr\nfrom .brinks import BrinksReader',
}
INVENTORIES={
    'wm':['SWING_K','LEG_TOLERANCE_ATR','MIN_HEIGHT_ATR','MAX_AGE_BARS','Formation','_swings','_dedup_pivots','detect'],
    'liquidity':['EQ_TOL_ATR','LOOKBACK','SWING_K','RUN_ATR','RUN_BARS','Pool','Run','_atr','_swings','pools','run'],
    'brinks':['BOX_START_H,BOX_END_H','RELEVANT_UNTIL_H','Box','today_box'],
    'checklists':['WICK_SYMMETRY_MAX','BLOCK_BODY_MIN','BLOCK_RANGE_MIN_ATR','RvcGvc','rvc_gvc','Block','block_quality','blocks','BrinksRead','brinks_read'],
}
CLASSES={'wm':'WmReader','liquidity':'LiquidityReader','brinks':'BrinksReader','checklists':'ChecklistReader'}
SIGNATURES={
    'wm':"def detect(symbol: str, timeframe: str='15m') -> Formation | None: pass",
    'liquidity':"def pools(symbol: str, timeframe: str='15m') -> list[Pool]: pass\ndef run(symbol: str, timeframe: str='15m') -> Run: pass",
    'brinks':"def today_box(symbol: str, now: datetime | None=None) -> Box | None: pass",
    'checklists':"def rvc_gvc(symbol: str, timeframe: str='15m') -> RvcGvc | None: pass\ndef blocks(symbol: str, timeframe: str='15m', lookback: int=60) -> list[Block]: pass\ndef brinks_read(symbol: str, timeframe: str='5m') -> BrinksRead: pass",
}
SHIM='from .pvsra import pvsra\nfrom .tree_tr import vector_zones'


def _identity(node):
    if isinstance(node,(ast.FunctionDef,ast.ClassDef)):
        return node.name
    if isinstance(node,ast.Assign):
        return ','.join(n.id for target in node.targets for n in ast.walk(target) if isinstance(n,ast.Name))
    raise ValueError('UNEXPECTED_SOURCE_NODE')


def _projection(name,text):
    nodes=_without_doc(ast.parse(text))
    imports=ast.parse(SOURCE_IMPORTS[name]).body
    if [_dump(n) for n in nodes[:len(imports)]]!=[_dump(n) for n in imports]:
        raise ValueError('SOURCE_IMPORT_MISMATCH')
    nodes=nodes[len(imports):]
    if [_identity(n) for n in nodes]!=INVENTORIES[name]:
        raise ValueError('SOURCE_ORDER_OR_INVENTORY_MISMATCH')
    signatures={n.name:n for n in ast.parse(SIGNATURES[name]).body}
    pure,methods=[],[]
    for node in nodes:
        if not isinstance(node,ast.FunctionDef) or node.name not in signatures:
            pure.append(node)
            continue
        signature=signatures[node.name]
        if node.decorator_list or _dump(node.args)!=_dump(signature.args) or _dump(node.returns)!=_dump(signature.returns):
            raise ValueError('SOURCE_SIGNATURE_MISMATCH:'+node.name)
        node.args.args.insert(0,ast.arg(arg='self'))
        if node.name=='brinks_read':
            target=ast.parse('from . import brinks as _bx').body[0]
            matches=[n for n in node.body if _dump(n)==_dump(target)]
            if len(matches)!=1:
                raise ValueError('SOURCE_BRINKS_IMPORT_COUNT')
            node.body.remove(matches[0])
            _replace_exact(node,'_bx.today_box(symbol)','self.brinks.today_box(symbol)')
            _replace_exact(node,"basis.fetch_corrected(symbol, '15m', 3)","self.source.fetch_corrected(symbol, '15m', 3)")
        if node.name=='today_box':
            _replace_exact(node,"basis.fetch_corrected(symbol, '5m', 2)","self.source.fetch_corrected(symbol, '5m', 2)")
            _replace_exact(node,'datetime.now(timezone.utc)','self.source.now_utc()')
        else:
            days=5 if node.name=='rvc_gvc' else 10
            _replace_exact(node,f'basis.fetch_corrected(symbol, timeframe, {days})',f'self.source.fetch_corrected(symbol, timeframe, {days})')
        if node.name=='run':
            _replace_exact(node,'pools(symbol, timeframe)','self.pools(symbol, timeframe)')
        methods.append(node)
    if [n.name for n in methods]!=list(signatures):
        raise ValueError('SOURCE_METHOD_ORDER')
    ctor=ast.parse('def __init__(self, source):\n    self.source = source\n'+
        ('    self.brinks = BrinksReader(source)\n' if name=='checklists' else '')).body[0]
    reader=ast.ClassDef(name=CLASSES[name],bases=[],keywords=[],body=[ctor]+methods,decorator_list=[])
    return ast.parse(IMPORTS[name]).body+pure+[reader]


def audit_pattern_readers_source(source_root):
    """Only certify the pinned private projections, never input/replay readiness."""
    blockers,checked,dependencies=[],[],{}
    report=dict(status='BLOCKED',source_subset_verified=False,blockers=blockers,
        checked_projections=checked,dependencies=dependencies,
        source_commits={'chart-desk':COMMIT},ready_for_replay=False,ready_for_training=False)
    try:
        parent=Path(source_root); root=parent/'chart-desk'
    except INPUT_ERRORS as exc:
        blockers.append('SOURCE_ROOT_INVALID:'+type(exc).__name__)
        return report
    try:
        if Path(_git(root,'--show-toplevel')).resolve()!=root.resolve(): blockers.append('NOT_REPOSITORY_ROOT')
        if _git(root,'HEAD')!=COMMIT: blockers.append('SOURCE_COMMIT_MISMATCH')
        baseline=_read_json(ROOT/'configs/trees/existing-alerts-baseline.json')
        if [r.get('commit') for r in baseline['repositories'] if r.get('name')=='chart-desk']!=[COMMIT]:
            blockers.append('BASELINE_COMMIT_MISMATCH')
    except INPUT_ERRORS as exc:
        blockers.append('SOURCE_IDENTITY_UNREADABLE:'+type(exc).__name__)
    for name in [*BLOBS,'pattern_tr']:
        try:
            if name=='pattern_tr':
                expected=ast.parse(SHIM).body
            else:
                text=(root/'chartdesk'/(name+'.py')).read_text(encoding='utf-8')
                raw=text.encode('utf-8')
                if hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()!=BLOBS[name]:
                    blockers.append('SOURCE_BLOB_MISMATCH:'+name)
                expected=_projection(name,text)
        except INPUT_ERRORS as exc:
            blockers.append('SOURCE_PROJECTION_UNREADABLE:'+name+':'+type(exc).__name__)
            continue
        try:
            actual=_without_doc(ast.parse((VENDOR/(name+'.py')).read_text(encoding='utf-8')))
            if [_dump(n) for n in actual]!=[_dump(n) for n in expected]:
                blockers.append('VENDOR_AST_MISMATCH:'+name)
            else: checked.append(name)
        except INPUT_ERRORS as exc:
            blockers.append('VENDOR_UNREADABLE:'+name+':'+type(exc).__name__)
    for name,audit,arg in [('tree_tr',audit_tree_tr,parent),('pvsra',audit_pvsra,root)]:
        try:
            result=audit(arg)
            dependencies[name]=result
            blockers.extend('DEPENDENCY:'+name+':'+b for b in result['blockers'])
            if not result['source_subset_verified'] and not result['blockers']:
                blockers.append('DEPENDENCY:'+name+':NOT_VERIFIED')
        except INPUT_ERRORS as exc:
            blockers.append('DEPENDENCY:'+name+':UNREADABLE:'+type(exc).__name__)
    if not blockers: report.update(status='VERIFIED',source_subset_verified=True)
    return report
