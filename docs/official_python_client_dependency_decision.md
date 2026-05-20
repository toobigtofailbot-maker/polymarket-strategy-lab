# Official Python Client Dependency Decision

## Purpose

WP14 records the official Polymarket Python CLOB client dependency decision before any dependency installation, authenticated client setup, order placement, signing, or live/API execution work.

This document is repo truth for future work packages. It does not authorize runtime integration.

## WP14 scope

WP14 is documentation and tests only. It reviews the official Python client choice, records boundary rules, updates repo-truth status, and adds tests proving that no official client dependency, source import, credential handling, signing, or trading behavior is introduced.

WP14 does not install packages, add dependencies, import official clients, initialize clients, read credentials, sign orders, place orders, cancel orders, query account/trade data, add network calls, add database support, add a scheduler, add a bot loop, add backtesting, add paper trading, add strategy signals, or add trade proposals.

## Sources reviewed

- Polymarket CLOB overview: https://docs.polymarket.com/trading/overview
- Polymarket CLOB V2 migration guide: https://docs.polymarket.com/v2-migration
- Polymarket clients and SDKs documentation: https://polymarket-docs.copilot.markets/api-reference/clients-sdks
- Old official Python client repository: https://github.com/Polymarket/py-clob-client
- Current official Python V2 client repository: https://github.com/Polymarket/py-clob-client-v2

## Candidate clients reviewed

| Client | Package or repo | WP14 classification | Dependency status | Runtime integration status |
|---|---|---|---|---|
| Old official Python client | `py-clob-client`, `Polymarket/py-clob-client` | `DO_NOT_USE_ARCHIVED` | `NOT_INSTALLED` | `NOT_STARTED` |
| Current official Python V2 client | `py-clob-client-v2`, `Polymarket/py-clob-client-v2` | `CANDIDATE_FOR_FUTURE_DEV_ONLY_EVALUATION` | `NOT_INSTALLED` | `NOT_STARTED` |

## Old `py-clob-client` status

Decision: `py-clob-client`: `DO_NOT_USE_ARCHIVED`.

The old official `Polymarket/py-clob-client` repository is archived. Its repository warning says it is no longer maintained, no longer functional, should not be used for new or existing integrations, and points users to the V2 client.

The old package must not be installed, imported, copied, vendored, forked for runtime use, or treated as an active integration candidate.

## Current `py-clob-client-v2` status

Decision: `py-clob-client-v2`: `CANDIDATE_FOR_FUTURE_DEV_ONLY_EVALUATION`.

The current official Python V2 package is `py-clob-client-v2`. Official docs recommend open-source SDK clients for order signing, authentication, and submission. The V2 Python repository is MIT licensed and includes authentication/order examples, which makes it live-capable and credential-sensitive.

WP14 does not approve installation or runtime use. The client remains candidate-only until a later dedicated work package performs security review, dependency pinning, explicit boundary review, and read-only sandbox evaluation.

## Why no dependency is installed in WP14

The official V2 client crosses sensitive boundaries because it supports wallet/private-key signing, API credential derivation, authenticated order placement, cancellation, account data, and trade queries. Installing it casually would make future runtime imports easier without the required security and boundary review.

WP14 is intentionally documentation-only. The decision is to keep dependency installation status: `NOT_INSTALLED`.

## Current active project data path

The active project data path remains the existing Python standard-library public adapter:

- `src/data_layer/polymarket/public_client.py`

That adapter is the only active public Polymarket data path. It is read-only, public-data oriented, and does not use the official client.

## Dependency decision

- `py-clob-client`: `DO_NOT_USE_ARCHIVED`
- `py-clob-client-v2`: `CANDIDATE_FOR_FUTURE_DEV_ONLY_EVALUATION`
- Dependency installation status: `NOT_INSTALLED`
- Runtime integration status: `NOT_STARTED`
- Authenticated client status: `FORBIDDEN_UNTIL_APPROVED_WP`
- Live trading status: `DISABLED`

## Future allowed evaluation path

A future official-client evaluation may be proposed only through a dedicated work package and PR. That evaluation must be:

- Isolated from runtime paths.
- Development-only.
- Read-only first.
- Explicit-network only.
- No-credential and no-private-key.
- Limited to public market data methods.
- Security-scanned before dependency installation or execution.
- Reviewed against runtime, credential, signing, order, risk, and live-trading boundaries.

If dependency installation is proposed later, that work package must update dependency files intentionally, pin versions, run available security tooling, document unavailable tooling honestly, and preserve protected runtime boundaries.

## Future blocked behavior

The following behavior remains blocked until an explicit later work package approves it:

- Installing `py-clob-client-v2`.
- Importing `py_clob_client_v2` from source/runtime code.
- Reading `.env` files or credential environment variables.
- Initializing authenticated CLOB clients.
- Creating or deriving API credentials.
- Handling private keys, wallet keys, mnemonics, or passphrases.
- Signing orders.
- Placing or cancelling orders.
- Querying private account, order, or trade data.
- Adding live/API execution paths.

## Authentication implications

Official docs separate public methods from L1 and L2 authenticated methods. Public methods expose market data, order books, prices, and spreads without authentication.

L1 uses wallet/private-key signing to create or derive API credentials. L2 uses API credentials for order placement, cancellation, trades, and account data. Even with L2 authentication, order creation still requires EIP-712 signing by a private key.

Therefore, authenticated client status remains `FORBIDDEN_UNTIL_APPROVED_WP`.

## Credential/private-key implications

WP14 adds no credential handling. No source file may read `.env`, `PK`, `PRIVATE_KEY`, `CLOB_API_KEY`, `CLOB_SECRET`, `CLOB_PASS_PHRASE`, wallet keys, mnemonic material, or passphrases.

Future credential/key work requires a separate approved credential and private-key boundary work package before any source code is added.

## Trading/order implications

The official V2 client includes order construction and posting examples. Those capabilities are protected execution behavior for this repo.

WP14 adds no order placement, order cancellation, order signing, strategy signal, trade proposal, backtest, paper trade, fill simulation, OMS, reconciliation, risk cap, execution gateway, or live-trading path.

## Security-tool implications

WP14 adds no runtime dependency and no external code. Gitleaks was rerun for this WP. Semgrep and pip-audit remain unavailable if the project-local `.venv-security/` environment is absent; their deferred status must not be treated as a new pass unless they are actually restored and run.

Before any future Python client installation, the dependency-security gates in `docs/deferred_items_log.md` and `docs/security_tooling_status.md` must be checked and either satisfied or explicitly deferred by the user.

## Runtime-boundary implications

The official client is absent from runtime paths. The current stdlib public adapter remains the only active Polymarket data path. Future official-client work must sit behind a read-only adapter boundary first and must not reach execution, OMS, reconciliation, risk caps, bounded overlay semantics, safe mode, configs, or live-trading paths without explicit approval.

## Deferred item impact

WP14 does not resolve the official CLOB client dependency security review. It narrows the decision:

- The archived old Python client is avoided.
- The V2 Python client remains candidate-only.
- Dependency installation and authenticated client integration remain deferred.

## WP15 Addendum

WP15 performs a dev-only read-only sandbox audit under `tools/polymarket/official_client_sandbox/`.

Project-level package installation status remains `NOT_INSTALLED`. WP15 does not add `py-clob-client-v2` to `pyproject.toml`, requirements files, lock files, runtime source paths, or any project dependency file.

Sandbox status: `DEV_ONLY_READ_ONLY_NO_CREDENTIALS`. The sandbox may create an ignored local `.venv-official-client/` only with an explicit setup flag and may install `py-clob-client-v2` only into that ignored venv when an explicit package version is supplied. That sandbox-only install does not resolve project dependency audit status.

Read-only public methods are useful enough to continue evaluating only as an isolated future dev-only experiment. They are not approved for runtime use, and the existing stdlib public adapter remains the active runtime public data path.

## Next WP recommendation

Recommended next WP:

`WP15 - Official Client Read-Only Sandbox Audit`, if the boundary review accepts a dev-only evaluation.

Fallback next WP:

`WP15 - Client Dependency Follow-Up`, if dependency-security tooling, credential/key boundaries, or official-client concerns remain unresolved.

## Safety statement

WP14 is documentation and test coverage only. It adds no trading logic, no strategy signals, no trade proposals, no backtesting, no paper trading, no order placement, no order cancellation, no signing, no authenticated client, no official client dependency, no official client import, no API credentials, no wallet/private keys, no `.env` loading, no live-trading path, no external repo code, no database, no scheduler, no polling loop, no bot loop, no deployment setup, and no network calls.
