# Advisory Prompt Runbook Package

## 1. Status

- Package status: DOCS_ONLY_ADVISORY_PROMPT_RUNBOOK_PACKAGE
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
- Prompt execution impact: NO_PROMPT_RUNNER

## 2. Purpose

WP41 creates human-operated advisory prompt and runbook guidance after the WP40
local advisory consumer prototype. This document is documentation only.

It does not implement prompt execution, LLM/Hermes runtime, agent runtime,
credentials, trading, database, dashboard, scheduler, polling, product
behavior, command runners, account connections, or provider integration.

## 3. Approved Advisory Use Cases

The approved advisory use cases are:

- read-only market-state analysis;
- performance review from local reports and exports;
- market research question planning;
- strategy hypothesis narrative;
- Codex / WP planning support.

All use cases are advisory-only and human-reviewed. They may support human
reasoning, but they do not create signals, orders, position sizing, runtime
parameters, config changes, approval decisions, or merge-readiness decisions.

## 4. Required Input Package

The operator prepares an explicit, sanitized context package before using any
template in this document. The package may include:

- relevant repo-truth docs read directly from the current checkout;
- optional WP40 advisory consumer output under ignored
  `local_data/advisory_outputs/`;
- optional agent context exports under ignored
  `local_data/agent_context_exports/`;
- optional analyst reports under ignored
  `local_data/agent_context_reports/`;
- freshness notes for each artifact;
- source commit for each generated artifact when available;
- generated timestamp for each generated artifact when available;
- known warnings, stale-context notices, missing-source notes, and deferred
  item references.

Input rules:

- use explicit operator-provided files only;
- no implicit `local_data` crawling;
- no arbitrary filesystem reads;
- no credentials, account data, private endpoint responses, authenticated API
  data, or trading-account state;
- repo-truth docs read directly are authoritative over generated outputs;
- WP40 outputs, exports, and reports are optional advisory context only.

## 5. Forbidden Inputs

Do not include or ask a prompt to read:

- `.env`;
- `.env.*`;
- credentials;
- API keys;
- private keys;
- wallet keys;
- mnemonics;
- passphrases;
- tokens;
- account data;
- private endpoint responses;
- authenticated API data;
- authenticated headers;
- live/paper trading account state;
- arbitrary local_data crawling;
- raw security scan outputs unless explicitly summarized for human review;
- official-client sandbox outputs unless separately approved;
- chat/user memory outside repo truth;
- network/GitHub API responses as runtime input;
- order, signing, wallet, account, or private execution state.

## 6. Mandatory Output Rules

Every prompt output must include:

- `ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED`;
- uncertainty/assumptions;
- source/freshness limitations;
- human-review checklist;
- repo-truth verification reminder;
- validation/security reminder where relevant;
- a reminder to avoid executable instructions.

Every output must be treated as untrusted advisory text until a human checks it
against current repo truth, direct files, required validation, security checks,
and normal PR review.

## 7. Forbidden Outputs

Prompt outputs must not include:

- executable trading signals;
- order instructions;
- order placement/cancellation requests;
- signing requests;
- account actions;
- copy-trading instructions;
- liquidation-sensitive bot parameters;
- position sizing;
- leverage recommendations;
- autonomous parameter updates;
- scheduler/bot-loop instructions;
- live/paper trading decisions;
- claims of merge readiness;
- implementation approval;
- automatic PR approval;
- credential handling instructions;
- config mutation instructions;
- command-runner instructions.

## 8. Prompt Template: Read-Only Market-State Analysis

```text
Role:
You are a read-only advisory analyst for a deterministic trading-bot repository.
Your output is ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.

Allowed inputs:
- Current repo-truth docs read directly from the repository.
- Operator-provided sanitized local advisory context.
- Optional WP40 output from local_data/advisory_outputs/.
- Optional local exports from local_data/agent_context_exports/.
- Optional local reports from local_data/agent_context_reports/.

Forbidden inputs/outputs:
- Do not use credentials, account data, private endpoint responses, live/paper
  account state, arbitrary local_data crawling, network/GitHub API responses, or
  chat/user memory outside repo truth.
- Do not produce executable trading signals, order instructions, position
  sizing, leverage recommendations, liquidation-sensitive bot parameters,
  account actions, copy-trading instructions, scheduler/bot-loop instructions,
  live/paper trading decisions, merge-readiness claims, implementation
  approval, or automatic PR approval.

Required analysis sections:
1. ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.
2. Source and freshness limitations.
3. Observations from the provided read-only market-state context.
4. Context checks against current repo truth.
5. Risk and uncertainty notes.
6. Human review questions.
7. Repo-truth verification reminder.
8. Validation/security reminder where relevant.

Uncertainty requirements:
- State assumptions explicitly.
- Label stale, missing, partial, or conflicting context.
- Do not claim latest facts unless the operator-provided context proves them.

No-trading-execution language:
This output must not contain trades, orders, position sizing, leverage,
liquidation-sensitive parameters, account actions, or executable instructions.
```

## 9. Prompt Template: Performance Review From Local Reports/Exports

```text
Role:
You are a performance-review advisor using only local reports and exports. Your
output is ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.

Allowed inputs:
- Current repo-truth docs read directly from the repository.
- Operator-provided local reports under local_data/agent_context_reports/.
- Operator-provided local exports under local_data/agent_context_exports/.
- Optional WP40 advisory output under local_data/advisory_outputs/.

Forbidden inputs/outputs:
- Do not infer account-level claims unless they are present in approved local
  artifacts.
- Do not use credentials, private endpoints, authenticated API data, account
  state, live/paper trading state, arbitrary local_data crawling, or network
  responses.
- Do not provide direct trade advice, direct strategy execution advice,
  position sizing, leverage, order instructions, signals, merge readiness, or
  implementation approval.

Required analysis sections:
1. ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.
2. Source and freshness limitations.
3. Summary of performance evidence in the local artifacts.
4. Data-quality issues and stale-context warnings.
5. Missing evidence and unsupported claims.
6. Review questions for a human operator.
7. Repo-truth verification reminder.
8. Validation/security reminder where relevant.

Uncertainty requirements:
- Separate facts from inferences.
- Mark any metric, claim, or trend as unsupported if the approved local
  artifacts do not contain direct evidence.
```

## 10. Prompt Template: Market Research Question Planning

```text
Role:
You are a market research planning assistant. Your output is
ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.

Allowed inputs:
- Current repo-truth docs read directly from the repository.
- Operator-provided sanitized local context, exports, reports, and optional
  WP40 advisory output.

Forbidden inputs/outputs:
- Do not browse, call network, call GitHub APIs, query providers, or claim
  latest facts unless a human separately verifies sources outside this repo
  workflow and provides sanitized context.
- Do not use credentials, account data, private endpoint responses,
  authenticated API data, or arbitrary local_data crawling.
- Do not produce trading signals, order instructions, position sizing,
  leverage, account actions, copy-trading instructions, merge readiness,
  implementation approval, or automatic PR approval.

Required analysis sections:
1. ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.
2. Research questions.
3. Source-check plan for a human operator.
4. Missing facts and source gaps.
5. Assumptions and uncertainty.
6. Repo-truth verification reminder.
7. Validation/security reminder where relevant.

Uncertainty requirements:
- Label every missing fact.
- Do not claim current or latest external facts without human-provided
  verification and date-stamped source context.
```

## 11. Prompt Template: Strategy Hypothesis Narrative

```text
Role:
You are a strategy hypothesis narrator. Your output is
ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.

Allowed inputs:
- Current repo-truth docs read directly from the repository.
- Operator-provided sanitized local reports, exports, optional WP40 advisory
  output, and human notes.

Forbidden inputs/outputs:
- Do not frame ideas as executable signals, trade proposals, order
  instructions, position sizing, leverage recommendations, liquidation-sensitive
  bot parameters, copy-trading instructions, account actions, or autonomous
  parameter updates.
- Do not authorize implementation, config changes, merge readiness, runtime
  work, paper trading, live trading, scheduler/bot-loop changes, or automatic PR
  approval.

Required analysis sections:
1. ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.
2. Hypothesis narrative, explicitly labeled as a hypothesis.
3. Supporting local evidence.
4. Invalidation assumptions.
5. Uncertainty and stale-context notes.
6. Human review questions.
7. Repo-truth verification reminder.
8. Validation/security reminder where relevant.

Uncertainty requirements:
- State what would disprove the hypothesis.
- Separate evidence from inference and future options.
```

## 12. Prompt Template: Codex / WP Planning Support

```text
Role:
You are a Codex / WP planning support assistant for a repo-governed work
package. Your output is ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.

Allowed inputs:
- Current repo-truth docs read directly from the repository.
- The active human-approved WP text.
- Directly inspected changed files, tests, validation summaries, and optional
  advisory helper output.

Forbidden inputs/outputs:
- Do not rely on chat/user memory outside repo truth.
- Do not treat helper output, WP40 output, local reports, or exports as repo
  truth.
- Do not claim merge readiness, approve implementation, approve PRs, modify
  files automatically, or bypass required validation/security checks.
- Do not suggest runtime, Hermes, LLM/provider, account, credential, trading,
  database, dashboard, scheduler, polling, dependency, or protected-boundary
  work unless the active WP explicitly authorizes it.

Required analysis sections:
1. ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.
2. Facts from repo truth.
3. Inferences and assumptions.
4. Decisions already made by the active WP.
5. Open questions or stop conditions.
6. Narrow next steps within the active WP.
7. Repo-truth verification reminder.
8. Validation/security reminder.

Uncertainty requirements:
- Separate fact, inference, decision, open question, and future option.
- Mark stale or indirect context.
- Require direct file inspection before any implementation or review claim.
```

## 13. Operator Runbook

The operator must verify repo truth directly before using any prompt template.

1. Verify repo truth directly by reading `AGENTS.md`, `CODEX_START_HERE.md`,
   `docs/project_status.md`, `docs/repo_truth_index.md`, and
   `docs/deferred_items_log.md`.
2. Identify allowed local artifacts explicitly. Use only selected files under
   `local_data/advisory_outputs/`, `local_data/agent_context_exports/`, and
   `local_data/agent_context_reports/`.
3. Optionally run the WP40 local advisory consumer manually with explicit input
   files. Do not crawl `local_data`.
4. Prepare a sanitized context package with freshness, source commit, generated
   timestamp, warnings, and known gaps.
5. Choose the correct prompt template for the human review task.
6. Paste only the sanitized package and the selected template into the external
   human-operated advisory session.
7. Verify output contains `ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED`,
   advisory-only/human-review labels, uncertainty, source/freshness limits,
   repo-truth reminders, and validation/security reminders.
8. Reject output if it contains forbidden instructions, forbidden inputs,
   merge-readiness claims, implementation approvals, automatic PR approval, or
   protected-boundary changes.
9. Use a separate approved WP for any repo change, implementation, runtime
   work, dependency change, prompt runner, LLM/Hermes/provider work, or trading
   workflow.

## 14. Stop And Escalation Conditions

Stop and escalate to a human if any input or output includes:

- credentials or secrets present;
- private keys/wallet/account material present;
- executable trading instructions;
- order placement, cancellation, signing, account action, or copy-trading
  instructions;
- position sizing, leverage recommendations, or liquidation-sensitive bot
  parameters;
- merge readiness without direct GitHub/repo review;
- implementation approval or automatic PR approval;
- runtime/Hermes/LLM/provider/network/database/dashboard/scheduler/paper/live
  trading/account/order/signing/copy-trading/dependency changes;
- stale or missing provenance;
- repo truth conflicts with prompt output;
- need for arbitrary local_data crawling, credentials, private endpoints,
  account data, or network responses.

## 15. Relationship To WP40

WP40 output may be used only as advisory context. WP40 output is not repo truth.
WP40 output is not validation. WP40 output cannot authorize trades, merges, runtime work, or protected changes. It also cannot authorize implementation approval, prompt execution,
LLM/Hermes integration, credentials, account access, scheduler changes,
database/dashboard work, or dependency changes.

Current repo truth and direct file inspection override WP40 output if they
conflict. Stale WP40 output must be rerun or discarded.

## 16. Future LLM/Hermes Separation

This package does not authorize LLM/Hermes/provider runtime. Any future
LLM/Hermes/provider work requires:

- explicit user approval;
- manual setup decision;
- dependency/security review;
- data-sharing boundary;
- prompt boundary;
- repo-truth authorization in a separate approved WP.

The repo must not run it in WP41. Prompt templates are for manual
human-operated use only and do not create a prompt runner, provider call,
Hermes install, agent runtime, memory store, network permission, command
authority, or credential path.

## 17. Next-WP Boundary

Safe next WP options after WP41 may include:

- WP42 - Advisory Prompt/Runbook Package Follow-Up, if gaps remain;
- WP42 - Advisory Consumer Integration Review / Operator Workflow Hardening, if
  the user wants to improve the local human-operated workflow without
  LLM/Hermes/runtime;
- WP42 - Provider/Hermes Decision Refresh, only if explicitly approved by the
  user;
- another explicitly approved safe repo-truth WP.

Do not jump to database, dashboard, strategy runtime, paper trading, live
trading, official-client runtime integration, scheduler, wallet/copy-trading,
production polling, Hermes install, LLM provider runtime, or agent runtime.

## 18. Non-Goals

- no implementation;
- no prompt runner;
- no runtime;
- no Hermes;
- no LLM/provider integration;
- no credentials;
- no trading;
- no scheduler;
- no database/dashboard;
- no dependency changes;
- no generated outputs.
