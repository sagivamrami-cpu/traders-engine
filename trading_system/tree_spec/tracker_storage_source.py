"""Independent full-module AST audit; retained source is never executed."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

from .tracker_admission_source import _dump, _git, _replace_exact, _selected, _without_doc


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "trading_system/tree_replay/_vendor/tracker_storage.py"
COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
BLOB = "b616b34022e436545d8c1daf85eced51614fd74e"
ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
          subprocess.SubprocessError)


def _projection(text):
    load, save = _selected(text, ["_load", "_save"])
    for node in (load, save):
        for old, new in [("STATE.exists()", "self.source.exists()"),
                         ("STATE.read_text()", "self.source.read_text()")]:
            _replace_exact(node, old, new)
        node.args.args.insert(0, ast.arg(arg="self"))
    load.name, save.name = "load", "save"
    for old, new in [
        ('STATE == ROOT / "out" / "open_trades.json" and ("unittest" in sys.modules or "pytest" in sys.modules)',
         "self.source.is_live_test_target()"),
        ("_audit_creation(cur, d)", "self.source.audit_creation(cur, d)"),
        ("time.time()", "self.source.now_epoch()"),
        ('STATE.with_suffix(f".rejected-{int(self.source.now_epoch())}")',
         'self.source.quarantine_path(f".rejected-{int(self.source.now_epoch())}")'),
        ("_atomic_write(STATE, json.dumps(d, ensure_ascii=False, indent=1))",
         "self.source.atomic_write(json.dumps(d, ensure_ascii=False, indent=1))"),
    ]:
        _replace_exact(save, old, new)
    _replace_exact(save, "from .basis import _atomic_write", None, statement=True)
    expected = ast.parse("import json\nclass TrackerStorage:\n    def __init__(self, source):\n        self.source = source")
    expected.body[1].body.extend([load, save])
    return expected.body


def audit_tracker_storage_source(source_root):
    blockers, checked = [], []
    report = {"status": "BLOCKED", "source_subset_verified": False,
        "blockers": blockers, "checked_projections": checked,
        "source_commits": {"chart-desk": COMMIT},
        "ready_for_replay": False, "ready_for_training": False}
    try:
        root = Path(source_root) / "chart-desk"
        if Path(_git(root, "--show-toplevel")).resolve() != root.resolve():
            blockers.append("NOT_REPOSITORY_ROOT")
        if _git(root, "HEAD") != COMMIT:
            blockers.append("SOURCE_COMMIT_MISMATCH")
        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
        if [r.get("commit") for r in baseline["repositories"] if r.get("name") == "chart-desk"] != [COMMIT]:
            blockers.append("BASELINE_COMMIT_MISMATCH")
        text = (root / "chartdesk/tracker.py").read_text(encoding="utf-8")
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
            checked.extend(["tracker._load", "tracker._save"])
    except ERRORS as exc:
        blockers.append(f"VENDOR_UNREADABLE:{type(exc).__name__}")
    if not blockers:
        report.update(status="VERIFIED", source_subset_verified=True)
    return report
