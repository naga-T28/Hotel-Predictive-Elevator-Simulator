"""Floor-plane grid discretization (requirements.md 9.6).

Mirrors the quantization scheme in Zhang et al., *Transformer Networks for
Predictive Group Elevator Control* (ECC 2022): a floor plane bounded by
``[0, width] x [0, height]`` is discretized into an ``Nx * Ny`` grid, and a
2D position is reduced to a single grid index ``p* = y* * Nx + x*``.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GridSpace:
    width_m: float = 20.0
    height_m: float = 20.0
    nx: int = 50
    ny: int = 50

    @property
    def dx(self) -> float:
        return self.width_m / self.nx

    @property
    def dy(self) -> float:
        return self.height_m / self.ny

    def to_grid_indices(self, x: float, y: float) -> tuple[int, int]:
        xi = min(max(int(x / self.dx), 0), self.nx - 1)
        yi = min(max(int(y / self.dy), 0), self.ny - 1)
        return xi, yi

    def grid_id(self, xi: int, yi: int) -> int:
        return yi * self.nx + xi

    @property
    def num_cells(self) -> int:
        return self.nx * self.ny

    def to_grid_id(self, x: float, y: float) -> int:
        xi, yi = self.to_grid_indices(x, y)
        return self.grid_id(xi, yi)
