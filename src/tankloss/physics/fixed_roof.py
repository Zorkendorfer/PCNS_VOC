"""Fixed-roof tank loss equations from AP-42 Chapter 7.1.

The functions in this module follow the 09/97 AP-42 notation for equations
1-1 through 1-25. Units are AP-42 English units unless noted otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


AP42_IDEAL_GAS_R = 10.731  # psia ft3 / lb-mole deg R
MMHG_PER_PSIA = 760.0 / 14.7


@dataclass(frozen=True)
class Component:
    """Liquid component data for Raoult-law mixture vapor properties."""

    name: str
    mass_lb: float
    molecular_weight: float
    antoine_a: float
    antoine_b: float
    antoine_c: float


@dataclass(frozen=True)
class FixedRoofTank:
    """Geometry for a vertical fixed cone-roof tank."""

    diameter_ft: float
    shell_height_ft: float
    liquid_height_ft: float
    cone_roof_slope_ft_per_ft: float = 0.0625


@dataclass(frozen=True)
class FixedRoofResult:
    """Detailed fixed-roof loss calculation outputs."""

    standing_loss_lb_per_year: float
    working_loss_lb_per_year: float
    total_loss_lb_per_year: float
    vapor_space_volume_ft3: float
    vapor_space_outage_ft: float
    vapor_density_lb_per_ft3: float
    vapor_space_expansion_factor: float
    vapor_space_saturation_factor: float
    vapor_molecular_weight: float
    vapor_pressure_psia: float
    liquid_surface_temperature_r: float


def _asarray(value: float | np.ndarray) -> np.ndarray:
    return np.asarray(value, dtype=float)


def _maybe_scalar(value: np.ndarray) -> float | np.ndarray:
    if value.shape == ():
        return float(value)
    return value


def rankine_to_celsius_ap42(temperature_r: float | np.ndarray) -> float | np.ndarray:
    """Convert deg R to deg C using AP-42's stated conversion, (R - 492) / 1.8."""

    return _maybe_scalar((_asarray(temperature_r) - 492.0) / 1.8)


def fahrenheit_to_rankine_ap42(temperature_f: float | np.ndarray) -> float | np.ndarray:
    """Convert deg F to deg R using the AP-42 worked-example convention, F + 460."""

    return _maybe_scalar(_asarray(temperature_f) + 460.0)


def antoine_pressure_psia(
    temperature_c: float | np.ndarray,
    a: float,
    b: float,
    c: float,
) -> float | np.ndarray:
    """Pure-component vapor pressure from AP-42 Equation 1-12b.

    The Antoine result is in mm Hg in the source equation and is converted
    to psia with AP-42's 760 mm Hg = 14.7 psia factor.
    """

    pressure_mmhg = 10.0 ** (a - b / (_asarray(temperature_c) + c))
    return _maybe_scalar(pressure_mmhg / MMHG_PER_PSIA)


def cone_roof_outage(
    diameter_ft: float | np.ndarray,
    roof_slope_ft_per_ft: float | np.ndarray = 0.0625,
) -> float | np.ndarray:
    """Cone-roof outage, HRO, from AP-42 Equation 1-6."""

    radius_ft = _asarray(diameter_ft) / 2.0
    return _maybe_scalar((_asarray(roof_slope_ft_per_ft) * radius_ft) / 3.0)


def vapor_space_outage(
    shell_height_ft: float | np.ndarray,
    liquid_height_ft: float | np.ndarray,
    roof_outage_ft: float | np.ndarray,
) -> float | np.ndarray:
    """Vapor space outage, HVO, from AP-42 Equation 1-4."""

    return _maybe_scalar(
        _asarray(shell_height_ft) - _asarray(liquid_height_ft) + _asarray(roof_outage_ft)
    )


def vapor_space_volume(
    diameter_ft: float | np.ndarray,
    vapor_space_outage_ft: float | np.ndarray,
) -> float | np.ndarray:
    """Tank vapor space volume, VV, from AP-42 Equation 1-3."""

    return _maybe_scalar((np.pi / 4.0) * _asarray(diameter_ft) ** 2 * _asarray(vapor_space_outage_ft))


def daily_average_ambient_temperature(
    daily_max_ambient_r: float | np.ndarray,
    daily_min_ambient_r: float | np.ndarray,
) -> float | np.ndarray:
    """Daily average ambient temperature, TAA, from AP-42 Equation 1-14."""

    return _maybe_scalar((_asarray(daily_max_ambient_r) + _asarray(daily_min_ambient_r)) / 2.0)


def liquid_bulk_temperature(
    daily_average_ambient_r: float | np.ndarray,
    paint_solar_absorptance: float | np.ndarray,
) -> float | np.ndarray:
    """Liquid bulk temperature, TB, from AP-42 Equation 1-15."""

    return _maybe_scalar(_asarray(daily_average_ambient_r) + 6.0 * _asarray(paint_solar_absorptance) - 1.0)


def daily_liquid_surface_temperature(
    daily_average_ambient_r: float | np.ndarray,
    liquid_bulk_temperature_r: float | np.ndarray,
    paint_solar_absorptance: float | np.ndarray,
    daily_solar_insolation_btu_ft2_day: float | np.ndarray,
) -> float | np.ndarray:
    """Daily average liquid surface temperature, TLA, from AP-42 Equation 1-13."""

    return _maybe_scalar(
        0.44 * _asarray(daily_average_ambient_r)
        + 0.56 * _asarray(liquid_bulk_temperature_r)
        + 0.0079
        * _asarray(paint_solar_absorptance)
        * _asarray(daily_solar_insolation_btu_ft2_day)
    )


def daily_vapor_temperature_range(
    daily_max_ambient_r: float | np.ndarray,
    daily_min_ambient_r: float | np.ndarray,
    paint_solar_absorptance: float | np.ndarray,
    daily_solar_insolation_btu_ft2_day: float | np.ndarray,
) -> float | np.ndarray:
    """Daily vapor temperature range, TV, from AP-42 Equation 1-17."""

    ambient_range_r = _asarray(daily_max_ambient_r) - _asarray(daily_min_ambient_r)
    return _maybe_scalar(
        0.72 * ambient_range_r
        + 0.028
        * _asarray(paint_solar_absorptance)
        * _asarray(daily_solar_insolation_btu_ft2_day)
    )


def daily_vapor_pressure_range(
    vapor_pressure_max_psia: float | np.ndarray,
    vapor_pressure_min_psia: float | np.ndarray,
) -> float | np.ndarray:
    """Daily vapor pressure range, PV, from AP-42 Equation 1-18."""

    return _maybe_scalar(_asarray(vapor_pressure_max_psia) - _asarray(vapor_pressure_min_psia))


def vapor_density(
    vapor_molecular_weight: float | np.ndarray,
    vapor_pressure_psia: float | np.ndarray,
    liquid_surface_temperature_r: float | np.ndarray,
) -> float | np.ndarray:
    """Vapor density, WV, from AP-42 Equation 1-9."""

    return _maybe_scalar(
        _asarray(vapor_molecular_weight)
        * _asarray(vapor_pressure_psia)
        / (AP42_IDEAL_GAS_R * _asarray(liquid_surface_temperature_r))
    )


def vapor_space_expansion_factor(
    daily_vapor_temperature_range_r: float | np.ndarray,
    liquid_surface_temperature_r: float | np.ndarray,
    daily_vapor_pressure_range_psia: float | np.ndarray,
    breather_vent_pressure_range_psig: float | np.ndarray,
    atmospheric_pressure_psia: float | np.ndarray,
    vapor_pressure_psia: float | np.ndarray,
) -> float | np.ndarray:
    """Vapor space expansion factor, KE, from AP-42 Equation 1-16."""

    temperature_term = _asarray(daily_vapor_temperature_range_r) / _asarray(liquid_surface_temperature_r)
    pressure_term = (
        _asarray(daily_vapor_pressure_range_psia) - _asarray(breather_vent_pressure_range_psig)
    ) / (_asarray(atmospheric_pressure_psia) - _asarray(vapor_pressure_psia))
    return _maybe_scalar(temperature_term + pressure_term)


def vapor_space_saturation_factor(
    vapor_pressure_psia: float | np.ndarray,
    vapor_space_outage_ft: float | np.ndarray,
) -> float | np.ndarray:
    """Vented vapor saturation factor, KS, from AP-42 Equation 1-22."""

    return _maybe_scalar(1.0 / (1.0 + 0.053 * _asarray(vapor_pressure_psia) * _asarray(vapor_space_outage_ft)))


def standing_storage_loss(
    vapor_space_volume_ft3: float | np.ndarray,
    vapor_density_lb_per_ft3: float | np.ndarray,
    vapor_space_expansion_factor_value: float | np.ndarray,
    vapor_space_saturation_factor_value: float | np.ndarray,
) -> float | np.ndarray:
    """Standing storage loss, LS, from AP-42 Equation 1-2."""

    return _maybe_scalar(
        365.0
        * _asarray(vapor_space_volume_ft3)
        * _asarray(vapor_density_lb_per_ft3)
        * _asarray(vapor_space_expansion_factor_value)
        * _asarray(vapor_space_saturation_factor_value)
    )


def turnover_factor(turnovers_per_year: float | np.ndarray) -> float | np.ndarray:
    """Working-loss turnover factor, KN, from AP-42 Equation 1-23 note."""

    turnovers = _asarray(turnovers_per_year)
    factor = np.where(turnovers > 36.0, (180.0 + turnovers) / (6.0 * turnovers), 1.0)
    return _maybe_scalar(factor)


def working_loss(
    vapor_molecular_weight: float | np.ndarray,
    vapor_pressure_psia: float | np.ndarray,
    annual_net_throughput_bbl_per_year: float | np.ndarray,
    turnover_factor_value: float | np.ndarray,
    product_factor: float | np.ndarray = 1.0,
) -> float | np.ndarray:
    """Working loss, LW, from AP-42 Equation 1-23."""

    return _maybe_scalar(
        0.0010
        * _asarray(vapor_molecular_weight)
        * _asarray(vapor_pressure_psia)
        * _asarray(annual_net_throughput_bbl_per_year)
        * _asarray(turnover_factor_value)
        * _asarray(product_factor)
    )


def mixture_vapor_properties(
    components: Iterable[Component],
    liquid_surface_temperature_r: float,
    round_temperature_c: int | None = None,
) -> dict[str, np.ndarray | float | list[str]]:
    """Calculate AP-42 Raoult-law mixture vapor pressure and vapor molecular weight.

    Returns liquid mole fractions, pure vapor pressures, partial pressures,
    vapor mole fractions, total vapor pressure, and vapor molecular weight.
    """

    component_list = list(components)
    if not component_list:
        raise ValueError("At least one component is required.")

    names = [component.name for component in component_list]
    masses = np.array([component.mass_lb for component in component_list], dtype=float)
    molecular_weights = np.array([component.molecular_weight for component in component_list], dtype=float)
    moles = masses / molecular_weights
    liquid_mole_fractions = moles / moles.sum()

    temperature_c = float(rankine_to_celsius_ap42(liquid_surface_temperature_r))
    if round_temperature_c is not None:
        temperature_c = round(temperature_c, round_temperature_c)
    pure_pressures_psia = np.array(
        [
            antoine_pressure_psia(
                temperature_c,
                component.antoine_a,
                component.antoine_b,
                component.antoine_c,
            )
            for component in component_list
        ],
        dtype=float,
    )
    partial_pressures_psia = pure_pressures_psia * liquid_mole_fractions
    total_pressure_psia = float(partial_pressures_psia.sum())
    vapor_mole_fractions = partial_pressures_psia / total_pressure_psia
    vapor_molecular_weight = float(np.sum(molecular_weights * vapor_mole_fractions))

    return {
        "names": names,
        "moles": moles,
        "liquid_mole_fractions": liquid_mole_fractions,
        "pure_pressures_psia": pure_pressures_psia,
        "partial_pressures_psia": partial_pressures_psia,
        "vapor_mole_fractions": vapor_mole_fractions,
        "vapor_pressure_psia": total_pressure_psia,
        "vapor_molecular_weight": vapor_molecular_weight,
    }


def fixed_roof_losses(
    tank: FixedRoofTank,
    components: Iterable[Component],
    daily_max_ambient_r: float,
    daily_min_ambient_r: float,
    daily_solar_insolation_btu_ft2_day: float,
    paint_solar_absorptance: float,
    atmospheric_pressure_psia: float,
    annual_net_throughput_bbl_per_year: float,
    turnovers_per_year: float,
    breather_vent_pressure_setting_psig: float = 0.03,
    breather_vent_vacuum_setting_psig: float = -0.03,
    product_factor: float = 1.0,
    mixture_temperature_round_c: int | None = None,
) -> FixedRoofResult:
    """Run the AP-42 fixed-roof calculation for a vertical cone-roof tank."""

    roof_outage_ft = cone_roof_outage(tank.diameter_ft, tank.cone_roof_slope_ft_per_ft)
    outage_ft = vapor_space_outage(tank.shell_height_ft, tank.liquid_height_ft, roof_outage_ft)
    volume_ft3 = vapor_space_volume(tank.diameter_ft, outage_ft)

    ambient_avg_r = daily_average_ambient_temperature(daily_max_ambient_r, daily_min_ambient_r)
    bulk_temp_r = liquid_bulk_temperature(ambient_avg_r, paint_solar_absorptance)
    liquid_surface_temp_r = daily_liquid_surface_temperature(
        ambient_avg_r,
        bulk_temp_r,
        paint_solar_absorptance,
        daily_solar_insolation_btu_ft2_day,
    )
    mixture = mixture_vapor_properties(
        components,
        liquid_surface_temp_r,
        round_temperature_c=mixture_temperature_round_c,
    )
    vapor_pressure_psia = float(mixture["vapor_pressure_psia"])
    vapor_mw = float(mixture["vapor_molecular_weight"])

    vapor_temp_range_r = daily_vapor_temperature_range(
        daily_max_ambient_r,
        daily_min_ambient_r,
        paint_solar_absorptance,
        daily_solar_insolation_btu_ft2_day,
    )
    min_liquid_surface_temp_r = liquid_surface_temp_r - 0.25 * vapor_temp_range_r
    max_liquid_surface_temp_r = liquid_surface_temp_r + 0.25 * vapor_temp_range_r
    min_pressure_psia = float(
        mixture_vapor_properties(
            components,
            min_liquid_surface_temp_r,
            round_temperature_c=mixture_temperature_round_c,
        )["vapor_pressure_psia"]
    )
    max_pressure_psia = float(
        mixture_vapor_properties(
            components,
            max_liquid_surface_temp_r,
            round_temperature_c=mixture_temperature_round_c,
        )["vapor_pressure_psia"]
    )
    vapor_pressure_range_psia = daily_vapor_pressure_range(max_pressure_psia, min_pressure_psia)
    breather_range_psig = breather_vent_pressure_setting_psig - breather_vent_vacuum_setting_psig

    density = vapor_density(vapor_mw, vapor_pressure_psia, liquid_surface_temp_r)
    expansion = vapor_space_expansion_factor(
        vapor_temp_range_r,
        liquid_surface_temp_r,
        vapor_pressure_range_psia,
        breather_range_psig,
        atmospheric_pressure_psia,
        vapor_pressure_psia,
    )
    saturation = vapor_space_saturation_factor(vapor_pressure_psia, outage_ft)
    standing = standing_storage_loss(volume_ft3, density, expansion, saturation)
    working = working_loss(
        vapor_mw,
        vapor_pressure_psia,
        annual_net_throughput_bbl_per_year,
        turnover_factor(turnovers_per_year),
        product_factor,
    )
    total = standing + working

    return FixedRoofResult(
        standing_loss_lb_per_year=float(standing),
        working_loss_lb_per_year=float(working),
        total_loss_lb_per_year=float(total),
        vapor_space_volume_ft3=float(volume_ft3),
        vapor_space_outage_ft=float(outage_ft),
        vapor_density_lb_per_ft3=float(density),
        vapor_space_expansion_factor=float(expansion),
        vapor_space_saturation_factor=float(saturation),
        vapor_molecular_weight=vapor_mw,
        vapor_pressure_psia=vapor_pressure_psia,
        liquid_surface_temperature_r=float(liquid_surface_temp_r),
    )
