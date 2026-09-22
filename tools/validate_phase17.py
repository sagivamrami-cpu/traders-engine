from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload
from trading_system.research.intake_packet import build_real_ohlcv_intake_packet

CREATED_AT = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
METADATA_PATH = ROOT / "configs/data/local-csv-onboarding-template.yaml"
SCHEMA_PATH = ROOT / "schemas/real_ohlcv_intake_packet.schema.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _valid_csv_copy(path: Path) -> Path:
    invalid_row = "SPY,2026-08-28T09:35:00,451.50,450.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05"
    valid_row = "SPY,2026-08-28T09:35:00,451.50,451.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05"
    path.write_text(FIXTURE_CSV.read_text(encoding="utf-8").replace(invalid_row, valid_row), encoding="utf-8")
    return path


def _assert_redacted(payload: dict, forbidden_path: Path) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    _require(payload["csv_path"] == "LOCAL_PATH_REDACTED", "top-level csv path must be redacted")
    _require(payload["inspection"]["csv_path"] == "LOCAL_PATH_REDACTED", "inspection csv path must be redacted")
    _require(str(forbidden_path) not in serialized, "packet must not include the local CSV path")
    _require("C:\\" not in serialized, "packet must not include Windows absolute paths")
    _require("/Users/" not in serialized, "packet must not include user absolute paths")
    _require(
        "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv" not in serialized,
        "packet must not include fixture CSV path",
    )


def _validate_packet(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def _run_cli(csv_path: Path) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/prepare_real_ohlcv_intake.py"),
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
    _require(str(csv_path) not in result.stdout, "CLI output must not include the local CSV path")
    _require("C:\\" not in result.stdout, "CLI output must not include Windows absolute paths")
    return json.loads(result.stdout)


def _assert_readiness_blocked() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/real_data_readiness.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    report = json.loads(result.stdout)
    _require(report["status"] == "BLOCKED", "real data readiness must remain blocked")


def main() -> None:
    validate_json_payload(SCHEMA_PATH, build_real_ohlcv_intake_packet(FIXTURE_CSV, METADATA_PATH, created_at=CREATED_AT).to_payload())

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = _valid_csv_copy(Path(tmpdir) / "valid.csv")
        packet = build_real_ohlcv_intake_packet(csv_path, METADATA_PATH, created_at=CREATED_AT).to_payload()
        _validate_packet(packet)
        _require(packet["status"] == "BLOCKED_INVALID_INPUT", "fixture intake must not enter the human-decision lane")
        _require(packet["production_allowed"] is False, "intake packet must not approve production")
        _require(
            set(packet["blocked_actions"])
            == {
                "BUILD_PRODUCTION_TRAINING_DATASET",
                "TRAIN_PRODUCTION_MODEL",
                "MODEL_PROMOTION",
                "LIVE_TRADING",
                "BROKER_EXECUTION",
                "CAPITAL_ALLOCATION",
            },
            "intake packet must include the exact blocked action set",
        )
        _require(
            set(packet["required_decision_records"])
            == {
                "REAL_HISTORICAL_OHLCV_CSV",
                "PRODUCTION_OHLCV_VENDOR_DECISION",
                "FIRST_REAL_SYMBOL",
                "FIRST_HISTORICAL_INTERVAL",
                "RAW_DATA_STORAGE_LICENSE_APPROVAL",
                "ORDER_FLOW_SOURCE_DECISION",
                "OPTIONS_SOURCE_DECISION",
            },
            "intake packet must include the exact required decision record set",
        )
        _assert_redacted(packet, csv_path)

        cli_payload = _run_cli(csv_path)
        _validate_packet(cli_payload)
        _assert_redacted(cli_payload, csv_path)

    subprocess.run(
        [sys.executable, str(ROOT / "tools/validate_phase16.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    _assert_readiness_blocked()

    print("Phase 17 artifacts validated")


if __name__ == "__main__":
    main()
