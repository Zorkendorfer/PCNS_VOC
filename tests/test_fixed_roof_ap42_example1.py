import pytest

from tankloss.physics.fixed_roof import (
    Component,
    FixedRoofTank,
    antoine_pressure_psia,
    daily_average_ambient_temperature,
    daily_liquid_surface_temperature,
    daily_vapor_temperature_range,
    fahrenheit_to_rankine_ap42,
    fixed_roof_losses,
    liquid_bulk_temperature,
    mixture_vapor_properties,
    rankine_to_celsius_ap42,
)


BENZENE = Component("benzene", 2812.0, 78.1, 6.905, 1211.033, 220.79)
TOLUENE = Component("toluene", 258.0, 92.1, 6.954, 1344.8, 219.48)
CYCLOHEXANE = Component("cyclohexane", 101.0, 84.2, 6.841, 1201.53, 222.65)
COMPONENTS = [BENZENE, TOLUENE, CYCLOHEXANE]


def test_ap42_example1_temperature_chain():
    tax = fahrenheit_to_rankine_ap42(64.3)
    tan = fahrenheit_to_rankine_ap42(36.2)
    taa = daily_average_ambient_temperature(tax, tan)
    tb = liquid_bulk_temperature(taa, paint_solar_absorptance=0.17)
    tla = daily_liquid_surface_temperature(taa, tb, 0.17, 1568.0)
    tv = daily_vapor_temperature_range(tax, tan, 0.17, 1568.0)

    assert taa == pytest.approx(510.25)
    assert tb == pytest.approx(510.27)
    assert tla == pytest.approx(512.36, abs=0.01)
    assert tv == pytest.approx(27.7, abs=0.1)
    assert rankine_to_celsius_ap42(tla) == pytest.approx(11.31, abs=0.01)


def test_ap42_example1_mixture_properties_at_average_temperature():
    mixture = mixture_vapor_properties(COMPONENTS, 512.36, round_temperature_c=0)

    assert mixture["liquid_mole_fractions"] == pytest.approx([0.90, 0.07, 0.03], abs=0.006)
    assert antoine_pressure_psia(11.0, 6.905, 1211.033, 220.79) == pytest.approx(0.926, rel=0.01)
    assert mixture["pure_pressures_psia"] == pytest.approx([0.926, 0.255, 0.966], rel=0.015)
    assert mixture["partial_pressures_psia"] == pytest.approx([0.833, 0.018, 0.029], abs=0.006)
    assert mixture["vapor_pressure_psia"] == pytest.approx(0.880, abs=0.006)
    assert mixture["vapor_mole_fractions"] == pytest.approx([0.947, 0.020, 0.033], abs=0.008)
    assert mixture["vapor_molecular_weight"] == pytest.approx(78.6, abs=0.4)


def test_ap42_example1_fixed_roof_losses():
    result = fixed_roof_losses(
        tank=FixedRoofTank(diameter_ft=6.0, shell_height_ft=12.0, liquid_height_ft=8.0),
        components=COMPONENTS,
        daily_max_ambient_r=fahrenheit_to_rankine_ap42(64.3),
        daily_min_ambient_r=fahrenheit_to_rankine_ap42(36.2),
        daily_solar_insolation_btu_ft2_day=1568.0,
        paint_solar_absorptance=0.17,
        atmospheric_pressure_psia=14.7,
        annual_net_throughput_bbl_per_year=201.0,
        turnovers_per_year=5.0,
        product_factor=1.0,
        mixture_temperature_round_c=0,
    )

    assert result.vapor_space_outage_ft == pytest.approx(4.0625)
    assert result.vapor_space_volume_ft3 == pytest.approx(114.86, abs=0.01)
    assert result.vapor_density_lb_per_ft3 == pytest.approx(1.26e-2, rel=0.02)
    assert result.vapor_space_expansion_factor == pytest.approx(0.077, abs=0.004)
    assert result.vapor_space_saturation_factor == pytest.approx(0.841, abs=0.003)
    assert result.standing_loss_lb_per_year == pytest.approx(34.2, abs=1.0)
    assert result.working_loss_lb_per_year == pytest.approx(13.9, abs=0.2)
    assert result.total_loss_lb_per_year == pytest.approx(48.1, abs=1.1)
