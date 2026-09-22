"""Read-only proof for the pinned live PENDING/OPEN resolver composition."""
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
VENDOR = "trading_system/tree_replay/_vendor/lifecycle_live_resolver.py"
SOURCE_KERNEL_AST_SHA256 = "82c517c1014c084b3a49fa4da9052ccdb3f8a9b5f26c2d06c2fdb7364547fe43"
CHILD_AUDITS = {
    "lifecycle_live_evidence": (
        "trading_system.tree_spec.lifecycle_live_evidence_source",
        "audit_lifecycle_live_evidence_source",
    ),
    "lifecycle_pending_resolution": (
        "trading_system.tree_spec.lifecycle_pending_resolution_source",
        "audit_lifecycle_pending_resolution_source",
    ),
    "lifecycle_open_postfill_evidence": (
        "trading_system.tree_spec.lifecycle_open_postfill_evidence_source",
        "audit_lifecycle_open_postfill_evidence_source",
    ),
    "lifecycle_open_minimum_success": (
        "trading_system.tree_spec.lifecycle_open_minimum_success_source",
        "audit_lifecycle_open_minimum_success_source",
    ),
    "lifecycle_open_protection": (
        "trading_system.tree_spec.lifecycle_open_protection_source",
        "audit_lifecycle_open_protection_source",
    ),
    "lifecycle_open_ordinary_resolution": (
        "trading_system.tree_spec.lifecycle_open_ordinary_resolution_source",
        "audit_lifecycle_open_ordinary_resolution_source",
    ),
    "lifecycle_open_zone_return": (
        "trading_system.tree_spec.lifecycle_open_zone_return_source",
        "audit_lifecycle_open_zone_return_source",
    ),
}
_EXPECTED_CHILD_AUDITS = tuple((name, *value) for name, value in CHILD_AUDITS.items())
_REQUIRED_CHILD_PROJECTIONS = (
    ("lifecycle_live_evidence", ("lifecycle_live_evidence",)),
    ("lifecycle_pending_resolution", ("lifecycle_pending_resolution",)),
    ("lifecycle_open_postfill_evidence", ("lifecycle_open_postfill_evidence",)),
    ("lifecycle_open_minimum_success", ("lifecycle_open_minimum_success",)),
    ("lifecycle_open_protection", ("lifecycle_open_protection",)),
    ("lifecycle_open_ordinary_resolution", ("lifecycle_open_ordinary_resolution",)),
    (
        "lifecycle_open_zone_return",
        (
            "lifecycle_open_zone_return_helper",
            "lifecycle_open_zone_return_live_call",
            "lifecycle_open_zone_return",
        ),
    ),
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


def _function(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise ValueError(f"SOURCE_FUNCTION_MISSING:{name}")


def _extract_source_kernel(text):
    """Parse and pin only source lines 2559--2760; never execute them."""
    try:
        fn = _function(ast.parse(text), "_check_live_locked")
    except (SyntaxError, ValueError) as exc:
        raise ValueError("SOURCE_LIVE_RESOLVER_KERNEL_MISMATCH") from exc
    kernel = fn.body[3:12]
    if len(kernel) != 9:
        raise ValueError("SOURCE_LIVE_RESOLVER_KERNEL_MISMATCH")
    actual = hashlib.sha256(
        _dump(ast.Module(body=kernel, type_ignores=[])).encode("utf-8")
    ).hexdigest()
    if actual != SOURCE_KERNEL_AST_SHA256:
        raise ValueError("SOURCE_LIVE_RESOLVER_KERNEL_MISMATCH")
    return copy.deepcopy(kernel)


def _runtime_projection():
    """The only allowed supplied-port adaptation of the verified kernel."""
    return ast.parse(
        '''"""Pinned live PENDING/OPEN resolver composition over supplied offline ports."""
from __future__ import annotations

import pandas as pd

from .lifecycle_live_evidence import LifecycleLiveEvidence
from .lifecycle_open_minimum_success import LifecycleOpenMinimumSuccess
from .lifecycle_open_ordinary_resolution import LifecycleOpenOrdinaryResolution
from .lifecycle_open_postfill_evidence import LifecycleOpenPostfillEvidence
from .lifecycle_open_protection import LifecycleOpenProtection
from .lifecycle_open_zone_return import LifecycleOpenZoneReturn
from .lifecycle_pending_resolution import LifecyclePendingResolution


class LifecycleLiveResolver:
    """Compose accepted live-resolution children in retained source order."""

    FORCE_BAR_AGE_S = LifecycleLiveEvidence.FORCE_BAR_AGE_S

    def __init__(self, source):
        self.source = source
        self.pending = LifecyclePendingResolution(source)
        self.postfill = LifecycleOpenPostfillEvidence(source)
        self.minimum = LifecycleOpenMinimumSuccess(source)
        self.protection = LifecycleOpenProtection(source)
        self.ordinary = LifecycleOpenOrdinaryResolution(source)
        self.zone_return = LifecycleOpenZoneReturn(source)

    def _observation(self, state: dict) -> tuple[dict, dict, dict]:
        """Return the source's two-read quote snapshot and corrected range facts."""
        prices = LifecycleLiveEvidence(self.source)._live_prices()
        bar_extremes = {}
        try:
            raw_quotes = self.source.quote_payload()
        except Exception:
            raw_quotes = {}
        now = self.source.now_epoch()
        symbols = {
            trade["symbol"]
            for trade in state.values()
            if trade.get("state") in ("PENDING", "OPEN")
        }
        for symbol in symbols:
            age = now - float((raw_quotes.get(symbol) or {}).get("ts", 0))
            if symbol in prices and age <= self.FORCE_BAR_AGE_S:
                continue
            try:
                bars, correction = self.source.fetch_corrected(symbol, "15m", 2)
                if correction is not None and (
                    getattr(correction, "unverified", False)
                    or getattr(correction, "source", "") == "tv_stale"
                ):
                    continue
                latest = pd.to_datetime(bars.index[-1], utc=True).timestamp()
                if symbol not in prices or latest > now - age:
                    bar_extremes[symbol] = (
                        float(bars["low"].iloc[-1]),
                        float(bars["high"].iloc[-1]),
                    )
                    prices[symbol] = float(bars["close"].iloc[-1])
            except Exception:
                continue
        return prices, bar_extremes, raw_quotes

    def resolve(self, state: dict) -> tuple[list[tuple[str, bool]], bool]:
        """Resolve supplied live records without persistence, delivery, or loading."""
        prices, bar_extremes, raw_quotes = self._observation(state)
        if not prices:
            return [], False

        messages: list[tuple[str, bool]] = []
        changed = False
        for _key, trade in list(state.items()):
            if trade.get("state") in ("STOPPED", "DONE", "CANCELLED"):
                continue
            symbol = trade["symbol"]
            if symbol not in prices:
                continue
            spot = prices[symbol]

            if trade.get("state") == "PENDING":
                child_messages, child_changed = self.pending.resolve(
                    trade, state=state, price=spot, bar_extremes=bar_extremes
                )
                messages.extend(child_messages)
                changed = changed or child_changed
                if trade.get("state") == "CANCELLED":
                    continue

            if trade.get("state") != "OPEN":
                continue
            low, high, provisional_minimum = self.postfill.collect(trade, spot)
            child_messages, child_changed, minimum_message = self.minimum.resolve(
                trade,
                low=low,
                high=high,
                spot=spot,
                quote=raw_quotes.get(symbol) or {},
                has_bar_extremes=symbol in bar_extremes,
                minimum_message=provisional_minimum,
            )
            messages.extend(child_messages)
            changed = changed or child_changed

            child_messages, child_changed = self.protection.resolve(trade, low=low, high=high)
            messages.extend(child_messages)
            changed = changed or child_changed
            if child_changed:
                continue

            child_messages, child_changed = self.ordinary.resolve(
                trade, low=low, high=high, minimum_message=minimum_message
            )
            messages.extend(child_messages)
            changed = changed or child_changed
            if trade.get("state") == "OPEN":
                child_messages, child_changed = self.zone_return.resolve(trade, spot=spot)
                messages.extend(child_messages)
                changed = changed or child_changed

        return messages, changed
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


def audit_lifecycle_live_resolver_source(source_root) -> dict:
    """Fail closed after parsing only retained source and runtime text."""
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
        _extract_source_kernel(text)
        checked.append("lifecycle_live_resolver_source_kernel")
        expected = _runtime_projection()
        actual = ast.parse((ROOT / Path(VENDOR)).read_text(encoding="utf-8"))
        if _dump(_without_docs(actual)) == _dump(_without_docs(expected)):
            checked.append("lifecycle_live_resolver")
        else:
            blockers.append("VENDOR_AST_MISMATCH:lifecycle_live_resolver")
    except Exception as exc:
        blockers.append(
            "SOURCE_PROJECTION_UNREADABLE:"
            f"lifecycle_live_resolver:{type(exc).__name__}:{exc}"
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
