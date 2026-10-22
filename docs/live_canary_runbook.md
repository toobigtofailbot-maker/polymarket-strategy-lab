# S10-LIVE-CANARY-01 attended canary runbook

This runbook is an operator sequence only. It grants no authority. `docs/live_trading_authorization.md` stays **DISABLED**. Neither merging this code, green CI nor any step below authorizes a live run. Each numbered stage needs Karl's separate, exact authorization at the time it happens.

The canary validates execution mechanics only. It is not edge, profitability or strategy qualification. `ONE_CREATE_ATTEMPTED` is not a fill.

## 1. Preconditions (each separately authorized; see `docs/deferred_items_log.md`, S10-LIVE-CANARY-01-D001 to D008)

- **Operator eligibility:** Karl's physical location at operation time, account eligibility and any identity verification are attested by the owner. No VPN, proxy, alternate host or region workaround is ever used.
- **Host:** the bound execution host runs the exact merge SHA, with strict host currentness and a fresh native geoblock reporting `blocked=false`.
- **Pinned Hermes:** the pinned Hermes runtime and a usable OAuth credential directory are on the host. The credential-directory transfer is a proposal pending Karl's approval. Its acceptance proof is one separately authorized, non-dispatch OAuth preflight reporting `PLAN_USAGE_ELIGIBLE`.
- **Strategy records:** the stores are installed, and so is the Alpha candidate and StrategyVersion lineage for one non-neg-risk binary market. Karl activates the policy and an `EXPLORATORY_LIVE` allocation. A fresh, genuine canonical assessment of the canary StrategyVersion must exist, made after that activation.
- **Wallet:** a deployed and funded Deposit Wallet and its signer exist in an eligible account. Gate-B never deploys a wallet.

## 2. Bootstrap, in this exact order (zero-economic, separately authorized)

1. Resolve `P = canonical_live_orch_store_path(state_root, wallet)`.
2. If `P.parent` is missing, create it, owned by the run user, mode `0700`, with no symlink in the path. Native create requires an existing parent.
3. If `P` already exists, STOP. Re-initialization needs Karl's separate decision.
4. Call `ProtectedExecutionGateway.create(P, created_time_ns=now)` exactly once, then `.close()`.
5. Read the head with `src.execution_gateway.live_canary.read_ledger_head(P)`. This is read-only. Never use `ProtectedExecutionGateway.open`, which appends a RESTARTED event.
6. Compute `live_canary.execution_host_binding_sha256(case)` offline from the case file.
7. Karl writes the Stage A artifact (`polymarket-live-canary-stage-a` 1.0.0) from these exact values. It contains:
   - release SHA and host binding;
   - state root and non-empty ledger head;
   - signer and wallet;
   - approved menu (equal to the case menu);
   - `BUY`, at most one CREATE;
   - the frozen 100/5/30/70 envelope;
   - a validity window of at most 72 h.

   Karl records the artifact's full SHA-256 in his separate post-merge activation decision. The case receives the artifact path and digest.
8. Only now run `check`.

**NO LIVE RUN** unless Karl's authentic activation record names the Stage A digest. The code checks machine conformance and single use only. It cannot detect a conformant artifact that Karl did not approve.

Keep the bound ledger intact: never delete, recreate or restore it. Backups must never restore an older ledger. Never use the native `live_orch canary` CLI for this canary.

## 3. Commands

```bash
python -m src.execution_gateway.live_canary check --case /abs/path/case.json
```

`check` is non-economic. It makes no OAuth call, key prompt, Gate-B session or order, and writes no store. Without a valid Stage A it returns a typed BLOCKED result only.

```bash
python -m src.execution_gateway.live_canary run --case /abs/path/case.json
```

`run` must be attended on an interactive TTY. Its steps:
1. Take the Stage A run lock.
2. Rerun `check`.
3. Fetch fresh menu snapshots.
4. Make one OAuth Stage B dispatch into a new, empty journal directory.
5. Run the bridge handoff.
6. Recheck Stage A.
7. Print the order summary.
8. Take the Stage B line. Type exactly `CONFIRM-LIVE-ORCH-ONE-BUY-CANARY <last 12 of permit_id> <last 12 of Stage A digest>`. These suffixes are a correlation check against the displayed IDs and your record, not authentication.
9. Recheck at the last boundary.
10. Call `.canary` once, with production defaults and the native no-echo signer prompt.

The permit window is at most 60 s. A slow confirmation ends in native `PERMIT_EXPIRED` with zero transmit. A retry is a new `run` with a new journal, and therefore a new OAuth dispatch. It is possible only while Stage A is unconsumed: any native ledger event, including a reconcile, consumes it.

## 4. After the run

If the receipt carries `reconcile_required`, run the printed `python -m src.execution_gateway.live_orch reconcile ...` command. There is no automatic reconcile loop.

A crash leaves the `live_canary` run lock behind, and the next run reports `STAGE_A_RUN_LOCKED`. Run native `reconcile` first; it takes no composer lock. Only then remove the stale lock by hand. Never delete the ledger.

## 5. Stop codes

| Code | Meaning |
|---|---|
| `CASE_INVALID` | Malformed or out-of-bounds case |
| `ATTENDED_TTY_REQUIRED` | No interactive TTY |
| `OFFLINE_SEAM_IN_ECONOMIC_PATH` | A test seam reached the real economic path |
| `OFFLINE_HANDOFF_IN_PRODUCTION` | A test-only handoff reached a production run |
| `STAGE_A_UNAVAILABLE`, `STAGE_A_DIGEST_MISMATCH`, `STAGE_A_INVALID` | Artifact absent, altered or malformed |
| `STAGE_A_WINDOW_INVALID` | Outside the Stage A validity window |
| `STAGE_A_SCOPE_MISMATCH` | Release, host, root, signer, wallet, menu, side, attempts or envelope differ, or the intent is outside the approved menu |
| `STAGE_A_LEDGER_UNINITIALIZED` | Ledger missing, empty or replay-invalid |
| `STAGE_A_CONSUMED` | Ledger head differs from the approved head |
| `STAGE_A_RUN_LOCKED` | Another run, or a stale crash lock, holds the run lock |
| `STRATEGY_ASSESSMENT_UNAVAILABLE`, `POLICY_NOT_ACTIVE`, `ALLOCATION_REQUIRED`, `ALLOCATION_NOT_ACTIVE`, `PORTFOLIO_CAPACITY_REJECTED`, `ALPHA_STRATEGY_LINEAGE_INVALID` | Strategy authority is not current |
| `HOST_NOT_CURRENT`, `ACCESS_NOT_ELIGIBLE` | Host or geoblock gate failed (never worked around) |
| `MARKET_NOT_ELIGIBLE`, `NEG_RISK_UNSUPPORTED`, `FEE_CONFIGURATION_UNKNOWN`, `SECONDS_DELAY_UNSUPPORTED`, `VENUE_SNAPSHOT_UNAVAILABLE` | Venue not admissible |
| `LIVE_ORCH_LEDGER_UNHEALTHY` | Native ledger replay failed |
| `OAUTH_JOURNAL_NOT_FRESH`, `OAUTH_PREFLIGHT_INELIGIBLE`, `OAUTH_ATTEMPT_FAILED`, `OAUTH_RESULT_NOT_WITNESSED` | No usable witnessed choice; no second dispatch |
| `OWNER_CONFIRMATION_MISMATCH` | The Stage B line was not exact, or EOF |
| `PERMIT_INTENT_MISMATCH` | Permit and intent are not the native pair |
| Native LIVE-ORCH codes (for example `PERMIT_EXPIRED`, `SINGLE_ORDER_LIMIT_EXCEEDED`, `VENUE_NOT_FEASIBLE`) | Final admission refused; zero transmit |
