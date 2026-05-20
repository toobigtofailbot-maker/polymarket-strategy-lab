# Polymarket Read-Only Polling Policy

## Purpose

WP16 defines a conservative, local, deterministic policy and rate-limit guard for future public market-data polling. It prepares the repo for a later bounded read-only runner without adding that runner in this work package.

## WP16 scope

WP16 adds offline policy source, an offline rate-limit guard, an offline policy inspection CLI, tests, and repo-truth updates.

WP16 does not add automated polling.
WP16 does not add a live scanner.
WP16 does not call Polymarket APIs.
WP16 does not create network requests.
WP16 does not add a scheduler, daemon, background worker, or bot loop.
WP16 does not create strategy signals or trade proposals.
WP16 does not place, cancel, sign, submit, buy, sell, or execute orders.
WP16 does not authenticate.
WP16 does not read credentials or `.env`.

Existing manual capture/probe tools remain manual; WP16 does not convert them into automatic processes.

## Current active public-data path

The current active runtime public-data path remains the standard-library read-only public adapter under `src/data_layer/polymarket/public_client.py`. WP16 does not replace it, wrap it in a runner, or schedule it.

## Official-client sandbox status

The official Python client remains sandbox-candidate-only and is not a project dependency. The WP15 sandbox stays under `tools/polymarket/official_client_sandbox/`, remains manual and explicit-network, and has no runtime authority.

## Why polling policy comes before polling implementation

Repeated public-data polling can create operational and venue-risk pressure even when it is read-only. The repo needs local budgets, endpoint classes, validation, and guard enforcement before a future WP can add any repeated request mechanism.

## Rate-limit uncertainty

WP8-D002 remains OPEN unless authoritative rate-limit evidence is added. WP16 adds no authoritative venue evidence and does not overclaim confirmed Polymarket rate limits.

Treat all limits as local safety budgets, not confirmed venue limits. Future higher-frequency polling requires authoritative documentation and/or controlled probe evidence promoted into repo truth.

## Conservative default policy

The default policy is manual-bounded-only:

- Automated loops are disabled for every endpoint class.
- Future external endpoint classes require explicit-network approval.
- Future network actions are disabled by default.
- No production or live polling defaults exist.
- Budgets are intentionally low until real rate-limit behavior is confirmed.

## Endpoint classes

WP16 defines policy entries for:

- `gamma_markets`
- `gamma_market_detail`
- `clob_book`
- `clob_price`
- `clob_spread`
- `clob_midpoint`
- `manual_snapshot_capture`
- `sandbox_probe`

These are planning classes only. They do not execute requests.

## Request-budget model

Each endpoint class has:

- a maximum local request count,
- a rolling window in seconds,
- a minimum interval in seconds,
- optional run bounds for markets or tokens,
- explicit-network requirements,
- disabled automated-loop authority.

No endpoint should run unbounded. No polling runner should be allowed without a kill switch and clear log output.

## Burst behavior

The default WP16 policy does not depend on bursts. The rate-limit guard supports an optional burst capacity for future planners, but future use must remain bounded, observable, and below the configured rolling-window budget.

## Minimum interval model

Minimum intervals are enforced per endpoint key by the local guard. Request planners must ask the guard before any future public request and record allowed attempts so the next decision is deterministic.

## Jitter/backoff guidance

Future polling must use jitter to avoid synchronized request bursts. Jitter must never shorten a configured minimum interval below the local policy floor.

Future polling must prefer low-frequency polling until real rate-limit behavior is confirmed. Never retry aggressively.

## HTTP 429 handling requirement

Any future runner must stop or back off on HTTP 429. A 429 response must not trigger aggressive retry behavior. The runner must log the endpoint class, configured budget, and next allowed local time.

## HTTP 5xx handling requirement

Any future runner must back off on HTTP 5xx responses, keep retries bounded, and avoid treating server errors as a reason to increase request frequency.

## Network failure handling requirement

Any future runner must handle network failures as non-fatal read-only failures, keep retries bounded, and produce clear log output. Network failure must not authorize strategy, execution, database, or live-trading behavior.

## No scheduler/bot-loop guarantee

WP16 adds no scheduler, daemon, background worker, long-running process, or bot loop. The manual CLI validates local policy and exits.

## No trading/strategy authority

The WP16 policy and guard have no strategy, execution, order-management, reconciliation, risk, paper-trading, backtesting, or live-trading authority. They do not create signals or trade proposals.

## Future polling runner requirements

Future polling must be explicit-network, bounded, observable, and guard-enforced.

A future approved runner must:

- require an explicit network opt-in,
- load conservative endpoint policy,
- ask the rate-limit guard before each request,
- record allowed attempts,
- enforce per-run market/token bounds,
- include a kill switch,
- log request decisions and backoff decisions,
- remain read-only,
- avoid credentials and authentication,
- avoid strategy and execution behavior.

Future polling runner may not bypass the WP16 rate-limit guard.

## Deferred item impact

WP8-D002 remains OPEN because rate-limit policy is not confirmed.

WP16 adds WP16-D001 because a read-only polling runner is not implemented yet.

WP16 adds WP16-D002 because the budgets are conservative local policy, not confirmed venue limits.

## Next WP recommendation

Recommended next WP: WP17 - Controlled Read-Only Market Data Polling Runner, if WP16 succeeds and the runner remains manual, explicit-network, bounded, observable, and guard-enforced.

Fallback next WP: WP17 - Polling Policy Follow-Up, if rate-limit guard or policy issues remain.

## Safety statement

WP16 is policy-and-guard-only. It makes no network calls, installs no runtime dependency, adds no database, adds no scheduler, adds no scanner, and adds no trading behavior.
