# Architecture Skeleton

## Purpose

This document defines the WP3 non-runtime architecture skeleton. It records intended module boundaries without implementing trading logic, venue integration, dependency installation, database behavior, dashboards, or live execution.

No external repo code is approved for runtime use by WP3.

## Skeleton

| Layer | Purpose | WP3 status |
|---|---|---|
| Shared data layer | Defines common market, wallet, proposal, and decision concepts for later implementation. | Documentation-only. |
| Strategy modules | Produce trade proposals from approved data inputs. | Documentation-only; strategies may propose trades only. |
| Signal/proposal layer | Carries strategy output toward deterministic review. | Documentation-only. |
| Deterministic risk engine | Evaluates proposals and returns deterministic approval or rejection decisions. | Documentation-only; cannot be overridden by AI, Hermes, Codex, or strategies. |
| Execution gateway | Future sole authority for order creation, submission, cancellation, and reconciliation after risk approval. | Documentation-only; no live authority in WP3. |
| Paper trading engine | Future simulator for non-live order behavior and performance review. | Documentation-only; no real order authority. |
| Monitoring/dashboard layer | Future read-only operational visibility, reports, and alerts. | Documentation-only; no control authority. |
| Deferred live execution | Future live path gated by authorization, risk controls, kill-switches, and security review. | Disabled. |

## Authority Rules

- Strategies produce proposals only.
- The risk engine decides deterministically.
- The execution gateway is the only future order authority.
- No module has live execution authority in WP3.
- No API client, venue adapter, wallet signer, bot loop, database, or dashboard implementation exists in WP3.
- No external repo code is approved for runtime use by WP3.
