from pathlib import Path

from tankloss.data import (
    build_default_daily_truth_dataset,
    default_synthetic_terminal_config,
    write_training_csv,
)


def test_daily_truth_dataset_has_one_row_per_tank_day_and_is_deterministic():
    config = default_synthetic_terminal_config(year=2025, seed=42)
    first = build_default_daily_truth_dataset(config)
    second = build_default_daily_truth_dataset(config)

    assert first == second
    assert len(first) == 365 * len(config.tanks)
    assert {row["tank_id"] for row in first} == {"TK-101", "TK-102", "TK-201", "TK-301"}
    assert all(row["total_loss_lb"] >= 0.0 for row in first)


def test_daily_truth_dataset_separates_fixed_and_floating_loss_components():
    config = default_synthetic_terminal_config(year=2025, seed=42)
    rows = build_default_daily_truth_dataset(config)
    fixed = next(row for row in rows if row["tank_id"] == "TK-101")
    floating = next(row for row in rows if row["tank_id"] == "TK-102")

    assert fixed["standing_loss_lb"] > 0.0
    assert fixed["working_loss_lb"] > 0.0
    assert fixed["deck_fitting_loss_lb"] == 0.0
    assert floating["standing_loss_lb"] == 0.0
    assert floating["rim_seal_loss_lb"] > 0.0
    assert floating["deck_fitting_loss_lb"] > floating["rim_seal_loss_lb"]


def test_write_training_csv_outputs_header_and_rows():
    config = default_synthetic_terminal_config(year=2025, seed=3)
    rows = build_default_daily_truth_dataset(config)
    path = write_training_csv(rows, Path("outputs/tests/training_data/training_data.csv"))
    lines = path.read_text(encoding="utf-8").splitlines()

    assert lines[0].startswith("date,tank_id,roof_type,product_id,")
    assert len(lines) == len(rows) + 1
