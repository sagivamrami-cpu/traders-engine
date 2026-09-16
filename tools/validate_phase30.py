from __future__ import annotations

import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json

SCHEMA_PATH = ROOT / "schemas/gc_timestamp_evidence_report.schema.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def _fixture_zip(path: Path) -> Path:
    aware = pd.DataFrame(
        {
            "gc_open": [1.0],
            "gc_high": [1.0],
            "gc_low": [1.0],
            "gc_close": [1.0],
            "gc_volume": [1.0],
            "ts_event": pd.to_datetime(["2026-01-01T00:00:00Z"]),
        }
    )
    naive = pd.DataFrame(
        {
            "volume": [1.0],
            "delta": [0.0],
            "trades": [1],
            "minute": pd.to_datetime(["2026-01-01T00:00:00"]),
        }
    )
    aware_buffer = io.BytesIO()
    naive_buffer = io.BytesIO()
    aware.to_parquet(aware_buffer, engine="pyarrow")
    naive.to_parquet(naive_buffer, engine="pyarrow")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("gc_1s/gc_1s_2026-01.parquet", aware_buffer.getvalue())
        archive.writestr("gc/GCext_of_1m.parquet", naive_buffer.getvalue())
        archive.writestr(
            "gc/README.md",
            "The naive timestamps are UTC wall-clock. Jan-May 2017 is damaged missing data.",
        )
    return path


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase29.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_timestamp_evidence.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))
    fixture = _fixture_zip(ROOT / ".tmp-phase30-timestamp-fixture.zip")
    try:
        result = _run(
            [
                sys.executable,
                str(ROOT / "tools/inspect_gc_timestamp_evidence.py"),
                "--ohlcv-zip",
                str(fixture),
                "--order-flow-zip",
                str(fixture),
            ]
        )
    finally:
        fixture.unlink(missing_ok=True)
    payload = json.loads(result.stdout)
    _require(
        payload["status"] == "EVIDENCE_COLLECTED_NEEDS_HUMAN_DECISION",
        "timestamp evidence must remain human-decision gated",
    )
    _require(payload["dataset_construction_allowed"] is False, "dataset construction must remain blocked")
    _require(payload["resampling_allowed"] is False, "resampling must remain blocked")
    _require(payload["training_allowed"] is False, "training must remain blocked")
    _require(
        payload["evidence_summary"]["timestamp_role_gate_status"] == "UNSATISFIED_EVIDENCE_ONLY",
        "timestamp role gate must remain unsatisfied",
    )
    for decision in (
        "D3_CONFIRM_OHLCV_TS_EVENT_START_OR_REJECT",
        "D3_CONFIRM_ORDER_FLOW_MINUTE_START_AND_UTC_LOCALIZATION_OR_REJECT",
    ):
        _require(decision in payload["required_human_decisions"], f"human decision missing: {decision}")
    for action in ("RESAMPLE_REAL_BARS", "JOIN_ORDER_FLOW_TO_OHLCV", "BUILD_REAL_DATASET"):
        _require(action in payload["blocked_actions"], f"blocked action missing: {action}")
    for forbidden in (str(fixture), "C:\\", "/Users/"):
        _require(forbidden not in result.stdout, "timestamp evidence output must not include local paths")
    print("Phase 30 artifacts validated")


if __name__ == "__main__":
    main()
