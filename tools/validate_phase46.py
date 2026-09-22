from __future__ import annotations

import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.hashing import sha256_file
from trading_system.research.gc_real_dataset_build import load_build_manifest

MANIFEST_PATH = ROOT / "configs/datasets/gc-30m-real-dataset-build-manifest.json"
ROWS_ROOT = ROOT / "market-data/gc-30m-real"
EXPECTED_DATASET_ID = "f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _contains_local_path(value: object) -> bool:
    if isinstance(value, dict):
        return any(_contains_local_path(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_local_path(item) for item in value)
    if isinstance(value, str):
        return "C:\\" in value or "/Users/" in value
    return False


def main() -> None:
    manifest = load_build_manifest(MANIFEST_PATH)
    _require(manifest["dataset_id"] == EXPECTED_DATASET_ID, "Phase 46 must validate the approved GC dataset_id")
    _require(manifest["mode"] == "GC_REAL_DATASET_BUILD", "manifest mode must identify a real GC dataset build")
    _require(manifest["real_dataset_built"] is True, "real dataset must be marked built")
    _require(manifest["training_allowed"] is False, "dataset build manifest must not authorize training")
    _require(manifest["model_promotion_allowed"] is False, "dataset build manifest must not authorize promotion")
    _require(not _contains_local_path(manifest), "manifest must not contain local machine paths")

    for action in ("MODEL_PROMOTION", "LIVE_TRADING", "BROKER_EXECUTION", "CAPITAL_ALLOCATION", "CLAIM_EDGE"):
        _require(action in manifest["blocked_actions"], f"blocked action missing: {action}")

    summary = manifest["summary"]
    _require(summary["rows_total"] == manifest["rows_count"], "summary row count must match manifest rows_count")
    _require(summary["rows_by_split"] == {"TRAIN": 271870, "VALIDATION": 47180, "TEST": 61312}, "raw split counts changed")
    _require(
        summary["variants"]["order_flow"]["included_rows_by_split"]
        == {"TRAIN": 238398, "VALIDATION": 45074, "TEST": 57584},
        "order-flow training split counts changed",
    )
    _require(
        summary["variants"]["order_flow"]["included_outcome_class_counts"]
        == {"EXPIRED": 47922, "STOP_FIRST": 146567, "TARGET_FIRST": 146567},
        "order-flow class distribution changed",
    )
    _require(
        summary["rules"]["entry"] == "NEXT_BAR_OPEN_AFTER_DECISION_BAR_CLOSE",
        "entry timing must stay next-bar-open after a closed decision bar",
    )
    _require(summary["rules"]["horizon_bars"] == 8, "label horizon must stay 8 bars")
    _require(summary["rules"]["embargo_bars"] == 8, "split embargo must stay 8 bars")

    rows_path = ROWS_ROOT / manifest["rows_relative_dir"] / manifest["rows_file"]
    _require(rows_path.is_file(), "rows parquet file is missing")
    _require(sha256_file(rows_path) == manifest["rows_sha256"], "rows parquet hash does not match manifest")

    parquet = pq.ParquetFile(rows_path)
    _require(parquet.metadata.num_rows == manifest["rows_count"], "parquet row count does not match manifest")
    _require(list(parquet.schema_arrow.names) == manifest["rows_columns"], "parquet columns do not match manifest")

    print("Phase 46 artifacts validated")


if __name__ == "__main__":
    main()
