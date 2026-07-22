"""Simulation state shared between the live engine and forward simulation
(requirements.md 5, 8.5)."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from elevator_sim.domain.building import Building
from elevator_sim.domain.elevator import ElevatorCar
from elevator_sim.domain.hall_call import HallCall
from elevator_sim.domain.passenger import Passenger


@dataclass
class SimulationState:
    time: float
    building: Building
    cars: dict[str, ElevatorCar]
    passengers: dict[str, Passenger]
    hall_calls: dict[str, HallCall]
    # Ground-truth passengers not yet arrived at the hall, sorted by
    # hall_arrival_time. Only Oracle-family predictors are allowed to read
    # this; non-prescient schedulers must not use it.
    future_arrivals: list[Passenger] = field(default_factory=list)

    # All synthetic 2D walks in progress on any floor (elevator-bound and
    # decoy alike), for TrajectoryBasedPredictor to observe partially
    # (requirements.md 9.6). Empty unless the trajectory traffic generator
    # is in use.
    trajectories: list = field(default_factory=list)

    def clone(self) -> "SimulationState":
        return copy.deepcopy(self)

    def assign(self, call: HallCall, car_id: str) -> None:
        """Tentatively assign a hall call's passengers to a car's pickup plan."""
        car = self.cars[car_id]
        call.assigned_car_id = car_id
        for passenger_id in call.passenger_ids:
            passenger = self.passengers[passenger_id]
            passenger.assigned_car_id = car_id
            car.assign_pickup(call.origin_floor, passenger_id)

    def waiting_passengers_for_car(self, car_id: str) -> list[Passenger]:
        return [
            p
            for p in self.passengers.values()
            if p.assigned_car_id == car_id and p.board_time is None
        ]
