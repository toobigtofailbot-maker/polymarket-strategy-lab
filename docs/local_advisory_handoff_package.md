# Local Advisory Handoff Package

## 1. Status

- Handoff status: DOCS_ONLY_LOCAL_ADVISORY_HANDOFF
- Applies to: Codex and Claude Code
- Runtime impact: NO_RUNTIME_CHANGE
- Tooling impact: NO_NEW_TOOLING
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Validation impact: NO_VALIDATION_WEAKENING
- Protected-boundary impact: NO_PROTECTED_BOUNDARY_CHANGE
- Agent runtime impact: NO_AGENT_RUNTIME
- Hermes impact: NO_HERMES_INSTALL_OR_RUNTIME
- Trading impact: NO_TRADING_EXECUTION

## 2. Purpose

WP38 resumes the advisory-agent planning path after the WP37 token-efficiency
sequence closeout. This document is a handoff and orientation package only. It
does not implement agent runtime, Hermes, LLMs, credentials, trading, database,
dashboard, scheduler, polling, or any product/runtime behavior.

The package records what advisory capabilities are approved in principle, what
remains forbidden, which repo components can be reused, what manual setup
decisions remain unresolved, and which future WPs should be considered first.

## 3. Current Repo Foundation

- WP20: advisory-agent policy and `docs/agent_model_registry.md`.
- WP21: `docs/agent_context_export_schema.md`.
- WP23: local/offline/read-only context exporter documented in
  `docs/agent_context_exporter.md`.
- WP24: context exporter operator runbook at
  `docs/agent_context_exporter_operator_runbook.md`.
- WP25: deterministic local/offline/read-only report generator documented in
  `docs/agent_context_report_generator.md`.
- WP26: analyst report operator runbook at
  `docs/agent_context_report_operator_runbook.md`.
- WP27: Agent/Hermes manual setup decision record at
  `docs/agent_hermes_manual_setup_decision_record.md`.
- WP28-WP37: token-efficiency helper stack and closeout, including
  `docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md`.

## 4. Existing Reusable Components

The following tracked components can inform future advisory planning without
granting execution authority:

- `docs/agent_model_registry.md`
- `docs/agent_context_export_schema.md`
- `docs/agent_context_exporter.md`
- `docs/agent_context_exporter_operator_runbook.md`
- `docs/agent_context_report_generator.md`
- `docs/agent_context_report_operator_runbook.md`
- `docs/agent_hermes_manual_setup_decision_record.md`
- `tools/git/diff_scope_summary.py`
- `tools/validation/validation_output_summary.py`
- `tools/git/code_blast_radius.py`
- `tools/git/status_snapshot.py`

## 5. Approved Advisory Capability Set

Future advisory work may support these capabilities only as non-executing,
read-only, human-reviewed support:

- read-only analyst / market-state analysis;
- performance review from local reports and exported context;
- market research from approved read-only context and local reports;
- strategy suggestion / hypothesis support as advisory narrative only;
- Codex / WP support for repo-governed implementation planning.

Advisory narrative only means the output can help a human reason about future
work. It is not a signal, order, parameter instruction, config change, approval,
or execution command.

## 6. Explicitly Forbidden Capabilities

WP38 does not authorize:

- fully autonomous trading agent;
- live trading;
- paper trading;
- order placement;
- order cancellation;
- signing;
- account connection;
- credential use;
- private authenticated APIs;
- copy-trading execution;
- scheduler/daemon/bot loop;
- Hermes runtime;
- LLM/provider runtime;
- database/dashboard/deployment;
- official-client runtime integration;
- production polling.

## 7. Parameter Recommendation Boundary

Parameter recommendations may only be future advisory narrative if explicitly
scoped by a later approved WP. No executable parameter recommendation engine is
authorized by WP38.

No position sizing, order instructions, liquidation-sensitive bot parameters, or
copy-trading instructions may be produced as runtime output without a separate
risk/safety/authorization WP. Strategy suggestions must be framed as
human-reviewed hypotheses, not executable commands.

## 8. Hermes / Manual Setup Status

Hermes is not installed. Hermes is not a runtime dependency. No manual setup is required for WP38.

Future Hermes work requires explicit user approval, setup decision, environment
documentation, provider/security review, and separate implementation WPs. Codex can prepare docs/tests/runbooks, but cannot complete user-side account/provider setup or credential creation.

## 9. What Codex Can Likely Handle Automatically Later

In later approved WPs, Codex can likely prepare:

- repo-truth docs;
- schemas;
- local/offline helper code;
- tests;
- runbooks;
- local report/context consumers;
- validation gates;
- advisory prompt/runbook packages;
- safe local CLI prototypes that do not call network, LLMs, Hermes, accounts,
  or trading endpoints.

## 10. What Remains Manual Or Externally Dependent Later

The following remain manual or externally dependent decisions:

- installing/choosing Hermes or an alternative agent environment;
- selecting LLM/provider account;
- API key creation;
- credentials storage approach;
- exchange/broker/Polymarket account access;
- legal/compliance/geography decision before live trading;
- any funding/capital/risk authorization;
- any live or paper execution approval.

## 11. Recommended Implementation Sequence After WP38

1. WP39 - Advisory Runtime Boundary And Consumption Design:
   design how future advisory consumers may read existing local exports/reports
   without runtime/LLM/Hermes execution.
2. WP40 - Local Advisory Consumer Prototype:
   optional local/offline/read-only consumer that reads existing reports/exports
   and produces deterministic advisory briefs, with no LLM/network/trading.
3. WP41 - Advisory Prompt/Runbook Package:
   human-operated prompt/runbook package for analysis, performance review,
   research, strategy hypotheses, and Codex/WP support.
4. WP42+ only after explicit approval:
   provider/Hermes decision, manual setup docs, dependency/security review, and
   runtime integration design.

Execution, paper trading, and live trading remain much later and require
separate authorization gates.

## 12. Next-WP Recommendation

Recommended next WP after WP38 is WP39 - Advisory Runtime Boundary And Consumption Design.

Alternative next WP is WP39 - Local Advisory Handoff Follow-Up if gaps remain.

Do not jump directly to runtime implementation, Hermes install, LLM provider
integration, database/dashboard, scheduler, paper trading, live trading, or
account connection.

## 13. Safety Boundary Checklist

- [x] no runtime behavior
- [x] no network
- [x] no credentials
- [x] no Hermes install
- [x] no LLM/provider dependency
- [x] no trading
- [x] no scheduler/bot loop
- [x] no database/dashboard
- [x] no official-client runtime integration
- [x] no generated outputs committed

## 14. Non-Goals

- no implementation;
- no runtime;
- no Hermes;
- no LLM;
- no credentials;
- no trading;
- no scheduler;
- no database/dashboard;
- no dependency changes.
