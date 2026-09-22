"""Read-only proof for the pinned OPEN minimum-success source branch."""
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
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_open_minimum_success.py"
SOURCE_START_LINE = 2690
SOURCE_END_LINE = 2704
CHILD_AUDITS = {
    "lifecycle_open_postfill_evidence": (
        "trading_system.tree_spec.lifecycle_open_postfill_evidence_source",
        "audit_lifecycle_open_postfill_evidence_source",
    ),
    "lifecycle_transitions": (
        "trading_system.tree_spec.lifecycle_transitions_source",
        "audit_lifecycle_transitions_source",
    ),
    "lifecycle_outcome_shelf": (
        "trading_system.tree_spec.lifecycle_outcome_shelf_source",
        "audit_lifecycle_outcome_shelf_source",
    ),
}
_EXPECTED_CHILD_AUDITS = (
    ("lifecycle_open_postfill_evidence", *CHILD_AUDITS["lifecycle_open_postfill_evidence"]),
    ("lifecycle_transitions", *CHILD_AUDITS["lifecycle_transitions"]),
    ("lifecycle_outcome_shelf", *CHILD_AUDITS["lifecycle_outcome_shelf"]),
)
_REQUIRED_CHILD_PROJECTIONS = (
    ("lifecycle_open_postfill_evidence", ("lifecycle_open_postfill_evidence",)),
    ("lifecycle_transitions", ("lifecycle_transitions",)),
    ("lifecycle_outcome_shelf", ("lifecycle_outcome_shelf",)),
)
_EXPECTED_BRANCH_NAMES = (
    "hit_protect", "quote", "quote_timestamp", "quote_minimum",
    "minimum_guard", "directional_progress", "progress_guard",
    "reported_points", "message_before_outcome", "minimum_outcome", "changed",
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


def _expected_minimum_success_branch():
    """The physical source slice, wrapped only so its indentation can parse."""
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
'''
    return ast.parse(wrapper).body[0].body


def _parse_pinned_minimum_success_slice(text):
    """Parse only retained tracker.py lines 2690--2704; never import source."""
    lines = text.splitlines(keepends=True)
    if len(lines) < SOURCE_END_LINE:
        raise ValueError("SOURCE_OPEN_MINIMUM_SUCCESS_SLICE_MISSING")
    wrapped = "for _ in ():\n" + "".join(lines[SOURCE_START_LINE - 1:SOURCE_END_LINE])
    tree = ast.parse(wrapped)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.For):
        raise ValueError("SOURCE_OPEN_MINIMUM_SUCCESS_SLICE_PARSE_MISMATCH")
    return tree.body[0].body


def _minimum_success_names(branch):
    expected = _expected_minimum_success_branch()
    if len(branch) != len(expected) or any(
        _dump(actual) != _dump(wanted) for actual, wanted in zip(branch, expected)
    ):
        raise ValueError("SOURCE_OPEN_MINIMUM_SUCCESS_ORDER_MISMATCH")
    return _EXPECTED_BRANCH_NAMES


def _extract_minimum_success_branch(text):
    """Return a copy only after exact physical source-order verification."""
    branch = _parse_pinned_minimum_success_slice(text)
    _minimum_success_names(branch)
    return copy.deepcopy(branch)


def _projection(text):
    """Build the only allowed private supplied-evidence projection."""
    _extract_minimum_success_branch(text)
    return ast.parse(
        '''
from __future__ import annotations
from .desk_success import DeskSuccess, minimum
from .lifecycle_outcome_shelf import LifecycleOutcomeShelf
from .lifecycle_transitions import LifecycleTransitions

class LifecycleOpenMinimumSuccess:
    FORCE_BAR_AGE_S = 120.0

    def __init__(self, source):
        self.source = source
        self.desk_success = DeskSuccess(source)
        self.transitions = LifecycleTransitions(source)
        self.outcomes = LifecycleOutcomeShelf(source)

    def resolve(self, trade: dict, *, low: float, high: float, spot: float,
                quote: dict, has_bar_extremes: bool,
                minimum_message: str | None) -> tuple[list[tuple[str, bool]], bool, str | None]:
        short = trade["direction"] == "\u05e9\u05d5\u05e8\u05d8"
        protective = self.transitions._protective(trade, short)
        hit_protect = high >= protective if short else low <= protective
        quote_ts = float(quote.get("price_ts") or quote.get("ts") or 0)
        if (not minimum_message and not hit_protect and not has_bar_extremes
                and quote.get("lp") == spot
                and 0 <= self.source.now_epoch() - quote_ts <= self.FORCE_BAR_AGE_S
                and quote_ts >= float(trade.get("filled_ts") or self.source.now_epoch())):
            minimum_message = self.desk_success.observe(
                trade, spot, quote_ts, "exact_venue_quote"
            )

        if not minimum_message:
            return [], False, minimum_message

        steps = self.transitions._progress_steps(trade, low if short else high, short)
        if steps and not hit_protect:
            trade["progress_step"] = steps[-1][0]
        trade["reported_progress_points"] = minimum(trade["symbol"])
        messages = [(minimum_message, trade["to_group"])]
        self.outcomes._outcome({**trade, "result": "minimum_success"})
        return messages, True, minimum_message
'''
    )


def _child_audit(name, source_root):
    module_name, function_name = CHILD_AUDITS[name]
    module = importlib.import_module(module_name)
    return getattr(module, function_name)(source_root)


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


def audit_lifecycle_open_minimum_success_source(source_root):
    """Fail closed on source identity, branch, runtime, or child-proof drift."""
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
            checked.append("lifecycle_open_minimum_success")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_open_minimum_success")
    except Exception as exc:
        blockers.append(
            "SOURCE_PROJECTION_UNREADABLE:"
            f"lifecycle_open_minimum_success:{type(exc).__name__}:{exc}"
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
