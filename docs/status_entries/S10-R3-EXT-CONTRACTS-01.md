# S10-R3-EXT-CONTRACTS-01

RUNTIME/DETERMINISTIC, exact 8 paths, branch `codex/s10-r3-ext-contracts-01` from clean synchronized main `9ea25d87d1c8ce0bafb04abaf645546510e8eedd`.
- PR #273 is merged: head `726ebf37ecdb51eeb3bf3c3cdc21db77dd9de3a2`, merge `9ea25d87d1c8ce0bafb04abaf645546510e8eedd`.
- PR #268 is open and untouched at `9a5a00cd61effa4e28b82f830427440b23aba86c`. Nothing is stacked on it and its expired fee policy is not used.
- Karl authorized bounded offline implementation within the package scope, conditional on native readiness. No network, provider, credential, Hermes, scheduler, paper, execution, live, capital or merge authority; merge stays Karl-only.

## Readiness

Package `SIDE24_S10_R3_EXT_CONTRACTS_01_CC_EXECUTION_PACKAGE.zip` (sha256 `98588dfc71ae7c7c86e29f0d9590a0f5d6904c875354c9a6bdd4b0f21ec9ce58`), `SHA256SUMS.txt` verified for all 6 files. Prompt SHA256 `8359575ef4ebe4998abf85fbd0f537c073cce771f65fcaca8f9de7edaccc54fd`, spec SHA256 `8e98725902b935b2e39660efa36fd58c80e804d7889be6ccd4243978e5a4b663`; the committed prompt and spec are byte-identical to the package (no repair).

- The native gate on the exact package bytes, on clean main `9ea25d8` before any branch or source change: exit 0, `IMPLEMENTATION_READY`, is_ready=true, RUNTIME/DETERMINISTIC, certificate_required=false, scope 8, 8 evidence items, 8 normative rules, error_codes empty.
- First invoked skill after mandatory startup reads: `ponytail` LITE.

## Implementation

Contract: `docs/public_market_contract_parity.md`. One finite offline operator `tools/alpha/run_public_market_contract_parity.py` (`run`/`verify`) over the pure library `src/data_layer/analytical_research/public_market_contract_parity.py`.

- **Call path:** caller SRC-01 scratch -> the unedited `run_source_grounding.verify` (cold, before copying) -> frozen copy -> `verify` again (same receipt id, equal to the cases file's `grounding_receipt_id`) -> native `load_corpus`/`bind_rule_texts`/`build_index`/`rank_markets` -> field-aware search -> one write-once content-addressed `pmcparity:sha256:` receipt. Path, hardlink, reparse and size guards are reused from the merged REL-01 operator; the socket guard and strict JSON from SRC-01.
- **Upstream pins (concept only, no code copied, both MIT):** `Polymarket/py-sdk@aa94ec431e3d4946576fb7c0d079fe1c14fcf676` (`examples/search.py` blob `895d728f…`, `src/polymarket/clients/public.py` blob `c0e1d178…`) and `ccxt/ccxt@28d9b2ca6e06173ce00f020cfd5bfac3275604d4` `ts/src/prediction/polymarket.ts` (blob `d7fb1dff…`). The blob ids were checked against the GitHub contents API at those commits. `ts/src/polymarket.ts` (blob `a428bf5e…`, `swap: true`) is perpetual futures and is refused.
- **Identity:** market, event, condition, category, status, clocks and rule digests are separate fields. Non-canonical ids, duplicate conditions, conflicting events, token collisions and count mismatches abstain. Every row is `ORIENTATION_UNPROVEN`, with no YES token and no tradable side.
- **SRC-01 compatibility:** `tools/alpha/run_source_grounding.py`, `source_grounding.py`, `alpha_discovery.py` and all PIT, Alpha, polymarket adapter, Hermes and fee files are unedited. A test pins that a legacy grounding receipt's code identity still equals `run_source_grounding.code_identity()`.

## Outcome (frozen SANITIZED_SYNTHETIC benchmark, untuned a-priori parameters)

60 cases input. 2 were refused (duplicate id, label outside the corpus) and 1 abstained `POST_CUTOFF` before scoring, leaving 57 validly paired cases: 50 positive, 7 no-match and 6 exact-identifier.

| Measure (57 paired) | field_aware_search_v1 | field_aware_text_only_v1 | merged rank_markets (R3-02) |
|---|---|---|---|
| Recall@10 | 49/58 | 49/58 | 52/58 |
| Precision@10 | 49/152 | 49/166 | 52/196 |
| False top-1 (positive, non-empty) | 0/42 | 1/42 | 2/44 |
| False exact-id top-1 | 0/6 | 0/6 | 0/6 |
| Abstained | 14/57 | 14/57 | 12/57 |

Field-aware search is more precise but recalls fewer labelled markets. This is not lift; `lift_claim` is null and `real_value` is `NOT_VERIFIED`. The real benchmark is `NOT_RUN` because no genuine local real corpus was supplied or found on the host. The `LOCAL_REAL_PIT` path is exercised with caller-declared fixture bytes, for mechanics only.

The offline vectors give these results. py-sdk: 5 projected, 1 invalid page; 1 tag and 1 profile `TAG_OR_PROFILE_UNSUPPORTED`. ccxt: 13 vectors with every refusal class, and 0 orientations proven. R3-23 and R3-27 stay `OWNER_ACCEPTANCE_PENDING`. All 36 capability rows are kept, with 0 new value acceptances.

## Validation state

LOCAL_VALIDATED on implementation commit `be73f0b`. Exact-head hosted checks, evidence mode and the Ready decision belong in the PR body, not here.

- **Diff-mode gate on `be73f0b`:** `wp_readiness_gate.py --check-diff --base main --head be73f0b`: exit 0, `IMPLEMENTATION_READY`, diff_scope checked, scope 8. `diff_scope_summary.py --require-exact-scope`: exact scope pass, 0 warnings.
- **Full suite:** run on `be73f0b` in the Linux docker image `s10-canary-siwc-validation:20261024`, `--network none --read-only`, using a clean LF clone with a real `origin/main` ref = `9ea25d8`. Command `python -B -m pytest -q -p no:cacheprovider --basetemp /tmp/full -ra`: exit 0, 14704 passed, 15 skipped, 125 warnings, 0 failed. The skips are pre-existing environment gates (strict DuckDB, pinned Hermes checkout, gitleaks binary, frontend Node, native Windows cases). The R007 symlink branch runs there.
- **Focused (Windows host):** the eight R001–R008 nodes in `tests/tools/alpha/test_public_market_contract_parity.py`: 8 passed. On this host the symlink branch of R007 is not exercised (WinError 1314, D005).
- **Adjacent families (Windows host):** `tests/tools/alpha`, `tests/data_layer/analytical_research`, `tests/data_layer/polymarket`, `tests/data_layer/point_in_time_market_research`, plus `tests/test_architecture_boundaries.py`, `tests/test_no_live_mode_by_default.py`, `tests/test_no_secret_placeholders.py` and both Hermes architecture guard files: 3596 passed, 6 skipped, 0 failed. This run started just before the two review fixes below, so the Linux full suite on `be73f0b` is the authoritative post-fix run.
- **Review fixes:** `find-bugs` found one Medium and one Low defect, both fixed in `be73f0b` with a regression assertion. A non-canonical native resolution date now abstains `MISSING_METADATA` instead of aborting the run, and a malformed month no longer crashes indexing. A later test-only commit replaced one R008 string literal; no source changed.
- **CLI smoke (outside the repo, real subprocesses):** `run` RUN_COMPLETE, receipt `pmcparity:sha256:9b53b08febf9dfd6117f4500f83edb2a583a8326f6bd2c9f0d3948ab83db854f`, code identity `code:sha256:04108be7754d8b75d9e7decf27936d43f6c314968a4b875cdf83600191b34d32`. Cold `verify` VERIFIED; identical repeat IDEMPOTENT_VERIFIED. A frozen-cases tamper gives TAMPER_DETECTED `RECOMPUTE_REFUSED:BENCHMARK_FREEZE_MISMATCH`; a receipt tamper gives TAMPER_DETECTED `RECEIPT_ID_MISMATCH` + `OUTPUT_MISMATCH:adoption`. An in-repo scratch is refused and nothing is created. Bad usage exits 2. Network attempts: 0.
- **Security:** generated-artifact guard passed. No local gitleaks binary on this host, so local gitleaks was not run; the pinned hosted gitleaks gate in `ci-final-gate` is authoritative. A local secret-pattern sweep of the added lines found nothing. No dependency, lock, CI or protected path changed.
