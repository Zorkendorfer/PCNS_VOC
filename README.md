# PCNS_VOC

Physics-constrained neural surrogate research scaffold for AP-42 organic liquid storage tank VOC loss calculations.

The project starts from a fixed-roof tank physics core and will grow toward the soft-vs-hard physics surrogate experiment described in `PLAN.md`.

## Current Status

- AP-42 Chapter 7.1 fixed-roof equations implemented for vertical cone-roof tanks.
- AP-42 floating-roof equations implemented for external and internal floating roof tanks.
- Raoult-law mixture vapor pressure and vapor molecular weight helpers.
- AP-42 Example 1, Example 3, and Example 4 regression tests.
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

## Source Material

AP-42 Chapter 7.1 is used as the public technical source for the tank-loss equations and worked examples. Raw extracted AP-42 text is treated as local reference material and is not included in this MIT-licensed repository.
