"""Curated AP-42 Chapter 7.1 property helpers.

The raw AP-42 text tables are intentionally not vendored in this repository.
This module carries the small, tested subset of constants needed by the
current examples and scenario defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, log10, sqrt

import numpy as np

from tankloss.physics.fixed_roof import Component, antoine_pressure_psia


@dataclass(frozen=True)
class PetroleumLiquid:
    """Selected petroleum-liquid properties from AP-42 Table 7.1-2."""

    name: str
    vapor_molecular_weight: float
    condensed_vapor_density_lb_per_gal: float
    liquid_density_lb_per_gal: float
    vapor_pressure_by_temp_f: dict[float, float]


PETROLEUM_LIQUIDS: dict[str, PetroleumLiquid] = {
    "gasoline_rvp_13": PetroleumLiquid(
        name="Gasoline RVP 13",
        vapor_molecular_weight=62.0,
        condensed_vapor_density_lb_per_gal=4.9,
        liquid_density_lb_per_gal=5.6,
        vapor_pressure_by_temp_f={
            40.0: 4.7,
            50.0: 5.7,
            60.0: 6.9,
            70.0: 8.3,
            80.0: 9.9,
            90.0: 11.7,
            100.0: 13.8,
        },
    ),
    "gasoline_rvp_10": PetroleumLiquid(
        name="Gasoline RVP 10",
        vapor_molecular_weight=66.0,
        condensed_vapor_density_lb_per_gal=5.1,
        liquid_density_lb_per_gal=5.6,
        vapor_pressure_by_temp_f={
            40.0: 3.4,
            50.0: 4.2,
            60.0: 5.2,
            70.0: 6.2,
            80.0: 7.4,
            90.0: 8.8,
            100.0: 10.5,
        },
    ),
    "gasoline_rvp_7": PetroleumLiquid(
        name="Gasoline RVP 7",
        vapor_molecular_weight=68.0,
        condensed_vapor_density_lb_per_gal=5.2,
        liquid_density_lb_per_gal=5.6,
        vapor_pressure_by_temp_f={
            40.0: 2.3,
            50.0: 2.9,
            60.0: 3.5,
            70.0: 4.3,
            80.0: 5.2,
            90.0: 6.2,
            100.0: 7.4,
        },
    ),
    "distillate_fuel_oil_no_2": PetroleumLiquid(
        name="Distillate fuel oil No. 2",
        vapor_molecular_weight=130.0,
        condensed_vapor_density_lb_per_gal=6.1,
        liquid_density_lb_per_gal=7.1,
        vapor_pressure_by_temp_f={
            40.0: 0.0031,
            50.0: 0.0045,
            60.0: 0.0074,
            70.0: 0.0090,
            80.0: 0.012,
            90.0: 0.016,
            100.0: 0.022,
        },
    ),
}


ANTOINE_ORGANIC_LIQUIDS: dict[str, tuple[float, float, float, float]] = {
    "benzene": (78.1, 6.905, 1211.033, 220.79),
    "cyclohexane": (84.2, 6.841, 1201.53, 222.65),
    "ethanol": (46.1, 8.321, 1718.21, 237.52),
    "methanol": (32.04, 7.897, 1474.08, 229.13),
    "toluene": (92.1, 6.954, 1344.8, 219.48),
}


PAINT_SOLAR_ABSORPTANCE: dict[tuple[str, str], float] = {
    ("aluminum_specular", "good"): 0.39,
    ("aluminum_specular", "poor"): 0.49,
    ("aluminum_diffuse", "good"): 0.60,
    ("aluminum_diffuse", "poor"): 0.68,
    ("gray_light", "good"): 0.54,
    ("gray_light", "poor"): 0.63,
    ("gray_medium", "good"): 0.68,
    ("gray_medium", "poor"): 0.74,
    ("red_primer", "good"): 0.89,
    ("red_primer", "poor"): 0.91,
    ("white", "good"): 0.17,
    ("white", "poor"): 0.34,
}


def petroleum_liquid(key: str) -> PetroleumLiquid:
    """Return a selected AP-42 petroleum liquid by normalized key."""

    try:
        return PETROLEUM_LIQUIDS[key]
    except KeyError as exc:
        available = ", ".join(sorted(PETROLEUM_LIQUIDS))
        raise KeyError(f"Unknown petroleum liquid {key!r}. Available: {available}") from exc


def petroleum_true_vapor_pressure_psia(liquid_key: str, temperature_f: float) -> float:
    """Interpolate AP-42 Table 7.1-2 true vapor pressure values."""

    liquid = petroleum_liquid(liquid_key)
    temperatures = np.array(sorted(liquid.vapor_pressure_by_temp_f), dtype=float)
    pressures = np.array([liquid.vapor_pressure_by_temp_f[temp] for temp in temperatures], dtype=float)
    if temperature_f < temperatures[0] or temperature_f > temperatures[-1]:
        raise ValueError(
            f"{temperature_f} deg F is outside the tabulated range "
            f"{temperatures[0]}-{temperatures[-1]} deg F for {liquid.name}."
        )
    return float(np.interp(temperature_f, temperatures, pressures))


def refined_petroleum_vapor_pressure_constants(
    reid_vapor_pressure_psia: float,
    astm_d86_slope_10pct_f_per_volpct: float,
) -> tuple[float, float]:
    """AP-42 Figure 7.1-15 constants for refined petroleum stocks."""

    slope_root = sqrt(astm_d86_slope_10pct_f_per_volpct)
    ln_rvp = log(reid_vapor_pressure_psia)
    a = 15.64 - 1.854 * slope_root - (0.8742 - 0.3280 * slope_root) * ln_rvp
    b = 8742.0 - 1042.0 * slope_root - (1049.0 - 179.4 * slope_root) * ln_rvp
    return a, b


def crude_oil_vapor_pressure_constants(reid_vapor_pressure_psia: float) -> tuple[float, float]:
    """AP-42 Figure 7.1-16 constants for crude oil stocks."""

    ln_rvp = log(reid_vapor_pressure_psia)
    return 12.82 - 0.9672 * ln_rvp, 7261.0 - 1216.0 * ln_rvp


def refined_petroleum_vapor_pressure_psia(
    temperature_f: float,
    reid_vapor_pressure_psia: float,
    astm_d86_slope_10pct_f_per_volpct: float,
) -> float:
    """AP-42 Figure 7.1-14b true vapor pressure for refined petroleum stocks."""

    a, b = refined_petroleum_vapor_pressure_constants(
        reid_vapor_pressure_psia,
        astm_d86_slope_10pct_f_per_volpct,
    )
    return float(exp(a - b / (temperature_f + 459.6)))


def antoine_component(name: str, mass_lb: float) -> Component:
    """Build a fixed-roof mixture component from curated AP-42 Antoine constants."""

    try:
        molecular_weight, a, b, c = ANTOINE_ORGANIC_LIQUIDS[name.lower()]
    except KeyError as exc:
        available = ", ".join(sorted(ANTOINE_ORGANIC_LIQUIDS))
        raise KeyError(f"Unknown Antoine component {name!r}. Available: {available}") from exc
    return Component(name=name.lower(), mass_lb=mass_lb, molecular_weight=molecular_weight, antoine_a=a, antoine_b=b, antoine_c=c)


def paint_solar_absorptance(color_or_type: str = "white", condition: str = "good") -> float:
    """AP-42 Table 7.1-6 paint solar absorptance lookup."""

    key = (color_or_type.lower(), condition.lower())
    try:
        return PAINT_SOLAR_ABSORPTANCE[key]
    except KeyError as exc:
        available = ", ".join(f"{color}/{cond}" for color, cond in sorted(PAINT_SOLAR_ABSORPTANCE))
        raise KeyError(f"Unknown paint absorptance {color_or_type!r}/{condition!r}. Available: {available}") from exc


def pure_organic_vapor_pressure_psia(name: str, temperature_c: float) -> float:
    """Pure organic vapor pressure from curated AP-42 Antoine constants."""

    _, a, b, c = ANTOINE_ORGANIC_LIQUIDS[name.lower()]
    return float(antoine_pressure_psia(temperature_c, a, b, c))
