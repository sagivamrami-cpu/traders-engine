"""Read-only retained-source proof for live-resolution evidence collection."""
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
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_live_resolution_evidence.py"
PREFIX = """import pandas as pd
from .lifecycle_live_evidence import LifecycleLiveEvidence
"""
_EXPECTED_FRAGMENT_NAMES = (
    "prices", "_bar_extremes", "try", "_now", "for", "if_not_prices",
)


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _git(path, arg):
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", arg],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _function(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise ValueError(f"SOURCE_FUNCTION_MISSING:{name}")


def _is_prices_assignment(node):
    return (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "prices"
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "_live_prices"
        and not node.value.args
        and not node.value.keywords
    )


def _is_empty_prices_guard(node):
    return (
        isinstance(node, ast.If)
        and isinstance(node.test, ast.UnaryOp)
        and isinstance(node.test.op, ast.Not)
        and isinstance(node.test.operand, ast.Name)
        and node.test.operand.id == "prices"
        and len(node.body) == 1
        and isinstance(node.body[0], ast.Return)
        and isinstance(node.body[0].value, ast.List)
        and node.body[0].value.elts == []
        and not node.orelse
    )


def _fragment_names(fragment):
    names = []
    for node in fragment:
        if _is_prices_assignment(node):
            names.append("prices")
        elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            names.append(node.targets[0].id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.id)
        elif isinstance(node, ast.Try):
            names.append("try")
        elif isinstance(node, ast.For):
            names.append("for")
        elif _is_empty_prices_guard(node):
            names.append("if_not_prices")
        else:
            names.append(type(node).__name__)
    return tuple(names)


def _extract_fragment(text):
    """Extract, but never execute, the fixed leading resolver evidence block."""
    fn = _function(ast.parse(text), "_check_live_locked")
    start = next((i for i, node in enumerate(fn.body) if _is_prices_assignment(node)), None)
    if start is None:
        raise ValueError("SOURCE_FRAGMENT_START_MISSING")
    end = next(
        (i for i in range(start, len(fn.body)) if _is_empty_prices_guard(fn.body[i])),
        None,
    )
    if end is None:
        raise ValueError("SOURCE_FRAGMENT_END_MISSING")
    fragment = copy.deepcopy(fn.body[start : end + 1])
    if _fragment_names(fragment) != _EXPECTED_FRAGMENT_NAMES:
        raise ValueError("SOURCE_FRAGMENT_ORDER_MISMATCH")
    return fragment


class _Rename(ast.NodeTransformer):
    def __init__(self, mapping):
        self.mapping = mapping

    def visit_Name(self, node):
        if node.id in self.mapping:
            return ast.copy_location(ast.Name(id=self.mapping[node.id], ctx=node.ctx), node)
        return node


def _expr(source):
    return ast.parse(source, mode="eval").body


def _replace_expr(tree, old, new, *, count=1):
    before, after = _expr(old), _expr(new)

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


class _DropPandasImport(ast.NodeTransformer):
    def visit_Try(self, node):
        node = self.generic_visit(node)
        node.body = [
            row for row in node.body
            if not (isinstance(row, ast.Import) and any(alias.name == "pandas" for alias in row.names))
        ]
        return node


class _EraseAnnotations(ast.NodeTransformer):
    def visit_AnnAssign(self, node):
        if node.value is None:
            raise ValueError("SOURCE_ANNOTATION_WITHOUT_VALUE")
        return ast.copy_location(ast.Assign(targets=[node.target], value=node.value), node)


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


def _projection(text):
    fragment = _extract_fragment(text)
    prices, extremes, raw_quotes, now, loop, guard = fragment
    if not (
        isinstance(extremes, ast.AnnAssign)
        and isinstance(extremes.target, ast.Name)
        and extremes.target.id == "_bar_extremes"
        and isinstance(raw_quotes, ast.Try)
        and isinstance(now, ast.Assign)
        and isinstance(now.targets[0], ast.Name)
        and now.targets[0].id == "_now"
        and isinstance(loop, ast.For)
    ):
        raise ValueError("SOURCE_FRAGMENT_SHAPE_MISMATCH")

    nodes = copy.deepcopy([prices, extremes, raw_quotes, now, loop])
    module = ast.Module(body=nodes, type_ignores=[])
    module = _Rename({
        "_bar_extremes": "bar_extremes", "_q": "raw_quotes", "_now": "now",
        "_s": "symbol", "_df": "bars", "_c": "correction", "_bar_ts": "latest",
        "_age": "age",
        "d": "state", "t": "trade", "_pd": "pd",
    }).visit(module)
    module = _replace_expr(module, "_live_prices()", "LifecycleLiveEvidence(self.source)._live_prices()")
    module = _replace_expr(module, "json.loads(QUOTES.read_text())", "self.source.quote_payload()")
    module = _replace_expr(module, "time.time()", "self.source.now_epoch()")
    module = _replace_expr(module, "basis.fetch_corrected(symbol, '15m', 2)", "self.source.fetch_corrected(symbol, '15m', 2)")
    module = _replace_expr(module, "FORCE_BAR_AGE_S", "self.FORCE_BAR_AGE_S")
    module = _DropPandasImport().visit(module)
    module = _EraseAnnotations().visit(module)

    loop = module.body[-1]
    symbols = ast.Assign(
        targets=[ast.Name(id="symbols", ctx=ast.Store())], value=copy.deepcopy(loop.iter)
    )
    loop.iter = ast.Name(id="symbols", ctx=ast.Load())
    fallback = loop.body[-1]
    if not isinstance(fallback, ast.Try):
        raise ValueError("SOURCE_FALLBACK_TRY_SHAPE_MISMATCH")
    winning = fallback.body[-1]
    if not isinstance(winning, ast.If) or len(winning.body) != 2:
        raise ValueError("SOURCE_FALLBACK_WINNER_SHAPE_MISMATCH")
    collect = ast.parse("""def collect(self, state: dict) -> tuple[dict, dict]:
    pass
""").body[0]
    collect.body = module.body[:-1] + [symbols, loop, ast.parse("return prices, bar_extremes").body[0]]
    constructor = ast.parse("""def __init__(self, source):
    self.source = source
""").body[0]
    constant = ast.parse("FORCE_BAR_AGE_S = LifecycleLiveEvidence.FORCE_BAR_AGE_S").body[0]
    cls = ast.parse("class LifecycleLiveResolutionEvidence:\n    pass").body[0]
    cls.body = [constant, constructor, collect]
    return ast.fix_missing_locations(ast.Module(body=ast.parse(PREFIX).body + [cls], type_ignores=[]))


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


def audit_lifecycle_live_resolution_evidence_source(source_root) -> dict:
    """Verify the pinned source fragment against its inert offline projection."""
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
            checked.append("lifecycle_live_resolution_evidence")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_live_resolution_evidence")
    except Exception as exc:
        blockers.append(
            "SOURCE_PROJECTION_UNREADABLE:"
            f"lifecycle_live_resolution_evidence:{type(exc).__name__}:{exc}"
        )
    return _report(blockers, checked)
