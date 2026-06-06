# Claude Start Here

## Purpose

This file is for Claude Code and other Claude-like coding agents. It does not replace `AGENTS.md` or `CODEX_START_HERE.md`. Read all three.

## Mandatory Startup Sequence

1. Read `AGENTS.md`.
2. Read `CLAUDE_START_HERE.md` (this file).
3. Read `CODEX_START_HERE.md`.
4. Read `docs/project_status.md`.
5. Read `docs/repo_truth_index.md`.
6. Read `docs/deferred_items_log.md`.
7. Read `docs/codex_execution_guidelines.md`.
8. Read `docs/ai/codex/README.md`.
9. Read only task-relevant files after that.

## Precedence

1. Current merged repo truth wins over memory, chat summaries, and old handoffs.
2. The active work package wins over generic workflow docs on package-specific scope.
3. Live GitHub PR state beats summaries and local drafts.
4. Chat memory and handoffs are supplementary only.

## Canonical WP Execution State Machine (WP59+)

Follow `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` for all WP execution, evidence packaging, evidence-mode selection, and review-readiness decisions.

## Claude-Specific Reminders

- Local PR body and final comment drafts are NOT posted GitHub evidence. A file on disk does not prove a GitHub comment was posted.
- Before saying `Ready for review: YES`, select exactly one evidence mode: `PUBLIC_VERIFIER_PASS`, `PRIVATE_REPO_MANUAL_VERIFIED`, or `BLOCKED_NOT_READY`. Document all required fields for the selected mode.
- Do not claim the posted evidence verifier passed unless you actually ran it against the live PR and it returned exit 0.
- In this private repo, public unauthenticated posted verifier exit 3 is not itself a process defect. It becomes a process defect only if PR evidence falsely reports PASS, omits the manual-verification fields, or sets Ready for review contrary to the state machine.
- Never call a manually inspected private-repo PR "posted verifier PASS." Use `PRIVATE_REPO_MANUAL_VERIFIED`.
- If GitHub API is unavailable or rate-limited, state that explicitly and use `PRIVATE_REPO_MANUAL_VERIFIED` with complete manual verification fields. Ready for review may be YES under this mode if all required fields are present.
- Review Mode must inspect live GitHub PR state, not local summaries.
- For WPs that add validators, scorers, parsers, schema validators, or boundary guards: the negative-test matrix policy in `docs/ai/codex/NEGATIVE_TEST_MATRIX_POLICY.md` applies.

## Stop Rules

Stop and report before branch creation or implementation if:

- `main` is stale, diverged, or dirty.
- Required previous merge evidence is missing.
- Generated artifacts are visible in a way that violates repo rules.
- The validation environment cannot run required checks.
- Safe implementation would require forbidden scope or protected runtime boundaries.
- Implementing a feature requires authentication, token loading, or secret access not approved by the WP.
- Posted evidence verification requires write access to GitHub.
- Any protected path (src/data_layer/, tools/polymarket/, tools/advisory/, tools/agent/, tools/validation/) would be modified by a workflow-only WP.
- The WP's changed-file count exceeds 35 without explicit user authorization.
