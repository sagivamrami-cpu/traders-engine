"""Static, inert proof for the supplied-only full-tree capture boundary."""
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "trading_system/tree_replay/full_tree_capture.py"
_FORBIDDEN_IMPORT_ROOTS = frozenset({"requests", "urllib", "socket", "pathlib", "os"})


def _empty_report() -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "source_subset_verified": False,
        "blockers": [],
        "source_bindings": [],
        "ready_for_replay": False,
        "ready_for_training": False,
    }


def _blocked(report: dict[str, object], *blockers: str) -> dict[str, object]:
    result = _empty_report()
    result["source_bindings"] = report.get("source_bindings", [])
    result["blockers"] = list(blockers) or ["AUDIT_UNREADABLE:UnknownError"]
    return result


def _dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


def _class(tree: ast.Module, name: str) -> ast.ClassDef | None:
    found = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name]
    return found[0] if len(found) == 1 else None


def _method(node: ast.ClassDef, name: str) -> ast.FunctionDef | None:
    found = [item for item in node.body if isinstance(item, ast.FunctionDef) and item.name == name]
    return found[0] if len(found) == 1 else None


def _args(function: ast.FunctionDef) -> list[str]:
    return [arg.arg for arg in (*function.args.posonlyargs, *function.args.args)]


def _imports(tree: ast.Module) -> tuple[set[tuple[int, str | None, str]], set[str]]:
    from_imports: set[tuple[int, str | None, str]] = set()
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".", 1)[0])
            from_imports.update((node.level, node.module, alias.name) for alias in node.names)
    return from_imports, roots


def _has_call(tree: ast.AST, name: str) -> bool:
    return any(isinstance(node, ast.Call) and _dotted(node.func) == name for node in ast.walk(tree))


def check_full_tree_capture_source() -> dict[str, object]:
    """Return a fail-closed static report; capture runtime is never imported."""
    report = _empty_report()
    try:
        tree = ast.parse(CAPTURE.read_text(encoding="utf-8"), filename=str(CAPTURE))
    except (OSError, SyntaxError) as exc:
        return _blocked(report, f"CAPTURE_UNREADABLE:{type(exc).__name__}")

    imports, roots = _imports(tree)
    forbidden = sorted(roots & _FORBIDDEN_IMPORT_ROOTS)
    if forbidden:
        return _blocked(report, *(f"FORBIDDEN_LIVE_IMPORT:{item}" for item in forbidden))
    required_imports = {
        (1, "_vendor.tree_walk", "TreeReader"),
        (1, "tree_revalidation", "TreeRevalidation"),
    }
    if not required_imports <= imports:
        return _blocked(report, "SOURCE_BINDING_MISMATCH")
    report["source_bindings"] = ["TreeReader", "TreeRevalidation"]
    if not (_has_call(tree, "TreeReader") and _has_call(tree, "TreeRevalidation")):
        return _blocked(report, "SOURCE_BINDING_CALL_MISMATCH")

    capture = _class(tree, "FullTreeEvidenceCapture")
    supplied = _class(tree, "FullTreeCaptureInput")
    if capture is None or supplied is None or _method(supplied, "read") is None:
        return _blocked(report, "SUPPLIED_INPUT_CONTRACT_MISMATCH")
    walk = _method(capture, "capture_walk")
    revalidation = _method(capture, "capture_revalidation")
    if walk is None or _args(walk) != ["self"] or walk.args.vararg or walk.args.kwarg:
        return _blocked(report, "FINAL_RESULT_INJECTION_SURFACE")
    if revalidation is None or _args(revalidation) != ["self", "pending_plan"]:
        return _blocked(report, "FINAL_RESULT_INJECTION_SURFACE")
    constructor = _method(capture, "__init__")
    if constructor is None or any(name in {"walk", "plan", "result"} for name in _args(constructor)):
        return _blocked(report, "FINAL_RESULT_INJECTION_SURFACE")
    report.update({"status": "VERIFIED", "source_subset_verified": True})
    return report
