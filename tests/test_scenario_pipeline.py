from tankloss.data import (
    build_synthetic_scenario,
    default_synthetic_terminal_config,
    generate_hourly_meteorology,
    generate_tank_operations,
    write_scenario_csv,
)


def test_default_synthetic_meteorology_generates_one_non_leap_year():
    config = default_synthetic_terminal_config(year=2025, seed=42)
    rows = generate_hourly_meteorology(config)

    assert len(rows) == 8760
    assert rows[0]["timestamp"] == "2025-01-01T00"
    assert rows[-1]["timestamp"] == "2025-12-31T23"
    assert min(row["air_temperature_c"] for row in rows) > -25.0
    assert max(row["air_temperature_c"] for row in rows) < 35.0
    assert all(row["solar_radiation_w_m2"] >= 0.0 for row in rows)


def test_default_synthetic_operations_are_deterministic_and_bounded():
    config = default_synthetic_terminal_config(year=2025, seed=42)
    first = generate_tank_operations(config)
    second = generate_tank_operations(config)

    assert first == second
    assert len(first) == 8760 * len(config.tanks)
    assert {row["tank_id"] for row in first} == {"TK-101", "TK-102", "TK-201", "TK-301"}
    assert all(0.12 <= row["fill_fraction"] <= 0.95 for row in first)
    assert all(row["throughput_bbl"] >= 0.0 for row in first)


def test_write_scenario_csv_outputs_expected_files():
    config = default_synthetic_terminal_config(year=2025, seed=7)
    scenario = build_synthetic_scenario(config)
    paths = write_scenario_csv(scenario, config_output_dir())

    assert set(paths) == {"meteorology", "operations", "metadata"}
    assert paths["meteorology"].read_text(encoding="utf-8").splitlines()[0].startswith("timestamp,")
    assert paths["operations"].read_text(encoding="utf-8").splitlines()[0].startswith("timestamp,tank_id,")
    assert '"scenario_id": "klaipeda_synthetic_v1"' in paths["metadata"].read_text(encoding="utf-8")


def config_output_dir():
    from pathlib import Path

    return Path("outputs/tests/scenario_pipeline")
