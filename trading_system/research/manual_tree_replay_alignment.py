from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.features.contracts import utc_iso

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_SCHEMA_PATH = ROOT / "schemas/manual_tree_golden_alerts.schema.json"
ALIGNMENT_SCHEMA_PATH = ROOT / "schemas/manual_tree_replay_alignment_report.schema.json"
GOLDEN_VERSION = "manual-tree-golden-alerts-0.1.0"
ALIGNMENT_VERSION = "manual-tree-replay-alignment-report-0.1.0"
BLOCKED_ACTIONS = [
    "RUN_MANUAL_TREE_REPLAY",
    "TRAIN_MODEL_FROM_MANUAL_ALERTS",
    "MAP_XAUUSD_TO_GC_WITHOUT_PROXY_STUDY",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
    "CLAIM_EDGE",
]


@dataclass(frozen=True)
class ManualTreeGoldenAlerts:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(GOLDEN_SCHEMA_PATH, self.payload)
        return self.payload


@dataclass(frozen=True)
class ManualTreeReplayAlignmentReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(ALIGNMENT_SCHEMA_PATH, self.payload)
        return self.payload


def _stable_id(payload: dict[str, Any], excluded_keys: Iterable[str]) -> str:
    excluded = set(excluded_keys)
    body = {key: value for key, value in payload.items() if key not in excluded}
    return hashlib.sha256(stable_json_dumps(body).encode("utf-8")).hexdigest()


def _alert_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _local_datetime(alert: dict[str, Any], source_timezone: str) -> datetime:
    return datetime.fromisoformat(f"{alert['alert_date']}T{alert['alert_time']}:00").replace(
        tzinfo=ZoneInfo(source_timezone)
    )


def _normalize_alert(alert: dict[str, Any], source_timezone: str) -> dict[str, Any]:
    local = _local_datetime(alert, source_timezone)
    utc = local.astimezone(ZoneInfo("UTC"))
    payload = {
        "source_row_index": int(alert["source_row_index"]),
        "raw_symbol": str(alert.get("asset", "XAUUSD")),
        "alert_local_time": local.isoformat(),
        "alert_utc_time": utc_iso(utc),
        "direction": str(alert["direction"]),
        "entry_price": float(alert["entry_price"]),
        "targets_hit_visible": int(alert.get("targets_hit_visible", 0)),
        "max_favorable_move": (
            None if alert.get("max_favorable_move") is None else float(alert["max_favorable_move"])
        ),
        "max_favorable_move_unit": "pips",
        "outcome_status": str(alert.get("outcome_status", "FILLED")),
        "transcription_confidence": str(alert.get("transcription_confidence", "HIGH")),
    }
    payload["alert_id"] = _alert_id(payload)
    return {"alert_id": payload.pop("alert_id"), **payload}


def build_manual_tree_golden_alerts(
    manual_alerts: Sequence[dict[str, Any]],
    *,
    created_at: datetime,
    source_timezone: str,
) -> ManualTreeGoldenAlerts:
    alerts = sorted(
        (_normalize_alert(alert, source_timezone) for alert in manual_alerts),
        key=lambda item: item["alert_utc_time"],
    )
    if not alerts:
        raise ValueError("manual alerts are required")
    payload = {
        "golden_set_id": "",
        "golden_set_version": GOLDEN_VERSION,
        "mode": "MANUAL_TREE_GOLDEN_ALERTS",
        "created_at": utc_iso(created_at),
        "source": "USER_PROVIDED_TRADE_SUMMARY_SCREENSHOT",
        "source_timezone": source_timezone,
        "timestamp_semantics": "ALERT_TIME",
        "raw_symbol": "XAUUSD",
        "alert_count": len(alerts),
        "alert_range_utc": {
            "start": alerts[0]["alert_utc_time"],
            "end": alerts[-1]["alert_utc_time"],
        },
        "alerts": alerts,
    }
    payload["golden_set_id"] = _stable_id(payload, {"golden_set_id", "created_at"})
    return ManualTreeGoldenAlerts(payload)


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _registered_symbols(symbol_map: Iterable[str] | dict[str, Any]) -> list[str]:
    if isinstance(symbol_map, dict):
        return sorted(str(item["canonical_symbol"]) for item in symbol_map.get("symbols", []))
    return sorted(str(item) for item in symbol_map)


def build_manual_tree_replay_alignment_report(
    golden_alerts: dict[str, Any],
    dataset_manifest: dict[str, Any],
    *,
    symbol_map: Iterable[str] | dict[str, Any],
    tree_gate_audit_id: str,
    created_at: datetime,
) -> ManualTreeReplayAlignmentReport:
    registered = _registered_symbols(symbol_map)
    dataset_range = {
        "start": str(dataset_manifest["summary"]["first_bar_start"]),
        "end": str(dataset_manifest["summary"]["last_bar_start"]),
    }
    alert_range = golden_alerts["alert_range_utc"]
    blocked_reasons = ["SYMBOL_MISMATCH_XAUUSD_VS_GC"]
    if "XAUUSD" not in registered:
        blocked_reasons.append("XAUUSD_NOT_REGISTERED_IN_SYMBOL_MAP")
    if _parse_utc(alert_range["start"]) > _parse_utc(dataset_range["end"]):
        blocked_reasons.append("ALERT_RANGE_AFTER_CURRENT_DATASET_END")
    blocked_reasons.append("TREE_GATES_NOT_IMPLEMENTED_FOR_MANUAL_REPLAY")
    payload = {
        "report_id": "",
        "report_version": ALIGNMENT_VERSION,
        "mode": "MANUAL_TREE_REPLAY_ALIGNMENT",
        "created_at": utc_iso(created_at),
        "status": "REPLAY_BLOCKED_SOURCE_DATA_GAP",
        "source_golden_set_id": golden_alerts["golden_set_id"],
        "tree_gate_audit_id": str(tree_gate_audit_id),
        "manual_alert_symbol": "XAUUSD",
        "manual_alert_count": int(golden_alerts["alert_count"]),
        "manual_alert_range_utc": alert_range,
        "current_dataset_id": str(dataset_manifest["dataset_id"]),
        "current_dataset_symbol": "GC",
        "current_dataset_range_utc": dataset_range,
        "registered_symbols": registered,
        "eligible_for_current_replay_count": 0,
        "blocked_reasons": blocked_reasons,
        "required_next_inputs": [
            "register XAUUSD as a separate replay symbol or record a human-approved GC proxy study",
            "obtain XAUUSD OHLCV for 2026-08-31 through 2026-09-04 with point-in-time timestamps",
            "obtain matching order-flow source or explicitly mark order-flow unavailable for this replay",
            "implement typed tree gates before scoring replay alignment",
        ],
        "replay_ready": False,
        "model_training_allowed": False,
        "model_promotion_allowed": False,
        "blocked_actions": list(BLOCKED_ACTIONS),
        "recommended_next_phase": "PHASE_59_XAUUSD_REPLAY_DATA_ONBOARDING_OR_PROXY_DECISION",
    }
    payload["report_id"] = _stable_id(payload, {"report_id", "created_at"})
    return ManualTreeReplayAlignmentReport(payload)
