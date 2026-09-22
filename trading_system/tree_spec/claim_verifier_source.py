"""Independent fixed-source audit of original claim verification over offline ports."""
import ast
import hashlib
from pathlib import Path

from .tracker_admission_source import (
    INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _selected, _without_doc,
)
from .lifecycle_primitives_source import audit_lifecycle_primitives_source


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "trading_system/tree_replay/_vendor/claim_verifier.py"
COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
BLOB = "3329fdb71f8aebdf13a6fa823e8be0d85e1ced03"
SOURCE_SYMBOLS = ["TOL", "Verdict", "_tol", "_bars", "_binance_bars", "_covers",
    "_fill_index", "target", "_NOT_YET", "_closed_past", "_claim_clock",
    "_fill_unseen", "_frame", "_extreme", "fill", "stop", "check_message"]
PURE = ["TOL", "Verdict", "_tol", "_covers", "_fill_index", "_NOT_YET",
        "_closed_past", "_fill_unseen", "_frame", "_extreme"]
METHODS = ["_bars", "_binance_bars", "target", "_claim_clock", "fill", "stop", "check_message"]
EXPRESSIONS = {
    "_bars": [("_binance_bars(symbol, days)", "self._binance_bars(symbol, days)"),
        ('basis.fetch_corrected(symbol, "15m", days)', 'self.source.fetch_corrected(symbol, "15m", days)')],
    "_binance_bars": [('pd.Timestamp.now(tz="UTC")', 'pd.Timestamp(self.source.now_utc())'),
        ('_json.load(_rq.urlopen(url, timeout=15))', 'self.source.fetch_json(url, timeout=15)')],
    "target": [('_bars(trade["symbol"])', 'self._bars(trade["symbol"])'),
        ('_claim_clock(trade, "claim_ts")', 'self._claim_clock(trade, "claim_ts")')],
    "_claim_clock": [('pd.Timestamp.now(tz="UTC")', 'pd.Timestamp(self.source.now_utc())')],
    "fill": [('_bars(trade["symbol"])', 'self._bars(trade["symbol"])'),
        ('pd.Timestamp.now(tz="UTC")', 'pd.Timestamp(self.source.now_utc())')],
    "stop": [('_bars(trade["symbol"])', 'self._bars(trade["symbol"])'),
        ('_claim_clock(trade, "resolved_ts", "claim_ts")', 'self._claim_clock(trade, "resolved_ts", "claim_ts")')],
    "check_message": [("reached(trade)", "self.movement.reached(trade)"),
        ('target(trade, float(m.group(1).replace(",", "")))', 'self.target(trade, float(m.group(1).replace(",", "")))'),
        ("fill(trade)", "self.fill(trade)"), ("stop(trade)", "self.stop(trade)")],
}
STATEMENTS = {
    "_fill_index": [("from .tradeplan import entry_zone", "from .pricing import entry_zone")],
    "_binance_bars": [("import json as _json", None), ("import urllib.request as _rq", None)],
    "check_message": [("from .desk_success import reached", None)],
}


def _projection(text):
    selected = _selected(text, SOURCE_SYMBOLS)
    nodes = dict(zip(SOURCE_SYMBOLS, selected))
    for name, pairs in EXPRESSIONS.items():
        for old, new in pairs:
            _replace_exact(nodes[name], old, new)
    for name, pairs in STATEMENTS.items():
        for old, new in pairs:
            _replace_exact(nodes[name], old, new, statement=True)
    cls = ast.parse("class ClaimVerifier:\n    def __init__(self, source):\n        self.source = source\n        self.movement = DeskSuccess(source)").body[0]
    for name in METHODS:
        node = nodes[name]
        if not isinstance(node, ast.FunctionDef) or node.decorator_list or any(
                a.arg == "self" for a in node.args.args):
            raise ValueError("METHOD_SHAPE_MISMATCH:"+name)
        node.args.args.insert(0, ast.arg(arg="self"))
        cls.body.append(node)
    imports = ast.parse("from __future__ import annotations\nimport re\nfrom dataclasses import dataclass\nimport pandas as pd\nfrom .desk_success import DeskSuccess").body
    return imports + [nodes[n] for n in PURE] + [cls]


def audit_claim_verifier_source(source_root):
    """Inspect source/ASTs only; no import or execution of verifier or source repo."""
    blockers, checked, dependencies = [], [], {}
    report = dict(status="BLOCKED", source_subset_verified=False, blockers=blockers,
        checked_projections=checked, dependencies=dependencies,
        source_commits={"chart-desk": COMMIT}, ready_for_replay=False, ready_for_training=False)
    try:
        source_root = Path(source_root)
    except INPUT_ERRORS as exc:
        blockers.append("SOURCE_ROOT_INVALID:"+type(exc).__name__)
        return report
    try:
        root = source_root / "chart-desk"
        if Path(_git(root, "--show-toplevel")).resolve() != root.resolve():
            blockers.append("NOT_REPOSITORY_ROOT")
        if _git(root, "HEAD") != COMMIT:
            blockers.append("SOURCE_COMMIT_MISMATCH")
        baseline = _read_json(ROOT / "configs/trees/existing-alerts-baseline.json")
        if [r.get("commit") for r in baseline["repositories"] if r.get("name") == "chart-desk"] != [COMMIT]:
            blockers.append("BASELINE_COMMIT_MISMATCH")
    except INPUT_ERRORS as exc:
        blockers.append("SOURCE_IDENTITY_UNREADABLE:"+type(exc).__name__)
    try:
        text = (source_root / "chart-desk/chartdesk/verify.py").read_text(encoding="utf-8")
        raw = text.encode("utf-8")
        if hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest() != BLOB:
            blockers.append("SOURCE_BLOB_MISMATCH")
        expected = _projection(text)
    except INPUT_ERRORS as exc:
        blockers.append(f"SOURCE_PROJECTION_UNREADABLE:{type(exc).__name__}:{exc}")
    else:
        try:
            actual = _without_doc(ast.parse(RUNTIME.read_text(encoding="utf-8")))
            if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
                blockers.append("VENDOR_AST_MISMATCH")
            else:
                checked.append("claim_verifier")
        except INPUT_ERRORS as exc:
            blockers.append("VENDOR_UNREADABLE:"+type(exc).__name__)
    try:
        inherited = audit_lifecycle_primitives_source(source_root)
        dependencies["lifecycle_primitives"] = inherited
        if not inherited["source_subset_verified"]:
            blockers.extend("DEPENDENCY:"+b for b in inherited["blockers"])
            if not inherited["blockers"]:
                blockers.append("DEPENDENCY:NOT_VERIFIED")
    except INPUT_ERRORS as exc:
        blockers.append("DEPENDENCY_UNREADABLE:"+type(exc).__name__)
    if not blockers:
        report.update(status="VERIFIED", source_subset_verified=True)
    return report
