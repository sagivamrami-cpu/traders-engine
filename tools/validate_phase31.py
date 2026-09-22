from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

STRATEGY_SCHEMA_PATH = ROOT / "schemas/gc_session_calendar_source_strategy.schema.json"
OBSERVED_SCHEMA_PATH = ROOT / "schemas/gc_observed_activity_calendar_profile.schema.json"
STRATEGY_PATH = ROOT / "configs/data/gc-session-calendar-source-strategy.yaml"
SESSION_CALENDAR_PATH = ROOT / "configs/data/session-calendar.yaml"
PENDING_GC_METALS_CALENDAR_ID = "cme-globex-metals-research-pending-v1"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def assert_pending_gc_metals_calendar_absent(calendar_path: Path) -> None:
    calendar = yaml.safe_load(calendar_path.read_text(encoding="utf-8"))
    calendar_ids = set((calendar or {}).get("calendars", {}))
    if PENDING_GC_METALS_CALENDAR_ID in calendar_ids:
        raise ValueError("pending GC metals calendar cannot be registered before D2 implementation")


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, engine="pyarrow")
    return buffer.getvalue()


def _write_activity_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "gc_activity_validator.zip"
    index = pd.DatetimeIndex(
        pd.to_datetime(
            [
                "2020-01-01T00:00:00Z",
                "2020-01-01T00:00:01Z",
                "2020-01-01T00:30:00Z",
            ]
        ),
        name="ts_event",
    )
    frame = pd.DataFrame(
        {
            "gc_open": [1.0, 1.0, 1.0],
            "gc_high": [1.0, 1.0, 1.0],
            "gc_low": [1.0, 1.0, 1.0],
            "gc_close": [1.0, 1.0, 1.0],
            "gc_volume": [1.0, 1.0, 1.0],
        },
        index=index,
    )
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("gc_1s/gc_1s_2020-01.parquet", _parquet_bytes(frame))
    return zip_path


def main() -> None:
    assert_pending_gc_metals_calendar_absent(SESSION_CALENDAR_PATH)
    _run([sys.executable, str(ROOT / "tools/validate_phase28.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_session_calendar_source_strategy.py", "-q"])
    Draft202012Validator.check_schema(load_json(STRATEGY_SCHEMA_PATH))
    Draft202012Validator.check_schema(load_json(OBSERVED_SCHEMA_PATH))

    strategy_result = _run(
        [
            sys.executable,
            str(ROOT / "tools/validate_gc_session_calendar_source_strategy.py"),
            "--strategy",
            str(STRATEGY_PATH),
        ]
    )
    strategy = json.loads(strategy_result.stdout)
    validate_json_payload(STRATEGY_SCHEMA_PATH, strategy)
    _require(
        strategy["status"] == "SOURCE_STRATEGY_APPROVED_CALENDAR_IMPLEMENTATION_REQUIRED",
        "D2 source strategy must be approved but implementation-gated",
    )
    _require(strategy["calendar_registration_allowed"] is False, "calendar registration must remain blocked")
    _require(strategy["databento_status_leg"]["query_allowed"] is False, "Databento status query must remain blocked")
    _require(strategy["resampling_allowed"] is False, "resampling must remain blocked")
    _require(strategy["training_allowed"] is False, "training must remain blocked")
    for action in ("REGISTER_SESSION_CALENDAR", "QUERY_DATABENTO_STATUS_SCHEMA", "BUILD_REAL_DATASET"):
        _require(action in strategy["blocked_actions"], f"blocked action missing: {action}")

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = _write_activity_zip(Path(tmpdir))
        observed_result = _run(
            [
                sys.executable,
                str(ROOT / "tools/inspect_gc_observed_activity_calendar.py"),
                "--zip",
                str(zip_path),
                "--strategy",
                str(STRATEGY_PATH),
            ]
        )
        observed = json.loads(observed_result.stdout)
        validate_json_payload(OBSERVED_SCHEMA_PATH, observed)
        _require(
            observed["session_calendar_gate_status"] == "UNSATISFIED_OBSERVED_ACTIVITY_ONLY",
            "observed activity must not satisfy the session-calendar gate",
        )
        _require(observed["calendar_registration_allowed"] is False, "observed profile must not allow calendar registration")
        for forbidden in (str(zip_path), str(STRATEGY_PATH), "C:\\", "/Users/"):
            _require(forbidden not in observed_result.stdout, "observed profile output must not include local paths")
    for forbidden in (str(STRATEGY_PATH), "C:\\", "/Users/"):
        _require(forbidden not in strategy_result.stdout, "source strategy output must not include local paths")
    print("Phase 31 artifacts validated")


if __name__ == "__main__":
    main()
