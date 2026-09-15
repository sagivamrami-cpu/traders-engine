"""Static proof for the local full-tree causal replay composition.

This is deliberately a source-text audit: it neither imports the replay
implementation nor executes a retained chart-desk checkout.  Its job is narrow:
prove that the replay calls the vendored full tree through the closed evidence
provider surface, and that no public report claims readiness for replay or
training.
"""
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_PROVIDER_PORTS = (
    "fetch_corrected",
    "now_utc",
    "now_epoch",
    "now_timestamp",
    "calendar_text",
    "calendar_exists",
    "list_reports",
    "read_report",
    "read_tv_csv",
    "deep_exists",
    "deep_bytes",
    "ensure_shadow_parent",
    "shadow_open",
)
_FORBIDDEN_IMPORT_ROOTS = frozenset({"requests", "urllib", "socket", "pathlib", "os"})
_LOCAL_FILES = {
    "provider": ROOT / "trading_system/tree_replay/full_tree_provider.py",
    "replay": ROOT / "trading_system/tree_replay/full_tree_replay.py",
    "contracts": ROOT / "trading_system/tree_replay/full_tree_contracts.py",
}


def _empty_report() -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "source_subset_verified": False,
        "blockers": [],
        "provider_ports": [],
        "source_bindings": [],
        "ready_for_replay": False,
        "ready_for_training": False,
    }


def _blocked(report: dict[str, object], *blockers: str) -> dict[str, object]:
    result = _empty_report()
    result["provider_ports"] = report.get("provider_ports", [])
    result["source_bindings"] = report.get("source_bindings", [])
    result["blockers"] = list(blockers) or ["AUDIT_UNREADABLE:UnknownError"]
    return result


def _dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted(node.value)
        return f"{prefix}.{node.attr}" if prefix else None
    return None


def _read_local_trees() -> dict[str, ast.Module]:
    parsed: dict[str, ast.Module] = {}
    for name, path in _LOCAL_FILES.items():
        try:
            parsed[name] = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            raise ValueError(f"LOCAL_UNREADABLE:{name}:{type(exc).__name__}") from exc
    return parsed


def _class(tree: ast.Module, name: str) -> ast.ClassDef:
    matches = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name]
    if len(matches) != 1:
        raise ValueError(f"CLASS_SET_MISMATCH:{name}")
    return matches[0]


def _methods(node: ast.ClassDef) -> set[str]:
    return {child.name for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _forbidden_imports(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".", 1)[0])
    return found & _FORBIDDEN_IMPORT_ROOTS


def _from_imports(tree: ast.Module) -> set[tuple[int, str | None, str]]:
    return {
        (node.level, node.module, alias.name)
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }


def _has_call(tree: ast.AST, dotted: str) -> bool:
    return any(
        isinstance(node, ast.Call) and _dotted(node.func) == dotted
        for node in ast.walk(tree)
    )


def _run_pass_is_closed(replay: ast.Module) -> bool:
    cls = _class(replay, "FullTreeCausalReplay")
    runs = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "run_pass"]
    if len(runs) != 1:
        return False
    positional = [arg.arg for arg in (*runs[0].args.posonlyargs, *runs[0].args.args)]
    return positional == ["self", "pass_id"] and not runs[0].args.vararg and not runs[0].args.kwarg


def _variant_contract_is_closed(contracts: ast.Module) -> bool:
    assignments = [node for node in contracts.body if isinstance(node, ast.Assign)]
    variants = [
        node for node in assignments
        if any(isinstance(target, ast.Name) and target.id == "_VARIANTS" for target in node.targets)
    ]
    if len(variants) != 1:
        return False
    values = variants[0].value
    if not isinstance(values, ast.Call) or _dotted(values.func) != "frozenset" or len(values.args) != 1:
        return False
    literal = values.args[0]
    if not isinstance(literal, (ast.Set, ast.Tuple, ast.List)):
        return False
    return {
        item.value for item in literal.elts if isinstance(item, ast.Constant) and type(item.value) is str
    } == {"full_tree:house", "full_tree:strict"}


def check_full_tree_replay_source(source_root: Path | str | None) -> dict[str, object]:
    """Return a fail-closed, raw-data-free audit report.

    ``source_root`` is intentionally validated only for the retained source
    checkout's chart-desk directory.  No code or market payload from that
    checkout is read or executed by this audit.
    """
    report = _empty_report()
    try:
        root = Path(source_root) if source_root is not None else None
        if root is None or not (root / "chart-desk").is_dir():
            return _blocked(report, "SOURCE_ROOT_INVALID")
        trees = _read_local_trees()
    except ValueError as exc:
        return _blocked(report, str(exc))
    except (TypeError, OSError) as exc:
        return _blocked(report, f"AUDIT_UNREADABLE:{type(exc).__name__}")

    provider_ports = _methods(_class(trees["provider"], "FullTreeCausalProvider"))
    report["provider_ports"] = sorted(provider_ports & set(REQUIRED_PROVIDER_PORTS))
    missing = [name for name in REQUIRED_PROVIDER_PORTS if name not in provider_ports]
    if missing:
        return _blocked(report, *(f"MISSING_PROVIDER_PORT:{name}" for name in missing))

    forbidden = sorted({
        *(_forbidden_imports(trees["provider"])),
        *(_forbidden_imports(trees["replay"])),
    })
    if forbidden:
        return _blocked(report, *(f"FORBIDDEN_LIVE_IMPORT:{name}" for name in forbidden))

    imports = _from_imports(trees["replay"])
    required_bindings = {
        (1, "_vendor.tree_walk", "TreeReader"),
        (1, "tree_revalidation", "TreeRevalidation"),
    }
    if not required_bindings <= imports:
        return _blocked(report, "SOURCE_BINDING_MISMATCH")
    report["source_bindings"] = ["TreeReader", "TreeRevalidation"]
    if not (_has_call(trees["replay"], "TreeReader") and _has_call(trees["replay"], "TreeRevalidation")):
        return _blocked(report, "SOURCE_BINDING_CALL_MISMATCH")
    if not _run_pass_is_closed(trees["replay"]):
        return _blocked(report, "FINAL_RESULT_INJECTION_SURFACE")
    if not _variant_contract_is_closed(trees["contracts"]):
        return _blocked(report, "FULL_TREE_VARIANT_CONTRACT_MISMATCH")

    report.update({"status": "VERIFIED", "source_subset_verified": True})
    return report
