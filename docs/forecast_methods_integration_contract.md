# Forecast Methods Integration Contract (S10-CAP-B1-METHODS-01)

B1-B. One offline vertical that runs pinned upstream forecasting, sampling and benchmark-metric methods over one native
forecast cohort, and feeds the results to the native scorers. It is RESEARCH_ONLY / DIAGNOSTIC_ONLY. It has no
provider, network, credential, strategy, paper, order or live authority.

## Flow

1. `tools/alpha/run_forecast_methods_integration.py run --forecast-scratch DIR --methods METHODS.json --scratch-dir DIR`.
2. The tool cold-verifies the caller's `forecast_evaluation` scratch with `run_forecast_evaluation.verify`. That step
   also cold-verifies SRC-01 and the frozen WP170 registry. The tool then copies the scratch and freezes the methods file.
3. It cold-verifies the frozen copy again, then calls `forecast_methods_integration.build_methods_core`:
   - **Method phase** (label-free): the input is the native event-deduplicated sampling frame from the verified receipt.
     The ForecastBench sampler port runs on it, and the selected ids are read against the native WP170 split. The
     upstream-objective Wang port is fitted on `forecast_evaluation.evaluate_history` training rows, pre-decision only.
     Target outcomes are never an input to this phase.
   - **Scoring phase** uses the native outcome gate and scorers.
     - `forecast_evaluation.score_diagnostic_candidate` scores the candidate with `score_one`, under the same
       `resolve_outcome` gate as the cohort.
     - `learning_feedback.score_frozen` must agree with the forecast receipt's paired count.
     - `learning_feedback._uncertainty` and `learning_feedback.calibration` provide the uncertainty and calibration
       diagnostics.
4. The tool writes one write-once receipt (`fcstmeth:sha256:`, schema `s10-cap-b1-methods01-receipt-v1`). `verify`
   recomputes it from the frozen copies; a partial scratch refuses and never replays.

Only a v2 forecast receipt (with WP170 membership) is a supported source. Sealed legacy v2 receipts work too. A v1
receipt refuses with `FORECAST_RECEIPT_SCHEMA_UNSUPPORTED`.

The methods file (`s10-cap-b1-methods01-methods-v1`) has a closed key set:
- `forecast_receipt_id` must equal the verified receipt.
- `sampler` holds the integer seed (0 to 2^32-1), `n_target`, `forecast_datetime` and an explicit native-to-ForecastBench
  `category_map`. `forecast_datetime` must be no earlier than the grounding cutoff and no later than any frame decision.
- `wang` holds `lambda_tolerance`.
- `provider_methods` must be `[]`.

## Method register (nine touched IDs)

Each ID's repository, commit, file and license are read from the unchanged native `forecast_evaluation.SOURCE_PINS`.
Those pins match the immutable roadmap registers `03_FULL_36_CAPABILITY_ADOPTION_MATRIX.csv` and
`09_SOURCE_TO_CLAIM_REGISTER.csv`. `check_register` refuses three things:
- a changed pin, file or license;
- an `ENG_OFFLINE` disposition without an executed, licensed callable and a native consumer;
- a non-accepted ID without a cause.

| ID | Pinned callable | Method class | Disposition | Cause / evidence |
|---|---|---|---|---|
| R3-01 | forecasting-tools@a54dd64 `ForecastBot._run_individual_question/_aggregate_predictions` | NOT_IMPLEMENTED_ZERO_FORECASTS | BLOCKED | Dependency closure (litellm, openai, asknews, tiktoken …) is not installed and installs are not authorized; it needs a real provider; model cost UNKNOWN |
| R3-06 | prediction-market-agent-tooling@817117d `Benchmarker.calculate_squared_errors` (LGPL-3.0) | SOURCE_PORT_UPSTREAM_NOT_EXECUTED | BLOCKED | Import needs sklearn, tqdm and web3 market models; `run_agents` needs network. Formula parity measured (2 × Brier; upstream `_compute_mse` returns a SUM) |
| R3-10 | prediction-market-pricing@04b916c `external_benchmark` | NOT_IMPLEMENTED_ZERO_FORECASTS | BLOCKED | Needs an `ODDS_API_KEY` credential, network and NBA data |
| R3-10-WANG | same pin, `hierarchical_wang_mle.estimate_mle` (intercept-only) | SOURCE_PORT_UPSTREAM_NOT_EXECUTED | BLOCKED | The real callable needs scipy (not installed). The port parity against native `fit_wang` is run evidence only |
| R3-12 | forecastbench@e8d3c94 `thin_pool_by_category` (MIT) | UPSTREAM_CALLABLE_EXECUTED_LOCALLY_GOLDEN_PINNED | ENG_OFFLINE | Exact parity with the real callable; consumed by a native TemporalSplitManifest read |
| R3-12-SAMPLER | same pin, `stratified_sample_questions` | UPSTREAM_CALLABLE_EXECUTED_LOCALLY_GOLDEN_PINNED | ENG_OFFLINE | As R3-12 |
| R3-18 | metac-bot-template@bcbd016 `integrations/main_lightningrod_eval` | NOT_IMPLEMENTED_ZERO_FORECASTS | OPEN_OWNER_RIGHTS | No license is declared. It depends on forecasting-tools, lightningrod-ai and providers, and requires Python < 3.14 |
| R3-20 | metaculus@bfae5fe `evaluate_forecasts_baseline_spot_forecast` binary (BSD-2) | UPSTREAM_CALLABLE_EXECUTED_LOCALLY_UNUSED_IMPORTS_STUBBED_GOLDEN_PINNED | ENG_OFFLINE | The pinned function body was executed. The unused Django and scipy imports were stubbed, and the binary path never touches them. Native `score_one` baseline equals it, except at the unclipped 0/1 boundary |
| R3-22 | forecastbench-sim@27776fc `CachedForecast` excess_brier (GPL-3.0) | UPSTREAM_CALLABLE_EXECUTED_LOCALLY_GOLDEN_PINNED | ENG_OFFLINE | Executed. The reject contract (NaN, out-of-range, bool) is reproduced by an independent formula, and the value equals native Brier |

`ENG_OFFLINE` means engineering parity offline. It is not `VALUE_VERIFIED`. The other 27 of the 36 program IDs, the
roadmap archive, the six provider lanes, Lane B and PR #268 are unchanged.

A8 here is diagnostics only; feedback routing stays with B5. There is no A3 real-model claim and no A4 genuine-claim
change. `forecast_evaluation`'s own v2 `adoption` block is unchanged, so v2 cores stay identical. The B1-B dispositions
live only in the new receipt and in this contract.

## Upstream execution evidence (local, outside the repository)

- **Checkouts.** Shallow fetch of the exact commit for each of the seven repositories into a scratch directory outside
  the repository. This was read-only software inspection: no install, no copy and no product network.
- **Environment.** Python 3.14.3, numpy 2.4.2 and pandas 3.0.1 (already installed locally; nothing installed). scipy,
  sklearn, litellm and forecasting-tools are absent.
- **ForecastBench.** The real `thin_pool_by_category`, `add_bin_columns`, `create_composite_bins`,
  `calculate_bin_weights` and `stratified_sample_questions` were compared with the stdlib port on 400 random pools (seed,
  n and thinning varied, including error cases): 0 mismatches.
  - On the native synthetic frame (seed 20261123, n 12) both give the selection pinned as `GOLDEN_FB_SELECTION` in the
    R003 test.
  - The stdlib port reproduces numpy's legacy `RandomState(int)`: the same MT19937 `init_genrand` seeding, `random_sample`
    as genrand_res53, `permutation` by masked rejection `random_interval`, `choice(replace=False)` as the permutation
    prefix, and the pandas `DataFrame.sample` row order.
- **Metaculus `score_math` and forecastbench-sim `CachedForecast`.** These were executed on a 9-probability grid × {0, 1};
  the goldens are in the R001 test.
- **Live re-run.** `POLYMARKET_UPSTREAM_ROOT=<dir of checkouts>` re-runs the live upstream comparisons inside R001 and
  R003. CI never imports upstream code.
- **Pinned file SHA-256s.**
  - forecastbench `_sampling.py`: `7d9cc720…`
  - forecastbench `_binning.py`: `4a968fe7…`
  - metaculus `score_math.py`: `4fab7094…`
  - fbsim `adapters.py`: `dc205c8e…`
  - pricing `hierarchical_wang_mle.py`: `41dfa63c…`
  - pmat `benchmark.py`: `aeb54b2b…`
  - forecasting-tools `forecast_bot.py`: `1cdb1bf2…`
  - metac-bot-template `main_lightningrod_eval.py`: `c8983593…`
  - pricing `external_benchmark.py`: `8629ddc8…`

## Wang parity (R3-10-WANG)

The upstream objective is `Pr(y=1) = Phi(Phi^-1(p) - lambda)`. Its parameters:
- price filter is the open interval (0.05, 0.95);
- p is clipped at 1e-6 and Phi at 1e-12;
- lambda bounds are (-2, 2);
- upstream uses scipy L-BFGS-B from 0.176.

The port uses 200 golden-section iterations and checks the upstream analytic gradient
`sum(y phi/Phi - (1-y) phi/(1-Phi))`. Convergence means |grad|/n ≤ 1e-5, or a bound is active.

Native `fit_wang` differs in two ways: a closed price interval [0.05, 0.95] and bounds [-1, 1]. Per case, the result is:
- `MATCH`: the training ids are identical, the native fit is not at its bound, and |Δlambda| ≤ the declared tolerance;
- `PARITY_FAILED`, with reasons `TRAINING_SET_DIFFERS_OPEN_VS_CLOSED_PRICE_RANGE`, `NATIVE_LAMBDA_AT_NARROWER_BOUND` or
  `LAMBDA_OUTSIDE_TOLERANCE`;
- abstention below the native `wang_min_training_n`.

The two estimators are never equated. The candidate `wang_upstream_objective_port_v1` is MARKET_PRICE_DERIVED.

## Synthetic run (frozen S10-R3-FORECAST-01 world, bound WP170 registry)

These numbers come from a-priori parameters, with no tuning:
- **Sampler.** Frame 35. Category thinning dropped 9 (3 not in the upstream taxonomy, 6 thinned); pool 26; zero-weight or
  unknown bin 4; weighted 22; requested and selected 12.
- **Upstream vs native selection.** Overlap with the native 33 selected is 10, upstream-only 2. The two selections are
  not equated.
- **WP170.** All 12 upstream-selected cases are MAPPED to OUT_OF_SAMPLE in the native split; nothing is released.
- **Wang.** 33/33 MATCH. The history prices are 0.2–0.8, so both training sets are identical.
- **Scoring.** 33 selected, 32 scorable, 31 with a candidate forecast, 29 paired with every native method.
  - Candidate paired Brier 0.151590323677 and log loss 0.453883214680, equal to native Wang at 12 dp.
  - Candidate minus market Brier: mean 0.018524806435, SE 0.014022262030.
  - `lift_status` = `INCONCLUSIVE_SYNTHETIC_LABELS_NOT_VALUE`.
- **Metric parity.** R3-20, R3-22 and R3-06 each give 29/29 MATCH on the paired cases.

A non-synthetic cohort below 30 paired cases is `INCONCLUSIVE_INSUFFICIENT_PAIRED`. Otherwise the result is `NO_LIFT`
unless mean + 2·SE < 0, which gives `LOCAL_OBSERVATION_UNREVIEWED_NOT_VALUE`. No path emits lift or value.

## Legacy compatibility

- `forecast_evaluation.py` gains only `score_diagnostic_candidate` (never called by `build_evaluation_core`) and the
  pinned `LEGACY_V2_CODE_IDENTITY`. That identity is `code_identity()` of the four identity files at merged main
  `0d5ddfa`, unchanged since PR #280.
- `run_forecast_evaluation.verify` replays a v2 receipt that claims that pinned identity against that identity. This
  works because v2 core logic is unchanged; the test proves the legacy and current cores are equal apart from
  `code_identity`.
- v1 replays as before. Default run/verify, WP170 membership and B1-A `bind_forecast` output are unchanged.
- Known limit: `run_learning_feedback.code_identity` binds `run_forecast_evaluation.code_identity()` transitively, by
  design. Learning receipts sealed before this change therefore recompute under the new identity, as after every prior
  forecast-code change (for example PR #280). `run_learning_feedback.py` is outside this package (D002).
