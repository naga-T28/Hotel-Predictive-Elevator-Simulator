# AGENTS.md

## Project Overview

This repository contains a discrete-event simulator for predictive group
elevator control in hotels. Its purpose is to evaluate whether hotel schedule
information and predicted passenger arrivals improve elevator service under
checkout, breakfast, banquet, and trajectory-based traffic.

The accompanying paper is written in Japanese. User-facing reports,
experimental interpretations, and additions intended for the paper should
therefore be written in Japanese unless the user requests another language.

## Sources of Truth

Consult the following files before making material changes:

1. `requirements.md` for functional, experimental, input, and output requirements.
2. `EXPERIMENT_VALIDATION_PLAN.md` for the comparison design required to support
   claims in the accompanying paper.
3. `DESIGN_DECISIONS.md` for intentional implementation choices and known
   differences from the referenced studies.
4. `README.md` for supported commands and documented limitations.

If these documents conflict, preserve observable behavior until the conflict is
identified explicitly. For experimental validity, prefer the stricter controls
in `EXPERIMENT_VALIDATION_PLAN.md`, and update `requirements.md` when a decision
changes the required behavior.

## Repository Layout

- `src/elevator_sim/`: simulator implementation.
- `configs/`: reproducible YAML experiment configurations.
- `tests/unit/`: isolated component and statistical tests.
- `tests/integration/`: end-to-end simulation behavior tests.
- `outputs/`: generated experiment results; do not treat these as source code.
- `requirements.md`: system and experiment requirements.
- `EXPERIMENT_VALIDATION_PLAN.md`: protocol for paper-quality experiments.

## Development Rules

- Preserve deterministic behavior for a fixed configuration and random seed.
- Use `numpy.random.Generator` instances derived from the run seed. Do not add
  unseeded randomness.
- Ensure scheduler comparisons use the same seed set and the same generated
  passenger demand for every compared method.
- Do not silently change elevator, traffic, parking, or prediction parameters
  between control methods.
- Keep traffic generation independent from prediction errors. In particular,
  an event-time error must modify the schedule seen by the predictor, not the
  actual passenger generation time.
- Do not use generated files under `outputs/` as hidden inputs to a simulation
  unless an experiment explicitly declares them as input data.
- Preserve existing user-generated outputs unless the user explicitly requests
  regeneration or deletion.
- Add or update tests for every behavioral change.
- Keep configuration schema changes backward compatible when practical.
- Record intentional modeling assumptions in `DESIGN_DECISIONS.md`.
- Update `README.md` when commands, output files, or supported configuration
  values change.

## Experimental Validity

Experiments intended to support the paper must follow these rules:

- Use at least 50 seed-matched repetitions for the primary comparison unless a
  smaller exploratory run is clearly labeled as preliminary.
- Compare, at minimum, a no-future-information baseline, parking-only control,
  hotel-informed predictive control with the same parking policy, and a
  prescient reference condition.
- Change only one experimental factor at a time.
- Report mean, standard deviation, and 95% confidence interval for each primary
  metric.
- Report the seed-paired difference from the declared baseline and its 95%
  confidence interval.
- Treat average waiting time as the primary outcome. Also report the 95th
  percentile waiting time, waits over 30 and 60 seconds, left-behind rate,
  total service time, empty travel distance, total travel distance, and stops.
- Do not directly rank checkout, breakfast, and banquet scenarios by raw metric
  values because their durations and demand profiles differ. Compare control
  methods within each scenario.
- Preserve every per-seed result needed to reproduce aggregate statistics.
- Save the effective configuration, seed set, and code revision with final
  paper results.
- Do not claim that predictive control is effective when the paired confidence
  interval includes zero. Report that no clear difference was observed.
- Clearly distinguish simulated evidence, inference, and limitations.

## Paper and Implementation Consistency

Do not describe functionality as implemented unless it exists in the current
code and is exercised by the reported experiment. In particular:

- The current predictive scheduler primarily minimizes estimated mean waiting
  time when assigning a newly observed hall call.
- Periodic parking repositioning is separate from hall-call assignment.
- Assigned calls are not globally reassigned at each rolling-horizon update.
- The full multi-objective function described in the paper, including the 95th
  percentile, crowding, stop count, and empty travel, is not yet the scheduler's
  implemented optimization objective.

Until those capabilities are implemented and tested, describe the method as
predictive sequential car assignment with periodic parking repositioning, not
as a complete implementation of the paper's multi-objective rolling-horizon
optimization.

## Verification

Use the repository virtual environment when available:

```bash
.venv/bin/pytest -q
```

For changes to experiment aggregation or the CLI, also run a small comparison
before launching expensive experiments:

```bash
.venv/bin/python -m elevator_sim compare \
  --config configs/smoke_test.yaml \
  --schedulers myopic,nearest_car \
  --baseline myopic \
  --runs 2 \
  --output /tmp/elevator_sim_compare_smoke
```

Before handing off changes, run `git diff --check`. Do not run the full 50-seed
paper experiment unless the user requests it or the task requires regenerated
results; clearly state when only tests and smoke runs were performed.

## Output and Reporting Conventions

- Store final paper-quality experiments in a new, clearly named output
  directory rather than overwriting exploratory results.
- Use seconds for time, floors for travel distance, and fractions internally
  for rates. Convert fractions to percentages only in presentation layers.
- Include units in table headings and graph axes.
- Avoid presenting more precision than the simulation assumptions justify;
  two decimal places are normally sufficient for reported time metrics.
- Japanese prose should use `シミュレーション`, not `シュミレーション`.
- A final report must identify the configuration, number of repetitions,
  baseline, prediction horizon, parking policy, and known limitations.
