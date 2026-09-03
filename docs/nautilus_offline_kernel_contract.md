# NautilusTrader Offline Kernel, ParquetDataCatalog & Deterministic Replay Contract (WP168)

Local, offline, read-only-against-canonical research runtime that translates verified WP167
pmxt-v2 external history into NautilusTrader instruments and market-data events, registers
them in a local `ParquetDataCatalog`, and replays them deterministically into a
repo-controlled `NautilusReplayReceipt`. This is an **event-replay proof only**: it does not
prove alpha, realistic fills, executable edge, paper readiness, or live readiness.

Package: `src/research_runtime/nautilus_offline/`. Dependency: exactly
`nautilus_trader==1.231.0` in addition to the WP167 pins (base install — no Polymarket extra
`py_clob_client_v2`, no Redis, no network). Upstream NautilusTrader is LGPL-3.0 and is
**installed, not vendored or modified**.

## Authority

No live data client, no live execution client, no authenticated Polymarket client, no
credentials/signing, no WebSocket, no Data API, no order submission/cancel, no strategy/alpha,
no P&L/fill/queue/slippage/latency/capacity modelling, no paper/live, no scheduler/daemon, no
Hermes runtime. Canonical WP167/PIT truth is read-only; the catalog/replay output is derived
research runtime state, never canonical. `execution_authority` is a constant `False`.

## Public API (frozen — exact signatures)

- `evaluate_offline_runtime() -> NautilusRuntimeCompatibilityResult`
- `build_binary_option(context: BinaryOptionMarketContext) -> BinaryOptionMappingResult`
- `convert_pmxt_v2_events(source: PmxtV2ReplaySource, context: BinaryOptionMarketContext) -> ConvertedEventStream`
- `build_catalog(stream: ConvertedEventStream, catalog_dir: pathlib.Path) -> CatalogBuildResult`
- `query_catalog(build_result: CatalogBuildResult) -> CatalogQueryResult`
- `run_offline_replay(stream: ConvertedEventStream, catalog_dir: pathlib.Path) -> NautilusReplayReceipt`

All inputs are typed, validated, repo-controlled values; raw file paths are input-only and
never enter logical identity or public output. Every public input/result is
`@dataclass(frozen=True)`; no public mutable `dict`/`list` is exposed.

## Public dataclasses (frozen — exact fields)

- `BinaryOptionMarketContext`: `condition_id`, `outcome_token_id`, `outcome_label`,
  `description`, `activation_ns`, `expiration_ns`, `price_increment`, `size_increment`,
  `maker_fee`, `taker_fee`, `ts_event_ns`, `ts_init_ns`.
- `PmxtV2ReplaySource`: `descriptor`, `source_files`.
- `NautilusRuntimeCompatibilityResult`: `is_valid`, `status`, `error_codes`,
  `nautilus_version`, `python_version`, `advisory_only`, `no_execution_authority`.
- `BinaryOptionMappingResult`: `is_valid`, `status`, `error_codes`, `instrument_id`,
  `price_increment`, `size_increment`, `warnings`, `binary_option`.
- `ConvertedEventStream`: `is_valid`, `status`, `error_codes`, `instrument_id`,
  `source_dataset_kind`, `source_external_dataset_id`, `conversion_policy_version`,
  `ordered_event_digests`, `input_event_counts_by_type`, `tick_size_regime_sequence`,
  `first_event_time_ns`, `last_event_time_ns`, `warnings`, `converted_events`.
- `CatalogBuildResult`: `is_valid`, `status`, `error_codes`, `instrument_registered`,
  `written_delta_count`, `written_trade_count`, `catalog_dir`, `stream_ref_digest`.
- `CatalogQueryResult`: `is_valid`, `status`, `error_codes`, `queried_delta_count`,
  `queried_trade_count`, `round_trip_matches`.
- `NautilusReplayReceipt`: `is_valid`, `status`, `error_codes`, `schema_id`, `schema_version`,
  `source_dataset_kind`, `source_external_dataset_id`, `conversion_policy_version`,
  `nautilus_version`, `instrument_id`, `input_event_counts_by_type`, `first_event_time_ns`,
  `last_event_time_ns`, `tick_size_regime_sequence`, `replay_processed_event_count`,
  `replay_digest`, `warnings`, `execution_authority`.

`converted_events` is an identity-excluded tuple carrying, in order, the Nautilus
`BinaryOption` instrument definition followed by the canonical ordered market-data objects.
Each source `book` event is exactly one Nautilus `OrderBookDeltas` snapshot (a `CLEAR`
followed by the canonical bid/ask level deltas); each `price_change` is one `OrderBookDelta`;
each `last_trade_price` is one `TradeTick`. A level whose size is `0` is a `DELETE` and a
negative size fails closed, for both a `book` level and a `price_change`; a positive size is a
snapshot rebuild `ADD` within a `book` and an incremental `UPDATE` for a `price_change`. The `OrderBookDeltas` snapshot is the public semantic: `catalog`
flattens it into its individual `OrderBookDelta` rows only for Parquet persistence, while
`replay` keeps the whole `OrderBookDeltas` as one semantic replay object so the engine-observed
order can be verified. `replay_processed_event_count` is the semantic replay-event count
(book + price_change + last_trade_price source events; `tick_size_change` is regime metadata
and produces no engine event). Engine-order parity compares an exact per-event semantic-token
trace (event kind plus the per-event `sequence` for order-book events or the deterministic
`TradeId` for trades, with `ts_init`/`ts_event`) against the declared canonical order; any
divergence, or a declared-count reconciliation failure, fails closed
`NAUTILUS_REPLAY_PARITY_INVALID`.

## External-dataset provenance (bound to WP167)

The replay source is the WP167 public `ExternalDatasetDescriptor` plus its
`PmxtV2SourceFile` tuple. Before conversion the descriptor `provider_id`, `dataset_name`,
`dataset_version`, `source_class`, `importer_id`, `importer_version`,
`source_timestamp_semantics`, and `receive_timestamp_semantics` must equal the WP167 pmxt-v2
constants; every source
file maps to exactly one descriptor source object by identical `object_name` and
`partition_identity` (a strict 1:1 bijection with unique object names, no extra/missing);
and every source file hash is revalidated with `revalidate_pmxt_v2_source_hash`. Failures
fail closed with no raw path/exception echo. The receipt commits exactly
`ExternalDatasetDescriptor.external_dataset_id` as `source_external_dataset_id` with
`source_dataset_kind = "WP167_EXTERNAL_DATASET_DESCRIPTOR"`. WP168 does not generalize to
canonical/analytical sources.

## Deterministic ordering & serialization

Canonical order is receive-time primary, physical-order-independent, total:
`(ts_init, ts_event, event_kind_rank, canonical_row_digest, canonical_row_bytes)`, where
`ts_init` = `timestamp_received` ns and `ts_event` = `timestamp` ns. Frozen `event_kind_rank`:
`book=0`, `price_change=1`, `last_trade_price=2`, `tick_size_change=3`. Byte-identical
duplicate rows are never silently deduplicated; they are expanded with a deterministic
duplicate ordinal `0..N-1` derived from multiplicity, and `source_row_index` is the position
in that canonical expanded sequence — never a filesystem/query/Parquet-physical position.

Canonical row bytes are UTF-8 canonical JSON (sorted keys, compact separators,
`ensure_ascii=false`, `allow_nan=false`): no float; timestamps as UTC integer nanoseconds;
`market` as canonical `0x` + 64 lowercase-hex; `asset_id` as canonical ASCII decimal digits;
decimals as fixed-point text at the documented pmxt-v2 scale; unowned event-specific fields as
explicit null; the context `price_increment`/`size_increment` and every book bid/ask
`price`/`size` string are strict fixed-point decimal text (ASCII digits with an optional
single fractional part — no exponent, leading sign, whitespace, `NaN`/`Infinity`, Unicode
digits, or JSON number), rejected otherwise; book bids/asks as `[["price","size"], ...]` with bids sorted strictly
descending by price and asks strictly ascending, a duplicate price level on one side failing
closed.

## pmxt-v2 event-semantic matrix

Owned fields (required non-null; unowned fields must be null; sides within `BUY`/`SELL`):
`book` owns `bids`, `asks`; `price_change` owns `price`, `size`, `side`, `best_bid`,
`best_ask`; `last_trade_price` owns `price`, `size`, `side`, `fee_rate_bps`,
`transaction_hash`; `tick_size_change` owns `old_tick_size`, `new_tick_size`.

## Tick-size policy

One stable Polymarket economic instrument identity at the finest valid historical price
increment; the exact chronological tick-size regime schedule is committed separately in the
receipt as `tick_size_regime_sequence`. Every validated historical price must be an exact
integer multiple of the finest increment, else conversion fails closed. Tick-size transitions
do not create new economic instrument identities. Deterministic tick-regime segmentation is a
future fallback only and is not implemented here.

## Replay identity constants (literal)

- `CONVERSION_POLICY_VERSION = "wp168-nautilus-pmxt-v2-conversion/1.0.0"`
- `REPLAY_RECEIPT_SCHEMA_ID = "polymarket-nautilus-offline-replay-receipt"`
- `REPLAY_RECEIPT_SCHEMA_VERSION = "1.0.0"`
- `REPLAY_IDENTITY_PREFIX = "nautilusreplay:sha256:"`

`replay_digest` = `REPLAY_IDENTITY_PREFIX` + SHA-256 hex of the canonical-JSON preimage whose
keys are exactly: `conversion_policy_version`, `source_dataset_kind`,
`source_external_dataset_id`, `nautilus_version`, `instrument_semantic_id`,
`ordered_event_semantic_digests` (each per-event `canonical_row_digest` with its duplicate
ordinal), `tick_size_regime_sequence`, and `replay_settings`. Excluded from identity: absolute
paths, temp/output dirs, the caller `catalog_dir`, physical Parquet bytes/row positions,
wall-clock time, environment identifiers, CI run ids, hostnames, and raw exception text. The
digest is sensitive to duplicate multiplicity and to `external_dataset_id`/source-hash
mutation, and insensitive to arbitrary physical ordering.

## Error taxonomy & precedence

Fixed product error precedence (public invalid results carry no raw exception, path, source
payload, credentials, or free-form metadata; codes returned deduplicated in this order):

1. `NAUTILUS_RUNTIME_UNSUPPORTED`
2. `NAUTILUS_DEPENDENCY_VERSION_INVALID`
3. `NAUTILUS_IMPORT_UNAVAILABLE`
4. `NAUTILUS_INSTRUMENT_MAPPING_INVALID`
5. `NAUTILUS_EVENT_CONVERSION_INVALID`
6. `NAUTILUS_CATALOG_WRITE_INVALID`
7. `NAUTILUS_CATALOG_QUERY_INVALID`
8. `NAUTILUS_REPLAY_INVALID`
9. `NAUTILUS_REPLAY_PARITY_INVALID`

## Successor boundaries

WP169 (public realtime WebSocket + public activity/wallet data plane) and WP170
(leakage-safe experiment registry & research-dataset OS) remain separately gated.
Executable-edge simulation, deterministic risk/reconciliation, paper, and live remain later
separately gated work.
