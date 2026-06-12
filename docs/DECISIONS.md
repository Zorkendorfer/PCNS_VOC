# Decisions

## 2026-06-12 - Use AP-42 as the Truth Model for M1

The physics core is anchored to AP-42 Chapter 7.1 equations and worked examples. Tests reproduce AP-42 numerical examples within tolerances that account for the chapter's rounded intermediate values.

## 2026-06-12 - Keep Raw AP-42 Extraction Out of the MIT Repository

The local extracted `ap42_c07s01.txt` file is ignored. The repository includes original implementation code, tests, and documentation, while treating the AP-42 extraction as local reference material.

## 2026-06-12 - Implement Fixed-Roof and Floating-Roof Physics First

M1 starts with the AP-42 fixed-roof Example 1 and floating-roof Examples 3 and 4 because they cover the main standing, working, rim-seal, withdrawal, deck-fitting, and deck-seam equation families needed for the later surrogate truth model.
