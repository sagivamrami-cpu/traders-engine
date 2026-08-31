from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.research.source_bundle import validate_local_source_bundle


def main() -> None:
    fixture_csv = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
    metadata_path = ROOT / "configs/data/local-csv-onboarding-template.yaml"
    retention_policy_path = ROOT / "configs/data/raw-data-retention-policy.yaml"
    schema_path = ROOT / "schemas/source_bundle_validation.schema.json"

    validation = validate_local_source_bundle(
        fixture_csv,
        metadata_path,
        retention_policy_path,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )
    payload = validation.to_payload()
    validate_json_payload(schema_path, payload)
    if payload["status"] != "ACCEPTED_FOR_DRY_RUN":
        raise ValueError(json.dumps(payload, sort_keys=True))

    cli_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/validate_local_source_bundle.py"),
            "--csv",
            str(fixture_csv),
            "--metadata",
            str(metadata_path),
            "--retention-policy",
            str(retention_policy_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    validate_json_payload(schema_path, json.loads(cli_result.stdout))
    print("Phase 11 artifacts validated")


if __name__ == "__main__":
    main()
