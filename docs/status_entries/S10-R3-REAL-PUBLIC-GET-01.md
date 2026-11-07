# S10-R3-REAL-PUBLIC-GET-01

RUNTIME/DETERMINISTIC, exact 8 paths, branch `codex/s10-r3-real-public-get-01` from clean synchronized main `72d077cf3f3be6bd29df9d29a2c74299d3b46509`.
- PR #275 is merged: head `0f6ad340194c2b3cbf6ac5ddc6c78a78e34df534`, merge `72d077cf3f3be6bd29df9d29a2c74299d3b46509`. Both are in main ancestry, and `origin/main` was exactly that merge at startup.
- PR #268 is open and untouched; nothing is stacked on it. No other same-WP PR or branch existed.
- Karl authorized **Phase A only**: dormant bounded code, offline proof and one PR. **Phase B (any real product GET) is not authorized**; it needs Karl's separate exact instruction after merge. No credential, dependency, provider, Hermes, scheduler, paper, execution, live-trading or capital authority. Merge NOT authorized; merge stays Karl-only.

`ACTUAL_LIVE_GET_EXECUTED=NO`. No real public request was made while implementing, testing, running CI or preparing the PR.

PR: see GitHub PR metadata and PR body.
Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable
and non-self-referential; it does not attempt to encode dynamic PR metadata or the SHA of the commit containing itself.

## Readiness

Package `SIDE24_S10_R3_REAL_PUBLIC_GET_01_CC_EXECUTION_PACKAGE.zip` (sha256 `8b7eb001b8a05f4f862ba5b65071771aeeb278e7757551b3ebafb1ef09c0f781`): `SHA256SUMS.txt` verified for all 5 files. Original prompt `cb5c159bb3c7e486555e53a1ca966f27d7218937f408fbd0360b48a3636e2ca8`, spec `f9aa2f969675a97fa7dc8296cdfe48434092b95060b208c0b4d0e9c0853c1b35`.

- On the original bytes, before any branch or source change, the native gate gave exit 1 `NOT_IMPLEMENTATION_READY` with `READINESS_PROMPT_STRUCTURE_INVALID` + `READINESS_RULE_MATRIX_INVALID`.
- One batch of wording-only repairs, within identical authority, scope and owner network non-activation (the same class SDK-DIRECT-01 repaired):
  - the missing mandatory matrix header row `RULE_ID|DOMAIN|SUBJECT|CONDITION|ACTION|CANONICAL_EFFECT|SPEC_PATH|EVIDENCE_ID` was added;
  - section 7 was retitled `Normative rule matrix, evidence plan and report-back` to carry the `report-back` signal.
- Final prompt `a079461fef30b9c64ee115a15929404135537ba9f91a99c6558871d7e91ec03c`; spec unchanged. The committed prompt and spec are those exact bytes.
- Native gate on the final bytes, before branching: exit 0, `IMPLEMENTATION_READY`, RUNTIME/DETERMINISTIC, certificate_required=false, scope 8, 8 evidence items, 8 normative rules, error_codes empty. No certificate was required or issued.
- First invoked skill after mandatory startup reads: `ponytail` LITE. The other real invocations are listed in the return ZIP skill ledger.

## Upstream source proof

- Installed `polymarket-client==0.10.0` and httpx 0.28.1, both already present; no dependency change.
- `OSB.sdk_identity()` (unchanged from SDK-DIRECT-01) re-checks on every `check`, `live` and `verify`: the distribution version, the git blobs of 11 installed SDK files against tag `polymarket-client-v0.10.0` commit `579bb2e56be9cc5d152546985870ee6ad795ec52`, and that `PublicClient.search` is the upstream function.
- `PublicClient.search(q="bitcoin", page_size=2).first_page()` dispatches through `sync_paginate_page_based` straight to `SyncTransport.get_json`. It produces exactly `GET https://gamma-api.polymarket.com/public-search?q=bitcoin&page=1&limit_per_type=2`.
- This path has no SDK rate-limit retry (`run_with_rate_limit_retry` is only on the non-paginated dispatch).
- No SDK code copied, no search algorithm added.

## Implementation

Contract: `docs/official_sdk_public_probe_contract.md`. Operator `tools/alpha/run_official_sdk_public_probe.py` (`check`/`live`/`verify`) over `src/data_layer/analytical_research/official_sdk_public_probe.py`.

- **Transport seam:** the same `SyncTransport(client=httpx.Client(...))` + `dataclasses.replace(_ctx, gamma=...)` injection SDK-DIRECT-01 uses. The client is set with `trust_env=False, follow_redirects=False`, 4/4/4/1 s timeouts and `accept-encoding: identity`.
- **`OneShotTransport` guard:**
  - lets one request reach the inner transport, and only for the exact method, scheme, host, port, path, query and header set;
  - counts the dial before it happens;
  - refuses 3xx, non-identity encoding and bodies over 1 MiB, measured before the SDK parses;
  - never starts a read that could cross the 15 s wall.
- **Real egress:** `httpx.HTTPTransport(verify=True, trust_env=False, http2=False, retries=0, proxy=None)` with one connection. The attempt runs in a daemon worker that is abandoned at 15 s + 1 s, which bounds DNS and stalls (D004).
- **Activation:** `OWNER_ACTIVATION_SHA256 = None`. `live` refuses `LIVE_ACTIVATION_SEALED` as its first statement, before reading input or building a client or transport. Phase B needs a reviewed, owner-merged pin of one exact activation record that binds URL, envelope, one attempt, scratch directory and UTC window. This is a review control, not a signature (D002).
- **Freeze:** the attempt is claimed write-once before dialing. `raw_response.bin` and a `sdkpublicget:sha256:` receipt are then written into one external scratch directory. The receipt records:
  - the envelope, SDK and code identities;
  - the outcome, dials, status, content type, byte count and SHA-256;
  - UTC start and end and the monotonic duration;
  - the SDK replay summary and the strict-JSON verdict.

  It holds no headers, cookies, exception text, condition ids or content. Origin is `PUBLIC_TLS_TRANSPORT_OBSERVED` (real egress) or `TEST_INJECTED_TRANSPORT_NOT_PUBLIC`; content is always `REMOTE_CONTENT_NOT_INDEPENDENTLY_ATTESTED`.
- **Verify:** every socket entry point is blocked. The frozen bytes replay through the real SDK via `OSB.invoke_search` on `httpx.MockTransport`, and the receipt is recomputed. An identical repeat of `live` is `IDEMPOTENT_VERIFIED` without network; a claimed attempt without a receipt is `ATTEMPT_ALREADY_CONSUMED`.
  - `--grounding-scratch` cold-verifies an SRC-01 scratch read-only and crosses SDK markets via `PMC.normalize_native` and `OSB.project_typed_page`. Orientation stays `ORIENTATION_UNPROVEN`, with no tradable side and no settlement or value claim.
  - Without that scratch the result is `NATIVE_PIT_CROSSCHECK_NOT_RUN`.
- **Compatibility:** SRC-01, EXT-CONTRACTS-01, SDK-DIRECT-01, PIT, `src/data_layer/polymarket/`, `tools/polymarket/`, Hermes, fee, CI, dependency and protected files are unedited.

## Adoption boundary

All 36 R3 rows stay tracked, with 0 owner value acceptances. R3-23 is `DIRECT_UPSTREAM_INTEGRATED_OPERATIONAL_VALUE_PENDING_OWNER`, and the receipt records `benchmark: NOT_RUN_SINGLE_PAGE` and `lift_claim: null`. R3-27 CCXT, Hermes, Oracle3, provider lanes, parity candidates, Lane B and PR #268 are unchanged. Deferred: D001-D004.

## Validation state

LOCAL_VALIDATION_PENDING.

Exact-head hosted checks, evidence mode and the Ready decision belong in the PR body, not here.
