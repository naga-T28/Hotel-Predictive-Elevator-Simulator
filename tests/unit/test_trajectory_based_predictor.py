import numpy as np

from elevator_sim.domain.building import Building
from elevator_sim.predictors.linear_rtd import train_remaining_time_model
from elevator_sim.predictors.trajectory_based import TrajectoryBasedPredictor
from elevator_sim.predictors.transformer import train_destination_model
from elevator_sim.simulation.state import SimulationState
from elevator_sim.traffic.grid import GridSpace
from elevator_sim.traffic.trajectory import TrajectoryGenerator


def make_predictor_and_trajectories(seed=1):
    rng = np.random.default_rng(seed)
    grid = GridSpace(nx=50, ny=50)
    gen = TrajectoryGenerator(rng=rng, grid=grid)
    trajectories = gen.generate_stream(
        floor=6, duration_seconds=1800, walk_start_rate_per_hour=324, elevator_bound_probability=0.3
    )
    destination_model = train_destination_model(trajectories, grid, epochs=15, batch_size=16, seed=0)
    rtd_model = train_remaining_time_model(trajectories)
    predictor = TrajectoryBasedPredictor(destination_model, rtd_model, grid)
    return predictor, trajectories, grid


def make_state(trajectories, time):
    building = Building.uniform(8, lobby_floor=1)
    return SimulationState(
        time=time, building=building, cars={}, passengers={}, hall_calls={}, trajectories=trajectories
    )


def test_predictor_ignores_walks_not_yet_started():
    predictor, trajectories, grid = make_predictor_and_trajectories()
    state = make_state(trajectories, time=-1.0)  # before any walk starts

    result = predictor.predict_future_passengers(current_time=-1.0, horizon_seconds=60.0, simulation_state=state)
    assert result == []


def test_predictor_skips_walks_that_already_reached_the_hall():
    predictor, trajectories, grid = make_predictor_and_trajectories()
    bound = next(t for t in trajectories if t.elevator_bound)
    state = make_state(trajectories, time=bound.hall_arrival_time + 100.0)

    result = predictor.predict_future_passengers(
        current_time=bound.hall_arrival_time + 100.0, horizon_seconds=60.0, simulation_state=state
    )
    assert all(pp.true_passenger_id != bound.person_id for pp in result)


def test_predictor_returns_predictions_with_valid_fields():
    predictor, trajectories, grid = make_predictor_and_trajectories(seed=4)
    bound = next(t for t in trajectories if t.elevator_bound and t.hall_arrival_time - t.start_time > 5)
    mid_time = bound.points[len(bound.points) // 2][2]
    state = make_state(trajectories, time=mid_time)

    result = predictor.predict_future_passengers(current_time=mid_time, horizon_seconds=120.0, simulation_state=state)

    match = [pp for pp in result if pp.true_passenger_id == bound.person_id]
    assert len(match) == 1
    pp = match[0]
    assert 0.0 <= pp.probability <= 1.0
    assert pp.predicted_arrival_time >= mid_time
    assert pp.origin_floor == bound.floor
