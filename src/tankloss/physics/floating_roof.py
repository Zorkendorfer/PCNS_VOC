"""Floating-roof tank loss equations from AP-42 Chapter 7.1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class DeckFitting:
    """Deck fitting parameters for AP-42 Equations 2-6 through 2-8."""

    name: str
    count: float
    kfa: float
    kfb: float = 0.0
    m: float = 0.0


@dataclass(frozen=True)
class FloatingRoofResult:
    """Detailed AP-42 floating-roof loss outputs."""

    rim_seal_loss_lb_per_year: float
    withdrawal_loss_lb_per_year: float
    deck_fitting_loss_lb_per_year: float
    deck_seam_loss_lb_per_year: float
    total_loss_lb_per_year: float
    vapor_pressure_function: float
    deck_fitting_loss_factor_lbmol_per_year: float


def vapor_pressure_function(
    vapor_pressure_psia: float | np.ndarray,
    atmospheric_pressure_psia: float | np.ndarray,
) -> float | np.ndarray:
    """Vapor pressure function, P*, from AP-42 Equation 2-3."""

    ratio = np.asarray(vapor_pressure_psia, dtype=float) / np.asarray(atmospheric_pressure_psia, dtype=float)
    value = ratio / (1.0 + np.sqrt(1.0 - ratio)) ** 2
    if value.shape == ():
        return float(value)
    return value


def rim_seal_loss(
    zero_wind_loss_factor: float,
    wind_loss_factor: float,
    wind_speed_mph: float,
    wind_exponent: float,
    tank_diameter_ft: float,
    vapor_pressure_function_value: float,
    vapor_molecular_weight: float,
    product_factor: float = 1.0,
) -> float:
    """Rim seal loss, LR, from AP-42 Equation 2-2."""

    wind_term = 0.0 if wind_speed_mph == 0.0 else wind_speed_mph**wind_exponent
    loss_factor = zero_wind_loss_factor + wind_loss_factor * wind_term
    return (
        loss_factor
        * tank_diameter_ft
        * vapor_pressure_function_value
        * vapor_molecular_weight
        * product_factor
    )


def withdrawal_loss(
    annual_throughput_bbl_per_year: float,
    shell_clingage_factor_bbl_per_1000_ft2: float,
    liquid_density_lb_per_gal: float,
    tank_diameter_ft: float,
    column_count: float = 0.0,
    effective_column_diameter_ft: float = 0.0,
) -> float:
    """Withdrawal loss, LWD, from AP-42 Equation 2-4."""

    column_factor = 1.0 + (column_count * effective_column_diameter_ft) / tank_diameter_ft
    return (
        0.943
        * annual_throughput_bbl_per_year
        * shell_clingage_factor_bbl_per_1000_ft2
        * liquid_density_lb_per_gal
        / tank_diameter_ft
        * column_factor
    )


def liquid_density_from_weight_fractions(
    weight_fractions: Iterable[float],
    component_densities_lb_per_gal: Iterable[float],
) -> float:
    """Mixture liquid density from AP-42 Example 3 reciprocal-weighted form."""

    fractions = np.asarray(list(weight_fractions), dtype=float)
    densities = np.asarray(list(component_densities_lb_per_gal), dtype=float)
    if fractions.shape != densities.shape:
        raise ValueError("weight fractions and densities must have matching lengths.")
    if not np.isclose(fractions.sum(), 1.0):
        raise ValueError("weight fractions must sum to 1.0.")
    return float(1.0 / np.sum(fractions / densities))


def deck_fitting_loss_factor(
    fitting: DeckFitting,
    wind_speed_mph: float,
    wind_speed_correction_factor: float = 0.7,
    wind_dependent: bool = True,
) -> float:
    """Single fitting loss factor, KFi, from AP-42 Equation 2-7 or 2-8."""

    if not wind_dependent:
        return fitting.kfa
    return fitting.kfa + fitting.kfb * (wind_speed_correction_factor * wind_speed_mph) ** fitting.m


def total_deck_fitting_loss_factor(
    fittings: Iterable[DeckFitting],
    wind_speed_mph: float,
    wind_speed_correction_factor: float = 0.7,
    wind_dependent: bool = True,
) -> float:
    """Total deck fitting loss factor, FF, from AP-42 Equation 2-6."""

    return float(
        sum(
            fitting.count
            * deck_fitting_loss_factor(
                fitting,
                wind_speed_mph=wind_speed_mph,
                wind_speed_correction_factor=wind_speed_correction_factor,
                wind_dependent=wind_dependent,
            )
            for fitting in fittings
        )
    )


def deck_fitting_loss(
    deck_fitting_loss_factor_value: float,
    vapor_pressure_function_value: float,
    vapor_molecular_weight: float,
    product_factor: float = 1.0,
) -> float:
    """Deck fitting loss, LF, from AP-42 Equation 2-5."""

    return (
        deck_fitting_loss_factor_value
        * vapor_pressure_function_value
        * vapor_molecular_weight
        * product_factor
    )


def deck_seam_loss(
    deck_seam_loss_factor: float,
    deck_seam_length_factor: float,
    tank_diameter_ft: float,
    vapor_pressure_function_value: float,
    vapor_molecular_weight: float,
    product_factor: float = 1.0,
) -> float:
    """Deck seam loss, LD, from AP-42 Equation 2-9."""

    return (
        deck_seam_loss_factor
        * deck_seam_length_factor
        * tank_diameter_ft**2
        * vapor_pressure_function_value
        * vapor_molecular_weight
        * product_factor
    )


def floating_roof_losses(
    tank_diameter_ft: float,
    vapor_pressure_psia: float,
    atmospheric_pressure_psia: float,
    vapor_molecular_weight: float,
    annual_throughput_bbl_per_year: float,
    shell_clingage_factor_bbl_per_1000_ft2: float,
    liquid_density_lb_per_gal: float,
    rim_seal_zero_wind_loss_factor: float,
    rim_seal_wind_loss_factor: float,
    rim_seal_wind_exponent: float,
    wind_speed_mph: float,
    deck_fittings: Iterable[DeckFitting],
    product_factor: float = 1.0,
    column_count: float = 0.0,
    effective_column_diameter_ft: float = 0.0,
    deck_seam_loss_factor: float = 0.0,
    deck_seam_length_factor: float = 0.0,
    wind_dependent_deck_fittings: bool = True,
) -> FloatingRoofResult:
    """Run AP-42 floating-roof loss equations 2-1 through 2-9."""

    p_star = vapor_pressure_function(vapor_pressure_psia, atmospheric_pressure_psia)
    rim = rim_seal_loss(
        rim_seal_zero_wind_loss_factor,
        rim_seal_wind_loss_factor,
        wind_speed_mph,
        rim_seal_wind_exponent,
        tank_diameter_ft,
        p_star,
        vapor_molecular_weight,
        product_factor,
    )
    withdrawal = withdrawal_loss(
        annual_throughput_bbl_per_year,
        shell_clingage_factor_bbl_per_1000_ft2,
        liquid_density_lb_per_gal,
        tank_diameter_ft,
        column_count,
        effective_column_diameter_ft,
    )
    fitting_factor = total_deck_fitting_loss_factor(
        deck_fittings,
        wind_speed_mph=wind_speed_mph,
        wind_dependent=wind_dependent_deck_fittings,
    )
    fitting = deck_fitting_loss(fitting_factor, p_star, vapor_molecular_weight, product_factor)
    seam = deck_seam_loss(
        deck_seam_loss_factor,
        deck_seam_length_factor,
        tank_diameter_ft,
        p_star,
        vapor_molecular_weight,
        product_factor,
    )
    total = rim + withdrawal + fitting + seam
    return FloatingRoofResult(
        rim_seal_loss_lb_per_year=float(rim),
        withdrawal_loss_lb_per_year=float(withdrawal),
        deck_fitting_loss_lb_per_year=float(fitting),
        deck_seam_loss_lb_per_year=float(seam),
        total_loss_lb_per_year=float(total),
        vapor_pressure_function=float(p_star),
        deck_fitting_loss_factor_lbmol_per_year=float(fitting_factor),
    )
