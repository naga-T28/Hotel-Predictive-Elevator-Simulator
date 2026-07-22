"""Hall call domain model (requirements.md 7, 16.3)."""
from __future__ import annotations

from dataclasses import dataclass, field

from elevator_sim.domain.passenger import Direction


@dataclass
class HallCall:
    call_id: str
    registered_at: float
    origin_floor: int
    destination_floor: int | None
    direction: Direction
    passenger_ids: list[str] = field(default_factory=list)
    assigned_car_id: str | None = None
