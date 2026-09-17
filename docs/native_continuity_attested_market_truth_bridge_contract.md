# WP175E Native Continuity-Attested Market Truth Bridge Contract

## Purpose and authority

WP175E / S10-DATA-03 adds one advisory research capability: a bounded interval
of durable WP169 public WebSocket evidence can become an immutable
`NativeContinuityAttestation` and parallel WP172 `NativeMarketTruthWindow`.
Continuity is derived mechanically; it is never caller authority. This contract
does not reclassify PMXT, search or tune a strategy, rerun OOS evidence, create a
paper order, submit or cancel a real order, read credentials or account state,
activate Gate C, claim `LIVE_PATH_EVIDENCE_READY`, or start WP176.

The implementation is local/offline. Workflow git/GitHub publication and hosted
CI use network; one bounded public unauthenticated WP169 smoke is optional after
local green and creates no product mutation. Credentials, real orders, and
capital at risk remain 0, 0, and USD 0. Merge remains separately authorized.

## WP169 evidence surface

`MarketTruthStore` retains `APPLICATION_ID = 1347242297`, `USER_VERSION = 1`,
the exact table/index DDL, append semantics, and checkpoint hash-chain authority.
WP175E adds no migration and no write API. Its additive reads:

- select only `ACCEPTED` `WS` observations for one exact asset and inclusive
  canonical receive-time interval;
- join each observation to its raw occurrence, recompute the raw envelope and
  normalized-child trust boundary, and recover the durable WS session id from
  the validated source cursor;
- return immutable archive/session/gap records in explicit append-sequence order;
- include session and per-asset gap history through the interval end so state at
  the interval start is reconstructable;
- reject over-bound queries and malformed persisted rows with closed WP169 error
  codes, without path, raw bytes, exception text, or secret echo.

The reads execute through an initialized store and cannot alter observations,
sessions, gaps, checkpoints, schema, or version pragmas. Physical SQLite row
order has no output authority.

## Native capture and attestation identity

`NativeMarketTruthContext` supplies only the explicit WP172 instrument mapping.
It has no capture-id or continuity input. `source_capture_id` is
`nativecapture:sha256:<digest>` over the durable WP169 WS session id and a fixed
version literal; a local path never enters the preimage.

`NativeContinuityAttestation` is frozen and content addressed under
`nativecontinuityattestation:sha256:`. Its identity binds source capture, asset,
requested receive interval, initial full snapshot, first/last accepted market
observation, observation count, session id, exact session/gap evidence digests,
gap open/healed counts, and derived continuity. Only the fixed
`advisory_only=true` and `no_execution_authority=true` flags and the ID itself are
outside the preimage. Its public constructor has no `continuity_complete`
parameter; only the store-backed builder derives that field.

Continuity can be true only if all of the following hold:

- the bounded nonempty interval and every included observation concern one exact
  asset;
- the first usable market-state observation is an accepted WS full `book`
  snapshot with `book_ready=true`;
- the session active at interval start and at that snapshot is the same durable
  session in `STREAMING` state;
- no session transition occurs after the interval start through its end, including
  `CONNECTING`, `RECONNECT_WAIT`, `FAILED`, or a second `STREAMING` epoch;
- exact gap history is structurally balanced before the interval; no gap is open
  at its start and no OPEN or HEALED transition occurs inside it;
- receive times remain monotonic in durable archive order and every included raw
  cursor binds to the attested session.

Every WP169 gap reason is continuity-breaking: `DISCONNECT`,
`TIMESTAMP_REGRESSION`, `HASH_CONFLICT`, `PARSE_FAULT`, `QUEUE_OVERFLOW`,
`STORAGE_FAILURE`, and `REORG`. A gap may be HEALED only by the existing WP169
behavior. A caller may select a later start at a later full snapshot after the
heal; that creates a new attested epoch and does not delete or rewrite history.
An unprovable interval returns `continuity_complete=false` or a closed native
error—never true by coercion.

## Native WP172 market truth

`NativeMarketTruthWindow` has the distinct namespace
`nativemarkettruthwindow:sha256:` and exposes source capture, instrument,
ordered observation ids, exact receive bounds, immutable BOOK/TRADE events,
derived continuity, and the complete bound attestation plus its id. The lineage
preimage binds those semantics, including event content and receive bounds.

The builder starts at a valid full snapshot, reconstructs canonical levels and
subsequent deltas, rejects duplicate/crossed/invalid depth and impossible
deletes, and converts valid `last_trade_price` observations without fabricating
trades. It uses exact `Decimal` strings and integer UTC nanosecond arithmetic;
binary float is absent. Receive time is the execution-knowledge clock. Only
accepted WS evidence is admitted. Quarantined, unsupported, CLOB, Gamma, Data
API, and Polygon records cannot substitute for native order-book truth.

## PMXT, evaluator, and paper compatibility

The existing `MarketTruthWindow` dataclass fields, PMXT lineage preimage,
`build_market_truth_window(PmxtV2ReplaySource, BinaryOptionMarketContext)`, and
gap-policy rule are unchanged: `NONE` alone is complete; `AS_CAPTURED` and
`KNOWN_GAPS` remain incomplete. Native capture IDs never overload
`source_external_dataset_id`.

`assess_executable_edge` admits exactly `MarketTruthWindow |
NativeMarketTruthWindow`, validates the concrete type, and then uses the same
events/continuity boundary. Native provenance grants no PASS advantage. The
existing precedence remains: invalid evidence rejects; non-authoritative
first-look is `DIAGNOSTIC_ONLY`; incomplete continuity/unknown fee/unavailable
truth is `EXECUTABLE_EDGE_INCONCLUSIVE`; known evidence missing fill, capacity,
or net-edge thresholds is `EXECUTABLE_EDGE_FAIL`; only all gates passing is
`EXECUTABLE_EDGE_PASS`.

`run_wp172_replay` admits the same exact union. It changes no
`PaperStrategyBinding`, assessment binding, fill, fee, accounting, risk,
reconciliation, persistence, or paper/live separation rule. Existing PMXT replay
remains backward compatible.

## Evidence result and successor

S10-EVID-01B completed `EVIDENCE_INCONCLUSIVE`. Genuine PMXT remains valid
external research evidence, and its `AS_CAPTURED` archive is not reclassified.
WP169-D001 is narrowed/resolved only for the delivered WP169-native -> WP172
market-truth bridge; no generic PIT -> Nautilus adapter is claimed.

WP175 stays merged dormant and Gate C is NOT AUTHORIZED. WP176 is NOT STARTED.
After WP175E merge, the next action is a separately gated prospective evidence
run: preregister a fresh candidate before viewing its forward OOS/native capture,
then use bounded WP169 public capture and this bridge for executable-edge
validation. That successor is not automatic live activation.
