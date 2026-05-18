# Codex Rulebook

Codex must read this file before every work package.

## Repo Truth

- Repo truth overrides chat memory, handoffs, assumptions, and ad hoc instructions.
- Current merged state wins over older summaries.
- Major decisions must be recorded in repo-truth docs before they are treated as project policy.
- If a requested task conflicts with repo truth, follow repo truth and report the conflict.

## Work Package Discipline

- One WP = one branch = one PR.
- Do not work on `main`.
- Before any WP branch is created, Codex must run the Remote Main Sync Gate or equivalent commands proving local `main` equals `origin/main`, the working tree is clean, and previous WP merge evidence exists.
- If local `main` is stale, diverged, dirty, or missing required previous WP files, stop before branch creation.
- Generated local environments and security-tool artifacts must never be committed.
- If `.venv-security/`, `tools/.bin/`, `tools/security/.cache/`, or `security-scan-output/` appear in `git status`, Codex must stop and run the generated-artifact investigation and cleanup workflow before starting a WP.
- Codex must not use GitHub Desktop or equivalent GUI staging for generated artifact folders.
- Do not stack a new WP on a prior WP branch.
- Do not manually merge prior WP branches locally.
- Do not expand scope inside a WP.
- If `git status --short` is dirty before starting a WP, stop and report.
- Never delete or overwrite user files without explicit instruction.
- If Codex defers a material issue, unavailable tool, unresolved dependency, blocked security check, or postponed decision, it must add or update an entry in `docs/deferred_items_log.md` in the same WP.
- Whenever Codex completes a WP, it must create or prepare a pull request and provide the PR review link in the final report, unless the user explicitly says no PR should be created.

## Trading Safety

- No live trading is allowed unless explicitly authorized in `docs/live_trading_authorization.md`.
- Strategy modules may only propose trades.
- The risk engine and execution gateway are deterministic and cannot be overridden by AI, Hermes, or Codex.
- AI, Hermes, and Codex may assist with research, monitoring, reporting, summaries, and code generation, but may not directly place live trades.
- Runtime execution, OMS, reconciliation, risk caps, bounded overlay semantics, safe mode, configs, and live-trading paths are protected boundaries.

## External Code

- No external repo code may be copied before license, security, and compatibility audit.
- Before any work package adds runtime dependencies, external code, venue API clients, trading execution paths, or copied source from an audited repo, Codex must check `docs/deferred_items_log.md` and `docs/security_tooling_status.md` and confirm relevant security-tooling gates are satisfied or explicitly deferred by the user.
- Research and workbench artifacts have no execution authority unless explicitly promoted through an approved WP.
- Untrusted external code must not be allowed to place live orders.

## Secrets

- No secrets in repo, docs, logs, tests, screenshots, or PRs.
- Do not commit API keys, private keys, wallet keys, mnemonic phrases, passphrases, tokens, or realistic secret placeholders.
- Use local environment variables or a future approved secret manager for credentials.
