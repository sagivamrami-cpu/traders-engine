from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "configs/data/xauusd-gc-crossmarket-order-flow-context.yaml"


def valid_policy_text() -> str:
    return """
version: xauusd-gc-crossmarket-order-flow-context-v1
target_instrument: OANDA:XAUUSD
source_instrument: CME:GC
source_dataset: DATABENTO/GLBX.MDP3
archive_sha256: 34f82b1b9306f3605b00d60bcb96cb4aa0fc74c5de1f2d2401d1c1d610f03155
selected_member: gc/GCext_of_1m.parquet
allowed_columns: [minute, volume, delta, trades]
timestamp_role: MINUTE_START_APPROVED_V1
timezone: UTC
damaged_window:
  start: "2017-01-01T00:00:00Z"
  end: "2017-06-01T00:00:00Z"
decision_ref: agent-exchange/decisions/2026-09-15T102150Z-human-gc-order-flow-xauusd-context.md
""".strip()


def test_policy_exposes_the_approved_xauusd_gc_context_identity():
    from trading_system.tree_replay.cross_market_flow_policy import CrossMarketFlowPolicy

    policy = CrossMarketFlowPolicy.load(POLICY)

    assert policy.target_instrument == "OANDA:XAUUSD"
    assert policy.source_instrument == "CME:GC"
    assert policy.source_dataset == "DATABENTO/GLBX.MDP3"
    assert policy.allowed_columns == ("minute", "volume", "delta", "trades")
    assert policy.damaged_start == datetime(2017, 1, 1, tzinfo=UTC)
    assert policy.damaged_end == datetime(2017, 6, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    "changed, expected",
    [
        ("OANDA:XAUUSD", "OANDA:GC"),
        ("CME:GC", "OANDA:XAUUSD"),
        ("[minute, volume, delta, trades]", "[minute, close, delta, trades]"),
        ("timezone: UTC", "timezone: Asia/Jerusalem"),
    ],
)
def test_policy_rejects_changed_identity_price_column_or_timezone(tmp_path, changed, expected):
    from trading_system.tree_replay.cross_market_flow_policy import CrossMarketFlowPolicy

    path = tmp_path / "policy.yaml"
    path.write_text(valid_policy_text().replace(changed, expected, 1), encoding="utf-8")

    with pytest.raises(ValueError, match="CROSS_MARKET_POLICY"):
        CrossMarketFlowPolicy.load(path)


def test_policy_rejects_unknown_fields_and_reversed_damage_window(tmp_path):
    from trading_system.tree_replay.cross_market_flow_policy import CrossMarketFlowPolicy

    unknown = tmp_path / "unknown.yaml"
    unknown.write_text(valid_policy_text() + "\nunapproved_price_mapping: true\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CROSS_MARKET_POLICY"):
        CrossMarketFlowPolicy.load(unknown)

    reversed_window = tmp_path / "reversed.yaml"
    reversed_window.write_text(
        valid_policy_text().replace("2017-06-01T00:00:00Z", "2016-06-01T00:00:00Z"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="CROSS_MARKET_POLICY"):
        CrossMarketFlowPolicy.load(reversed_window)
