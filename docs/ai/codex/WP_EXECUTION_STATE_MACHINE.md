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

`DRAFTABILITY_PASS` is track-specific. For `FAST` and `RUNTIME`, it means the
deterministic prompt/spec/readiness checks pass with no open decisions; it is not
an independent LLM review and must never be described as an independent
certificate. For `PROTECTED`, a separate certificate covers the exact prompt/spec
raw-byte hashes, all twelve lenses, an empty unresolved-decision set, and PASS
implementability simulation. The execution agent cannot create or alter its own
PASS certificate. Any protected prompt/spec semantic edit or exact hash mismatch
stops execution and requires independent recertification.

The state names and human authorization boundary do not change. Readiness never
grants `AUTHORIZED`.

WP159 has one exact, one-time bootstrap waiver for its own low-risk draft-PR
implementation. It is accepted only when the schema guard proves the locked
WP159 repository, primary package class, base, predecessor PR/head/merge,
Risk Level 0/1, zero capital, no runtime/workflow/dependency/network/credential
or trading authority, explicit user authorization, implementation-only
authority, review-ready=false, merge=false, mandatory independent live-PR
review, and the code-bound final WP159 prompt/spec hashes. The waiver does not
equal `DRAFTABILITY_PASS`, cannot authorize readiness or merge, cannot be
rehashed for altered bytes, and is unavailable to every non-WP159 package.

There is no automated `PRE_READY_SEMANTIC_PASS` state in this version. That is
separately gated WP160 scope.

### Governance-track routing (WP171G)

Every new WP prompt states exactly one `Governance track expected: FAST`,
`Governance track expected: RUNTIME`, or `Governance track expected: PROTECTED`
front-matter line and exactly one canonical `BEGIN_GOVERNANCE_AUTHORITY_V1`
block. The block is the prompt's normative machine-readable authority
declaration and contains `risk_level` plus all sixteen spec authority booleans;
prompt prose cannot broaden authority beyond it. Readiness requires exact
prompt/spec equality before independently deriving the minimum track from the
equal machine-readable fields:

- `PROTECTED` for Risk 4 or any credential, execution, or live authority.
- `RUNTIME` when not PROTECTED and Risk 3 or any network, scheduler,
  Hermes-runtime, or paper authority is present.
- `FAST` for the remaining Risk 0–2 packages without those authorities.

A prompt may select a stricter track and may never select a weaker one.
Historical pre-WP171G packages with valid certificates remain accepted as
legacy `PROTECTED`; this compatibility route does not waive their certificate.
They do not require retrofitting the authority mirror. For every new governed
package, a missing, duplicate, malformed, reordered, or mismatching mirror fails
closed before `IMPLEMENTATION_READY`.

### Pre-implementation package-readiness gate (WP168G; routed by WP171G)

After WP168G, applicable implementation WPs run one deterministic, local/offline,
read-only command between `DRAFTABILITY_PASS` and the human `AUTHORIZED` transition:

```
python tools/wp/wp_readiness_gate.py \
  --wp docs/wp_specs/<WP>/wp_prompt.txt \
  --spec docs/wp_specs/<WP>/wp_spec.json \
  --repo-root .
```

Add `--certificate docs/wp_specs/<WP>/draftability_certificate.json` for
`PROTECTED` (mandatory) or an existing historical certified package. The flag
is optional for `FAST` and `RUNTIME`.

The gate validates the strict spec and canonical prompt authority mirror, then
composes the existing `tools/wp/wp_spec_guard.py` certificate/package validation
only when a certificate is required or supplied, with prompt-structure validation,
a structured `NORMATIVE_RULE_MATRIX_V1`
semantic-contradiction sweep, evidence-plan coherence, exact-scope authority, and a
successor-boundary check. Its `IMPLEMENTATION_READY` result is a **non-authority package
gate only**: readiness is not authorization. Passing the gate does not create the
`AUTHORIZED` state and never proves the user authorized implementation — the user remains
the sole source of `AUTHORIZED`. The gate adds no new authority state; the canonical
authorization state chain remains exactly
`LOCAL_DRAFT -> DRAFTABILITY_PASS -> AUTHORIZED -> IMPLEMENTED_LOCAL`.

For certificate-free FAST/RUNTIME packages, the public result reports
`readiness_basis: DETERMINISTIC`, `package_guard_passed: null`, and does not list
`package_guard` among checked sections. Certificate-bearing packages report the
actual package-guard result and hash binding.

**WP168G bootstrap:** the readiness gate does not exist on WP168G's merged base, so
WP168G itself could not require the new gate as a pre-implementation prerequisite. WP168G
was activated through the existing independent 12-lens draftability + `wp_spec_guard`
process and self-hosts the new gate in a final `--check-diff` run as post-implementation
evidence. All later applicable implementation WPs must pass the pre-implementation
readiness gate before the user grants `AUTHORIZED`.

**WP171G transition:** WP171G itself voluntarily uses `PROTECTED` and satisfies
the legacy strict certificate workflow one final time. FAST/RUNTIME routing
applies to successor packages only after WP171G merges.

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

Track-specific correction rule:
- `FAST`/`RUNTIME`: after bounded discovery, same-capability file corrections
  within declared authority and size budget may be applied in one batch, then
  deterministic spec/readiness checks are rerun. No independent recertification
  or user round trip is required.
- `PROTECTED`: semantic package changes retain exact-hash invalidation and require
  a fresh independent certificate before implementation continues.

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

Track minimums:
- `FAST`: focused and affected-adjacent checks while editing; at stable candidate,
  readiness `--check-diff`, actual-surface security, exact-head hosted CI, and one
  authoritative broad/full suite locally or by equivalent exact-head hosted CI.
- `RUNTIME`: focused plus boundary/integration checks while editing; at stable
  candidate, one combined independent implementation review, one authoritative
  full suite locally or by equivalent exact-head hosted CI, and exact-head CI.
- `PROTECTED`: independent pre-implementation certificate, protected-boundary and
  full security/credential checks, full suite, exact-head CI, and required final
  independent review.

All tracks require independent Side PR review. No track can convert a failed
required test, security check, or CI check into Ready for review: YES. Repeated
broad suites on an unstable candidate are avoided, not waived.

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


## Risk-Based Local-First CI (S10-CI-OPT-02)

This successor governs CI selection only. It preserves local-first development,
draft suppression, same-PR cancellation and fresh exact-head evidence. No push-main
rerun, product network, runtime activation, credentials, orders or capital authority
is introduced. The historical S10-CI-OPT-01 fixed matrix above is the default-off
and Tier 3 baseline; selective routing below supersedes its fixed-for-every-PR rule
only after Karl separately verifies required trusted ci-final-gate protection and
explicitly enables CI_RISK_ROUTING_ENABLED. This WP never enables the switch or
changes repository settings. main was observed unprotected, not enforced.

The classifier executes from the verified base commit with complete Git change
provenance, including rename/copy origins and deletions. Missing, unsafe, truncated
or contradictory provenance/specification rejects planning. Head-owned labels,
changed specs, user tier requests and broad governance labels cannot grant a downgrade.
Unknown impact selects Tier 3. A changed CI workflow, classifier, security validator,
dependency/lock/native ABI, protected credential/auth/signing/orders/execution,
hard risk/capital/economic reconciliation or critical live lifecycle requires Tier 3.

| Tier | Required hosted coverage |
|---|---|
| 1 | Positively proven benign docs/metadata or isolated pure stdlib helper: one Ubuntu 24.04/Python 3.12 smoke leg with lightweight governance guards; no native/full suite, audits, Windows, NDFD or frontend |
| 2 | Substantive noncritical public-wallet, Hermes research, Alpha campaigns/budgets/research scheduling, ordinary backend/frontend and noncritical deployment: one Ubuntu/Python 3.12 full compatibility suite plus base audit; frontend only for relevant changes |
| 3 | Four full Ubuntu/Windows x Python 3.12/3.14 compatibility legs, both strict NDFD legs, both Python audits and frontend: nine legacy runner legs |

Prefer Tier 2 when the actual diff is eligible and authoritative local evidence
plus selected hosted checks suffice. RUNTIME/Risk 3 and a research scheduler are
not automatic Tier 3. Specific unverified native/OS compatibility is an escalation
reason. Complementary feasible Windows/WSL2/Docker local evidence remains required
where relevant; all WPs retain one authoritative stable-head local full-suite PASS.

Default absent/false/malformed routing retains all nine legacy legs; initial
CI-OPT-02 bootstrap must run these plus classify and ci-final-gate (eleven rows).
An activated future base without a classifier fails. Canonical plans bind exact
base/head, reason codes, a nonempty OS/Python/smoke matrix and audit/NDFD/frontend
booleans. The unique non-matrix final gate runs even after dependency failures,
recomputes the trusted plan, requires success for every selected job and skipped
for every nonrequired job. Required skipped/failed/cancelled/missing/unknown results,
malformed outputs, head mismatch or inconsistent plan never pass. Aggregate matrix
success is insufficient: inspect actual expanded runner rows and resolved audit
logs on the exact head. The two Python audits preserve only CVE-2026-104851, and
strict DuckDB/native/SDK/NDFD checks and locked frontend npm audit stay intact.

Exact-head changes invalidate previous evidence. Final Side18 review and Karl-only
merge remain separate; neither readiness nor a green CI plan grants activation.
The first five eligible postactivation PRs disclose actual summed raw runner-minutes,
tier and executed legs against the eight-run 36.3-minute baseline, distinguishing
billed minutes. No dashboard, scheduler, policy registry or second workflow is added.
