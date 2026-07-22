"""Linear regression model for remaining-time-to-destination prediction
(requirements.md 9.8).

Mirrors Zhang et al. eq. (3): ``t* = beta1 * x* + beta2 * y*``, fit per
destination on grid-index positions paired with the true remaining time to
that destination, ``t* = t_d - t``. We add an intercept (``beta0``) since
scikit-learn's default is more general and strictly dominates the
paper's origin-constrained fit.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LinearRegression

from elevator_sim.traffic.trajectory import Trajectory


class LinearRemainingTimeModel:
    def __init__(self) -> None:
        self.model = LinearRegression()
        self._fitted = False

    def fit(self, trajectories: list[Trajectory]) -> None:
        X, y = [], []
        for traj in trajectories:
            if not traj.elevator_bound or traj.hall_arrival_time is None:
                continue
            for xi, yi, t in traj.points:
                X.append([xi, yi])
                y.append(traj.hall_arrival_time - t)

        if not X:
            raise ValueError("No elevator-bound trajectories to fit LinearRemainingTimeModel")

        self.model.fit(np.array(X), np.array(y))
        self._fitted = True

    def predict(self, xi: float, yi: float) -> float:
        if not self._fitted:
            raise RuntimeError("LinearRemainingTimeModel.fit() must be called first")
        value = self.model.predict(np.array([[xi, yi]]))[0]
        return max(0.0, float(value))

    def rmse(self, trajectories: list[Trajectory]) -> float:
        errors = []
        for traj in trajectories:
            if not traj.elevator_bound or traj.hall_arrival_time is None:
                continue
            for xi, yi, t in traj.points:
                predicted = self.predict(xi, yi)
                actual = traj.hall_arrival_time - t
                errors.append((predicted - actual) ** 2)
        return float(np.sqrt(np.mean(errors))) if errors else 0.0


def train_remaining_time_model(trajectories: list[Trajectory]) -> LinearRemainingTimeModel:
    model = LinearRemainingTimeModel()
    model.fit(trajectories)
    return model
