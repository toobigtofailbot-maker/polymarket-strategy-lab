# Wallet Trade Event Snapshot Schema

## Purpose

WP78 defines a local/offline wallet trade event snapshot fixture shape and a
small local loader/validator.

A wallet trade event snapshot is an advisory observation that a wallet-like
identifier was observed in relation to a market-like identifier at a historical
timestamp with direction, price, and size context. It is not a trade signal,
copied order, wallet skill claim, copyability result, paper trade, or live
trade.

WP78 adds no Polymarket wallet API client, no network ingestion, no credentials,
no wallet monitoring, no scheduler, no dashboard, no wallet skill profiler, no
copyability simulation, no wallet intelligence report generator, no research
queue integration, no paper-trading behavior, and no live execution.

## Required Shape

The static design example is:

- `docs/schemas/wallet_trade_event_snapshot_v1.example.json`

Required top-level sections:

- `_notice`
- `_schema_version`
- `_status`
- `event`
- `wallet_reference`
- `market_reference`
- `observation`
- `context`
- `review`
- `safety`

Required logical event fields:

- `schema_version`
- `event_id`
- `source_type`
- `source_id`
- `observed_at_utc`
- `wallet_id_or_address`
- `market_id`
- `condition_id`
- `market_category`
- `direction_observed`
- `price_observed`
- `size_observed`
- `asset_id`
- `outcome_label`
- `liquidity_context_available`
- `orderbook_context_available`
- `copyability_context_available`
- `suspicious_flow_flag`
- `human_review_required`
- `advisory_only_notice`
- `safety`

## Allowed Source Types

Allowed `source_type` values:

- `LOCAL_FIXTURE`
- `MANUAL_RESEARCH_ENTRY`
- `SANITIZED_EXPORT`
- `SYNTHETIC_TEST_FIXTURE`

Forbidden source types:

- `LIVE_API`
- `AUTHENTICATED_API`
- `WALLET_MONITOR`
- `ORDER_FEED`
- `EXECUTION_FEED`

A future work package that authorizes wallet API or network ingestion must
define a separate contract. WP78 does not authorize it.

## Direction Values

Allowed `direction_observed` values:

- `YES_OBSERVED`
- `NO_OBSERVED`
- `UNKNOWN_OBSERVED`
- `HISTORICAL_OBSERVATION_ONLY`

These values are historical observations only. The validator rejects trade-like
direction values such as `BUY`, `SELL`, `LONG`, `SHORT`, `ENTER`, `EXIT`, and
`TRADE`.

## Safety Flags

Every valid record must include these safety flags set to `true`:

- `manual_research_only`
- `not_automated_copy_trading`
- `no_live_execution`
- `no_order_placement`
- `no_position_sizing`
- `no_risk_override`
- `no_parameter_auto_change`

These flags mean the snapshot has no execution authority, no copy-trading
authority, no sizing authority, no risk authority, and no parameter-changing
authority.

## Validation Behavior

The validator:

- accepts one mapping that follows the WP78 snapshot shape;
- checks required sections and required fields;
- checks the expected schema version;
- checks allowed source types;
- checks allowed historical direction values;
- checks boolean context and review flags;
- checks safety flags are present and true;
- rejects forbidden trade-like keys such as `position_size`, `expected_return`,
  `execute`, and `auto_copy`;
- rejects credential-like keys such as `api_key`, `private_key`, `secret_key`,
  `wallet_private_key`, `seed_phrase`, and `passphrase`;
- returns `WALLET_TRADE_EVENT_FIXTURE_VALID` or
  `WALLET_TRADE_EVENT_FIXTURE_INVALID`.

The validator does not compute wallet skill, wallet rank, copyability PnL,
delayed-copy outcome, research-priority boost, trade edge, expected return,
position size, win rate, strategy result, paper PnL, or live PnL.

## Loader Behavior

The loader accepts explicit local paths only:

- a single JSON object representing one wallet trade event record;
- a JSON list of wallet trade event records;
- a directory containing direct-child `*.json` files.

Directory loading is deterministic:

- only direct-child `*.json` files are loaded;
- files are sorted by filename;
- non-json files are ignored without being read;
- nested directories are not scanned.

The loader rejects or records loader-level errors for:

- missing paths;
- unsupported file extensions;
- invalid JSON;
- JSON list entries that are not objects;
- URL-like inputs including `http://`, `https://`, `ws://`, `wss://`, and
  `ftp://`.

The loader may read an explicit operator-provided path under `local_data/` only
when that exact path is passed by the caller and the file is not committed. It
does not auto-scan `local_data/`.

## Boundaries

WP78 is local/offline/read-only. It adds no runtime network behavior, no API
polling, no authenticated account access, no credentials, no scheduler, no
dashboard, no bot loop, no Hermes/LLM execution authority, no paper-trading
strategy, no live trading, no order placement, no cancellation, no position
sizing, no risk override, and no parameter auto-change.

Research/workbench artifacts created by this schema have no execution authority
unless a later approved work package explicitly promotes them through repo-truth
review.
