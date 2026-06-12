import pytest

from tankloss.physics.fixed_roof import (
    Component,
    daily_average_ambient_temperature,
    daily_liquid_surface_temperature,
    liquid_bulk_temperature,
    mixture_vapor_properties,
)
from tankloss.physics.floating_roof import (
    DeckFitting,
    deck_fitting_loss_factor,
    floating_roof_losses,
    liquid_density_from_weight_fractions,
    total_deck_fitting_loss_factor,
    vapor_pressure_function,
)


BENZENE = Component("benzene", 750.0, 78.1, 6.905, 1211.033, 220.79)
TOLUENE = Component("toluene", 150.0, 92.1, 6.954, 1344.8, 219.48)
CYCLOHEXANE = Component("cyclohexane", 100.0, 84.2, 6.841, 1201.53, 222.65)
MIXTURE = [BENZENE, TOLUENE, CYCLOHEXANE]


def test_ap42_example3_external_floating_roof_mixture_properties():
    taa = daily_average_ambient_temperature(522.2, 505.6)
    tb = liquid_bulk_temperature(taa, 0.17)
    tla = daily_liquid_surface_temperature(taa, tb, 0.17, 1165.0)
    mixture = mixture_vapor_properties(MIXTURE, tla, round_temperature_c=0)

    assert taa == pytest.approx(513.9)
    assert tb == pytest.approx(513.92)
    assert tla == pytest.approx(515.5, abs=0.1)
    assert mixture["liquid_mole_fractions"] == pytest.approx([0.773, 0.131, 0.096], abs=0.002)
    assert mixture["pure_pressures_psia"] == pytest.approx([1.04, 0.29, 1.08], abs=0.02)
    assert mixture["partial_pressures_psia"] == pytest.approx([0.80, 0.038, 0.104], abs=0.01)
    assert mixture["vapor_pressure_psia"] == pytest.approx(0.942, abs=0.015)
    assert mixture["vapor_mole_fractions"] == pytest.approx([0.85, 0.040, 0.110], abs=0.015)
    assert mixture["vapor_molecular_weight"] == pytest.approx(79.3, abs=0.5)


def test_ap42_example3_external_floating_roof_losses():
    fittings = [
        DeckFitting("access hatch", count=1, kfa=36.0, kfb=5.9, m=1.2),
        DeckFitting("vacuum breaker", count=1, kfa=7.8, kfb=0.01, m=4.0),
        DeckFitting("gauge hatch/sample port", count=1, kfa=2.3),
    ]

    assert deck_fitting_loss_factor(fittings[0], wind_speed_mph=10.2) == pytest.approx(98.4, abs=0.5)
    assert deck_fitting_loss_factor(fittings[1], wind_speed_mph=10.2) == pytest.approx(33.8, abs=0.5)
    assert total_deck_fitting_loss_factor(fittings, wind_speed_mph=10.2) == pytest.approx(134.5, abs=0.8)
    assert liquid_density_from_weight_fractions([0.75, 0.15, 0.10], [7.4, 7.3, 6.5]) == pytest.approx(
        7.3, abs=0.1
    )

    result = floating_roof_losses(
        tank_diameter_ft=20.0,
        vapor_pressure_psia=0.942,
        atmospheric_pressure_psia=14.7,
        vapor_molecular_weight=79.3,
        annual_throughput_bbl_per_year=23810.0,
        shell_clingage_factor_bbl_per_1000_ft2=0.0015,
        liquid_density_lb_per_gal=7.3,
        rim_seal_zero_wind_loss_factor=1.6,
        rim_seal_wind_loss_factor=0.3,
        rim_seal_wind_exponent=1.6,
        wind_speed_mph=10.2,
        deck_fittings=fittings,
    )

    assert result.vapor_pressure_function == pytest.approx(0.017, abs=0.001)
    assert result.withdrawal_loss_lb_per_year == pytest.approx(12.0, abs=1.0)
    assert result.rim_seal_loss_lb_per_year == pytest.approx(376.0, abs=15.0)
    assert result.deck_fitting_loss_lb_per_year == pytest.approx(181.0, abs=8.0)
    assert result.deck_seam_loss_lb_per_year == pytest.approx(0.0)
    assert result.total_loss_lb_per_year == pytest.approx(569.0, abs=20.0)


def test_ap42_example4_internal_floating_roof_gasoline_losses():
    p_star = vapor_pressure_function(7.18, 14.7)
    assert p_star == pytest.approx(0.166, abs=0.002)

    fittings = [
        DeckFitting("access hatch", count=2, kfa=36.0),
        DeckFitting("automatic gauge float well", count=1, kfa=14.0),
        DeckFitting("pipe column well", count=1, kfa=10.0),
        DeckFitting("ladder well", count=1, kfa=56.0),
        DeckFitting("adjustable deck legs", count=5.0 + 70.0 / 10.0 + 70.0**2 / 600.0, kfa=7.9),
        DeckFitting("sample pipe well", count=1, kfa=43.1),
        DeckFitting("vacuum breaker", count=1, kfa=6.2),
    ]

    result = floating_roof_losses(
        tank_diameter_ft=70.0,
        vapor_pressure_psia=7.18,
        atmospheric_pressure_psia=14.7,
        vapor_molecular_weight=62.0,
        annual_throughput_bbl_per_year=1_190_500.0,
        shell_clingage_factor_bbl_per_1000_ft2=0.0015,
        liquid_density_lb_per_gal=5.6,
        rim_seal_zero_wind_loss_factor=0.3,
        rim_seal_wind_loss_factor=0.6,
        rim_seal_wind_exponent=0.0,
        wind_speed_mph=0.0,
        deck_fittings=fittings,
        column_count=1.0,
        effective_column_diameter_ft=1.0,
        deck_seam_loss_factor=0.0,
        deck_seam_length_factor=0.0,
        wind_dependent_deck_fittings=False,
    )

    assert result.deck_fitting_loss_factor_lbmol_per_year == pytest.approx(361.0, abs=1.0)
    assert result.withdrawal_loss_lb_per_year == pytest.approx(137.0, abs=2.0)
    assert result.rim_seal_loss_lb_per_year == pytest.approx(216.0, abs=4.0)
    assert result.deck_fitting_loss_lb_per_year == pytest.approx(3715.0, abs=40.0)
    assert result.deck_seam_loss_lb_per_year == pytest.approx(0.0)
    assert result.total_loss_lb_per_year == pytest.approx(4068.0, abs=50.0)
