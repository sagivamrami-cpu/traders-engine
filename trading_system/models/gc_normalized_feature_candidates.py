from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.features.contracts import utc_iso

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_normalized_feature_candidates_report.schema.json"
REPORT_VERSION = "gc-normalized-feature-candidates-report-0.1.0"
MODE = "GC_NORMALIZED_FEATURE_CANDIDATES"
RAW_FEATURE_EXCLUSIONS = {
    "close": "RAW_PRICE_FEATURE_EXCLUDED_FOR_REGIME_DRIFT",
    "atr_14": "RAW_ATR_FEATURE_EXCLUDED_FOR_REGIME_DRIFT",
}
APPROVED_EXISTING_FEATURES = [
    "ret_1",
    "ret_4",
    "ret_8",
    "ret_14",
    "range_over_atr",
    "direction_is_long",
    "direction_is_short",
]
NORMALIZED_FEATURE_DEFINITIONS = [
    {
        "name": "atr_14_over_close",
        "formula": "atr_14 / close",
        "source_features": ["atr_14", "close"],
        "zero_denominator_policy": "SET_NULL_THEN_TRAIN_SPLIT_IMPUTE",
        "reason": "Use relative volatility instead of raw ATR so price-regime changes do not dominate the model.",
    },
    {
        "name": "of_delta_over_of_volume",
        "formula": "of_delta / of_volume",
        "source_features": ["of_delta", "of_volume"],
        "zero_denominator_policy": "SET_NULL_THEN_TRAIN_SPLIT_IMPUTE",
        "reason": "Normalize buy-sell pressure by traded volume.",
    },
    {
        "name": "of_delta_sum_14_over_of_volume_sum_14",
        "formula": "of_delta_sum_14 / of_volume_sum_14",
        "source_features": ["of_delta_sum_14", "of_volume_sum_14"],
        "zero_denominator_policy": "SET_NULL_THEN_TRAIN_SPLIT_IMPUTE",
        "reason": "Normalize cumulative order-flow pressure by cumulative activity.",
    },
    {
        "name": "of_trades_per_minute",
        "formula": "of_trades / of_minutes_present",
        "source_features": ["of_trades", "of_minutes_present"],
        "zero_denominator_policy": "SET_NULL_THEN_TRAIN_SPLIT_IMPUTE",
        "reason": "Convert raw trade count into activity density per observed minute.",
    },
    {
        "name": "of_volume_per_trade",
        "formula": "of_volume / of_trades",
        "source_features": ["of_volume", "of_trades"],
        "zero_denominator_policy": "SET_NULL_THEN_TRAIN_SPLIT_IMPUTE",
        "reason": "Capture average transaction size without letting raw volume dominate.",
    },
    {
        "name": "of_volume_vs_14bar_avg",
        "formula": "of_volume / (of_volume_sum_14 / 14)",
        "source_features": ["of_volume", "of_volume_sum_14"],
        "zero_denominator_policy": "SET_NULL_THEN_TRAIN_SPLIT_IMPUTE",
        "reason": "Measure current volume against its recent local baseline.",
    },
    {
        "name": "of_trades_vs_14bar_avg",
        "formula": "of_trades / (of_trades_sum_14 / 14)",
        "source_features": ["of_trades", "of_trades_sum_14"],
        "zero_denominator_policy": "SET_NULL_THEN_TRAIN_SPLIT_IMPUTE",
        "reason": "Measure current trade count against its recent local baseline.",
    },
]
FORBIDDEN_FEATURE_INPUTS = [
    "outcome_class",
    "net_return_r",
    "time_to_outcome_bars",
    "entry_price",
    "target_price",
    "stop_price",
    "risk_r",
]
FEATURE_GROUPS = {
    "PRICE_RETURNS": ["ret_1", "ret_4", "ret_8", "ret_14", "range_over_atr"],
    "VOLATILITY_NORMALIZED": ["atr_14_over_close"],
    "ORDER_FLOW_NORMALIZED": [
        "of_delta_over_of_volume",
        "of_delta_sum_14_over_of_volume_sum_14",
        "of_trades_per_minute",
        "of_volume_per_trade",
        "of_volume_vs_14bar_avg",
        "of_trades_vs_14bar_avg",
    ],
    "DIRECTION_CONTEXT": ["direction_is_long", "direction_is_short"],
}
REQUIRED_TRAINING_CONTROLS = [
    "TRAIN_ONLY_IMPUTATION_AND_STANDARDIZATION",
    "VALIDATION_ONLY_THRESHOLD_SELECTION",
    "TEST_ONLY_FINAL_EVALUATION",
    "NO_LABEL_OR_OUTCOME_FEATURE_INPUTS",
]
BLOCKED_ACTIONS = [
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
    "CLAIM_EDGE",
]


@dataclass(frozen=True)
class GcNormalizedFeatureCandidatesReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _report_id(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "report_id"}
    return hashlib.sha256(stable_json_dumps(body).encode("utf-8")).hexdigest()


def _excluded_raw_features(feature_diagnostics: dict[str, Any]) -> list[dict[str, str]]:
    drifted = {str(item["feature"]) for item in feature_diagnostics.get("top_drift_features", [])}
    return [
        {"feature": feature, "reason": reason}
        for feature, reason in RAW_FEATURE_EXCLUSIONS.items()
        if feature in drifted
    ]


def _next_model_feature_set() -> list[str]:
    normalized_names = [item["name"] for item in NORMALIZED_FEATURE_DEFINITIONS]
    return APPROVED_EXISTING_FEATURES + normalized_names


def build_gc_normalized_feature_candidates_report(
    feature_diagnostics: dict[str, Any],
    *,
    created_at: datetime,
) -> GcNormalizedFeatureCandidatesReport:
    payload = {
        "report_id": "",
        "report_version": REPORT_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "status": "NORMALIZED_FEATURE_CANDIDATES_READY",
        "dataset_id": str(feature_diagnostics["dataset_id"]),
        "variant": str(feature_diagnostics["variant"]),
        "source_feature_diagnostics_report_id": str(feature_diagnostics["report_id"]),
        "source_feature_diagnostics_status": str(feature_diagnostics["status"]),
        "included_rows_by_split": dict(feature_diagnostics["included_rows_by_split"]),
        "research_training_allowed": True,
        "model_promotion_allowed": False,
        "next_model_feature_set": _next_model_feature_set(),
        "approved_existing_features": list(APPROVED_EXISTING_FEATURES),
        "normalized_feature_definitions": list(NORMALIZED_FEATURE_DEFINITIONS),
        "excluded_raw_features": _excluded_raw_features(feature_diagnostics),
        "forbidden_feature_inputs": list(FORBIDDEN_FEATURE_INPUTS),
        "feature_groups": {group: list(features) for group, features in FEATURE_GROUPS.items()},
        "required_training_controls": list(REQUIRED_TRAINING_CONTROLS),
        "blocked_actions": list(BLOCKED_ACTIONS),
        "recommended_next_phase": "PHASE_52_NORMALIZED_FEATURE_MODEL_RETRAINING",
    }
    payload["report_id"] = _report_id(payload)
    return GcNormalizedFeatureCandidatesReport(payload)
