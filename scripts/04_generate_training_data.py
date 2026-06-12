"""Generate AP-42 truth-labeled daily training data."""

from __future__ import annotations

import argparse
from pathlib import Path

from tankloss.data import build_default_daily_truth_dataset, default_synthetic_terminal_config, write_training_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("outputs/04_generate_training_data/default/training_data.csv"))
    args = parser.parse_args()

    config = default_synthetic_terminal_config(year=args.year, seed=args.seed)
    rows = build_default_daily_truth_dataset(config)
    path = write_training_csv(rows, args.output)
    print(f"training_data: {path}")
    print(f"rows: {len(rows)}")


if __name__ == "__main__":
    main()
