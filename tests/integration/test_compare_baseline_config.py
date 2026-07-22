import pandas as pd
import pytest
import yaml

from elevator_sim.cli import main

SMOKE_CONFIG = {
    "experiment": {"name": "smoke_test", "random_seed": 1, "repetitions": 2},
    "building": {"floors": 8, "lobby_floor": 1},
    "elevators": {
        "count": 3,
        "capacity_people": 15,
        "seconds_per_floor": 2.5,
        "start_delay_seconds": 1.0,
        "door_open_seconds": 1.5,
        "door_close_seconds": 1.5,
        "boarding_seconds_per_person": 0.7,
        "alighting_seconds_per_person": 0.6,
    },
    "traffic": {"pattern": "down_peak", "total_arrival_rate_per_hour": 453.6},
    "scheduler": {"type": "myopic", "immediate_assignment": True},
    "prediction": {
        "type": "no_prediction",
        "horizon_seconds": 10,
        "optimization_horizon_seconds": 60,
        "probability_threshold": 0.2,
        "number_of_continuations": 1,
    },
    "simulation": {"warmup_seconds": 30, "duration_seconds": 180, "cooldown_seconds": 30},
}


def _write_config(path, **overrides):
    data = yaml.safe_load(yaml.safe_dump(SMOKE_CONFIG))
    for section, values in overrides.items():
        data.setdefault(section, {}).update(values)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    return path


def test_compare_with_baseline_config_writes_both_paired_comparisons(tmp_path):
    main_config = _write_config(tmp_path / "main.yaml")
    baseline_config = _write_config(
        tmp_path / "baseline.yaml", scheduler={"type": "myopic", "immediate_assignment": True}
    )
    output_dir = tmp_path / "out"

    main(
        [
            "compare",
            "--config", str(main_config),
            "--schedulers", "myopic,nearest_car",
            "--baseline", "nearest_car",
            "--baseline-config", str(baseline_config),
            "--baseline-label", "baseline",
            "--runs", "2",
            "--output", str(output_dir),
        ]
    )

    assert (output_dir / "baseline").is_dir()
    assert (output_dir / "myopic").is_dir()
    assert (output_dir / "nearest_car").is_dir()

    summary = pd.read_csv(output_dir / "comparison_summary.csv", index_col=0)
    assert "baseline" in summary.index

    # Primary paired_comparisons.csv is vs the explicit --baseline (nearest_car);
    # since that differs from --baseline-label, a second file vs the true
    # baseline condition should also be written.
    paired = pd.read_csv(output_dir / "paired_comparisons.csv", index_col=0)
    assert "baseline" in paired.index
    assert (paired["baseline_scheduler"] == "nearest_car").all()

    paired_vs_baseline = pd.read_csv(
        output_dir / "paired_comparisons_vs_baseline.csv", index_col=0
    )
    assert set(paired_vs_baseline.index) == {"myopic", "nearest_car"}
    assert (paired_vs_baseline["baseline_scheduler"] == "baseline").all()


def test_compare_rejects_mismatched_baseline_config_seed(tmp_path):
    main_config = _write_config(tmp_path / "main.yaml")
    mismatched_baseline = _write_config(
        tmp_path / "baseline.yaml", experiment={"name": "smoke_test", "random_seed": 99, "repetitions": 2}
    )
    output_dir = tmp_path / "out"

    with pytest.raises(ValueError, match="random_seed"):
        main(
            [
                "compare",
                "--config", str(main_config),
                "--schedulers", "myopic",
                "--baseline-config", str(mismatched_baseline),
                "--runs", "1",
                "--output", str(output_dir),
            ]
        )
