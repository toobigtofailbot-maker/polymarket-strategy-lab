# Repo-Truth Policy Guard

## Purpose

This guard document defines the mechanical repo-truth policy guard and one-shot readiness gate
that ensures active policy docs stay aligned with the post-WP91 optional-final-comment model.
It prevents regression of retired old-policy wording into active current policy.

After WP91 retired mandatory final GitHub evidence comments, this guard:
1. Defines the active canonical policy-doc set (docs that are live and enforced).
2. Defines the old-policy phrase sweep list (phrases that cannot appear as active current policy).
3. Defines classification labels for phrase hits.
4. Defines the one-shot readiness gate for product and policy WPs.
5. Defines status-fragment consistency rules.

Added in WP92.

---

## Active Canonical Policy-Doc Set

The following files are active policy docs — they must reflect post-WP91 optional-final-comment
policy and are scanned by the old-policy phrase sweep:

```
# Core codex docs (original WP92 set)
docs/ai/codex/EVIDENCE_ARCHITECTURE.md
docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md
docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md
docs/ai/codex/PR_REVIEW_CHECKLIST.md
docs/ai/codex/VALIDATION_MATRIX.md
docs/ai/codex/WP_DRAFTING_STANDARD.md
docs/ai/codex/FOLLOWUP_PROMPT_STANDARD.md
docs/ai/codex/RESULT_OUTPUT_INVARIANT_STANDARD.md
docs/work_package_template.md
docs/status_entries/README.md
.github/pull_request_template.md

# Top-level agent startup/rulebook docs (added WP92 follow-up)
AGENTS.md
CLAUDE_START_HERE.md
CODEX_START_HERE.md
AI_CODING_AGENT_START_HERE.md

# Execution and evidence helper/design docs (added WP92 follow-up)
docs/ai/codex/WP_EXECUTION_REPORT.md
docs/ai/codex/CONCISE_REPORTING_RULES.md
docs/ai/codex/POSTED_PR_EVIDENCE_REVIEW_HARDENING.md
docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md
docs/ai/codex/WP_BUNDLING_POLICY.md
docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md
docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md
docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER.md
docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md
docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md
docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md
```

Historical status fragments are NOT active policy docs:

```
docs/status_entries/WP*.md
```

Historical status fragments may contain wording from the WP that created them. They do not set
active policy. The phrase sweep does not scan historical status fragments.

---

## Old-Policy Phrase Sweep

The following phrases must NOT appear as active post-WP91 policy in active canonical policy docs.

Required search phrases:

```
CURRENT FINAL WP EVIDENCE
--final-comment
require-current-final-marker
final comment required
final evidence comment required
current final evidence comment required
Ready only after final evidence
Ready for review only after final evidence
mark Ready for review only after final evidence passes
final comment will be posted after merge
PR body and final comment drafts
latest final comment must exist
final comment starts with CURRENT FINAL WP EVIDENCE
final evidence comment is mandatory
```

These phrases are **allowed only** when a classification label appears in one of these
context scopes relative to the phrase hit:

1. **Same line or ±5 lines**: the phrase hit line or nearby lines contain an allowed classifier.
2. **Nearest section header** (nearest `##` heading above the hit): the section heading text
   contains an allowed classifier such as "Historical WP47–WP90" or "optional final comments".
3. **Document-level preamble** (first 25 lines of the file): the file has a document-level
   "After WP91" or "Historical" disclaimer near the top that scopes the whole document.

Allowed classifier tokens (checked case-insensitively):

```
historical wp
wp86-wp90 only
wp86–wp90 only
after wp91
not required
optional
omit
if no final comment
if skipping
HISTORICAL_WP86_WP90_ONLY
REWRITTEN_TO_POST_WP91_POLICY
REMOVED
OPTIONAL_NON_CANONICAL_COMMENT
not posted
not mandatory
is not required
non-canonical
not a merge blocker
```

They are **not allowed** in:
- Active instructions without a classifier in any of the three context scopes above
- Current gates or templates outside clearly labeled historical sections
- Current required report-back sections without qualification

---

## Phrase-Hit Classifications

When an old-policy phrase is found in a repo-truth file, it must be classified as one of:

| Classification | Meaning |
|---|---|
| `ACTIVE_POST_WP91_POLICY` | **Forbidden** — phrase is presented as active current policy after WP91 |
| `HISTORICAL_WP86_WP90_ONLY` | **Allowed** — phrase is clearly labeled as historical WP86–WP90 only |
| `REMOVED` | Phrase has been deleted from the file |
| `REWRITTEN_TO_POST_WP91_POLICY` | Phrase rewritten to reflect optional/non-canonical post-WP91 model |
| `OPTIONAL_NON_CANONICAL_COMMENT` | Phrase refers to an optional/non-canonical final comment (allowed) |

No unclassified hit is allowed in active policy docs. Every occurrence of a sweep phrase
must carry a classification that explains why it is present.

---

## Product WP One-Shot Readiness Gate

Required for product/report/export/loader/validator WPs before `Ready for review: YES`:

```
One-Shot Readiness Gate:
- repo-truth phrase sweep: PASS
- PR body/status fragment contradiction matrix: PASS
- status fragment stable/non-self-referential: PASS
- result-object field coverage: PASS / NOT_APPLICABLE
- serializer losslessness: PASS / NOT_APPLICABLE
- full public output scan: PASS / NOT_APPLICABLE
- invalid-output no-echo: PASS / NOT_APPLICABLE
- validation tier complete: PASS
- guards: PASS
```

---

## Policy WP One-Shot Readiness Gate

Required for workflow/policy/template/review docs WPs before `Ready for review: YES`:

```
One-Shot Readiness Gate:
- canonical-doc set reviewed: PASS
- repo-truth phrase sweep: PASS
- old-policy phrase hits classified: PASS
- templates aligned: PASS
- PR review checklist aligned: PASS
- validation matrix aligned: PASS
- status-fragment guidance aligned: PASS
- workflow docs tests updated: PASS
- contradiction matrix updated if policy changes: PASS
- no product/source/tool/dependency changes: PASS
```

---

## Final Comment Policy After WP91

After WP91, the active final comment policy is:

```
Final GitHub evidence comments are optional and non-canonical.
Absence of a final GitHub evidence comment is not a merge blocker.
The PR body is the current review evidence surface.
The status fragment is the stable non-self-referential repo record.
An optional final comment may not override or contradict the PR body.
```

See `docs/ai/codex/FINAL_COMMENT_POLICY.md` for the canonical final comment policy document.

---

## Status-Fragment Consistency Rules

Future status fragments must satisfy all of the following before `Ready for review: YES`:

```
- stable/non-self-referential wording present
- no "Head commit:" used for current in-review SHA
- no fixed current live PR head SHA
- no evidence guard pending while Ready for review is YES
- no LOCAL_DRAFT_VERIFIED as final active evidence source while Ready for review is YES
- Ready for review state agrees with PR body
- validation summary agrees with PR body or is explicitly stable historical record
```

Required stable wording for every status fragment:

```
Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable
and non-self-referential; it does not attempt to encode the SHA of the commit containing itself.
```

If a specific implementation commit is recorded, label it exactly:

```
Validated implementation commit: <SHA>
```

The label `Head commit:` is reserved for post-merge historical records only.

---

## Result-Object / Output Gate Reminders

For WPs that introduce or return public result objects (dataclasses, TypedDicts,
dict-returning functions):

- All public fields enumerated and classified (scanned / exempt / forbidden).
- Test proves `{f.name for f in fields(ResultType)} <= set(serialized)` or equivalent
  recursive scan.
- Invalid result objects scanned, not only valid result objects.
- Manual serializers prohibited unless a field-coverage test proves losslessness.
- Recursive forbidden-terms scan covers the entire result object, not only the `errors` field.

---

## Required PR-Body Evidence Format

Every WP PR body must include:

```
WP identity
Previous PR merge verification
Current live PR head: see GitHub PR metadata and PR body (not a fixed SHA)
Package class
Authority posture
Changed files
Active canonical policy-doc set reviewed (for policy WPs)
Old-policy phrase sweep result (for policy WPs)
One-Shot Readiness Gate result
Test/guard summary
Requirement-to-evidence table (M/L/XL WPs)
Ready for review: YES/NO
```

---

## Cross-References

- `AGENTS.md` — top-level agent startup and posted evidence verification rules
- `CLAUDE_START_HERE.md` — Claude Code startup guidance
- `CODEX_START_HERE.md` — Codex startup guidance
- `AI_CODING_AGENT_START_HERE.md` — AI coding agent startup guidance
- `docs/ai/codex/EVIDENCE_ARCHITECTURE.md` — Model D evidence architecture (WP88+)
- `docs/ai/codex/FINAL_COMMENT_POLICY.md` — canonical final comment policy (WP91)
- `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` — PR evidence reporting discipline
- `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md` — local guard tool
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md` — reviewer checks including phrase sweep
- `docs/ai/codex/VALIDATION_MATRIX.md` — package-class validation requirements
- `docs/ai/codex/WP_DRAFTING_STANDARD.md` — WP drafting standard
- `docs/ai/codex/WP_EXECUTION_REPORT.md` — execution report format
- `docs/ai/codex/POSTED_PR_EVIDENCE_REVIEW_HARDENING.md` — posted evidence review hardening
- `docs/ai/codex/WP_BUNDLING_POLICY.md` — WP bundling policy
- `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` — WP execution state machine
- `docs/work_package_template.md` — WP template with one-shot gate
- `docs/status_entries/README.md` — status fragment format and rules
- `.github/pull_request_template.md` — PR template with one-shot gate
- `tests/test_codex_workflow_docs.py` — mechanical enforcement tests
