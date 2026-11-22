# S10-CAP-B1-SOURCE-FORECAST-01

B1-A: native source/PIT scout and research feeding the existing W01 Hermes consumer and the forecast consumer spine.
RUNTIME/Risk3/L, exactly 11 paths. Branch `codex/s10-cap-b1-source-forecast-01` was cut from clean synchronized main
`b637c00` (merge of PR #282, head `f932d49`). PR #268 is open, separately owned and untouched; nothing is stacked on it.

## Identity

- WP ID: S10-CAP-B1-SOURCE-FORECAST-01
- Title: B1-A — Source/PIT to research and forecast consumer spine
- Branch: codex/s10-cap-b1-source-forecast-01
- PR: see GitHub PR metadata and PR body.
- Base commit: b637c00230e698129e8696bcb3927db157106a86
- Validated implementation commit: recorded in the PR body (this fragment is stable and non-self-referential).
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable and non-self-referential; it does not attempt to encode dynamic PR metadata or the SHA of the commit containing itself.
- Merge commit: (fill after merge)
- Evidence mode: recorded in the PR body (selected under docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md from the posted-body verifier result)

## Authority Posture

- Package class: B1_OFFLINE_SOURCE_FORECAST_CONSUMER_SPINE.
- Implementation authority: YES. Side26's exact B1-A grant under Karl's 2026-11-21 standing software-development delegation, conditional on native readiness.
- Report/export authority: YES (PR and report-back only).
- Paper authority: NO
- Execution authority: NO
- Live authority: NO
- Credential authority: NO
- Runtime/scheduler authority: NO (one finite manual operator; no daemon or loop)
- Canonical evidence authority: offline SANITIZED_SYNTHETIC test receipts only; disposable test Alpha registries are appended through W01's existing interface.
- Network authority: none for runtime/product. Workflow network only (git fetch/push, GitHub PR publication, hosted CI).
- Dependency-change authority: NO
- Protected boundary groups (docs/ai/codex/PROTECTED_PATHS.md): credentials/secrets, authenticated clients, wallet/account, order placement/cancel, execution gateway, paper engine, scheduler/bot loop, runtime/daemon, dashboard/deployment, dependency/lock changes, external code copying and generated artifacts are all untouched.

## Readiness

- The external package bytes (prompt `edd55c34…`, spec `8279ac96…`) failed the native gate with `READINESS_PROMPT_STRUCTURE_INVALID` and `READINESS_RULE_MATRIX_INVALID`, exit 1.
- Pre-edit structural correction: prompt section 8 adds the objective, authority, negative matrix, evidence plan, successor and report-back signals plus a nine-row normative rule matrix. No scope or authority changed. Gate: exit 0, `IMPLEMENTATION_READY`, RUNTIME, certificate_required=false, scope 11, 9 evidence items, 9 rules.
- Post-edit correction (session-approved 2026-11-22, prompt section 9, D004): the tools test was renamed to `tests/tools/alpha/test_run_source_forecast_spine.py` to remove a duplicate test basename that broke default-mode full-suite collection.
- Final prompt SHA-256 `50fd0ea15db07c0984ff8cfde5b80d828f35165ba451742fb4f05219db8dda4d`, spec SHA-256 `b4546e14bfd70210b590aa2f07a62a0ebf5515acac3492e8a0bfde59c2ce7015`. Gate on these bytes: exit 0, `IMPLEMENTATION_READY`, 11/9/9, error_codes [].

## Implementation

Contract: `docs/source_forecast_spine_contract.md`.

- `source_forecast_spine.py`: `load_grounding` (native SRC-01 verify), `scout` (A1), `research` (A2: pinned Metaculus leaves narrow the W01 allowlist; pinned official SDK on MockTransport cross-checks identity), `check_lineage`, `w01_case`, `bind_forecast`, `build_core`/`finalize`. It defines no new canonical identity or store.
- `run_source_forecast_spine.py`: `run` checks A1/A2, then lineage, then runs forecast run/verify, then W01 run/verify, then writes one write-once receipt. `verify` is a cold recompute. Replay is idempotent; a partial scratch refuses.
- All existing W01, source-grounding, forecast, Alpha, market and upstream bridge modules are byte-unchanged.

## Scope Boundary

- src/data_layer/analytical_research/source_forecast_spine.py
- tools/alpha/run_source_forecast_spine.py
- tests/data_layer/analytical_research/test_source_forecast_spine.py
- tests/tools/alpha/test_run_source_forecast_spine.py
- docs/source_forecast_spine_contract.md
- docs/deferred_items_log.md
- docs/project_status.md
- docs/repo_truth_index.md
- docs/status_entries/S10-CAP-B1-SOURCE-FORECAST-01.md
- docs/wp_specs/S10-CAP-B1-SOURCE-FORECAST-01/wp_prompt.txt
- docs/wp_specs/S10-CAP-B1-SOURCE-FORECAST-01/wp_spec.json

## Negative Test Matrix

| Category | Coverage |
|---|---|
| Unknown / cross-venue / noncanonical market | R005 (`TARGET_MARKET_ID_NONCANONICAL`, `TARGET_NOT_IN_UNIVERSE`) |
| Mismatched rule hash | R005 (`TARGET_RULE_NOT_BOUND`), R004 (forecast `RULE_MISMATCH` refuses binding) |
| Duplicate / ambiguous identity | R005 (`DUPLICATE_CONDITION` abstain, `TARGET_CANDIDATE_AMBIGUOUS`) |
| Absent bytes / late capture / revision / unauthorized source | R005 (all four refused, so A2 returns `NO_ADMITTED_PRE_CUTOFF_SOURCE`), R002 (late source refused) |
| False quote / injected instructions / role claim | R006 pinned (`COOPERATION_NOT_GROUNDED`, `CHILD_OUTPUT_NOT_JSON`, `CHILD_OUTPUT_SCHEMA_INVALID`) |
| Missing / conflicting candidate or family lineage | R005 and R007 (`*_NOT_IN_LINEAGE`) |
| Credentials / trade verbs | R006 (`SECRET_MATERIAL_REJECTED`, `FORBIDDEN_FIELD`), with no echo |
| Missing or wrong pin | R006 (`DELEGATION_REFUSED`), no append |
| Replay / partial / tamper / stale / code identity | R007 |
| Network / sockets | R002 and R006 (zero connect attempts) |
| SDK identity conflict / malformed page | R002, R008 |
| Numeric precision, fees, orders, risk | NOT_APPLICABLE: no price, size, fee or order path exists in the new code |
| Schema-version migration | NOT_APPLICABLE: new v1 schemas only; existing receipts are read through their native verifiers |

## Validation Summary

- Focused, adjacent, full-suite, diff-scope, generated-artifact, gitleaks and hosted-CI commands and results are recorded in the PR body and in `SIDE26_B1A_CC_REPORT_BACK.md`.

## Deferred Items

- Added S10-CAP-B1-SOURCE-FORECAST-01-D001 to D006 (D004 resolved in-WP).

## Next WP Pointer

- Suggested next WP: S10-CAP-B1-METHODS-01 (B1-B), only after Karl merges reviewed B1-A.
- Suggested next WP notes: upstream ForecastBot / Wang MLE / sampler / ForecastBench method parity, with independent source and security review.

## Ready for Review

- Ready for review: recorded in the PR body after posted-evidence verification. Merge: NO (Karl only).
