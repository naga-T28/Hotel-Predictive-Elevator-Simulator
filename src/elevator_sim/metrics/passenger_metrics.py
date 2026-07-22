"""Passenger-level metrics (requirements.md 11.1, 11.2)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from elevator_sim.domain.passenger import Passenger, PassengerStatus


def in_evaluation_window(passenger: Passenger, warmup_seconds: float, duration_seconds: float) -> bool:
    return warmup_seconds <= passenger.hall_arrival_time < (warmup_seconds + duration_seconds)


@dataclass
class PassengerMetricsSummary:
    average_waiting_time: float
    median_waiting_time: float
    p95_waiting_time: float
    max_waiting_time: float
    average_ride_time: float
    average_total_service_time: float
    pct_waited_over_30s: float
    pct_waited_over_60s: float
    left_behind_count: int
    left_behind_rate: float
    transported_count: int
    throughput_per_hour: float
    evaluated_passenger_count: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def compute_passenger_metrics(
    passengers: dict[str, Passenger],
    warmup_seconds: float,
    duration_seconds: float,
) -> PassengerMetricsSummary:
    evaluated = [
        p for p in passengers.values() if in_evaluation_window(p, warmup_seconds, duration_seconds)
    ]

    served = [p for p in evaluated if p.status == PassengerStatus.ARRIVED and p.waiting_time is not None]
    left_behind = [p for p in evaluated if p.status == PassengerStatus.LEFT_BEHIND]
    waits = np.array([p.waiting_time for p in served]) if served else np.array([0.0])
    rides = np.array([p.ride_time for p in served]) if served else np.array([0.0])
    totals = np.array([p.total_service_time for p in served]) if served else np.array([0.0])

    n_evaluated = len(evaluated)
    return PassengerMetricsSummary(
        average_waiting_time=float(np.mean(waits)),
        median_waiting_time=float(np.median(waits)),
        p95_waiting_time=float(np.percentile(waits, 95)),
        max_waiting_time=float(np.max(waits)),
        average_ride_time=float(np.mean(rides)),
        average_total_service_time=float(np.mean(totals)),
        pct_waited_over_30s=float(np.mean(waits >= 30.0)) if served else 0.0,
        pct_waited_over_60s=float(np.mean(waits >= 60.0)) if served else 0.0,
        left_behind_count=len(left_behind),
        left_behind_rate=(len(left_behind) / n_evaluated) if n_evaluated else 0.0,
        transported_count=len(served),
        throughput_per_hour=(len(served) / duration_seconds) * 3600.0 if duration_seconds else 0.0,
        evaluated_passenger_count=n_evaluated,
    )


def passenger_records(passengers: dict[str, Passenger]) -> list[dict]:
    records = []
    for p in passengers.values():
        records.append(
            {
                "passenger_id": p.passenger_id,
                "hall_arrival_time": p.hall_arrival_time,
                "origin_floor": p.origin_floor,
                "destination_floor": p.destination_floor,
                "group_size": p.group_size,
                "luggage_factor": p.luggage_factor,
                "call_time": p.call_time,
                "assigned_car_id": p.assigned_car_id,
                "board_time": p.board_time,
                "arrival_time": p.arrival_time,
                "status": p.status.value,
                "waiting_time": p.waiting_time,
                "ride_time": p.ride_time,
                "total_service_time": p.total_service_time,
            }
        )
    return records
