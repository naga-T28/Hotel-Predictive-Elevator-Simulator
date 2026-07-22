"""Myopic Scheduler: uses only currently known passengers (requirements.md 8.1)."""
from __future__ import annotations

from elevator_sim.domain.hall_call import HallCall
from elevator_sim.simulation.forward_simulator import forward_simulate
from elevator_sim.simulation.state import SimulationState

LOOKAHEAD_SECONDS = 600.0


class MyopicScheduler:
    name = "myopic"

    def assign_call(self, call: HallCall, state: SimulationState) -> str:
        best_car_id = None
        best_cost = float("inf")

        for car_id in state.cars:
            copied_state = state.clone()
            copied_state.assign(call, car_id)
            car = copied_state.cars[car_id]
            result = forward_simulate(
                car=car,
                passenger_lookup=copied_state.passengers,
                future_passengers=[],
                current_time=state.time,
                horizon_seconds=LOOKAHEAD_SECONDS,
            )
            cost = result.mean_wait
            if cost < best_cost - 1e-9:
                best_cost = cost
                best_car_id = car_id

        return best_car_id
