"""Trajectory-based predictor combining the Transformer destination model
and the linear remaining-time model (requirements.md 9.6-9.9).

Two-stage prediction: (1) does this partially observed walk look like it is
heading to the elevator (PPGE, via the Transformer classifier), and (2) if
so, how much longer until it gets there (via linear regression on grid
position). The PPGE >= threshold gating itself is left to
:class:`~elevator_sim.schedulers.predictive.PredictiveScheduler`, which
already applies ``probability_threshold`` generically to any predictor's
output (requirements.md 9.9).
"""
from __future__ import annotations

from elevator_sim.predictors.base import PredictedPassenger
from elevator_sim.predictors.linear_rtd import LinearRemainingTimeModel
from elevator_sim.predictors.transformer import TransformerDestinationModel
from elevator_sim.simulation.state import SimulationState
from elevator_sim.traffic.grid import GridSpace


class TrajectoryBasedPredictor:
    def __init__(
        self,
        destination_model: TransformerDestinationModel,
        remaining_time_model: LinearRemainingTimeModel,
        grid: GridSpace,
    ) -> None:
        self.destination_model = destination_model
        self.remaining_time_model = remaining_time_model
        self.grid = grid

    def predict_future_passengers(
        self,
        current_time: float,
        horizon_seconds: float,
        simulation_state: SimulationState,
    ) -> list[PredictedPassenger]:
        predicted: list[PredictedPassenger] = []

        for traj in simulation_state.trajectories:
            if traj.start_time > current_time:
                continue  # walk has not started yet from the tracking system's point of view
            if traj.hall_arrival_time is not None and traj.hall_arrival_time <= current_time:
                continue  # already at the hall (a real HallCall exists for them by now)

            partial = traj.points_up_to(current_time)
            if not partial:
                continue

            token_ids = [self.grid.grid_id(xi, yi) for xi, yi, _ in partial]
            probability = self.destination_model.predict_probability(token_ids)

            last_xi, last_yi, _ = partial[-1]
            remaining_time = self.remaining_time_model.predict(last_xi, last_yi)
            predicted_arrival_time = current_time + remaining_time
            if remaining_time > horizon_seconds:
                continue

            predicted.append(
                PredictedPassenger(
                    predicted_arrival_time=predicted_arrival_time,
                    origin_floor=traj.floor,
                    destination_floor=None,
                    probability=probability,
                    expected_group_size=1.0,
                    true_passenger_id=traj.person_id,
                )
            )

        return predicted
