"""Poisson arrival process traffic generator (requirements.md 6.1, 6.2, 6.4)."""
from __future__ import annotations

import numpy as np

from elevator_sim.domain.building import Building
from elevator_sim.domain.passenger import Passenger


class PoissonTrafficGenerator:
    """Generates passenger hall arrivals from a homogeneous Poisson process.

    Supports the two traffic patterns needed for the paper-reproduction
    experiment (requirements.md 6.4): ``down_peak`` (upper floors -> lobby)
    and ``up_peak`` (lobby -> upper floors).
    """

    def __init__(
        self,
        rng: np.random.Generator,
        building: Building,
        pattern: str,
        total_arrival_rate_per_hour: float,
    ) -> None:
        self.rng = rng
        self.building = building
        self.pattern = pattern
        self.total_arrival_rate_per_hour = total_arrival_rate_per_hour

    def generate(self, duration_seconds: float) -> list[Passenger]:
        lobby = self.building.lobby_floor
        other_floors = [f for f in self.building.floor_ids if f != lobby]
        if not other_floors:
            return []

        if self.pattern == "down_peak":
            rate_per_floor_per_hour = self.total_arrival_rate_per_hour / len(other_floors)
            od_pairs = [(floor, lobby) for floor in other_floors]
        elif self.pattern == "up_peak":
            rate_per_floor_per_hour = self.total_arrival_rate_per_hour / len(other_floors)
            od_pairs = [(lobby, floor) for floor in other_floors]
        else:
            raise ValueError(f"Unsupported traffic pattern: {self.pattern}")

        rate_per_second = rate_per_floor_per_hour / 3600.0

        passengers: list[Passenger] = []
        counter = 0
        for origin, destination in od_pairs:
            t = 0.0
            while True:
                interarrival = self.rng.exponential(1.0 / rate_per_second)
                t += interarrival
                if t > duration_seconds:
                    break
                counter += 1
                passengers.append(
                    Passenger(
                        passenger_id=f"P{counter:05d}",
                        hall_arrival_time=round(t, 3),
                        origin_floor=origin,
                        destination_floor=destination,
                        generated_at=round(t, 3),
                    )
                )

        passengers.sort(key=lambda p: p.hall_arrival_time)
        for i, p in enumerate(passengers, start=1):
            p.passenger_id = f"P{i:05d}"
        return passengers
