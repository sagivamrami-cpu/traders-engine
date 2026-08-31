from __future__ import annotations

import json
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
from trading_system.data_foundation.storage_policy import (
    evaluate_raw_data_retention,
    load_raw_data_retention_policy,
)


def main() -> None:
    policy_path = ROOT / "configs/data/raw-data-retention-policy.yaml"
    schema_path = ROOT / "schemas/raw_data_retention_policy.schema.json"
    policy_payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    validate_json_payload(schema_path, policy_payload)

    metadata = yaml.safe_load((ROOT / "configs/data/local-csv-onboarding-template.yaml").read_text(encoding="utf-8"))
    manifest = build_raw_source_manifest_for_csv(
        ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv",
        metadata,
        load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
        load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
        ingested_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )
    decision = evaluate_raw_data_retention(load_raw_data_retention_policy(policy_path), manifest)
    payload = decision.to_payload()
    if payload["status"] != "MANIFEST_ONLY_ALLOWED":
        raise ValueError(json.dumps(payload, sort_keys=True))
    if payload["retention_approved"]:
        raise ValueError("raw data retention must remain unapproved")
    if payload["raw_copy_allowed"] or payload["raw_mutation_allowed"] or payload["network_upload_allowed"]:
        raise ValueError("raw data write, mutation, and upload actions must remain blocked")
    print("Phase 10 artifacts validated")


if __name__ == "__main__":
    main()
