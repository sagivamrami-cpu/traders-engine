import pytest

from trading_system.evaluation.metrics import accuracy, brier_score_target_first, expected_calibration_error
from trading_system.evaluation.predictions import prediction_from_majority_baseline


def test_majority_baseline_prediction_is_one_hot_and_schema_ready():
    prediction = prediction_from_majority_baseline(
        "candidate-1",
        baseline_class="TARGET_FIRST",
        model_version="majority-class-baseline-0.1.0",
        feature_schema_version="feature-catalog-0.1.0",
    )

    assert prediction.p_target_first == 1.0
    assert prediction.p_stop_first == 0.0
    assert prediction.p_expired == 0.0
    assert prediction.coverage_status == "LOW_COVERAGE"


def test_accuracy_counts_exact_class_matches():
    assert accuracy(["TARGET_FIRST", "STOP_FIRST", "EXPIRED"], ["TARGET_FIRST", "TARGET_FIRST", "EXPIRED"]) == 2 / 3


def test_brier_score_for_target_first():
    assert brier_score_target_first([1.0, 0.0, 0.25], ["TARGET_FIRST", "STOP_FIRST", "TARGET_FIRST"]) == 0.1875


def test_expected_calibration_error_uses_probability_bins():
    ece = expected_calibration_error(
        [0.1, 0.2, 0.8, 0.9],
        ["STOP_FIRST", "TARGET_FIRST", "TARGET_FIRST", "STOP_FIRST"],
        bin_count=2,
    )

    assert ece == pytest.approx(0.35)
