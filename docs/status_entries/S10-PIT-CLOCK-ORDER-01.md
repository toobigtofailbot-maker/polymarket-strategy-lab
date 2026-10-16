# S10-PIT-CLOCK-ORDER-01 Status Entry

## Identity and authority

- WP ID: S10-PIT-CLOCK-ORDER-01
- Title: Precise nanosecond PIT clock ordering
- Branch: codex/side19-pit-clock-order
- Base commit: 4ee22b89bb63ae3fd11e935943694577e3444919 (PR236; merged head 75db804b3351e1d3c6699336a0dadd77c97a4133).
- Validated implementation commit: recorded in the external exact-head ZIP to avoid a self-referential containing-commit claim.
- PR/current live PR head/merge: none; publication, hosted CI, merge and deployment require later owner approval.
- Evidence mode: BLOCKED_NOT_READY (local implementation only; no posted evidence).
- Package class: SHARED_PIT_CLOCK_CORRECTION; M; risk2; FAST; exact six paths.
- Implementation/report authority: Karl authorized this narrow local repair and one verified ZIP. Canonical evidence authority is limited to local WP evidence. No historical reclassification/backfill.
- Network: workflow Git fetch/remote identity and an unsuccessful GitHub metadata read only; product/provider/source/account calls0. No dependency/lock change or install; use the existing permitted Python3.12 validation image.
- Credential, paper, scheduler, Hermes, strategy, execution, order, capital and live authority: NO; trading USD0/orders0.

## Scope and change

Exactly two functional paths plus the four mandatory governance records:

- src/data_layer/point_in_time_market_research/research_provenance.py
- tests/data_layer/point_in_time_market_research/test_research_provenance.py
- docs/deferred_items_log.md
- docs/status_entries/S10-PIT-CLOCK-ORDER-01.md
- docs/wp_specs/S10-PIT-CLOCK-ORDER-01/wp_prompt.txt
- docs/wp_specs/S10-PIT-CLOCK-ORDER-01/wp_spec.json

One private canonical UTC nanosecond key, one cutoff-key computation and two replaced comparisons. Existing parser, serialization/IDs, alias, correction/uncertainty/local/public/missing precedence and errors are preserved. No caller rewrite or general utility. All other paths and Centralized Boundary Groups in docs/ai/codex/PROTECTED_PATHS.md remain outside scope. Generated environments and logs stay external/uncommitted.

## Validation evidence

- Native pre-implementation readiness: exit0, FAST, six paths, five evidence requirements, three normative rules, zero errors, no certificate required. Initial package-format errors were corrected before functional implementation and are retained externally.
- Baseline regression: `python -B -m pytest -q -p no:cacheprovider --tb=short tests/data_layer/point_in_time_market_research/test_research_provenance.py::test_nanosecond_order_matches_independent_oracle` -> expected exit1, 44 failed/192 passed.
- Focused/adjacent: `python -B -m pytest -q -rs -p no:cacheprovider tests/data_layer/point_in_time_market_research/test_research_provenance.py tests/research_runtime/hermes_controlled_runtime/test_context_broker_reconciliation.py tests/data_layer/wallet_intelligence/test_profile.py tests/data_layer/wallet_intelligence/test_copyability.py` -> exit0, 348 passed, zero skips.
- Required final checks: native readiness `--check-diff`, generated-artifact guard, exact diff/whitespace, compatibility/identity proof, dependency health and one authoritative full pytest at the final candidate. Actual commands, exits, counts, skips/failures and immutable commit binding are retained together in the external ZIP. This fragment makes no full-suite PASS claim in advance.
- Negative test matrix: temporal admission YES; missing/null/type/empty/malformed/future/conflicting inputs and safe accepted clock spellings. Wording/secret-filter categories are inapplicable because no filter changes.
- No test skips, native guard edits or security-policy bypass were introduced. Hosted/Windows cross-platform verification and independent review are not claimed.

## Deferred and next decision

See S10-PIT-CLOCK-ORDER-01-D001 in docs/deferred_items_log.md. Broader two-stage/source-admission work remains separate and blocked. Historical research can be re-evaluated only by a separately approved rerun; existing records/IDs are not rewritten.

Ready for review: NO. Review the one exact-head local ZIP first; subsequent PR publication, CI and merge remain Karl's decisions.
