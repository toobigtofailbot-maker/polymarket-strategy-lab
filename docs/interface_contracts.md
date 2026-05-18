# Interface Contracts

## Purpose

This document records conceptual interface contracts for future work. These are markdown-only draft contracts, not executable schemas, runtime types, validators, API clients, or trading logic.

## TradeProposal Draft Fields

- proposal_id
- strategy_id
- market_id
- venue
- side
- price
- size
- rationale
- source_snapshot_id
- created_at
- expires_at

## RiskDecision Draft Fields

- decision_id
- proposal_id
- status
- reason
- approved_price
- approved_size
- risk_limits_checked
- decided_at

## MarketSnapshot Draft Fields

- snapshot_id
- venue
- market_id
- condition_id
- best_bid
- best_ask
- last_price
- liquidity
- captured_at

## WalletSignal Draft Fields

- signal_id
- wallet_identifier
- venue
- market_id
- observed_action
- confidence
- source
- observed_at

## PaperOrder Draft Fields

- paper_order_id
- proposal_id
- decision_id
- market_id
- side
- price
- size
- simulated_status
- simulated_at

## ExecutionIntent Draft Fields

- intent_id
- proposal_id
- decision_id
- mode
- venue
- order_action
- price
- size
- created_at

## Contract Rules

- These contracts do not authorize implementation.
- These contracts do not authorize live execution.
- Future executable schemas require a later approved work package.
- Future venue-specific fields must remain behind internal adapters.
