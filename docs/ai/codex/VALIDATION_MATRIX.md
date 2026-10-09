# Validation Matrix

## Package Classes By Risk Level

Package classes are grouped by risk level. Each class defines its minimum validation surface. Higher risk classes require stronger gates.

## Pre-Implementation Package Readiness Gate (WP168G; routed by WP171G)

This gate is separate from the optional, non-canonical final comment; mandatory final
GitHub evidence comments were retired after WP91.

After WP171G, every implementation WP must pass the one-command pre-implementation
package-readiness gate **before** the user grants the `AUTHORIZED` transition. The
prompt declares a track and one canonical machine-readable authority mirror. The gate
first requires the mirror's risk level and all sixteen authority booleans to equal the
spec, then independently derives the minimum from those equal values:

```
python tools/wp/wp_readiness_gate.py \
  --wp docs/wp_specs/<WP>/wp_prompt.txt \
  --spec docs/wp_specs/<WP>/wp_spec.json \
  --repo-root .
```

Add `--certificate docs/wp_specs/<WP>/draftability_certificate.json` for PROTECTED
or when checking an existing historical certified package. FAST/RUNTIME do not require
an independent pre-implementation certificate.

The gate must exit `0` with `IMPLEMENTATION_READY` before authorization. It is a
deterministic, local/offline, read-only check that reuses `tools/wp/wp_spec_guard.py`
for certificate/package validation only when a certificate is supplied, and adds
authority-mirror equality, prompt-structure validation, a structured semantic-contradiction sweep,
evidence-plan coherence, exact-scope authority, and a successor-boundary check.
`IMPLEMENTATION_READY` is technical package readiness only; it is **not authorization**
and never grants `AUTHORIZED`. At the final implementation head the gate is re-run in
`--check-diff` mode so actual changed paths equal the exact machine-spec scope and every
planned pytest evidence node exists with a bounded reachable assertion. The gate did not
exist on WP168G's base, so WP168G itself used the existing draftability bootstrap and
self-hosts the gate as final `--check-diff` evidence.

New governed prompts must contain exactly one bounded
`BEGIN_GOVERNANCE_AUTHORITY_V1` block in the canonical order. Missing, duplicate,
malformed, reordered, or prompt/spec-mismatching blocks fail closed. Prompt prose
cannot broaden authority beyond the mirror. Historical certified packages before
WP171G remain compatible without retrofitting it. Certificate-free FAST/RUNTIME
results report `package_guard_passed: null` and a deterministic readiness basis.

### Full-changed-set scope-guard discovery (WP168G)

Before scope freeze / implementation authorization for a file-changing WP, the
package-readiness process MUST perform a bounded discovery of repository guards whose logic
evaluates the COMPLETE changed-file set (for example `git diff --name-only origin/main` plus
untracked files compared by exact-set equality to a hard-coded authorized set) and MUST prove
that the governed scope contains every required compatibility edit for those guards. This
requirement is bounded: it covers mechanically discoverable current repository patterns plus
mandatory full-suite validation at the exact final head. It does NOT claim to mathematically
prove every possible future test dependency; the full repository suite at the exact final head
remains the backstop. Guards that evaluate the complete changed-file set should derive the
active WP's authorized set from its machine spec so a newly-added WP is authorized by its own
governed exact scope rather than rejected merely for being new.

## Governance-Track Validation

| Track | While editing | Stable candidate | Independent review |
|---|---|---|---|
| FAST | Focused tests, affected adjacent tests, cheap static/import/type checks | Readiness `--check-diff`, actual-surface security, exact-head hosted CI, one authoritative broad/full suite locally or by equivalent exact-head hosted CI | Final Side PR review mandatory; no internal final LLM reviewer unless the WP requests one |
| RUNTIME | Focused and directly affected integration tests, runtime/network boundary tests, relevant security/dependency checks | Readiness `--check-diff`, one authoritative full suite locally or by equivalent exact-head hosted CI, exact-head hosted CI | One combined independent implementation reviewer plus final Side PR review |
| PROTECTED | Protected-boundary tests and full applicable security/credential checks | Readiness `--check-diff`, full suite, exact-head hosted CI | Independent pre-implementation certificate, required final independent review, and final Side PR review |

PROTECTED is the minimum for Risk 4 or credential/execution/live authority. RUNTIME is
the minimum for non-PROTECTED Risk 3 or network/scheduler/Hermes-runtime/paper authority.
FAST is the remaining Risk 0–2 case. A stricter voluntary track is allowed; a weaker
track is rejected. No track may convert a failed required check into Ready YES.
Repeated broad validation is avoided while a candidate is changing; this does not waive
the one authoritative stable-candidate result.

### Risk Level 0 — Docs / Workflow Only (Lowest Risk)

| Package class | Focused tests | Adjacent tests | Broad/full suite | Diff scope | Artifact guard | Security | GitHub evidence re-fetch | Status fragment |
|---|---|---|---|---|---|---|---|---|
| docs-only policy WP | Doc content tests | Repo truth index | Per track | Required | Required | Report unavailable | Required if posting claimed | Required (WP86+) |
| schema-only WP | Schema doc tests | Repo truth index | Per track | Required | Required | Report unavailable | Required if posting claimed | Required (WP86+) |
| workflow-docs-tests-only WP | Workflow/template tests | Project status / arch boundary | Per track | Required | Required | Report unavailable | Required if posting claimed | Required (WP86+) |
| workflow/governance WP | Workflow docs/template tests, focused docs tests, exact PR evidence reporting check | Project status wording check, network usage wording check | Per track | Required | Required | Report unavailable | Required if posting claimed | Required (WP86+) |
| docs-tests-workflow-governance-hardening | All workflow/governance WP checks | Bundle risk class, follow-up classification | Per track | Required | Required | Report unavailable | Required if posting claimed | Required (WP86+) |
| workflow-governance-docs-tests-state-machine | All workflow/governance WP checks, state machine doc present | Evidence mode declared | Per track | Required | Required | Report unavailable | Required if posting claimed | Required (WP86+) |

All Risk Level 0 WPs must also confirm:
- Package size class stated.
- No `src/`, `tools/` (unless explicitly scoped), dependency, or lock-file changes.
- Exact PR evidence reporting discipline.
- Network usage wording accurate.
- Current-final evidence marker in final comment (only if a final comment is voluntarily posted; optional after WP91).
- Guard input source stated in PR body.
- Evidence mode declared (PUBLIC_VERIFIER_PASS / PRIVATE_REPO_MANUAL_VERIFIED / BLOCKED_NOT_READY).

### Risk Level 1 — Local/Offline Source (Low Risk)

| Package class | Focused tests | Adjacent tests | Broad/full suite | Diff scope | Artifact guard | Security | GitHub evidence re-fetch | Status fragment |
|---|---|---|---|---|---|---|---|---|
| validator WP | Focused validator tests, negative-test matrix | Adjacent schema tests, architecture boundary | Per track | Required | Required | gitleaks if available | Required if posting claimed | Required (WP86+) |
| report/output WP | Focused report tests, advisory output safety | Adjacent schema and boundary tests | Per track | Required | Required | gitleaks if available | Required if posting claimed | Required (WP86+) |
| local/offline source WP | Focused unit tests, negative-test matrix | Architecture boundary | Per track | Required | Required | gitleaks if available | Required if posting claimed | Required (WP86+) |
| local report/export WP | Offline tests with local fixtures | No credential/network tests | Per track | Required | Required | gitleaks if available | Required if posting claimed | Required (WP86+) |
| github-aware-readonly-workflow-helper WP | Focused helper tests with fake responses | Docs workflow tests | Per track | Required | Required | gitleaks if available | Required — posted verifier after PR posted | Required (WP86+) |
| local-offline-stdlib-governance-helper-hardening | WP-spec guard focused tests; scope-helper compatibility and exact-mode tests; negative-test matrix | Workflow-doc tests; project-status and repo-truth checks | Per track | Exact scope required | Required | Honest availability; gitleaks if available | Required — authenticated live re-fetch | Required (WP86+) |

All Risk Level 1 WPs must also confirm:
- Output under ignored `local_data/` only (for report/export WPs).
- No credentials, no private endpoints, no account queries.
- Negative-test matrix present when adding validators, scorers, parsers, or filters.
- Advisory output safety helper used for output WPs if available.
- Recursive forbidden-terms scan for output surfaces.

### Risk Level 2 — Data Ingestion / External Data (Medium Risk)

| Package class | Focused tests | Adjacent tests | Broad/full suite | Diff scope | Artifact guard | Security | GitHub evidence re-fetch | Status fragment |
|---|---|---|---|---|---|---|---|---|
| read-only public-data WP | Offline tests; explicit-network smoke only if scoped | Boundary/scope tests | Per track | Required | Required | gitleaks + pip-audit if available | Required | Required (WP86+) |
| official-client sandbox WP | Isolated sandbox tests, no `src/` import | No runtime/auth tests | Per track | Required | Required | gitleaks + pip-audit | Required | Required (WP86+) |
| security/tooling WP | Tool availability checks, generated-artifact controls | Honest unavailable reporting | Per track | Required | Required | All available tools | Required | Required (WP86+) |

### Risk Level 3 — Paper / Scheduler / Bot Loop (High Risk — Blocked Until Authorized)

| Package class | Minimum validation |
|---|---|
| future paper-trading package | Blocked until explicitly authorized; must prove mode separation, no live fallback, deterministic simulation boundaries. All Level 1+2 gates plus paper-mode boundary proof. |
| data ingestion WP | Blocked unless explicitly authorized; stronger rate-limit, credential, and network-boundary gates required. |
| runtime dependency WP | Blocked unless explicitly authorized by repo truth and active WP; dependency audit required; stronger security and dependency-audit gates required. |
| scheduler/bot loop WP | Blocked until explicitly authorized with kill switch, rate-limit evidence, and observability plan. |

### Risk Level 4 — Credentials / Execution / Live (Highest Risk — Blocked)

| Package class | Minimum validation |
|---|---|
| credential/auth WP | Blocked until `docs/live_trading_authorization.md` updated and credential boundary WP explicitly authorized. |
| execution WP | Blocked; requires separate authorization and risk-engine review. |
| future live-trading package | Blocked until explicitly authorized in repo truth and `docs/live_trading_authorization.md`; strongest safety, security, risk, and review gates required. |

### PR Review Package

| Package class | Validation |
|---|---|
| PR review package | PR metadata, changed files, comments, checks, final report comment, validation evidence, safety boundaries, exact PR evidence reporting discipline, status fragment, and requirement-to-evidence traceability inspected. |

## All Work Packages

- Changed-file scope check.
- Forbidden-path preservation.
- Generated-artifact guard after final commit.
- One authoritative broad/full suite on the stable candidate as required by the
  governance-track table. Under S10-CI-OPT-01 the normal path for every track is a
  local authoritative full suite on the stable candidate followed by exactly one
  final exact-head hosted CI matrix (see "Local-First Validation And Final Hosted CI").
  FAST/RUNTIME may rely on equivalent exact-head hosted CI only when the local
  environment genuinely cannot run the suite and that limitation is reported;
  PROTECTED retains local full-suite plus exact-head hosted CI requirements.
- `docs/project_status.md` current-WP wording check.
- Dependency and lock-file preservation unless explicitly scoped.
- Exact PR evidence reporting discipline: exact full validation commands in PR body (no ellipses, no abbreviated commands, no placeholder text), accurate network usage wording, consistent counts in PR body (and between PR body and optional final comment if posted), and stale counts corrected before Ready for review: YES. After WP91, final comment is optional; PR body is the required evidence surface. See `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`.
- PR evidence consistency guard: run `tools/git/pr_evidence_consistency_guard.py` on exact local drafts intended for posting (or on copied posted GitHub content if evidence was posted before the guard ran). Include WP47 hardening flags where local PR body drafts are available. After WP91, `--final-comment` and `--require-current-final-marker` are omitted if no final comment is posted:
  ```
  python tools/git/pr_evidence_consistency_guard.py --pr-body <FINAL_PR_BODY_TEXT> --expected-head <HEAD_SHA> --required-command "python tools/git/status_snapshot.py --format text --include-deferred --include-helper-inventory --include-next-wp-candidates --include-protected-boundaries" --required-command "python tools/git/diff_scope_summary.py --base main --head HEAD --package-class local-offline-stdlib-governance-helper-hardening --allowed-prefix docs/ --allowed-prefix tests/ --allowed-prefix tools/git/pr_evidence_consistency_guard.py --forbidden-prefix src/" --require-standard-network-wording --require-ready-yes --forbid-inline-test-counts --forbid-placeholder-evidence --require-posted-evidence-note
  ```
  If a final comment is also posted (optional after WP91), add `--final-comment <CURRENT_FINAL_EVIDENCE_COMMENT_TEXT> --require-current-final-marker` to the invocation.
  If the guard fails, Ready for review must be NO. Report exact guard invocation and result in the PR body (and in the optional final comment if posted). See `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`.

## Local-First Validation And Final Hosted CI (S10-CI-OPT-01)

Hosted GitHub Actions CI is final exact-head verification, not the iterative
development test loop. `.github/workflows/ci.yml` therefore runs only on
`pull_request` events of type `opened`, `synchronize`, `reopened` and
`ready_for_review`; every top-level job is skipped while the pull request is a draft
(`github.event.pull_request.draft == false`); there is no push-to-main run, so a
green PR head is not re-run merely because it merged; and same-PR concurrency
(`ci-pr-<number>`, `cancel-in-progress: true`) cancels a stale run when a newer
eligible head appears. This changes hosted run frequency only: the final hosted
matrix keeps the same nine jobs (compat ubuntu-24.04/windows-2022 x py3.12/py3.14,
dependency-audit, ndfd-grib-compat ubuntu-24.04/windows-2022, ndfd-grib-dependency-audit,
cockpit-frontend) with every audit, strict DuckDB mode, focused test and full pytest
step unchanged, and Tier 3 retains every legacy leg.

| Stage | Required behavior |
|---|---|
| While editing | Run focused, adjacent and static checks locally. Batch same-scope corrections before pushing. Do not use hosted CI as the iterative test loop. |
| Stable candidate | Run readiness `--check-diff`, diff/artifact/security hygiene, and one authoritative local broad/full suite. Use the authorized ephemeral network-isolated Linux Docker pattern when workstation native-module policy blocks the suite; run platform-specific local checks where technically practical. |
| PR publication | Create or update one DRAFT PR and keep it draft while source is changing. Only after the local stable-candidate PASS, mark it Ready for review once; that transition launches the one required exact-head hosted plan. |
| After a real hosted test failure | Convert back to draft before iterative repairs where practical, fix and batch locally, rerun local validation, and mark Ready again only when stable. |
| Hosted infrastructure failure on an unchanged head | Rerun only the affected cancelled or failed-to-start job where GitHub supports it; do not rerun already-green jobs. A cancellation before runner/test execution is infrastructure evidence, not a code PASS or FAIL. |
| Exact-head rule | Any source or workflow change after a hosted PASS invalidates that exact-head hosted evidence; fresh exact-head hosted CI is then mandatory before Ready for review: YES. A hosted PASS on an older head never justifies Ready for review: YES for a changed head. |

## github-aware-readonly-workflow-helper WP

Minimum validation:
- Focused helper tests with fake GitHub API responses (no real network in unit tests).
- No auth/token/env-secret reading verified in tests.
- Docs workflow tests.
- Full pytest after final commit.
- Generated artifact guard.
- Diff scope summary.
- Code blast radius.
- PR evidence consistency guard (local).
- Posted PR evidence verifier after PR is posted.

Required guard invocation example (after WP91, omit `--final-comment` and `--require-current-final-marker` if no final comment is posted):
```bash
python tools/git/pr_evidence_consistency_guard.py \
  --pr-body pr_body.txt \
  --expected-head <HEAD_SHA> \
  --require-guard-result \
  --require-posted-evidence-note \
  --forbid-placeholder-evidence \
  --forbid-inline-test-counts \
  --require-standard-network-wording \
  --require-ready-yes
```
If an optional final comment was posted: add `--final-comment final_comment.txt --require-current-final-marker`.

Required posted verifier invocation after PR is posted:
```bash
python tools/git/posted_pr_evidence_verifier.py \
  --repo toobigtofailbot-maker/polymarket-strategy-lab \
  --pr <PR_NUMBER> \
  --expected-head <HEAD_SHA> \
  --require-current-final-marker \
  --require-guard-result \
  --require-ready-yes \
  --require-standard-network-wording \
  --forbid-placeholder-evidence \
  --forbid-inline-test-counts \
  --format text
```

Ready for review: YES requires local guard PASS and one complete evidence mode (see `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md`):
- `PUBLIC_VERIFIER_PASS`: posted verifier exit 0 required.
- `PRIVATE_REPO_MANUAL_VERIFIED`: posted verifier UNAVAILABLE with exit code required; reason required; all manual live verification fields required.
- `BLOCKED_NOT_READY`: Ready for review must be NO.

Evidence mode does not replace validation. Validation proves code/docs state. Evidence mode proves PR reporting state. They are independent assessments.

## Docs, Schema, And Workflow WPs

- Focused doc tests.
- Full pytest.
- No runtime/source changes unless explicitly scoped.

## Validation-Output Summarization

Apply the summarization rules from `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md`:

- Report exact command, exit code (if available), pass/fail, test counts, warning count, and output path for each validation step.
- Include failure snippets when any check fails.
- Do not summarize away failure evidence.
- Do not report unavailable tools as passed.

A future validation-output summary helper (designed in `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md`) may summarize validation results in a compact format. However, all mandatory validation commands remain mandatory regardless of whether the helper is used. The helper summarizes evidence; it does not replace it. Design docs do not authorize implementation until a separate approved implementation WP.

## Read-Only Public-Data WPs

- Offline tests.
- Explicit-network smoke only if scoped.
- Output stays under ignored `local_data/`.
- No credentials, authentication, private endpoints, account queries, or private data.

## Runtime, Dependency, Paper, And Live WPs

These package classes are blocked unless explicitly authorized by repo truth and the active work package. They require stronger security, dependency, safety, and review gates than docs-only or schema-only work.

## Result/Report/Loader/Validator WPs — Field-Coverage Gate (WP88+)

All WPs that introduce or return public result objects (dataclasses, TypedDicts, dict-returning functions) must satisfy the field-coverage gate from `docs/ai/codex/RESULT_OUTPUT_INVARIANT_STANDARD.md`:

- All public fields enumerated and classified (scanned / exempt / forbidden).
- Test: `{f.name for f in fields(ResultType)} <= set(serialized)` or equivalent recursive scan.
- Invalid result objects scanned, not only valid result objects.
- Manual serializers prohibited unless a field-coverage test proves losslessness.
- Recursive forbidden-terms scan covers the entire result object, not only the `errors` field.

## Repo-Truth Policy Guard And One-Shot Gate (WP92+)

All workflow-policy WPs (workflow/governance, docs-only policy, workflow-docs-tests-only) must also confirm:

- Active canonical policy-doc set reviewed for old-policy phrase sweep.
- Repo-truth phrase sweep performed on all active canonical policy docs.
- Any old-policy phrase hit classified as `HISTORICAL_WP86_WP90_ONLY`, `REMOVED`, `REWRITTEN_TO_POST_WP91_POLICY`, or `OPTIONAL_NON_CANONICAL_COMMENT`.
- No phrase hit classified as `ACTIVE_POST_WP91_POLICY`.
- One-Shot Readiness Gate (Policy WP gate) declared and PASS in PR body.
- Workflow docs tests updated to enforce the guard.
- No src/, tools/, dependency, or lock-file changes.

See `docs/ai/codex/REPO_TRUTH_POLICY_GUARD.md` for the active canonical policy-doc set, phrase list, and classification definitions.

## Evidence Architecture Model D (WP88+; updated by WP91)

All WPs from WP88 onward must satisfy Model D from `docs/ai/codex/EVIDENCE_ARCHITECTURE.md`:

- PR body is the current review evidence surface; status fragment is a stable non-self-referential record.
- Status fragment PR identity should use `PR: see GitHub PR metadata and PR body.` for in-review WPs; `PR: TBD` is invalid with Ready YES.
- Status fragment must not record the current live PR head as a fixed SHA.
- Status fragment must use `Validated implementation commit:` (not `Head commit:`) for in-review validated SHAs.
- Final comment is optional and non-canonical after WP91 — not required for merge readiness.
- Evidence contradiction matrix must be checked before `Ready for review: YES`.
- `NOT_VERIFIED` + `Ready for review: YES` is always invalid.
- Absence of a final comment is not a merge blocker after WP91.


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
