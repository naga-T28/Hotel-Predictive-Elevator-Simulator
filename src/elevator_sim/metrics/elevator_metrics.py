"""Car-level metrics (requirements.md 11.3)."""
from __future__ import annotations

from elevator_sim.domain.elevator import ElevatorCar


def car_records(cars: dict[str, ElevatorCar]) -> list[dict]:
    records = []
    for car in cars.values():
        total_time = car.busy_seconds + car.idle_seconds
        avg_load = car.load_area_seconds / total_time if total_time > 0 else 0.0
        records.append(
            {
                "car_id": car.car_id,
                "total_distance_floors": car.total_distance,
                "empty_distance_floors": car.empty_distance,
                "loaded_distance_floors": car.total_distance - car.empty_distance,
                "stop_count": car.stop_count,
                "door_open_count": car.door_open_count,
                "average_load": avg_load,
                "average_occupancy_rate": avg_load / car.capacity_people if car.capacity_people else 0.0,
                "busy_seconds": car.busy_seconds,
                "idle_seconds": car.idle_seconds,
            }
        )
    return records


def total_empty_distance(cars: dict[str, ElevatorCar]) -> float:
    return sum(car.empty_distance for car in cars.values())


def total_stop_count(cars: dict[str, ElevatorCar]) -> int:
    return sum(car.stop_count for car in cars.values())
