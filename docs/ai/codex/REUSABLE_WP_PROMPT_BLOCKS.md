# Reusable WP Prompt Blocks

## Applies To

Codex and Claude Code.

## Purpose

These blocks reduce repeated boilerplate across work packages. A WP may reference a block by name instead of reproducing the full text. The block text is authoritative; active WP scope, forbidden scope, and acceptance/failure criteria always override blocks where they conflict.

Reusable blocks do not:

- Replace package-specific WP fields.
- Authorize scope expansion beyond the active WP.
- Substitute for actual evidence in the final report.

## Required Per-WP Fields (Not Replaceable By Blocks)

Every WP must still specify:

- WP ID and title
- Branch name
- Required previous merge commit
- Package class
- Objective
- Allowed files (expected new and modified files)
- Forbidden scope
- Package-specific tests
- Acceptance criteria
- Failure criteria

## Standard Preflight Block

1. Confirm local branch is `main`.
2. Confirm working tree is clean (`git status --short`).
3. Run `python tools/git/preflight_generated_artifact_guard.py`. Stop if it fails.
4. Run `python tools/git/preflight_sync_main.py` with `--required-commit <hash>` and `--required-file` flags for all expected previous WP files. Stop if it fails.
5. Confirm local `HEAD` equals `origin/main`.
6. Confirm required previous merge commit is present in `git rev-list HEAD`.
7. Create WP branch only after clean preflight.

See `docs/codex_execution_guidelines.md` for the full sequence.

## Standard Security Check Block

Run in this order:

1. `python tools/security/verify_project_gitleaks.py` — report exit code and result.
2. `python tools/security/check_security_tools.py` — report availability of semgrep, pip-audit, and other tools.
3. `python tools/security/run_available_security_checks.py` — report result for each available tool.

Report unavailable tools as UNAVAILABLE/SKIPPED. Do not report them as passed. Unavailable tools are not a blocker for docs-only / no-dependency WPs, but the status must be stated honestly.

See `docs/security_and_secrets.md` and `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` for summarization rules.

## Standard Validation Block

After all changes are committed:

1. Run `python -m pytest tests/<wp-specific-test>.py` — report counts.
2. Run `python -m pytest` (full suite) — report counts.
3. Run `git diff --check` — confirm no whitespace errors.
4. Run `python tools/git/preflight_generated_artifact_guard.py` — confirm clean.

Do not claim merge-ready if any step fails or is blocked.

See `docs/ai/codex/VALIDATION_MATRIX.md` for package-class validation requirements.

## Standard Final Report Block

Final PR comment must include (concise but evidence-complete):

- WP ID / package class
- Branch / base / required previous merge commit
- Changed files
- Validation summary (commands, exit codes, counts)
- Boundary check (runtime/source/tooling/dependency/Hermes/credentials/trading)
- Deferred items changed
- Open issues / assumptions
- Ready for review: YES/NO

See `docs/ai/codex/CONCISE_REPORTING_RULES.md` and `docs/ai/codex/WP_EXECUTION_REPORT.md`.

## Standard Safety Boundary Block

Confirm in the final report:

- No runtime source under `src/` added or modified beyond WP scope.
- No dependency or lock files changed.
- No Hermes installation, Hermes runtime dependency, or Hermes config added.
- No agent runtime, agent CLI, scheduler, daemon, or bot loop added.
- No credentials, `.env`, API keys, private keys, wallet keys, or tokens added.
- No LLM dependency, provider SDK, or network calls added.
- No strategy signals, trade proposals, paper trading, or live trading paths added.
- No external code copied before license and security audit.

See `AGENTS.md` and `docs/runtime_boundaries.md`.

## Standard Generated Artifact Block

Before and after every WP:

- Run `python tools/git/preflight_generated_artifact_guard.py`.
- Confirm `.venv-security/`, `tools/.bin/`, `tools/security/.cache/`, `security-scan-output/`, `.venv-official-client/`, `official-client-sandbox-output/`, and `local_data/` are not in staged or committed files.
- Never commit generated artifacts, local environment files, or report/export outputs.

See `docs/codex_execution_guidelines.md`.

## Standard Stop/Escalation Block

Stop and report (do not continue) if:

- `main` is stale, diverged, dirty, or missing required previous WP evidence.
- Generated artifacts are visible before branch creation.
- Required previous merge commit is absent.
- Implementation requires new tooling, external dependencies, runtime code, network calls, or generated artifacts.
- Documentation would weaken validation, imply validation can be skipped, or authorize forbidden behavior.
- Tests fail.
- Security checks fail in a way that blocks the WP.
- PR cannot be created.

See `CODEX_START_HERE.md` stop rules and `AGENTS.md` escalation rules.
