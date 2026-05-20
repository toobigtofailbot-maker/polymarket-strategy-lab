# Polymarket Read-Only Polling Runner

## Purpose

WP17 adds the first controlled manual runner for bounded public market-data polling. It exists to validate a finite public read-only path on top of the WP16 polling policy and local rate-limit guard.

## WP17 scope

WP17 adds a manual finite read-only polling runner only. It does not add automated polling. It does not add a scheduler, daemon, background worker, or bot loop. It does not add strategy signals or trade proposals. It does not add backtesting or paper trading.

## Current active public-data path

The active path remains the standard-library `PolymarketPublicClient` under `src/data_layer/polymarket/`. WP17 uses the existing Gamma `/markets` adapter method and, when explicitly configured with token IDs, the existing CLOB `/book` adapter method. CLOB `/health` is not used.

## WP16 policy/guard dependency

The runner depends on `default_polling_policy()` and `RateLimitGuard` from WP16. The WP16 policy remains the local source for per-endpoint budgets and per-run market/token bounds.

## Explicit-network requirement

WP17 default CLI behavior makes no network calls. WP17 network behavior requires `--allow-network`. Without that flag, the CLI validates policy, shows the finite plan, emits a dry-run summary, and exits.

## Finite-run guarantee

The runner builds one finite request plan from the CLI/config and exits after that plan is handled. There is no recurring loop, retry loop, daemon behavior, service behavior, or background process.

## Per-run bounds

The runner caps Gamma market list size by the lower of CLI `--markets-limit` and the WP16 `gamma_markets.max_markets_per_run` policy. Optional order-book calls are capped by the lower of CLI `--order-books-limit`, provided token IDs, and the WP16 `clob_book.max_tokens_per_run` policy. The CLI default for order books is zero.

## Rate-limit guard enforcement

When `--allow-network` is present, the runner calls `RateLimitGuard.record_allowed()` before each public adapter call. If the guard denies the call, the client is not called and the summary records the denial reason and retry-after value.

## Request outcome logging

The run summary records the bounded plan, guard decisions, outcome labels, HTTP status codes when available, public item counts, and start/completion timestamps. It does not store raw large API payloads.

## HTTP 429 behavior

HTTP 429 is recorded as a rate-limit outcome and ends the finite run. The runner does not retry aggressively and does not sleep.

## HTTP 5xx behavior

HTTP 5xx is recorded as a server-error outcome and ends the finite run. The runner does not retry aggressively and does not sleep.

## Network failure behavior

Network and read-only adapter failures are recorded in the structured summary and end the finite run. The runner does not escalate into repeated probing.

## Local output behavior

The CLI writes no file by default. If `--json-out` is passed, output must be under `local_data/polymarket/polling_runs/`, which is protected by the existing `local_data/` ignore rule. Output is a sanitized summary only.

## No scheduler/bot-loop guarantee

WP17 does not add automated polling. WP17 does not add a scheduler, daemon, background worker, service, bot loop, while-true loop, or time.sleep loop. Future scheduled or continuous polling requires a separate approved WP.

## No trading/strategy authority

WP17 does not place, cancel, sign, submit, buy, sell, or execute orders. It does not add strategy signals or trade proposals. It does not add backtesting, paper trading, fill simulation, OMS, execution gateway, risk-engine changes, private account querying, private trade querying, or private order querying.

## No credential/authentication authority

WP17 does not authenticate. WP17 does not read credentials or `.env`. It adds no private keys, wallet keys, mnemonics, passphrases, API keys, tokens, authenticated headers, or credential path.

## Official client boundary

WP17 does not import or install the official client. The official Python client remains sandbox-candidate-only and is not a project dependency.

## Deferred item impact

WP8-D002 remains OPEN because venue rate limits remain unconfirmed. WP16-D002 remains OPEN because WP16 budgets are conservative local policy, not confirmed venue limits. WP16-D001 is resolved for the manual bounded runner condition because the runner is explicit-network, bounded, guard-enforced, logged, tested, and has no trading authority.

## Next WP recommendation

If WP17 issues remain, the next WP should be a read-only polling runner follow-up. If WP17 succeeds, a possible later WP is snapshot capture integration with the guarded runner, still without database, scheduler, strategy, or trading authority.

Future higher-frequency polling requires authoritative rate-limit evidence and repo-truth updates. Future scheduled or continuous polling requires a separate approved WP with observability, kill switch, and safety-boundary updates.

## Safety statement

WP17 is dev-only manual public-data tooling. It does not authorize live trading, automated polling, production scanning, authenticated API use, or any execution path.
