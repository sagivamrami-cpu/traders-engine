"""Independent inert-source audit of the private tracker gate/record closure.

Only ASTs are transformed here, never compiled, imported or executed. The fixed
authority below is independent of the declarative manifest and prior auditors.
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
VENDOR = "trading_system/tree_replay/_vendor/"
TRACKER_SYMBOLS = ["MAX_STOP_BLOCK_H", "QUOTE_MAX_AGE_S", "_trade_identity",
    "record", "_born_in_zone", "_record_locked", "_entry_band", "has_open",
    "_higher_bias", "_live_prices", "_thesis_baseline", "_anchor_names", "_tail",
    "_recent_rejection", "_cooldown_release", "blocked_after_stop",
    "LEVEL_COOLDOWN_S", "blocked_same_level"]
TRADEPLAN_SYMBOLS = ["born_in_zone", "WEAK_GATE", "THESIS_RECOVER",
                     "thesis_now", "thesis_verdict"]
METHODS = ["record", "_born_in_zone", "_record_locked", "_entry_band", "has_open",
    "_higher_bias", "_live_prices", "_thesis_baseline", "_recent_rejection",
    "_cooldown_release", "blocked_after_stop", "blocked_same_level", "thesis_now"]
TRACKER_IMPORTS = """from __future__ import annotations
import json
import hashlib
import math
from io import BytesIO
import pandas as pd
from . import basis_symbols as basis
from .pricing import entry_zone"""
FILES = [
    {"path": "chartdesk/tracker.py", "git_blob_sha1": "b616b34022e436545d8c1daf85eced51614fd74e",
     "vendor_path": VENDOR + "tracker_admission.py", "symbols": TRACKER_SYMBOLS,
     "projection": "tracker_ports"},
    {"path": "chartdesk/tradeplan.py", "git_blob_sha1": "d09e9be39ce8dadf1674029e0c03751c70502135",
     "vendor_path": VENDOR + "tracker_admission.py", "symbols": TRADEPLAN_SYMBOLS,
     "projection": "tracker_thesis_and_build_band"},
    {"path": "chartdesk/symbols.py", "git_blob_sha1": "c2fd40c8a97d98aa3650d95c8fbe64a5ce43e8f7",
     "vendor_path": VENDOR + "tracker_symbols.py", "symbols": "whole_module",
     "projection": "whole_module"},
    {"path": "chartdesk/tradeplan.py", "git_blob_sha1": "d09e9be39ce8dadf1674029e0c03751c70502135",
     "vendor_path": VENDOR + "pricing.py",
     "symbols": ["MIN_RR", "SWING_MULT", "STYLE_MULT", "INTRADAY_MULT", "INTRADAY_TARGET_COUNT",
        "FAR_TP1_R", "INSERT_TP1_R", "_with_measured_rung", "ENTRY_ZONE", "entry_zone",
        "STOP_BANDS", "apply_stop_band", "Plan", "MIN_TARGET_SEP_ATR", "ladder_ready",
        "ordered_ladder", "distinct_targets", "_n_levels", "resolve_ladder"],
     "imports": "from __future__ import annotations\nfrom dataclasses import dataclass, field\nfrom . import basis_symbols as basis",
     "projection": "pricing_plan"},
    {"path": "chartdesk/basis.py", "git_blob_sha1": "f3396f3a9fefd71f0f71422001a5521af0a05cd2",
     "vendor_path": VENDOR + "basis_symbols.py", "symbols": ["_BARE_ALIASES", "canonical_symbol"],
     "imports": "from __future__ import annotations", "projection": "pure"},
    {"path": "chartdesk/quarters.py", "git_blob_sha1": "d540b7bba60e992ff711954716ad265337116fc1",
     "vendor_path": VENDOR + "quarters.py", "symbols": ["GRID", "_asset", "Level", "_kind", "nearest"],
     "imports": "from __future__ import annotations\nfrom dataclasses import dataclass", "projection": "pure"},
    {"path": "chartdesk/entry_quality.py", "git_blob_sha1": "0cd76eb8c607690610f4559e5946a60e8f7647ac",
     "vendor_path": VENDOR + "admission_quality.py",
     "symbols": ["MAX_REJECTION_AGE_S", "LABEL_NO_ANCHOR", "LABEL_NO_TRIGGER", "PREDICATE",
        "_ANCHOR_PREFIXES", "_PRICE_TAIL", "_NAME_SPLIT", "_COUNT_PREFIX", "anchor_names",
        "aligned_trigger", "still_defending", "opposing_label", "evaluate", "_rej"],
     "imports": "from __future__ import annotations\nimport re", "projection": "pure"},
    {"path": "chartdesk/zones.py", "git_blob_sha1": "92f7b99373b4f266a1d80e2d997b965f973d7698",
     "vendor_path": VENDOR + "admission_swing.py", "symbols": ["SWING_K", "_last_swing"],
     "imports": "from __future__ import annotations", "projection": "pure"},
]
# Each replacement is scoped to a named function and exact source AST. Counts
# are independently fixed, not inferred from the candidate runtime/manifest.
EXPRESSIONS = {
    "record": [("_higher_bias(sym)", "self._higher_bias(sym)"),
        ("_thesis_baseline(sym, plan.direction)", "self._thesis_baseline(sym, plan.direction)"),
        ("_born_in_zone(plan, sym)", "self._born_in_zone(plan, sym)"),
        ("_locked()", "self.source.locked()"),
        ("_record_locked(plan, variant, to_group, bias_at_send, thesis, born)",
         "self._record_locked(plan, variant, to_group, bias_at_send, thesis, born)")],
    "_born_in_zone": [("_live_prices()", "self._live_prices()"),
        ('_entry_band({"symbol": plan.symbol, "entry": plan.entry})',
         'self._entry_band({"symbol": plan.symbol, "entry": plan.entry})')],
    "_record_locked": [("_load()", "self.source.load()"),
        ("has_open(basis.canonical_symbol(plan.symbol), plan.direction, state=d)",
         "self.has_open(basis.canonical_symbol(plan.symbol), plan.direction, state=d)"),
        ("time.time()", "self.source.now_epoch()"), ("_save(d)", "self.source.save(d)")],
    "has_open": [("_load()", "self.source.load()")],
    "_higher_bias": [("matrix.read_symbol(symbol, tfs=tfs)", "self.source.read_symbol(symbol, tfs=tfs)")],
    "_live_prices": [("json.loads(QUOTES.read_text())", "self.source.quote_payload()"),
                     ("time.time()", "self.source.now_epoch()")],
    "_thesis_baseline": [("_tp.thesis_now(symbol)", "self.thesis_now(symbol)"),
                         ("_tp.thesis_verdict(now[1], direction)", "thesis_verdict(now[1], direction)")],
    "_recent_rejection": [("_tail(EVENTS)", "_tail_reader(self.source.event_log_reader)")],
    "_cooldown_release": [("time.time()", "self.source.now_epoch()"),
        ("_recent_rejection(symbol, direction, stopped_ts, self.source.now_epoch() if asof is None else float(asof), entry)",
         "self._recent_rejection(symbol, direction, stopped_ts, self.source.now_epoch() if asof is None else float(asof), entry)")],
    "blocked_after_stop": [("_load()", "self.source.load()"), ("time.time()", "self.source.now_epoch()"),
        ('matrix.read_symbol(symbol, tfs=("4h", "1h"))', 'self.source.read_symbol(symbol, tfs=("4h", "1h"))'),
        ('basis.fetch_corrected(symbol, "15m", 5)', 'self.source.fetch_corrected(symbol, "15m", 5)'),
        ("_cooldown_release(symbol, direction, plan, last, stopped_ts, hours)",
         "self._cooldown_release(symbol, direction, plan, last, stopped_ts, hours)")],
    "blocked_same_level": [("time.time()", "self.source.now_epoch()"), ("_load()", "self.source.load()")],
    "thesis_now": [('matrix.read_symbol(symbol, tfs=("4h", "1h", "30m", "15m", "5m"))',
                    'self.source.read_symbol(symbol, tfs=("4h", "1h", "30m", "15m", "5m"))')],
}
STATEMENTS = {
    "_born_in_zone": [("from .tradeplan import born_in_zone", None)],
    "_entry_band": [("from .tradeplan import entry_zone", "from .pricing import entry_zone")],
    "_higher_bias": [("from . import matrix", None)],
    "_thesis_baseline": [("from . import tradeplan as _tp", None)],
    "_anchor_names": [("from .entry_quality import anchor_names", "from .admission_quality import anchor_names")],
    "_recent_rejection": [("from .tradeplan import entry_zone", "from .pricing import entry_zone")],
    "_cooldown_release": [("from . import symbols as _sym", "from . import tracker_symbols as _sym")],
    "blocked_after_stop": [("from . import matrix, zones", "from . import admission_swing as zones")],
    "blocked_same_level": [("from .tradeplan import entry_zone", "from .pricing import entry_zone")],
}
EXPECTED_CONTRACT = {
    "schema_version": "tracker-admission-source-contracts-v1",
    "repositories": REPOSITORIES, "files": FILES,
    "methods": METHODS, "tracker_imports": TRACKER_IMPORTS,
    "expression_substitutions_once_per_function": EXPRESSIONS,
    "statement_substitutions_once_per_function": STATEMENTS,
    "tail_adaptation": "path:Path -> open_reader; path.open(rb) -> open_reader() inside original try; fixed small-fixture BytesIO wrapper",
    "scope": "Private original tracker admission/record dependency; no causal binding, lifecycle, simulation or labels",
    "ready_for_replay": False, "ready_for_training": False,
}
INPUT_ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
                subprocess.SubprocessError)


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _name(node):
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None


def _without_doc(tree):
    return tree.body[1:] if ast.get_docstring(tree) is not None else tree.body


def _replace_exact(tree, old, new, *, statement=False):
    original = ast.parse(old).body[0] if statement else ast.parse(old, mode="eval").body
    replacement = None if new is None else (ast.parse(new).body[0] if statement else ast.parse(new, mode="eval").body)
    class Replace(ast.NodeTransformer):
        count = 0
        def visit(self, node):
            if _dump(node) == _dump(original):
                self.count += 1
                return copy.deepcopy(replacement)
            return super().visit(node)
    visitor = Replace()
    result = visitor.visit(tree)
    if visitor.count != 1:
        raise ValueError(f"SUBSTITUTION_PRECONDITION:{old}:count={visitor.count}")
    return result


def _selected(text, symbols):
    selected = [n for n in ast.parse(text).body if _name(n) in symbols]
    if [_name(n) for n in selected] != symbols:
        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
    return selected


def _tracker_projection(tracker_text, tradeplan_text):
    tracker = _selected(tracker_text, TRACKER_SYMBOLS)
    tradeplan = _selected(tradeplan_text, TRADEPLAN_SYMBOLS)
    nodes = {_name(n): n for n in tracker + tradeplan}
    for name, edits in EXPRESSIONS.items():
        for old, new in edits:
            nodes[name] = _replace_exact(nodes[name], old, new)
    for name, edits in STATEMENTS.items():
        for old, new in edits:
            nodes[name] = _replace_exact(nodes[name], old, new, statement=True)
    tail = nodes["_tail"]
    signature = ast.parse("def _tail(path: Path, window: int = 400_000, cap: int = 8_000_000) -> bytes | None: pass").body[0]
    if _dump(tail.args) != _dump(signature.args) or _dump(tail.returns) != _dump(signature.returns) or tail.decorator_list:
        raise ValueError("TAIL_SIGNATURE_MISMATCH")
    _replace_exact(tail, 'path.open("rb")', "open_reader()")
    tail.name = "_tail_reader"
    tail.args.args[0] = ast.arg(arg="open_reader")
    wrapper = ast.parse(
        "def _tail_bytes(raw, window: int=400000, cap: int=8000000) -> bytes | None:\n"
        "    if raw is None:\n        return None\n"
        "    return _tail_reader(lambda: BytesIO(raw), window, cap)"
    ).body[0]
    cls = ast.parse("class TrackerAdmission:\n    def __init__(self, source):\n        self.source = source").body[0]
    for name in METHODS:
        node = nodes[name]
        if not isinstance(node, ast.FunctionDef) or node.decorator_list or any(a.arg == "self" for a in node.args.args):
            raise ValueError(f"METHOD_SHAPE_MISMATCH:{name}")
        node.args.args.insert(0, ast.arg(arg="self"))
        cls.body.append(node)
    return ast.parse(TRACKER_IMPORTS).body + [nodes[n] for n in
        ("MAX_STOP_BLOCK_H", "QUOTE_MAX_AGE_S", "LEVEL_COOLDOWN_S", "WEAK_GATE",
         "THESIS_RECOVER", "_trade_identity", "_anchor_names", "_tail")] + [wrapper] + [
         nodes["born_in_zone"], nodes["thesis_verdict"], cls]


def _dependency_projection(text, row):
    if row["projection"] == "whole_module":
        return _without_doc(ast.parse(text))
    nodes = _selected(text, row["symbols"])
    if row["projection"] == "pricing_plan":
        plan = next(n for n in nodes if _name(n) == "Plan")
        methods = ("risk", "rr", "rr_far", "tradeable")
        plan.body = [n for n in plan.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) or n.name in methods]
        kept = [n for n in plan.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if [n.name for n in kept] != list(methods) or any(
                not isinstance(n, ast.FunctionDef) or [_dump(d) for d in n.decorator_list] !=
                [_dump(ast.Name(id="property", ctx=ast.Load()))] for n in kept):
            raise ValueError("PLAN_PROPERTY_PROJECTION_MISMATCH")
    return ast.parse(row["imports"]).body + nodes


def _git(repo, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0")
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    result = subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(repo),
                             "rev-parse", *args], env=env, text=True, encoding="utf-8",
                            capture_output=True, timeout=10, check=True)
    return result.stdout.strip()


def _no_duplicates(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError(f"DUPLICATE_JSON_KEY:{k}")
        result[k] = v
    return result


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates)


def _report(blockers, checked):
    return {"status": "BLOCKED" if blockers else "VERIFIED",
        "source_subset_verified": not blockers, "blockers": blockers,
        "checked_projections": checked, "source_commits": dict(REPOSITORIES),
        "ready_for_replay": False, "ready_for_training": False}


def audit_tracker_admission_source(source_root) -> dict:
    """Verify explicit retained parent, complete projection and inherited bodies."""
    blockers, checked = [], []
    try:
        source_root = Path(source_root)
    except INPUT_ERRORS as exc:
        return _report([f"SOURCE_ROOT_INVALID:{type(exc).__name__}"], checked)
    try:
        manifest = _read_json(ROOT / "configs/trees/tracker-admission-source-contracts.json")
        if json.dumps(manifest, sort_keys=True, allow_nan=False) != json.dumps(EXPECTED_CONTRACT, sort_keys=True, allow_nan=False):
            blockers.append("CONTRACT_MISMATCH")
        baseline = _read_json(ROOT / "configs/trees/existing-alerts-baseline.json")
        for repo, commit in REPOSITORIES.items():
            if [r.get("commit") for r in baseline["repositories"] if r.get("name") == repo] != [commit]:
                blockers.append(f"BASELINE_COMMIT_MISMATCH:{repo}")
    except INPUT_ERRORS as exc:
        blockers.append(f"CONTRACT_UNREADABLE:{type(exc).__name__}:{exc}")
    for repo, commit in REPOSITORIES.items():
        try:
            path = source_root / repo
            if Path(_git(path, "--show-toplevel")).resolve() != path.resolve():
                blockers.append(f"NOT_REPOSITORY_ROOT:{repo}")
            if _git(path, "HEAD") != commit:
                blockers.append(f"SOURCE_COMMIT_MISMATCH:{repo}")
        except INPUT_ERRORS as exc:
            blockers.append(f"SOURCE_IDENTITY_UNREADABLE:{repo}:{type(exc).__name__}")
    sources = {}
    for row in FILES:
        path = row["path"]
        if path in sources:
            continue
        try:
            text = (source_root / "chart-desk" / path).read_text(encoding="utf-8")
            data = text.encode("utf-8")  # normalize checkout CRLF to Git LF
            digest = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            if digest != row["git_blob_sha1"]:
                blockers.append(f"SOURCE_BLOB_MISMATCH:chart-desk/{path}")
                continue
            sources[path] = text
        except INPUT_ERRORS as exc:
            blockers.append(f"SOURCE_UNREADABLE:chart-desk/{path}:{type(exc).__name__}")
    projections = {}
    try:
        projections[VENDOR + "tracker_admission.py"] = _tracker_projection(
            sources["chartdesk/tracker.py"], sources["chartdesk/tradeplan.py"])
    except INPUT_ERRORS as exc:
        blockers.append(f"SOURCE_PROJECTION_UNREADABLE:tracker_admission:{type(exc).__name__}:{exc}")
    for row in FILES[2:]:
        try:
            projections[row["vendor_path"]] = _dependency_projection(sources[row["path"]], row)
        except INPUT_ERRORS as exc:
            blockers.append(f"SOURCE_PROJECTION_UNREADABLE:{row['path']}:{type(exc).__name__}:{exc}")
    for vendor, expected in projections.items():
        try:
            actual = _without_doc(ast.parse((ROOT / vendor).read_text(encoding="utf-8")))
            if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
                blockers.append(f"VENDOR_AST_MISMATCH:{vendor}")
            else:
                checked.append(vendor)
        except INPUT_ERRORS as exc:
            blockers.append(f"VENDOR_UNREADABLE:{vendor}:{type(exc).__name__}")
    return _report(blockers, checked)
