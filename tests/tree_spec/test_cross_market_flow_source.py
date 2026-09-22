from __future__ import annotations

import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FLOW = ROOT / "trading_system/tree_replay/cross_market_flow.py"


def api():
    return importlib.import_module("trading_system.tree_spec.cross_market_flow_source")


def test_static_audit_proves_no_price_mapping_or_live_loader_and_false_readiness():
    report = api().check_cross_market_flow_source()

    assert report["status"] == "VERIFIED"
    assert report["forbidden_price_mapping"] is False
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False
    assert report["source_bindings"] == ["CrossMarketFlowPolicy", "FullTreeEvidenceBundle"]


def test_static_audit_blocks_weakened_closed_minute_comparison(monkeypatch):
    module = api()
    original = FLOW.read_text(encoding="utf-8")
    assert "current + _MINUTE <= decision_time" in original
    actual_read = Path.read_text

    def read_text(path, *args, **kwargs):
        if path.resolve() == FLOW.resolve():
            return original.replace("current + _MINUTE <= decision_time", "current + _MINUTE < decision_time", 1)
        return actual_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    report = module.check_cross_market_flow_source()

    assert report["status"] == "BLOCKED"
    assert report["blockers"] == ["CLOSED_MINUTE_COMPARISON_MISMATCH"]


def test_static_audit_blocks_cvd_or_live_import(monkeypatch):
    module = api()
    original = FLOW.read_text(encoding="utf-8")
    actual_read = Path.read_text

    def read_text(path, *args, **kwargs):
        if path.resolve() == FLOW.resolve():
            return "import requests\ncvd = 0\n" + original
        return actual_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    report = module.check_cross_market_flow_source()

    assert report["status"] == "BLOCKED"
    assert report["blockers"] == ["FORBIDDEN_LIVE_IMPORT:requests", "FORBIDDEN_CUMULATIVE_FEATURE:cvd"]
