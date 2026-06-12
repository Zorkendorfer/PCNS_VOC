# Pre-Registered Hypothesis

This file is written before any surrogate model training or optimization experiments.

## Primary Hypothesis

Soft-penalty physics-informed surrogates will claim composition or scheduling savings that shrink materially when optimized plans are re-evaluated with the hard AP-42 truth model.

The gap is expected to grow under out-of-distribution operating conditions, especially higher vapor-pressure products and warmer meteorological regimes.

## Comparator

Hard physics-by-construction surrogates are expected to produce claimed savings that are approximately realized under AP-42 truth re-evaluation, because their outputs cannot violate the core loss constraints by construction.

## Diagnostic

For each surrogate architecture, the fabrication metric is:

```text
fabricated_savings = claimed_savings_under_surrogate - realized_savings_under_truth
```

The headline result will report fabricated-savings distributions by architecture and soft-penalty weight, with paired comparisons across common random seeds and identical optimization problems.

## Interpretation Rules

A reproduction of the LNG-PINN fabrication pattern supports the claim that soft-physics fabrication is a cross-domain process-engineering pathology.

A non-reproduction is also informative: it bounds the pathology and suggests the LNG result depended on domain-specific structure, optimization leverage, or surrogate design choices.
