"""Experiment execution: single runs, multi-seed repetitions, and
scheduler comparisons (requirements.md 12, 18)."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from elevator_sim.config import Config
from elevator_sim.domain.building import Building
from elevator_sim.metrics.elevator_metrics import car_records
from elevator_sim.metrics.passenger_metrics import (
    PassengerMetricsSummary,
    compute_passenger_metrics,
    passenger_records,
)
from elevator_sim.domain.hotel_event import HotelEvent
from elevator_sim.domain.passenger import Passenger
from elevator_sim.predictors.hotel_informed import HotelInformedPredictor
from elevator_sim.predictors.linear_rtd import train_remaining_time_model
from elevator_sim.predictors.no_prediction import NoPredictionPredictor
from elevator_sim.predictors.noisy_oracle import NoisyOraclePredictor
from elevator_sim.predictors.oracle import OraclePredictor
from elevator_sim.predictors.trajectory_based import TrajectoryBasedPredictor
from elevator_sim.predictors.transformer import train_destination_model
from elevator_sim.schedulers.myopic import MyopicScheduler
from elevator_sim.schedulers.nearest_car import NearestCarScheduler
from elevator_sim.schedulers.parking import ParkingScheduler
from elevator_sim.schedulers.predictive import PredictiveScheduler
from elevator_sim.schedulers.prescient import PrescientScheduler
from elevator_sim.simulation.engine import EngineConfig, SimulationEngine, SimulationResult
from elevator_sim.traffic.grid import GridSpace
from elevator_sim.traffic.hotel_schedule import HotelTrafficGenerator
from elevator_sim.traffic.poisson import PoissonTrafficGenerator
from elevator_sim.traffic.trajectory import Trajectory, TrajectoryTrafficGenerator


def build_hotel_events(config: Config) -> list[HotelEvent]:
    return [HotelEvent(**e.model_dump()) for e in config.hotel_events]


def build_building(config: Config) -> Building:
    return Building.uniform(config.building.floors, config.building.lobby_floor)


def build_grid(config: Config) -> GridSpace:
    tcfg = config.trajectory
    return GridSpace(
        width_m=tcfg.floor_width_m, height_m=tcfg.floor_height_m, nx=tcfg.grid_nx, ny=tcfg.grid_ny
    )


def build_arrivals(
    config: Config, rng: np.random.Generator, building: Building
) -> tuple[list[Passenger], list[Trajectory]]:
    pattern = config.traffic.pattern
    arrival_window = config.simulation.warmup_seconds + config.simulation.duration_seconds

    if pattern in ("down_peak", "up_peak"):
        gen = PoissonTrafficGenerator(
            rng=rng,
            building=building,
            pattern=pattern,
            total_arrival_rate_per_hour=config.traffic.total_arrival_rate_per_hour,
        )
        return gen.generate(arrival_window), []

    if pattern == "trajectory":
        grid = build_grid(config)
        gen = TrajectoryTrafficGenerator(
            rng=rng,
            building=building,
            grid=grid,
            walk_start_rate_per_hour=config.trajectory.walk_start_rate_per_hour,
            elevator_bound_probability=config.trajectory.elevator_bound_probability,
        )
        return gen.generate(arrival_window)

    if pattern == "hotel":
        events = build_hotel_events(config)
        gen = HotelTrafficGenerator(
            rng=rng,
            building=building,
            events=events,
            baseline_rate_per_hour=config.traffic.baseline_rate_per_hour,
            baseline_pattern=config.traffic.baseline_pattern,
        )
        return gen.generate(arrival_window), []

    raise ValueError(f"Unsupported traffic pattern: {pattern}")


def build_predictor(config: Config, rng: np.random.Generator, building: Building, seed: int):
    ptype = config.prediction.type
    if ptype == "no_prediction":
        return NoPredictionPredictor()
    if ptype == "oracle":
        return OraclePredictor()
    if ptype == "noisy_oracle":
        err = config.prediction.prediction_error
        return NoisyOraclePredictor(
            rng=rng,
            floor_ids=building.floor_ids,
            recall=err.recall,
            precision=err.precision,
            arrival_time_std_seconds=err.arrival_time_std_seconds,
            destination_accuracy=err.destination_accuracy,
        )
    if ptype == "trajectory":
        tcfg = config.trajectory
        grid = build_grid(config)
        # Train on a held-out trajectory sample (a different RNG stream than
        # the run's actual arrivals) so the model is evaluated on unseen
        # walks, matching the reference paper's train/test split by seed.
        training_seed = tcfg.training_seed if tcfg.training_seed is not None else seed + 1_000_000
        training_rng = np.random.default_rng(training_seed)
        training_gen = TrajectoryTrafficGenerator(
            rng=training_rng,
            building=building,
            grid=grid,
            walk_start_rate_per_hour=tcfg.walk_start_rate_per_hour,
            elevator_bound_probability=tcfg.elevator_bound_probability,
        )
        _, training_trajectories = training_gen.generate(tcfg.training_duration_seconds)

        destination_model = train_destination_model(
            training_trajectories,
            grid,
            epochs=tcfg.training_epochs,
            batch_size=tcfg.training_batch_size,
            seed=training_seed % (2**31),
        )
        remaining_time_model = train_remaining_time_model(training_trajectories)
        return TrajectoryBasedPredictor(destination_model, remaining_time_model, grid)
    if ptype == "hotel_informed":
        return HotelInformedPredictor(
            rng=rng,
            events=build_hotel_events(config),
            baseline_rate_per_hour=config.traffic.baseline_rate_per_hour,
            baseline_destination_floor=building.lobby_floor,
        )
    raise ValueError(f"Unknown prediction type: {ptype}")


def build_parking_scheduler(config: Config, building: Building) -> ParkingScheduler | None:
    if not (config.parking.enabled or config.scheduler.type == "parking"):
        return None
    pcfg = config.parking
    return ParkingScheduler(
        strategy=pcfg.strategy,
        lobby_floor=building.lobby_floor,
        fixed_floors=pcfg.fixed_floors,
        zone_floors=pcfg.zone_floors,
        demand_weights=pcfg.demand_weights,
    )


def build_scheduler(config: Config, rng: np.random.Generator, building: Building, seed: int):
    if not config.scheduler.immediate_assignment:
        raise ValueError("Only immediate_assignment=true is supported in this release.")

    stype = config.scheduler.type
    if stype == "nearest_car":
        return NearestCarScheduler()
    if stype == "myopic":
        return MyopicScheduler()
    if stype == "parking":
        return build_parking_scheduler(config, building)
    if stype == "prescient":
        return PrescientScheduler(
            optimization_horizon_seconds=config.prediction.optimization_horizon_seconds
        )
    if stype == "predictive":
        predictor = build_predictor(config, rng, building, seed)
        return PredictiveScheduler(
            predictor=predictor,
            prediction_horizon_seconds=config.prediction.horizon_seconds,
            optimization_horizon_seconds=config.prediction.optimization_horizon_seconds,
            number_of_continuations=config.prediction.number_of_continuations,
            probability_threshold=config.prediction.probability_threshold,
        )
    raise ValueError(f"Unknown scheduler type: {stype}")


@dataclass
class RunOutcome:
    seed: int
    scheduler_type: str
    result: SimulationResult
    summary: PassengerMetricsSummary
    car_records: list[dict]


def run_single(config: Config, seed: int, scheduler_type: str | None = None) -> RunOutcome:
    random.seed(seed)
    rng = np.random.default_rng(seed)

    cfg = config.model_copy(deep=True)
    if scheduler_type is not None:
        cfg.scheduler.type = scheduler_type

    building = build_building(cfg)
    arrivals, trajectories = build_arrivals(cfg, rng, building)
    scheduler = build_scheduler(cfg, rng, building, seed)

    parking_scheduler = (
        scheduler if cfg.scheduler.type == "parking" else build_parking_scheduler(cfg, building)
    )

    engine_config = EngineConfig(
        warmup_seconds=cfg.simulation.warmup_seconds,
        duration_seconds=cfg.simulation.duration_seconds,
        cooldown_seconds=cfg.simulation.cooldown_seconds,
        reposition_interval_seconds=cfg.parking.reposition_interval_seconds,
    )
    engine = SimulationEngine(
        building=building,
        elevator_specs=cfg.elevators.model_dump(),
        scheduler=scheduler,
        arrivals=arrivals,
        engine_config=engine_config,
        trajectories=trajectories,
        parking_scheduler=parking_scheduler,
    )
    result = engine.run()
    summary = compute_passenger_metrics(
        result.passengers, cfg.simulation.warmup_seconds, cfg.simulation.duration_seconds
    )
    return RunOutcome(
        seed=seed,
        scheduler_type=cfg.scheduler.type,
        result=result,
        summary=summary,
        car_records=car_records(result.cars),
    )


def run_repetitions(config: Config, scheduler_type: str, n_runs: int) -> list[RunOutcome]:
    base_seed = config.experiment.random_seed
    return [
        run_single(config, seed=base_seed + i, scheduler_type=scheduler_type) for i in range(n_runs)
    ]


def run_comparison(
    config: Config, scheduler_types: list[str], n_runs: int = 1
) -> dict[str, list[RunOutcome]]:
    return {stype: run_repetitions(config, stype, n_runs) for stype in scheduler_types}


def aggregate_summaries(outcomes: list[RunOutcome]) -> dict:
    df = pd.DataFrame([o.summary.to_dict() for o in outcomes])
    agg = {}
    for column in df.columns:
        agg[f"{column}_mean"] = float(df[column].mean())
        agg[f"{column}_std"] = float(df[column].std(ddof=0)) if len(df) > 1 else 0.0
    agg["n_runs"] = len(outcomes)
    return agg


def aggregate_full(outcomes: list[RunOutcome]) -> dict:
    """Passenger-metric aggregates plus per-run summed car metrics."""
    agg = aggregate_summaries(outcomes)

    car_totals = []
    for outcome in outcomes:
        cdf = pd.DataFrame(outcome.car_records)
        car_totals.append(
            {
                "empty_distance": cdf["empty_distance_floors"].sum(),
                "stop_count": cdf["stop_count"].sum(),
                "total_distance": cdf["total_distance_floors"].sum(),
            }
        )
    car_df = pd.DataFrame(car_totals)
    for column in car_df.columns:
        agg[f"{column}_mean"] = float(car_df[column].mean())
        agg[f"{column}_std"] = float(car_df[column].std(ddof=0)) if len(car_df) > 1 else 0.0

    return agg


def pooled_waiting_times(outcomes: list[RunOutcome], warmup_seconds: float, duration_seconds: float) -> list[float]:
    from elevator_sim.metrics.passenger_metrics import in_evaluation_window

    waits: list[float] = []
    for outcome in outcomes:
        for p in outcome.result.passengers.values():
            if p.waiting_time is not None and in_evaluation_window(p, warmup_seconds, duration_seconds):
                waits.append(p.waiting_time)
    return waits


def write_run_outputs(output_dir: str | Path, config: Config, outcome: RunOutcome) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(exist_ok=True)

    with open(out / "config.yaml", "w", encoding="utf-8") as f:
        import yaml

        yaml.safe_dump(config.model_dump(), f, allow_unicode=True, sort_keys=False)

    pd.DataFrame(passenger_records(outcome.result.passengers)).to_csv(
        out / "passenger_metrics.csv", index=False
    )
    pd.DataFrame(outcome.car_records).to_csv(out / "elevator_metrics.csv", index=False)
    pd.DataFrame([e.__dict__ for e in outcome.result.event_log]).to_csv(
        out / "event_log.csv", index=False
    )
    pd.DataFrame([a.__dict__ for a in outcome.result.assignment_log]).to_csv(
        out / "assignment_log.csv", index=False
    )

    summary = {
        "scheduler_type": outcome.scheduler_type,
        "seed": outcome.seed,
        **outcome.summary.to_dict(),
    }
    with open(out / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
