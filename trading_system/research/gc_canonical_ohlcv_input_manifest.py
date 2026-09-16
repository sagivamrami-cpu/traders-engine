from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import to_plain_data, validate_json_payload
from trading_system.features.contracts import utc_iso

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_VERSION = "gc-canonical-ohlcv-input-manifest-0.1.0"
MODE = "GC_CANONICAL_OHLCV_INPUT_MANIFEST"
SCHEMA_PATH = ROOT / "schemas/gc_canonical_ohlcv_input_manifest.schema.json"


@dataclass(frozen=True)
class GcCanonicalOhlcvInputManifestReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected canonical OHLCV input manifest YAML mapping")
    return to_plain_data(loaded)


def build_gc_canonical_ohlcv_input_manifest_report(
    manifest_path: Path,
    *,
    created_at: datetime,
) -> GcCanonicalOhlcvInputManifestReport:
    manifest = _load_yaml(manifest_path)
    payload = {
        "manifest_id": _id({"created_at": utc_iso(created_at), "manifest": manifest}),
        "manifest_version": MANIFEST_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "canonical_symbol": str(manifest["canonical_symbol"]),
        "status": str(manifest["status"]),
        "source_type": str(manifest["source_type"]),
        "source_decision_ref": str(manifest["source_decision_ref"]),
        "vendor_decision_ref": str(manifest["vendor_decision_ref"]),
        "symbol_decision_ref": str(manifest["symbol_decision_ref"]),
        "interval_decision_ref": str(manifest["interval_decision_ref"]),
        "archive_sha256": str(manifest["archive_sha256"]),
        "archive_size_bytes": int(manifest["archive_size_bytes"]),
        "archive_member_count": int(manifest["archive_member_count"]),
        "observed_first_at": str(manifest["observed_first_at"]),
        "observed_last_at": str(manifest["observed_last_at"]),
        "timestamp_role": str(manifest["timestamp_role"]),
        "local_path": str(manifest["local_path"]),
        "canonical_ohlcv_input_gate_status": str(manifest["canonical_ohlcv_input_gate_status"]),
        "dataset_identity_gate_status": str(manifest["dataset_identity_gate_status"]),
        "dataset_construction_allowed": bool(manifest["dataset_construction_allowed"]),
        "training_allowed": bool(manifest["training_allowed"]),
        "blocked_actions": list(manifest["blocked_actions"]),
        "blocked_reasons": list(manifest["blocked_reasons"]),
    }
    return GcCanonicalOhlcvInputManifestReport(payload=payload)
