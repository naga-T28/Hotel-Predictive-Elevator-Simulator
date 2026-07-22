"""Noisy Predictor: true future passengers with artificial detection and
measurement errors (requirements.md 9.5)."""
from __future__ import annotations

import numpy as np

from elevator_sim.predictors.base import PredictedPassenger
from elevator_sim.simulation.state import SimulationState


class NoisyOraclePredictor:
    def __init__(
        self,
        rng: np.random.Generator,
        floor_ids: list[int],
        recall: float = 0.80,
        precision: float = 0.90,
        arrival_time_std_seconds: float = 2.0,
        destination_accuracy: float = 0.95,
    ) -> None:
        self.rng = rng
        self.floor_ids = floor_ids
        self.recall = recall
        self.precision = precision
        self.arrival_time_std_seconds = arrival_time_std_seconds
        self.destination_accuracy = destination_accuracy

    def predict_future_passengers(
        self,
        current_time: float,
        horizon_seconds: float,
        simulation_state: SimulationState,
    ) -> list[PredictedPassenger]:
        deadline = current_time + horizon_seconds
        true_future = [
            p for p in simulation_state.future_arrivals if p.hall_arrival_time <= deadline
        ]

        detected = [p for p in true_future if self.rng.random() < self.recall]

        predicted: list[PredictedPassenger] = []
        for passenger in detected:
            destination = passenger.destination_floor
            if self.rng.random() >= self.destination_accuracy:
                candidates = [f for f in self.floor_ids if f != passenger.origin_floor and f != destination]
                if candidates:
                    destination = int(self.rng.choice(candidates))

            noisy_arrival = passenger.hall_arrival_time + self.rng.normal(
                0.0, self.arrival_time_std_seconds
            )
            predicted.append(
                PredictedPassenger(
                    predicted_arrival_time=max(current_time, noisy_arrival),
                    origin_floor=passenger.origin_floor,
                    destination_floor=destination,
                    probability=1.0,
                    expected_group_size=passenger.group_size,
                    true_passenger_id=passenger.passenger_id,
                )
            )

        true_positive_count = len(detected)
        if self.precision > 0:
            false_positive_count = int(
                round(true_positive_count * (1.0 - self.precision) / self.precision)
            )
        else:
            false_positive_count = 0

        for _ in range(false_positive_count):
            origin = int(self.rng.choice(self.floor_ids))
            destination_candidates = [f for f in self.floor_ids if f != origin]
            destination = int(self.rng.choice(destination_candidates)) if destination_candidates else origin
            arrival = current_time + self.rng.uniform(0, horizon_seconds)
            predicted.append(
                PredictedPassenger(
                    predicted_arrival_time=arrival,
                    origin_floor=origin,
                    destination_floor=destination,
                    probability=1.0,
                    expected_group_size=1.0,
                    true_passenger_id=None,
                )
            )

        return predicted
