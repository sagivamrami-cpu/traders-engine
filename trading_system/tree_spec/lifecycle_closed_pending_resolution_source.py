"""Read-only proof for the pinned closed-bar PENDING lifecycle branch."""
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
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_closed_pending_resolution.py"
_EXPECTED_FRAGMENT_NAMES = ("expiry", "if_touched_entry")
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
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


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
    if len(fragment) != 2:
        return tuple(type(node).__name__ for node in fragment)
    expiry, touched = fragment
    names = []
    expiry_test = ast.parse(
        '(now - t["ts"]) > _expire_h(t) * 3600 and not touched_entry', mode="eval"
    ).body
    touched_test = ast.parse("touched_entry", mode="eval").body
    names.append("expiry" if isinstance(expiry, ast.If) and _dump(expiry.test) == _dump(expiry_test) else type(expiry).__name__)
    names.append("if_touched_entry" if isinstance(touched, ast.If) and _dump(touched.test) == _dump(touched_test) else type(touched).__name__)
    return tuple(names)


def _extract_closed_pending_fragment(text):
    """Extract only the closed-bar PENDING body; never execute source."""
    fn = _function(ast.parse(text), "check")
    expiry_test = ast.parse(
        '(now - t["ts"]) > _expire_h(t) * 3600 and not touched_entry', mode="eval"
    ).body
    guards = [
        node
        for node in ast.walk(fn)
        if _is_pending_guard(node)
        and any(
            isinstance(child, ast.If) and _dump(child.test) == _dump(expiry_test)
            for child in node.body
        )
    ]
    if len(guards) != 1:
        raise ValueError("SOURCE_CLOSED_PENDING_BRANCH_MISSING_OR_AMBIGUOUS")
    fragment = copy.deepcopy(guards[0].body)
    if _fragment_names(fragment) != _EXPECTED_FRAGMENT_NAMES:
        raise ValueError("SOURCE_CLOSED_PENDING_BRANCH_ORDER_MISMATCH")
    return fragment


def _call_name(node):
    return _dump(node.func) if isinstance(node, ast.Call) else None


def _require_source_contract(fragment):
    """Require the source branch shape that this offline projection adapts."""
    expiry, touched = fragment
    if not isinstance(expiry, ast.If) or len(expiry.body) != 12 or not isinstance(expiry.body[-1], ast.Continue):
        raise ValueError("SOURCE_CLOSED_PENDING_EXPIRY_SHAPE_MISMATCH")
    if _call_name(expiry.body[0].value) != _dump(ast.parse('_mark_terminal(t, "CANCELLED")', mode="eval").body.func):
        raise ValueError("SOURCE_CLOSED_PENDING_EXPIRY_TERMINAL_MISMATCH")
    if not isinstance(expiry.body[9], ast.Expr) or "expired" not in ast.unparse(expiry.body[9]):
        raise ValueError("SOURCE_CLOSED_PENDING_EXPIRY_OUTCOME_MISMATCH")
    if _call_name(expiry.body[10].value) != _dump(ast.parse("_shelve(t)", mode="eval").body.func):
        raise ValueError("SOURCE_CLOSED_PENDING_EXPIRY_SHELF_MISMATCH")

    if not isinstance(touched, ast.If) or len(touched.body) != 11:
        raise ValueError("SOURCE_CLOSED_PENDING_TOUCH_SHAPE_MISMATCH")
    conflict, revalidate, failed, *success = touched.body
    conflict_test = ast.parse('has_open(t["symbol"], t["direction"], state=d)', mode="eval").body
    if not isinstance(conflict, ast.If) or _dump(conflict.test) != _dump(conflict_test):
        raise ValueError("SOURCE_CLOSED_PENDING_CONFLICT_GUARD_MISMATCH")
    if len(conflict.body) != 6 or not isinstance(conflict.body[-1], ast.Continue):
        raise ValueError("SOURCE_CLOSED_PENDING_CONFLICT_SHAPE_MISMATCH")
    if not isinstance(revalidate, ast.Assign) or _dump(revalidate.value) != _dump(ast.parse("revalidate_pending(t, now=now)", mode="eval").body):
        raise ValueError("SOURCE_CLOSED_PENDING_REVALIDATION_CLOCK_MISMATCH")
    if not isinstance(failed, ast.If) or _dump(failed.test) != _dump(ast.parse("not ok", mode="eval").body):
        raise ValueError("SOURCE_CLOSED_PENDING_REVALIDATION_GUARD_MISMATCH")
    if len(failed.body) != 5 or not isinstance(failed.body[-1], ast.Continue):
        raise ValueError("SOURCE_CLOSED_PENDING_REVALIDATION_SHAPE_MISMATCH")
    expected = ast.parse(
        '''
t["state"] = "OPEN"
t["revalidation_verified"] = bool(verified)
t["fill_verification_reason"] = why or "verified"
t["filled_ts"] = t["progress_ts"] = time.time()
changed = True
note = _fill_caveat(why, verified)
if touched_stop:
    _mark_terminal(t, "STOPPED")
    out.append(("placeholder", t["to_group"]))
    _outcome({**t, "result": "stopped_ambiguous"})
    continue
out.append((_fill_line(t, name, side) + note, t["to_group"]))
'''
    ).body
    for actual, wanted in zip(success[:6], expected[:6]):
        if _dump(actual) != _dump(wanted):
            raise ValueError("SOURCE_CLOSED_PENDING_SUCCESS_PREFIX_MISMATCH")
    ambiguity, fill = success[6:]
    if not isinstance(ambiguity, ast.If) or _dump(ambiguity.test) != _dump(expected[6].test):
        raise ValueError("SOURCE_CLOSED_PENDING_STOP_AMBIGUITY_GUARD_MISMATCH")
    if len(ambiguity.body) != 4 or not isinstance(ambiguity.body[-1], ast.Continue):
        raise ValueError("SOURCE_CLOSED_PENDING_STOP_AMBIGUITY_SHAPE_MISMATCH")
    if not isinstance(ambiguity.body[2], ast.Expr) or "stopped_ambiguous" not in ast.unparse(ambiguity.body[2]):
        raise ValueError("SOURCE_CLOSED_PENDING_STOP_AMBIGUITY_OUTCOME_MISMATCH")
    if not isinstance(fill, ast.Expr) or "_fill_line(t, name, side) + note" not in ast.unparse(fill):
        raise ValueError("SOURCE_CLOSED_PENDING_FILL_MESSAGE_MISMATCH")


def _without_docs(tree):
    tree = copy.deepcopy(tree)
    for node in ast.walk(tree):
        if isinstance(getattr(node, "body", None), list) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                node.body = node.body[1:]
    class _PresentationText(ast.NodeTransformer):
        """Ignore only non-ASCII human presentation text, never control facts."""

        def visit_Constant(self, node):
            if isinstance(node.value, str) and not node.value.isascii():
                return ast.copy_location(ast.Constant(value="<presentation-text>"), node)
            return node

    return _PresentationText().visit(tree)


def _projection(text):
    """Build the exact offline closed-PENDING projection after source validation."""
    _require_source_contract(_extract_closed_pending_fragment(text))
    return ast.parse(
        '''from __future__ import annotations
from ..tree_revalidation import TreeRevalidation
from . import lifecycle_voice as voice
from .lifecycle_bars import _entry_band
from .lifecycle_outcome_shelf import LifecycleOutcomeShelf
from .lifecycle_transitions import LifecycleTransitions

class LifecycleClosedPendingResolution:
    def __init__(self, source):
        self.source = source
        self.outcomes = LifecycleOutcomeShelf(source)
        self.transitions = LifecycleTransitions(source)
        self.revalidation = TreeRevalidation(source)

    def resolve(self, trade: dict, *, state: dict, since, high: float, low: float, now: float) -> tuple[list[tuple[str, bool]], bool]:
        if trade.get("state") != "PENDING":
            return ([], False)
        short = trade["direction"] == "׳©׳•׳¨׳˜"
        name = trade["symbol"].split(":")[-1]
        side = "SELL" if short else "BUY"
        zone_low, zone_high = _entry_band(trade)
        touched_entry = high >= zone_low if short else low <= zone_high
        touched_stop = high >= float(trade["stop"]) if short else low <= float(trade["stop"])
        if (float(now) - float(trade["ts"])) > self.outcomes._expire_h(trade) * 3600 and not touched_entry:
            self.transitions._mark_terminal(trade, "CANCELLED")
            risk = abs(float(trade["entry"]) - float(trade["stop"])) or 1e-9
            start = float(since["open"].iloc[0])
            ran = (start - float(low)) if short else (float(high) - start)
            missed_r = ran / risk
            extra = ""
            if missed_r >= 1.0:
                extra = (f"\\n׳”׳›׳™׳•׳•׳ ׳”׳™׳” ׳ ׳›׳•׳: ׳”׳׳—׳™׳¨ ׳¨׳¥ {voice.dist(trade['symbol'], ran)} "
                         f"({missed_r:.1f}R) ׳׳›׳™׳•׳•׳ ׳”׳¢׳¡׳§׳” ׳‘׳׳™ ׳׳’׳¢׳× ׳‘׳›׳ ׳™׳¡׳”.")
            message = (voice.head("ג–ן¸", trade["symbol"], trade["direction"], trade["entry"], "׳₪׳’׳”")
                       + f"\\n׳”׳›׳ ׳™׳¡׳” ׳׳ ׳׳•׳׳©׳” ׳×׳•׳ {self.outcomes._expire_h(trade):.0f} ׳©׳¢׳•׳×."
                       + extra)
            self.outcomes._outcome({**trade, "result": "expired", "missed_r": round(missed_r, 2), "missed_points": round(ran, 2)})
            self.outcomes._shelve(trade)
            return ([(message, trade["to_group"])], True)
        if not touched_entry:
            return ([], False)
        if self.outcomes.has_open(trade["symbol"], trade["direction"], state=state):
            why = "׳¢׳¡׳§׳” ׳׳—׳¨׳× ׳‘׳׳•׳×׳• ׳ ׳›׳¡ ׳•׳‘׳׳•׳×׳• ׳›׳™׳•׳•׳ ׳›׳‘׳¨ ׳₪׳¢׳™׳׳”"
            self.transitions._mark_terminal(trade, "CANCELLED")
            message = self.transitions._cancel_line(trade, why)
            self.outcomes._outcome({**trade, "result": "open_slot_conflict_at_fill"})
            return ([(message, trade["to_group"])], True)
        ok, why, verified = self.revalidation.revalidate_pending(trade, now=now)
        if not ok:
            self.transitions._mark_terminal(trade, "CANCELLED")
            message = self.transitions._cancel_line(trade, why)
            self.outcomes._outcome({**trade, "result": "invalidated_at_fill"})
            return ([(message, trade["to_group"])], True)
        trade["state"] = "OPEN"
        trade["revalidation_verified"] = bool(verified)
        trade["fill_verification_reason"] = why or "verified"
        trade["filled_ts"] = trade["progress_ts"] = self.source.now_epoch()
        note = self.transitions._fill_caveat(why, verified)
        if touched_stop:
            self.transitions._mark_terminal(trade, "STOPPED")
            message = (voice.head("נ›‘", trade["symbol"], trade["direction"], trade["entry"], f"׳¡׳˜׳•׳₪ @ {float(trade['stop']):,.2f}")
                       + "\\n׳”׳›׳ ׳™׳¡׳” ׳•׳”׳¡׳˜׳•׳₪ ׳ ׳’׳¢׳• ׳‘׳׳•׳×׳• ׳—׳׳•׳ ג€” ׳‘׳׳§׳¨׳” ׳›׳–׳” ׳׳ ׳—׳ ׳• ׳¡׳•׳₪׳¨׳™׳ ׳¡׳˜׳•׳₪ (׳”׳©׳׳¨׳ ׳™).")
            self.outcomes._outcome({**trade, "result": "stopped_ambiguous"})
            return ([(message, trade["to_group"])], True)
        message = self.transitions._fill_line(trade, name, side) + note
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


def audit_lifecycle_closed_pending_resolution_source(source_root):
    """Fail-closed audit of the retained closed-bar PENDING projection."""
    blockers, checked, dependencies = [], [], {}
    try:
        source_root = Path(source_root)
        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
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
        tracker = repo / "chartdesk/tracker.py"
        text = tracker.read_text(encoding="utf-8")
        raw = text.encode("utf-8")
        digest = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        if digest != BLOB:
            blockers.append("SOURCE_BLOB_MISMATCH:tracker.py")
        expected = _projection(text)
        actual = ast.parse((ROOT / Path(VENDOR)).read_text(encoding="utf-8"))
        if _dump(_without_docs(actual)) == _dump(_without_docs(expected)):
            checked.append("lifecycle_closed_pending_resolution")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_closed_pending_resolution")
    except Exception as exc:
        blockers.append(f"SOURCE_PROJECTION_UNREADABLE:lifecycle_closed_pending_resolution:{type(exc).__name__}:{exc}")

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
