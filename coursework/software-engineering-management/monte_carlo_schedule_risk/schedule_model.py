"""Core model: PERT estimation, CPM and Monte Carlo simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Task:
    task_id: str
    task_name: str
    phase: str
    predecessors: tuple[str, ...]
    a: float
    m: float
    b: float
    owner: str

    @property
    def pert_mean(self) -> float:
        return (self.a + 4 * self.m + self.b) / 6

    @property
    def pert_sd(self) -> float:
        return (self.b - self.a) / 6

    @property
    def beta_parameters(self) -> tuple[float, float]:
        """Match the PERT mean and variance with a Beta distribution."""
        if not (self.a < self.m < self.b):
            raise ValueError(f"{self.task_id}: require a < m < b")
        span = self.b - self.a
        standardized_mean = (self.pert_mean - self.a) / span
        standardized_var = (self.pert_sd / span) ** 2
        common = (
            standardized_mean * (1 - standardized_mean) / standardized_var - 1
        )
        alpha = standardized_mean * common
        beta = (1 - standardized_mean) * common
        return max(alpha, 1e-3), max(beta, 1e-3)


def load_tasks(path: str | bytes) -> list[Task]:
    frame = pd.read_csv(path, encoding="utf-8-sig")
    required = {
        "task_id",
        "task_name",
        "phase",
        "predecessors",
        "a",
        "m",
        "b",
        "owner",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    tasks: list[Task] = []
    for row in frame.itertuples(index=False):
        raw_pred = "" if pd.isna(row.predecessors) else str(row.predecessors)
        predecessors = tuple(
            item.strip() for item in raw_pred.split(",") if item.strip()
        )
        tasks.append(
            Task(
                task_id=str(row.task_id).strip(),
                task_name=str(row.task_name).strip(),
                phase=str(row.phase).strip(),
                predecessors=predecessors,
                a=float(row.a),
                m=float(row.m),
                b=float(row.b),
                owner=str(row.owner).strip(),
            )
        )
    validate_tasks(tasks)
    return tasks


def validate_tasks(tasks: Iterable[Task]) -> None:
    task_list = list(tasks)
    ids = [task.task_id for task in task_list]
    if len(ids) != len(set(ids)):
        raise ValueError("Task IDs must be unique")
    known = set(ids)
    for task in task_list:
        unknown = set(task.predecessors).difference(known)
        if unknown:
            raise ValueError(f"{task.task_id}: unknown predecessors {sorted(unknown)}")
    topological_order(task_list)


def topological_order(tasks: Iterable[Task]) -> list[Task]:
    by_id = {task.task_id: task for task in tasks}
    indegree = {
        task.task_id: len(set(task.predecessors)) for task in by_id.values()
    }
    successors: dict[str, list[str]] = {task_id: [] for task_id in by_id}
    for task in by_id.values():
        for pred in set(task.predecessors):
            successors[pred].append(task.task_id)

    queue = [task_id for task_id, degree in indegree.items() if degree == 0]
    ordered: list[Task] = []
    while queue:
        current = queue.pop(0)
        ordered.append(by_id[current])
        for nxt in successors[current]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if len(ordered) != len(by_id):
        raise ValueError("Task graph contains a cycle")
    return ordered


def _pass_schedule(
    tasks: list[Task],
    duration_by_id: dict[str, float],
) -> tuple[dict[str, float], dict[str, float], float]:
    order = topological_order(tasks)
    es: dict[str, float] = {}
    ef: dict[str, float] = {}
    for task in order:
        start = max((ef[pred] for pred in task.predecessors), default=0.0)
        es[task.task_id] = start
        ef[task.task_id] = start + duration_by_id[task.task_id]
    project_finish = max(ef.values())
    return es, ef, project_finish


def deterministic_schedule(tasks: list[Task]) -> dict:
    order = topological_order(tasks)
    duration_by_id = {task.task_id: task.pert_mean for task in tasks}
    es, ef, project_finish = _pass_schedule(tasks, duration_by_id)

    successors: dict[str, list[str]] = {task.task_id: [] for task in tasks}
    for task in tasks:
        for pred in task.predecessors:
            successors[pred].append(task.task_id)

    ls: dict[str, float] = {}
    lf: dict[str, float] = {}
    for task in reversed(order):
        latest_finish = (
            min(ls[succ] for succ in successors[task.task_id])
            if successors[task.task_id]
            else project_finish
        )
        lf[task.task_id] = latest_finish
        ls[task.task_id] = latest_finish - duration_by_id[task.task_id]

    total_float = {
        task.task_id: ls[task.task_id] - es[task.task_id] for task in tasks
    }
    critical_ids = [
        task.task_id for task in order if abs(total_float[task.task_id]) < 1e-8
    ]

    return {
        "order": [task.task_id for task in order],
        "es": es,
        "ef": ef,
        "ls": ls,
        "lf": lf,
        "total_float": total_float,
        "critical_ids": critical_ids,
        "project_duration": project_finish,
        "duration_by_id": duration_by_id,
    }


def _critical_path_label(tasks: list[Task], schedule: dict) -> list[str]:
    """Reconstruct one representative critical path from the sink task."""
    by_id = {task.task_id: task for task in tasks}
    sink = max(
        schedule["critical_ids"],
        key=lambda task_id: schedule["ef"][task_id],
    )
    path = [sink]
    current = sink
    while True:
        task = by_id[current]
        candidates = [
            pred
            for pred in task.predecessors
            if pred in schedule["critical_ids"]
            and abs(schedule["ef"][pred] - schedule["es"][current]) < 1e-8
        ]
        if not candidates:
            break
        current = max(candidates, key=lambda pred: schedule["ef"][pred])
        path.append(current)
    return list(reversed(path))


def sample_task_durations(
    tasks: list[Task],
    n_simulations: int,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    columns: list[np.ndarray] = []
    for task in tasks:
        alpha, beta = task.beta_parameters
        standardized = rng.beta(alpha, beta, size=n_simulations)
        columns.append(task.a + standardized * (task.b - task.a))
    return np.column_stack(columns)


def simulate_project(
    tasks: list[Task],
    n_simulations: int,
    seed: int,
) -> dict:
    order = topological_order(tasks)
    index = {task.task_id: idx for idx, task in enumerate(order)}
    samples = sample_task_durations(order, n_simulations, seed)
    durations = np.zeros_like(samples)

    for idx, task in enumerate(order):
        if task.predecessors:
            pred_indices = [index[pred] for pred in task.predecessors]
            starts = durations[:, pred_indices].max(axis=1)
        else:
            starts = np.zeros(n_simulations)
        durations[:, idx] = starts + samples[:, idx]

    project_duration = durations.max(axis=1)
    return {
        "task_order": [task.task_id for task in order],
        "samples": samples,
        "early_finish": durations,
        "project_duration": project_duration,
    }


def summarize_simulation(
    tasks: list[Task],
    simulation: dict,
    deadline_days: int,
) -> dict:
    project_duration = simulation["project_duration"]
    percentiles = np.percentile(project_duration, [5, 10, 25, 50, 75, 80, 90, 95])
    return {
        "n_simulations": int(project_duration.size),
        "mean": float(project_duration.mean()),
        "std": float(project_duration.std(ddof=1)),
        "min": float(project_duration.min()),
        "p05": float(percentiles[0]),
        "p10": float(percentiles[1]),
        "p25": float(percentiles[2]),
        "p50": float(percentiles[3]),
        "p75": float(percentiles[4]),
        "p80": float(percentiles[5]),
        "p90": float(percentiles[6]),
        "p95": float(percentiles[7]),
        "max": float(project_duration.max()),
        "deadline_days": int(deadline_days),
        "on_time_probability": float(
            np.mean(project_duration <= deadline_days)
        ),
        "overrun_probability": float(
            np.mean(project_duration > deadline_days)
        ),
        "expected_overrun_days": float(
            np.maximum(project_duration - deadline_days, 0).mean()
        ),
        "task_order": simulation["task_order"],
    }


def task_level_statistics(
    tasks: list[Task],
    simulation: dict,
) -> pd.DataFrame:
    rows = []
    order = simulation["task_order"]
    by_id = {task.task_id: task for task in tasks}
    for idx, task_id in enumerate(order):
        task = by_id[task_id]
        values = simulation["samples"][:, idx]
        rows.append(
            {
                "task_id": task.task_id,
                "task_name": task.task_name,
                "phase": task.phase,
                "pert_mean": task.pert_mean,
                "pert_sd": task.pert_sd,
                "beta_alpha": task.beta_parameters[0],
                "beta_beta": task.beta_parameters[1],
                "sim_mean": float(values.mean()),
                "sim_std": float(values.std(ddof=1)),
                "sim_p10": float(np.percentile(values, 10)),
                "sim_p50": float(np.percentile(values, 50)),
                "sim_p90": float(np.percentile(values, 90)),
            }
        )
    return pd.DataFrame(rows)


def sensitivity_analysis(
    tasks: list[Task],
    simulation: dict,
) -> pd.DataFrame:
    order = simulation["task_order"]
    frame = pd.DataFrame(simulation["samples"], columns=order)
    frame["project_duration"] = simulation["project_duration"]
    correlations = frame.corr(method="spearman")["project_duration"].drop(
        "project_duration"
    )

    base = {task.task_id: task.pert_mean for task in tasks}
    rows = []
    for idx, task_id in enumerate(order):
        task = next(item for item in tasks if item.task_id == task_id)
        low_value = float(np.percentile(simulation["samples"][:, idx], 10))
        high_value = float(np.percentile(simulation["samples"][:, idx], 90))
        low_input = dict(base)
        high_input = dict(base)
        low_input[task_id] = low_value
        high_input[task_id] = high_value
        low_duration = _pass_schedule(tasks, low_input)[2]
        high_duration = _pass_schedule(tasks, high_input)[2]
        rows.append(
            {
                "task_id": task.task_id,
                "task_name": task.task_name,
                "phase": task.phase,
                "spearman": float(correlations[task.task_id]),
                "low_p10_duration": low_duration,
                "high_p90_duration": high_duration,
                "swing": high_duration - low_duration,
            }
        )
    result = pd.DataFrame(rows)
    result["rank"] = result["spearman"].rank(
        ascending=False, method="min"
    ).astype(int)
    return result.sort_values(["rank", "swing"], ascending=[True, False])


def seed_stability(
    tasks: list[Task],
    deadline_days: int,
    seeds: list[int],
    n_simulations_each: int = 10_000,
) -> pd.DataFrame:
    rows = []
    for seed in seeds:
        simulation = simulate_project(tasks, n_simulations_each, seed)
        summary = summarize_simulation(tasks, simulation, deadline_days)
        rows.append(
            {
                "seed": seed,
                "n_simulations": n_simulations_each,
                "mean": summary["mean"],
                "p80": summary["p80"],
                "p90": summary["p90"],
                "on_time_probability": summary["on_time_probability"],
            }
        )
    return pd.DataFrame(rows)
