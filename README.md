# PCNS_VOC

Physics-constrained neural surrogate research scaffold for AP-42 organic liquid storage tank VOC loss calculations.

The project starts from a fixed-roof tank physics core and will grow toward the soft-vs-hard physics surrogate experiment described in `PLAN.md`.

## Current Status

- AP-42 Chapter 7.1 fixed-roof equations implemented for vertical cone-roof tanks.
- AP-42 floating-roof equations implemented for external and internal floating roof tanks.
- Raoult-law mixture vapor pressure and vapor molecular weight helpers.
- Curated AP-42 product-property helpers for gasoline RVP classes, selected Antoine liquids, refined-stock RVP correlations, and paint absorptance.
- AP-42 Example 1, Example 3, and Example 4 regression tests.
- Deterministic synthetic Klaipeda tank-farm scenario generator with one year of hourly weather and tank-operation rows.
- AP-42 truth-label generator for daily surrogate training rows.
- GitHub Actions CI running the pytest suite on Python 3.11.

## Development

Install the package with test dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run tests:

```powershell
python -m pytest -q
```

Build the default synthetic scenario:

```powershell
python scripts/02_build_scenario.py --output-dir outputs/02_build_scenario/default
```

Generate daily AP-42 truth labels:

```powershell
python scripts/04_generate_training_data.py --output outputs/04_generate_training_data/default/training_data.csv
```

## Source Material

AP-42 Chapter 7.1 is used as the public technical source for the tank-loss equations and worked examples. Raw extracted AP-42 text is treated as local reference material and is not included in this MIT-licensed repository.
