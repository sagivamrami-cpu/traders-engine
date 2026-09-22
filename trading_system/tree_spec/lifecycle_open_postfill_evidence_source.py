"""Read-only AST proof for the tracker OPEN post-fill evidence branch."""
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
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_open_postfill_evidence.py"
CHILD_AUDITS = {
    "lifecycle_live_evidence": (
        "trading_system.tree_spec.lifecycle_live_evidence_source",
        "audit_lifecycle_live_evidence_source",
    ),
    "lifecycle_primitives": (
        "trading_system.tree_spec.lifecycle_primitives_source",
        "audit_lifecycle_primitives_source",
    ),
}
_EXPECTED_CHILD_AUDITS = (
    ("lifecycle_live_evidence", *CHILD_AUDITS["lifecycle_live_evidence"]),
    ("lifecycle_primitives", *CHILD_AUDITS["lifecycle_primitives"]),
)
_REQUIRED_CHILD_PROJECTIONS = (
    ("lifecycle_live_evidence", ("lifecycle_live_evidence",)),
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


def _function(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise ValueError(f"SOURCE_FUNCTION_MISSING:{name}")


def _is_open_guard(node):
    return (
        isinstance(node, ast.If)
        and not node.orelse
        and _dump(node.test) == _dump(ast.parse('t["state"] == "OPEN"', mode="eval").body)
    )


def _open_branch_names(branch):
    expected = ast.parse(
        '''
protective = _protective(t, short)
_lo = _hi = px
minimum_msg = None
try:
    _df, _c = basis.fetch_corrected(t["symbol"], "15m", 2)
    _bad_tape = (_c is not None and
                 (getattr(_c, "unverified", False) or
                  getattr(_c, "source", "") == "tv_stale"))
    _fi = (_fill_on_tape(_df, t)
           if (not _bad_tape or _historical_replay_safe(_df, _c, t))
           else None)
    if _fi is not None:
        minimum_msg = desk_success.observe_bars(t, _df)
        _h, _l = _position_extremes(_df.loc[_fi:], t, fill_bar_first=True)
        _lo, _hi = min(px, _l), max(px, _h)
except Exception:
    pass
'''
    ).body
    names = ("protective", "spot_window", "minimum_message", "tape_try")
    if len(branch) < len(expected) or any(
        _dump(actual) != _dump(wanted) for actual, wanted in zip(branch[:len(expected)], expected)
    ):
        raise ValueError("SOURCE_OPEN_BRANCH_ORDER_MISMATCH")
    return names


def _extract_open_branch(text):
    """Extract the exact OPEN block without importing or executing source."""
    fn = _function(ast.parse(text), "_check_live_locked")
    guards = [node for node in ast.walk(fn) if _is_open_guard(node)]
    if len(guards) != 1:
        raise ValueError("SOURCE_OPEN_BRANCH_MISSING_OR_AMBIGUOUS")
    branch = copy.deepcopy(guards[0].body[:4])
    _open_branch_names(branch)
    return branch


def _projection(text):
    """Adapt only the verified source evidence block to its supplied ports."""
    _extract_open_branch(text)
    return ast.parse(
        '''
from copy import copy
from .desk_success import DeskSuccess
from .lifecycle_bars import _fill_on_tape, _position_extremes
from .lifecycle_live_evidence import LifecycleLiveEvidence

class LifecycleOpenPostfillEvidence:
    def __init__(self, source):
        self.source = source
        self.live_evidence = LifecycleLiveEvidence(source)

    def collect(self, trade: dict, spot: float) -> tuple[float, float, str | None]:
        low = high = spot
        minimum_message = None
        try:
            tape, correction = self.source.fetch_corrected(trade["symbol"], "15m", 2)
            bad_tape = correction is not None and (
                getattr(correction, "unverified", False)
                or getattr(correction, "source", "") == "tv_stale"
            )
            fill = (
                _fill_on_tape(tape, trade)
                if not bad_tape or self.live_evidence._historical_replay_safe(tape, correction, trade)
                else None
            )
            if fill is not None:
                minimum_message = DeskSuccess(self.source).observe_bars(copy(trade), tape)
                tape_high, tape_low = _position_extremes(
                    tape.loc[fill:], trade, fill_bar_first=True
                )
                low, high = min(spot, tape_low), max(spot, tape_high)
        except Exception:
            pass
        return low, high, minimum_message
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


def audit_lifecycle_open_postfill_evidence_source(source_root):
    """Fail closed on identity, source projection, or accepted-child drift."""
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
            checked.append("lifecycle_open_postfill_evidence")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_open_postfill_evidence")
    except Exception as exc:
        blockers.append(
            "SOURCE_PROJECTION_UNREADABLE:"
            f"lifecycle_open_postfill_evidence:{type(exc).__name__}:{exc}"
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
