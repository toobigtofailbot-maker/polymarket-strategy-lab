# S10-HERMES-CTX-02 — Pinned Hermes Default SOUL.md Research-Home Compatibility Repair

Status: implementation complete; independent RUNTIME implementation review complete.

PR and current head: see GitHub PR metadata and PR body. This committed fragment is stable
and does not contain a mutable branch-head SHA; exact-head hosted CI and validation evidence
are recorded in the PR body.

Independent RUNTIME implementation review: PASS_WITH_NOTES, no blocking findings.
Ready for review: YES.
Side13 final exact-head review: PENDING.
Merge authorized: NO.
AF1 continuation: NOT AUTHORIZED by this WP.

## Frozen base and scope

- Base/main and PR #193 / WP164A merge SHA: `70f867bdcd5e97b0dc05d4008c2c023feb461658`.
- Governance track RUNTIME, risk level 3, package size M.
- Exact changed scope: 10 required = 10 allowed = 10 actual paths.
- Pinned Hermes: v0.21.3, release tag v2026.9.14, source commit 345cd2b.
- Accepted stock SOUL.md: 667 bytes, SHA-256
  `36c1f5a2e92cd1d018311eaf4c8f1e8886672eae78212e033c681d0e3d5d506f` (re-derived read-only
  from the pinned source at implementation time; no drift).
- Negative matrix: T01-T14 in
  `tests/research_runtime/hermes_controlled_runtime/test_runner.py`.

## Trigger and root cause

S10-GATE-AF1 Phase-B stopped with `PHASE_B_LOCAL_EVIDENCE_DEFECT` /
`HERMES_HOME_CONTROL_PLANE_INVALID`: the merged research-home preflight rejected any SOUL.md,
while pinned Hermes seeds its stock SOUL.md on every home initialization and the controlled
runtime re-runs the clean-home check before every invocation. Discovery of the defect consumed
zero provider, Firecrawl, and Polymarket calls.

## Delivered

- Private fail-closed verifier `_is_absent_or_pinned_stock_soul_md` in
  `src/research_runtime/hermes_controlled_runtime/runner.py`: absent SOUL.md passes; otherwise
  only a regular, non-symlink, non-reparse file of exactly 667 bytes whose raw-byte SHA-256
  equals the frozen digest passes. Size is checked before hashing; stat/open/read errors
  reject; no normalization, legacy template, prefix/fuzzy match, or caller-supplied digest.
- Frozen private constants bind the exception to the pinned artifact; Hermes is not imported.
- All other clean-home rules are unchanged: safe-home locator, `config.yaml`, non-empty
  `plugins/` and `skills/`, MEMORY/USER/AGENTS/CLAUDE/GEMINI and `.cursorrules`.
- `.env` and `auth.json` are still permitted by name only and are never opened.
- Admission verification only: SOUL.md is never deleted, rewritten, normalized, or replaced.
- Contract, project status, and repo-truth index record exact-stock-only semantics.

## Authority and residual limits

Real Hermes/provider/model calls: 0. Firecrawl/Polymarket/OAuth calls: 0. Secrets read: 0.
Dependencies/locks/workflows: unchanged. Policy, argv, managed config, provider/model,
toolset, retry/fallback, telemetry, and context-protocol semantics: unchanged.
AF1 branch/workspace: untouched. AF1 Attempt-03: UNCONSUMED and NOT AUTHORIZED.
H1 #5: NOT AUTHORIZED. Gate C: NOT AUTHORIZED. Capital/orders: 0.

## Successor boundary

After Side13 final review and Karl's separate merge only: refresh merged main, reconcile the
existing local AF1 branch onto repaired main, produce a new AF1 Phase-A head, re-validate,
freeze new digests, and obtain a new exact Attempt-03 authorization bound to that head before
re-checking the AF1 credential home. This package authorizes none of those steps.
