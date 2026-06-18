# AI Coding Agent Workflow Guidance

> **Path compatibility note:** The `docs/ai/codex/` path is the current historical location for shared AI-coding-agent workflow docs. Unless a file explicitly says otherwise, these docs apply to Codex, Claude Code, and any future AI coding agent operating under this repo's WP discipline.

## Precedence

The AI coding agent must apply guidance in this order:

1. Current merged repo truth.
2. Active work package scope, including explicit forbidden scope.
3. `AGENTS.md`.
4. Workflow docs under `docs/ai/codex/`.
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

All AI coding agent execution must follow the token-efficiency operating model:

- `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` — context hygiene, summarization, and design gates.
- `docs/ai/codex/CONCISE_REPORTING_RULES.md` — mandatory final report format and omission rules.
- `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md` — standard blocks for preflight, security, validation, reporting, and safety.
- `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md` — WP29 design-only document for a future local/offline/read-only diff scope summary helper. This document does not authorize implementation; a future approved implementation WP is required.
- `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md` — WP31 design-only document for a future local/offline/read-only validation-output summary helper. This document does not authorize implementation; a future approved implementation WP is required.
- `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md` — WP35 design document for the local/offline/read-only memory/status snapshot helper; WP36 added implementation decisions in Section 19.
- `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md` — WP36 user-facing reference for the implemented local/offline/read-only memory/status snapshot helper (`tools/git/status_snapshot.py`). Advisory only. Does not replace repo truth, validation, or human review.
- `docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md` — WP37 docs-only
  closeout for the WP28-WP36 helper sequence. It defines operational helper
  usage order and remaining deferred items; it does not authorize product,
  advisory-agent, Hermes, runtime, database, dashboard, scheduler, polling, or
  trading work.

Token efficiency must never weaken validation, skip required checks, or omit failure evidence from final reports.

## Operating Rule

Active work package forbidden scope wins. Nested or supporting docs do not authorize protected runtime work. If a safe implementation would require protected runtime paths, dependencies, credentials, live trading behavior, or scope expansion, the AI coding agent must stop and report instead of improvising.

## Canonical WP Execution State Machine (WP59+)

`docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` is the canonical state machine for all WP execution phases, evidence mode selection, and review-readiness gates. It applies to Ask Mode, Code Mode, and Review Mode boundaries.

Before `Ready for review: YES`, select exactly one evidence mode from the state machine: `PUBLIC_VERIFIER_PASS`, `PRIVATE_REPO_MANUAL_VERIFIED`, or `BLOCKED_NOT_READY`.

## Tool-Specific Startup Adapters (WP60A+)

The shared startup file `AI_CODING_AGENT_START_HERE.md` is the entry point for all AI coding agents. After that, each tool reads its adapter:

- Codex: read `CODEX_START_HERE.md` for Codex-specific startup guidance.
- Claude Code: read `CLAUDE_START_HERE.md` for Claude Code-specific startup guidance, posted evidence verification rules, and stop rules.

Before `Ready for review: YES`, the AI coding agent must select the correct evidence mode per `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md`. If the public unauthenticated verifier is unavailable (exit 3), use `PRIVATE_REPO_MANUAL_VERIFIED` with complete manual verification fields. See `docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md`.

## Negative Test Matrix (WP58+)

WPs that add or modify validators, scorers, parsers, schema validators, boundary guards, evidence guards, or semantic wording filters must include a negative-test matrix before `Ready for review: YES`. See `docs/ai/codex/NEGATIVE_TEST_MATRIX_POLICY.md`.

## WP Drafting Standard (WP86+)

All WPs from WP86 onward must follow the execution-package drafting discipline. See `docs/ai/codex/WP_DRAFTING_STANDARD.md` for:
- Mandatory front matter
- Authority / Non-Authority Posture
- Hard Merge Gate
- Context Budget
- Compatibility / Impossibility Check
- Concrete Stop Conditions
- Requirement-to-Evidence Traceability
- Evidence model and status fragments

## Status Entries / Committed Evidence Fragments (WP86+)

Every WP from WP86 onward commits a status fragment at `docs/status_entries/WP<NN>.md`. These are the preferred committed evidence surface for WPs — they travel with the branch and cannot be accidentally superseded by a later comment.

See `docs/status_entries/README.md` for the required format and the evidence distinction policy (LOCAL_DRAFT_VERIFIED vs POSTED_GITHUB_API_VERIFIED vs MANUAL_UI_VERIFIED).

## Evidence Architecture — Model D (WP88+)

From WP88 onward, all evidence surfaces must comply with Model D from `docs/ai/codex/EVIDENCE_ARCHITECTURE.md`:

- **PR body** is the current review evidence surface (current live PR head, validation, guards, traceability).
- **Status fragment** is a stable non-self-referential repo record — it must not record the current live PR head as a fixed SHA.
- **Final GitHub comment** is a transition-only verification pointer during WP86–WP90.
- The evidence contradiction matrix must be checked before `Ready for review: YES`.

## Result Object And Output Invariant Standard (WP88+)

WPs that introduce result objects, loaders, validators, or report generators must satisfy `docs/ai/codex/RESULT_OUTPUT_INVARIANT_STANDARD.md`:

- All public fields enumerated and classified.
- Field-coverage test proves serializer covers all public fields.
- Invalid result objects scanned recursively.
- Manual serializers forbidden unless field-coverage test is present.

## Follow-Up Prompt Standard (WP88+)

Every follow-up to a not-merge-ready review must follow `docs/ai/codex/FOLLOWUP_PROMPT_STANDARD.md`:

- Root cause classified before the fix is described.
- Root cause explains WHY the failure happened, not only what it was.
- Evidence contradiction matrix result is stated.
- Follow-up does not patch only the visible symptom.

## Shared Claude/Codex Operating Layer

All files under `docs/ai/codex/` apply to Codex, Claude Code, and all future AI coding agents unless a specific file says otherwise. The path `docs/ai/codex/` is a historical naming artifact — it is the shared AI-coding-agent workflow layer, not a Codex-only layer.

Claude-specific and Codex-specific files (`CLAUDE_START_HERE.md`, `CODEX_START_HERE.md`) are thin adapter entrypoints only. They add tool-specific startup notes and do not duplicate or override the shared layer in `docs/ai/codex/`.

Prompt wrappers (e.g., `prompts/execution_brief.md`, `.claude/skills/*.md`) are compatibility wrappers only and are not canonical. Canonical standards are: `AGENTS.md`, `AI_CODING_AGENT_START_HERE.md`, `CODEX_START_HERE.md`, `CLAUDE_START_HERE.md`, `docs/project_status.md`, `docs/repo_truth_index.md`, `docs/work_package_template.md`, and `docs/ai/codex/*.md`.

## Protected Boundaries Centralized (WP86+)

Protected boundary groups are centralized in `docs/ai/codex/PROTECTED_PATHS.md`. Future WPs must reference that document's boundary group table rather than repeating inconsistent forbidden lists. See the Centralized Boundary Group Reference section in that document.
