"""Hotel-specific demand generation from event schedules (requirements.md
6.3, 8.6). This is a project-specific extension beyond the reference paper's
scope (which only models generic down-peak Poisson traffic); see
DESIGN_DECISIONS.md items 4 and 9 for the modeling choices made here."""
from __future__ import annotations

import numpy as np

from elevator_sim.domain.building import Building
from elevator_sim.domain.hotel_event import HotelEvent
from elevator_sim.domain.passenger import Passenger
from elevator_sim.traffic.poisson import PoissonTrafficGenerator


def _sample_destination(rng: np.random.Generator, destination_distribution: dict[int, float]) -> int:
    floors = list(destination_distribution.keys())
    weights = np.array(list(destination_distribution.values()), dtype=float)
    weights = weights / weights.sum()
    return int(rng.choice(floors, p=weights))


class HotelTrafficGenerator:
    """Turns a list of :class:`HotelEvent` into concrete passenger arrivals,
    optionally blended with a baseline Poisson traffic floor
    (requirements.md 6.2 "Two-way traffic" / "Burst traffic")."""

    def __init__(
        self,
        rng: np.random.Generator,
        building: Building,
        events: list[HotelEvent],
        baseline_rate_per_hour: float = 0.0,
        baseline_pattern: str = "down_peak",
    ) -> None:
        self.rng = rng
        self.building = building
        self.events = events
        self.baseline_rate_per_hour = baseline_rate_per_hour
        self.baseline_pattern = baseline_pattern

    def _generate_event_arrivals(self, event: HotelEvent, duration_seconds: float) -> list[Passenger]:
        center = (event.start_time + event.end_time) / 2.0 if event.end_time > event.start_time else event.start_time
        group_size = max(1, event.group_size)
        n_groups = max(1, -(-event.expected_people // group_size))  # ceil division

        remaining = event.expected_people
        arrivals: list[Passenger] = []
        for _ in range(n_groups):
            size = min(group_size, remaining)
            if size <= 0:
                break
            remaining -= size

            t = float(self.rng.normal(center, max(event.spread_seconds, 1e-6)))
            t = min(max(t, 0.0), duration_seconds - 1e-3)

            origin = int(self.rng.choice(event.source_floors))
            destination_distribution = {
                floor: weight for floor, weight in event.destination_distribution.items() if floor != origin
            }
            if not destination_distribution:
                continue
            destination = _sample_destination(self.rng, destination_distribution)

            arrivals.append(
                Passenger(
                    passenger_id="",  # assigned after global sort
                    hall_arrival_time=round(t, 3),
                    origin_floor=origin,
                    destination_floor=destination,
                    group_id=event.event_id,
                    group_size=size,
                    luggage_factor=event.luggage_factor,
                    generated_at=round(t, 3),
                )
            )
        return arrivals

    def generate(self, duration_seconds: float) -> list[Passenger]:
        arrivals: list[Passenger] = []
        for event in self.events:
            arrivals.extend(self._generate_event_arrivals(event, duration_seconds))

        if self.baseline_rate_per_hour > 0:
            baseline_gen = PoissonTrafficGenerator(
                rng=self.rng,
                building=self.building,
                pattern=self.baseline_pattern,
                total_arrival_rate_per_hour=self.baseline_rate_per_hour,
            )
            arrivals.extend(baseline_gen.generate(duration_seconds))

        arrivals.sort(key=lambda p: p.hall_arrival_time)
        for i, p in enumerate(arrivals, start=1):
            p.passenger_id = f"H{i:05d}"
        return arrivals
