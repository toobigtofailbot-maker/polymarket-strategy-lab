# Work Package Template

## WP ID

## Title

## Package Identity

- Work Package ID:
- Title:
- Repository:
- Base branch:
- Work branch:
- Required previous merge commit:
- Previous PR:

## Package Class

## Authorization Basis

- Active user approval:
- Repo-truth basis:
- Explicit forbidden scope:

## Objective

## Context

## Current Expected Repo Truth

- Current phase:
- Merged WPs:
- Runtime status:
- Safety boundary status:

## Scope

## Required Discovery Before Editing

- Required repo-truth files:
- Required changed-file inspection:
- Required PR or issue inspection:

## Security Tooling Impact

## Base Verification

- Base branch:
- Local main commit:
- Origin/main commit:
- Local main equals origin/main: yes/no
- Required previous WP commit present: yes/no
- Required previous WP files present: yes/no
- Remote Main Sync Gate result:
- Generated artifact guard result:
- Generated artifacts cleaned: yes/no
- Any generated artifacts visible in final git status: yes/no

## Out Of Scope

## Target Files

## Exact Changed-File Set

## Implementation Steps

## Tests

## Token Efficiency And Reusable Blocks

This WP may reference the following reusable blocks from `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`:

- Standard Preflight Block
- Standard Security Check Block
- Standard Validation Block
- Standard Final Report Block
- Standard Safety Boundary Block
- Standard Generated Artifact Block
- Standard Stop/Escalation Block
- Standard PR Evidence Reporting Discipline Block

Reusable blocks reduce boilerplate; they do not replace package-specific fields, forbidden scope, or acceptance/failure criteria.

See `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` and `docs/ai/codex/CONCISE_REPORTING_RULES.md` for concise report-back format.

## PR Evidence Reporting Discipline

Every WP must satisfy the Standard PR Evidence Reporting Discipline Block before Ready for review: YES. This means:

- PR body contains exact full validation command invocations (no ellipses, no abbreviated commands).
- Final top-level PR comment contains exact full validation command invocations.
- Network usage wording accurately distinguishes workflow network use from runtime/API/product/account network behavior.
- PR body and final PR comment are consistent on all counts, commands, and results.
- Stale counts corrected before Ready for review: YES.
- Unavailable tools reported as UNAVAILABLE/SKIPPED or SKIPPED_NOT_PRESENT, not as passed.
- `tools/git/pr_evidence_consistency_guard.py` run on local PR body and final comment drafts before Ready for review: YES. If guard fails, Ready for review must be NO. Report exact guard invocation and result in both PR body and final comment.

See `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`, `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`, and `docs/ai/codex/PR_REVIEW_CHECKLIST.md` for the full policy and reviewer-facing checks.

## Post-Final-Commit Validation

- Generated Artifact Guard after final commit:
- Focused tests after final commit:
- Full pytest after final commit:
- `git diff --check` after final commit:
- Security checks after final commit:

## Deferred Items Added/Updated/Resolved

## Deferred Security/Tooling Items Updated

## Acceptance Criteria

## Failure Criteria

## Stop/Report Triggers

- Main is stale, diverged, dirty, or missing previous WP evidence.
- Generated artifacts are visible in a forbidden way.
- Required validation cannot run.
- Implementation requires forbidden paths, dependencies, credentials, runtime behavior, or scope expansion.

## Safety Confirmations

- No live trading code added unless explicitly authorized.
- No external repo code copied before audit.
- No secrets committed.
- Repo-truth docs updated.
- Scope respected.
- Pull request created or prepared with review link unless explicitly waived by the user.

## PR Body Required Sections

- Summary
- Package class
- Files changed
- Safety boundary confirmations
- Tests run with exact result counts and exact full commands (no ellipses)
- Helper validation results with exact full commands and all flags
- Security checks and results with exact commands
- Network usage (use standard distinction wording if git/PR network used)
- Generated artifact status
- Dependency and lock-file status
- Deferred items changed
- Suggested next WP

## Final PR Comment Required Sections

- A. Work Package ID / package class
- B. Branch / base
- C. Repo-truth discovery
- D. Delivered changes
- E. Validation results
- F. Validation gates
- G. Repo-truth updates
- H. Deferred items
- I. Forbidden-scope check
- J. Generated-artifact check
- K. Security checks
- L. Network usage
- M. PR / push status
- N. Open escalations / assumptions
- O. Ready for review: YES/NO

## Expected Codex Final Report

- Work Package ID
- Package class
- Summary
- Branch name
- Commit hash
- PR review link
- Base verification
- Files changed
- Tests run
- Test results
- Safety confirmations
- Deferred items added/updated/resolved
- Open issues / assumptions
- Ready for review: YES/NO
- Suggested next WP
