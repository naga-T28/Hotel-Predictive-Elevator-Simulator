"""Hotel-informed predictor (requirements.md 8.6).

Estimates a time-varying per-floor arrival rate from the hotel's own event
schedule (checkout, breakfast, banquet end, etc.) instead of a flat Poisson
rate: each event contributes a Gaussian-shaped rate bump around its
scheduled time, so e.g. checkout demand at a floor rises just before
checkout time and fades afterwards, per requirements.md 8.6 ("チェックアウト
時間直前から将来下り乗客の発生確率を増加させる"). Falls back to a flat
baseline rate when no event is active for a floor.
"""
from __future__ import annotations

import numpy as np

from elevator_sim.domain.hotel_event import HotelEvent
from elevator_sim.predictors.base import PredictedPassenger
from elevator_sim.simulation.state import SimulationState


def _gaussian_density(t: float, mean: float, std: float) -> float:
    std = max(std, 1e-6)
    z = (t - mean) / std
    return float(np.exp(-0.5 * z * z) / (std * np.sqrt(2.0 * np.pi)))


class HotelInformedPredictor:
    def __init__(
        self,
        rng: np.random.Generator,
        events: list[HotelEvent],
        baseline_rate_per_hour: float = 0.0,
        baseline_destination_floor: int = 1,
    ) -> None:
        self.rng = rng
        self.events = events
        self.baseline_rate_per_hour = baseline_rate_per_hour
        self.baseline_destination_floor = baseline_destination_floor
        self._floors = sorted({floor for event in events for floor in event.source_floors})

    def _active_event(self, floor: int, at_time: float) -> HotelEvent | None:
        """The event contributing the most instantaneous arrival rate to
        `floor` at `at_time`, among events whose 3-sigma window covers it."""
        best_event = None
        best_rate = 0.0
        for event in self.events:
            if floor not in event.source_floors:
                continue
            center = (event.start_time + event.end_time) / 2.0 if event.end_time > event.start_time else event.start_time
            center += event.prediction_time_offset_seconds
            if abs(at_time - center) > 3 * max(event.spread_seconds, 1.0):
                continue
            rate = _gaussian_density(at_time, center, event.spread_seconds) * event.expected_people
            if rate > best_rate:
                best_rate = rate
                best_event = event
        return best_event

    def _rate_per_second(self, floor: int, at_time: float) -> tuple[float, HotelEvent | None]:
        event = self._active_event(floor, at_time)
        if event is None:
            return self.baseline_rate_per_hour / 3600.0, None
        center = (event.start_time + event.end_time) / 2.0 if event.end_time > event.start_time else event.start_time
        center += event.prediction_time_offset_seconds
        return _gaussian_density(at_time, center, event.spread_seconds) * event.expected_people, event

    def predict_future_passengers(
        self,
        current_time: float,
        horizon_seconds: float,
        simulation_state: SimulationState,
    ) -> list[PredictedPassenger]:
        predicted: list[PredictedPassenger] = []
        midpoint = current_time + horizon_seconds / 2.0

        floors = self._floors or [f for f in simulation_state.building.floor_ids]
        for floor in floors:
            rate_per_second, event = self._rate_per_second(floor, midpoint)
            expected_count = rate_per_second * horizon_seconds
            count = self.rng.poisson(expected_count) if expected_count > 0 else 0

            for _ in range(count):
                arrival = current_time + float(self.rng.uniform(0, horizon_seconds))
                if event is not None:
                    destinations = list(event.destination_distribution.keys())
                    weights = np.array(list(event.destination_distribution.values()), dtype=float)
                    weights = weights / weights.sum()
                    destination = int(self.rng.choice(destinations, p=weights))
                    group_size = event.group_size
                else:
                    destination = self.baseline_destination_floor
                    group_size = 1

                if destination == floor:
                    continue

                predicted.append(
                    PredictedPassenger(
                        predicted_arrival_time=arrival,
                        origin_floor=floor,
                        destination_floor=destination,
                        probability=1.0,
                        expected_group_size=group_size,
                    )
                )

        return predicted
