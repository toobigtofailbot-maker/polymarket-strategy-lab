# S10-R3-FORECAST-WP170-BIND-01

RUNTIME/Risk3, exactly 8 paths. Branch `codex/s10-r3-forecast-wp170-bind-01` cut from clean synchronized main
`c249409` (merge of PR #279, head `985bdb4`).

- PR #268 is open, separate and untouched.
- Karl's first-person bootstrap authorizes only this bounded offline implementation, conditional on the native
  readiness gate on the exact prompt/spec. Merge: NO (Karl only).

## Readiness

- Prompt SHA-256 `12f28028c7d7c846cb64dd62d5b7478c358e814daad6a9fb1abb718cc3cbf097`, spec SHA-256
  `2c6a44204192c2add21ecd48a1e5dbf5a2763650c62ac6cdbd1aa99648e61b18` (package `SHA256SUMS` verified). The committed
  copies under `docs/wp_specs/S10-R3-FORECAST-WP170-BIND-01/` are byte-identical.
- Native gate on those exact bytes before any source change: exit 0, `IMPLEMENTATION_READY`, RUNTIME,
  certificate_required=false, scope 8, 7 evidence items, 7 normative rules, readiness basis DETERMINISTIC.
- Startup reads first; Ponytail LITE was the first actually invoked skill.

## Implementation

Contract: `docs/forecast_evaluation_contract.md` (section "Per-case WP170 membership").

- **Reuse:** native `experiment_registry.load_and_verify_experiment_registry` (read-only), the registry's own
  `ResearchDatasetManifest.samples`, `TemporalSplitManifest` role sets and `experiment_os.membership_hash`. No new
  registry, split, OOS or sample logic; no registry write.
- **Identity checks (global stop):** manifest, dataset binding, feature set and label definition must agree across
  experiment, split and manifest; sample ids unique and counted; split sets a disjoint subset of the samples
  (`WP170_IDENTITY_MISMATCH` / `WP170_SPLIT_INVALID` / `WP170_SPLIT_NOT_FOUND` / `WP170_MANIFEST_NOT_FOUND`).
- **Per-case mapping:** exact `market_id` + `decision_time`, plus the case's cited native PIT metadata record
  version. Every offered target gets one outcome: `MAPPED` (with role), `UNMAPPED` (not found, decision-time
  mismatch, unproven provenance), `AMBIGUOUS` (several samples), or `REFUSED` (cross-market source, rule-version
  conflict, feature/label clock violations, outside every split role, purged, embargoed, event/leakage-group
  conflict). Labels are never read for mapping; cohort and scores are unchanged by binding.
- **Receipts:** new receipts are schema v2 with a `wp170.membership` block (counts by reason and role, membership
  hashes, `mapped_sample_ids_sha256`, `oos_release: NOT_RELEASED`, `run_evidence_receipt: null`). Verify is
  version-aware: historical v1 receipts are rebuilt in the v1 shape against the pinned original code identity
  `LEGACY_V1_CODE_IDENTITY` (the `c249409` code), so their identity and paired scoring still cold-verify; an
  unknown schema is recomputed as v2 and fails.
- **Legacy proof:** the tests extract the real `c249409` `src`/`tools` with `git archive`, run that old CLI in a
  subprocess to produce genuine v1 receipts, then cold-verify them with the new code; restamped, rescored and
  relabelled forgeries are detected. The pin equals the hash of the `c249409` blobs.

## Outcome (SANITIZED_SYNTHETIC grounding, test-built WP170 registries)

- Exact-binding fixture: 2 mapped, 1 ambiguous, 6 refused, remainder unmapped, every reason counted.
- No value, OOS, qualification or performance claim. `NOT_VALUE_VERIFIED` (deferred D001).
- Adoption rows, the 36 commitments, six owner-gated pilots and Lane B are unchanged.

## Limitations

See `docs/deferred_items_log.md` section "S10-R3-FORECAST-WP170-BIND-01 deferred items" (D001-D005):
synthetic only; pre-`43e3d94` v1 receipts were already unverifiable and stay so; LEARN-01 still accepts only the
current forecast code identity; no rule hash in `ResearchSample`; the legacy tests need full Git history.

## Validation state

Validation commands and results are recorded in the PR body. Exact-head hosted checks, evidence mode and the
Ready decision belong in the PR body.
