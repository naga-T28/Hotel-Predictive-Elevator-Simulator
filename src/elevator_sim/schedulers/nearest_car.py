"""Nearest Car Scheduler: simple baseline (requirements.md 8.2)."""
from __future__ import annotations

from elevator_sim.domain.hall_call import HallCall
from elevator_sim.simulation.state import SimulationState

STOP_OVERHEAD_SECONDS = 6.0


class NearestCarScheduler:
    name = "nearest_car"

    def assign_call(self, call: HallCall, state: SimulationState) -> str:
        best_car_id = None
        best_cost = float("inf")
        for car_id, car in state.cars.items():
            cost = car.travel_time(call.origin_floor) + len(car.stop_queue) * STOP_OVERHEAD_SECONDS
            if cost < best_cost - 1e-9:
                best_cost = cost
                best_car_id = car_id
        return best_car_id
