"""Truth-labeled training data generation from synthetic scenarios."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from tankloss.data.scenario import ScenarioConfig, TankConfig, _tank_capacity_bbl, build_synthetic_scenario
from tankloss.physics.fixed_roof import (
    cone_roof_outage,
    daily_average_ambient_temperature,
    daily_liquid_surface_temperature,
    daily_vapor_pressure_range,
    daily_vapor_temperature_range,
    liquid_bulk_temperature,
    rankine_to_celsius_ap42,
    standing_storage_loss,
    turnover_factor,
    vapor_density,
    vapor_space_expansion_factor,
    vapor_space_outage,
    vapor_space_saturation_factor,
    vapor_space_volume,
    working_loss,
)
from tankloss.physics.floating_roof import DeckFitting, floating_roof_losses
from tankloss.properties import (
    ANTOINE_ORGANIC_LIQUIDS,
    paint_solar_absorptance,
    petroleum_liquid,
    petroleum_true_vapor_pressure_psia,
    pure_organic_vapor_pressure_psia,
    refined_petroleum_vapor_pressure_psia,
)


W_M2_HOUR_TO_BTU_FT2 = 0.316998
M_S_TO_MPH = 2.2369362921
PSIA_ATM = 14.7


@dataclass(frozen=True)
class ProductState:
    """Product properties at one AP-42 liquid surface temperature."""

    vapor_pressure_psia: float
    vapor_molecular_weight: float
    liquid_density_lb_per_gal: float


def celsius_to_fahrenheit(temperature_c: float) -> float:
    return temperature_c * 9.0 / 5.0 + 32.0


def fahrenheit_to_rankine(temperature_f: float) -> float:
    return temperature_f + 460.0


def rankine_to_fahrenheit(temperature_r: float) -> float:
    return temperature_r - 460.0


def _gasoline_rvp_from_key(product_key: str) -> float | None:
    if product_key == "gasoline_rvp_13":
        return 13.0
    if product_key == "gasoline_rvp_10":
        return 10.0
    if product_key == "gasoline_rvp_7":
        return 7.0
    return None


def _petroleum_pressure(product_key: str, temperature_f: float) -> float:
    rvp = _gasoline_rvp_from_key(product_key)
    if rvp is not None:
        return refined_petroleum_vapor_pressure_psia(temperature_f, rvp, 3.0)

    liquid = petroleum_liquid(product_key)
    temperatures = sorted(liquid.vapor_pressure_by_temp_f)
    bounded_temperature = min(max(temperature_f, temperatures[0]), temperatures[-1])
    return petroleum_true_vapor_pressure_psia(product_key, bounded_temperature)


def _product_state(product_key: str, liquid_surface_temperature_r: float) -> ProductState:
    temperature_f = rankine_to_fahrenheit(liquid_surface_temperature_r)
    temperature_c = float(rankine_to_celsius_ap42(liquid_surface_temperature_r))

    if product_key in ANTOINE_ORGANIC_LIQUIDS:
        molecular_weight, _, _, _ = ANTOINE_ORGANIC_LIQUIDS[product_key]
        return ProductState(
            vapor_pressure_psia=pure_organic_vapor_pressure_psia(product_key, temperature_c),
            vapor_molecular_weight=molecular_weight,
            liquid_density_lb_per_gal=6.6,
        )

    liquid = petroleum_liquid(product_key)
    return ProductState(
        vapor_pressure_psia=_petroleum_pressure(product_key, temperature_f),
        vapor_molecular_weight=liquid.vapor_molecular_weight,
        liquid_density_lb_per_gal=liquid.liquid_density_lb_per_gal,
    )


def _daily_meteorology(rows: Iterable[dict[str, float | str]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict[str, float | str]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["timestamp"])[:10]].append(row)

    daily: dict[str, dict[str, float]] = {}
    for date, date_rows in grouped.items():
        temps_c = [float(row["air_temperature_c"]) for row in date_rows]
        solar = [float(row["solar_radiation_w_m2"]) for row in date_rows]
        wind = [float(row["wind_speed_m_s"]) for row in date_rows]
        tax_f = celsius_to_fahrenheit(max(temps_c))
        tan_f = celsius_to_fahrenheit(min(temps_c))
        daily[date] = {
            "tax_f": tax_f,
            "tan_f": tan_f,
            "tax_r": fahrenheit_to_rankine(tax_f),
            "tan_r": fahrenheit_to_rankine(tan_f),
            "air_temperature_mean_c": float(np.mean(temps_c)),
            "solar_btu_ft2_day": float(np.sum(solar) * W_M2_HOUR_TO_BTU_FT2),
            "wind_speed_mph": float(np.mean(wind) * M_S_TO_MPH),
        }
    return daily


def _daily_operations(rows: Iterable[dict[str, float | str]]) -> dict[tuple[str, str], dict[str, float | str]]:
    grouped: dict[tuple[str, str], list[dict[str, float | str]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["tank_id"]), str(row["timestamp"])[:10])].append(row)

    daily: dict[tuple[str, str], dict[str, float | str]] = {}
    for key, date_rows in grouped.items():
        daily[key] = {
            "product_id": date_rows[0]["product_id"],
            "product_property_key": date_rows[0]["product_property_key"],
            "roof_type": date_rows[0]["roof_type"],
            "fill_fraction": float(np.mean([float(row["fill_fraction"]) for row in date_rows])),
            "liquid_height_ft": float(np.mean([float(row["liquid_height_ft"]) for row in date_rows])),
            "throughput_bbl": float(np.sum([float(row["throughput_bbl"]) for row in date_rows])),
        }
    return daily


def _fixed_roof_daily_losses(
    tank: TankConfig,
    product_key: str,
    liquid_height_ft: float,
    throughput_bbl_day: float,
    met: dict[str, float],
) -> dict[str, float]:
    alpha = paint_solar_absorptance(tank.paint, "good")
    taa = daily_average_ambient_temperature(met["tax_r"], met["tan_r"])
    tb = liquid_bulk_temperature(taa, alpha)
    tla = daily_liquid_surface_temperature(taa, tb, alpha, met["solar_btu_ft2_day"])
    tv = daily_vapor_temperature_range(met["tax_r"], met["tan_r"], alpha, met["solar_btu_ft2_day"])
    state = _product_state(product_key, tla)
    state_min = _product_state(product_key, tla - 0.25 * tv)
    state_max = _product_state(product_key, tla + 0.25 * tv)

    hro = cone_roof_outage(tank.diameter_ft)
    hvo = vapor_space_outage(tank.shell_height_ft, liquid_height_ft, hro)
    vv = vapor_space_volume(tank.diameter_ft, hvo)
    wv = vapor_density(state.vapor_molecular_weight, state.vapor_pressure_psia, tla)
    pv = daily_vapor_pressure_range(state_max.vapor_pressure_psia, state_min.vapor_pressure_psia)
    ke = vapor_space_expansion_factor(tv, tla, pv, 0.06, PSIA_ATM, state.vapor_pressure_psia)
    ks = vapor_space_saturation_factor(state.vapor_pressure_psia, hvo)

    standing_annual = standing_storage_loss(vv, wv, ke, ks)
    annualized_throughput = throughput_bbl_day * 365.0
    capacity_bbl = _tank_capacity_bbl(tank)
    annualized_turnovers = annualized_throughput / capacity_bbl if capacity_bbl else 0.0
    working_annual = working_loss(
        state.vapor_molecular_weight,
        state.vapor_pressure_psia,
        annualized_throughput,
        turnover_factor(annualized_turnovers),
        1.0,
    )

    return {
        "vapor_pressure_psia": state.vapor_pressure_psia,
        "vapor_molecular_weight": state.vapor_molecular_weight,
        "liquid_surface_temperature_r": float(tla),
        "standing_loss_lb": max(float(standing_annual) / 365.0, 0.0),
        "working_loss_lb": max(float(working_annual) / 365.0, 0.0),
        "rim_seal_loss_lb": 0.0,
        "withdrawal_loss_lb": 0.0,
        "deck_fitting_loss_lb": 0.0,
        "deck_seam_loss_lb": 0.0,
    }


def _internal_floating_deck_fittings(diameter_ft: float) -> list[DeckFitting]:
    return [
        DeckFitting("access hatch", count=2, kfa=36.0),
        DeckFitting("automatic gauge float well", count=1, kfa=14.0),
        DeckFitting("pipe column well", count=1, kfa=10.0),
        DeckFitting("ladder well", count=1, kfa=56.0),
        DeckFitting("adjustable deck legs", count=5.0 + diameter_ft / 10.0 + diameter_ft**2 / 600.0, kfa=7.9),
        DeckFitting("sample pipe well", count=1, kfa=43.1),
        DeckFitting("vacuum breaker", count=1, kfa=6.2),
    ]


def _floating_roof_daily_losses(
    tank: TankConfig,
    product_key: str,
    throughput_bbl_day: float,
    met: dict[str, float],
) -> dict[str, float]:
    alpha = paint_solar_absorptance(tank.paint, "good")
    taa = daily_average_ambient_temperature(met["tax_r"], met["tan_r"])
    tb = liquid_bulk_temperature(taa, alpha)
    tla = daily_liquid_surface_temperature(taa, tb, alpha, met["solar_btu_ft2_day"])
    state = _product_state(product_key, tla)
    is_internal = tank.roof_type == "internal_floating"

    annual = floating_roof_losses(
        tank_diameter_ft=tank.diameter_ft,
        vapor_pressure_psia=state.vapor_pressure_psia,
        atmospheric_pressure_psia=PSIA_ATM,
        vapor_molecular_weight=state.vapor_molecular_weight,
        annual_throughput_bbl_per_year=throughput_bbl_day * 365.0,
        shell_clingage_factor_bbl_per_1000_ft2=0.0015,
        liquid_density_lb_per_gal=state.liquid_density_lb_per_gal,
        rim_seal_zero_wind_loss_factor=0.3 if is_internal else 1.6,
        rim_seal_wind_loss_factor=0.6 if is_internal else 0.3,
        rim_seal_wind_exponent=0.0 if is_internal else 1.6,
        wind_speed_mph=0.0 if is_internal else met["wind_speed_mph"],
        deck_fittings=_internal_floating_deck_fittings(tank.diameter_ft),
        column_count=1.0 if is_internal else 0.0,
        effective_column_diameter_ft=1.0 if is_internal else 0.0,
        deck_seam_loss_factor=0.0,
        deck_seam_length_factor=0.0,
        wind_dependent_deck_fittings=not is_internal,
    )

    return {
        "vapor_pressure_psia": state.vapor_pressure_psia,
        "vapor_molecular_weight": state.vapor_molecular_weight,
        "liquid_surface_temperature_r": float(tla),
        "standing_loss_lb": 0.0,
        "working_loss_lb": 0.0,
        "rim_seal_loss_lb": annual.rim_seal_loss_lb_per_year / 365.0,
        "withdrawal_loss_lb": annual.withdrawal_loss_lb_per_year / 365.0,
        "deck_fitting_loss_lb": annual.deck_fitting_loss_lb_per_year / 365.0,
        "deck_seam_loss_lb": annual.deck_seam_loss_lb_per_year / 365.0,
    }


def build_daily_truth_dataset(scenario: dict[str, object], config: ScenarioConfig) -> list[dict[str, float | str]]:
    """Aggregate a scenario to daily AP-42 truth-labeled training rows."""

    met_by_date = _daily_meteorology(scenario["meteorology"])  # type: ignore[arg-type]
    ops_by_tank_day = _daily_operations(scenario["operations"])  # type: ignore[arg-type]
    tank_by_id = {tank.tank_id: tank for tank in config.tanks}
    rows: list[dict[str, float | str]] = []

    for (tank_id, date), ops in sorted(ops_by_tank_day.items()):
        tank = tank_by_id[tank_id]
        met = met_by_date[date]
        product_key = str(ops["product_property_key"])
        if tank.roof_type in {"fixed_cone", "fixed_roof"}:
            losses = _fixed_roof_daily_losses(
                tank,
                product_key,
                float(ops["liquid_height_ft"]),
                float(ops["throughput_bbl"]),
                met,
            )
        elif tank.roof_type in {"internal_floating", "external_floating"}:
            losses = _floating_roof_daily_losses(tank, product_key, float(ops["throughput_bbl"]), met)
        else:
            raise ValueError(f"Unsupported roof type: {tank.roof_type}")

        total_loss = (
            losses["standing_loss_lb"]
            + losses["working_loss_lb"]
            + losses["rim_seal_loss_lb"]
            + losses["withdrawal_loss_lb"]
            + losses["deck_fitting_loss_lb"]
            + losses["deck_seam_loss_lb"]
        )
        rows.append(
            {
                "date": date,
                "tank_id": tank_id,
                "roof_type": tank.roof_type,
                "product_id": str(ops["product_id"]),
                "product_property_key": product_key,
                "diameter_ft": round(tank.diameter_ft, 6),
                "shell_height_ft": round(tank.shell_height_ft, 6),
                "liquid_height_ft": round(float(ops["liquid_height_ft"]), 6),
                "fill_fraction": round(float(ops["fill_fraction"]), 6),
                "throughput_bbl_day": round(float(ops["throughput_bbl"]), 6),
                "tax_f": round(met["tax_f"], 6),
                "tan_f": round(met["tan_f"], 6),
                "solar_btu_ft2_day": round(met["solar_btu_ft2_day"], 6),
                "wind_speed_mph": round(met["wind_speed_mph"], 6),
                "vapor_pressure_psia": round(losses["vapor_pressure_psia"], 8),
                "vapor_molecular_weight": round(losses["vapor_molecular_weight"], 6),
                "liquid_surface_temperature_r": round(losses["liquid_surface_temperature_r"], 6),
                "standing_loss_lb": round(losses["standing_loss_lb"], 8),
                "working_loss_lb": round(losses["working_loss_lb"], 8),
                "rim_seal_loss_lb": round(losses["rim_seal_loss_lb"], 8),
                "withdrawal_loss_lb": round(losses["withdrawal_loss_lb"], 8),
                "deck_fitting_loss_lb": round(losses["deck_fitting_loss_lb"], 8),
                "deck_seam_loss_lb": round(losses["deck_seam_loss_lb"], 8),
                "total_loss_lb": round(float(total_loss), 8),
            }
        )
    return rows


def build_default_daily_truth_dataset(config: ScenarioConfig) -> list[dict[str, float | str]]:
    """Build truth rows from the default synthetic scenario for a config."""

    return build_daily_truth_dataset(build_synthetic_scenario(config), config)


def write_training_csv(rows: list[dict[str, float | str]], path: Path) -> Path:
    """Write truth-labeled training rows to CSV."""

    if not rows:
        raise ValueError("No training rows to write.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path
