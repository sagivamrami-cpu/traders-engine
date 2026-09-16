"""Read-only proof for the pinned conservative OPEN protection branch."""
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
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_open_protection.py"
SOURCE_START_LINE = 2690
SOURCE_END_LINE = 2715
CHILD_AUDITS = {
    "lifecycle_outcome_shelf": (
        "trading_system.tree_spec.lifecycle_outcome_shelf_source",
        "audit_lifecycle_outcome_shelf_source",
    ),
    "lifecycle_transitions": (
        "trading_system.tree_spec.lifecycle_transitions_source",
        "audit_lifecycle_transitions_source",
    ),
}
_EXPECTED_CHILD_AUDITS = (
    ("lifecycle_outcome_shelf", *CHILD_AUDITS["lifecycle_outcome_shelf"]),
    ("lifecycle_transitions", *CHILD_AUDITS["lifecycle_transitions"]),
)
_REQUIRED_CHILD_PROJECTIONS = (
    ("lifecycle_outcome_shelf", ("lifecycle_outcome_shelf",)),
    ("lifecycle_transitions", ("lifecycle_transitions",)),
)
_EXPECTED_PROTECTION_NAMES = (
    "hit_protect", "quote", "quote_timestamp", "quote_minimum",
    "minimum_success", "ambiguity",
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


def _expected_protection_branch():
    """The physical source slice, wrapped only so its ``continue`` can parse."""
    wrapper = '''
for _ in ():
    hit_protect = (_hi >= protective) if short else (_lo <= protective)
    q = _q.get(t["symbol"]) or {}
    qts = float(q.get("price_ts") or q.get("ts") or 0)
    if (not minimum_msg and not hit_protect and t["symbol"] not in _bar_extremes
            and q.get("lp") == px and 0 <= time.time() - qts <= FORCE_BAR_AGE_S
            and qts >= float(t.get("filled_ts") or time.time())):
        minimum_msg = desk_success.observe(t, px, qts, "exact_venue_quote")
    if minimum_msg:
        steps = _progress_steps(t, _lo if short else _hi, short)
        if steps and not hit_protect:
            t["progress_step"] = steps[-1][0]
        t["reported_progress_points"] = desk_success.minimum(t["symbol"])
        out.append((minimum_msg, t["to_group"]))
        _outcome({**t, "result": "minimum_success"})
        changed = True
    if _ambiguous_touch(t, _lo, _hi, short, protective):
        _mark_terminal(t, "STOPPED" if not t["hit"] else "DONE")
        changed = True
        msg, res = _resolve_ambiguous(t, name, side)
        out.append((msg, t["to_group"]))
        _outcome({**t, "result": res})
        continue
'''
    return ast.parse(wrapper).body[0].body


def _parse_pinned_protection_slice(text):
    """Parse only retained tracker.py lines 2690--2715, never the source module."""
    lines = text.splitlines(keepends=True)
    if len(lines) < SOURCE_END_LINE:
        raise ValueError("SOURCE_OPEN_PROTECTION_SLICE_MISSING")
    wrapped = "for _ in ():\n" + "".join(lines[SOURCE_START_LINE - 1:SOURCE_END_LINE])
    tree = ast.parse(wrapped)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.For):
        raise ValueError("SOURCE_OPEN_PROTECTION_SLICE_PARSE_MISMATCH")
    return tree.body[0].body


def _protection_names(branch):
    expected = _expected_protection_branch()
    if len(branch) != len(expected) or any(
        _dump(actual) != _dump(wanted) for actual, wanted in zip(branch, expected)
    ):
        raise ValueError("SOURCE_OPEN_PROTECTION_ORDER_MISMATCH")
    return _EXPECTED_PROTECTION_NAMES


def _extract_protection_branch(text):
    """Return the exact AST branch after checking the pinned physical slice."""
    branch = _parse_pinned_protection_slice(text)
    _protection_names(branch)
    return copy.deepcopy(branch)


def _projection(text):
    """Build the allowed supplied-window projection after static source proof."""
    _extract_protection_branch(text)
    return ast.parse(
        '''
from __future__ import annotations
from .lifecycle_outcome_shelf import LifecycleOutcomeShelf
from .lifecycle_transitions import LifecycleTransitions

class LifecycleOpenProtection:
    def __init__(self, source):
        self.source = source
        self.outcomes = LifecycleOutcomeShelf(source)
        self.transitions = LifecycleTransitions(source)

    def resolve(self, trade: dict, *, low: float, high: float) -> tuple[list[tuple[str, bool]], bool]:
        short = trade["direction"] == "\u05e9\u05d5\u05e8\u05d8"
        name = trade["symbol"].split(":")[-1]
        side = "SELL" if short else "BUY"
        protective = self.transitions._protective(trade, short)
        if not self.transitions._ambiguous_touch(trade, low, high, short, protective):
            return ([], False)
        self.transitions._mark_terminal(trade, "STOPPED" if not trade["hit"] else "DONE")
        message, result = self.transitions._resolve_ambiguous(trade, name, side)
        self.outcomes._outcome({**trade, "result": result})
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


def audit_lifecycle_open_protection_source(source_root):
    """Fail closed on source identity, protected slice, runtime, or child drift."""
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
        expected = _projection(text)
        actual = ast.parse((ROOT / Path(VENDOR)).read_text(encoding="utf-8"))
        if _dump(_without_docs(actual)) == _dump(_without_docs(expected)):
            checked.append("lifecycle_open_protection")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_open_protection")
    except Exception as exc:
        blockers.append(
            "SOURCE_PROJECTION_UNREADABLE:"
            f"lifecycle_open_protection:{type(exc).__name__}:{exc}"
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
