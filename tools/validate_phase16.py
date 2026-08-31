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
from trading_system.data_foundation.source_identity import (
    load_source_identity_policy,
    validate_source_identity,
)
from trading_system.research.source_bundle import validate_local_source_bundle

CREATED_AT = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _metadata() -> dict:
    return yaml.safe_load((ROOT / "configs/data/local-csv-onboarding-template.yaml").read_text(encoding="utf-8"))


def main() -> None:
    policy_path = ROOT / "configs/data/source-identity-policy.yaml"
    policy_payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    validate_json_payload(ROOT / "schemas/source_identity_policy.schema.json", policy_payload)
    policy = load_source_identity_policy(policy_path)

    fixture_identity = validate_source_identity(_metadata(), policy)
    _require(fixture_identity.status == "FIXTURE_ONLY", "fixture metadata must be fixture-only")
    _require(
        "PRODUCTION_DATASET_CONSTRUCTION" in fixture_identity.blocked_actions,
        "fixture identity must block production dataset construction",
    )
    _require(fixture_identity.production_allowed is False, "fixture identity must not approve production")

    fixture_symbol_metadata = _metadata()
    fixture_symbol_metadata["source_id"] = "real-ohlcv-spy-1m"
    fixture_symbol_result = validate_source_identity(fixture_symbol_metadata, policy)
    _require(fixture_symbol_result.status == "BLOCKED", "real source with fixture symbol must be blocked")
    _require(
        "FIXTURE_SYMBOL_FORBIDDEN_FOR_REAL_SOURCE" in fixture_symbol_result.blocked_reasons,
        "real source with fixture symbol must report fixture symbol leakage",
    )

    missing_decision_metadata = _metadata()
    missing_decision_metadata["source_id"] = "real-ohlcv-spy-1m"
    missing_decision_metadata["canonical_symbol"] = "SPY.US"
    missing_decision_result = validate_source_identity(missing_decision_metadata, policy)
    _require(missing_decision_result.status == "BLOCKED", "real source without decision ref must be blocked")
    _require(
        "MISSING_HUMAN_DECISION_REF" in missing_decision_result.blocked_reasons,
        "real source without decision ref must report missing human decision ref",
    )

    pending_metadata = _metadata()
    pending_metadata["source_id"] = "real-ohlcv-spy-1m"
    pending_metadata["canonical_symbol"] = "SPY.US"
    pending_metadata["human_decision_ref"] = "agent-exchange/decisions/example.md"
    pending_result = validate_source_identity(pending_metadata, policy)
    _require(
        pending_result.status == "REAL_SOURCE_PENDING_HUMAN_DECISION",
        "real source with decision ref must remain pending human decision",
    )
    _require(pending_result.production_allowed is False, "decision ref alone must not approve production")

    bundle = validate_local_source_bundle(
        ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv",
        ROOT / "configs/data/local-csv-onboarding-template.yaml",
        ROOT / "configs/data/raw-data-retention-policy.yaml",
        created_at=CREATED_AT,
    ).to_payload()
    validate_json_payload(ROOT / "schemas/source_bundle_validation.schema.json", bundle)
    _require(bundle["source_identity"]["status"] == "FIXTURE_ONLY", "bundle must include fixture identity")
    _require(bundle["source_identity"]["production_allowed"] is False, "bundle identity must not approve production")

    subprocess.run(
        [sys.executable, str(ROOT / "tools/validate_phase15.py")],
        capture_output=True,
        text=True,
        check=True,
    )

    print("Phase 16 artifacts validated")


if __name__ == "__main__":
    main()
