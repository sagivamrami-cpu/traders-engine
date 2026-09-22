"""Fail-closed text/AST audit of the explicit-clock correction subset only.

Neither the source nor vendor module is imported or executed by this auditor.
Expected pins, coverage, imports and specialization are fixed independently of
the manifest. Passing does not establish full replay or training readiness.
"""

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/trees/correction-source-contracts.json"
SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
SOURCE_BLOB = "f3396f3a9fefd71f0f71422001a5521af0a05cd2"
SOURCE_PATH = "chartdesk/basis.py"
VENDOR_PATH = "trading_system/tree_replay/_vendor/correction.py"
SYMBOLS = ["Correction", "EXCHANGE_NATIVE", "broker_shape_ok"]
IMPORTS = "from __future__ import annotations\nfrom dataclasses import dataclass\nimport pandas as pd"
DEFAULT_SOURCE_ROOT = Path(
    "C:/Users/roeea/AppData/Local/Temp/"
    "tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk"
)
EXPECTED_CONTRACT = {
    "schema_version": "chartdesk-correction-source-contracts-v1",
    "repository": "chart-desk",
    "commit": SOURCE_COMMIT,
    "scope": "Pure Correction and broker-shape evidence with an explicit replay clock; no offset application or admission",
    "files": [{
        "path": SOURCE_PATH, "git_blob_sha1": SOURCE_BLOB,
        "vendor_path": VENDOR_PATH, "symbols": SYMBOLS,
        "allowed_imports": IMPORTS,
        "adaptations": [
            "Rename broker_shape_ok to broker_shape_ok_at",
            "Add required keyword-only decision_time argument",
            'Replace the single pd.Timestamp.now("UTC") call with pd.Timestamp(decision_time)',
        ],
    }],
    "ready_for_replay": False,
    "ready_for_training": False,
}


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _name(node):
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None


def _expected_module(text):
    source = ast.parse(text)
    imports = ast.parse(IMPORTS).body
    allowed = [_dump(node) for node in imports]
    source_imports = [node for node in source.body
                      if isinstance(node, (ast.Import, ast.ImportFrom)) and _dump(node) in allowed]
    if [_dump(node) for node in source_imports] != allowed:
        raise ValueError("SOURCE_IMPORT_ORDER_OR_SET_MISMATCH")
    selected = [node for node in source.body if _name(node) in SYMBOLS]
    if [_name(node) for node in selected] != SYMBOLS:
        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
    predicate = selected[-1]
    expected_clock = ast.parse('pd.Timestamp.now("UTC")', mode="eval").body
    clock_calls = [node for node in ast.walk(predicate)
                   if isinstance(node, ast.Call) and _dump(node) == _dump(expected_clock)]
    if len(clock_calls) != 1:
        raise ValueError("SOURCE_CLOCK_CALL_MISMATCH")
    predicate.name = "broker_shape_ok_at"
    predicate.args.kwonlyargs.append(ast.arg(arg="decision_time"))
    predicate.args.kw_defaults.append(None)
    # Mutate this single matched AST call; preserve every other node verbatim.
    replacement = ast.parse("pd.Timestamp(decision_time)", mode="eval").body
    clock_calls[0].func = replacement.func
    clock_calls[0].args = replacement.args
    clock_calls[0].keywords = replacement.keywords
    return ast.Module(body=imports + selected, type_ignores=[])


def _report(blockers):
    return {
        "source_commit": SOURCE_COMMIT, "subset_verified": not blockers,
        "source_subset_verified": not blockers, "blockers": blockers,
        "ready_for_replay": False, "ready_for_training": False,
    }


def check_source_parity(source_root: Path) -> dict:
    """Verify the fixed baseline, full source blob and entire ordered vendor AST."""
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        # JSON serialization distinguishes false from 0, unlike Python equality.
        if json.dumps(contract, sort_keys=True, allow_nan=False) != json.dumps(EXPECTED_CONTRACT, sort_keys=True, allow_nan=False):
            return _report(["CONTRACT_MISMATCH"])
        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
        pins = [row.get("commit") for row in baseline["repositories"] if row.get("name") == "chart-desk"]
        if pins != [SOURCE_COMMIT]:
            return _report(["BASELINE_COMMIT_MISMATCH"])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return _report([f"CONTRACT_UNREADABLE:{type(exc).__name__}"])

    try:
        # read_text uses universal newlines: checkout CRLF becomes canonical LF.
        text = (Path(source_root) / SOURCE_PATH).read_text(encoding="utf-8")
        data = text.encode("utf-8")
        blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        if blob != SOURCE_BLOB:
            return _report([f"SOURCE_BLOB_MISMATCH:{SOURCE_PATH}"])
        expected = _expected_module(text)
    except (OSError, ValueError, SyntaxError) as exc:
        return _report([f"SOURCE_UNREADABLE:{SOURCE_PATH}:{type(exc).__name__}"])
    try:
        actual = ast.parse((ROOT / VENDOR_PATH).read_text(encoding="utf-8"))
        if _dump(actual) != _dump(expected):
            return _report([f"VENDOR_AST_MISMATCH:{VENDOR_PATH}"])
    except (OSError, ValueError, SyntaxError) as exc:
        return _report([f"VENDOR_UNREADABLE:{VENDOR_PATH}:{type(exc).__name__}"])
    return _report([])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root", type=Path,
        default=Path(os.environ.get("TR_CHARTDESK_SOURCE_ROOT", str(DEFAULT_SOURCE_ROOT))),
        help="Pinned chart-desk checkout (text only); overrides environment and retained default",
    )
    report = check_source_parity(parser.parse_args().source_root)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["subset_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
