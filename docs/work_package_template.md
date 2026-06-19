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
- Package class:
- Package size class:
- Evidence mode expected:
- Runtime impact:
- Product impact:
- Network impact:
- Credential impact:
- Dependency impact:
- Trading impact:

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

## Recommended Claude/Codex Mode

- Model/reasoning:
- Reason:
- Escalate to higher reasoning or STOP if:

## Authority / Non-Authority Posture

### Authorized in this WP

(List exact authorized subsystems: workflow docs, schema docs, validators, reports, etc.)

### Not authorized in this WP

(List exact forbidden subsystems: source/runtime, data-layer, paper engine, scheduler, credentials, live trading, etc.)

### Authority Posture Fields

- Implementation authority:
- Report/export authority:
- Paper authority:
- Execution authority:
- Live authority:
- Credential authority:
- Runtime/scheduler authority:
- Canonical evidence authority:
- Network authority:
- Dependency-change authority:

### Canonical Evidence / Runtime / Paper / Live Posture

(State evidence mode and any runtime/paper/live authority here. Reference `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md`.)

## Hard Merge Gate

Before doing substantive work, run:

```bash
git fetch origin --prune
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
git log -1 --oneline
git status --short --branch
```

Required checks:
1. Required previous PR is merged.
2. Record required previous PR final head SHA.
3. Record required previous PR merge commit.
4. Verify main contains required previous PR final head SHA.
5. Verify no newer conflicting PR merged.
6. Verify no open WP branch for this WP exists locally or remotely.
7. Verify no open PR for this WP exists.
8. Verify target doc does not already claim this WP complete.

If any condition fails, STOP and report before proceeding.

Merge gate result:
- Required previous PR merged: YES/NO
- Required previous PR final head SHA:
- Required previous PR merge commit:
- main contains required head: YES/NO
- No conflicting newer PR: YES/NO
- No existing WP branch: YES/NO
- No existing WP PR: YES/NO

## Context Budget

Read first:
- AGENTS.md
- AI_CODING_AGENT_START_HERE.md
- CODEX_START_HERE.md / CLAUDE_START_HERE.md
- docs/project_status.md
- docs/repo_truth_index.md
- docs/deferred_items_log.md
- docs/ai/codex/README.md

Read for this package:
- (list files directly changed or inspected for this specific WP)

Read only if blocked:
- (list files to read only if a specific blocker arises)

Do not read / do not touch:
- src/ (unless explicitly authorized)
- tools/ (unless explicitly authorized)
- requirements.txt, pyproject.toml, package.json, lock files
- local_data/
- credentials, .env files

Search terms if paths changed:
- (list fallback search terms if key files have moved)

## Compatibility / Impossibility Check

(Required for nontrivial WPs: validators, reports, schemas, exports, collectors, workflow WPs, large bundles, any WP touching evidence policy or advisory output surfaces.)

| Required behavior | Controlling repo mechanism | Files likely needed | Allowed in this WP? | Compatible? | Action |
|---|---|---|---:|---:|---|
| (describe required behavior) | (controlling doc or mechanism) | (files) | YES/NO | YES/NO | (update docs/tests, split WP, STOP) |

If any row shows "not allowed" or "not compatible", STOP or split before proceeding.

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

**WP91 update:** After WP91, final GitHub evidence comments are optional and non-canonical. Absence of a final comment is not a merge blocker after WP91. Required evidence surfaces after WP91 are the PR body and the stable/non-self-referential status fragment. If an optional final comment is posted, it must not contradict the PR body and must state it is optional and non-canonical.

## Posted PR Evidence Discipline — Historical WP47/WP54/WP58/WP86–WP90 Only (Not Active After WP91)

**Not active after WP91.** The following applied during WP86–WP90 only. After WP91, final comments are optional and non-canonical.

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

## Posted GitHub Evidence Verification — Historical WP58/WP86–WP90 Only (Not Active After WP91)

**Not active after WP91.** The posted verifier workflow and current-final comment requirement applied during WP86–WP90 only. After WP91, the posted verifier is not a required final-comment merge gate.

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

## Posted Evidence Self-Check — Historical WP54/WP86–WP90 Only (Not Active After WP91)

**Not active after WP91.** The following applied during WP86–WP90 only. After WP91, no final comment is required.

Before Ready for review: YES, the AI coding agent must declare one of the following in both the PR body and the final comment:

1. Guard ran on exact local draft texts intended for posting as-is. State: "Guard input source: exact local drafts intended for posting."
2. Already-posted PR body and latest current-final evidence comment were copied into local temp files and the guard ran on those copies. State: "Guard input source: copied from posted GitHub PR body and current-final comment."

If any posted evidence changes after the last guard run, the guard must be rerun. If the AI coding agent cannot confirm the live GitHub content matches what the guard checked, it must state that limitation and may not claim posted evidence was verified.

## Evidence Architecture Model D (mandatory, WP88+)

Before Ready for review: YES, confirm all of the following:

```
Evidence architecture: Model D (docs/ai/codex/EVIDENCE_ARCHITECTURE.md)
PR body is current review evidence surface: YES/NO
Status fragment is stable/non-self-referential: YES/NO
Status fragment current live PR head as fixed SHA: ABSENT (must be absent)
Status fragment uses "Validated implementation commit:" label: YES/NO
Final comment is optional/non-canonical after WP91: YES/NO/NOT_APPLICABLE
Evidence contradiction matrix: NO invalid combinations present
NOT_VERIFIED + Ready YES combination: ABSENT (must be absent)
```

## Result Object Field-Coverage Gate (mandatory for result/report/loader/validator WPs, WP88+)

If this WP introduces a result object, loader, validator, or report generator:

```
Field-coverage gate required: YES / NO
If YES:
  - All public fields enumerated: YES/NO
  - Each field classified scanned/exempt/forbidden: YES/NO
  - Field-coverage test (fields(ResultType) <= set(serialized)): YES/NO
  - Invalid result objects scanned recursively: YES/NO
  - Manual serializer (if used) has field-coverage test: YES/NO
```

See `docs/ai/codex/RESULT_OUTPUT_INVARIANT_STANDARD.md`.

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

## Concrete Stop Conditions

(List concrete stop conditions tied to this WP's risk class. Generic STOP language is insufficient. Each condition must name the specific trigger and consequence.)

For output WPs (validators, reports, exports), include:
- STOP if invalid-output no-echo cannot be tested.
- STOP if central advisory output safety helper is unavailable.
- STOP if a validator returns raw invalid input in any output surface.
- STOP if a report copies raw metadata into output.
- STOP if any output surface cannot be recursively scanned for forbidden terms.

For all nontrivial WPs, include:
- STOP if changed files exceed the declared allowed scope.
- STOP if validation cannot be rerun after final source changes.
- STOP if any dependency or lock file would change.

(Add WP-specific stop conditions here.)

## Requirement-to-Evidence Traceability

(Required for nontrivial WPs — M, L, XL size class — before Ready for review: YES.)

| Requirement | Source WP section | Evidence location | Status |
|---|---|---|---|
| (requirement description) | (WP section number or name) | (test name, guard result, doc section, etc.) | SATISFIED/OPEN |

No `Ready for review: YES` without this table for M/L/XL WPs.

## Safety Confirmations

- No live trading code added unless explicitly authorized.
- No external repo code copied before audit.
- No secrets committed.
- Repo-truth docs updated.
- Scope respected.
- Pull request created or prepared with review link unless explicitly waived by the user.

## Status Fragment

Create `docs/status_entries/WP<NN>.md` as part of this WP. See `docs/status_entries/README.md` for the required format and field definitions.

The status fragment must be committed on the WP branch and merged with the PR.

- Status fragment path: docs/status_entries/WP<NN>.md
- Status fragment committed: YES/NO

## PR Body Required Sections

- Summary
- Package class and package size class
- Authorization / why now
- Hard merge gate result
- Compatibility / impossibility table (for nontrivial WPs)
- Files changed
- Adoption items implemented (for workflow WPs)
- Evidence model decision (for WPs touching evidence policy)
- Status-fragment convention decision (for WPs introducing new evidence conventions)
- Safety boundary confirmations
- Tests run with exact result counts and exact full commands (no ellipses)
- Helper validation results with exact full commands and all flags
- Security checks and results with exact commands
- Network usage (use standard distinction wording if git/PR network used)
- Generated artifact status
- Dependency and lock-file status
- Deferred items changed
- Requirement-to-evidence traceability table (for M/L/XL WPs)
- Follow-up prevention explanation (for workflow WPs)
- Open issues / deferred items
- Suggested next WP

## Final PR Comment Required Sections

**After WP91, a final PR comment is optional.** Absence of a final comment is not a merge blocker. If an optional final comment is posted, it must not contradict the PR body and must state it is optional and non-canonical.

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
- Q. Status fragment committed: YES/NO (docs/status_entries/WP<NN>.md)
- R. Requirement-to-evidence traceability table (for M/L/XL WPs)
- S. Ready for review: YES/NO

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
