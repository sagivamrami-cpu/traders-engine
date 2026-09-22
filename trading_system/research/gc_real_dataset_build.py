"""Build the first real GC 30m research dataset from the local Databento archives.

Governance enforced in code (D9-final):
- the dataset contract must carry ``dataset_construction_allowed: true`` and a
  non-empty ``construction_authorized_by`` list;
- every authorization record must be a human decision record under
  ``agent-exchange/decisions/`` containing ``Decision: APPROVED`` and the exact
  ``dataset_id`` of the identity manifest;
- the identity is recomputed against the local archives and must be
  ``LOCAL_ARCHIVE_VERIFIED`` with the same ``dataset_id`` as the committed
  identity manifest.

Local paths are never written into the manifest.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
import yaml

from trading_system.data_foundation.hashing import sha256_file, stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.features.contracts import utc_iso
from trading_system.research import gc_real_dataset_builder as builder
from trading_system.research.gc_dataset_identity import (
    build_gc_dataset_identity,
    compute_local_archive_hashes,
    load_identity_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_VERSION = "gc-30m-real-dataset-build-manifest-0.1.0"
MODE = "GC_REAL_DATASET_BUILD"
SCHEMA_PATH = ROOT / "schemas/gc_real_dataset_build_manifest.schema.json"
ORDER_FLOW_MEMBER = "gc/GCext_of_1m.parquet"
ROWS_FILENAME = "rows.parquet"


@dataclass(frozen=True)
class GcRealDatasetBuildManifest:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


class ConstructionNotAuthorized(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Archive readers
# ---------------------------------------------------------------------------


def load_ohlcv_30m_from_zip(zip_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    frames: list[pd.DataFrame] = []
    members_read = 0
    rows_1s = 0
    with zipfile.ZipFile(zip_path) as archive:
        names = sorted(name for name in archive.namelist() if name.endswith(".parquet"))
        for name in names:
            table = pq.read_table(io.BytesIO(archive.read(name)))
            frame = table.to_pandas()
            rows_1s += len(frame)
            members_read += 1
            if frame.empty:
                continue
            frames.append(builder.resample_1s_to_30m(frame))
    bars = pd.concat(frames).sort_index()
    if bars.index.has_duplicates:
        bars = bars.groupby(level=0, sort=True).agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
            seconds_with_trades=("seconds_with_trades", "sum"),
        )
        bars.index.name = "bar_start"
    stats = {"members_read": members_read, "source_rows_1s": int(rows_1s), "bars_30m_with_data": int(len(bars))}
    return bars, stats


def load_order_flow_30m_from_zip(zip_path: Path, member: str = ORDER_FLOW_MEMBER) -> tuple[pd.DataFrame, dict[str, Any]]:
    with zipfile.ZipFile(zip_path) as archive:
        frame = pq.read_table(io.BytesIO(archive.read(member))).to_pandas()
    forbidden = [column for column in frame.columns if "cvd" in str(column).lower() or "cum" in str(column).lower()]
    if forbidden:
        raise ValueError(f"forbidden cumulative columns present in order-flow member: {forbidden}")
    bars = builder.aggregate_order_flow_30m(frame[["volume", "delta", "trades"]])
    stats = {"member": member, "source_rows_1m": int(len(frame)), "bars_30m_with_order_flow": int(len(bars))}
    return bars, stats


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"expected mapping in {path.name}")
    return loaded


def check_construction_authorization(contract_path: Path, dataset_id: str, root: Path | None = None) -> list[str]:
    """Return the list of authorization record refs; raise if construction is not authorized."""
    root = root or ROOT
    contract = _load_yaml(contract_path)
    if contract.get("dataset_construction_allowed") is not True:
        raise ConstructionNotAuthorized("contract dataset_construction_allowed is not true")
    refs = list(contract.get("construction_authorized_by", []))
    if not refs:
        raise ConstructionNotAuthorized("contract construction_authorized_by is empty")
    for ref in refs:
        if not str(ref).startswith("agent-exchange/decisions/"):
            raise ConstructionNotAuthorized(f"authorization ref is not a decision record: {ref}")
        record = root / ref
        if not record.is_file():
            raise ConstructionNotAuthorized(f"authorization record missing: {ref}")
        text = record.read_text(encoding="utf-8")
        if "Decision: APPROVED" not in text:
            raise ConstructionNotAuthorized(f"authorization record is not APPROVED: {ref}")
        if dataset_id not in text:
            raise ConstructionNotAuthorized(f"authorization record does not bind dataset_id: {ref}")
    if contract.get("training_allowed") is not False:
        raise ConstructionNotAuthorized("contract training_allowed must remain false at build time")
    return [str(ref) for ref in refs]


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def build_real_dataset(
    *,
    ohlcv_zip: Path,
    order_flow_zip: Path,
    identity_config: Path,
    identity_manifest: Path,
    contract_path: Path,
    out_dir: Path,
    created_at: datetime,
    root: Path | None = None,
) -> GcRealDatasetBuildManifest:
    root = root or ROOT
    local_hashes = compute_local_archive_hashes({"ohlcv_1s": ohlcv_zip, "order_flow_1m": order_flow_zip})
    identity = build_gc_dataset_identity(
        identity_config, created_at=created_at, local_archive_hashes=local_hashes, root=root
    ).to_payload()
    if identity["identity_source"] != "LOCAL_ARCHIVE_VERIFIED":
        raise ConstructionNotAuthorized(f"local archives do not verify: {identity['blocked_reasons']}")
    committed = load_identity_manifest(identity_manifest)
    if committed["dataset_id"] != identity["dataset_id"]:
        raise ConstructionNotAuthorized("committed identity manifest dataset_id differs from recomputed identity")
    dataset_id = str(identity["dataset_id"])
    authorization_refs = check_construction_authorization(contract_path, dataset_id, root=root)

    ohlcv_30m, ohlcv_stats = load_ohlcv_30m_from_zip(ohlcv_zip)
    order_flow_30m, order_flow_stats = load_order_flow_30m_from_zip(order_flow_zip)
    built = builder.build_dataset(ohlcv_30m, order_flow_30m)

    rows = built.rows.copy()
    rows.insert(0, "dataset_id", dataset_id)
    rows.insert(1, "dataset_version", builder.BUILDER_VERSION)
    dataset_dir = out_dir / dataset_id[:16]
    dataset_dir.mkdir(parents=True, exist_ok=True)
    rows_path = dataset_dir / ROWS_FILENAME
    rows.to_parquet(rows_path, index=False)
    rows_sha256 = sha256_file(rows_path)

    body = {
        "manifest_version": MANIFEST_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "dataset_id": dataset_id,
        "dataset_name": str(identity["dataset_name"]),
        "identity_manifest_id": str(committed["manifest_id"]),
        "identity_source": str(identity["identity_source"]),
        "builder_version": builder.BUILDER_VERSION,
        "feature_schema_version": builder.FEATURE_SCHEMA_VERSION,
        "label_version": builder.LABEL_VERSION,
        "contract_version": builder.CONTRACT_VERSION,
        "authorization_record_refs": authorization_refs,
        "source_hashes": {
            "ohlcv_1s_zip": str(local_hashes["ohlcv_1s"]["sha256"]),
            "order_flow_zip": str(local_hashes["order_flow_1m"]["sha256"]),
        },
        "ohlcv_source_stats": ohlcv_stats,
        "order_flow_source_stats": order_flow_stats,
        "rows_file": ROWS_FILENAME,
        "rows_relative_dir": dataset_id[:16],
        "rows_sha256": rows_sha256,
        "rows_count": int(len(rows)),
        "rows_columns": [str(column) for column in rows.columns],
        "summary": built.summary,
        "contract_identity_status": "UNDECLARED_PENDING_RESEARCH",
        "real_dataset_built": True,
        "training_allowed": False,
        "model_promotion_allowed": False,
        "blocked_actions": [
            "MODEL_PROMOTION",
            "LIVE_TRADING",
            "BROKER_EXECUTION",
            "CAPITAL_ALLOCATION",
            "CLAIM_EDGE",
        ],
    }
    manifest_id = hashlib.sha256(stable_json_dumps(body).encode("utf-8")).hexdigest()
    return GcRealDatasetBuildManifest(payload={"manifest_id": manifest_id, **body})


def load_build_manifest(path: Path) -> dict[str, Any]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_json_payload(SCHEMA_PATH, payload)
    return payload
