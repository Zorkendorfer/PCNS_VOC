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

__all__ = [
    "ProductConfig",
    "ScenarioConfig",
    "TankConfig",
    "build_synthetic_scenario",
    "default_synthetic_terminal_config",
    "generate_hourly_meteorology",
    "generate_tank_operations",
    "write_scenario_csv",
]
