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
SCHEMA_PATH = ROOT / "schemas/gc_model_diagnostics_report.schema.json"
REPORT_VERSION = "gc-model-diagnostics-report-0.1.0"
MODE = "GC_MODEL_DIAGNOSTICS"


@dataclass(frozen=True)
class GcModelDiagnosticsReport:
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _report_id(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "report_id"}
    return hashlib.sha256(stable_json_dumps(body).encode("utf-8")).hexdigest()


def _metric(run: dict[str, Any], key: str) -> float | None:
    value = run.get("metrics", {}).get(key)
    return None if value is None else float(value)


def _delta(model_value: float | None, baseline_value: float | None) -> float | None:
    if model_value is None or baseline_value is None:
        return None
    return model_value - baseline_value


def _top_coefficients(run: dict[str, Any], limit: int = 10) -> list[dict[str, float | str]]:
    coefficients = run.get("coefficients", {})
    ranked = sorted(
        (
            {
                "feature": str(feature),
                "coefficient": float(coefficient),
                "abs_coefficient": abs(float(coefficient)),
            }
            for feature, coefficient in coefficients.items()
        ),
        key=lambda item: (-float(item["abs_coefficient"]), str(item["feature"])),
    )
    return ranked[:limit]


def _blocked_reasons(baseline_run: dict[str, Any], first_model_run: dict[str, Any]) -> list[str]:
    reasons = []
    test_expected_r = _metric(first_model_run, "test_expected_r_per_candidate")
    test_accuracy_delta = _delta(_metric(first_model_run, "test_accuracy"), _metric(baseline_run, "test_accuracy"))
    if test_expected_r is None:
        reasons.append("MISSING_TEST_EXPECTED_R")
    elif test_expected_r <= 0:
        reasons.append("NEGATIVE_TEST_EXPECTED_R")
    if test_accuracy_delta is None:
        reasons.append("MISSING_TEST_ACCURACY_DELTA")
    elif test_accuracy_delta <= 0:
        reasons.append("TEST_ACCURACY_NOT_ABOVE_BASELINE")
    if first_model_run.get("promotion_allowed") is not False:
        reasons.append("MODEL_RUN_PROMOTION_BOUNDARY_INVALID")
    return reasons


def build_gc_model_diagnostics_report(
    baseline_run: dict[str, Any],
    first_model_run: dict[str, Any],
    *,
    created_at: datetime,
) -> GcModelDiagnosticsReport:
    blocked_reasons = _blocked_reasons(baseline_run, first_model_run)
    payload = {
        "report_id": "",
        "report_version": REPORT_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "status": "FEATURE_DIAGNOSTICS_REQUIRED" if blocked_reasons else "RESEARCH_REVIEW_REQUIRED",
        "dataset_id": str(first_model_run["dataset_id"]),
        "baseline_run_id": str(baseline_run["run_id"]),
        "first_model_run_id": str(first_model_run["run_id"]),
        "baseline_model_type": str(baseline_run["model_type"]),
        "first_model_type": str(first_model_run["model_type"]),
        "split_summary": dict(sorted(first_model_run["split_summary"].items())),
        "metric_deltas": {
            "validation_accuracy_delta_vs_baseline": _delta(
                _metric(first_model_run, "validation_accuracy"),
                _metric(baseline_run, "validation_accuracy"),
            ),
            "test_accuracy_delta_vs_baseline": _delta(
                _metric(first_model_run, "test_accuracy"),
                _metric(baseline_run, "test_accuracy"),
            ),
            "validation_expected_r_per_candidate": _metric(first_model_run, "validation_expected_r_per_candidate"),
            "test_expected_r_per_candidate": _metric(first_model_run, "test_expected_r_per_candidate"),
            "validation_selected_trade_rate": _metric(first_model_run, "validation_selected_trade_rate"),
            "test_selected_trade_rate": _metric(first_model_run, "test_selected_trade_rate"),
        },
        "top_coefficients": _top_coefficients(first_model_run),
        "blocked_reasons": blocked_reasons,
        "promotion_allowed": False,
        "recommended_next_phase": "PHASE_50_FEATURE_DIAGNOSTICS_AND_EXPERIMENT_DESIGN",
    }
    payload["report_id"] = _report_id(payload)
    return GcModelDiagnosticsReport(payload)
