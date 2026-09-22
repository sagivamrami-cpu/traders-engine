"""Inert source proof for tracker lifecycle transition and message helpers."""
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
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_transitions.py"
SYMBOLS = (
    "_tp_management_line", "_UNVERIFIED_NOTE", "_fill_caveat", "_il_clock",
    "_journey", "_ambiguous_touch", "_resolve_ambiguous", "_ambiguous_result",
    "_resolve_protective", "_protective_result", "_mark_terminal", "PROGRESS_PCT",
    "_progress_pct", "_progress_steps", "_progress_messages", "_protective",
    "_fill_line", "_target_line", "_no_score", "_cancel_line",
)
SIGNATURES = (
    "def _tp_management_line(i: int, total: int) -> str: pass",
    "def _fill_caveat(why: str, verified: bool) -> str: pass",
    "def _il_clock(ts) -> str: pass",
    "def _journey(t: dict) -> str: pass",
    "def _ambiguous_touch(t: dict, lo: float, hi: float, short: bool, protective: float) -> bool: pass",
    "def _resolve_ambiguous(t: dict, name: str, side: str) -> tuple[str, str]: pass",
    "def _ambiguous_result(t: dict, name: str, side: str) -> tuple[str, str]: pass",
    "def _resolve_protective(t: dict, name: str, side: str) -> tuple[str, str, str]: pass",
    "def _protective_result(t: dict, name: str, side: str) -> tuple[str, str, str]: pass",
    "def _mark_terminal(t: dict, state: str) -> None: pass",
    "def _progress_pct(symbol: str) -> float: pass",
    "def _progress_steps(t: dict, best: float, short: bool) -> list[tuple[int, float]]: pass",
    "def _progress_messages(t: dict, best: float, short: bool, name: str, side: str) -> list[tuple[str, bool]]: pass",
    "def _protective(t: dict, short: bool) -> float: pass",
    "def _fill_line(t: dict, name: str, side: str) -> str: pass",
    "def _target_line(t: dict, i: int, tag: str, px: float) -> str: pass",
    "def _no_score(why: str) -> str: pass",
    "def _cancel_line(t: dict, why: str) -> str: pass",
)
PREFIX = """from __future__ import annotations
import re
from . import basis_symbols as basis
from . import lifecycle_voice as voice
from .desk_success import DeskSuccess
from .lifecycle_bars import _entry_band
"""
INPUT_ERRORS = (
    OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
    UnicodeError, subprocess.SubprocessError,
)
CHILD_AUDITS = {
    "lifecycle_primitives": (
        "trading_system.tree_spec.lifecycle_primitives_source",
        "audit_lifecycle_primitives_source",
    ),
}
_EXPECTED_CHILD_AUDITS = (
    (
        "lifecycle_primitives",
        "trading_system.tree_spec.lifecycle_primitives_source",
        "audit_lifecycle_primitives_source",
    ),
)
_REQUIRED_CHILD_PROJECTIONS = (
    (
        "lifecycle_primitives",
        "lifecycle_bars", "desk_success", "lifecycle_voice",
    ),
)


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git(path, arg):
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", arg],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


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


def _replace(tree, old, new, *, count=1):
    before = ast.parse(old, mode="eval").body
    after = ast.parse(new, mode="eval").body

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


def _child_audit(name, source_root):
    module_name, function_name = CHILD_AUDITS[name]
    module = importlib.import_module(module_name)
    return getattr(module, function_name)(source_root)


def _valid_child_report(expected_projections, child):
    if (
        not isinstance(child, dict)
        or type(child.get("source_subset_verified")) is not bool
        or not isinstance(child.get("blockers"), list)
        or not all(isinstance(row, str) for row in child["blockers"])
    ):
        return False
    try:
        json.dumps(child, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return False
    if not child["source_subset_verified"]:
        return True
    return (
        child.get("status") == "VERIFIED"
        and child["blockers"] == []
        and child.get("checked_projections") == list(expected_projections)
        and child.get("source_commits") == {"chart-desk": COMMIT}
        and child.get("ready_for_replay") is False
        and child.get("ready_for_training") is False
    )


def _projection(text):
    selected = [node for node in ast.parse(text).body if _name(node) in SYMBOLS]
    if tuple(_name(node) for node in selected) != SYMBOLS:
        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
    nodes = {_name(node): copy.deepcopy(node) for node in selected}
    for expected in map(lambda source: ast.parse(source).body[0], SIGNATURES):
        node = nodes[expected.name]
        if (
            not isinstance(node, ast.FunctionDef)
            or [_dump(row) for row in node.decorator_list]
            != [_dump(row) for row in expected.decorator_list]
        ):
            raise ValueError(f"SOURCE_DECORATOR_MISMATCH:{expected.name}")
        _signature(node, expected)

    edits = {
        "_fill_caveat": (
            ('_UNVERIFIED_NOTE', 'self._UNVERIFIED_NOTE'),
        ),
        "_journey": (
            (
                'voice.rung_points(t["entry"], _progress_pct(t["symbol"]), step)',
                'voice.rung_points(t["entry"], self._progress_pct(t["symbol"]), step)',
            ),
            ('_il_clock(t.get("be_ts"))', 'self._il_clock(t.get("be_ts"))'),
        ),
        "_resolve_ambiguous": (
            ('_ambiguous_result(t, name, side)', 'self._ambiguous_result(t, name, side)'),
        ),
        "_ambiguous_result": (
            ('desk_success.stop_note(t)', 'self.desk_success.stop_note(t)'),
        ),
        "_resolve_protective": (
            ('_protective_result(t, name, side)', 'self._protective_result(t, name, side)'),
        ),
        "_protective_result": (
            ('_journey(t)', 'self._journey(t)'),
            ('desk_success.stop_note(t)', 'self.desk_success.stop_note(t)'),
        ),
        "_mark_terminal": (
            ('time.time()', 'self.source.now_epoch()'),
        ),
        "_progress_pct": (
            ('PROGRESS_PCT.items()', 'self.PROGRESS_PCT.items()'),
        ),
        "_progress_steps": (
            ('_progress_pct(t["symbol"])', 'self._progress_pct(t["symbol"])'),
        ),
        "_progress_messages": (
            ('_progress_steps(t, best, short)', 'self._progress_steps(t, best, short)'),
        ),
        "_target_line": (
            ('_tp_management_line(i, len(t["targets"]))', 'self._tp_management_line(i, len(t["targets"]))'),
        ),
        "_cancel_line": (
            ('_no_score(why)', 'self._no_score(why)'),
        ),
    }
    for name, rows in edits.items():
        for old, new in rows:
            nodes[name] = _replace(nodes[name], old, new)

    cls = ast.parse(
        """class LifecycleTransitions:
    def __init__(self, source):
        self.source = source
        self.desk_success = DeskSuccess(source)
"""
    ).body[0]
    for symbol in SYMBOLS:
        node = nodes[symbol]
        if isinstance(node, ast.FunctionDef):
            node.args.args.insert(0, ast.arg(arg="self"))
        cls.body.append(node)
    return ast.Module(body=ast.parse(PREFIX).body + [cls], type_ignores=[])


def audit_lifecycle_transitions_source(source_root):
    """Inspect the retained transition subset and actual inherited audit only."""
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
    except INPUT_ERRORS as exc:
        blockers.append(f"SOURCE_IDENTITY_UNREADABLE:{type(exc).__name__}")
        return report()

    try:
        text = (repo / "chartdesk/tracker.py").read_text(encoding="utf-8")
        raw = text.encode("utf-8")
        if hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != BLOB:
            blockers.append("SOURCE_BLOB_MISMATCH:tracker.py")
        expected = _projection(text)
        actual = ast.parse((ROOT / Path(VENDOR)).read_text(encoding="utf-8"))
        if _dump(_without_docs(actual)) == _dump(_without_docs(expected)):
            checked.append("lifecycle_transitions")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_transitions")
    except INPUT_ERRORS as exc:
        blockers.append(
            "SOURCE_PROJECTION_UNREADABLE:"
            f"lifecycle_transitions:{type(exc).__name__}:{exc}"
        )

    expected_names = {row[0] for row in _EXPECTED_CHILD_AUDITS}
    if set(CHILD_AUDITS) != expected_names:
        blockers.append("CHILD_AUDIT_IDENTITY_MISMATCH:SET")
    required = {row[0]: row[1:] for row in _REQUIRED_CHILD_PROJECTIONS}
    for name, module_name, function_name in _EXPECTED_CHILD_AUDITS:
        if CHILD_AUDITS.get(name) != (module_name, function_name):
            blockers.append(f"CHILD_AUDIT_IDENTITY_MISMATCH:{name}")
            continue
        try:
            child = _child_audit(name, source_root)
            if not _valid_child_report(required[name], child):
                raise TypeError("CHILD_REPORT_SHAPE")
            dependencies[name] = child
            blockers.extend(f"DEPENDENCY:{name}:{row}" for row in child["blockers"])
            if not child["source_subset_verified"] and not child["blockers"]:
                blockers.append(f"DEPENDENCY:{name}:NOT_VERIFIED")
        except Exception as exc:
            blockers.append(f"DEPENDENCY:{name}:UNREADABLE:{type(exc).__name__}")
    return report()
