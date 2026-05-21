# Agent / Hermes Manual Setup Decision Record

## Status

- Decision record status: MANUAL_SETUP_DECISION_RECORD
- Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime status: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Live trading status: DISABLED
- Credentials status: NOT_USED
- Network permission status: NOT_GRANTED_FOR_AGENT_RUNTIME
- Memory/persistence status: NOT_STARTED
- Command execution status: NOT_GRANTED
- Decision state: DECISION_DEFERRED_PENDING_USER_SELECTION

## Purpose

This is a decision record, not an installation guide. It defines the gates, manual choices, and approval steps required before any Hermes or agent runtime work begins in a future work package.

No Hermes installation, agent runtime, provider SDK, credentials, network permission, memory/persistence, or command execution is performed in WP27. This WP is documentation and test only.

The existing local exporter and report generator from WP23–WP26 remain deterministic, local/offline, and read-only. They require no Hermes installation and no agent runtime. They continue to produce local advisory handoff material independent of any future runtime decision.

## Current Local Advisory Assets

The following tools are implemented and available without any agent runtime or Hermes installation:

- **WP23 context exporter** — `tools/polymarket/export_agent_context.py`: local/offline/read-only JSON context export from allowlisted repo-truth docs and optional local report metadata. Output to ignored `local_data/agent_context_exports/` only when explicit path is provided.
- **WP24 exporter operator runbook** — `docs/agent_context_exporter_operator_runbook.md`: step-by-step human-operator instructions for safe manual exporter use, including git hygiene and validation steps.
- **WP25 report generator** — `tools/polymarket/generate_agent_context_report.py`: deterministic local/offline/read-only Markdown and JSON report generation from WP23-compatible context exports. Output to ignored `local_data/agent_context_reports/` only when explicit path is provided.
- **WP26 report operator runbook** — `docs/agent_context_report_operator_runbook.md`: step-by-step human-operator instructions for safe manual report generation, including validation and git hygiene steps.

These assets produce a local advisory handoff package that can be used for human review without any agent runtime.

## Candidate Future Runtime Choices

### Option A: Hermes Selected Later

**What it would allow:**
- Hermes runtime installed locally on operator machine (not in repo).
- Local reports and context exports shared with Hermes for advisory read-only review.
- Hermes may summarize, propose, and suggest — but not execute, trade, or modify configs.

**What remains forbidden:**
- Autonomous trading.
- Credentials in repo.
- Order placement, cancellation, signing, or submission.
- Scheduler or bot loop.
- Automatic config mutation.
- Private endpoint access.

**Manual choices required:**
- User selects Hermes explicitly.
- User decides local machine vs VPS/cloud for Hermes runtime.
- User decides model/provider.
- User provides provider API keys outside the repo.
- User approves allowed command list.
- User approves allowed file/directory access.
- User approves network permission scope.
- User approves memory/persistence location.
- User decides logging and retention policy.

**Future WP required:**
- WP28 or later: Hermes Setup Checklist And Manual Decision Follow-Up (docs/tests only, no install).
- A later approved WP for actual Hermes installation and setup.

### Option B: Alternative Local Agent Runtime Selected Later

**What it would allow:**
- Alternative local agent runtime (e.g. LangChain agent, custom Python orchestrator) installed locally.
- Local reports and context exports used as input for advisory review.
- Advisory output only — no execution.

**What remains forbidden:**
- Same forbidden list as Option A.

**Manual choices required:**
- User selects alternative runtime explicitly.
- Same environment, provider, command, and network decisions as Option A.

**Future WP required:**
- WP28 or later: decision record follow-up with selected runtime docs/tests.
- A later approved WP for actual runtime installation and setup.

### Option C: No Runtime For Now — Continue Local/Offline Handoff Package

**What it would allow:**
- Continue using WP23–WP26 exporter and report tools for manual advisory handoff.
- Human analyst reads local reports directly.
- No agent runtime required.

**What remains forbidden:**
- No change to existing boundaries. All forbidden items remain forbidden.

**Manual choices required:**
- User explicitly defers runtime selection.
- User reviews local advisory material without Hermes or agent runtime.

**Future WP required:**
- WP28 or later: Local Advisory Handoff Package (packaging exporter/report outputs for manual review session).

### Option D: Decision Deferred

**What it would allow:**
- No action on runtime selection in this WP or next WP.
- Decision remains open for a future session.

**What remains forbidden:**
- Same as all other options — no runtime, no credentials, no network, no execution.

**Manual choices required:**
- User explicitly defers all runtime decisions.

**Future WP required:**
- A later WP to revisit this decision record once runtime preference is known.

## Manual User Decisions Required Before Any Runtime Setup

The following decisions must be made by the user before any future Hermes or agent runtime setup work begins in a work package:

1. **Whether to use Hermes or defer** — explicit user confirmation of Hermes as the selected runtime, or explicit deferral.
2. **Local machine vs VPS/cloud** — where the agent runtime will run. This affects environment docs, security posture, and jurisdiction.
3. **Model/provider choice** — which LLM provider (e.g. OpenAI, Anthropic, local model) will be used. Affects provider key handling, cost, and data sharing.
4. **Provider/API key handling outside repo** — how API keys will be stored and accessed without entering the repo or `.env` files committed to git.
5. **Allowed commands** — explicit list of shell or tool commands the agent runtime may invoke. Must be reviewed and approved before any command permission is granted.
6. **Allowed files/directories** — explicit list of files and directories the agent runtime may read. Must not include credentials, private keys, `.env`, or trading execution state.
7. **Whether local reports/exports may be shared with provider** — explicit decision on whether local report content may be sent to a remote LLM API. Privacy and data-handling implications must be considered.
8. **Network permission** — explicit scope of any outbound network access granted to the agent runtime. Default is no network permission.
9. **Memory/persistence location** — where agent memory, session state, or conversation history will be stored. Must be outside the repo and must not include credentials.
10. **Logging/retention policy** — how long agent interaction logs are retained, who may access them, and whether they contain sensitive content.
11. **Max autonomy level** — explicit cap on what the agent runtime may do without human confirmation. Advisory-only is the default.
12. **Explicit no-trading/no-execution boundary** — confirmation that the agent runtime will not have order placement, execution, signing, or OMS authority in any configuration.
13. **Incident response / kill switch expectations** — how the agent runtime is stopped, how sessions are terminated, and what happens if unexpected behavior is observed.

## What Codex Can Prepare Automatically Later

In future approved work packages, Codex can prepare the following without requiring user manual action:

- **Local advisory handoff package** — using existing WP23–WP26 exporter and report outputs as input. Packages context exports and reports into a structured handoff directory for manual review.
- **Setup checklist docs** — a step-by-step checklist for manually installing and verifying Hermes or another agent runtime, to be followed by the user outside the repo.
- **Environment checklist docs** — a pre-flight checklist for the operator environment before any runtime setup, covering Python version, PATH, ignore hygiene, and security tooling status.
- **Prompt templates for advisory review** — reusable prompt structures that an operator may paste into a Hermes or agent session manually. Templates are docs only; they do not invoke any runtime.
- **Static safety checks** — test-only assertions that no runtime dependency, no credentials, no network permission, and no forbidden command class has been introduced.
- **Read-only command allowlist docs** — documentation of a proposed safe command set for read-only advisory use, to be reviewed and approved by the user before any runtime permission is granted.
- **No-runtime integration scaffolding docs/tests** — structure docs and tests defining what a future safe integration would look like, without implementing any runtime behavior.

These items do not require Hermes installation and do not grant any execution authority.

## What Codex Must Not Do Automatically

The following actions are forbidden for Codex to perform automatically in any work package without explicit user instruction and repo-truth approval:

- **Install Hermes** — no Hermes installation command may be run automatically.
- **Install provider SDKs** — no OpenAI, Anthropic, LangChain, or other LLM provider package may be added as a project dependency.
- **Create `.env`** — no `.env` file may be created with credentials, keys, or tokens.
- **Request or store API keys** — no credential request, capture, or storage may occur in any automated step.
- **Configure memory/persistence** — no agent memory store, session database, or conversation history file may be created automatically.
- **Grant network access** — no network permission may be added to any agent runtime or tool configuration automatically.
- **Grant command execution** — no command allowlist or shell execution permission may be added without explicit user review and approval.
- **Connect accounts** — no account connection, wallet link, or authenticated session may be established automatically.
- **Call private endpoints** — no private Polymarket, exchange, or provider endpoint may be called automatically.
- **Place/cancel/sign/submit orders** — no order operation may be performed by any automated Codex step.
- **Run scheduler/bot loop** — no `while True`, `time.sleep`, daemon, service, background worker, or scheduler may be started automatically.
- **Mutate configs automatically** — no strategy config, risk config, execution config, or runtime config may be modified automatically by an agent or Codex step.
- **Create trade signals/proposals unless separately scoped later** — no strategy signal, trade proposal, parameter recommendation, or execution intent may be generated without a future separately approved WP explicitly scoping that capability.

## Required Future Approval Gates

The following gates must be satisfied and documented in repo truth before the corresponding capability is activated:

1. **Runtime selection gate** — user explicitly names the selected runtime (Hermes or alternative) in a work package instruction. Codex does not select a runtime autonomously.
2. **Installation gate** — an approved work package explicitly authorizes Hermes or alternative runtime installation. Gate includes security tooling rerun (gitleaks, semgrep, pip-audit).
3. **Provider/API-key gate** — user provides explicit documented decision on provider and key handling outside the repo. No key is committed to the repo.
4. **Network-permission gate** — an approved work package explicitly defines network scope. Default is no network permission.
5. **Memory/persistence gate** — user approves memory location and retention policy outside the repo before any agent memory store is created.
6. **Command-allowlist gate** — user reviews and approves an explicit command list before any command execution permission is granted to the agent runtime.
7. **Data-sharing gate** — user explicitly decides whether local report content may be sent to a remote LLM API. Default is no sharing.
8. **Safety/incident-response gate** — user documents kill switch expectations and incident response procedure before any agent runtime is activated.
9. **Live-trading gate** — this gate is defined in `docs/live_trading_authorization.md` and remains entirely separate from agent setup. Agent runtime setup does not satisfy the live-trading gate. Live trading remains DISABLED.

## Recommended Next Path

### Default safe next WP

**WP28 - Local Advisory Handoff Package**

If the user wants to continue with local/offline/no-Hermes-runtime advisory work, WP28 packages the WP23–WP26 exporter and report outputs into a structured local handoff directory with operator instructions. This does not require any runtime selection or installation decision.

### Alternative if user chooses to prepare Hermes docs

**WP28 - Hermes Setup Checklist And Manual Decision Follow-Up**

If the user explicitly decides to prepare Hermes setup documentation (without installation), WP28 produces a Hermes setup checklist and manual decision follow-up doc that walks through the gates defined in this record. Still no installation, no provider SDK, no credentials, no network, no runtime.

### If no-agent-runtime path is preferred

**WP28 - Agent/Hermes Decision Record Follow-Up**

If this decision record requires revision, test gaps, or additional gate documentation, WP28 can address those items without adding any runtime.

**Do not proceed to Hermes installation until the user explicitly chooses runtime/provider/environment and repo truth authorizes it in a future work package.**

## Non-Goals / Forbidden Scope

The following are explicitly out of scope for WP27 and for any automatic Codex action:

- No installation of Hermes or any agent runtime
- No Hermes configuration file
- No runtime or dev dependency changes
- No provider SDK (OpenAI, Anthropic, LangChain, etc.)
- No credentials, `.env`, API keys, private keys, wallet keys, mnemonics, passphrases, tokens, or authenticated headers
- No network access or network permission grant
- No memory/persistence setup
- No command execution permission
- No strategy recommendation, signal, or trade proposal
- No trade signal generator
- No backtest, paper trading, or historical simulation
- No live trading
- No scheduler, daemon, background worker, bot loop, `while True`, or `time.sleep`
- No account connection or private endpoint access
- No automatic config mutation
- No order placement, cancellation, signing, or submission
- No OMS, risk engine, execution gateway, or reconciliation
- No dashboard or database
- No deployment setup

## Decision State

Default state: **DECISION_DEFERRED_PENDING_USER_SELECTION**

Hermes may be considered as a future option, but it is not selected, installed, or configured by WP27. No explicit runtime choice is being made in this work package. The decision remains deferred and requires explicit user instruction in a future work package to proceed.

The live-trading gate defined in `docs/live_trading_authorization.md` is entirely separate from agent setup and is not satisfied by any agent runtime installation or configuration.
