# Advisory Runtime Boundary And Consumption Design

## 1. Status

- Design status: DOCS_ONLY_ADVISORY_RUNTIME_BOUNDARY_DESIGN
- Applies to: Codex and Claude Code
- Runtime impact: NO_RUNTIME_CHANGE
- Tooling impact: NO_NEW_TOOLING
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Validation impact: NO_VALIDATION_WEAKENING
- Protected-boundary impact: NO_PROTECTED_BOUNDARY_CHANGE
- Agent runtime impact: NO_AGENT_RUNTIME
- Hermes impact: NO_HERMES_INSTALL_OR_RUNTIME
- LLM/provider impact: NO_LLM_PROVIDER_RUNTIME
- Trading impact: NO_TRADING_EXECUTION

## 2. Purpose

WP39 defines the boundary for future local advisory consumers. It is a
design/orientation package only.

This document does not implement an advisory consumer, runtime, Hermes, LLM,
credentials, trading, database, dashboard, scheduler, polling, command runner,
or product behavior.

The purpose is to define how a later prototype may safely consume existing
local/offline advisory outputs and repo-truth docs while preserving non-
execution boundaries.

## 3. Existing Foundation

The design builds on these existing repo-truth components:

- WP20 advisory-agent policy and `docs/agent_model_registry.md`.
- WP21 context export schema at `docs/agent_context_export_schema.md`.
- WP23 local/offline/read-only context exporter documented in
  `docs/agent_context_exporter.md`.
- WP24 context exporter operator runbook at
  `docs/agent_context_exporter_operator_runbook.md`.
- WP25 deterministic local/offline/read-only report generator documented in
  `docs/agent_context_report_generator.md`.
- WP26 analyst report operator runbook at
  `docs/agent_context_report_operator_runbook.md`.
- WP27 Agent/Hermes manual setup decision record at
  `docs/agent_hermes_manual_setup_decision_record.md`.
- WP38 local advisory handoff package at
  `docs/local_advisory_handoff_package.md`.
- WP28-WP37 token-efficiency helper stack and closeout, including
  `docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md`,
  `tools/git/diff_scope_summary.py`,
  `tools/validation/validation_output_summary.py`,
  `tools/git/code_blast_radius.py`, and `tools/git/status_snapshot.py`.

These components can inform future advisory consumption. They do not grant
runtime, agent, Hermes, LLM, trading, credential, account, scheduler, database,
or dashboard authority.

## 4. Design Boundary

An advisory consumer means a local/offline/read-only process or future runbook
that reads approved local context/report inputs and repo-truth docs, then emits
human-reviewed advisory summaries.

An advisory consumer is:

- not agent runtime;
- not Hermes;
- not LLM/provider runtime;
- not scheduler/bot loop;
- not trading/execution system;
- not database/dashboard;
- not account-connected.

It may summarize and organize local advisory evidence for human review. It must
not make decisions, place orders, mutate configs, approve PRs, or claim merge
readiness.

## 5. Allowed Future Input Sources

Future advisory consumers may read only explicitly scoped, allowlisted local
inputs:

- tracked repo-truth docs listed in `docs/repo_truth_index.md`;
- `docs/agent_context_export_schema.md`;
- `docs/agent_context_exporter.md`;
- `docs/agent_context_report_generator.md`;
- `docs/agent_context_report_operator_runbook.md`;
- local agent context exports only under ignored
  `local_data/agent_context_exports/` when explicitly provided by the operator;
- local agent context reports only under ignored
  `local_data/agent_context_reports/` when explicitly provided by the operator.

Input rules:

- no implicit crawling of `local_data`;
- no arbitrary file reads;
- no network input;
- no GitHub API input;
- no private endpoint input;
- no account input;
- repo truth overrides stale exports and reports.

## 6. Forbidden Input Sources

Future advisory consumers must not read or ingest:

- `.env`, `.env.*`;
- credentials;
- private keys;
- wallet keys;
- mnemonics;
- passphrases;
- tokens;
- account data;
- private endpoint responses;
- authenticated API data;
- authenticated headers;
- arbitrary `local_data` crawling;
- raw security scan outputs;
- official-client sandbox outputs unless separately approved;
- chat/user memory outside repo truth;
- network/GitHub API responses;
- live/paper trading account state;
- order, trade, signing, or wallet execution state.

## 7. Allowed Future Output Types

Allowed future outputs are advisory-only and human-reviewed:

- market-state summary;
- performance review summary;
- research question list;
- strategy hypothesis narrative;
- risk/uncertainty notes;
- Codex/WP planning notes;
- human-review checklist;
- local advisory brief under ignored `local_data/advisory_outputs/` only if
  explicitly scoped later.

Every output must state that it is advisory-only, stale unless verified against
current repo truth, and subject to human review.

## 8. Forbidden Output Types

Future advisory consumers must not emit:

- executable trading signals;
- order instructions;
- order placement/cancellation requests;
- signing requests;
- account actions;
- copy-trading instructions;
- liquidation-sensitive bot parameters;
- position sizing;
- autonomous parameter updates;
- scheduler/bot-loop instructions;
- live/paper trading decisions;
- claims of merge readiness or implementation approval;
- automatic PR approval;
- config mutation instructions;
- credentials, keys, tokens, or private endpoint material.

## 9. Deterministic Local Advisory Model

The first future prototype should be deterministic and local/offline/read-only.

It may parse existing report/export files and produce a bounded advisory brief.
It must not call an LLM. It must not call Hermes. It must not call network. It
must not call account, Polymarket private API, or official authenticated client
paths.

It must not generate orders. It must not generate signals. It must not generate
executable strategy configurations. It must include advisory-only, human-review, and validation reminders.

## 10. Future LLM/Hermes Separation

LLM/Hermes consumption is not authorized by WP39.

Future LLM/Hermes work requires a separate provider/manual setup decision,
security/dependency review, prompt boundary, data-sanitization review, and
runtime authorization.

A deterministic local consumer may be built before any LLM/Hermes integration.
LLM/Hermes must not be treated as required for the first advisory consumer
prototype.

## 11. Security And Sanitization Requirements For Future Prototype

A future prototype must include:

- safe input allowlist;
- output redaction for obvious secrets;
- no arbitrary filesystem reads;
- no network;
- no command execution;
- no credential file reading;
- no generated output committed;
- no private account data;
- no private endpoint data;
- no raw security scan output ingestion;
- clear failures for disallowed paths.

Gitleaks and semgrep remain separate validation. The prototype cannot replace
security checks, dependency review, generated-artifact checks, pytest, human
review, or the final PR comment.

## 12. Human Review And Advisory Framing

Every advisory output must be clearly labeled advisory-only.

Outputs must include uncertainty/assumptions. Outputs must require human
review. Outputs cannot approve trades, PRs, runtime changes, credentials, or
protected work. Outputs cannot decide merge readiness.

Repo truth, required validation, security checks, direct changed-file
inspection, PR review, and human decisions remain authoritative.

## 13. Future WP40 Prototype Requirements

WP40 - Local Advisory Consumer Prototype is the safe next prototype shape if
this design is accepted.

The WP40 prototype must be a local/offline/read-only deterministic advisory consumer prototype.
It reads only explicitly provided local export/report paths under
`local_data/agent_context_exports/` and
`local_data/agent_context_reports/`, plus allowlisted repo-truth docs.

WP40 must preserve:

- no LLM/Hermes/network/account/trading;
- no signal/order output;
- no credential reads;
- no arbitrary filesystem reads;
- no command execution;
- no dependency changes unless separately approved;
- no generated output committed;
- no source/runtime path changes unless a later approved WP changes package
  class and protected-boundary review.

Text/JSON output may be allowed only under an ignored local path if explicitly
requested by that future WP. Tests must cover path restrictions, forbidden
imports, advisory labels, no signal/order output, no credential reads, and no
generated output committed.

## 14. Recommended Implementation Sequence After WP39

1. WP40 - Local Advisory Consumer Prototype, if this design is accepted.
2. WP41 - Advisory Prompt/Runbook Package.
3. WP42 - Provider/Hermes Decision Refresh, only if the user wants LLM/Hermes
   later.
4. Later WPs only after explicit approval: dependency/security review, runtime
   integration design, paper trading design, live authorization.

Do not jump to database, dashboard, strategy runtime, paper trading, live
trading, official-client runtime integration, scheduler, wallet/copy-trading,
production polling, Hermes install, LLM provider runtime, or agent runtime.

## 15. WP40 Implementation Decision

WP40 implements the deterministic local advisory consumer prototype at
`tools/advisory/local_advisory_consumer.py`.

Resolved implementation choices:

- the prototype is local/offline/read-only and standard-library only;
- input files must be explicit paths only;
- context exports are allowed only under `local_data/agent_context_exports/`;
- analyst reports are allowed only under `local_data/agent_context_reports/`;
- default output is stdout only;
- optional output is restricted to `local_data/advisory_outputs/`;
- text and JSON output are supported;
- no LLM, Hermes, network, account, or trading behavior is added;
- generated advisory outputs are ignored local data and must not be committed.

WP40 does not grant runtime, agent, LLM, Hermes, account, trading, scheduler,
database, dashboard, or execution authority. Historical design content above
remains intact and authoritative for future advisory-consumer boundaries.

## 16. WP39 Non-Goals

- no implementation;
- no runtime;
- no Hermes;
- no LLM/provider runtime;
- no credentials;
- no trading;
- no scheduler;
- no database/dashboard;
- no dependency changes;
- no generated outputs;
- no command runner;
- no product behavior.
