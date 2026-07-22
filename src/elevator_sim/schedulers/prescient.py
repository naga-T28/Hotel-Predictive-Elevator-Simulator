"""Prescient Scheduler: upper-bound performance using perfect future
knowledge (requirements.md 8.4)."""
from __future__ import annotations

from elevator_sim.predictors.oracle import OraclePredictor
from elevator_sim.schedulers.predictive import PredictiveScheduler


class PrescientScheduler(PredictiveScheduler):
    name = "prescient"

    def __init__(self, optimization_horizon_seconds: float = 600.0) -> None:
        super().__init__(
            predictor=OraclePredictor(),
            prediction_horizon_seconds=optimization_horizon_seconds,
            optimization_horizon_seconds=optimization_horizon_seconds,
            number_of_continuations=1,
        )
