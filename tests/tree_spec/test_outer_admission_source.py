"""Pinned-source proof for the full level-reversal outer-admission sequence."""
from __future__ import annotations

import hashlib
import importlib
import os
from pathlib import Path

import pytest


RETAINED_ROOT = Path(os.environ.get("TR_TREE_SOURCE_ROOT", Path(__file__).resolve().parents[2] / ".source-checkouts"))


def _api():
    return importlib.import_module("trading_system.tree_spec.causal_replay_source")


def _blob(text: str) -> str:
    raw = text.encode("utf-8")
    return hashlib.sha1(f"blob {len(raw)}\0".encode("utf-8") + raw).hexdigest()


def _mutated_audit(monkeypatch, old: str, new: str):
    module = _api()
    source = RETAINED_ROOT / "chart-desk" / "scripts" / "market_watch.py"
    original = source.read_text(encoding="utf-8")
    assert old in original
    changed = original.replace(old, new, 1)
    assert changed != original
    read_text = Path.read_text

    def patched_read_text(path, *args, **kwargs):
        if path.resolve() == source.resolve():
            return changed
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", patched_read_text)
    monkeypatch.setattr(module, "BLOB", _blob(changed))
    return module.check_source_parity(RETAINED_ROOT)


def test_pinned_source_exposes_full_outer_admission_gate_order():
    report = _api().check_source_parity(RETAINED_ROOT)

    assert report["status"] == "VERIFIED"
    assert report["projection"]["outer_admission_gate_order"] == [
        "entry_quality_annotation",
        "tradeable_plan",
        "hunting_window",
        "entry_clock",
        "post_stop",
        "occupied_slot",
        "same_level",
        "active_reversal",
        "episode",
        "record_alert_guard",
        "record",
    ]
    assert report["projection"]["outer_admission_dependencies"] == {
        "entry_quality": {
            "repository": "chart-desk",
            "path": "chartdesk/entry_quality.py",
            "function": "evaluate",
        },
        "hunting_window": {
            "repository": "chart-desk",
            "path": "chartdesk/windows.py",
            "function": "outside_reason",
        },
        "entry_clock": {
            "repository": "trading-floor",
            "path": "floor/marketclock.py",
            "function": "entry_blocked",
        },
    }


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("            _score_entry(plan)\n", "            _score_entry_missing(plan)\n"),
        ("if not plan.tradeable:", "if False:"),
        ("if st.get(state_key):", "if False:"),
    ],
)
def test_outer_admission_audit_rejects_omitted_required_gate(monkeypatch, old, new):
    report = _mutated_audit(monkeypatch, old, new)

    assert report["status"] == "BLOCKED"
    assert "MARKET_WATCH_ORDER_MISMATCH" in report["blockers"]
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_outer_admission_audit_rejects_window_and_clock_reordering(monkeypatch):
    source = RETAINED_ROOT / "chart-desk" / "scripts" / "market_watch.py"
    original = source.read_text(encoding="utf-8")
    window = '''            from chartdesk.windows import outside_reason as _outside
            outside = _outside()
            if outside:
                _blocked(plan, f"מחוץ לחלון: {outside}", source=src)
                continue
'''
    clock = '''            from floor import marketclock as _mc
            closed = _mc.entry_blocked()
            if closed:
                _blocked(plan, f"שוק סגור: {closed}", source=src)
                continue
'''
    assert window + clock in original
    changed = original.replace(window + clock, clock + window, 1)
    module = _api()
    read_text = Path.read_text

    def patched_read_text(path, *args, **kwargs):
        if path.resolve() == source.resolve():
            return changed
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", patched_read_text)
    monkeypatch.setattr(module, "BLOB", _blob(changed))
    report = module.check_source_parity(RETAINED_ROOT)

    assert report["status"] == "BLOCKED"
    assert "MARKET_WATCH_ORDER_MISMATCH" in report["blockers"]
