import pytest

from tankloss.properties import (
    antoine_component,
    paint_solar_absorptance,
    petroleum_liquid,
    petroleum_true_vapor_pressure_psia,
    pure_organic_vapor_pressure_psia,
    refined_petroleum_vapor_pressure_constants,
    refined_petroleum_vapor_pressure_psia,
)


def test_ap42_table_7_1_2_gasoline_rvp13_interpolates_example4_pressure():
    gasoline = petroleum_liquid("gasoline_rvp_13")

    assert gasoline.vapor_molecular_weight == pytest.approx(62.0)
    assert gasoline.liquid_density_lb_per_gal == pytest.approx(5.6)
    assert petroleum_true_vapor_pressure_psia("gasoline_rvp_13", 62.0) == pytest.approx(7.18)


def test_ap42_table_7_1_2_gasoline_vapor_pressure_is_monotone():
    pressures = [
        petroleum_true_vapor_pressure_psia("gasoline_rvp_10", temperature_f)
        for temperature_f in [40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    ]

    assert pressures == sorted(pressures)


def test_ap42_figure_7_1_15_refined_stock_constants_are_reasonable_for_motor_gasoline():
    a, b = refined_petroleum_vapor_pressure_constants(
        reid_vapor_pressure_psia=13.0,
        astm_d86_slope_10pct_f_per_volpct=3.0,
    )
    pressure_62f = refined_petroleum_vapor_pressure_psia(
        temperature_f=62.0,
        reid_vapor_pressure_psia=13.0,
        astm_d86_slope_10pct_f_per_volpct=3.0,
    )

    assert a == pytest.approx(11.64, abs=0.01)
    assert b == pytest.approx(5044.0, abs=2.0)
    assert pressure_62f == pytest.approx(7.18, abs=0.05)


def test_ap42_table_7_1_5_selected_antoine_constants_feed_component_builder():
    benzene = antoine_component("benzene", mass_lb=2812.0)

    assert benzene.molecular_weight == pytest.approx(78.1)
    assert pure_organic_vapor_pressure_psia("benzene", 11.0) == pytest.approx(0.926, rel=0.01)
    assert pure_organic_vapor_pressure_psia("methanol", 20.0) == pytest.approx(1.86, rel=0.04)


def test_ap42_table_7_1_6_paint_absorptance_lookup():
    assert paint_solar_absorptance("white", "good") == pytest.approx(0.17)
    assert paint_solar_absorptance("white", "poor") == pytest.approx(0.34)
    assert paint_solar_absorptance("gray_medium", "good") == pytest.approx(0.68)
