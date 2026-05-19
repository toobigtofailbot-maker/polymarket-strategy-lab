# Polymarket Client Boundary Review

## Purpose

WP14 defines strict boundaries for any future official Polymarket client evaluation. These boundaries prevent the official client from being installed, imported, initialized, or used casually in runtime paths.

## Public read-only boundary

`src/data_layer/polymarket/public_client.py` remains the active read-only stdlib public adapter.

The active adapter may read public market metadata, order books, prices, and spreads according to previously approved read-only data-layer rules. It has no credential, signing, account, order, execution, strategy, backtest, scheduler, database, or live-trading authority.

## Official client dependency boundary

No official Python CLOB client package is installed in WP14.

No source file may import `py_clob_client_v2` until an approved future work package adds dependency evaluation. No source file may import the archived `py_clob_client` package at all.

Any future dependency proposal must be isolated, explicit, pinned, security-scanned, reviewed in a dedicated PR, and approved before runtime use.

## Authenticated client boundary

Authenticated client setup is forbidden until an approved future work package explicitly authorizes it.

No source file may create a `ClobClient` with a key, signer, or credentials. No source file may create or derive API credentials. No source file may initialize L1 or L2 authenticated client behavior.

## Credential boundary

No source file may read `.env`, `PK`, `PRIVATE_KEY`, `CLOB_API_KEY`, `CLOB_SECRET`, `CLOB_PASS_PHRASE`, wallet keys, mnemonic material, or passphrases.

Credential handling requires a future approved credential/key boundary work package before any source code is added.

## Private-key and wallet boundary

Private keys, wallet keys, session signers, funder addresses, deposit-wallet signing, mnemonic material, and passphrases are outside WP14 scope and remain forbidden in source/runtime paths.

## Signing boundary

Order signing and EIP-712 signing are protected execution-adjacent behavior. Signing code must not be added outside a future approved work package that covers credential handling, key custody, risk controls, execution gateway boundaries, and live-trading authorization state.

## Order-placement boundary

Order placement and cancellation are forbidden. No source file may add order methods or wrappers that create, sign, submit, post, cancel, or execute trades.

## Account/trade-history boundary

Private account, balance, allowance, open-order, and trade-history queries are authenticated behavior. They remain forbidden until a future approved work package explicitly scopes credential handling and account-data boundaries.

## Future sandbox evaluation boundary

Any future official-client experiment must be isolated from runtime paths, dev-only, read-only first, explicit-network only, no credentials, no private keys, no account/trade endpoints, security-scanned, and reviewed through a dedicated work package and PR.

The first acceptable evaluation shape is a sandbox that can inspect public market data only, behind an adapter boundary, with tests proving that authenticated methods are not reachable.

## Future execution gateway boundary

The future execution gateway remains the only possible order authority, and it does not exist in WP14. Official client code must not bypass the execution gateway, OMS, reconciliation, risk caps, bounded overlay semantics, safe mode, configs, or live-trading authorization rules.

## Future risk-engine dependency

No official client integration may place, cancel, sign, or submit orders unless a future deterministic risk engine and execution gateway explicitly approve the action path. AI, Hermes, Codex, strategy modules, and data-layer tools must not override risk decisions.

## Prohibited imports and method names

Prohibited imports in source/runtime paths:

- `py_clob_client`
- `py_clob_client_v2`

Prohibited method names in source/runtime paths:

- `create_and_post_order`
- `create_and_post_market_order`
- `create_order`
- `post_order`
- `submit_order`
- `cancel_order`
- `sign_order`
- `execute_trade`
- `buy`
- `sell`

## CI/test expectations

Tests must assert:

- The official client dependency is not added in WP14.
- No `py_clob_client_v2` imports exist in source/runtime files.
- No credential/private-key/auth/order method names are introduced.
- Future official-client evaluation tests are explicit-network only and no-credential until a later approved work package changes repo truth.
- Generated artifacts, local snapshot/catalog/report/export outputs, lock files, dependency files, and external repo source are not committed as part of WP14.

## Review checklist additions

Future reviews must check:

- Official client dependency not installed?
- No `py_clob_client_v2` imports?
- No private-key, wallet, or API credential handling?
- No authenticated client setup?
- No order placement, cancellation, or signing methods?
- Client decision docs updated?
- Archived old client marked avoid?
- V2 client marked candidate only?

## Safety statement

WP14 keeps the official client absent. Live trading remains disabled. Authentication, credentials, private keys, signing, order placement, order cancellation, account data, trade history, execution, OMS, reconciliation, risk caps, configs, scheduler behavior, bot loops, database support, strategy signals, trade proposals, backtesting, paper trading, and deployment setup remain outside scope and unimplemented.
