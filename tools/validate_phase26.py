from __future__ import annotations

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

SCHEMA_PATH = ROOT / "schemas/gc_order_flow_era_map.schema.json"
GATES_PATH = ROOT / "configs/data/gc-order-flow-quality-gates.yaml"
DECISIONS_PATH = ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    import io

    buffer = io.BytesIO()
    frame.to_parquet(buffer, engine="pyarrow")
    return buffer.getvalue()


def _write_era_map_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "gc_order_flow_era_map_validator.zip"
    minute = pd.to_datetime(["2020-01-01T00:00:00Z"])
    of_frame = pd.DataFrame({"volume": [1], "delta": [1], "trades": [1], "cvd": [1], "minute": minute})
    ext_frame = pd.DataFrame(
        {"volume": [1], "delta": [1], "trades": [1], "minute": minute.tz_localize(None)}
    )
    ohlcv_frame = pd.DataFrame(
        {"open": [1.0], "high": [2.0], "low": [0.5], "close": [1.5], "volume": [1], "minute": minute}
    )
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("gc/README.md", "# GC order flow\n")
        archive.writestr("gc/GCall_of_1m.parquet", _parquet_bytes(of_frame))
        archive.writestr("gc/GCext_of_1m.parquet", _parquet_bytes(ext_frame))
        archive.writestr("gc/GCall_ohlcv_1m.parquet", _parquet_bytes(ohlcv_frame))
    return zip_path


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase25.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_order_flow_era_map.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = _write_era_map_zip(Path(tmpdir))
        result = _run(
            [
                sys.executable,
                str(ROOT / "tools/inspect_gc_order_flow_era_map.py"),
                "--zip",
                str(zip_path),
                "--gates",
                str(GATES_PATH),
                "--decisions",
                str(DECISIONS_PATH),
            ]
        )
        payload = json.loads(result.stdout)
        _require(
            payload["status"] == "ORDER_FLOW_PARQUET_FILE_CATALOG_SOURCE_BLOCKED",
            "order-flow Parquet catalog must be profiled but source-blocked",
        )
        _require(len(payload["parquet_eras"]) == 3, "temporary era map must include every Parquet file")
        _require(payload["dataset_construction_allowed"] is False, "dataset construction must remain blocked")
        _require(payload["training_allowed"] is False, "training must remain blocked")
        _require(payload["order_flow_era_map_gate_status"] == "UNSATISFIED_FILE_CATALOG_ONLY", "file catalog must not satisfy era-map gate")
        _require("USE_ARCHIVED_CVD_COLUMN" in payload["blocked_actions"], "archived CVD use must remain blocked")
        for forbidden in (str(zip_path), str(GATES_PATH), str(DECISIONS_PATH), "C:\\", "/Users/"):
            _require(forbidden not in result.stdout, "era-map CLI output must not include local paths")
    print("Phase 26 artifacts validated")


if __name__ == "__main__":
    main()
