from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from trading_system.data_foundation.csv_inspection import inspect_local_ohlcv_csv
from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map
from trading_system.data_foundation.source_identity import (
    SourceIdentityValidation,
    load_source_identity_policy,
    validate_source_identity,
)
from trading_system.features.contracts import utc_iso

INTAKE_PACKET_VERSION = "real-ohlcv-intake-packet-0.1.0"
MODE = "REAL_OHLCV_INTAKE_PACKET"
REDACTED_LOCAL_PATH = "LOCAL_PATH_REDACTED"
BLOCKED_ACTIONS = (
    "BUILD_PRODUCTION_TRAINING_DATASET",
    "TRAIN_PRODUCTION_MODEL",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
)
REQUIRED_DECISION_RECORDS = (
    "REAL_HISTORICAL_OHLCV_CSV",
    "PRODUCTION_OHLCV_VENDOR_DECISION",
    "FIRST_REAL_SYMBOL",
    "FIRST_HISTORICAL_INTERVAL",
    "RAW_DATA_STORAGE_LICENSE_APPROVAL",
    "ORDER_FLOW_SOURCE_DECISION",
    "OPTIONS_SOURCE_DECISION",
)
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RealOhlcvIntakePacket:
    packet_id: str
    created_at: datetime
    status: str
    raw_file_sha256: str
    row_count: int
    raw_symbols: tuple[str, ...]
    first_observed_at: str | None
    last_observed_at: str | None
    inspection: dict[str, Any]
    source_identity: SourceIdentityValidation
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "packet_version": INTAKE_PACKET_VERSION,
            "mode": MODE,
            "created_at": utc_iso(self.created_at),
            "status": self.status,
            "csv_path": REDACTED_LOCAL_PATH,
            "raw_file_sha256": self.raw_file_sha256,
            "row_count": self.row_count,
            "raw_symbols": list(self.raw_symbols),
            "first_observed_at": self.first_observed_at,
            "last_observed_at": self.last_observed_at,
            "inspection": self.inspection,
            "source_identity": self.source_identity.to_payload(),
            "required_decision_records": list(REQUIRED_DECISION_RECORDS),
            "production_allowed": False,
            "blocked_actions": list(BLOCKED_ACTIONS),
            "blocked_reasons": list(self.blocked_reasons),
        }


def _metadata_inputs(metadata: dict[str, Any]) -> dict[str, str]:
    return {
        "source_id": str(metadata["source_id"]),
        "canonical_symbol": str(metadata["canonical_symbol"]),
        "asset_class": str(metadata["asset_class"]),
        "venue": str(metadata["venue"]),
        "timeframe": str(metadata["timeframe"]),
        "session_calendar_id": str(metadata["session_calendar_id"]),
        "owner": str(metadata["owner"]),
    }


def _redact_inspection(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(payload)
    redacted["csv_path"] = REDACTED_LOCAL_PATH
    id_payload = {key: value for key, value in redacted.items() if key != "inspection_id"}
    redacted["inspection_id"] = hashlib.sha256(stable_json_dumps(id_payload).encode("utf-8")).hexdigest()
    return redacted


def _packet_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def build_real_ohlcv_intake_packet(
    csv_path: Path,
    metadata_path: Path,
    *,
    created_at: datetime,
    project_root: Path | None = None,
) -> RealOhlcvIntakePacket:
    root = ROOT if project_root is None else project_root
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    normalization_policy = load_normalization_policy(root / "configs/data/normalization-policy.yaml")
    symbol_map = load_symbol_map(root / "configs/data/symbol-map.yaml")
    inspection = inspect_local_ohlcv_csv(
        csv_path,
        _metadata_inputs(metadata),
        normalization_policy,
        symbol_map,
        created_at=created_at,
    ).to_payload()
    identity_policy = load_source_identity_policy(root / "configs/data/source-identity-policy.yaml")
    source_identity = validate_source_identity(metadata, identity_policy, project_root=root)
    blocked_reasons = _unique(
        (
            *inspection["blocked_reasons"],
            *source_identity.blocked_reasons,
            "HUMAN_DECISION_RECORDS_REQUIRED",
        )
    )
    status = "BLOCKED_NEEDS_HUMAN_DECISION"
    if inspection["status"] == "BLOCKED" or source_identity.status != "REAL_SOURCE_PENDING_HUMAN_DECISION":
        status = "BLOCKED_INVALID_INPUT"
    redacted_inspection = _redact_inspection(inspection)
    id_payload = {
        "created_at": utc_iso(created_at),
        "status": status,
        "raw_file_sha256": inspection["raw_file_sha256"],
        "row_count": inspection["row_count"],
        "raw_symbols": inspection["raw_symbols"],
        "first_observed_at": inspection["first_observed_at"],
        "last_observed_at": inspection["last_observed_at"],
        "inspection_status": inspection["status"],
        "source_identity": source_identity.to_payload(),
        "blocked_reasons": blocked_reasons,
    }
    return RealOhlcvIntakePacket(
        packet_id=_packet_id(id_payload),
        created_at=created_at,
        status=status,
        raw_file_sha256=str(inspection["raw_file_sha256"]),
        row_count=int(inspection["row_count"]),
        raw_symbols=tuple(inspection["raw_symbols"]),
        first_observed_at=inspection["first_observed_at"],
        last_observed_at=inspection["last_observed_at"],
        inspection=redacted_inspection,
        source_identity=source_identity,
        blocked_reasons=blocked_reasons,
    )
