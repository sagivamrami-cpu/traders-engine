from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.csv_onboarding import build_raw_source_manifest_for_csv
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map


def main() -> None:
    fixture_csv = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
    metadata_path = ROOT / "configs/data/local-csv-onboarding-template.yaml"
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    policy = load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml")
    symbol_map = load_symbol_map(ROOT / "configs/data/symbol-map.yaml")
    manifest = build_raw_source_manifest_for_csv(
        fixture_csv,
        metadata,
        policy,
        symbol_map,
        ingested_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )
    validate_json_payload(ROOT / "schemas/raw_source_manifest.schema.json", manifest)

    cli_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/onboard_ohlcv_csv.py"),
            "--csv",
            str(fixture_csv),
            "--metadata",
            str(metadata_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    validate_json_payload(ROOT / "schemas/raw_source_manifest.schema.json", json.loads(cli_result.stdout))
    print("Phase 8 artifacts validated")


if __name__ == "__main__":
    main()
