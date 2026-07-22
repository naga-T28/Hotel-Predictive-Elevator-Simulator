"""No Prediction predictor, used by the Myopic Scheduler (requirements.md 9.3)."""
from __future__ import annotations

from elevator_sim.predictors.base import PredictedPassenger
from elevator_sim.simulation.state import SimulationState


class NoPredictionPredictor:
    def predict_future_passengers(
        self,
        current_time: float,
        horizon_seconds: float,
        simulation_state: SimulationState,
    ) -> list[PredictedPassenger]:
        return []
