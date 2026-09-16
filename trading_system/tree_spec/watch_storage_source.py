"""Audit exact pinned watch main persistence statements without executing source."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

from .tracker_admission_source import _dump, _git, _replace_exact, _selected, _without_doc


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "trading_system/tree_replay/_vendor/watch_storage.py"
COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
BLOB = "f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b"
ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
          subprocess.SubprocessError)


def _projection(text):
    main, = _selected(text, ["main"])
    patterns = [
        "st = json.loads(STATE.read_text()) if STATE.exists() else {}",
        "STATE.parent.mkdir(exist_ok=True)",
        "STATE.write_text(json.dumps(st))",
    ]
    expected = [_dump(ast.parse(s).body[0]) for s in patterns]
    positions = [[i for i, n in enumerate(main.body) if _dump(n) == p] for p in expected]
    if [len(p) for p in positions] != [1, 1, 2]:
        raise ValueError("WATCH_PERSISTENCE_CARDINALITY_MISMATCH")
    load_i, directory_i = positions[0][0], positions[1][0]
    first_i, final_i = positions[2]
    if not load_i < directory_i == first_i-1 < final_i:
        raise ValueError("WATCH_PERSISTENCE_ORDER_MISMATCH")
    if final_i != len(main.body)-2 or _dump(main.body[-1]) != _dump(ast.parse("return 0").body[0]):
        raise ValueError("WATCH_FINAL_PERSISTENCE_BOUNDARY_MISMATCH")
    load, directory, first, final = [main.body[i] for i in (load_i, directory_i, first_i, final_i)]
    for old, new in [("STATE.exists()", "self.source.exists()"),
                     ("STATE.read_text()", "self.source.read_text()")]:
        _replace_exact(load, old, new)
    _replace_exact(directory, "STATE.parent.mkdir(exist_ok=True)",
                   "self.source.ensure_directory(exist_ok=True)")
    for node in (first, final):
        _replace_exact(node, "STATE.write_text(json.dumps(st))", "self.source.write_text(json.dumps(st))")
    module = ast.parse("import json\nclass WatchStorage:\n    def __init__(self, source):\n        self.source = source")
    for signature, body in [
        ("def load(self): pass", [load, ast.parse("return st").body[0]]),
        ("def save_before_producers(self, st): pass", [directory, first]),
        ("def save_final(self, st): pass", [final]),
    ]:
        method = ast.parse(signature).body[0]
        method.body = body
        module.body[1].body.append(method)
    return module.body


def audit_watch_storage_source(source_root):
    blockers, checked = [], []
    report = dict(status="BLOCKED", source_subset_verified=False, blockers=blockers,
        checked_projections=checked, source_commits={"chart-desk": COMMIT},
        ready_for_replay=False, ready_for_training=False)
    try:
        root = Path(source_root) / "chart-desk"
        if Path(_git(root, "--show-toplevel")).resolve() != root.resolve():
            blockers.append("NOT_REPOSITORY_ROOT")
        if _git(root, "HEAD") != COMMIT:
            blockers.append("SOURCE_COMMIT_MISMATCH")
        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
        if [r.get("commit") for r in baseline["repositories"] if r.get("name") == "chart-desk"] != [COMMIT]:
            blockers.append("BASELINE_COMMIT_MISMATCH")
        text = (root / "scripts/market_watch.py").read_text(encoding="utf-8")
        data = text.encode("utf-8")
        if hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest() != BLOB:
            blockers.append("SOURCE_BLOB_MISMATCH")
        expected = _projection(text)
    except ERRORS as exc:
        blockers.append(f"SOURCE_UNREADABLE:{type(exc).__name__}:{exc}")
        return report
    try:
        actual = _without_doc(ast.parse(RUNTIME.read_text(encoding="utf-8")))
        if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
            blockers.append("VENDOR_AST_MISMATCH")
        elif not blockers:
            checked.extend(["watch.load", "watch.save_before_producers", "watch.save_final"])
    except ERRORS as exc:
        blockers.append(f"VENDOR_UNREADABLE:{type(exc).__name__}")
    if not blockers:
        report.update(status="VERIFIED", source_subset_verified=True)
    return report
