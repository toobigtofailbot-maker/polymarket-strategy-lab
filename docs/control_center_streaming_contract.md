# Control Center Streaming / Freshness / Gap / Resync Contract (S10-CC-STREAM-01)

## Purpose

S10-CC-STREAM-01 adds the first bounded Control Center auto-refresh transport. It is default-off,
request-scoped and same-origin. It creates no new canonical event bus, freshness oracle, source poller,
replay store or execution runtime:

```text
existing authoritative HTTP GET projections
        ↑
TanStack Query active-family invalidation / re-fetch
        ↑
same-origin browser stream (one per shell)
        ↑
default-off request-scoped SSE refresh/resync signal stream
```

The server-sent events carry transport metadata only. They never carry canonical market,
experiment, StrategyLifecycle, Hermes, Alpha, OPS, paper or gateway payloads. The existing HTTP GET
projections remain the only authoritative data surfaces. Every page still shows exactly what its GET
projection returns.

The semantic separations are permanent:

```text
transport connected != domain fresh
transport sequence != canonical store sequence
REFRESH_DUE != source changed
transport gap != market-data gap
server signal time != market/account observation time
recorded gateway state != current host/network/account truth
SSE refresh != command/execution/live authority
```

## Kill switch

| Surface | Contract |
|---|---|
| `CockpitConfig.streaming_enabled` | appended last; exact `bool`; default `False`; every earlier positional field is unchanged |
| CLI | `--enable-streaming` (`store_true`, default off) is the only way to enable it |
| Environment / config discovery | none; no environment variable or file can enable streaming |

When streaming is disabled, the Control Center behaves exactly as before: refresh is manual only.

## Transport module

`src/operator_cockpit_stream.py` is transport-only. Its imports are exactly `__future__`, `asyncio`,
`json`, `re`, `time`, `typing` and `uuid`. It imports no canonical domain or store module, no
`sqlite3`, filesystem, environment, subprocess, network-client, WebSocket, FastAPI or Starlette
module. It persists nothing and keeps no module-level transport state.

Frozen constants:

| Constant | Value |
|---|---|
| `STREAM_SCHEMA_VERSION` | `"1.0.0"` |
| `BASE_TICK_SECONDS` | `5` |
| `STREAM_EVENT_KINDS` | `RESYNC_REQUIRED`, `REFRESH_DUE`, `HEARTBEAT` |
| `STREAM_FAMILY_REFRESH_SECONDS` | `overview` 10, `market` 5, `experiments` 30, `strategies` 30, `hermes` 30, `alpha` 30, `ops` 5, `paper` 5, `audit` 10 |

The family keys are the existing frontend `QueryFamily` tokens. `market` is the family of the
`/markets` route; there is no separate `markets` token. The cadence is fixed by the server, and no
caller (HTTP, CLI, environment or config) can change it.

The only test seams are the module-internal sleeper, clock and connection-id factory. Production
uses `asyncio.sleep`, `time.time_ns` and UUID4-derived ids. The seams are not reachable through
HTTP, CLI, environment or configuration.

### Connection lifecycle

Each `GET /api/stream/events` request is exactly one connection:

1. A fresh connection id `ccstream:<32 lowercase hex>` is created.
2. `sequence` starts at `1`.
3. `RESYNC_REQUIRED` is emitted immediately.
4. The loop waits for the 5-second base tick.
5. After each tick the loop stops if the client disconnected. Otherwise it emits `REFRESH_DUE`
   when the family cadence is due (tick number × 5 is a multiple of the family cadence) and
   `HEARTBEAT` otherwise.
6. `sequence` increases by exactly one per emitted event.
7. The loop ends on disconnect or cancellation. There is no internal retry, no background
   continuation and no exception swallowing.

The loop exists only while its HTTP request is connected. There is no app-start, lifespan, global or
background task. A disconnected client is noticed at the latest one base tick later, either by the
disconnect probe or by cancellation of the response task.

### Event envelope and framing

Each event has exactly these JSON fields, in this order:

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | `"1.0.0"` |
| `connection_id` | string | `ccstream:<32 lowercase hex>`, ephemeral and non-canonical |
| `sequence` | positive integer | connection-local transport sequence |
| `kind` | string | `RESYNC_REQUIRED`, `REFRESH_DUE` or `HEARTBEAT` |
| `family` | string | the requested `QueryFamily` token |
| `server_time_ns` | decimal string | the server time at which the signal was emitted, not a JSON number |

SSE framing (compact JSON, ASCII, no `retry:` directive and no comment lines):

```text
id: <connection_id>:<sequence>
event: resync|refresh|heartbeat
data: <compact JSON envelope>

```

`REFRESH_DUE` only means the server cadence says the active family should be re-read. It does not
mean that a source changed or that data is fresh or stale. `HEARTBEAT` only means the transport
emitted a scheduled event. Neither carries a domain payload, path, error text, secret or private
data.

## API

Both routes are GET only. POST, PUT, PATCH and DELETE return 405. The final `/api` route set has
exactly 27 routes. No existing route, DTO or semantics changes. The closed error map gains
`STREAM_DISABLED -> 503`.

### `GET /api/stream/status`

Any query pair returns `400 INVALID_INPUT`. The response is exactly:

```text
read_only: true
enabled: <bool>
transport: "SSE"
semantics: "SERVER_PACED_ACTIVE_FAMILY_REFRESH"
source_push: false
canonical_event_stream: false
domain_freshness_guarantee: false
replay_available: false
base_tick_seconds: 5
refresh_seconds_by_family: <the exact cadence mapping>
```

It is transport configuration only, never domain freshness or currentness.

### `GET /api/stream/events?family=<QueryFamily>`

The query is validated before the enablement check. It must be exactly one pair, the key must be
exactly `family` and the value must be one of the nine `QueryFamily` tokens. A duplicate, unknown,
extra or missing pair returns `400 INVALID_INPUT`. A valid family while streaming is disabled returns
exactly `503 {"error":{"code":"STREAM_DISABLED"}}`.

When enabled, the route returns a `StreamingResponse` with `Content-Type: text/event-stream` and
`Cache-Control: no-cache` over the request-scoped generator. It adds no proxy or deployment headers.

## Reconnect, gap and resync

There is no replay buffer and no persistent transport history. `Last-Event-ID` is never used to
resume: a reconnect is a new server connection with a new id, and its first event is always
`RESYNC_REQUIRED`.

The browser keeps only the current connection id and last sequence for its one stream:

| Observation | Action |
|---|---|
| first valid event, or a changed connection id | resync: re-read the active family over HTTP |
| same connection and `sequence == last + 1` | normal processing |
| same connection and any other sequence | transport gap: resync the active family |
| `RESYNC_REQUIRED` | re-read the active family |
| `REFRESH_DUE` | re-read the active family |
| `HEARTBEAT` | update transport metadata only; nothing is re-read |
| malformed or wrong-family event data | drop it; clear the baseline so the next valid event resyncs |

After a resync, the newest valid event becomes the baseline. A transport gap is never labelled a
market-data gap, and no attempt is made to replay canonical domain events.

## Frontend

- `api.ts` adds the exact `StreamStatus` and `StreamEvent` DTOs, the global `streamStatusQuery` key
  `["cc","stream","status"]` (`/stream/status`, strictly validated), the same-origin
  `streamEventUrl(family)` helper, the strict `parseStreamEvent` validator and the
  `advanceStreamBaseline` gap/resync rule. Malformed input never becomes query data and is never
  rendered.
- `app.tsx` adds one centralized `StreamRefreshController` in the shell. It is the only browser
  stream construction site in the frontend. If the status is not enabled (including while it is
  loading or unavailable), no stream is opened and the shell shows `Auto-refresh: Disabled`. When
  enabled it opens one stream for the active family. Its effect cleanup closes the stream on family
  change or unmount. Native browser reconnect is allowed; there is no custom reconnect timer or
  backoff, and an error only marks the transport disconnected.
- Stream-driven refresh only ever calls
  `queryClient.invalidateQueries({ queryKey: familyKey(activeFamily) })`. It never invalidates every
  `cc` family and never calls `setQueryData` with canonical content.
- Manual Refresh is unchanged and always usable. The Query defaults (`staleTime: Infinity`,
  `retry: false`, no focus or reconnect refetch) are unchanged. There is no `setInterval`,
  `refetchInterval`, WebSocket, local/session storage or mutation method.
- Transport states: Disabled, Connecting, Connected, Resyncing, Disconnected. The visible wording
  says auto-refresh/transport, never system or domain health. The shell shows this notice:
  "Auto-refresh updates this workspace from the existing authoritative HTTP snapshots. Stream
  connection state is transport status, not domain freshness or trading readiness."
- The last signal is labelled "Server refresh-signal time". It is converted from the decimal
  nanosecond string with `BigInt`, never through an unsafe JavaScript number. No browser clock drives
  domain freshness.
- Storybook answers `/api/stream/status` with the exact `enabled=false` DTO through the shared
  `mock(...)` helper for every story, so no story opens a stream. The preview catch-all stays closed.

## Domain freshness stays domain-owned

STREAM-01 does not synthesize global freshness or currentness. Existing domain concepts keep their
meaning and owners: market `received_at`, paper `last_market_receive_ns`, the recorded gateway
heartbeat / user-stream / access / reconciliation fields, the Hermes information cutoff, the Alpha
discovery `as_of`, and policy/allocation validity windows. The OPS-01 recorded gateway warnings are
unchanged. Re-reading recorded evidence more often does not make it a fresh account, host or network
check.

Nothing in the transport may claim, from the transport itself: data fresh, market current, account
current, host current, network eligible, execution ready, live ready, a market data feed, source
changed, canonical event stream, or any incident/alert state.

## Operational note

uvicorn's default graceful shutdown waits for open responses. While a browser stream is open, the
first interrupt of a locally launched cockpit may wait for that stream, and a second interrupt
forces the exit. Closing the browser tab ends the stream at the next base tick. This is standard
uvicorn behavior and is not a background task.

## Deferred / forbidden (unchanged by this WP)

| Concern | Status |
|---|---|
| global cross-store canonical sequence, source-native push, source-head polling, writer hooks | forbidden |
| browser polling, WebSocket, replay buffer or persisted transport history | forbidden |
| current account / host / network truth, fresh geoblock or execution-network eligibility | deferred to protected runtime owners |
| incident / alert lifecycle | deferred (no canonical owner) |
| operator commands, auth, CSRF, idempotency receipts | S10-CC-CMD-01 (separately gated) |
| private production deployment, proxy, TLS, monitoring, mobile hardening | S10-CC-PROD-01 (separately gated) |

Future commands must not depend on this stream: they return canonical receipts and re-read the
canonical HTTP snapshots.

## Authority

Runtime: one bounded request-scoped SSE loop only. External or product network: none. Canonical
evidence: transport presentation only; no new canonical owner. StrategyLifecycle, Hermes, Alpha,
paper and gateway sources: unchanged and not mutated. Credentials and account reads: none. Strategy,
paper, execution and live authority: none. Capital: USD 0. Merge: Karl only.
