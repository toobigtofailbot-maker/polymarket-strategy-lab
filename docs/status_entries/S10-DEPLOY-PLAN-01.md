# S10-DEPLOY-PLAN-01 Status

- WP: `S10-DEPLOY-PLAN-01` — Production VPS Hosting Direction Lock
- Base: `d45d9587401faddd2ba92f33cb84f2988b6cfe70` (execution base equals the frozen base)
- Predecessor: PR #206 / `S10-QUAL-DATA-03`, head `b7d77f95df093b259a2a2b809ffe20308539e397`, MERGED at the base SHA
  (`isDraft=false`, GitHub server merge time 2026-10-01T15:08:12Z)
- Package class: `DOCS_ONLY_ARCHITECTURE_ROADMAP`; governance FAST, risk 1, capital at risk USD 0; no draftability
  certificate required
- Package size class: L in the machine spec. Side14 drafted M; the repo WP spec guard caps M at 10 changed files, so the
  exact 13-path scope is classified L (classification only; no path added, removed or widened; S10-DEPLOY-PLAN-01-D005)
- Exact changed-file scope: 13 / 13 (docs/tests only); src/tools/workflows/dependencies unchanged
- Branch: `claude/dazzling-allen-wru4ti` (the session-designated branch; suggested name
  `codex/s10-deploy-plan-01-production-vps-hosting-direction`)
- Authorization: Karl's sending of the exact Side14 package is the implementation authorization; merge separately gated
- Evidence mode: `PRIVATE_REPO_MANUAL_VERIFIED`
- PR: see GitHub PR metadata and PR body.
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable and
  non-self-referential; it does not encode dynamic PR metadata or the SHA of the commit containing itself.
- Merge authorized: NO

Current S10-DEPLOY-PLAN-01 state: IMPLEMENTED_READY_FOR_REVIEW

## Hosting Direction (planning truth only)

- Focused contract: `docs/production_vps_hosting_direction.md`
- Decision status: APPROVED_PLANNING_DIRECTION
- Deployment status: NOT_PROVISIONED / NOT_DEPLOYED
- Provider: AlphaVPS
- Location: Sofia, Bulgaria
- Initial tier: C8G
- Resources: 4 vCPU / 8 GB ECC RAM / 75 GB NVMe RAID-10
- OS: Ubuntu 24.04 LTS / x86-64
- Architecture: ONE_CONSOLIDATED_POLYMARKET_VPS
- Default split-VPS architecture: NO
- Upgrade path: C8G -> C12G -> C16G/P-series -> larger only by telemetry evidence
- Upgrade criteria recorded: YES (memory, CPU, disk capacity, disk I/O, execution-path interference, recovery,
  resource-isolation failure; review triggers only, never automatic; exact metrics frozen later by S10-DEPLOY-01)
- Migration point: after a real strategy-specific WP172 EXECUTABLE_EDGE_PASS exists and before the first serious
  production-hosted paper runtime using the existing WP173 system
- WP172 generic substrate already exists: YES (PR #174)
- WP173 generic serious-paper system already exists: YES (PR #175; not reimplemented)
- Future deployment package: S10-DEPLOY-01 — Production VPS Runtime Baseline (DRAFT-ELIGIBLE LATER)
- Future deployment package authorized: NO
- Minimum production-host proof recorded: YES
- Single-host coexistence proof recorded: YES
- C8G telemetry disposition required: YES (C8G_SUFFICIENT or UPGRADE_ELIGIBLE:<reason>; no auto-upgrade/purchase)
- Superseded as current truth: WP61 "cheap VPS later" shorthand (kept as history), the charter's open VPS/cloud choice,
  and the "after WP172 and before WP173" shorthand

## Qualification Chain

- PR #206 / S10-QUAL-DATA-03: MERGED (merge `d45d9587401faddd2ba92f33cb84f2988b6cfe70`)
- DATA03 implementation state: DATA03_IMPLEMENTED_NOT_STARTED
- Attempt 03 source probe: PROBE_PASS
- Next immediate runtime action: zero-network DATA-03 prepare (the already-drafted post-merge prepare closure, unchanged)
- no real accrue before 2026-10-15T00:00:00Z
- DATA-03 moved to VPS: NO (remains on the current operator environment)
- DATA-03 code/contract/status fragment/WP artifacts edited: NO
- S10-DEPLOY-PLAN-01 changes planning truth only and does not interrupt the qualification chain

## Authority

- VPS purchased/provisioned: NO
- Deployment performed: NO
- AlphaVPS probed/benchmarked: NO
- Credentials created: NO
- DATA-03 runtime commands run: NO
- Paper authority changed: NO
- Live authority changed: NO
- Gate C: NOT AUTHORIZED
- Capital/orders: USD 0 / 0
- Network: workflow only (Remote Main Sync Gate, git fetch/push, PR publication, GitHub connector reads, CI-pinned PyPI
  install into a scratch virtualenv outside the repo); no product, provider, hosting or account network

## Deferred Items

- Added: S10-DEPLOY-PLAN-01-D001 (S10-DEPLOY-01 implementation, DEFERRED_NOT_AUTHORIZED), D002 (WP61-D003 direction
  superseded; deployment still deferred), D003 (exact upgrade metrics/baseline, DEFERRED_TO_S10_DEPLOY_01), D004
  (jurisdiction/geoblocking/terms/latency verification of the Sofia host, P1, DEFERRED_TO_S10_DEPLOY_01), D005
  (size-class label reconciliation, RECORDED_DESIGN_NOTE)
- Resolved: none

## Validation

- Focused docs tests: `python -m pytest -q -p no:cacheprovider tests/test_architecture_direction_docs.py tests/test_project_status_docs.py tests/test_repo_truth_docs.py` -> see PR body
- Readiness --check-diff: `python tools/wp/wp_readiness_gate.py --wp docs/wp_specs/S10-DEPLOY-PLAN-01/wp_prompt.txt --spec docs/wp_specs/S10-DEPLOY-PLAN-01/wp_spec.json --repo-root . --check-diff --base d45d9587401faddd2ba92f33cb84f2988b6cfe70 --head HEAD` -> see PR body
- Negative test matrix: NOT_APPLICABLE (no validator/guard/parser added; docs tests carry stale-wording negatives)
- Background tasks alive after final response: NO
