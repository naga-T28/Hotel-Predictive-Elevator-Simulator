"""Predictive Group Elevator Scheduler (requirements.md 8.5, 9.9, 9.10)."""
from __future__ import annotations

from statistics import mean

from elevator_sim.domain.hall_call import HallCall
from elevator_sim.predictors.base import PassengerPredictor
from elevator_sim.simulation.forward_simulator import forward_simulate
from elevator_sim.simulation.state import SimulationState


class PredictiveScheduler:
    name = "predictive"

    def __init__(
        self,
        predictor: PassengerPredictor,
        prediction_horizon_seconds: float = 10.0,
        optimization_horizon_seconds: float = 120.0,
        number_of_continuations: int = 1,
        probability_threshold: float = 0.0,
    ) -> None:
        self.predictor = predictor
        self.prediction_horizon_seconds = prediction_horizon_seconds
        self.optimization_horizon_seconds = optimization_horizon_seconds
        self.number_of_continuations = max(1, number_of_continuations)
        self.probability_threshold = probability_threshold

    def assign_call(self, call: HallCall, state: SimulationState) -> str:
        best_car_id = None
        best_cost = float("inf")

        for car_id in state.cars:
            scenario_costs = []
            for _ in range(self.number_of_continuations):
                future_scenario = [
                    pp
                    for pp in self.predictor.predict_future_passengers(
                        current_time=state.time,
                        horizon_seconds=self.prediction_horizon_seconds,
                        simulation_state=state,
                    )
                    if pp.probability >= self.probability_threshold
                ]
                copied_state = state.clone()
                copied_state.assign(call, car_id)
                car = copied_state.cars[car_id]

                result = forward_simulate(
                    car=car,
                    passenger_lookup=copied_state.passengers,
                    future_passengers=future_scenario,
                    current_time=state.time,
                    horizon_seconds=self.optimization_horizon_seconds,
                )
                scenario_costs.append(result.mean_wait)

            expected_cost = mean(scenario_costs)
            if expected_cost < best_cost - 1e-9:
                best_cost = expected_cost
                best_car_id = car_id

        return best_car_id
