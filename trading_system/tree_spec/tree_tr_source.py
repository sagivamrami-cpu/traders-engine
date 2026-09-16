"""Inert whole-module audit of TR vector memory and daily pivots."""
import ast
import hashlib
from pathlib import Path

from tools.check_reversal_source_parity import check_source_parity as audit_pvsra
from .tracker_admission_source import (
    INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _selected, _without_doc,
)

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/'trading_system/tree_replay/_vendor/tree_tr.py'
COMMIT='68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
BLOB='8297c712d20404880d4d8949e96efbf48613909c'
SIGNATURE="""def vector_zones(df: pd.DataFrame, pv: pd.DataFrame | None = None, *,
    zone_from: str = 'body', cleared_by: str = 'wick', max_zones: int = 500,
    auction: bool | pd.Series = False, session_tz: str = A.DEFAULT_TZ) -> pd.DataFrame: pass"""


def _projection(text):
    nodes=_selected(text,['vector_zones','daily_pivots'])
    node=nodes[0]
    signature=ast.parse(SIGNATURE).body[0]
    if not isinstance(node,ast.FunctionDef) or node.decorator_list or (
        _dump(node.args)!=_dump(signature.args) or _dump(node.returns)!=_dump(signature.returns)):
        raise ValueError('SOURCE_VECTOR_SIGNATURE_MISMATCH')
    node.args.kwonlyargs=node.args.kwonlyargs[:-2]
    node.args.kw_defaults=node.args.kw_defaults[:-2]
    _replace_exact(node,'pvsra(df, auction=auction, session_tz=session_tz)','pvsra(df)')
    return ast.parse('import pandas as pd\nfrom .pvsra import pvsra').body+nodes


def audit_tree_tr_source(source_root):
    """Verify pinned source and actual PVSRA closure; do not execute either."""
    blockers,checked,dependencies=[],[],{}
    report=dict(status='BLOCKED',source_subset_verified=False,blockers=blockers,
        checked_projections=checked,dependencies=dependencies,
        source_commits={'chart-desk':COMMIT},ready_for_replay=False,ready_for_training=False)
    try:
        root=Path(source_root)/'chart-desk'
    except INPUT_ERRORS as exc:
        blockers.append('SOURCE_ROOT_INVALID:'+type(exc).__name__)
        return report
    try:
        if Path(_git(root,'--show-toplevel')).resolve()!=root.resolve():
            blockers.append('NOT_REPOSITORY_ROOT')
        if _git(root,'HEAD')!=COMMIT:
            blockers.append('SOURCE_COMMIT_MISMATCH')
        baseline=_read_json(ROOT/'configs/trees/existing-alerts-baseline.json')
        if [r.get('commit') for r in baseline['repositories'] if r.get('name')=='chart-desk']!=[COMMIT]:
            blockers.append('BASELINE_COMMIT_MISMATCH')
    except INPUT_ERRORS as exc:
        blockers.append('SOURCE_IDENTITY_UNREADABLE:'+type(exc).__name__)
    try:
        text=(root/'chartdesk/tr.py').read_text(encoding='utf-8')
        raw=text.encode('utf-8')
        if hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()!=BLOB:
            blockers.append('SOURCE_BLOB_MISMATCH:tr.py')
        expected=_projection(text)
    except INPUT_ERRORS as exc:
        blockers.append('SOURCE_PROJECTION_UNREADABLE:'+type(exc).__name__)
    else:
        try:
            actual=_without_doc(ast.parse(RUNTIME.read_text(encoding='utf-8')))
            if [_dump(n) for n in actual]!=[_dump(n) for n in expected]:
                blockers.append('VENDOR_AST_MISMATCH')
            else:
                checked.append('tree_tr')
        except INPUT_ERRORS as exc:
            blockers.append('VENDOR_UNREADABLE:'+type(exc).__name__)
    try:
        result=audit_pvsra(root)
        dependencies['pvsra']=result
        blockers.extend('DEPENDENCY:pvsra:'+b for b in result['blockers'])
        if not result['source_subset_verified'] and not result['blockers']:
            blockers.append('DEPENDENCY:pvsra:NOT_VERIFIED')
    except INPUT_ERRORS as exc:
        blockers.append('DEPENDENCY:pvsra:UNREADABLE:'+type(exc).__name__)
    if not blockers:
        report.update(status='VERIFIED',source_subset_verified=True)
    return report
