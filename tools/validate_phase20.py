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

SCHEMA_PATH = ROOT / "schemas/databento_gc_source_profile.schema.json"
METADATA_PATH = ROOT / "configs/data/databento-gc-source-metadata.yaml"
DECISIONS_PATH = ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _gc_frame(timestamps: list[str]) -> pd.DataFrame:
    index = pd.DatetimeIndex(pd.to_datetime(timestamps), name="ts_event").tz_localize("UTC")
    return pd.DataFrame(
        {
            "gc_open": [100.0] * len(timestamps),
            "gc_high": [101.0] * len(timestamps),
            "gc_low": [99.0] * len(timestamps),
            "gc_close": [100.5] * len(timestamps),
            "gc_volume": [10.0] * len(timestamps),
        },
        index=index,
    )


def _write_test_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "gc_validator_archive.zip"
    frames = {
        "gc_2020-01.parquet": _gc_frame(["2020-01-01T00:00:00", "2020-01-01T00:00:01"]),
        "gc_2020-02.parquet": _gc_frame(["2020-02-01T00:00:00", "2020-02-01T00:00:01"]),
    }
    with zipfile.ZipFile(zip_path, "w") as archive:
        for name, frame in frames.items():
            buffer = io.BytesIO()
            frame.to_parquet(buffer, engine="pyarrow")
            archive.writestr(name, buffer.getvalue())
    return zip_path


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase19.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_databento_gc_source_profile.py", "-q"])

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
    _require(readiness["status"] == "BLOCKED", "readiness with GC decisions must remain blocked")
    _require(readiness["satisfied_count"] == 6, "GC decisions must satisfy exactly six readiness items")
    _require(readiness["open_count"] == 1, "only options decision must remain open/deferred")
    open_items = {
        item["item_id"]
        for item in readiness["required_items"]
        if item["status"] == "OPEN_HUMAN_DECISION"
    }
    _require("ORDER_FLOW_SOURCE_DECISION" not in open_items, "order-flow decision must be approved")
    _require("OPTIONS_SOURCE_DECISION" in open_items, "options decision must remain open/deferred")

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = _write_test_zip(Path(tmpdir))
        cli_result = _run(
            [
                sys.executable,
                str(ROOT / "tools/inspect_databento_gc_zip.py"),
                "--zip",
                str(zip_path),
                "--metadata",
                str(METADATA_PATH),
                "--decisions",
                str(DECISIONS_PATH),
            ]
        )
        payload = json.loads(cli_result.stdout)
        validate_json_payload(SCHEMA_PATH, payload)
        _require(payload["status"] == "PROFILE_SAMPLED_DATASET_BLOCKED", "test-zip profile must be sampled but dataset-blocked")
        _require(payload["dataset_construction_allowed"] is False, "profile must not allow dataset construction")
        _require(payload["training_allowed"] is False, "profile must not allow training")
        _require(payload["allowed_next_actions"] == [], "profile must not advertise next actions")
        _require(payload["source_identity"]["status"] == "REAL_SOURCE_PENDING_HUMAN_DECISION", "source identity must stay pending")
        _require(payload["full_archive_quality_status"] == "NOT_PROVEN_IN_PHASE_20", "phase 20 must not certify the full archive")
        for forbidden in (str(zip_path), str(METADATA_PATH), str(DECISIONS_PATH), "C:\\", "/Users/"):
            _require(forbidden not in cli_result.stdout, "CLI output must not include local paths")

    print("Phase 20 artifacts validated")


if __name__ == "__main__":
    main()
