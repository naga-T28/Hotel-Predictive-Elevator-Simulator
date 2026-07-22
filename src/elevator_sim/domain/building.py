"""Building domain model (requirements.md 5.1)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Floor:
    floor_id: int
    floor_type: str = "guest_room"
    room_count: int = 0
    occupancy_rate: float = 0.0
    is_elevator_serviceable: bool = True
    population: int = 0


@dataclass
class Building:
    floors: list[Floor]
    lobby_floor: int = 1

    @property
    def floor_ids(self) -> list[int]:
        return [f.floor_id for f in self.floors]

    @property
    def min_floor(self) -> int:
        return min(self.floor_ids)

    @property
    def max_floor(self) -> int:
        return max(self.floor_ids)

    def is_valid_floor(self, floor_id: int) -> bool:
        return floor_id in self.floor_ids

    @classmethod
    def uniform(cls, num_floors: int, lobby_floor: int = 1) -> "Building":
        floors = [
            Floor(
                floor_id=i,
                floor_type="lobby" if i == lobby_floor else "guest_room",
            )
            for i in range(1, num_floors + 1)
        ]
        return cls(floors=floors, lobby_floor=lobby_floor)
