# AI Coding Agent Start Here

## Purpose

This is the shared startup entry point for all AI coding agents operating in this repository.

It does not replace `AGENTS.md`. It does not replace tool-specific adapter files (`CODEX_START_HERE.md`, `CLAUDE_START_HERE.md`).

## Applies To

- Codex (OpenAI)
- Claude Code (Anthropic)
- Any future AI coding agent operating under this repo's WP discipline

## Mandatory Startup Sequence

Every AI coding agent must complete this sequence before any WP work:

1. Read `AGENTS.md`.
2. Read `AI_CODING_AGENT_START_HERE.md` (this file).
3. Read the tool-specific adapter:
   - Codex: read `CODEX_START_HERE.md`.
   - Claude Code: read `CLAUDE_START_HERE.md`.
   - Other agent: read the adapter if one exists; otherwise follow shared rules and report the missing adapter.
4. Read `docs/project_status.md`.
5. Read `docs/repo_truth_index.md`.
6. Read `docs/deferred_items_log.md`.
7. Read `docs/ai/codex/README.md`.
8. Follow `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` for all WP execution phases, evidence mode selection, and review-readiness gates.
9. Read task-relevant files only after completing steps 1–8.

## Precedence

Apply guidance in this order:

1. Current merged repo truth.
2. Active work package (scope, forbidden scope, acceptance/failure criteria).
3. Live GitHub PR state.
4. `AGENTS.md`.
5. `AI_CODING_AGENT_START_HERE.md` (this file).
6. Tool-specific adapter (`CODEX_START_HERE.md` or `CLAUDE_START_HERE.md`).
7. Workflow docs under `docs/ai/codex/`.
8. Chat memory and handoffs (supplementary only; lowest precedence).

## Evidence Mode

Before `Ready for review: YES`, the AI coding agent must select exactly one evidence mode from `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md`:

- `PUBLIC_VERIFIER_PASS` — public unauthenticated verifier returned exit 0.
- `PRIVATE_REPO_MANUAL_VERIFIED` — repo is private or verifier unavailable; manual live GitHub verification completed with all required fields.
- `BLOCKED_NOT_READY` — cannot satisfy either above mode; PR is not ready for review.

Do not infer evidence mode. Select exactly one and document all required fields.

## Stop Rules

Stop and report before branch creation or implementation if any of the following apply:

- Local `main` is stale, diverged, or dirty.
- Required previous WP merge evidence is missing.
- A generated artifact violation is present.
- Required validation cannot run.
- Safe implementation would require forbidden scope or protected runtime boundaries.
- Implementing the WP requires credentials or secret access not approved by the WP.
- Evidence mode cannot be satisfied.
- A WP60A or higher governance rule is violated by the proposed action.
