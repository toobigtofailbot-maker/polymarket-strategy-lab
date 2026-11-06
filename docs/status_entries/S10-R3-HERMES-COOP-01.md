# S10-R3-HERMES-COOP-01

RUNTIME/DETERMINISTIC, exact 9 paths, branch `codex/s10-r3-hermes-coop-01` from clean synchronized main `105eb6c6bd366f1e585e83a03766ad27cf9b9616`.
- PR #272 is merged: head `11fa10f9d30f821709d94cced78d65b53e4758e8`, merge `105eb6c6bd366f1e585e83a03766ad27cf9b9616`.
- PR #268 is open and untouched at `9a5a00cd61effa4e28b82f830427440b23aba86c`. Nothing is stacked on it.
- Karl authorized implementation within the package scope, conditional on native readiness. Caller-supplied specialist submissions are not proof of real Hermes delegation. No paid provider, no permission expansion, no research promotion, no merge; merge stays Karl-only.

## Readiness

Package prompt SHA256 `2d588f791a5769f21ef25a39586cbee2f07b61e7bbccbcc384e1bdb73ed08f96` (as delivered) and spec SHA256 `e7ba13804149f33026328278e807cb4e8bdb9373e65324b92e280ecf0112a219` (package `SHA256SUMS.txt` verified).

- The native gate on the exact delivered bytes, on clean detached main before any branch or source change: exit 1, `NOT_IMPLEMENTATION_READY`, `READINESS_PROMPT_STRUCTURE_INVALID`.
- Heading-only repair, no normative change: "Authority:" became "Authority / Non-Authority:" and the §8 heading names the negative test matrix, evidence plan and hard stops. Committed prompt SHA256 `00f2c4c3d3a9ad846ad4f366f4e9c8b10707e0cb7a1e526563b7cd170bc23603`; the spec is byte-identical.
- Round 1: the native gate on the repaired bytes, same clean main: exit 0, `IMPLEMENTATION_READY`, is_ready=true, RUNTIME/DETERMINISTIC, certificate_required=false, scope 9, 8 evidence items, 8 normative rules, error_codes empty.
- Round 1 stopped BLOCKED_NOT_READY: the frozen source path `src/data_layer/analytical_research/hermes_cooperation.py` matched the historical `^src/.*/hermes` guards (D005).
- Side24 targeted correction (owner-authorized): the source path only changes to `src/data_layer/analytical_research/research_cooperation.py`; scope stays exactly 9 paths and no authority field changes. Corrected prompt SHA256 `40593fc464d2389b24bd295ccb8e5596708c248968ff10da8a04903dd6c17f2f`, spec SHA256 `cb092d58fcd494d7875897c1aa699404f266466e8f039ba4bc9aa33c61958726` (correction package `SHA256SUMS.txt` verified). The native gate on these exact bytes, on clean detached main `105eb6c` before any source change: exit 0, `IMPLEMENTATION_READY`, RUNTIME/DETERMINISTIC, certificate_required=false, scope 9, error_codes empty. The committed prompt and spec are byte-identical.

## Implementation

Contract: `docs/hermes_cooperation_citation_contract.md`. One finite offline operator `tools/alpha/run_hermes_cooperation.py` (`run`/`verify`) over the library `src/data_layer/analytical_research/research_cooperation.py`.

- **Call path:** frozen copy of an SRC-01 scratch -> the real, unedited `run_source_grounding.verify` (must be `VERIFIED` and match the case's `grounding_receipt_id`) -> native `load_corpus`/`bind_rule_texts`/`evaluate_sources`/`join_alpha_candidates` -> per-question assessment -> one write-once content-addressed `hermescoop:sha256:` receipt with a native `ResearchProvenanceManifest`.
- **SRC-01 compatibility:** `tools/alpha/run_source_grounding.py` is not edited (git blob `49eb952984c50d5f38d1afd8e11ff90f14af2a33` pinned by test); its `code_identity` and historic receipts stay valid; no Hermes module is imported by it.
- **Citations:** a sorted ledger over SRC-01 ACCEPTED sources only; each citation must be allowlisted, bound to the question's market, admissible at the question cutoff under SRC-01's clock rules plus native `evaluate_replay_admissibility`, and an exact UTF-8 substring of the frozen bytes. Statuses: SUPPORTED_QUOTE_PRESENT, CONTRADICTED_BY_OTHER_ROLE, UNSUPPORTED_OR_UNCITED, SOURCE_UNAVAILABLE, POST_CUTOFF, UNKNOWN. Quote integrity, source origin (`SOURCE_ORIGIN_UNVERIFIED`) and fact truth (`NOT_AUTOMATICALLY_VERIFIED`) are separate fields.
- **Roles:** FORECASTER and FALSIFIER rows are `CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED` with `execution_provenance: ABSENT_NO_HERMES_INVOCATION`. Optional native drafts go through the unchanged `models.validate_research_draft`; their URLs must be sanctioned and every scored claim must cite a draft source. Missing, empty, duplicate, scope-mismatched or same-origin roles abstain. No vote, no probability, no truth verdict.
- **Authority:** RESEARCH_ONLY; all sockets blocked; no Hermes, `delegate_task`, provider, model, store, WP170, paper, order, strategy or capital path. Receipt `authority` is all false or 0 except `research_only`.

## Outcome (frozen SANITIZED_SYNTHETIC benchmark, corpus `9dc3ab67413c4abf33ba322dedb3738df1595f3d893186c000ec9aaf64feae12`)

54 questions over 10 SRC-01 markets (22 accepted sources); 52 eligible, 2 invalid (unknown market, non-native candidate); 44 validly paired, 7 comparison-only, 1 both abstained.

| Measure (52 eligible) | baseline_single_role_v0 | two_role_cooperation_v1 |
|---|---|---|
| Evaluated / abstained | 51 / 1 | 44 / 8 |
| Claims | 51 | 88 |
| Quote verified / false | 47 / 2 | 80 / 4 |
| Labelled conflicts found / missed (of 10) | 0 / 10 | 10 / 0 |
| Counterevidence surfaced / missed (of 23) | 0 / 23 | 21 / 2 |

Labels were authored with the corpus and a single role cannot disagree with itself, so this measures checker accounting on authored cases, not research quality, lift or real Hermes delegation (D001-D003). All 36 capability ids are kept; only `R3-05` and `R3-05-CITATIONS` advance, to offline non-value states.

## Validation state

LOCAL_VALIDATED on correction commit `1a248e8` (all 9 paths; `hermes_cooperation.py` absent). Current head, exact-head hosted checks, evidence mode and the Ready decision belong in the PR body, not here.

- **Four historical guards + R008 first (Windows host):** `test_hermes_advisory_foundation_architecture_docs.py::test_no_actual_hermes_implementation_artifacts_added`, `test_hermes_input_output_contracts_and_validator_requirements_docs.py::test_no_actual_hermes_implementation_artifacts_added`, `test_autonomous_feedback.py::test_auto02_historical_hermes_guards_exact_allowlist_and_sibling_negative`, `test_two_stage.py::test_ts02_existing_hermes_strategy_context_and_ts01_compatibility` and `test_coop_scope_adoption_negative_matrix_and_legacy_src`: 5 passed, 0 skipped. The guards and pins are unedited.
- **Full suite (one stable candidate):** Linux docker image `s10-canary-siwc-validation:20261024`, `--network none --read-only`, clean LF clone at `1a248e8` with a real `origin/main` ref = `105eb6c`, `python -B -m pytest -q -p no:cacheprovider --basetemp /tmp/full -ra`: exit 0, 14696 passed, 15 skipped, 125 warnings, 0 failed. The skips are pre-existing environment gates (strict DuckDB, pinned Hermes checkout, gitleaks binary, frontend Node, native Windows cases); the coop symlink-refusal test runs there.
- **Round-1 full-suite history (superseded):** `d5c6ba7` had 4 failed / 14692 passed (the D005 guards); earlier attempts failed only for environment reasons (no `origin/main` ref; fragment not yet committed).
- **Focused (Windows host):** `test_hermes_cooperation.py` + `test_source_grounding.py` + deferred-log test: 42 passed, 1 skipped (the separate symlink-refusal test; WinError 1314, D004).
- **Adjacent (Windows host):** `tests/tools/alpha`, `tests/data_layer/analytical_research`, `tests/research_runtime/hermes_controlled_runtime`, both Hermes architecture guard files, architecture boundaries, no-live-mode and no-secret-placeholder tests: 2154 passed, 15 skipped, 0 failed.
- **Round-1 review fixes (kept):** native cutoff admissibility (`INGESTED_AFTER_CUTOFF`, native basis), empty role -> `ROLE_EMPTY` abstention, native-draft claim/source binding, whole-question benchmark commitment, unhashable citation pairs, split symlink test.
- **Security:** gitleaks 8.27.2 `git --redact` over `105eb6c..1a248e8`: no leaks. Generated-artifact guard passed. Authority boundary review: BOUNDARY_INTACT. No dependency added.
- **CLI receipt on the renamed code (SANITIZED_SYNTHETIC, outside the repo):** code identity `code:sha256:f2131723a9a209f2f27e7d96e9cca53e5298ee15890a28233a1c832ae0dec019`; SRC-01 verify VERIFIED; `run` RUN_COMPLETE `hermescoop:sha256:8c54a617dc5cd149f3265b9ceae9ceb33825a8aca659a5b953bdccd55a14d6f1`; cold `verify` VERIFIED; repeat IDEMPOTENT_VERIFIED; a tampered case copy TAMPER_DETECTED (exit 1); bad usage exit 2; network attempts 0. The benchmark case bytes, denominators and metrics are identical to round 1; only the code identity and receipt id changed.
