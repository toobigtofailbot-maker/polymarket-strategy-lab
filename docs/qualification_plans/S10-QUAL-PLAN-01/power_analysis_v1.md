# S10-QUAL-PLAN-01 Power Analysis v1 (frozen before prospective OOS)

Status: frozen analytic commitment of `S10-QUAL-PLAN-01`; bound into
`docs/qualification_plans/S10-QUAL-PLAN-01/weather_plan_v1.json` by the SHA-256 of this file's LF-normalized UTF-8
bytes (`sample_power_plan.power_analysis_doc_sha256_lf`). Reference id: `s10-qual-plan-01.power-analysis-v1`.

No corpus score, outcome, prevalence, feature distribution or effect estimate was used to set any value here. No
data was accessed. This document computes no predictive score and grants no qualification, preregistration, OOS,
strategy, paper, execution or live authority. WP170 remains the sole preregistration/OOS authority.

The two questions below are deliberately separate:

1. **Development sufficiency** (section 1): are there enough historical FORMATION rows to estimate the frozen
   B1/B2 logistic models precisely? This is a property of the historical DATA-02 FORMATION role only.
2. **OOS comparison power** (section 2): are there enough genuinely prospective target dates to detect a frozen
   planning effect in the fixed-sequence Brier comparisons? This is a property of the prospective DATA-03 OOS
   membership only.

A development floor never substitutes for OOS power and vice versa.

## 1. Development sufficiency (Riley-style, FORMATION only)

Method: Riley et al. (2020, BMJ 368:m441) minimum sample size for developing a binary-outcome prediction model.
EPV10 (events per variable) is **not** used.

Frozen criterion (iii), precise estimation of the overall outcome risk within an absolute margin `delta`:

```text
n = ceil((z / delta)^2 * phi * (1 - phi))
z = 1.96, delta = 0.05, phi = 0.5 (maximum-variance anticipated outcome proportion; no prevalence is used)
n = ceil(1536.64 * 0.25) = ceil(384.16) = 385 structurally eligible FORMATION rows
```

Frozen FORMATION hard stop: `>= 385` structurally eligible FORMATION rows **and** `>= 20` effective FORMATION target
dates (a target date with at least one non-purged FORMATION row). Otherwise the future S10-QUAL-REAL-01 terminal is
`QUAL_FORMATION_INSUFFICIENT`: no fit, no score, no tuning, no re-allocation.

Criteria (i) and (ii) need an anticipated Cox-Snell `R2_cs`, which cannot be set without outcome-dependent data.
They are **diagnostic context only** and do not change the frozen floor. `P` is the number of candidate predictor
parameters (B1 `P = 2`, B2 `P = 3`); target global shrinkage `S = 0.9`; `max R2_cs = 0.75` at `phi = 0.5`.

Criterion (i), `n = P / ((S - 1) * ln(1 - R2_cs / S))`:

| anticipated R2_cs | B1 (P = 2) | B2 (P = 3) |
| --- | --- | --- |
| 0.02 | 890 | 1335 |
| 0.05 | 350 | 525 |
| 0.07 | 248 | 371 |
| 0.10 | 170 | 255 |
| 0.15 | 110 | 165 |
| 0.20 | 80 | 120 |

Criterion (ii), optimism in Nagelkerke R2 at most 0.05, `S = R2_cs / (R2_cs + 0.05 * max R2_cs)`, same formula:

| anticipated R2_cs | B1 (P = 2) | B2 (P = 3) |
| --- | --- | --- |
| 0.02 | 52 | 78 |
| 0.05 | 51 | 77 |
| 0.10 | 50 | 75 |
| 0.20 | 47 | 71 |

Reading: the frozen 385-row floor also satisfies criterion (i) for B2 whenever the anticipated `R2_cs >= 0.07`
and criterion (ii) at every tabulated value. For weaker anticipated signals criterion (i) would ask for more rows;
the frozen Firth/Jeffreys-prior estimation (no tunable penalty) is the only shrinkage-related safeguard and no
post-hoc recalibration is permitted. This limitation is recorded, not tuned away.

Other development floors (frozen in the plan): SELECTION = the last 7 eligible historical target dates with
`>= 5` effective SELECTION dates after the WP170 purge/embargo; `>= 100` rows in every role
(`min_samples_per_role = 100`).

## 2. Prospective OOS comparison power (target-date clustered)

Statistical unit: `target_date`. Per-date loss differential `d_t` = mean row-level Brier differential
(candidate minus comparator) over all eligible rows, cities and checkpoints of date `t`. Each comparison is a
one-sided paired loss-difference test on `d_1..d_n` in chronological order (plan `test_family_plan`).

Frozen planning values (none derived from any corpus score or effect estimate):

```text
target power           = 0.8
one-sided alpha        = 0.025     (each fixed-sequence comparison; FWER 0.025)
planning MDE           dz = 0.5    (standardized mean of d_t)
lag-1 autocorrelation  rho1 = 0.25 (planning assumption)
VIF                    = 1 + 2*rho1 = 1.5
```

Derivation (normal approximation with the Guenther small-sample t correction, inflated for serial dependence):

```text
z_{1-alpha} = 1.959964,  z_{power} = 0.841621
((z_{1-alpha} + z_{power}) / dz)^2          = 31.3955
+ z_{1-alpha}^2 / 2                          = 33.3162  (independent-date equivalent)
* VIF 1.5                                    = 49.9744
n = ceil(49.9744) = 50 effective prospective target dates
```

Frozen prospective OOS target: **50** effective target dates (the chronologically first 50 eligible dates
`D1..D50` after `oos_start = 2026-10-15T00:00:00Z`, considered through the cap `2027-02-12T00:00:00Z`). Fewer than
50 effective dates by the cap is `QUAL_OOS_INSUFFICIENT_AT_CAP` (no extension, no REAL-01, no score).

Sensitivity of the required number of dates (same formula):

| dz \ rho1 | 0.00 | 0.25 | 0.40 |
| --- | --- | --- | --- |
| 0.4 | 51 | 77 | 92 |
| 0.5 | 34 | 50 | 60 |
| 0.6 | 24 | 36 | 43 |

Approximate power at the frozen 50 dates (`n_eff = 50 / VIF`, power = `Phi(dz * sqrt(n_eff - z_{1-alpha}^2 / 2) - z_{1-alpha})`):

| dz \ rho1 | 0.00 | 0.25 | 0.40 |
| --- | --- | --- | --- |
| 0.4 | 0.792 | 0.611 | 0.530 |
| 0.5 | 0.934 | 0.800 | 0.720 |
| 0.6 | 0.986 | 0.920 | 0.862 |

The sensitivity tables are fixed documentation; none of their cells may be selected after data is seen. The
frozen test statistic (Diebold-Mariano with a Newey-West Bartlett lag-1 long-run variance and a Student t
critical value with 49 degrees of freedom) is defined in the plan and is not re-chosen from this table.

## 3. Boundary

This document freezes planning arithmetic only. It creates no `PreregisteredExperiment`, lifecycle/OOS-release
record, `QualificationCandidate` or qualification-gate receipt, reads no DATA-02/DATA-03 row and makes no
network call.
