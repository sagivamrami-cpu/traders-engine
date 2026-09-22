from __future__ import annotations


def accuracy(predicted: list[str], actual: list[str]) -> float | None:
    if not actual:
        return None
    correct = sum(1 for pred, outcome in zip(predicted, actual) if pred == outcome)
    return correct / len(actual)


def brier_score_target_first(probabilities: list[float], actual: list[str]) -> float | None:
    if not actual:
        return None
    total = 0.0
    for probability, outcome in zip(probabilities, actual):
        expected = 1.0 if outcome == "TARGET_FIRST" else 0.0
        total += (probability - expected) ** 2
    return total / len(actual)


def expected_calibration_error(probabilities: list[float], actual: list[str], *, bin_count: int) -> float | None:
    if not actual:
        return None
    if bin_count <= 0:
        raise ValueError("bin_count must be positive")
    total = 0.0
    sample_count = len(actual)
    for bin_index in range(bin_count):
        lower = bin_index / bin_count
        upper = (bin_index + 1) / bin_count
        pairs = [
            (probability, outcome)
            for probability, outcome in zip(probabilities, actual)
            if _in_probability_bin(probability, lower, upper, include_upper=bin_index == bin_count - 1)
        ]
        if not pairs:
            continue
        confidence = sum(probability for probability, _ in pairs) / len(pairs)
        observed = sum(1 for _, outcome in pairs if outcome == "TARGET_FIRST") / len(pairs)
        total += (len(pairs) / sample_count) * abs(confidence - observed)
    return total


def _in_probability_bin(probability: float, lower: float, upper: float, *, include_upper: bool) -> bool:
    if include_upper:
        return lower <= probability <= upper
    return lower <= probability < upper
