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
MANIFEST_VERSION = "gc-cme-calendar-evidence-manifest-0.1.0"
MODE = "GC_CME_CALENDAR_EVIDENCE_MANIFEST"
SCHEMA_PATH = ROOT / "schemas/gc_cme_calendar_evidence_manifest.schema.json"


@dataclass(frozen=True)
class GcCmeCalendarEvidenceManifestReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected CME evidence manifest YAML mapping")
    return to_plain_data(loaded)


def build_gc_cme_calendar_evidence_manifest_report(
    manifest_path: Path,
    *,
    created_at: datetime,
) -> GcCmeCalendarEvidenceManifestReport:
    manifest = _load_yaml(manifest_path)
    payload = {
        "manifest_id": _id({"created_at": utc_iso(created_at), "manifest": manifest}),
        "manifest_version": MANIFEST_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "canonical_symbol": str(manifest["canonical_symbol"]),
        "calendar_id": str(manifest["calendar_id"]),
        "status": str(manifest["status"]),
        "source_strategy_ref": str(manifest["source_strategy_ref"]),
        "construction_policy_ref": str(manifest["construction_policy_ref"]),
        "session_calendar_gate_status": str(manifest["session_calendar_gate_status"]),
        "authoritative_source_family": str(manifest["authoritative_source_family"]),
        "sources": [dict(source) for source in manifest["sources"]],
        "coverage_assessment": dict(manifest["coverage_assessment"]),
        "required_missing_evidence": list(manifest["required_missing_evidence"]),
        "calendar_registration_allowed": bool(manifest["calendar_registration_allowed"]),
        "dataset_construction_allowed": bool(manifest["dataset_construction_allowed"]),
        "resampling_allowed": bool(manifest["resampling_allowed"]),
        "training_allowed": bool(manifest["training_allowed"]),
        "blocked_actions": list(manifest["blocked_actions"]),
        "blocked_reasons": list(manifest["blocked_reasons"]),
    }
    return GcCmeCalendarEvidenceManifestReport(payload=payload)
