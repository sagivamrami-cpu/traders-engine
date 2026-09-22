"""Inert retained-source proof for the changed-only tracker lifecycle caller."""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "trading_system/tree_replay/lifecycle_caller.py"
COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
BLOB = "b616b34022e436545d8c1daf85eced51614fd74e"
INPUT_ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
                subprocess.SubprocessError)
CHILD_AUDITS = {
    "lifecycle_gate_park": (
        "trading_system.tree_spec.lifecycle_gate_park_source",
        "audit_lifecycle_gate_park_source",
    ),
    "tracker_lock": (
        "trading_system.tree_spec.tracker_lock_source",
        "audit_tracker_lock_source",
    ),
}
_EXPECTED_CHILD_AUDITS = {
    "lifecycle_gate_park": (
        "trading_system.tree_spec.lifecycle_gate_park_source",
        "audit_lifecycle_gate_park_source",
    ),
    "tracker_lock": (
        "trading_system.tree_spec.tracker_lock_source",
        "audit_tracker_lock_source",
    ),
}

_RUNTIME = '''from __future__ import annotations
from ._vendor.lifecycle_gate import LifecycleGate
from ._vendor.tracker_lock import LockBusy

class TrackerLifecycleCaller:
    def __init__(self, source):
        self.source = source
        self.gate = LifecycleGate(source)

    def _run(self, resolve):
        state = self.source.load()
        if not state:
            return []
        out, changed = self._result(resolve(state))
        if not changed:
            return out
        return self._commit(out, state)

    @staticmethod
    def _result(result):
        if not isinstance(result, tuple) or len(result) != 2:
            raise TypeError("resolver must return (list[tuple[str, bool]], bool)")
        out, changed = result
        if not isinstance(out, list) or not isinstance(changed, bool):
            raise TypeError("resolver must return (list[tuple[str, bool]], bool)")
        if any(not isinstance(message, tuple) or len(message) != 2
               or not isinstance(message[0], str) or not isinstance(message[1], bool)
               for message in out):
            raise TypeError("resolver must return (list[tuple[str, bool]], bool)")
        return out, changed

    def _commit(self, out, state):
        out = self.gate._persist_gated_lifecycle(out, state)
        self.source.save(state)
        return out

    def check(self, resolve):
        return self._run(resolve)

    def _check_live_locked(self, resolve):
        return self._run(resolve)

    def check_live(self, resolve):
        try:
            with self.source.locked(skip_if_busy=True):
                return self._check_live_locked(resolve)
        except LockBusy:
            return []
'''


def _dump(node):
    return ast.dump(node, include_attributes=False)


class _RemoveDocs(ast.NodeTransformer):
    def _body(self, node):
        self.generic_visit(node)
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body = node.body[1:]
        return node

    visit_Module = _body
    visit_FunctionDef = _body
    visit_ClassDef = _body


def _without_docs(tree):
    return _RemoveDocs().visit(copy.deepcopy(tree))


def _git(path, arg):
    return subprocess.run(["git", "-C", str(path), "rev-parse", arg], check=True,
                          text=True, capture_output=True).stdout.strip()


def _child_audit(name, source_root):
    module_name, function_name = CHILD_AUDITS[name]
    return getattr(importlib.import_module(module_name), function_name)(source_root)


def _function(tree, name):
    found = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(found) != 1:
        raise ValueError(f"SOURCE_FUNCTION_SET_MISMATCH:{name}")
    return found[0]


def _tail_matches(node):
    expected = ast.parse('''
if changed:
    out = _persist_gated_lifecycle(out, d)
    _save(d)
return out
''').body
    return [_dump(row) for row in node.body[-2:]] == [_dump(row) for row in expected]


def _wrapper_matches(node):
    expected = ast.parse('''
def check_live() -> list[tuple[str, bool]]:
    try:
        with _locked(skip_if_busy=True):
            return _check_live_locked()
    except LockBusy:
        return []
''').body[0]
    actual = _without_docs(node)
    return _dump(actual) == _dump(expected)


def _audit_source(text, blockers, checked):
    tree = ast.parse(text)
    for name in ("check", "_check_live_locked"):
        if _tail_matches(_function(tree, name)):
            checked.append(f"tracker.{name}.changed_tail")
        else:
            blockers.append(f"SOURCE_TAIL_MISMATCH:{name}")
    if _wrapper_matches(_function(tree, "check_live")):
        checked.append("tracker.check_live.lockbusy_wrapper")
    else:
        blockers.append("SOURCE_WRAPPER_MISMATCH:check_live")


def _audit_runtime(blockers, checked):
    actual = ast.parse(RUNTIME.read_text(encoding="utf-8"))
    expected = ast.parse(_RUNTIME)
    if _dump(_without_docs(actual)) == _dump(_without_docs(expected)):
        checked.append("tree_replay.TrackerLifecycleCaller")
    else:
        blockers.append("RUNTIME_AST_MISMATCH:tracker_lifecycle_caller")


def _valid_child_report(child):
    return (isinstance(child, dict)
            and type(child.get("source_subset_verified")) is bool
            and isinstance(child.get("blockers"), list)
            and all(isinstance(row, str) for row in child["blockers"]))


def audit_tracker_lifecycle_caller_source(source_root):
    """Parse retained tracker text and actual child proofs without executing source."""
    blockers, checked, dependencies = [], [], {}
    report = lambda: {
        "status": "BLOCKED" if blockers else "VERIFIED",
        "source_subset_verified": not blockers,
        "blockers": blockers,
        "checked_projections": checked,
        "dependencies": dependencies,
        "source_commits": {"chart-desk": COMMIT},
        "ready_for_replay": False,
        "ready_for_training": False,
    }
    try:
        source_root = Path(source_root)
        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
        if [row.get("commit") for row in baseline["repositories"] if row.get("name") == "chart-desk"] != [COMMIT]:
            blockers.append("BASELINE_COMMIT_MISMATCH")
        repo = source_root / "chart-desk"
        if Path(_git(repo, "--show-toplevel")).resolve() != repo.resolve():
            blockers.append("NOT_REPOSITORY_ROOT")
        if _git(repo, "HEAD") != COMMIT:
            blockers.append("SOURCE_COMMIT_MISMATCH")
        text = (repo / "chartdesk/tracker.py").read_text(encoding="utf-8")
        data = text.encode("utf-8")
        if hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != BLOB:
            blockers.append("SOURCE_BLOB_MISMATCH:tracker.py")
        _audit_source(text, blockers, checked)
    except INPUT_ERRORS as exc:
        blockers.append(f"SOURCE_UNREADABLE:{type(exc).__name__}")
        return report()
    try:
        _audit_runtime(blockers, checked)
    except INPUT_ERRORS as exc:
        blockers.append(f"RUNTIME_UNREADABLE:{type(exc).__name__}")
    for name, expected_audit in _EXPECTED_CHILD_AUDITS.items():
        if CHILD_AUDITS.get(name) != expected_audit:
            blockers.append(f"CHILD_AUDIT_IDENTITY_MISMATCH:{name}")
            continue
        try:
            child = _child_audit(name, source_root)
            if not _valid_child_report(child):
                raise TypeError("CHILD_REPORT_SHAPE")
            dependencies[name] = child
            blockers.extend(f"DEPENDENCY:{name}:{row}" for row in child["blockers"])
            if not child["source_subset_verified"] and not child["blockers"]:
                blockers.append(f"DEPENDENCY:{name}:NOT_VERIFIED")
        except Exception as exc:
            blockers.append(f"DEPENDENCY:{name}:UNREADABLE:{type(exc).__name__}")
    return report()
