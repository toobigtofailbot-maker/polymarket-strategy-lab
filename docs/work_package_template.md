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
- Tests run with exact result counts
- Security checks and results
- Network usage
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
