"""Matplotlib visualizations (requirements.md 14)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# Use a CJK-capable font when available so Japanese axis/title labels render
# instead of falling back to tofu boxes on matplotlib's default DejaVu Sans.
for _font in ["Hiragino Sans", "Yu Gothic", "Noto Sans CJK JP", "IPAexGothic"]:
    if _font in {f.name for f in matplotlib.font_manager.fontManager.ttflist}:
        matplotlib.rcParams["font.family"] = _font
        break
matplotlib.rcParams["axes.unicode_minus"] = False

CATEGORICAL_PALETTE = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
]

SCHEDULER_ORDER = ["myopic", "nearest_car", "prescient", "predictive"]


def _color_for(key: str, order: list[str]) -> str:
    if key not in order:
        order = order + [key]
    idx = order.index(key) % len(CATEGORICAL_PALETTE)
    return CATEGORICAL_PALETTE[idx]


def _style_axes(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#c3c2b7")
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.yaxis.grid(True, color="#e5e4df", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors="#52514e")


def plot_waiting_time_distribution(
    waits_by_scheduler: dict[str, list[float]], output_path: str | Path
) -> None:
    """Box plot of passenger waiting time per scheduler (requirements.md 14.1)."""
    schedulers = list(waits_by_scheduler.keys())
    fig, ax = plt.subplots(figsize=(1.6 * max(len(schedulers), 2) + 2, 4.5))

    box = ax.boxplot(
        [waits_by_scheduler[s] for s in schedulers],
        tick_labels=schedulers,
        patch_artist=True,
        widths=0.5,
        medianprops={"color": "#0b0b0b", "linewidth": 1.5},
        whiskerprops={"color": "#52514e"},
        capprops={"color": "#52514e"},
        flierprops={"markersize": 3, "markeredgecolor": "#9a998f"},
    )
    for patch, sched in zip(box["boxes"], schedulers):
        color = _color_for(sched, SCHEDULER_ORDER)
        patch.set_facecolor(color)
        patch.set_alpha(0.55)
        patch.set_edgecolor(color)

    _style_axes(ax)
    ax.set_ylabel("待ち時間 (秒)")
    ax.set_title("制御方式ごとの待ち時間分布")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_scheduler_comparison(aggregate_df: pd.DataFrame, output_path: str | Path) -> None:
    """Bar charts comparing schedulers on key metrics (requirements.md 14.5)."""
    metrics = [
        ("average_waiting_time_mean", "平均待ち時間 (秒)"),
        ("p95_waiting_time_mean", "95%ile待ち時間 (秒)"),
        ("left_behind_rate_mean", "乗り残し率"),
        ("empty_distance_mean", "空運転距離 (階)"),
        ("stop_count_mean", "停止回数"),
    ]
    metrics = [m for m in metrics if m[0] in aggregate_df.columns]

    fig, axes = plt.subplots(1, len(metrics), figsize=(3.2 * len(metrics), 4.0))
    if len(metrics) == 1:
        axes = [axes]

    schedulers = list(aggregate_df.index)
    colors = [_color_for(s, SCHEDULER_ORDER) for s in schedulers]

    for ax, (col, label) in zip(axes, metrics):
        values = aggregate_df[col].values
        err_col = col.replace("_mean", "_std")
        errors = aggregate_df[err_col].values if err_col in aggregate_df.columns else None
        ax.bar(schedulers, values, color=colors, width=0.6, yerr=errors, capsize=3)
        _style_axes(ax)
        ax.set_title(label, fontsize=10)
        ax.tick_params(axis="x", rotation=30)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_elevator_position_timeline(event_df: pd.DataFrame, output_path: str | Path) -> None:
    """Time vs. floor trajectory per car (requirements.md 14.2)."""
    events = event_df[event_df["event_type"].isin(["board", "alight"])].copy()
    events = events.dropna(subset=["floor"]).sort_values("timestamp")

    fig, ax = plt.subplots(figsize=(10, 4.5))
    car_ids = sorted(events["car_id"].dropna().unique())
    for car_id in car_ids:
        sub = events[events["car_id"] == car_id]
        ax.plot(
            sub["timestamp"],
            sub["floor"],
            marker="o",
            markersize=3,
            linewidth=1.2,
            color=_color_for(car_id, car_ids),
            label=car_id,
        )

    _style_axes(ax)
    ax.set_xlabel("時間 (秒)")
    ax.set_ylabel("フロア")
    ax.set_title("号機運行軌跡")
    if car_ids:
        ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_occupancy_timeline(event_df: pd.DataFrame, output_path: str | Path) -> None:
    """Load factor per car over time (requirements.md 14.4)."""
    events = event_df[event_df["event_type"].isin(["board", "alight"])].copy()
    events = events.dropna(subset=["load"]).sort_values("timestamp")

    fig, ax = plt.subplots(figsize=(10, 4.5))
    car_ids = sorted(events["car_id"].dropna().unique())
    for car_id in car_ids:
        sub = events[events["car_id"] == car_id]
        ax.step(
            sub["timestamp"],
            sub["load"],
            where="post",
            linewidth=1.2,
            color=_color_for(car_id, car_ids),
            label=car_id,
        )

    _style_axes(ax)
    ax.set_xlabel("時間 (秒)")
    ax.set_ylabel("積載量")
    ax.set_title("号機積載率の時系列")
    if car_ids:
        ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
