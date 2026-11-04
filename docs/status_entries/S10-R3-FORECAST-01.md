# S10-R3-FORECAST-01

RUNTIME/Risk3/M, exact 8 paths, branch `codex/s10-r3-forecast-01` from clean synchronized main `da5031c6a4c79f63dd0968df3cceb1b12d0de72f`.
- PR #269 is merged, with head `1a0e4cf88cd3ece75fa485ba75e3e11b01fb86ec` in ancestry.
- PR #268 is open and untouched at `9a5a00cd61effa4e28b82f830427440b23aba86c`. Nothing is stacked on it.
- Karl authorized implementation conditional on native readiness.

## Readiness

The package's prompt SHA256 is `641dbae7a931da1add54541bd376c959f8a692fbfa6624a75701587220f9cb89` and its spec SHA256 is `5476abaeea175eb785ec609ab04f61e121fae1815b05320c27f8b27162463473`.

The pre-branch native gate on the extracted bytes returned exit 1, `READINESS_PACKAGE_GUARD_INVALID`. The spec's `failure_precedence` was not the fixed native WP159 list, and two state-transition categories were outside the allowed set.

I repaired only the spec, before branching. Scope and authority are identical, and the change follows the merged S10-R3-SRC-01 spec. The WP runtime refusal precedence moved into the contract doc. The repaired spec is `2c8f7f8545fc2ace534bb96a33a29cbe9119172e6eb5013de4604de5638ec882`.

The rerun returned:
- exit 0, `IMPLEMENTATION_READY`, is_ready=true;
- RUNTIME/DETERMINISTIC, scope 8, error_codes empty.

The committed prompt and spec are byte-identical to the gated files.

## Implementation

One finite offline operator, `tools/alpha/run_forecast_evaluation.py` (`run`/`verify`), over `src/data_layer/analytical_research/forecast_evaluation.py`. The contract is in `docs/forecast_evaluation_contract.md`.

- **Grounding:** the caller's S10-R3-SRC-01 scratch is cold-verified with the native `run_source_grounding.verify`, then the frozen copy is verified again.
- **Binding:** targets bind to the native universe market, question hash, BOUND rule hash, native event group, admitted SRC-01 source ids and the yes/no orientation.
- **Independent forecast:** a training-only beta(1,1) category × horizon prior, or ABSTAIN with numerator and denominator.
- **Wang comparator:** a separate probit-distortion comparator, always `MARKET_PRICE_DERIVED`.
- **Sampling:** SHA-256 seeded largest-remainder sampling over category × horizon × price band, one market per event, with no labels read.
- **Scoring:** Brier, ε=1e-12 clipped log loss and the Metaculus baseline score, computed on the primary paired set (independent, market and base rate). Wang is reported on its own paired subset.
- **WP170:** checked read-only, or the run is marked unbound. Scores are always `DIAGNOSTIC_ONLY`.
- **Upstream code:** all 9 pinned upstream files exist and their licenses were checked. They are adapted as algorithm or concept only; no code was copied or installed.

## Outcome

The frozen inline SANITIZED_SYNTHETIC corpus has SHA-256 `2b8be21612572111e5458a30923fe9a35133d44746a1e9b00e3d8ff8ec161238`.

| Paired measure (29 cases) | Independent prior | Base rate | Market | Wang |
|---|---|---|---|---|
| Brier | 0.237860661506 | 0.235932591350 | 0.133065517241 | 0.151590323677 |
| Log loss | 0.668736574038 | 0.664769554392 | 0.428316057643 | 0.453883214680 |

- **Cohort:** offered 37, eligible 36, selected 33.
- **Scoring:** 32 scorable.
- **Result:** NO_LIFT, with `NO_REAL_VALUE_VERIFIED` (D001).
- **Parity:** R3-18, R3-20 and R3-22 are `PARITY_OPEN_PENDING_KARL_ACCEPTANCE`.
- **Unchanged:** the other 27 of 36 IDs, the six provider lanes and Lane B.
- **Successor:** `S10-R3-LEARN-01` remains mandatory.

## Validation state

IMPLEMENTED_LOCAL / LOCAL_VALIDATION_COMPLETE. The validated implementation commit is `9761be12cf3e7c7cbcdd96f90aa47afa6c2a8f34`; later commits change only this fragment. Current head, exact-head hosted checks, evidence mode and the Ready decision belong in the PR body.

**Authoritative full suite on 9761be1:** `python -B -m pytest -q -p no:cacheprovider --basetemp /tmp/full -ra` gave 14652 passed, 15 skipped, 125 warnings in 1476.47s, exit 0. It ran in the existing pinned image `s10-canary-siwc-validation:20261024`:
- `--network none --read-only`;
- tmpfs `/tmp` and a uid-1000 0700 tmpfs HOME;
- a disposable LF clone;
- `safe.directory=/repo` via `GIT_CONFIG_*` env;
- no pull or install.

**Retained earlier attempt, not counted as a pass:** on d7bce37 without `safe.directory`, 34 git-backed scope tests failed. Git refused the bind-mounted clone ("dubious ownership"), so this was an environment fault and no code change followed. 14617 tests passed in that run.

**Other checks on 9761be1:**

| Check | Result |
|---|---|
| Focused `tests/tools/alpha/test_forecast_evaluation.py` | 8 passed |
| Focused + adjacent (SRC-01, WP170 registry and prereg, Alpha discovery, qualification, calibration-metric, architecture and both official-client boundary modules) | 418 passed |
| Native readiness `--check-diff --base da5031c6a4c79f63dd0968df3cceb1b12d0de72f --head HEAD` | exit 0, IMPLEMENTATION_READY, scope 8 |
| Generated-artifact guard | passed |
| `git diff --check` | clean |

- **Red-green:** the R001–R008 module fails to import against main `da5031c`.
- **Not run locally:** gitleaks is not installed locally; the hosted gitleaks gate in exact-head CI is the secret scan. Semgrep registry rules need network, so Semgrep was not run. pip-audit is not applicable because no dependency changed.

## Review and repairs

One independent implementation review, in a separate reviewer context, of d7bce37 returned PASS_WITH_NOTES with no HIGH findings.

**MEDIUM findings:**
- An outcome that resolved before the decision was still scored.
- SRC-01 sources were not bound to targets.
- A Wang abstention emptied the paired set.

**LOW findings:**
- The event-group dedup step was missing from the inclusion probability.
- Non-canonical prior decimals were accepted.
- A `MISSING` category sentinel could collide with history.
- An untrusted receipt id was echoed in verify output.
- Doc wording on error counts was misleading.

All were fixed with negative tests in 9761be1, plus a Wang `lambda_at_bound` flag. History clocks remain caller-asserted; the receipt labels them and the gap is deferred as D004.

## Skills

- **Ponytail Lite (invoked first):** reuse of SRC-01 verify, the socket guard, strict JSON and `load_corpus`; stdlib only; external and multi-producer probabilities cut, so unknown keys are refused.
- **hermes-alpha-reuse-check:** no existing reusable research scorer.
- **runtime-authority-boundary-review:** BOUNDARY_INTACT.
- **financial-invariant-check:** no CRITICAL, HIGH or MEDIUM findings; λ-at-bound was LOW and is now flagged.
- **verification-before-completion:** applied, with fresh outputs before every claim.
- **Not run:**
  - spec-to-code-compliance, because it writes into the repository; the independent reviewer checked R001–R008 instead.
  - wp-predraft-inspector and wp-one-shot-review, not applicable because the package was already drafted.

## Negative matrix and deferred issues

A negative matrix is required: YES. The full matrix is enumerated in the PR body and the R007 test. Not applicable: spelling-variant regexes, because forbidden keys are matched structurally.

Deferred items D001–D004 are recorded in `docs/deferred_items_log.md`.

PR: see GitHub PR metadata and the PR body. This fragment is stable and non-self-referential.

Operations not performed:
- no product, provider, model, market, account or credential operation;
- no LLM or Hermes;
- no scheduler;
- no canonical store write;
- no paper or live activation.

Capital/orders USD0/0; LIVE DISABLED.
