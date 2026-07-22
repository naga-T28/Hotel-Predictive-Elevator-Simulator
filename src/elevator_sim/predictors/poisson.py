"""Aggregate Poisson Predictor (requirements.md 9.4).

Generates future passengers from a configured (or historically estimated)
per-floor arrival rate rather than by observing ground truth or trajectories.
Used to validate the Predictive Scheduler's plumbing before trajectory-based
or hotel-informed prediction is available.
"""
from __future__ import annotations

import numpy as np

from elevator_sim.predictors.base import PredictedPassenger
from elevator_sim.simulation.state import SimulationState


class AggregatePoissonPredictor:
    def __init__(
        self,
        rng: np.random.Generator,
        floor_rates_per_hour: dict[int, float],
        destination_floor: int,
    ) -> None:
        self.rng = rng
        self.floor_rates_per_hour = floor_rates_per_hour
        self.destination_floor = destination_floor

    def predict_future_passengers(
        self,
        current_time: float,
        horizon_seconds: float,
        simulation_state: SimulationState,
    ) -> list[PredictedPassenger]:
        predicted: list[PredictedPassenger] = []
        for floor, rate_per_hour in self.floor_rates_per_hour.items():
            expected_count = (rate_per_hour / 3600.0) * horizon_seconds
            count = self.rng.poisson(expected_count) if expected_count > 0 else 0
            for _ in range(count):
                arrival = current_time + float(self.rng.uniform(0, horizon_seconds))
                predicted.append(
                    PredictedPassenger(
                        predicted_arrival_time=arrival,
                        origin_floor=floor,
                        destination_floor=self.destination_floor,
                        probability=1.0,
                        expected_group_size=1.0,
                    )
                )
        return predicted
