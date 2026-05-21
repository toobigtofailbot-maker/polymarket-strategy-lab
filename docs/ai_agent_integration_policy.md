# AI-Agent Integration Policy

## Status

- AI-agent layer status: POLICY_ONLY_NOT_IMPLEMENTED
- Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime status: NOT_STARTED
- Agent context export status: LOCAL_OFFLINE_READ_ONLY_EXPORTER_ON_BRANCH
- Agent context export schema status: POLICY_SCHEMA_DEFINED_EXPORTER_IMPLEMENTED_LOCAL_OFFLINE_READ_ONLY
- Agent report generation status: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Fully autonomous trading agent status: EXCLUDED_FOR_NOW

WP20 records policy only. It does not install Hermes, add an agent runtime, add an agent context exporter, add report generation, add scheduling, add network polling, add credentials, or connect to any account.

WP21 adds `docs/agent_context_export_schema.md` as a schema contract for a local read-only context export. WP23 adds a local/offline/read-only exporter that reads only allowlisted local inputs and writes only under ignored `local_data/agent_context_exports/` when explicitly requested. Agent runtime, Hermes setup, and report generation remain NOT_STARTED. The advisory-only boundary is unchanged.

WP24 adds `docs/agent_context_exporter_operator_runbook.md` for safe manual exporter operation. It does not authorize Hermes runtime use, agent runtime use, or report generation.

WP23 does not add Hermes runtime or dependency, report generation, strategy proposals, account connection, network calls, credentials, execution authority, scheduler, daemon, or bot loop.

## Core Principle

AI-agent, Hermes, Codex, and future LLM layers may observe, summarize, research, and propose only. Deterministic project modules remain responsible for risk, execution, live authorization, and order handling.

Every accepted AI or agent suggestion must become either a human-approved config change or a normal Codex work package reviewed through the repo-truth workflow. No AI agent, Hermes agent, Codex assistant, or future LLM layer may self-apply changes or directly control live trading.

## Allowed Advisory Capabilities

### Read-Only Analysis

A future read-only analyst agent or capability may summarize local repo-approved reports and snapshots after a future exporter exists. It has no network by default and no account connection.

### Performance Review

A future performance review agent or capability is advisory only. It may analyze strategy, paper, or live logs only after such logs exist and after future work packages authorize their schemas. It may not directly stop, start, or change live strategies.

### Market Research

A future market research agent or capability is advisory only. It may produce research candidates after rate-limit and data policies allow it. WP20 authorizes no autonomous scanning loop.

### Strategy Suggestion

A future strategy suggestion or hypothesis capability may draft hypotheses and human-review proposals. WP20 does not authorize executable trade proposals, strategy signals, paper trading, backtesting, or automatic strategy promotion.

### Codex / WP Support

A future Codex / WP support capability may summarize repo truth and draft candidate work packages. It may not approve pull requests, merge, create branches, or execute Codex work autonomously.

## Explicitly Excluded

The following are FORBIDDEN unless a later repo-truth decision explicitly changes the boundary:

- fully autonomous trading agent;
- agent-controlled execution;
- agent-controlled credentials;
- agent-controlled signing;
- agent-controlled autonomous order placement;
- agent-controlled autonomous order cancellation;
- agent-controlled scheduler or bot loop;
- agent-controlled autonomous parameter application;
- agent-controlled live authorization.

## Staging

- WP20: policy, docs, and tests only.
- WP21: local read-only agent context export schema, still no runtime Hermes dependency.
- WP23: local/offline/read-only context exporter, still no runtime Hermes dependency and no report generation.
- Later: performance review after paper, strategy, or live logs exist and are authorized.
- Later: market research after rate-limit and data policy is stronger.
- Later: strategy suggestion only with evidence, replay, and paper review.
- Later: parameter recommendation remains delayed and advisory-only.
- Fully autonomous trading remains excluded until explicitly revisited in repo truth.

## Risks

- prompt injection;
- false confidence;
- stale context;
- agent drift;
- credential leakage;
- unauthorized command execution;
- scope creep from advisory to execution;
- overfitting or narrative-driven strategy suggestions.

