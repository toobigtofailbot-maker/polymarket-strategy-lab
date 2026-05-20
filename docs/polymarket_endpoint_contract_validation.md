# Polymarket Endpoint Contract Validation

## Purpose

This document records the WP9 endpoint contract validation for the read-only Polymarket public data adapter introduced in WP8. The goal is to confirm whether the endpoint candidates derived from public documentation actually respond as expected before adding snapshot persistence, automated polling, or any SDK dependency.

## WP9 Scope

WP9 is strictly limited to:

- Controlled, minimal, GET-only public probes against Polymarket public endpoints.
- Documentation of observed response shapes.
- Updating endpoint verification metadata only where actual probe evidence supports it.
- Adding minimal contract-validation tooling and offline tests.
- Updating deferred items WP8-D001 and WP8-D002.
- Deciding the next WP direction.

WP9 does not add trading logic, order placement, signing, authenticated clients, credentials, wallet handling, live-trading paths, runtime dependencies, automated polling, or a scheduler.

## Commands Run

### Preflight

```
python tools/git/preflight_generated_artifact_guard.py
python tools/git/preflight_sync_main.py --required-commit fa9fc25e8c5b59167bd7032c26763f74a7b0a21b --required-file docs/polymarket_readonly_adapter_evaluation.md --required-file src/data_layer/polymarket/public_client.py --required-file tools/polymarket/readonly_smoke_test.py --required-file tools/git/preflight_generated_artifact_guard.py
```

Both passed.

### Security

```
python tools/security/verify_project_gitleaks.py   → AVAILABLE (8.27.2), no findings
python tools/security/check_security_tools.py      → gitleaks AVAILABLE; semgrep, pip-audit NOT_AVAILABLE
python tools/security/run_available_security_checks.py  → gitleaks PASS; semgrep/pip-audit SKIPPED (unavailable)
```

semgrep and pip-audit are unavailable because `.venv-security/` was not restored. WP9 adds no runtime dependency, so this is not a blocker. These tools are not falsely marked as passing.

### Network probe (explicit, manual, gated)

```
python tools/polymarket/readonly_contract_probe.py --allow-network --markets-limit 3 --report-path security-scan-output/wp9_contract_probe_report.json
```

Run once. Output written to ignored `security-scan-output/` directory. Not committed.

### Tests

```
python -m pytest
```

155 tests passed, 0 failures.

## Endpoint Contract Validation Summary

| Endpoint | Status | HTTP | Notes |
|---|---|---|---|
| Gamma `GET /markets` | **CONFIRMED** | 200 | Returns JSON list of market dicts. |
| Gamma `GET /markets/{id}` | **CONFIRMED** | 200 | Requires integer `id`, not conditionId hash. |
| CLOB `GET /health` | **NOT CONFIRMED** | 404 | Endpoint does not respond at `/health`. |
| CLOB `GET /book?token_id=...` | **CONFIRMED** | 200 | Returns bids/asks dict. |

## Gamma `/markets` Result

- **URL:** `https://gamma-api.polymarket.com/markets?limit=3`
- **HTTP status:** 200
- **Response shape:** JSON array of market objects.
- **Record count:** 3 records returned for `limit=3`.
- **Key fields observed:**
  - `id`: string representation of an integer (e.g. `"540817"`) — **this is the correct identifier for `/markets/{id}`**
  - `conditionId`: 0x-prefixed hex hash — **not usable as the /markets/{id} path parameter** (returns 422)
  - `question`: string
  - `active`: string (`"true"` / `"false"`)
  - `clobTokenIds`: **JSON-encoded string** (e.g. `'["token1","token2"]'`), not a Python list — **WP8 parser mismatch**
  - `outcomes`: **JSON-encoded string** (e.g. `'["Yes","No"]'`) — **WP8 parser mismatch**
  - `outcomePrices`: JSON-encoded string
  - `conditionId`, `endDate`, `startDate`, `question`, `slug`, `volume`, `liquidity`, and ~85 additional fields

## Gamma `/markets/{identifier}` Result

- **URL:** `https://gamma-api.polymarket.com/markets/540817`
- **HTTP status:** 200
- **Response shape:** single market dict (same field set as list items).
- **Confirmed:** identifier must be the integer `id` string. Using `conditionId` hash returns HTTP 422.

## CLOB `/health` Result

- **URL:** `https://clob.polymarket.com/health`
- **HTTP status:** 404
- **Result:** endpoint does not exist at this path.
- **Conclusion:** WP8 endpoint candidate is not confirmed. CLOB `/health` remains unverified.

## CLOB `/book?token_id=...` Result

- **URL:** `https://clob.polymarket.com/book?token_id={token_id}`
- **HTTP status:** 200
- **Response shape:** JSON object with keys:
  - `asks`: list of `{"price": str, "size": str}` dicts
  - `bids`: list of `{"price": str, "size": str}` dicts
  - `asset_id`: string (same as token_id)
  - `hash`: string
  - `last_trade_price`: string
  - `market`: string (conditionId hash)
  - `min_order_size`: string
  - `neg_risk`: boolean
  - `tick_size`: string
  - `timestamp`: integer (Unix milliseconds)
- **Confirmed:** bids/asks structure matches WP8 `OrderBookSnapshot` parser expectations.
- **Required:** token_id must be extracted by JSON-parsing `clobTokenIds` from the `/markets` response.

## Observed Response-Shape Summary

### WP8 assumptions vs. WP9 observations

| Field | WP8 assumption | WP9 observation |
|---|---|---|
| `clobTokenIds` | Python list | JSON-encoded string — must call `json.loads()` |
| `outcomes` | Python list | JSON-encoded string — must call `json.loads()` |
| `outcomePrices` | Python list | JSON-encoded string |
| `/markets/{id}` identifier | conditionId hash | integer `id` field (e.g. `"540817"`) |
| CLOB `/health` | HTTP 200 JSON | HTTP 404 — endpoint absent |

## Adapter Metadata Changes

`src/data_layer/polymarket/public_client.py` updated:

- `gamma_markets`: `verified=True`, `verified_in_wp="WP9"`, `verified_at_utc="2026-05-18"`
- `gamma_market_by_id`: `verified=True`, `verified_in_wp="WP9"`, `verified_at_utc="2026-05-18"`, note about `id` vs `conditionId`
- `clob_book`: `verified=True`, `verified_in_wp="WP9"`, `verified_at_utc="2026-05-18"`, note about clobTokenIds JSON parsing
- `clob_health`: remains `verified=False`, note added documenting HTTP 404 result
- `DEFAULT_USER_AGENT` updated to `wp9-contract-validation`

## Parser Changes

`parse_market_summary` updated to:

1. Handle `clobTokenIds` as a JSON-encoded string (call `json.loads()` if value starts with `[`).
2. Handle `outcomes` as a JSON-encoded string (same approach).
3. Both Python list and JSON-encoded string inputs are supported for backwards compatibility.

New helper: `_parse_json_string_or_list(value)` — handles both forms defensively.

`parse_order_book_snapshot` is unchanged. The `bids`/`asks` structure matches the WP8 assumption.

## Sanitization Policy

- The network probe writes output only to ignored `security-scan-output/` (not committed).
- No raw API payloads are committed to this repository.
- Market IDs and condition IDs in this document are public identifiers from the Gamma API. They are minimal and used only to document the probe.
- No private data, wallet addresses, API keys, or credentials appear in any committed file.

## Rate-Limit Policy Status

**Not confirmed.** WP8-D002 remains OPEN.

The WP9 probe used `limit=3` with a 10-second timeout and ran once manually. No HTTP 429 responses were received and no rate-limit headers were observed in the response. This does not constitute rate-limit confirmation — a single low-volume probe provides no information about sustained request limits, burst limits, or policy enforcement.

Rate-limit policy must be confirmed from authoritative Polymarket documentation or API response headers before any automated or frequent request pattern is scheduled.

## Deferred Item Impact

### WP8-D001 — Polymarket public endpoint contract not confirmed

**Updated:** Three of four endpoint candidates confirmed via WP9 controlled probe:

- Gamma `/markets`: CONFIRMED
- Gamma `/markets/{id}`: CONFIRMED (integer `id` required, not `conditionId`)
- CLOB `/book`: CONFIRMED
- CLOB `/health`: NOT CONFIRMED (HTTP 404)

WP8-D001 updated to READY_FOR_WP with the following scope:
- Gamma `/markets`, Gamma `/markets/{id}`, and CLOB `/book` are confirmed for limited dev/paper read-only use.
- CLOB `/health` is not confirmed and should not be used in production or automated code.
- Parser must handle JSON-encoded string fields (`clobTokenIds`, `outcomes`). WP9 updates the parser accordingly.

### WP8-D002 — Rate-limit policy not confirmed

**Remains OPEN.** Low-volume probe does not confirm rate limits. See Rate-Limit Policy Status above.

### New deferred items added

- WP9-D001: CLOB `/health` endpoint absent at expected path.
- WP9-D002: `clobTokenIds` and `outcomes` are JSON-encoded strings — parser updated in WP9; snapshot persistence code must also handle this.

## Remaining Uncertainties

1. **CLOB `/health`**: The correct health/status endpoint path for the CLOB API is unknown. This is not blocking for read-only market data use but prevents service health monitoring.
2. **Rate-limit policy**: Not confirmed. Must be addressed before automated polling.
3. **Token ID stability**: Not known whether `clobTokenIds` values persist across market updates or whether they can be safely cached.
4. **Gamma API pagination**: The `limit` parameter works but cursor/offset pagination for large market sets was not tested.
5. **Market identifier stability**: The integer `id` field was used for the chained `/markets/{id}` probe. Whether this integer is stable over the market lifecycle is not confirmed.

## Next WP Recommendation

**WP10 — Polymarket Market Metadata Snapshot Persistence**

The three confirmed endpoints are sufficient for a minimal read-only snapshot:
- Fetch market metadata list via `GET /markets`.
- Fetch single market detail via `GET /markets/{id}`.
- Fetch order-book snapshots via `GET /book?token_id=...` (token extracted from `clobTokenIds`).

WP10 should:
- Add a local JSON snapshot writer under `src/data_layer/polymarket/`.
- Use the updated parser (WP9) to produce `MarketSummary` records.
- Write snapshots to ignored local paths for strategy research.
- Document snapshot file format and provenance.
- Remain strictly read-only with no automated polling.

WP10 should NOT proceed to the official Python client dependency decision unless the stdlib adapter proves insufficient for the snapshot use case.

## WP16 Polling Policy Note

Future repeated polling must use the WP16 local rate-limit guard and polling policy. One-off endpoint probes do not confirm venue rate limits and cannot be used as authorization for automated scanning or higher-frequency polling.

## Safety Statement

WP9:
- Made no changes to trading logic.
- Added no order placement, cancellation, or signing methods.
- Added no authenticated client.
- Added no API credentials, private keys, or wallet handling.
- Added no live-trading paths or live-trading configuration.
- Made no global or system package installations.
- Added no runtime Python dependencies.
- Network access was performed manually, explicitly gated by `--allow-network`, and used only GET-only public endpoints.
- Automated tests do not require live network.
- Rate-limit policy was not overclaimed.
- No generated artifacts were committed.
