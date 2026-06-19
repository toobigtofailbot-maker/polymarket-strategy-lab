# AI Coding Agent Rulebook

The AI coding agent must read this file before every work package. This rulebook applies to Codex and Claude Code equally, and to any future AI coding agent operating under this repository's WP discipline.

After this file, every AI coding agent must read `AI_CODING_AGENT_START_HERE.md`, then its tool-specific adapter (`CODEX_START_HERE.md` for Codex, `CLAUDE_START_HERE.md` for Claude Code), then the relevant workflow guidance under `docs/ai/codex/`.

## Repo Truth

- Repo truth overrides chat memory, handoffs, assumptions, and ad hoc instructions.
- Current merged state wins over older summaries.
- Major decisions must be recorded in repo-truth docs before they are treated as project policy.
- If a requested task conflicts with repo truth, follow repo truth and report the conflict.

## Work Package Discipline

- One WP = one branch = one PR.
- Do not work on `main`.
- Before any WP branch is created, the AI coding agent must run the Remote Main Sync Gate or equivalent commands proving local `main` equals `origin/main`, the working tree is clean, and previous WP merge evidence exists.
- If local `main` is stale, diverged, dirty, or missing required previous WP files, stop before branch creation.
- Generated local environments and security-tool artifacts must never be committed.
- If `.venv-security/`, `tools/.bin/`, `tools/security/.cache/`, or `security-scan-output/` appear in `git status`, the AI coding agent must stop and run the generated-artifact investigation and cleanup workflow before starting a WP.
- The AI coding agent must not use GitHub Desktop or equivalent GUI staging for generated artifact folders.
- Do not stack a new WP on a prior WP branch.
- Do not manually merge prior WP branches locally.
- Do not expand scope inside a WP.
- If `git status --short` is dirty before starting a WP, stop and report.
- Never delete or overwrite user files without explicit instruction.
- If the AI coding agent defers a material issue, unavailable tool, unresolved dependency, blocked security check, or postponed decision, it must add or update an entry in `docs/deferred_items_log.md` in the same WP.
- Whenever the AI coding agent completes a WP, it must create or prepare a pull request and provide the PR review link in the final report, unless the user explicitly says no PR should be created.
- After WP91, a full final report PR comment is optional and non-canonical. The PR body is the current review evidence surface; the stable status fragment is the committed repo record. Absence of a final PR comment is not a merge blocker. If an optional final comment is posted, it must not contradict the PR body.
- If the final validation environment cannot run required tests or checks, the AI coding agent must report blocked/not merge-ready rather than imply readiness.

## Trading Safety

- No live trading is allowed unless explicitly authorized in `docs/live_trading_authorization.md`.
- Strategy modules may only propose trades.
- The risk engine and execution gateway are deterministic and cannot be overridden by AI, Hermes, or Codex.
- AI, Hermes, and Codex may assist with research, monitoring, reporting, summaries, and code generation, but may not directly place live trades.
- Accepted AI/Hermes/Codex suggestions must flow through human review, approved config changes, or normal Codex work packages before they change repo or runtime behavior.
- Runtime execution, OMS, reconciliation, risk caps, bounded overlay semantics, safe mode, configs, and live-trading paths are protected boundaries.

## External Code

- No external repo code may be copied before license, security, and compatibility audit.
- Before any work package adds runtime dependencies, external code, venue API clients, trading execution paths, or copied source from an audited repo, the AI coding agent must check `docs/deferred_items_log.md` and `docs/security_tooling_status.md` and confirm relevant security-tooling gates are satisfied or explicitly deferred by the user.
- Research and workbench artifacts have no execution authority unless explicitly promoted through an approved WP.
- Untrusted external code must not be allowed to place live orders.

## Token Efficiency

- The AI coding agent must apply the token-efficiency operating model defined in `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md`.
- Context hygiene, validation-output summarization, concise reporting, and reusable prompt-block rules are binding on all WPs.
- Token efficiency must never weaken validation, skip required checks, or omit failure evidence.

## PR Evidence Reporting Discipline

- The AI coding agent must use exact PR body and stable status-fragment evidence discipline before requesting review on any WP. Optional final PR comments may be posted for reviewer clarity but are non-canonical and must not contradict the PR body. See `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`.
- Abbreviated validation commands, ellipses in command evidence, stale counts, and inaccurate network usage wording must all be corrected before Ready for review: YES.
- The PR body and the stable status fragment must not contradict each other on test counts, command results, files changed, or network usage. After WP91, if an optional final comment is posted, it must not contradict the PR body.
- Network usage wording must accurately distinguish workflow network use (Remote Main Sync Gate, git fetch/pull/push, PR publication) from runtime/API/product/account network behavior. Do not say "no network" if git remote synchronization or PR publication ran.
- Ready for review: YES is forbidden if any evidence defect remains uncorrected.

## Secrets

- No secrets in repo, docs, logs, tests, screenshots, or PRs.
- Do not commit API keys, private keys, wallet keys, mnemonic phrases, passphrases, tokens, or realistic secret placeholders.
- Use local environment variables or a future approved secret manager for credentials.

## Canonical WP Execution State Machine

Detailed WP execution, evidence packaging, evidence-mode selection, and review-readiness decisions are governed by `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md`.

If another workflow doc conflicts with the state machine, the state machine wins unless the active WP gives a narrower package-specific instruction.

Private-repo manual live verification is a first-class evidence mode only when the state machine's required fields are complete.

## Tool-Specific Startup Adapters

- Codex must read `CODEX_START_HERE.md` for Codex-specific startup guidance.
- Claude Code must read `CLAUDE_START_HERE.md` for Claude Code-specific startup guidance, posted evidence verification rules, and stop rules.

## Posted GitHub Evidence Verification

Local PR body and final comment drafts are not posted GitHub evidence. Before `Ready for review: YES`, the AI coding agent must select exactly one evidence mode from `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` (PUBLIC_VERIFIER_PASS, PRIVATE_REPO_MANUAL_VERIFIED, or BLOCKED_NOT_READY) and document it completely in the PR body. See `docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md`. After WP91, a final GitHub comment is not required; the evidence mode declaration belongs in the PR body only.

## Negative Test Matrix Policy

WPs that add or modify validators, scorers, parsers, schema validators, boundary guards, evidence guards, or semantic wording filters must include a negative-test matrix before `Ready for review: YES`. See `docs/ai/codex/NEGATIVE_TEST_MATRIX_POLICY.md`.

## WP Drafting Standard (WP86+)

All WPs from WP86 onward must be drafted to execution-package discipline. This means every WP must include: Authority / Non-Authority Posture, Hard Merge Gate, Context Budget, Compatibility / Impossibility Check (nontrivial WPs), Concrete Stop Conditions tied to risk class, Requirement-to-Evidence Traceability (M/L/XL WPs), and a committed status fragment (`docs/status_entries/WP<NN>.md`). See `docs/ai/codex/WP_DRAFTING_STANDARD.md`.

## Status Fragments (WP86+)

Every WP from WP86 onward must commit a status fragment at `docs/status_entries/WP<NN>.md` on the WP branch before requesting review. Status fragments are committed evidence records and the preferred primary evidence surface. See `docs/status_entries/README.md`.

## Protected Boundary Groups (WP86+)

Protected boundary groups are centralized in `docs/ai/codex/PROTECTED_PATHS.md`. Future WPs must reference that document's Centralized Boundary Group Reference table in their Authority / Non-Authority Posture section rather than repeating inconsistent forbidden lists.
