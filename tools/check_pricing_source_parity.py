"""Audit the pure pinned pricing closure as text/AST only, never by execution.

Plan is an explicit class projection: preserve its decorators, bases, keywords,
all non-method class statements (including every dataclass field), and exactly
risk/rr/rr_far/tradeable. No other class or function is projected. Ordered module
comparison rejects extra symbols, imports, duplicate definitions and mutations.
The trusted pins and coverage below are independent of the supplied manifest.
"""

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path

try:
    from . import check_reversal_source_parity as reversal_audit
except ImportError:  # Direct CLI invocation, with tools/ on sys.path.
    import check_reversal_source_parity as reversal_audit


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/trees/reversal-pricing-contracts.json"
SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
SOURCE_BLOBS = {
    "chartdesk/tradeplan.py": "d09e9be39ce8dadf1674029e0c03751c70502135",
    "chartdesk/basis.py": "f3396f3a9fefd71f0f71422001a5521af0a05cd2",
    "chartdesk/quarters.py": "d540b7bba60e992ff711954716ad265337116fc1",
    "chartdesk/tr.py": "8297c712d20404880d4d8949e96efbf48613909c",
    "chartdesk/level_reversal.py": "7c0eee53d97a1ba9280626fdb2d20eba61b5aa1b",
}
PLAN_METHODS = ("risk", "rr", "rr_far", "tradeable")
PLAN_PROJECTION = {
    "class": "Plan",
    "preserve": "original decorators, bases, keywords and all non-method class statements",
    "methods": list(PLAN_METHODS),
    "complete_source_class": False,
}
REQUIRED_FILES = {
    "chartdesk/tradeplan.py": {
        "vendor_path": "trading_system/tree_replay/_vendor/pricing.py",
        "symbols": ["MIN_RR", "SWING_MULT", "STYLE_MULT", "INTRADAY_MULT",
                    "INTRADAY_TARGET_COUNT", "FAR_TP1_R", "INSERT_TP1_R",
                    "_with_measured_rung", "ENTRY_ZONE", "entry_zone", "STOP_BANDS",
                    "apply_stop_band", "Plan", "MIN_TARGET_SEP_ATR", "ladder_ready",
                    "ordered_ladder", "distinct_targets", "_n_levels", "resolve_ladder"],
        "allowed_imports": "from __future__ import annotations\nfrom dataclasses import dataclass, field\nfrom . import basis_symbols as basis",
    },
    "chartdesk/basis.py": {
        "vendor_path": "trading_system/tree_replay/_vendor/basis_symbols.py",
        "symbols": ["_BARE_ALIASES", "canonical_symbol"],
        "allowed_imports": "from __future__ import annotations",
    },
    "chartdesk/quarters.py": {
        "vendor_path": "trading_system/tree_replay/_vendor/quarters.py",
        "symbols": ["GRID", "_asset", "Level", "_kind", "nearest"],
        "allowed_imports": "from __future__ import annotations\nfrom dataclasses import dataclass",
    },
    "chartdesk/tr.py": {
        "vendor_path": "trading_system/tree_replay/_vendor/atr.py",
        "symbols": ["atr"],
        "allowed_imports": "import pandas as pd",
    },
    "chartdesk/level_reversal.py": {
        "vendor_path": "trading_system/tree_replay/_vendor/reversal_pricing.py",
        "symbols": ["build_plan"],
        "allowed_imports": "from __future__ import annotations\nimport pandas as pd\nfrom .level_reversal import Reversal, _normalise\nfrom . import pricing as tradeplan\nfrom . import atr as tr",
    },
}
EXPECTED_CONTRACT = {
    "schema_version": "chartdesk-reversal-pricing-contracts-v1",
    "repository": "chart-desk",
    "commit": SOURCE_COMMIT,
    "plan_projection": PLAN_PROJECTION,
    "inherited_dependency_audit": "tools/check_reversal_source_parity.py:check_source_parity",
    "files": [{"path": path, "git_blob_sha1": SOURCE_BLOBS[path], **scope}
              for path, scope in REQUIRED_FILES.items()],
    "ready_for_replay": False,
    "ready_for_training": False,
}


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _name(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _project_plan(node):
    if not isinstance(node, ast.ClassDef) or node.name != "Plan":
        raise ValueError("PLAN_CLASS_MISMATCH")
    result = copy.deepcopy(node)
    result.body = [n for n in result.body
                   if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   or n.name in PLAN_METHODS]
    methods = [n for n in result.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if [n.name for n in methods] != list(PLAN_METHODS):
        raise ValueError("PLAN_PROPERTY_SET_MISMATCH")
    for method in methods:
        if not isinstance(method, ast.FunctionDef) or [_dump(d) for d in method.decorator_list] != [_dump(ast.Name(id="property", ctx=ast.Load()))]:
            raise ValueError("PLAN_PROPERTY_DECORATOR_MISMATCH")
    return result


def _expected_nodes(text, scope):
    selected = [n for n in ast.parse(text).body if _name(n) in scope["symbols"]]
    if [_name(n) for n in selected] != scope["symbols"]:
        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
    return ast.parse(scope["allowed_imports"]).body + [
        _project_plan(n) if isinstance(n, ast.ClassDef) and n.name == "Plan" else n
        for n in selected]


def _report(blockers):
    return {"source_commit": SOURCE_COMMIT, "subset_verified": not blockers,
            "source_subset_verified": not blockers, "blockers": blockers,
            "ready_for_replay": False, "ready_for_training": False}


def check_source_parity(source_root: Path) -> dict:
    """Fail closed on contract, baseline, source, vendor or inherited changes."""
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        # Serialized comparison also distinguishes JSON booleans from numbers.
        if json.dumps(contract, sort_keys=True) != json.dumps(EXPECTED_CONTRACT, sort_keys=True):
            return _report(["CONTRACT_MISMATCH"])
        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
        pins = [row.get("commit") for row in baseline["repositories"] if row.get("name") == "chart-desk"]
        if pins != [SOURCE_COMMIT]:
            return _report(["BASELINE_COMMIT_MISMATCH"])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return _report([f"CONTRACT_UNREADABLE:{type(exc).__name__}"])

    blockers = []
    try:
        inherited = reversal_audit.check_source_parity(source_root)
        if inherited.get("subset_verified") is not True or inherited.get("blockers") != []:
            blockers.append("INHERITED_REVERSAL_AUDIT_FAILED")
            blockers.extend(f"INHERITED:{b}" for b in inherited.get("blockers", []))
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        blockers.append(f"INHERITED_REVERSAL_AUDIT_UNREADABLE:{type(exc).__name__}")

    for path, scope in REQUIRED_FILES.items():
        try:
            # Normalize checkout CRLF to Git's canonical LF before blob hashing.
            text = (Path(source_root) / path).read_text(encoding="utf-8")
            data = text.encode("utf-8")
            digest = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            if digest != SOURCE_BLOBS[path]:
                blockers.append(f"SOURCE_BLOB_MISMATCH:{path}")
                continue
            expected = _expected_nodes(text, scope)
        except (OSError, ValueError, SyntaxError) as exc:
            blockers.append(f"SOURCE_UNREADABLE:{path}:{type(exc).__name__}")
            continue
        try:
            vendor = ast.parse((ROOT / scope["vendor_path"]).read_text(encoding="utf-8"))
            actual = vendor.body
            if ast.get_docstring(vendor) is not None:
                actual = actual[1:]
            if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
                blockers.append(f"VENDOR_AST_MISMATCH:{scope['vendor_path']}")
        except (OSError, ValueError, SyntaxError) as exc:
            blockers.append(f"VENDOR_UNREADABLE:{scope['vendor_path']}:{type(exc).__name__}")
    return _report(blockers)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True, help="Pinned chart-desk checkout; text only")
    args = parser.parse_args()
    report = check_source_parity(args.source_root)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["subset_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
