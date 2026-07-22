"""Oracle Predictor: returns the true future passengers (requirements.md 9.2)."""
from __future__ import annotations

from elevator_sim.predictors.base import PredictedPassenger
from elevator_sim.simulation.state import SimulationState


class OraclePredictor:
    def predict_future_passengers(
        self,
        current_time: float,
        horizon_seconds: float,
        simulation_state: SimulationState,
    ) -> list[PredictedPassenger]:
        deadline = current_time + horizon_seconds
        predicted = []
        for passenger in simulation_state.future_arrivals:
            if passenger.hall_arrival_time > deadline:
                break
            predicted.append(
                PredictedPassenger(
                    predicted_arrival_time=passenger.hall_arrival_time,
                    origin_floor=passenger.origin_floor,
                    destination_floor=passenger.destination_floor,
                    probability=1.0,
                    expected_group_size=passenger.group_size,
                    true_passenger_id=passenger.passenger_id,
                )
            )
        return predicted
