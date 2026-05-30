# Local Advisory Consumer Prototype

## 1. Status

- Prototype status: LOCAL_OFFLINE_READ_ONLY_ADVISORY_CONSUMER
- Script: `tools/advisory/local_advisory_consumer.py`
- Package class: local tooling / advisory prototype
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Command execution impact: NO_COMMAND_EXECUTION
- Agent runtime impact: NO_AGENT_RUNTIME
- Hermes impact: NO_HERMES_INSTALL_OR_RUNTIME
- LLM/provider impact: NO_LLM_PROVIDER_RUNTIME
- Trading impact: NO_TRADING_EXECUTION
- Advisory authority: ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED

## 2. Purpose

WP40 implements the first deterministic local/offline/read-only advisory
consumer prototype defined by WP39.

The prototype consumes explicitly provided local agent context exports and
local analyst reports, then creates bounded advisory-only briefs for human
review. It does not replace repo truth, validation, security checks, direct
changed-file inspection, PR review, or human decision-making.

The prototype does not create an agent runtime.

## 3. Allowed Inputs

Allowed explicit input files:

- `local_data/agent_context_exports/` JSON files passed with `--context-export`.
- `local_data/agent_context_reports/` Markdown or text files passed with `--analyst-report`.
- A small allowlist of repo-truth docs for boundary reminders:
  - `docs/project_status.md`
  - `docs/repo_truth_index.md`
  - `docs/local_advisory_handoff_package.md`
  - `docs/advisory_runtime_boundary_consumption_design.md`
  - `docs/security_and_secrets.md`
  - `docs/live_trading_authorization.md`

The prototype uses explicit input paths only. It does not crawl `local_data/`
or auto-discover files.

## 4. Forbidden Inputs

The prototype must not read or ingest:

- `.env` files;
- credentials;
- private keys;
- wallet keys;
- mnemonics;
- tokens;
- account data;
- private endpoint responses;
- authenticated API data;
- arbitrary local_data crawling;
- network or GitHub API responses;
- live or paper trading account state.

## 5. Outputs

Default behavior writes no file and prints a concise advisory-only brief to
stdout.

Allowed output content:

- advisory-only local context summary;
- research questions;
- risk and uncertainty notes;
- human-review checklist when `--include-review-checklist` is provided;
- validation and repo-truth reminders.

Optional file output is allowed only when `--output` is provided and only under:

- `local_data/advisory_outputs/`

Generated advisory outputs are ignored local data and must not be committed.

## 6. Forbidden Outputs

The prototype must not produce:

- executable trading signals;
- order instructions;
- position sizing;
- liquidation-sensitive bot parameters;
- copy-trading instructions;
- account actions;
- scheduler or bot-loop instructions;
- live or paper trading decisions;
- config mutation instructions;
- merge-readiness decisions;
- implementation approvals.

If source text contains trading-like language, the prototype withholds the raw
phrase and emits a neutral warning that human review is required.

## 7. Commands

Help:

```powershell
python tools/advisory/local_advisory_consumer.py --help
```

Text from context export:

```powershell
python tools/advisory/local_advisory_consumer.py --context-export local_data/agent_context_exports/example.local.json --format text
```

Text from report:

```powershell
python tools/advisory/local_advisory_consumer.py --analyst-report local_data/agent_context_reports/example.local.md --format text --include-review-checklist
```

JSON:

```powershell
python tools/advisory/local_advisory_consumer.py --context-export local_data/agent_context_exports/example.local.json --format json
```

Optional output:

```powershell
python tools/advisory/local_advisory_consumer.py --context-export local_data/agent_context_exports/example.local.json --format json --output local_data/advisory_outputs/example_advisory.local.json
```

## 8. Exit Codes

- `0`: advisory brief generated.
- `1`: sensitive-content strict failure from `--fail-on-sensitive-hit`.
- `2`: usage, configuration, or input error.

## 9. Sensitive Redaction

The prototype detects and redacts obvious secret-like values in output,
including `API_KEY`, `PRIVATE_KEY`, `CLOB_SECRET`, `CLOB_PASS_PHRASE`,
`MNEMONIC`, `TOKEN`, long Bearer tokens, and PEM private-key blocks.

This redaction is not a replacement for gitleaks, semgrep, security review, or
human inspection.

## 10. Non-Goals

- no LLM;
- no Hermes;
- no runtime;
- no scheduler;
- no account connection;
- no trading;
- no paper trading;
- no live trading;
- no order, signing, or copy-trading behavior;
- no database/dashboard;
- no dependency changes.
