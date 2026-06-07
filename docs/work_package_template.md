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
- Execution agent:
- Shared startup file read: AI_CODING_AGENT_START_HERE.md — yes/no
- Tool-specific adapter read: CODEX_START_HERE.md / CLAUDE_START_HERE.md / other — yes/no

## Package Class

## Package Size Class

S / M / L / XL — see `docs/ai/codex/WP_BUNDLING_POLICY.md` for definitions.

## Risk-Class Bundle Justification

(Required for M and L packages. For S packages, state "S package — no bundle justification required".)

Why this bundle is safe within one risk class:
Why all changed files belong to the same objective:
What is explicitly excluded:
Rollback surface:
Changed-file budget (declared vs actual):
Mode-boundary table: (list each mode boundary and confirm it is not crossed)

## Forbidden Bundle Check

- [ ] This WP does not combine research scoring with trade recommendation wording.
- [ ] This WP does not combine data/report writer with buy/sell/entry/exit/sizing language.
- [ ] This WP does not combine paper trading with live trading.
- [ ] This WP does not combine credentials with order placement.
- [ ] This WP does not combine scheduler/bot loop with execution.
- [ ] This WP does not combine Hermes/agent runtime with execution authority.
- [ ] No dependency or runtime integration is bundled with feature logic without explicit approval.

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
- AI coding agent startup complete: yes/no
- Tool-specific adapter used:

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
- `tools/git/pr_evidence_consistency_guard.py` run with WP47 hardening flags and `--require-guard-result` on exact local drafts or copied posted content before Ready for review: YES. If guard fails, Ready for review must be NO. Report exact guard invocation AND full guard result output (result line, checked categories, exit code) in both PR body and final comment. A command invocation line alone is insufficient.

## Posted PR Evidence Discipline (mandatory, WP47)

- **Forbidden: file-list parenthetical test counts.** Do not write test counts in file-list descriptions or summary parentheticals such as "focused tests (34 tests)". Test counts belong only in validation result sections.
- **Required: current final evidence marker.** The final top-level PR comment must start with or contain "CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments" when it supersedes earlier evidence comments.
- **Required: Guard input source line.** Both PR body and final comment must include "Guard input source: exact local drafts intended for posting" or equivalent.
- **Forbidden: placeholder evidence tokens.** `<HEAD_SHA>`, `TBD`, `placeholder`, `actual:`, `TODO`, or fake SHA filler must not appear in PR body or final comment.

## Negative Test Matrix (mandatory when applicable, WP58)

State whether a negative-test matrix is required for this WP:

```
Negative test matrix required: YES / NO
```

If YES, list the categories covered from `docs/ai/codex/NEGATIVE_TEST_MATRIX_POLICY.md`.

If NO, explain why the matrix is not applicable (e.g., no validator/scorer/parser added or modified).

## Posted GitHub Evidence Verification (mandatory when available, WP58)

After posting the PR body and current-final evidence comment to GitHub, run:

```
python tools/git/posted_pr_evidence_verifier.py \
  --repo toobigtofailbot-maker/polymarket-strategy-lab \
  --pr <PR_NUMBER> \
  --expected-head <HEAD_SHA> \
  --require-current-final-marker \
  --require-guard-result \
  --require-ready-yes \
  --require-standard-network-wording \
  --forbid-placeholder-evidence \
  --forbid-inline-test-counts \
  --format text
```

State the verifier result in both the PR body and the final comment:
- If PASS: include the command, result, and verified head SHA.
- If UNAVAILABLE: state reason and describe manual live verification performed.

See `docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md` for full policy.

## Posted Evidence Self-Check (mandatory, WP54)

Before Ready for review: YES, the AI coding agent must declare one of the following in both the PR body and the final comment:

1. Guard ran on exact local draft texts intended for posting as-is. State: "Guard input source: exact local drafts intended for posting."
2. Already-posted PR body and latest current-final evidence comment were copied into local temp files and the guard ran on those copies. State: "Guard input source: copied from posted GitHub PR body and current-final comment."

If any posted evidence changes after the last guard run, the guard must be rerun. If the AI coding agent cannot confirm the live GitHub content matches what the guard checked, it must state that limitation and may not claim posted evidence was verified.

## Follow-Up Process-Defect Classification (mandatory, WP54)

Every review follow-up that required a correction must be classified. If no follow-up occurred, state so explicitly.

```
Follow-up correction required: YES/NO
Classification: (A/B/C/D/E/F/G/H/I or none)
Cause:
Resolution:
Systemic assessment:
Separate hardening WP needed: YES/NO
If NO, why not:
```

Classification categories: A=Evidence/reporting failure, B=Repo-truth/status reconciliation failure, C=Validation not rerun after final change, D=Scope drift, E=Boundary/protected-scope risk, F=Implementation logic defect, G=Test coverage gap, H=External/tooling/environment limitation, I=Reviewer-requested clarification without defect.

See `docs/ai/codex/WP_BUNDLING_POLICY.md` for the full follow-up classification policy and posted evidence self-check rule.

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

- A. Work Package ID / package class / package size class
- B. Branch / base / head SHA
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
- N. Follow-up process-defect classification
- O. Guard input source
- P. Open escalations / assumptions
- Q. Ready for review: YES/NO

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
