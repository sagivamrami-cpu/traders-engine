"""Verify the audited EMA subset against pinned source text; never import that repo."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/trees/ema-feature-contracts.json"
SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
# Fixed audit scope, independent of the manifest rows being checked. Blob values
# remain trusted manifest configuration; this is not a manifest authenticity check.
REQUIRED_FILES = {
    "chartdesk/indicators.py": (
        "trading_system/tree_replay/_vendor/indicators.py",
        {"_seeded_recursive", "ema", "stdev"},
        "from __future__ import annotations\nimport numpy as np\nimport pandas as pd",
    ),
    "chartdesk/tr.py": (
        "trading_system/tree_replay/_vendor/tr.py",
        {"TR_EMAS", "emas", "ema_cloud"},
        "from __future__ import annotations\nimport pandas as pd\nfrom . import indicators as I",
    ),
    "chartdesk/features.py": (None, set(), ""),
}


def _name(node):
    if isinstance(node, ast.FunctionDef):
        return node.name
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _contract_blockers(contract, pin):
    """Validate fixed source-identity/coverage before reading source/vendor files."""
    if not isinstance(contract, dict):
        return ["CONTRACT_INVALID_OBJECT"]
    blockers = []
    for field, expected in (("schema_version", "chartdesk-ema-contracts-v1"),
                            ("repository", "chart-desk"), ("commit", SOURCE_COMMIT)):
        if contract.get(field) != expected:
            blockers.append(f"CONTRACT_{field.upper()}_MISMATCH")
    if pin != SOURCE_COMMIT:
        blockers.append("CONTRACT_COMMIT_MISMATCH")
    rows = contract.get("files")
    if not isinstance(rows, list):
        return blockers + ["CONTRACT_FILE_SET_MISMATCH"]
    paths = [row.get("path") if isinstance(row, dict) else None for row in rows]
    if (not all(isinstance(path, str) for path in paths) or
            len(paths) != len(REQUIRED_FILES) or set(paths) != set(REQUIRED_FILES)):
        return blockers + ["CONTRACT_FILE_SET_MISMATCH"]
    for row in rows:
        path = row["path"]
        vendor_path, expected_symbols, expected_imports = REQUIRED_FILES[path]
        if "vendor_path" not in row or row["vendor_path"] != vendor_path:
            blockers.append(f"CONTRACT_VENDOR_PATH_MISMATCH:{path}")
        symbols = row.get("symbols")
        if (not isinstance(symbols, list) or
                not all(isinstance(symbol, str) for symbol in symbols) or
                len(symbols) != len(expected_symbols) or set(symbols) != expected_symbols):
            blockers.append(f"CONTRACT_SYMBOL_SET_MISMATCH:{path}")
        imports = row.get("allowed_imports")
        try:
            if not isinstance(imports, str):
                raise ValueError("allowed_imports must be text")
            # Compare full AST lists (order-insensitive), preserving duplicates;
            # comments/spacing may vary but neither code nor extra imports may enter.
            actual = sorted(_dump(node) for node in ast.parse(imports).body)
            expected = sorted(_dump(node) for node in ast.parse(expected_imports).body)
            if actual != expected:
                raise ValueError("allowed_imports differs from audited scope")
        except (ValueError, SyntaxError):
            blockers.append(f"CONTRACT_IMPORT_MISMATCH:{path}")
        blob = row.get("git_blob_sha1")
        if not isinstance(blob, str) or re.fullmatch(r"[0-9a-f]{40}", blob) is None:
            blockers.append(f"CONTRACT_BLOB_INVALID:{path}")
    return blockers


def check_source_parity(source_root: Path) -> dict:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
    pin = next(row["commit"] for row in baseline["repositories"] if row["name"] == "chart-desk")
    blockers = _contract_blockers(contract, pin)
    if blockers:
        return {"source_commit": pin, "source_subset_verified": False,
                "blockers": blockers, "ready_for_replay": False, "ready_for_training": False}
    for row in contract["files"]:
        try:
            # read_text normalizes checkout CRLF; Git blob identity is computed
            # against the canonical LF text, including its final newline.
            source = (Path(source_root) / row["path"]).read_text(encoding="utf-8")
            data = source.encode("utf-8")
            blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            if blob != row["git_blob_sha1"]:
                blockers.append(f"SOURCE_BLOB_MISMATCH:{row['path']}")
                continue
            if row["vendor_path"] is None:
                continue
            original = ast.parse(source)
            vendor = ast.parse((ROOT / row["vendor_path"]).read_text(encoding="utf-8"))
            symbols = set(row["symbols"])
            originals = {name: node for node in original.body if (name := _name(node)) in symbols}
            copied = [node for node in vendor.body if _name(node) in symbols]
            if len(copied) != len(symbols) or {_name(n) for n in copied} != symbols:
                blockers.append(f"SYMBOL_SET_MISMATCH:{row['vendor_path']}")
            for node in copied:
                if _name(node) not in originals or _dump(node) != _dump(originals[_name(node)]):
                    blockers.append(f"FUNCTION_MISMATCH:{row['path']}:{_name(node)}")
            allowed_imports = {_dump(n) for n in ast.parse(row["allowed_imports"]).body}
            actual_imports = {_dump(n) for n in vendor.body if isinstance(n, (ast.Import, ast.ImportFrom))}
            if allowed_imports != actual_imports:
                blockers.append(f"IMPORT_MISMATCH:{row['vendor_path']}")
            for node in vendor.body:
                if (_name(node) in symbols or isinstance(node, (ast.Import, ast.ImportFrom)) or
                    isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
                    continue
                blockers.append(f"UNEXPECTED_TOP_LEVEL:{row['vendor_path']}")
        except (OSError, ValueError, SyntaxError) as exc:
            blockers.append(f"SOURCE_UNREADABLE:{row['path']}:{type(exc).__name__}")
    return {"source_commit": pin, "source_subset_verified": not blockers,
            "blockers": blockers, "ready_for_replay": False, "ready_for_training": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True, help="Pinned chart-desk checkout")
    args = parser.parse_args()
    try:
        report = check_source_parity(args.source_root)
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        print(json.dumps({"error": str(exc), "source_subset_verified": False,
                          "ready_for_replay": False, "ready_for_training": False}))
        return 1
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["source_subset_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
