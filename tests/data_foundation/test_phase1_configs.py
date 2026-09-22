from pathlib import Path

import pytest
import yaml

import tools.validate_phase1 as phase1

ROOT = Path(__file__).resolve().parents[2]


def load_yaml(relative_path: str) -> dict:
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


def test_data_configs_are_versioned():
    for path in [
        "configs/data/source-inventory.yaml",
        "configs/data/session-calendar.yaml",
        "configs/data/symbol-map.yaml",
        "configs/data/normalization-policy.yaml",
    ]:
        data = load_yaml(path)
        assert data["version"]


def test_approved_sources_reference_calendar_and_symbol():
    inventory = load_yaml("configs/data/source-inventory.yaml")
    calendars = load_yaml("configs/data/session-calendar.yaml")["calendars"]
    symbols = load_yaml("configs/data/symbol-map.yaml")["symbols"]
    canonical_symbols = {item["canonical_symbol"] for item in symbols}

    for source in inventory["sources"]:
        assert source["owner"]
        if source["source_status"] != "APPROVED_FIXTURE":
            continue
        assert source["session_calendar_id"] in calendars
        assert source["canonical_symbol"] in canonical_symbols


def test_real_sources_remain_open_human_decisions():
    inventory = load_yaml("configs/data/source-inventory.yaml")
    real_sources = [source for source in inventory["sources"] if source["source_id"].startswith("real-")]
    assert real_sources
    assert {source["source_status"] for source in real_sources} == {"OPEN_HUMAN_DECISION"}


def test_non_fixture_sources_cannot_be_approved_by_inventory_status(tmp_path: Path, monkeypatch):
    config_root = tmp_path / "configs/data"
    config_root.mkdir(parents=True)
    (config_root / "session-calendar.yaml").write_text(
        yaml.safe_dump({"version": "test", "calendars": {"us-equities-regular-v1": {}}}),
        encoding="utf-8",
    )
    (config_root / "symbol-map.yaml").write_text(
        yaml.safe_dump(
            {
                "version": "test",
                "symbols": [
                    {"canonical_symbol": "TR_FIXTURE_SPY"},
                    {"canonical_symbol": "GC"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (config_root / "normalization-policy.yaml").write_text(
        yaml.safe_dump({"version": "test"}),
        encoding="utf-8",
    )
    (config_root / "source-inventory.yaml").write_text(
        yaml.safe_dump(
            {
                "version": "test",
                "sources": [
                    {
                        "source_id": "ohlcv-fixture-v1",
                        "source_status": "APPROVED_FIXTURE",
                        "session_calendar_id": "us-equities-regular-v1",
                        "canonical_symbol": "TR_FIXTURE_SPY",
                        "owner": "Codex",
                    },
                    {
                        "source_id": "databento-gc-1s",
                        "source_status": "APPROVED",
                        "session_calendar_id": "cme-globex-metals-research-pending-v1",
                        "canonical_symbol": "GC",
                        "owner": "Human Data Owner",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(phase1, "ROOT", tmp_path)

    with pytest.raises(ValueError, match="non-fixture source is not open"):
        phase1.validate_data_configs()


def test_pending_gc_metals_calendar_cannot_be_registered_before_d2(tmp_path: Path, monkeypatch):
    config_root = tmp_path / "configs/data"
    config_root.mkdir(parents=True)
    (config_root / "session-calendar.yaml").write_text(
        yaml.safe_dump(
            {
                "version": "test",
                "calendars": {
                    "us-equities-regular-v1": {},
                    "cme-globex-metals-research-pending-v1": {},
                },
            }
        ),
        encoding="utf-8",
    )
    (config_root / "symbol-map.yaml").write_text(
        yaml.safe_dump({"version": "test", "symbols": [{"canonical_symbol": "TR_FIXTURE_SPY"}]}),
        encoding="utf-8",
    )
    (config_root / "normalization-policy.yaml").write_text(
        yaml.safe_dump({"version": "test"}),
        encoding="utf-8",
    )
    (config_root / "source-inventory.yaml").write_text(
        yaml.safe_dump(
            {
                "version": "test",
                "sources": [
                    {
                        "source_id": "ohlcv-fixture-v1",
                        "source_status": "APPROVED_FIXTURE",
                        "session_calendar_id": "us-equities-regular-v1",
                        "canonical_symbol": "TR_FIXTURE_SPY",
                        "owner": "Codex",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(phase1, "ROOT", tmp_path)

    with pytest.raises(ValueError, match="pending GC metals calendar cannot be registered before D2"):
        phase1.validate_data_configs()
