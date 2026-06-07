# Codex Start Here

## Purpose

This file is the Codex-specific startup adapter for this repository.

It does not replace `AGENTS.md`. It does not replace `AI_CODING_AGENT_START_HERE.md`. Read all three.

Shared startup rules are in `AI_CODING_AGENT_START_HERE.md`. This file adds only Codex-specific notes.

## Mandatory Startup Sequence (Codex)

1. Read `AGENTS.md`.
2. Read `AI_CODING_AGENT_START_HERE.md`.
3. Read `CODEX_START_HERE.md` (this file).
4. Continue with repo-truth files per `AI_CODING_AGENT_START_HERE.md`:
   - Read `docs/project_status.md`.
   - Read `docs/repo_truth_index.md`.
   - Read `docs/deferred_items_log.md`.
   - Read `docs/ai/codex/README.md`.
   - Follow `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md`.
   - Read task-relevant files only after that.

## Precedence

1. Current merged repo truth wins over memory, chat summaries, and old handoffs.
2. The active work package wins over generic workflow docs on package-specific scope.
3. Actual changed files and live GitHub PR state beat summaries.
4. Chat memory and handoffs are supplementary only.

## Context Hygiene And Token Efficiency

After completing the mandatory startup sequence, read only files relevant to the active WP. Avoid re-reading large docs unless the WP directly modifies or depends on them. Prefer targeted file reads and exact line references over full-file reproduction. See `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` for the full operating model.

Token efficiency rules must never be used to skip required checks, shorten validation, or omit failure evidence.

## Stop And Report Rules

Stop and report before branch creation or implementation if:

- `main` is stale, diverged, or dirty.
- Required previous merge evidence is missing.
- Generated artifacts are visible in a way that violates repo rules.
- The validation environment cannot run required checks.
- Safe implementation would require forbidden scope or protected runtime boundaries.

## Canonical WP Execution State Machine (WP59+)

After completing the startup sequence, follow `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` for all WP execution, evidence packaging, and review-readiness decisions.

Do not infer evidence mode. Select exactly one:
- `PUBLIC_VERIFIER_PASS`
- `PRIVATE_REPO_MANUAL_VERIFIED`
- `BLOCKED_NOT_READY`
