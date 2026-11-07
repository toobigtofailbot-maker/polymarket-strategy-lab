# Official SDK public search probe contract (S10-R3-REAL-PUBLIC-GET-01)

Status: Phase B pin (S10-R3-REAL-PUBLIC-GET-01B), not executed. `ACTUAL_LIVE_GET_EXECUTED=NO`.
Research only; no credentials, orders, strategy, paper, capital or live-trading authority.

## What it is

One manually invoked, finite probe around the installed upstream `polymarket-client==0.10.0`
(`Polymarket/py-sdk` tag `polymarket-client-v0.10.0`, commit `579bb2e56be9cc5d152546985870ee6ad795ec52`).
The SDK builds and parses the request; this repository only supplies the transport under it.

- Source: `src/data_layer/analytical_research/official_sdk_public_probe.py`
- Operator: `tools/alpha/run_official_sdk_public_probe.py` (`check`, `live`, `verify`)
- Reused unchanged: `official_sdk_search_bridge.sdk_identity`, `invoke_search`, `project_typed_page`,
  `_sdk_error_code`; `run_source_grounding.no_network` and `_strict_json`; `run_related_market_alpha`
  path guards; `public_market_contract_parity.normalize_native`; the S10-R3-SRC-01 cold verifier.

## The one request

`PublicClient.search(q="bitcoin", page_size=2).first_page()` produces exactly
`GET https://gamma-api.polymarket.com/public-search?q=bitcoin&page=1&limit_per_type=2`.

The `OneShotTransport` guard enforces at transport level:

| Bound | Value |
|---|---|
| Attempts | 1 total, counted before dialing; a failure is still the attempt |
| Method, scheme, host, port, path | `GET`, `https`, `gamma-api.polymarket.com`, 443, `/public-search` |
| Query | exactly `q=bitcoin`, `page=1`, `limit_per_type=2`; nothing else |
| Headers | only host, accept, accept-encoding (`identity`), connection, user-agent; no cookie or auth |
| Redirects, retries, pagination | refused; `follow_redirects=False`, `retries=0`, the continuation cursor is never followed |
| Proxy, environment | none; `trust_env=False` on client and transport |
| TLS | verified, hostname checked, HTTP/1.1, one connection |
| Body | at most 1 MiB read before the SDK parses; content encoding other than identity refused |
| Time | connect/read/write 4 s, pool 1 s; a read that could cross 15 s is not started; the## Activation (Phase A sealed; Phase B pinned by S10-R3-REAL-PUBLIC-GET-01B)

Phase A shipped `OWNER_ACTIVATION_SHA256 = None`. While it is `None`, `live` returns
`LIVE_ACTIVATION_SEALED` before reading any input or building any transport.

`live` requires one activation record (closed keys: `schema_id`, `wp_id`, `approved_by`, `attempt_id`,
`request_url`, `max_attempts`, `scratch_dir`, `not_before_utc`, `not_after_utc`, `envelope_sha256`) that
is byte-identical to the pin, with the exact URL, envelope and scratch directory, `max_attempts` 1 and
the current UTC time inside the window.

S10-R3-REAL-PUBLIC-GET-01B pins Karl's explicitly approved record:

| Field | Value |
|---|---|
| Raw record SHA-256 (`OWNER_ACTIVATION_SHA256`) | `a642058790796d4ec4de25c6b03003d0b0c0242c942a9b5c58843ddc4520634a` |
| `attempt_id` | `R3-SDK-PUBLICGET-20261107-01` |
| `scratch_dir` | `C:\Users\Public\Documents\polymarket-r3-sdk-one-get-20261107` |
| Window (UTC, inclusive) | `2026-11-07T00:00:00Z` .. `2026-11-21T23:59:59Z` |
| `envelope_sha256` | `110be3589860cc1e03f69eb41437941ea5685afb25109cd87cc53b722e82a3e9` |

The record file stays in the owner handoff package and is not committed. Changing any byte needs a new
owner approval and a new reviewed pin; an expired window is never extended locally.

The pin is a repository review control, not a cryptographic signature. A caller-created file, flag or
fixture never satisfies it. The `attempt_claimed.json` marker is local to one scratch directory: it
cannot stop a modified copy, another host or another scratch. The one-attempt limit is the owner's
operator-level agreement, not a global lock.

### Two-stage owner procedure

1. Karl reviews and merges the pin PR. A pin on an unmerged branch is not an execution grant. No test,
   CI job or review step runs `live`; every test uses an injected transport with sockets blocked.
2. Only after a deliberate post-merge instruction, one operator on the intended Windows host runs, once,
   from merged `main`:
   `python -B tools/alpha/run_official_sdk_public_probe.py live --scratch-dir "C:\Users\Public\Documents\polymarket-r3-sdk-one-get-20261107" --activation-record <absolute path to the exact owner record, outside the scratch>`
   then `verify` on the same scratch. A failed or timed-out attempt is still the one attempt; there is
   no retry, rerun, other host or other scratch under this approval.

 flag or
fixture never satisfies it.

## Freeze, receipt and replay

`live` claims the attempt (`attempt_claimed.json`, write-once) before dialing. It writes
`raw_response.bin` (bounded) and `receipt.json` (`sdkpublicget:sha256:` id) into one absolute scratch
directory outside the repository.

The receipt records:
- the exact envelope and its SHA-256, the SDK identity and the code identity;
- the outcome code, dials, HTTP status, content type, byte count and body SHA-256;
- UTC start and end and the monotonic duration;
- an offline SDK replay summary and the strict-JSON verdict.

It never stores raw headers, cookies, exception text, condition ids or response content.

Origin labels: `PUBLIC_TLS_TRANSPORT_OBSERVED` (real egress) or `TEST_INJECTED_TRANSPORT_NOT_PUBLIC`.
Content is always `REMOTE_CONTENT_NOT_INDEPENDENTLY_ATTESTED`. A TLS GET is not settlement, PIT or
source-quality evidence.

`verify` blocks every socket entry point. It replays the frozen bytes through the real SDK on
`httpx.MockTransport`, recomputes the receipt and reports `TAMPER_DETECTED` on any difference. Other rules:
- An identical repeat of `live` returns `IDEMPOTENT_VERIFIED` without network.
- A claimed attempt without a receipt is `ATTEMPT_ALREADY_CONSUMED`, never retried.

`verify --grounding-scratch` cold-verifies a caller-named S10-R3-SRC-01 scratch, read-only. It crosses
the SDK markets with the native identities and abstains on unknown markets, conflicts or a PIT snapshot
later than the acquisition. Orientation stays `ORIENTATION_UNPROVEN`, and there is no tradable side,
settlement equivalence or value claim. Without that scratch the result is `NATIVE_PIT_CROSSCHECK_NOT_RUN`.

## Refusal codes

| Stage | Codes |
|---|---|
| Activation | `LIVE_ACTIVATION_SEALED`, `ACTIVATION_FINGERPRINT_MISMATCH`, `ACTIVATION_RECORD_INVALID`, `ACTIVATION_SCOPE_MISMATCH`, `ACTIVATION_SCRATCH_MISMATCH`, `ACTIVATION_WINDOW_INVALID` |
| Paths and repeat | `SCRATCH_INSIDE_REPOSITORY`, `SCRATCH_INVALID`, `SCRATCH_NOT_EMPTY`, `ATTEMPT_ALREADY_CONSUMED`, `WRITE_ONCE_CONFLICT` |
| SDK identity | `SDK_NOT_INSTALLED`, `SDK_VERSION_MISMATCH`, `SDK_SOURCE_MISMATCH`, `SDK_METHOD_NOT_UPSTREAM` |
| Request guard | `METHOD_REFUSED`, `HOST_REFUSED`, `PATH_REFUSED`, `QUERY_REFUSED`, `HEADER_REFUSED`, `BODY_REFUSED`, `SECOND_REQUEST_REFUSED` |
| Response (attempt counted) | `REDIRECT_REFUSED`, `CONTENT_ENCODING_REFUSED`, `RESPONSE_OVERSIZE`, `TIME_BUDGET_EXCEEDED`, `SDK_RATE_LIMITED`, `SDK_REQUEST_REJECTED`, `SDK_PARSE_REJECTED`, `SDK_TRANSPORT_ERROR`, `TRANSPORT_FAILED` |
| Verify | `RECEIPT_UNREADABLE`, `RECEIPT_SHAPE_INVALID`, `RECEIPT_ID_MISMATCH`, `OUTPUT_MISMATCH:<field>`, `ACQUISITION_TIME_CONFLICT`, `NETWORK_ATTEMPT_BLOCKED` |

## Not in scope

No second request, other query, recurring acquisition, benchmark or lift claim. A single page proves
transport and SDK shape only. R3-23 is integrated directly upstream, but its operational and value
acceptance stays pending with the owner. No provider, Hermes, scheduler, dependency, PR #268, fee,
order or capital change.
