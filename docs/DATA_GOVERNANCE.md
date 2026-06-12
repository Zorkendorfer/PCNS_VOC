# Data Governance

This repository must not include KN Energies internal data unless written approval has been obtained and recorded outside the repository.

Until approval exists, all scenarios, tank farms, product slates, operations, and economic inputs must be synthetic, public, or clearly derived from open sources.

## Current Allowed Inputs

- AP-42 equations and worked examples as public technical reference material.
- Synthetic tank geometry and operating schedules.
- Public meteorological and price proxies, once selected and cited.
- User-entered parameters that are not copied from confidential systems.

## Current Exclusions

- KN tank inventories, dimensions, schedules, product allocations, SCADA exports, loading windows, commercial contracts, and internal prices.
- Any document or spreadsheet whose access depends on employment, vendor, client, or terminal-system privileges.

## Rule For Future Work

If a value may plausibly be internal operational knowledge, mark it as `[TODO-JONAS: approval/data source needed]` and keep the runnable default synthetic.
