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

SCHEMA_PATH = ROOT / "schemas/gc_order_flow_availability_era_policy.schema.json"
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


def _write_policy_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "gc_order_flow_availability_policy_validator.zip"
    frame = pd.DataFrame(
        {
            "volume": [10, 20, 30, 40],
            "delta": [1, -2, 3, -4],
            "trades": [3, 4, 5, 6],
            "cvd": [1, -1, 2, -2],
            "minute": pd.to_datetime(
                [
                    "2016-12-31T23:59:00Z",
                    "2017-01-01T00:00:00Z",
                    "2017-06-01T00:00:00Z",
                    "2017-06-01T00:01:00Z",
                ]
            ),
        }
    )
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("gc/README.md", "# GC order flow\n")
        archive.writestr("gc/GCall_of_1m.parquet", _parquet_bytes(frame))
    return zip_path


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase26.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_order_flow_availability_era_policy.py", "-q"])
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = _write_policy_zip(Path(tmpdir))
        result = _run(
            [
                sys.executable,
                str(ROOT / "tools/inspect_gc_order_flow_availability_era_policy.py"),
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
            payload["status"] == "FILE_RANGE_REGIME_CANDIDATE_ERA_MAP_UNSATISFIED",
            "availability policy must remain source-blocked",
        )
        _require(
            payload["order_flow_era_map_gate_status"] == "UNSATISFIED_POLICY_CANDIDATE_ONLY",
            "availability policy candidate must not satisfy era-map gate",
        )
        _require(payload["dataset_construction_allowed"] is False, "dataset construction must remain blocked")
        _require(payload["training_allowed"] is False, "training must remain blocked")
        _require("USE_ARCHIVED_CVD_COLUMN" in payload["blocked_actions"], "archived CVD use must remain blocked")
        _require("ORDER_FLOW_ERA_MAP" in payload["required_remaining_gates"], "era-map gate must remain")
        _require("ROW_LEVEL_2017_MASK" in payload["required_remaining_gates"], "row-level 2017 mask gate must remain")
        for forbidden in (str(zip_path), str(GATES_PATH), str(DECISIONS_PATH), "C:\\", "/Users/"):
            _require(forbidden not in result.stdout, "availability policy CLI output must not include local paths")
    print("Phase 27 artifacts validated")


if __name__ == "__main__":
    main()
