import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.research.intake_packet import build_real_ohlcv_intake_packet

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
METADATA_PATH = ROOT / "configs/data/local-csv-onboarding-template.yaml"


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
    schema = json.loads((ROOT / "schemas/real_ohlcv_intake_packet.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def packet(csv_path: Path):
    return build_real_ohlcv_intake_packet(
        csv_path,
        METADATA_PATH,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    ).to_payload()


def test_intake_packet_payload_validates_against_schema(tmp_path: Path):
    payload = packet(valid_csv(tmp_path / "valid.csv"))

    validate_payload(payload)
    assert payload["packet_version"] == "real-ohlcv-intake-packet-0.1.0"
    assert payload["status"] == "BLOCKED_INVALID_INPUT"
    assert payload["source_identity"]["status"] == "FIXTURE_ONLY"


def test_intake_packet_never_outputs_local_csv_path(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")
    payload = packet(csv_path)

    serialized = json.dumps(payload, sort_keys=True)
    assert str(csv_path) not in serialized
    assert "C:\\" not in serialized
    assert "/Users/" not in serialized
    assert payload["csv_path"] == "LOCAL_PATH_REDACTED"
    assert payload["inspection"]["csv_path"] == "LOCAL_PATH_REDACTED"


def test_intake_packet_does_not_mark_source_approved(tmp_path: Path):
    payload = packet(valid_csv(tmp_path / "valid.csv"))

    assert payload["production_allowed"] is False
    assert "BUILD_PRODUCTION_TRAINING_DATASET" in payload["blocked_actions"]
    assert payload["source_identity"]["production_allowed"] is False
    assert set(payload["blocked_actions"]) == {
        "BUILD_PRODUCTION_TRAINING_DATASET",
        "TRAIN_PRODUCTION_MODEL",
        "MODEL_PROMOTION",
        "LIVE_TRADING",
        "BROKER_EXECUTION",
        "CAPITAL_ALLOCATION",
    }
    assert set(payload["required_decision_records"]) == {
        "REAL_HISTORICAL_OHLCV_CSV",
        "PRODUCTION_OHLCV_VENDOR_DECISION",
        "FIRST_REAL_SYMBOL",
        "FIRST_HISTORICAL_INTERVAL",
        "RAW_DATA_STORAGE_LICENSE_APPROVAL",
        "ORDER_FLOW_SOURCE_DECISION",
        "OPTIONS_SOURCE_DECISION",
    }


def test_intake_packet_inspection_id_is_redacted_path_derived(tmp_path: Path):
    payload_one = packet(valid_csv(tmp_path / "one.csv"))
    payload_two = packet(valid_csv(tmp_path / "two.csv"))

    assert payload_one["inspection"]["inspection_id"] == payload_two["inspection"]["inspection_id"]


def test_prepare_real_ohlcv_intake_cli_failure_does_not_leak_path(tmp_path: Path):
    missing_csv = tmp_path / "missing.csv"

    result = subprocess.run(
        [
            sys.executable,
            "tools/prepare_real_ohlcv_intake.py",
            "--csv",
            str(missing_csv),
            "--metadata",
            str(METADATA_PATH),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert str(missing_csv) not in result.stdout
    assert str(missing_csv) not in result.stderr
    assert "C:\\" not in result.stderr
    assert "/Users/" not in result.stderr


def test_invalid_csv_intake_packet_is_blocked_without_leaking_path():
    payload = packet(FIXTURE_CSV)
    serialized = json.dumps(payload, sort_keys=True)

    validate_payload(payload)
    assert payload["status"] == "BLOCKED_INVALID_INPUT"
    assert "INVALID_OHLC" in payload["blocked_reasons"]
    assert str(FIXTURE_CSV) not in serialized


def test_prepare_real_ohlcv_intake_cli_outputs_redacted_schema_valid_json(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")

    result = subprocess.run(
        [
            sys.executable,
            "tools/prepare_real_ohlcv_intake.py",
            "--csv",
            str(csv_path),
            "--metadata",
            str(METADATA_PATH),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_payload(payload)
    assert payload["csv_path"] == "LOCAL_PATH_REDACTED"
    assert str(csv_path) not in result.stdout
    assert "C:\\" not in result.stdout


def test_human_templates_make_approval_boundary_explicit():
    metadata_template = (ROOT / "configs/data/real-ohlcv-source-metadata-template.yaml").read_text(encoding="utf-8")
    decision_template = (ROOT / "agent-exchange/templates/human-decision-record.md").read_text(encoding="utf-8")

    assert "UNSET_REAL_SOURCE_ID" in metadata_template
    assert "human_decision_ref: UNSET_HUMAN_DECISION_RECORD_PATH" in metadata_template
    assert "This template is not an approval record." in decision_template
    for field in ("Approver:", "Created at:", "Scope:", "Decision:", "Evidence:"):
        assert field in decision_template
