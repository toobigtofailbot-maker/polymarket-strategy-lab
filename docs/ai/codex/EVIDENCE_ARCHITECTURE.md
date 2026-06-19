# Evidence Architecture — Model D

## Status

- Evidence architecture version: MODEL_D
- Introduced in: WP88
- Applies to: all WPs from WP88 onward
- Supersedes: prior three-surface evidence model that allowed PR body, status fragment, and final comment to drift

## Purpose

Define exactly which evidence surface is authoritative for what, so that no two surfaces can ever contradict each other and claim "Ready for review: YES" simultaneously.

## 1. Why This Document Exists

WP87 exposed a class of failure where:

- "full result scan" did not mechanically prove every public field was scanned;
- a manual serializer silently omitted an advisory field;
- the evidence surfaces (PR body, status fragment, final comment) were allowed to drift;
- a status fragment recorded a "current live PR head" SHA that became stale the next commit;
- `NOT_VERIFIED` and `Ready for review: YES` appeared together without blocking merge.

Model D closes those gaps by assigning one unambiguous role to each evidence surface.

## 2. Evidence Source Hierarchy

From highest to lowest authority:

1. **GitHub PR metadata** — source of truth for the current live PR head SHA.
2. **PR body** — source of truth for current review evidence (validation, guards, changed files, traceability).
3. **Status fragment** (`docs/status_entries/WP<NN>.md`) — stable historical/repo record; not a live-head tracker.
4. **Final GitHub comment** — optional reviewer clarification after WP91; was transition-only pointer during WP86–WP90.
5. **Local drafts** — never treated as posted evidence.

No surface below may claim authority that belongs to a higher surface.

## 3. PR Body — Current Review Evidence Surface

The PR body is the current review evidence surface. It may contain:

- current live PR head (from GitHub metadata)
- current base SHA
- changed-file count
- validation summary
- guard summary
- security summary
- current Ready for review status
- current posted/re-fetch state
- requirement-to-evidence traceability table
- scope/boundary summary
- compatibility/impossibility table
- evidence mode declaration

The PR body must not contain stale embedded final-evidence blocks that duplicate the final comment verbatim and can drift.

The PR body is the **only** repo-visible surface allowed to claim the current live PR head as a **current review fact**.

## 4. Status Fragment — Stable Repo Record

The status fragment (`docs/status_entries/WP<NN>.md`) is a committed, stable historical record. It travels with the branch and cannot be accidentally superseded by a later comment.

### 4.1 What status fragments may contain

- WP ID
- PR number
- branch
- base commit
- validated implementation commit (labeled exactly `Validated implementation commit:`)
- merge commit (to be filled after merge)
- scope and authority posture
- changed files
- validation summary
- guard summary
- security summary
- boundary statement
- deferred items
- next WP pointer
- evidence policy note

### 4.2 What status fragments must not contain

Status fragments must never contain:

- the current live PR head as a fixed SHA (this becomes stale after the next commit)
- `Head commit:` labeling a currently-in-review PR head
- `NOT_VERIFIED` combined with `Ready for review: YES`
- claims that local draft verification equals posted GitHub verification
- a duplicate full final-comment evidence table that can drift

### 4.3 Required wording for live PR head

Every status fragment must include exactly this wording (or its equivalent):

```
Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable
and non-self-referential; it does not attempt to encode the SHA of the commit containing itself.
```

### 4.4 Validated implementation commit labeling

If a specific implementation commit was validated (distinct from the current head), label it:

```
Validated implementation commit: <SHA>
```

Never label a currently-in-review head as `Head commit:`. That label is reserved for historical merge records.

## 5. Final GitHub Comment — Optional Reviewer Clarification (After WP91)

**After WP91:** Final GitHub evidence comments are **optional**. They are not required for merge readiness.

A final comment may be posted voluntarily for reviewer clarity. If posted, it must:

- not claim canonical evidence authority
- not contradict the PR body
- not claim to supersede the PR body as the current review evidence surface
- not encode a current live PR head as a fixed SHA that will become stale

If a final comment is voluntarily posted, it should say:

> This comment is optional and non-canonical; the PR body is the current review evidence surface.

**Historical context (WP86–WP90 transition):** During the WP86–WP90 transition, final GitHub comments were required as short transition markers containing the `CURRENT FINAL WP EVIDENCE` marker, current live PR head re-fetched after posting, validation summary mirrored from PR body, and posted evidence self-check. That transition ended with WP90. WP91 retires the mandatory final-comment requirement.

## 6. Evidence Contradiction Matrix

The following combinations are **invalid** and must block merge:

| Invalid combination | Required outcome |
|---|---|
| `Posted evidence self-check: NOT_VERIFIED` + `Ready for review: YES` | Block merge |
| `PR body and latest final evidence comment compared after posting: NO` + `Ready for review: YES` (if a final comment was posted) | Block merge |
| `LOCAL_DRAFT_VERIFIED` treated as posted GitHub verification | Block merge |
| status fragment claims current live PR head as fixed SHA | Block merge |
| status fragment uses `Head commit:` for the currently-in-review PR head | Block merge |
| PR body and final comment report different current live PR head SHAs (if a final comment was posted) | Block merge |
| final comment claims canonical evidence authority after WP91 | Block merge |
| optional final comment contradicts PR body | Block merge |
| multiple final evidence comments without latest authoritative marker (if final comments were posted through WP90) | Block merge |
| status fragment and PR body disagree on validation summary | Block merge or update status fragment before Ready |
| Ready status appears in multiple surfaces with contradictory values | Block merge |
| No final GitHub evidence comment exists after WP91 | **Not invalid** — absence of final comment is not a merge blocker after WP91 |

The following are **valid** combinations after WP91:

| Valid combination | Meaning |
|---|---|
| PR body current + status fragment stable/non-self-referential + no final comment | Fully valid; may merge (after WP91) |
| `POSTED_GITHUB_API_VERIFIED` + `compared after posting: YES` + `Ready for review: YES` | Fully verified; may merge |
| `MANUAL_UI_VERIFIED` + allowed-by-policy note + `Ready for review: YES` | Manual verification accepted; may merge |
| `NOT_VERIFIED` + `Ready for review: NO` | Not ready; correction required |
| optional final comment posted, explicitly non-canonical, does not contradict PR body | Allowed; comment is non-canonical |

No intermediate state (e.g., `LOCAL_DRAFT_VERIFIED` + `Ready for review: YES`) is valid unless the active WP's package class explicitly permits it and the evidence mode is declared.

## 7. Transition Policy

**After WP91 (current policy):**

The WP86–WP90 transition ended with WP91. Final GitHub evidence comments are retired as a mandatory evidence surface.

Current policy:

- PR body is the current review evidence surface.
- Status fragment is the stable non-self-referential repo record.
- Final GitHub comments are optional reviewer clarifications only; they are not required for merge readiness and are not canonical evidence.
- A PR must not be blocked from merge solely because no final evidence comment exists.
- If a final comment is voluntarily posted, it must not contradict the PR body or claim canonical evidence authority.

**Historical context (WP86–WP90 transition):**

During the WP86–WP90 transition, both committed status entries and final GitHub PR comments were required. The committed status entry was the preferred evidence surface. The final GitHub comment was required as a posted verification pointer. WP91 explicitly removed the final comment requirement and documented that decision in repo truth.

## 8. Cross-References

- `docs/status_entries/README.md` — format and convention for per-WP status entries
- `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` — evidence reporting rules
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md` — reviewer checks including contradiction matrix
- `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` — evidence mode definitions
- `docs/ai/codex/RESULT_OUTPUT_INVARIANT_STANDARD.md` — field-coverage and serializer standards for result objects
- `docs/ai/codex/FOLLOWUP_PROMPT_STANDARD.md` — root-cause-first follow-up prompt standard
