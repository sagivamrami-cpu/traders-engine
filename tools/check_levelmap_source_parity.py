"""Audit the complete offline level-map graph as text/AST, never by execution.

The source identities, ordered projections, transformations and dependency
manifest identities are fixed here independently of the untrusted manifests.
Only audit tools are imported. No source or vendor module is executed.
"""

import argparse
import ast
import hashlib
import importlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/trees/levelmap-source-contracts.json"
SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
DEFAULT_SOURCE_ROOT = Path(
    "C:/Users/roeea/AppData/Local/Temp/"
    "tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk"
)
SOURCE_BLOBS = {
    "chartdesk/levelmap.py": "01fc9fe098aa7a5991ce62c3a83e870e4f0d5a2e",
    "chartdesk/sessions.py": "2f44d322178feb14b0488abda51b40581db5b31f",
}
REQUIRED_FILES = {
    "chartdesk/levelmap.py": {
        "vendor_path": "trading_system/tree_replay/_vendor/levelmap_build.py",
        "symbols": ["NamedLevel", "SESSION_OPEN_LEVELS", "_session_open_levels", "_ema_levels", "build"],
        "allowed_imports": "from __future__ import annotations\nfrom dataclasses import dataclass, field\nimport pandas as pd\nfrom . import map_tr as tr, quarters, map_sessions as sessions\nfrom .back_days import _back_day_levels",
    },
    "chartdesk/sessions.py": {
        "vendor_path": "trading_system/tree_replay/_vendor/map_sessions.py",
        "symbols": ["SessionSpec", "SESSIONS", "_hm", "psy_levels"],
        "allowed_imports": "from __future__ import annotations\nfrom dataclasses import dataclass, field\nfrom zoneinfo import ZoneInfo\nimport numpy as np\nimport pandas as pd",
    },
}
COMPOSITION_PATH = "trading_system/tree_replay/_vendor/map_tr.py"
COMPOSITION_IMPORTS = "from .tr import emas\nfrom .ranges import weekly_from_daily, monthly_from_daily, tr_levels"
# Verified from commit:path Git objects, not inherited manifest values. The
# existing EMA audit uses import/symbol sets; this graph additionally requires
# the complete ordered projection, including TR_EMAS before its default use.
STRICT_EMA_FILES = {
    "chartdesk/indicators.py": {
        "git_blob_sha1": "672f0428c3a81b86376d4f792ae40ecd174a2025",
        "vendor_path": "trading_system/tree_replay/_vendor/indicators.py",
        "symbols": ["_seeded_recursive", "ema", "stdev"],
        "allowed_imports": "from __future__ import annotations\nimport numpy as np\nimport pandas as pd",
    },
    "chartdesk/tr.py": {
        "git_blob_sha1": "8297c712d20404880d4d8949e96efbf48613909c",
        "vendor_path": "trading_system/tree_replay/_vendor/tr.py",
        "symbols": ["TR_EMAS", "emas", "ema_cloud"],
        "allowed_imports": "from __future__ import annotations\nimport pandas as pd\nfrom . import indicators as I",
    },
}
ADAPTATIONS = [
    "Add required keyword-only source and bind basis = source after each selected function docstring",
    "Rename build to build_at; add required keyword-only decision_time",
    "Rename _session_open_levels to _session_open_levels_at; replace optional now with required keyword-only decision_time",
    'Replace exactly pd.Timestamp.now("UTC") if now is None else pd.Timestamp(now) with pd.Timestamp(decision_time)',
    "Pass source and decision_time to the session helper; pass source to the EMA helper",
]
# Canonical JSON SHA256, including source blob pins and all metadata. In
# particular the earlier EMA auditor treats blobs as manifest configuration;
# sealing its accepted manifest here prevents changing both source and its pin.
DEPENDENCIES = {
    "range": ("check_range_source_parity", {
        "range-level-contracts.json": "f2420531d29c7234d9755fca96da1a43243728fa512cc9717bc380b46d830765",
    }),
    "pricing": ("check_pricing_source_parity", {
        "reversal-pricing-contracts.json": "1befa8299d48b3786e9c7ac1b974065bb01a243106e413baf34bf7d2c680e7b1",
        "level-reversal-contracts.json": "7351516739d7c78cd1ee7198509bb86d39ea041879a1620b24e6d39d2b147a4a",
    }),
    "ema": ("check_ema_source_parity", {
        "ema-feature-contracts.json": "794f1612b6f91dbf129c260cf6cc05c37572ba3174b49959494bbe885ce0174a",
    }),
    "correction": ("check_correction_source_parity", {
        "correction-source-contracts.json": "7f64ccb82612bbba66b3504dcad7bf08f646ff318b2cdfeacf629df35c9b4d98",
    }),
}
EXPECTED_CONTRACT = {
    "schema_version": "chartdesk-levelmap-source-contracts-v1",
    "repository": "chart-desk", "commit": SOURCE_COMMIT,
    "scope": "Complete original level-map calculation graph with injected offline source and explicit decision time; no frame validation or admission",
    "files": [{"path": path, "git_blob_sha1": SOURCE_BLOBS[path], **scope}
              for path, scope in REQUIRED_FILES.items()],
    "adaptations": ADAPTATIONS,
    "composition": {"vendor_path": COMPOSITION_PATH, "allowed_imports": COMPOSITION_IMPORTS},
    "strict_ema_dependencies": {
        "files": [{"path": path, **scope} for path, scope in STRICT_EMA_FILES.items()],
        "ignored_vendor_statements": "Only an optional initial module docstring",
    },
    "dependency_audits": {
        name: {"tool": f"tools/{tool}.py:check_source_parity", "manifest_sha256": manifests}
        for name, (tool, manifests) in DEPENDENCIES.items()
    },
    "ready_for_replay": False, "ready_for_training": False,
}
INPUT_ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
                ImportError, StopIteration)


def _json(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _name(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        return getattr(node.targets[0], "id", None)
    if isinstance(node, ast.AnnAssign):
        return getattr(node.target, "id", None)
    return None


def _exactly_one(tree, expression):
    expected = ast.parse(expression, mode="eval").body
    found = [node for node in ast.walk(tree) if _dump(node) == _dump(expected)]
    if len(found) != 1:
        raise ValueError(f"SOURCE_TRANSFORMATION_COUNT_MISMATCH:{expression}")
    return found[0]


def _replace_expression(original, expression):
    replacement = ast.parse(expression, mode="eval").body
    # Callers use this only when both expressions have the same AST node type.
    if type(original) is not type(replacement):
        raise ValueError("SOURCE_TRANSFORMATION_TYPE_MISMATCH")
    for field in original._fields:
        setattr(original, field, getattr(replacement, field))


def _specialize(function):
    signatures = {
        "_session_open_levels": "def f(symbol: str, missing: list | None = None, now=None): pass",
        "_ema_levels": "def f(symbol: str, missing: list | None = None): pass",
        "build": "def f(symbol: str, missing: list | None = None): pass",
    }
    expected = ast.parse(signatures[function.name]).body[0]
    if _dump(function.args) != _dump(expected.args) or function.decorator_list:
        raise ValueError(f"SOURCE_SIGNATURE_MISMATCH:{function.name}")
    if any(isinstance(node, ast.Name) and node.id == "source" for node in ast.walk(function)):
        raise ValueError("SOURCE_INJECTION_NAME_COLLISION")
    if function.name == "_session_open_levels":
        clock = _exactly_one(function, 'pd.Timestamp.now("UTC") if now is None else pd.Timestamp(now)')
        # Replace the complete conditional expression, preserving its assignment.
        assignments = [node for node in ast.walk(function)
                       if isinstance(node, ast.Assign) and node.value is clock]
        if len(assignments) != 1 or [_name(assignments[0])] != ["now"]:
            raise ValueError("SOURCE_CLOCK_ASSIGNMENT_MISMATCH")
        assignments[0].value = ast.parse("pd.Timestamp(decision_time)", mode="eval").body
        function.name = "_session_open_levels_at"
        function.args.args.pop()  # precondition above fixes optional now exactly
        function.args.defaults.pop()
    elif function.name == "build":
        session_call = _exactly_one(function, "_session_open_levels(symbol, missing)")
        ema_call = _exactly_one(function, "_ema_levels(symbol, missing)")
        _replace_expression(session_call, "_session_open_levels_at(symbol, missing, source=source, decision_time=decision_time)")
        _replace_expression(ema_call, "_ema_levels(symbol, missing, source=source)")
        function.name = "build_at"
    function.args.kwonlyargs.append(ast.arg(arg="source"))
    function.args.kw_defaults.append(None)
    if function.name != "_ema_levels":
        function.args.kwonlyargs.append(ast.arg(arg="decision_time"))
        function.args.kw_defaults.append(None)
    insertion = 1 if ast.get_docstring(function) is not None else 0
    function.body.insert(insertion, ast.parse("basis = source").body[0])
    return function


def _expected_module(text, path):
    scope = REQUIRED_FILES[path]
    source = ast.parse(text)
    imports = ast.parse(scope["allowed_imports"]).body
    if path == "chartdesk/levelmap.py":
        original_imports = ast.parse(
            "from __future__ import annotations\nfrom dataclasses import dataclass, field\n"
            "import pandas as pd\nfrom . import basis, data, quarters, sessions, tr"
        ).body
    else:
        original_imports = imports + ast.parse("from . import tr").body
    actual_imports = [node for node in source.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    if [_dump(n) for n in actual_imports] != [_dump(n) for n in original_imports]:
        raise ValueError("SOURCE_IMPORT_ORDER_OR_SET_MISMATCH")
    selected = [node for node in source.body if _name(node) in scope["symbols"]]
    if [_name(node) for node in selected] != scope["symbols"]:
        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
    if path == "chartdesk/levelmap.py":
        selected = [_specialize(node) if isinstance(node, ast.FunctionDef) else node for node in selected]
    return ast.Module(body=imports + selected, type_ignores=[])


def _report(blockers, dependencies):
    return {"source_commit": SOURCE_COMMIT, "subset_verified": not blockers,
            "source_subset_verified": not blockers, "blockers": blockers,
            "dependency_audits": dependencies,
            "ready_for_replay": False, "ready_for_training": False}


def _audit_dependencies(source_root, blockers):
    reports = {}
    for name, (tool, manifests) in DEPENDENCIES.items():
        for filename, expected_hash in manifests.items():
            try:
                value = json.loads((ROOT / "configs/trees" / filename).read_text(encoding="utf-8"))
                digest = hashlib.sha256(_json(value).encode("utf-8")).hexdigest()
                if digest != expected_hash:
                    blockers.append(f"DEPENDENCY_CONTRACT_MISMATCH:{name}:{filename}")
            except INPUT_ERRORS as exc:
                blockers.append(f"DEPENDENCY_CONTRACT_UNREADABLE:{name}:{filename}:{type(exc).__name__}")
        # Still call every dependency audit even when one manifest failed.
        try:
            prefix = f"{__package__}." if __package__ else ""
            checker = importlib.import_module(prefix + tool)
            result = checker.check_source_parity(source_root)
            reports[name] = result
            if (result.get("source_subset_verified") is not True or result.get("blockers") != []
                    or result.get("ready_for_replay") is not False
                    or result.get("ready_for_training") is not False):
                blockers.append(f"DEPENDENCY_AUDIT_FAILED:{name}")
                blockers.extend(f"DEPENDENCY:{name}:{item}" for item in result.get("blockers", []))
        except INPUT_ERRORS as exc:
            reason = f"DEPENDENCY_AUDIT_UNREADABLE:{name}:{type(exc).__name__}"
            blockers.append(reason)
            reports[name] = {"source_subset_verified": False, "blockers": [reason],
                             "ready_for_replay": False, "ready_for_training": False}
    return reports


def _compare_vendor(path, expected, blockers, *, prefix="", initial_docstring=False):
    try:
        actual = ast.parse((ROOT / path).read_text(encoding="utf-8"))
        if initial_docstring and ast.get_docstring(actual) is not None:
            actual.body = actual.body[1:]
        if _dump(actual) != _dump(expected):
            blockers.append(f"{prefix}VENDOR_AST_MISMATCH:{path}")
    except INPUT_ERRORS as exc:
        blockers.append(f"{prefix}VENDOR_UNREADABLE:{path}:{type(exc).__name__}")


def _audit_strict_ema(source_root, blockers):
    for path, scope in STRICT_EMA_FILES.items():
        try:
            text = (Path(source_root) / path).read_text(encoding="utf-8")
            data = text.encode("utf-8")
            blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            if blob != scope["git_blob_sha1"]:
                blockers.append(f"STRICT_EMA_SOURCE_BLOB_MISMATCH:{path}")
                continue
            source = ast.parse(text)
            imports = ast.parse(scope["allowed_imports"]).body
            allowed = [_dump(node) for node in imports]
            original_imports = [node for node in source.body
                                if isinstance(node, (ast.Import, ast.ImportFrom)) and _dump(node) in allowed]
            if [_dump(node) for node in original_imports] != allowed:
                raise ValueError("SOURCE_IMPORT_ORDER_OR_SET_MISMATCH")
            selected = [node for node in source.body if _name(node) in scope["symbols"]]
            if [_name(node) for node in selected] != scope["symbols"]:
                raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
            expected = ast.Module(body=imports + selected, type_ignores=[])
        except INPUT_ERRORS as exc:
            blockers.append(f"STRICT_EMA_SOURCE_UNREADABLE:{path}:{type(exc).__name__}")
            continue
        _compare_vendor(scope["vendor_path"], expected, blockers,
                        prefix="STRICT_EMA_", initial_docstring=True)


def check_source_parity(source_root: Path) -> dict:
    """Fail closed on missing/changed pins, source, projection or dependencies."""
    blockers = []
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if _json(contract) != _json(EXPECTED_CONTRACT):
            blockers.append("CONTRACT_MISMATCH")
        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
        pins = [row.get("commit") for row in baseline["repositories"] if row.get("name") == "chart-desk"]
        if pins != [SOURCE_COMMIT]:
            blockers.append("BASELINE_COMMIT_MISMATCH")
    except INPUT_ERRORS as exc:
        blockers.append(f"CONTRACT_UNREADABLE:{type(exc).__name__}")

    dependencies = _audit_dependencies(source_root, blockers)
    _audit_strict_ema(source_root, blockers)
    for path, scope in REQUIRED_FILES.items():
        try:
            # Universal newline reading normalizes checkout CRLF to Git LF.
            text = (Path(source_root) / path).read_text(encoding="utf-8")
            data = text.encode("utf-8")
            blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            if blob != SOURCE_BLOBS[path]:
                blockers.append(f"SOURCE_BLOB_MISMATCH:{path}")
                continue
            expected = _expected_module(text, path)
        except INPUT_ERRORS as exc:
            blockers.append(f"SOURCE_UNREADABLE:{path}:{type(exc).__name__}")
            continue
        _compare_vendor(scope["vendor_path"], expected, blockers)
    _compare_vendor(COMPOSITION_PATH, ast.parse(COMPOSITION_IMPORTS), blockers)
    return _report(blockers, dependencies)


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
