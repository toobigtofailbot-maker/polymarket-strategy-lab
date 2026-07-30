# WP Execution State Machine

Status: `WORKFLOW_GOVERNANCE_CANONICAL`
Applies to: Claude Code and Codex
Scope: WP execution, evidence mode, review readiness

If another workflow doc conflicts with this state machine, this document wins unless the active WP gives a narrower package-specific instruction.

---

## Canonical Execution Phases

```
0. Receive WP
1. Startup read
2. Repo-truth preflight
2A. Draftability gate and explicit implementation authorization
3. Branch creation
4. Scoped implementation
5. Validation
6. Evidence package construction
7. Local evidence guard
8. GitHub posting
9. Posted/private evidence mode selection
10. Ready-for-review decision
11. Review/merge decision
12. Post-merge reconciliation
```

The authorization state chain is:

```
LOCAL_DRAFT -> DRAFTABILITY_PASS -> AUTHORIZED -> IMPLEMENTED_LOCAL
```

`DRAFTABILITY_PASS` requires a separate certificate covering the exact
prompt/spec raw-byte hashes, all twelve lenses, an empty unresolved-decision
set, and PASS implementability simulation. The execution agent cannot create
or alter its own PASS certificate. Any prompt/spec semantic edit or exact hash
mismatch stops execution and requires recertification.

WP159 has one explicit bootstrap waiver for its own low-risk draft-PR
implementation. It is accepted only when the schema guard proves Risk Level
0/1, zero capital, no runtime/workflow/dependency/network/credential or trading
authority, explicit user authorization, implementation-only authority,
review-ready=false, merge=false, and mandatory independent live-PR review. The
waiver does not equal `DRAFTABILITY_PASS`, cannot authorize readiness or merge,
and is unavailable to higher-risk packages.

There is no automated `PRE_READY_SEMANTIC_PASS` state in this version. That is
separately gated WP160 scope.

---

## Phase 0 — Receive WP

**Input:** WP prompt or instructions.
**Action:** Read WP fully. Identify package class, allowed scope, forbidden scope, hard dependencies.
**Output:** Scope boundary known; stop conditions identified.
**Stop condition:** WP conflicts with protected boundaries; WP requests impossible evidence; WP requires forbidden scope.
**Verifier:** Human; repo truth.

Rules:
- Active WP overrides generic workflow docs only inside its approved scope.
- If the WP conflicts with protected boundaries, stop and report.
- If the WP requests impossible evidence (e.g., requires verifier PASS when repo is private and no authenticated helper exists), stop and ask.

---

## Phase 1 — Startup Read

**Input:** Active WP received.
**Action:** Read all mandatory startup files before any other action.
**Output:** Current repo state known; deferred items known.
**Stop condition:** Any required startup file is missing or contradicts repo state in a way that blocks safe implementation.
**Verifier:** Agent self-check.

Required reads (Claude Code):
- `AGENTS.md`
- `CLAUDE_START_HERE.md`
- `CODEX_START_HERE.md`
- `docs/project_status.md`
- `docs/repo_truth_index.md`
- `docs/deferred_items_log.md`
- `docs/ai/codex/README.md`
- Task-relevant docs only after the above.

---

## Phase 2 — Repo-Truth Preflight

**Input:** Startup reads complete.
**Action:** Verify repo state matches WP hard dependencies.
**Output:** Preflight passed or blocked.
**Stop condition:** Any fact below differs from WP requirement.
**Verifier:** Agent via git commands; preflight tools.

Required checks:
- Latest merged PR and merge commit confirmed present on `main`.
- No open PR exists for the current WP already.
- Local `main` equals `origin/main` (or equivalent remote-sync verification).
- Working tree is clean.
- Generated artifact guard passes.
- Protected boundary check: no forbidden path touched by prior uncommitted work.

---

## Phase 3 — Branch Creation

**Input:** Preflight passed.
**Action:** Create the WP branch from clean `main`.
**Output:** Branch exists; working tree clean on new branch.
**Stop condition:** Preflight not yet passed; main is dirty or stale.
**Verifier:** `git status`; `git log`.

Rules:
- One WP = one branch = one PR.
- Never stack WP branches.
- Never manually merge prior WP branches locally.

---

## Phase 4 — Scoped Implementation

**Input:** Branch created.
**Action:** Implement only what the active WP allows.
**Output:** Changed files within allowed scope only.
**Stop condition:** Any change would touch forbidden scope or protected boundary.
**Verifier:** Agent self-check; diff scope summary.

---

## Phase 5 — Validation

**Input:** Implementation complete.
**Action:** Run all required validation for the package class.
**Output:** Validation results recorded; unavailable tools reported honestly.
**Stop condition:** Required validation cannot run and the WP did not explicitly authorize skipping it.
**Verifier:** pytest; helper tools; agent judgment.

Validation is separated into four concerns:

```
Implementation validation: code/docs state correct.
Docs validation: doc structure, wording, cross-references correct.
Evidence validation: PR body correct (final comment optional after WP91).
Security/tool availability reporting: unavailable tools reported as UNAVAILABLE, not passed.
```

**Critical distinction:**

```
Validation proves repo state.
Evidence mode proves PR reporting state.
They are not the same thing.
```

A WP may have all validation passing while evidence mode is BLOCKED_NOT_READY (e.g., because the PR comment was not yet posted). A WP may have evidence mode PRIVATE_REPO_MANUAL_VERIFIED while all tests pass. These are independent assessments.

---

## Phase 6 — Evidence Package Construction

**Input:** Validation complete.
**Action:** Prepare PR body draft (and optionally current-final evidence comment draft after WP91).
**Output:** Local draft files ready for guard check and posting.
**Stop condition:** Required evidence fields cannot be filled honestly.
**Verifier:** Agent self-check; local guard.

Recommended split:

```
PR body (required):
- Package identity
- Changed files
- Scope/boundary summary
- Validation summary
- Evidence mode summary
- Guard result

Final current-final evidence comment (optional after WP91):
- Full exact validation command evidence
- Local guard result
- Posted verifier / manual verification details
- Evidence mode declaration
- Final Ready decision
```

The PR body is the primary evidence surface after WP91. An optional final comment may carry additional detail. Long duplicate narratives in both surfaces are not required, provided all state-machine required fields are present in the PR body and key facts match.

---

## Phase 7 — Local Evidence Guard

**Input:** Local PR body draft (and optional final comment draft if posting one after WP91).
**Action:** Run `tools/git/pr_evidence_consistency_guard.py` with required flags.
**Output:** Guard PASS or FAIL with categories.
**Stop condition:** Guard fails — fix evidence before proceeding.
**Verifier:** Guard tool exit code.

**Important:**
- The local guard checks local text only.
- It does not prove the GitHub comment was posted.
- It does not fetch or validate live GitHub PR body or comments.
- Local guard PASS is necessary but not sufficient to prove posted GitHub evidence is correct.

If guard fails, Ready for review must be NO. Fix all failures before rerunning.

---

## Phase 8 — GitHub Posting

**Input:** Local guard passed.
**Action:** Post or update PR body on GitHub; optionally post current-final evidence comment on GitHub (not required after WP91).
**Output:** Live PR body exists on GitHub; optional final comment posted if one was prepared.
**Stop condition:** GitHub is unavailable (proceed to Phase 9 with UNAVAILABLE reporting).
**Verifier:** gh CLI; manual GitHub UI inspection.

---

## Phase 9 — Posted/Private Evidence Mode Selection

**Input:** PR body and evidence comment posted (or posting confirmed impossible).
**Action:** Select exactly one evidence mode and document it completely.
**Output:** Evidence mode declared; all required fields present.
**Stop condition:** Required fields for the selected mode cannot be completed honestly.
**Verifier:** Manual or automated check against this state machine's mode definitions.

Select exactly one mode:

```
PUBLIC_VERIFIER_PASS
PRIVATE_REPO_MANUAL_VERIFIED
BLOCKED_NOT_READY
```

### Mode A — PUBLIC_VERIFIER_PASS

Allowed only when the public unauthenticated GitHub API or an approved future verifier can read the live PR body and comments and returns exit 0.

Required fields in PR body (and optional final comment if posted):

```
Evidence mode: PUBLIC_VERIFIER_PASS
Posted GitHub evidence verifier: PASS; exit 0
Verifier command: <exact command>
Verified PR body head SHA: <sha>
Verified latest current-final comment URL: <url>        (not required after WP91 if no final comment posted)
Verified latest current-final comment head SHA: <sha>   (not required after WP91 if no final comment posted)
Ready for review: YES/NO
```

Forbidden under this mode:
- Using this mode if the verifier returns exit 3 (resource not found / private repo).
- Using this mode based only on manual UI inspection.
- Using this mode when the verifier exits with any code other than 0.

**Exit 3 from the public verifier means the repo/PR is not accessible to the unauthenticated API. This is not itself a process defect; it is a signal to use PRIVATE_REPO_MANUAL_VERIFIED instead.**

### Mode B — PRIVATE_REPO_MANUAL_VERIFIED

Allowed when the public unauthenticated GitHub verifier cannot access the PR body/comments (private repo, access denied, rate limit, tool unavailable). This is the expected evidence mode for this repository.

Required fields in PR body (and optional final comment if posted):

```
Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED
Posted GitHub evidence verifier: UNAVAILABLE; exit <code>
Reason: <private repo / unauthenticated API unavailable / rate limit / access denied>
Manual live GitHub verification performed: YES
Manual verification method: <GitHub UI / already-available GitHub connector / approved authenticated environment if separately authorized>
Verified PR body head SHA: <sha>
Verified latest current-final comment URL: <url or UI-visible latest current-final marker if URL unavailable>   (not required after WP91 if no final comment posted)
Verified latest current-final comment head SHA: <sha>                                                            (not required after WP91 if no final comment posted)
Verified latest current-final comment contains: validation results, local guard result, follow-up classification, network wording, Ready for review  (not required after WP91 if no final comment posted)
Ready for review: YES/NO
```

**Clarification:**
Manual live verification means a human or already-available approved environment inspects the live GitHub PR body and latest current-final comment. It does not authorize new authentication code, token handling, API helper modification, credential storage, or automated private-repo verifier implementation.

Rules:
- This is a valid evidence mode for private repos.
- Public verifier unavailable / exit 3 is not itself a process defect when documented under this mode.
- This mode must never be reported as `Posted GitHub evidence verifier: PASS`.
- The defect is false PASS reporting or incomplete manual verification fields — not the fact that the public verifier is unavailable.
- Ready for review: YES is allowed under this mode only when all required manual fields above are complete.

### Mode C — BLOCKED_NOT_READY

Required when:
- Public verifier is unavailable AND manual verification is incomplete.
- PR body or final comment mismatch remains (if a final comment was posted).
- Latest current-final comment cannot be identified (applies only if a final comment was posted; absence of final comment is not a blocker after WP91).
- Current head SHA cannot be confirmed in the PR body.
- Required validation is missing.
- Protected boundary was touched.

Required fields:

```
Evidence mode: BLOCKED_NOT_READY
Ready for review: NO
Blocker: <specific reason>
```

**Ready for review must be NO under this mode. There is no exception.**

---

## Phase 10 — Ready-for-Review Decision

**Input:** Evidence mode selected and documented.
**Action:** Evaluate all gates and set Ready for review.
**Output:** `Ready for review: YES` or `Ready for review: NO`.
**Stop condition:** Any gate below fails.
**Verifier:** Agent self-check against this checklist.

Ready for review: YES is allowed only when all of the following are true:

1. Implementation/docs validation passed, or unavailable checks are honestly reported.
2. Local guard passed.
3. Exactly one evidence mode is declared and complete.
4. Evidence mode is not BLOCKED_NOT_READY.
5. Protected boundaries are clean.
6. Follow-up classification is present and accurate.
7. Deferred items log is updated.
8. Repo-truth docs are updated.
9. No generated artifacts committed.
10. No dependency or lock-file changes (unless explicitly scoped).

If any item is not met, Ready for review: NO.

---

## Phase 11 — Review/Merge Decision

**Input:** Ready for review: YES set; PR posted.
**Action:** Human reviewer inspects PR. Merge or request changes.
**Output:** PR merged or changes requested.
**Stop condition:** Reviewer finds evidence defect, scope violation, or test failure.
**Verifier:** Human reviewer.

---

## Phase 12 — Post-Merge Reconciliation

**Input:** PR merged.
**Action:** Next WP must begin by reconciling the previous WP as merged.
**Output:** `docs/project_status.md` updated; merged WP listed; next WP set as current.
**Stop condition:** None — this is required for every WP.
**Verifier:** Agent self-check; project status tests.

Rules:
- `docs/project_status.md` may be stale immediately after merge.
- Stale status after merge is expected and not itself a defect until the next WP reconciles it.
- The next WP must not assume the previous WP's status is already reconciled.
- Reconciliation must move the merged WP's status from `_ON_BRANCH` to `_MERGED`.

---

## Evidence Mode Summary

| Mode | Verifier result | Manual verification | Ready YES allowed |
|---|---|---|---|
| PUBLIC_VERIFIER_PASS | exit 0 | Not required | Yes, when all fields complete |
| PRIVATE_REPO_MANUAL_VERIFIED | UNAVAILABLE; exit 3 or other | Required; all fields complete | Yes, when all fields complete |
| BLOCKED_NOT_READY | Any | Incomplete or blocked | NO — always |

---

## Cross-References

- `AGENTS.md` — binding Codex and Claude Code operating rules
- `CLAUDE_START_HERE.md` — Claude Code startup and drift prevention
- `CODEX_START_HERE.md` — Codex startup sequence
- `docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md` — posted evidence policy and mode details
- `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` — evidence reporting discipline rules
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md` — reviewer evidence mode checks
- `docs/ai/codex/WP_EXECUTION_REPORT.md` — final report format with evidence mode block
- `docs/ai/codex/VALIDATION_MATRIX.md` — package-class validation requirements
- `tools/git/posted_pr_evidence_verifier.py` — public unauthenticated posted verifier helper
