# TANKLOSS-PINN — Project Plan

**Working title:** *Physics-constrained neural surrogates for evaporative VOC losses from petroleum product storage tanks: testing the generalization of soft-penalty fabrication artifacts beyond LNG dispatch*

**Author:** Jonas (Cargo Process Engineer, KN Energies SEPT; MSc Inovatyvių procesų inžinerija, Klaipėda University)
**Predecessor project:** LNG-PINN (composition-aware FSRU dispatch optimization, Independence FSRU, Klaipėda). This project ports its methodological skeleton — surrogate → economic optimization → controlled soft-vs-hard experiment → fabrication diagnostic — to a new physical domain.

---

## 1. Research question and contributions

**Central question:** Is the *soft-physics fabrication* phenomenon (soft-penalty PINN architectures generating spurious economic savings that vanish under hard physics-by-construction constraints) a general pathology of physics-informed ML in process engineering, or an artifact specific to the LNG dispatch domain?

**Target contributions (in priority order):**

1. **C1 — Fabrication generalization result.** A controlled soft-vs-hard experiment on tank evaporative-loss surrogates, directly mirroring LNG-PINN script 08. Either outcome is publishable: reproduction strengthens the original finding into a cross-domain claim; non-reproduction bounds its scope.
2. **C2 — A reusable fabrication diagnostic.** Formalize the LNG-PINN script-08 procedure as a domain-agnostic, executable test (`tankloss.diagnostics.fabrication`) that any process-engineering PINN study can run. Package and document it as a standalone module.
3. **C3 — A hard-constrained tank-loss surrogate + economic layer.** Physics-by-construction neural surrogate of AP-42 breathing/working losses, embedded in an emission-cost optimization (product loss value + regulatory cost), demonstrated on a realistic Baltic terminal case study.
4. **C4 (case study) — SEPT-grounded scenario.** Klaipėda meteorology, realistic product slate (EN 228 gasoline, EN 590 diesel, FAME/HVO blends, methanol), plausible tank farm configuration. Initially synthetic-but-realistic; upgradeable to real KN data if/when employer approval is obtained.

**Dual-use:** structure everything so the same codebase and experiments feed (a) a journal article and (b) a Klaipėda University master's thesis following Lithuanian conventions (tikslas, uždaviniai, ginamieji teiginiai, Lithuanian santrauka) — same pattern as the LNG-PINN thesis conversion.

---

## 2. Ground-truth physics model (the "CoolProp role")

The reference model that defines truth for surrogate training and against which fabrication is measured.

### 2.1 Tank loss equations — AP-42 Chapter 7.1
Implement as a clean, tested, vectorized Python package (`tankloss.physics`):

- **Fixed-roof tanks:** standing (breathing) losses `L_S` and working losses `L_W`:
  - Vapor space expansion factor `K_E` from diurnal temperature range and breather vent settings.
  - Vented vapor saturation factor `K_S`.
  - Stock vapor density from true vapor pressure (TVP) at liquid surface temperature.
  - Working loss turnover factor `K_N`, product factor `K_P`.
- **Internal/external floating roof tanks (IFR/EFR):** rim-seal losses, withdrawal (clingage) losses, deck-fitting losses, deck-seam losses. Parameterize seal types (mechanical shoe, liquid-mounted, vapor-mounted; primary vs primary+secondary).
- **Surface temperature model:** AP-42 liquid surface temperature correlations from ambient temperature, insolation, and tank paint solar absorptance.

### 2.2 Vapor pressure / product properties (`tankloss.properties`)
- TVP/RVP relationships for gasoline (ASTM correlation), Antoine equations for pure components (methanol — note its distinct hazard/emission profile), diesel/FAME low-volatility handling.
- Use `thermo`/`chemicals` libraries (or CoolProp where applicable) for pure-component vapor pressures; AP-42 default speciation profiles for petroleum mixtures.
- Composition-awareness hook: parameterize gasoline by RVP class and ethanol content (E5/E10) — this is the analog of LNG composition in the predecessor paper and the lever the fabrication experiment will probe.

### 2.3 Validation
- Unit tests against AP-42 worked examples (the chapter includes fully worked numerical examples — reproduce them to <1% deviation).
- Cross-check a subset against EPA TANKS-equivalent open implementations if available; otherwise AP-42 examples are sufficient ground truth.
- Property sanity tests: RVP→TVP monotonicity in temperature, Antoine bounds, etc.

---

## 3. Data pipeline (`tankloss.data`)

1. **Meteorology:** Open-Meteo historical API (or equivalent open source) for Klaipėda — hourly ambient temperature, daily min/max, solar radiation, wind. Cache locally as Parquet. `[TODO-JONAS: confirm preferred met data source; LHMT data if accessible]`
2. **Economic inputs:**
   - Product prices: Platts-style proxies are paywalled — use public proxy series (e.g., EIA/ARA spot benchmarks) with a clearly documented mapping. `[TODO-JONAS: pick proxy series]`
   - Regulatory cost: model VOC emission cost as a parameter sweep (€/t VOC) spanning plausible IED/national-fee values rather than committing to one number; document Lithuanian environmental pollution tax rates as the anchor. `[TODO-JONAS: verify current LT pollution tax rate for VOC]`
3. **Tank farm scenario:** YAML-defined synthetic terminal: N tanks with realistic geometry (diameter, height, paint, roof type, seal config), product assignments, throughput/turnover schedules. Defaults inspired by public photos/specs of Baltic liquid product terminals — **no KN internal data without written approval**.
4. **Scenario generator:** sample one year of hourly operation: fill levels, pumping events, product switches.

---

## 4. Surrogate models (`tankloss.models`)

Mirror LNG-PINN architecture choices for comparability:

- **S0 — Black-box MLP baseline** (no physics).
- **S1 — Soft-penalty PINN:** MLP with physics residual terms in the loss (mass balance of vapor space, non-negativity of losses, saturation bounds), weighted by λ; sweep λ.
- **S2 — Hard physics-by-construction:** architecture that cannot violate the constraints — e.g., output parameterizations guaranteeing non-negativity, exact mass-balance closure via constrained output layers, monotonicity enforced by construction (input-convex / monotone networks where the physics dictates monotonicity, e.g., losses increasing in TVP).
- Inputs: tank geometry features, product property features (RVP class, ethanol content, composition vector), meteorological features, operation features (turnovers, fill level). Output: hourly/daily evaporative loss per mechanism.
- Training: PyTorch, deterministic seeds, config-driven (Hydra or plain YAML), experiment tracking with simple CSV/JSON logs (no external services).

---

## 5. Optimization layer (`tankloss.optimize`)

The economic decision problem in which fabrication will or will not appear:

- **Decision variables:** product-to-tank assignment, fill scheduling / turnover timing, optional seal/paint retrofit selection (discrete), loading window timing relative to diurnal temperature.
- **Objective:** minimize (value of evaporated product + VOC regulatory cost), subject to throughput and storage constraints.
- **Composition lever:** allow the optimizer to exploit composition/RVP-class differences — exactly where LNG-PINN found soft models fabricating savings.
- Solve with the surrogate in the loop (gradient-based where smooth; CP-SAT/MILP wrapper for discrete retrofit decisions).
- **Truth evaluation:** every optimized plan is re-evaluated with the ground-truth AP-42 model. Fabrication metric = (claimed savings under surrogate) − (realized savings under truth), normalized.

---

## 6. The controlled experiment (port of LNG-PINN script 08)

`scripts/08_soft_vs_hard.py` — the heart of the paper:

1. Train S0/S1(λ-sweep)/S2 on identical data splits, seeds, and budgets.
2. Run the identical optimization problem with each surrogate.
3. Re-evaluate all plans under ground truth.
4. Report: fabricated-savings distribution per architecture, per λ; out-of-distribution behavior (e.g., RVP classes / temperatures outside the training range); constraint-violation statistics for soft models.
5. Statistical treatment: ≥10 seeds per configuration; report medians + IQR; paired comparisons.

**Hypothesis registered up front (write into `docs/HYPOTHESIS.md` before running):** soft-penalty surrogates will claim composition/scheduling savings that materially shrink under truth re-evaluation, with the gap growing OOD; hard-constrained surrogates' claimed savings will be approximately realized.

---

## 7. Repository structure

```
tankloss-pinn/
├── PLAN.md                  # this file
├── docs/
│   ├── HYPOTHESIS.md        # pre-registered expectations (write FIRST)
│   ├── DECISIONS.md         # running ADR log
│   └── DATA_GOVERNANCE.md   # explicit rule: no KN data without approval
├── src/tankloss/
│   ├── physics/             # AP-42 implementations + tests
│   ├── properties/          # TVP/RVP, Antoine, speciation
│   ├── data/                # met data, prices, scenario generator
│   ├── models/              # S0/S1/S2
│   ├── optimize/            # economic layer
│   └── diagnostics/         # fabrication diagnostic (C2, reusable)
├── scripts/                 # numbered pipeline, 01_… to 09_…
│   ├── 01_fetch_met_data.py
│   ├── 02_build_scenario.py
│   ├── 03_validate_physics.py      # AP-42 worked examples
│   ├── 04_generate_training_data.py
│   ├── 05_train_surrogates.py
│   ├── 06_optimize_baseline.py
│   ├── 07_ood_stress_test.py
│   ├── 08_soft_vs_hard.py          # the headline experiment
│   └── 09_make_paper_figures.py
├── configs/                 # YAML for tanks, products, training, sweeps
├── tests/
├── paper/                   # LaTeX article (journal target)
└── thesis/                  # LT-convention thesis skeleton (shared figures)
```

---

## 8. Paper / thesis skeleton (`paper/main.tex`)

1. Introduction — terminal VOC losses as economic + regulatory problem; the soft-physics fabrication finding from the predecessor paper; the generalization question.
2. Background — AP-42 loss mechanisms; PINN constraint taxonomies (soft penalty vs hard by-construction); related surrogate-optimization gap literature.
3. Methods — ground-truth model, surrogates, optimization problem, fabrication diagnostic (C2 formalized with pseudocode).
4. Case study — Klaipėda-meteorology synthetic terminal; scenario design.
5. Results — script 08 outputs; OOD analysis; retrofit-decision sensitivity.
6. Discussion — why fabrication does/doesn't transfer; mechanistic explanation; implications for industrial deployment of PINN surrogates.
7. Limitations — synthetic tank farm pending data approval; AP-42 as truth proxy (model-vs-model caveat, inherited from LNG-PINN — address it head-on).

Thesis variant adds: tikslas/uždaviniai/ginamieji teiginiai front matter, expanded Chapter 2 theory, Lithuanian santrauka. Reuse the LNG-PINN thesis conversion patterns.

---

## 9. Milestones

| # | Milestone | Definition of done |
|---|-----------|--------------------|
| M1 | Physics core validated | AP-42 worked examples reproduced in tests; CI green |
| M2 | Data + scenario pipeline | One year of hourly Klaipėda scenario data generated reproducibly |
| M3 | Surrogates trained | S0/S1/S2 meet accuracy floor on held-out data (define: R² > 0.99 in-distribution vs truth) |
| M4 | Optimization layer | Baseline plan beats naive schedule under truth re-evaluation |
| M5 | **Script 08 results** | Fabrication metrics with ≥10 seeds; figures drafted |
| M6 | Paper draft | All sections drafted; no `[FILL]` placeholders except data-approval-gated ones |
| M7 | Thesis skeleton | LT-convention .tex compiling with shared figures |

---

## 10. Rules for Claude Code

- **Write `docs/HYPOTHESIS.md` before any model training.** The pre-registration is part of the paper's credibility.
- Test-driven for `physics/` and `properties/`: AP-42 worked examples are the acceptance tests.
- Every script idempotent, config-driven, seeded; outputs to `outputs/<script>/<run-id>/`.
- No external experiment-tracking services; plain files only.
- **Never** hardcode or fetch KN Energies internal data. `DATA_GOVERNANCE.md` governs; real-data integration is a separate, approval-gated phase.
- Prefer small, reviewable commits per milestone; keep a running `docs/DECISIONS.md`.
- Mark anything requiring Jonas's input as `[TODO-JONAS: …]` and collect them in a single tracked list.
- Python 3.11+, PyTorch, numpy/pandas/scipy, `thermo`/`chemicals`, matplotlib (paper-quality figures, no seaborn), pytest. Mac-compatible (MPS or CPU; no CUDA assumptions).

---

## 11. Open items for Jonas

- `[TODO-JONAS]` Raise publication/data-use question with KN manager (frame as terminal visibility); until then everything stays synthetic.
- `[TODO-JONAS]` Confirm thesis supervisor interest (Prof. Paulauskienė — direct overlap with her VOC-at-KN research).
- `[TODO-JONAS]` Choose journal target (candidates: Computers & Chemical Engineering, Journal of Loss Prevention, Energy & AI) — affects length/format.
- `[TODO-JONAS]` Decide whether C2 diagnostic gets released as a small standalone open-source package (citability boost).
- `[TODO-JONAS]` Met data source preference and VOC pollution-tax anchor value.
