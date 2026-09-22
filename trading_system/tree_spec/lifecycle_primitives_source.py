"""Independently pin and audit inert lifecycle source, complete projections and dependencies."""
import ast
import hashlib
from pathlib import Path

from .tracker_admission_source import (
    INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _selected, _without_doc,
    audit_tracker_admission_source,
)


ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "trading_system/tree_replay/_vendor"
COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
BLOBS = {
    "tracker.py": "b616b34022e436545d8c1daf85eced51614fd74e",
    "desk_success.py": "d2b2fdb2889841f587338e56041ffdc8df6c298c",
    "voice.py": "46fc6912ed8914b54209f9c08c12de9f48a19059",
}
BAR_SYMBOLS = ["_fill_on_tape", "_position_extremes", "position_bars", "_open_extremes", "_entry_band"]
METHODS = ["reached", "observe", "observe_bars", "classification", "stop_note"]
# Exact expressions once per named function, not a broad name-based rewrite.
EXPRESSIONS = {
    "reached": [("time.time()", "self.source.now_epoch()")],
    "observe": [("reached(t)", "self.reached(t)"),
                ("reached(candidate)", "self.reached(candidate)"),
                ("time.time()", "self.source.now_epoch()")],
    "observe_bars": [("reached(t)", "self.reached(t)"),
        ('tracker.pd.Timestamp.now(tz="UTC")', 'pd.Timestamp(self.source.now_utc())'),
        ('observe(t, float(hits.loc[at, column]), time.time(), "verified_post_fill_bars")',
         'self.observe(t, float(hits.loc[at, column]), self.source.now_epoch(), "verified_post_fill_bars")')],
    "classification": [("reached(t)", "self.reached(t)")],
    "stop_note": [("reached(t)", "self.reached(t)")],
}


def _bars_projection(text):
    nodes = _selected(text, BAR_SYMBOLS)
    _replace_exact(nodes[-1], "from .tradeplan import entry_zone",
                   "from .pricing import entry_zone", statement=True)
    return ast.parse("import pandas as pd").body + nodes


def _success_projection(text):
    nodes = _selected(text, ["VERSION", "FLOOR", "minimum"]+METHODS)
    _replace_exact(nodes[2], "from .basis import canonical_symbol",
                   "from .basis_symbols import canonical_symbol", statement=True)
    cls = ast.parse("class DeskSuccess:\n    def __init__(self, source):\n        self.source = source").body[0]
    for name, node in zip(METHODS, nodes[3:]):
        if not isinstance(node, ast.FunctionDef) or node.decorator_list or any(
                arg.arg == "self" for arg in node.args.args):
            raise ValueError("METHOD_SHAPE_MISMATCH:"+name)
        for old, new in EXPRESSIONS[name]:
            _replace_exact(node, old, new)
        if name == "observe_bars":
            _replace_exact(node, "from . import tracker", "from . import lifecycle_bars as tracker", statement=True)
        node.args.args.insert(0, ast.arg(arg="self"))
        cls.body.append(node)
    imports = ast.parse("from __future__ import annotations\nimport math\nimport pandas as pd\nfrom . import lifecycle_voice as voice").body
    return imports + nodes[:3] + [cls]


def audit_lifecycle_primitives_source(source_root):
    """Only source inspection: never import or execute retained chart-desk code."""
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
    for file, candidate, project in [
        ("tracker.py", "lifecycle_bars", _bars_projection),
        ("desk_success.py", "desk_success", _success_projection),
        ("voice.py", "lifecycle_voice", lambda text: _without_doc(ast.parse(text))),
    ]:
        try:
            text = (source_root / "chart-desk/chartdesk" / file).read_text(encoding="utf-8")
            raw = text.encode("utf-8")
            digest = hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
            if digest != BLOBS[file]:
                blockers.append("SOURCE_BLOB_MISMATCH:"+file)
                continue
            expected = project(text)
        except INPUT_ERRORS as exc:
            blockers.append(f"SOURCE_PROJECTION_UNREADABLE:{file}:{type(exc).__name__}:{exc}")
            continue
        try:
            actual = _without_doc(ast.parse((VENDOR / (candidate+".py")).read_text(encoding="utf-8")))
            if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
                blockers.append("VENDOR_AST_MISMATCH:"+candidate+".py")
            else:
                checked.append(candidate)
        except INPUT_ERRORS as exc:
            blockers.append(f"VENDOR_UNREADABLE:{candidate}.py:{type(exc).__name__}")
    try:
        inherited = audit_tracker_admission_source(source_root)
        dependencies["tracker_admission"] = inherited
        if not inherited["source_subset_verified"]:
            blockers.extend("DEPENDENCY:"+b for b in inherited["blockers"])
            if not inherited["blockers"]:
                blockers.append("DEPENDENCY:NOT_VERIFIED")
    except INPUT_ERRORS as exc:
        blockers.append("DEPENDENCY_UNREADABLE:"+type(exc).__name__)
    if not blockers:
        report.update(status="VERIFIED", source_subset_verified=True)
    return report
