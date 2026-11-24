# S10-CAP-B1-METHODS-01

B1-B: bundled forecast, sampling and benchmark method parity over one native forecast cohort, consumed by the native
scorers. RUNTIME/Risk3/L, exactly 18 paths (16 plus 2 by Side26 Amendment 01). Branch `codex/s10-cap-b1-methods-01` was cut from clean synchronized main
`0d5ddfa` (merge of PR #283, head `af34e06`). PR #268 is open, separately owned and untouched; nothing is stacked on it.

## Identity

- WP ID: S10-CAP-B1-METHODS-01
- Title: B1-B — Bundled forecast/sampling/benchmark method parity
- Branch: codex/s10-cap-b1-methods-01
- PR: see GitHub PR metadata and PR body.
- Base commit: 0d5ddfaada8289454d8b4b2b08548c36ff18b16a
- Validated implementation commit: recorded in the PR body (this fragment is stable and non-self-referential).
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable and non-self-referential; it does not attempt to encode dynamic PR metadata or the SHA of the commit containing itself.
- Merge commit: (fill after merge)
- Evidence mode: recorded in the PR body (selected under docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md from the posted-body verifier result)

## Authority Posture

- Package class: B1_OFFLINE_METHOD_PARITY_CONSUMER.
- Implementation authority: YES. Side26's exact B1-B grant under Karl's standing software-development authorization, conditional on native readiness.
- Report/export authority: YES (PR and report-back only).
- Paper authority: NO
- Execution authority: NO
- Live authority: NO
- Credential authority: NO
- Model/provider spend authority: NO (cost UNKNOWN; zero provider calls)
- Runtime/scheduler authority: NO (one finite manual operator; no daemon or loop)
- Canonical evidence authority: offline SANITIZED_SYNTHETIC test receipts only.
- Network authority: none for runtime/product/source API. Workflow network only (git fetch/push, GitHub PR publication, hosted CI), plus read-only shallow fetches of the seven pinned upstream commits into a scratch directory outside the repository for local parity (no install, no copy).
- Dependency-change authority: NO
- Protected boundary groups (docs/ai/codex/PROTECTED_PATHS.md): credentials/secrets, authenticated clients, wallet/account, order placement/cancel, execution gateway, paper engine, scheduler/bot loop, runtime/daemon, dashboard/deployment, dependency/lock changes, external code copying and generated artifacts are all untouched.

## Readiness

- The frozen package bytes passed the native gate unmodified: exit 0, `IMPLEMENTATION_READY`, RUNTIME, certificate_required=false, scope 16, 12 evidence items, 12 rules, error_codes [].
- Side26 Amendment 01 (2026-11-23) added `tools/alpha/run_learning_feedback.py` and `tests/tools/alpha/test_learning_feedback.py` after a base-vs-head witness reproduced a LEARN-01 historical cold-verify regression (D002). Prompt section 9, spec arrays and `max_changed_files=18` were updated before any source edit. Gate: exit 0, `IMPLEMENTATION_READY`, 18/12/12, error_codes [].
- Prompt and spec SHA-256 values are recorded in the PR body with the gate output.

## Implementation

Contract: `docs/forecast_methods_integration_contract.md`.

- `forecast_methods_integration.py` (stdlib only) contains:
  - the nine-ID method register, with pins read from native `SOURCE_PINS`; `check_register` refuses false acceptance;
  - a ForecastBench sampler port that reproduces numpy's legacy RandomState exactly;
  - the WP170 membership read;
  - the upstream-objective Wang port with per-case parity;
  - the Metaculus, fbsim and Gnosis metric formulas;
  - the paired comparison, plus `build_methods_core`, `finalize_receipt` and `verify_receipt`.
- `forecast_evaluation.py` gains the additive opt-in `score_diagnostic_candidate` (never called by `build_evaluation_core`) and the pinned `LEGACY_V2_CODE_IDENTITY`.
- `run_forecast_evaluation.py`: `verify` replays a v2 receipt that claims the pinned legacy identity. Nothing else changes.
- `run_learning_feedback.py` (Amendment 01): `verify` replays a LEARN-01 receipt sealed at `0d5ddfa`. It requires the exactly pinned former identity `LEGACY_V2_LEARN_CODE_IDENTITY` and a nested forecast that natively verifies with `FE.LEGACY_V2_CODE_IDENTITY`. Runs and current receipts are unchanged.
- `run_forecast_methods_integration.py` provides `run` (cold forecast verify, freeze, method phase, native scoring, write-once receipt) and a cold `verify`.
- W01, B1-A, source-grounding, native learning_feedback.py, experiment_os, the Alpha modules and the roadmap archive are byte-unchanged.

## Dispositions

| ID | Disposition |
|---|---|
| R3-12, R3-12-SAMPLER, R3-20, R3-22 | ENG_OFFLINE (real pinned callable executed locally; goldens pinned) |
| R3-10-WANG, R3-06 | BLOCKED (dependencies absent; port/formula parity only) |
| R3-10, R3-01 | BLOCKED (provider, credential, network; zero forecasts) |
| R3-18 | OPEN_OWNER_RIGHTS (no license declared) |

None is VALUE_VERIFIED. The other 27 of the 36 program IDs are unchanged.

## Scope Boundary

- src/data_layer/analytical_research/forecast_methods_integration.py
- src/data_layer/analytical_research/forecast_evaluation.py
- tools/alpha/run_forecast_methods_integration.py
- tools/alpha/run_forecast_evaluation.py
- tests/data_layer/analytical_research/test_forecast_methods_integration.py
- tests/tools/alpha/test_run_forecast_methods_integration.py
- tests/tools/alpha/test_forecast_evaluation.py
- tests/tools/alpha/test_forecast_wp170_binding.py
- tools/alpha/run_learning_feedback.py
- tests/tools/alpha/test_learning_feedback.py
- docs/forecast_methods_integration_contract.md
- docs/forecast_evaluation_contract.md
- docs/deferred_items_log.md
- docs/project_status.md
- docs/repo_truth_index.md
- docs/status_entries/S10-CAP-B1-METHODS-01.md
- docs/wp_specs/S10-CAP-B1-METHODS-01/wp_prompt.txt
- docs/wp_specs/S10-CAP-B1-METHODS-01/wp_spec.json

## Negative Test Matrix

| Category | Coverage |
|---|---|
| Malformed / duplicated records | R009 (`METHODS_JSON_INVALID`, `METHODS_SCHEMA_INVALID`, `METHODS_FIELDS_INVALID`, `DUPLICATE_SAMPLE`), R007 (`FBSIM_RECORD_REJECTED`) |
| Type / null / empty | R009 (`SAMPLER_INVALID`, `WANG_INVALID`), R006 (`CANDIDATE_SHAPE_INVALID`, `CANDIDATE_PROBABILITY_INVALID`), R011 (`NO_PAIRED_CASES`) |
| Unsorted / overlapping temporal splits, clock | R004 (`TRAIN_TEST_OVERLAP`), R009 (`SAMPLER_CLOCK_BEFORE_GROUNDING`, `SAMPLER_CLOCK_AFTER_DECISION`) |
| Unsupported source / schema | R002 and R008 (`FORECAST_RECEIPT_SCHEMA_UNSUPPORTED` for v1), R009 (`SOURCE_RECEIPT_MISMATCH`, `FORECAST_RECEIPT_ID_INVALID`), R003 (`CATEGORY_NOT_IN_UPSTREAM_TAXONOMY`) |
| Wrong pin / license / false acceptance | R001 and R012 (`REGISTER_PIN_MISMATCH`, `REGISTER_LICENSE_MISMATCH`, `REGISTER_FALSE_ACCEPTANCE`, `REGISTER_CAUSE_MISSING`, `REGISTER_DISPOSITION_INVALID`, `REGISTER_IDS_INVALID`) |
| Sandbox escape / scratch | R010 (`SCRATCH_INSIDE_REPOSITORY`, `SCRATCH_NOT_EMPTY`, partial scratch, write-once) |
| Forbidden credential / trade wording | R009 (`FORBIDDEN_FIELD`), R010 (secret material, no echo) |
| Wrong outcome availability | R006 and R007 (the native gate excludes the unresolved case; denominators recorded) |
| Unknown cost / provider | R005 (`PROVIDER_EXECUTION_NOT_AUTHORIZED_COST_UNKNOWN`, explicit open, zero forecasts) |
| Scorer direction / native disagreement | R009 (`SCORER_DIRECTION_MISMATCH`) |
| False lift / value | R011 (`INCONCLUSIVE_SYNTHETIC_LABELS_NOT_VALUE`, `INCONCLUSIVE_INSUFFICIENT_PAIRED`, `NO_LIFT`, `LOCAL_OBSERVATION_UNREVIEWED_NOT_VALUE`) |
| Replay / tamper / code identity / network | R010 (`TAMPER_DETECTED`, `RECEIPT_ID_MISMATCH`, `NETWORK_ATTEMPT_BLOCKED`), R008 legacy tamper |
| Historical LEARN-01 identity (Amendment 01) | `test_learning_sealed_pre_b1b_receipts_replay_current_and_refusals` (forged and current-claimed identity, downgrade, score, outcome, nested identity and swapped forecast all refuse) |
| Safe allowed vocabulary | R010 (`DIAGNOSTICS_ONLY` and `NOT_RELEASED` accepted; `CONFIRMED_EDGE`, `QUALIFIED_STRATEGY` and `OOS_RELEASED` absent) |
| No-citation | NOT_APPLICABLE: no text claim or citation is produced; upstream identity is pinned by commit, file and license |
| Trade fee / order / live | NOT_APPLICABLE: no price, size, fee, order or live path exists in the new code |

## Validation Summary

- Commands and results are recorded in the PR body and in `SIDE26_B1B_CC_REPORT_BACK.md`. They cover the R001–R012 exact nodes, adjacent tests, historical guards, the full suite, diff scope, the generated-artifact check, gitleaks and hosted CI.

## Deferred Items

- Added S10-CAP-B1-METHODS-01-D001 to D007; D002 resolved in-WP by Amendment 01.

## Next WP Pointer

- Suggested next WP: B2 rules/relations plus wallet/public intelligence, only after Karl merges reviewed B1-B. Use the minimum technical split if the file/authority guard requires one.
- W08 orchestration and A8/A9 controlled feedback remain on the compressed roadmap.

## Ready for Review

- Ready for review: recorded in the PR body after posted-evidence verification. Merge: NO (Karl only).
