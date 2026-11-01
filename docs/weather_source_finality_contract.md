# Original weather source finality research

S10-WEATHER-SOURCE-FINALITY-01 is the exact-nine-path RUNTIME/Risk3 package on
merged PR264, base `b678b5c98179a858f3df8b37016ae738a81311d0`. Karl explicitly
authorized implementation of frozen prompt SHA256
`506f8c1245d566ca0846800658916b978d6b3475a98c0a1cb10542d2632d3d5f` and spec
`e2a5cee3760447136dae708556e69dbed37a785e96d6007b9aa42f37c391248e`.
Those bytes are unchanged. Native readiness is deterministic, not a certificate.
Implementation does not authorize real product GET, method admission or merge.

## Interface

One finite tool: `tools/alpha/run_weather_finality.py`, exposing `audit(request)`
and `verify(request, receipt)`. Import, audit and verify are offline. The CLI is:

```
python -B tools/alpha/run_weather_finality.py audit --request-file /external/request.json --output-dir /external/new-audit
python -B tools/alpha/run_weather_finality.py verify --request-file /external/new-audit/request.json --receipt-file /external/new-audit/receipt.json
```

Exit0 means completed research (possibly entirely UNKNOWN) or successful cold
verification; exit1 is a closed refusal; exit2 is sanitized CLI misuse. Raw arguments,
paths, URLs, source bodies and exceptions are not printed. `complete.json` is the terminal
marker; it binds the exact receipt.json SHA256. Existing output directories are refused. An interrupted or
refused invocation may leave exclusively created forensic files without that marker;
they are incomplete, never a successful bundle and never automatically retried. No files are deleted on refusal.
Verify requires the terminal marker and matching receipt digest and writes nothing. Input request/evidence/capture inventories are rechecked. The receipt data file is written before final input checks; only then is complete.json exclusively published, with no later failure-producing input checks.

Request keys, with no extras: `schema_id=weather-finality-request`,
`schema_version=1.0.0`, `analysis_mode=ORIGINAL_CAPTURE|SYNTHETIC_ONLY`,
`capture_dir` (absolute external native capture directory), `evidence_bundle_file`
(absolute external file or null). Missing original capture refuses with unavailable
counts null. Missing CLI/settlement evidence completes with UNKNOWN.

Evidence bundle keys: `schema_id=weather-finality-evidence`, `schema_version=1.0.0`,
`evaluated_ns` (positive integer UTC ns), `receipts` (at most24),
`synthetic_complete_groups` (at most6 station:date strings; must be empty in ORIGINAL_CAPTURE).
All retained body files must be direct siblings of their bundle. This is a bounded
flat evidence layout, not an arbitrary recursive import. The enclosing direct-file
inventory is pinned against addition/removal; all referenced raw bytes are pinned.
Unrelated subdirectories are not evidence inputs. Source capture inventory is
separately validated and pinned in full using native rules. SQLite sidecars refuse.

Each retained entry has exactly: `kind`, `market_id`, `body_file`, `sha256`, `url`,
`started_ns`, `received_ns`, `status`, `http_status`, `http_date`. `kind` is
NWS_INDEX/NWS_PRODUCT/GAMMA/V3_RESOLUTION. Failed transports have null body/hash and
may have null HTTP status/date. Successful bodies require matching SHA256,
HTTP_2XX/numeric2xx, bounded bytes and no secret pattern. Entry clocks must be
ordered and no later than evaluated_ns. A source metadata field is never an
independent attestation. Unknown/duplicate JSON keys, invalid numeric types,
unsafe paths, symlinks/reparse traversal, hardlinks and overwrite attempts refuse.
Native bridge safe-reader/directory-handle checks are reused without edits.

## Reuse and source contract

`provenance.verify_capture`, Hunter cold verification and the bridge's `_source`
bind actual native method, five code hashes, capture/native manifests, original
rule/station/date/condition and ordered Yes/No tokens. No lifecycle store, strategy
creation, fee/sizing evaluator, gateway, account or provider is invoked. Retained
hashes prove local consistency only; source origin stays UNVERIFIED.

The native method is `RAIN_NWS_V1` / `nws-gridpoint-pop-climate-day-v1`,
LAST_BEFORE_1400_ET only, precipitation >=Decimal0.01 inches, trace excluded.
NDFD station-standard-offset helpers define the24h climate day. The rule cutoff
is instead next-date14:00 America/New_York, DST-aware: for2026-10-31 it is
2026-11-01T19:00:00Z. Gamma endDate is not substituted for either clock.
Entry-window labels use remaining time to climate-day close: [0,6),[6,12),
[12,24),[24,48] hours. Outside stays OUTSIDE_WINDOWS. Original issue/received/cutoff
timestamps remain unchanged. Native grid updateTime is preserved as forecast_grid_update_ns; forecast_issue_ns is null because a separate issuance receipt is not established. No post-decision label becomes a prediction input.
Near-resolution observations remain NOT_OBSERVED unless actually collected by an
approved source path; no synthetic backfill of original forecasts.

The CLI parser accepts a narrow full-day NWS text shape: one CDUS WMO header
matching issuingOffice and UTC issue minute, one CLI station-suffix PIL, one
English issue-date/time/explicit US-zone line matching issuanceTime, one climate
summary for the exact date, one PRECIPITATION(IN) section and one daily
TODAY/YESTERDAY row. Month/year/record/normal totals are not daily observations.
Partial-day/VALID AS OF, issue before climate close or at/after cutoff, wrong
station/date/header/metadata, M/missing/ambiguous totals, unsupported layout or
conflicting latest eligible versions cannot certify finality. T/TRACE and0.00
map to No; >=0.01 maps to Yes. Candidate raw_sha256 is the actual retained body
digest, not a reserialized JSON digest.

Venue candidate checking reuses QDR.normalize_gamma_market, native rule parsing,
V3.normalize_row and QDR.resolve_label. Offline V3_RESOLUTION bodies are arrays
of1..64 raw row mappings using native market/id/assets_ids/winning_asset_id/
winning_outcome/timestamp_received/timestamp names; dates are UTC strings converted
before native normalization. Market/condition/token/rule must match; venue time <=
receive time <= retained receipt receive time, after climate close. Gamma's closed
flag/price alone gives no winner. Every instrument in a station/day group needs
its own matching evidence; absent/conflicting instruments remain UNKNOWN.

## Proof limits and output

There is no installed trusted verifier of complete historical CLI publication
coverage or independent original archive origin in this package. Neither a current
index, a local HTTP receipt/hash nor a user boolean supplies that proof. ORIGINAL_CAPTURE
therefore retains parsed CLI and venue candidates/local agreement but leaves independent
CLI/venue/dual statuses UNKNOWN and source_verified_group_count0 under currently
supported proof types. This is an explicit capability/evidence limit, recorded in
the deferred log, not a claim that all possible authentic proof can be certified.
No new trust registry, certificate issuer, RPC client or synthetic bypass is introduced.
Authentic unavailable/unprovable outcomes remain UNKNOWN. A locally conflicting
candidate is exposed as local DISAGREEMENT without forcing a payout.

SYNTHETIC_ONLY can exercise positive/negative coverage and independent-channel
mechanics; its synthetic_verified_group_count never enters original source counts,
native independent_event_groups, calibration or qualification. A standalone imported
resolution JSON row never becomes an independently authentic archive witness.
The old Aug18-Sep26 NDFD/PendulumFlow corpus is incompatible with the original
gridpoint forecast method; time/rule APIs may be reused but those rows are not promoted.

RESULT_FIELDS, GROUP_FIELDS and COMPLETE_FIELDS enumerate every public receipt/terminal field; each field is
classified scanned in OUTPUT_CLASSIFICATION/GROUP_CLASSIFICATION/COMPLETE_CLASSIFICATION and recursively
scanned as canonical bytes, including invalid outputs. A hand-built dictionary is
not a full output-surface scan unless a field-coverage test proves it covers every
public field. Tests assert exact field/classification equality and no-echo for
valid and invalid results. Canonical content hashes bind tool bytes, normalized
request and retained input hashes; source_bindings names native method/code/manifest
hashes explicitly. Group output keeps independent station/day identity distinct
from per-instrument condition/rule/ordered-token identity, source/label clocks,
candidate product/value/winner, both local and independent statuses and closed reasons.

actual_get_attempts is invocation-local: audit/verify0; fetch-once reports actual
transport attempts even on refusal. retained_http_attempts/retained_bytes describe
input acquisition evidence and never claim new calls. Cold verification binds the
original receipt's acquisition counter to its retained inventory, then returns a
zero-new-GET replay result; this does not authenticate those historical requests.
accepted_production_methods/corpora, independent_event_groups and real_orders are0;
production_eligible=false; METHOD_NOT_QUALIFIED; no_live/no_order=true; real-market
event-to-order latency UNMEASURED. No trade signal, PnL, permit or order is generated.

## Default-off finite retrieval

`fetch-once --request-file ... --output-dir ... --authorize-public-get` is a separate
explicit opt-in interface. Karl has NOT authorized its real invocation. The flag
cannot itself establish human permission. Offline tests inject transports and run
without network. At most6groups/24attempts,2000000bytes per response/32000000total,
12s per attempt/300s total; no redirects, proxies, retries or pagination.

Only canonical api.weather.gov/products?location=station-suffix&type=CLI&start=...
&end=...&limit=500, strict server UUID /products/id from that retained index, and
gamma-api.polymarket.com/markets/original-id are accepted. Native capture.public_read
is reused. No forecast.weather.gov HTML scraper or data-api/CTF/RPC/third-party host.
One index and one Gamma per group leave at most12product attempts for six groups;
more versions mean incomplete coverage/UNKNOWN. A per-attempt intent precedes each
request; raw bodies, HTTP status/date and clocks are retained externally. No source,
database or original capture is rewritten. No daemon, timer or provider is enabled.

## Negative-test matrix and validation

R001 no authority/mutation; R002 native lineage/missing archive; R003 report date,
station/version/cutoff/DST/trace/missing/conflict; R004 independent venue missing,
matching/conflicting/synthetic versus original; R005 causal clocks/window edges;
R006 side/group dedup and incompatible historical method; R007 default-off,
fixed URLs/attempt/byte/time budgets and no retry; R008 cold replay/field coverage,
tampered bytes/inventory/duplicate JSON/unsafe links/overwrite/no-echo; R009 no
method/financial/bridge promotion; R010 truthful missingness/counters/cadence.
Additional regressions cover unknown HTTP statuses, attempt intents, raw digests,
future venue timestamps and SQLite sidecars. Each maps to the exact frozen pytest
node in tests/tools/alpha/test_weather_finality.py. Process receipts are separate
from tests; fixtures do not prove the real workflow or historical settlements.

## Owner-operated forward recipe (not active)

After separate source/host/time/budget approval, the owner may run the unchanged
PR263 finite capture once before a chosen rain climate day, retain raw/source-code
receipts, and later authorize one finite finality probe after next-date14:00 ET
within the documented168h text-product window. Preserve preliminary/near-resolution
information as a separate channel with actual received timestamps; never regenerate
an old forecast. Compare windows, YES/NO and hybrid exit only as research hypotheses.
This is a manual recipe, not an installed schedule. Temperature remains research-only;
no extra temperature network/code/inventory was needed. Missing revision/settlement
proof is recorded; no repeat job or automatic successor WP follows.

Protected boundary groups in docs/ai/codex/PROTECTED_PATHS.md remain uncrossed.
Existing PR263, PR264, financial caps and the USD5 attended canary are unchanged.
Karl alone merges after independent Side23 review. No operational authority follows.
