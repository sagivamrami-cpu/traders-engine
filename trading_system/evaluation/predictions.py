from __future__ import annotations

from trading_system.evaluation.contracts import PredictionPayload

MODEL_ID = "majority-class-baseline"
CALIBRATION_VERSION = "uncalibrated-majority-0.1.0"


def prediction_from_majority_baseline(
    candidate_id: str,
    *,
    baseline_class: str,
    model_version: str,
    feature_schema_version: str,
) -> PredictionPayload:
    p_target = 1.0 if baseline_class == "TARGET_FIRST" else 0.0
    p_stop = 1.0 if baseline_class == "STOP_FIRST" else 0.0
    p_expired = 1.0 if baseline_class == "EXPIRED" else 0.0
    return PredictionPayload(
        candidate_id=candidate_id,
        model_id=MODEL_ID,
        model_version=model_version,
        feature_schema_version=feature_schema_version,
        p_target_first=p_target,
        p_stop_first=p_stop,
        p_expired=p_expired,
        expected_net_return_r=2.0 * p_target - p_stop,
        expected_mae_r=p_stop,
        expected_mfe_r=2.0 * p_target,
        uncertainty=0.0,
        coverage_status="LOW_COVERAGE",
        calibration_version=CALIBRATION_VERSION,
    )
