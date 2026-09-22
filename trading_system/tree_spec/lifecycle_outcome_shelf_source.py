"""Inert retained-source proof for tracker outcome and shelf helpers."""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
BLOB = "b616b34022e436545d8c1daf85eced51614fd74e"
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_outcome_shelf.py"
SYMBOLS = (
    "OUTCOMES", "EXPIRE_H", "EXPIRE_BY_STYLE", "_outcome", "_atomic_json",
    "has_open", "_expire_h", "SHELF", "SHELF_MAX_H", "REVIVAL_COOLDOWN_S",
    "_shelve",
)
_EXPECTED_SYMBOLS = (
    "OUTCOMES", "EXPIRE_H", "EXPIRE_BY_STYLE", "_outcome", "_atomic_json",
    "has_open", "_expire_h", "SHELF", "SHELF_MAX_H", "REVIVAL_COOLDOWN_S",
    "_shelve",
)
SIGNATURES = (
    "def _outcome(row: dict, *, event_ts: float | None = None) -> None: pass",
    "def _atomic_json(path, obj) -> None: pass",
    "def has_open(symbol: str, direction: str | None = None, *, state: dict | None = None) -> bool: pass",
    "def _expire_h(t: dict) -> float: pass",
    "def _shelve(t: dict) -> None: pass",
)
PREFIX = """from __future__ import annotations
import json
from pathlib import PurePosixPath
from .tracker_admission import TrackerAdmission
"""
INPUT_ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError,
                SyntaxError, UnicodeError, subprocess.SubprocessError)
CHILD_AUDITS = {
    "tracker_admission": (
        "trading_system.tree_spec.tracker_admission_source",
        "audit_tracker_admission_source",
    ),
    "lifecycle_gate": (
        "trading_system.tree_spec.lifecycle_gate_park_source",
        "audit_lifecycle_gate_park_source",
    ),
}
_EXPECTED_CHILD_AUDITS = (
    (
        "tracker_admission",
        "trading_system.tree_spec.tracker_admission_source",
        "audit_tracker_admission_source",
    ),
    (
        "lifecycle_gate",
        "trading_system.tree_spec.lifecycle_gate_park_source",
        "audit_lifecycle_gate_park_source",
    ),
)
_REQUIRED_CHILD_PROJECTIONS = (
    (
        "tracker_admission",
        (
            "trading_system/tree_replay/_vendor/tracker_admission.py",
            "trading_system/tree_replay/_vendor/tracker_symbols.py",
            "trading_system/tree_replay/_vendor/pricing.py",
            "trading_system/tree_replay/_vendor/basis_symbols.py",
            "trading_system/tree_replay/_vendor/quarters.py",
            "trading_system/tree_replay/_vendor/admission_quality.py",
            "trading_system/tree_replay/_vendor/admission_swing.py",
        ),
    ),
    ("lifecycle_gate", ("lifecycle_gate",)),
)
_REQUIRED_CHILD_COMMITS = (
    (
        "tracker_admission",
        (
            ("chart-desk", "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"),
            ("trading-floor", "d827dd792cbd1d396b4ee325879c63e57388e07a"),
        ),
    ),
    (
        "lifecycle_gate",
        (("chart-desk", "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"),),
    ),
)


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _name(node):
    if isinstance(node, ast.FunctionDef):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None


def _signature(node, expected):
    actual_return = None if node.returns is None else _dump(node.returns)
    expected_return = None if expected.returns is None else _dump(expected.returns)
    if (
        not isinstance(node, ast.FunctionDef)
        or node.name != expected.name
        or _dump(node.args) != _dump(expected.args)
        or actual_return != expected_return
    ):
        raise ValueError(f"SOURCE_SIGNATURE_MISMATCH:{expected.name}")


def _replace(tree, old, new, *, count=1, statement=False):
    before = ast.parse(old).body[0] if statement else ast.parse(old, mode="eval").body
    after = None if new is None else (
        ast.parse(new).body[0] if statement else ast.parse(new, mode="eval").body
    )

    class Replace(ast.NodeTransformer):
        seen = 0

        def visit(self, node):
            if _dump(node) == _dump(before):
                self.seen += 1
                return copy.deepcopy(after)
            return super().visit(node)

    visitor = Replace()
    result = visitor.visit(tree)
    if visitor.seen != count:
        raise ValueError(
            f"SUBSTITUTION_PRECONDITION:{old}:count={visitor.seen}:expected={count}"
        )
    return result


def _rename_name(tree, old, new, *, count):
    class Rename(ast.NodeTransformer):
        seen = 0

        def visit_Name(self, node):
            if node.id == old:
                self.seen += 1
                return ast.copy_location(ast.Name(id=new, ctx=node.ctx), node)
            return node

    visitor = Rename()
    result = visitor.visit(tree)
    if visitor.seen != count:
        raise ValueError(f"RENAME_PRECONDITION:{old}:count={visitor.seen}:expected={count}")
    return result


class _RemoveDocs(ast.NodeTransformer):
    def _body(self, node):
        self.generic_visit(node)
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            node.body = node.body[1:]
        return node

    visit_Module = _body
    visit_FunctionDef = _body
    visit_ClassDef = _body


def _without_docs(tree):
    return _RemoveDocs().visit(copy.deepcopy(tree))


def _git(path, arg):
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", arg],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _child_audit(name, source_root):
    module_name, function_name = CHILD_AUDITS[name]
    module = importlib.import_module(module_name)
    return getattr(module, function_name)(source_root)


def _valid_child_report(expected_projections, expected_commits, child):
    if (
        not isinstance(child, dict)
        or type(child.get("source_subset_verified")) is not bool
        or not isinstance(child.get("blockers"), list)
        or not all(isinstance(row, str) for row in child["blockers"])
    ):
        return False
    try:
        json.dumps(child, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except Exception:
        return False
    if not child["source_subset_verified"]:
        return child.get("status") == "BLOCKED" and bool(child["blockers"])
    return (
        child.get("status") == "VERIFIED"
        and child["blockers"] == []
        and child.get("checked_projections") == list(expected_projections)
        and child.get("source_commits") == dict(expected_commits)
        and child.get("ready_for_replay") is False
        and child.get("ready_for_training") is False
    )


def _projection(text):
    if SYMBOLS != _EXPECTED_SYMBOLS:
        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
    selected = [node for node in ast.parse(text).body if _name(node) in SYMBOLS]
    if tuple(_name(node) for node in selected) != SYMBOLS:
        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
    nodes = {_name(node): copy.deepcopy(node) for node in selected}
    for signature in map(lambda item: ast.parse(item).body[0], SIGNATURES):
        node = nodes[signature.name]
        if (
            not isinstance(node, ast.FunctionDef)
            or [_dump(row) for row in node.decorator_list]
            != [_dump(row) for row in signature.decorator_list]
        ):
            raise ValueError(f"SOURCE_DECORATOR_MISMATCH:{signature.name}")
        _signature(node, signature)

    nodes["OUTCOMES"] = ast.parse(
        'OUTCOMES = PurePosixPath("chart-desk/out/trade_outcomes.jsonl")'
    ).body[0]
    nodes["SHELF"] = ast.parse(
        'SHELF = PurePosixPath("chart-desk/out/shelved_trades.json")'
    ).body[0]
    for name, rows in {
        "_outcome": (
            ("OUTCOMES.parent.mkdir(parents=True, exist_ok=True)",
             "self.source.outcomes_mkdir(self.OUTCOMES.parent.as_posix(), parents=True, exist_ok=True)", False),
            ("time.time()", "self.source.now_epoch()", False),
            ('OUTCOMES.open("a", encoding="utf-8")',
             'self.source.open_outcomes("a", encoding="utf-8")', False),
        ),
        "_expire_h": (
            ("EXPIRE_BY_STYLE[\"tree\"]", "self.EXPIRE_BY_STYLE[\"tree\"]", False),
            ("EXPIRE_BY_STYLE.get(style, EXPIRE_H)", "self.EXPIRE_BY_STYLE.get(style, self.EXPIRE_H)", False),
        ),
        "_shelve": (
            ('SHELF.read_text(encoding="utf-8")', 'self.source.shelf_text(encoding="utf-8")', False),
            ("SHELF.exists()", "self.source.shelf_exists()", False),
            ("time.time()", "self.source.now_epoch()", False),
            ("_atomic_json(SHELF, d)", "self._atomic_json(self.SHELF, d)", False),
        ),
        "_atomic_json": (
            ("import os", None, True),
            ("import tempfile", None, True),
            ("path.parent.mkdir(parents=True, exist_ok=True)",
             "self.source.atomic_mkdir(path.parent.as_posix(), parents=True, exist_ok=True)", False),
            ("tempfile.mkstemp(dir=str(path.parent), suffix=\".tmp\")",
             "self.source.atomic_mkstemp(path.parent.as_posix(), suffix=\".tmp\")", False),
            ('os.fdopen(fd, "w", encoding="utf-8")',
             'self.source.atomic_fdopen(fd, "w", encoding="utf-8")', False),
            ("os.fsync(fh.fileno())", "self.source.atomic_fsync(fh)", False),
            ("os.replace(tmp, path)", "self.source.atomic_replace(tmp, path.as_posix())", False),
            ("os.unlink(tmp)", "self.source.atomic_unlink(tmp)", False),
        ),
    }.items():
        for old, new, statement in rows:
            nodes[name] = _replace(nodes[name], old, new, statement=statement)
    nodes["_outcome"] = _rename_name(nodes["_outcome"], "f", "fh", count=2)

    has_open = nodes["has_open"]
    has_open.body = ast.parse(
        "return self.admission.has_open(symbol, direction, state=state)"
    ).body
    constructor = ast.parse("""class LifecycleOutcomeShelf:
    def __init__(self, source):
        self.source = source
        self.admission = TrackerAdmission(source)
""").body[0].body[0]
    cls = ast.parse("class LifecycleOutcomeShelf:\n    pass").body[0]
    cls.body = []
    for name in ("OUTCOMES", "EXPIRE_H", "EXPIRE_BY_STYLE"):
        cls.body.append(nodes[name])
    cls.body.append(constructor)
    for name in ("_outcome", "_atomic_json", "has_open", "_expire_h", "SHELF",
                 "SHELF_MAX_H", "REVIVAL_COOLDOWN_S", "_shelve"):
        node = nodes[name]
        if isinstance(node, ast.FunctionDef):
            node.args.args.insert(0, ast.arg(arg="self"))
        cls.body.append(node)
    return ast.Module(body=ast.parse(PREFIX).body + [cls], type_ignores=[])


def _report(blockers, checked, dependencies):
    return {
        "status": "BLOCKED" if blockers else "VERIFIED",
        "source_subset_verified": not blockers,
        "blockers": blockers,
        "checked_projections": checked,
        "dependencies": dependencies,
        "source_commits": {"chart-desk": COMMIT},
        "ready_for_replay": False,
        "ready_for_training": False,
    }


def audit_lifecycle_outcome_shelf_source(source_root) -> dict:
    """Check the pinned source projection and real inherited audits, fail closed."""
    blockers, checked, dependencies = [], [], {}
    try:
        source_root = Path(source_root)
        baseline = _read_json(ROOT / "configs/trees/existing-alerts-baseline.json")
        commits = [
            row.get("commit") for row in baseline["repositories"]
            if row.get("name") == "chart-desk"
        ]
        if commits != [COMMIT]:
            blockers.append("BASELINE_COMMIT_MISMATCH")
        repo = source_root / "chart-desk"
        if Path(_git(repo, "--show-toplevel")).resolve() != repo.resolve():
            blockers.append("NOT_REPOSITORY_ROOT")
        if _git(repo, "HEAD") != COMMIT:
            blockers.append("SOURCE_COMMIT_MISMATCH")
    except Exception as exc:
        blockers.append(f"SOURCE_IDENTITY_UNREADABLE:{type(exc).__name__}")
        return _report(blockers, checked, dependencies)

    try:
        text = (repo / "chartdesk/tracker.py").read_text(encoding="utf-8")
        raw = text.encode("utf-8")
        digest = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        if digest != BLOB:
            blockers.append("SOURCE_BLOB_MISMATCH:tracker.py")
        expected = _projection(text)
        actual = ast.parse((ROOT / Path(VENDOR)).read_text(encoding="utf-8"))
        if _dump(_without_docs(actual)) == _dump(_without_docs(expected)):
            checked.append("lifecycle_outcome_shelf")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_outcome_shelf")
    except Exception as exc:
        blockers.append(
            "SOURCE_PROJECTION_UNREADABLE:"
            f"lifecycle_outcome_shelf:{type(exc).__name__}:{exc}"
        )

    expected_names = {row[0] for row in _EXPECTED_CHILD_AUDITS}
    if set(CHILD_AUDITS) != expected_names:
        blockers.append("CHILD_AUDIT_IDENTITY_MISMATCH:SET")
    projections = dict(_REQUIRED_CHILD_PROJECTIONS)
    commits = {name: dict(value) for name, value in _REQUIRED_CHILD_COMMITS}
    for name, module_name, function_name in _EXPECTED_CHILD_AUDITS:
        if CHILD_AUDITS.get(name) != (module_name, function_name):
            blockers.append(f"CHILD_AUDIT_IDENTITY_MISMATCH:{name}")
            continue
        try:
            child = _child_audit(name, source_root)
            if not _valid_child_report(projections[name], commits[name], child):
                raise TypeError("CHILD_REPORT_SHAPE")
            dependencies[name] = child
            blockers.extend(f"DEPENDENCY:{name}:{row}" for row in child["blockers"])
        except Exception as exc:
            blockers.append(f"DEPENDENCY:{name}:UNREADABLE:{type(exc).__name__}")
    return _report(blockers, checked, dependencies)
