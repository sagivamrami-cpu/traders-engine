from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from trading_system.data_foundation.csv_onboarding import REQUIRED_OHLCV_COLUMNS, CsvOnboardingError
from trading_system.data_foundation.hashing import sha256_file, stable_json_dumps
from trading_system.data_foundation.normalization import (
    load_normalization_policy,
    load_symbol_map,
    normalize_ohlcv_row,
    read_csv_rows,
)
from trading_system.data_foundation.storage_policy import (
    evaluate_raw_data_retention,
    load_raw_data_retention_policy,
)
from trading_system.features.contracts import utc_iso
from trading_system.research.intake_packet import REDACTED_LOCAL_PATH
from trading_system.research.real_source_onboarding import (
    RECORDS_PRESENT_STATUS,
    build_real_source_onboarding_preflight,
)

BUNDLE_VERSION = "real-source-local-bundle-0.1.0"
MODE = "REAL_SOURCE_LOCAL_BUNDLE_PREPARATION"
PREPARED_STATUS = "LOCAL_MANIFEST_PREPARED_PRODUCTION_BLOCKED"
BLOCKED_ACTIONS = (
    "RUN_OFFLINE_DRY_RUN",
    "BUILD_PRODUCTION_TRAINING_DATASET",
    "TRAIN_PRODUCTION_MODEL",
    "CLAIM_EDGE",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
    "DEPLOYMENT",
    "COPY_RAW_CSV",
    "MUTATE_RAW_CSV",
    "UPLOAD_RAW_CSV",
)
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RealSourceLocalBundle:
    bundle_id: str
    created_at: datetime
    status: str
    decisions_path_present: bool
    preflight: dict[str, Any]
    source_identity: dict[str, Any]
    local_manifest: dict[str, Any] | None
    retention_decision: dict[str, Any]
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "bundle_version": BUNDLE_VERSION,
            "mode": MODE,
            "created_at": utc_iso(self.created_at),
            "status": self.status,
            "csv_path": REDACTED_LOCAL_PATH,
            "metadata_path": REDACTED_LOCAL_PATH,
            "decisions_path": REDACTED_LOCAL_PATH if self.decisions_path_present else None,
            "retention_policy_path": REDACTED_LOCAL_PATH,
            "preflight": self.preflight,
            "source_identity": self.source_identity,
            "local_manifest": self.local_manifest,
            "retention_decision": self.retention_decision,
            "dry_run_summary": None,
            "production_allowed": False,
            "allowed_next_actions": [],
            "blocked_actions": list(BLOCKED_ACTIONS),
            "blocked_reasons": list(self.blocked_reasons),
        }


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise CsvOnboardingError("datetime must be timezone-aware")
    return value.isoformat().replace("+00:00", "Z")


def _validate_columns(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise CsvOnboardingError("csv contains no rows")
    missing = sorted(REQUIRED_OHLCV_COLUMNS - set(rows[0]))
    if missing:
        raise CsvOnboardingError(f"missing required columns: {', '.join(missing)}")


def _build_sanitized_manifest(
    csv_path: Path,
    metadata: dict[str, Any],
    *,
    created_at: datetime,
    root: Path,
) -> dict[str, Any]:
    normalization_policy = load_normalization_policy(root / "configs/data/normalization-policy.yaml")
    symbol_map = load_symbol_map(root / "configs/data/symbol-map.yaml")
    rows = read_csv_rows(csv_path)
    _validate_columns(rows)
    records = [
        normalize_ohlcv_row(
            row,
            normalization_policy,
            symbol_map,
            source_id=str(metadata["source_id"]),
            source_version=str(metadata["schema_version"]),
        )
        for row in rows
    ]
    observed_symbols = {record.canonical_symbol for record in records}
    canonical_symbol = str(metadata["canonical_symbol"])
    if observed_symbols != {canonical_symbol}:
        raise CsvOnboardingError(
            "csv canonical symbols do not match metadata canonical_symbol: "
            + ", ".join(sorted(observed_symbols))
        )
    observed_at_values = [record.observed_at for record in records]
    return {
        "manifest_version": metadata["manifest_version"],
        "source_id": metadata["source_id"],
        "source_type": metadata["source_type"],
        "source_status": metadata["source_status"],
        "asset_class": metadata["asset_class"],
        "venue": metadata["venue"],
        "canonical_symbol": metadata["canonical_symbol"],
        "raw_symbol": metadata["raw_symbol"],
        "timeframe": metadata["timeframe"],
        "timezone": metadata["timezone"],
        "session_calendar_id": metadata["session_calendar_id"],
        "schema_version": metadata["schema_version"],
        "raw_file": REDACTED_LOCAL_PATH,
        "raw_file_sha256": sha256_file(csv_path),
        "row_count": len(rows),
        "first_observed_at": _format_utc(min(observed_at_values)),
        "last_observed_at": _format_utc(max(observed_at_values)),
        "ingested_at": _format_utc(created_at),
        "correction_policy": metadata["correction_policy"],
        "owner": "HUMAN_DATA_OWNER_REDACTED",
    }


def _preflight_summary(preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "preflight_id": preflight["preflight_id"],
        "preflight_version": preflight["preflight_version"],
        "mode": preflight["mode"],
        "created_at": preflight["created_at"],
        "status": preflight["status"],
        "csv_path": REDACTED_LOCAL_PATH,
        "metadata_path": REDACTED_LOCAL_PATH,
        "decisions_path": REDACTED_LOCAL_PATH if preflight["decisions_path"] else None,
        "production_allowed": False,
        "allowed_next_actions": [],
        "blocked_actions": preflight["blocked_actions"],
        "blocked_reasons": preflight["blocked_reasons"],
    }


def _source_identity_for_emit(source_identity: dict[str, Any]) -> dict[str, Any]:
    if source_identity["status"] != "FIXTURE_ONLY":
        return source_identity
    blocked_reasons = tuple(
        dict.fromkeys([*source_identity["blocked_reasons"], "FIXTURE_SOURCE_NOT_ALLOWED"])
    )
    return {
        **source_identity,
        "status": "BLOCKED",
        "production_allowed": False,
        "blocked_reasons": list(blocked_reasons),
    }


def _bundle_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _blocked_retention(retention_policy_path: Path) -> dict[str, Any]:
    return _phase19_retention_decision(retention_policy_path, {})


def _phase19_retention_decision(
    retention_policy_path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    payload = evaluate_raw_data_retention(
        load_raw_data_retention_policy(retention_policy_path),
        manifest,
    ).to_payload()
    payload["status"] = "BLOCKED"
    payload["retention_approved"] = False
    payload["raw_copy_allowed"] = False
    payload["raw_mutation_allowed"] = False
    payload["network_upload_allowed"] = False
    payload["manifest_output_allowed"] = True
    payload["dry_run_output_allowed"] = False
    payload["blocked_reasons"] = list(
        dict.fromkeys([*payload["blocked_reasons"], "RUN_OFFLINE_DRY_RUN_BLOCKED_FOR_REAL_SOURCE"])
    )
    return payload


def build_real_source_local_bundle(
    csv_path: Path,
    metadata_path: Path,
    decisions_path: Path | None,
    retention_policy_path: Path,
    *,
    created_at: datetime,
    project_root: Path | None = None,
) -> RealSourceLocalBundle:
    root = ROOT if project_root is None else project_root
    full_preflight = build_real_source_onboarding_preflight(
        csv_path,
        metadata_path,
        decisions_path,
        created_at=created_at,
        project_root=root,
    ).to_payload()
    preflight = _preflight_summary(full_preflight)
    source_identity = _source_identity_for_emit(full_preflight["source_identity"])
    reasons: list[str] = []
    local_manifest: dict[str, Any] | None = None
    retention_decision = _blocked_retention(retention_policy_path)
    status = "BLOCKED"
    if full_preflight["status"] != RECORDS_PRESENT_STATUS:
        reasons.append("PREFLIGHT_NOT_RECORDS_PRESENT")
        reasons.extend(full_preflight["blocked_reasons"])
    else:
        try:
            metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
            local_manifest = _build_sanitized_manifest(csv_path, metadata, created_at=created_at, root=root)
            retention_decision = _phase19_retention_decision(retention_policy_path, local_manifest)
            status = PREPARED_STATUS
            reasons.extend(retention_decision["blocked_reasons"])
        except Exception:
            reasons.append("LOCAL_MANIFEST_PREPARATION_FAILED")
            local_manifest = None
    id_payload = {
        "created_at": utc_iso(created_at),
        "status": status,
        "preflight_id": preflight["preflight_id"],
        "source_identity": source_identity,
        "local_manifest": local_manifest,
        "retention_status": retention_decision["status"],
        "blocked_reasons": list(dict.fromkeys(reasons)),
    }
    return RealSourceLocalBundle(
        bundle_id=_bundle_id(id_payload),
        created_at=created_at,
        status=status,
        decisions_path_present=decisions_path is not None,
        preflight=preflight,
        source_identity=source_identity,
        local_manifest=local_manifest,
        retention_decision=retention_decision,
        blocked_reasons=tuple(dict.fromkeys(reasons)),
    )
