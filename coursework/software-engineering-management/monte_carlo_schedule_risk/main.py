"""Run the full Monte Carlo schedule risk analysis and export results."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config import (
    DATA_PATH,
    DEADLINE_DAYS,
    FIGURES_DIR,
    N_SIMULATIONS,
    PROJECT_NAME,
    RANDOM_SEED,
    RESULTS_DIR,
)
from plots import (
    plot_cdf,
    plot_duration_histogram,
    plot_gantt,
    plot_network,
    plot_sensitivity,
)
from schedule_model import (
    _critical_path_label,
    deterministic_schedule,
    load_tasks,
    seed_stability,
    sensitivity_analysis,
    simulate_project,
    summarize_simulation,
    task_level_statistics,
)


def _prepare_output_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def _schedule_table(tasks, schedule) -> pd.DataFrame:
    by_id = {task.task_id: task for task in tasks}
    rows = []
    for task_id in schedule["order"]:
        task = by_id[task_id]
        rows.append(
            {
                "task_id": task.task_id,
                "task_name": task.task_name,
                "phase": task.phase,
                "predecessors": ",".join(task.predecessors),
                "duration": schedule["duration_by_id"][task_id],
                "es": schedule["es"][task_id],
                "ef": schedule["ef"][task_id],
                "ls": schedule["ls"][task_id],
                "lf": schedule["lf"][task_id],
                "total_float": schedule["total_float"][task_id],
                "critical": task_id in schedule["critical_ids"],
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    _prepare_output_dirs()
    tasks = load_tasks(DATA_PATH)

    deterministic = deterministic_schedule(tasks)
    critical_path = _critical_path_label(tasks, deterministic)

    simulation = simulate_project(tasks, N_SIMULATIONS, RANDOM_SEED)
    summary = summarize_simulation(tasks, simulation, DEADLINE_DAYS)
    task_stats = task_level_statistics(tasks, simulation)
    sensitivity = sensitivity_analysis(tasks, simulation)
    schedule_table = _schedule_table(tasks, deterministic)

    stability = seed_stability(
        tasks,
        deadline_days=DEADLINE_DAYS,
        seeds=[RANDOM_SEED + offset for offset in range(5)],
        n_simulations_each=10_000,
    )

    summary.update(
        {
            "project_name": PROJECT_NAME,
            "random_seed": RANDOM_SEED,
            "deterministic_duration": deterministic["project_duration"],
            "merge_bias_days": summary["mean"] - deterministic["project_duration"],
            "critical_path": critical_path,
            "critical_ids": deterministic["critical_ids"],
        }
    )

    summary_path = RESULTS_DIR / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    task_stats.to_csv(RESULTS_DIR / "task_statistics.csv", index=False, encoding="utf-8-sig")
    sensitivity.to_csv(RESULTS_DIR / "sensitivity.csv", index=False, encoding="utf-8-sig")
    schedule_table.to_csv(
        RESULTS_DIR / "deterministic_schedule.csv",
        index=False,
        encoding="utf-8-sig",
    )
    stability.to_csv(RESULTS_DIR / "seed_stability.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        {
            "simulation_id": range(1, N_SIMULATIONS + 1),
            "project_duration": simulation["project_duration"],
        }
    ).to_csv(
        RESULTS_DIR / "project_duration_samples.csv",
        index=False,
        encoding="utf-8-sig",
    )

    plot_network(tasks, FIGURES_DIR / "fig1_task_network.png")
    plot_gantt(tasks, deterministic, FIGURES_DIR / "fig2_deterministic_gantt.png")
    plot_duration_histogram(
        simulation["project_duration"],
        summary,
        FIGURES_DIR / "fig3_duration_histogram.png",
    )
    plot_cdf(
        simulation["project_duration"],
        summary,
        FIGURES_DIR / "fig4_duration_cdf.png",
    )
    plot_sensitivity(sensitivity, FIGURES_DIR / "fig5_sensitivity.png")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nResults: {RESULTS_DIR}")
    print(f"Figures: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
