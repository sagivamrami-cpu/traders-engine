import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from trading_system.research.real_source_onboarding import build_real_source_onboarding_preflight

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
CREATED_AT = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)


def valid_csv(path: Path) -> Path:
    path.write_text(
        FIXTURE_CSV.read_text(encoding="utf-8").replace(
            "SPY,2026-08-28T09:35:00,451.50,450.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05",
            "SPY,2026-08-28T09:35:00,451.50,451.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05",
        ),
        encoding="utf-8",
    )
    return path


def validate_payload(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/real_source_onboarding_preflight.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def write_record(path: Path, *, decision: str = "APPROVED") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "Approver: Human Data Owner",
                "Created at: 2026-08-31T20:00:00Z",
                "Scope: Phase 18 preflight test only",
                f"Decision: {decision}",
                "Evidence: Temporary test record; not production approval",
            ]
        ),
        encoding="utf-8",
    )


def write_real_source_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    project_root = tmp_path / "project"
    (project_root / "configs/data").mkdir(parents=True)
    (project_root / "configs/research").mkdir(parents=True)
    shutil.copyfile(
        ROOT / "configs/data/normalization-policy.yaml",
        project_root / "configs/data/normalization-policy.yaml",
    )
    shutil.copyfile(
        ROOT / "configs/data/source-identity-policy.yaml",
        project_root / "configs/data/source-identity-policy.yaml",
    )
    shutil.copyfile(
        ROOT / "configs/research/real-data-readiness-checklist.yaml",
        project_root / "configs/research/real-data-readiness-checklist.yaml",
    )
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
    write_record(project_root / "agent-exchange/decisions/source.md")
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
    decision_items = {
        "REAL_HISTORICAL_OHLCV_CSV": "APPROVED",
        "PRODUCTION_OHLCV_VENDOR_DECISION": "APPROVED",
        "FIRST_REAL_SYMBOL": "APPROVED",
        "FIRST_HISTORICAL_INTERVAL": "APPROVED",
        "RAW_DATA_STORAGE_LICENSE_APPROVAL": "APPROVED",
        "ORDER_FLOW_SOURCE_DECISION": "DEFERRED",
        "OPTIONS_SOURCE_DECISION": "DEFERRED",
    }
    decisions_path.write_text(
        yaml.safe_dump(
            {
                "version": "real-data-decisions-0.1.0",
                "decisions": [
                    {
                        "item_id": item_id,
                        "decision": decision,
                        "approver": "Human Data Owner",
                        "decided_at": "2026-08-31T20:00:00Z",
                        "scope": "Phase 18 preflight test only",
                        "evidence": [f"agent-exchange/decisions/{decision.lower()}.md"],
                    }
                    for item_id, decision in decision_items.items()
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    write_record(project_root / "agent-exchange/decisions/approved.md", decision="APPROVED")
    write_record(project_root / "agent-exchange/decisions/deferred.md", decision="DEFERRED")
    return project_root, metadata_path, decisions_path


def test_preflight_blocks_without_decision_file(tmp_path: Path):
    payload = build_real_source_onboarding_preflight(
        valid_csv(tmp_path / "valid.csv"),
        ROOT / "configs/data/real-ohlcv-source-metadata-template.yaml",
        None,
        created_at=CREATED_AT,
    ).to_payload()

    validate_payload(payload)
    assert payload["preflight_version"] == "real-source-onboarding-preflight-0.1.0"
    assert payload["status"] == "BLOCKED"
    assert payload["production_allowed"] is False
    assert payload["csv_path"] == "LOCAL_PATH_REDACTED"
    assert "MISSING_DECISIONS_FILE" in payload["blocked_reasons"]


def test_preflight_records_present_keeps_production_and_onboarding_blocked(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")
    project_root, metadata_path, decisions_path = write_real_source_fixture(tmp_path)

    payload = build_real_source_onboarding_preflight(
        csv_path,
        metadata_path,
        decisions_path,
        created_at=CREATED_AT,
        project_root=project_root,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "PREFLIGHT_RECORDS_PRESENT_PRODUCTION_BLOCKED"
    assert payload["production_allowed"] is False
    assert payload["allowed_next_actions"] == []
    assert "BUILD_PRODUCTION_TRAINING_DATASET" in payload["blocked_actions"]
    assert payload["readiness"]["status"] == "BLOCKED"


def test_preflight_output_never_leaks_local_paths(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")
    project_root, metadata_path, decisions_path = write_real_source_fixture(tmp_path)

    payload = build_real_source_onboarding_preflight(
        csv_path,
        metadata_path,
        decisions_path,
        created_at=CREATED_AT,
        project_root=project_root,
    ).to_payload()
    serialized = json.dumps(payload, sort_keys=True)

    assert str(csv_path) not in serialized
    assert str(metadata_path) not in serialized
    assert str(decisions_path) not in serialized
    assert "C:\\" not in serialized
    assert "/Users/" not in serialized


def test_preflight_redacts_nested_readiness_decision_details(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")
    project_root, metadata_path, decisions_path = write_real_source_fixture(tmp_path)
    decisions = yaml.safe_load(decisions_path.read_text(encoding="utf-8"))
    for entry in decisions["decisions"]:
        if entry["item_id"] == "OPTIONS_SOURCE_DECISION":
            entry["decision"] = "NOT_APPROVED"
            entry["scope"] = f"Private local scope {tmp_path}"
            entry["evidence"] = [f"{tmp_path}\\private-evidence.md"]
    decisions_path.write_text(yaml.safe_dump(decisions, sort_keys=True), encoding="utf-8")

    payload = build_real_source_onboarding_preflight(
        csv_path,
        metadata_path,
        decisions_path,
        created_at=CREATED_AT,
        project_root=project_root,
    ).to_payload()
    serialized = json.dumps(payload, sort_keys=True)

    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert "Private local scope" not in serialized
    assert "private-evidence" not in serialized
    assert str(tmp_path) not in serialized
    assert "HUMAN_DECISION_SCOPE_REDACTED" in serialized
    assert "HUMAN_DECISION_EVIDENCE_REDACTED" in serialized


def test_preflight_cli_outputs_redacted_blocked_json(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")

    result = subprocess.run(
        [
            sys.executable,
            "tools/preflight_real_source_onboarding.py",
            "--csv",
            str(csv_path),
            "--metadata",
            "configs/data/real-ohlcv-source-metadata-template.yaml",
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
