# S10-LIVE-ORCH-01 Status Entry

## Identity

- WP ID: S10-LIVE-ORCH-01
- Title: Restricted Live Orchestration + First-Live Canary Core
- Package class: PROTECTED_RESTRICTED_LIVE_ORCHESTRATION
- Branch: claude/s10-live-orch-01-restricted-live-orchestration
- Frozen base commit: 3f4d9ed91c0e96b9fc19389ac59e01f079caa3fe
- Required predecessor: PR #218 / S10-DEPLOY-EXEC-01R3, head b1779f5bc6e945eedfa1ba0692a9e1baca779973,
  merge 3f4d9ed91c0e96b9fc19389ac59e01f079caa3fe
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Merge authorized: NO
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body
- Readiness basis: INDEPENDENT_CERTIFICATE (PROTECTED; certificate hash-bound to the exact
  prompt/spec bytes; the implementer created no certificate)
- Certified package: prompt SHA-256 41d35b5b1bc78ef54d15fbb1395dda4687e8845db7c88186ab84f3330f8e9393,
  spec SHA-256 950e55bf092f4c66b2ef743ff0b5be4e1b62e6c7980a7334c959949dd69b5a6a, certificate SHA-256
  238cbdd5a949891c44743cd6c5475722b30ce0878b663c2c7945c88ecaafd664 (all byte-identical in
  `docs/wp_specs/S10-LIVE-ORCH-01/`)

## Authority / Non-Authority Posture

- Package class / size / risk: PROTECTED_RESTRICTED_LIVE_ORCHESTRATION / XL (explicit XL
  authorization) / 4
- Governance track: PROTECTED
- Exact implementation scope: 27 paths
- Source runtime, network, credentials, execution, live: YES as dormant protected capability only
  (separately gated); workflow governance, local offline tooling, workflow files, dependencies,
  scheduler, Hermes runtime, strategy, paper: NO
- Implementation/CI real product network calls: 0; real credentials: 0; authenticated account
  access: 0; real economic CREATE/CANCEL: 0; capital: USD 0; live: DISABLED
- Workflow network use: Git remote synchronization, branch push, PR publication and hosted CI only
- Dependency, workflow, `tools/` change: NO (polymarket-client==0.10.0 unchanged)
- Protected boundary groups crossed only within the certified scope: execution gateway, protected
  runtime; never crossed: dependency/lock changes, workflow files, external code copying, generated
  artifacts, `src/exploratory_gate_c/`, `src/strategy_lifecycle/`, `src/research_runtime/`,
  `src/paper_trading/`, `src/data_layer/`, operator cockpit

## Current Capability

- Contract: `docs/live_orchestration_contract.md`
- `src/execution_gateway/live_orch.py`: single manual foreground orchestrator (`preflight` read-only,
  `canary` one CREATE maximum, `reconcile` risk-reducing only); no daemon, scheduler, service,
  WebSocket recovery authority, raw SDK client or cockpit mutation UI
- Authority chain: exact current ExploratoryGateCPermit + exact ExecutionIntent + strict
  execution-host currentness / NTP + fresh geoblock + exact Deposit Wallet identity + fresh bounded
  account truth + fresh compatible public venue + frozen capital envelope + healthy canonical ledger
  -> durable LIVE_ORCH_ADMISSION -> durable CREATE_STARTED -> at most one transmit -> authoritative
  reconciliation -> no-new-exposure
- First-live CREATE: BUY only (SELL -> SIDE_UNSUPPORTED_FIRST_CANARY before admission, signing or
  transmit); envelope USD 100 / 5 / 30 / 70, no auto scaling; truthful observed-PnL guards 5 / 7.5 / 10
- Gate-B: bounded exact account truth (100-item bound -> ACCOUNT_HISTORY_LIMIT_EXCEEDED), trade IDs
  and settlement statuses retained, local aggressive BUY construction (`create_market_order`, never a
  post), LIVE-ORCH cancel transport with never-resend identities, fee-enabled standard metadata usable
- Gate-C: LIVE-ORCH one-use mutation boundary (post-construction no-widening inspection,
  ORDER_ENCODING_UNSUPPORTED on pinned 0.10.0 rounding drift, durable admission then CREATE_STARTED,
  one transmit, unknown response AMBIGUOUS, cancel recovery with a NEW identity each round); the
  historical classifier no longer treats venue code `unknown` as definitive rejection
- Gateway/store: restart-safe multi-episode LIVE-ORCH ledger in the existing journal (closed states,
  closed transition table, replay validation, restart flag, one permit per episode); public venue
  order IDs and release SHA persistable only under allowlisted field names
- EXEC-FEAS: Gamma USDC-notional and CLOB-share minima are independent dimensions with the new
  closed diagnostic MINIMUM_ORDER_SHARES_NOT_MET

## Reviewed Defects Closed

- A: clean terminal episodes no longer make the ledger single-use; fresh permits work after restart
- B: a known reconciled residual position is carried as commitment and coexists with a later fresh
  BUY when aggregate guards pass; unknown positions block
- C: ambiguous cancel has a bounded recovery exit with fresh attempt identities (max three rounds)
- D: ExploratoryGateCPermit is the upstream economic-intent authority; no paper qualification needed
- E: gamma_market_id, condition_id and token_id stay distinct in every episode binding
- F: unknown / unrecognized CREATE responses are AMBIGUOUS
- G: trade IDs and settlement status persisted; FAILED is not a fill; MATCHED/MINED/RETRYING are not final
- H: LIVE-ORCH commitment is computed from authoritative truth (the historical "0" is not used)
- I: fee-enabled standard markets are usable with a known fee configuration
- J: EXEC-FEAS minimum-order dimensions repaired (R009 negative control on the frozen base)

## Package Notes

- Certification history: the first certified prompt listed
  `fetch_public_venue_snapshot(..., started_at_ns, completed_at_ns)`; the implementer hard-stopped
  S10_LIVE_ORCH_INTERFACE_MISMATCH before any code. The recertified prompt (single-line factual
  correction to `opener=None, clock_ns=None`, spec unchanged) received a new independent certificate
  and Karl re-authorization before implementation.
- Local validation ran in an ephemeral Linux Docker container (Python 3.12, the hosted-CI dependency
  pins) because Windows Application Control blocks the native pyarrow/nautilus extensions on the
  operator workstation; Karl authorized the container for validation only.
- Observed outside scope, not changed (historical WP175 path): `GateCSession.create_limit_order`
  compares the signed `signer` with the EOA signer although pinned 0.10.0 signs Deposit Wallet
  (signature type 3) orders with `signer == wallet`; and the WP174 shadow venue-context adapter maps
  `market_id` to the condition ID. LIVE-ORCH does not use either path. Recording them in
  `docs/deferred_items_log.md` would need a 28th path, so they are reported in the PR body instead.

## Successor Boundary

- Next: S10-LIVE-CANARY-01 First Restricted Live Canary Activation, separately gated; requires a
  standalone exact-merge Karl authorization binding the actual merge/deployed SHA, exact permit ID,
  exact intent ID, public canary-wallet identity, one CREATE maximum, the USD 100 / 5 / 30 / 70
  envelope and operator confirmation
- This package never authorizes a real order

## Repo-Truth Reconciliation

- S10-DEPLOY-EXEC-01: MERGED (PR #214; repairs PR #215, #217 and #218)
- S10-LIVE-ORCH-01: current protected implementation target / implemented review target
- WP175: historical manual canary path, unchanged in authority
- ALPHA-03 and DATA-03: separate / non-blocking
- Control Center: separate / non-canonical
- Live: DISABLED; capital/orders USD 0 / 0

## Validation Summary

- Readiness (exact certificate + `--check-diff`), focused tests, compatibility guards,
  architecture/status/repo-truth tests, diff/artifact/security hygiene, one stable full suite and
  exact-head hosted CI: recorded with exact commands/results in the PR body after final validation
