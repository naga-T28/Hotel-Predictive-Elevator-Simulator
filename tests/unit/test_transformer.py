import numpy as np

from elevator_sim.predictors.transformer import build_training_set, train_destination_model
from elevator_sim.traffic.grid import GridSpace
from elevator_sim.traffic.trajectory import TrajectoryGenerator


def make_trajectories(seed=1):
    rng = np.random.default_rng(seed)
    grid = GridSpace(nx=50, ny=50)
    gen = TrajectoryGenerator(rng=rng, grid=grid)
    trajectories = gen.generate_stream(
        floor=4, duration_seconds=1800, walk_start_rate_per_hour=324, elevator_bound_probability=0.3
    )
    return trajectories, grid


def test_build_training_set_produces_truncated_prefixes_with_labels():
    trajectories, grid = make_trajectories()
    sequences, labels = build_training_set(trajectories, grid, truncation_fractions=(0.5, 1.0))

    assert len(sequences) == len(labels) == 2 * len(trajectories)
    assert set(labels) <= {0.0, 1.0}
    # the 1.0-fraction prefix should be at least as long as the 0.5 prefix for the same trajectory
    assert len(sequences[1]) >= len(sequences[0])


def test_trained_model_scores_elevator_bound_higher_than_decoy():
    trajectories, grid = make_trajectories(seed=2)
    model = train_destination_model(trajectories, grid, epochs=15, batch_size=16, seed=0)

    bound = [t for t in trajectories if t.elevator_bound]
    decoy = [t for t in trajectories if not t.elevator_bound]
    assert bound and decoy

    def full_sequence(traj):
        return [grid.grid_id(xi, yi) for xi, yi, _ in traj.points]

    bound_probs = [model.predict_probability(full_sequence(t)) for t in bound]
    decoy_probs = [model.predict_probability(full_sequence(t)) for t in decoy]

    assert np.mean(bound_probs) > np.mean(decoy_probs)


def test_predict_probability_handles_empty_sequence():
    trajectories, grid = make_trajectories(seed=3)
    model = train_destination_model(trajectories, grid, epochs=5, batch_size=16, seed=0)
    assert model.predict_probability([]) == 0.0
