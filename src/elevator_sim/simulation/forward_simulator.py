"""Lightweight forward simulation used by the Predictive Scheduler to score
candidate assignments (requirements.md 8.5, 9.9, 9.10).

This is intentionally a fast, synchronous approximation of car motion (not a
SimPy process) so it can be evaluated many times per hall-call assignment.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from elevator_sim.domain.elevator import ElevatorCar
from elevator_sim.domain.passenger import Passenger
from elevator_sim.predictors.base import PredictedPassenger


@dataclass
class ForwardSimResult:
    estimated_wait_times: dict[str, float] = field(default_factory=dict)
    stops_simulated: int = 0

    @property
    def mean_wait(self) -> float:
        if not self.estimated_wait_times:
            return 0.0
        return sum(self.estimated_wait_times.values()) / len(self.estimated_wait_times)


def forward_simulate(
    car: ElevatorCar,
    passenger_lookup: dict[str, Passenger],
    future_passengers: list[PredictedPassenger],
    current_time: float,
    horizon_seconds: float,
) -> ForwardSimResult:
    """Walk a car's (already extended) stop plan forward in time and estimate
    the waiting time of every passenger it is expected to pick up within the
    horizon.
    """
    car = car.clone()

    # Attach future passengers as hypothetical pickups so they influence the
    # projected route, but keep track of them separately so we can compute
    # their expected wait relative to their predicted arrival time.
    future_by_floor: dict[int, list[PredictedPassenger]] = {}
    deadline = current_time + horizon_seconds
    for fp in future_passengers:
        if fp.predicted_arrival_time > deadline:
            continue
        # Only the pickup stop is pre-scheduled here (mirroring the real
        # engine, which only commits a destination stop once a passenger has
        # actually boarded) so that a destination coinciding with the car's
        # current floor cannot be sorted ahead of its own pickup stop.
        car.add_stop(fp.origin_floor)
        future_by_floor.setdefault(fp.origin_floor, []).append(fp)

    result = ForwardSimResult()
    t = current_time
    floor = car.current_floor
    onboard_destinations: list[int] = [p.destination_floor for p in car.passengers]

    for stop in list(car.stop_queue):
        floor_diff = abs(stop - floor)
        travel = (
            car.start_delay_seconds + floor_diff * car.seconds_per_floor if floor_diff else 0.0
        )
        t += travel
        if t - current_time > horizon_seconds:
            break

        t += car.door_open_seconds

        # Alighting: passengers already onboard whose destination is this stop.
        alighting = onboard_destinations.count(stop)
        if alighting:
            t += car.alighting_seconds_per_person * alighting
            onboard_destinations = [d for d in onboard_destinations if d != stop]

        # Boarding: real passengers assigned to this floor.
        for pid in car.assigned_pickups.get(stop, []):
            passenger = passenger_lookup.get(pid)
            if passenger is None or passenger.board_time is not None:
                continue
            board_time = max(t, passenger.hall_arrival_time)
            result.estimated_wait_times[pid] = board_time - passenger.hall_arrival_time
            onboard_destinations.append(passenger.destination_floor)
        if car.assigned_pickups.get(stop):
            t += car.boarding_seconds_per_person * len(car.assigned_pickups[stop])

        # Boarding: predicted future passengers.
        for fp in future_by_floor.get(stop, []):
            board_time = max(t, fp.predicted_arrival_time)
            key = f"future::{id(fp)}"
            result.estimated_wait_times[key] = board_time - fp.predicted_arrival_time
            if fp.destination_floor is not None:
                onboard_destinations.append(fp.destination_floor)
            t += car.boarding_seconds_per_person * fp.expected_group_size

        t += car.door_close_seconds
        floor = stop
        result.stops_simulated += 1

    return result
