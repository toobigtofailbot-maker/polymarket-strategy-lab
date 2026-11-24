# S10-CAP-B2-RELATIONS-WALLET-01

B2: bundled W04 rules/relations + W05 wallet/public intelligence over one shared PIT case, consumed from the existing
native producers. RUNTIME/Risk3/L, exactly 11 paths. Branch `codex/s10-cap-b2-relations-wallet-01` was cut from clean
synchronized main `573ac90` (merge of PR #284, head `a716b4c`). PR #268 is open, separately owned and untouched;
nothing is stacked on it.

## Identity

- WP ID: S10-CAP-B2-RELATIONS-WALLET-01
- Title: B2 — Bundled shared-PIT relations (A5) + public-wallet (A6) advisory handoff
- Branch: codex/s10-cap-b2-relations-wallet-01
- PR: see GitHub PR metadata and PR body.
- Base commit: 573ac905b62fd2ee8e577db943503f6d8727b1d7
- Validated implementation commit: recorded in the PR body (this fragment is stable and non-self-referential).
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable and non-self-referential; it does not attempt to encode dynamic PR metadata or the SHA of the commit containing itself.
- Merge commit: (fill after merge)
- Evidence mode: recorded in the PR body (selected under docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md from the posted-body verifier result)

## Authority Posture

- Package class: B2_OFFLINE_SHARED_CASE_RELATION_WALLET_CONSUMER.
- Implementation authority: YES. Side26's exact B2 grant under Karl's standing software-development authorization, conditional on native readiness.
- Report/export authority: YES (PR and report-back only).
- Paper authority: NO
- Execution authority: NO
- Live authority: NO
- Credential authority: NO
- Real wallet / account / source acquisition authority: NO (synthetic public identifiers only)
- Model/provider spend authority: NO (zero provider, LLM or Hermes calls in B2)
- Runtime/scheduler authority: NO (one finite manual operator; no daemon or loop)
- Canonical evidence authority: offline SANITIZED_SYNTHETIC test receipts only.
- Network authority: none for runtime/product/source/wallet API. Workflow network only (git fetch/push, GitHub PR publication, hosted CI), plus read-only checkouts of the four pinned upstream commits (R3-04, R3-11, R3-19, R3-14) into a scratch directory outside the repository for software inspection (no install, no copy, no dataset download).
- Dependency-change authority: NO
- Protected boundary groups (docs/ai/codex/PROTECTED_PATHS.md): credentials/secrets, authenticated clients, wallet/account, order placement/cancel, execution gateway, paper engine, scheduler/bot loop, runtime/daemon, dashboard/deployment, dependency/lock changes, external code copying and generated artifacts are all untouched.

## Readiness

- One ordinary structural fix to the frozen prompt before any source edit: the section heading `7. STOPS / SUCCESSOR` became `7. HARD STOPS / SUCCESSOR` (the native gate's hard-stops signal). Spec bytes unchanged.
- Gate: exit 0, `IMPLEMENTATION_READY`, RUNTIME, certificate_required=false, scope 11, 12 evidence items, 12 rules, error_codes [].
- Prompt and spec SHA-256 values are recorded in the PR body with the gate output.

## Implementation

Contract: `docs/relation_wallet_spine_contract.md`.

- `relation_wallet_spine.py`: closed case validation; `b1a_lineage` (read-only A1–A4 ids); `bind_target` (native scout on the spine's frozen grounding, compared to B1-A by native ids); `relations` (A5: selected native REL-01 rows + genuine Oracle3 parity, rule-SHA binding, full denominators, read-side A7 pointer); `wallet` (A6: native WALLET-01 → WALLET-02 → WALLET-03 on the same head, cohort, contexts and cutoff, exact PIT context binding, mapping round trip); six-ID capability ledger; core/finalize.
- `run_relation_wallet_spine.py`: `run` (write-once scratch, socket block, freeze/re-hash, Oracle3 parity run, nested native verifies, receipt) and read-only `verify` (full recompute; `TAMPER_DETECTED` on any difference).
- Every native producer (B1-A, W01, SRC-01, REL-01, Oracle3 bridge/parity, WALLET-01/02/03, Alpha modules) and the roadmap archive are byte-unchanged; no native module imports B2.

## Dispositions

| ID | Disposition |
|---|---|
| R3-03 | ENG_OFFLINE_SHARED_CASE_CONSUMED_BY_A5_NOT_VALUE_VERIFIED (genuine vendored `check_constraint` on the shared case) |
| R3-03-FEES | FIXTURE_FEE_SCHEDULE_INVOKED_CURRENTNESS_UNVERIFIED |
| R3-04, R3-11, R3-19 | OPEN, NATIVE_ONLY (upstream import closure needs unvendored modules, provider clients or network) |
| R3-14 | OPEN_OWNER_RIGHTS, BLOCKED_SCHEMA_INSPECTED_ONLY (36 GiB external dataset, no data license) |

None is VALUE_VERIFIED; owner disposition PENDING. The other 30 of the 36 program IDs are unchanged.

## Scope Boundary

- src/data_layer/analytical_research/relation_wallet_spine.py
- tools/alpha/run_relation_wallet_spine.py
- tests/data_layer/analytical_research/test_relation_wallet_spine.py
- tests/tools/alpha/test_run_relation_wallet_spine.py
- docs/relation_wallet_spine_contract.md
- docs/deferred_items_log.md
- docs/project_status.md
- docs/repo_truth_index.md
- docs/status_entries/S10-CAP-B2-RELATIONS-WALLET-01.md
- docs/wp_specs/S10-CAP-B2-RELATIONS-WALLET-01/wp_prompt.txt
- docs/wp_specs/S10-CAP-B2-RELATIONS-WALLET-01/wp_spec.json

## Negative Test Matrix

| Category | Coverage |
|---|---|
| Malformed / duplicate / missing / unknown fields | R009 (`CASE_FIELDS_INVALID`, `CASE_JSON_INVALID` for duplicate key, NaN, encoding, truncation; `CASE_UNREADABLE` empty/oversize) |
| Type / null / empty / bool-as-int / float money | R009 (`MODEL_IDS_INVALID`, `WALLET_HEAD_INVALID`, `QUOTE_WITNESSES_INVALID`, `COST_SCENARIOS_INVALID`, `MARKET_CONTEXTS_INVALID`) |
| Case variants / noncanonical ids / clocks | R009 (`TARGET_MARKET_ID_NONCANONICAL`, `WALLET_AS_OF_INVALID`, `UPSTREAM_RECEIPT_ID_INVALID`) |
| Wrong market / universe / rule / lineage | R002 (`SPINE_TARGET_MISMATCH`, `SPINE_GROUNDING_MISMATCH`, `TARGET_NOT_ADMITTED:*`, `REL_*_MISMATCH`, `PARITY_REL_MISMATCH`), R004 (`RULE_IDENTITY_MISMATCH`) |
| Relation direction / settlement semantics | R004 (counterexample, tie/cancel/reschedule/partial INCONCLUSIVE, VOID modelled, `RULE_CONFLICT`) |
| Wallet PIT / identity / coverage gaps | R006 (late observation, weak identity, no/scenario/wrong-token/late quote, orientation, missing cost/depth, outside cohort, tampered retained bytes, head drift, corrupt ledger, cutoff after decision), R002 context refusals |
| Path / link / sidecar / scratch safety | R009 (`QUOTE_MEMBER_INVALID`, `QUOTE_MEMBER_UNSAFE`, `SQLITE_SIDECAR_PRESENT`), R010 (`SCRATCH_NOT_EMPTY`, `SCRATCH_INVALID`, `INPUT_PATHS_OVERLAP`, partial scratch) |
| Forbidden credential / secret wording | R009 (`FORBIDDEN_FIELD` incl. case variants, `SECRET_MATERIAL_REJECTED`; native price/depth/fee names still accepted) |
| Replay / tamper / network / no echo | R010 (receipt, case, registry, ledger, REL, parity, bundle, spine tamper → not VERIFIED; zero socket calls; no path/traceback echo), R009 usage exit 2 |
| False value / tradability / person inference | R011 (no `tradable`/value/size/lift terms; A7 conditional only), R006 (no address, score, rank or recommendation) |
| Historical receipts | R008 (native code identities pinned; REL/parity/B1-A receipts cold-verify unchanged) |

## Validation Summary

- Commands and results are recorded in the PR body and in `SIDE26_B2_CC_REPORT_BACK.md`. They cover the R001–R012 exact nodes, adjacent suites, the full suite, diff scope, readiness `--check-diff`, the generated-artifact check, gitleaks and hosted CI.

## Deferred Items

- Added S10-CAP-B2-RELATIONS-WALLET-01-D001 to D006.

## Next WP Pointer

- Suggested next WP: B3 only after Karl merges reviewed B2. W08 coordinator consumes the B2 receipt interface; A8/A9 remain later owners.

## Ready for Review

- Ready for review: recorded in the PR body after posted-evidence verification. Merge: NO (Karl only).
