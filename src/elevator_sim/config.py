"""YAML configuration schema and loader (requirements.md 13.1)."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ExperimentConfig(BaseModel):
    name: str = "experiment"
    random_seed: int = 42
    repetitions: int = 1


class BuildingConfig(BaseModel):
    floors: int = 8
    lobby_floor: int = 1


class ElevatorsConfig(BaseModel):
    count: int = 3
    capacity_people: float = 15
    seconds_per_floor: float = 2.5
    start_delay_seconds: float = 1.0
    door_open_seconds: float = 1.5
    door_close_seconds: float = 1.5
    boarding_seconds_per_person: float = 0.7
    alighting_seconds_per_person: float = 0.6


class TrafficConfig(BaseModel):
    pattern: str = "down_peak"  # down_peak | up_peak | trajectory | hotel
    total_arrival_rate_per_hour: float = 453.6
    # Only used when pattern == "hotel": an optional flat Poisson traffic
    # floor blended in alongside the event-driven bursts.
    baseline_rate_per_hour: float = 0.0
    baseline_pattern: str = "down_peak"


class TrajectoryConfig(BaseModel):
    grid_nx: int = 50
    grid_ny: int = 50
    floor_width_m: float = 20.0
    floor_height_m: float = 20.0
    walking_speed_mps: float = 1.2
    # Total pedestrian walk-start rate per floor (all destinations, not just
    # the elevator). Default reproduces the paper's medium arrival regime:
    # 64.8 pph elevator-bound / 0.2 PPGE prior = 324 pph total foot traffic.
    walk_start_rate_per_hour: float = 324.0
    elevator_bound_probability: float = 0.2
    training_epochs: int = 20
    training_batch_size: int = 20
    training_duration_seconds: float = 600.0
    training_seed: int | None = None


class SchedulerConfig(BaseModel):
    type: str = "myopic"  # myopic | nearest_car | prescient | predictive | parking
    immediate_assignment: bool = True


class ParkingConfig(BaseModel):
    enabled: bool = False
    strategy: str = "all_to_lobby"  # all_to_lobby | fixed_per_car | zoned | demand_weighted
    fixed_floors: dict[str, int] = Field(default_factory=dict)
    zone_floors: list[int] = Field(default_factory=list)
    demand_weights: dict[int, float] = Field(default_factory=dict)
    reposition_interval_seconds: float = 30.0


class HotelEventConfig(BaseModel):
    event_id: str
    event_type: str
    # Seconds since simulation start (internal time unit, requirements.md 4.2).
    start_time: float
    end_time: float = 0.0  # equal to (or less than) start_time => a point-in-time event
    source_floors: list[int]
    destination_distribution: dict[int, float]
    expected_people: int
    spread_seconds: float = 300.0
    group_size: int = 1
    luggage_factor: float = 1.0


class PredictionErrorConfig(BaseModel):
    recall: float = 0.80
    precision: float = 0.90
    arrival_time_std_seconds: float = 2.0
    destination_accuracy: float = 0.95


class PredictionConfig(BaseModel):
    type: str = "no_prediction"  # no_prediction | oracle | noisy_oracle | trajectory | hotel_informed
    horizon_seconds: float = 10.0
    optimization_horizon_seconds: float = 120.0
    probability_threshold: float = 0.2
    number_of_continuations: int = 1
    prediction_error: PredictionErrorConfig = Field(default_factory=PredictionErrorConfig)


class SimulationConfig(BaseModel):
    warmup_seconds: float = 300.0
    duration_seconds: float = 3600.0
    cooldown_seconds: float = 300.0


class Config(BaseModel):
    experiment: ExperimentConfig = Field(default_factory=ExperimentConfig)
    building: BuildingConfig = Field(default_factory=BuildingConfig)
    elevators: ElevatorsConfig = Field(default_factory=ElevatorsConfig)
    traffic: TrafficConfig = Field(default_factory=TrafficConfig)
    trajectory: TrajectoryConfig = Field(default_factory=TrajectoryConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    parking: ParkingConfig = Field(default_factory=ParkingConfig)
    prediction: PredictionConfig = Field(default_factory=PredictionConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    hotel_events: list[HotelEventConfig] = Field(default_factory=list)


def load_config(path: str | Path) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return Config.model_validate(raw)
