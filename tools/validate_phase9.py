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

from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map
from trading_system.models.readiness import load_training_policy
from trading_system.research.offline_dry_run import build_local_csv_research_dry_run


def main() -> None:
    fixture_csv = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
    metadata_path = ROOT / "configs/data/local-csv-onboarding-template.yaml"
    dry_run = build_local_csv_research_dry_run(
        fixture_csv,
        yaml.safe_load(metadata_path.read_text(encoding="utf-8")),
        load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
        load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
        load_training_policy(ROOT / "configs/models/baseline-training-policy.yaml"),
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )
    validate_json_payload(ROOT / "schemas/offline_research_run.schema.json", dry_run.to_payload())

    cli_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/run_local_csv_dry_run.py"),
            "--csv",
            str(fixture_csv),
            "--metadata",
            str(metadata_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    validate_json_payload(ROOT / "schemas/offline_research_run.schema.json", json.loads(cli_result.stdout))
    print("Phase 9 artifacts validated")


if __name__ == "__main__":
    main()
