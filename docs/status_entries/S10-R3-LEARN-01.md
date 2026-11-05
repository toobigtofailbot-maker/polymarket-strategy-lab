# S10-R3-LEARN-01

RUNTIME/Risk3/M, exact 8 paths, branch `codex/s10-r3-learn-01` from clean synchronized main `25562380a643a45a4f97c3603805c30a9e655394`.
- PR #270 is merged: head `20617f054c981c8e4f3e64e3ad625b2c62d6b22f`, merge `25562380a643a45a4f97c3603805c30a9e655394`.
- PR #268 is open and untouched at `9a5a00cd61effa4e28b82f830427440b23aba86c`. Nothing is stacked on it.
- Karl authorized implementation conditional on native readiness. Merge stays Karl-only.

## Readiness

The package prompt SHA256 is `91bfb8b5857ac1660766eb64c3c43c30fbfd0f3a44dcd8f6edee2fdf6e7a76c2` and the spec SHA256 is `4922bfa9b085dc95c096a967e6ed0f46902c767c1dfc523f1b1774207eac22f7`.

I ran the native gate on those exact extracted bytes on clean main, before branch creation. It returned:
- exit 0, `IMPLEMENTATION_READY`, is_ready=true;
- RUNTIME/DETERMINISTIC, scope 8, error_codes empty.

No spec repair was needed. The committed prompt and spec are byte-identical to the gated files.

## Implementation

One finite offline operator, `tools/alpha/run_learning_feedback.py` (`run`/`verify`), over `src/data_layer/analytical_research/learning_feedback.py`. The contract is in `docs/outcome_learning_feedback_contract.md`.

- **Upstream:** the merged `run_forecast_evaluation.verify` runs on the caller's FORECAST-01 scratch, then again on the frozen copy. The forecast code identity must equal the current one.
- **Join:** later outcome records (`s10-r3-learn01-outcomes-v1`) bind to the frozen selected case's market, event group, rule hash, Yes label and binary labels, with resolved, known and first-seen clocks.
  - Each selected case ends in exactly one state: SCORABLE, MISSING_OUTCOME, DISPUTED, LATE_AFTER_CUTOFF or EXCLUDED.
  - Post-cutoff revisions go only into a correction ledger.
  - A label already frozen in the forecast inputs must match.
- **Scoring:** the original frozen `p_yes` is scored unchanged with native `forecast_evaluation.score_one`, with per-method offered, eligible, missing, disputed, late, excluded, abstained, unavailable and scored counts. The primary paired set and the Wang subset are hash-bound. The original FORECAST-01 scoring is kept as a hashed historical snapshot.
- **Diagnostics:** predeclared calibration bins, per-category and per-horizon coverage, gap, and Brier-difference mean and standard error, with minimum-n insufficiency and `significance_claim: false`.
- **Proposals:** one advisory proposal per category from a closed reason set. Ids are content-addressed with no self-hash. Alpha candidate and episode links are read-only, or `ALPHA_LINK_UNVERIFIED`.
- **Provenance:** synthetic labels are `SYNTHETIC_LABEL_NOT_SETTLEMENT` and imported labels are `CALLER_IMPORTED_ORIGIN_UNAUTHENTICATED`. `settlement_origin_verified` is always false. A claimed source hash is refused as `SOURCE_CLAIM_UNVALIDATED` (D002).
- **Authority:** RESEARCH_ONLY, DIAGNOSTIC_ONLY and NO_CANONICAL_WRITE. Zero network is enforced by the shared socket guard. There are no Alpha, PIT or WP170 writes and no dependencies.

## Outcome (real operator run, SANITIZED_SYNTHETIC)

The run used the committed FORECAST-01 fixture: 37 offered, 33 selected. The packet held 33 records: 32 cases, plus one post-cutoff correction. One case was left without a record and one was made late.

| Measure | Value |
|---|---|
| Selected | 33 |
| Scorable | 31 |
| Missing | 1 |
| Late | 1 |
| Disputed | 0 |
| Excluded | 0 |
| Primary paired | 27 |
| Scorable event groups | 31 (disjoint) |
| Proposals | 8 |

| Paired measure (27 cases) | Independent prior | Base rate | Market | Wang |
|---|---|---|---|---|
| Brier | 0.236583522298 | 0.234173907850 | 0.124574074074 | 0.140952561087 |
| Log loss | 0.666164703658 | 0.661205730636 | 0.409504918604 | 0.429180588643 |

- `lift_status` is `DIAGNOSTIC_ONLY_NOT_OOS_LIFT_NOT_VALUE` and the value status is `NO_REAL_VALUE_VERIFIED` (D001).
- All 36 capability ids are unchanged, with 0 status changes. The six provider lanes are unchanged and R3-10-WANG stays market-price-derived.

## Validation state

IMPLEMENTED_LOCAL. The PR body carries the validated commit, full-suite, hosted CI and evidence mode.
