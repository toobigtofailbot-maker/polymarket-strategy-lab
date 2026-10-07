# S10-CC-STREAM-01 Status Entry

## Identity

- WP ID: S10-CC-STREAM-01
- Title: Control Center Streaming / Freshness / Gap / Resync Layer
- Package class / size / risk: CONTROL_CENTER_SSE_ACTIVE_FAMILY_REFRESH_GAP_RESYNC_RUNTIME / L / 3
- Governance track: RUNTIME; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-cc-stream-01-sse-freshness-gap-resync
- Frozen base: 7bba7f0d6657364b9358d1a4a96807f024db0533
- Predecessor: PR #226 / S10-CC-OPS-01, head 90d30129ce0f3282395b6f319ce25c622191d39b, merged at the base
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Ready for review: NO until all final evidence passes (live value in the PR body)
- Merge authorized: NO (Karl only; review owner Side17)
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Capability (default-off request-scoped refresh/resync transport)

- New transport-only module `src/operator_cockpit_stream.py`. Its imports are exactly `__future__`,
  `asyncio`, `json`, `re`, `time`, `typing` and `uuid`. It reads no canonical store, file, environment
  value or network resource, persists nothing and keeps no module-level transport state. The sleeper,
  clock and connection-id factory are internal test seams only.
- Kill switch: `CockpitConfig.streaming_enabled` is appended last as an exact `bool` defaulting to
  `False`. Only the explicit `--enable-streaming` (`store_true`) CLI flag enables it. There is no
  environment fallback or config discovery.
- `src/operator_cockpit.py` adds `STREAM_DISABLED -> 503` and exactly two GET routes, for 27 `/api`
  routes in total:
  - `GET /api/stream/status`: the exact transport-only configuration DTO (`enabled`, `transport` SSE,
    `semantics` SERVER_PACED_ACTIVE_FAMILY_REFRESH, `source_push` / `canonical_event_stream` /
    `domain_freshness_guarantee` / `replay_available` false, `base_tick_seconds` 5 and the exact
    cadence mapping). Any query pair returns `400 INVALID_INPUT`.
  - `GET /api/stream/events?family=<QueryFamily>`: exactly one closed `family` query, validated before
    enablement; valid but disabled returns `503 STREAM_DISABLED`; enabled returns a
    `text/event-stream` `StreamingResponse` with `Cache-Control: no-cache`.
- One request-scoped loop per connected request: a fresh `ccstream:<32 hex>` id, sequence 1 and
  `RESYNC_REQUIRED` immediately, then a 5-second base tick that emits `REFRESH_DUE` at the fixed
  family cadence (overview 10, market 5, experiments 30, strategies 30, hermes 30, alpha 30, ops 5,
  paper 5, audit 10 seconds) or `HEARTBEAT`. The sequence increases by one per event. The loop stops
  on disconnect or cancellation with no retry, background task, replay buffer or persisted history.
  `Last-Event-ID` is never used to resume.
- Envelope: exactly `schema_version`, `connection_id`, `sequence`, `kind`, `family`, `server_time_ns`
  (a decimal string). SSE framing is `id: <connection_id>:<sequence>`, `event: resync|refresh|heartbeat`
  and compact `data:`. There is no `retry:` directive and no domain payload.
- Frontend: `api.ts` adds the exact `StreamStatus` / `StreamEvent` DTOs, the strictly validated global
  `["cc","stream","status"]` query, the same-origin `streamEventUrl(family)`, the strict
  `parseStreamEvent` validator and the `advanceStreamBaseline` gap/resync rule. `app.tsx` adds one
  centralized shell `StreamRefreshController`, which is the only browser stream construction site. It
  opens a stream only when the backend reports enabled and closes it on family change or unmount.
  Reconnect is native only. A new connection id or a same-connection sequence gap resyncs the active
  family over HTTP. `RESYNC_REQUIRED` and `REFRESH_DUE` invalidate only `familyKey(activeFamily)`,
  `HEARTBEAT` invalidates nothing, and malformed events are dropped. Manual Refresh and the
  conservative Query defaults are unchanged. The shell shows `Auto-refresh: <transport state>` and the
  required transport-not-freshness notice. CSS adds only the shell indicator classes.
- Storybook: the shared `mock(...)` helper answers `/api/stream/status` with the exact disabled DTO
  for all 35 stories, so no story opens a stream.
- Contract: `docs/control_center_streaming_contract.md`.

## Historical Compatibility Edits

- `tests/test_operator_cockpit.py`: the exact `/api` route set adds only `/api/stream/status` and
  `/api/stream/events` (27 routes).
- `tests/test_operator_cockpit_research.py`: the two exact `/api` route-count assertions move from 25
  to 27. The two broad no-EventSource guards are narrowed so that only the centralized shell
  `StreamRefreshController` may hold the single construction site. The WebSocket, `setInterval`,
  `refetchInterval`, `useMutation` and mutation-method bans are unchanged.
- `tests/test_operator_cockpit_ops.py`: the exact `/api` route count moves from 25 to 27, and the same
  narrow EventSource correction applies (OpsView owns no realtime loop; the `setTimeout` ban stays).
- `tests/test_architecture_boundaries.py`: one exact `src/operator_cockpit_stream.py` allowlist entry
  with RUNTIME / risk-3 request-scoped transport wording (no wildcard, no other entry).

## Exact Scope (17 paths)

- src/operator_cockpit.py, src/operator_cockpit_stream.py
- tests/test_operator_cockpit_stream.py, tests/test_operator_cockpit.py,
  tests/test_operator_cockpit_research.py, tests/test_operator_cockpit_ops.py,
  tests/test_architecture_boundaries.py
- src/operator_cockpit_frontend/src/{api.ts, app.tsx, styles.css, foundation.stories.tsx}
- docs/control_center_streaming_contract.md
- docs/project_status.md, docs/repo_truth_index.md, docs/status_entries/S10-CC-STREAM-01.md
- docs/wp_specs/S10-CC-STREAM-01/{wp_prompt.txt, wp_spec.json}

## Authority / Non-Authority Posture

- Runtime/scheduler: only the bounded request-scoped SSE loop. No daemon, background worker, source
  poller, custom retry worker, WebSocket, Hermes runtime, paper engine or execution runtime.
- StrategyLifecycle, Hermes, Alpha, paper and gateway sources: unchanged; mutations 0. Credentials 0;
  account reads 0; product network 0; commands 0; deployment changes 0; signatures/orders 0; capital
  USD 0; live DISABLED.
- No new persistence, dependency, lockfile or workflow change.
- Transport connection, sequence, heartbeat, signal time, refresh-due and gap are never domain
  freshness, source change, market-data gap, account/host/network currentness, incident state, Gate-C
  eligibility or execution/live readiness. The OPS-01 recorded gateway warnings are unchanged.

## Successor Boundary

After Side17 review and Karl merge, next separately gated: S10-CC-CMD-01 (protected operator commands),
then S10-CC-PROD-01 (private production deployment / monitoring / mobile hardening). STREAM-01
authorizes neither. Future commands must not depend on SSE.

## Validation

Focused stream tests (S01-S16), the cockpit / research / OPS / architecture compatibility tests,
Control Center frontend typecheck / build / Storybook build / smoke / audit, readiness, exact scope,
unchanged-source checks, hygiene, security, the independent exact-head implementation review, one
local full suite and the final exact-head hosted matrix are recorded in the PR body.
