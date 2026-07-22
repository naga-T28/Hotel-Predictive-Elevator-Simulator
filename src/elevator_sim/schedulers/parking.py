"""Parking Scheduler: proactively repositions idle cars (requirements.md 8.3).

Hall-call assignment itself is delegated to :class:`NearestCarScheduler`;
what distinguishes this scheduler is :meth:`target_floor_for_car`, which the
simulation engine polls periodically (every
``simulation.reposition_interval_seconds``) to send any currently-idle car
toward a strategically chosen floor before the next call arrives.
"""
from __future__ import annotations

from typing import Callable

from elevator_sim.domain.hall_call import HallCall
from elevator_sim.schedulers.nearest_car import NearestCarScheduler
from elevator_sim.simulation.state import SimulationState

DemandSource = Callable[[float], dict[int, float]]


class ParkingScheduler:
    name = "parking"

    def __init__(
        self,
        strategy: str = "all_to_lobby",
        lobby_floor: int = 1,
        fixed_floors: dict[str, int] | None = None,
        zone_floors: list[int] | None = None,
        demand_weights: dict[int, float] | None = None,
        demand_source: DemandSource | None = None,
    ) -> None:
        self.strategy = strategy
        self.lobby_floor = lobby_floor
        self.fixed_floors = fixed_floors or {}
        self.zone_floors = zone_floors or []
        self.demand_weights = demand_weights or {}
        self.demand_source = demand_source
        self._call_scheduler = NearestCarScheduler()

    def assign_call(self, call: HallCall, state: SimulationState) -> str:
        return self._call_scheduler.assign_call(call, state)

    def target_floor_for_car(self, car_id: str, state: SimulationState) -> int:
        if self.strategy == "all_to_lobby":
            return self.lobby_floor

        if self.strategy == "fixed_per_car":
            return self.fixed_floors.get(car_id, self.lobby_floor)

        if self.strategy == "zoned":
            car_ids = sorted(state.cars.keys())
            if not self.zone_floors or car_id not in car_ids:
                return self.lobby_floor
            zone_index = car_ids.index(car_id) % len(self.zone_floors)
            return self.zone_floors[zone_index]

        if self.strategy == "demand_weighted":
            weights = self.demand_source(state.time) if self.demand_source else self.demand_weights
            if not weights:
                return self.lobby_floor
            return max(weights, key=weights.get)

        raise ValueError(f"Unknown parking strategy: {self.strategy}")
