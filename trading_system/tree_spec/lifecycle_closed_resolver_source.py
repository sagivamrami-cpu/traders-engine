"""Read-only proof for the pinned closed-bar lifecycle resolver composition."""
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
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_closed_resolver.py"
CHILD_AUDITS = {
    "lifecycle_closed_pending_resolution": (
        "trading_system.tree_spec.lifecycle_closed_pending_resolution_source",
        "audit_lifecycle_closed_pending_resolution_source",
    ),
    "lifecycle_primitives": (
        "trading_system.tree_spec.lifecycle_primitives_source",
        "audit_lifecycle_primitives_source",
    ),
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
    "lifecycle_open_protection": (
        "trading_system.tree_spec.lifecycle_open_protection_source",
        "audit_lifecycle_open_protection_source",
    ),
    "lifecycle_open_ordinary_resolution": (
        "trading_system.tree_spec.lifecycle_open_ordinary_resolution_source",
        "audit_lifecycle_open_ordinary_resolution_source",
    ),
}
_EXPECTED_CHILD_AUDITS = tuple((name, *value) for name, value in CHILD_AUDITS.items())
_REQUIRED_CHILD_PROJECTIONS = (
    ("lifecycle_closed_pending_resolution", ("lifecycle_closed_pending_resolution",)),
    ("lifecycle_primitives", ("lifecycle_bars", "desk_success", "lifecycle_voice")),
    ("lifecycle_outcome_shelf", ("lifecycle_outcome_shelf",)),
    ("lifecycle_transitions", ("lifecycle_transitions",)),
    ("tree_revalidation", ("matrix_reader", "tree_revalidation")),
    ("lifecycle_open_protection", ("lifecycle_open_protection",)),
    ("lifecycle_open_ordinary_resolution", ("lifecycle_open_ordinary_resolution",)),
)
_KERNEL_NAMES = (
    "corrected_fetch", "correction_gates", "strict_since_slice", "prefill_extrema",
    "postfill_extrema", "pending_branch", "open_branch",
)


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _git(path, arg):
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", arg],
        check=True, text=True, capture_output=True,
    ).stdout.strip()


def _without_docs(tree):
    tree = copy.deepcopy(tree)
    for node in ast.walk(tree):
        if isinstance(getattr(node, "body", None), list) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                node.body = node.body[1:]
    return tree


def _function(tree, name):
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    return matches[0]


def _one_statement(code):
    return ast.parse(code).body[0]


def _kernel_names(loop):
    """Require the source's physical closed loop, without executing retained text."""
    expected = [
        _one_statement('if t["state"] in ("STOPPED", "DONE", "CANCELLED"):\n    continue'),
        _one_statement('sym = t["symbol"]'),
        _one_statement('idx = pd.to_datetime(df.index, utc=True)'),
        _one_statement('since = df[[ts.timestamp() > t["ts"] for ts in idx]]'),
        _one_statement('if len(since) < 1:\n    continue'),
        _one_statement('hi = float(since["high"].max())'),
        _one_statement('lo = float(since["low"].min())'),
        _one_statement('_ext = _open_extremes(since, t)'),
        _one_statement('hi_f, lo_f = _ext if _ext is not None else (_e, _e)'),
    ]
    indices = (0, 1, 3, 4, 5, 6, 7, 10, 11)
    if len(loop.body) != 19 or any(_dump(loop.body[index]) != _dump(wanted) for index, wanted in zip(indices, expected)):
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    if not isinstance(loop.body[2], ast.Try) or len(loop.body[2].body) != 3:
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    fetch, unverified, stale = loop.body[2].body
    if _dump(fetch) != _dump(_one_statement('df, corr = basis.fetch_corrected(sym, "15m", 3)')):
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    if not isinstance(unverified, ast.If) or not isinstance(stale, ast.If):
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    if "unverified" not in ast.unparse(unverified.test) or "tv_stale" not in ast.unparse(stale.test):
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    pending, opened = loop.body[17:]
    if _dump(pending.test) != _dump(ast.parse('t["state"] == "PENDING"').body[0].value):
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    if _dump(opened.test) != _dump(ast.parse('t["state"] == "OPEN"').body[0].value):
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    if not pending.body or isinstance(pending.body[-1], ast.Continue):
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    if len(opened.body) < 6 or not isinstance(opened.body[2], ast.Assign):
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    if "desk_success.observe_bars(t, since)" not in ast.unparse(opened.body[2]):
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    if not isinstance(opened.body[4], ast.If) or not isinstance(opened.body[4].body[-1], ast.Continue):
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    return _KERNEL_NAMES


def _extract_closed_kernel(text):
    tree = ast.parse(text)
    check = _function(tree, "check")
    wanted_loop = ast.parse('for key, t in list(d.items()):\n    pass').body[0]
    loops = [node for node in check.body if isinstance(node, ast.For) and _dump(node.target) == _dump(wanted_loop.target)]
    if len(loops) != 1 or _dump(loops[0].iter) != _dump(ast.parse('list(d.items())').body[0].value):
        raise ValueError("SOURCE_CLOSED_RESOLVER_KERNEL_MISMATCH")
    _kernel_names(loops[0])
    return copy.deepcopy(loops[0])


def _runtime_projection():
    """The precise bounded adaptation: closed bars only, no zone-return path."""
    return ast.parse(
        '''"""Pinned closed-bar lifecycle composition over caller-supplied mutable state."""
from __future__ import annotations
import pandas as pd
from .desk_success import DeskSuccess, minimum
from .lifecycle_bars import _open_extremes
from .lifecycle_closed_pending_resolution import LifecycleClosedPendingResolution
from .lifecycle_open_ordinary_resolution import LifecycleOpenOrdinaryResolution
from .lifecycle_open_protection import LifecycleOpenProtection
from .lifecycle_outcome_shelf import LifecycleOutcomeShelf
from .lifecycle_transitions import LifecycleTransitions

class LifecycleClosedResolver:
    """Resolve the retained closed 15-minute-bar branch without persistence or delivery."""
    TERMINAL = ("STOPPED", "DONE", "CANCELLED")
    def __init__(self, source):
        self.source = source
        self.pending = LifecycleClosedPendingResolution(source)
        self.desk_success = DeskSuccess(source)
        self.protection = LifecycleOpenProtection(source)
        self.ordinary = LifecycleOpenOrdinaryResolution(source)
        self.outcomes = LifecycleOutcomeShelf(source)
        self.transitions = LifecycleTransitions(source)
    def _resolve_closed_open(self, trade: dict, *, since, low: float, high: float):
        """Apply the retained closed-bar OPEN ordering to one post-fill window."""
        short = trade["direction"] == "שורט"
        protective = self.transitions._protective(trade, short)
        hit_protect = high >= protective if short else low <= protective
        minimum_message = self.desk_success.observe_bars(trade, since)
        messages: list[tuple[str, bool]] = []
        changed = False
        if minimum_message:
            steps = self.transitions._progress_steps(trade, low if short else high, short)
            if steps and not hit_protect:
                trade["progress_step"] = steps[-1][0]
            trade["reported_progress_points"] = minimum(trade["symbol"])
            messages.append((minimum_message, trade["to_group"]))
            self.outcomes._outcome({**trade, "result": "minimum_success"})
            changed = True
        child_messages, child_changed = self.protection.resolve(trade, low=low, high=high)
        messages.extend(child_messages)
        changed = changed or child_changed
        if child_changed:
            return messages, changed
        child_messages, child_changed = self.ordinary.resolve(trade, low=low, high=high, minimum_message=minimum_message)
        messages.extend(child_messages)
        return messages, changed or child_changed
    def resolve(self, state: dict, *, now: float) -> tuple[list[tuple[str, bool]], bool]:
        """Advance all supplied nonterminal records from corrected closed bars at one pass clock."""
        messages: list[tuple[str, bool]] = []
        changed = False
        for _key, trade in list(state.items()):
            if trade.get("state") in self.TERMINAL:
                continue
            try:
                frame, correction = self.source.fetch_corrected(trade["symbol"], "15m", 3)
                if correction is not None and (getattr(correction, "unverified", False) or getattr(correction, "source", "") == "tv_stale"):
                    continue
            except Exception:
                continue
            timestamps = pd.to_datetime(frame.index, utc=True)
            since = frame[[timestamp.timestamp() > float(trade["ts"]) for timestamp in timestamps]]
            if since.empty:
                continue
            high = float(since["high"].max())
            low = float(since["low"].min())
            extrema = _open_extremes(since, trade)
            post_fill_high, post_fill_low = extrema or (float(trade["entry"]),) * 2
            child_messages, child_changed = self.pending.resolve(trade, state=state, since=since, high=high, low=low, now=now)
            messages.extend(child_messages)
            changed = changed or child_changed
            if trade.get("state") != "OPEN":
                continue
            child_messages, child_changed = self._resolve_closed_open(trade, since=since, high=post_fill_high, low=post_fill_low)
            messages.extend(child_messages)
            changed = changed or child_changed
        return messages, changed
'''
    )


def _child_audit(name, source_root):
    module_name, function_name = CHILD_AUDITS[name]
    return getattr(importlib.import_module(module_name), function_name)(source_root)


def _valid_child_report(expected, report):
    if not isinstance(report, dict):
        return False
    try:
        json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return (
        report.get("status") == "VERIFIED"
        and report.get("source_subset_verified") is True
        and report.get("blockers") == []
        and report.get("checked_projections") == list(expected)
        and isinstance(report.get("dependencies"), dict)
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


def audit_lifecycle_closed_resolver_source(source_root) -> dict:
    """Fail closed after reading/parsing retained tracker text and vendor text only."""
    blockers, checked, dependencies = [], [], {}
    try:
        source_root = Path(source_root)
        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
        if [row.get("commit") for row in baseline["repositories"] if row.get("name") == "chart-desk"] != [COMMIT]:
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
        if hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != BLOB:
            blockers.append("SOURCE_BLOB_MISMATCH:tracker.py")
        _extract_closed_kernel(text)
        checked.append("lifecycle_closed_resolver_source_kernel")
        expected = _runtime_projection()
        actual = ast.parse((ROOT / Path(VENDOR)).read_text(encoding="utf-8"))
        if _dump(_without_docs(actual)) == _dump(_without_docs(expected)):
            checked.append("lifecycle_closed_resolver")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_closed_resolver")
    except Exception as exc:
        blockers.append(f"SOURCE_PROJECTION_UNREADABLE:lifecycle_closed_resolver:{type(exc).__name__}:{exc}")
    if set(CHILD_AUDITS) != {row[0] for row in _EXPECTED_CHILD_AUDITS}:
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
