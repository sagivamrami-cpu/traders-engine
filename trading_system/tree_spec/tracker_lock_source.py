"""Independent complete lock-policy AST audit; retained source is never executed."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess

from .tracker_admission_source import _dump, _git, _replace_exact, _selected, _without_doc

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "trading_system/tree_replay/_vendor/tracker_lock.py"
COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
BLOB = "b616b34022e436545d8c1daf85eced51614fd74e"
ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
          subprocess.SubprocessError)


def _replace_counted(tree, old, new, count):
    original = ast.parse(old, mode="eval").body
    replacement = ast.parse(new, mode="eval").body
    class Replace(ast.NodeTransformer):
        found = 0
        def visit(self, node):
            if _dump(node) == _dump(original):
                self.found += 1
                return copy.deepcopy(replacement)
            return super().visit(node)
    visitor = Replace()
    visitor.visit(tree)
    if visitor.found != count:
        raise ValueError(f"SUBSTITUTION_PRECONDITION:{old}:count={visitor.found}")


def _projection(text):
    timeout, resolve, stall, busy_error, busy, held, locked = _selected(text, [
        "LOCK_TIMEOUT_S", "RESOLVE_LOCK_WAIT_S", "LOCK_STALL_S", "LockBusy",
        "_busy_for", "_HELD", "_locked"])
    _replace_counted(busy, "time.time()", "self.source.now_epoch()", 2)
    _replace_exact(busy, "LOCK_BUSY.read_text()", "self.source.read_busy()")
    _replace_exact(busy, "LOCK_BUSY.write_text(str(self.source.now_epoch()))",
                   "self.source.write_busy(str(self.source.now_epoch()))")
    _replace_counted(locked, "_HELD", "self.held", 6)
    for old, new in [
        ("LOCK.parent.mkdir(parents=True, exist_ok=True)", "self.source.ensure_lock_directory()"),
        ('open(LOCK, "a+")', "self.source.open_lock()"),
        ("filelock.try_acquire(f, timeout=wait)", "self.source.try_acquire(f, timeout=wait)"),
        ("LOCK_BUSY.unlink(missing_ok=True)", "self.source.clear_busy()"),
        ("_busy_for()", "self._busy_for()"),
        ('print(f"[tracker] lock refused for {stuck:.0f}s -- treating the " "holder as hung and proceeding unlocked", file=sys.stderr, flush=True)',
         'self.source.warn(f"[tracker] lock refused for {stuck:.0f}s -- treating the " "holder as hung and proceeding unlocked")'),
        ("filelock.release(f)", "self.source.release(f)"),
    ]:
        _replace_exact(locked, old, new)
    _replace_exact(locked, "from . import filelock", None, statement=True)
    busy.args.args.insert(0, ast.arg(arg="self"))
    locked.args.args.insert(0, ast.arg(arg="self"))
    locked.name = "locked"
    cls = ast.parse("class TrackerLock:\n    def __init__(self, source):\n        self.source = source").body[0]
    # Original held initializer is an audited dependency, not a runtime-derived value.
    held.targets = [ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()),
                                  attr="held", ctx=ast.Store())]
    cls.body[0].body.append(held)
    cls.body.extend([busy, locked])
    imports = ast.parse("from __future__ import annotations\nfrom contextlib import contextmanager").body
    return imports + [timeout, resolve, stall, busy_error, cls]


def audit_tracker_lock_source(source_root):
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
            checked.extend(["tracker.lock_constants", "tracker.LockBusy",
                            "tracker._busy_for", "tracker._locked"])
    except ERRORS as exc:
        blockers.append(f"VENDOR_UNREADABLE:{type(exc).__name__}")
    if not blockers:
        report.update(status="VERIFIED", source_subset_verified=True)
    return report
