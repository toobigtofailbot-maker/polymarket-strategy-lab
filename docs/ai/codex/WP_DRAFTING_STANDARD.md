# WP Drafting Standard

## Status

- WP drafting standard status: WORKFLOW_GOVERNANCE_MANDATORY
- Applies to: Codex, Claude Code, and all future AI coding agents
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Introduced: WP86

## Purpose

Every future work package must be drafted to execution-package discipline. This document defines the mandatory sections and quality gates that prevent recurring follow-up loops.

The goal is not to add bureaucracy. The goal is to stop paying for avoidable follow-up loops by making every WP self-verifying before the reviewer sees it.

## 1. Mandatory WP Front Matter

Every WP prompt must begin with:

```
Package Identity:
  WP ID:
  Title:
  Repository:
  Base branch:
  Suggested branch:
  Package class:
  Package size class:
  Evidence mode expected:
  Runtime impact:
  Product impact:
  Network impact:
  Credential impact:
  Dependency impact:
  Trading impact:

Recommended Claude/Codex Mode:
  Model/reasoning:
  Reason:
  Escalate to higher reasoning or STOP if:
```

## 2. Authority / Non-Authority Posture

Every WP must include an authority posture section. This section must enumerate exactly what is and is not authorized.

Required authority fields:

```
Implementation authority:
Report/export authority:
Paper authority:
Execution authority:
Live authority:
Credential authority:
Runtime/scheduler authority:
Canonical evidence authority:
Network authority:
Dependency-change authority:
```

The not-authorized list must be explicit. Generic "no live trading" language is insufficient. Name the exact subsystems that are forbidden for this WP.

## 3. Hard Merge Gate

Every WP that depends on a previous WP must include a hard merge gate section with exact commands:

```bash
git fetch origin --prune
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
git log -1 --oneline
git status --short --branch
```

Required checks before proceeding:
1. Required previous PR is merged.
2. Record required previous PR final head SHA.
3. Record required previous PR merge commit.
4. Verify main contains required previous PR final head SHA.
5. Verify no newer conflicting PR merged.
6. Verify no open WP branch for this WP exists locally or remotely.
7. Verify no open PR for this WP exists.
8. Verify target doc does not already claim this WP complete.

If any condition fails, STOP and report.

## 4. Context Budget

Every WP must define a context budget to prevent context overload and scope drift:

```
Read first:          (mandatory startup files — AGENTS.md, project_status.md, etc.)
Read for this WP:    (files directly changed or inspected in this WP)
Read only if blocked: (files to read if a specific blocker arises)
Do not read/touch:   (explicit forbidden file categories)
Search terms:        (fallback search terms if paths have moved)
```

The "do not read/touch" list must explicitly name protected categories: `src/`, `tools/`, dependency files, credentials, etc.

## 5. Compatibility / Impossibility Check

Every nontrivial WP must include a compatibility/impossibility table in the PR body or execution notes:

| Required behavior | Controlling repo mechanism | Files likely needed | Allowed in this WP? | Compatible? | Action |
|---|---|---|---:|---:|---|
| ... | ... | ... | YES/NO | YES/NO | ... |

Mandatory for:
- validator WPs
- report WPs
- schema WPs
- export WPs
- collector WPs
- workflow WPs
- large bundled WPs (L/XL)
- any WP touching evidence policy
- any WP touching advisory output surfaces

If any row shows incompatible or not allowed, STOP or split the WP.

## 6. Concrete Stop Conditions

Every WP must include concrete stop conditions tied to the package risk class, not generic STOP language.

Required format for each stop condition:

```
STOP if <specific condition> — because <specific consequence>.
```

Package-class stop conditions that must be included where applicable:

**For output WPs (validators, reports, exports):**
- STOP if invalid-output no-echo cannot be tested.
- STOP if central advisory output safety helper is unavailable.
- STOP if a validator returns raw invalid input in any output surface.
- STOP if a report copies raw metadata into output.
- STOP if any output surface cannot be recursively scanned for forbidden terms.

**For evidence WPs:**
- STOP if PR body/final evidence cannot be re-fetched after posting where required.
- STOP if posted evidence self-check is not possible.

**For all nontrivial WPs:**
- STOP if changed files exceed allowed scope.
- STOP if validation cannot be rerun after final source changes.
- STOP if the dependency/lock file would change.

## 7. Validation by Package Class

Every WP must state its package class and what validation is required for that class.

The validation matrix is in `docs/ai/codex/VALIDATION_MATRIX.md`.

Do not infer validation requirements. State them explicitly in the WP and confirm each after implementation.

## 8. Requirement-to-Evidence Traceability

Every nontrivial WP PR body must include a traceability table:

| Requirement | Source WP section | Evidence location | Status |
|---|---|---|---|
| ... | ... | ... | SATISFIED/OPEN |

No `Ready for review: YES` without this table for nontrivial WPs (M, L, XL size class).

## 9. Evidence Model

Every WP must declare its evidence mode before `Ready for review: YES`:

```
Evidence mode: PUBLIC_VERIFIER_PASS / PRIVATE_REPO_MANUAL_VERIFIED / BLOCKED_NOT_READY
```

Required evidence distinctions (see `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md`):

| Evidence type | Token |
|---|---|
| Local draft only | LOCAL_DRAFT_VERIFIED |
| Posted GitHub PR body/comment confirmed via API | POSTED_GITHUB_API_VERIFIED |
| Posted GitHub PR body/comment confirmed via manual UI | MANUAL_UI_VERIFIED |
| Not verified | NOT_VERIFIED |

Local drafts do not count as posted GitHub evidence.

When a WP claims a posted GitHub PR body or posted final evidence comment is verified, the actor must re-fetch that posted GitHub state after posting. A draft written and checked locally — even if identical to what will be posted — is `LOCAL_DRAFT_VERIFIED`, not `POSTED_GITHUB_API_VERIFIED`.

## 10. Review Self-Diagnosis

Every not-merge-ready review must include a self-diagnosis block:

```
Root cause:
Preventable: YES/NO
What should have caught it:
Immediate process change:
Durable guidance change needed: YES/NO
If YES, describe:
Follow-up defect category: (A/B/C/D/E/F/G/H/I)
```

If no review follow-up occurred, state that explicitly.

## 11. Worktree-First Execution

Preferred execution model:

```
One WP = one dedicated worktree = one branch = one PR
```

Branch-only fallback is allowed but must include:
- Explicit fallback note in the WP and PR body.
- Clean branch state confirmed before work starts.
- No dirty main.
- No branch reuse unless explicitly confirmed by the user.

## 12. Shared Claude/Codex Layer

All files under `docs/ai/codex/` apply to Codex, Claude Code, and all future AI coding agents unless a specific file says otherwise.

Claude-specific files are thin entrypoints pointing to the shared layer. Prompt wrappers and adapter files are non-canonical.

Precedence when sources conflict:
1. Current merged repo truth.
2. Active WP scope.
3. `AGENTS.md` and shared startup.
4. `docs/ai/codex/` workflow docs.
5. Chat memory, handoffs, generic best practice.

## 13. Prompt Wrappers Are Non-Canonical

If prompt wrapper docs exist (e.g., `prompts/execution_brief.md`, `.claude/skills/*.md`), they are compatibility wrappers only.

Canonical standards are: `AGENTS.md`, `AI_CODING_AGENT_START_HERE.md`, `CODEX_START_HERE.md`, `CLAUDE_START_HERE.md`, `docs/project_status.md`, `docs/repo_truth_index.md`, `docs/work_package_template.md`, and `docs/ai/codex/*.md`.

Prompt wrappers must not contradict canonical standards. If they do, canonical standards win.

## 14. Safety / Evidence Precedence Table

| Condition | Ready for review allowed? | Required output |
|---|---:|---|
| PR body current, no final comment where required | NO | follow-up / update evidence |
| Final comment current, PR body stale | NO | update PR body |
| Local drafts checked only | NO | state `Ready for review: NO` unless policy allows local-only |
| Posted GitHub evidence re-fetched and matches | YES | `POSTED_GITHUB_API_VERIFIED` or equivalent |
| GitHub API unavailable but manual UI verified | YES only if policy permits | `MANUAL_UI_VERIFIED` |
| Evidence surfaces mismatch | NO | record mismatch |
| Current head changed after validation | NO | rerun or justify evidence |
| Status fragment and PR body mismatch | NO | update both |

## 15. Forbidden Variant Matrix (Output WPs)

For WPs touching any advisory, report, or output surface, the following terms must not appear in machine outputs (they may appear only in normative forbidden-list sections of docs):

```
buy/sell recommendation
trade-ready
execution-ready
position sizing
expected return
profit target
stop loss
take profit
copy signal
strategy signal
paper trading candidate
```

## 16. Raw Metadata / Free-Form Mapping Policy

Raw metadata and free-form mappings must not be passed through into advisory, report, or validator outputs unless explicitly allowlisted and recursively scanned for forbidden terms.

This rule belongs in output-safety policy and WP scope, not in product code.
