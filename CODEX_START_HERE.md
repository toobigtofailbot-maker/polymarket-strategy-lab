# Codex Start Here

## Purpose

This is the first file Codex should read after a work package is received, after `AGENTS.md` if the active environment automatically starts there.

It gives the concise startup sequence for this repository. It does not authorize broader scope than the active work package.

## Mandatory Startup Sequence

1. Read `AGENTS.md`.
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

## Stop And Report Rules

Stop and report before branch creation or implementation if:

- `main` is stale, diverged, or dirty.
- Required previous merge evidence is missing.
- Generated artifacts are visible in a way that violates repo rules.
- The validation environment cannot run required checks.
- Safe implementation would require forbidden scope or protected runtime boundaries.
