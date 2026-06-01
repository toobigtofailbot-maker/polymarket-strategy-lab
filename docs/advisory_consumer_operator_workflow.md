# Advisory Consumer Operator Workflow

## 1. Status

- Package status: DOCS_ONLY_ADVISORY_OPERATOR_WORKFLOW_HARDENING
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

WP42 hardens the human-operated advisory workflow after the WP40 local advisory
consumer prototype and the WP41 advisory prompt/runbook package.

This document is documentation only. It connects existing local/offline/read-only
advisory components into a safe operator workflow. It does not implement
workflow execution, prompt execution, LLM/Hermes runtime, agent runtime,
credentials, trading, database, dashboard, scheduler, polling, product behavior,
command runners, account connections, or provider integration.

## 3. Existing Component Chain

The safe advisory chain uses existing components only:

- `docs/local_advisory_handoff_package.md`
- `docs/advisory_runtime_boundary_consumption_design.md`
- `docs/local_advisory_consumer_prototype.md`
- `tools/advisory/local_advisory_consumer.py`
- `docs/advisory_prompt_runbook_package.md`
- `docs/agent_context_exporter_operator_runbook.md`
- `docs/agent_context_report_operator_runbook.md`

Token-efficiency helpers may provide advisory orientation, but never authority:

- `tools/git/status_snapshot.py`
- `tools/git/diff_scope_summary.py`
- `tools/git/code_blast_radius.py`
- `tools/validation/validation_output_summary.py`

These components do not grant runtime, Hermes, LLM/provider, credential,
account, trading, database, dashboard, scheduler, polling, dependency, prompt
runner, or product authority.

## 4. End-To-End Operator Workflow

### Stage 0: verify repo truth directly

Read current repo-truth files directly from the checked-out branch before using
any advisory output:

- `AGENTS.md`
- `CODEX_START_HERE.md`
- `docs/project_status.md`
- `docs/repo_truth_index.md`
- `docs/deferred_items_log.md`
- task-relevant boundary docs, including `docs/runtime_boundaries.md`,
  `docs/security_and_secrets.md`, and `docs/live_trading_authorization.md`

Repo truth overrides chat memory, stale exports, local reports, WP40 output,
WP41 prompt output, and helper summaries.

### Stage 1: identify allowed local artifacts

List each local artifact explicitly before use. Allowed local artifacts are
explicit files only under:

- `local_data/agent_context_exports/`
- `local_data/agent_context_reports/`
- `local_data/advisory_outputs/`

There is no implicit crawling, no arbitrary file reads, and no tracked generated
outputs.

### Stage 2: check freshness and provenance

For every selected artifact, check freshness, provenance, source commit,
generated timestamp, warnings, stale-context notes, and missing-source notes.
Reject or rerun stale context when repo truth or branch state has moved.

### Stage 3: optionally run WP40 local advisory consumer manually

The operator may optionally run the WP40 local advisory consumer manually with
explicit input files only. Use the existing `tools/advisory/local_advisory_consumer.py`
prototype and follow `docs/local_advisory_consumer_prototype.md`.

Do not crawl `local_data`. Do not add new tools. Do not run a workflow runner,
prompt runner, LLM, Hermes, provider SDK, account connection, network polling,
or trading path.

### Stage 4: inspect WP40 advisory output

Inspect WP40 advisory output before using it in any prompt or review package.
Reject the output if it contains forbidden output, missing provenance, stale
context without a warning, credentials, account data, private endpoint material,
or any claim that it can approve implementation, merge readiness, runtime work,
or protected-boundary changes.

### Stage 5: select WP41 prompt template manually

Select the matching WP41 prompt template manually from
`docs/advisory_prompt_runbook_package.md`. WP41 prompt templates are manual-only.
They do not create a prompt runner, do not call a provider, and do not authorize
LLM/Hermes/provider runtime.

### Stage 6: prepare sanitized context package

Prepare a sanitized context package that contains only explicit allowed files,
freshness/provenance notes, source commit, generated timestamp, warnings, stale
or missing context notes, and the selected WP41 prompt template.

Do not include credentials, account data, private endpoint responses,
authenticated API data, private execution state, `.env` content, raw security
scan output, arbitrary `local_data`, network responses, or GitHub API responses
as runtime input.

### Stage 7: use a human-operated advisory session only

Paste the sanitized package into a human-operated advisory session only. The
operator controls the session. The repo does not run prompts, call providers,
install Hermes, store credentials, grant network permission, or execute commands
as part of this workflow.

### Stage 8: review output against forbidden-output checklist

Treat all advisory output as untrusted until reviewed against the forbidden
output checklist in this document and WP41. Reject output that exceeds advisory
scope, claims authority, or suggests protected work without an approved WP.

### Stage 9: convert acceptable action into a separate approved WP

Advisory observations do not become work automatically. Any repo change,
implementation, test change, runtime proposal, dependency proposal, prompt-runner
idea, LLM/Hermes/provider decision, trading workflow, database/dashboard work,
scheduler/polling work, or protected-boundary change requires a separate
repo-truth-approved WP.

### Stage 10: archive or discard stale local advisory context outside git

After review, archive or discard stale local advisory context outside git.
Generated exports, reports, and advisory outputs remain ignored local data and
must not be staged or committed.

## 5. Evidence Package Checklist

Before using any advisory output, the operator must record:

- repo-truth files checked;
- source commit recorded;
- generated timestamp recorded;
- local artifact paths explicitly listed;
- stale/missing context noted;
- warnings copied;
- forbidden input check completed;
- human reviewer named or otherwise identified;
- no credentials/account/private endpoint/trading account data included.

## 6. Allowed Local Artifact Paths

Allowed paths are explicit files only:

- `local_data/agent_context_exports/` explicit files only.
- `local_data/agent_context_reports/` explicit files only.
- `local_data/advisory_outputs/` explicit files only.

Rules:

- no implicit crawling;
- no arbitrary file reads;
- no tracked generated outputs;
- no local artifact may override repo truth;
- no generated output may be committed.

## 7. Forbidden Inputs And Stop Conditions

Stop and reject the workflow if any input includes or requires:

- `.env`
- credentials
- API keys
- private keys
- wallet keys
- mnemonics
- tokens
- account data
- private endpoint responses
- authenticated API data
- live/paper trading account state
- arbitrary local_data crawling
- network/GitHub API responses as runtime input
- raw security scan outputs unless explicitly summarized
- prompt output claiming merge readiness
- prompt output proposing runtime/Hermes/LLM/provider/trading/database/dashboard/scheduler/polling/dependency work without approved WP

Also stop if an operator needs arbitrary filesystem access, credentials,
network calls, private endpoints, account state, generated output committed to
git, or any protected runtime boundary change.

## 8. Forbidden Output Checklist

Reject advisory output that contains:

- executable trading signals
- order instructions
- signing requests
- account actions
- copy-trading instructions
- liquidation-sensitive bot parameters
- position sizing
- leverage recommendations
- autonomous parameter updates
- scheduler/bot-loop instructions
- live/paper trading decisions
- claims of merge readiness
- implementation approval
- automatic PR approval
- credential handling instructions
- command-runner instructions
- config mutation instructions
- prompt-runner instructions
- workflow-runner instructions
- provider/Hermes runtime setup instructions without approved WP
- database/dashboard/scheduler/polling/product work without approved WP

## 9. Decision Log Template

Use this template for each advisory workflow review:

```text
workflow date:
operator:
repo commit checked:
repo-truth files checked:
local artifacts used:
artifact generated timestamps:
stale-context notes:
WP40 consumer command used:
WP41 prompt template used:
rejected outputs:
accepted advisory observations:
resulting repo action:
required next WP:
confirmation no protected work was authorized:
```

## 10. Conversion Rules From Advisory Output To Repo WP

- advisory observations do not become work automatically;
- every repo change needs a separate explicit WP;
- runtime/protected areas require explicit authorization;
- first create a design WP before implementation when runtime, provider,
  dependency, credential, account, scheduler, database, dashboard, polling,
  trading, or protected-boundary implications exist;
- Provider/Hermes Decision Refresh remains a separate future WP and requires
  explicit user approval;
- separate risk/legal/authorization WPs are required before paper trading, live
  trading, account connection, signing, order placement, execution, copy-trading,
  or live authorization work.

Advisory output can at most become evidence for a human-authored future WP
proposal. It cannot approve its own implementation.

## 11. Relationship To WP41

WP41 prompt templates are manual-only. WP42 defines how to operate them safely
with current local advisory components and explicit human review.

WP42 does not create a prompt runner. WP42 does not authorize LLM/Hermes/provider runtime.
WP42 does not change WP41 template boundaries.
WP41 output remains ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED and cannot replace repo
truth, validation, security checks, changed-file inspection, PR review, or human
approval.

## 12. Protected Boundary Reaffirmation

This workflow preserves:

- no implementation;
- no workflow runner;
- no prompt runner;
- no runtime/source/product behavior;
- no tools modified;
- no dependencies/lock files;
- no Hermes/LLM/agent runtime;
- no credentials/network/trading;
- no database/dashboard/scheduler/polling/product work;
- no generated outputs committed.

Live trading remains DISABLED. Credentials remain NOT_USED. Agent execution
authority remains FORBIDDEN. Hermes remains NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY.

## 13. Next-WP Boundary

Safe next WP options after WP42 may include:

- WP43 - Provider/Hermes Decision Refresh, only if explicitly approved by the
  user;
- WP43 - Local Advisory Workflow Follow-Up, if gaps remain;
- another explicitly approved safe repo-truth WP.

Do not jump to database, dashboard, strategy runtime, paper trading, live
trading, official-client runtime integration, scheduler, wallet/copy-trading,
production polling, Hermes install, LLM provider runtime, or agent runtime
unless explicitly approved by the user and repo truth is updated through a
separate WP.

## 14. Non-Goals

- no runtime;
- no LLM/provider integration;
- no Hermes;
- no agent runtime;
- no prompt runner;
- no workflow runner;
- no credentials;
- no trading;
- no paper trading;
- no live trading;
- no account connection;
- no database/dashboard;
- no scheduler/polling;
- no dependency changes;
- no generated outputs.
