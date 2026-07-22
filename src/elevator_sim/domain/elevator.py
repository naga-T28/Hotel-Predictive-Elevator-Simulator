"""Elevator car domain model (requirements.md 5.2, 5.3, 16.2)."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum

from elevator_sim.domain.passenger import Direction, Passenger


class CarState(str, Enum):
    IDLE = "IDLE"
    MOVING_UP = "MOVING_UP"
    MOVING_DOWN = "MOVING_DOWN"
    DOOR_OPENING = "DOOR_OPENING"
    DOOR_OPEN = "DOOR_OPEN"
    BOARDING = "BOARDING"
    ALIGHTING = "ALIGHTING"
    DOOR_CLOSING = "DOOR_CLOSING"


@dataclass
class ElevatorCar:
    car_id: str
    current_floor: int
    capacity_people: float
    seconds_per_floor: float
    start_delay_seconds: float
    door_open_seconds: float
    door_close_seconds: float
    boarding_seconds_per_person: float
    alighting_seconds_per_person: float

    position: float = 0.0
    direction: Direction = Direction.IDLE
    state: CarState = CarState.IDLE
    current_load: float = 0.0

    passengers: list[Passenger] = field(default_factory=list)
    # floor -> list of passenger_ids that this car must pick up at that floor
    assigned_pickups: dict[int, list[str]] = field(default_factory=dict)
    stop_queue: list[int] = field(default_factory=list)

    total_distance: float = 0.0
    empty_distance: float = 0.0
    stop_count: int = 0
    door_open_count: int = 0
    busy_seconds: float = 0.0
    idle_seconds: float = 0.0
    load_area_seconds: float = 0.0  # for time-weighted average load

    def __post_init__(self) -> None:
        self.position = float(self.current_floor)

    @property
    def assigned_calls(self) -> list[str]:
        return [pid for pids in self.assigned_pickups.values() for pid in pids]

    def travel_time(self, target_floor: int) -> float:
        floor_diff = abs(target_floor - self.current_floor)
        if floor_diff == 0:
            return 0.0
        return self.start_delay_seconds + floor_diff * self.seconds_per_floor

    def can_accept(self, occupancy: float) -> bool:
        return self.current_load + occupancy <= self.capacity_people + 1e-9

    def add_stop(self, floor: int) -> None:
        """Insert a stop maintaining a simple SCAN order relative to current motion."""
        if floor in self.stop_queue:
            return

        if not self.stop_queue:
            self.stop_queue.append(floor)
            return

        direction = self.direction
        if direction == Direction.IDLE:
            direction = Direction.UP if floor >= self.current_floor else Direction.DOWN

        same_direction = [
            f for f in self.stop_queue
            if (f - self.current_floor) * direction.value >= 0
        ]
        opposite_direction = [f for f in self.stop_queue if f not in same_direction]

        if (floor - self.current_floor) * direction.value >= 0:
            same_direction.append(floor)
            same_direction = sorted(set(same_direction), key=lambda f: f * direction.value)
        else:
            opposite_direction.append(floor)
            opposite_direction = sorted(set(opposite_direction), key=lambda f: -f * direction.value)

        self.stop_queue = same_direction + opposite_direction

    def assign_pickup(self, floor: int, passenger_id: str) -> None:
        self.assigned_pickups.setdefault(floor, []).append(passenger_id)
        self.add_stop(floor)

    def occupancy_rate(self) -> float:
        if self.capacity_people <= 0:
            return 0.0
        return self.current_load / self.capacity_people

    def clone(self) -> "ElevatorCar":
        return copy.deepcopy(self)
