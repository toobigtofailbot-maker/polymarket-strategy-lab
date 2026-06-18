# Follow-Up Prompt Standard

## Status

- Standard version: V1
- Introduced in: WP88
- Applies to: all follow-up responses to not-merge-ready reviews

## Purpose

Ensure every follow-up addresses the root cause of a not-merge-ready review, not only the visible symptom. WP87 follow-ups that patched the symptom while leaving the underlying evidence lifecycle or repo architecture broken created compounding failures.

## 1. Root-Cause-First Rule

A follow-up must classify the root cause **before** describing the fix.

Reviewers must reject follow-ups that:

- patch only the visible symptom (e.g., update a SHA) without explaining why the SHA was wrong;
- describe what was done without explaining why the failure happened;
- leave an evidence lifecycle or repo architecture gap unfixed.

## 2. Required Follow-Up Template

Use this template for every follow-up to a not-merge-ready review:

```
# Follow-up — <PR/WP> Root-Cause Correction

## Classification

Root cause category (select one or more):
- [ ] A — evidence/reporting failure (stale SHA, drift between surfaces, missing marker)
- [ ] B — repo-truth/status reconciliation failure (project_status.md, repo_truth_index.md out of date)
- [ ] C — validation not rerun after final change (tests/guards not rerun after last edit)
- [ ] D — scope drift (change fell outside the allowed file prefix list)
- [ ] E — boundary/protected-scope risk (src/, tools/, .github/workflows/ touched without authorization)
- [ ] F — implementation logic defect (incorrect behavior, wrong output, wrong validation rule)
- [ ] G — test coverage gap (public field not tested, invalid path not tested, recursive scan missing)
- [ ] H — external/tooling/environment limitation (unavailable tool, platform constraint)
- [ ] I — reviewer-requested clarification without defect

## Current Live Facts

- PR: #<number>
- Live head (re-fetched from GitHub after last push): <SHA>
- Base commit: <SHA>
- Changed files (count): <N>
- Exact failing evidence or test: <quote the exact failure>

## Root Cause

State WHY the failure happened, not only what failed.

Example (wrong): "The SHA in the status fragment was incorrect."
Example (right): "The status fragment used `Head commit:` to record a SHA that was current
at the time of writing but became stale after the next follow-up commit. The standard
did not forbid tracking the current live PR head in the status fragment."

## Required Correction

1. Fix the invariant/lifecycle/root cause (not only the symptom).
2. Add a proof test or evidence check that would have caught this failure.
3. Update only allowed evidence surfaces.
4. Re-fetch live PR state after posting if posted evidence is involved.
5. Do not claim Ready for review: YES if the contradiction matrix fails.

## Forbidden Scope

List exact paths that must not be touched in this follow-up:
- (paths from the WP forbidden-scope list)

## Validation

Commands to run by file-change type:

If docs changed:
- python -m pytest tests/test_codex_workflow_docs.py -v
- python -m pytest tests/test_project_status_docs.py -v

If tests changed:
- python -m pytest <changed test file> -v
- python -m pytest (full suite)

If source changed:
- python -m pytest <focused test> -v
- python -m pytest (full suite)

Always:
- git diff --check
- python tools/git/preflight_generated_artifact_guard.py
- python tools/git/pr_evidence_consistency_guard.py <flags>

## Ready Rule

`Ready for review: YES` only if:
1. All tests pass.
2. Contradiction matrix passes (no invalid combination from EVIDENCE_ARCHITECTURE.md Section 6).
3. Evidence mode is declared.
4. Status fragment is stable/non-self-referential (no current live PR head as fixed SHA).
5. Final comment (if required) is a transition-only pointer, not a duplicate evidence table.

## Required Response Fields

Return exactly:

```
Root cause category: <A/B/C/D/E/F/G/H/I>
Root cause explanation: <why, not what>
Correction made: <what changed and why it fixes the root cause>
Proof added: <new test or evidence check>
Evidence surfaces updated: <which surfaces, and how>
Contradiction matrix: PASS/FAIL
Ready for review: YES/NO
```

```

## 3. Reviewer Check

Reviewers must confirm for every same-PR follow-up:

- [ ] Self-diagnosis block present (root cause category, explanation, correction, proof added).
- [ ] Root cause explains WHY the failure happened, not only what it was.
- [ ] Follow-up did not address only the symptom while leaving the underlying lifecycle or architecture gap open.
- [ ] Evidence contradiction matrix result is stated.
- [ ] Ready for review: YES only if all required checks pass.

## 4. Cross-References

- `docs/ai/codex/EVIDENCE_ARCHITECTURE.md` — evidence surface model and contradiction matrix
- `docs/ai/codex/RESULT_OUTPUT_INVARIANT_STANDARD.md` — field-coverage and no-echo invariants
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md` — reviewer checklist including follow-up classification
- `docs/ai/codex/WP_BUNDLING_POLICY.md` — follow-up defect classification categories
