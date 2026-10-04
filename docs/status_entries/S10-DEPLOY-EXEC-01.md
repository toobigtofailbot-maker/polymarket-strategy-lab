# S10-DEPLOY-EXEC-01 Status Entry

## Identity

- WP ID: S10-DEPLOY-EXEC-01
- Title: Execution-Host Runtime Substrate & Coexistence Proof
- Package class: EXECUTION_HOST_RUNTIME_SUBSTRATE
- Branch: claude/s10-deploy-exec-01-execution-host-substrate
- Frozen base commit: 0392c2d2080a656d8ffd69f42abf8ad91d1f90e2
- Required predecessor: PR #213 / S10-GATE-C-EXPLORE-01, head 342dfeb24652eccb1b6bdf237039b268115b1fb7,
  merge 0392c2d2080a656d8ffd69f42abf8ad91d1f90e2
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Merge authorized: NO
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body
- Readiness basis: DETERMINISTIC (RUNTIME; no certificate required)

## Authority / Non-Authority Posture

- Package class / size / risk: EXECUTION_HOST_RUNTIME_SUBSTRATE / L / 3
- Governance track: RUNTIME
- Exact implementation scope: 18 paths
- Local offline tooling: YES — additive `tools/deployment/` extension plus one systemd unit
- Scheduler: YES — systemd supervision/restart mechanics of the inactive critical probe only
- Network: YES — Git/GitHub workflow traffic only; the bounded public research smoke belongs to
  the separately authorized Phase B
- Source runtime (`src/`), credentials, account reads, execution, paper, strategy, Hermes, live: NO
- GateCLivePermit / GateCSession arm / A3: NO; signing, order create/post/cancel/amend: NO
- Dependency, workflow, `tools/wp/` change: NO
- Capital/orders: USD 0 / 0
- Protected boundary groups not crossed: credentials/secrets, authenticated clients,
  wallet/account behavior, order placement/cancel, execution gateway, paper engine,
  dependency/lock changes, external code copying, generated artifacts

## Current Capability

- Contract: `docs/execution_host_runtime_contract.md` (DEPLOY-01 research baseline contract
  unchanged; research/critical slice values unchanged)
- Execution-host binding (`polymarket-execution-host-binding`): pseudonymous pmhost-v1 host id,
  exact release SHA, release manifest hash, critical-probe unit hash; canonical, timestamp-free,
  written atomically only by the explicit `execution-host-bind` step
- Currentness evidence (`polymarket-execution-host-currentness`): pmboot-v1 boot id, closed
  fail-closed codes for host/release/current-symlink/manifest/unit mismatch; strict mode requires
  synchronized NTP, exact SSH-only UFW and persistent state
- `polymarket-execution-critical-probe.service`: non-economic heartbeat in
  `polymarket-critical.slice`, Restart=on-failure, RestartSec=1s, no network/environment/credential,
  single-writer lock; installed, verified and hashed by bootstrap but left disabled/inactive
- Coexistence evaluator: closed dispositions C8G_EXECUTION_HOST_SUFFICIENT /
  UPGRADE_ELIGIBLE:CRITICAL_DEADLINE|CRITICAL_DEGRADATION|MEMORY|CPU|DISK|IO /
  EXECUTION_HOST_INCONCLUSIVE; nearest-rank p95; `> 500.0` ms deadline; `> 20%` degradation
- Terminal Phase-B evidence: EXECUTION_HOST_PROVEN_C8G /
  EXECUTION_HOST_EVIDENCE_COMPLETE_UPGRADE_ELIGIBLE:<reason> / EXECUTION_HOST_INCONCLUSIVE;
  never implies live readiness
- Synthetic test fixtures prove evaluator semantics only, never actual host capacity

## Phase B (separately authorized; not part of this implementation)

- Phase B executed: NO
- AlphaVPS accessed/configured in Phase A: NO
- AlphaVPS purchased/provisioned: operator-reported by Karl; not repository-observed
- Project deployment on AlphaVPS: NOT PERFORMED; actual host technical facts: UNKNOWN until Phase B
- Remaining Phase-B items: exact merge-SHA release build/transfer, actual-host verification,
  governed bootstrap, binding, strict currentness, process-kill/restart proof, isolated and mixed
  60-second coexistence windows, real backup/isolated restore, one real reboot with recovery
  verification, probe stop/disable, sanitized terminal evidence returned to Side 16 / Karl
- No automatic upgrade, purchase or second host; Karl decides

## Repo-Truth Reconciliation

- S10-GATE-C-EXPLORE-01: MERGED (PR #213)
- S10-DEPLOY-EXEC-01: current bounded implementation target / implemented review target
- S10-LIVE-ORCH-01: next core successor after execution-host substrate proof, NOT STARTED
- Gate-C eligibility and DEPLOY-EXEC host proof: each necessary-but-not-sufficient
- ALPHA-03 and DATA-03: separate / non-blocking
- Control Center: separate / non-canonical
- Live: DISABLED; capital/orders USD 0 / 0

## Validation Summary

- Readiness, focused tests, architecture/status/repo-truth tests, exact-scope diff, authoritative
  full suite and exact-head hosted CI: recorded with exact commands/results in the PR body after
  final validation
