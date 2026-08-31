from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.csv_inspection import inspect_local_ohlcv_csv
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map


def metadata_inputs() -> dict[str, str]:
    return {
        "source_id": "local-csv-ohlcv-spy",
        "canonical_symbol": "TR_FIXTURE_SPY",
        "asset_class": "EQUITY_ETF",
        "venue": "LOCAL_CSV",
        "timeframe": "1m",
        "session_calendar_id": "us-equities-regular-v1",
        "owner": "Human Data Owner",
    }


def main() -> None:
    fixture_csv = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
    with tempfile.TemporaryDirectory() as temp_dir:
        valid_csv = Path(temp_dir) / "valid-ohlcv.csv"
        valid_csv.write_text(
            fixture_csv.read_text(encoding="utf-8").replace(
                "SPY,2026-08-28T09:35:00,451.50,450.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05",
                "SPY,2026-08-28T09:35:00,451.50,451.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05",
            ),
            encoding="utf-8",
        )
        validate_phase13(valid_csv)
    print("Phase 13 artifacts validated")


def validate_phase13(fixture_csv: Path) -> None:
    schema_path = ROOT / "schemas/local_csv_inspection_report.schema.json"
    report = inspect_local_ohlcv_csv(
        fixture_csv,
        metadata_inputs(),
        load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
        load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )
    payload = report.to_payload()
    validate_json_payload(schema_path, payload)
    if payload["status"] != "SHAPE_VALIDATED_NEEDS_BUNDLE_VALIDATION":
        raise ValueError("inspection must stop at shape validation before bundle validation")
    if payload["suggested_metadata"]["source_status"] != "OPEN_HUMAN_DECISION":
        raise ValueError("suggested metadata must remain unapproved")

    cli_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/inspect_local_ohlcv_csv.py"),
            "--csv",
            str(fixture_csv),
            "--source-id",
            "local-csv-ohlcv-spy",
            "--canonical-symbol",
            "TR_FIXTURE_SPY",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    validate_json_payload(schema_path, json.loads(cli_result.stdout))


if __name__ == "__main__":
    main()
