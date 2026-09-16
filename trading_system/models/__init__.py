"""Research-only Phase 5 model readiness and baseline training."""

from trading_system.models.baseline import train_majority_baseline
from trading_system.models.contracts import ModelTrainingRun
from trading_system.models.readiness import (
    TrainingPolicy,
    TrainingReadinessResult,
    evaluate_training_readiness,
)

__all__ = [
    "ModelTrainingRun",
    "TrainingPolicy",
    "TrainingReadinessResult",
    "evaluate_training_readiness",
    "train_majority_baseline",
]
