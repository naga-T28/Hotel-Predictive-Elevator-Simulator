"""Scheduler common interface (requirements.md 8)."""
from __future__ import annotations

from typing import Protocol

from elevator_sim.domain.hall_call import HallCall
from elevator_sim.simulation.state import SimulationState


class Scheduler(Protocol):
    name: str

    def assign_call(self, call: HallCall, state: SimulationState) -> str:
        """Return the car_id that should serve this hall call."""
        ...
