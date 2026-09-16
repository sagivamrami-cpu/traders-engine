from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json, validate_json_payload

SCHEMA_PATH = ROOT / "schemas/databento_gc_order_flow_profile.schema.json"
METADATA_PATH = ROOT / "configs/data/databento-gc-order-flow-source-metadata.yaml"
GATES_PATH = ROOT / "configs/data/gc-order-flow-quality-gates.yaml"
DECISIONS_PATH = ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=check)


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, engine="pyarrow")
    return buffer.getvalue()


def _write_order_flow_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "gc_order_flow_validator.zip"
    index = pd.DatetimeIndex(pd.to_datetime(["2020-01-01T00:00:00Z"]), name="minute")
    of_frame = pd.DataFrame({"volume": [1], "delta": [1], "trades": [1], "cvd": [1]}, index=index)
    ohlcv_frame = pd.DataFrame(
        {"open": [1.0], "high": [2.0], "low": [0.5], "close": [1.5], "volume": [1]},
        index=index,
    )
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("gc/README.md", "# GC order flow\n")
        archive.writestr("gc/GCall_of_1m.parquet", _parquet_bytes(of_frame))
        archive.writestr("gc/GCall_ohlcv_1m.parquet", _parquet_bytes(ohlcv_frame))
        archive.writestr("gc/ticks/GC_trades_2020-01-01.dbn.zst", b"fake")
    return zip_path


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase21.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_databento_gc_order_flow_profile.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))

    readiness_result = _run(
        [
            sys.executable,
            str(ROOT / "tools/real_data_readiness.py"),
            "--decisions",
            str(DECISIONS_PATH),
        ]
    )
    readiness = json.loads(readiness_result.stdout)
    _require(readiness["status"] == "BLOCKED", "real-data readiness must remain blocked")
    _require(readiness["satisfied_count"] == 6, "readiness must satisfy exactly six items")
    _require(readiness["open_count"] == 1, "only options readiness item must remain open/deferred")
    open_items = {
        item["item_id"]
        for item in readiness["required_items"]
        if item["status"] == "OPEN_HUMAN_DECISION"
    }
    _require("ORDER_FLOW_SOURCE_DECISION" not in open_items, "order-flow source decision must be approved")
    _require("OPTIONS_SOURCE_DECISION" in open_items, "options source decision must remain open/deferred")

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = _write_order_flow_zip(Path(tmpdir))
        result = _run(
            [
                sys.executable,
                str(ROOT / "tools/inspect_databento_gc_order_flow_zip.py"),
                "--zip",
                str(zip_path),
                "--metadata",
                str(METADATA_PATH),
                "--gates",
                str(GATES_PATH),
                "--decisions",
                str(DECISIONS_PATH),
            ]
        )
        payload = json.loads(result.stdout)
        validate_json_payload(SCHEMA_PATH, payload)
        _require(
            payload["status"] == "ORDER_FLOW_PROFILE_SAMPLED_SOURCE_BLOCKED",
            "temporary order-flow profile must stay sampled-source blocked",
        )
        _require(
            payload["timeframe_status"] == "BASELINE_APPROVED_V1_NOT_MODEL_FINAL",
            "order-flow profile must reflect D1 baseline approval without model finality",
        )
        _require(
            payload["first_baseline_candidate"] == "30m_UTC_FIXED_BASELINE_APPROVED_V1",
            "order-flow baseline candidate must match D1-approved value",
        )
        _require(payload["training_allowed"] is False, "order-flow profile must not allow training")
        _require(payload["allowed_next_actions"] == [], "order-flow profile must not advertise next actions")
        for forbidden in (str(zip_path), str(METADATA_PATH), str(GATES_PATH), str(DECISIONS_PATH), "C:\\", "/Users/"):
            _require(forbidden not in result.stdout, "order-flow CLI output must not include local paths")

    print("Phase 23 artifacts validated")


if __name__ == "__main__":
    main()
