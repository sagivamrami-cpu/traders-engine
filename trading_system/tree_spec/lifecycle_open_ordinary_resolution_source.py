"""Read-only proof for the pinned ordinary OPEN-resolution source fragment."""
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
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_open_ordinary_resolution.py"
SOURCE_START_LINE = 2721
SOURCE_END_LINE = 2750
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
_EXPECTED_FRAGMENT_NAMES = (
    "tp1_now", "targets_guard", "tp1_value", "tp1_touch", "progress",
    "progress_guard", "target_loop", "recomputed_protection", "all_targets",
    "protective_guard",
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


def _expected_ordinary_fragment():
    return ast.parse(
        '''
tp1_now = False
if t["targets"]:
    _tp1 = float(t["targets"][0][1])
    tp1_now = (_lo <= _tp1) if short else (_hi >= _tp1)
progress = [] if (hit_protect or minimum_msg or tp1_now or "TP1" in t["hit"]) else \\
    _progress_messages(t, _lo if short else _hi, short, name, side)
if progress:
    out.extend(progress)
    t["progress_ts"] = time.time()
    changed = True
for i, (tname, tpx) in enumerate(t["targets"], 1):
    tag = f"TP{i}"
    if tag in t["hit"]:
        continue
    if (_lo <= tpx) if short else (_hi >= tpx):
        t["hit"].append(tag)
        t["progress_ts"] = time.time()
        changed = True
        out.append((_target_line(t, i, tag, tpx), t["to_group"]))
        _outcome({**t, "result": tag.lower()})
hit_protect = (_hi >= protective) if short else (_lo <= protective)
if len(t["hit"]) >= len(t["targets"]):
    _mark_terminal(t, "DONE")
    changed = True
elif hit_protect:
    msg, result, state = _resolve_protective(t, name, side)
    _mark_terminal(t, state)
    changed = True
    out.append((msg, t["to_group"]))
    _outcome({**t, "result": result})
'''
    ).body


def _fragment_names(fragment):
    expected = _expected_ordinary_fragment()
    if len(fragment) != len(expected) or any(
        _dump(actual) != _dump(wanted) for actual, wanted in zip(fragment, expected)
    ):
        raise ValueError("SOURCE_OPEN_ORDINARY_ORDER_MISMATCH")
    return _EXPECTED_FRAGMENT_NAMES


def _extract_ordinary_fragment(text):
    """Read and parse only the physical source slice; never execute source."""
    lines = text.splitlines(keepends=True)
    if len(lines) < SOURCE_END_LINE:
        raise ValueError("SOURCE_OPEN_ORDINARY_SLICE_MISSING")
    fragment = ast.parse(textwrap.dedent(
        "".join(lines[SOURCE_START_LINE - 1:SOURCE_END_LINE])
    )).body
    _fragment_names(fragment)
    return copy.deepcopy(fragment)


def _projection(text):
    """Build the only permitted private supplied-window projection."""
    _extract_ordinary_fragment(text)
    return ast.parse(
        '''
from __future__ import annotations
from .lifecycle_outcome_shelf import LifecycleOutcomeShelf
from .lifecycle_transitions import LifecycleTransitions

class LifecycleOpenOrdinaryResolution:
    def __init__(self, source):
        self.source = source
        self.outcomes = LifecycleOutcomeShelf(source)
        self.transitions = LifecycleTransitions(source)

    def resolve(self, trade: dict, *, low: float, high: float, minimum_message) -> tuple[list[tuple[str, bool]], bool]:
        short = trade["direction"] == "\\u05e9\\u05d5\\u05e8\\u05d8"
        name = trade["symbol"].split(":")[-1]
        side = "SELL" if short else "BUY"
        protective = self.transitions._protective(trade, short)
        hit_protect = high >= protective if short else low <= protective

        tp1_now = False
        if trade["targets"]:
            target_one = float(trade["targets"][0][1])
            tp1_now = low <= target_one if short else high >= target_one
        progress = ([] if (hit_protect or minimum_message or tp1_now or "TP1" in trade["hit"])
                    else self.transitions._progress_messages(
                        trade, low if short else high, short, name, side))

        messages: list[tuple[str, bool]] = []
        changed = False
        if progress:
            messages.extend(progress)
            trade["progress_ts"] = self.source.now_epoch()
            changed = True

        for index, (_target_name, target_price) in enumerate(trade["targets"], 1):
            tag = f"TP{index}"
            if tag in trade["hit"]:
                continue
            if low <= target_price if short else high >= target_price:
                trade["hit"].append(tag)
                trade["progress_ts"] = self.source.now_epoch()
                changed = True
                messages.append((self.transitions._target_line(
                    trade, index, tag, target_price), trade["to_group"]))
                self.outcomes._outcome({**trade, "result": tag.lower()})

        hit_protect = high >= protective if short else low <= protective
        if len(trade["hit"]) >= len(trade["targets"]):
            self.transitions._mark_terminal(trade, "DONE")
            changed = True
        elif hit_protect:
            message, result, state = self.transitions._resolve_protective(trade, name, side)
            self.transitions._mark_terminal(trade, state)
            changed = True
            messages.append((message, trade["to_group"]))
            self.outcomes._outcome({**trade, "result": result})

        return messages, changed
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


def audit_lifecycle_open_ordinary_resolution_source(source_root) -> dict:
    """Fail closed on source, projection, child-proof, or report drift."""
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
            checked.append("lifecycle_open_ordinary_resolution")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_open_ordinary_resolution")
    except Exception as exc:
        blockers.append(
            "SOURCE_PROJECTION_UNREADABLE:"
            f"lifecycle_open_ordinary_resolution:{type(exc).__name__}:{exc}"
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
