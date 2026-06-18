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
4. **Final GitHub comment** — transition-only posted verification pointer during the WP86–WP90 transition.
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

## 5. Final GitHub Comment — Transition-Only Verification Pointer

During the WP86–WP90 transition, final GitHub comments remain required. After WP90, a later WP may remove or simplify this requirement; that decision must appear in repo truth.

Until that decision is made, final comments must be **short transition markers**. They may contain:

- the `CURRENT FINAL WP EVIDENCE` marker
- PR number
- current live PR head re-fetched after posting
- statement that PR body is the current review surface
- statement that status fragment is stable/non-self-referential
- validation summary mirrored from PR body
- posted evidence self-check (`POSTED_GITHUB_API_VERIFIED` or `MANUAL_UI_VERIFIED`)
- PR body / final comment comparison result
- status fragment / PR body comparison result
- evidence contradiction matrix result
- Ready for review

Final comments must not contain:

- large duplicate evidence tables that can drift from the PR body
- separate changed-file inventories that can drift
- separate requirement-to-evidence tables that can drift
- a current live head that was not re-fetched after posting
- `NOT_VERIFIED` combined with `Ready for review: YES`

## 6. Evidence Contradiction Matrix

The following combinations are **invalid** and must block merge:

| Invalid combination | Required outcome |
|---|---|
| `Posted evidence self-check: NOT_VERIFIED` + `Ready for review: YES` | Block merge |
| `PR body and latest final evidence comment compared after posting: NO` + `Ready for review: YES` | Block merge |
| `LOCAL_DRAFT_VERIFIED` treated as posted GitHub verification | Block merge |
| status fragment claims current live PR head as fixed SHA | Block merge |
| status fragment uses `Head commit:` for the currently-in-review PR head | Block merge |
| PR body and final comment report different current live PR head SHAs | Block merge |
| final comment claims verification without post-posting re-fetch | Block merge |
| multiple final evidence comments without latest authoritative marker | Block merge |
| status fragment and PR body disagree on validation summary | Block merge or update status fragment before Ready |
| Ready status appears in multiple surfaces with contradictory values | Block merge |

The following are **valid** combinations:

| Valid combination | Meaning |
|---|---|
| `POSTED_GITHUB_API_VERIFIED` + `compared after posting: YES` + `Ready for review: YES` | Fully verified; may merge |
| `MANUAL_UI_VERIFIED` + allowed-by-policy note + `Ready for review: YES` | Manual verification accepted; may merge |
| `NOT_VERIFIED` + `Ready for review: NO` | Not ready; correction required |

No intermediate state (e.g., `LOCAL_DRAFT_VERIFIED` + `Ready for review: YES`) is valid unless the active WP's package class explicitly permits it and the evidence mode is declared.

## 7. Transition Policy

During WP86–WP90 transition:

- Both committed status entries and final GitHub PR comments are required.
- The committed status entry is the preferred evidence surface (cannot be superseded by a later comment).
- The final GitHub comment remains required as a posted verification pointer.
- After WP90, a later WP may explicitly remove or simplify the final comment requirement; that decision must appear in repo truth.

## 8. Cross-References

- `docs/status_entries/README.md` — format and convention for per-WP status entries
- `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` — evidence reporting rules
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md` — reviewer checks including contradiction matrix
- `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` — evidence mode definitions
- `docs/ai/codex/RESULT_OUTPUT_INVARIANT_STANDARD.md` — field-coverage and serializer standards for result objects
- `docs/ai/codex/FOLLOWUP_PROMPT_STANDARD.md` — root-cause-first follow-up prompt standard
