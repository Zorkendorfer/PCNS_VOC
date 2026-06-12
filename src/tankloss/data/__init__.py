"""Synthetic and public-data scenario generation."""

from tankloss.data.scenario import (
    ProductConfig,
    ScenarioConfig,
    TankConfig,
    build_synthetic_scenario,
    default_synthetic_terminal_config,
    generate_hourly_meteorology,
    generate_tank_operations,
    write_scenario_csv,
)
from tankloss.data.training import (
    ProductState,
    build_daily_truth_dataset,
    build_default_daily_truth_dataset,
    write_training_csv,
)

__all__ = [
    "ProductConfig",
    "ScenarioConfig",
    "TankConfig",
    "build_synthetic_scenario",
    "default_synthetic_terminal_config",
    "generate_hourly_meteorology",
    "generate_tank_operations",
    "write_scenario_csv",
    "ProductState",
    "build_daily_truth_dataset",
    "build_default_daily_truth_dataset",
    "write_training_csv",
]
