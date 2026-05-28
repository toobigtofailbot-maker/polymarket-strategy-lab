# Token Efficiency Operating Model

## Status

- Token-efficiency operating model status: ACTIVE_REPO_TRUTH_GUIDANCE
- Applies to: Codex and Claude Code
- Validation impact: NO_VALIDATION_WEAKENING
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Protected-boundary impact: NO_PROTECTED_BOUNDARY_CHANGE

## Purpose

Reduce unnecessary context volume and repeated boilerplate while preserving validation integrity and safety boundaries. Apply to Codex and Claude Code execution, reviews, and prompt drafting.

This model does not authorize skipping any required preflight, validation, security check, final PR comment, or repo-truth update. Any apparent conflict between token savings and validation must resolve in favor of validation.

## Core Principles

- Repo truth wins over summaries, chat memory, and handoffs.
- Read targeted files, not the entire repo, after completing the mandatory startup docs.
- Summarize command outputs without hiding failure evidence.
- Reuse prompt blocks by reference to reduce boilerplate.
- Keep final reports concise but evidence-complete.
- Never skip or shorten validation for token savings.
- Do not omit failed checks, unavailable tools, or boundary drift from reports.

## Context Hygiene Rules

1. Complete the mandatory startup doc sequence first (`AGENTS.md`, `docs/project_status.md`, `docs/repo_truth_index.md`, `docs/deferred_items_log.md`, `docs/codex_execution_guidelines.md`, `docs/ai/codex/README.md`).
2. After startup, read only files directly relevant to the active WP scope.
3. Avoid re-reading large docs unless the active WP modifies or depends on them.
4. Prefer exact line references, changed-file summaries, and targeted file reads over pasting full file contents into context.
5. Do not paste full test logs or large command outputs into PR comments unless they are needed to diagnose a failure.
6. When listing files, prefer concise file-path lists over full-content reproduction.

## Validation-Output Summarization Rules

Report the following for each validation command:

- Command used (exact invocation).
- Exit code (if available).
- Pass / fail result.
- Test count, pass count, and failure count (for pytest).
- Warning count (if any).
- Artifact path or output path (if any).

When a check fails, include the relevant failure snippet. Do not hide or truncate failure output needed for diagnosis.

Do not replace validation with summaries alone. Full raw logs may remain local unless needed to debug a failure; the summary still must be present in the final report.

Unavailable tools must be reported as UNAVAILABLE/SKIPPED. Do not report them as passed.

## Concise Status-Entry Rules

When updating `docs/project_status.md`:

- Add the new WP ID, title, package class, changed files, deferred-item changes, and boundary-effect statements.
- Do not repeat long historical prose already present.
- Keep current-WP security wording accurate and updated to the current WP number.
- Do not claim security tools ran if they did not.

## Reusable Prompt-Block Rules

WPs may reference repo-local reusable prompt blocks (defined in `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`) for standard preflight, validation, final report, and safety language.

Reusable blocks reduce repeated boilerplate. They do not:

- Override the active WP's scope, forbidden scope, or acceptance criteria.
- Remove the requirement for package-specific required fields (WP ID, branch, previous merge commit, allowed files, forbidden scope, acceptance/failure criteria).
- Substitute for actual evidence in the final report.

## Future Helper-Tool Design Gates

Before implementing any token-efficiency helper tool, the following design discipline applies:

- **Command-output compression helper**: a design-first or narrow stdlib helper WP is required before any implementation. Must be stdlib-only with no external dependency.
- **Diff/scope summary helper**: safe as a local helper if stdlib-only and no runtime. Design doc or narrow WP first. See `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md` for the approved WP29 design.
- **Validation-output summary helper**: design-first WP required before implementation. Must be stdlib-only, local/offline/read-only, no command execution unless a future implementation WP explicitly scopes runner mode. See `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md` for the approved WP31 design. Must not weaken required validation or hide unavailable tools.
- **Code indexing / blast-radius helper**: design-only guidance is recorded in `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md`. Implementation remains not implemented and requires a separate approved WP. Any future helper must remain advisory only and must not replace package scope, raw logs, command execution, direct changed-file inspection, integrity views, registry validators, scoped pytest, full pytest, repo-truth file inspection, or semantic review. No external indexing tools without explicit approved WP.
- **Memory / status snapshot helper**: design-only guidance is recorded in `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md` (WP35). Implementation is not started and requires a separate approved implementation WP. Any future helper must be advisory only, local/offline/read-only, stdlib-only, stale-aware, sanitized, and repo-truth-derived. Snapshots must never replace repo-truth verification, direct file reads, validation, tests, security checks, human review, or final PR comments. No persistence layer without explicit approval.
- **External tools (RTK, code-review-graph, token-savior, or similar)**: design and security review WP required before any dependency addition or vendoring. No installation or import without explicit approved WP.

Helper tools added without an approved design WP violate this operating model and must be reverted.
