# Codex Execution Guidelines

- Read `AGENTS.md` before every WP.
- Run `git status --short` and `git branch --show-current` before starting.
- Stop and report if the working tree is dirty before WP work begins.
- Before creating any WP branch, run the Remote Main Sync Gate or this equivalent sequence:
  - `git fetch origin --prune`
  - `git switch main`
  - `git pull --ff-only origin main`
  - verify `git status --short` is clean
  - verify local `HEAD` equals `origin/main`
  - verify required previous WP merge commit and required previous WP files
- Create one branch per WP.
- Open one PR per WP.
- Do not work on `main`.
- Do not stack a new WP on a prior WP branch.
- Do not manually merge prior WP branches locally.
- Do not continue from stale local `main`.
- Do not expand scope beyond the WP.
- Run required tests before final report.
- Whenever Codex completes a WP, create or prepare a pull request and provide the PR review link in the final report, unless the user explicitly says no PR should be created.
- Never delete user files without explicit instruction.
- Do not copy external repo code before audit.
- Do not add live trading code unless the WP explicitly authorizes it and `docs/live_trading_authorization.md` is updated.

## Stop Conditions

Stop if required work needs protected runtime boundaries, secrets, external code reuse, or live-trading paths not authorized by the WP.

## Expected Output After Each WP

Report WP ID, summary, branch name, commit hash, PR review link, files changed, tests run, results, safety confirmations, open issues, and the suggested next WP.
