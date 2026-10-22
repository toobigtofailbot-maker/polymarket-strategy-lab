# S10-LIVE-CANARY-01: attended one-process Hermes choice -> native permit -> LIVE-ORCH first BUY canary composer

**Authority:** Karl authorized the complete software implementation of the certified 13-path package on 2026-10-21. That covers implementation, tests, branch and PR publication, and one final exact-head hosted CI run. It authorizes no live trading, real OAuth or model call, credential, account, host deployment, wallet, funding, order, capital or merge.
**Executor:** Claude Code.
**Branch:** `claude/s10-live-canary-01-attended-composer`.
**Frozen main:** `d41dbaaacd5833e229f5095ec689673b6544740d`.
**Predecessor:** PR #246, head `2bd85a3302b448370097b16a7aaf5136b293d502`, merged at frozen main.

**Governance:** PROTECTED, risk 4, size L, exactly 13 paths, R001–R009 and NR001–NR009. The independent Side21 certificate (sha256 `4f816ee3…3063`) binds prompt `94a7f497…ee11` and spec `f5ef3c76…b835`. With it, native `wp_spec_guard` returns PASS and `wp_readiness_gate` returns `IMPLEMENTATION_READY` for 13 files.

**State:** IMPLEMENTED_LOCAL. Merge ready: NO; Karl merges manually after Side21's final review. This fragment is stable and non-self-referential. The live PR head, CI and full-suite counts are in the PR body.

## Design

- **`src/execution_gateway/live_canary.py`:**
  - `check` is non-economic. It verifies the stores, policy, allocation and capacity, Alpha lineage, the canonical assessment, host currentness, geoblock, fresh venue, the native ledger, the OAuth paths and the read-only Stage A binding.
  - `run` is attended and TTY-only. Its sequence:
    1. take the Stage A run lock, a native `WalletSessionLock` in `<root>/live_canary`;
    2. rerun `check`;
    3. make one witnessed OAuth Stage B dispatch;
    4. call `prepare_live_canary_handoff`;
    5. recheck Stage A;
    6. print the order summary and take the Stage B line: phrase plus permit and Stage A suffixes;
    7. recheck the ledger head at the last boundary;
    8. make exactly one `LiveOrchestrator(config).canary(permit, intent)` call with production defaults.
- **Stage A:** the binding is machine conformance and single use only. The receipt label is `MACHINE_CONFORMANCE_ONLY_OWNER_APPROVAL_EXTERNAL`. Owner approval is the external activation record, operations blocker D007.
  - An empty or missing ledger is never approvable.
  - Deleting or recreating the ledger, or any ledger event, is detected.
  - Code cannot detect a privileged restore of an older ledger copy with identical bytes. This is a declared trusted-host limitation, shared with native `PERMIT_ALREADY_CONSUMED`.
- **Order type:** composer orders are post-only PASSIVE_MAKER, because AUTO-01 admits only GTC/GTD. The maker fee reserve is therefore exactly zero, or the run fails with `FEE_CONFIGURATION_UNKNOWN`. The native USD 5 cap is applied at final admission to the canary-time fee.
- **Bridge:** `live_preflight_bridge.prepare_live_canary_handoff` is additive. It returns the exact native permit and intent only on PASS. `run_live_preflight_bridge` receipt bytes are unchanged.
- **`live_orch.revalidate_venue`, the only section 4F change:** an absent `secondsDelay` is admissible only for post-only PASSIVE_MAKER GTC/GTD, recorded as `NOT_APPLICABLE_POST_ONLY`.
  - A known non-zero delay, and every other intent, still fails closed.
  - Absent is never read as zero.
  - A crossing post-only BUY stays `VENUE_NOT_FEASIBLE`.
- **`docs/live_trading_authorization.md`:** one appended two-stage paragraph. `LIVE TRADING STATUS: DISABLED` is unchanged.
- **Tests:** R001 is in `tests/research_runtime/test_live_preflight_bridge.py`, R002–R007 in `tests/execution_gateway/test_live_canary.py`, and R008/R009 in `tests/execution_gateway/test_live_orch.py`. All are offline and every result is OFFLINE_TEST_ONLY.
- **External operations blockers:** `docs/deferred_items_log.md`, S10-LIVE-CANARY-01-D001 to D008. Restored hosted-CI billing, section 7(g), is no longer a blocker.

## Call counts

Real OAuth or model dispatch 0, credential 0, account or private session 0, signer key 0, order 0, capital USD 0. Neither the implementation nor the tests used runtime, product or account network.
