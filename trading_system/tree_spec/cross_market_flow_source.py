"""Static boundary proof for the GC-to-XAUUSD context sidecar."""
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FLOW = ROOT / "trading_system/tree_replay/cross_market_flow.py"
POLICY = ROOT / "trading_system/tree_replay/cross_market_flow_policy.py"
SIDECAR = ROOT / "trading_system/tree_replay/full_tree_cross_market_context.py"
_FORBIDDEN_IMPORTS = frozenset({"requests", "urllib", "socket", "pathlib", "os"})
_FORBIDDEN_CUMULATIVE_NAMES = frozenset({"cvd", "cumulative_delta"})


def _empty_report() -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "blockers": [],
        "source_bindings": [],
        "forbidden_price_mapping": False,
        "ready_for_replay": False,
        "ready_for_training": False,
    }


def _blocked(report: dict[str, object], *blockers: str) -> dict[str, object]:
    result = _empty_report()
    result["source_bindings"] = report["source_bindings"]
    result["blockers"] = list(blockers) or ["CROSS_MARKET_SOURCE_UNREADABLE"]
    return result


def _imports(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".", 1)[0])
    return found


def _from_imports(tree: ast.Module) -> set[str]:
    return {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }


def _class_fields(tree: ast.Module, class_name: str) -> set[str]:
    matches = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name]
    if len(matches) != 1:
        return set()
    return {
        node.target.id
        for node in matches[0].body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }


def check_cross_market_flow_source() -> dict[str, object]:
    """Verify local source boundaries without opening any market-data archive."""
    report = _empty_report()
    try:
        text = {path: path.read_text(encoding="utf-8") for path in (FLOW, POLICY, SIDECAR)}
        trees = {path: ast.parse(source, filename=str(path)) for path, source in text.items()}
    except (OSError, SyntaxError) as exc:
        return _blocked(report, f"CROSS_MARKET_SOURCE_UNREADABLE:{type(exc).__name__}")

    # The policy loader intentionally reads a pinned local YAML contract.  The
    # aggregation and evidence sidecar themselves must not acquire live data.
    forbidden_imports = sorted(
        set().union(*(_imports(trees[path]) for path in (FLOW, SIDECAR))) & _FORBIDDEN_IMPORTS
    )
    names = {
        node.id.lower()
        for tree in trees.values()
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    }
    blockers = [f"FORBIDDEN_LIVE_IMPORT:{name}" for name in forbidden_imports]
    blockers.extend(
        f"FORBIDDEN_CUMULATIVE_FEATURE:{name}"
        for name in sorted(names & _FORBIDDEN_CUMULATIVE_NAMES)
    )
    if blockers:
        return _blocked(report, *blockers)

    if "current + _MINUTE <= decision_time" not in text[FLOW]:
        return _blocked(report, "CLOSED_MINUTE_COMPARISON_MISMATCH")
    flow_fields = _class_fields(trees[FLOW], "CrossMarketFlowContext")
    if {"open", "high", "low", "close", "price"} & flow_fields:
        report["forbidden_price_mapping"] = True
        return _blocked(report, "FORBIDDEN_PRICE_MAPPING_SURFACE")
    if "CrossMarketFlowPolicy" not in _from_imports(trees[FLOW]):
        return _blocked(report, "POLICY_BINDING_MISMATCH")
    if "FullTreeEvidenceBundle" not in _from_imports(trees[SIDECAR]):
        return _blocked(report, "FULL_TREE_BINDING_MISMATCH")
    report.update({
        "status": "VERIFIED",
        "source_bindings": ["CrossMarketFlowPolicy", "FullTreeEvidenceBundle"],
    })
    return report
