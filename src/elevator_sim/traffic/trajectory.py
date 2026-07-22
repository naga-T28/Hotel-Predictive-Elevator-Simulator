"""Synthetic 2D pedestrian trajectory generation (requirements.md 9.6).

The reference paper generates floor-by-floor pedestrian trajectories with the
proprietary ``SimTread`` simulator (see requirements.md 2.3 for why this
project cannot reuse it). This module is our from-scratch stand-in: a
straight-line-plus-noise walk from a random room location to either the
elevator hall (an "elevator-bound" trajectory, which becomes a real future
Passenger) or another room (a "decoy" trajectory the destination predictor
must learn to reject).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from elevator_sim.domain.building import Building
from elevator_sim.domain.passenger import Passenger
from elevator_sim.traffic.grid import GridSpace

TrajectoryPoint = tuple[int, int, float]  # (xi, yi, timestamp)


@dataclass(frozen=True)
class FloorLayout:
    width_m: float = 20.0
    height_m: float = 20.0
    elevator_position: tuple[float, float] = (19.0, 19.0)
    num_rooms: int = 15

    def room_positions(self, rng: np.random.Generator) -> list[tuple[float, float]]:
        margin = 1.0
        return [
            (
                float(rng.uniform(margin, self.width_m - margin)),
                float(rng.uniform(margin, self.height_m - margin)),
            )
            for _ in range(self.num_rooms)
        ]


@dataclass
class Trajectory:
    person_id: str
    floor: int
    points: list[TrajectoryPoint]
    elevator_bound: bool
    start_time: float
    hall_arrival_time: float | None

    def points_up_to(self, time: float) -> list[TrajectoryPoint]:
        return [p for p in self.points if p[2] <= time]


class TrajectoryGenerator:
    """Generates one synthetic trajectory per call, and can bulk-generate a
    stream of trajectories (a mix of elevator-bound and decoy walks) for a
    floor over a time window."""

    def __init__(
        self,
        rng: np.random.Generator,
        grid: GridSpace,
        layout: FloorLayout | None = None,
        walking_speed_mps: float = 1.2,
        sampling_interval_seconds: float = 1.0,
        position_noise_m: float = 0.15,
    ) -> None:
        self.rng = rng
        self.grid = grid
        self.layout = layout or FloorLayout(width_m=grid.width_m, height_m=grid.height_m)
        self.walking_speed_mps = walking_speed_mps
        self.sampling_interval_seconds = sampling_interval_seconds
        self.position_noise_m = position_noise_m

    def _walk(self, start_xy: tuple[float, float], end_xy: tuple[float, float], start_time: float):
        start = np.array(start_xy)
        end = np.array(end_xy)
        distance = float(np.linalg.norm(end - start))
        duration = max(distance / self.walking_speed_mps, self.sampling_interval_seconds)
        n_steps = max(1, int(duration / self.sampling_interval_seconds))

        points: list[TrajectoryPoint] = []
        for i in range(1, n_steps + 1):
            frac = min(i / n_steps, 1.0)
            pos = start + frac * (end - start)
            pos += self.rng.normal(0.0, self.position_noise_m, size=2)
            pos = np.clip(pos, [0.0, 0.0], [self.layout.width_m, self.layout.height_m])
            xi, yi = self.grid.to_grid_indices(float(pos[0]), float(pos[1]))
            timestamp = start_time + frac * duration
            points.append((xi, yi, timestamp))
        return points, duration

    def generate_one(
        self,
        person_id: str,
        floor: int,
        start_time: float,
        elevator_bound_probability: float,
        room_positions: list[tuple[float, float]],
    ) -> Trajectory:
        start_pos = room_positions[self.rng.integers(0, len(room_positions))]
        elevator_bound = self.rng.random() < elevator_bound_probability

        if elevator_bound:
            end_pos = self.layout.elevator_position
        else:
            candidates = [p for p in room_positions if p != start_pos]
            end_pos = candidates[self.rng.integers(0, len(candidates))] if candidates else self.layout.elevator_position

        points, duration = self._walk(start_pos, end_pos, start_time)
        hall_arrival_time = start_time + duration if elevator_bound else None

        return Trajectory(
            person_id=person_id,
            floor=floor,
            points=points,
            elevator_bound=elevator_bound,
            start_time=start_time,
            hall_arrival_time=hall_arrival_time,
        )

    def generate_stream(
        self,
        floor: int,
        duration_seconds: float,
        walk_start_rate_per_hour: float,
        elevator_bound_probability: float,
        id_prefix: str = "T",
    ) -> list[Trajectory]:
        """Generate a Poisson stream of walk-start events on one floor, each
        producing either an elevator-bound or decoy trajectory."""
        room_positions = self.layout.room_positions(self.rng)
        rate_per_second = walk_start_rate_per_hour / 3600.0

        trajectories = []
        t = 0.0
        counter = 0
        while True:
            t += self.rng.exponential(1.0 / rate_per_second)
            if t > duration_seconds:
                break
            counter += 1
            trajectories.append(
                self.generate_one(
                    person_id=f"{id_prefix}{floor}_{counter:05d}",
                    floor=floor,
                    start_time=t,
                    elevator_bound_probability=elevator_bound_probability,
                    room_positions=room_positions,
                )
            )
        return trajectories


class TrajectoryTrafficGenerator:
    """Building-wide traffic generator that drives passenger hall arrivals
    from synthetic 2D trajectories rather than a bare Poisson clock.

    Every floor produces a stream of pedestrian walks; only the
    elevator-bound ones become real :class:`Passenger` hall arrivals, but all
    of them (bound and decoy) are returned so a trajectory-based predictor
    can observe partial walks in progress, exactly as the reference paper's
    floor-mounted position tracking system would.
    """

    def __init__(
        self,
        rng: np.random.Generator,
        building: Building,
        grid: GridSpace | None = None,
        walk_start_rate_per_hour: float = 90.0,
        elevator_bound_probability: float = 0.2,
    ) -> None:
        self.rng = rng
        self.building = building
        self.grid = grid or GridSpace()
        self.walk_start_rate_per_hour = walk_start_rate_per_hour
        self.elevator_bound_probability = elevator_bound_probability
        self.generator = TrajectoryGenerator(rng=rng, grid=self.grid)

    def generate(self, duration_seconds: float) -> tuple[list[Passenger], list[Trajectory]]:
        lobby = self.building.lobby_floor
        other_floors = [f for f in self.building.floor_ids if f != lobby]

        all_trajectories: list[Trajectory] = []
        for floor in other_floors:
            all_trajectories.extend(
                self.generator.generate_stream(
                    floor=floor,
                    duration_seconds=duration_seconds,
                    walk_start_rate_per_hour=self.walk_start_rate_per_hour,
                    elevator_bound_probability=self.elevator_bound_probability,
                )
            )

        pairs: list[tuple[Passenger, Trajectory]] = []
        for traj in all_trajectories:
            if not traj.elevator_bound:
                continue
            grid_points = [(self.grid.grid_id(xi, yi), t) for xi, yi, t in traj.points]
            passenger = Passenger(
                passenger_id=traj.person_id,
                hall_arrival_time=round(traj.hall_arrival_time, 3),
                origin_floor=traj.floor,
                destination_floor=lobby,
                generated_at=traj.start_time,
                trajectory=grid_points,
            )
            pairs.append((passenger, traj))

        pairs.sort(key=lambda pair: pair[0].hall_arrival_time)
        passengers: list[Passenger] = []
        for i, (passenger, traj) in enumerate(pairs, start=1):
            passenger.passenger_id = f"P{i:05d}"
            traj.person_id = passenger.passenger_id
            passengers.append(passenger)

        return passengers, all_trajectories
