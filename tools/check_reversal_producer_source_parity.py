"""Audit pinned original find/conflicts and their accepted graph as inert text.

Only audit tools are imported. Source checkouts, vendor calculation modules and
runtime clock wrappers are never imported or executed by this tool.
"""

import argparse
import ast
import hashlib
import importlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/trees/reversal-producer-contracts.json"
SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
SOURCE_PATH = "chartdesk/level_reversal.py"
SOURCE_BLOB = "7c0eee53d97a1ba9280626fdb2d20eba61b5aa1b"
VENDOR_PATH = "trading_system/tree_replay/_vendor/reversal_producer.py"
DEFAULT_SOURCE_ROOT = Path(
    "C:/Users/roeea/AppData/Local/Temp/"
    "tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk"
)
ALLOWED_IMPORTS = (
    "from __future__ import annotations\n"
    "import pandas as pd\n"
    "from .level_reversal import Reversal, _utc, LIVE_MAX_AGE_S\n"
    "from .reversal_pricing import build_plan\n"
    "from . import pricing as tradeplan"
)
MAP_MANIFEST = "configs/trees/levelmap-source-contracts.json"
# Independently sealed accepted manifest, canonical json.dumps(sort_keys=True,
# allow_nan=False). This is not read from the producer's supplied manifest.
MAP_MANIFEST_SHA256 = "0cd26630c3274cdaf7c4959c87d8ac06be89652229ed24c541fd46c7cd76a5ab"
ADAPTATIONS = [
    "Rename find to find_at with required keyword-only decision_time, source, map_source, detector",
    "After the original docstring bind basis = source, levelmap = map_source, detect_frame = detector",
    "Replace the original now clock assignment with now = _utc(decision_time)",
    "Preserve all remaining find statements and the complete conflicts function unchanged",
]
EXPECTED_CONTRACT = {
    "schema_version": "chartdesk-reversal-producer-contracts-v1",
    "repository": "chart-desk",
    "commit": SOURCE_COMMIT,
    "scope": "Original reversal find and conflicts with injected offline dependencies and decision time; no outer admission",
    "files": [{"path": SOURCE_PATH, "git_blob_sha1": SOURCE_BLOB,
               "vendor_path": VENDOR_PATH, "symbols": ["find", "conflicts"],
               "allowed_imports": ALLOWED_IMPORTS}],
    "adaptations": ADAPTATIONS,
    "dependency_audits": {
        "levelmap": {"tool": "tools/check_levelmap_source_parity.py:check_source_parity",
                     "manifest_path": MAP_MANIFEST, "manifest_sha256": MAP_MANIFEST_SHA256},
    },
    "ready_for_replay": False,
    "ready_for_training": False,
}
INPUT_ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
                ImportError, StopIteration)


def _json(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _expected_module(text):
    """Prove injection preconditions before projecting the original bodies."""
    tree = ast.parse(text)
    selected = [node for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in ("find", "conflicts")]
    if [node.name for node in selected] != ["find", "conflicts"]:
        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
    find, conflicts = selected
    signature = ast.parse("def find(symbol: str, *, now=None): pass").body[0]
    if (not isinstance(find, ast.FunctionDef) or find.decorator_list or find.returns is not None
            or find.type_comment is not None or _dump(find.args) != _dump(signature.args)):
        raise ValueError("SOURCE_SIGNATURE_MISMATCH:find")
    conflict_signature = ast.parse(
        "def conflicts(reversal: tradeplan.Plan | None, candidate: tradeplan.Plan | None) -> bool: pass"
    ).body[0]
    if (not isinstance(conflicts, ast.FunctionDef) or conflicts.decorator_list
            or conflicts.type_comment is not None
            or _dump(conflicts.args) != _dump(conflict_signature.args)
            or _dump(conflicts.returns) != _dump(conflict_signature.returns)):
        raise ValueError("SOURCE_SIGNATURE_MISMATCH:conflicts")
    if ast.get_docstring(find) is None:
        raise ValueError("SOURCE_DOCSTRING_MISSING:find")
    # All new parameter names must be unused. Existing globals must not already
    # be locally bound: inserting bindings must change only their dependency.
    injected = {"decision_time", "source", "map_source", "detector"}
    rebound = {"basis", "levelmap", "detect_frame"}
    for node in ast.walk(find):
        if isinstance(node, ast.Name) and (
                node.id in injected or (node.id in rebound and not isinstance(node.ctx, ast.Load))):
            raise ValueError("SOURCE_INJECTION_NAME_COLLISION")
        if isinstance(node, (ast.Global, ast.Nonlocal)) and (injected | rebound).intersection(node.names):
            raise ValueError("SOURCE_INJECTION_NAME_COLLISION")
        if isinstance(node, ast.arg) and node.arg in injected | rebound:
            raise ValueError("SOURCE_INJECTION_NAME_COLLISION")
    clock = ast.parse('now = _utc(pd.Timestamp.now(tz="UTC") if now is None else now)').body[0]
    if len(find.body) < 2 or _dump(find.body[1]) != _dump(clock):
        raise ValueError("SOURCE_CLOCK_ASSIGNMENT_MISMATCH")
    if sum(_dump(node) == _dump(clock.value) for node in ast.walk(find)) != 1:
        raise ValueError("SOURCE_CLOCK_COUNT_MISMATCH")
    if sum(isinstance(node, ast.Name) and node.id == "now" and isinstance(node.ctx, ast.Store)
           for node in ast.walk(find)) != 1:
        raise ValueError("SOURCE_CLOCK_BINDING_MISMATCH")
    find.name = "find_at"
    find.args = ast.parse(
        "def find_at(symbol: str, *, decision_time, source, map_source, detector): pass"
    ).body[0].args
    bindings = ast.parse(
        "basis = source\nlevelmap = map_source\ndetect_frame = detector\nnow = _utc(decision_time)"
    ).body
    find.body = [find.body[0]] + bindings + find.body[2:]
    return ast.Module(body=ast.parse(ALLOWED_IMPORTS).body + [find, conflicts], type_ignores=[])


def _audit_levelmap(source_root, blockers):
    try:
        manifest = json.loads((ROOT / MAP_MANIFEST).read_text(encoding="utf-8"))
        digest = hashlib.sha256(_json(manifest).encode("utf-8")).hexdigest()
        if digest != MAP_MANIFEST_SHA256:
            blockers.append("DEPENDENCY_CONTRACT_MISMATCH:levelmap")
    except INPUT_ERRORS as exc:
        blockers.append(f"DEPENDENCY_CONTRACT_UNREADABLE:levelmap:{type(exc).__name__}")
    # Still invoke the complete accepted audit even if the manifest is bad.
    try:
        prefix = f"{__package__}." if __package__ else ""
        checker = importlib.import_module(prefix + "check_levelmap_source_parity")
        result = checker.check_source_parity(source_root)
        if (result.get("subset_verified") is not True
                or result.get("source_subset_verified") is not True
                or result.get("blockers") != []
                or result.get("ready_for_replay") is not False
                or result.get("ready_for_training") is not False):
            blockers.append("DEPENDENCY_AUDIT_FAILED:levelmap")
        return result
    except INPUT_ERRORS as exc:
        reason = f"DEPENDENCY_AUDIT_UNREADABLE:levelmap:{type(exc).__name__}"
        blockers.append(reason)
        return {"subset_verified": False, "source_subset_verified": False,
                "blockers": [reason], "ready_for_replay": False, "ready_for_training": False}


def check_source_parity(source_root: Path) -> dict:
    """Return a fail-closed report for missing, malformed or mutated inputs."""
    blockers = []
    try:
        manifest = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if _json(manifest) != _json(EXPECTED_CONTRACT):
            blockers.append("CONTRACT_MISMATCH")
        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
        pins = [row.get("commit") for row in baseline["repositories"] if row.get("name") == "chart-desk"]
        if pins != [SOURCE_COMMIT]:
            blockers.append("BASELINE_COMMIT_MISMATCH")
    except INPUT_ERRORS as exc:
        blockers.append(f"CONTRACT_UNREADABLE:{type(exc).__name__}")
    dependency = _audit_levelmap(source_root, blockers)
    expected = None
    try:
        # Normalize checkout newlines to Git LF without importing source code.
        text = (Path(source_root) / SOURCE_PATH).read_text(encoding="utf-8")
        data = text.encode("utf-8")
        blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        if blob != SOURCE_BLOB:
            blockers.append(f"SOURCE_BLOB_MISMATCH:{SOURCE_PATH}")
        else:
            expected = _expected_module(text)
    except INPUT_ERRORS as exc:
        blockers.append(f"SOURCE_UNREADABLE:{SOURCE_PATH}:{type(exc).__name__}")
    try:
        actual = ast.parse((ROOT / VENDOR_PATH).read_text(encoding="utf-8"))
        if expected is not None and _dump(actual) != _dump(expected):
            blockers.append(f"VENDOR_AST_MISMATCH:{VENDOR_PATH}")
    except INPUT_ERRORS as exc:
        blockers.append(f"VENDOR_UNREADABLE:{VENDOR_PATH}:{type(exc).__name__}")
    return {"status": "BLOCKED" if blockers else "VERIFIED", "source_commit": SOURCE_COMMIT,
            "subset_verified": not blockers, "source_subset_verified": not blockers,
            "blockers": blockers, "dependency_audits": {"levelmap": dependency},
            "ready_for_replay": False, "ready_for_training": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root", type=Path,
        default=Path(os.environ.get("TR_CHARTDESK_SOURCE_ROOT", str(DEFAULT_SOURCE_ROOT))),
        help="Pinned chart-desk source text; overrides environment and retained default",
    )
    report = check_source_parity(parser.parse_args().source_root)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["subset_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
