"""Predictor common interface (requirements.md 9.1)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from elevator_sim.simulation.state import SimulationState


@dataclass
class PredictedPassenger:
    predicted_arrival_time: float
    origin_floor: int
    destination_floor: int | None
    probability: float
    expected_group_size: float = 1.0
    true_passenger_id: str | None = None


class PassengerPredictor(Protocol):
    def predict_future_passengers(
        self,
        current_time: float,
        horizon_seconds: float,
        simulation_state: "SimulationState",
    ) -> list[PredictedPassenger]:
        ...
