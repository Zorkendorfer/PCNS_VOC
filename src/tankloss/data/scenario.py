"""Deterministic synthetic terminal scenario generation.

The M2 pipeline starts with synthetic-but-realistic data so no confidential
terminal data are needed. Public meteorology can later replace the synthetic
weather rows while keeping the downstream operation schema stable.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ProductConfig:
    """Synthetic product definition for scenario generation."""

    product_id: str
    property_key: str
    annual_turnovers: float
    throughput_variability: float


@dataclass(frozen=True)
class TankConfig:
    """Synthetic tank definition."""

    tank_id: str
    roof_type: str
    diameter_ft: float
    shell_height_ft: float
    working_height_ft: float
    paint: str
    product_id: str
    initial_fill_fraction: float


@dataclass(frozen=True)
class ScenarioConfig:
    """Top-level deterministic scenario configuration."""

    scenario_id: str
    year: int
    seed: int
    latitude: float
    longitude: float
    timezone: str
    products: tuple[ProductConfig, ...]
    tanks: tuple[TankConfig, ...]


def default_synthetic_terminal_config(year: int = 2025, seed: int = 42) -> ScenarioConfig:
    """Return the default synthetic Klaipeda terminal scenario."""

    products = (
        ProductConfig("gasoline_summer", "gasoline_rvp_7", annual_turnovers=18.0, throughput_variability=0.45),
        ProductConfig("gasoline_winter", "gasoline_rvp_13", annual_turnovers=16.0, throughput_variability=0.55),
        ProductConfig("diesel", "distillate_fuel_oil_no_2", annual_turnovers=12.0, throughput_variability=0.35),
        ProductConfig("methanol", "methanol", annual_turnovers=10.0, throughput_variability=0.50),
    )
    tanks = (
        TankConfig("TK-101", "fixed_cone", 90.0, 42.0, 38.0, "white", "gasoline_summer", 0.62),
        TankConfig("TK-102", "internal_floating", 110.0, 48.0, 44.0, "white", "gasoline_winter", 0.55),
        TankConfig("TK-201", "fixed_cone", 120.0, 52.0, 48.0, "gray_light", "diesel", 0.72),
        TankConfig("TK-301", "fixed_cone", 70.0, 36.0, 32.0, "white", "methanol", 0.50),
    )
    return ScenarioConfig(
        scenario_id="klaipeda_synthetic_v1",
        year=year,
        seed=seed,
        latitude=55.7033,
        longitude=21.1443,
        timezone="Europe/Vilnius",
        products=products,
        tanks=tanks,
    )


def _hourly_timestamps(year: int) -> list[datetime]:
    start = datetime(year, 1, 1)
    stop = datetime(year + 1, 1, 1)
    hours: list[datetime] = []
    current = start
    while current < stop:
        hours.append(current)
        current += timedelta(hours=1)
    return hours


def generate_hourly_meteorology(config: ScenarioConfig) -> list[dict[str, float | str]]:
    """Generate one year of hourly synthetic Klaipeda meteorology."""

    rng = np.random.default_rng(config.seed)
    rows: list[dict[str, float | str]] = []
    timestamps = _hourly_timestamps(config.year)
    noise = rng.normal(0.0, 1.2, size=len(timestamps))

    for index, timestamp in enumerate(timestamps):
        day = timestamp.timetuple().tm_yday - 1
        hour = timestamp.hour
        seasonal = 7.0 + 12.0 * np.sin(2.0 * np.pi * (day - 105.0) / 365.0)
        diurnal = 3.0 * np.sin(2.0 * np.pi * (hour - 7.0) / 24.0)
        temp_c = seasonal + diurnal + noise[index]

        day_length = 12.0 + 5.5 * np.sin(2.0 * np.pi * (day - 80.0) / 365.0)
        sunrise = 12.0 - day_length / 2.0
        daylight_phase = (hour - sunrise) / max(day_length, 1.0)
        daylight = 0.0
        if 0.0 <= daylight_phase <= 1.0:
            daylight = np.sin(np.pi * daylight_phase)
        cloud_factor = float(np.clip(rng.normal(0.72, 0.16), 0.25, 1.0))
        solar_w_m2 = 820.0 * daylight * cloud_factor

        wind_m_s = float(np.clip(rng.weibull(2.0) * 4.2, 0.2, 18.0))
        rows.append(
            {
                "timestamp": timestamp.isoformat(timespec="hours"),
                "air_temperature_c": round(float(temp_c), 3),
                "solar_radiation_w_m2": round(float(solar_w_m2), 3),
                "wind_speed_m_s": round(wind_m_s, 3),
            }
        )
    return rows


def _tank_capacity_bbl(tank: TankConfig) -> float:
    volume_ft3 = (np.pi / 4.0) * tank.diameter_ft**2 * tank.working_height_ft
    return float(volume_ft3 / 5.614583333)


def generate_tank_operations(config: ScenarioConfig) -> list[dict[str, float | str]]:
    """Generate hourly tank fill and throughput rows for every configured tank."""

    rng = np.random.default_rng(config.seed + 17)
    product_by_id = {product.product_id: product for product in config.products}
    rows: list[dict[str, float | str]] = []
    timestamps = _hourly_timestamps(config.year)
    hours_per_year = len(timestamps)

    for tank in config.tanks:
        product = product_by_id[tank.product_id]
        capacity_bbl = _tank_capacity_bbl(tank)
        annual_throughput_bbl = product.annual_turnovers * capacity_bbl
        base_hourly_throughput = annual_throughput_bbl / hours_per_year
        fill = tank.initial_fill_fraction

        for timestamp in timestamps:
            day = timestamp.timetuple().tm_yday - 1
            seasonal_factor = 1.0 + 0.25 * np.sin(2.0 * np.pi * (day - 20.0) / 365.0)
            event_factor = 1.0
            if rng.random() < 0.035:
                event_factor += rng.uniform(2.0, 5.0)
            throughput_bbl = max(
                0.0,
                base_hourly_throughput
                * seasonal_factor
                * event_factor
                * rng.lognormal(mean=0.0, sigma=product.throughput_variability * 0.25),
            )

            direction = 1.0 if rng.random() < 0.5 else -1.0
            fill = float(np.clip(fill + direction * throughput_bbl / capacity_bbl, 0.12, 0.95))
            rows.append(
                {
                    "timestamp": timestamp.isoformat(timespec="hours"),
                    "tank_id": tank.tank_id,
                    "product_id": product.product_id,
                    "product_property_key": product.property_key,
                    "roof_type": tank.roof_type,
                    "fill_fraction": round(fill, 5),
                    "liquid_height_ft": round(fill * tank.working_height_ft, 3),
                    "throughput_bbl": round(float(throughput_bbl), 5),
                }
            )
    return rows


def build_synthetic_scenario(config: ScenarioConfig | None = None) -> dict[str, object]:
    """Build meteorology, tank operations, and metadata for a synthetic scenario."""

    selected = config or default_synthetic_terminal_config()
    return {
        "metadata": {
            "scenario_id": selected.scenario_id,
            "year": selected.year,
            "seed": selected.seed,
            "latitude": selected.latitude,
            "longitude": selected.longitude,
            "timezone": selected.timezone,
            "source": "synthetic",
        },
        "products": [asdict(product) for product in selected.products],
        "tanks": [asdict(tank) for tank in selected.tanks],
        "meteorology": generate_hourly_meteorology(selected),
        "operations": generate_tank_operations(selected),
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write to {path}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_scenario_csv(scenario: dict[str, object], output_dir: Path) -> dict[str, Path]:
    """Write scenario outputs as plain files for reproducible pipelines."""

    output_dir.mkdir(parents=True, exist_ok=True)
    meteorology_path = output_dir / "meteorology.csv"
    operations_path = output_dir / "operations.csv"
    metadata_path = output_dir / "metadata.json"

    _write_csv(meteorology_path, scenario["meteorology"])  # type: ignore[arg-type]
    _write_csv(operations_path, scenario["operations"])  # type: ignore[arg-type]
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "metadata": scenario["metadata"],
                "products": scenario["products"],
                "tanks": scenario["tanks"],
            },
            handle,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")
    return {
        "meteorology": meteorology_path,
        "operations": operations_path,
        "metadata": metadata_path,
    }
