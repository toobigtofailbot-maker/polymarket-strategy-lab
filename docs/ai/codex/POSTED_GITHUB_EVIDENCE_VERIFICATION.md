# Posted GitHub Evidence Verification

Status: `WORKFLOW_GOVERNANCE_MANDATORY`

Applies to: Codex and Claude Code. The GitHub helper is read-only, manual, workflow-only.

---

## Problem

The local PR evidence consistency guard (`tools/git/pr_evidence_consistency_guard.py`) validates local drafts only:

- It does not fetch live GitHub PR body.
- It does not prove the PR body was actually updated on GitHub.
- It does not prove the final evidence comment was posted to GitHub.
- It does not identify the latest current-final comment in GitHub's comment history.

Passing the local guard is necessary but not sufficient to prove posted GitHub evidence is correct.

---

## Required Workflow After WP58

1. Prepare PR body draft locally.
2. Prepare current-final evidence comment draft locally.
3. Run local `pr_evidence_consistency_guard.py` on both drafts.
4. Post or update the PR body on GitHub.
5. Post the current-final evidence comment on GitHub.
6. Run `posted_pr_evidence_verifier.py` against the live GitHub PR.
7. If the verifier fails: `Ready for review: NO`.
8. If the verifier cannot run due to network or tool limitation: state that explicitly, perform manual verification by inspecting live GitHub PR body and comments, and document the result. `Ready for review: NO` unless manual live verification is fully documented.

---

## Current-Final Comment Rule

The latest valid evidence comment must:

- Start with or contain: `CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments`
- Include the current head SHA.
- Include a guard result line, checked categories, and exit code.
- Include `Guard input source:`.

Older current-final comments must be superseded by the latest one.

---

## PR Body Rule

The PR body must state whether live GitHub posted evidence was verified. After WP58, it must include:

- The `posted_pr_evidence_verifier.py` command used.
- The verifier result.
- The latest current-final comment URL if available.

---

## Standard Wording

When verifier passes:

```
Posted GitHub evidence verifier: PASS; exit 0
Verified PR body head SHA: <sha>
Verified latest current-final evidence comment SHA: <sha>
```

When verifier cannot run:

```
Posted GitHub evidence verifier: UNAVAILABLE — <reason>
Manual live GitHub verification performed: YES/NO
Manual verification result: <description>
```

---

## Failure Examples

- No comments exist on the PR.
- Comments exist but none contain `CURRENT FINAL WP EVIDENCE`.
- Current-final comment exists but contains a stale head SHA.
- Guard result is missing from the current-final comment.
- PR body was updated but the current-final comment was never posted.
- Current-final comment was posted but PR body was not updated.
- Placeholder tokens (`<HEAD_SHA>`, `TBD`, `TODO`, `placeholder`) remain in either surface.
- Guard input source is missing from the current-final comment.
- PR body and current-final comment contain different head SHAs.

---

## Non-Goals

This workflow does not:

- Post or edit GitHub content.
- Require authentication or tokens.
- Support private repos in WP58.
- Replace human review.
- Prove that tests actually passed (only that the guard reported passing).

---

## Cross-References

- `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`
- `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md`
- `docs/ai/codex/WP_EXECUTION_REPORT.md`
- `docs/ai/codex/WP_BUNDLING_POLICY.md`
- `.github/pull_request_template.md`
- `tools/git/posted_pr_evidence_verifier.py`
