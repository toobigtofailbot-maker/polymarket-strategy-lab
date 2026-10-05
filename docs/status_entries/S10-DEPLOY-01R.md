# S10-DEPLOY-01R Status Entry

## Identity

- WP ID: S10-DEPLOY-01R
- Title: Canonical Public-Smoke Persistent-Path Repair
- Parent: S10-DEPLOY-01 (repair envelope; not a new roadmap capability or architecture)
- Triggered by: S10-DEPLOY-EXEC-01 Phase B (real AlphaVPS C8G run on cbdff8ccdce36d1fc51eda45d4f8140c80932931)
- Classification: bounded canonical public-smoke persistent-path repair
- Package class / size / risk: RESEARCH_SMOKE_PATH_CONTRACT_REPAIR / S / 3
- Governance track: RUNTIME; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-deploy-01r-public-smoke-path-repair
- Base: cbdff8ccdce36d1fc51eda45d4f8140c80932931
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Merge authorized: NO
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Defect

- The canonical relative smoke DB path (`local_data/polymarket/deploy_smoke.sqlite3`) traverses the
  governed release `local_data` symlink, while WP169 correctly rejects symlinked parents.
- On the correctly deployed host the one authorized smoke returned `FAILED [STORE_CONFLICT]` with zero
  actual counts and no network fetch, so the mixed window was not a valid mixed-load proof and the
  coexistence evaluator correctly returned `EXECUTION_HOST_INCONCLUSIVE` (`RESEARCH_SMOKE_NOT_PASSED`).
- Not a C8G capacity, network, provider or bootstrap-repair failure.

## Repair

- Canonical `--output-db` is now `/var/lib/polymarket/local_data/polymarket/deploy_smoke.sqlite3`.
- Precondition: `/var/lib/polymarket/local_data/polymarket` exists as a real directory (not a
  symlink) owned and writable by `polymarket` with bounded permissions; the DB path is not a symlink.
- The historical release-relative invocation is superseded for future host activation; the
  historical S10-DEPLOY-01 prompt/spec are preserved unedited.
- Exactly one smoke per separately authorized activation attempt; public, unauthenticated, finite,
  foreground, research slice, 60 seconds, max-pages 1, truthful actual-count criteria unchanged.
- Store security policy: UNCHANGED
- Source/runtime implementation: UNCHANGED (`src/**`, `tools/polymarket/**`, `runtime_baseline.py`,
  bootstrap, systemd units untouched)

## Exact Scope (5 paths)

- docs/research_platform_runtime_baseline_contract.md
- docs/status_entries/S10-DEPLOY-01R.md
- docs/wp_specs/S10-DEPLOY-01R/wp_prompt.txt
- docs/wp_specs/S10-DEPLOY-01R/wp_spec.json
- tests/deployment/test_runtime_baseline.py

## Authority / Non-Authority Posture

- Phase B: SUSPENDED pending repair merge and a fresh Phase-B authorization bound to the new merge SHA
- Formal reboot consumed: NO
- VPS during repair: frozen (current cbdff8c release, binding present, telemetry active, critical
  probe disabled/inactive); no smoke, mixed window, backup, restore or reboot
- Trading credentials: NO
- Authenticated account access: NO
- Orders: 0
- Capital: USD 0
- Live: DISABLED
- Successor: the S10-DEPLOY-EXEC-01 Phase B on the new merge SHA (separately authorized);
  S10-LIVE-ORCH-01 remains separately gated
