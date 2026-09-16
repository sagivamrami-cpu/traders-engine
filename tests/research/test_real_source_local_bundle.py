import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

from trading_system.data_foundation.csv_onboarding import CsvOnboardingError, build_raw_source_manifest_for_csv
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map
from trading_system.research.real_source_local_bundle import build_real_source_local_bundle
from trading_system.research.source_bundle import validate_local_source_bundle

ROOT = Path(__file__).resolve().parents[2]
CREATED_AT = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"


def valid_csv(path: Path) -> Path:
    path.write_text(
        FIXTURE_CSV.read_text(encoding="utf-8").replace(
            "SPY,2026-08-28T09:35:00,451.50,450.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05",
            "SPY,2026-08-28T09:35:00,451.50,451.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05",
        ),
        encoding="utf-8",
    )
    return path


def write_record(path: Path, *, decision: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "Approver: Human Data Owner",
                "Created at: 2026-08-31T21:00:00Z",
                "Scope: Phase 19 local-only real-source bundle test",
                f"Decision: {decision}",
                "Evidence: Temporary test record; not production approval",
            ]
        ),
        encoding="utf-8",
    )


def write_real_source_project(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    project_root = tmp_path / "project"
    (project_root / "configs/data").mkdir(parents=True)
    (project_root / "configs/research").mkdir(parents=True)
    shutil.copyfile(ROOT / "configs/data/normalization-policy.yaml", project_root / "configs/data/normalization-policy.yaml")
    shutil.copyfile(ROOT / "configs/data/source-identity-policy.yaml", project_root / "configs/data/source-identity-policy.yaml")
    shutil.copyfile(ROOT / "configs/data/raw-data-retention-policy.yaml", project_root / "configs/data/raw-data-retention-policy.yaml")
    shutil.copyfile(ROOT / "configs/research/real-data-readiness-checklist.yaml", project_root / "configs/research/real-data-readiness-checklist.yaml")
    (project_root / "configs/data/symbol-map.yaml").write_text(
        "\n".join(
            [
                "version: symbol-map-0.1.0",
                "symbols:",
                "  - canonical_symbol: SPY.US",
                "    asset_class: EQUITY_ETF",
                "    venue: TEST_REAL_SOURCE",
                "    raw_symbols: [SPY]",
                "    contract_policy: not_applicable",
            ]
        ),
        encoding="utf-8",
    )
    write_record(project_root / "agent-exchange/decisions/source.md", decision="APPROVED")
    write_record(project_root / "agent-exchange/decisions/approved.md", decision="APPROVED")
    write_record(project_root / "agent-exchange/decisions/deferred.md", decision="DEFERRED")
    metadata = yaml.safe_load((ROOT / "configs/data/real-ohlcv-source-metadata-template.yaml").read_text(encoding="utf-8"))
    metadata.update(
        {
            "source_id": "real-ohlcv-spy-1m",
            "asset_class": "EQUITY_ETF",
            "venue": "TEST_REAL_SOURCE",
            "canonical_symbol": "SPY.US",
            "raw_symbol": "SPY",
            "timeframe": "1m",
            "timezone": "America/New_York",
            "session_calendar_id": "us-equities-regular-v1",
            "human_decision_ref": "agent-exchange/decisions/source.md",
        }
    )
    metadata_path = project_root / "configs/data/real-source.yaml"
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=True), encoding="utf-8")
    decisions_path = project_root / "agent-exchange/decisions/decisions.yaml"
    decisions_path.write_text(
        yaml.safe_dump(
            {
                "version": "real-data-decisions-0.1.0",
                "decisions": [
                    {
                        "item_id": item_id,
                        "decision": decision,
                        "approver": "Human Data Owner",
                        "decided_at": "2026-08-31T21:00:00Z",
                        "scope": "Phase 19 local-only bundle test",
                        "evidence": [f"agent-exchange/decisions/{decision.lower()}.md"],
                    }
                    for item_id, decision in {
                        "REAL_HISTORICAL_OHLCV_CSV": "APPROVED",
                        "PRODUCTION_OHLCV_VENDOR_DECISION": "APPROVED",
                        "FIRST_REAL_SYMBOL": "APPROVED",
                        "FIRST_HISTORICAL_INTERVAL": "APPROVED",
                        "RAW_DATA_STORAGE_LICENSE_APPROVAL": "APPROVED",
                        "ORDER_FLOW_SOURCE_DECISION": "DEFERRED",
                        "OPTIONS_SOURCE_DECISION": "DEFERRED",
                    }.items()
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return (
        project_root,
        metadata_path,
        decisions_path,
        project_root / "configs/data/raw-data-retention-policy.yaml",
    )


def validate_payload(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/real_source_local_bundle.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_real_source_local_bundle_blocks_without_accepted_preflight(tmp_path: Path):
    payload = build_real_source_local_bundle(
        valid_csv(tmp_path / "valid.csv"),
        ROOT / "configs/data/real-ohlcv-source-metadata-template.yaml",
        None,
        ROOT / "configs/data/raw-data-retention-policy.yaml",
        created_at=CREATED_AT,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert payload["production_allowed"] is False
    assert payload["local_manifest"] is None
    assert payload["dry_run_summary"] is None
    assert payload["allowed_next_actions"] == []
    assert "PREFLIGHT_NOT_RECORDS_PRESENT" in payload["blocked_reasons"]


def test_real_source_local_bundle_blocks_fixture_identity_with_schema_valid_payload(tmp_path: Path):
    payload = build_real_source_local_bundle(
        valid_csv(tmp_path / "valid.csv"),
        ROOT / "configs/data/local-csv-onboarding-template.yaml",
        None,
        ROOT / "configs/data/raw-data-retention-policy.yaml",
        created_at=CREATED_AT,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert payload["source_identity"]["status"] == "BLOCKED"
    assert "FIXTURE_SOURCE_NOT_ALLOWED" in payload["source_identity"]["blocked_reasons"]
    assert payload["local_manifest"] is None
    assert "PREFLIGHT_NOT_RECORDS_PRESENT" in payload["blocked_reasons"]


def test_real_source_local_bundle_prepares_redacted_manifest_only(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")
    project_root, metadata_path, decisions_path, retention_path = write_real_source_project(tmp_path)

    payload = build_real_source_local_bundle(
        csv_path,
        metadata_path,
        decisions_path,
        retention_path,
        created_at=CREATED_AT,
        project_root=project_root,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "LOCAL_MANIFEST_PREPARED_PRODUCTION_BLOCKED"
    assert payload["production_allowed"] is False
    assert payload["allowed_next_actions"] == []
    assert payload["dry_run_summary"] is None
    assert payload["local_manifest"]["raw_file"] == "LOCAL_PATH_REDACTED"
    assert payload["local_manifest"]["source_status"] == "OPEN_HUMAN_DECISION"
    assert payload["local_manifest"]["canonical_symbol"] == "SPY.US"
    assert payload["local_manifest"]["row_count"] > 0
    assert payload["retention_decision"]["retention_approved"] is False
    assert payload["retention_decision"]["status"] == "BLOCKED"
    assert payload["retention_decision"]["dry_run_output_allowed"] is False
    assert payload["retention_decision"]["manifest_output_allowed"] is True
    assert "BUILD_PRODUCTION_TRAINING_DATASET" in payload["blocked_actions"]
    assert "RUN_OFFLINE_DRY_RUN" in payload["blocked_actions"]
    assert "CLAIM_EDGE" in payload["blocked_actions"]
    assert "DEPLOYMENT" in payload["blocked_actions"]
    assert "COPY_RAW_CSV" in payload["blocked_actions"]
    assert "MUTATE_RAW_CSV" in payload["blocked_actions"]
    assert "UPLOAD_RAW_CSV" in payload["blocked_actions"]
    assert "RAW_RETENTION_REQUIRES_HUMAN_APPROVAL" in payload["blocked_reasons"]


def test_real_source_local_bundle_schema_requires_claim_edge_block():
    schema = (ROOT / "schemas/real_source_local_bundle.schema.json").read_text(encoding="utf-8")

    assert '{"contains": {"const": "CLAIM_EDGE"}}' in schema


def test_real_source_local_bundle_output_never_leaks_paths(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")
    project_root, metadata_path, decisions_path, retention_path = write_real_source_project(tmp_path)

    payload = build_real_source_local_bundle(
        csv_path,
        metadata_path,
        decisions_path,
        retention_path,
        created_at=CREATED_AT,
        project_root=project_root,
    ).to_payload()
    serialized = json.dumps(payload, sort_keys=True)

    assert str(csv_path) not in serialized
    assert str(metadata_path) not in serialized
    assert str(decisions_path) not in serialized
    assert str(retention_path) not in serialized
    assert "Human Data Owner" not in serialized
    assert "APPROVED" not in serialized
    assert "DEFERRED" not in serialized
    assert "C:\\" not in serialized
    assert "/Users/" not in serialized


def test_real_source_local_bundle_schema_rejects_nested_preflight_details(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")
    project_root, metadata_path, decisions_path, retention_path = write_real_source_project(tmp_path)
    payload = build_real_source_local_bundle(
        csv_path,
        metadata_path,
        decisions_path,
        retention_path,
        created_at=CREATED_AT,
        project_root=project_root,
    ).to_payload()
    payload["preflight"]["intake_packet"] = {
        "owner": "Human Data Owner",
        "decision": "APPROVED",
        "csv_path": "C:\\unsafe.csv",
    }

    with pytest.raises(ValidationError):
        validate_payload(payload)


def test_real_source_still_cannot_enter_fixture_onboard_or_bundle(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")
    project_root, metadata_path, _decisions_path, retention_path = write_real_source_project(tmp_path)
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))

    with pytest.raises(CsvOnboardingError, match="REAL_SOURCE_ONBOARDING_PREFLIGHT_REQUIRED"):
        build_raw_source_manifest_for_csv(
            csv_path,
            metadata,
            load_normalization_policy(project_root / "configs/data/normalization-policy.yaml"),
            load_symbol_map(project_root / "configs/data/symbol-map.yaml"),
            ingested_at=CREATED_AT,
            project_root=project_root,
        )

    bundle = validate_local_source_bundle(
        csv_path,
        metadata_path,
        retention_path,
        created_at=CREATED_AT,
        project_root=project_root,
    ).to_payload()
    assert bundle["status"] == "BLOCKED"
    assert bundle["dry_run_summary"] is None
    assert "REAL_SOURCE_ONBOARDING_PREFLIGHT_REQUIRED" in bundle["blocked_reasons"]


def test_real_source_local_bundle_cli_outputs_redacted_json(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")

    result = subprocess.run(
        [
            sys.executable,
            "tools/prepare_real_source_local_bundle.py",
            "--csv",
            str(csv_path),
            "--metadata",
            "configs/data/real-ohlcv-source-metadata-template.yaml",
            "--retention-policy",
            "configs/data/raw-data-retention-policy.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert "LOCAL_PATH_REDACTED" in result.stdout
    assert str(tmp_path) not in result.stdout


def test_real_source_local_bundle_cli_covers_prepared_path_without_leaks(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")
    project_root, metadata_path, decisions_path, retention_path = write_real_source_project(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "tools/prepare_real_source_local_bundle.py",
            "--csv",
            str(csv_path),
            "--metadata",
            str(metadata_path),
            "--decisions",
            str(decisions_path),
            "--retention-policy",
            str(retention_path),
            "--project-root",
            str(project_root),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_payload(payload)
    assert payload["status"] == "LOCAL_MANIFEST_PREPARED_PRODUCTION_BLOCKED"
    assert payload["retention_decision"]["status"] == "BLOCKED"
    assert payload["dry_run_summary"] is None
    assert str(csv_path) not in result.stdout
    assert str(metadata_path) not in result.stdout
    assert str(decisions_path) not in result.stdout
    assert str(retention_path) not in result.stdout
    assert str(project_root) not in result.stdout
    assert "Human Data Owner" not in result.stdout
    assert "APPROVED" not in result.stdout
    assert "DEFERRED" not in result.stdout
