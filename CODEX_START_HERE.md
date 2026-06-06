# Codex Start Here

## Purpose

This is the first file Codex should read after a work package is received, after `AGENTS.md` if the active environment automatically starts there.

It gives the concise startup sequence for this repository. It does not authorize broader scope than the active work package.

## Mandatory Startup Sequence

1. Read `AGENTS.md`.
1b. Read `CLAUDE_START_HERE.md` (Claude Code only — skip if running as Codex/OpenAI environment).
2. Read `docs/project_status.md`.
3. Read `docs/repo_truth_index.md`.
4. Read `docs/deferred_items_log.md`.
5. Read `docs/codex_execution_guidelines.md`.
6. Read `docs/ai/codex/README.md`.
7. Read only task-relevant repo-truth files after that.

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

## Posted GitHub Evidence Verification (WP58+)

Local PR body and final comment drafts are not posted GitHub evidence. Before `Ready for review: YES`, Claude Code must select an evidence mode per the state machine and document it completely. See `docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md`.
