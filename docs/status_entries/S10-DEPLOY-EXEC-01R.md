# S10-DEPLOY-EXEC-01R Status Entry

## Identity

- WP ID: S10-DEPLOY-EXEC-01R
- Title: Bootstrap Activation Invariant Repair
- Parent: S10-DEPLOY-EXEC-01 (repair envelope; not a new roadmap capability or architecture)
- Classification: bounded same-capability Phase-A bootstrap defect repair
- Package class / size / risk: BOOTSTRAP_ACTIVATION_DEFECT_REPAIR / S / 3
- Governance track: RUNTIME; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-deploy-exec-01-bootstrap-activation-repair
- Base: fe4e2f1557dec5667d32fa1479f0bfc7ead1c940 (parent PR #214 merge)
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Merge authorized: NO
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Trigger

- Real Phase-B run of the merged parent on the AlphaVPS C8G host:
  STOP BOOTSTRAP_ACTIVATION_DEFECT after the governed bootstrap reported BOOTSTRAP_COMPLETE
- Defects:
  - RUNTIME_VENV_NOT_EXECUTABLE — under `umask 027` the root-created venv was unreadable to
    `User=polymarket` (telemetry 203/EXEC; the critical probe would fail alike)
  - RELEASE_FILE_SET_MISMATCH — `pip install "$target_release"` built in-tree, leaving `build/` and
    `src/polymarket_strategy_lab.egg-info` in the immutable release, so activated-release
    verification (and execution-host binding/currentness) failed
- The observed failure is a bootstrap mechanism failure, not a C8G capacity result.

## Repair

- pip installs from a disposable `/tmp/polymarket-install-source.*` copy of the already-verified
  pristine incoming release, removed on PASS and via the EXIT trap on every FAIL
- after `pip check`: `chmod -R go+rX,go-w`, then `runuser -u polymarket` must execute the venv
  python and resolve project metadata (else `RUNTIME_VENV_NOT_EXECUTABLE`), then `chmod -R a-w`
- post-install `verify-release --allow-activation-artifacts` gate
  (`POST_INSTALL_RELEASE_VERIFY_FAILED`) before unit verification, firewall gates and the atomic
  current switch; `runuser` and `mktemp` join the required-command gate
- release verifier unchanged: `build/` and `*.egg-info` remain rejected; the release stays
  root-owned and never runtime-writable

## Exact Scope (5 paths)

- docs/status_entries/S10-DEPLOY-EXEC-01R.md
- docs/wp_specs/S10-DEPLOY-EXEC-01R/wp_prompt.txt
- docs/wp_specs/S10-DEPLOY-EXEC-01R/wp_spec.json
- tests/deployment/test_runtime_baseline.py
- tools/deployment/bootstrap_ubuntu_24_04.sh

## Authority / Non-Authority Posture

- Phase B: SUSPENDED pending repair merge and a fresh Phase-B authorization bound to the new merge SHA
- Host hand patch: NO
- VPS containment (parent Phase B, before this repair): telemetry timer disabled/inactive; critical
  probe disabled/inactive; no execution-host binding; the fe4e2f1 release remains forensic history only
- Trading credentials: NO
- Authenticated account access: NO
- Orders: 0
- Capital: USD 0
- Live: DISABLED
- runtime_baseline.py, systemd units, slices, src/, workflows, dependencies: unchanged
- Successor: the parent's Phase B on the new merge SHA (separately authorized); S10-LIVE-ORCH-01
  remains the parent's separately gated successor
