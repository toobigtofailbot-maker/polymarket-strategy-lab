# S10-ALPHA-NEAR-TERM-02 scratch research contract

RUNTIME/risk 3; seven paths only. Karl authorized implementation, offline validation
and PR publication, not acquisition, providers, account access or activation.
`docs/wp_specs/S10-ALPHA-NEAR-TERM-02/` contains the byte-exact governing package.
The Centralized Boundary Group Reference in `docs/ai/codex/PROTECTED_PATHS.md`
remains authoritative. This tool creates no PIT/Alpha registry or execution intent.

## Commands and limits

`python -B tools/alpha/run_near_term_market_screener.py run --scratch-dir ABS`
and `verify --scratch-dir ABS`. There are no other options, clock override,
provider flags or configurable endpoints. Tests inject clock/transport into `run`.
Scratch is an absolute new/empty directory outside the checkout, with no symlink
or reparse components. One operation only; no resume, retry, overwrite or repair.
The nearest existing ancestor is also resolved before writes, so Windows trailing
dot/space or short-name aliases cannot disguise the checkout as external scratch.

Discovery uses the fixed Gamma `/markets` query, in order: `closed=false`,
`end_date_min=<captured as_of UTC>`, `end_date_max=<as_of+7200s UTC>`,
`limit=100`, `offset=N`, offsets0..1900 in steps100. `urlencode` percent-encodes
the RFC3339 UTC instants; local strict time validation remains authoritative. First short/empty, failed/invalid or repeated full page
stops discovery. Twenty full pages mean COVERAGE_TRUNCATED. There is no server
sort, active/category filter or alternative endpoint. Server time filters are
unverified discovery assistance, not an assertion of source completeness. At most ten locally
prioritized binary CTF markets and twenty numeric-token `/book` reads follow;
both tokens are ordered numerically. The finite plan uses at most forty GETs,
with an independent hard ceiling of 64. Each body is <=2MiB, socket timeout
<=15s and monotonic acquisition budget 240s. Budget is checked before each read;
one in-flight socket read may overrun its deadline by at most its timeout.
Redirects, proxy discovery, arbitrary headers, HTTP mutation and retries refuse.
Raw source decoding reuses the native depth/node/string bounds unchanged.
Before canonicalization, every decoded Decimal must have at most 64 digits and
adjusted exponent in [-64,64]; every string must encode as UTF8. Violations are
SOURCE_INVALID with bounded raw bytes retained. This additional scalar gate avoids
fixed-point expansion or lone-surrogate failures; native parser limits stay unchanged.

## Time, categories and mechanics

Only explicit timezone-aware full `endDate` timestamps are parsed, to integer
nanoseconds (at most six fractional digits). `0 < end-as_of <=7200s` is the
IN_WINDOW bucket / END_TIME_IN_120M_METADATA_ONLY classification. No event start,
date-only value, title or timezone inference substitutes. End metadata is not
resolution or settlement proof. Local rank is `end_ns`, preserving captured order for ties; no numeric secondary candidate selection.
Every row is retained: out-of-window timestamps receive FILTER_MISMATCH;
missing/malformed time receives UNKNOWN. Both make the assessment incomplete.
HTTP4XX discovery refusal records FILTER_CONTRACT_UNVERIFIED, without retry.

Every observed top-level category is counted. Valid strings <=128 characters
are SHA256-keyed by their canonical original JSON value; known case-folded fee
categories have fixed labels and others OPAQUE_CATEGORY. Absent/malformed values
are UNKNOWN with malformed counts. Category names/questions never reach stdout.
Identical repeated IDs count once; conflicting IDs retain the first source
pointer, exclude mechanics and count PAGE_CONFLICT. Raw rows retain all evidence.
Malformed IDs are null with source pointers and stay in unknown denominators.

Recognized CTF means a valid binary numeric token pair and condition, no native
Hunter V2 marker, and no explicit unknown/version contradiction. Native Gamma
and CLOB normalizers bind identity again. V2, unknown/nonbinary identity and
neg-risk remain unassessed/inconclusive, not a category exclusion from capture.
Only observed active/accepting/book-enabled and closed=false rows are shortlisted.

Fee policy `documented-fees-20261028-near-term-02` uses the frozen category table and
expires 2026-11-04T00:00:00Z. It is an assumption-bound upper fee check, not an
observed fee charge. Unmapped/contradictory/expired fee evidence is FEE_UNKNOWN, even with Gamma zero.
An absent/null category alone has the narrow documented fallback below; malformed
or unrecognized strings never become a category or a fallback class. Native `size_order`/`fee_max` retain USD2..5,
separate Gamma USDC and CLOB share minima, .01 shares and .01 USDC SDK narrowing.
Native depth refusal is inconclusive. TimeoutError (including URLError wrapping
one) becomes TIMEOUT; other connection/TLS/DNS errors remain
TRANSPORT_UNAVAILABLE without inferring their root cause. No exception text echoes. Stale/future (>30s or negative age), unknown
fee, invalid tick/identity/delay or unsupported state take precedence over a
minimum arithmetic rejection. Only all dimensions PASS yields
MECHANICALLY_POSSIBLE_WITH_BOUNDED_ASSUMPTIONS. No forecast, edge, fill probability,
permit, StrategyVersion, ExecutionIntent or actual economics is created.

## Frozen record schemas (before source implementation)

All records use schema_version `near-term-market-screen@2.0.0`; JSON is strict
UTF8, duplicate/nonfinite-free, sorted-key compact encoding with explicit nulls.
Raw payload digests cover exact bytes. Extracted Gamma object digest covers its
derived canonical representation, separately bound to original page/index.

| Record | Exact fields |
|---|---|
| config | schema_version, page_limit, page_cap, market_cap, book_cap, request_cap, max_body_bytes, socket_timeout_s, acquisition_budget_s, window_s, book_age_s, fee_policy_version |
| started | schema_version, as_of_utc, as_of_ns, started_monotonic_ns, config_sha256 |
| request STARTED | schema_version, request_index, endpoint_kind, url, started_utc, started_monotonic_ns |
| receipt | schema_version, request_index, endpoint_kind, url, started_utc, received_utc, started_monotonic_ns, received_monotonic_ns, status_class, body_state, raw_file, raw_sha256, byte_count |
| manifest | schema_version, config_sha256, started_sha256, as_of_utc, mechanics_evaluated_ns, fee_policy_version, sources, coverage, categories, markets, tokens, summary |
| source reference | request_index, receipt_sha256, raw_sha256 |
| coverage | pages_requested, available, unavailable, invalid, raw_rows, unique_ids, identical_duplicates, conflicting_ids, stop_reason, external_universe_completeness, status_counts, protocol_counts, time_counts, selection_counts, book_counts, filter_counts, fee_method_counts |
| category | category_key, label, market_count, malformed_count |
| market | market_id, source_request_index, source_row_index, category_key, protocol_state, status_state, time_state, end_time_utc, selection_state, reason_codes, filter_state, category_origin |
| token | market_id, token_id, outcome_index, source_request_index, state, first_reason, dimension_codes, gamma_notional_min_usd, clob_min_shares, best_ask, best_ask_depth_shares, gamma_tick, clob_tick, seconds_delay, book_timestamp_ns, age_ns_at_evaluation, fee_rate_bound, fee_exponent, shares, principal_usd, fee_bound_usd, all_in_usd, sdk_grid_state, derived_gamma_sha256, fee_method, fee_class, fee_policy_expiry_utc |
| summary | assessment, category_count, market_count, in_window_count, selected_market_count, unacquired_market_count, book_count, fresh_book_count, possible_count, minimum_failure_count, inconclusive_count, resolution_within_120m_confirmed_count, external_universe_completeness, claim |
| terminal / run stdout | schema_version, status, error_codes, manifest_sha256, summary |
| index | operation, terminal_sha256 |
| verify stdout | schema_version, status, error_codes, manifest_sha256, verified_operation_count, network_attempts, provider_dispatches |

Nested bucket keys are exact: status ACTIVE/INACTIVE/UNKNOWN; protocol
CTF/V2/UNKNOWN; time MISSING/MALFORMED/DATE_ONLY/TIMEZONE_MISSING/EXPIRED/
FUTURE_OUTSIDE/IN_WINDOW; selection SELECTED/NOT_ACQUIRED/INELIGIBLE; book
AVAILABLE/FRESH/STALE/INVALID/UNAVAILABLE/NOT_ACQUIRED. Protocol UNKNOWN includes
nonbinary or invalid token/condition identities. SDK state UNKNOWN/PASS/FAIL.
Dimension keys are identity, freshness, status, tick, delay, fee, minimum, depth,
sdk_grid. Values PASS/FAIL/UNKNOWN. Body states AVAILABLE/UNAVAILABLE/INVALID/
OVERSIZE. Endpoint kinds DISCOVERY/BOOK; HTTP status classes HTTP_2XX/HTTP_4XX/
HTTP_5XX/REDIRECT_REFUSED/TIMEOUT/TRANSPORT_UNAVAILABLE/OVERSIZE. Failure codes are closed
implementation constants, never source strings. Missing numeric outputs are null.
All fields are recursively scanned; verified numeric IDs, hashes, typed counts,
booleans, enum strings and canonical decimal strings are type-checked exemptions.
Raw vendor bodies, arbitrary descriptions, exception text and unknown keys are
forbidden on structured surfaces. R006/R007 enforce exact field coverage,
recursive no-echo and invalid-output behavior.
A hand-built dictionary is not a full output-surface scan unless a field-coverage test
proves it covers every public field. The contract table independently freezes field
coverage in the tests; all containers and strings are SCANNED, typed int/bool/null
leaves are EXEMPT because they cannot echo source text. Every unclassified field,
free-form source key/value or raw body on these surfaces is FORBIDDEN.

## Evidence graph and replay

Root: config.json, op-000001/, index-op-000001.json. Operation: started.json,
request-NN.started.json, receipt-NN.json, optional raw-NN.bin, manifest.json,
terminal.json. NN=01..64, contiguous request identities. Exclusive creation;
files are bounded regular non-reparse files. No unknown paths or directories.
Manifest binds config, started and ordered receipts/raw hashes; terminal binds
manifest; index binds terminal. No self-reference. Equal bytes on distinct valid
request indices retain distinct files and provenance; equal hashes alone do not
mean corrupt evidence. A repeated full discovery page at a different offset does
trigger the independent pagination-churn rule.

Verify reconstructs selected URLs, source states, row classifications, numeric
mechanics, all denominators and terminal using the recorded cutoff/evaluation
clock. It validates source and request consistency and rejects modified, missing,
extra, noncanonical or forged-derived fields. A hard-killed incomplete run is
rejected, never repaired. Entire-evidence replacement/deletion cannot be detected
without an external retained hash: scratch is not an authenticated audit ledger.
Sequential request intervals cannot overlap. A receipt may overrun a per-request
read deadline by one socket timeout: at most 30s total per request and no receipt
later than 255s after operation start. These are replay ceilings, not retry authority.

COMPLETED with EVIDENCE_INCOMPLETE is a truthful partial operation, not a full
world observation. Any source/coverage conflict/truncation, in-window unknown or
unacquired candidate causes incomplete summary. Universe completeness is always
UNPROVEN; confirmed resolution count is always zero. Replay creates no current
eligibility claim and performs no network, provider or canonical-registry writes.

## Negative matrix and validation

R001 pagination/caps/dedup/category cases; R002 0/1/7200/7201-second and malformed
time cases; R003 source statuses, redirected/oversize/malformed/duplicate-key,
nonfinite/type/null/empty inputs and deadline refusals; R004 positive native
mechanics, two minimum units, depth/tick/delay/unknown fee/version/staleness and
SDK narrowing; R005 category/time/protocol/status/capacity accounting; R006
tamper, missing/extra/reparse/raw/receipt/index/manifest cases and cold replay;
R007 forbidden operation guards, exact fields and output no-echo. Free-text
wording filters are not added: policy spelling/case categories13/14 are N/A;
payload metadata never becomes an output string. Case-folded fee-category
matching has a positive fixture, and unknown spellings remain unknown.

Required focused/adjacent, security, exact-spec/diff/readiness, authoritative full
suite and independent combined implementation review remain mandatory. PR body
owns exact-head CI and posted evidence; stable fragment never fixes its own PR
head. No source guard waiver or eighth-file change is allowed.


## Narrow fee-class provenance (R002)

Official public sources inspected during drafting:
- https://docs.polymarket.com/trading/fees : highest **listed categorical** rate0.07;
  share-based curve. This is not a universal protocol maximum.
- https://docs.polymarket.com/market-data/market-details : Gamma feesEnabled and
  feeSchedule rate/exponent/takerOnly/rebateRate semantics; Gamma minimum is USD.
- https://github.com/Polymarket/py-clob-client-v2/blob/394ecc18ab9ab20b48095b0b5c5de0042bdd6bb3/tests/test_fee_calculations.py#L334 :
  production fixture explicitly maps politics_fees to0.04/exponent1. The same
  source has crypto_fees_v2 at0.072, demonstrating documentation/source drift.
- https://docs.polymarket.com/api-reference/markets/list-markets : documented
  end_date_min/end_date_max. No actual filtered API acceptance was observed here.

The bounded research inference allows only exact `politics_fees` when category is
absent/null, version is explicitly v1, comboStatus is disabled, and native binary
CTF identity, negRisk=false and all other mechanics pass. Gamma feeSchedule must
be complete, takerOnly=true, exponent1, finite rate0..1, feesEnabled boolean; if
fees are disabled the declared rate must be zero. Bound=max(enabled Gamma rate,
0.07), rounded upward with native fee_max. Higher validated rates are retained.
`zero_fees`, missing/unknown types, crypto_fees_v2, absent protocol/combo evidence,
malformed category and opaque taxonomy remain unknown. No string suffix proves
protocol; no title/slug/tag class mapping. This is intentionally a narrow supported
class, not a general feeType registry. Recognized top-level categories keep their
separate conservative route; explicit comboStatus other than disabled refuses.
Expiry remains2026-11-04T00:00:00Z. No policy refresh, cap change or trading permit.

Tokens independently record fee_method UNKNOWN/TOP_LEVEL_CATEGORY/
DOCUMENTED_WORST_CASE_CATEGORY_UNKNOWN, fee_class UNKNOWN/RECOGNIZED_CATEGORY/
POLITICS_STANDARD, and fee_policy_expiry_utc. The exact source page/row and
receipt/raw/derived Gamma digests bind provenance without echoing source labels.
Taxonomy remains UNKNOWN for the fallback. category_origin is MISSING/MALFORMED/
TOP_LEVEL. filter_state is MATCH/FILTER_MISMATCH/UNKNOWN; filter_counts use those
keys and count captured deduplicated rows. fee_method_counts use fee_method keys
and count selected token records, not markets. Zero tokens means zero evaluations.

## Historical v1 compatibility and empirical proof (R005/R006)

The new verifier accepts only v2 records; v1 evidence is not rewritten or
reinterpreted. Use the reproducible pinned predecessor tree at
`d0765424ecfa1857770ba8cc5d23f577e9bf05fb` for v1 verification, offline:

```
git archive --format=tar --output=<ABS_EXTERNAL_BASE_TAR> d0765424ecfa1857770ba8cc5d23f577e9bf05fb
tar -xf <ABS_EXTERNAL_BASE_TAR> -C <ABS_NEW_EXTERNAL_LEGACY_SOURCE>
python -B <ABS_NEW_EXTERNAL_LEGACY_SOURCE>/tools/alpha/run_near_term_market_screener.py verify --scratch-dir <ABS_ORIGINAL_V1_SCRATCH>
```

The legacy source directory must be distinct from the evidence directory. Check
scanner raw-byte SHA256 before executing:
`cca41e755b87357790321b838ed1ef599ff229925a336f535391b9f6fec2cfef`.
Retain before/after scratch hashes. Native imports come from that pinned tree.
This path requires only local Git objects, no download or product request.

Original historical three raw page SHA256s (respectively offsets0,100,200):
`8ab6af92779bef05930ebca80cd8f4d68f2a18c2f853ccaa08609bdab2a9f5e4`,
`e8f7e2bc455e3aaf550b2b4f82402ef76448d7a9ddd7a62ec299f91e1e05837a`,
`1fe6f8e4178dd8f940f58d3282f22742f572b696cdf5d1381b281dd68714e3f9`.
Original archive and full pinned-v1 replay remain external evidence. The committed
portable test fixture is a compressed **derived projection** of fields used by
the scanner from all300 original rows; it is not original raw bytes. Its offline
replay deliberately simulates a server ignoring the new filters:300 distinct
IDs,300 absent categories,2 expired/298 beyond-window/0 in-window, no books,
then unavailable offset300. The new FILTER_MISMATCH denominator is300. This tests
honest partial coverage rather than asserting no market opportunities globally.
Synthetic positive/missing-category fixtures are explicitly separate from real
observations. Neither proves resolution, settlement, edge, fills or profitability.

## Negative matrix and exact requirement nodes (R001-R008)

R001 filtered URLs/local cutoffs/filter mismatch; R002 missing/null/wrong-type/
empty/unsupported feeType/schedule/protocol/combo and higher rate; R003 timeout,
HTTP classes/redirect/oversize/malformed/no-echo; R004 fee-inclusive floor/cap,
independent minima, stale/future/tick/delay/depth/grid; R005 immutable cold replay,
rehashed query/provenance/extra/missing paths and pinned-v1; R006 real-derived
projection and synthetic counterexample; R007 no activation/unchanged pure Hunter;
R008 categories/filter/fee/token/market denominators and nonclaims. Existing hostile
recursive field-coverage/no-echo and reparse tests remain. Free-text typo/wording
filters are not added; such policy matrix categories are not applicable. Source
strings remain untrusted raw evidence and never become structured prose fields.
