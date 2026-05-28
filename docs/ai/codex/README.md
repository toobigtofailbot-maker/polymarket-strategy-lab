# Codex Workflow Guidance

## Precedence

Codex must apply guidance in this order:

1. Current merged repo truth.
2. Active work package scope, including explicit forbidden scope.
3. `AGENTS.md`.
4. Codex workflow docs under `docs/ai/codex/`.
5. Chat memory, handoffs, and generic best practice.

Repo-side guidance is default discipline. It is not permission to broaden scope.

## Operating Modes

### Ask Mode

Use Ask Mode for planning, triage, and recommendations. Inspect repo truth before recommending action. Separate fact, inference, decision, open question, and future option.

### Code Mode

Use Code Mode for one locked work package on one branch. Confirm preflight gates, keep the changed-file set narrow, run required validation, publish one PR, and post the required final report comment.

### Review Mode

Use Review Mode for PR review. Inspect PR metadata, changed files, comments, checks, validation evidence, and boundary drift. PR body text alone is not evidence that final report discipline was satisfied.

## Token Efficiency And Concise Reporting

All Codex and Claude Code execution must follow the token-efficiency operating model:

- `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` — context hygiene, summarization, and design gates.
- `docs/ai/codex/CONCISE_REPORTING_RULES.md` — mandatory final report format and omission rules.
- `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md` — standard blocks for preflight, security, validation, reporting, and safety.
- `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md` — WP29 design-only document for a future local/offline/read-only diff scope summary helper. This document does not authorize implementation; a future approved implementation WP is required.
- `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md` — WP31 design-only document for a future local/offline/read-only validation-output summary helper. This document does not authorize implementation; a future approved implementation WP is required.
- `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md` — WP35 design-only document for a future local/offline/read-only memory/status snapshot helper. This document does not authorize implementation; a future approved implementation WP is required. Design docs do not authorize implementation until a future approved implementation WP.

Token efficiency must never weaken validation, skip required checks, or omit failure evidence from final reports.

## Operating Rule

Active work package forbidden scope wins. Nested or supporting docs do not authorize protected runtime work. If a safe implementation would require protected runtime paths, dependencies, credentials, live trading behavior, or scope expansion, Codex must stop and report instead of improvising.
