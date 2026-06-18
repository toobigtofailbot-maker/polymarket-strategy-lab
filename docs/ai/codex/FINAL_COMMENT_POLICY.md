# Final Comment Policy

## Status

- Final comment policy status: OPTIONAL_AFTER_WP91
- Decision made in: WP91
- Applies to: all WPs after WP91
- Supersedes: WP86–WP90 transition policy requiring final GitHub PR comments

## Decision

After WP91, mandatory final GitHub evidence comments are **retired**.

Final comments are optional reviewer clarifications only. They are not required for merge readiness.

## Evidence Mode After WP91

```
Evidence mode: PR_BODY_CURRENT_REVIEW_SURFACE
Status fragment mode: STABLE_NON_SELF_REFERENTIAL
Final comment mode: OPTIONAL_REVIEW_CLARIFICATION
```

## What Is Required After WP91

1. **GitHub PR metadata** — source of truth for the current live PR head SHA.
2. **PR body** — current review evidence surface (validation, guards, changed files, traceability).
3. **Status fragment** (`docs/status_entries/WP<NN>.md`) — stable non-self-referential repo record.

A PR is merge-ready when PR body + status fragment evidence is complete and consistent.
A final comment is not required.

## What Is Optional After WP91

A final GitHub PR comment may be posted voluntarily for reviewer clarity.

If posted, it must:

- state explicitly that it is optional and non-canonical
- not contradict the PR body
- not claim to supersede the PR body as the current review evidence surface
- not encode a current live PR head as a fixed SHA

Recommended wording for any voluntarily posted final comment:

> This comment is optional and non-canonical; the PR body is the current review evidence surface.

## What Is Forbidden After WP91

The following are forbidden and must block merge:

- PR body claims final comment is required for merge readiness
- PR body says "final comment will be posted after merge" as a required evidence step
- Optional final comment contradicts PR body
- Optional final comment claims canonical evidence authority
- Merge blocked solely because no final comment exists

## Historical Context (WP86–WP90 Transition)

During the WP86–WP90 transition, final GitHub comments were required as short transition markers. They were required to start with "CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments" and contain a validation summary mirrored from the PR body, a posted evidence self-check (`POSTED_GITHUB_API_VERIFIED` or `MANUAL_UI_VERIFIED`), and a re-fetched current live PR head.

That transition was explicitly limited to WP86–WP90. WP91 closes the transition, removes the mandatory final-comment surface, and makes PR body + status fragment the complete evidence model.

## Why This Decision Was Made

WP87–WP90 repeatedly showed that final comments create stale-head follow-up loops:

- The final comment head SHA becomes stale after each subsequent commit.
- Re-fetching after every commit adds work without adding safety.
- The PR body and status fragment already capture all necessary review evidence.
- The committed status fragment cannot be accidentally superseded by a later comment.

The PR body is a better current-evidence surface: it is always current, always visible to reviewers, and updated in-place rather than replaced by new comments.

## Analogy

We used a temporary extra stamp (final comment) while changing the inspection system. Now that the new system is installed (PR body + status fragment), WP91 removes the temporary stamp. The PR body is the current checklist; the status fragment is the archive card.

## Cross-References

- `docs/ai/codex/EVIDENCE_ARCHITECTURE.md` — Model D evidence architecture; defines PR body, status fragment, and final comment roles
- `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` — PR evidence reporting rules (updated for WP91)
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md` — reviewer checks (updated for WP91)
- `docs/ai/codex/VALIDATION_MATRIX.md` — validation requirements by package class (updated for WP91)
- `docs/status_entries/README.md` — status fragment format and policy (updated for WP91)
- `.github/pull_request_template.md` — PR template (updated for WP91)
