from pathlib import Path

import yaml

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
