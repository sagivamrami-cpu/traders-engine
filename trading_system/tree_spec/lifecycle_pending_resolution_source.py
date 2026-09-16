"""Read-only source proof for the tracker PENDING fill/cancel branch."""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
BLOB = "b616b34022e436545d8c1daf85eced51614fd74e"
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_pending_resolution.py"
_EXPECTED_FRAGMENT_NAMES = (
    "entry_band", "extremes", "touch", "if_not_touched", "if_open_slot",
    "revalidate", "if_not_revalidated", "open_state", "revalidation_verified",
    "fill_verification_reason", "fill_timestamps", "changed", "fill_caveat",
    "fill_message",
)
CHILD_AUDITS = {
    "lifecycle_outcome_shelf": (
        "trading_system.tree_spec.lifecycle_outcome_shelf_source",
        "audit_lifecycle_outcome_shelf_source",
    ),
    "lifecycle_transitions": (
        "trading_system.tree_spec.lifecycle_transitions_source",
        "audit_lifecycle_transitions_source",
    ),
    "tree_revalidation": (
        "trading_system.tree_spec.tree_revalidation_source",
        "audit_tree_revalidation_source",
    ),
    "lifecycle_primitives": (
        "trading_system.tree_spec.lifecycle_primitives_source",
        "audit_lifecycle_primitives_source",
    ),
}
_EXPECTED_CHILD_AUDITS = (
    ("lifecycle_outcome_shelf", *CHILD_AUDITS["lifecycle_outcome_shelf"]),
    ("lifecycle_transitions", *CHILD_AUDITS["lifecycle_transitions"]),
    ("tree_revalidation", *CHILD_AUDITS["tree_revalidation"]),
    ("lifecycle_primitives", *CHILD_AUDITS["lifecycle_primitives"]),
)
_REQUIRED_CHILD_PROJECTIONS = (
    ("lifecycle_outcome_shelf", ("lifecycle_outcome_shelf",)),
    ("lifecycle_transitions", ("lifecycle_transitions",)),
    ("tree_revalidation", ("matrix_reader", "tree_revalidation")),
    ("lifecycle_primitives", ("lifecycle_bars", "desk_success", "lifecycle_voice")),
)


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _git(path, arg):
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", arg],
        check=True, text=True, capture_output=True,
    ).stdout.strip()


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _function(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise ValueError(f"SOURCE_FUNCTION_MISSING:{name}")


def _is_pending_guard(node):
    return (
        isinstance(node, ast.If)
        and _dump(node.test) == _dump(ast.parse('t["state"] == "PENDING"', mode="eval").body)
        and not node.orelse
    )


def _fragment_names(fragment):
    names = []
    expected = ast.parse(
        '''
_zlo, _zhi = _entry_band(t)
_lo, _hi = _bar_extremes.get(t["symbol"], (px, px))
touched = (_hi >= _zlo) if short else (_lo <= _zhi)
if not touched:
    continue
ok, why, verified = revalidate_pending(t)
t["state"] = "OPEN"
t["revalidation_verified"] = bool(verified)
t["fill_verification_reason"] = why or "verified"
t["filled_ts"] = t["progress_ts"] = time.time()
changed = True
caveat = _fill_caveat(why, verified)
out.append((_fill_line(t, name, side) + caveat, t["to_group"]))
'''
    ).body
    for node in fragment:
        if _dump(node) == _dump(expected[0]):
            names.append("entry_band")
        elif _dump(node) == _dump(expected[1]):
            names.append("extremes")
        elif _dump(node) == _dump(expected[2]):
            names.append("touch")
        elif _dump(node) == _dump(expected[3]):
            names.append("if_not_touched")
        elif isinstance(node, ast.If) and _dump(node.test) == _dump(ast.parse('has_open(t["symbol"], t["direction"], state=d)', mode="eval").body):
            names.append("if_open_slot")
        elif _dump(node) == _dump(expected[4]):
            names.append("revalidate")
        elif isinstance(node, ast.If) and _dump(node.test) == _dump(ast.parse("not ok", mode="eval").body):
            names.append("if_not_revalidated")
        elif _dump(node) == _dump(expected[5]):
            names.append("open_state")
        elif _dump(node) == _dump(expected[6]):
            names.append("revalidation_verified")
        elif _dump(node) == _dump(expected[7]):
            names.append("fill_verification_reason")
        elif _dump(node) == _dump(expected[8]):
            names.append("fill_timestamps")
        elif _dump(node) == _dump(expected[9]):
            names.append("changed")
        elif _dump(node) == _dump(expected[10]):
            names.append("fill_caveat")
        elif _dump(node) == _dump(expected[11]):
            names.append("fill_message")
        else:
            names.append(type(node).__name__)
    return tuple(names)


def _extract_pending_fragment(text):
    """Extract only the PENDING body; this function never executes source."""
    fn = _function(ast.parse(text), "_check_live_locked")
    guards = [node for node in ast.walk(fn) if _is_pending_guard(node)]
    if len(guards) != 1:
        raise ValueError("SOURCE_PENDING_BRANCH_MISSING_OR_AMBIGUOUS")
    fragment = copy.deepcopy(guards[0].body)
    if _fragment_names(fragment) != _EXPECTED_FRAGMENT_NAMES:
        raise ValueError("SOURCE_PENDING_BRANCH_ORDER_MISMATCH")
    return fragment


def _call_name(node):
    return _dump(node.func) if isinstance(node, ast.Call) else None


def _require_source_contract(fragment):
    """Require every source decision that the offline projection adapts."""
    entry, extremes, touch, no_touch, conflict, revalidate, failed, *success = fragment
    expected = ast.parse(
        """
_zlo, _zhi = _entry_band(t)
_lo, _hi = _bar_extremes.get(t["symbol"], (px, px))
touched = (_hi >= _zlo) if short else (_lo <= _zhi)
if not touched:
    continue
ok, why, verified = revalidate_pending(t)
t["state"] = "OPEN"
t["revalidation_verified"] = bool(verified)
t["fill_verification_reason"] = why or "verified"
t["filled_ts"] = t["progress_ts"] = time.time()
changed = True
caveat = _fill_caveat(why, verified)
out.append((_fill_line(t, name, side) + caveat, t["to_group"]))
"""
    ).body
    for actual, wanted in zip(
        (entry, extremes, touch, no_touch, revalidate, *success), expected
    ):
        if _dump(actual) != _dump(wanted):
            raise ValueError("SOURCE_PENDING_BRANCH_CONTRACT_MISMATCH")

    has_open = ast.parse('has_open(t["symbol"], t["direction"], state=d)', mode="eval").body
    if not isinstance(conflict, ast.If) or _dump(conflict.test) != _dump(has_open):
        raise ValueError("SOURCE_PENDING_CONFLICT_GUARD_MISMATCH")
    if not isinstance(failed, ast.If) or _dump(failed.test) != _dump(ast.parse("not ok", mode="eval").body):
        raise ValueError("SOURCE_PENDING_REVALIDATION_GUARD_MISMATCH")
    for branch, result, terminal_index, outcome_index, length in (
        (conflict.body, "open_slot_conflict_at_fill", 1, 4, 6),
        (failed.body, "invalidated_at_fill", 0, 3, 5),
    ):
        if len(branch) != length or not isinstance(branch[-1], ast.Continue):
            raise ValueError("SOURCE_PENDING_CANCEL_PATH_MISMATCH")
        if _call_name(branch[terminal_index].value) != _dump(ast.parse('_mark_terminal(t, "CANCELLED")', mode="eval").body.func):
            raise ValueError("SOURCE_PENDING_CANCEL_TERMINAL_MISMATCH")
        if not isinstance(branch[outcome_index], ast.Expr) or result not in ast.unparse(branch[outcome_index]):
            raise ValueError("SOURCE_PENDING_OUTCOME_MISMATCH")


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


def _projection(text):
    """Make the allowed offline PENDING projection after verifying its source AST."""
    _require_source_contract(_extract_pending_fragment(text))
    return ast.parse(
        '''from __future__ import annotations
from ..tree_revalidation import TreeRevalidation
from .lifecycle_bars import _entry_band
from .lifecycle_outcome_shelf import LifecycleOutcomeShelf
from .lifecycle_transitions import LifecycleTransitions

class LifecyclePendingResolution:
    def __init__(self, source):
        self.source = source
        self.outcomes = LifecycleOutcomeShelf(source)
        self.transitions = LifecycleTransitions(source)
        self.revalidation = TreeRevalidation(source)

    def resolve(self, trade: dict, *, state: dict, price: float, bar_extremes: dict) -> tuple[list[tuple[str, bool]], bool]:
        short = trade["direction"] == "שורט"
        name = trade["symbol"].split(":")[-1]
        side = "SELL" if short else "BUY"
        zone_low, zone_high = _entry_band(trade)
        low, high = bar_extremes.get(trade["symbol"], (price, price))
        touched = high >= zone_low if short else low <= zone_high
        if not touched:
            return ([], False)
        if self.outcomes.has_open(trade["symbol"], trade["direction"], state=state):
            why = "עסקה אחרת באותו נכס ובאותו כיוון כבר פעילה"
            self.transitions._mark_terminal(trade, "CANCELLED")
            message = self.transitions._cancel_line(trade, why)
            self.outcomes._outcome({**trade, "result": "open_slot_conflict_at_fill"})
            return ([(message, trade["to_group"])], True)
        ok, why, verified = self.revalidation.revalidate_pending(trade)
        if not ok:
            self.transitions._mark_terminal(trade, "CANCELLED")
            message = self.transitions._cancel_line(trade, why)
            self.outcomes._outcome({**trade, "result": "invalidated_at_fill"})
            return ([(message, trade["to_group"])], True)
        trade["state"] = "OPEN"
        trade["revalidation_verified"] = bool(verified)
        trade["fill_verification_reason"] = why or "verified"
        trade["filled_ts"] = trade["progress_ts"] = self.source.now_epoch()
        caveat = self.transitions._fill_caveat(why, verified)
        message = self.transitions._fill_line(trade, name, side) + caveat
        return ([(message, trade["to_group"])], True)
'''
    )


def _child_audit(name, source_root):
    module_name, function_name = CHILD_AUDITS[name]
    module = importlib.import_module(module_name)
    return getattr(module, function_name)(source_root)


def _valid_child_report(expected, report):
    try:
        json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return (
        isinstance(report, dict)
        and report.get("status") == "VERIFIED"
        and report.get("source_subset_verified") is True
        and report.get("blockers") == []
        and report.get("checked_projections") == list(expected)
        and report.get("source_commits") == {"chart-desk": COMMIT}
        and report.get("ready_for_replay") is False
        and report.get("ready_for_training") is False
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


def audit_lifecycle_pending_resolution_source(source_root):
    """Fail-closed audit of the retained PENDING branch and composed children."""
    blockers, checked, dependencies = [], [], {}
    try:
        source_root = Path(source_root)
        baseline = _read_json(ROOT / "configs/trees/existing-alerts-baseline.json")
        commits = [row.get("commit") for row in baseline["repositories"] if row.get("name") == "chart-desk"]
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
        expected = _projection(text)
        actual = ast.parse((ROOT / Path(VENDOR)).read_text(encoding="utf-8"))
        if _dump(_without_docs(actual)) == _dump(_without_docs(expected)):
            checked.append("lifecycle_pending_resolution")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_pending_resolution")
    except Exception as exc:
        blockers.append(f"SOURCE_PROJECTION_UNREADABLE:lifecycle_pending_resolution:{type(exc).__name__}:{exc}")

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
