"""Plotting functions for the schedule risk report."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from config import DEADLINE_DAYS, PHASE_COLORS, PHASE_ORDER
from schedule_model import Task


plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 140
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_network(tasks: list[Task], path: Path) -> None:
    phase_x = {
        "需求与设计": 0.0,
        "开发实现": 3.6,
        "前端与集成": 7.1,
        "测试与上线": 10.5,
    }
    positions = {
        "A": (0.0, 2.2),
        "B": (0.0, 1.1),
        "C": (0.0, 0.0),
        "D": (3.6, 3.3),
        "E": (3.6, 2.25),
        "F": (3.6, 1.2),
        "G": (3.6, 0.15),
        "H": (3.6, -0.9),
        "I": (7.1, 2.0),
        "J": (7.1, 0.5),
        "K": (10.5, 1.6),
        "L": (10.5, 0.45),
        "M": (10.5, -0.7),
    }

    fig, ax = plt.subplots(figsize=(10.2, 4.8))
    ax.set_xlim(-1.25, 12.4)
    ax.set_ylim(-1.55, 4.25)
    ax.axis("off")

    for phase, x in phase_x.items():
        ax.text(
            x,
            4.02,
            phase,
            ha="center",
            va="center",
            fontsize=11,
            color=PHASE_COLORS[phase],
            weight="bold",
        )
        ax.plot(
            [x - 1.15, x + 1.15],
            [3.82, 3.82],
            color=PHASE_COLORS[phase],
            linewidth=2,
            alpha=0.9,
        )

    by_id = {task.task_id: task for task in tasks}
    for task in tasks:
        x, y = positions[task.task_id]
        color = PHASE_COLORS[task.phase]
        box = FancyBboxPatch(
            (x - 0.94, y - 0.29),
            1.88,
            0.58,
            boxstyle="round,pad=0.04,rounding_size=0.08",
            linewidth=1.2,
            edgecolor=color,
            facecolor=color + "16",
        )
        ax.add_patch(box)
        ax.text(
            x - 0.77,
            y + 0.07,
            task.task_id,
            fontsize=9.8,
            weight="bold",
            color=color,
            va="center",
        )
        ax.text(
            x - 0.48,
            y + 0.07,
            task.task_name,
            fontsize=8.4,
            color="#233142",
            va="center",
        )
        ax.text(
            x,
            y - 0.16,
            f"{task.pert_mean:.1f} 天",
            fontsize=7.8,
            color="#667085",
            ha="center",
            va="center",
        )

    for task in tasks:
        target = positions[task.task_id]
        for pred in task.predecessors:
            source = positions[pred]
            if abs(source[0] - target[0]) < 1e-9:
                if target[1] < source[1]:
                    start = (source[0], source[1] - 0.29)
                    end = (target[0], target[1] + 0.29)
                else:
                    start = (source[0], source[1] + 0.29)
                    end = (target[0], target[1] - 0.29)
            else:
                start = (source[0] + 0.94, source[1])
                end = (target[0] - 0.94, target[1])
            arrow = FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=8,
                linewidth=0.8,
                color="#AAB4C3",
                shrinkA=2,
                shrinkB=2,
                connectionstyle="arc3,rad=0.04",
                zorder=0,
            )
            ax.add_patch(arrow)

    ax.text(
        0.0,
        -1.35,
        "节点中的“工期”为 PERT 期望值（工作日）",
        fontsize=8.4,
        color="#667085",
        ha="left",
    )
    _save(fig, path)


def plot_gantt(
    tasks: list[Task],
    schedule: dict,
    path: Path,
) -> None:
    by_id = {task.task_id: task for task in tasks}
    fig, ax = plt.subplots(figsize=(9.4, 5.8))
    sorted_ids = sorted(
        [task.task_id for task in tasks],
        key=lambda task_id: (schedule["es"][task_id], task_id),
    )
    y_positions = np.arange(len(sorted_ids))

    for y, task_id in zip(y_positions, sorted_ids):
        task = by_id[task_id]
        start = schedule["es"][task_id]
        duration = schedule["duration_by_id"][task_id]
        is_critical = task_id in schedule["critical_ids"]
        ax.barh(
            y,
            duration,
            left=start,
            height=0.54,
            color=PHASE_COLORS[task.phase],
            alpha=0.88 if is_critical else 0.55,
            edgecolor="#1A1A1A" if is_critical else "none",
            linewidth=0.8 if is_critical else 0,
        )
        ax.text(
            start + duration + 0.8,
            y,
            f"{start:.1f}-{start + duration:.1f}",
            va="center",
            fontsize=8.2,
            color="#475467",
        )

    ax.axvline(
        DEADLINE_DAYS,
        color="#C44E52",
        linestyle="--",
        linewidth=1.4,
        label=f"计划截止 {DEADLINE_DAYS} 天",
    )
    ax.set_yticks(y_positions)
    ax.set_yticklabels(
        [f"{task_id} {by_id[task_id].task_name}" for task_id in sorted_ids],
        fontsize=9.4,
    )
    ax.invert_yaxis()
    ax.set_xlabel("工作日")
    ax.set_title("PERT 均值下的确定性进度计划", fontsize=12, weight="bold")
    ax.grid(axis="x", color="#E8EDF3", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", fontsize=9.0, frameon=False)
    _save(fig, path)


def plot_duration_histogram(
    project_duration: np.ndarray,
    summary: dict,
    path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 4.7))
    bins = np.arange(
        np.floor(project_duration.min()) - 0.5,
        np.ceil(project_duration.max()) + 1.0,
        1.0,
    )
    ax.hist(
        project_duration,
        bins=bins,
        color="#4C78A8",
        alpha=0.72,
        edgecolor="white",
        linewidth=0.5,
    )
    ax.axvline(
        summary["mean"],
        color="#C44E52",
        linewidth=1.7,
        label=f"均值 {summary['mean']:.2f} 天",
    )
    ax.axvline(
        summary["p80"],
        color="#E9A03B",
        linewidth=1.4,
        linestyle="--",
        label=f"P80 {summary['p80']:.1f} 天",
    )
    ax.axvline(
        summary["p90"],
        color="#2A9D8F",
        linewidth=1.4,
        linestyle=":",
        label=f"P90 {summary['p90']:.1f} 天",
    )
    ax.axvline(
        DEADLINE_DAYS,
        color="#111827",
        linewidth=1.8,
        label=f"截止 {DEADLINE_DAYS} 天",
    )
    ax.set_xlabel("项目总工期（工作日）")
    ax.set_ylabel("模拟频数")
    ax.set_title("项目总工期蒙特卡洛分布", fontsize=12, weight="bold")
    ax.grid(axis="y", color="#E8EDF3", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", fontsize=9.0, frameon=False)
    ax.text(
        0.02,
        0.96,
        f"按期完工概率：{summary['on_time_probability']:.1%}",
        transform=ax.transAxes,
        va="top",
        fontsize=11,
        weight="bold",
        color="#1F3A5F",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#F3F7FC", edgecolor="none"),
    )
    _save(fig, path)


def plot_cdf(
    project_duration: np.ndarray,
    summary: dict,
    path: Path,
) -> None:
    values = np.sort(project_duration)
    probabilities = np.arange(1, values.size + 1) / values.size
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    ax.plot(values, probabilities, color="#2A9D8F", linewidth=2.2)
    ax.axhline(
        summary["on_time_probability"],
        color="#C44E52",
        linewidth=1.2,
        linestyle="--",
    )
    ax.axvline(DEADLINE_DAYS, color="#111827", linewidth=1.4)
    ax.scatter(
        [DEADLINE_DAYS],
        [summary["on_time_probability"]],
        color="#C44E52",
        zorder=5,
    )
    ax.annotate(
        f"{summary['on_time_probability']:.1%}",
        (DEADLINE_DAYS, summary["on_time_probability"]),
        xytext=(12, -24),
        textcoords="offset points",
        fontsize=11,
        weight="bold",
        color="#C44E52",
    )
    ax.set_xlabel("项目总工期（工作日）")
    ax.set_ylabel("累计概率")
    ax.set_ylim(0, 1.02)
    ax.set_title("项目按期完工累计概率", fontsize=12, weight="bold")
    ax.grid(color="#E8EDF3", linewidth=0.8)
    ax.set_axisbelow(True)
    _save(fig, path)


def plot_sensitivity(sensitivity: pd.DataFrame, path: Path) -> None:
    top = sensitivity.head(9).iloc[::-1].copy()

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.8))
    ax1, ax2 = axes
    colors = [PHASE_COLORS[phase] for phase in top["phase"]]

    ax1.barh(
        top["task_id"],
        top["spearman"],
        color=colors,
        alpha=0.82,
        height=0.6,
    )
    ax1.set_xlabel("Spearman 相关系数")
    ax1.set_title("任务工期与总工期相关性", fontsize=11, weight="bold")
    ax1.grid(axis="x", color="#E8EDF3", linewidth=0.8)
    ax1.set_axisbelow(True)
    for y, value in enumerate(top["spearman"]):
        ax1.text(value + 0.015, y, f"{value:.2f}", va="center", fontsize=7.8)

    ax2.barh(
        top["task_id"],
        top["swing"],
        color=colors,
        alpha=0.82,
        height=0.6,
    )
    ax2.set_xlabel("P10→P90 引起的总工期摆幅（天）")
    ax2.set_title("单任务工期扰动敏感度", fontsize=11, weight="bold")
    ax2.grid(axis="x", color="#E8EDF3", linewidth=0.8)
    ax2.set_axisbelow(True)
    for y, value in enumerate(top["swing"]):
        ax2.text(value + 0.04, y, f"{value:.2f}", va="center", fontsize=7.8)

    for ax in axes:
        ax.tick_params(axis="y", labelsize=9.0)
    _save(fig, path)
