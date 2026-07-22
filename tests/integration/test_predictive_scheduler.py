"""Requirements.md 20.2: a Predictive Scheduler with future information
disabled must behave the same as the Myopic Scheduler."""
import numpy as np

from elevator_sim.domain.building import Building
from elevator_sim.predictors.no_prediction import NoPredictionPredictor
from elevator_sim.schedulers.myopic import MyopicScheduler
from elevator_sim.schedulers.predictive import PredictiveScheduler
from elevator_sim.simulation.engine import EngineConfig, SimulationEngine
from elevator_sim.traffic.poisson import PoissonTrafficGenerator

ELEVATOR_SPECS = dict(
    count=2,
    capacity_people=15,
    seconds_per_floor=2.5,
    start_delay_seconds=1.0,
    door_open_seconds=1.5,
    door_close_seconds=1.5,
    boarding_seconds_per_person=0.7,
    alighting_seconds_per_person=0.6,
)


def _make_arrivals(building: Building):
    rng = np.random.default_rng(99)
    gen = PoissonTrafficGenerator(rng, building, "down_peak", total_arrival_rate_per_hour=300)
    return gen.generate(600)


def _run(scheduler):
    building = Building.uniform(8, lobby_floor=1)
    arrivals = _make_arrivals(building)
    engine = SimulationEngine(
        building=building,
        elevator_specs=ELEVATOR_SPECS,
        scheduler=scheduler,
        arrivals=arrivals,
        engine_config=EngineConfig(warmup_seconds=0, duration_seconds=600, cooldown_seconds=120),
    )
    return engine.run()


def test_predictive_without_future_info_matches_myopic_assignments():
    myopic_result = _run(MyopicScheduler())
    predictive_result = _run(PredictiveScheduler(predictor=NoPredictionPredictor()))

    myopic_cars = {pid: p.assigned_car_id for pid, p in myopic_result.passengers.items()}
    predictive_cars = {pid: p.assigned_car_id for pid, p in predictive_result.passengers.items()}

    assert myopic_cars == predictive_cars
