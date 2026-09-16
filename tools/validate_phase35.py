from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

SCHEMA_PATH = ROOT / "schemas/gc_fine_observed_gap_profile.schema.json"
STRATEGY_PATH = ROOT / "configs/data/gc-session-calendar-source-strategy.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, engine="pyarrow")
    return buffer.getvalue()


def _write_gap_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "gc_gap_validator.zip"
    frame = pd.DataFrame(
        {"gc_close": [100.0, 100.1, 100.2]},
        index=pd.DatetimeIndex(
            pd.to_datetime(["2020-01-01T00:00:00Z", "2020-01-01T00:00:01Z", "2020-01-01T00:00:10Z"]),
            name="ts_event",
        ),
    )
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("gc_1s/gc_1s_2020-01.parquet", _parquet_bytes(frame))
    return zip_path


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase34.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_fine_observed_gap_profile.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = _write_gap_zip(Path(tmpdir))
        result = _run(
            [
                sys.executable,
                str(ROOT / "tools/inspect_gc_fine_observed_gap_profile.py"),
                "--zip",
                str(zip_path),
                "--strategy",
                str(STRATEGY_PATH),
                "--top-n-gaps",
                "2",
            ]
        )
        payload = json.loads(result.stdout)
        validate_json_payload(SCHEMA_PATH, payload)
        _require(
            payload["status"] == "FINE_OBSERVED_GAP_PROFILE_READY_SESSION_CALENDAR_UNSATISFIED",
            "fine observed gap profile must remain calendar-unsatisfied",
        )
        _require(payload["timestamp_column_only"] is True, "profile must read timestamp column only")
        _require(payload["expected_cadence_seconds"] == 1, "profile must declare 1s expected cadence")
        _require(payload["largest_gap_seconds"] == 9, "expected validator gap not reported")
        _require(
            payload["periods"][0]["timestamp_order_status"] == "ALREADY_MONOTONIC",
            "profile must report timestamp ordering",
        )
        _require(payload["calendar_registration_allowed"] is False, "calendar registration must remain blocked")
        _require(payload["dataset_construction_allowed"] is False, "dataset construction must remain blocked")
        _require(payload["resampling_allowed"] is False, "resampling must remain blocked")
        _require(payload["training_allowed"] is False, "training must remain blocked")
        for forbidden in (str(zip_path), str(STRATEGY_PATH), "C:\\", "/Users/"):
            _require(forbidden not in result.stdout, "fine gap profile output must not include local paths")
    print("Phase 35 artifacts validated")


if __name__ == "__main__":
    main()
