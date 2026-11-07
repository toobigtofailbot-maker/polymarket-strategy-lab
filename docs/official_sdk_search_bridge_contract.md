# Official SDK public search bridge contract (S10-R3-SDK-DIRECT-01)

Posture: `OFFLINE_RESEARCH_ONLY`, `DIRECT_UPSTREAM_SDK_METHOD_INVOKED_ON_FIXTURE`, `SOURCE_ORIGIN_UNVERIFIED`,
`REAL_VALUE_NOT_VERIFIED`, `NO_PROVIDER_OR_TRADING_AUTHORITY`. Research only. No real network request,
credential, authenticated method, provider, Hermes, scheduler, order, strategy, paper, capital or live
authority. Merge stays Karl-only.

## What is reused, not rebuilt

| Piece | Source | Use |
|---|---|---|
| `PublicClient.search(q=..., page_size=...).first_page()` | installed `polymarket-client==0.10.0` (already pinned in `pyproject.toml`) | the real SDK method builds the request, decodes JSON, handles status, paginates and returns typed `SearchResults` |
| Offline seam | upstream `tests/unit/test_paginate_transport.py` (blob `f2a608f025c2eb74c4d1d49365541c86ab188d81`) | `SyncTransport(client=httpx.Client(transport=httpx.MockTransport(handler)))` placed in `client._ctx.gamma` with `dataclasses.replace` |
| SRC-01 verify, PIT corpus, rule binding, BM25 | `tools/alpha/run_source_grounding.py`, `source_grounding.py`, `alpha_discovery.py` | unchanged; caller scratch cold-verified before and after the frozen copy |
| Native identity table, field-aware search, labelled cases | `public_market_contract_parity.py`, `tools/alpha/run_public_market_contract_parity.py::_core` (PR #274) | called unchanged, so the EXT code identity and receipts are preserved |

Upstream: `Polymarket/py-sdk` tag `polymarket-client-v0.10.0`, commit
`579bb2e56be9cc5d152546985870ee6ad795ec52`, MIT. `sdk_identity()` requires the installed distribution
version `0.10.0` and the git blob of 11 installed SDK files (`clients/public.py`
`abe091d10ba65132e0674605c6a48023b0317bff`, `clients/_transport.py`
`4c049727d7f2f3c7ab656872c4a54863ac240d4c`, dispatch, pagination, gamma actions and the search,
event and market models) to equal the tag. `PublicClient.search` must be the function defined in that
`public.py`. Otherwise the run stops (`SDK_VERSION_MISMATCH`, `SDK_SOURCE_MISMATCH`,
`SDK_METHOD_NOT_UPSTREAM`). The R3 concept pin `aa94ec431e3d4946576fb7c0d079fe1c14fcf676` is a
different revision and is not used. No SDK code is copied. Only `PublicClient.search` is invoked; no
`SecureClient`, auth, order or signing name is imported.

## Operator

```
python -B tools/alpha/run_official_sdk_search.py run --grounding-scratch DIR --ext-cases CASES.json --sdk-pages PAGES.json --scratch-dir DIR
python -B tools/alpha/run_official_sdk_search.py verify --scratch-dir DIR
```

Caller-named absolute local files only, with the merged path guards (symlink, hardlink, reparse, alias,
`..`, secret-shaped directory, inside-repository and size caps: cases 1 MiB, pages 8 MiB, page body
256 KiB, 500 pages). Every socket entry point is blocked. The scratch is one empty absolute directory
outside the repository, written once: `inputs/grounding/`, `inputs/cases.json`, `inputs/sdk_pages.json`,
`receipt.json`. An identical repeat returns `IDEMPOTENT_VERIFIED`; different bytes refuse
`SCRATCH_NOT_EMPTY`. `verify` re-invokes the real SDK on the frozen bytes, recomputes every output and
writes nothing.

## Pages file (`s10-r3-sdk-direct01-pages-v1`)

`{schema_id, corpus_class, ext_benchmark_sha256, source_label: "LOCAL_FIXTURE_UNAUTHENTICATED",
sdk: {distribution: "polymarket-client", version: "0.10.0"}, pages: [...]}`. `corpus_class` and
`ext_benchmark_sha256` must equal the EXT cases file, which binds the pages to the frozen labelled cases.
Each page is `{case_id, captured_at, request, response: {status, content_type, body_b64}}`. Requests use
only the SDK keywords `q`, `page_size` (1-10), `events_status`, `events_tag`, `search_tags`,
`search_profiles`, and `q`/`events_status`/`events_tag` must equal the case query. Strict JSON
throughout; credential-shaped keys or values anywhere, including inside decoded bodies, stop the run.

## Per-page outcome (first failure wins)

`PAGE_FIELDS_INVALID`, `DUPLICATE_PAGE`, `PAGE_CASE_NOT_PAIRED` (not an EXT-valid case),
`REQUEST_PARAMETER_UNSUPPORTED`, `REQUEST_INVALID`, `REQUEST_CASE_MISMATCH`, `SOURCE_POST_CUTOFF`
(`captured_at` later than the snapshot `as_of`), `PAGE_OVERSIZE`. These are refused before the SDK runs.
Then the SDK is invoked once: `SDK_PARSE_REJECTED`, `SDK_REQUEST_REJECTED`, `SDK_REDIRECT_REFUSED`,
`SDK_RATE_LIMITED`, `SDK_INPUT_REJECTED`, `MOCK_TRANSPORT_NOT_REACHED`, `SECOND_REQUEST_REFUSED`,
`SDK_REQUEST_SHAPE_UNEXPECTED`. Then `STRICT_JSON_REJECTED` (the SDK accepts NaN and duplicate keys; the
native strict check does not), `SDK_TYPED_RESULT_INVALID`, `PAGE_CONTINUATION_REFUSED` (the cursor is
never followed), and finally `SDK_TYPED_PAGE_PROJECTED`.

Projection reads only SDK-typed `Event`/`Market` objects. Each SDK market is
`IDENTITY_CONSISTENT`, `MARKET_ID_NONCANONICAL`, `NOT_IN_UNIVERSE`, `NATIVE_IDENTITY_ABSTAINED`,
`CONDITION_ID_CONFLICT`, `OUTCOME_TOKEN_CONFLICT`, `DUPLICATE_MARKET` or `EVENT_RELATION_CONFLICT`. A Gamma
event id is `EVENT_ID_UNVERIFIED` unless it equals the native event id. Every market is
`ORIENTATION_UNPROVEN` with no tradable side. Markets the SDK silently dropped are counted from the raw
page (`sdk_dropped_markets`), never hidden. Tags and profiles are counted, not projected.

## Upstream gaps observed in v0.10.0

- `Market.outcomes.yes` is `outcomes[0]` positionally, whatever its label says (a `["No","Yes"]` market
  puts "No" in the yes slot). It is recorded as `sdk_yes_slot_label` and never used as orientation.
- Non-binary and malformed markets are dropped from `Event.markets` without an error.
- NaN and duplicate JSON keys are accepted.
- Search has no exact-id, rule-presence or resolution-date filter, so exact-id-only cases are
  `CASE_NOT_SDK_SEARCHABLE`.

## Comparison and receipt

The same EXT-valid cases are scored for the SDK page projection, the merged field-aware search and the
merged R3-02 BM25 with `source_grounding._method_metrics`. Two scopes: all EXT-valid cases, and the cases
whose page reached `SDK_TYPED_PAGE_PROJECTED`. Below 50 paired cases there are no metrics
(`PAIRED_BENCHMARK_REFUSED`). Supplied-page coverage (`identity_consistent_rate`,
`labels_present_in_page`, drops) is reported apart from ranking. SDK rows only re-express what the
caller's pages contain: this is not SDK retrieval quality and `lift_claim` is null. Without a genuine
caller real corpus, `real_benchmark` is `NOT_RUN_REAL_DATA`.

The receipt id `sdksearch:sha256:` covers the deterministic core: SDK identity, input file hashes, the EXT
core receipt id and code identity, every page row with its request, body hash and SDK verdict, and the
comparison. Wall-clock SDK time and peak traced memory sit beside the core as `measurements`
(`reproducible: false`). Verify checks their shape and bounds only.

## Adoption state (all 36 capability rows tracked)

R3-23 advances only to `DIRECT_UPSTREAM_INTEGRATION_OFFLINE_PENDING_OWNER_VALUE`. Operational value and
Karl acceptance stay pending. R3-27 stays `CUSTOM_ADAPTED_IMPLEMENTATION` with owner acceptance pending;
CCXT direct reuse is a separate decision. The other 34 rows are unchanged. There is no parity
auto-acceptance, and PR #268 stays separate and unconsumed.

Successor: `S10-R3-REAL-PUBLIC-GET-01`. A real credentialless Gamma GET through the same SDK method needs
its own exact owner approval: host, path, request count, byte and time caps, redirect and retry policy,
and provenance. That approval is not granted here.
