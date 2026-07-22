import numpy as np

from elevator_sim.predictors.linear_rtd import train_remaining_time_model
from elevator_sim.traffic.grid import GridSpace
from elevator_sim.traffic.trajectory import TrajectoryGenerator


def make_trajectories(seed=0, n_floors=3):
    rng = np.random.default_rng(seed)
    grid = GridSpace(nx=50, ny=50)
    gen = TrajectoryGenerator(rng=rng, grid=grid)
    trajectories = []
    for floor in range(2, 2 + n_floors):
        trajectories.extend(
            gen.generate_stream(
                floor=floor, duration_seconds=1800, walk_start_rate_per_hour=324, elevator_bound_probability=0.3
            )
        )
    return trajectories


def test_remaining_time_model_fits_and_predicts_nonnegative():
    trajectories = make_trajectories()
    model = train_remaining_time_model(trajectories)

    bound = next(t for t in trajectories if t.elevator_bound)
    for xi, yi, _t in bound.points:
        assert model.predict(xi, yi) >= 0.0


def test_remaining_time_decreases_towards_destination():
    trajectories = make_trajectories()
    model = train_remaining_time_model(trajectories)

    bound = next(t for t in trajectories if t.elevator_bound and len(t.points) >= 4)
    xi0, yi0, _ = bound.points[0]
    xi1, yi1, _ = bound.points[-1]

    assert model.predict(xi1, yi1) < model.predict(xi0, yi0)


def test_remaining_time_model_rmse_is_reasonably_small():
    trajectories = make_trajectories(seed=5)
    model = train_remaining_time_model(trajectories)
    rmse = model.rmse(trajectories)
    assert rmse < 15.0  # sanity bound; paper reports RMSE ~1.29s on real data
