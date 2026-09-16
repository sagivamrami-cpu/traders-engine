"""Inert-text audit of the complete pinned admission calculation closure.

The retained desks are never imported or executed. Every runtime module,
including reused EMA/TR dependencies, is compared as a complete ordered AST.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
REPOSITORIES = {
    "chart-desk": "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9",
    "trading-floor": "d827dd792cbd1d396b4ee325879c63e57388e07a",
}
# Independent fixed authority: a supplied manifest cannot narrow this closure.
FILES = [
    {
        "repository": "chart-desk",
        "path": "chartdesk/matrix.py",
        "git_blob_sha1": "28641487567c457b6922c2a63055659867bb4248",
        "vendor_path": "trading_system/tree_replay/_vendor/admission_matrix.py",
        "symbols": [
            "WEIGHTS",
            "LOOKBACK",
            "ToolRead",
            "_clip",
            "_atr",
            "read_tr",
            "read_supertrend",
            "read_vwap",
            "read_structure",
            "TOOLS",
            "TFView",
            "read_tf",
            "_bar_ts"
        ],
        "allowed_imports": "from __future__ import annotations\nfrom dataclasses import dataclass\nfrom . import admission_toolkit as toolkit\nfrom . import tr\nfrom . import atr as tr_atr",
        "adaptation": "matrix_frame_and_atr_import"
    },
    {
        "repository": "chart-desk",
        "path": "chartdesk/toolkit.py",
        "git_blob_sha1": "dede9042db891d9ff2e6d6523918fe6d98b11ab0",
        "vendor_path": "trading_system/tree_replay/_vendor/admission_toolkit.py",
        "symbols": [
            "SUPERTREND_LADDER",
            "supertrend_ladder",
            "ladder_state",
            "vwap_bands"
        ],
        "allowed_imports": "from __future__ import annotations\nimport numpy as np\nimport pandas as pd\nfrom . import admission_indicators as I",
        "adaptation": "none"
    },
    {
        "repository": "chart-desk",
        "path": "chartdesk/indicators.py",
        "git_blob_sha1": "672f0428c3a81b86376d4f792ae40ecd174a2025",
        "vendor_path": "trading_system/tree_replay/_vendor/admission_indicators.py",
        "symbols": [
            "rma",
            "true_range",
            "atr",
            "supertrend"
        ],
        "allowed_imports": "from __future__ import annotations\nimport numpy as np\nimport pandas as pd\nfrom .indicators import _seeded_recursive",
        "adaptation": "none"
    },
    {
        "repository": "chart-desk",
        "path": "chartdesk/entry_quality.py",
        "git_blob_sha1": "0cd76eb8c607690610f4559e5946a60e8f7647ac",
        "vendor_path": "trading_system/tree_replay/_vendor/admission_quality.py",
        "symbols": [
            "MAX_REJECTION_AGE_S",
            "LABEL_NO_ANCHOR",
            "LABEL_NO_TRIGGER",
            "PREDICATE",
            "_ANCHOR_PREFIXES",
            "_PRICE_TAIL",
            "_NAME_SPLIT",
            "_COUNT_PREFIX",
            "anchor_names",
            "aligned_trigger",
            "still_defending",
            "opposing_label",
            "evaluate",
            "_rej"
        ],
        "allowed_imports": "from __future__ import annotations\nimport re",
        "adaptation": "none"
    },
    {
        "repository": "trading-floor",
        "path": "floor/marketclock.py",
        "git_blob_sha1": "246b01255a2203e2a04c2ef7d549f67087b4f2c9",
        "vendor_path": "trading_system/tree_replay/_vendor/admission_clocks.py",
        "symbols": [
            "TZ",
            "CLOSE_WEEKDAY,CLOSE_HOUR",
            "OPEN_WEEKDAY,OPEN_HOUR",
            "now_il",
            "is_closed",
            "WARN_MIN_BEFORE",
            "minutes_to_close",
            "entry_blocked"
        ],
        "allowed_imports": "from __future__ import annotations\nfrom datetime import datetime\nfrom zoneinfo import ZoneInfo",
        "adaptation": "required_aware_floor_clock"
    },
    {
        "repository": "chart-desk",
        "path": "chartdesk/windows.py",
        "git_blob_sha1": "53453b73e7f0c48647945e7d58ba6b30ed8d4102",
        "vendor_path": "trading_system/tree_replay/_vendor/admission_clocks.py",
        "symbols": [
            "TZ",
            "HUNT_START_H",
            "HUNT_END_H",
            "hunting",
            "outside_reason"
        ],
        "allowed_imports": "",
        "adaptation": "required_aware_hunting_clock_shared_TZ"
    },
    {
        "repository": "chart-desk",
        "path": "chartdesk/zones.py",
        "git_blob_sha1": "92f7b99373b4f266a1d80e2d997b965f973d7698",
        "vendor_path": "trading_system/tree_replay/_vendor/admission_swing.py",
        "symbols": [
            "SWING_K",
            "_last_swing"
        ],
        "allowed_imports": "from __future__ import annotations",
        "adaptation": "none"
    },
    {
        "repository": "chart-desk",
        "path": "chartdesk/indicators.py",
        "git_blob_sha1": "672f0428c3a81b86376d4f792ae40ecd174a2025",
        "vendor_path": "trading_system/tree_replay/_vendor/indicators.py",
        "symbols": [
            "_seeded_recursive",
            "ema",
            "stdev"
        ],
        "allowed_imports": "from __future__ import annotations\nimport numpy as np\nimport pandas as pd",
        "adaptation": "none"
    },
    {
        "repository": "chart-desk",
        "path": "chartdesk/tr.py",
        "git_blob_sha1": "8297c712d20404880d4d8949e96efbf48613909c",
        "vendor_path": "trading_system/tree_replay/_vendor/tr.py",
        "symbols": [
            "TR_EMAS",
            "emas",
            "ema_cloud"
        ],
        "allowed_imports": "from __future__ import annotations\nimport pandas as pd\nfrom . import indicators as I",
        "adaptation": "none"
    },
    {
        "repository": "chart-desk",
        "path": "chartdesk/tr.py",
        "git_blob_sha1": "8297c712d20404880d4d8949e96efbf48613909c",
        "vendor_path": "trading_system/tree_replay/_vendor/atr.py",
        "symbols": [
            "atr"
        ],
        "allowed_imports": "import pandas as pd",
        "adaptation": "none"
    }
]
EXPECTED_CONTRACT = {
    "schema_version": "admission-source-contracts-v1",
    "repositories": REPOSITORIES,
    "files": FILES,
    "scope": "Pure original admission calculations on supplied frames and explicit aware clocks; no outer admission, source execution, state replay or labels",
    "ready_for_replay": False,
    "ready_for_training": False,
}
INPUT_ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
                StopIteration, subprocess.SubprocessError)


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _name(node):
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    if isinstance(node, ast.Assign):
        return ",".join(n.id for target in node.targets for n in ast.walk(target)
                        if isinstance(n, ast.Name))
    return None


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys)


def _canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def _replace_exact(tree, old, new, count):
    """Replace only a declared AST expression and require the original count."""
    old_dump = _dump(ast.parse(old, mode="eval").body)
    replacement = ast.parse(new, mode="eval").body

    class Replace(ast.NodeTransformer):
        found = 0

        def visit(self, node):
            if _dump(node) == old_dump:
                self.found += 1
                return copy.deepcopy(replacement)
            return super().visit(node)

    visitor = Replace()
    result = visitor.visit(tree)
    if visitor.found != count:
        raise ValueError("SPECIALIZATION_PRECONDITION_MISMATCH")
    return result


def _required_time(function):
    expected = ast.parse("def f(now: datetime | None = None): pass").body[0].args
    if _dump(function.args) != _dump(expected):
        raise ValueError("SOURCE_CLOCK_SIGNATURE_MISMATCH")
    function.args = ast.parse("def f(now: datetime): pass").body[0].args
    return function


def _project(text, row):
    """Original ordered definitions with only explicit import/fetch/clock edits."""
    source = ast.parse(text)
    selected = [node for node in source.body if _name(node) in row["symbols"]]
    if [_name(node) for node in selected] != row["symbols"]:
        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
    mode = row["adaptation"]
    if mode == "matrix_frame_and_atr_import":
        atr = selected[row["symbols"].index("_atr")]
        _replace_exact(atr, "tr.atr(df, 14)", "tr_atr.atr(df, 14)", 1)
        function = selected[row["symbols"].index("read_tf")]
        signature = ast.parse("def read_tf(symbol: str, tf: str) -> TFView: pass").body[0]
        if (_dump(function.args) != _dump(signature.args)
                or _dump(function.returns) != _dump(signature.returns)
                or function.decorator_list or len(function.body) != 3):
            raise ValueError("SOURCE_READ_TF_SHAPE_MISMATCH")
        fetch = ast.parse(
            "df, corr = basis.fetch_corrected(symbol, tf, LOOKBACK[tf])\n"
            "note = corr.render() if corr.show else None"
        ).body
        if [_dump(n) for n in function.body[:2]] != [_dump(n) for n in fetch]:
            raise ValueError("SOURCE_FETCH_SPECIALIZATION_MISMATCH")
        returned = function.body[2]
        if (not isinstance(returned, ast.Return) or not isinstance(returned.value, ast.Call)
                or _dump(returned.value.func) != _dump(ast.Name(id="TFView", ctx=ast.Load()))):
            raise ValueError("SOURCE_TFVIEW_CONSTRUCTOR_MISSING")
        function.name = "read_frame"
        function.args = ast.parse("def f(df, tf, basis_note=None): pass").body[0].args
        # Preserve the entire original constructor, tool order and all fields.
        function.body = [_replace_exact(returned, "note", "basis_note", 1)]
    elif mode == "required_aware_floor_clock":
        for node in selected:
            if isinstance(node, ast.FunctionDef):
                _required_time(node)
                if node.name == "now_il":
                    original = ast.parse(
                        "if now is None:\n    return datetime.now(TZ)\n"
                        "return now.astimezone(TZ) if now.tzinfo else now.replace(tzinfo=TZ)"
                    ).body
                    if [_dump(n) for n in node.body] != [_dump(n) for n in original]:
                        raise ValueError("SOURCE_NOW_IL_BODY_MISMATCH")
                    node.body = ast.parse(
                        'if not isinstance(now, datetime):\n'
                        '    raise TypeError("now must be an aware datetime")\n'
                        'if now.tzinfo is None or now.utcoffset() is None:\n'
                        '    raise ValueError("now must be an aware datetime")\n'
                        'return now.astimezone(TZ)'
                    ).body
    elif mode == "required_aware_hunting_clock_shared_TZ":
        expected_tz = ast.parse('TZ = ZoneInfo("Asia/Jerusalem")').body[0]
        if _dump(selected[0]) != _dump(expected_tz):
            raise ValueError("SHARED_TIMEZONE_MISMATCH")
        selected = selected[1:]  # identical TZ already projected from marketclock
        for node in selected:
            if isinstance(node, ast.FunctionDef):
                _required_time(node)
                _replace_exact(node, "(now or datetime.now(TZ)).astimezone(TZ)",
                               "now_il(now)", 1)
    elif mode != "none":
        raise ValueError("UNKNOWN_SPECIALIZATION")
    return ast.parse(row["allowed_imports"]).body + selected


def _git(repo, *args):
    # Local rev-parse only: no source imports, hooks, filters, status refresh,
    # object fetches or external processes configured by the source repository.
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1",
               GIT_TERMINAL_PROMPT="0")
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-C", str(repo), "rev-parse", *args],
        env=env, text=True, encoding="utf-8", capture_output=True, timeout=10,
        check=True,
    )
    return result.stdout.strip()


def audit_admission_source(source_root) -> dict:
    """Audit an explicit parent of the pinned chart-desk/trading-floor checkouts."""
    blockers = []
    checked = []
    try:
        source_root = Path(source_root)
    except INPUT_ERRORS as exc:
        return _report([f"SOURCE_ROOT_INVALID:{type(exc).__name__}"], checked)
    try:
        contract = _read_json(ROOT / "configs/trees/admission-source-contracts.json")
        if _canonical(contract) != _canonical(EXPECTED_CONTRACT):
            blockers.append("CONTRACT_MISMATCH")
        baseline = _read_json(ROOT / "configs/trees/existing-alerts-baseline.json")
        for repo, commit in REPOSITORIES.items():
            pins = [row.get("commit") for row in baseline["repositories"]
                    if row.get("name") == repo]
            if pins != [commit]:
                blockers.append(f"BASELINE_COMMIT_MISMATCH:{repo}")
    except INPUT_ERRORS as exc:
        blockers.append(f"CONTRACT_UNREADABLE:{type(exc).__name__}")
    for repo, commit in REPOSITORIES.items():
        try:
            path = source_root / repo
            if Path(_git(path, "--show-toplevel")).resolve() != path.resolve():
                blockers.append(f"NOT_REPOSITORY_ROOT:{repo}")
            if _git(path, "HEAD") != commit:
                blockers.append(f"SOURCE_COMMIT_MISMATCH:{repo}")
        except INPUT_ERRORS as exc:
            blockers.append(f"SOURCE_IDENTITY_UNREADABLE:{repo}:{type(exc).__name__}")
    expected_modules = {}
    unavailable = set()
    for row in FILES:
        path = f'{row["repository"]}/{row["path"]}'
        vendor = row["vendor_path"]
        try:
            text = (source_root / path).read_text(encoding="utf-8")
            data = text.encode("utf-8")  # canonical Git LF after universal newline read
            digest = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            if digest != row["git_blob_sha1"]:
                blockers.append(f"SOURCE_BLOB_MISMATCH:{path}")
                unavailable.add(vendor)
                continue
            expected_modules.setdefault(vendor, []).extend(_project(text, row))
            checked.append({"source": path, "vendor": vendor, "symbols": list(row["symbols"])})
        except INPUT_ERRORS as exc:
            blockers.append(f"SOURCE_PROJECTION_UNREADABLE:{path}:{type(exc).__name__}")
            unavailable.add(vendor)
    for vendor in dict.fromkeys(row["vendor_path"] for row in FILES):
        try:
            actual = ast.parse((ROOT / vendor).read_text(encoding="utf-8"))
            # Existing accepted modules have a descriptive module docstring.
            # Strip at most that one string, not arbitrary top-level expressions.
            if ast.get_docstring(actual) is not None:
                actual.body = actual.body[1:]
            expected = ast.Module(body=expected_modules.get(vendor, []), type_ignores=[])
            if vendor not in unavailable and _dump(actual) != _dump(expected):
                blockers.append(f"VENDOR_AST_MISMATCH:{vendor}")
        except INPUT_ERRORS as exc:
            blockers.append(f"VENDOR_UNREADABLE:{vendor}:{type(exc).__name__}")
    return _report(blockers, checked)


def _report(blockers, checked):
    return {
        "status": "BLOCKED" if blockers else "VERIFIED",
        "source_subset_verified": not blockers,
        "blockers": blockers,
        "checked_projections": checked,
        "source_commits": dict(REPOSITORIES),
        "ready_for_replay": False,
        "ready_for_training": False,
    }
