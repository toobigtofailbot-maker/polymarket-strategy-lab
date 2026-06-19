# Posted GitHub Evidence Verification

Status: `HISTORICAL_WP58_TO_WP90_PLUS_OPTIONAL_AFTER_WP91` — see Post-WP91 Policy section below.

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

## Post-WP91 Policy

After WP91, mandatory final GitHub evidence comments are retired.

Required current evidence surfaces:
1. GitHub PR metadata for current live PR head.
2. PR body as the current review evidence surface.
3. Stable non-self-referential status fragment.

Not required after WP91:
- current-final evidence comment exists;
- final comment starts with CURRENT FINAL WP EVIDENCE;
- final comment contains current live PR head;
- latest current-final comment URL/head SHA is present;
- posted verifier checks PR comments as a merge gate.

If an optional final comment is posted after WP91:
- it is non-canonical;
- it must not contradict the PR body;
- absence of that comment is not a merge blocker after WP91.

`Ready for review: YES` is allowed after WP91 when PR body + status fragment evidence is complete and consistent. No posted verifier run or final comment is required.

---

## Historical WP58/WP86–WP90 Workflow (Not Active After WP91)

The following sections describe the mandatory final-comment verification workflow that applied during WP58–WP90. This workflow is **not active after WP91**. It is preserved here for historical reference only.

---

## Evidence Modes

Select exactly one evidence mode before setting `Ready for review: YES`. See `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` for full phase definitions and required fields.

### PUBLIC_VERIFIER_PASS

Allowed only when the public unauthenticated GitHub API can read the live PR body and comments and the verifier returns exit 0.

Standard wording:

```
Evidence mode: PUBLIC_VERIFIER_PASS
Posted GitHub evidence verifier: PASS; exit 0
Verifier command: <exact command>
Verified PR body head SHA: <sha>
Verified latest current-final comment URL: <url>
Verified latest current-final comment head SHA: <sha>
Ready for review: YES/NO
```

### PRIVATE_REPO_MANUAL_VERIFIED

Allowed when the public unauthenticated GitHub verifier cannot access the PR body/comments due to private repo, access denied, rate limit, or tool unavailability.

For private repositories or environments where the public unauthenticated GitHub API cannot fetch PR body/comments, the posted GitHub evidence verifier must be reported as UNAVAILABLE with its exit code. Manual live GitHub verification may satisfy the posted-evidence requirement only under this mode.

Standard wording:

```
Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED
Posted GitHub evidence verifier: UNAVAILABLE; exit 3
Reason: private repo / public unauthenticated GitHub API cannot fetch posted PR evidence
Manual live GitHub verification performed: YES
Manual verification method: <GitHub UI / already-available GitHub connector / approved authenticated environment if separately authorized>
Verified PR body head SHA: <sha>
Verified latest current-final comment URL: <url>
Verified latest current-final comment head SHA: <sha>
Verified latest current-final comment contains: validation results, local guard result, follow-up classification, network wording, Ready for review
Ready for review: YES/NO
```

This is a valid evidence mode for private repos. Public verifier unavailable / exit 3 is not itself a process defect when documented under this mode.

This mode must never be reported as `Posted GitHub evidence verifier: PASS`.

### BLOCKED_NOT_READY

Required when manual verification is incomplete or when any required field cannot be confirmed honestly.

```
Evidence mode: BLOCKED_NOT_READY
Ready for review: NO
Blocker: <specific reason>
```

---

## Required Workflow After WP58

1. Prepare PR body draft locally.
2. Prepare current-final evidence comment draft locally.
3. Run local `pr_evidence_consistency_guard.py` on both drafts.
4. Post or update the PR body on GitHub.
5. Post the current-final evidence comment on GitHub.
6. Attempt `posted_pr_evidence_verifier.py` against the live GitHub PR.
7. Select evidence mode:
   - If verifier returns exit 0: use `PUBLIC_VERIFIER_PASS`.
   - If verifier returns exit 3 (private repo / resource not found): use `PRIVATE_REPO_MANUAL_VERIFIED` with complete manual verification fields.
   - If manual verification fields cannot be completed: use `BLOCKED_NOT_READY`.
8. `Ready for review: YES` allowed only under `PUBLIC_VERIFIER_PASS` or `PRIVATE_REPO_MANUAL_VERIFIED` with all required fields complete.

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

The PR body must state the evidence mode used. After WP58, it must include:

- The evidence mode declared.
- The `posted_pr_evidence_verifier.py` command used (even if UNAVAILABLE).
- The verifier result (PASS/UNAVAILABLE + exit code).
- The latest current-final comment URL if available.

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
- Public verifier returned exit 3 but evidence mode says `PUBLIC_VERIFIER_PASS`.
- Manual verification was performed but evidence reports it as posted verifier PASS.
- PR body references an older current-final comment as the latest.
- Ready YES with evidence mode BLOCKED_NOT_READY.

---

## Non-Goals

This workflow does not:

- Post or edit GitHub content.
- Require authentication or tokens.
- Implement authenticated or private-repo GitHub verification.
- Replace human review.
- Prove that tests actually passed (only that the guard reported passing).

---

## Cross-References

- `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` — canonical state machine; authoritative for evidence mode definitions
- `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`
- `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md`
- `docs/ai/codex/WP_EXECUTION_REPORT.md`
- `docs/ai/codex/WP_BUNDLING_POLICY.md`
- `.github/pull_request_template.md`
- `tools/git/posted_pr_evidence_verifier.py`
