# Codex Execution Guidelines

> **Compatibility note:** This file is historically named for Codex but applies to all AI coding agents unless a line is explicitly tool-specific. For shared startup, see `AI_CODING_AGENT_START_HERE.md`.

- Read `AGENTS.md` before every WP.
- Read `AI_CODING_AGENT_START_HERE.md` and the relevant tool-specific adapter (`CODEX_START_HERE.md` for Codex, `CLAUDE_START_HERE.md` for Claude Code) before every WP.
- Read `docs/ai/codex/README.md` before WP execution.
- Run `git status --short` and `git branch --show-current` before starting.
- Stop and report if the working tree is dirty before WP work begins.
- Before creating any WP branch, run `python tools/git/preflight_generated_artifact_guard.py`.
- If `.venv-security/`, `tools/.bin/`, `tools/security/.cache/`, or `security-scan-output/` are visible, verify they are untracked and unstaged, then run `python tools/git/cleanup_generated_artifacts.py --apply`.
- Before creating any WP branch, run the Remote Main Sync Gate or this equivalent sequence:
  - `git fetch origin --prune`
  - `git switch main`
  - `git pull --ff-only origin main`
  - verify `git status --short` is clean
  - verify local `HEAD` equals `origin/main`
  - verify required previous WP merge commit and required previous WP files
- Preferred execution model: one WP = one dedicated worktree = one branch = one PR. Using a dedicated worktree isolates WP work from other branches and reduces accidental scope bleed.
- Branch-only fallback is allowed but requires an explicit fallback note in the WP and PR body, confirmation of clean branch state before work starts, and no dirty main.
- Create one branch per WP.
- Open one PR per WP.
- Do not work on `main`.
- Do not stack a new WP on a prior WP branch.
- Do not manually merge prior WP branches locally.
- Do not reuse a prior WP branch unless explicitly confirmed by the user.
- Do not continue from stale local `main`.
- Do not expand scope beyond the WP.
- Run required tests before final report.
- The PR body does not replace the final report comment.
- Post the full WP final report as a top-level PR comment before requesting review.
- Rerun pytest after the final commit unless the active WP explicitly defines and justifies a narrower validation gate.
- Rerun `python tools/git/preflight_generated_artifact_guard.py` after the final commit.
- Update `docs/project_status.md` security wording to the current WP when checks are run or assessed in the current WP.
- Do not use "passed" wording for unavailable tools such as semgrep or pip-audit.
- Include exact base verification fields: base branch, local main commit, origin/main commit, whether local main equals origin/main, required previous WP commit presence, required previous WP files presence, Remote Main Sync Gate result, and Generated Artifact Guard result.
- Include `Ready for review: YES/NO`.
- Whenever the AI coding agent completes a WP, create or prepare a pull request and provide the PR review link in the final report, unless the user explicitly says no PR should be created.
- Never delete user files without explicit instruction.
- Do not copy external repo code before audit.
- Do not add live trading code unless the WP explicitly authorizes it and `docs/live_trading_authorization.md` is updated.

## Token Efficiency Discipline

Apply the token-efficiency operating model (`docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md`) on every WP:

- After completing the mandatory startup sequence, read only files relevant to the active WP.
- Prefer targeted file reads and exact line references over full-file reproduction.
- Summarize validation output (command, exit code, counts) without hiding failure evidence.
- Use reusable prompt blocks by reference (`docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`) to reduce boilerplate.
- Keep final reports concise but evidence-complete; see `docs/ai/codex/CONCISE_REPORTING_RULES.md`.
- Token efficiency must never skip, shorten, or omit required validation, security checks, or failure evidence.

## Stop Conditions

Stop if required work needs protected runtime boundaries, secrets, external code reuse, or live-trading paths not authorized by the WP.

## Claude Code Startup And Posted Evidence (WP58+; Claude-specific)

Claude Code must read `CLAUDE_START_HERE.md` in addition to `AGENTS.md` and `AI_CODING_AGENT_START_HERE.md` before every WP.

Before `Ready for review: YES`, Claude Code must run `tools/git/posted_pr_evidence_verifier.py` against the live PR when GitHub access is available. If unavailable, state why explicitly and document manual live GitHub verification. Do not claim the verifier passed unless it was actually run against the live PR. See `docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md`.

## WP Drafting Discipline (WP86+)

All WPs from WP86 onward must follow the execution-package drafting discipline in `docs/ai/codex/WP_DRAFTING_STANDARD.md`.

Required WP sections (WP86+):
- Authority / Non-Authority Posture
- Hard Merge Gate
- Context Budget
- Compatibility / Impossibility Check (nontrivial WPs)
- Concrete Stop Conditions (tied to risk class)
- Requirement-to-Evidence Traceability (M/L/XL WPs)
- Status Fragment (`docs/status_entries/WP<NN>.md`)

## Status Fragments (WP86+)

Every WP from WP86 onward must commit a status fragment at `docs/status_entries/WP<NN>.md` on the WP branch.

See `docs/status_entries/README.md` for the required format and evidence distinction policy.

## Expected Output After Each WP

Report WP ID, summary, branch name, commit hash, PR review link, files changed, tests run, results, safety confirmations, open issues, status fragment path, and the suggested next WP.
