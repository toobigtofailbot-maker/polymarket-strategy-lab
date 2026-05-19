# Polymarket Data Semantics

## Purpose

This document defines the canonical terms used when handling Polymarket read-only public data in this project. It extends `docs/data_semantics.md` with Polymarket-specific concepts introduced in WP8.

All terms here describe read-only observations. No term in this document grants order-placement, signing, or trading authority.

## Market Identifiers

| Term | Definition |
|---|---|
| `market_id` | A Polymarket-internal integer or string identifier for a market question. Used in Gamma API paths. May differ from `condition_id`. |
| `condition_id` | A hex-encoded Ethereum condition identifier (e.g. `0xabc...`) used in the CLOB and on-chain. The primary stable identifier for a market. |
| `token_id` | A numeric string (large integer) identifying a specific outcome token within a market. Used in CLOB order-book requests. Each market has one token per outcome (typically two). |
| `asset_id` | Synonym for `token_id` in some API surfaces. |
| `outcome_label` | A human-readable string for an outcome (e.g. `"Yes"`, `"No"`). |

## Market Metadata

| Term | Definition |
|---|---|
| `question` | The text of the market's prediction question. |
| `market_status` | Active, closed, resolved, or paused as reported by the venue. |
| `resolution_date` | The expected or actual date/time at which the market resolves. |
| `liquidity` | Venue-reported measure of available liquidity; read-only observation. |
| `volume` | Venue-reported cumulative trading volume; read-only observation. |
| `category` | Venue-assigned grouping (e.g. sports, politics, crypto). |

## Order-Book Data

| Term | Definition |
|---|---|
| `order_book_snapshot` | A point-in-time read-only record of bids and asks for a specific token. Not an order. Not a trading signal. |
| `bid` | A price/size pair representing the best available buy interest at the venue. Read-only observation. |
| `ask` | A price/size pair representing the best available sell interest at the venue. Read-only observation. |
| `bids` | Ordered list of bid levels from highest price to lowest. |
| `asks` | Ordered list of ask levels from lowest price to highest. |
| `best_bid` | The highest bid price in the snapshot. |
| `best_ask` | The lowest ask price in the snapshot. |
| `mid` | The midpoint between best bid and best ask. Not a venue-provided field; computed locally if needed. |
| `spread` | The difference between best ask and best bid. Computed locally. |
| `price` | A CLOB price expressed as a decimal between 0 and 1, representing implied probability. |
| `size` | A token quantity at a given price level. |

## Timestamps And Staleness

| Term | Definition |
|---|---|
| `snapshot_timestamp` | The UTC datetime when the adapter fetched the snapshot. Recorded by the adapter. |
| `venue_timestamp` | A timestamp returned by the venue API if present. May differ from `snapshot_timestamp`. |
| `staleness` | The age of a snapshot relative to the current time. Used to reject stale data in strategy inputs. |
| `max_staleness_seconds` | A configurable threshold above which a snapshot is considered stale and must not be used in decisions. |

## Provenance

| Term | Definition |
|---|---|
| `source` | The API endpoint and base URL used to retrieve data (e.g. `https://gamma-api.polymarket.com/markets`). |
| `adapter_version` | Identifier for the adapter code that produced the record. |
| `request_info` | A structured record of the HTTP method, URL, query parameters, response code, and latency. For audit and debugging; not for trading. |
| `read_only_provenance` | A marker indicating the record came from a read-only public GET request and has no order-placement authority. |

## What This Data Is Not

- An order book snapshot is not an order.
- A bid or ask observation is not a trade proposal.
- A market metadata record is not authorization to trade.
- Price data is not a signal until processed by an approved strategy module.
- Token IDs are not wallet addresses or private keys.
