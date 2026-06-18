# Status Entries — Committed Per-WP Evidence Fragments

## Purpose

Status entries are committed, per-WP evidence records. They are the preferred committed evidence surface for future work packages (WP86+).

Status entries replace the failure-prone pattern of relying solely on mutable GitHub PR comments as the only evidence record. A committed status entry is repo truth — it cannot be accidentally superseded by a later comment, and it travels with the branch.

Status entries complement — not replace — the existing PR evidence system during transition. Final GitHub PR comments remain required during transition (see Section 5 below).

## When to Create a Status Entry

Create a status entry for every WP from WP86 onward. The entry is committed on the WP branch and merged with the PR.

## Status Entry Format

Each WP gets one file: `docs/status_entries/WP<NN>.md`.

Required fields:

```markdown
# WP<NN> Status Entry

## Identity

- WP ID: WP<NN>
- Title:
- Branch:
- PR:
- Base commit:
- Head commit:
- Merge commit: (fill after merge)
- Evidence mode: PUBLIC_VERIFIER_PASS / PRIVATE_REPO_MANUAL_VERIFIED / BLOCKED_NOT_READY

## Authority Posture

- Package class:
- Implementation authority: YES/NO
- Report/export authority: YES/NO
- Paper authority: NO
- Execution authority: NO
- Live authority: NO
- Credential authority: NO
- Runtime/scheduler authority: NO
- Canonical evidence authority: (describe what evidence was produced)
- Network authority: (describe any network used)
- Dependency-change authority: YES/NO

## Scope Boundary

Changed files:
- (list each file)

Allowed prefixes:
- (list each allowed prefix for this WP's diff scope)

Forbidden prefixes:
- src/ (unless explicitly allowed)
- tools/ (unless explicitly allowed)
- requirements.txt, pyproject.toml, package.json, lock files

## Validation Summary

- Focused tests: (command → result)
- Adjacent tests: (command → result)
- Full pytest: (command → result)
- Diff scope summary: (command → result)
- Generated artifact guard: (command → result)
- PR evidence consistency guard: PASS/FAIL
- Security checks: PASS/UNAVAILABLE/SKIPPED

## Guard Summary

- PR evidence guard: PASS/FAIL
- Guard input source: LOCAL_DRAFT_VERIFIED / POSTED_GITHUB_API_VERIFIED / MANUAL_UI_VERIFIED

## Deferred Items

- (list any deferred items added or resolved in this WP)

## Next WP Pointer

- Suggested next WP:
- Suggested next WP notes:

## Ready for Review

- Ready for review: YES/NO
```

## Evidence Distinction

| Evidence type | Token | When applicable |
|---|---|---|
| Local draft only — guard ran on files not yet posted | `LOCAL_DRAFT_VERIFIED` | Default for new WPs before posting |
| Posted GitHub PR body/comment confirmed via API | `POSTED_GITHUB_API_VERIFIED` | After public verifier exits 0 |
| Posted GitHub PR body/comment confirmed via manual UI | `MANUAL_UI_VERIFIED` | Private repo; API unavailable |
| Not verified | `NOT_VERIFIED` | Blocked; must be explained |

**Local drafts do not count as posted GitHub evidence.**

When a WP claims a posted GitHub PR body or posted final evidence comment is verified, the actor must re-fetch that posted GitHub state after posting. Writing and checking a draft locally — even if identical to what will be posted — is `LOCAL_DRAFT_VERIFIED`, not `POSTED_GITHUB_API_VERIFIED`.

A `Ready for review: YES` with `LOCAL_DRAFT_VERIFIED` is only allowed when the WP package class explicitly permits it (e.g., docs-only WPs that use `PRIVATE_REPO_MANUAL_VERIFIED` with manual UI verification).

## Transition Policy (WP86–WP90)

During transition (WP86 through WP90), both committed status entries and final GitHub PR comments are required.

After WP90, a later WP may explicitly decide to keep, simplify, or replace the final GitHub comment requirement. That decision must appear in repo truth.

The committed status entry is the preferred evidence surface going forward because it:
- Cannot be accidentally superseded by a later GitHub comment.
- Is part of the merged branch history.
- Travels with the code change.
- Removes the failure-prone reliance on a reviewer finding "the latest" comment.

## Relationship to Other Evidence Docs

- `docs/ai/codex/WP_EXECUTION_REPORT.md` — mandatory PR final report comment format.
- `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` — exact validation command requirements.
- `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md` — local guard tool.
- `docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md` — posted verifier tool.
- `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` — evidence mode definitions.
- `docs/ai/codex/WP_DRAFTING_STANDARD.md` — evidence model section.
