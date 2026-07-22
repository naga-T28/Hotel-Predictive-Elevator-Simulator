"""Transformer-based destination predictor (requirements.md 9.7).

A small Transformer encoder that consumes a (possibly partial) sequence of
grid-cell indices from a person's walk and outputs the "Predicted Probability
of Going to Elevator" (PPGE) from Zhang et al. The reference paper uses a
4-encoder/4-decoder sequence-to-sequence stack trained on full trajectories
per floor; we use a smaller encoder-only classifier (this is a binary
"elevator or not" head, not a full destination sequence decoder) sized for
CPU training on a synthetic dataset, per requirements.md 15.1 ("CPUのみで基本
シミュレーションを実行可能" — GPU is optional and only relevant to training).
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

from elevator_sim.traffic.trajectory import Trajectory

DEFAULT_TRUNCATION_FRACTIONS = (0.2, 0.4, 0.6, 0.8, 1.0)


class _EncoderClassifier(nn.Module):
    def __init__(self, num_grid_cells: int, d_model: int, nhead: int, num_layers: int, max_len: int) -> None:
        super().__init__()
        self.pad_idx = num_grid_cells
        self.max_len = max_len
        self.token_embedding = nn.Embedding(num_grid_cells + 1, d_model, padding_idx=self.pad_idx)
        self.position_embedding = nn.Embedding(max_len, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=4 * d_model, batch_first=True
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers, enable_nested_tensor=False)
        self.classifier = nn.Linear(d_model, 1)

    def forward(self, token_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        positions = torch.arange(token_ids.size(1), device=token_ids.device).unsqueeze(0)
        x = self.token_embedding(token_ids) + self.position_embedding(positions)
        encoded = self.encoder(x, src_key_padding_mask=~attention_mask.bool())
        mask = attention_mask.unsqueeze(-1)
        pooled = (encoded * mask).sum(1) / mask.sum(1).clamp(min=1)
        return self.classifier(pooled).squeeze(-1)


class TransformerDestinationModel:
    """Binary "is this partial walk heading to the elevator?" classifier over
    grid-id token sequences."""

    def __init__(
        self,
        num_grid_cells: int,
        max_len: int = 64,
        d_model: int = 32,
        nhead: int = 4,
        num_layers: int = 2,
        seed: int = 0,
    ) -> None:
        torch.manual_seed(seed)
        self.max_len = max_len
        self.pad_idx = num_grid_cells
        self.net = _EncoderClassifier(num_grid_cells, d_model, nhead, num_layers, max_len)
        self._fitted = False

    def _encode_batch(self, sequences: list[list[int]]) -> tuple[torch.Tensor, torch.Tensor]:
        truncated = [seq[-self.max_len :] if seq else [self.pad_idx] for seq in sequences]
        max_len_in_batch = max(len(s) for s in truncated)
        token_ids = torch.full((len(truncated), max_len_in_batch), self.pad_idx, dtype=torch.long)
        attention_mask = torch.zeros((len(truncated), max_len_in_batch), dtype=torch.float32)
        for i, seq in enumerate(truncated):
            token_ids[i, : len(seq)] = torch.tensor(seq, dtype=torch.long)
            attention_mask[i, : len(seq)] = 1.0
        return token_ids, attention_mask

    def fit(
        self,
        sequences: list[list[int]],
        labels: list[float],
        epochs: int = 20,
        batch_size: int = 20,
        lr: float = 1e-3,
    ) -> None:
        if not sequences:
            raise ValueError("No training sequences provided to TransformerDestinationModel")

        optimizer = torch.optim.Adam(self.net.parameters(), lr=lr)
        loss_fn = nn.BCEWithLogitsLoss()
        labels_arr = np.array(labels, dtype=np.float32)
        n = len(sequences)

        self.net.train()
        rng = np.random.default_rng(0)
        for _ in range(epochs):
            order = rng.permutation(n)
            for start in range(0, n, batch_size):
                idx = order[start : start + batch_size]
                batch_sequences = [sequences[i] for i in idx]
                token_ids, attention_mask = self._encode_batch(batch_sequences)
                targets = torch.tensor(labels_arr[idx])

                optimizer.zero_grad()
                logits = self.net(token_ids, attention_mask)
                loss = loss_fn(logits, targets)
                loss.backward()
                optimizer.step()

        self.net.eval()
        self._fitted = True

    def predict_probability(self, grid_id_sequence: list[int]) -> float:
        if not self._fitted:
            raise RuntimeError("TransformerDestinationModel.fit() must be called first")
        if not grid_id_sequence:
            return 0.0
        token_ids, attention_mask = self._encode_batch([grid_id_sequence])
        with torch.no_grad():
            logits = self.net(token_ids, attention_mask)
            probability = torch.sigmoid(logits).item()
        return float(probability)


def build_training_set(
    trajectories: list[Trajectory],
    grid,
    truncation_fractions: tuple[float, ...] = DEFAULT_TRUNCATION_FRACTIONS,
) -> tuple[list[list[int]], list[float]]:
    """Turn full trajectories into (prefix, label) training examples at
    several completion fractions, so the model learns to predict early
    (requirements.md 9.7's "60% of trajectory" evaluation regime)."""
    sequences: list[list[int]] = []
    labels: list[float] = []
    for traj in trajectories:
        n = len(traj.points)
        if n == 0:
            continue
        label = 1.0 if traj.elevator_bound else 0.0
        for frac in truncation_fractions:
            k = max(1, int(round(n * frac)))
            prefix = traj.points[:k]
            token_ids = [grid.grid_id(xi, yi) for xi, yi, _ in prefix]
            sequences.append(token_ids)
            labels.append(label)
    return sequences, labels


def train_destination_model(
    trajectories: list[Trajectory],
    grid,
    epochs: int = 20,
    batch_size: int = 20,
    seed: int = 0,
) -> TransformerDestinationModel:
    sequences, labels = build_training_set(trajectories, grid)
    model = TransformerDestinationModel(num_grid_cells=grid.num_cells, seed=seed)
    model.fit(sequences, labels, epochs=epochs, batch_size=batch_size)
    return model
