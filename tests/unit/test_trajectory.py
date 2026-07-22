import numpy as np

from elevator_sim.traffic.grid import GridSpace
from elevator_sim.traffic.trajectory import FloorLayout, TrajectoryGenerator


def make_generator(seed=0):
    rng = np.random.default_rng(seed)
    grid = GridSpace(nx=50, ny=50)
    return TrajectoryGenerator(rng=rng, grid=grid), grid


def test_elevator_bound_trajectory_ends_near_elevator():
    gen, grid = make_generator()
    layout = gen.layout
    traj = gen.generate_one(
        person_id="P1",
        floor=3,
        start_time=0.0,
        elevator_bound_probability=1.0,  # force elevator-bound
        room_positions=[(2.0, 2.0), (5.0, 5.0)],
    )
    assert traj.elevator_bound is True
    assert traj.hall_arrival_time is not None
    assert traj.hall_arrival_time > traj.start_time
    # last grid cell should be the one containing the elevator position
    last_xi, last_yi, _ = traj.points[-1]
    ex, ey = grid.to_grid_indices(*layout.elevator_position)
    assert abs(last_xi - ex) <= 1
    assert abs(last_yi - ey) <= 1


def test_decoy_trajectory_has_no_hall_arrival_time():
    gen, grid = make_generator()
    traj = gen.generate_one(
        person_id="P2",
        floor=3,
        start_time=0.0,
        elevator_bound_probability=0.0,  # force decoy
        room_positions=[(2.0, 2.0), (5.0, 5.0), (10.0, 3.0)],
    )
    assert traj.elevator_bound is False
    assert traj.hall_arrival_time is None


def test_points_up_to_filters_by_time():
    gen, grid = make_generator()
    traj = gen.generate_one(
        person_id="P1",
        floor=3,
        start_time=0.0,
        elevator_bound_probability=1.0,
        room_positions=[(2.0, 2.0), (18.0, 18.0)],
    )
    midpoint_time = traj.points[len(traj.points) // 2][2]
    partial = traj.points_up_to(midpoint_time)
    assert len(partial) <= len(traj.points)
    assert all(t <= midpoint_time for _, _, t in partial)


def test_generate_stream_produces_mixed_population():
    gen, grid = make_generator(seed=3)
    trajectories = gen.generate_stream(
        floor=5, duration_seconds=1800, walk_start_rate_per_hour=324, elevator_bound_probability=0.2
    )
    assert len(trajectories) > 0
    bound_fraction = sum(t.elevator_bound for t in trajectories) / len(trajectories)
    assert 0.05 < bound_fraction < 0.4  # roughly around 0.2
