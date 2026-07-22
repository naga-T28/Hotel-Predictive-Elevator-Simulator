"""Hotel event domain model (requirements.md 6.3, 16.5)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HotelEvent:
    event_id: str
    event_type: str
    start_time: float
    end_time: float
    source_floors: list[int]
    destination_distribution: dict[int, float]
    expected_people: int

    # Extensions beyond the minimal 16.5 dataclass, needed to drive a
    # concrete passenger generator (requirements.md 5.5, 6.3):
    spread_seconds: float = 300.0
    group_size: int = 1
    luggage_factor: float = 1.0
    prediction_time_offset_seconds: float = 0.0
