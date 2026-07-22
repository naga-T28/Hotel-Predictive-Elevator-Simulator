"""Command line interface (requirements.md 18)."""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

from elevator_sim.config import load_config
from elevator_sim.experiments.runner import (
    RunOutcome,
    aggregate_full,
    aggregate_summaries,
    pooled_waiting_times,
    run_comparison,
    run_repetitions,
    run_single,
    write_run_outputs,
)
from elevator_sim.visualization.plots import (
    plot_elevator_position_timeline,
    plot_occupancy_timeline,
    plot_scheduler_comparison,
    plot_waiting_time_distribution,
)


def _write_single_run_figures(output_dir: Path, outcome: RunOutcome, warmup: float, duration: float) -> None:
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    waits = pooled_waiting_times([outcome], warmup, duration)
    plot_waiting_time_distribution(
        {outcome.scheduler_type: waits}, figures_dir / "waiting_time_distribution.png"
    )

    event_df = pd.DataFrame([e.__dict__ for e in outcome.result.event_log])
    if not event_df.empty:
        plot_elevator_position_timeline(event_df, figures_dir / "elevator_position_timeline.png")
        plot_occupancy_timeline(event_df, figures_dir / "occupancy_timeline.png")


def cmd_run(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    seed = args.seed if args.seed is not None else config.experiment.random_seed
    outcome = run_single(config, seed=seed)

    output_dir = Path(args.output or f"outputs/{config.experiment.name}")
    write_run_outputs(output_dir, config, outcome)
    _write_single_run_figures(
        output_dir, outcome, config.simulation.warmup_seconds, config.simulation.duration_seconds
    )

    print(f"[run] scheduler={outcome.scheduler_type} seed={seed}")
    print(json.dumps(outcome.summary.to_dict(), indent=2, ensure_ascii=False))
    print(f"Outputs written to {output_dir}")


def cmd_compare(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    scheduler_types = [s.strip() for s in args.schedulers.split(",") if s.strip()]
    results = run_comparison(config, scheduler_types, n_runs=args.runs)

    output_dir = Path(args.output or f"outputs/{config.experiment.name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    aggregate_rows = {}
    waits_by_scheduler = {}
    for scheduler_type, outcomes in results.items():
        scheduler_dir = output_dir / scheduler_type
        write_run_outputs(scheduler_dir, config, outcomes[0])
        aggregate_rows[scheduler_type] = aggregate_full(outcomes)
        waits_by_scheduler[scheduler_type] = pooled_waiting_times(
            outcomes, config.simulation.warmup_seconds, config.simulation.duration_seconds
        )

    aggregate_df = pd.DataFrame(aggregate_rows).T
    aggregate_df.to_csv(output_dir / "comparison_summary.csv")
    with open(output_dir / "comparison_summary.json", "w", encoding="utf-8") as f:
        json.dump(aggregate_rows, f, indent=2, ensure_ascii=False)

    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    plot_waiting_time_distribution(waits_by_scheduler, figures_dir / "waiting_time_distribution.png")
    plot_scheduler_comparison(aggregate_df, figures_dir / "scheduler_comparison.png")

    print(aggregate_df[[c for c in aggregate_df.columns if c.endswith("_mean")]].to_string())
    print(f"Outputs written to {output_dir}")


def _run_one(config_path: str, seed: int, scheduler_type: str) -> RunOutcome:
    config = load_config(config_path)
    return run_single(config, seed=seed, scheduler_type=scheduler_type)


def cmd_experiment(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    base_seed = config.experiment.random_seed
    seeds = [base_seed + i for i in range(args.runs)]

    if args.parallel and args.parallel > 1:
        with ProcessPoolExecutor(max_workers=args.parallel) as pool:
            outcomes = list(
                pool.map(_run_one, [args.config] * len(seeds), seeds, [config.scheduler.type] * len(seeds))
            )
    else:
        outcomes = run_repetitions(config, config.scheduler.type, args.runs)

    output_dir = Path(args.output or f"outputs/{config.experiment.name}")
    runs_dir = output_dir / "runs"
    for outcome in outcomes:
        write_run_outputs(runs_dir / f"seed_{outcome.seed}", config, outcome)

    aggregate = aggregate_full(outcomes)
    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(aggregate, f, indent=2, ensure_ascii=False)

    waits = pooled_waiting_times(
        outcomes, config.simulation.warmup_seconds, config.simulation.duration_seconds
    )
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    plot_waiting_time_distribution({config.scheduler.type: waits}, figures_dir / "waiting_time_distribution.png")

    print(json.dumps(aggregate, indent=2, ensure_ascii=False))
    print(f"Outputs written to {output_dir}")


def cmd_plot(args: argparse.Namespace) -> None:
    input_dir = Path(args.input)
    figures_dir = input_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    passenger_csv = input_dir / "passenger_metrics.csv"
    event_csv = input_dir / "event_log.csv"

    if passenger_csv.exists():
        pdf = pd.read_csv(passenger_csv)
        waits = pdf.loc[pdf["status"] == "ARRIVED", "waiting_time"].dropna().tolist()
        scheduler_name = input_dir.name
        plot_waiting_time_distribution({scheduler_name: waits}, figures_dir / "waiting_time_distribution.png")

    if event_csv.exists():
        edf = pd.read_csv(event_csv)
        if not edf.empty:
            plot_elevator_position_timeline(edf, figures_dir / "elevator_position_timeline.png")
            plot_occupancy_timeline(edf, figures_dir / "occupancy_timeline.png")

    print(f"Figures written to {figures_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="elevator_sim")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run a single experiment")
    p_run.add_argument("--config", required=True)
    p_run.add_argument("--output")
    p_run.add_argument("--seed", type=int)
    p_run.set_defaults(func=cmd_run)

    p_compare = sub.add_parser("compare", help="Compare multiple scheduler types")
    p_compare.add_argument("--config", required=True)
    p_compare.add_argument("--schedulers", required=True, help="Comma-separated scheduler types")
    p_compare.add_argument("--runs", type=int, default=1)
    p_compare.add_argument("--output")
    p_compare.set_defaults(func=cmd_compare)

    p_experiment = sub.add_parser("experiment", help="Run multiple random seeds")
    p_experiment.add_argument("--config", required=True)
    p_experiment.add_argument("--runs", type=int, default=50)
    p_experiment.add_argument("--parallel", type=int, default=1)
    p_experiment.add_argument("--output")
    p_experiment.set_defaults(func=cmd_experiment)

    p_plot = sub.add_parser("plot", help="Regenerate figures from an output directory")
    p_plot.add_argument("--input", required=True)
    p_plot.set_defaults(func=cmd_plot)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
