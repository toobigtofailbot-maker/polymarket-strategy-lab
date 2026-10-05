# Long-Term Bot Completion Roadmap

## A. Status

- Current protected implementation package: S10-LIVE-ORCH-01 Restricted Live Orchestration +
  First-Live Canary Core on frozen base `3f4d9ed91c0e96b9fc19389ac59e01f079caa3fe` after PR #218 /
  S10-DEPLOY-EXEC-01R3 (merged: YES; head `b1779f5bc6e945eedfa1ba0692a9e1baca779973`). PROTECTED, risk 4, exact
  27-path XL scope, independent certificate (`docs/live_orchestration_contract.md`): one manual
  foreground orchestrator (`src/execution_gateway/live_orch.py`) consuming one exact current
  ExploratoryGateCPermit with strict host currentness, fresh geoblock, exact Deposit Wallet
  identity, bounded account truth, fresh venue drift checks and the frozen USD 100 / 5 / 30 / 70
  envelope; durable admission before at most one BUY CREATE; restart-safe multi-episode
  reconciliation; plus the EXEC-FEAS minimum-order dimension repair. Dormant capability only:
  implementation/CI real network, credentials, account access, orders and capital are 0; live
  DISABLED; the first real canary (S10-LIVE-CANARY-01) is separately gated.

- Immediate merged predecessor: S10-DEPLOY-EXEC-01 Execution-Host Runtime Substrate &
  Coexistence Proof (PR #214 merged at `fe4e2f1557dec5667d32fa1479f0bfc7ead1c940`; head
  `9871dddf98565b16194209f032cf8279bfbd34f1`; repairs PR #215, #217 and #218 merged; formerly the
  current bounded implementation package) on frozen base `0392c2d2080a656d8ffd69f42abf8ad91d1f90e2` after PR #213 / S10-GATE-C-EXPLORE-01
  (merged: YES; head `342dfeb24652eccb1b6bdf237039b268115b1fb7`). RUNTIME, risk 3, exact 18-path scope. It extends the merged
  S10-DEPLOY-01 `tools/deployment/` baseline (`docs/execution_host_runtime_contract.md`): a
  sanitized execution-host binding/currentness contract, a non-economic critical-probe service in
  the existing critical slice (installed but inactive after bootstrap), a closed
  research-versus-critical coexistence evaluator and closed terminal Phase-B evidence semantics.
  Execution-capable host substrate only: no `src/` change, credential, account, Gate-C permit
  consumption, signing, order, OMS, reconciliation, capital or live authority.
  Status at DEPLOY-EXEC implementation time: S10-GATE-C-EXPLORE-01: MERGED (PR #213);
  S10-DEPLOY-EXEC-01: then the current implemented review target (now MERGED in PR #214)
  (repository mechanism; real AlphaVPS host proof is a separately authorized Phase B after
  merge, NOT PERFORMED); S10-LIVE-ORCH-01: next core successor after execution-host substrate proof,
  NOT STARTED. AlphaVPS purchased/provisioned per Karl (operator-reported; not repository-observed);
  project deployment on it NOT PERFORMED. No automatic upgrade or second host. ALPHA-03 and DATA-03
  separate/non-blocking; Control Center separate and non-canonical. Live DISABLED; capital/orders
  USD 0 / 0.

- Earlier merged predecessor: S10-GATE-C-EXPLORE-01 Exploratory Gate C Policy Permit Core
  (PR #213 merged at `0392c2d2080a656d8ffd69f42abf8ad91d1f90e2`; head `342dfeb24652eccb1b6bdf237039b268115b1fb7`; formerly the current protected
  implementation package) on frozen base `35db4f05347b8b27f7bd0296cf9b1b0627e58d12` after PR #212 / S10-EXEC-FEAS-01 (merged: YES;
  head `99f3c3c8acc09ae3b5646f785446d69a7b8b2290`). PROTECTED, risk 4, exact 18-path scope, independent certificate.
  It adds only the stdlib-only `src/exploratory_gate_c/` package
  (`docs/exploratory_gate_c_contract.md`): verified read-only STRAT-LIFE and Hermes manager store
  loading, exact StrategyVersion / active policy / EXPLORATORY_LIVE allocation / portfolio capacity
  / latest compatible Hermes assessment / exactly re-derived FEASIBLE-or-LIMITED EXEC-FEAS binding,
  a content-addressed ExploratoryGateCDecision and an exact-intent ExploratoryGateCPermit.
  Eligibility authority only: necessary-but-not-sufficient future evidence, not live activation;
  no network, account, geoblock, credential, signing, order, persistence, legacy WP175 Gate-C live
  permit, A3 or live authority; WP175 unchanged.
  Status at GATE-C-EXPLORE implementation time: S10-STRAT-LIFE-01: MERGED; S10-HERMES-STRAT-01:
  MERGED; S10-EXEC-FEAS-01: MERGED; S10-GATE-C-EXPLORE-01: then the current protected implemented
  review target (now MERGED in PR #213); S10-DEPLOY-EXEC-01: then the next core successor after
  review+merge; S10-LIVE-ORCH-01: later; S10-CC-OPS-01: separate, may begin only after
  GATE-C-EXPLORE merges. S10-CC-FOUND-01 parallel/independent; ALPHA-03
  parallel/non-blocking; DATA-03 unchanged and non-blocking; S10-DEPLOY-01 host activation
  separate. Live DISABLED; capital/orders USD 0 / 0.

- Earlier merged predecessor: S10-EXEC-FEAS-01 Current Public Execution Feasibility Core (PR #212
  merged at `35db4f05347b8b27f7bd0296cf9b1b0627e58d12`; head `99f3c3c8acc09ae3b5646f785446d69a7b8b2290`; formerly the current bounded implementation package)
  on frozen base `4519aab3d7f8424fc74c59104cc4e7afe0ff11b8` after PR #211 / S10-HERMES-STRAT-01 (merged: YES;
  head `9439283768b78b7302290ba6b8611e3477aa3c6a`). It adds only the stdlib-only `src/execution_feasibility/` package
  (`docs/execution_feasibility_contract.md`): one exact StrategyVersion bound read-only, a
  content-addressed ExecutionIntent, a bounded two-GET public Gamma/CLOB
  PublicExecutionVenueSnapshot and a deterministic ExecutionFeasibilityAssessment (FEASIBLE /
  LIMITED / INCONCLUSIVE / NOT_FEASIBLE). Public current mechanics only: no persistence, account
  state, Gate C, order, execution, credential or live authority; not WP172 executable edge.
  Status at EXEC-FEAS implementation time: S10-STRAT-LIFE-01: MERGED; S10-HERMES-STRAT-01: MERGED;
  S10-EXEC-FEAS-01: then the implemented review target (now MERGED in PR #212);
  S10-GATE-C-EXPLORE-01: then next after review+merge.
  ALPHA-03, DATA-03 and the Control Center (S10-CC-FOUND-01) stay parallel; DATA-03 unchanged
  and non-blocking. Capital/orders USD 0 / 0.

- Earlier merged predecessor: S10-HERMES-STRAT-01 Hermes Strategy Manager Core (PR #211 merged
  at `4519aab3d7f8424fc74c59104cc4e7afe0ff11b8`; formerly the current bounded implementation package) on
  frozen base `dab28ee45c1f8267248d52601c90d3f3509034f9` after PR #210 / S10-STRAT-LIFE-01 (merged: YES; head
  `d3c98d7530c8cec6b65e5d76492f1d7da8edf783`). It adds an additive default-off strategy mode to the existing controlled Hermes
  runtime and `strategy_manager.py`, which records canonical soft Hermes strategy decisions
  (CONTINUE / SCALE / REDUCE / ADAPT / PAPER / QUARANTINE / RETIRE) for one exact StrategyVersion
  from a verified STRAT-LIFE snapshot and bounded evidence in an append-only history store
  (`docs/hermes_strategy_manager_contract.md`). Soft judgments only: no STRAT-LIFE write,
  PortfolioAuthorityPolicy change, execution feasibility, Gate C, paper, execution, credential or
  live authority; zero real provider/model calls. Next core package after review and merge:
  S10-EXEC-FEAS-01. S10-CC-FOUND-01 is NOT AUTHORIZED / NOT STARTED until HERMES-STRAT merges.
  ALPHA-03 parallel; DATA-03 unchanged and non-blocking. Capital/orders USD 0 / 0.

- Earlier merged predecessor: S10-STRAT-LIFE-01 Strategy Lifecycle + Global
  Portfolio Authority Core (PR #210 merged at `dab28ee45c1f8267248d52601c90d3f3509034f9`; formerly the current bounded
  implementation package) on frozen base `02eeed13dc0b9552e5685f48198d060e78c797e1` after
  PR #209 / S10-DEPLOY-01 (merged: YES; head `3e9d595e014275662e90b5f22809f66b3e82cb39`).
  V2.1 target architecture: ACCEPTED (see `docs/architecture_decision_record.md`). The package
  adds only the stdlib-only `src/strategy_lifecycle/` substrate: immutable strategy
  family/version identity and lineage, mechanical bounded-vs-material adaptation
  classification, advisory evidence posture, strategy health, strategy-local restrictions,
  risk allocations, one human-authorized global PortfolioAuthorityPolicy, deterministic
  portfolio budget/capacity accounting, and an append-only hash-chained SQLite lifecycle
  store derived by verified replay (`docs/strategy_lifecycle_portfolio_authority_contract.md`).
  It wires into no existing runtime; Hermes strategy manager, ALPHA-03, execution feasibility,
  Gate C, paper, execution, credentials and live remain unimplemented/unchanged. S10-DEPLOY-01
  host activation is NOT YET PERFORMED and separately gated; DATA-03 is unchanged and
  non-blocking; ALPHA-03 is a separate parallel feeder. Capital/orders USD 0 / 0.

- Earlier merged predecessor: S10-DEPLOY-01 Research Platform Runtime Baseline (PR #209
  merged at `02eeed13dc0b9552e5685f48198d060e78c797e1`; formerly the current bounded
  implementation package) on frozen base `0b14c951c4546ebc28e0d129643da4ad4615ce2e` after PR #208 /
  S10-PAPER-RESEARCH-01. It adds only the credential-free `tools/deployment/` baseline: exact
  release build/verification, Ubuntu 24.04 x86-64 bootstrap, native systemd research/critical
  slices, once-per-minute sanitized host telemetry, persistent `/var/lib` state, SQLite-aware
  backup and isolated restore verification, SSH-only inbound firewall contract, and a frozen
  post-merge bounded public smoke. Repository implementation is authorized; provider purchase,
  provisioning, remote login and activation remain deferred to a human post-merge closure.
  DATA-03 stays on its current operator environment. This baseline may precede candidate WP172,
  but execution coexistence/hardening still follows a real WP172 PASS. No credentials, paper
  session, product scheduler, execution, Gate C, live trading, capital, or orders are authorized.

- Earlier merged predecessor: S10-PAPER-RESEARCH-01 on frozen base
  `d7166f947d764c4fbda65a7d8092d3984a37c7a7` after PR #207 / S10-DEPLOY-PLAN-01.
  WP173 now has two strictly separated admission modes: its existing qualified serious-paper path
  backed by WP172 `EXECUTABLE_EDGE_PASS`, and an additive non-qualifying research-paper learning
  tier backed by a `ResearchPaperStrategyBinding`. Both reuse the same deterministic journal,
  accounting, risk, fill, control and recovery machinery; legacy stores require no migration.
  Research-paper performance snapshots are verified-store-derived, content-addressed,
  advisory-only and carry no qualification, execution or live authority. They reuse existing
  Hermes deterministic-project-evidence and Alpha deterministic-evidence-ref semantics without
  provider calls or registry mutation. DATA-03 remains a parallel confirmatory weather lane and
  is untouched; the first-look cohort starting `2026-10-15T00:00:00Z` remains protected. This WP
  does not implement a weather strategy, candidate-specific strategy logic, ALPHA-03, Gate C,
  credentials, scheduling, execution or live trading; capital/orders 0.

- Current bounded implementation: S10-ALPHA-02 on exact base
  `a2fba4d770cd6fac1cfb551419d040d65768a8e9`; S10-WALLET-02 / PR #190,
  S10-HERMES-CTX-01, S10-WALLET-01, and S10-ALPHA-01 are COMPLETE. The package adds only
  deterministic local/offline observed-PIT-universe, material-change, temporal-posture,
  triage/skip, bounded research-allocation, capture-request-data, and append-only discovery-memory
  evidence. External all-Polymarket completeness remains UNPROVEN. It adds no product network,
  Hermes/provider call, scheduler, credential, qualification, expected-return, strategy,
  paper/live, capital, signing, order, H1 #5, or Gate-C authority. After separate review and merge,
  S10-GATE-AF1 is the current Phase-A implementation target and next mandatory gate, recertified on
  base 1ccf42df0e95586b98c79a0bf912343f9c34df31 (PR #195, S10-HERMES-CTX-03) after WP164A (PR #193) completed its runtime
  certification. AF1 Attempt-03 was consumed with TRUE_STOP / PHASE_B_LOCAL_EVIDENCE_DEFECT and no
  AF1 gate result (shared request-scanner defect repaired by PR #195); its successor AF1 Attempt-04
  ran on runtime execution head dead42658e8fc9139d82f772e1f2fff67ba07674, is CONSUMED, and finalized AF1_PASS (all ten
  dimensions PASS; receipt af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2). AF1_PASS is research-system gate success only;
  non-wallet S10-QUAL-01 is now separately eligible to be drafted/authorized, the wallet-specific
  path and ALPHA-03/HERMES-SI remain separately gated, and none is authorized; no additional AF1
  attempt is authorized. WALLET-03/WALLET-04 and ALPHA-03/ALPHA-04 retain their
  separately gated scopes.

- Historical planning predecessor: S10-DEPLOY-PLAN-01 — Production VPS Hosting Direction Lock (base
  d45d9587401faddd2ba92f33cb84f2988b6cfe70, after PR #206 / S10-QUAL-DATA-03 merged with head
  b7d77f95df093b259a2a2b809ffe20308539e397 at 2026-10-01T15:08:12Z). Docs/tests planning truth only
  (docs/production_vps_hosting_direction.md): AlphaVPS, Sofia, Bulgaria; initial tier C8G (4 vCPU / 8 GB ECC RAM /
  75 GB NVMe RAID-10); Ubuntu 24.04 LTS / x86-64; ONE_CONSOLIDATED_POLYMARKET_VPS with no default separate
  research/live VPS; upgrades C8G -> C12G -> C16G/P-series -> larger only by telemetry evidence.
  S10-DEPLOY-01 supersedes the old serial migration wording: the research baseline may be
  implemented now, while a real strategy-specific WP172 PASS remains required before later
  execution coexistence proof and serious production-hosted paper. Deployment status remains
  NOT_PROVISIONED / NOT_DEPLOYED. DATA-03
  remains on the current operator environment (not moved to the VPS); the next immediate DATA-03 runtime action
  remains the zero-network prepare, with no real accrue before 2026-10-15T00:00:00Z. This package does not
  interrupt the qualification chain and grants no purchase, provisioning, deployment, credential, scheduler, paper,
  live, Gate C or capital authority; capital/orders 0.
  Historical S10-DEPLOY-PLAN-01 compatibility wording placed deployment "after a real
  strategy-specific WP172 EXECUTABLE_EDGE_PASS exists and before the first serious
  production-hosted paper runtime using the existing WP173 system" and recorded the superseded
  serial sequence `-> real WP172 executable-edge evidence / EXECUTABLE_EDGE_PASS -> S10-DEPLOY-01
  Production VPS Runtime Baseline -> serious production-hosted WP173 paper runtime`. That quotation
  does not override the current split research-baseline and later execution-migration lanes. The
  old shorthand "after WP172 and before WP173" is superseded.

- Historical predecessor (PR #206 merged at d45d9587401faddd2ba92f33cb84f2988b6cfe70 with head
  b7d77f95df093b259a2a2b809ffe20308539e397 at 2026-10-01T15:08:12Z), formerly the bounded implementation target: S10-QUAL-DATA-03 (base 75e17927155dc7ffb5aebfba2f1d97ddd5c2f8b9,
  after PR #205 / S10-QUAL-PLAN-01 merged with head 11244eed9686b01e29ede83ea6578bb0a781db6f at 2026-10-01T02:39:26Z,
  before the freeze deadline) implements the mechanical prospective OOS accrual path and execution-terms capture frozen
  by the PLAN-01 plan without analytic change: a pure accrual module plus one manual operator (prepare, probe-sources,
  accrue, seal, verify-final) with the frozen 11/12 UTC census, pending/terminal classification, a hash-chained
  multi-run ledger, the stable chronological 50-date prefix, the one-way oosmembership seal, the closed visible-report
  firewall, MR12 execution evidence from the frozen official fee page and the N2 + 150 <= 256 provenance pre-gate.
  Code-merge state DATA03_IMPLEMENTED_NOT_STARTED; one bounded pre-OOS probe (PROBE_PASS on the Attempt 03
  full-network recovery probe; Attempts 01/02 were environment egress denials); no real accrue run before
  2026-10-15T00:00:00Z; no forecast, fit, score, candidate, gate run or WP170 object; no scheduler. After merge only
  manual bounded accrue runs; S10-QUAL-REAL-01 only after a final membership seal and the Side14 evidence/status
  closure (separately gated); WP170/WP172/WP173, Gate C and live remain NOT AUTHORIZED; capital/orders 0.

- Historical predecessor (PR #205 merged at 75e17927155dc7ffb5aebfba2f1d97ddd5c2f8b9), formerly the bounded implementation target: S10-QUAL-PLAN-01 (base e2edb21e25e7841376c3cb51c27a622fbc0cbc83,
  after PR #204 / S10-QUAL-B0X-01 merged with head debcfdf723505b67a1280ac9f303d5abd293c998) commits one
  content-addressed weather qualification analytic-plan freeze (plan SHA-256
  3b2a99abea8bbd18794c8117d6c1ab696ac817217cd5713367b2ee9a76aa9463) before genuinely prospective OOS evidence begins:
  oos_start 2026-10-15T00:00:00Z, merge deadline 2026-10-14T00:00:00Z, cap 2027-02-12T00:00:00Z; DATA-02 stays
  permanently HISTORICAL_NON_OOS; hypothesis, B0, features, label, Firth logistic model, splits, power (50 target
  dates), fixed-sequence Brier family, DATA-03 seal rules, execution-evidence meaning and WP170 handoff frozen, with
  every data-dependent candidate field a closed mechanical rule. Docs/tests only; no data, network, fit, score,
  candidate, gate run or WP170 record; WP170 remains the sole preregistration/OOS authority. S10-QUAL-DATA-03
  (prospective OOS accrual + execution-terms capture) is the next expected package only after this WP merges before
  the deadline (separately gated); S10-QUAL-REAL-01 only after 50 sealed prospective dates; WP170/WP172/WP173, Gate C
  and live remain NOT AUTHORIZED; capital/orders 0.

- Historical predecessor (PR #204 merged at e2edb21e25e7841376c3cb51c27a622fbc0cbc83), formerly the bounded implementation target: S10-QUAL-B0X-01 (base ebd6f84c95e30451fe1c9ad431e405c57c113074,
  after PR #203 / S10-QUAL-DATA-02 merged with head b9e2e6995ee232720d0516b1fa234dec8bdac5e3) answers the DATA-02
  EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION B0 status with an additive qualification-contract extension:
  one external-reconstruction B0 rule EXTERNAL_PIT_MARKET_PROBABILITY_V1 and one feature source class
  MARKET_EXTERNAL_RECONSTRUCTION with rule-specific B2 coupling; canonical PIT_MARKET_PROBABILITY_V1 / MARKET_PIT,
  schema 1.0.0 and canonical candidate ids unchanged; external evidence is never relabelled canonical PIT, never
  backdated and never a DatasetSnapshotReference. No network, data, real candidate or gate run; the qualification
  gate and WP170 are unchanged. S10-QUAL-REAL-01 is the next expected package only after this WP merges
  (separately gated); WP170/WP172/WP173, Gate C and live remain NOT AUTHORIZED; capital/orders 0.

- Historical predecessor (PR #203 merged at ebd6f84c95e30451fe1c9ad431e405c57c113074), formerly the bounded implementation target: S10-QUAL-DATA-02 (base 6f67bac990d8ab338f1b87140ae077e9df4172dd,
  after PR #202 / S10-QUAL-DATA-01 merged with head 33c031f41626550294eb6667620b4ce75589d719) completes the frozen
  S10-QUAL-DATA-01 weather qualification corpus in one bounded run seeded from the verified PR #202 run-01 raw
  artifacts (cache only; whole corpus re-derived), with the D011 failed-read rules, a frozen 429/503 backoff and
  bounded new-network caps; dates, checkpoints, windows and policies unchanged; terminal QUAL_DATA_READY or
  QUAL_DATA_INSUFFICIENT. The single completion run terminated QUAL_DATA_READY (783 evidence-complete rows over
  32 target dates; budget not exhausted; verify-final VERIFIED). Data formation only: B0 compatibility stays
  EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION; no QualificationCandidate, no qualification gate run; the
  B0 compatibility package or any rerun is separately gated; WP170/WP172/WP173, Gate C and live remain NOT
  AUTHORIZED; capital/orders 0.

- Historical predecessor (PR #202 merged at 6f67bac990d8ab338f1b87140ae077e9df4172dd), formerly the bounded implementation target: S10-QUAL-DATA-01 (base 77738717fee422fe83d8bb2b7765c36dfbe6b283,
  after PR #201 / S10-NDFD-GRIB-01 merged with head cd70800d40f60f4ec20f5b17e107cc56643562a2) forms one bounded,
  content-addressed weather qualification-data readiness corpus for the PR #200 RESEARCH_SUPPORTIVE daily-rain
  lineage (PendulumFlow v3 external market history, official NDFD PoP12 vintages, Gamma/NWS rules and labels,
  two fixed checkpoints, factual counts and execution facts) with terminal QUAL_DATA_READY or
  QUAL_DATA_INSUFFICIENT. After the Side14 same-WP correction (D008/D009), the authoritative replacement run
  terminated QUAL_DATA_INSUFFICIENT (frozen byte budget exhausted; 212 evidence-complete rows over 12 target
  dates; verify-final VERIFIED); the superseded QUAL_DATA_READY run is retained as defect evidence.
  Data formation only: PendulumFlow is never canonical PIT (B0 compatibility
  EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION); no QualificationCandidate, no qualification gate run;
  S10-QUAL-REAL-01 or a B0 compatibility decision is separately gated; WP170/WP172/WP173, Gate C and live remain
  NOT AUTHORIZED; capital/orders 0.

- Historical predecessor (PR #201 merged at 77738717fee422fe83d8bb2b7765c36dfbe6b283), formerly the bounded implementation target: S10-NDFD-GRIB-01 (base 3d3e3b673e53dae4d2e3b28a6816264b205bb015,
  after PR #200 / S10-ALPHA-REAL-01 merged with head 80faf1dcb32d760a15c5de3c008cd2aefa3a6f12) enables
  optional offline NDFD GRIB2 decoding only: the exact optional extra ndfd-grib (eccodes==2.48.0;
  eccodeslib==2.48.0.26 on non-Windows), proven on ubuntu-24.04 / windows-2022 Python 3.12 against one
  committed official NDFD PoP12 fixture. It resolves only the S10-QUAL-DATA-01 NDFD_DEPENDENCY_REQUIRED
  decoder blocker; global Python support remains 3.12-3.14. S10-QUAL-DATA-01 may be redrafted/resumed
  next and remains unimplemented; no QualificationCandidate or real gate receipt exists; WP170/WP172/WP173,
  Gate C and live remain NOT AUTHORIZED; capital/orders 0.

- Historical predecessor (PR #200 merged at 3d3e3b673e53dae4d2e3b28a6816264b205bb015), formerly the bounded implementation target: S10-ALPHA-REAL-01 (base f74e183a514d21a28013bf433c79126a68c72389,
  after PR #199 / S10-TEST-WS-01 merged with head 99c300421f3404a68b573674d1d6d09e8c363412) implements the
  Phase-A manual operator for the first real NON-WALLET Alpha evidence seed (frozen NWS-resolved Polymarket
  daily-rain research program): at most one controlled Hermes research-child launch after Karl's separate
  runtime activation, tool-side full-draft revalidation, one Side13 result-state decision and one canonical
  Alpha source/candidate/family/episode lineage. Runtime attempt-01 ran exactly once and is CONSUMED:
  RUN_VALIDATED, Side13 decision RESEARCH_SUPPORTIVE, final terminal ALPHA_REAL_01_SUPPORTIVE (episode
  alphaepisode:sha256:2e4c0f484649930ba2677bc360070f0e9ba6ef0e09ecd23b383a32ff3b69000c; registry head
  alpharegistryentry:sha256:4b9a20f7f0e931dfea7cced80a64d7a4be7ccc58e265dbb9ebde15edb2d79847). That verified
  unique current RESEARCH_SUPPORTIVE leaf makes S10-QUAL-REAL-01 (first real NON-WALLET
  QualificationCandidate build + S10-GATE-QUAL-01 evaluation) DRAFT-ELIGIBLE only; qualification/data
  readiness is NOT proven and remains that successor's evidence-readiness work. S10-QUAL-REAL-01, WP170,
  H1 #5 and Gate C are NOT AUTHORIZED; capital/orders 0.

- Historical predecessor (PR #198 merged at d7891ed63b4c58c9cc150cd0c750c262ca8e5a74), formerly the bounded implementation target: S10-GATE-QUAL-01 (base b5cfb9846ff78af2d1a260843d5f2f1a67639305,
  after PR #197 / S10-QUAL-01 merged with head 652a2181926ac6f92f72d0013af99ec5e24ba892) implements the
  deterministic qualification packet acceptance gate only: eight closed dimensions and
  QUAL_PASS / QUAL_FAIL / QUAL_INCONCLUSIVE over an existing NON-WALLET QualificationCandidate, with
  structural rejections kept separate from substantive dispositions. No real candidate is evaluated and
  no real gate receipt is persisted. Next and separately gated: a real NON-WALLET candidate evaluation
  with the merged gate; only a real QUAL_PASS makes candidate-specific WP170 work eligible to be drafted,
  then WP172 / WP173. First real evaluation, WP170, H1 #5 and Gate C are NOT AUTHORIZED; capital/orders 0.

- Historical predecessor (PR #197 merged at b5cfb9846ff78af2d1a260843d5f2f1a67639305), formerly the bounded implementation target: S10-QUAL-01 (base 3b877a01ed797d26fddf81a8936c880692573028,
  after PR #196 / S10-GATE-AF1) implements the deterministic NON-WALLET QualificationCandidate
  substrate only. It produces NO qualification PASS/FAIL/INCONCLUSIVE decision, qualifies no real
  candidate, keeps WP170 as the preregistration/OOS authority (feature/model implementation remains
  WP170) and fails wallet-dependent packets with WALLET_GATE_REQUIRED. Next and separately gated:
  S10-GATE-QUAL-01, then separately gated WP170 candidate work, then WP172 / WP173. S10-GATE-QUAL-01,
  H1 #5 and Gate C are NOT AUTHORIZED; capital/orders 0.

- WP: WP52 (merged; merge commit 259fac091a3b8d0d22aaab13345f440d5a958af2); WP55 (resolution ambiguity taxonomy/manual-label workflow merged); WP56 (label schema validation merged; merge commit a310e641eb790bd3906d054d703dd11945180e6c); WP57 (local/offline/read-only feature extraction from validated labels merged); WP60A (agent-neutral startup layer merged); WP61 (architecture direction lock-in and microstructure quality metadata merged); WP62 (cross-market relationship metadata merged); WP63 (resolution source hierarchy metadata merged; merge commit e1ab1aa7e0915a3c65afc9eb5a55c58292ef6910); WP64 (research queue/report/session packet merged; merge commit 7795efd45b19ab89c943bd49602449baa67411db); WP65 (local research queue export/operator runbook merged; merge commit 5c5b0c7ef8a2d1f094a2eff6dabbe6fd4be434f7); WP75 (human review label fixture loader merged; PR #76 merge commit 0160ac1c7087625a4596edd541524445bc004bd5); WP76 (wallet intelligence roadmap lock-in merged; PR #77 merge commit 91cd26e4fe16d492fa2f7b319fba176ee60cd9d5); WP77 (wallet intelligence architecture/profile/signal contract merged; PR #78 merge commit 24badbfb7a9da06ee4c8ae94795e1f2c862af913); WP78 (wallet trade event snapshot schema/local loader/validator on branch)
- Package class: DOCS_ONLY_ROADMAP_MERGED; RESOLUTION_AMBIGUITY_TAXONOMY_MERGED; RESOLUTION_AMBIGUITY_LABEL_SCHEMA_VALIDATION_MERGED; RESOLUTION_AMBIGUITY_LABEL_FEATURE_EXTRACTION_MERGED; ARCHITECTURE_DIRECTION_MERGED; LOCAL_OFFLINE_READ_ONLY_MICROSTRUCTURE_QUALITY_MERGED; LOCAL_OFFLINE_READ_ONLY_CROSS_MARKET_RELATIONSHIP_METADATA_MERGED; LOCAL_OFFLINE_READ_ONLY_RESOLUTION_SOURCE_HIERARCHY_MERGED; LOCAL_OFFLINE_READ_ONLY_RESEARCH_QUEUE_REPORT_SESSION_PACKET_MERGED; LOCAL_OFFLINE_READ_ONLY_RESEARCH_QUEUE_EXPORT_OPERATOR_RUNBOOK_MERGED; HUMAN_REVIEW_LABEL_FIXTURE_LOADER_MERGED; DOCS_TESTS_ONLY_WALLET_INTELLIGENCE_ROADMAP_LOCKIN_MERGED; DOCS_SCHEMA_TESTS_ONLY_WALLET_INTELLIGENCE_CONTRACT_MERGED; LOCAL_OFFLINE_READ_ONLY_WALLET_TRADE_EVENT_FIXTURE_LOADER_ON_BRANCH
- Side onboarding lock: SIDE4_ONBOARDING_LOCK_MERGED
- Authority: PLANNING_GUIDANCE_ONLY
- NOT_AUTHORIZATION
- NO_RUNTIME_CHANGE
- NO_SOURCE_CHANGE
- NO_TOOLS_CHANGE
- NO_DEPENDENCY_CHANGE
- NO_NETWORK
- NO_TRADING_EXECUTION
- NO_PAPER_TRADING
- NO_HERMES_RUNTIME
- NO_AGENT_RUNTIME
- NO_CREDENTIALS
- NO_SCHEDULER
- NO_BOT_LOOP
- WP51 merge commit: c57b9c0adcc044f8bd9ed01a6368f2fafdbe222f
- WP53 merge commit: 7514b1aded39c5f1ca0c5abae4fdae86b6c4f1d6
- WP54 merge commit: fb45fb849b0641e2007ef66f50bfd5725354b8f0
- WP76 merge commit: 91cd26e4fe16d492fa2f7b319fba176ee60cd9d5
- WP77 merge commit: 24badbfb7a9da06ee4c8ae94795e1f2c862af913

## B. Purpose

This document locks the long-term bot-completion roadmap into repo truth for
future Side chats, Claude Code/Codex sessions, and reviewers.

It explains what is already built, what is missing, and how many WP phases
remain before this project becomes a real paper-trading or live-trading bot.

**This is planning guidance only.** It does not approve any future implementation,
paper trading, live trading, execution, credentials, scheduler, bot loop,
Hermes/agent runtime, wallet-copying, or autonomous agent runtime. Each future
phase requires its own explicitly approved work package.

## C. Current Simple-State Summary

The project currently has blueprints, safety rules, a core scorer, a direction
lock, and the first feature-extraction foundation.

It does not yet have a finished trading bot. It cannot yet decide trades,
simulate realistic fills, place orders, manage live risk, or run autonomously.

**Self-driving-car analogy:** We have the garage rules, the safety checklist,
and the first engine block. The sensors, navigation system, test track, brakes,
steering wheel, dashboard, and road permission are not yet fully built.

More precisely:
- Garage rules and safety checklist → repo governance, protected boundaries,
  Codex workflow discipline
- First engine block → WP49 core scorer + WP51 feature extraction foundation
- Sensors → feature extraction for microstructure, resolution ambiguity,
  calibration data
- Navigation → research strategy layer, hypothesis engine
- Test track → paper-trading engine
- Brakes → risk engine and kill switches
- Steering wheel → live execution gateway
- Dashboard → operational monitoring, reporting, deployment
- Road permission → authenticated client, credentials, live-trading
  authorization

## D. Current Repo-Built Components

The following capabilities are built and merged into repo truth as of WP52:

1. **Repo-truth governance** — AGENTS.md, CODEX_START_HERE.md, authority
   hierarchy, protected-boundary rules, Codex execution guidelines, WP
   template, review checklist, testing requirements.

2. **Codex/PR evidence discipline** — PR evidence reporting discipline
   (WP45), PR evidence consistency guard (WP46), posted PR evidence review
   hardening (WP47), validation matrix, PR review checklist.

3. **Local/offline/read-only snapshot and data layer** — Polymarket public
   endpoint adapter, snapshot capture (WP10/WP18), snapshot reader, market
   catalog (WP11), snapshot quality gates (WP12/WP19), deduplication and
   catalog exports (WP13), read-only polling runner (WP17).

4. **Local artifact quality/reporting basis** — Local reports (WP12/WP19),
   quality gate framework, sanitized catalog export layer.

5. **Advisory read-only/Hermes boundary docs** — AI-agent integration
   policy (WP20), Hermes read-only boundary (WP20), agent model registry
   (WP20), agent context export schema (WP21), advisory runtime boundary
   design (WP39), agent/Hermes manual setup decision record (WP27).

6. **Local advisory consumer/reporting pieces** — Local read-only agent
   context exporter (WP23), analyst report generator (WP25), local advisory
   consumer prototype (WP40), advisory prompt/runbook package (WP41),
   advisory consumer operator workflow (WP42), token-efficiency helper stack
   (WP28-WP37).

7. **Market Research Priority Scoring design** — Docs-only scoring layer
   design (WP44).

8. **Output contract** — Binding schema/output contract (WP48) defining
   top-level fields, score components, advisory-only labels,
   staleness/provenance/missing-data contracts, and forbidden fields.

9. **Core scorer** — Local/offline/read-only core scorer (WP49):
   `src/data_layer/market_research_priority_scoring.py`, stdlib-only,
   in-memory output only, advisory-only.

10. **Feature extraction foundation** — Local/offline/read-only first feature
    extraction module (WP51):
    `src/data_layer/market_research_priority_features.py`, bridges snapshot
    artifacts into prepared scorer inputs.

11. **Research data foundation direction lock** — Locked direction document
    (WP50), approved near-term sequence, blocked directions, non-signal
    semantics.

12. **Resolution ambiguity taxonomy and manual-label workflow** — Docs/schema/tests-only
    taxonomy document (WP55) on branch: 14 ambiguity categories, review status values,
    severity/confidence separation, 17-field manual label schema, local/offline/read-only
    human review workflow. Research-data-quality metadata only; no parser, no feature
    extraction, no scorer integration in WP55.

13. **Architecture direction lock-in** — WP61 adds
    `docs/architecture_decision_record.md` with planning constraints only:
    SQLite first/Postgres later if needed; Streamlit first/Grafana later/Next.js
    only if productizing; local development first/cheap VPS later; rules-based
    plus research-score-driven first; LLM read-only analyst/proposal layer only;
    research-only -> paper -> dry-run -> manual live approval -> restricted live.
    Superseded by V2.1 (historical context only): the LLM read-only-only assumption and
    the universal manual-live-approval ladder are superseded as future target
    architecture by the accepted V2.1 architecture (global PortfolioAuthorityPolicy,
    later Hermes strategy judgment inside it).
    Its "cheap VPS later" hosting shorthand is historical context only, superseded
    by the S10-DEPLOY-PLAN-01 production VPS hosting direction
    (`docs/production_vps_hosting_direction.md`).

14. **Microstructure Quality V1 metadata** — WP61 adds advisory-only
    `microstructure_quality` metadata to prepared market contexts from local
    order-book snapshots only. It is not a score component and does not change
    scorer weights.

15. **Protected boundaries** — Live trading DISABLED; credentials NOT_USED;
    execution NOT_STARTED; authenticated client FORBIDDEN_UNTIL_APPROVED_WP;
    Hermes NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY; agent runtime NOT_STARTED;
    agent execution authority FORBIDDEN; fully autonomous trading agent
    EXCLUDED_FOR_NOW; scheduler NOT_STARTED; bot loop NOT_STARTED.

16. **Wallet intelligence roadmap, contract, and fixture loader** — WP76 locks top-wallet
    intelligence as a future advisory research signal layer, not a blind
    copy-trading engine. WP77 adds docs/schema/tests-only architecture,
    watched-wallet profile, registry status, signal contract, copyability status,
    suspicious-flow, and safety-flag design. WP78 adds only local/offline
    wallet trade event fixture schema, validator, and explicit-path loader.
    No wallet API client, real wallet monitoring, automatic copy-trading,
    paper/live trading, credentials, or execution behavior is authorized.

## E. Missing Major Capabilities

The following major capabilities are not yet complete as of WP52. Each
requires one or more explicitly approved future work packages.

- Robust scanner and refresh pipeline for scoring outputs
- Resolution-rule ambiguity feature extraction and automated parser (taxonomy and
  manual-label workflow defined in WP55; automated extraction and parser remain not started)
- Microstructure quality features beyond basic order-book availability
- Local scoring export and report integration (CLI/export/report writer)
- Calibration and resolved-outcome validation harness
- Research strategy layer (hypothesis engine, market-selection logic)
- Paper-trading engine (realistic fill simulation, P&L tracking)
- Risk engine and kill switches (position limits, drawdown gates, emergency
  stops)
- Authenticated client boundary, credentials handling, wallet/signing
  infrastructure
- Live execution gateway (order placement, cancellation, order management)
- Scheduler and bot loop (recurring jobs, health monitoring)
- Operational monitoring, dashboard, and deployment infrastructure

## F. Milestones

These are rough planning ranges, not commitments. Repo truth, implementation
discoveries, and future user decisions may change these estimates.

All ranges are measured from the WP51/WP52 baseline.

| Milestone | Description | Estimated WPs from baseline |
|---|---|---|
| Research Intelligence Bot | A bot that can score, rank, and report market research priorities for human review, with honest data quality signals. Not a trading bot. | 15-25 WPs |
| Paper Trading Bot | A bot that can simulate paper trades with realistic fill assumptions and track simulated P&L, without real orders. | 45-75 WPs |
| Controlled Live Bot | A live bot that can place and cancel real orders in a controlled scope, with human-review gates and kill switches. | 75-110 WPs |
| Robust Autonomous-ish Bot | A bot that can run with reduced human review for defined market categories, with strong risk controls and monitoring. | 100-160 WPs |

Earlier aggressive or minimal estimates are not authorization to skip gates.

## G. Phase Roadmap

Each phase below has a short layman explanation and an analogy. WP ranges are
rough planning estimates from the WP51/WP52 baseline, not commitments.

### Phase 1: Data Foundation and Feature Extraction

**What:** Build all the sensor inputs the bot needs to evaluate markets —
staleness tracking, resolution rule signals, microstructure quality,
provenance enforcement.

**Analogy:** Give the bot eyes.

**Estimated range:** 6-10 WPs

Includes: provenance/staleness hardening, resolution-rule ambiguity taxonomy
and extraction, microstructure quality features, CLI/export/report writer for
local scoring integration.

### Phase 2: Market Understanding, Resolution, and Graphing

**What:** Teach the bot the rules of each market — how markets resolve, which
markets are related, and how to reason about ambiguous resolution.

**Analogy:** Teach the bot the rules of the game.

**Estimated range:** 10-16 WPs

Includes: resolution-rule taxonomy, manual label workflow, basic resolution
metadata extraction, metadata-only cross-market relationship graph.

### Phase 3: Microstructure and Liquidity Quality

**What:** Check the microstructure quality indicators of each market — spread,
depth, slippage. These are data-quality inputs, not trade-readiness signals.

**Analogy:** Check whether the road is drivable.

**Estimated range:** 8-14 WPs

Includes: spread bps, depth buckets, slippage estimates as microstructure
quality indicators and execution realism inputs for later approved simulation
work only. Not tradability. Not execution confidence. No fill-probability
implementation is approved by this roadmap. No trade-readiness signal.

### Phase 4: Scoring Output, Reporting, and Human Workflow

**What:** Build the dashboard-like output that lets a human researcher
understand, trust, and act on the scoring layer before any automation is
added.

**Analogy:** Build the dashboard before adding autopilot.

**Estimated range:** 7-12 WPs

Includes: CLI/export integration, local report generation, advisory consumer
integration, human-review workflow, staleness and quality summaries.

### Phase 5: Calibration and Validation

**What:** Check whether the compass points north — verify that the scoring
layer's outputs correlate with historical reality using resolved outcomes.

**Analogy:** Check whether the compass points north.

**Estimated range:** 8-15 WPs

Includes: resolved-outcome dataset validation, calibration harness design,
score-to-outcome correlation analysis, re-calibration workflow.

### Phase 6: Research Strategy Layer

**What:** Teach the bot how to think about market selection, but not how to
act — build the hypothesis generation and research priority logic.

**Analogy:** Teach the bot how to think, but not act.

**Estimated range:** 8-14 WPs

Includes: research hypothesis engine, market-selection logic, strategy
research framing, advisory-only output with no execution authority.

### Phase 7: Paper Trading

**What:** Run the bot on a flight simulator before flying the real plane —
simulate trades with realistic fill assumptions and track simulated P&L.

**Analogy:** Flight simulator before flying.

**Estimated range:** 12-20 WPs

Includes: paper-trading engine, realistic fill simulation, simulated P&L
tracking, paper-trading safety gates, no real orders.

### Phase 8: Risk Engine and Kill Switches

**What:** Build the brakes — position limits, drawdown gates, emergency stops,
kill switches, and risk controls required before any live order is placed.

**Analogy:** Build the brakes.

**Estimated range:** 10-16 WPs

Includes: position limit guards, drawdown gates, emergency stop logic, kill
switch design, risk engine design, safety gate enforcement.

### Phase 9: Live Execution

**What:** Connect the steering wheel to the real car — build the execution
gateway that places and cancels real orders, with authenticated credentials
and signing.

**Analogy:** Connect the steering wheel to the real car.

**Estimated range:** 14-25 WPs

Includes: authenticated client integration, credentials handling,
order placement and cancellation, order management system, execution boundary
review, live-trading authorization.

### Phase 10: Scheduler, Bot Loop, Monitoring, and Operations

**What:** Let it run without falling asleep — add scheduling, health
monitoring, operational dashboards, alerting, and deployment infrastructure.

**Analogy:** Let it run without falling asleep.

**Estimated range:** 10-18 WPs

Includes: scheduler design, bot loop, health monitoring, alerting,
operational dashboard, deployment infrastructure, incident response.

Hosting direction (S10-DEPLOY-PLAN-01, planning only): deployment infrastructure
targets ONE consolidated AlphaVPS C8G host in Sofia, Bulgaria, through the
separately gated S10-DEPLOY-01 Production VPS Runtime Baseline package at the
migration point recorded in `docs/production_vps_hosting_direction.md`.

## H. Total Estimate

| Scope | Estimated WPs from WP51/WP52 baseline |
|---|---|
| Research-only useful bot | 15-25 WPs |
| Paper-trading bot | 45-75 WPs |
| Basic controlled live bot | 75-110 WPs |
| Robust live/autonomous-ish bot | 100-160 WPs |
| **Full serious completion range** | **93-160 WPs** |

These are rough planning ranges. Earlier aggressive or minimal estimates are
not authorization to skip gates.

## I. What Is Not Approved By This Roadmap

This roadmap document does not approve any of the following. Each item
requires its own explicitly approved work package before any implementation
begins:

- Strategy implementation
- Paper trading
- Live trading
- Execution
- Credentials
- Authenticated client
- Wallet and signing
- Order placement
- Scheduler
- Bot loop
- Dashboard, database, or deployment
- Hermes runtime or agent runtime
- Autonomous agent
- Wallet-copying
- Wallet intelligence implementation beyond advisory docs/schema/tests
- Individual wallet ranking
- LLM rule parsing
- Semantic cross-market matching
- Official-source live monitoring
- Any other item not listed as a current repo-built component in Section D

Planning-only documents do not grant implementation authority.

## J. Side 4.0 Onboarding Summary

This section exists to give a new Side 4.0 chat (or future session) the
minimum context needed to continue work safely without relying on stale chat
memory.

### Onboarding Steps

1. **Read repo truth first, not chat memory.** Chat memory may be stale.
   Repo truth is authoritative.

2. **Start with these documents in order:**
   - `docs/project_status.md` — current phase, branch, merged WPs
   - `docs/repo_truth_index.md` — full authority hierarchy
   - `docs/research_data_foundation_direction.md` — locked near-term
     research-data direction
   - `docs/long_term_bot_completion_roadmap.md` — this document
   - `docs/market_research_priority_scoring_layer.md` — scoring layer design
   - `docs/market_research_priority_scoring_output_contract.md` — binding
     output contract
   - `docs/deferred_items_log.md` — all open deferred items

3. **Confirm current main and latest merged PR through GitHub before drafting
   or reviewing.** Run the Remote Main Sync Gate:
   `python tools/git/preflight_sync_main.py --required-commit <LATEST_MERGE_SHA>`

4. **Continue Side 3.0 role and workflow, not start a new project.**
   Side 4.0 should pick up where Side 3.0 left off using the same
   repo-truth-first discipline, one WP at a time, no skipped gates.

5. **Safe next path after WP52 merge:** The immediate next path is
   provenance/staleness/missing-data enforcement hardening, only if
   explicitly approved by the user after WP52 is merged. Alternatively,
   resolution-rule ambiguity taxonomy, microstructure quality feature
   extraction, or another repo-truth-safe WP — each requiring explicit
   approval.

6. **Do not move to strategy, paper/live trading, execution, credentials,
   scheduler/bot loop, wallet-copying, Hermes runtime, or autonomous agent
   runtime** without explicit future WPs. The long-term roadmap in this
   document describes the path but does not authorize it.

### What Side 3.0 Left For Side 4.0

- WP52 adds this roadmap and Side 4.0 onboarding lock.
- WP51 is merged: local/offline/read-only feature extraction foundation at
  `src/data_layer/market_research_priority_features.py`.
- WP49 is merged: local/offline/read-only core scorer at
  `src/data_layer/market_research_priority_scoring.py`.
- Protected boundaries remain unchanged.
- Open deferred items: WP49-D002, WP49-D003, WP50-D001, WP51-D001,
  WP51-D002, WP51-D003, WP51-D004. See `docs/deferred_items_log.md`.

## K. Review Checklist For Future WPs

Use this checklist before marking any future WP as ready for review:

- [ ] Does the WP preserve local/offline/read-only boundaries?
- [ ] Does it accidentally turn the research-priority score into a trade
      signal?
- [ ] Does it add any network or runtime behavior?
- [ ] Does it require credentials, authenticated clients, or signing?
- [ ] Does it require strategy, paper-trading, live-trading, risk, or
      execution approval (none of these are approved by WP52)?
- [ ] Does it change dependency or lock files?
- [ ] Does it correctly update `docs/project_status.md`,
      `docs/repo_truth_index.md`, and `docs/deferred_items_log.md`?
- [ ] Does it pass the PR evidence consistency guard with all WP47 hardening
      flags?
- [ ] If an optional post-WP91 final PR comment is posted, is it explicitly
      non-canonical and consistent with the canonical PR body?

## L. Post-WP169 Successor Sequence (WP170 -> WP176)

This section is PLANNING_GUIDANCE_ONLY and NOT_AUTHORIZATION; it does not approve
any successor. WP169 is merged via PR #170 at merge commit
`17df81001171988e9ca49f92dc8fd170ecaa7103`. WP173 updates this durable roadmap
to the current merged/review sequence:

- WP169 — Market Truth / Realtime Data Plane (merged).
- WP170 — Falsification-Grade Experiment Registry & Research Dataset OS (merged).
- WP171 — Interactive Operator Cockpit (merged).
- WP171G — Lean Agent Execution Governance transition (merged).
- WP172 — Alpha + Executable Edge MVP (merged via PR #174; final head
  `39363e5a081b6737104260725b1b0c8fcffe9196`; merge commit
  `418bae72f24b0694eccc657ed5dc3f90a3f38f2a`).
- WP173 — Serious Paper Trading System + Paper Cockpit (current review target).
  Superseded status (S10-DEPLOY-PLAN-01): the "current review target" label above is the
  historical snapshot from when this section was written; WP173 has since merged via PR #175
  (final implementation head `79e2953dee8754dc8d09781edd647202dee834aa`; merge commit
  `e0202750c1e6f2a3a885aa6efa04bbd8d0b2291a`) and adds no OS scheduler/service, daemon or
  deployment authority.
- WP174 — Auth / Signing / Execution Gateway.
- WP175 — Restricted Live Canary (merged dormant via PR #178; first live activation
  blocked by `LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE`).
- WP175D — External Historical Research Bridge (Side10 S10-DATA-02): the root-cause
  prerequisite/unblocker between merged dormant WP175 and the genuine strategy evidence
  its first live canary needs. It lets validated PMXT v2 external history enter the
  WP170 experiment OS with preserved external provenance (never canonical PIT), and is
  followed by the separately gated S10-EVID-01 evidence-production gate. It does not
  rename, implement, or authorize canonical WP176.
- S10-EVID-01B — genuine PMXT evidence run (completed `EVIDENCE_INCONCLUSIVE`):
  the external bridge worked, but the tested candidate missed first-look OOS
  criteria and PMXT `AS_CAPTURED` remained correctly continuity-incomplete.
- WP175E — Native Continuity-Attested Market Truth Bridge (Side10 S10-DATA-03):
  additive bounded WP169 accepted-WS/session/gap evidence reads plus a
  store-derived native continuity attestation and parallel WP172 market-truth
  window. It preserves the PMXT path and WP173 paper semantics, performs no
  strategy search or evidence rerun, claims no generic PIT-to-Nautilus adapter,
  and does not authorize Gate C or WP176. After merge, its successor is a
  separately gated prospective evidence run that preregisters a fresh candidate
  before forward OOS/native capture; it is not automatic live activation.
- WP176 — Mature Controlled Live.

Hermes/alpha automation may proceed later as a separately authorized parallel
track during paper soak. It is not a gate for WP173 paper operation or for this
successor numbering.

Old Streamlit-first and pre-WP171G numbering is superseded at roadmap level.
The former WP177 restricted-live and WP178 mature-live labels are historical aliases,
superseded by WP175 and WP176 respectively; they carry no current authorization.
Each unmerged successor remains separately gated and requires its governance-track
readiness, independent Side review, and explicit user authorization. WP173 grants
no authority to start WP174.

WP175H — Controlled Hermes Research Runtime Core (Side10 S10-HERMES-01) adds the
first repo-owned, dormant-by-default deterministic control plane around one bounded,
one-shot, web-only EXTERNAL Hermes research session pinned to Hermes Agent v0.21.3.
It is CODE COMPLETE but RUNTIME ACTIVATED: NO, with zero real provider/model calls
and no trading, paper, execution, live, credential, scheduler, or merge authority.
The first real provider-backed / public-web run is separately gated as S10-GATE-H1
Controlled Public Research Pilot; a successful pilot leads to S10-ALPHA-01
Multi-Lane Alpha Factory Core. Both are separately gated and NOT STARTED and gain no
trading authority; WP175 remains merged dormant, Gate C is NOT AUTHORIZED, and
WP176 Mature Controlled Live is NOT STARTED.

## WP175N / S10-ALPHA-01 Alpha Factory Core And Post-H1 Sequence (current, PLANNING_GUIDANCE_ONLY)

This section is PLANNING_GUIDANCE_ONLY / NOT_AUTHORIZATION; it does not approve any run,
merge, or Gate-C activation. It records the current post-H1 sequencing truth after
`GENUINE_H1_PASS`.

- Genuine H1 basis: S10-GATE-H1 is `GENUINE_H1_PASS`; accepted H1 is H1 #4; historical real
  H1 research invocations consumed = 4 (H1 #1, H1 #2, H1 #3, H1 #4, each separately
  human-authorized); H1 #5 is NOT AUTHORIZED. HAP-03: configured Firecrawl-only web backend
  with web_search/web_extract persisted, but remote Firecrawl HTTP is not independently
  proven (pinned v0.21.3 exposes no downstream backend HTTP telemetry). HAP-04: four
  separately authorized invocations with no automatic controller rerun or provider/model/
  backend substitution.
- Optimization hierarchy: cost per useful research observation -> cost per
  novel/falsifiable hypothesis -> cost per qualified candidate -> cost per durable realized
  edge.
- Current decomposed sequence: GENUINE H1 PASS -> S10-ALPHA-01 -> S10-WALLET-01 ->
  S10-HERMES-CTX-01 -> S10-WALLET-02 -> S10-ALPHA-02 -> S10-GATE-AF1. After GATE-AF1,
  non-wallet hypotheses flow to S10-QUAL-01 -> S10-GATE-QUAL-01 -> WP170 -> WP172 -> WP173 ->
  the existing restricted-live path; wallet-dependent hypotheses flow to S10-WALLET-03 ->
  S10-WALLET-04 -> S10-GATE-WALLET-01 -> a wallet-specific evidence lane inside S10-QUAL-01
  -> S10-GATE-QUAL-01 -> the SAME WP170/WP172/WP173 path.
- Wallet-intelligence track persists as a first-class capability: WALLET-01, WALLET-02,
  WALLET-03, WALLET-04, and GATE-WALLET-01. S10-GATE-WALLET-01 is CONDITIONAL and is not a
  global qualification blocker; there is no wallet live shortcut.
- Immediate software successor after WP175N merge is S10-WALLET-01, then S10-HERMES-CTX-01.
  WP175N does not start WALLET-01.
- S10-ALPHA-02 owns universe triage, freshness, material-change detection, automatic reopen,
  and prioritization; S10-ALPHA-03 owns scheduler/budgets/campaign autonomy; S10-ALPHA-04
  owns downstream outcome learning. None are in WP175N.
- S10-HERMES-SI-01 / S10-GATE-HSI-01 (research-layer self-improvement) unlock on sufficient
  accepted AF1 benchmark material, NOT on full live completion, and may run in parallel with
  wallet proof, qualification, WP170, WP172, WP173, and later live progression; they gain no
  deterministic/economic/execution/risk/credential/capital/Gate-C authority.
- The old monolithic WP180/WP181 Hermes/Alpha sequencing is SUPERSEDED by this Alpha core
  contract and current roadmap. WP176 remains decomposed into WP176A-E for mature
  deterministic live capability. Gate C remains human-only and NOT AUTHORIZED.

- S10-WALLET-01 (Public Wallet / Point-in-Time Wallet Evidence Foundation) delivers the
  deterministic, replayable, point-in-time-safe PUBLIC wallet evidence substrate: shared
  research provenance/PIT/DQ/replay core, the wallet_intelligence contracts/reconciliation/
  ledger/ingest package, and bounded public Data API v2 wallet GET reads (default off). It is
  evidence-only and creates no qualification, ranking, copyability, order, signing, paper, live,
  scheduler, Hermes, WP170, or Gate-C authority. Later S10-WALLET-02/03/04, S10-GATE-WALLET-01,
  QUAL-01, and WP170 own real profiling, copyability, incrementality, the wallet gate,
  qualification, and preregistered/OOS experiments. Immediate separately gated successor:
  S10-HERMES-CTX-01. Gate C remains human-only and NOT AUTHORIZED.

## S10-DEPLOY-01 Research Platform Runtime Baseline (merged implementation; host activation separately gated)

The implementation contract is `docs/research_platform_runtime_baseline_contract.md`; the hosting
direction is `docs/production_vps_hosting_direction.md`. Repository implementation authority is
limited to the exact package. Host status remains NOT_PROVISIONED / NOT_DEPLOYED.
PR #209 merged this repository implementation at `02eeed13dc0b9552e5685f48198d060e78c797e1`
(head `3e9d595e014275662e90b5f22809f66b3e82cb39`); host activation is NOT YET PERFORMED and
remains a separately gated human operator closure.

- Hosting target: AlphaVPS, Sofia, Bulgaria; initial tier C8G (4 vCPU / 8 GB ECC RAM / 75 GB
  NVMe RAID-10); Ubuntu 24.04 LTS / x86-64.
- Architecture: ONE_CONSOLIDATED_POLYMARKET_VPS. A second VPS needs a future explicit decision
  supported by evidence that same-host isolation is insufficient.
- Research sequence: S10-PAPER-RESEARCH-01 -> S10-DEPLOY-01 research baseline -> later separately
  authorized research services. This lane does not wait for DATA-03 or candidate-specific WP172.
- Promotion sequence: candidate qualification -> WP170 -> real WP172 PASS -> later execution
  coexistence/hardening proof -> serious production-hosted WP173 paper -> separately authorized
  auth/signing/live gates.
- Mechanism: credential-free exact release + Python venv + persistent `/var/lib/polymarket` +
  native systemd. The research slice is bounded; the critical slice reserves future capacity;
  telemetry is the only recurring scheduler. No product daemon is installed.
- Capacity output is research-only: C8G_RESEARCH_BASELINE_SUFFICIENT,
  UPGRADE_ELIGIBLE:MEMORY/CPU/DISK/IO, or BASELINE_INCONCLUSIVE. It never proves execution/live
  capacity and never auto-purchases or auto-upgrades.
- DATA-03 remains on the current operator environment and is not moved to the VPS.
- No VPS purchase, provisioning, host activation, credentials, product scheduler, paper session,
  execution, signing, Gate C, live, capital or orders are authorized by this implementation PR.

## S10-STRAT-LIFE-01 V2.1 Strategy Lifecycle + Portfolio Authority Sequence (current)

V2.1 target architecture: ACCEPTED; canonical record in `docs/architecture_decision_record.md`.
This section is PLANNING_GUIDANCE_ONLY for successors; it authorizes no successor start.

- Known-candidate path (no ALPHA-03 prerequisite): KNOWN CANDIDATE -> lifecycle -> Hermes
  strategy manager -> execution feasibility -> exploratory Gate C -> execution host -> live
  orchestrator -> tiny exploratory live.
- Parallel discovery lane: ALPHA-03 -> recurring autonomous discovery/research -> new
  candidate -> same lifecycle. ALPHA-03 is a parallel feeder, not a prerequisite.
- Strong formal lane (unchanged): candidate needing durable/larger evidence -> qualification
  -> WP170 -> formal WP172 -> qualified paper -> larger validated risk band.
- Implementation sequence: S10-STRAT-LIFE-01 -> S10-HERMES-STRAT-01 -> S10-EXEC-FEAS-01 ->
  S10-GATE-C-EXPLORE-01 -> S10-DEPLOY-EXEC-01 -> S10-LIVE-ORCH-01.
- Parallel lanes: S10-DEPLOY-01 host activation, DATA-03 weather evidence, S10-ALPHA-03
  discovery. None blocks the known-candidate path and none starts automatically.
- Global portfolio envelope: a human-authorized global PortfolioAuthorityPolicy replaces
  per-strategy manual live approval as target architecture. Strategy-local failure is
  strategy-local by default (QUARANTINED/RETIRED or PAUSE/PAPER_ONLY blocks only that
  strategy's active budget). Bounded child adaptations may inherit the exact parent band;
  material children are capped at EXPLORATORY_LIVE for automatic inheritance.
- Current runtime is unchanged: controlled Hermes research mode, current Gate C, qualification,
  WP170, formal WP172, WP173 qualified and research-paper modes, DATA-03 and S10-DEPLOY-01
  tooling. Live trading remains DISABLED; capital/orders USD 0 / 0.

## S10-HERMES-STRAT-01 Hermes Strategy Manager Core (merged)

PLANNING_GUIDANCE_ONLY for successors; it authorizes no successor start.

- Known-candidate path capability status: lifecycle (S10-STRAT-LIFE-01: MERGED) -> Hermes
  strategy manager (S10-HERMES-STRAT-01: implemented capability, MERGED in PR #211) -> execution
  feasibility (S10-EXEC-FEAS-01: next core package) -> exploratory Gate C -> execution host ->
  live orchestrator -> tiny exploratory live.
- Raw generic Hermes research remains research-only and untrusted; HERMES-STRAT records the
  canonical soft strategy decision, which is not a hard authorization (SCALE stays downstream
  gated).
- S10-CC-FOUND-01 becomes eligible to draft/start in parallel only after HERMES-STRAT actually
  merges; until then it is NOT AUTHORIZED / NOT STARTED.
- ALPHA-03 remains a parallel feeder; DATA-03 unchanged and non-blocking; S10-DEPLOY-01 host
  activation separate; Gate C unchanged; live DISABLED; capital/orders USD 0 / 0.

## S10-EXEC-FEAS-01 Current Public Execution Feasibility Core (merged)

PLANNING_GUIDANCE_ONLY for successors; it authorizes no successor start.

- S10-STRAT-LIFE-01: MERGED. S10-HERMES-STRAT-01: MERGED. S10-EXEC-FEAS-01: MERGED (PR #212 merged
  at `35db4f05347b8b27f7bd0296cf9b1b0627e58d12`; head `99f3c3c8acc09ae3b5646f785446d69a7b8b2290`).
- Known-candidate path capability status: lifecycle (MERGED) -> Hermes strategy manager (MERGED)
  -> execution feasibility (S10-EXEC-FEAS-01: implemented capability, MERGED in PR #212) ->
  exploratory Gate C (S10-GATE-C-EXPLORE-01: see the current section below) -> execution host
  -> live orchestrator -> tiny exploratory live.
- Current public execution feasibility (public mechanics of one exact intent) is not WP172 formal
  executable edge; WP172 remains the formal durable executable-edge evidence lane.
- ALPHA-03 remains a parallel feeder and is not a prerequisite; DATA-03 unchanged and
  non-blocking; the Control Center (S10-CC-FOUND-01) stays a parallel lane; S10-DEPLOY-01 host
  activation separate; Gate C unchanged; live DISABLED; capital/orders USD 0 / 0.

## S10-GATE-C-EXPLORE-01 Exploratory Gate C Policy Permit Core (merged)

PLANNING_GUIDANCE_ONLY for successors; it authorizes no successor start.

- S10-STRAT-LIFE-01: MERGED. S10-HERMES-STRAT-01: MERGED. S10-EXEC-FEAS-01: MERGED.
  S10-GATE-C-EXPLORE-01: MERGED (PR #213 merged at `0392c2d2080a656d8ffd69f42abf8ad91d1f90e2`; head
  `342dfeb24652eccb1b6bdf237039b268115b1fb7`).
- Known-candidate path capability status: lifecycle (MERGED) -> Hermes strategy manager (MERGED)
  -> execution feasibility (MERGED) -> exploratory Gate C (S10-GATE-C-EXPLORE-01: implemented
  capability, MERGED in PR #213) -> execution host (S10-DEPLOY-EXEC-01: see the current section
  below) -> live orchestrator (S10-LIVE-ORCH-01: later) -> tiny exploratory live.
- The exploratory permit is hard eligibility evidence for one exact intent, necessary but not
  sufficient: execution-host identity, restart/recovery, authenticated account/access checks,
  reconciliation and order mutation remain future protected runtime work (S10-DEPLOY-EXEC-01,
  S10-LIVE-ORCH-01). WP175 remains the separate historical/manual restricted-live canary.
- S10-CC-OPS-01 may begin only after GATE-C-EXPLORE merges, under the locked Control Center
  baseline, as a separate package; S10-CC-FOUND-01 stays parallel/independent; ALPHA-03 remains a
  parallel feeder and is not a prerequisite; DATA-03 unchanged and non-blocking; S10-DEPLOY-01
  host activation separate; live DISABLED; capital/orders USD 0 / 0.

## S10-DEPLOY-EXEC-01 Execution-Host Runtime Substrate & Coexistence Proof (merged)

Status: MERGED (PR #214; repairs PR #215, #217 and #218). The bullets below are the
implementation-time record; see the S10-LIVE-ORCH-01 section for the current package.

PLANNING_GUIDANCE_ONLY for successors; it authorizes no successor start.

- S10-GATE-C-EXPLORE-01: MERGED (PR #213). S10-DEPLOY-EXEC-01: current implemented review target
  (repository mechanism, `docs/execution_host_runtime_contract.md`). After merge the mechanism is
  merged, but the actual AlphaVPS host proof stays separately gated until an authorized Phase B
  completes.
- Known-candidate path capability status: lifecycle (MERGED) -> Hermes strategy manager (MERGED)
  -> execution feasibility (MERGED) -> exploratory Gate C (MERGED) -> execution host
  (S10-DEPLOY-EXEC-01: implemented repository mechanism, current review target; Phase-B host proof
  separately gated) -> live orchestrator (S10-LIVE-ORCH-01: next core successor after
  execution-host substrate proof, NOT STARTED) -> tiny exploratory live.
- Gate-C eligibility and DEPLOY-EXEC host proof are each necessary but not sufficient. Account /
  access / reconciliation, trading credentials and order mutation remain future protected
  S10-LIVE-ORCH-01 work.
- Capacity outcomes are review triggers only: no automatic upgrade or purchase; Karl decides; a
  second VPS remains a separate material architecture decision.
- ALPHA-03 and DATA-03 remain separate, non-blocking lanes; the Control Center remains separate and
  non-canonical; live DISABLED; capital/orders USD 0 / 0.

## S10-LIVE-ORCH-01 Restricted Live Orchestration + First-Live Canary Core (current)

PLANNING_GUIDANCE_ONLY for successors; it authorizes no successor start.

- S10-DEPLOY-EXEC-01: MERGED (PR #214; repairs PR #215, #217 and #218). S10-LIVE-ORCH-01: current
  protected implemented review target (`docs/live_orchestration_contract.md`), dormant capability
  only; merge does not activate live trading.
- Known-candidate path capability status: lifecycle (MERGED) -> Hermes strategy manager (MERGED)
  -> execution feasibility (MERGED) -> exploratory Gate C (MERGED) -> execution host (MERGED) ->
  live orchestrator (S10-LIVE-ORCH-01: implemented dormant capability, current protected review
  target) -> first restricted live canary (S10-LIVE-CANARY-01: separately gated, requires a
  separate exact-merge Karl authorization).
- First-live CREATE is BUY only under the frozen USD 100 / 5 / 30 / 70 envelope with no auto
  scaling; SELL, Session Keys, Builder credentials, SDK upgrade, heartbeat daemon, WebSocket
  recovery authority, automatic CREATE retry, neg-risk / delayed markets, redemption,
  wallet deployment / approval automation and multi-strategy scheduling stay deferred.
- ALPHA-03 and DATA-03 remain separate, non-blocking lanes; the Control Center remains separate and
  non-canonical; live DISABLED; implementation capital/orders USD 0 / 0.
