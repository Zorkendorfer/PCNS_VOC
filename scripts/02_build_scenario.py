"""Build the default synthetic Klaipeda tank-farm scenario."""

from __future__ import annotations

import argparse
from pathlib import Path

from tankloss.data import build_synthetic_scenario, default_synthetic_terminal_config, write_scenario_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/02_build_scenario/default"))
    args = parser.parse_args()

    config = default_synthetic_terminal_config(year=args.year, seed=args.seed)
    scenario = build_synthetic_scenario(config)
    paths = write_scenario_csv(scenario, args.output_dir)
    for label, path in paths.items():
        print(f"{label}: {path}")


if __name__ == "__main__":
    main()
