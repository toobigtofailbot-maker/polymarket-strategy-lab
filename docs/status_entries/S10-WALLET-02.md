# S10-WALLET-02 — PIT Wallet Profiles, Skill, Specialization, Archetypes and Cohorts

Status: IMPLEMENTATION COMPLETE (final local committed-head validation complete; hosted CI
and live PR evidence are recorded only in the PR body)

PR: see GitHub PR metadata and PR body.
Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable
and non-self-referential; it does not attempt to encode dynamic PR metadata or the SHA of
the commit containing itself.

Ready for review: see the current PR body after exact-head hosted CI and live evidence
verification. This stable fragment does not predict mutable GitHub state.
Merge authorized: NO.

## Frozen base and scope

- Base/main and PR #189 merge SHA: `45b6cb4db7fc5e8ac2ae21145bf00be658740025`.
- Required predecessor implementation head: `bf346a65cf1b93b5e61d2420a8da1629be2bd191`.
- Branch: `codex/s10-wallet-02-pit-profile-snapshots`.
- Governance track: FAST; Risk level: 2; exact scope: 17 required = 17 allowed paths.
- Evidence mode expected: `PRIVATE_REPO_MANUAL_VERIFIED`.
- Negative matrix required: YES. N01-N15 are executable in the focused profile suite and
  cover missing/null/wrong-type/empty fields, future PIT evidence, forbidden/unknown
  fields, binary floats, malformed mappings, duplicate/conflicting inputs, safe descriptive
  wording, reconciliation, survivorship, identity, and authority boundaries. Credential-
  token and spelling-variant wording scans are not applicable because this WP adds no
  free-form semantic wording filter.

## Delivered

- Frozen content-addressed `WalletProfileMarketContext`,
  `WalletDiscoveryCohortSnapshot`, and `WalletProfileSnapshot` records.
- Verified read-only WALLET-01 ledger loading with exact ledger-head binding.
- Shared PIT admissibility, reconciliation-aware canonical selection, explicit exclusion
  evidence, and PIT-safe public-account clustering.
- Independent-group sample evidence; exact Decimal/Jeffreys shrinkage; descriptive
  specialization; direct-evidence archetypes; strict no-float mapping round trips.
- WP79 retained as non-canonical fixture-era compatibility history; WALLET-03/04 ownership
  unchanged.

## Authority and residual limits

Product wallet/market network calls: 0. Hermes/provider/model calls: 0. H1 #5: NOT
AUTHORIZED. Credential/private-key operations: 0. Qualification/strategy/paper/live/order/
signing operations: 0. Capital at risk: USD 0. Gate C: NOT AUTHORIZED. Profile database:
NONE. Dependency/lock/workflow/tool delta: 0.

Exact empirical minimum-n, HHI, posterior, promotion, and cluster thresholds remain
deferred. Copyability economics remain WALLET-03; incremental-value evidence remains
WALLET-04. After separate review and merge, the next package is S10-ALPHA-02.

## Validation summary

- Preimplementation readiness: `IMPLEMENTATION_READY`; FAST; exact scope 17.
- `python -m pytest -q tests/data_layer/wallet_intelligence/test_profile.py` -> 15 passed.
- `python -m pytest -q tests/data_layer/wallet_intelligence tests/data_layer/point_in_time_market_research/test_research_provenance.py` -> 152 passed.
- `python -m pytest -q tests/test_project_status_docs.py tests/test_repo_truth_docs.py tests/test_wallet_intelligence_architecture_contract_docs.py tests/test_wallet_intelligence_roadmap_docs.py` -> 308 passed.
- Historical architecture/complete-diff guard command from the WP -> 221 passed.
- `python tools/git/preflight_generated_artifact_guard.py` -> passed.
- Security runner -> gitleaks PASS; semgrep PASS; pip-audit PASS; npm/cargo audits
  SKIPPED_NOT_APPLICABLE.
- Exact-scope helper -> 17 required, 17 actual, 0 missing, 0 extra, 0 warnings.
- Final readiness `--check-diff` -> `IMPLEMENTATION_READY`; 25 evidence items; 17 rules.
- `python -m pip check` -> no broken requirements; committed diff check -> clean.
- `python -m pytest -q` -> 11,663 passed, 4 skipped, 124 warnings.
- Exact-head hosted CI, PR evidence guard, and `PRIVATE_REPO_MANUAL_VERIFIED` live evidence:
  see the current PR body; not duplicated into this stable fragment.
