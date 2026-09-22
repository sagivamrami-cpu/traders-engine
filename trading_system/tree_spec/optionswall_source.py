"""Inert full-source audit of options artifacts, fixed mapping and clock ports."""
import ast
import hashlib
from pathlib import Path

from .tracker_admission_source import INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _without_doc

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/'trading_system/tree_replay/_vendor/optionswall.py'
COMMIT='68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
BLOB='c7d27ca396c162f6997b2a72bbd035ed6477e05b'
SOURCE_IMPORTS='''from __future__ import annotations
import datetime as dt
import glob
import json
import math
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from .workspace import repo'''
IMPORTS='''from __future__ import annotations
import datetime as dt
import json
import math
from dataclasses import dataclass
from zoneinfo import ZoneInfo
import pandas as pd
from io import StringIO'''
PHYSICAL_GLOBALS='''REPORTS = str(repo("options-desk") / "out" / "report-*.json")
TV_DIR = Path(__file__).resolve().parent.parent / "data" / "tv"'''
INVENTORY=['REPORTS','TV_DIR','MAX_QUOTE_AGE_MIN','MAX_ANCHOR_GAP_MIN','ETF_OF','TV_FILE_OF',
    'Walls','OptionsStatus','_timestamp','_finite','_anchor','_front_expiry','status','load']
SIGNATURES='''def _anchor(symbol: str, market_asof: pd.Timestamp) -> tuple[float, pd.Timestamp] | None: pass
def status(symbol: str, _current_spot: float | None=None, *, now: pd.Timestamp | None=None) -> OptionsStatus: pass
def load(symbol: str, spot: float) -> Walls | None: pass'''
REPLACEMENTS={
    '_anchor':[
        ('TV_DIR / TV_FILE_OF[symbol]','TV_FILE_OF[symbol]'),
        ('pd.read_csv(path)','pd.read_csv(StringIO(self.source.read_tv_csv(path)))')],
    'status':[
        ('glob.glob(REPORTS)','self.source.list_reports()'),
        ("Path(files[-1]).read_text(encoding='utf-8')",'self.source.read_report(files[-1])'),
        ("pd.Timestamp.now(tz='UTC')",'pd.Timestamp(self.source.now_utc())'),
        ('_anchor(symbol, market_asof)','self._anchor(symbol, market_asof)')],
    'load':[('status(symbol, spot)','self.status(symbol, spot)')],
}


def _name(node):
    if isinstance(node,(ast.ClassDef,ast.FunctionDef)):
        return node.name
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
        return node.targets[0].id
    raise ValueError('UNEXPECTED_SOURCE_NODE')


def _projection(text):
    nodes=_without_doc(ast.parse(text))
    imports=ast.parse(SOURCE_IMPORTS).body
    if [_dump(n) for n in nodes[:len(imports)]]!=[_dump(n) for n in imports]:
        raise ValueError('SOURCE_IMPORT_MISMATCH')
    nodes=nodes[len(imports):]
    if [_name(n) for n in nodes]!=INVENTORY:
        raise ValueError('SOURCE_INVENTORY_MISMATCH')
    if [_dump(n) for n in nodes[:2]]!=[_dump(n) for n in ast.parse(PHYSICAL_GLOBALS).body]:
        raise ValueError('SOURCE_PHYSICAL_GLOBAL_MISMATCH')
    signatures={n.name:n for n in ast.parse(SIGNATURES).body}
    pure,methods=[],[]
    for node in nodes[2:]:
        if not isinstance(node,ast.FunctionDef) or node.name not in signatures:
            pure.append(node)
            continue
        sig=signatures[node.name]
        if node.decorator_list or _dump(node.args)!=_dump(sig.args) or _dump(node.returns)!=_dump(sig.returns):
            raise ValueError('SOURCE_SIGNATURE_MISMATCH:'+node.name)
        node.args.args.insert(0,ast.arg(arg='self'))
        for old,new in REPLACEMENTS[node.name]:
            _replace_exact(node,old,new)
        methods.append(node)
    if [n.name for n in methods]!=list(signatures):
        raise ValueError('SOURCE_METHOD_ORDER')
    ctor=ast.parse('def __init__(self, source):\n    self.source = source').body
    reader=ast.ClassDef(name='OptionsWallReader',bases=[],keywords=[],body=ctor+methods,decorator_list=[])
    return ast.parse(IMPORTS).body+pure+[reader]


def audit_optionswall_source(source_root):
    """Certify projection only; no historical artifact or feed readiness claim."""
    blockers,checked=[],[]
    report=dict(status='BLOCKED',source_subset_verified=False,blockers=blockers,
        checked_projections=checked,source_commits={'chart-desk':COMMIT},
        ready_for_replay=False,ready_for_training=False)
    try:
        root=Path(source_root)/'chart-desk'
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
    try:
        text=(root/'chartdesk/optionswall.py').read_text(encoding='utf-8')
        raw=text.encode('utf-8')
        if hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()!=BLOB:
            blockers.append('SOURCE_BLOB_MISMATCH')
        expected=_projection(text)
    except INPUT_ERRORS as exc:
        blockers.append('SOURCE_PROJECTION_UNREADABLE:'+type(exc).__name__)
    else:
        try:
            actual=_without_doc(ast.parse(RUNTIME.read_text(encoding='utf-8')))
            if [_dump(n) for n in actual]!=[_dump(n) for n in expected]: blockers.append('VENDOR_AST_MISMATCH')
            else: checked.append('optionswall')
        except INPUT_ERRORS as exc:
            blockers.append('VENDOR_UNREADABLE:'+type(exc).__name__)
    if not blockers: report.update(status='VERIFIED',source_subset_verified=True)
    return report
