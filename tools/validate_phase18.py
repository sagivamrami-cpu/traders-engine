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

from trading_system.data_foundation.manifests import load_json
from trading_system.research.real_source_onboarding import build_real_source_onboarding_preflight

CREATED_AT = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
SCHEMA_PATH = ROOT / "schemas/real_source_onboarding_preflight.schema.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _valid_csv_copy(path: Path) -> Path:
    invalid_row = "SPY,2026-08-28T09:35:00,451.50,450.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05"
    valid_row = "SPY,2026-08-28T09:35:00,451.50,451.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05"
    path.write_text(FIXTURE_CSV.read_text(encoding="utf-8").replace(invalid_row, valid_row), encoding="utf-8")
    return path


def _validate(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def _assert_redacted(serialized: str, *forbidden_paths: Path) -> None:
    for path in forbidden_paths:
        _require(str(path) not in serialized, f"output must not include local path {path.name}")
    _require("C:\\" not in serialized, "output must not include Windows absolute paths")
    _require("/Users/" not in serialized, "output must not include user absolute paths")


def _run_cli(csv_path: Path) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/preflight_real_source_onboarding.py"),
            "--csv",
            str(csv_path),
            "--metadata",
            str(ROOT / "configs/data/real-ohlcv-source-metadata-template.yaml"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    _assert_redacted(result.stdout, csv_path, ROOT / "configs/data/real-ohlcv-source-metadata-template.yaml")
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
    subprocess.run(
        [sys.executable, str(ROOT / "tools/validate_phase17.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/data_foundation/test_csv_onboarding.py",
            "tests/research/test_source_bundle.py",
            "tests/research/test_real_source_onboarding_preflight.py",
            "-q",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = _valid_csv_copy(Path(tmpdir) / "valid.csv")
        payload = build_real_source_onboarding_preflight(
            csv_path,
            ROOT / "configs/data/real-ohlcv-source-metadata-template.yaml",
            None,
            created_at=CREATED_AT,
        ).to_payload()
        _validate(payload)
        _require(payload["status"] == "BLOCKED", "default preflight must be blocked")
        _assert_redacted(json.dumps(payload, sort_keys=True), csv_path)

        cli_payload = _run_cli(csv_path)
        _validate(cli_payload)
        _require(cli_payload["status"] == "BLOCKED", "default CLI preflight must be blocked")

    _assert_readiness_blocked()
    print("Phase 18 artifacts validated")


if __name__ == "__main__":
    main()
