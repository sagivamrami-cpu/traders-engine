"""Audit a pinned reversal/PVSRA subset using text and ASTs only.

Never imports or executes the supplied source checkout (or the vendor files).
The trusted audit scope and blob identities are fixed here independently of
the manifest, so removing manifest rows cannot reduce the verification scope.
"""

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/trees/level-reversal-contracts.json"
SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
SOURCE_BLOBS = {
    "chartdesk/level_reversal.py": "7c0eee53d97a1ba9280626fdb2d20eba61b5aa1b",
    "chartdesk/tr.py": "8297c712d20404880d4d8949e96efbf48613909c",
    "chartdesk/auction.py": "6f9539269ccdbb1174c0ffecb343e610c304b984",
}
DETECTOR_SYMBOLS = (
    "ELIGIBLE_LEVELS", "ELIGIBLE_MA_PREFIXES", "SELL_VECTORS", "BUY_VECTORS",
    "TF_MINUTES", "LIVE_MAX_AGE_S", "Reversal", "_utc", "_normalise",
    "is_eligible_level", "_eligible", "_episode", "two_bar_signal",
    "single_bar_signal", "detect_frame",
)
# Zero-based positions in the original pvsra body, including its docstring at 0.
PVSRA_STATEMENT_INDICES = (*range(1, 8), *range(12, 22), 23)
REQUIRED_FILES = {
    "chartdesk/level_reversal.py": {
        "vendor_path": "trading_system/tree_replay/_vendor/level_reversal.py",
        "symbols": list(DETECTOR_SYMBOLS),
        "allowed_imports": "from __future__ import annotations\nfrom dataclasses import dataclass\nimport pandas as pd\nfrom . import pvsra as tr",
        "statement_indices": [],
    },
    "chartdesk/tr.py": {
        "vendor_path": "trading_system/tree_replay/_vendor/pvsra.py",
        "symbols": ["pvsra"],
        "allowed_imports": "import numpy as np\nimport pandas as pd",
        "statement_indices": list(PVSRA_STATEMENT_INDICES),
    },
    "chartdesk/auction.py": {
        "vendor_path": None,
        "symbols": ["resolve_slots"],
        "allowed_imports": "",
        "statement_indices": [],
    },
}


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _name(node):
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _without_docstring(body):
    if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        return body[1:]
    return body


def _selected(module, symbols):
    nodes = [node for node in module.body if _name(node) in symbols]
    if len(nodes) != len(symbols) or {_name(node) for node in nodes} != set(symbols):
        raise ValueError("SOURCE_SYMBOL_SET_MISMATCH")
    return nodes


def _contract_blockers(contract):
    if not isinstance(contract, dict):
        return ["CONTRACT_INVALID_OBJECT"]
    blockers = []
    for key, expected in (
        ("schema_version", "chartdesk-level-reversal-contracts-v1"),
        ("repository", "chart-desk"), ("commit", SOURCE_COMMIT),
        ("specialization", "pvsra-default-auction-false-v1"),
    ):
        if contract.get(key) != expected:
            blockers.append(f"CONTRACT_{key.upper()}_MISMATCH")
    rows = contract.get("files")
    if not isinstance(rows, list):
        return blockers + ["CONTRACT_FILE_SET_MISMATCH"]
    paths = [row.get("path") if isinstance(row, dict) else None for row in rows]
    if (not all(isinstance(path, str) for path in paths) or
            len(paths) != len(REQUIRED_FILES) or set(paths) != set(REQUIRED_FILES)):
        return blockers + ["CONTRACT_FILE_SET_MISMATCH"]
    for row in rows:
        path = row["path"]
        expected = REQUIRED_FILES[path]
        for field in ("vendor_path", "symbols", "statement_indices"):
            # JSON equality alone lets bool masquerade as a statement index.
            if (field not in row or row[field] != expected[field] or
                    field == "statement_indices" and any(type(i) is not int for i in row[field])):
                blockers.append(f"CONTRACT_{field.upper()}_MISMATCH:{path}")
        if row.get("git_blob_sha1") != SOURCE_BLOBS[path]:
            blockers.append(f"CONTRACT_BLOB_MISMATCH:{path}")
        try:
            imports = row.get("allowed_imports")
            if not isinstance(imports, str) or _dump(ast.parse(imports)) != _dump(ast.parse(expected["allowed_imports"])):
                blockers.append(f"CONTRACT_IMPORT_MISMATCH:{path}")
        except (ValueError, SyntaxError):
            blockers.append(f"CONTRACT_IMPORT_MISMATCH:{path}")
    return blockers


def _specialize_pvsra(source, auction):
    """Prove the branch preconditions before selecting exact source statements."""
    signature = ast.parse(
        "def pvsra(df: pd.DataFrame, lookback: int = 10, *, "
        "auction: bool | pd.Series = False, session_tz: str = A.DEFAULT_TZ) "
        "-> pd.DataFrame: pass"
    ).body[0]
    if (not isinstance(source, ast.FunctionDef) or source.decorator_list or
            _dump(source.args) != _dump(signature.args) or
            _dump(source.returns) != _dump(signature.returns) or
            len(source.body) != 24 or ast.get_docstring(source) is None):
        raise ValueError("PVSRA_SOURCE_DEFAULTS_MISMATCH")
    expected_setup = ast.parse(
        'slots = A.resolve_slots(df.index, auction, session_tz)\n'
        'amask = None if slots is None else slots.ne("")\n'
        'extra: dict = {}'
    ).body
    if [_dump(n) for n in source.body[8:11]] != [_dump(n) for n in expected_setup]:
        raise ValueError("PVSRA_SOURCE_SETUP_MISMATCH")
    branch, guard = source.body[11], source.body[22]
    expected_branch = ast.parse(
        "if amask is None or not bool(amask.any()):\n    slots = None"
    ).body[0]
    if (not isinstance(branch, ast.If) or not branch.orelse or
            _dump(branch.test) != _dump(expected_branch.test) or
            [_dump(n) for n in branch.body] != [_dump(n) for n in expected_branch.body] or
            not isinstance(guard, ast.If) or guard.orelse or
            _dump(guard.test) != _dump(ast.parse("slots is not None", mode="eval").body)):
        raise ValueError("PVSRA_SOURCE_BRANCH_MISMATCH")
    resolver_signature = ast.parse(
        "def resolve_slots(index, auction, tz: str = DEFAULT_TZ) -> pd.Series | None: pass"
    ).body[0]
    resolver_first = ast.parse("if auction is False or auction is None:\n    return None").body[0]
    if (not isinstance(auction, ast.FunctionDef) or auction.decorator_list or
            _dump(auction.args) != _dump(resolver_signature.args) or
            _dump(auction.returns) != _dump(resolver_signature.returns) or
            not _without_docstring(auction.body) or
            _dump(_without_docstring(auction.body)[0]) != _dump(resolver_first)):
        raise ValueError("AUCTION_DEFAULT_PRECONDITION_MISMATCH")
    result = copy.deepcopy(source)
    result.args.kwonlyargs = []
    result.args.kw_defaults = []
    result.body = [copy.deepcopy(source.body[i]) for i in PVSRA_STATEMENT_INDICES]
    return result


def _report(blockers):
    return {"source_commit": SOURCE_COMMIT, "subset_verified": not blockers,
            "source_subset_verified": not blockers, "blockers": blockers,
            "ready_for_replay": False, "ready_for_training": False}


def check_source_parity(source_root: Path) -> dict:
    """Fail closed on missing, malformed or changed coverage/source/vendor text."""
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        blockers = _contract_blockers(contract)
        if blockers:
            return _report(blockers)
        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
        pins = [row.get("commit") for row in baseline["repositories"] if row.get("name") == "chart-desk"]
        if pins != [SOURCE_COMMIT]:
            return _report(["BASELINE_COMMIT_MISMATCH"])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return _report([f"CONTRACT_UNREADABLE:{type(exc).__name__}"])

    originals = {}
    for path, scope in REQUIRED_FILES.items():
        try:
            # read_text normalizes checkout CRLF to Git's canonical LF text.
            text = (Path(source_root) / path).read_text(encoding="utf-8")
            data = text.encode("utf-8")
            digest = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            if digest != SOURCE_BLOBS[path]:
                blockers.append(f"SOURCE_BLOB_MISMATCH:{path}")
                continue
            originals[path] = _selected(ast.parse(text), scope["symbols"])
        except (OSError, ValueError, SyntaxError) as exc:
            blockers.append(f"SOURCE_UNREADABLE:{path}:{exc}")
    if blockers:
        return _report(blockers)
    try:
        specialized = _specialize_pvsra(originals["chartdesk/tr.py"][0], originals["chartdesk/auction.py"][0])
    except (ValueError, TypeError, AttributeError) as exc:
        return _report([f"SPECIALIZATION_INVALID:{exc}"])

    for path, scope in REQUIRED_FILES.items():
        if scope["vendor_path"] is None:
            continue
        try:
            vendor = ast.parse((ROOT / scope["vendor_path"]).read_text(encoding="utf-8"))
            actual = _without_docstring(vendor.body)
            expected = ast.parse(scope["allowed_imports"]).body
            expected += [specialized] if path == "chartdesk/tr.py" else originals[path]
            if path == "chartdesk/tr.py":
                # Only module/function documentation may differ; arguments,
                # decorators and every executable nested statement must match.
                for node in actual:
                    if isinstance(node, ast.FunctionDef) and node.name == "pvsra":
                        node.body = _without_docstring(node.body)
            # Full ordered module comparison rejects extra/duplicate symbols,
            # imports, executable expressions and mutations hidden in decorators.
            if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
                blockers.append(f"VENDOR_AST_MISMATCH:{scope['vendor_path']}")
        except (OSError, ValueError, SyntaxError) as exc:
            blockers.append(f"VENDOR_UNREADABLE:{scope['vendor_path']}:{type(exc).__name__}")
    return _report(blockers)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True, help="Pinned chart-desk checkout; read as text only")
    args = parser.parse_args()
    report = check_source_parity(args.source_root)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["subset_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
