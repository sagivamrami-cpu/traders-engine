"""Audit the pinned range dependency closure using source text/AST only.

No source or vendor module is imported or executed. Coverage, statement order,
imports and Git blobs are fixed here independently of the supplied manifest.
Success verifies this subset only; replay and training readiness stay false.
"""

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/trees/range-level-contracts.json"
SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
DEFAULT_SOURCE_ROOT = Path(
    "C:/Users/roeea/AppData/Local/Temp/"
    "tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk"
)
SOURCE_BLOBS = {
    "chartdesk/tr.py": "8297c712d20404880d4d8949e96efbf48613909c",
    "chartdesk/levelmap.py": "01fc9fe098aa7a5991ce62c3a83e870e4f0d5a2e",
}
REQUIRED_FILES = {
    "chartdesk/tr.py": {
        "vendor_path": "trading_system/tree_replay/_vendor/ranges.py",
        "symbols": ["daily_pivots", "average_range", "range_hilo",
                    "weekly_from_daily", "monthly_from_daily", "tr_levels"],
        "allowed_imports": "from __future__ import annotations\nimport pandas as pd",
    },
    "chartdesk/levelmap.py": {
        "vendor_path": "trading_system/tree_replay/_vendor/back_days.py",
        "symbols": ["BACK_DAYS", "_back_day_levels"],
        "allowed_imports": "from __future__ import annotations",
    },
}
EXPECTED_CONTRACT = {
    "schema_version": "chartdesk-range-level-contracts-v1",
    "repository": "chart-desk",
    "commit": SOURCE_COMMIT,
    "scope": "Pure range/rollover/back-day dependency closure; pivots are internal dependencies, not a new emitted map family",
    "files": [{"path": path, "git_blob_sha1": SOURCE_BLOBS[path], **scope}
              for path, scope in REQUIRED_FILES.items()],
    "ready_for_replay": False,
    "ready_for_training": False,
}


def _name(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _expected_nodes(text, scope):
    source = ast.parse(text)
    imports = ast.parse(scope["allowed_imports"]).body
    allowed = [_dump(node) for node in imports]
    source_imports = [node for node in source.body
                      if isinstance(node, (ast.Import, ast.ImportFrom)) and _dump(node) in allowed]
    if [_dump(node) for node in source_imports] != allowed:
        raise ValueError("SOURCE_IMPORT_ORDER_OR_SET_MISMATCH")
    selected = [node for node in source.body if _name(node) in scope["symbols"]]
    if [_name(node) for node in selected] != scope["symbols"]:
        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
    return imports + selected


def _report(blockers):
    return {"source_commit": SOURCE_COMMIT, "subset_verified": not blockers,
            "source_subset_verified": not blockers, "blockers": blockers,
            "ready_for_replay": False, "ready_for_training": False}


def check_source_parity(source_root: Path) -> dict:
    """Fail closed on missing prerequisites, pin drift or altered module ASTs."""
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        # JSON comparison distinguishes false from 0 as well as exact coverage.
        if json.dumps(contract, sort_keys=True) != json.dumps(EXPECTED_CONTRACT, sort_keys=True):
            return _report(["CONTRACT_MISMATCH"])
        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
        pins = [row.get("commit") for row in baseline["repositories"] if row.get("name") == "chart-desk"]
        if pins != [SOURCE_COMMIT]:
            return _report(["BASELINE_COMMIT_MISMATCH"])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return _report([f"CONTRACT_UNREADABLE:{type(exc).__name__}"])

    blockers = []
    for path, scope in REQUIRED_FILES.items():
        try:
            # read_text normalizes checkout CRLF to canonical Git LF.
            text = (Path(source_root) / path).read_text(encoding="utf-8")
            data = text.encode("utf-8")
            blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            if blob != SOURCE_BLOBS[path]:
                blockers.append(f"SOURCE_BLOB_MISMATCH:{path}")
                continue
            expected = _expected_nodes(text, scope)
        except (OSError, ValueError, SyntaxError) as exc:
            blockers.append(f"SOURCE_UNREADABLE:{path}:{type(exc).__name__}")
            continue
        try:
            actual = ast.parse((ROOT / scope["vendor_path"]).read_text(encoding="utf-8")).body
            # Compare the entire ordered module: no added statements or imports.
            if [_dump(node) for node in actual] != [_dump(node) for node in expected]:
                blockers.append(f"VENDOR_AST_MISMATCH:{scope['vendor_path']}")
        except (OSError, ValueError, SyntaxError) as exc:
            blockers.append(f"VENDOR_UNREADABLE:{scope['vendor_path']}:{type(exc).__name__}")
    return _report(blockers)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root", type=Path,
        default=Path(os.environ.get("TR_CHARTDESK_SOURCE_ROOT", str(DEFAULT_SOURCE_ROOT))),
        help="Pinned chart-desk checkout, read as text only; defaults to TR_CHARTDESK_SOURCE_ROOT or retained local checkout",
    )
    args = parser.parse_args()
    report = check_source_parity(args.source_root)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["subset_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
