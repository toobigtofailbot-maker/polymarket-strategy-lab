# S10-R3-SDK-DIRECT-01

RUNTIME/DETERMINISTIC, exact 8 paths, branch `codex/s10-r3-sdk-direct-01` from clean synchronized main `84c0c67e70470daf20eb1d4afdb126af61b3987d`.
- PR #274 is merged: head `6d9b1828c5591626c23fecf446175fa0003b3a96`, merge `84c0c67e70470daf20eb1d4afdb126af61b3987d`. Both are in main ancestry, and `origin/main` was exactly that merge at startup.
- PR #268 is open and untouched. Nothing is stacked on it and its expired fee policy is not used.
- Karl authorized bounded offline upstream-first implementation within the package scope, conditional on native readiness. No real public request, credential, dependency change, provider, Hermes, scheduler, paper, execution, live, capital or merge authority; merge stays Karl-only.

PR: see GitHub PR metadata and PR body.
Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable
and non-self-referential; it does not attempt to encode dynamic PR metadata or the SHA of the commit containing itself.

## Readiness

Package `SIDE24_S10_R3_SDK_DIRECT_01_CC_EXECUTION_PACKAGE.zip`: `SHA256SUMS.txt` verified for all 5 files (original prompt `5bac6037a47e750e1bcb7f4f9c6bf54d86fa7ab59aa1f8d5f098b0d76cf37d57`, spec `f229783cfd30c050b4886903ab485313204518563fbe3987de61c295617ccd6e`).

- On the original bytes, before any branch or source change, the native gate gave exit 1 `NOT_IMPLEMENTATION_READY` `READINESS_GOVERNANCE_TRACK_INVALID`: the track line carried trailing prose.
- Routine wording-only repairs within identical authority and scope:
  - the track line became exactly `Governance track expected: RUNTIME`, and its prose moved to a `Readiness basis:` line;
  - the missing mandatory matrix header row `RULE_ID|DOMAIN|SUBJECT|CONDITION|ACTION|CANONICAL_EFFECT|SPEC_PATH|EVIDENCE_ID` was added;
  - section 8 was retitled to carry the `report-back` signal.
- The intermediate re-gate gave `READINESS_PROMPT_STRUCTURE_INVALID` + `READINESS_RULE_MATRIX_INVALID`, both fixed by the last two repairs.
- Final prompt `2b55472989eb8f5d9dff4430a4aa1322ee1912a61523ff6e45a7c86533bb16dc`; spec unchanged. The committed prompt and spec are those exact bytes.
- Native gate on the final bytes, before branching: exit 0, `IMPLEMENTATION_READY`, RUNTIME/DETERMINISTIC, certificate_required=false, scope 8, 8 evidence items, 8 normative rules, error_codes empty. No certificate was required or issued.
- First invoked skill after mandatory startup reads: `ponytail` LITE. Also invoked: `wp-readiness-preflight` and `hermes-alpha-reuse-check` (no existing SDK search use; native `PolymarketPublicClient` has no search).

## Upstream source proof

- Installed `polymarket-client==0.10.0` (already pinned in `pyproject.toml` and the CI `WP174_DEPS`; no dependency change).
- `Polymarket/py-sdk` tag `polymarket-client-v0.10.0` resolves to commit `579bb2e56be9cc5d152546985870ee6ad795ec52`, license MIT; checked via the GitHub API (workflow network only).
- The git blobs of 11 installed SDK files equal the tag:
  - `clients/public.py` `abe091d1…`, `clients/_transport.py` `4c049727…`
  - dispatch, pagination, gamma actions, search/event/market models, `pagination.py`, `errors.py`, `version.py`
- `sdk_identity()` re-checks this on every run and verify.
- The upstream seam test `tests/unit/test_paginate_transport.py` blob `f2a608f0…` uses exactly the gamma `SyncTransport` + `httpx.MockTransport` + `dataclasses.replace` injection reused here.
- No SDK code copied. The R3 concept pin `aa94ec43…` is a different revision and is not used.

## Implementation

Contract: `docs/official_sdk_search_bridge_contract.md`. One finite offline operator, `tools/alpha/run_official_sdk_search.py` (`run`/`verify`), over `src/data_layer/analytical_research/official_sdk_search_bridge.py`.

- **Call path:** caller SRC-01 scratch, then the unedited `run_source_grounding.verify` (cold, before and after the frozen copy). Then the unedited `run_public_market_contract_parity._core` (EXT comparators, code identity preserved). Then, per frozen page, one real `PublicClient.search(...).first_page()` answered by `httpx.MockTransport` at `https://fixture.invalid`. Typed SDK `SearchResults`/`Event`/`Market` are crossed with the native identity rows. The result is one write-once `sdksearch:sha256:` receipt.
- **Fail-closed:** every socket entry point is blocked. One request per page; continuation cursors, redirects and second requests are refused.
- **Upstream gaps found in v0.10.0 and recorded (D002):**
  - `outcomes.yes` is positional (`outcomes[0]`), whatever its label says;
  - non-binary and malformed markets are dropped silently;
  - NaN and duplicate keys are accepted;
  - there are no exact-id or rule filters.
- **Gap containment:** the yes-slot label is recorded but never used, dropped markets are counted, native strict JSON refuses after the SDK call, and every market is `ORIENTATION_UNPROVEN`.
- **Compatibility:** SRC-01, EXT-CONTRACTS, alpha_discovery, PIT, polymarket adapter, Hermes, fee, CI, dependency and protected files are unedited.

## Outcome (frozen EXT-CONTRACTS-01 cases, label-blind SANITIZED_SYNTHETIC fixture pages)

The 60 EXT cases give 57 EXT-valid cases. 56 pages were submitted: 53 typed and projected, 1 `DUPLICATE_PAGE` and 2 `PAGE_CASE_NOT_PAIRED`. 4 exact-id-only cases are `CASE_NOT_SDK_SEARCHABLE`, leaving 53 paired cases (47 positive, 6 no-match).

| Measure | SDK fixture page | field_aware_search_v1 | rank_markets BM25 |
|---|---|---|---|
| Recall@10, 57 EXT-valid | 45/58 | 49/58 | 52/58 |
| Precision@10, 57 EXT-valid | 45/159 | 49/152 | 52/196 |
| Recall@10, 53 paired | 45/55 | 48/55 | 52/55 |
| Precision@10, 53 paired | 45/159 | 48/151 | 52/196 |
| Abstained, 53 paired | 3/53 | 11/53 | 8/53 |

SDK market rows: 185, of which 172 are identity-consistent, 7 not in the universe and 6 native-abstained. 3 markets were dropped by the SDK and 11 tags are unsupported.

The SDK rows only re-express the supplied fixture pages: this is not SDK retrieval quality and not lift. `lift_claim` is null, `real_value` is `NOT_VERIFIED` and `real_benchmark` is `NOT_RUN_REAL_DATA`. R3-23 is now `DIRECT_UPSTREAM_INTEGRATION_OFFLINE_PENDING_OWNER_VALUE`. R3-27 stays `CUSTOM_ADAPTED_IMPLEMENTATION`, owner acceptance pending. All 36 rows are tracked, with 0 value acceptances.

## Validation state

LOCAL_VALIDATION_PASSED. Validated implementation commit: `2ee0755`. Later commits on this branch change only this status fragment.

- **Full suite on `2ee0755`:** `python -B -m pytest -q -p no:cacheprovider --basetemp /tmp/full -ra` gave 14712 passed, 15 skipped, 0 failed (968s).
  - Image `s10-canary-siwc-validation:20261024`, Python 3.12.14, `polymarket-client` 0.10.0, httpx 0.28.1.
  - `--network none --read-only`, tmpfs `/tmp` and uid-1000 0700 HOME, disposable LF clone with real `origin/main` = `84c0c67`; no pull or install.
  - The skips are pre-existing environment gates: strict DuckDB, pinned Hermes checkout, gitleaks binary, frontend Node and native Windows cases.
- **Focused (Windows host):** `tests/tools/alpha/test_official_sdk_search.py` 8 passed (R001–R008). R007 exercises the symlink branch on Linux only (D005).
- **Native gate diff check** on `2ee0755` against `main`: exit 0 `IMPLEMENTATION_READY`, error_codes empty. **Exact scope:** `diff_scope_summary.py --require-exact-scope` pass, 0 warnings. **Generated-artifact guard:** passed.
- **Real-subprocess CLI smoke** outside the repository, on the committed fixture builders:
  - run → `RUN_COMPLETE` with 53 real SDK invocations; cold verify → `VERIFIED`; repeat → `IDEMPOTENT_VERIFIED`;
  - frozen-pages tamper → `TAMPER_DETECTED`; receipt tamper → `TAMPER_DETECTED` (`RECEIPT_ID_MISMATCH`, `OUTPUT_MISMATCH:authority`);
  - in-repository scratch → `SCRATCH_INSIDE_REPOSITORY`, nothing created; bad usage → exit 2; network attempts 0.

Exact-head hosted checks, evidence mode and the Ready decision belong in the PR body, not here.
