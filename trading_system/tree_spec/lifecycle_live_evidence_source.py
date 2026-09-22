"""Inert retained-source proof for tracker lifecycle live-evidence helpers."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
BLOB = "b616b34022e436545d8c1daf85eced51614fd74e"
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_live_evidence.py"
SYMBOLS = (
    "QUOTE_MAX_AGE_S", "_live_prices", "_historical_replay_safe",
    "FORCE_BAR_AGE_S",
)
_EXPECTED_SYMBOLS = (
    "QUOTE_MAX_AGE_S", "_live_prices", "_historical_replay_safe",
    "FORCE_BAR_AGE_S",
)
SIGNATURES = (
    "def _live_prices() -> dict: pass",
    "def _historical_replay_safe(df, corr, t: dict) -> bool: pass",
)
PREFIX = """import math
import pandas as pd
"""


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


def _git(path, arg):
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", arg],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _projection(text):
    if SYMBOLS != _EXPECTED_SYMBOLS:
        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
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

    nodes["_live_prices"] = _replace(
        nodes["_live_prices"],
        "json.loads(QUOTES.read_text())",
        "self.source.quote_payload()",
    )
    nodes["_live_prices"] = _replace(
        nodes["_live_prices"], "time.time()", "self.source.now_epoch()"
    )
    nodes["_live_prices"] = _replace(
        nodes["_live_prices"], "QUOTE_MAX_AGE_S", "self.QUOTE_MAX_AGE_S"
    )

    constructor = ast.parse("""class LifecycleLiveEvidence:
    def __init__(self, source):
        self.source = source
""").body[0].body[0]
    cls = ast.parse("class LifecycleLiveEvidence:\n    pass").body[0]
    cls.body = [constructor]
    for symbol in SYMBOLS:
        node = nodes[symbol]
        if isinstance(node, ast.FunctionDef):
            node.args.args.insert(0, ast.arg(arg="self"))
        cls.body.append(node)
    return ast.Module(body=ast.parse(PREFIX).body + [cls], type_ignores=[])


def _report(blockers, checked):
    return {
        "status": "BLOCKED" if blockers else "VERIFIED",
        "source_subset_verified": not blockers,
        "blockers": blockers,
        "checked_projections": checked,
        "dependencies": {},
        "source_commits": {"chart-desk": COMMIT},
        "ready_for_replay": False,
        "ready_for_training": False,
    }


def audit_lifecycle_live_evidence_source(source_root) -> dict:
    """Check a read-only retained subset against the private offline port."""
    blockers, checked = [], []
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
        return _report(blockers, checked)

    try:
        text = (repo / "chartdesk/tracker.py").read_text(encoding="utf-8")
        raw = text.encode("utf-8")
        digest = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        if digest != BLOB:
            blockers.append("SOURCE_BLOB_MISMATCH:tracker.py")
        expected = _projection(text)
        actual = ast.parse((ROOT / Path(VENDOR)).read_text(encoding="utf-8"))
        if _dump(_without_docs(actual)) == _dump(_without_docs(expected)):
            checked.append("lifecycle_live_evidence")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_live_evidence")
    except Exception as exc:
        blockers.append(
            "SOURCE_PROJECTION_UNREADABLE:"
            f"lifecycle_live_evidence:{type(exc).__name__}:{exc}"
        )
    return _report(blockers, checked)
