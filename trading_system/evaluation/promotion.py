from __future__ import annotations

from trading_system.evaluation.contracts import ModelEvaluationReport


def evaluate_promotion_gate(report: ModelEvaluationReport, policy) -> dict[str, object]:
    reasons: list[str] = []
    if int(report.aggregate_metrics.get("window_count", len(report.windows)) or 0) < policy.min_windows:
        reasons.append("INSUFFICIENT_WALK_FORWARD_WINDOWS")
    reasons.extend(
        [
            "HUMAN_APPROVAL_MISSING",
            "SHADOW_EVIDENCE_MISSING",
            "PAPER_EVIDENCE_MISSING",
            "COST_FILL_EVIDENCE_MISSING",
        ]
    )
    return {"promotion_allowed": False, "blocked_reasons": reasons}
