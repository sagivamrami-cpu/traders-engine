"""Read-only proof for the pinned OPEN zone-return helper and caller boundary."""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import textwrap


ROOT = Path(__file__).resolve().parents[2]
COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
BLOB = "b616b34022e436545d8c1daf85eced51614fd74e"
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_open_zone_return.py"
SOURCE_HELPER_START_LINE = 1046
SOURCE_HELPER_END_LINE = 1106
SOURCE_LIVE_CALL_START_LINE = 2751
SOURCE_LIVE_CALL_END_LINE = 2759
CHILD_AUDITS = {
    "lifecycle_transitions": (
        "trading_system.tree_spec.lifecycle_transitions_source",
        "audit_lifecycle_transitions_source",
    ),
    "lifecycle_primitives": (
        "trading_system.tree_spec.lifecycle_primitives_source",
        "audit_lifecycle_primitives_source",
    ),
    "revalidation": (
        "trading_system.tree_spec.revalidation_source",
        "audit_revalidation_source",
    ),
}
_EXPECTED_CHILD_AUDITS = tuple((name, *value) for name, value in CHILD_AUDITS.items())
_REQUIRED_CHILD_PROJECTIONS = (
    ("lifecycle_transitions", ("lifecycle_transitions",)),
    ("lifecycle_primitives", ("lifecycle_bars", "desk_success", "lifecycle_voice")),
    ("revalidation", ("revalidation",)),
)
_EXPECTED_HELPER_NAMES = ("excursion", "entry_recheck", "zone_return_message")
_EXPECTED_LIVE_CALL_NAMES = (
    "zone_return_call", "zone_return_guard", "message_append", "changed",
)


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _without_docs(tree):
    tree = copy.deepcopy(tree)
    for node in ast.walk(tree):
        if isinstance(getattr(node, "body", None), list) and node.body:
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                node.body = node.body[1:]
    return tree


def _git(path, arg):
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", arg],
        check=True, text=True, capture_output=True,
    ).stdout.strip()


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _expected_zone_return_helper():
    return ast.parse(
        '''
def _excursion(t: dict) -> str:
    step = max(int(t.get("progress_step") or 0), int(desk_success.reached(t)))
    return f"{step}/{len(t.get('hit') or [])}"

def _entry_recheck(t: dict) -> str:
    try:
        ok, why, verified = still_valid(t)
    except Exception:
        ok, why, verified = True, "", False
    why = _no_score(why)
    if not ok and not verified:
        return _ZONE_UNVERIFIED
    if ok:
        return (voice.check("\\u05ea\\u05e0\\u05d0\\u05d9 \\u05d4\\u05db\\u05e0\\u05d9\\u05e1\\u05d4 \\u05e2\\u05d3\\u05d9\\u05d9\\u05df \\u05de\\u05ea\\u05e7\\u05d9\\u05d9\\u05de\\u05d9\\u05dd", True)
                + (f"\\n{why}" if why else "")
                + ("" if verified else f"\\n{_ZONE_UNVERIFIED}"))
    return (voice.check("\\u05ea\\u05e0\\u05d0\\u05d9 \\u05d4\\u05db\\u05e0\\u05d9\\u05e1\\u05d4 \\u05dc\\u05d0 \\u05de\\u05ea\\u05e7\\u05d9\\u05d9\\u05de\\u05d9\\u05dd \\u05db\\u05e2\\u05ea", False)
            + (f"\\n{why}" if why else ""))

def _zone_return_message(t: dict, px: float, short: bool) -> str | None:
    gone = _excursion(t)
    if gone == "0/0":
        return None
    said = t.get("zone_return_at")
    if said is not None:
        try:
            said_targets = int(str(said).split("/")[1])
        except (IndexError, ValueError):
            said_targets = 0
        if len(t.get("hit") or []) <= said_targets:
            return None
    zlo, zhi = _entry_band(t)
    if not ((px >= zlo) if short else (px <= zhi)):
        return None
    sym, dr, entry = t["symbol"], t["direction"], float(t["entry"])
    stop = float(t["stop"])
    lines = [voice.head("\\U0001f501", sym, dr, entry, "\\u05d7\\u05d6\\u05e8\\u05d4 \\u05dc\\u05d0\\u05d6\\u05d5\\u05e8 \\u05d4\\u05db\\u05e0\\u05d9\\u05e1\\u05d4"),
             "", f"\\u05de\\u05d7\\u05d9\\u05e8 \\u05d1\\u05e2\\u05d3\\u05db\\u05d5\\u05df: {px:,.2f}\\n\\u05d0\\u05d6\\u05d5\\u05e8: {zlo:,.2f}–{zhi:,.2f}",
             f"\\u05e1\\u05d8\\u05d5\\u05e4 \\u05de\\u05e7\\u05d5\\u05e8\\u05d9: {stop:,.2f} · \\u05de\\u05e8\\u05d7\\u05e7 {voice.dist(sym, px - stop)}", ""]
    road = _journey(t)
    if road:
        lines.append(road)
    lines.append(_entry_recheck(t))
    lines.append("\\n\\u05d4\\u05e1\\u05d8\\u05d5\\u05e4 \\u05d5\\u05d4\\u05d9\\u05e2\\u05d3\\u05d9\\u05dd \\u05dc\\u05dc\\u05d0 \\u05e9\\u05d9\\u05e0\\u05d5\\u05d9. \\u05d6\\u05d4 \\u05d0\\u05d9\\u05e0\\u05d5 \\u05d0\\u05d5\\u05ea \\u05dc\\u05db\\u05e0\\u05d9\\u05e1\\u05d4 \\u05e0\\u05d5\\u05e1\\u05e4\\u05ea.")
    t["zone_return_at"] = gone
    return "\\n".join(lines)
'''
    ).body


def _parse_pinned_zone_return_helper(text):
    lines = text.splitlines(keepends=True)
    if len(lines) < SOURCE_HELPER_END_LINE:
        raise ValueError("SOURCE_OPEN_ZONE_RETURN_HELPER_SLICE_MISSING")
    return ast.parse("".join(lines[SOURCE_HELPER_START_LINE - 1:SOURCE_HELPER_END_LINE])).body


def _helper_names(branch):
    expected = _expected_zone_return_helper()
    if len(branch) != len(expected) or any(
        _dump(actual) != _dump(wanted) for actual, wanted in zip(_without_docs(ast.Module(body=branch, type_ignores=[])).body, expected)
    ):
        raise ValueError("SOURCE_OPEN_ZONE_RETURN_HELPER_MISMATCH")
    return _EXPECTED_HELPER_NAMES


def _extract_zone_return_helper(text):
    branch = _parse_pinned_zone_return_helper(text)
    _helper_names(branch)
    return copy.deepcopy(branch)


def _expected_live_call_boundary():
    return ast.parse(
        '''
if True:
    pass
else:
    back = _zone_return_message(t, px, short)
    if back:
        out.append((back, t["to_group"]))
        changed = True
'''
    ).body[0].orelse


def _parse_pinned_live_call_boundary(text):
    lines = text.splitlines(keepends=True)
    if len(lines) < SOURCE_LIVE_CALL_END_LINE:
        raise ValueError("SOURCE_OPEN_ZONE_RETURN_LIVE_CALL_SLICE_MISSING")
    body = textwrap.dedent("".join(lines[SOURCE_LIVE_CALL_START_LINE - 1:SOURCE_LIVE_CALL_END_LINE]))
    tree = ast.parse("if True:\n    pass\n" + body)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.If):
        raise ValueError("SOURCE_OPEN_ZONE_RETURN_LIVE_CALL_SLICE_PARSE_MISMATCH")
    return tree.body[0].orelse


def _live_call_names(branch):
    expected = _expected_live_call_boundary()
    if len(branch) != len(expected) or any(
        _dump(actual) != _dump(wanted) for actual, wanted in zip(branch, expected)
    ):
        raise ValueError("SOURCE_OPEN_ZONE_RETURN_LIVE_CALL_MISMATCH")
    return _EXPECTED_LIVE_CALL_NAMES


def _extract_live_call_boundary(text):
    branch = _parse_pinned_live_call_boundary(text)
    _live_call_names(branch)
    return copy.deepcopy(branch)


def _runtime_projection():
    return ast.parse(
        '''
from __future__ import annotations
from . import lifecycle_voice as voice
from .lifecycle_bars import _entry_band
from .lifecycle_transitions import LifecycleTransitions
from .revalidation import Revalidation

_ZONE_UNVERIFIED = "\\u05ea\\u05e0\\u05d0\\u05d9 \\u05d4\\u05db\\u05e0\\u05d9\\u05e1\\u05d4 \\u05dc\\u05d0 \\u05d0\\u05d5\\u05de\\u05ea\\u05d5 \\u05de\\u05d7\\u05d3\\u05e9 — \\u05d0\\u05d9\\u05df \\u05e0\\u05ea\\u05d5\\u05e0\\u05d9\\u05dd \\u05d8\\u05e8\\u05d9\\u05d9\\u05dd."

class LifecycleOpenZoneReturn:
    def __init__(self, source):
        self.source = source
        self.transitions = LifecycleTransitions(source)
        self.revalidation = Revalidation(source)

    def _excursion(self, trade: dict) -> str:
        step = max(int(trade.get("progress_step") or 0), int(self.transitions.desk_success.reached(trade)))
        return f"{step}/{len(trade.get('hit') or [])}"

    def _entry_recheck(self, trade: dict) -> str:
        try:
            ok, why, verified = self.revalidation.still_valid(trade)
        except Exception:
            ok, why, verified = True, "", False
        why = self.transitions._no_score(why)
        if not ok and not verified:
            return _ZONE_UNVERIFIED
        if ok:
            return (voice.check("\\u05ea\\u05e0\\u05d0\\u05d9 \\u05d4\\u05db\\u05e0\\u05d9\\u05e1\\u05d4 \\u05e2\\u05d3\\u05d9\\u05d9\\u05df \\u05de\\u05ea\\u05e7\\u05d9\\u05d9\\u05de\\u05d9\\u05dd", True)
                    + (f"\\n{why}" if why else "")
                    + ("" if verified else f"\\n{_ZONE_UNVERIFIED}"))
        return (voice.check("\\u05ea\\u05e0\\u05d0\\u05d9 \\u05d4\\u05db\\u05e0\\u05d9\\u05e1\\u05d4 \\u05dc\\u05d0 \\u05de\\u05ea\\u05e7\\u05d9\\u05d9\\u05de\\u05d9\\u05dd \\u05db\\u05e2\\u05ea", False)
                + (f"\\n{why}" if why else ""))

    def _zone_return_message(self, trade: dict, spot: float, short: bool) -> str | None:
        gone = self._excursion(trade)
        if gone == "0/0":
            return None
        said = trade.get("zone_return_at")
        if said is not None:
            try:
                said_targets = int(str(said).split("/")[1])
            except (IndexError, ValueError):
                said_targets = 0
            if len(trade.get("hit") or []) <= said_targets:
                return None
        zone_low, zone_high = _entry_band(trade)
        if not (spot >= zone_low if short else spot <= zone_high):
            return None
        symbol, direction, entry = trade["symbol"], trade["direction"], float(trade["entry"])
        stop = float(trade["stop"])
        lines = [voice.head("\\U0001f501", symbol, direction, entry, "\\u05d7\\u05d6\\u05e8\\u05d4 \\u05dc\\u05d0\\u05d6\\u05d5\\u05e8 \\u05d4\\u05db\\u05e0\\u05d9\\u05e1\\u05d4"), "", f"\\u05de\\u05d7\\u05d9\\u05e8 \\u05d1\\u05e2\\u05d3\\u05db\\u05d5\\u05df: {spot:,.2f}\\n\\u05d0\\u05d6\\u05d5\\u05e8: {zone_low:,.2f}–{zone_high:,.2f}", f"\\u05e1\\u05d8\\u05d5\\u05e4 \\u05de\\u05e7\\u05d5\\u05e8\\u05d9: {stop:,.2f} · \\u05de\\u05e8\\u05d7\\u05e7 {voice.dist(symbol, spot - stop)}", ""]
        journey = self.transitions._journey(trade)
        if journey:
            lines.append(journey)
        lines.append(self._entry_recheck(trade))
        lines.append("\\n\\u05d4\\u05e1\\u05d8\\u05d5\\u05e4 \\u05d5\\u05d4\\u05d9\\u05e2\\u05d3\\u05d9\\u05dd \\u05dc\\u05dc\\u05d0 \\u05e9\\u05d9\\u05e0\\u05d5\\u05d9. \\u05d6\\u05d4 \\u05d0\\u05d9\\u05e0\\u05d5 \\u05d0\\u05d5\\u05ea \\u05dc\\u05db\\u05e0\\u05d9\\u05e1\\u05d4 \\u05e0\\u05d5\\u05e1\\u05e4\\u05ea.")
        trade["zone_return_at"] = gone
        return "\\n".join(lines)

    def resolve(self, trade: dict, *, spot: float) -> tuple[list[tuple[str, bool]], bool]:
        short = trade["direction"] == "\\u05e9\\u05d5\\u05e8\\u05d8"
        message = self._zone_return_message(trade, float(spot), short)
        if message is None:
            return ([], False)
        return ([(message, trade["to_group"])], True)
'''
    )


def _child_audit(name, source_root):
    module_name, function_name = CHILD_AUDITS[name]
    module = importlib.import_module(module_name)
    return getattr(module, function_name)(source_root)


def _valid_child_report(expected, child):
    if not isinstance(child, dict):
        return False
    try:
        json.dumps(child, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return (
        child.get("status") == "VERIFIED"
        and child.get("source_subset_verified") is True
        and child.get("blockers") == []
        and child.get("checked_projections") == list(expected)
        and isinstance(child.get("dependencies"), dict)
        and child.get("source_commits") == {"chart-desk": COMMIT}
        and child.get("ready_for_replay") is False
        and child.get("ready_for_training") is False
    )


def _report(blockers, checked, dependencies):
    return {
        "status": "BLOCKED" if blockers else "VERIFIED",
        "source_subset_verified": not blockers,
        "blockers": blockers,
        "checked_projections": checked,
        "dependencies": dependencies,
        "source_commits": {"chart-desk": COMMIT},
        "ready_for_replay": False,
        "ready_for_training": False,
    }


def audit_lifecycle_open_zone_return_source(source_root):
    """Fail closed after parsing only the retained source and runtime text."""
    blockers, checked, dependencies = [], [], {}
    try:
        source_root = Path(source_root)
        baseline = _read_json(ROOT / "configs/trees/existing-alerts-baseline.json")
        commits = [
            row.get("commit") for row in baseline["repositories"]
            if row.get("name") == "chart-desk"
        ]
        if commits != [COMMIT]:
            blockers.append("BASELINE_COMMIT_MISMATCH")
        repo = source_root / "chart-desk"
        if Path(_git(repo, "--show-toplevel")).resolve() != repo.resolve():
            blockers.append("NOT_REPOSITORY_ROOT")
        if _git(repo, "HEAD") != COMMIT:
            blockers.append("SOURCE_COMMIT_MISMATCH")
    except Exception as exc:
        blockers.append(f"SOURCE_IDENTITY_UNREADABLE:{type(exc).__name__}")
        return _report(blockers, checked, dependencies)

    try:
        text = (repo / "chartdesk/tracker.py").read_text(encoding="utf-8")
        raw = text.encode("utf-8")
        digest = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        if digest != BLOB:
            blockers.append("SOURCE_BLOB_MISMATCH:tracker.py")
        _extract_zone_return_helper(text)
        checked.append("lifecycle_open_zone_return_helper")
        _extract_live_call_boundary(text)
        checked.append("lifecycle_open_zone_return_live_call")
        expected = _runtime_projection()
        actual = ast.parse((ROOT / Path(VENDOR)).read_text(encoding="utf-8"))
        if _dump(_without_docs(actual)) == _dump(_without_docs(expected)):
            checked.append("lifecycle_open_zone_return")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_open_zone_return")
    except Exception as exc:
        blockers.append(
            "SOURCE_PROJECTION_UNREADABLE:"
            f"lifecycle_open_zone_return:{type(exc).__name__}:{exc}"
        )

    expected_names = {row[0] for row in _EXPECTED_CHILD_AUDITS}
    if set(CHILD_AUDITS) != expected_names:
        blockers.append("CHILD_AUDIT_IDENTITY_MISMATCH:SET")
    required = dict(_REQUIRED_CHILD_PROJECTIONS)
    for name, module_name, function_name in _EXPECTED_CHILD_AUDITS:
        if CHILD_AUDITS.get(name) != (module_name, function_name):
            blockers.append(f"CHILD_AUDIT_IDENTITY_MISMATCH:{name}")
            continue
        try:
            child = _child_audit(name, source_root)
            if not _valid_child_report(required[name], child):
                raise TypeError("CHILD_REPORT_SHAPE")
            dependencies[name] = child
        except Exception as exc:
            blockers.append(f"DEPENDENCY:{name}:UNREADABLE:{type(exc).__name__}")
    return _report(blockers, checked, dependencies)
