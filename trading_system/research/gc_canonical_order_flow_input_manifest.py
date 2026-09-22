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
MANIFEST_VERSION = "gc-canonical-order-flow-input-manifest-0.1.0"
MODE = "GC_CANONICAL_ORDER_FLOW_INPUT_MANIFEST"
SCHEMA_PATH = ROOT / "schemas/gc_canonical_order_flow_input_manifest.schema.json"


@dataclass(frozen=True)
class GcCanonicalOrderFlowInputManifestReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected canonical order-flow input manifest YAML mapping")
    return to_plain_data(loaded)


def build_gc_canonical_order_flow_input_manifest_report(
    manifest_path: Path,
    *,
    created_at: datetime,
) -> GcCanonicalOrderFlowInputManifestReport:
    manifest = _load_yaml(manifest_path)
    payload = {
        "manifest_id": _id({"created_at": utc_iso(created_at), "manifest": manifest}),
        "manifest_version": MANIFEST_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "canonical_symbol": str(manifest["canonical_symbol"]),
        "status": str(manifest["status"]),
        "source_type": str(manifest["source_type"]),
        "profile_only_decision_ref": str(manifest["profile_only_decision_ref"]),
        "timestamp_decision_ref": str(manifest["timestamp_decision_ref"]),
        "source_profile_ref": str(manifest["source_profile_ref"]),
        "era_map_ref": str(manifest["era_map_ref"]),
        "availability_policy_ref": str(manifest["availability_policy_ref"]),
        "archive_sha256": str(manifest["archive_sha256"]),
        "archive_size_bytes": int(manifest["archive_size_bytes"]),
        "archive_member_count": int(manifest["archive_member_count"]),
        "parquet_member_count": int(manifest["parquet_member_count"]),
        "selected_member": str(manifest["selected_member"]),
        "selected_member_role": str(manifest["selected_member_role"]),
        "selected_member_row_count": int(manifest["selected_member_row_count"]),
        "selected_member_columns": list(manifest["selected_member_columns"]),
        "selected_member_start_at": str(manifest["selected_member_start_at"]),
        "selected_member_end_at": str(manifest["selected_member_end_at"]),
        "timestamp_role": str(manifest["timestamp_role"]),
        "timezone_policy": str(manifest["timezone_policy"]),
        "known_damaged_aggressor_window": dict(manifest["known_damaged_aggressor_window"]),
        "archived_cvd_policy": str(manifest["archived_cvd_policy"]),
        "canonical_order_flow_input_gate_status": str(manifest["canonical_order_flow_input_gate_status"]),
        "order_flow_source_decision_status": str(manifest["order_flow_source_decision_status"]),
        "order_flow_era_map_gate_status": str(manifest["order_flow_era_map_gate_status"]),
        "dataset_identity_gate_status": str(manifest["dataset_identity_gate_status"]),
        "local_path": str(manifest["local_path"]),
        "dataset_construction_allowed": bool(manifest["dataset_construction_allowed"]),
        "training_allowed": bool(manifest["training_allowed"]),
        "blocked_actions": list(manifest["blocked_actions"]),
        "blocked_reasons": list(manifest["blocked_reasons"]),
    }
    return GcCanonicalOrderFlowInputManifestReport(payload=payload)
