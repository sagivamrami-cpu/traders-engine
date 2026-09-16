from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.features.contracts import utc_iso

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_feature_diagnostics_report.schema.json"
REPORT_VERSION = "gc-feature-diagnostics-report-0.1.0"
MODE = "GC_FEATURE_DIAGNOSTICS"
BLOCKED_ACTIONS = [
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
    "CLAIM_EDGE",
]


@dataclass(frozen=True)
class GcFeatureDiagnosticsReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _report_id(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "report_id"}
    return hashlib.sha256(stable_json_dumps(body).encode("utf-8")).hexdigest()


def _number(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _eligible(rows: pd.DataFrame, variant: str) -> pd.DataFrame:
    included_column = f"included_{variant}"
    frame = rows[rows[included_column].astype(bool)].copy()
    frame = frame[frame["outcome_class"].notna()]
    frame = frame[frame["outcome_class"] != "AMBIGUOUS"]
    return frame


def _feature_names(first_model_run: dict[str, Any], rows: pd.DataFrame) -> list[str]:
    names = []
    for name in first_model_run["feature_names"]:
        if name in ("direction_is_long", "direction_is_short"):
            continue
        if name in rows.columns and pd.api.types.is_numeric_dtype(rows[name]):
            names.append(str(name))
    return names


def _split(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    return frame[frame["split"] == split]


def _series_mean(frame: pd.DataFrame, feature: str) -> float | None:
    if frame.empty:
        return None
    return _number(frame[feature].mean())


def _feature_summary(frame: pd.DataFrame, feature: str) -> dict[str, float | None]:
    train = _split(frame, "TRAIN")
    validation = _split(frame, "VALIDATION")
    test = _split(frame, "TEST")
    train_mean = _series_mean(train, feature)
    validation_mean = _series_mean(validation, feature)
    test_mean = _series_mean(test, feature)
    train_std = _number(train[feature].std(ddof=0)) if not train.empty else None
    denominator = train_std if train_std and train_std > 1e-12 else None
    target_train = train[train["outcome_class"] == "TARGET_FIRST"]
    non_target_train = train[train["outcome_class"] != "TARGET_FIRST"]
    target_mean = _series_mean(target_train, feature)
    non_target_mean = _series_mean(non_target_train, feature)
    return {
        "train_mean": train_mean,
        "validation_mean": validation_mean,
        "test_mean": test_mean,
        "train_std": train_std,
        "validation_drift_z": None if denominator is None or validation_mean is None or train_mean is None else (validation_mean - train_mean) / denominator,
        "test_drift_z": None if denominator is None or test_mean is None or train_mean is None else (test_mean - train_mean) / denominator,
        "train_target_mean": target_mean,
        "train_non_target_mean": non_target_mean,
        "train_target_separation": None if target_mean is None or non_target_mean is None else target_mean - non_target_mean,
    }


def _top_drift(feature_summaries: dict[str, dict[str, float | None]]) -> list[dict[str, float | str | None]]:
    ranked = sorted(
        (
            {
                "feature": feature,
                "test_drift_z": summary["test_drift_z"],
                "validation_drift_z": summary["validation_drift_z"],
            }
            for feature, summary in feature_summaries.items()
        ),
        key=lambda item: (
            -abs(float(item["test_drift_z"])) if item["test_drift_z"] is not None else 0.0,
            str(item["feature"]),
        ),
    )
    return ranked[:10]


def _regime_split_summary(frame: pd.DataFrame) -> dict[str, float | int | None]:
    if frame.empty:
        return {"rows": 0, "target_rate": None, "mean_return_r": None}
    return {
        "rows": int(len(frame)),
        "target_rate": float((frame["outcome_class"] == "TARGET_FIRST").mean()),
        "mean_return_r": _number(frame["net_return_r"].mean()),
    }


def _regime(frame: pd.DataFrame, mask: pd.Series) -> dict[str, dict[str, float | int | None]]:
    regime_frame = frame[mask]
    return {split: _regime_split_summary(_split(regime_frame, split)) for split in ("TRAIN", "VALIDATION", "TEST")}


def _regime_summaries(frame: pd.DataFrame) -> dict[str, dict[str, dict[str, float | int | None]]]:
    summaries: dict[str, dict[str, dict[str, float | int | None]]] = {}
    summaries["direction=LONG"] = _regime(frame, frame["direction"] == "LONG")
    summaries["direction=SHORT"] = _regime(frame, frame["direction"] == "SHORT")
    if "of_delta" in frame.columns:
        summaries["of_delta=POSITIVE"] = _regime(frame, frame["of_delta"] > 0)
        summaries["of_delta=NEGATIVE_OR_ZERO"] = _regime(frame, frame["of_delta"] <= 0)
    if "ret_14" in frame.columns:
        summaries["ret_14=POSITIVE"] = _regime(frame, frame["ret_14"] > 0)
        summaries["ret_14=NEGATIVE_OR_ZERO"] = _regime(frame, frame["ret_14"] <= 0)
    if "atr_14" in frame.columns:
        train_atr = _split(frame, "TRAIN")["atr_14"].dropna()
        if not train_atr.empty:
            low = float(train_atr.quantile(1 / 3))
            high = float(train_atr.quantile(2 / 3))
            summaries["atr_14=LOW"] = _regime(frame, frame["atr_14"] <= low)
            summaries["atr_14=MID"] = _regime(frame, (frame["atr_14"] > low) & (frame["atr_14"] <= high))
            summaries["atr_14=HIGH"] = _regime(frame, frame["atr_14"] > high)
    return summaries


def _recommended_experiments(top_drift_features: list[dict[str, Any]], model_diagnostics: dict[str, Any]) -> list[str]:
    experiments = ["REGIME_FILTER_RESEARCH", "THRESHOLD_STABILITY_REVIEW"]
    if any(str(item["feature"]).startswith("of_") for item in top_drift_features[:3]):
        experiments.append("ORDER_FLOW_FEATURE_STABILITY_REVIEW")
    if "NEGATIVE_TEST_EXPECTED_R" in model_diagnostics.get("blocked_reasons", []):
        experiments.append("FAILED_TRADE_CLUSTER_REVIEW")
    return sorted(set(experiments))


def build_gc_feature_diagnostics_report(
    rows: pd.DataFrame,
    build_manifest: dict[str, Any],
    first_model_run: dict[str, Any],
    model_diagnostics: dict[str, Any],
    *,
    created_at: datetime,
    variant: str = "order_flow",
) -> GcFeatureDiagnosticsReport:
    frame = _eligible(rows, variant)
    features = _feature_names(first_model_run, frame)
    feature_summaries = {feature: _feature_summary(frame, feature) for feature in features}
    top_drift_features = _top_drift(feature_summaries)
    payload = {
        "report_id": "",
        "report_version": REPORT_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "status": "EXPERIMENT_DESIGN_REQUIRED",
        "dataset_id": str(build_manifest["dataset_id"]),
        "variant": variant,
        "diagnostic_focus": "FEATURE_AND_REGIME_STABILITY",
        "source_model_run_id": str(first_model_run["run_id"]),
        "source_model_diagnostics_report_id": str(model_diagnostics["report_id"]),
        "included_rows_by_split": dict(build_manifest["summary"]["variants"][variant]["included_rows_by_split"]),
        "feature_summaries": feature_summaries,
        "top_drift_features": top_drift_features,
        "regime_summaries": _regime_summaries(frame),
        "recommended_experiments": _recommended_experiments(top_drift_features, model_diagnostics),
        "blocked_actions": BLOCKED_ACTIONS,
        "promotion_allowed": False,
    }
    payload["report_id"] = _report_id(payload)
    return GcFeatureDiagnosticsReport(payload)
