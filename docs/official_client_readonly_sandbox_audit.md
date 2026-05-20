# Official Client Read-Only Sandbox Audit

## Purpose

WP15 creates a strictly isolated, development-only sandbox to evaluate whether the current official Python V2 CLOB client candidate could be useful for public read-only market data in a future work package.

This audit does not authorize runtime use.

## WP15 Scope

WP15 adds documentation, tests, and sandbox tooling under `tools/polymarket/official_client_sandbox/`.

WP15 does not add runtime source code, database support, dashboard support, scheduler behavior, bot loops, strategy signals, trade proposals, backtesting, paper trading, order simulation, order placement, order cancellation, signing, authenticated client setup, or live-trading paths.

## WP14 Dependency Boundary Inherited

WP15 inherits the WP14 decision:

- Old `Polymarket/py-clob-client` remains `DO_NOT_USE_ARCHIVED`.
- Current `py-clob-client-v2` remains `CANDIDATE_FOR_FUTURE_DEV_ONLY_EVALUATION`.
- The official client is not installed as a project dependency.
- No official client import exists under `src/`.
- Authenticated client setup remains forbidden.
- Credential, private-key, signing, order, account, and trade behavior remain forbidden.
- The existing stdlib public adapter remains the active runtime public Polymarket data path.

## Sandbox Directory

Sandbox tooling is isolated under:

`tools/polymarket/official_client_sandbox/`

Official-client imports are permitted only inside this sandbox tooling and only when a local sandbox package exists.

## Sandbox Environment Path

The local sandbox virtual environment path is:

`.venv-official-client/`

That path is ignored by git and protected by the generated artifact guard. It must not be committed.

## Package Candidate

The only candidate package for this sandbox is:

`py-clob-client-v2`

WP15 does not install `py-clob-client-v2` as a project dependency.

## Version Resolution / Pinning Approach

WP15 does not pin or add the package to project dependency files.

The setup script requires an explicit `--package-version` when `--install-package` is used. This prevents accidental floating installation in the sandbox and keeps project-level dependency status unchanged.

## Installation Status

Project-level installation status: `NOT_INSTALLED`.

Sandbox installation status for this work package: not required for automated tests. The sandbox scripts can create `.venv-official-client/` and install an explicit version locally if a developer chooses to run that command, but the venv and package are ignored local artifacts.

## Dependency Audit Status

Gitleaks was rerun in WP15. A historical documentation false positive in `docs/deferred_items_log.md` was handled with a narrow `.gitleaks.toml` allowlist scoped to the exact documentation phrase and path; the rerun then passed.

Semgrep and pip-audit were unavailable because `.venv-security/` is absent. They were not newly passed in WP15.

No pip-audit run was performed against `.venv-official-client/` because the official-client sandbox package was not installed during the required default command path.

## Public Read-Only Methods Considered

The sandbox inspection script searches for likely public read-only methods such as:

- `get_markets`
- `get_sampling_markets`
- `get_market`
- `get_order_book`
- `get_order_books`
- `get_price`
- `get_prices`
- `get_spread`
- `get_midpoint`
- `get_midpoints`

If the package API shape differs, the sandbox reports the mismatch rather than forcing authenticated behavior.

## Authenticated Methods Explicitly Excluded

The sandbox treats live-capable and authenticated method names as excluded capabilities. Their presence in the official package is expected and does not make them usable in this repo.

Excluded behavior includes authenticated client construction, API credential derivation, account queries, balance queries, open-order queries, trade-history queries, order creation, order signing, order posting, order cancellation, buy, sell, submit, and execution behavior.

## Credential/Private-Key/Signing Boundary

WP15 does not create authenticated clients.

WP15 does not read credentials or `.env`.

WP15 does not handle private keys, wallet keys, mnemonics, API keys, passphrases, or secrets.

WP15 does not sign or place/cancel orders.

WP15 does not query private account/trade/order endpoints.

## Network Behavior

Network access is optional and gated by `--allow-network`.

Default sandbox commands do not make network calls. Automated tests must not require live network or package installation.

WP15 may only inspect or probe public read-only market data.

## Local Output Behavior

Sandbox outputs are local generated artifacts only. They are ignored under:

- `official-client-sandbox-output/`
- `local_data/polymarket/official_client_sandbox/`

The default commands do not write output. The optional probe writes sanitized summaries only when an explicit output flag is passed.

## Runtime Integration Status

WP15 does not authorize runtime use.

WP15 does not import official client packages under `src/`.

The existing stdlib public adapter remains the active runtime path.

Official-client sandbox tooling has no strategy, execution, risk, OMS, reconciliation, storage, dashboard, scheduler, bot-loop, backtesting, paper-trading, or live-trading authority.

## Findings

Fact: The sandbox directory and scripts exist under `tools/polymarket/official_client_sandbox/`.

Fact: `.venv-official-client/` and sandbox output paths are ignored and guarded as generated local artifacts.

Fact: The setup script creates or installs only when explicit flags are passed and requires an explicit package version for installation.

Fact: The offline inspection script refuses package inspection outside `.venv-official-client/`.

Fact: The read-only probe exits before package import, client construction, or network calls unless `--allow-network` is passed.

Inference: The official client remains suitable only for future dev-only evaluation until an approved dependency/security work package pins and audits it as a project dependency.

Decision: WP15 keeps `py-clob-client-v2` project-level status as `NOT_INSTALLED`.

## Deferred Item Impact

WP14-D001 remains `OPEN`: sandbox-only installation, if performed locally, does not resolve project dependency pinning or audit.

WP14-D002 remains `BLOCKED`: no credential/key/security boundary exists and authenticated behavior remains forbidden.

WP14-D003 moves to `READY_FOR_WP` because the isolated read-only sandbox exists, is tested, and has no runtime/auth/trading boundary violation.

WP15-D001 is added because the official client sandbox API shape remains not fully confirmed unless a future run installs an explicit version and records inspection/probe evidence.

WP15-D002 is added because the official client package is not audited as a project dependency.

## Next WP Recommendation

Recommended next WP:

`WP16 - Official Client Sandbox Follow-Up`, if a developer installs a pinned sandbox version and the API shape or optional probe remains inconclusive.

Alternative next WP:

`WP16 - Read-Only Live Market Data Polling Policy And Rate-Limit Guard`, if the decision is to continue with the existing stdlib adapter and keep the official client optional.

## Safety Statement

WP15 adds no trading logic, no strategy signals, no trade proposals, no backtesting, no paper trading, no order placement, no order cancellation, no signing, no authenticated client, no official client project dependency, no official client import under `src/`, no API credentials, no wallet/private keys, no `.env` loading, no live-trading paths, no external repo code, no runtime dependency, no database support, no scheduler, no polling loop, no bot loop, and no deployment setup.
