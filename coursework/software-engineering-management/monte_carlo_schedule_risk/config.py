"""Project-level configuration for the Monte Carlo schedule risk analysis."""

from pathlib import Path


PROJECT_NAME = "校园二手交易平台 V1.0"
DEADLINE_DAYS = 61
N_SIMULATIONS = 20_000
RANDOM_SEED = 2026

ROOT_DIR = Path(__file__).resolve().parent
DATA_PATH = ROOT_DIR / "data" / "tasks.csv"
RESULTS_DIR = ROOT_DIR / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

PHASE_ORDER = ["需求与设计", "开发实现", "前端与集成", "测试与上线"]
PHASE_COLORS = {
    "需求与设计": "#4C78A8",
    "开发实现": "#2A9D8F",
    "前端与集成": "#E9A03B",
    "测试与上线": "#C44E52",
}
