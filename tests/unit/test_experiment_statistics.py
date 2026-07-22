from types import SimpleNamespace

import pytest

from elevator_sim.experiments.runner import paired_comparison


def outcome(seed: int, average_waiting_time: float):
    return SimpleNamespace(
        seed=seed,
        summary=SimpleNamespace(average_waiting_time=average_waiting_time),
    )


def test_paired_comparison_matches_runs_by_seed():
    results = {
        "myopic": [outcome(1, 20.0), outcome(2, 30.0)],
        # Deliberately reverse order to verify pairing is by seed, not list position.
        "predictive": [outcome(2, 27.0), outcome(1, 18.0)],
    }

    comparison = paired_comparison(results, "myopic")["predictive"]

    assert comparison["n_pairs"] == 2
    assert comparison["mean_waiting_time_difference_seconds"] == pytest.approx(-2.5)
    assert comparison["improvement_pct"] == pytest.approx(10.0)
    assert comparison["difference_ci95_high"] < 0.0


def test_paired_comparison_rejects_unknown_baseline():
    with pytest.raises(ValueError, match="Unknown baseline scheduler"):
        paired_comparison({"myopic": [outcome(1, 20.0)]}, "missing")
