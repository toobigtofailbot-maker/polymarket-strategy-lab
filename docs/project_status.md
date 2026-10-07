# Project Status

# S10-LIVE-ORCH-01 current protected implementation target: Restricted Live Orchestration + First-Live Canary Core; Package class: PROTECTED_RESTRICTED_LIVE_ORCHESTRATION; Package size class: XL (explicit XL authorization); Governance track: PROTECTED; Risk level: 4; Exact changed-file scope: 27; Frozen base: 3f4d9ed91c0e96b9fc19389ac59e01f079caa3fe; Immediate predecessor: PR #218 / S10-DEPLOY-EXEC-01R3; PR #218 merged: YES; PR #218 head: b1779f5bc6e945eedfa1ba0692a9e1baca779973; PR #218 merge: 3f4d9ed91c0e96b9fc19389ac59e01f079caa3fe; S10-STRAT-LIFE-01: MERGED; S10-HERMES-STRAT-01: MERGED; S10-EXEC-FEAS-01: MERGED; S10-GATE-C-EXPLORE-01: MERGED; S10-DEPLOY-EXEC-01: MERGED (PR #214; repairs PR #215, #217, #218); current protected implementation target: S10-LIVE-ORCH-01 (implemented review target); readiness: IMPLEMENTATION_READY (PROTECTED, INDEPENDENT_CERTIFICATE, certificate hash-bound); capability: dormant protected foreground orchestrator src/execution_gateway/live_orch.py (preflight / canary / reconcile) over the existing Gate-B, Gate-C and gateway/store boundaries: exact current ExploratoryGateCPermit revalidation, strict execution-host currentness / NTP PASS, fresh geoblock PASS, exact Deposit Wallet identity, fresh bounded account truth, fresh venue drift contract, durable LIVE_ORCH_ADMISSION before CREATE_STARTED, at most one BUY CREATE, restart-safe multi-episode reconciliation of partial fills, settlement statuses and cancel ambiguity; EXEC-FEAS minimum-order dimension repair; contract: docs/live_orchestration_contract.md; first-live CREATE side: BUY only (SELL -> SIDE_UNSUPPORTED_FIRST_CANARY); capital envelope: USD 100 account / USD 5 order / USD 30 aggregate commitment / USD 70 free collateral, auto scaling: NO; implementation/CI real product network calls: 0; real credentials: 0; authenticated account access: 0; real CREATE/CANCEL: 0; dependency/workflow change: 0; first real canary: S10-LIVE-CANARY-01, separately gated (NOT AUTHORIZED); WP175: historical manual path; ALPHA-03: separate / non-blocking; DATA-03: unchanged and non-blocking; Control Center: separate / non-canonical; live: DISABLED; S10-LIVE-ORCH-01 capital/orders: USD 0 / 0; Merge authorized: NO

# S10-DEPLOY-EXEC-01 merged historical predecessor (PR #214 merged: YES at fe4e2f1557dec5667d32fa1479f0bfc7ead1c940 with head 9871dddf98565b16194209f032cf8279bfbd34f1; repairs PR #215, #217 and #218 merged; formerly the current bounded implementation target): Execution-Host Runtime Substrate & Coexistence Proof; Package class: EXECUTION_HOST_RUNTIME_SUBSTRATE; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 18; Frozen base: 0392c2d2080a656d8ffd69f42abf8ad91d1f90e2; Immediate predecessor: PR #213 / S10-GATE-C-EXPLORE-01; PR #213 merged: YES; PR #213 head: 342dfeb24652eccb1b6bdf237039b268115b1fb7; PR #213 merge: 0392c2d2080a656d8ffd69f42abf8ad91d1f90e2; S10-STRAT-LIFE-01: MERGED; S10-HERMES-STRAT-01: MERGED; S10-EXEC-FEAS-01: MERGED; S10-GATE-C-EXPLORE-01: MERGED; current bounded implementation target: S10-DEPLOY-EXEC-01 (implemented review target); readiness: IMPLEMENTATION_READY (RUNTIME); capability: additive extension of the merged S10-DEPLOY-01 tools/deployment/ baseline with a sanitized execution-host binding and currentness contract (pseudonymous pmhost-v1 host id, pmboot-v1 boot id, exact release SHA, release manifest hash, critical-probe unit hash), one non-economic polymarket-execution-critical-probe.service in the existing polymarket-critical.slice (Restart=on-failure, RestartSec=1s, no network, no credentials; installed but disabled/inactive after bootstrap), a closed research-versus-critical coexistence evaluator (C8G_EXECUTION_HOST_SUFFICIENT / UPGRADE_ELIGIBLE:CRITICAL_DEADLINE|CRITICAL_DEGRADATION|MEMORY|CPU|DISK|IO / EXECUTION_HOST_INCONCLUSIVE) and closed terminal Phase-B evidence semantics (EXECUTION_HOST_PROVEN_C8G / EXECUTION_HOST_EVIDENCE_COMPLETE_UPGRADE_ELIGIBLE:<reason> / EXECUTION_HOST_INCONCLUSIVE); contract: docs/execution_host_runtime_contract.md; research baseline contract unchanged; slice values unchanged; Phase A: repository mechanism only; Phase B (real AlphaVPS proof): NOT AUTHORIZED / NOT PERFORMED, separately authorized after merge; AlphaVPS purchased/provisioned: operator-reported by Karl, not repository-observed; project deployment on AlphaVPS: NOT PERFORMED; actual host technical facts: UNKNOWN until Phase B; automatic upgrade / second host: NO (Karl decides); Gate-C eligibility: necessary-but-not-sufficient; src changed: NO; credentials: NONE; authenticated client/account reads: NONE; GateCLivePermit / A3: NOT ISSUED / NOT ENTERED; signing/order placement/cancel: NONE; OMS/reconciliation: NONE; dependency/workflow change: 0; S10-LIVE-ORCH-01: next core successor after execution-host substrate proof (NOT STARTED); ALPHA-03: separate / non-blocking; DATA-03: unchanged and non-blocking; Control Center: separate / non-canonical; paper/execution/live: NO; live: DISABLED; S10-DEPLOY-EXEC-01 capital/orders: USD 0 / 0; Merge authorized: NO

# S10-GATE-C-EXPLORE-01 merged historical predecessor (PR #213 merged: YES at 0392c2d2080a656d8ffd69f42abf8ad91d1f90e2 with head 342dfeb24652eccb1b6bdf237039b268115b1fb7; formerly the current protected implementation target): Exploratory Gate C Policy Permit Core; Package class: EXPLORATORY_GATE_C_POLICY_PERMIT_CORE; Package size class: L; Governance track: PROTECTED; Risk level: 4; Exact changed-file scope: 18; Frozen base: 35db4f05347b8b27f7bd0296cf9b1b0627e58d12; Immediate predecessor: PR #212 / S10-EXEC-FEAS-01; PR #212 merged: YES; PR #212 head: 99f3c3c8acc09ae3b5646f785446d69a7b8b2290; PR #212 merge: 35db4f05347b8b27f7bd0296cf9b1b0627e58d12; S10-STRAT-LIFE-01: MERGED; S10-HERMES-STRAT-01: MERGED; S10-EXEC-FEAS-01: MERGED; current protected implementation target: S10-GATE-C-EXPLORE-01 (implemented review target); readiness: IMPLEMENTATION_READY (PROTECTED, INDEPENDENT_CERTIFICATE, certificate hash-bound); capability: new stdlib-only src/exploratory_gate_c/ package that loads the existing STRAT-LIFE and Hermes strategy-manager stores only through their verified read-only loaders, binds the exact StrategyVersion, active global PortfolioAuthorityPolicy, current EXPLORATORY_LIVE allocation, STRAT-LIFE portfolio capacity, the latest compatible Hermes assessment and an exactly re-derived FEASIBLE/LIMITED EXEC-FEAS intent/snapshot/assessment into a content-addressed ExploratoryGateCDecision (PERMIT_ELIGIBLE / PERMIT_REJECTED) and, only when eligible, a content-addressed exact-intent ExploratoryGateCPermit; contract: docs/exploratory_gate_c_contract.md; exploratory permit: necessary-but-not-sufficient future evidence, not live activation; runtime account/access/reconciliation/identity revalidation: REQUIRED; legacy WP175 Gate-C live permit / A3: NOT ISSUED / NOT ENTERED; WP175 unchanged; src/execution_gateway changed: NO; persistence: NONE; network/account/geoblock reads: NONE; credentials: NONE; signing/order placement/cancel: NONE; scheduler/background loop: NONE; S10-DEPLOY-EXEC-01: next core successor after GATE-C-EXPLORE review and merge (NOT STARTED); S10-LIVE-ORCH-01: later; S10-CC-OPS-01: separate package, may begin only after GATE-C-EXPLORE merges under the locked Control Center baseline (not implemented here); S10-CC-FOUND-01: parallel / independent; ALPHA-03: parallel / non-blocking; DATA-03: unchanged and non-blocking; S10-DEPLOY-01 host activation: separate; dependency/workflow/tools change: 0; paper/live: NO; live: DISABLED; S10-GATE-C-EXPLORE-01 capital/orders: USD 0 / 0; Merge authorized: NO

# S10-EXEC-FEAS-01 merged historical predecessor (PR #212 merged: YES at 35db4f05347b8b27f7bd0296cf9b1b0627e58d12 with head 99f3c3c8acc09ae3b5646f785446d69a7b8b2290; formerly the current bounded implementation target): Current Public Execution Feasibility Core; Package class: CURRENT_PUBLIC_EXECUTION_FEASIBILITY_CORE; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 17; Frozen base: 4519aab3d7f8424fc74c59104cc4e7afe0ff11b8; Immediate predecessor: PR #211 / S10-HERMES-STRAT-01; PR #211 merged: YES; PR #211 head: 9439283768b78b7302290ba6b8611e3477aa3c6a; PR #211 merge: 4519aab3d7f8424fc74c59104cc4e7afe0ff11b8; S10-STRAT-LIFE-01: MERGED; S10-HERMES-STRAT-01: MERGED; current bounded implementation target: S10-EXEC-FEAS-01 (implemented review target); readiness: IMPLEMENTATION_READY (RUNTIME); capability: new stdlib-only src/execution_feasibility/ package that binds one exact StrategyVersion read-only (execution_rule_sha256 derived from its canonical execution_rule), builds a content-addressed ExecutionIntent, acquires bounded current public Gamma market and CLOB book evidence through exactly two fixed-host unauthenticated GET requests into a content-addressed PublicExecutionVenueSnapshot, and deterministically evaluates venue mechanics into a content-addressed ExecutionFeasibilityAssessment (FEASIBLE / LIMITED / INCONCLUSIVE / NOT_FEASIBLE); contract: docs/execution_feasibility_contract.md; public current mechanics only; persistence: NONE; account state: NONE; execution feasibility is not WP172 executable edge (EXECUTABLE_EDGE_PASS unchanged); profitability claim: NO; public endpoints: gamma-api.polymarket.com/markets/<id> and clob.polymarket.com/book only; real external calls during implementation/CI: 0; credentials: NONE; account reads: NONE; order placement/cancel/signing: NONE; scheduler/background loop: NONE; S10-GATE-C-EXPLORE-01: next core package after EXEC-FEAS review and merge (NOT AUTHORIZED / NOT STARTED); Gate C changed: NO (NOT AUTHORIZED); ALPHA-03: parallel / non-blocking; DATA-03: unchanged and non-blocking; S10-CC-FOUND-01: parallel lane, not started by this package; S10-DEPLOY-01 host activation: separate; dependency/workflow/tools change: 0; paper/execution/live: NO; live: DISABLED; S10-EXEC-FEAS-01 capital/orders: USD 0 / 0; Merge authorized: NO

# S10-HERMES-STRAT-01 merged historical predecessor (PR #211 merged: YES at 4519aab3d7f8424fc74c59104cc4e7afe0ff11b8 with head 9439283768b78b7302290ba6b8611e3477aa3c6a; formerly the current bounded implementation target): Hermes Strategy Manager Core — V2.1 Soft Strategy Judgment; Package class: HERMES_STRATEGY_MANAGER_CORE; Package size class: XL (XL_FOR_SCOPE_ONLY, Scope Amendment 01); Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 22; Frozen base: dab28ee45c1f8267248d52601c90d3f3509034f9; Immediate predecessor: PR #210 / S10-STRAT-LIFE-01; PR #210 merged: YES; PR #210 head: d3c98d7530c8cec6b65e5d76492f1d7da8edf783; PR #210 merge: dab28ee45c1f8267248d52601c90d3f3509034f9; S10-STRAT-LIFE-01: MERGED; current bounded implementation target: S10-HERMES-STRAT-01; readiness: IMPLEMENTATION_READY (RUNTIME); capability: additive default-off strategy mode in the existing controlled Hermes runtime (generic and context modes unchanged) plus src/research_runtime/hermes_controlled_runtime/strategy_manager.py that evaluates one exact StrategyVersion from a verified STRAT-LIFE snapshot with bounded admissible evidence, runs exactly one controlled Hermes assessment, validates the untrusted strategy-mode draft deterministically and records a canonical soft Hermes strategy decision (HermesStrategyAssessment) with HermesStrategyRunRecord lineage in an append-only hash-chained SQLite history store (application id 1213418801); contract: docs/hermes_strategy_manager_contract.md; raw generic Hermes research remains research-only and untrusted; HERMES-STRAT decisions are soft judgments, not hard authorizations; direct STRAT-LIFE mutation: NO; PortfolioAuthorityPolicy mutation: NO; child StrategyVersion creation: NO; historical Hermes compatibility guard edits: 2 (exact path exceptions only); authority expansion from amendment: NONE; real provider/model calls: 0; S10-EXEC-FEAS-01: next core package after HERMES-STRAT review and merge (not implemented); S10-CC-FOUND-01: NOT AUTHORIZED / NOT STARTED until HERMES-STRAT merges; Control Center: NOT STARTED; ALPHA-03: parallel / non-blocking; DATA-03: unchanged and non-blocking; S10-DEPLOY-01 host activation: separate; Gate C changed: NO (NOT AUTHORIZED); scheduler/background loop: NONE; credentials: NONE; paper/execution/live: NO; live: DISABLED; S10-HERMES-STRAT-01 capital/orders: USD 0 / 0; Merge authorized: NO

# S10-STRAT-LIFE-01 merged historical predecessor (PR #210 merged: YES at dab28ee45c1f8267248d52601c90d3f3509034f9 with head d3c98d7530c8cec6b65e5d76492f1d7da8edf783; formerly the current bounded implementation target): Strategy Lifecycle + Global Portfolio Authority Core; Package class: STRATEGY_LIFECYCLE_PORTFOLIO_AUTHORITY_CORE; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 20; Frozen base: 02eeed13dc0b9552e5685f48198d060e78c797e1; Immediate predecessor: PR #209 / S10-DEPLOY-01; PR #209 merged: YES; PR #209 head: 3e9d595e014275662e90b5f22809f66b3e82cb39; PR #209 merge: 02eeed13dc0b9552e5685f48198d060e78c797e1; S10-DEPLOY-01 repo implementation: MERGED; host activation: NOT YET PERFORMED / separately gated; V2.1 target architecture: ACCEPTED; current bounded implementation target: S10-STRAT-LIFE-01; readiness: IMPLEMENTATION_READY (RUNTIME); capability: stdlib-only src/strategy_lifecycle/ substrate with immutable content-addressed strategy family/version identity and parent lineage, mechanical bounded-vs-material adaptation classification, advisory evidence posture, strategy health, strategy-local restrictions, risk allocations, one human-authorized global PortfolioAuthorityPolicy with activation/revocation receipts, deterministic portfolio budget/capacity accounting and one append-only hash-chained SQLite lifecycle store (application id 1398033457) derived by verified replay; contract: docs/strategy_lifecycle_portfolio_authority_contract.md; WP61/WP95/WP154 universal target assumptions superseded as future target architecture (history retained); not wired into Alpha Factory, Hermes, paper, qualification, WP170, WP172, Gate C, execution, deployment or cockpit; Hermes strategy manager implemented: NO; existing controlled Hermes research mode unchanged until S10-HERMES-STRAT-01; qualification/WP170/WP172 changed: NO; WP173 paper modes changed: NO; Gate C changed: NO (NOT AUTHORIZED); ALPHA-03: separate / parallel, not implemented and not a known-candidate prerequisite; DATA-03: unchanged and non-blocking; dependency/workflow/tools change: 0; network/credentials/scheduler: NONE; paper/execution/live: NO; live: DISABLED; S10-STRAT-LIFE-01 capital/orders: USD 0 / 0; next separately draftable after review and merge: S10-HERMES-STRAT-01 and S10-EXEC-FEAS-01; Merge authorized: NO

# S10-DEPLOY-01 merged historical predecessor (PR #209 merged: YES at 02eeed13dc0b9552e5685f48198d060e78c797e1 with head 3e9d595e014275662e90b5f22809f66b3e82cb39; host activation NOT YET PERFORMED; formerly the current bounded implementation target): Research Platform Runtime Baseline; Package class: RESEARCH_PLATFORM_RUNTIME_BASELINE; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 19; Frozen base: 0b14c951c4546ebc28e0d129643da4ad4615ce2e; Immediate predecessor: PR #208 / S10-PAPER-RESEARCH-01 merged: YES at that SHA with head d5f61c086cbef74010856be88134e04c0e81a06d; Current branch: codex/s10-deploy-01-research-runtime-baseline; readiness: IMPLEMENTATION_READY (RUNTIME); capability: credential-free exact tracked-file release build/verify, Ubuntu 24.04 x86-64 native-systemd bootstrap, persistent /var/lib/polymarket research state, exact bounded research slice and reserved critical slice, sanitized once-per-minute telemetry, SQLite-aware hashed backup, isolated integrity-checked restore drills, explicit SSH-port deny-inbound firewall contract and one bounded post-merge public WP169 smoke; deployment repository family: tools/deployment/; source runtime change: 0; dependency/lock/workflow change: 0; provider purchase/provisioning/remote login: NO; host activation: DEFERRED_POST_MERGE_HUMAN_OPERATOR_CLOSURE; research baseline may precede DATA-03 and candidate-specific WP172; later execution coexistence/hardening proof remains required after a real WP172 PASS and before production-hosted serious paper/live; DATA-03 remains on its current operator environment untouched; product recurring scheduler: NONE (host telemetry timer only); credentials: NONE; authenticated Polymarket calls: 0; paper/execution/live: NO; live: DISABLED; Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders: 0; Merge authorized: NO

# S10-CI-SEC-01 current bounded security closure (open branch claude/s10-ci-sec-01-dependency-security-ci-closure; not merged): Dependency-Security CI Closure; Package class: SECURITY_TOOLING_DEPENDENCY_CI_CLOSURE; Package size class: M; Governance track: FAST; Risk level: 2; Exact changed-file scope: 8; Frozen base: f9a0bae6a69d008862e6466f1fe532bc9416de5d; Immediate predecessor: PR #220 / S10-CI-OPT-01; PR #220 merged: YES; PR #220 head: d6899e205f0652c7314216016d95cd17e6f01f46; readiness: IMPLEMENTATION_READY (FAST, DETERMINISTIC, no certificate; source_runtime authority only because the exact-scope lockfile src/operator_cockpit_frontend/package-lock.json is under src/); security findings: source-map-js 1.2.1 GHSA-68fv-2mgg-jv7q (high, frontend development dependency) and fsspec 2026.2.0 CVE-2026-104851 (high, exact-pinned transitively by stable nautilus_trader==1.231.0); remediation: cockpit lock patched to source-map-js 1.2.2 (lock-only, package.json unchanged); both Python audit jobs run python -m pip_audit --ignore-vuln CVE-2026-104851 and every other finding still fails; exception removal trigger: a separately authorized stable compatible NautilusTrader upgrade resolving fsspec >= 2026.6.0 that passes compatibility, pip check, dependency audit and full validation (a prerelease alone is not a removal path); Python pin/pyproject change: 0; forced fsspec: NO; Nautilus migration: NO; product/runtime source logic change: 0; stable record: docs/status_entries/S10-CI-SEC-01.md; PR #221 / S10-LIVE-CANARY-UA-01: separately paused pending this closure (untouched); live: DISABLED; S10-CI-SEC-01 capital/orders: USD 0 / 0; Merge authorized: NO

# S10-CC-FOUND-01 merged historical predecessor (PR #223 merged: YES at 780bf84144439ebc6b1b53f468f257d70707014c with head 786d060089c71cc7f26e1b3d543c65011b950b58; formerly the current Control Center implementation target): Control Center Frontend Foundation + Existing Cockpit Compatibility Migration (REV A); Package class: CONTROL_CENTER_FRONTEND_FOUNDATION; Package size class: L; Governance track: FAST; Risk level: 2; Exact changed-file scope: 20; Frozen base: 71a83bf1d989b5e0bb8a4feab72132756d1eef15; Immediate predecessor: PR #221 / S10-LIVE-CANARY-UA-01; PR #221 merged: YES; PR #221 head: c76b6eeb9157ab578c2655701ab9950d1bd474bd; readiness: IMPLEMENTATION_READY (FAST, DETERMINISTIC, no certificate); capability: the five existing read-only cockpit views migrated onto a Control Center frontend foundation (React Router declarative routes /overview /markets /experiments /paper /audit, typed same-origin /api client, conservative TanStack Query with active-family manual refresh, semantic CSS tokens and primitives, deterministic Storybook/MSW reference states, loopback-only Vite dev proxy); exact new frontend pins: react-router 8.4.0, @tanstack/react-query 5.104.0, storybook 10.6.1, @storybook/react-vite 10.6.1, msw 2.15.0, msw-storybook-addon 3.0.3; cockpit-frontend CI job adds only the Storybook static build; backend src/operator_cockpit.py and its 14 GET-only routes unchanged; tests/test_operator_cockpit.py carries only the two REV A historical frontend-guard updates; Control Center lane: parallel to the live-network lane, which remains separately blocked on execution-network / geoblock resolution; no realtime, Strategy/Hermes/OPS read model, protected command, deployment, credential, account, product network, execution or live authority; live trading DISABLED; capital/orders USD 0 / 0; status record: docs/status_entries/S10-CC-FOUND-01.md; Ready for review: see PR body; merge NOT AUTHORIZED (Karl only).

# S10-CC-RESEARCH-01 merged historical predecessor (PR #224 merged: YES at e8fbba6436020d543816e1be3fd45ad9c74dffd7 with head 4dd11f1b35bf49cb14d3e03d257f775926ddf116; formerly the current Control Center implementation target): Control Center StrategyLifecycle + Hermes Read-Only Research Vertical; Package class: CONTROL_CENTER_STRATEGY_HERMES_RESEARCH_READ_MODEL; Package size class: L; Governance track: FAST; Risk level: 2; Exact changed-file scope: 15 (13 issued + Side17-approved amendments A tests/test_architecture_boundaries.py and A2 tests/test_operator_cockpit.py); Frozen base: 780bf84144439ebc6b1b53f468f257d70707014c; Immediate predecessor: PR #223 / S10-CC-FOUND-01; PR #223 merged: YES; PR #223 head: 786d060089c71cc7f26e1b3d543c65011b950b58; readiness: IMPLEMENTATION_READY (FAST, DETERMINISTIC, no certificate); capability: read-only projection src/operator_cockpit_research.py over load_strategy_lifecycle_store and load_hermes_strategy_manager_store only, four GET-only routes /api/strategies, /api/strategies/{strategy_version_id}, /api/hermes/assessments, /api/hermes/assessments/{assessment_id}, display-only context status CURRENT / STALE_CONTEXT / TARGET_MISSING from strategy_lifecycle_context_fingerprint, latest assessment only from the verified manager mapping, exact root-to-target lineage, strategy routes usable without Hermes, and /strategies + /hermes Control Center workspaces with Storybook/MSW states; contract: docs/control_center_strategy_hermes_research_contract.md; Hermes assessments are soft research judgments, never approval, portfolio, Gate-C, execution or live authority; Alpha inference: NONE (S10-CC-RESEARCH-02 separately gated); Hermes invocations / provider calls: 0 / 0; strategy / paper mutations: 0 / 0; dependency/workflow change: 0; credentials/account reads/product network: NONE; live trading DISABLED; capital/orders USD 0 / 0; status record: docs/status_entries/S10-CC-RESEARCH-01.md; merged by Karl via PR #224.

# S10-CC-RESEARCH-02 merged historical predecessor (PR #225 merged: YES at 2685429aca6c0b655308a562a693d3075c1994a4 with head d4075ea344a318897e5cd755eb691a2bd45daa89; formerly the current Control Center implementation target): Control Center Alpha Factory + Evidence / Research Lineage; Package class: CONTROL_CENTER_ALPHA_RESEARCH_MEMORY_DISCOVERY_READ_MODEL; Package size class: L; Governance track: FAST; Risk level: 2; Exact changed-file scope: 15; Frozen base: e8fbba6436020d543816e1be3fd45ad9c74dffd7; Immediate predecessor: PR #224 / S10-CC-RESEARCH-01; PR #224 merged: YES; PR #224 head: 4dd11f1b35bf49cb14d3e03d257f775926ddf116; readiness: IMPLEMENTATION_READY (FAST, DETERMINISTIC, no certificate); capability: read-only Alpha Factory + Discovery projection inside the existing src/operator_cockpit_research.py over load_and_verify_alpha_factory_registry and load_and_verify_alpha_discovery_registry only, six GET routes /api/alpha/memory, /api/alpha/candidates, /api/alpha/candidates/{candidate_id}, /api/alpha/episodes/{research_episode_id}, /api/alpha/discovery/queue, /api/alpha/discovery/triage/{market_triage_decision_id} (24 total /api routes), candidate ordering by registry sequence, same-snapshot candidate/family/episode/source lineage with research leaves (several allowed), opaque deterministic evidence refs, latest recorded discovery queue by greatest registry sequence with policy/universe/lane accounting, external universe completeness UNPROVEN, triage + material change detail and exact-head matched_* Alpha resolution (NOT_BOUND / UNAVAILABLE / HEAD_MISMATCH / RESOLVED), independent sources, and one /alpha workspace (Research Memory + Discovery Queue) with Storybook/MSW states; contract: docs/control_center_alpha_research_contract.md; no new persistence; no dependency/workflow change; no Strategy/Hermes inferred Alpha join; no qualification/AF1 history synthesis; RESEARCH_SUPPORTIVE is never qualification or trading authority and discovery priority is never trade priority; no network/runtime/mutation authority; Alpha mutations 0; Hermes invocations / provider calls: 0 / 0; credentials/account reads/product network: NONE; live trading DISABLED; capital/orders USD 0 / 0; status record: docs/status_entries/S10-CC-RESEARCH-02.md; merged by Karl via PR #225.

# S10-CC-OPS-01 merged historical predecessor (PR #226 merged: YES at 7bba7f0d6657364b9358d1a4a96807f024db0533 with head 90d30129ce0f3282395b6f319ce25c622191d39b; formerly the current Control Center implementation target): Control Center Portfolio / Risk / Runtime Operations Read Model; Package class: CONTROL_CENTER_PORTFOLIO_RISK_RUNTIME_OPS_READ_MODEL; Package size class: L; Governance track: FAST; Risk level: 2; Exact changed-file scope: 16; Frozen base: 2685429aca6c0b655308a562a693d3075c1994a4; Immediate predecessor: PR #225 / S10-CC-RESEARCH-02; PR #225 merged: YES; PR #225 head: d4075ea344a318897e5cd755eb691a2bd45daa89; readiness: IMPLEMENTATION_READY (FAST, DETERMINISTIC, no certificate); capability: new pure read-only projection src/operator_cockpit_ops.py over load_strategy_lifecycle_store only and the canonical evaluate_portfolio_capacity called exactly once per request at one backend time.time_ns value, one GET route /api/ops/portfolio (25 total /api routes; any query INVALID_INPUT; closed SOURCE_UNAVAILABLE) returning the exact active policy with all 17 money/count limits or null, the canonical capacity result (no-active-policy POLICY_NOT_ACTIVE and canonical rejections are HTTP 200 domain states), same-snapshot strategy budget reservations with window truth, health, exact per-strategy capacity result and active restrictions, and fixed non-authority flags; one /ops workspace with the ops query family and five OPS-owned keys composing the existing /api/paper/summary, /api/paper/risk, /api/gateway/status and /api/gateway/audit projections unchanged, independent source panels, manual refresh and six Storybook/MSW states; contract: docs/control_center_ops_read_model_contract.md; budget reservations are not actual account exposure; paper stays SIMULATED PAPER ONLY and is never merged with reservation economics; recorded gateway state is never current account, host or network truth, Gate-C eligibility or live readiness; no incident/alert registry, EXEC-FEAS/Gate-C history, LIVE-ORCH drill-down, host-currentness or geoblock request; StrategyLifecycle / paper / gateway source and mutations: unchanged / 0; no new persistence; no dependency/workflow change; credentials/account reads/product network: NONE; live trading DISABLED; capital/orders USD 0 / 0; status record: docs/status_entries/S10-CC-OPS-01.md; successor S10-CC-STREAM-01 separately gated.

# S10-CC-STREAM-01 current Control Center implementation target (open branch claude/s10-cc-stream-01-sse-freshness-gap-resync; not merged): Control Center Streaming / Freshness / Gap / Resync Layer; Package class: CONTROL_CENTER_SSE_ACTIVE_FAMILY_REFRESH_GAP_RESYNC_RUNTIME; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 17; Frozen base: 7bba7f0d6657364b9358d1a4a96807f024db0533; Immediate predecessor: PR #226 / S10-CC-OPS-01; PR #226 merged: YES; PR #226 head: 90d30129ce0f3282395b6f319ce25c622191d39b; readiness: IMPLEMENTATION_READY (RUNTIME, DETERMINISTIC, no certificate); capability: new transport-only module src/operator_cockpit_stream.py (stdlib asyncio/json/re/time/typing/uuid only; no canonical store, filesystem, environment, subprocess, network-client or WebSocket import; no persistence) and a default-off kill switch (CockpitConfig.streaming_enabled appended as exact bool False; explicit --enable-streaming store_true CLI opt-in only; no environment fallback); two GET routes /api/stream/status (exact transport-only configuration DTO; any query INVALID_INPUT) and /api/stream/events?family=<QueryFamily> (exactly one closed family query validated before enablement; valid but disabled 503 STREAM_DISABLED; enabled text/event-stream with Cache-Control no-cache), 27 total /api routes; one request-scoped SSE wait/emit loop per connected request only (no startup/global/background task, custom retry, source poller, replay buffer or persisted transport history) with BASE_TICK_SECONDS 5 and fixed family cadence overview 10, market 5, experiments 30, strategies 30, hermes 30, alpha 30, ops 5, paper 5, audit 10 seconds; every connection gets a fresh ccstream id, starts at sequence 1 with RESYNC_REQUIRED, then emits REFRESH_DUE or HEARTBEAT with a +1 connection-local sequence and decimal-string server_time_ns, and terminates on disconnect or cancellation; envelopes carry transport metadata only; frontend: one centralized shell StreamRefreshController owns the only browser stream (opened only when the backend reports enabled; closed on family change/unmount; native reconnect only), a new connection id or same-connection sequence gap resyncs the active family over HTTP, RESYNC_REQUIRED/REFRESH_DUE invalidate only familyKey(activeFamily), HEARTBEAT invalidates nothing, malformed events are dropped, manual Refresh and the conservative Query defaults are unchanged, Storybook answers /api/stream/status with the exact disabled DTO through the shared mock helper; contract: docs/control_center_streaming_contract.md; transport connected/sequence/refresh-due/gap/signal time are never domain freshness, source change, market-data gap, account/host/network currentness, incident state or execution/live authority; StrategyLifecycle / Hermes / Alpha / paper / gateway source and mutations: unchanged / 0; no dependency/workflow change; credentials/account reads/product network: NONE; live trading DISABLED; capital/orders USD 0 / 0; status record: docs/status_entries/S10-CC-STREAM-01.md; successors S10-CC-CMD-01 and S10-CC-PROD-01 separately gated; Ready for review: see PR body; merge NOT AUTHORIZED (Karl only).

# S10-CI-OPT-01 workflow-governance review target: Local-First CI Cost Optimization; Package class: WORKFLOW_GOVERNANCE_CI_COST_OPTIMIZATION; Package size class: M; Governance track: FAST; Risk level: 2; Exact changed-file scope: 9; Frozen base: 7dc323df2aa5820621cc2e6cf89a1d91827ed122; Immediate predecessor: PR #219 / S10-LIVE-ORCH-01; PR #219 merged: YES; PR #219 head: 30a5d70aaf385450cd8a9644773e6ecd25a10b9a; PR #219 merge: 7dc323df2aa5820621cc2e6cf89a1d91827ed122; readiness: IMPLEMENTATION_READY (FAST, DETERMINISTIC, no certificate); capability: .github/workflows/ci.yml runs on pull_request opened/synchronize/reopened/ready_for_review only, every top-level job is skipped while the PR is a draft, the duplicate push-to-main full matrix is removed and same-PR concurrency cancels stale runs; final hosted coverage unchanged (same nine jobs, OS/Python matrices, audits, strict DuckDB, NDFD strict, focused tests and full pytest; no path filters); canonical guidance: local-first validation, PR draft until stable, one final exact-head hosted matrix, fresh exact-head CI after any change, affected-job-only infrastructure reruns (docs/ai/codex/VALIDATION_MATRIX.md, docs/ai/codex/WP_DRAFTING_STANDARD.md); stable record: docs/status_entries/S10-CI-OPT-01.md; product source/tools/dependency/credential change: 0; product network change: 0; first real canary: S10-LIVE-CANARY-01, separately gated live successor (NOT AUTHORIZED); live: DISABLED; S10-CI-OPT-01 capital/orders: USD 0 / 0; Merge authorized: NO

# S10-PAPER-RESEARCH-01 current bounded implementation target: Generic Research-Paper + Evidence Loop Bridge; Package class: GENERIC_RESEARCH_PAPER_EVIDENCE_LOOP_BRIDGE; Package size class: XL; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 21; Frozen base: d7166f947d764c4fbda65a7d8092d3984a37c7a7; Immediate predecessor: PR #207 / S10-DEPLOY-PLAN-01 merged: YES at that SHA with head 48a4e69e4083b04d88e4e16457e03e713314834d; readiness: IMPLEMENTATION_READY (RUNTIME); capability: separate immutable ResearchPaperStrategyBinding and PaperEngine.create_research path reusing the existing WP173 store, journal, risk, fill, accounting, control and recovery machinery without WP170/WP172 objects; legacy qualified PaperStrategyBinding and store replay preserved without schema migration; research admission enforces allowed markets, a half-open decision-time window, execution style and NON_CONFIRMATORY_RESEARCH_PAPER reserved-evidence isolation; ResearchPaperPerformanceSnapshot is deterministic, exact-store-head/state-bound, sanitized, advisory-only and has no qualification/execution/live authority; existing Hermes ContextEvidenceItem deterministic-project-evidence semantics and Alpha ResearchEpisode deterministic_evidence_refs compatibility are reused without Hermes-core or Alpha-source change; production Gate C remains unchanged and rejects research bindings; research paper is a learning tier only and cannot satisfy qualification, WP172, Gate C or live promotion; DATA-03 is a parallel weather confirmatory lane, remains untouched, and the weather first-look cohort beginning 2026-10-15T00:00:00Z remains protected; candidate-specific strategy logic, ALPHA-03 and S10-DEPLOY-01 remain separate/not implemented; product/provider/Hermes calls: 0; scheduler/background loop: NONE; credentials: NONE; execution/live: NO; capital/orders: USD 0 / 0; Merge authorized: NO

# S10-DEPLOY-PLAN-01 current bounded planning target: Production VPS Hosting Direction Lock; Package class: DOCS_ONLY_ARCHITECTURE_ROADMAP; Package size class: L (Side14 draft label M; the repo WP spec guard caps M at 10 changed files, so the exact 13-path scope is classified L with no scope change); Governance track: FAST; Risk level: 1; Exact changed-file scope: 13; Frozen base: d45d9587401faddd2ba92f33cb84f2988b6cfe70; Immediate predecessor: PR #206 / S10-QUAL-DATA-03 merged: YES at that SHA with head b7d77f95df093b259a2a2b809ffe20308539e397 (isDraft=false) at 2026-10-01T15:08:12Z; Current branch: claude/dazzling-allen-wru4ti (suggested codex/s10-deploy-plan-01-production-vps-hosting-direction); readiness: IMPLEMENTATION_READY (FAST); Current S10-DEPLOY-PLAN-01 state: IMPLEMENTED_READY_FOR_REVIEW; planning truth only: focused contract docs/production_vps_hosting_direction.md; decision status: APPROVED_PLANNING_DIRECTION; deployment status: NOT_PROVISIONED / NOT_DEPLOYED; provider: AlphaVPS; location: Sofia, Bulgaria; initial tier: C8G; initial resources: 4 vCPU / 8 GB ECC RAM / 75 GB NVMe RAID-10; OS: Ubuntu 24.04 LTS / x86-64; architecture: ONE_CONSOLIDATED_POLYMARKET_VPS; default separate research/live VPS: NO; upgrade path: C8G -> C12G -> C16G/P-series -> larger only by telemetry evidence (eligibility triggers, never automatic upgrades or purchases); migration point: after a real strategy-specific WP172 EXECUTABLE_EDGE_PASS exists and before the first serious production-hosted paper runtime using the existing WP173 system (generic WP172 merged via PR #174 and WP173 merged via PR #175 already exist; WP173 is not reimplemented); future implementation package: S10-DEPLOY-01 Production VPS Runtime Baseline, DRAFT-ELIGIBLE LATER / NOT AUTHORIZED; supersedes the WP61 cheap-VPS-later shorthand and the open VPS/cloud choice; current qualification chain: PR #206 / S10-QUAL-DATA-03: MERGED; DATA03 implementation state: DATA03_IMPLEMENTED_NOT_STARTED; Attempt 03 source probe: PROBE_PASS; next immediate runtime action: zero-network DATA-03 prepare; no real accrue before 2026-10-15T00:00:00Z; DATA-03 moved to VPS: NO; S10-DEPLOY-PLAN-01 changes planning truth only and does not interrupt the qualification chain; src/tools/workflow/dependency changes: 0; VPS purchased/provisioned: NO; deployment performed: NO; credentials: NONE; scheduler/background watcher: NONE; paper authority changed: NO; live authority changed: NO; live: DISABLED; Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders: 0; next expected package: the already-drafted S10-QUAL-DATA-03 post-merge prepare closure, unchanged (separately gated); S10-DEPLOY-01 must not be executed now; Merge authorized: NO

# S10-QUAL-DATA-03 merged historical truth: PR #206 / S10-QUAL-DATA-03 merged: YES at d45d9587401faddd2ba92f33cb84f2988b6cfe70 with head b7d77f95df093b259a2a2b809ffe20308539e397 (isDraft=false) at GitHub server merge time 2026-10-01T15:08:12Z; DATA03 implementation state: DATA03_IMPLEMENTED_NOT_STARTED; Attempt 03 source probe: PROBE_PASS; next immediate runtime action: zero-network DATA-03 prepare (post-merge prepare closure, separately gated and substantively unchanged); no real accrue before 2026-10-15T00:00:00Z; DATA-03 remains on the current operator environment and is not moved to the VPS; historical implementation-WP record follows: Prospective Weather Qualification OOS Accrual + Execution-Terms Capture; Package class: WEATHER_QUALIFICATION_PROSPECTIVE_OOS_ACCRUAL; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 15; Frozen base: 75e17927155dc7ffb5aebfba2f1d97ddd5c2f8b9; Immediate predecessor: PR #205 / S10-QUAL-PLAN-01 merged: YES at that SHA with head 11244eed9686b01e29ede83ea6578bb0a781db6f (isDraft=false); Current branch: claude/determined-clarke-n9cryi (suggested codex/s10-qual-data-03-prospective-oos-accrual); readiness: IMPLEMENTATION_READY (RUNTIME); Current S10-QUAL-DATA-03 state: DATA03_IMPLEMENTED_NOT_STARTED; S10-QUAL-DATA-03 implements the mechanical prospective OOS accrual path frozen by S10-QUAL-PLAN-01 without analytic change: pure module src/data_layer/analytical_research/qualification_oos_accrual.py and manual operator tools/qualification/run_s10_qual_data_03.py (prepare, probe-sources, accrue, seal, verify-final); PLAN-01 plan SHA-256 3b2a99abea8bbd18794c8117d6c1ab696ac817217cd5713367b2ee9a76aa9463, merge 75e17927155dc7ffb5aebfba2f1d97ddd5c2f8b9, freeze deadline 2026-10-14T00:00:00Z, oos_start 2026-10-15T00:00:00Z, embargo lower bound 2026-10-17T00:00:00Z, cap 2027-02-12T00:00:00Z; DATA-02 permanently HISTORICAL_NON_OOS; frozen 11/12 UTC new_market census (a failed discovery read never closes the census: STRUCTURAL_CLASSIFICATION_PENDING); PENDING_LABEL_FINALITY without timeout (LABEL_GAMMA_NOT_FINAL never emitted); label-free row ids weatherqualoosrow:sha256; external B0 EXTERNAL_PIT_MARKET_PROBABILITY_V1 and q/L sealed as canonical decimal strings; stable chronological 50-date prefix; one-way oosmembership seal; closed visible-report firewall; fee source https://help.polymarket.com/en/articles/13364478-trading-fees; N2 + 150 <= 256 provenance pre-gate at prepare; per-run caps 12,288 attempts / 6,442,450,944 bytes; cumulative 65,536 / 34,359,738,368 / 64 runs; contract docs/qualification_weather_oos_accrual_contract.md; one bounded pre-OOS probe-sources only; Source probe: PROBE_PASS (Attempt 03 full-network recovery probe on unchanged 1ef1f842d7baf425addc0f1d7891e819bbffdd78: 15 attempts / 6,446,842 bytes over the five authorized hosts only, no OOS or prospective data; historical Attempts 01/02 were environment egress denials with 0 source bytes; S10-QUAL-DATA-03-D007 RESOLVED_PROBE_PASS_AFTER_ENVIRONMENT_RECOVERY); Real accrue run executed: NO; dependency/workflow changes: 0; QualificationCandidate created: NO; Qualification gate run: NO; WP170 object created: NO; Scores computed: NO; scheduler/background watcher: NONE; WP170/WP172/WP173: NOT STARTED; live: DISABLED; Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders: 0; post-merge prepare then manual accrue from 2026-10-15T00:00:00Z only; S10-QUAL-REAL-01 only after a final membership seal and Side14 closure (separately gated); Merge authorized: NO

# S10-QUAL-PLAN-01 merged historical truth: PR #205 / S10-QUAL-PLAN-01 merged: YES at 75e17927155dc7ffb5aebfba2f1d97ddd5c2f8b9 with head 11244eed9686b01e29ede83ea6578bb0a781db6f (isDraft=false) at GitHub server merge time 2026-10-01T02:39:26Z, before the 2026-10-14T00:00:00Z freeze deadline (freeze valid); its frozen plan is bound unchanged by S10-QUAL-DATA-03; historical plan-freeze-WP record follows: Weather Qualification Prospective Plan Freeze; Package class: WEATHER_QUALIFICATION_PROSPECTIVE_PLAN_FREEZE; Package size class: L; Governance track: FAST; Risk level: 2; Exact changed-file scope: 13; Frozen base: e2edb21e25e7841376c3cb51c27a622fbc0cbc83; Immediate predecessor: PR #204 / S10-QUAL-B0X-01 merged: YES at that SHA with head debcfdf723505b67a1280ac9f303d5abd293c998 (isDraft=false); Current branch: claude/great-clarke-fkezb8 (suggested codex/s10-qual-plan-01-weather-plan-freeze); readiness: IMPLEMENTATION_READY (FAST); Current S10-QUAL-PLAN-01 state: IMPLEMENTED_READY_FOR_REVIEW; S10-QUAL-PLAN-01 is an analytic-plan freeze only (docs/tests): content-addressed plan docs/qualification_plans/S10-QUAL-PLAN-01/weather_plan_v1.json, plan SHA-256 3b2a99abea8bbd18794c8117d6c1ab696ac817217cd5713367b2ee9a76aa9463 (sha256 of exact bytes); oos_start 2026-10-15T00:00:00Z; freeze deadline 2026-10-14T00:00:00Z (GitHub server merge timestamp plus merge SHA; a later merge is OOS_START_FREEZE_WINDOW_MISSED); cap 2027-02-12T00:00:00Z; DATA-02 dates permanently HISTORICAL_NON_OOS; hypothesis nws-public-weather-incrementality v1; B0 EXTERNAL_PIT_MARKET_PROBABILITY_V1 (spread 0.1, trade age 86400); B1 wx.ndfd_pop12_max_climate_day_v1 + time.ndfd_lead_hours_v1, B2 adds mkt.ext_b0_probability_v1; Firth logistic B1/B2 (all-zero init, tolerance 1e-10, max 100 iterations, FIT_FAILED without fallback); hyperparameter search NONE; random_seeds []; formation >= 385 rows and >= 20 dates; selection last 7 dates with >= 5 effective; 100 rows per role; OOS target 50 target dates; Brier primary, log-loss diagnostic, B2 LTE 0.25, fixed sequence B2-B0, B2-B1, B1-B0 at one-sided FWER 0.025; DATA-03 seal/exposure rules and oosmembership seal frozen; execution evidence never backdated; WP170 remains sole preregistration/OOS authority; contract docs/qualification_weather_plan_freeze_contract.md; src/tools/workflow/dependency changes: 0; data accessed: NO; product/source network: NONE; PreregisteredExperiment created: NO; QualificationCandidate created: NO; Qualification gate run: NO; WP170/WP172/WP173: NOT STARTED; live: DISABLED; Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders: 0; next expected package S10-QUAL-DATA-03 only after this WP merges at or before the freeze deadline (separately gated); Merge authorized: NO

# S10-QUAL-B0X-01 merged historical truth: PR #204 / S10-QUAL-B0X-01 merged: YES at e2edb21e25e7841376c3cb51c27a622fbc0cbc83 with head debcfdf723505b67a1280ac9f303d5abd293c998 (isDraft=false); its additive external B0 rule is bound unchanged by the S10-QUAL-PLAN-01 plan freeze; historical contract-extension-WP record follows: External-Reconstruction B0 Qualification Contract Extension; Package class: EXTERNAL_RECONSTRUCTION_B0_QUALIFICATION_CONTRACT; Package size class: L (drafted S; reconciled to the spec-guard file budget, scope unchanged); Governance track: FAST; Risk level: 2; Exact changed-file scope: 14; Frozen base: ebd6f84c95e30451fe1c9ad431e405c57c113074; Immediate predecessor: PR #203 / S10-QUAL-DATA-02 merged: YES at that SHA with head b9e2e6995ee232720d0516b1fa234dec8bdac5e3 (isDraft=false); Current branch: claude/clever-cori-rfw5lb (suggested codex/s10-qual-b0x-01-external-b0-contract); readiness: IMPLEMENTATION_READY (FAST); Current S10-QUAL-B0X-01 state: IMPLEMENTED_READY_FOR_REVIEW; S10-QUAL-B0X-01 is an additive qualification-contract extension only: exactly one external-reconstruction B0 rule EXTERNAL_PIT_MARKET_PROBABILITY_V1 and exactly one feature source class MARKET_EXTERNAL_RECONSTRUCTION; canonical PIT_MARKET_PROBABILITY_V1 / MARKET_PIT unchanged; rule-specific B2 coupling (canonical B0 -> MARKET_PIT only, external B0 -> MARKET_EXTERNAL_RECONSTRUCTION only, mixed rejects; both market classes reject in B1); identical B0 parameter keys/bounds and fallback mechanics; observability by external capture timestamp_received; no backdating by Last-Modified/public_available_time; external evidence never MARKET_PIT, SOURCE_KIND_CANONICAL_PIT, DatasetSnapshotReference or local-first-seen; no import bridge; QUALIFICATION_SCHEMA_VERSION 1.0.0; canonical candidate ids unchanged (binary qualificationcandidate:sha256:6f94dec0c556d9a3574349e8696cee6fb128933cf393fb8da212f70adf075f21); qualification_gate.py, __init__.py, DATA-02 sources/operators and WP170 unchanged; dependency/workflow changes: 0; network/data acquisition: NONE; QualificationCandidate real execution: NO; Qualification gate real run: NO; WP170/WP172/WP173: NOT STARTED; live: DISABLED; Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders: 0; next expected package S10-QUAL-REAL-01 only after this WP merges (separately gated); Merge authorized: NO

# S10-QUAL-DATA-02 merged historical truth: PR #203 / S10-QUAL-DATA-02 merged: YES at ebd6f84c95e30451fe1c9ad431e405c57c113074 with head b9e2e6995ee232720d0516b1fa234dec8bdac5e3 (isDraft=false); sealed QUAL_DATA_READY corpus retained unchanged; its EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION B0 status is answered by the S10-QUAL-B0X-01 external-reconstruction B0 contract (the corpus stays never canonical PIT); historical corpus-completion-WP record follows: Weather Qualification Corpus Completion; Package class: WEATHER_QUALIFICATION_CORPUS_COMPLETION; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 15; Frozen base: 6f67bac990d8ab338f1b87140ae077e9df4172dd; Immediate predecessor: PR #202 / S10-QUAL-DATA-01 merged: YES at that SHA with head 33c031f41626550294eb6667620b4ce75589d719 (isDraft=false); Current branch: codex/s10-qual-data-02-weather-corpus-completion; readiness: IMPLEMENTATION_READY (RUNTIME); Current S10-QUAL-DATA-02 state: QUAL_DATA_READY; Terminal QUAL_DATA_READY (EVIDENCE_COMPLETE_ROWS_PRESENT), verify-final VERIFIED (zero network), bundle weatherqualbundle:sha256:a5911ab05cc8c650377447aa46f65f3b2002fc458e3c51a64f8705b1adcc69ae, logical dataset weatherqualdataset:sha256:a3e98a35ea052e1dfeb5225239a74beaee47d04111ebb34e6d27717490d9ac39, PR #202 seed verified (3600 artifacts admitted; failed seed entries admitted: 0; 3060 reused / 1,728,309,493 bytes), 600 discovered / 570 included / 30 excluded markets (15 LABEL_V3_SOURCE_READ_FAILED, 15 outside corpus), 783 evidence-complete rows (checkpoint A 465, checkpoint B 318) over 32 independent target dates, 7 MARKET_HISTORY_SOURCE_INVALID rows, new network 3,919 attempts / 2,572,004,490 bytes (0 HTTP 429/503), budget not exhausted; S10-QUAL-DATA-02 is data formation/corpus completion only: one bounded completion run of the frozen S10-QUAL-DATA-01 weather corpus seeded from the verified PR #202 run-01 (predecessor-code bound; only hash-valid successful raw artifacts admitted; failed seed entries admitted: 0; whole corpus re-derived), D011 failed-read rules (failed best_bid_ask hour -> MARKET_HISTORY_SOURCE_INVALID; failed last_trade_price hour never searched; failed market_resolved read -> LABEL_V3_SOURCE_READ_FAILED; failed tick_size_change explicit), frozen 429/503 backoff 2s/8s/30s (Retry-After <= 60 s can only lengthen), new-network caps 12,288 attempts / 6,442,450,944 bytes / 268,435,456 per response / 2,000 hours; dates, checkpoints, windows, label window and finality policies unchanged; PendulumFlow v3 is THIRD_PARTY_NATIVE_FRAME_ARCHIVE / EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION, never canonical PIT; b0_contract_compatibility EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION; contract docs/qualification_weather_corpus_completion_contract.md; operator tools/qualification/run_s10_qual_data_02.py; dependency/workflow changes: 0; qualification/gate/provenance contract changes: 0; QualificationCandidate created: NO; Qualification gate run: NO; WP170/WP172/WP173: NOT STARTED; credentials/scheduler/Hermes/strategy/paper/execution: 0; live: DISABLED; Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders: 0; Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; Merge authorized: NO

# S10-QUAL-DATA-01 merged historical truth: PR #202 / S10-QUAL-DATA-01 merged: YES at 6f67bac990d8ab338f1b87140ae077e9df4172dd with head 33c031f41626550294eb6667620b4ce75589d719 (isDraft=false); QUAL_DATA_INSUFFICIENT seed evidence retained and completed by S10-QUAL-DATA-02; historical readiness-WP record follows: Weather Qualification Data Readiness; Package class: WEATHER_QUALIFICATION_DATA_READINESS; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 20; Frozen base: 77738717fee422fe83d8bb2b7765c36dfbe6b283; Immediate predecessor: PR #201 / S10-NDFD-GRIB-01 merged: YES at that SHA with head cd70800d40f60f4ec20f5b17e107cc56643562a2 (isDraft=false); Historical Alpha predecessor: PR #200 / S10-ALPHA-REAL-01 (RESEARCH_SUPPORTIVE); Current branch: codex/s10-qual-data-01-weather-readiness; readiness: IMPLEMENTATION_READY (RUNTIME); Current S10-QUAL-DATA-01 state: QUAL_DATA_INSUFFICIENT; replacement run (Side14 same-WP correction of D008/D009 and the checkpoint-B diagnostic): Terminal QUAL_DATA_INSUFFICIENT (FROZEN_BUDGET_EXHAUSTED), verify-final VERIFIED (zero network), bundle weatherqualbundle:sha256:ceca0252b4d41cf9b49591bb3a65ed9e0b79d9321b269ecbab86f5a90ea085e1, logical dataset weatherqualdataset:sha256:9058a05354390ca7e61bcb47871f93b925e99571f7cc48f40b057eb0e8454413, 600 discovered / 325 included / 275 excluded markets (225 budget-exhausted), 212 evidence-complete rows (checkpoint A 160, checkpoint B 52) over 12 independent target dates, 0 RULE_SEMANTICS_UNSUPPORTED, b0_contract_compatibility EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION, governed network 4,031 attempts / 2,147,013,454 bytes; superseded defective run (QUAL_DATA_READY weatherqualbundle:sha256:0d37fcab27fb1e4bf128b60dd491a8c9af08d33b7220d38f521bcd2f33c446a6) retained as historical evidence; S10-QUAL-DATA-01 is data formation/readiness only: one bounded public read-only corpus run (PendulumFlow v3, NOAA NDFD PoP12, Gamma-by-id via the existing public client, NWS station metadata) into ignored local evidence; target dates 2026-08-18..2026-09-26; checkpoints MARKET_OBSERVABLE_PLUS_60M_V1 and TARGET_CLIMATE_DAY_START_V1; PendulumFlow v3 is THIRD_PARTY_NATIVE_FRAME_ARCHIVE / EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION, never canonical PIT; b0_contract_compatibility expected EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION; contract docs/qualification_weather_data_readiness_contract.md; operator tools/qualification/run_s10_qual_data_01.py; dependency/workflow changes: 0; qualification/gate/provenance contract changes: 0; QualificationCandidate created: NO; Qualification gate run: NO; WP170/WP172/WP173: NOT STARTED; credentials/scheduler/Hermes/strategy/paper/execution: 0; live: DISABLED; Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders: 0; Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; Merge authorized: NO

# S10-NDFD-GRIB-01 merged historical truth: PR #201 / S10-NDFD-GRIB-01 merged: YES at 77738717fee422fe83d8bb2b7765c36dfbe6b283 with head cd70800d40f60f4ec20f5b17e107cc56643562a2 (isDraft=false); optional ndfd-grib decoder capability retained; historical dependency-WP record follows: NDFD GRIB2 Decoder Dependency Enablement; Package class: RUNTIME_DEPENDENCY_NDFD_GRIB2_ENABLEMENT; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 19; Frozen base: 3d3e3b673e53dae4d2e3b28a6816264b205bb015; Immediate predecessor: PR #200 / S10-ALPHA-REAL-01 merged: YES at that SHA with head 80faf1dcb32d760a15c5de3c008cd2aefa3a6f12 (isDraft=false); triggering blocker: S10-QUAL-DATA-01 source probe SOURCE_COMPATIBILITY_BLOCKED:NDFD_DEPENDENCY_REQUIRED; Current branch: codex/s10-ndfd-grib-01-eccodes; readiness: IMPLEMENTATION_READY (RUNTIME); S10-NDFD-GRIB-01 enables optional offline NDFD GRIB2 decoding only: one optional pyproject extra ndfd-grib with exact pins eccodes==2.48.0 (Python 3.12) and eccodeslib==2.48.0.26 (non-Windows Python 3.12), binary wheels only, no source build, no vendored decoder, no lock file; requires-python >=3.12,<3.15 and the six base pins UNCHANGED; global Python support remains 3.12-3.14; NDFD decoder capability is proven only on ubuntu-24.04 / windows-2022 Python 3.12 (Python 3.13/3.14, macOS, ARM not claimed); committed official NDFD CONUS PoP12 fixture tests/fixtures/ndfd_grib/ndfd_pop12_reference.grib2 (first message of noaa-ndfd-pds wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031046, SHA-256 ecdac869039c2342f8a8ff8c57aa4fef602728e3257d0de7af5c091047c719ea) is a compatibility oracle only, not canonical research evidence; frozen decode fingerprint 0b5e478b2fff21519adbe12a993f0f3106f449343640f0fb521e4e8f792653ec; contract docs/ndfd_grib_decoder_dependency_contract.md; dedicated hosted CI ndfd-grib-compat and ndfd-grib-dependency-audit, existing CI jobs unchanged; src/ changes: 0; product/runtime network: 0; S10-QUAL-DATA-01 may be redrafted/resumed next; S10-QUAL-DATA-01: NOT IMPLEMENTED by this WP; QualificationCandidate created: NO; real qualification gate receipt: NONE; WP170/WP172/WP173: NOT STARTED; credentials/scheduler/Hermes/strategy/paper/execution: 0; live: DISABLED; Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders: 0; Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; Merge authorized: NO

# S10-ALPHA-REAL-01 merged historical truth: PR #200 / S10-ALPHA-REAL-01 merged: YES at 3d3e3b673e53dae4d2e3b28a6816264b205bb015 with head 80faf1dcb32d760a15c5de3c008cd2aefa3a6f12 (isDraft=false); RESEARCH_SUPPORTIVE Alpha seed retained; historical seed-WP record follows: First Real Non-Wallet Alpha Evidence Seed; Package class: FIRST_REAL_NON_WALLET_ALPHA_EVIDENCE_SEED; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 12; Frozen base: f74e183a514d21a28013bf433c79126a68c72389; Immediate predecessor: PR #199 / S10-TEST-WS-01 merged: YES at that SHA with head 99c300421f3404a68b573674d1d6d09e8c363412 (isDraft=false); qualification capability predecessor: PR #198 / S10-GATE-QUAL-01 merged at d7891ed63b4c58c9cc150cd0c750c262ca8e5a74; Current branch: claude/s10-alpha-real-01-seed-746777; readiness: IMPLEMENTATION_READY (RUNTIME); frozen package prompt SHA-256 c7f607f1f388b33b696c228b5393eace5048bbeb87d06343323d52ca5c39e5ea and spec SHA-256 9745d4ceb68c7332d1faed7c10509a949507943191ecd956c51c65bf9edd8e5d; Phase-A manual foreground operator tools/alpha/run_s10_alpha_real_01.py (contract docs/alpha_real_non_wallet_seed_contract.md) for the frozen NWS-resolved Polymarket daily-rain research program: tool-side full-draft capture/revalidation over the merged controlled Hermes runtime (context mode off), one Side13 result-state decision and an exact-set atomic append of one non-wallet Alpha source/candidate/family/episode lineage into a dedicated ignored registry; maximum controller executions 1 and maximum research-child launches 1 only after Karl's separate runtime activation of an exact envelope; rerun/replacement/fallback: 0; USD 5 accepted reported estimated-cost ceiling (not invoice-attested); Current S10-ALPHA-REAL-01 state: ALPHA_REAL_01_SUPPORTIVE; Real research-child launch occurred: YES (exactly one); Attempt consumed: YES (attempt-01; no rerun, no attempt-02); Real Alpha lineage created from provider research: YES; runtime attempt-01 executed exactly once at Phase-A head 4db1cb8e4ffa9cb6122f064faab82d379c74ad44 under Karl-authorized envelope SHA-256 eee8003c216cfd892f54666c030520ec2b8920d20a52d222401e3e7f48c24af0: RUN_VALIDATED, research-child launch count 1, transport_attempt_count 1, api_call_count 9, verified openai-codex / gpt-5.6-sol, receipt hermesresearchreceipt:sha256:69037db6d6df59283da89110998ef17d2854c73c29052039b20acb89ac6cbd0f, accepted reported estimated cost USD 0.0 (cost status included, source none; not invoice-attested), projection SHA-256 d23f304d57eef4d6dc05ee73afe98227d15dbc5a4334aa630569084b17b78064, review bundle SHA-256 14ec89f6760d3d2ae0b2c4751ddc8ec647d1e65b2350735d1b5810e622478be6; Side13 decision RESEARCH_SUPPORTIVE (decision SHA-256 e31d98dd5909ceaa77759932103f878d5c26624366e140ac07a395f8966e96dd); final terminal ALPHA_REAL_01_SUPPORTIVE; 12 usable sources, candidate alphacandidate:sha256:2d1523c8086acf536ad07512e1eaffed9cb9405b65e83c87b89b40ba77ee3add, family alphafamily:sha256:136000bd56f2fc27cf490cf675ddf2715b0acfc1ee934aa5cdf2579925c208d8, episode alphaepisode:sha256:2e4c0f484649930ba2677bc360070f0e9ba6ef0e09ecd23b383a32ff3b69000c; dedicated ignored registry 15 rows, head alpharegistryentry:sha256:4b9a20f7f0e931dfea7cced80a64d7a4be7ccc58e265dbb9ebde15edb2d79847; protected AF1/H1 evidence unchanged; HUMAN_CREDENTIAL_SETUP_REQUIRED: closed by Karl's manual home setup (operator never read credentials); RESEARCH_SUPPORTIVE is not qualification, OOS success, executable edge, profitability, paper, live or Gate C and is not a claim that weather information beats market probability; qualification/data readiness is NOT proven (historical-vintage, price-construction, rule-census, sample/power and PIT facts remain missing; S10-QUAL-REAL-01 must independently establish real dataset refs, PIT provenance, sample/power, a B0/B1/B2 or generic metric plan, critical execution evidence and exact AF1 binding); post-runtime reconciliation changed only six docs paths (operator/tests/prompt/spec unchanged); S10-QUAL-REAL-01 draft eligibility: YES (DRAFT-ELIGIBLE only); S10-QUAL-REAL-01: NOT AUTHORIZED; QualificationCandidate created: NO; qualification gate run: NO; QualificationCandidate/S10-GATE-QUAL-01 evaluation: NOT AUTHORIZED; WP170/WP172/WP173: NOT STARTED; wallet evidence: 0; operator credential access: 0; operator Polymarket product API calls: 0; src/ changes: 0; Dependencies/locks/workflows: UNCHANGED; H1 #5: NOT AUTHORIZED; Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders: 0; Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; Merge authorized: NO

# S10-TEST-WS-01 merged historical truth: PR #199 / S10-TEST-WS-01 merged: YES at f74e183a514d21a28013bf433c79126a68c72389 with head 99c300421f3404a68b573674d1d6d09e8c363412 (isDraft=false); tests-only reconnect synchronization repair retained; historical tests-only WP record follows: Deterministic Reconnect Synchronization in Market WebSocket Tests; Package class: DETERMINISTIC_TEST_SYNCHRONIZATION_REPAIR; Package size class: M; Governance track: FAST; Risk level: 1; Exact changed-file scope: 8; Frozen base: d7891ed63b4c58c9cc150cd0c750c262ca8e5a74; Immediate predecessor: PR #198 / S10-GATE-QUAL-01 merged: YES at that SHA with head ec97a25b3e3174bfa71e3799110e729247dfa026 (isDraft=false); Current branch: codex/s10-test-ws-01-deterministic-reconnect-sync; readiness: IMPLEMENTATION_READY (FAST); tests-only repair of the WP169 Market WebSocket reconnect-test timing flake seen on hosted CI run 36437422894 (windows-2022 / py3.12, assert 1 >= 2): the four wall-clock-sensitive reconnect tests in tests/data_layer/polymarket/test_market_truth_websocket.py now await the observable condition itself (second-connection reconnect subscription payload emitted; HEALED gap evidence persisted; bounded socket #2 open events) with a finite 30s timeout that stops the runner and fails clearly instead of hanging; the real 1s product reconnect backoff is preserved; all existing assertions unchanged; src/ changes: 0; _BACKOFF_SCHEDULE: UNCHANGED; backoff/sleeper injection API: NONE; Dependencies/locks/workflows: UNCHANGED; product network/Hermes/provider/scheduler/credentials: 0; strategy/paper/execution/live/orders: 0; Gate C: NOT AUTHORIZED; capital at risk: USD 0; Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; Merge authorized: NO

# S10-GATE-QUAL-01 merged historical truth: PR #198 / S10-GATE-QUAL-01 merged: YES at d7891ed63b4c58c9cc150cd0c750c262ca8e5a74 with head ec97a25b3e3174bfa71e3799110e729247dfa026 (isDraft=false); deterministic qualification acceptance gate retained; historical gate-WP record follows: Deterministic Qualification Packet Acceptance Gate; Package class: DETERMINISTIC_QUALIFICATION_PACKET_ACCEPTANCE_GATE; Package size class: L; Governance track: FAST; Risk level: 2; Exact changed-file scope: 15; Frozen base: b5cfb9846ff78af2d1a260843d5f2f1a67639305; Immediate predecessor: PR #197 / S10-QUAL-01 merged: YES at that SHA with head 652a2181926ac6f92f72d0013af99ec5e24ba892 (isDraft=false; S10-QUAL-01 remains a non-qualifying packet substrate); Current branch: codex/s10-gate-qual-01-acceptance-gate; readiness: IMPLEMENTATION_READY (FAST); S10-GATE-QUAL-01 deterministic gate implementation is complete on the branch (src/data_layer/analytical_research/qualification_gate.py; contract docs/qualification_gate_contract.md): one immutable content-addressed QualificationGateReceipt under policy qualification-gate-policy/1.0.0 with eight closed dimensions (PACKET_INTEGRITY, CURRENT_RESEARCH_LINEAGE, PREDECESSOR_EVIDENCE, PIT_PROVENANCE_READINESS, SAMPLE_POWER_READINESS, WP170_CROSSING_READINESS, EXECUTION_EVIDENCE_READINESS, AUTHORITY_CONTAINMENT) and QUAL_PASS/QUAL_FAIL/QUAL_INCONCLUSIVE (FAIL precedence; wp170_entry_eligible iff QUAL_PASS); structural rejections return no receipt and are never QUAL_FAIL/QUAL_INCONCLUSIVE; the candidate-bound Alpha head may be an append-only ancestor of the current head; QUAL_PASS is qualification-only (not predictive edge, OOS success, executable edge, profitability, paper, live or Gate C authority); current WP170 B1 public-non-market FeatureDefinition capability is not claimed; qualification.py/experiment_os.py/experiment_registry.py unchanged; No real candidate was created/evaluated by this WP; No real QualificationGateReceipt exists or is persisted by this WP; synthetic terminal outcomes are test fixtures only; first real candidate/evaluation: NOT AUTHORIZED; WP170 experiment/OOS: NOT STARTED / NOT AUTHORIZED by this WP; WP172/WP173: NOT STARTED; wallet qualification: BLOCKED on S10-WALLET-03 -> S10-WALLET-04 -> S10-GATE-WALLET-01 -> real wallet evidence lane; H1 #5: NOT AUTHORIZED; Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders: 0; product network/Hermes/provider/wallet runtime/scheduler/credentials: 0; Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; Merge authorized: NO

# S10-QUAL-01 merged historical truth: PR #197 / S10-QUAL-01 merged: YES at b5cfb9846ff78af2d1a260843d5f2f1a67639305 with head 652a2181926ac6f92f72d0013af99ec5e24ba892 (isDraft=false); non-qualifying packet substrate retained; historical packet-WP record follows: Deterministic Qualification Candidate Packet and WP170 Crossing Contract; Package class: DETERMINISTIC_QUALIFICATION_CANDIDATE_PACKET; Package size class: L; Governance track: FAST; Risk level: 2; Exact changed-file scope: 15; Frozen base: 3b877a01ed797d26fddf81a8936c880692573028; Immediate predecessor: PR #196 / S10-GATE-AF1 merged: YES at that SHA with head d456dafc407d7b079b642fc34cd10781690eb8b0 (AF1_PASS; all ten dimensions PASS; receipt af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2); Current branch: codex/s10-qual-01-qualification-candidate; readiness: IMPLEMENTATION_READY (FAST); implements the deterministic NON-WALLET QualificationCandidate substrate (src/data_layer/analytical_research/qualification.py; contract docs/qualification_candidate_contract.md): one immutable content-addressed advisory packet binding a unique current RESEARCH_SUPPORTIVE Alpha lineage leaf, an AF1_PASS receipt, verified ResearchProvenanceManifest ids/cutoffs, frozen hypothesis/feature/label/split/sample-power/test-family plans, the B0/B1/B2 forecast-evaluation interface and execution-feasibility evidence availability; S10-QUAL-01 itself produces NO QUAL PASS/FAIL/INCONCLUSIVE decision; no real candidate is qualified by this implementation WP; AF1_PASS remains research-system gate success only; qualification feature refs are logical refs and current WP170 B1 public-non-market FeatureDefinition capability is not claimed; feature/model implementation remains WP170; WP170 remains preregistration/OOS authority (experiment_os.py/experiment_registry.py unchanged); wallet-dependent qualification: BLOCKED on S10-WALLET-03/S10-WALLET-04/S10-GATE-WALLET-01 (WALLET_GATE_REQUIRED); next and separately gated: S10-GATE-QUAL-01 (Deterministic Qualification Packet Acceptance Gate); S10-GATE-QUAL-01: NOT AUTHORIZED; WP170 experiment/OOS: NOT STARTED; WP172/WP173: NOT STARTED; H1 #5: NOT AUTHORIZED; Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders: 0; Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; Merge authorized: NO

# S10-GATE-AF1 current finalized research-system gate: Alpha Factory Research-System Quality, Coverage, Reproducibility & Authority Gate; final AF1 outcome: AF1_PASS (research-system gate success only); all ten dimensions: PASS; final AF1GateReceipt: af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2; evidence state: FINALIZED; runtime execution head: dead42658e8fc9139d82f772e1f2fff67ba07674 (Attempt-04 real calls ran only there); final publication head: later post-runtime recovery commit(s) descending from it; post-runtime recovery: explicit Side13/Karl lifecycle-test recovery amendment after the package correctly hard-stopped (nine authorized post-runtime paths: three AF1 lifecycle/status tests plus six evidence/status docs; no source/operator/prompt/spec/gate-contract change); historical pre-reconciliation AF1 handoff a1d96fd55f826f9af063ace2c930353cbe41ed73, original Phase-A checkpoint af07264a6dc85b9a7bfe6016042011685c957554 and Attempt-03 Phase-A head 777b33d5e3eb3ae6814716f45f3dc6a8a673ed16 are historical evidence identities only; LOCAL-EVIDENCE DEFECT CORRECTION 01 retained; historical runtime evidence/envelope 0f7a2680 invalidated and old current workspace quarantined; Package class: ALPHA_FACTORY_RESEARCH_SYSTEM_GATE; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 19; Frozen base: 1ccf42df0e95586b98c79a0bf912343f9c34df31; Immediate predecessor: PR #195 / S10-HERMES-CTX-03 merged: YES at that SHA with head ddc25d189359b6e365edcf08c762cb0552b7170a (canonical public Polymarket identifier secret-scanner compatibility repair); Prior predecessor: PR #194 / S10-HERMES-CTX-02 merged: YES at 15097f70f5f5358879fde73b2b30d26ecdb80402 with head f6b337ce1d4581516c3d10d792034f00043a8a74 (exact pinned stock SOUL.md research-home admission); Runtime dependency: PR #193 / WP164A merged: YES at 70f867bdcd5e97b0dc05d4008c2c023feb461658 with runtime-certified head 1c7de22f31cd093771d6bc0748c440ad5284b105; WP164A dependency certification: COMPLETE; S10-GATE-AF1 blocked by WP164A: NO; Purpose: five immutable AF1 evidence records, exact eight-case deterministic adversarial corpus, ten closed gate dimensions, closed retry_limit=0 envelope schema, exclusive pre-call population sentinel, immediate complete 38-field typed population-result persistence, actual-returned-count population success semantics, one canonical captured_at_utc PIT cutoff, digest-bound manifest/receipt provenance, bounded historical-replay benchmark composition, absolute context-artifact root, typed blinded usefulness review, deterministic replay, and strict no-authority containment; AF1 Attempt-01: CONSUMED / historical invalidated evidence; AF1 Attempt-02: CONSUMED / historical invalidated evidence; AF1 Attempt-03: CONSUMED / TRUE_STOP / PHASE_B_LOCAL_EVIDENCE_DEFECT; Attempt-03 AF1 gate result: NONE; Attempt-03 public population: SUCCEEDED (exactly 1 call; 25 markets / 1 book, built 26, inserted 26; result SHA-256 fcf5a085aef0954f91812f53231405b9746e583886ea950ca2cd91bc0cf9dc8e); Attempt-03 Hermes/provider/model calls: 0; Attempt-03 Firecrawl calls: 0; Attempt-03 accepted provider cost: USD 0; Attempt-03 root cause: shared HERMES request secret-scanner false positive on canonical event:polymarket:0x<64 hex>, repaired by merged PR #195; live-shaped AF1 cross-layer regression: ADDED; AF1 Attempt-04 (s10-gate-af1-attempt-04): CONSUMED / AF1_BLIND_REVIEW_REQUIRED -> FINALIZED / AF1_PASS; Attempt-04 envelope SHA-256: 627fcd4cb6c946cabfb86bb2b38ef18b27b8c7fbb73400314b96adeb1d3530b1; Attempt-04 public population: exactly 1 call, POPULATION_PERSISTED_AND_REGISTERED, 25 markets / 1 book actual, built 26, inserted 26, VALID_WITH_WARNINGS (EVENT_TIME_MISSING_ALLOWED), result SHA-256 9adb1b68420afbd15172a92dca57aec2feffc6b39df82753d97ae15b311534cc, cutoff 2026-09-28T01:54:02.507161Z; benchmark manifest af1manifest:sha256:4af901f88ee52002457f35fae7aa94e30759418d13bd5406534edce56e657b57 (coverage COMPLETE); Attempt-04 population: fresh bounded 25/1 into new empty stores, no Attempt-03 store reuse; Attempt-04 cases C1/C2/C3: RESEARCH_DRAFT_VALIDATED; controller invocations: 3; retry/replacement/fallback/fourth call: 0; provider/model: openai-codex / gpt-5.6-sol; receipt-reported accepted cost: USD 0.0 per case; backend telemetry: NOT_DIRECTLY_ATTESTED; Firecrawl call count: UNKNOWN (no invoice-level cost attestation); blind-review bundle SHA-256: 12058c282bd24d332bb767b7a75c201e4f0b9fcbdebdf0f7cb09c07672a8e74f; independent Side12 blind-review decision SHA-256: eba65849219faf65f27849a6b5be0fe1c1cf27e0cc47bb3ada084afb77d99bc3; review labels: USEFUL_RESEARCH_OUTPUT x3; deterministic reproduction: byte-identical (evidence SHA-256 130a82b5ace6eb2cedf49b540ddd30df48be05cfcc57bf3173b45b452cce22ab); verify-run/verify-review/verify-final: VALID; AF1_PASS does not prove profitability, expected return, qualification, OOS validity, executable edge, paper readiness, live readiness or Gate C; successors: non-wallet S10-QUAL-01 now separately eligible to be drafted/authorized; wallet-specific and ALPHA-03/HERMES-SI paths remain separately gated per roadmap; none authorized; additional AF1 attempt: NOT AUTHORIZED; runtime activation: CONSUMED (no further activation authorized); H1 #5: NOT AUTHORIZED; credentials/OAuth/private keys: 0; scheduler/retry/fallback: 0; qualification/strategy/paper/execution/live/orders: 0; Gate C: NOT AUTHORIZED; capital at risk: USD 0; Dependencies/locks/workflows: UNCHANGED; Merge authorized: NO.

# S10-HERMES-CTX-03 current bounded compatibility repair: Canonical Public Polymarket Identifier Secret-Scanner Compatibility Repair; Package class: BOUNDED_HERMES_PUBLIC_IDENTIFIER_SECRET_SCANNER_COMPATIBILITY_REPAIR; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 11; Frozen base: 15097f70f5f5358879fde73b2b30d26ecdb80402; PR #194 / S10-HERMES-CTX-02 merged: YES; Trigger: S10-GATE-AF1 Attempt-03 = CONSUMED; runtime terminal: TRUE_STOP / PHASE_B_LOCAL_EVIDENCE_DEFECT; public population: SUCCEEDED (exactly 1 public population call); AF1 gate result: NONE; Hermes/provider/model calls: 0; Firecrawl calls: 0; accepted provider cost: USD 0; Root cause: canonical public Polymarket event id event:polymarket:0x<64 hex> false-positive in the shared HERMES request secret scanner (generic rule \b0x[a-fA-F0-9]{40,}\b) when the context controller serialized canonical subject_refs into public_market_context; Repair: local/offline compatibility repair implemented in models.py; public-id compatibility rule: inside public_market_context only, exact complete canonical market:polymarket:<decimal>, event:polymarket:0x<exactly 64 lowercase hex>, event:polymarket:market-<decimal> and the canonical CLOB token id form (polymarket token namespace + <decimal>; exact grammar in the Hermes runtime contract) survive the generic long-hex rule; the generic long-hex rule remains global; malformed canonical-looking event:polymarket: ids fail closed; bare long-hex, wallet/account-shaped, credential and malformed values remain fail-closed; other request fields keep the ordinary strict scan; request identity uses original bytes; schemas and Hermes invocation policy id unchanged; package provider/model/Firecrawl/Polymarket/OAuth calls: 0; network authority: NONE; credential authority: NONE; AF1 branch/workspace/Attempt-03 evidence modified: NO; successor AF1 runtime attempt: NOT AUTHORIZED by this package; H1 #5: NOT AUTHORIZED; Gate C: NOT AUTHORIZED; capital/orders: 0; Dependencies/locks/workflows: UNCHANGED; Merge authorized: NO.

S10-HERMES-CTX-03 history: Attempt-03 is recorded as neither AF1 PASS nor AF1 FAIL; the S10-HERMES-CTX-02 block below records Attempt-03 state as of that package's merge, after which Attempt-03 was executed and CONSUMED; historical S10-HERMES-CTX-01/02 evidence is otherwise unchanged.

# S10-HERMES-CTX-02 current bounded compatibility repair: Pinned Hermes Default SOUL.md Research-Home Compatibility Repair; Package class: BOUNDED_HERMES_DEFAULT_SOUL_RESEARCH_HOME_COMPATIBILITY_REPAIR; Package size class: M; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 10; Frozen base: 70f867bdcd5e97b0dc05d4008c2c023feb461658; PR #193 / WP164A merged: YES; Trigger: S10-GATE-AF1 PHASE_B_LOCAL_EVIDENCE_DEFECT reason HERMES_HOME_CONTROL_PLANE_INVALID; Root cause: merged research-home preflight rejected any SOUL.md while pinned Hermes v0.21.3 (tag v2026.9.14, commit 345cd2b) seeds its stock DEFAULT_SOUL_MD on every home initialization and the controlled runtime rechecks the home before every invocation, so the rule and the pinned runtime were structurally incompatible; Repair: admit SOUL.md only when it is a regular non-symlink file with exact raw bytes of the pinned stock default (667 bytes, SHA-256 36c1f5a2e92cd1d018311eaf4c8f1e8886672eae78212e033c681d0e3d5d506f); every custom/modified/symlinked/non-exact SOUL.md and every other clean-home rule remains fail-closed; admission verification only, no mutation-to-pass; Package: local/offline implementation repair; defect-discovery provider/Firecrawl/Polymarket calls: 0; package provider/model/Firecrawl/Polymarket/OAuth calls: 0; AF1 Attempt-03: UNCONSUMED / NOT AUTHORIZED; AF1 branch modified/rebased: NO; S10-GATE-AF1: BLOCKED until this repair merges, AF1 is reconciled onto repaired main, and a fresh exact Attempt-03 authorization is bound to a new Phase-A head; H1 #5: NOT AUTHORIZED; Gate C: NOT AUTHORIZED; capital/orders: 0; credentials/secrets read: 0; Dependencies/locks/workflows: UNCHANGED; Merge authorized: NO.

S10-HERMES-CTX-02 history: historical S10-HERMES-CTX-01 and S10-GATE-H1 evidence is unchanged; only the universal SOUL.md rejection is narrowed to exact-stock-only admission.

# WP164A merged runtime-certified upstream dependency: Post-WP156A Reconciliation and Attempt-03 Certification; Package class: BOUNDED_PUBLIC_POPULATION_LIVE_COMPATIBILITY_REPAIR; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 14; Historical frozen base: 9332aa2b2591d7e3fb015ae10165f063aeb8fa1d; PR #193 merged: YES; merge commit: 70f867bdcd5e97b0dc05d4008c2c023feb461658; exact runtime-tested head: 1c7de22f31cd093771d6bc0748c440ad5284b105; tested head contained in merged main with zero file difference; PR #193 exact-head hosted CI: PASSED; Historical WP164A candidates: 31379495e70dee1a0d698300e3371911af62de3a / 17ce49aa96c798244d852fc5daf16299bee79ef9 / 53da1d50fb8a91ecdb32cd44611241f0062925ff / 5a7044147c018389402e71f35a759e1d621c4b25; Attempt-01: CONSUMED / WP164A_PUBLIC_SMOKE_LOCAL_EVIDENCE_DEFECT; Attempt-02: CONSUMED / WP164A_PUBLIC_SMOKE_BATCH_INVALID / 25 markets / 1 book / 26 built / 0 inserted / RECORD_VERSION_HASH_COLLISION_OR_MISMATCH / 25 accepted / 0 quarantine / 0 duplicate; Attempt-03: CONSUMED / WP164A_PUBLIC_SMOKE_COMPLETE_SUCCESS / 25 markets fetched / 1 order book fetched / 26 built / 26 inserted / batch valid / 26 unique accepted / 0 quarantined / 0 duplicates / EVENT_TIME_MISSING_ALLOWED warning retained / coordinator invocations: exactly 1 / retries/replacements: 0; observed Attempt-03 counts are historical runtime evidence, not future guarantees; WP164A dependency certification: COMPLETE; S10-GATE-AF1 blocked by WP164A: NO; AF1 Attempt-03: NOT AUTHORIZED; no WP164A Attempt-04; the single-use WP164A operator is expected non-runnable after merge because Attempt-03 is permanently consumed; frozen WP164A prompt/spec/operator/status-fragment pre-smoke wording is historical authorization evidence only; H1 #5: NOT AUTHORIZED; credentials/private keys/signing: 0; strategy/paper/execution/live/orders: 0; capital at risk: USD 0; Dependencies/locks/workflows: UNCHANGED.

WP164A AF1 history: AF1 Attempt-01/02 remain historical invalidated/consumed evidence only; no AF1 authorization is revived by the WP164A upstream correction or its consumed Attempt-03.

# WP156A active upstream correction: Large Canonical Payload Batch Fingerprint Correction; Package class: LARGE_CANONICAL_PAYLOAD_BATCH_FINGERPRINT_CORRECTION; Package size class: L; Governance track: FAST; Risk level: 2; Exact changed-file scope: 12; Frozen base: 46bc862018208b30971228ed719c7e9337142b41; PR #191 / S10-ALPHA-02 merged: YES at that SHA with implementation head 40bcee515251d2e958754bddd3dfae278928ec5c; Trigger: consumed WP164A public-smoke Attempt-02 ended WP164A_PUBLIC_SMOKE_BATCH_INVALID after 25 markets, 1 book, 26 built, 0 inserted, exact batch error RECORD_VERSION_HASH_COLLISION_OR_MISMATCH; deterministic root cause reproduced: a valid ordinary ORDER_BOOK canonical payload can serialize above 4096 characters and the legacy private batch fingerprint re-wrapped it as one bounded string; correction: commit exact canonical payload UTF-8 SHA-256 plus byte length in _record_fingerprint while preserving all true WP156 bounds, public identities, canonical batch material, duplicate/lineage semantics and vocabulary; offline WP164 large-book persistence/registration regression included; WP164A Attempt-02 remains permanently consumed; public/product network calls: 0; Hermes/provider calls: 0; AF1 Attempt-03: NOT AUTHORIZED; credentials/scheduler/strategy/paper/execution/live/orders: 0; capital at risk: USD 0; Dependencies/locks/workflows: UNCHANGED; downstream WP164A reconciliation is separately gated after WP156A review and merge; Merge authorized: YES_CONDITIONAL_BY_SIDE12_FINAL_ONE_SHOT_CLOSURE_AFTER_ALL_EXACT_HEAD_HARD_GATES.

# S10-ALPHA-02 current bounded implementation target: PIT Market-Universe Alpha Discovery, Material Change, Triage, Reopen Decisioning and Research Queue Core; Package class: DETERMINISTIC_PIT_ALPHA_DISCOVERY_CONTROL_PLANE; Package size class: L; Governance track: FAST; Risk level: 2; Exact changed-file scope: 17; Frozen base: a2fba4d770cd6fac1cfb551419d040d65768a8e9; PR #190 / S10-WALLET-02 merged: YES at that SHA with implementation head 2d53af9b3a51f8f9a27334e8bc3b2c40efe6864a; Purpose: deterministic local/offline observed-PIT-universe snapshots, material-change evidence, explicit Alpha-memory temporal posture, complete triage/skip accounting, bounded core/exploration/audit research allocation, prospective capture-request data, and separate append-only discovery memory; schema 1.0.0; discovery registry application id 1464877426; external all-Polymarket completeness: UNPROVEN; product market/wallet network calls: 0; Hermes/provider/model calls: 0; H1 #5: NOT AUTHORIZED; scheduler/campaign: 0; credentials/private keys/signing: 0; qualification/expected-return/strategy/paper/live/orders: 0; Gate C: NOT AUTHORIZED; capital at risk: USD 0; Dependencies/locks/workflows/tools: UNCHANGED; successor after separate review and merge: S10-GATE-AF1; Merge authorized: NO.

# S10-WALLET-02 merged historical truth: PIT Wallet Profiles, Skill, Specialization, Archetypes and Cohorts; Package class: DETERMINISTIC_PIT_WALLET_PROFILE_SNAPSHOT_LAYER; Package size class: L; Governance track: FAST; Risk level: 2; Exact changed-file scope: 17; Frozen base: 45b6cb4db7fc5e8ac2ae21145bf00be658740025; PR #189 / S10-HERMES-CTX-01 merged: YES at that SHA with implementation head bf346a65cf1b93b5e61d2420a8da1629be2bd191; Purpose: immutable content-addressed discovery cohorts, PIT market contexts, and WalletProfileSnapshot research evidence over a read-only verified WALLET-01 ledger, with reconciliation-aware evidence selection, public-account clustering, independent-group sample strength, exact Decimal Jeffreys shrinkage, descriptive specialization, and direct-evidence archetypes; profile schema/policy: 1.0.0 / wallet-profile-policy/1.0.0; profile database: NONE; product wallet/market network calls: 0; Hermes/provider/model calls: 0; H1 #5: NOT AUTHORIZED; credentials/private keys/signing: 0; qualification/strategy/paper/live/orders: 0; Gate C: NOT AUTHORIZED; capital at risk: USD 0; Dependencies/locks/workflows/tools: UNCHANGED; WP79 fixture profile: historical compatibility material, NOT canonical real-evidence profiling; WALLET-03 copyability economics and WALLET-04 incremental value: separately gated; successor S10-ALPHA-02 is now the current separately authorized bounded implementation target; Merge authorized for WALLET-02: COMPLETE BY PR #190.

# S10-HERMES-CTX-01 current implementation target: Blind-First Hermes Context Broker, Reveal Eligibility, Reconciliation & Evidence Verification; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 34; Base SHA: 7495427820c892497e9c195a8b130c2d32102c67; PR #188 / S10-WALLET-01 merged: YES at that SHA; S10-ALPHA-01: COMPLETE; S10-WALLET-01: COMPLETE; Purpose: dormant deterministic campaign/state protocol, blind-artifact barrier, caller-rooted immutable artifact store, exact verified Alpha registry + shared provenance/PIT reveal broker, context claim contract, evidence precedence/grounding/contradiction/falsification/quality gates, managed v0.21.3 memory/profile isolation, and sanitized exact-session telemetry; ordinary H1 compatibility retained; Real Hermes/provider calls: 0; real Firecrawl calls: 0; OAuth/credential changes: 0; wallet/market network calls: 0; paper/live/economic orders: 0; H1 #5: NOT AUTHORIZED; remote Firecrawl HTTP/redirect telemetry: UNAVAILABLE; exact physical provider attempt count: UNKNOWN where same-provider recovery cannot be directly attested; Dependencies/locks/workflows: UNCHANGED; HERMES-SI: no authority; Gate C/capital/orders: unchanged and NOT AUTHORIZED; after separate merge/review the mandatory successor is S10-WALLET-02, then S10-ALPHA-02; Merge authorized: NO.

# S10-WALLET-01 current review target: Public Wallet / Point-in-Time Wallet Evidence Foundation; Side11 capability handle: S10-WALLET-01; Primary package class: PUBLIC_WALLET_EVIDENCE_FOUNDATION; Package size class: XL; Governance track: FAST; Risk level: 2; Base SHA: 584924b5a23e00e13d400885fc50b8eebdd412a3; PR #187 / WP175N / S10-ALPHA-01 merged: YES; Purpose: deterministic, replayable, point-in-time-safe PUBLIC wallet evidence substrate ONLY — shared research provenance/PIT/DQ/replay core (research_provenance.py), new src/data_layer/wallet_intelligence package (contracts/reconciliation/ledger/public_ingest), and bounded public Data API v2 wallet GET reads on the existing client with hard bounds and disabled-by-default policy; Wallet evidence ledger application id 0x57414C31 (proven unique, distinct from Alpha Factory 1464877425 and WP170 1464877424); `/v2/trades` combo state disposition: E2 UNKNOWN (never coerced to FALSE); Network default OFF, GET-only, no retry/sleep/scheduler/daemon; Real wallet/market network calls during implementation/CI: 0; credentials: 0; private keys/signing: 0; authenticated API: 0; Hermes calls: 0; H1 calls: 0; qualification: NO; WP170 experiment creation: NO; paper/live: NO; Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders submitted: 0; Dependencies/locks/workflows: UNCHANGED; WALLET-02: NOT STARTED; HERMES-CTX-01: NOT STARTED; immediate successor after merge/review: S10-HERMES-CTX-01 (separately gated); Merge authorized: NO.

# WP175N current review target: Multi-Lane Alpha Factory Core; Side11 capability handle: S10-ALPHA-01; Primary package class: DETERMINISTIC_MULTI_LANE_ALPHA_FACTORY_CANONICAL_RESEARCH_MEMORY; Package size class: L; Governance track: FAST; Risk level: 2; Exact changed-file scope: 16; Base SHA: b4e53ea509b41d157a3db81beb42226443093191; WP175M / PR #186 merged: YES; S10-GATE-H1: GENUINE_H1_PASS; Accepted H1: H1 #4; Historical real H1 research invocations consumed: 4 (H1 #1, H1 #2, H1 #3, H1 #4, each separately human-authorized); H1 #5: NOT AUTHORIZED; H1 #4 machine terminal: RESEARCH_DRAFT_VALIDATED (openai-codex / gpt-5.6-sol, receipt hermes-research-run-receipt/1.3.0, 22/22 required draft fields, deterministic safety PASS); Side11 independent content review: PASS; HAP-03: configured Firecrawl-only web backend, web_search/web_extract persisted, remote Firecrawl HTTP independently proven: NO (pinned v0.21.3 exposes no downstream backend HTTP telemetry); HAP-04: four separately authorized H1 invocations, no automatic controller rerun/provider-model/backend substitution or automatic paid top-up; WP175N purpose: the first canonical Alpha Factory research-memory substrate ONLY — a standalone record model (src/data_layer/analytical_research/alpha_factory.py) and a bounded append-only SQLite registry (src/data_layer/analytical_research/alpha_factory_registry.py) exported from the analytical_research __init__; Records: ResearchSourceReference/OpportunityCandidate/HypothesisFamily/ResearchEpisode, frozen content-addressed, schema 1.0.0; Primitive evidence lanes: HISTORICAL_REPEATABILITY/FUNDAMENTAL/WEATHER/CROSS_MARKET/RESOLUTION_RULES/MICROSTRUCTURE; COMPOSITE not stored, is_multi_lane derived, lane order identity-invariant; Result states: 9 closed with per-state evidence matrix, exact-scope negative evidence (no global blacklist), append-only reopen; Novelty/mechanism fingerprints deterministic and prose/producer-excluded, separate from record ids; Producer provenance fail-closed; recursive secret/authority key rejection, binary-float rejection, PUBLIC_HTTPS URL boundary, no fetch; Alpha registry: format s10-alpha-factory-registry, integer schema version 1, application id 1464877425 (proven unique, distinct from WP170 1464877424), append-only hash chain + UPDATE/DELETE triggers, caller-order-independent atomic append, projected-history cross refs, tamper detection, read-only verified load, conservative bounds; WP170 experiment_os/experiment_registry (application id 1464877424): UNCHANGED; no ExperimentFamily/AlphaHypothesis/PreregisteredExperiment reuse; HypothesisFamily is NOT ExperimentFamily; no qualification created; zero direct Hermes runtime import; no network; no scheduler; no prioritization; no economics; Wallet-intelligence roadmap anchor: WALLET-01..WALLET-04 + GATE-WALLET-01 frozen, wallet gate CONDITIONAL not global, no live shortcut; immediate software successor after merge/review: S10-WALLET-01 then S10-HERMES-CTX-01, both separately gated and NOT STARTED by WP175N; old monolithic WP180/WP181 Hermes/Alpha sequencing: SUPERSEDED; WP176 decomposed WP176A-E: NOT STARTED; Real H1 research invocations during WP175N: 0; provider/model calls: 0; Firecrawl calls: 0; OAuth operations: 0; Hermes runtime calls: 0; wallet/market network calls: 0; RUNTIME ACTIVATED: NO; S10-ALPHA-01: IMPLEMENTATION_AUTHORIZED (CURRENT_REVIEW_TARGET, merged: NO); Gate C: NOT AUTHORIZED; capital at risk: USD 0; orders submitted: 0; Dependencies/locks/workflows: UNCHANGED; Merge authorized: NO.

# WP175M current review target: Hermes Draft Prompt Contract Alignment And Schema Diagnostics; Side11 capability handle: S10-HERMES-01E; Primary package class: BOUNDED_HERMES_DRAFT_CONTRACT_ALIGNMENT_AND_SCHEMA_DIAGNOSTICS; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 15; Base SHA: b36155201304126339482ea74e77181466181b9c; WP175L / PR #185 merged: YES; Historical real H1 research invocations consumed: 3; H1 #3 terminal status/error: OUTPUT_SCHEMA_INVALID / DRAFT_FIELD_MISSING; H1 #3 runtime perspective: real controlled research/model interaction completed (child exit 0, not timed out, stderr empty, VALID usage, api_call_count 5); H1 #3 exact root cause: PROMPT_OUTPUT_CONTRACT_SCHEMA_NOT_ACTUALLY_EMBEDDED; more precisely: the instruction told Hermes to match a provided research-draft schema but the envelope supplied only draft_schema_version, never the deterministic field contract validate_research_draft enforces; H1 #3 forensic: unique persisted session identified by exact frozen request id, correct schema_version + request_id, all other canonical required fields absent, alternative structured schema improvised (as_of/completeness/cross_category_assessment/evidence_map/generated_at/research_category/research_question/scope/sources), validator first missing canonical field = advisory_only, web_search observed, web_extract observed, unexpected tools = none; remote Firecrawl HTTP independently proven: NO (RUNTIME_TOOL_TELEMETRY = UNAVAILABLE_ON_PINNED_V0_21_3); title_generation usage-row lesson: session_model_usage aggregates an auxiliary title_generation row, so exact aggregate equality is not a safe session-identity method; the main research route usage matched the receipt; WP175M purpose: align the prompt/output contract with the validator BEFORE generation + sanitized schema-failure observability ONLY; canonical draft output contract: models.py build_research_draft_output_schema derived from the SAME constants validate_research_draft enforces (STOP CONTRACT_VALIDATOR_DRIFT), _DRAFT_LIST_FIELDS promoted to public DRAFT_LIST_FIELDS plus canonical ordered DRAFT_REQUIRED_TOP_LEVEL_FIELDS; system instruction version: hermes-research-system-instruction/1.1.0; envelope draft_output_schema embedded in as_mapping/to_query_bytes/to_prompt_string/envelope_digest; authority-flag injection: DECLINED (all draft authority flags remain MODEL-OUTPUT REQUIRED and exactly true, wrapper never injects); substantive post-hoc repair: NONE (a wrong substantive schema still fails closed); sanitized diagnostics: static canonical field-name tokens + fixed statuses only, never rejected values or arbitrary model keys or raw session id; receipt schema: hermes-research-run-receipt/1.3.0 with additive prompt_envelope_sha256/draft_output_contract_sha256/draft_diagnostics_status/draft_present_required_fields/draft_missing_required_fields/draft_first_missing_field/usage_session_id_digest; provider/model evidence preservation: with valid usage the actual provider/model are recorded before draft validation so a schema failure keeps verified provider openai-codex / model gpt-5.6-sol while terminal status stays OUTPUT_SCHEMA_INVALID, mismatch precedence after valid draft UNCHANGED; frozen H1 request id d977b2073c685c64a6398475ba437aa9cc63be517b2260c513ffd4e9ba795b69 reproducible: YES (request identity derives only from public_fields()); Hermes pin/provider/model/toolset/retry/managed-profile/runtime-envelope/request/draft-payload schema: UNCHANGED; response_capture.py/dependencies/locks/workflows: UNCHANGED; H1 real research invocations during WP175M: 0; provider/API calls: 0; Firecrawl research calls: 0; OAuth operations: 0; network activity: 0; MANUAL-HERMES-ACCEPT-01 repeated: NO; RUNTIME ACTIVATED: NO; H1 #4: NOT AUTHORIZED; S10-ALPHA-01: BLOCKED; Gate C: NOT AUTHORIZED; Alpha Factory: NOT STARTED; Wallet-intelligence roadmap anchor: WALLET-01..WALLET-04 + GATE-WALLET-01 frozen, wallet gate NOT global, no live shortcut, WALLET-01 blocked pending genuine H1 PASS + S10-ALPHA-01; WP176 Mature Controlled Live: NOT STARTED; immediate successor after merge/review: post-merge controlled structured-output contract validation using the exact patched runtime, then a SEPARATE human/governance decision on whether a fourth real S10-GATE-H1 run (H1 #4) is justified (three real H1 invocations, H1 #1, H1 #2, and H1 #3, are already consumed; the next possible invocation is H1 #4, which WP175M does NOT authorize); Merge authorized: NO.

# WP175L current review target: Sanitized Windows Runtime Envelope And Startup Preflight; Side11 capability handle: S10-HERMES-01D; Primary package class: BOUNDED_HERMES_WINDOWS_RUNTIME_ENVELOPE_AND_STARTUP_PREFLIGHT; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 12; Base SHA: 473fcd4e6fa95f1230fd29d384f8be736e5085e1; WP175K / PR #184 merged: YES; Historical real H1 research invocations consumed: 2; H1 #2 confirmed root cause: CONTROLLED_WINDOWS_RUNTIME_ENVIRONMENT_INSUFFICIENT_FOR_HERMES_PROFILE_INITIALIZATION; H1 #2 research/provider-model-binding/Firecrawl: NOT_REACHED; decisive sanitized startup failure: RuntimeError Could not determine home directory; pinned call chain: hermes_cli/main.py::_apply_profile_override -> hermes_constants.get_default_hermes_root -> _get_platform_default_hermes_home; why --version missed it: answered by the fast-version path before profile init; WP175K: SUCCESSFUL AS OBSERVABILITY HARDENING; WP175L purpose: hybrid sanitized Windows runtime envelope + real startup preflight ONLY; runtime envelope: EXPLICIT_BENIGN_ALLOWLIST_NEVER_OS_ENVIRON_COPY; Finding E (Side11 exact-head review of c73934c): forwarding the real per-user LOCALAPPDATA/USERPROFILE let pinned hermes_cli/main.py::_apply_profile_override read a sticky personal %LOCALAPPDATA%/hermes/active_profile and re-home the explicit H1 HERMES_HOME; corrected to a HYBRID envelope; Windows MACHINE allowlist forwarded from real parent: COMSPEC/PATHEXT/WINDIR/OS/PROCESSOR_ARCHITECTURE/NUMBER_OF_PROCESSORS/PROGRAMDATA/PROGRAMFILES/PROGRAMFILES(X86)/COMMONPROGRAMFILES; Windows PER-USER roots SYNTHETIC/CONTROLLED (never real parent): USERPROFILE/HOMEDRIVE/HOMEPATH/APPDATA/LOCALAPPDATA derived under a backend-owned ephemeral runtime-user root so Path.home() works, the pinned default root resolves under a controlled LOCALAPPDATA carrying no unrelated active_profile, and the explicit H1 HERMES_HOME stays authoritative; secret-name rejection: RETAINED; injection/capability denylist: ADDED; ambient provider credentials forwarded: NO; startup preflight: hermes --help offline, same hybrid envelope, synthetic per-user roots, throwaway HERMES_HOME, STARTUP_PREFLIGHT_FAILED fails closed with transport_attempt_count 0 and no H1 slot consumed; provider/model/toolset/retry/managed-profile/request/draft/receipt-schema/failure-precedence: UNCHANGED; models.py/policy.py/response_capture.py/__init__.py/dependencies/locks/workflows: UNCHANGED; H1 real research invocations during WP175L: 0; provider/API calls: 0; Firecrawl research calls: 0; OAuth operations: 0; network activity: 0; MANUAL-HERMES-ACCEPT-01 repeated: NO; RUNTIME ACTIVATED: NO; H1 #3: NOT AUTHORIZED; S10-ALPHA-01: BLOCKED; Gate C: NOT AUTHORIZED; Alpha Factory: NOT STARTED; Wallet-intelligence roadmap anchor: WALLET-01..WALLET-04 + GATE-WALLET-01 frozen, wallet gate NOT global, no live shortcut, WALLET-01 blocked pending genuine H1 PASS + S10-ALPHA-01; WP176 Mature Controlled Live: NOT STARTED; immediate successor after merge/review: a CONTROLLED STARTUP PREFLIGHT using the exact patched runner, then a SEPARATE human/governance decision on whether a third real S10-GATE-H1 run (H1 #3) is justified (two real H1 invocations, H1 #1 and H1 #2, are already consumed; the next possible invocation is H1 #3, which WP175L does NOT authorize); Merge authorized: NO.

# WP175K current review target: Sanitized Hermes Failure-Evidence Capture Hardening; Side11 capability handle: S10-HERMES-01C; Primary package class: BOUNDED_HERMES_SANITIZED_FAILURE_EVIDENCE_HARDENING; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 14; Base SHA: e4323305a9ab6d8434ad451942420606f9252ff9; WP175J / PR #183 merged: YES; Incident: S10-GATE-H1 single authorized real invocation consumed = 1, result FAIL_RUNTIME_CONTRACT / EXIT_CODE_NONZERO, usage evidence MISSING, validated research NONE, sources 0; DIAG-01: ROOT_CAUSE_NARROWED_NOT_CONFIRMED; DIAG-02: PREACCOUNTING_PATHS_PASS_ROOT_CAUSE_STILL_UNRECOVERABLE; genuine H1 PASS: NO; WP175K purpose: sanitized failure-evidence capture hardening ONLY; receipt schema: hermes-research-run-receipt/1.2.0; raw stderr: FORBIDDEN_SANITIZED_BOUNDED_EXCERPT_ONLY; MAX_SANITIZED_STDERR_EXCERPT_BYTES: 4096; provider/model/toolset/retry/managed-profile/failure-precedence: UNCHANGED; H1 real research invocations during WP175K: 0; provider/API calls: 0; Firecrawl research calls: 0; OAuth operations: 0; network activity: 0; RUNTIME ACTIVATED: NO; H1 rerun: NOT_AUTHORIZED; S10-ALPHA-01: BLOCKED; Gate C: NOT AUTHORIZED; Alpha Factory: NOT STARTED; dependencies/locks/workflows: UNCHANGED; immediate successor after merge/review: a SEPARATE human/governance decision on whether a second real S10-GATE-H1 run is justified, not Alpha and not an automatic rerun; WP176 Mature Controlled Live: NOT STARTED; Merge authorized: NO.

# WP175J current review target: Hermes Version Banner Preflight Parser Correction; Side11 capability handle: S10-HERMES-01B; Primary package class: BOUNDED_HERMES_VERSION_BANNER_PREFLIGHT_CORRECTION; Package size class: L; Governance track: RUNTIME; Risk level: 3; Exact changed-file scope: 12; Base SHA: 0bc994c6659c6175ed7cf45cb7149ead51774344; WP175I / PR #182 merged: YES; Parser defect: the generic first-semver search skipped v0.21.3 and selected release date 2026.9.14 from `Hermes Agent v0.21.3 (2026.9.14)`; correction: Hermes-branded package-version extraction with no generic fallback; AppContainer launcher issue: SETUP_ONLY_RESOLVED_SEPARATELY; exact non-virtualized CLI succeeds: YES; H1 real research invocations: 0; provider/API calls: 0; Firecrawl research calls: 0; RUNTIME ACTIVATED: NO; Gate C: NOT AUTHORIZED; Alpha Factory: NOT STARTED; dependencies/locks/workflows: UNCHANGED; immediate successor after merge/review: fresh-human-authorized S10-GATE-H1 resumed; S10-ALPHA-01 remains blocked on genuine H1 PASS plus Side11 review; WP176 Mature Controlled Live: NOT STARTED; Merge authorized: NO.

# WP175I current review target: Controlled Research Profile Enforcement; Side10 capability handle: S10-HERMES-01A; Primary package class: BOUNDED_CONTROLLED_RESEARCH_PROFILE_ENFORCEMENT_CORRECTION; Package size class: L; Governance track: RUNTIME; Deterministic readiness: IMPLEMENTATION_READY_NO_CERTIFICATE; Risk level: 3; Implementation posture: LOCAL_SOFTWARE_ONLY_EXTERNAL_RUNTIME_POLICY_CORRECTION_NO_REMOTE_ACTIVATION; Exact changed-file scope: 15; Base SHA: 3e5dd322800e656f942d46c768fc93aa7ac2e7ea; WP175H / PR #181 merged: YES; Pinned external runtime: Hermes Agent v0.21.3 (tag v2026.9.14, commit 345cd2b) UNCHANGED; Research argv safe-mode: REMOVED; Research argv ignore-user-config/ignore-rules: RETAINED; Controlled managed scope: EPHEMERAL_REPO_OWNED_NON_SECRET_MANAGED_DIR; Firecrawl search/extract: PINNED; Web keyless fallback/rescue: OFF; Web cache: OFF; Fallback providers: EMPTY; agent.api_max_retries: 1; Same-provider primary transport recovery: ALLOWED_BOUNDED; Custom/user/project plugin loading: FORBIDDEN; Pinned bundled backend discovery: ALLOWED; Allowed toolset: web only; Hermes invocation policy schema: 2.0.0; S10-GATE-H1 first attempt: FAIL / SOFTWARE_GAP / H1_BLOCKED_BEFORE_REMOTE_ACTIVATION; Prior H1 real research invocations: 0; OAuth initiated: NO; Firecrawl secret requested/used: 0; H1 authorization consumed: NO; CODE COMPLETE: YES; RUNTIME ACTIVATED: NO; Real provider-backed research run: NO; Real provider/model call count: 0; Product web call count in implementation/CI: 0; Credentials created/used: 0; Real orders submitted: 0; Capital at risk: USD 0; Dependencies/lock/workflow files: UNCHANGED; WP170/WP172/WP173/WP175 semantics: UNCHANGED; models.py and response_capture.py: UNCHANGED; WP175 merged dormant: YES; Gate-C activation: NOT AUTHORIZED; LIVE_PATH_EVIDENCE_READY: NOT CLAIMED; First real run separately gated: S10-GATE-H1 Controlled Public Research Pilot resumes only after WP175I merge and Side10 review, then S10-ALPHA-01 Multi-Lane Alpha Factory Core, both NOT STARTED; WP176 Mature Controlled Live: NOT STARTED; Merge authorized: NO.

# WP175H merged (S10-HERMES-01, PR #181): Controlled Hermes Research Runtime Core; Side10 capability handle: S10-HERMES-01; Primary package class: CONTROLLED_EXTERNAL_HERMES_RESEARCH_RUNTIME_CORE; Package size class: XL_FOR_SCOPE_SIZE_ONLY; Governance track: RUNTIME; Deterministic readiness: IMPLEMENTATION_READY_NO_CERTIFICATE; Risk level: 3; Implementation posture: DORMANT_BY_DEFAULT_BOUNDED_EXTERNAL_HERMES_ONESHOT_RESEARCH_CONTROLLER; Exact changed-file scope: 24; Base SHA: 22557ee3b0beeeb13a3c3b626ae8f30e11967364; WP175E / PR #180 merged: YES; Pinned external runtime: Hermes Agent v0.21.3 (tag v2026.9.14, commit 345cd2b); REAL_HERMES_BINARY_NOT_PRESENT: activation prerequisite not a code blocker; Allowed toolset: web (web_search + web_extract) only; Tool isolation proven: YES; Filesystem isolation (ephemeral empty cwd, never repo/home/local_data): YES; CODE COMPLETE: YES; RUNTIME ACTIVATED: NO; Real provider-backed research run: NO; Real provider/model call count: 0; Product web call count in implementation/CI: 0; Credentials created/used: 0; Real orders submitted: 0; Capital at risk: USD 0; Dependencies/lock/workflow files: UNCHANGED; WP170/WP172/WP173/WP175 semantics: UNCHANGED; Legacy WP99/WP133/WP145 advisory validators: UNCHANGED; Hermes prose is untrusted research content, never canonical economic truth; WP175 merged dormant: YES; Gate-C activation: NOT AUTHORIZED; LIVE_PATH_EVIDENCE_READY: NOT CLAIMED; First real run separately gated: S10-GATE-H1 Controlled Public Research Pilot then S10-ALPHA-01 Multi-Lane Alpha Factory Core, both NOT STARTED; WP176 Mature Controlled Live: NOT STARTED; Merge authorized: NO.

# WP175E current review target: Native Continuity-Attested Market Truth Bridge; Side10 capability ID: S10-DATA-03; Primary package class: LOCAL_OFFLINE_NATIVE_CONTINUITY_MARKET_TRUTH_BRIDGE; Package size class: L; Governance track: FAST; Deterministic readiness: IMPLEMENTATION_READY_NO_CERTIFICATE; Risk level: 2; Implementation posture: WP169_NATIVE_ACCEPTED_WS_EVIDENCE_TO_WP172_ADVISORY_MARKET_TRUTH_ONLY; Exact changed-file scope: 20; Base SHA: 195cc1a42b73d08185f96c613d9a95154f919102; WP175D / PR #179 merged: YES; WP175D merge commit: 195cc1a42b73d08185f96c613d9a95154f919102; S10-EVID-01B result: EVIDENCE_INCONCLUSIVE; Genuine PMXT external research path remains valid: YES; PMXT AS_CAPTURED reclassified: NO; New public surface: additive bounded WP169 read evidence + NativeContinuityAttestation + NativeMarketTruthWindow + native builder/validator; Native source_capture_id: DERIVED_FROM_DURABLE_WS_SESSION; WP169 APPLICATION_ID/USER_VERSION/DDL/indexes: UNCHANGED; Existing PMXT MarketTruthWindow/API/identity: UNCHANGED; Evaluator classification/fee/fill/capacity/net-edge rules: UNCHANGED; WP173 binding/fill/accounting/risk/reconciliation: UNCHANGED; Dependencies/lock/workflow files: UNCHANGED; Required product network: NONE; Credentials created/used: 0; Real orders submitted: 0; Capital at risk: USD 0; WP169-D001: NARROWED_ONLY_TO_WP169_NATIVE_TO_WP172_BRIDGE_EXTENT; Generic PIT-to-Nautilus adapter claimed: NO; WP175 merged dormant: YES; WP175 Gate-C activation: NOT AUTHORIZED; LIVE_PATH_EVIDENCE_READY: NOT CLAIMED; WP176 Mature Controlled Live: NOT STARTED; Successor: SEPARATELY_GATED_PREREGISTERED_PROSPECTIVE_EVIDENCE_RUN_AFTER_MERGE; Merge authorized: NO.

# S10-EVID-01B completed before WP175E with `EVIDENCE_INCONCLUSIVE`: genuine PMXT v2 evidence reached WP170/WP172, but the tested candidate did not satisfy first-look OOS criteria and PMXT `AS_CAPTURED` correctly remained continuity-incomplete. WP175E does not rewrite that result or tune a replacement candidate.

# WP175D current review target: External Historical Research Bridge; Side10 capability ID: S10-DATA-02; Primary package class: LOCAL_OFFLINE_EXTERNAL_HISTORICAL_RESEARCH_BRIDGE; Package size class: XL_FOR_SCOPE_SIZE_ONLY; Governance track: FAST; Deterministic readiness: IMPLEMENTATION_READY_NO_CERTIFICATE; Risk level: 2; Implementation posture: LOCAL_OFFLINE_EXTERNAL_HISTORY_PROVENANCE_BRIDGE_ONLY; Exact changed-file scope: 24; Base SHA: 489c6f9548c39cb3bcb2196a81d5352a0d1dd653; Dependencies/lock/workflow files: UNCHANGED; Network: NONE; Downloader: NONE; Credentials created/used: 0; Capital at risk: USD 0; Orders submitted: 0; Paper/strategy/execution/live: NONE; Canonical PIT authority unchanged: YES; External provenance preserved: YES; New public surface: PmxtV2ResearchLineage + ExternalDatasetBinding + PMXT->WP170 bridge; Registry: ExternalDatasetBinding persists under existing DATASET_BINDING kind by exact schema_id dispatch (REGISTRY_FORMAT_ID/REGISTRY_SCHEMA_VERSION/REGISTRY_APPLICATION_ID unchanged, no migration); WP175 merged dormant: YES; WP175 PR: 178; WP175 merge commit: 489c6f9548c39cb3bcb2196a81d5352a0d1dd653; WP175-D002 / S10-DATA-02: CLOSES_ON_WP175D_MERGE; WP175 Gate-C activation: NOT AUTHORIZED; LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE remains true until genuine evidence is later produced; First post-WP175D action: S10-EVID-01 genuine strategy evidence production gate (not automatic live activation); WP176 Mature Controlled Live: NOT STARTED; Merge authorized: NO.

# WP175 current review target: Restricted Live Canary; Primary package class: PROTECTED_RESTRICTED_LIVE_CANARY; Package size class: XL_FOR_SCOPE_SIZE_ONLY; Governance track: PROTECTED; Independent exact-hash certification: PASS_ALL_TWELVE_LENSES; Deterministic readiness: IMPLEMENTATION_READY; Phase-A/B authorization: YES_FOR_CERTIFIED_BYTES; Runtime authority: A0_DISABLED / A1_READ_ONLY / A2_SHADOW / A3_RESTRICTED_LIVE only while a valid manual arm receipt is active; Gate-C activation: PENDING_SEPARATE_EXACT_HEAD_HUMAN_AUTHORIZATION; Strategy qualification: LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE; Real secret used in implementation/CI: NO; Real economic CREATE count: 0; Capital at risk: USD 0; Mature/unattended live: FORBIDDEN_WP176; Dependencies/lock/workflow files: UNCHANGED; Exact changed-file scope: 30; WP174B merged: YES; WP174B PR: 177; WP175 PR: 178; Dormant-merge prerequisite: FINAL_MERGE_SMOKE_CREATE_ATTEMPTS=0 (disabled Gate-C code is merge-eligible with zero real economic CREATEs, pending a separate Karl exact-head merge authorization); First live canary: FIRST_LIVE_ACTIVATION_CANARY_CREATE_ATTEMPTS=1 POST-MERGE only; LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE is an activation-only blocker (see deferred S10-DATA-02); Merge authorized: NO.

- WP174B current review target: Gate-B Production Credential, Signing & Real-Mutation Enablement; Primary package class: PROTECTED_GATE_B_PRODUCTION_CREDENTIAL_SIGNING_MUTATION_ENABLEMENT; Package size class: XL_FOR_SCOPE_SIZE_ONLY; Governance track: PROTECTED; Independent exact-hash certification: PASS_ALL_TWELVE_LENSES; Deterministic readiness: IMPLEMENTATION_READY; Phase-B authorization: YES_FOR_CERTIFIED_BYTES; Runtime authority: A0_DISABLED / A1_READ_ONLY / A2_SHADOW_ONLY; Gate-B capability: B0_LOCKED_TO_B4_ORTHOGONAL_TO_AUTHORITY; Real-secret loading: EPHEMERAL_NO_ECHO_NEVER_PERSISTED; L2 credentials: IN_MEMORY_NEVER_PERSISTED; Real local LIMIT signing: PROVEN_WITHOUT_POST; Real cancellation transport: GATE_B_ENABLED; Real economic CREATE: FORBIDDEN_GATE_C; A3_RESTRICTED_LIVE: ABSENT; Live capital: FORBIDDEN_GATE_C; Capital at risk: USD 0; Wallet deployment/funding/approvals/transfers/Session Keys/Builder/Relayer: NONE; Architecture: official polymarket-client==0.10.0 unchanged plus narrow repo-owned Gate-B module and operator command; websockets: 15.0.1; Dependencies/lock/workflow files: UNCHANGED; Exact changed-file scope: 22; Unresolved decisions: 0; WP174 merged: YES; WP174 PR: 176; WP174 final head: 6fff7fefd8f936824a7586f94d452ca073b225dd; WP174 merge commit: dbb4ee0e21e409c4639edc44cce17696a5b15156; WP174-D001 Real secret loading and real SDK signing/mutation: RESOLVED_WP174B; WP175 Restricted Live Canary: SEPARATELY_GATED_NOT_STARTED; PR: 177; Merge authorized: NO.
- WP174 current review target: Protected Authentication, Signing & Execution Gateway; Primary package class: PROTECTED_AUTH_SIGNING_EXECUTION_GATEWAY; Package size class: XL_FOR_SCOPE_SIZE_ONLY; Governance track: PROTECTED; Independent exact-hash certification: PASS_ALL_TWELVE_LENSES; Deterministic readiness: IMPLEMENTATION_READY; Gate A authorization: YES_FOR_CERTIFIED_BYTES; Runtime authority: A0_DISABLED / A1_READ_ONLY / A2_SHADOW_ONLY; Real-secret loading: FORBIDDEN_GATE_B; Real venue mutation: FORBIDDEN_GATE_B; A3_RESTRICTED_LIVE: ABSENT; Live capital: FORBIDDEN_GATE_C; Capital at risk: USD 0; Initial order surface: LIMIT_ONLY; Architecture: official polymarket-client==0.10.0 plus narrow repo-owned gateway and SQLite journal; websockets: 15.0.1; Exact changed-file scope: 24; Unresolved decisions: 0; WP173 merged: YES; WP173 PR: 175; WP173 final head: 79e2953dee8754dc8d09781edd647202dee834aa; WP173 merge commit: e0202750c1e6f2a3a885aa6efa04bbd8d0b2291a; WP175 Restricted Live Canary: SEPARATELY_GATED_NOT_STARTED; Merge authorized: NO.

- WP173 current review target: Serious Paper Trading System + Paper Cockpit; Primary package class: SERIOUS_PAPER_RUNTIME_ACCOUNTING_RISK_RECONCILIATION_COCKPIT; Package size class: XL_FOR_SCOPE_BUDGET_ONLY; Governance track: RUNTIME; Deterministic readiness: IMPLEMENTATION_READY_NO_CERTIFICATE; Risk level: 3; Implementation posture: SIMULATED_PAPER_ONLY_MANUAL_FOREGROUND_RUNTIME; Merge authorized: NO; Exact changed-file scope: 31; Dependencies/lock/workflow files: UNCHANGED; New external product network: NO; Local WP169 store access: READ_ONLY; Existing cockpit loopback: PRESERVED; Credentials/signing/private account/real order/live execution: NONE; Capital at risk: USD 0; WP172 merged: YES; WP172 PR: 174; WP172 final head: 39363e5a081b6737104260725b1b0c8fcffe9196; WP172 merge commit: 418bae72f24b0694eccc657ed5dc3f90a3f38f2a; Obsolete Hermes WP172: SUPERSEDED_OFF_CRITICAL_PATH; Next major capability: WP174_AUTH_SIGNING_EXECUTION_GATEWAY_SEPARATELY_GATED_NOT_STARTED; Later: WP175_RESTRICTED_LIVE_CANARY_THEN_WP176_MATURE_CONTROLLED_LIVE; Hermes/alpha automation may proceed later in parallel during paper soak and is not a paper gate.

- WP172 current review target: Alpha + Executable Edge MVP; Primary package class: LOCAL_OFFLINE_EXECUTABLE_EDGE_RESEARCH; Package size class: XL_FOR_SCOPE_BUDGET_ONLY; Governance track: FAST; Deterministic readiness: IMPLEMENTATION_READY_NO_CERTIFICATE; Risk level: 2; Implementation posture: LOCAL_OFFLINE_COST_AWARE_RESEARCH_ONLY; Ready for review: YES; Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; Merge authorized: NO; Exact changed-file scope: 18; Dependencies/lock files: UNCHANGED; Product/runtime network calls: 0; Credentials created/used: 0; Capital at risk: USD 0; Orders submitted: 0; Paper/real/live execution: NOT AUTHORIZED; WP171G merged: YES; WP171G PR: 173; WP171G final head: 140f5d23b771c7596eb0aa716eebbb7a376e0f7d; WP171G merge commit: 82546d8390540f68cd427149e29bc67069513754; Obsolete Hermes WP172 work: PARKED_SUPERSEDED_NOT_CRITICAL_PATH; Next phase: WP173_SERIOUS_PAPER_TRADING_SYSTEM_SEPARATELY_GATED_NOT_STARTED

- WP171G canonical transition: Lean Agent Execution Governance is the one-time review target after merged WP171; Primary package class: WORKFLOW_GOVERNANCE_EXECUTION_ACCELERATION; Package size class: L; Governance track for WP171G itself: PROTECTED_LEGACY_FINAL_USE; Prompt authority mirror: REQUIRED_EXACT_RISK_PLUS_16_BOOLEAN_SPEC_EQUALITY; Certificate-free package-guard result: NULL_NOT_RUN; Ready for review: YES_INDEPENDENTLY_CERTIFIED; Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; Merge authorized: NO; Runtime/product impact: NONE; Dependencies/lock files: UNCHANGED; Credentials/orders/capital at risk: NONE/USD 0; WP171 merged: YES; WP171 PR: 172; WP171 final head: a650c08ab233e47beca7565a5bb8df11a4f41d02; WP171 merge commit: d6a15e4007fe3ced5a7d059ec3fcdec496d2dc7d; Canonical successor after WP171G: WP172 — Alpha + Executable Edge MVP — SEPARATELY_GATED_NOT_STARTED

## Historical snapshot through WP171 review

- Current phase: WP171 Interactive Operator Cockpit MVP is the current review target following merged WP170, with historical merged-state compatibility floor WP130; Primary package class: INTERACTIVE_OPERATOR_COCKPIT_MVP; Repository validation class: local-read-only-loopback-operator-view; Package size class: XL; XL explicit authorization: YES_FOR_SCOPE_BUDGET_ONLY; Risk level: 2; Implementation posture: LOCAL_OPERATOR_READ_ONLY_COCKPIT_NO_EXECUTION_AUTHORITY; Ready for review: YES_INDEPENDENTLY_CERTIFIED; Independent draftability certificate: PASS_ALL_TWELVE_LENSES; Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; Merge authorized: NO; Independent live PR review required: YES; Exact changed-file scope: 26; New optional Python dependencies: fastapi==0.141.1, uvicorn==0.52.4; Frontend exact dependencies: react==19.3.0, react-dom==19.3.0, vite==8.3.0, typescript==7.0.2, @types/react==19.3.0, @types/react-dom==19.3.0; Node CI: 24.18.0 LTS; External data downloader: NONE; Product/runtime external network calls: 0; Local loopback browser/API: AUTHORIZED; Credentials created/used: 0; Capital at risk: USD 0; Orders submitted: 0; Authoritative WP169/WP170 writes: 0; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; Canonical PIT authority unchanged: YES; No credentials/authenticated/signing/orders/OMS/Hermes/strategy/paper/risk/execution/live: YES; WP169 merged: YES; WP170 merged: YES; WP170 PR: 171; WP170 final head: 8e5d83f695d2f2ef38c9f30e3a8e95eb271718da; WP170 merge commit: 434af62f0891959d145b631a77b472b3e80915d3; Historical WP170 predecessor evidence: following merged WP169; Primary package class: FALSIFICATION_GRADE_EXPERIMENT_REGISTRY_AND_RESEARCH_DATASET_OS; Package size class: XL; XL explicit authorization: YES; Risk level: 2; Implementation posture: LOCAL_OFFLINE_DETERMINISTIC_APPEND_ONLY_RESEARCH_CONTROL_NO_EXECUTION_AUTHORITY; New direct runtime dependency: NONE; Default network posture: OFF; Product/runtime network calls: 0; Direct Nautilus ingestion claimed: NO; WP161 merged: YES; WP166 merged: YES; WP167 merged: YES; WP168 merged: YES; WP168G merged: YES; WP169 merged: YES; WP169 PR: 170; WP169 final head: c4a09aeb33e4c271feb709622660e5e58a00b642; WP169 merge commit: 17df81001171988e9ca49f92dc8fd170ecaa7103; Next phase: WP171_INTERACTIVE_OPERATOR_COCKPIT_SEPARATELY_GATED; Next phase: WP172 — Hermes Runtime + Alpha Factory — SEPARATELY_GATED
- WP156 same-PR integrity follow-up status: F_G_H_FAIL_CLOSED_CORRECTION_COMPLETE; quarantine caller-derived optional fields project to `None`; complete record-specific/envelope metadata is committed into record-version identity; builder-equivalent batch revalidation excludes tampered records from accepted IDs and usable lineage; single-record and paired same-ID tampering are covered; authority and dependency posture unchanged
- Repo state: WP95 records the accepted Hermes/research-brain execution plan; WP96-WP98 record the advisory architecture, contract requirements, and manual prompt/runbook foundation; WP99 records the local/offline/read-only advisory output validator; WP100 records the local/offline/read-only in-memory context-packet builder foundation; WP101 records the local/offline/read-only in-memory context-packet dry-run receipt foundation; WP102 records the local/offline/read-only in-memory manual research dry-run operator review record foundation; WP103 records the local/offline/read-only in-memory candidate-review context packet integration adapter; WP104 records the local/offline/read-only in-memory candidate-review manual chain smoke helper; WP105 records the docs/status/tests-only candidate-review operator handoff contract; WP106 records the local/offline/read-only in-memory candidate-review operator handoff object implementation; WP107 records the docs/status/tests-only candidate-review handoff local manual export contract; WP108 records the local/offline/read-only in-memory candidate-review handoff manual export artifact builder; WP109 records the local/offline/manual-only explicit file writer for valid WP108 artifact output only; WP110 records a docs/status/tests-only manual operator runbook for using the WP109 writer safely; WP111 records a docs/status/tests-only temp-only pytest smoke exercise for the existing WP106 -> WP108 -> WP109 path using synthetic safe fixture data and pytest tmp_path only; WP112 records a docs/status/tests-only closeout and next-phase decision record for the bounded WP106 -> WP108 -> WP109 -> WP110 -> WP111 manual export chain; WP113 records a docs/status/tests-only future CLI-wrapper contract for the completed WP106 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 local manual export chain; WP114 records a docs/status/tests-only CLI command-surface and strict input-handoff contract; WP115 records the local/offline/manual CLI wrapper implementation around the existing WP109 writer for strict WP108 artifact-result JSON envelopes only; WP116 records a docs/status/tests-only operator runbook and smoke receipt for safe manual use of the existing WP115 CLI; WP117 records a docs/status/tests-only CLI chain closeout and research-workflow transition decision record stating the local/manual export chain through WP116 is complete enough for bounded operator use and the next recommended phase is Hermes-assisted candidate-review research workflow, not paper/live trading; WP118 records a docs/status/tests-only Hermes candidate-review research workflow intake contract for manual/local/offline/advisory-only human-reviewed selection of already-valid upstream candidate-review packets or export artifacts; WP119 records a docs/status/tests-only Hermes candidate-review research workflow runbook for manual/local/offline/advisory-only operator review after WP118 intake and before future schemas/storage/implementation; WP120 records a docs/status/tests-only Hermes candidate-review research question record contract for future manual/local/offline/advisory-only planning records after WP118 intake and WP119 runbook; WP121 records a local/offline/read-only in-memory Hermes candidate-review research question record validator/build/assert layer implementing the WP120 contract for explicit caller-supplied mappings only; WP122 records a local/offline/read-only in-memory Hermes candidate-review advisory output validation receipt validator/build/assert layer for explicit caller-supplied mappings only; WP123 records a local/offline/read-only in-memory Hermes candidate-review human decision and follow-up research task record validator/build/assert layer for explicit caller-supplied mappings only; no product/runtime network, no credentials, no account/order/private state, no paper/live, no execution/risk/order, no scheduler/dashboard/bot-loop, no Hermes runtime/provider/model/prompt runner, no parser/loader/writer/storage path, no CLI, no report/export pipeline, no dependency/workflow/lock-file, no copied external code, and no committed generated-artifact behavior changes
- Merged WPs: WP1, WP2, WP3, WP4, WP5, WP6, WP7, WP8, WP9, WP10, WP10-Follow-up, WP11, WP12, WP13, WP14, WP15, WP16, WP17, WP18, WP19, WP20, WP21, WP22, WP23, WP24, WP25, WP26, WP27, WP28, WP29, WP30, WP31, WP32, WP33, WP34, WP35, WP36, WP37, WP38, WP39, WP40, WP41, WP42, WP43, WP44, WP45, WP46, WP47, WP48, WP49, WP50, WP51, WP52, WP53, WP54, WP55, WP56, WP57, WP58, WP59, WP60A, WP61, WP62, WP63, WP64, WP65, WP66, WP67, WP68, WP69, WP70, WP71, WP72, WP73, WP74, WP75, WP76, WP77, WP78, WP79, WP80, WP81, WP82, WP83, WP84, WP86, WP87, WP88, WP89, WP90, WP91, WP92, WP93, WP94, WP95, WP96, WP97, WP98, WP99, WP100, WP101, WP102, WP103, WP104, WP105, WP106, WP107, WP108, WP109, WP110, WP111, WP112, WP113, WP114, WP115, WP116, WP117, WP118, WP119, WP120, WP121, WP122, WP123, WP124, WP125, WP126, WP127, WP128, WP129, WP130, WP131, WP132, WP133, WP134, WP135, WP136, WP137, WP138, WP139, WP140, WP141, WP142, WP143, WP144, WP145, WP146, WP147, WP148, WP149, WP150, WP151, WP152, WP153, WP154, WP155, WP156, WP157, WP158, WP159, WP160, WP161, WP162, WP163, WP164, WP165, WP166, WP167, WP168, WP168G, WP169, WP170
- Current branch: see GitHub PR metadata and PR body; committed status docs are authored as stable post-merge target repo truth
- Multi-agent coding workflow status: AGENT_NEUTRAL_START_LAYER_MERGED
- API integration status: STDLIB_READ_ONLY_PUBLIC_DATA_ACTIVE; MANUAL_EXPLICIT_NETWORK_POLLING_RUNNER_DEV_ONLY; MANUAL_GUARD_ENFORCED_SNAPSHOT_CAPTURE_DEV_ONLY
- Runtime dependency integration status: STARTED_WP167_ANALYTICAL_PYARROW_DUCKDB_POLARS
- Official client runtime dependency status: NOT_STARTED_FOR_OFFICIAL_CLIENT_RUNTIME
- Live trading status: DISABLED
- Credentials status: NOT_USED
- Execution status: NOT_STARTED
- Official Python client status: SANDBOX_CANDIDATE_ONLY_NOT_PROJECT_DEPENDENCY
- Authenticated client status: FORBIDDEN_UNTIL_APPROVED_WP
- AI-agent layer status: POLICY_ONLY_NOT_IMPLEMENTED
- Agent context export schema status: POLICY_SCHEMA_DEFINED_EXPORTER_IMPLEMENTED_LOCAL_OFFLINE_READ_ONLY
- Agent context exporter status: LOCAL_OFFLINE_READ_ONLY_EXPORTER
- Agent context exporter operator runbook status: LOCAL_OPERATOR_RUNBOOK
- Agent report generation status: LOCAL_OFFLINE_READ_ONLY_REPORT_GENERATOR
- Agent report operator runbook status: LOCAL_ANALYST_REPORT_OPERATOR_RUNBOOK
- Agent/Hermes manual setup decision status: MANUAL_SETUP_DECISION_RECORD_MERGED
- Token-efficiency operating model status: ACTIVE_REPO_TRUTH_GUIDANCE
- Diff/scope summary helper design status: DESIGN_MERGED
- Diff/scope summary helper implementation status: LOCAL_OFFLINE_READ_ONLY_HELPER_MERGED
- WP159 draftability/specification/exact-scope foundation status: MERGED; WP159 PR: 159; WP159 final head: 177e60c59023456a54124b7da093f0a08f5f15b0; WP159 merge commit: 352e2f54f712511da02882ee2937cc72c5e21ad9; Guard schema: polymarket-work-package-spec@1.0.0; Guard result schema: polymarket-wp-spec-guard-result@1.0.0; Diff helper legacy schema: 1.0; Diff helper WP-spec schema: 2.0; Exact package files: 23; Package size: XL_EXPLICITLY_AUTHORIZED; Bootstrap waiver: WAIVED_FOR_LOW_RISK_DRAFT_PR_IMPLEMENTATION; Independent PASS certificate: NOT_CREATED; Ready for review: NO; Merge authorized: NO; Runtime/product/network/credential/dependency/trading impact: NONE; WP160 and WP161 authority: NONE
- Validation-output summary helper design status: DESIGN_MERGED
- Validation-output summary helper implementation status: LOCAL_OFFLINE_READ_ONLY_HELPER_MERGED
- Code-index / blast-radius helper design status: DESIGN_MERGED
- Code-index / blast-radius helper implementation status: LOCAL_OFFLINE_READ_ONLY_HELPER_MERGED
- Memory/status snapshot helper design status: DESIGN_MERGED
- Memory/status snapshot helper implementation status: LOCAL_OFFLINE_READ_ONLY_HELPER_MERGED
- Token-efficiency sequence closeout status: DOCS_ONLY_CLOSEOUT_MERGED
- Local advisory handoff package status: DOCS_ONLY_LOCAL_ADVISORY_HANDOFF_MERGED
- Advisory runtime boundary and consumption design status: DOCS_ONLY_ADVISORY_RUNTIME_BOUNDARY_DESIGN_MERGED
- Local advisory consumer prototype status: LOCAL_OFFLINE_READ_ONLY_ADVISORY_CONSUMER_MERGED
- Advisory prompt/runbook package status: DOCS_ONLY_ADVISORY_PROMPT_RUNBOOK_MERGED
- Advisory operator workflow hardening status: DOCS_ONLY_ADVISORY_OPERATOR_WORKFLOW_MERGED
- Market research priority scoring layer status: DOCS_ONLY_DESIGN_MERGED; SCHEMA_OUTPUT_CONTRACT_MERGED; CORE_SCORER_MERGED; RESEARCH_DATA_FOUNDATION_DIRECTION_MERGED; FEATURE_EXTRACTION_FOUNDATION_MERGED; LONG_TERM_ROADMAP_MERGED; DATA_INTEGRITY_HARDENING_MERGED; MICROSTRUCTURE_QUALITY_MERGED; CROSS_MARKET_RELATIONSHIP_METADATA_MERGED; RESOLUTION_SOURCE_HIERARCHY_MERGED; RESEARCH_QUEUE_REPORT_SESSION_PACKET_MERGED; RESEARCH_QUEUE_EXPORT_OPERATOR_RUNBOOK_MERGED; CALIBRATION_HARNESS_DESIGN_MERGED; CALIBRATION_RECORD_SCHEMA_VALIDATOR_MERGED; LOCAL_RESOLVED_OUTCOME_FIXTURE_LOADER_MERGED; CALIBRATION_REPORT_GENERATOR_DESIGN_MERGED; LOCAL_CALIBRATION_METRIC_COMPUTATION_MERGED; LOCAL_CALIBRATION_REPORT_GENERATOR_MERGED; LOCAL_CALIBRATION_REPORT_EXPORT_MERGED; HUMAN_REVIEW_LABEL_WORKFLOW_DESIGN_MERGED; HUMAN_REVIEW_LABEL_RECORD_VALIDATOR_MERGED; HUMAN_REVIEW_LABEL_FIXTURE_LOADER_MERGED; WALLET_INTELLIGENCE_ROADMAP_MERGED; WALLET_INTELLIGENCE_ARCHITECTURE_CONTRACT_MERGED; WALLET_TRADE_EVENT_FIXTURE_LOADER_MERGED; WALLET_SIGNAL_RESEARCH_PROFILER_MERGED; WALLET_COPYABILITY_DELAY_SIMULATOR_DESIGN_MERGED; WALLET_INTELLIGENCE_REPORT_CONTRACT_MERGED; WALLET_COPYABILITY_DELAY_EVALUATOR_MERGED; WALLET_INTELLIGENCE_REPORT_GENERATOR_MERGED; WALLET_SIGNAL_PAPER_STRATEGY_CONTRACT_MERGED; WALLET_SIGNAL_PAPER_STRATEGY_CONTRACT_LOCAL_VALIDATOR_MERGED; EXECUTION_PACKAGE_DISCIPLINE_ADOPTION_MERGED; WALLET_SIGNAL_PAPER_STRATEGY_CANDIDATE_FIXTURE_LOADER_MERGED; EVIDENCE_ARCHITECTURE_REPAIR_MERGED; WALLET_SIGNAL_CANDIDATE_REVIEW_REPORT_MERGED; WALLET_SIGNAL_CANDIDATE_REVIEW_REPORT_EXPORT_MERGED
- Research queue export/operator runbook status: LOCAL_OFFLINE_EXPLICIT_MANUAL_EXPORT_MERGED
- Calibration harness design status: DOCS_SCHEMA_DESIGN_ONLY_MERGED
- Resolved outcome data requirements status: DOCS_DESIGN_ONLY_MERGED
- Calibration record example schema status: DOCS_STATIC_EXAMPLE_SCHEMA_MERGED
- Calibration record schema validator status: LOCAL_OFFLINE_READ_ONLY_VALIDATOR_MERGED
- Resolved outcome fixture loader status: LOCAL_OFFLINE_READ_ONLY_FIXTURE_LOADER_MERGED
- Calibration report generator design status: DOCS_SCHEMA_TESTS_DESIGN_ONLY_MERGED
- Calibration metric computation status: LOCAL_OFFLINE_READ_ONLY_METRIC_COMPUTATION_MERGED
- Calibration report generator implementation status: LOCAL_OFFLINE_READ_ONLY_REPORT_GENERATOR_MERGED
- Calibration report export status: LOCAL_OFFLINE_EXPLICIT_MANUAL_EXPORT_MERGED
- WP54 bundled-WP execution policy status: WORKFLOW_GOVERNANCE_MERGED
- WP54 guard --require-guard-result flag status: LOCAL_OFFLINE_STDLIB_GUARD_HARDENING_MERGED
- Resolution ambiguity taxonomy/manual-label workflow status: DOCS_SCHEMA_TESTS_ONLY_MERGED
- Resolution ambiguity label schema validation status: LOCAL_OFFLINE_READ_ONLY_LABEL_SCHEMA_VALIDATION_MERGED
- Resolution ambiguity local feature extraction from validated labels status: LOCAL_OFFLINE_READ_ONLY_LABEL_FEATURE_EXTRACTION_MERGED
- Market research priority scoring implementation status: LOCAL_OFFLINE_READ_ONLY_CORE_SCORER_MERGED
- Market research priority scoring feature extraction status: LOCAL_OFFLINE_READ_ONLY_FEATURE_EXTRACTION_FOUNDATION_MERGED; RESOLUTION_AMBIGUITY_LABEL_FEATURE_EXTRACTION_MERGED; LOCAL_OFFLINE_READ_ONLY_MICROSTRUCTURE_QUALITY_MERGED; LOCAL_OFFLINE_READ_ONLY_CROSS_MARKET_RELATIONSHIP_METADATA_MERGED; LOCAL_OFFLINE_READ_ONLY_RESOLUTION_SOURCE_HIERARCHY_MERGED
- Architecture direction lock-in status: ARCHITECTURE_DIRECTION_MERGED
- Microstructure quality feature extraction status: LOCAL_OFFLINE_READ_ONLY_MICROSTRUCTURE_QUALITY_MERGED
- Cross-market relationship metadata status: LOCAL_OFFLINE_READ_ONLY_CROSS_MARKET_RELATIONSHIP_METADATA_MERGED
- Resolution source hierarchy metadata status: LOCAL_OFFLINE_READ_ONLY_RESOLUTION_SOURCE_HIERARCHY_MERGED
- Research queue/report/session packet status: LOCAL_OFFLINE_READ_ONLY_RESEARCH_OUTPUT_PACKET_MERGED
- Claude start layer status: CLAUDE_START_HERE_MERGED
- Posted GitHub evidence verifier status: GITHUB_AWARE_READ_ONLY_WORKFLOW_HELPER_MERGED
- Negative test matrix policy status: WORKFLOW_GOVERNANCE_MERGED
- PR template structured evidence status: WORKFLOW_GOVERNANCE_MERGED
- Canonical WP execution state machine status: WORKFLOW_GOVERNANCE_MERGED
- Private-repo evidence mode status: WORKFLOW_GOVERNANCE_MERGED
- Evidence mode review-readiness gate status: WORKFLOW_GOVERNANCE_MERGED
- Market research priority scoring CLI/export/report status: LOCAL_OFFLINE_EXPLICIT_MANUAL_EXPORT_MERGED
- Research data foundation direction status: DOCS_ONLY_DIRECTION_LOCK_MERGED
- Long-term bot roadmap status: DOCS_ONLY_ROADMAP_MERGED
- Side 4 onboarding lock status: DOCS_ONLY_SIDE4_ONBOARDING_LOCK_MERGED
- PR evidence reporting discipline status: WORKFLOW_GOVERNANCE_MERGED
- PR evidence consistency guard status: LOCAL_OFFLINE_STDLIB_GUARD_MERGED
- Posted PR evidence review hardening status: DOCS_AND_GUARD_HARDENING_MERGED
- WP execution package discipline adoption status: WORKFLOW_DOCS_TESTS_ONLY_MERGED
- WP drafting standard status: WORKFLOW_GOVERNANCE_MERGED
- Status entries / committed evidence fragments status: WORKFLOW_CONVENTION_MERGED
- Final comment transition status: RETIRED_AFTER_WP91; mandatory final GitHub evidence comments retired; PR body is current review evidence surface; status fragment is stable non-self-referential record; final comments optional non-canonical after WP91
- Repo-truth policy guard status: REPO_TRUTH_POLICY_GUARD_MERGED; one-shot readiness gate added to PR template and WP template; phrase sweep defined for active canonical policy-doc set; workflow docs tests updated; no product behavior changed; no runtime/paper/live/credential/network/dependency behavior changed
- Candidate review report operator runbook status: DOCS_ONLY_OPERATOR_RUNBOOK_MERGED; documents the import-based local/offline WP87 fixture-loader, WP89 candidate review report, and WP90 export workflow; WP93 final follow-up hardens stable-only status-fragment policy and repairs the WP93 status fragment PR field; no new CLI, source code, tools, runtime/paper/live/credential/network/API/account behavior, scheduler/dashboard/bot loop, dependency, or lock-file change
- Candidate review workflow local smoke receipt status: LOCAL_SMOKE_RECEIPT_MERGED; verifies the existing WP87/WP89/WP90 import-only workflow through docs/tests and temp-only local export smoke coverage; no new CLI, source code, tools, runtime/paper/live/credential/network/API/account behavior, scheduler/dashboard/bot loop, dependency, or lock-file change
- Hermes research-brain execution plan status: REPO_TRUTH_PLAN_LOCKED; canonical plan is `docs/hermes_research_brain_execution_plan.md`; future material plan changes must update repo-truth docs in the same WP or an approved follow-up, because chat memory and PR comments alone are not authoritative
- Hermes advisory foundation architecture status: REPO_TRUTH_ARCHITECTURE_LOCKED; canonical architecture is `docs/hermes_advisory_foundation_research_brain_architecture.md`; WP96 elaborates WP95 Phase 1 only and preserves broad Hermes research freedom, strict deterministic control boundaries, and the prohibition on Hermes runtime/install/provider/model/credential/schema/validator/prompt-pack/runbook/exporter/paper/live/execution/risk/scheduler/dashboard/bot-loop authority
- Historical WP96 next phase completed by WP97: Hermes input/output contracts and validator hardening
- Hermes input/output contracts and validator requirements status: REPO_TRUTH_DOCUMENTATION_LEVEL_CONTRACT_REQUIREMENTS_LOCKED; canonical contract requirements doc is `docs/hermes_input_output_contracts_and_validator_requirements.md`; WP97 documents Phase 2 only and creates no machine-readable schema, source validator, prompt pack, runbook, exporter, parser, context-packet generator, Hermes runtime, provider/model configuration, credential path, paper/live behavior, execution/order/risk behavior, scheduler/dashboard behavior, bot-loop behavior, source code, tools, dependency file, or lock file
- Hermes research prompt pack and operator runbooks status: REPO_TRUTH_RESEARCH_PROMPT_PACK_AND_OPERATOR_RUNBOOKS_LOCKED; canonical prompt pack and runbook doc is `docs/hermes_research_prompt_pack_and_operator_runbooks.md`; WP98 documents Phase 3 only and creates no prompt runner, machine-readable schema, source validator, exporter, parser, context-packet generator, Hermes runtime, provider/model configuration, credential path, paper/live behavior, execution/order/risk behavior, scheduler/dashboard behavior, bot-loop behavior, source code, tools, dependency file, or lock file; defines 10 manual-use-only research prompt families with operator preflight, input preparation, prompt-injection policy, common output requirements, output review checklist, forbidden output matrix, human-review and deterministic handoff rules, failure/stop conditions, manual setup dependency note, future implementation gates, and next WP sequence pointer
- Hermes advisory output validator status: LOCAL_OFFLINE_READ_ONLY_VALIDATOR_MERGED; validator module is `src/data_layer/hermes_advisory_output_validator.py`; WP99 implements stdlib-only deterministic local/offline/read-only validator for in-memory Hermes advisory output mappings; enforces WP97/WP98 required boolean safety fields, required text/list fields, confidence-level allowlist, recursive forbidden-term scan, recursive raw-metadata-key rejection, fail-closed behavior, and no unsafe echo; no Hermes runtime, prompt runner, context-packet exporter, CLI, network, credentials, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior
- Hermes context-packet exporter foundation status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_PACKET_BUILDER_MERGED; builder module is `src/data_layer/hermes_context_packet_exporter.py`; WP100 implements deterministic stdlib-only construction of sanitized in-memory advisory context packets from explicit caller-supplied summaries; enforces required identity/evidence/provenance/safety/payload concepts, recursive forbidden-content and raw/free-form mapping rejection, fail-closed empty invalid packets, and no unsafe echo; no Hermes runtime, prompt runner, CLI, file export/report writer, product/runtime network, credentials, account/order/private state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior
- Hermes context-packet dry-run receipt status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_DRY_RUN_RECEIPT_MERGED; receipt module is `src/data_layer/hermes_context_packet_dry_run_receipt.py`; WP101 implements deterministic stdlib-only construction of in-memory dry-run receipts from explicit caller-supplied WP100 context packets and readiness checks; validates WP100 safety flags, required packet fields, checked source references, exact readiness checks, stop reasons, recursive forbidden content, raw/free-form mapping rejection, fail-closed empty invalid receipts, and no unsafe echo; no Hermes runtime/install/connect, prompt runner, prompt execution, CLI, file export/report writer, product/runtime network, credentials, account/order/private state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior
- Hermes manual research dry-run operator review status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_OPERATOR_REVIEW_MERGED; review module is `src/data_layer/hermes_manual_research_dry_run_review.py`; WP102 implements deterministic stdlib-only construction of in-memory manual research dry-run operator review records from explicit caller-supplied WP101 dry-run receipts and source-review checks; validates receipt type/status/safety flags, required receipt identity fields, required source reference fields, exact source-review checks, stop reasons, recursive forbidden content, raw/free-form mapping rejection, fail-closed empty invalid reviews, and no unsafe echo; no Hermes runtime/install/connect, prompt runner, prompt execution, CLI, file export/report writer, product/runtime network, credentials, account/order/private state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior
- Hermes candidate-review context packet integration status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_CANDIDATE_REVIEW_INTEGRATION_MERGED; adapter module is `src/data_layer/hermes_candidate_review_context_packet_integration.py`
- Hermes candidate-review manual chain smoke status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_CHAIN_SMOKE_MERGED; smoke helper module is `src/data_layer/hermes_candidate_review_manual_chain_smoke.py`; WP104 composes WP103/WP101/WP102 safe helpers to show the research-chain pieces assemble without file I/O, network, CLI, prompt execution, Hermes runtime, credentials, paper/live behavior, or execution/risk behavior; no Hermes install/connect/run, prompt runner, file writer/export/report writer, CLI, product/runtime network, credentials, account/order/private state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior; WP103 implements deterministic stdlib-only (plus approved WP100 internal import) construction of sanitized in-memory advisory context packets from explicit caller-supplied candidate-review report data; pre-validates all inputs for forbidden credential/trade/execution/runtime/raw-mapping-key content, maps safe fields to WP100 context-packet builder, returns WP100 HermesContextPacketBuildResult with advisory-only/human-review-required/no-authority flags; fail-closed empty invalid packets; no unsafe echo; no Hermes runtime/install/connect, prompt runner, prompt execution, CLI, file export/report writer, product/runtime network, credentials, account/order/private state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior
- Hermes candidate-review operator handoff contract status: DOCS_STATUS_TESTS_ONLY_OPERATOR_HANDOFF_CONTRACT_MERGED; canonical contract doc is `docs/hermes_candidate_review_operator_handoff_contract.md`; WP105 defines the human-operator handoff contract around the WP103 -> WP101 -> WP102 -> WP104 candidate-review research chain, including required conceptual groups, safety flags, allowed research decision labels, forbidden interpretation, forbidden wording matrix, raw metadata/free-form mapping policy, no-unsafe-echo policy, fail-closed policy, future implementation gates, and operator runbook summary; no source implementation, file writer/export/report writer, CLI, Hermes runtime/provider/model/prompt runner, network/API/product/account behavior, credentials, paper/live, execution/risk/order, scheduler/dashboard/bot-loop, dependency, workflow, or generated-artifact behavior
- Hermes candidate-review in-memory operator handoff object status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_OPERATOR_HANDOFF_OBJECT_MERGED; handoff module is `src/data_layer/hermes_candidate_review_operator_handoff.py`; WP106 implements the first deterministic stdlib-only local/offline/read-only in-memory handoff object layer for the WP105 operator handoff contract; validates required conceptual groups, safety flags, allowed decision labels, source-review checklist, forbidden content recursion, raw/free-form metadata rejection, fail-closed empty invalid handoffs, and no unsafe echo; no Hermes install/connect/run, prompt runner, file writer/export/report writer, CLI, product/runtime network, credentials, account/order/private state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior
- Hermes candidate-review handoff local manual export contract status: DOCS_STATUS_TESTS_ONLY_LOCAL_MANUAL_EXPORT_CONTRACT_MERGED; canonical contract doc is `docs/hermes_candidate_review_handoff_local_manual_export_contract.md`; WP107 defines the future local/manual export/report artifact contract for valid WP106 handoff outputs without implementing a writer/exporter/CLI/runtime; no source implementation, file writer/export/report writer, CLI, Hermes runtime/provider/model/prompt runner, network/API/product/account behavior, credentials, paper/live, execution/risk/order, scheduler/dashboard/bot-loop, dependency, workflow, or generated-artifact behavior
- Hermes candidate-review handoff in-memory manual export artifact status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_EXPORT_ARTIFACT_MERGED; module is `src/data_layer/hermes_candidate_review_handoff_manual_export_artifact.py`; WP108 implements a deterministic stdlib-only local/offline/read-only in-memory artifact builder for valid WP106 handoff output following the WP107 contract; no file writer/export-to-disk/report writer/CLI, Hermes install/connect/run, prompt runner, product/runtime network, credentials, account/order/private state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, workflow, or lock-file behavior
- Hermes candidate-review handoff local manual export file writer status: LOCAL_OFFLINE_MANUAL_ONLY_FILE_WRITER_MERGED; writer module is `src/data_layer/hermes_candidate_review_handoff_manual_export_writer.py`; WP109 implements a deterministic stdlib-only local/offline/manual-only explicit file writer for valid WP108 artifact output; writes a deterministic UTF-8 Markdown artifact to an explicit operator-supplied local path; returns bytes_written and sha256; fails closed for invalid input; parent directory must exist; no CLI, scheduler, daemon, background writer, Hermes install/connect/run, prompt runner, product/runtime network, credentials, account/order/private state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, workflow, or lock-file behavior; no committed generated artifact files
- Hermes candidate-review local manual export operator runbook status: DOCS_STATUS_TESTS_ONLY_LOCAL_MANUAL_EXPORT_OPERATOR_RUNBOOK_MERGED; canonical runbook doc is `docs/hermes_candidate_review_local_manual_export_operator_runbook.md`; WP110 documents manual-only operator use of the WP109 writer for valid WP108 artifacts, including allowed inputs, explicit local `.md`/`.txt` output path rules, parent-directory preflight, generated-artifact no-commit rules, human review, failure handling, forbidden scope, and future gates; no source implementation, CLI, scheduler, daemon, background writer, Hermes install/connect/run, prompt runner, product/runtime network, credentials, account/order/private state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, workflow, or lock-file behavior
- Hermes candidate-review local manual export smoke exercise status: DOCS_STATUS_TESTS_ONLY_TEMP_ONLY_LOCAL_MANUAL_EXPORT_SMOKE_EXERCISE_REVIEW_TARGET; canonical smoke exercise doc is `docs/hermes_candidate_review_local_manual_export_smoke_exercise.md`; WP111 demonstrates the existing WP106 -> WP108 -> WP109 manual export path under pytest `tmp_path` only, using synthetic safe fixture data and producing no committed generated artifacts; no source implementation, CLI, scheduler, daemon, background writer, automatic report/export pipeline, Hermes install/connect/run, prompt runner, product/runtime network, credentials, account/order/private state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, workflow, generated-artifact, or lock-file behavior
- Hermes candidate-review local manual export chain closeout status: DOCS_STATUS_TESTS_ONLY_LOCAL_MANUAL_EXPORT_CHAIN_CLOSEOUT_REVIEW_TARGET; canonical closeout doc is `docs/hermes_candidate_review_local_manual_export_chain_closeout.md`; WP112 records the bounded WP106 -> WP108 -> WP109 -> WP110 -> WP111 manual export chain as locally coherent and manual-only; no source implementation, CLI, scheduler, daemon, background writer, automation, report pipeline, Hermes install/connect/run, prompt runner, product/runtime network, credentials, account/order/private state, paper/live, execution/risk, dashboard, bot-loop, dependency, workflow, lock-file, or committed generated-artifact behavior changes.
- Hermes candidate-review local manual export CLI wrapper contract status: DOCS_STATUS_TESTS_ONLY_CLI_WRAPPER_CONTRACT_MERGED; canonical contract doc is `docs/hermes_candidate_review_local_manual_export_cli_wrapper_contract.md`; WP113 defines a possible future manual/local/offline CLI wrapper contract for the completed WP106/WP108/WP109/WP110/WP111/WP112 local manual export chain; WP113 does not implement a CLI, source module, tool, scheduler, daemon, background writer, report/export automation, Hermes runtime/provider/model/prompt runner, network/API/product/account behavior, credentials/private state, paper/live, execution/risk/order, dashboard, bot-loop, dependency, workflow, lock-file, copied external code, or committed generated-artifact behavior.
- Hermes candidate-review local manual export CLI command surface contract status: DOCS_STATUS_TESTS_ONLY_CLI_COMMAND_SURFACE_CONTRACT_MERGED; canonical contract doc is `docs/hermes_candidate_review_local_manual_export_cli_command_surface_contract.md`; WP114 defines the exact future command shape, strict WP108 artifact-result input handoff envelope, rejection rules, output behavior, exit-code policy, failure behavior, negative-test obligations, and human-review requirement before the WP115 implementation layer; WP114 does not implement a CLI, source module, tool, command parser, command runner, shell wrapper, JSON parser implementation, scheduler, daemon, background writer, report/export automation, Hermes runtime/provider/model/prompt runner, network/API/product/account behavior, credentials/private state, paper/live, execution/risk/order, dashboard, bot-loop, dependency, workflow, lock-file, copied external code, or committed generated-artifact behavior.
- Hermes candidate-review local manual export CLI wrapper implementation status: LOCAL_OFFLINE_MANUAL_CLI_WRAPPER_MERGED; CLI module is `tools/hermes_candidate_review_manual_export_cli.py`; WP115 adds one stdlib-only local/offline/manual wrapper around the existing WP109 writer, accepts only a strict local WP108 artifact-result JSON envelope, writes only to one explicit operator-supplied `.md` or `.txt` output path, rejects protected/tracked repo and generated-artifact output paths, preserves fail-closed and no-unsafe-echo behavior, and prints only bounded neutral success/error summaries; no source implementation under `src/`, no product/runtime network, no credentials/private state, no account/order/private state, no paper/live/execution/risk/order behavior, no scheduler/dashboard/bot-loop/runtime/daemon behavior, no Hermes runtime/provider/model/prompt runner behavior, no dependency/workflow/lock-file changes, and no committed generated-artifact behavior changes.
- Hermes candidate-review local manual export CLI operator runbook and smoke receipt status: DOCS_STATUS_TESTS_ONLY_CLI_OPERATOR_RUNBOOK_SMOKE_RECEIPT_MERGED; canonical runbook doc is `docs/hermes_candidate_review_local_manual_export_cli_operator_runbook.md`; smoke receipt doc is `docs/hermes_candidate_review_local_manual_export_cli_smoke_receipt.md`; WP116 documents safe manual operator use of the existing WP115 CLI command shape, input/output preflight, expected success/failure behavior, cleanup rules, and future gates; WP116 adds no implementation, no CLI modification, no source under `src/`, no product/runtime network, no credentials/private state, no account/order/private state, no paper/live/execution/risk/order behavior, no scheduler/dashboard/bot-loop/runtime/daemon behavior, no Hermes runtime/provider/model/prompt runner behavior, no dependency/workflow/lock-file changes, and no committed generated-artifact behavior changes.
- Hermes candidate-review local manual export CLI chain closeout and research-workflow transition status: DOCS_STATUS_TESTS_ONLY_CLI_CHAIN_CLOSEOUT_RESEARCH_WORKFLOW_TRANSITION_MERGED; canonical closeout doc is `docs/hermes_candidate_review_local_manual_export_cli_chain_closeout.md`; WP117 records that the WP106 -> WP107 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 -> WP113 -> WP114 -> WP115 -> WP116 local/manual export and CLI convenience chain is complete enough for bounded operator use; the chain supports only manual, local, offline, human-reviewed export of already-valid WP108 artifact-result envelopes through the WP115 CLI or lower-level import path; the WP115 CLI is a convenience wrapper, not automation; WP117 records the next recommended phase as Hermes-assisted candidate-review research workflow, not paper/live trading; WP117 adds no implementation, no WP115 CLI modification, no source under `src/`, no tools behavior, no product/runtime network, no credentials/private state, no account/order/private state, no paper/live/execution/risk/order behavior, no scheduler/dashboard/bot-loop/runtime/daemon behavior, no Hermes runtime/provider/model/prompt runner behavior, no dependency/workflow/lock-file changes, and no committed generated-artifact behavior changes.
- Hermes candidate-review research workflow intake contract status: DOCS_STATUS_TESTS_ONLY_RESEARCH_WORKFLOW_INTAKE_CONTRACT_MERGED; canonical intake contract is `docs/hermes_candidate_review_research_workflow_intake_contract.md`; WP118 defines only the manual/local/offline/advisory-only intake and packet-selection contract for human-reviewed Hermes-assisted candidate-review research preparation from already-valid upstream artifacts or packets; allowed conceptual inputs are already-valid WP106 handoff objects or exported representations, already-valid WP108 manual export artifact results or reviewed local export artifacts, WP115 CLI-exported local review artifacts generated from strict valid WP108 envelopes, relevant repo-truth docs/status fragments, and structured reviewed non-secret operator notes that are not raw/free-form metadata; WP118 creates no parser, loader, runner, output schema, writer, validator, storage, CLI behavior, automation, Hermes runtime/provider/model/prompt runner behavior, network/API/product/account behavior, credentials/private state, paper/live/execution/risk/order behavior, scheduler/dashboard/bot-loop/runtime/daemon behavior, dependency/workflow/lock-file changes, or committed generated-artifact behavior changes.
- Hermes candidate-review research workflow runbook status: DOCS_STATUS_TESTS_ONLY_RESEARCH_WORKFLOW_RUNBOOK_MERGED; canonical runbook is `docs/hermes_candidate_review_research_workflow_runbook.md`; WP119 documents only the manual/local/offline/advisory-only operator workflow after WP118 intake and before any future schemas/storage/implementation; it defines operator preconditions, neutral research-question rules, manual Hermes prompt adaptation boundaries, advisory output review boundaries, conceptual human decision categories, cleanup/repo hygiene, future gates, and non-authority posture; WP119 creates no parser, loader, runner, output schema, writer, validator, storage, tools, CLI behavior, automation, Hermes runtime/provider/model/prompt runner behavior, network/API/product/account behavior, credentials/private state, paper/live/execution/risk/order behavior, scheduler/dashboard/bot-loop/runtime/daemon behavior, dependency/workflow/lock-file changes, or committed generated-artifact behavior changes.
- Hermes candidate-review research question record contract status: DOCS_STATUS_TESTS_ONLY_RESEARCH_QUESTION_RECORD_CONTRACT_MERGED; canonical research question record contract is `docs/hermes_candidate_review_research_question_record_contract.md`; WP120 defines only the future manual/local/offline/advisory-only research question record contract after WP118 intake and WP119 runbook; it defines conceptual required future field concepts, allowed non-executing research question types, forbidden research question types, evidence/preflight requirements, human review requirements, future gates, and non-authority posture; WP120 creates no parser, writer, loader, storage path, CLI behavior, Hermes prompt runner, model/provider integration, automation, report pipeline, dashboard, paper/live behavior, execution/risk/order behavior, credentials, workflow, dependency, generated artifact, or tools behavior.
- Hermes candidate-review research question record implementation status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_RESEARCH_QUESTION_RECORD_MERGED; module is `src/data_layer/hermes_candidate_review_research_question_record.py`; WP121 implements the WP120 contract as a stdlib-only deterministic in-memory validator/build/assert layer for explicit caller-supplied research question record mappings; invalid input fails closed with empty record output and neutral diagnostics; unsafe caller content is not echoed in invalid results; required fields, allowed research question types, required preflight flags, required non-authority safety flags, human review, non-authority notice, raw/free-form metadata rejection, and recursive forbidden-content rejection are enforced; no parser, loader, writer, storage path, CLI behavior, report/export pipeline, Hermes runtime/provider/model/prompt runner, product/runtime/API/account network behavior, credentials/private state, paper/live/execution/risk/order behavior, scheduler/dashboard/bot-loop/runtime/daemon behavior, dependency/workflow/lock-file change, or committed generated artifact behavior is added.
- Hermes candidate-review advisory output validation receipt status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_ADVISORY_OUTPUT_VALIDATION_RECEIPT_MERGED; module is `src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py`; WP122 implements a stdlib-only deterministic in-memory validator/build/assert layer for explicit caller-supplied advisory output validation receipt mappings; invalid input fails closed with empty receipt output and neutral diagnostics; unsafe caller content is not echoed in invalid results; required fields, allowed receipt labels, required review flags, required non-authority safety flags, human review, non-authority notice, raw/free-form metadata rejection, and recursive forbidden-content rejection are enforced; no parser, loader, writer, storage path, CLI behavior, report/export pipeline, Hermes runtime/provider/model/prompt runner, product/runtime/API/account network behavior, credentials/private state, paper/live/execution/risk/order behavior, scheduler/dashboard/bot-loop/runtime/daemon behavior, dependency/workflow/lock-file change, or committed generated artifact behavior is added.
- Hermes candidate-review human decision and follow-up record status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_HUMAN_DECISION_FOLLOW_UP_RECORD_MERGED; module is `src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py`; WP123 implements a stdlib-only deterministic in-memory validator/build/assert layer for explicit caller-supplied human decision and manual follow-up research task mappings; invalid input fails closed with empty decision/task output and neutral diagnostics; unsafe caller content is not echoed in invalid results; required fields, allowed decision/task labels, required non-authority safety flags, human review, non-authority notice, raw/free-form metadata rejection, and recursive forbidden-content rejection are enforced; no parser/loader/writer/storage path, no CLI, no report/export pipeline, no Hermes runtime/provider/model/prompt runner, no product/runtime/API/account network behavior, no credentials/private state, no paper/live/execution/risk/order behavior, no scheduler/dashboard/bot-loop/runtime/daemon behavior, no dependency/workflow/lock-file change, and no committed generated artifact behavior is added.
- Hermes candidate-review manual research session package status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_RESEARCH_SESSION_PACKAGE_MERGED; module is `src/data_layer/hermes_candidate_review_manual_research_session_package.py`; WP124 combines explicit caller-supplied WP121-WP123 workflow records into one deterministic stdlib-only in-memory validator/build/assert package; WP125 adds its manual/local/offline/advisory-only operator runbook and temp-only synthetic smoke exercise with no source implementation and no WP121-WP124 source-module modification; invalid input fails closed with empty package output and neutral diagnostics; no parser/loader/writer/storage path, CLI, report/export pipeline, Hermes runtime/provider/model/prompt runner, product/runtime/API/account network behavior, credentials/private state, paper/live/execution/risk/order behavior, scheduler/dashboard/bot-loop/runtime/daemon behavior, dependency/workflow/lock-file change, or committed generated artifact behavior is added.
- Hermes candidate-review research candidate queue status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_RESEARCH_CANDIDATE_QUEUE_MERGED; module is `src/data_layer/hermes_candidate_review_research_candidate_queue.py`; WP126 validates and builds explicit caller-supplied in-memory candidate items and non-empty queue packages with exact safety flags, human review, recursive forbidden-content/raw-metadata rejection, fail-closed empty invalid outputs, and neutral no-echo diagnostics.
- Hermes candidate-review research candidate queue operator runbook/temp smoke status: DOCS_STATUS_TESTS_ONLY_MANUAL_LOCAL_OFFLINE_ADVISORY_QUEUE_OPERATOR_RUNBOOK_TEMP_SMOKE_MERGED; WP127 documents explicit in-memory synthetic item/package assembly and temp-only fail-closed smoke coverage; no source modification or protected behavior.
- Hermes candidate-review manual queue selection/research-question handoff status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_EXPLICIT_HUMAN_SELECTION_HANDOFF_MERGED; module is `src/data_layer/hermes_candidate_review_manual_queue_selection_handoff.py`; WP128 validates explicit caller-supplied manual selection/rejection records and caller-supplied proposed research-question handoffs with exact safety flags, recursive forbidden-content/raw-metadata rejection, and fail-closed neutral no-echo outputs.
- Hermes candidate-review manual queue-selection-to-question chain status: DOCS_STATUS_TESTS_ONLY_MANUAL_LOCAL_OFFLINE_ADVISORY_CHAIN_RUNBOOK_TEMP_SMOKE_MERGED; WP129 documents and smoke-tests the manual WP126 -> WP128 -> WP121 in-memory compatibility chain with synthetic fixtures only.
- Hermes candidate-review manual research briefing packet status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_RESEARCH_BRIEFING_PACKET_MERGED; module is `src/data_layer/hermes_candidate_review_manual_research_briefing_packet.py`; WP130 organizes explicit caller-supplied research questions, references, gaps, limitations, checks, and requested response-section labels for human review only; no prompt generation/execution, model/provider/Hermes call, research answer or finding generation, network, ingestion, scoring, priority, recommendation, storage, export, CLI, runtime, or trading authority exists.
- Hermes candidate-review manual research briefing packet operator runbook/temp smoke status: DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_SMOKE_MERGED; WP131 documents manual construction and in-memory inspection through the existing WP130 API and adds fail-closed no-adapter reviewer traps; no source, prompt/response/model/Hermes, file output, runtime, network, credentials, storage, paper/live, execution/risk/order, or trading authority exists.
- Hermes candidate-review manual research request contract status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_RESEARCH_REQUEST_MERGED; module is `src/data_layer/hermes_candidate_review_manual_research_request.py`; WP132 validates and sanitizes explicit caller-supplied request, source/citation/evidence/section requirement labels, bounded budgets, exact safety flags, and non-authority notices; invalid input fails closed without caller-content echo; no prompt generation/execution, Hermes/model/provider/tool call, browsing/source fetching, answer/finding generation, storage/export, CLI, scheduler, runtime, or trading authority exists.
- Hermes candidate-review manual research response contract status: LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_MANUAL_RESEARCH_RESPONSE_MERGED; module is `src/data_layer/hermes_candidate_review_manual_research_response.py`; WP133 validates and sanitizes explicit caller-supplied content and fails closed without echo; no factual/source/citation verification or authority expansion exists.
- Hermes candidate-review manual research response operator runbook/temp smoke status: DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_MANUAL_RESEARCH_RESPONSE_SMOKE_MERGED; WP134 documents exact manual use of WP133 and tests synthetic in-memory positive, fail-closed, no-echo, no-adapter, and empty-`tmp_path` behavior; no source, prompt/model/Hermes/tool, product network, verification, storage, runtime, paper/live, execution/risk/order, credential, recommendation, probability, scoring, ranking, or priority authority exists.
- Hermes candidate-review manual research request-to-response session chain runbook/temp smoke status: DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_MANUAL_REQUEST_RESPONSE_SESSION_CHAIN_SMOKE_MERGED; WP135 documents and smoke-tests independent explicit caller construction through WP132 and WP133 with eight test-only linkage assertions, valid-but-mismatched evidence, no adapter or automatic transfer, no chain/session product object, no generated response, no source/citation verification, and empty `tmp_path`; no source, runtime, network, storage, paper/live, execution/risk/order, credential, recommendation, probability, scoring, ranking, or priority authority exists.
- Hermes candidate-review manual request-response-validation receipt chain contract/smoke decision status: DOCS_STATUS_TESTS_ONLY_MANUAL_REQUEST_RESPONSE_VALIDATION_RECEIPT_CHAIN_DECISION_MERGED; Direct three-record smoke: NOT APPROVED. WP121 research-question lineage is mandatory. Required future topology: WP121 → WP132 → WP133 → WP122. WP136 prohibits field reinterpretation and automatic transfer and implements no source, smoke, adapter, chain/session object, verification, runtime, network, storage, or trading behavior.
- Hermes candidate-review manual research question-request-response-validation receipt four-record chain runbook/temp smoke status: DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_FOUR_RECORD_MANUAL_LINEAGE_SMOKE_MERGED; WP137 documents and smoke-tests four independently authored zero-argument fixtures through WP121 → WP132 → WP133 → WP122 with fourteen post-validation relationships, thirteen valid-but-inconsistent cases, four human-review failures, four unsafe no-echo cases, no repair, no adapter, no chain/session product object, no source change, and empty `tmp_path`; no runtime, product network, storage, paper/live, execution/risk/order, credential, recommendation, probability, scoring, ranking, or priority authority exists.
- Hermes candidate-review four-record lineage to human decision and follow-up chain decision status: DOCS_STATUS_TESTS_ONLY_FOUR_RECORD_LINEAGE_TO_HUMAN_DECISION_FOLLOW_UP_CHAIN_DECISION_MERGED; Six-record future smoke: APPROVED FOR A SEPARATE WP. Required future topology: WP121 → WP132 → WP133 → WP122 → WP123 decision → WP123 follow-up task. WP121→decision, WP122→decision, and decision→task references are direct; WP132/WP133 lineage is inherited through WP121/WP122. WP139 is the separately approved implementation package. WP138 adds no source, no smoke, no adapter, no runtime, no product network, no storage, and no paper/live, execution/risk/order, credential, recommendation, probability, scoring, ranking, priority, or trading authority.
- Hermes candidate-review manual six-record research lineage, human decision, and follow-up-task runbook/temp smoke status: DOCS_STATUS_TESTS_PLUS_TEMP_ONLY_SYNTHETIC_SIX_RECORD_MANUAL_LINEAGE_HUMAN_DECISION_FOLLOW_UP_TASK_SMOKE_MERGED; WP139 documents and temp-smoke-tests six independently authored zero-argument fixtures through WP121 → WP132 → WP133 → WP122 → WP123 decision → WP123 follow-up task with eighteen post-validation relationships, sixteen explicit non-linkages, seventeen valid-but-inconsistent cases, six human-review failures, six unsafe no-echo failures, no repair, no automatic transfer, no generated decision/task, no adapter, no chain/session/linkage product object, no source change, and empty `tmp_path`; no runtime, product network, storage, paper/live, execution/risk/order, credential, recommendation, probability, scoring, ranking, or priority authority exists.
- Hermes candidate-review manual six-record workflow closeout and assisted-research transition status: DOCS_STATUS_TESTS_ONLY_MANUAL_SIX_RECORD_WORKFLOW_CLOSEOUT_ASSISTED_RESEARCH_TRANSITION_MERGED; Manual six-record workflow status: CLOSED_COMPLETE_ENOUGH_FOR_BOUNDED_MANUAL_USE. Default manual-chain extension: STOP. Next phase: HERMES_ASSISTED_RESEARCH_EXPERIMENT_CONTRACT. Hermes installation/runtime activation: NOT AUTHORIZED. Deterministic validation and safety authority: UNCHANGED. Hermes paper/live/execution authority: FORBIDDEN. WP141 was separately approved as the contract-definition package. WP140 adds no source, smoke, provider/model call, network research, storage, credential, paper/live, execution/risk/order, recommendation, probability, scoring, ranking, priority, or runtime authority.
- Hermes candidate-review assisted research session experiment contract status: DOCS_STATUS_TESTS_ONLY_PROVIDER_NEUTRAL_RUNTIME_INACTIVE_ASSISTED_RESEARCH_EXPERIMENT_CONTRACT_MERGED; Experiment contract status: PROVIDER_NEUTRAL_RUNTIME_INACTIVE. Assisted output status: UNTRUSTED_DRAFT_ONLY. Deterministic validation: MANDATORY_BEFORE_ACCEPTANCE. Human review: MANDATORY_BEFORE_ANY_DOWNSTREAM_HANDOFF. Hermes installation/runtime activation: NOT AUTHORIZED. Provider/model selection: NOT AUTHORIZED. Network/source fetching: NOT AUTHORIZED. Persistence/storage: NOT AUTHORIZED. Paper/live/execution authority: FORBIDDEN. WP142 was separately approved as the local synthetic fixture/rubric package. WP141 adds no source, schema, validator, prompt, fixture, smoke, runtime, product-network, credential, storage, recommendation, probability, scoring, ranking, strategy, paper/live, execution/risk/order, acceptance, or promotion authority.
- Hermes candidate-review assisted research gold-case fixture pack and evaluation rubric status: DOCS_STATUS_TESTS_FIXTURE_ONLY_LOCAL_SYNTHETIC_OFFLINE_GOLD_CASE_PACK_EVALUATION_RUBRIC_MERGED; Fixture-pack status: LOCAL_SYNTHETIC_OFFLINE_TEST_ONLY. Case count: 20. Positive/complete cases: 6. Refusal/defer cases: 6. Adversarial cases: 8. Human-review rubric: 16_CATEGORIES_THREE_LEVEL_SCALE. Hard safety gates: ZERO_TOLERANCE. Provider/model performance claims: NONE. Hermes installation/runtime activation: NOT AUTHORIZED. Network/source fetching: NOT AUTHORIZED. Persistence/storage authority: FORBIDDEN. Paper/live/execution authority: FORBIDDEN. WP143 was separately approved as the provider/runtime/privacy/permissions/budget decision package. Canonical document is `docs/hermes_candidate_review_assisted_research_experiment_gold_case_fixture_pack_and_evaluation_rubric.md`; static fixture is `tests/fixtures/hermes_candidate_review_assisted_research_gold_cases.json`; WP142 adds no source, runtime loader, product evaluator, prompt, model call/output, fetched source, persistent result, credential, recommendation, probability, ranking, paper/live, execution/risk/order, or factual-verification authority.
- Hermes candidate-review assisted research provider/runtime/privacy/permissions/budget decision status: DOCS_STATUS_TESTS_ONLY_HERMES_PROVIDER_RUNTIME_PRIVACY_PERMISSIONS_BUDGET_DECISION_MERGED; Assisted-research architecture: LOCAL_DETERMINISTIC_CONTROL_PLANE_WITH_EPHEMERAL_HERMES_SESSION. Model-access posture: PROVIDER_NEUTRAL_REMOTE_MODEL_CANDIDATES_WITH_OPTIONAL_LOCAL_BASELINE. Provider decision: SHORTLIST_MAXIMUM_TWO_REMOTE_CANDIDATES_PLUS_OPTIONAL_ONE_LOCAL_BASELINE. Experiment data classification: SYNTHETIC_OFFLINE_TEST_DATA_ONLY. Network posture for the first future experiment: PROVIDER_ENDPOINT_ONLY_DENY_ALL_OTHER_NETWORK. Repository posture: NO_REPOSITORY_WIDE_ACCESS. Command and shell posture: DISABLED. Tool posture: NO_BROWSER_NO_SEARCH_NO_SOURCE_FETCH_NO_TRADING_TOOLS. Memory posture: EPHEMERAL_SESSION_MEMORY_ONLY. Persistent memory: FORBIDDEN. Credential posture: OUT_OF_REPO_OPERATOR_INJECTED_LEAST_PRIVILEGE_REVOCABLE_SECRET. Maximum total remote calls: 140. Maximum total experiment spend: USD 100. Maximum daily spend: USD 25. Maximum single-call spend: USD 2. Concurrent remote calls: 1. Provider activation: NOT AUTHORIZED. Hermes installation/runtime activation: NOT AUTHORIZED. Paper/live/execution authority: FORBIDDEN. WP144 was separately approved as the documentation-only harness-contract and dry-run-plan package. Canonical document is `docs/hermes_candidate_review_assisted_research_provider_runtime_privacy_permissions_budget_decision.md`; WP143 adds no source, tools, runtime, provider/model/credential activation, product network, source retrieval, storage, recommendation, probability, ranking, paper/live, execution/risk/order, acceptance, or promotion authority.
- Hermes candidate-review assisted research controlled experiment harness contract, prompt/configuration boundary, and dry-run plan status: DOCS_STATUS_TESTS_ONLY_HERMES_CONTROLLED_EXPERIMENT_HARNESS_CONTRACT_DRY_RUN_PLAN_MERGED; Harness contract status: DOCUMENTATION_ONLY_RUNTIME_INACTIVE. Controller authority: LOCAL_DETERMINISTIC_EXCLUSIVE. Hermes session posture: ONE_CASE_ONE_EPHEMERAL_SESSION. Provider adapter posture: ONE_EXPLICIT_CANDIDATE_CONFIGURATION_ONE_ALLOWLISTED_ENDPOINT. Prompt/configuration status: VERSIONED_NON_EXECUTABLE_CONTRACT_ONLY. Input posture: EXACT_VALIDATED_WP142_CASE_BUNDLE_ONLY. Output posture: UNTRUSTED_DRAFT_ONLY. Raw input/output persistence: FORBIDDEN_BY_DEFAULT. Sanitized experiment metadata: FUTURE_ALLOW_EXACT_FIELDS_ONLY. Network posture: DENY_ALL_EXCEPT_ONE_CONTROLLER_MEDIATED_PROVIDER_ENDPOINT. Tool posture: NO_BROWSER_NO_SEARCH_NO_SOURCE_FETCH_NO_SHELL_NO_TRADING_TOOLS. Memory posture: EPHEMERAL_SESSION_ONLY_DELETE_ON_TEARDOWN. Dry-run posture: LOCAL_NO_PROVIDER_NO_NETWORK_NO_CREDENTIAL. Deterministic validation and human review: MANDATORY. Hermes/provider/model activation: NOT AUTHORIZED. Paper/live/execution authority: FORBIDDEN. WP145 was separately approved as the local skeleton and test-only no-network dry-run package. Canonical document is `docs/hermes_candidate_review_assisted_research_controlled_experiment_harness_contract_prompt_configuration_boundary_and_dry_run_plan.md`; WP144 adds no source, tools, workflow, controller, adapter, prompt/config artifact, runtime, provider/model/credential activation, product network, dry-run execution, source retrieval, storage, recommendation, probability, ranking, paper/live, execution/risk/order, acceptance, or promotion authority.
- Hermes candidate-review assisted research local deterministic harness skeleton and no-network dry-run status: LOCAL_OFFLINE_TEST_ORIENTED_SKELETON_MERGED; Harness implementation status: LOCAL_OFFLINE_TEST_ORIENTED_SKELETON. Controller authority: LOCAL_DETERMINISTIC_EXCLUSIVE. Adapter status: TEST_ONLY_PRECOMPUTED_FAKE_RESPONSE. External callable invoked: FALSE. Adapter call count: 0. Exact positive-case outcome: MANDATORY. Ten WP142 hard gates: EXPLICITLY_DERIVED. Recursive source-access scan: ALL_VALIDATED_TEXT_SURFACES. Dry-run case count: 1. Dry-run case ID: GC-P01-COMPLETE-SUPPORTED. Network: FORBIDDEN. Credentials: FORBIDDEN. Hermes installation/invocation: FORBIDDEN. Provider/model call: FORBIDDEN. Stable raw input/output persistence: FORBIDDEN. Temporary filesystem: PYTEST_TMP_PATH_ONLY. Output: SANITIZED_EVIDENCE_ONLY. Deterministic WP133 validation: MANDATORY. Human review: EXPLICIT_CALLER_SUPPLIED_ACKNOWLEDGEMENT_REQUIRED. Automatic downstream records: FORBIDDEN. Paper/live/execution authority: FORBIDDEN. WP146 was separately approved as the local-harness closeout and remote-readiness decision package. Canonical module is `src/data_layer/hermes_candidate_review_assisted_research_local_dry_run_harness.py`; operator note is `docs/hermes_candidate_review_assisted_research_local_dry_run_harness_operator_note.md`; WP145 adds no Hermes/provider/model/credential/product-network/source-fetching/stable-output/downstream-record/paper/live/execution/trading behavior.
- Hermes candidate-review assisted research local-harness closeout and controlled remote-experiment readiness decision status: DOCS_STATUS_TESTS_ONLY_LOCAL_HARNESS_CLOSEOUT_REMOTE_READINESS_DECISION_MERGED; Local harness phase status: CLOSED_COMPLETE_ENOUGH_FOR_BOUNDED_LOCAL_DRY_RUN. WP145 corrected evidence accepted: YES. Local one-case dry-run status: ACCEPTED_AS_TEST_ONLY_CONTROL_EVIDENCE. WP145 implementation classification: BOUNDED_LOCAL_CONTROL_SKELETON. WP145 phase-completion decision: ACCEPT. Remote controlled experiment readiness: NOT_READY. Primary remote-readiness blocker: CURRENT_PROVIDER_MODEL_PRIVACY_RETENTION_COST_AND_ENDPOINT_EVIDENCE_MISSING. Provider/model candidate naming: DEFERRED_CURRENT_EXTERNAL_RESEARCH_REQUIRED. Current external provider/model research: REQUIRED_BEFORE_REMOTE_EXPERIMENT_IMPLEMENTATION. Remote experiment implementation authorization: DENIED_PENDING_RESEARCH_AND_CONTROL_GATES. Remote adapter implementation: NOT AUTHORIZED. Hermes installation/invocation: NOT AUTHORIZED. Provider/model call: NOT AUTHORIZED. Credential creation/use: NOT AUTHORIZED. Network endpoint activation: NOT AUTHORIZED. Experiment spending: NOT AUTHORIZED. Raw input/output persistence: NOT AUTHORIZED. Paper/live/execution authority: FORBIDDEN. Next phase: CURRENT_PROVIDER_MODEL_PRIVACY_RETENTION_COST_RESEARCH_AND_CANDIDATE_SHORTLIST. WP147 was separately approved. Canonical document is `docs/hermes_candidate_review_assisted_research_local_harness_closeout_and_controlled_remote_experiment_readiness_decision.md`; WP146 adds no source, tools, runtime, provider/model activation, credentials, product network, endpoint activation, spending, storage, recommendation, probability, ranking, paper/live, execution/risk/order, or trading authority.
- Hermes candidate-review assisted research current provider/model, privacy, retention, cost, endpoint, and candidate-shortlist research status: DOCS_STATUS_TESTS_ONLY_CURRENT_PROVIDER_MODEL_RESEARCH_AND_CANDIDATE_SHORTLIST_MERGED; WP147 research status: COMPLETE. PR147-FU1 classification: B — candidate-eligibility evidence integrity and canonical evidence consistency. Research cut-off: 2026-07-22T23:49:02Z. Candidate pool posture: CURRENT_AUTHORITATIVE_FIRST_PARTY_RESEARCH_ONLY. Provider decision: NO_PROVIDER_SELECTED_EVIDENCE_INSUFFICIENT. Remote configurations researched deeply: 3. Remote configurations eligible: 0. Remote configurations shortlisted: 0. Candidate shortlist decision: EVIDENCE_INSUFFICIENT_NO_SHORTLIST. Candidate classifications: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES, and ANT-SONNET-MESSAGES are NOT_SHORTLISTABLE_EVIDENCE_INSUFFICIENT; GGL-FLASH-DEVELOPER is PRELIMINARY_STOP_EVIDENCE_INSUFFICIENT. Canonical Anthropic costs: expected_us_geo_cost: USD 0.0594; stress_us_geo_cost: USD 0.2970. Local baseline decision: DEFERRED_HARDWARE_EVIDENCE_MISSING. Remote controlled experiment readiness: NOT_READY. Provider/model activation: NOT AUTHORIZED. Provider/model call: NOT AUTHORIZED. Hermes installation/invocation: NOT AUTHORIZED. Provider account creation: NOT AUTHORIZED. Credential creation/use: NOT AUTHORIZED. Network endpoint activation: NOT AUTHORIZED. Experiment spending: NOT AUTHORIZED. Raw input/output persistence: NOT AUTHORIZED. Paper/live/execution authority: FORBIDDEN. Next phase: MANDATORY_EVIDENCE_RESOLUTION_AND_RESEARCH_REFRESH_DECISION. WP148 was separately approved. Canonical document is `docs/hermes_candidate_review_assisted_research_current_provider_model_privacy_retention_cost_endpoint_research_and_candidate_shortlist.md`; WP147 adds no source, tools, fixtures, workflows, dependencies, locks, runtime, provider/model activation/calls, credentials, product network, spending, storage, recommendation, probability, ranking, paper/live, execution/risk/order, or trading authority.
- Hermes candidate-review assisted research mandatory provider evidence resolution and research refresh decision status: DOCS_STATUS_TESTS_ONLY_MANDATORY_PROVIDER_EVIDENCE_RESOLUTION_AND_RESEARCH_REFRESH_DECISION_MERGED; Research cut-off: 2026-07-23T16:10:31Z. Refreshed source count: 11. Tier 1 source count: 10. Tier 2 source count: 1. Tier 2 source IDs: ANT-R02. OpenAI deletion result: EVIDENCE_INSUFFICIENT. OpenAI key-lifecycle result: EVIDENCE_INSUFFICIENT. Anthropic deletion result: EVIDENCE_INSUFFICIENT. Anthropic subprocessor result: PASS. Anthropic security/incident result: PASS. Google result: EVIDENCE_INSUFFICIENT. WP148 evidence-resolution status: COMPLETE_EVIDENCE_STILL_INSUFFICIENT. Candidate eligibility result: EVIDENCE_INSUFFICIENT_NO_ELIGIBLE_CANDIDATE. Remote configurations deeply researched: 3. Remote configurations eligible: 0. Remote configurations shortlisted: 0. Provider/model selection: NOT MADE. Local baseline pivot decision: DEFER_HARDWARE_EVIDENCE_MISSING. Remote controlled experiment readiness: NOT_READY. Next phase: REMOTE_PROVIDER_TRACK_DEFER_OR_RESEARCH_REFRESH_LATER_DECISION. Provider/model activation: NOT AUTHORIZED. Provider/model call: NOT AUTHORIZED. Hermes installation/invocation: NOT AUTHORIZED. Provider account creation: NOT AUTHORIZED. Credential creation/use: NOT AUTHORIZED. Network endpoint activation: NOT AUTHORIZED. Experiment spending: NOT AUTHORIZED. Raw input/output persistence: NOT AUTHORIZED. Paper/live/execution authority: FORBIDDEN. WP149 requires separate approval and was separately approved for this decision package. Canonical document is `docs/hermes_candidate_review_assisted_research_mandatory_provider_evidence_resolution_and_research_refresh_decision.md`; WP148 adds no source, tools, fixtures, workflows, dependencies, locks, configuration, credentials, prompts, runtime, provider/model calls, endpoint activation, spending, storage, paper/live, execution/risk/order, or trading authority.
- Hermes remote provider track deferral and revisit criteria decision status: DOCS_STATUS_TESTS_ONLY_REMOTE_PROVIDER_TRACK_DEFERRAL_REVISIT_CRITERIA_DECISION_MERGED; Remote provider track status: DEFERRED_PENDING_MATERIAL_NEW_EVIDENCE. Automatic periodic provider re-research: FORBIDDEN. Repeated unchanged provider research: FORBIDDEN. Scheduled periodic provider sweep: FORBIDDEN. Reopen based only on elapsed time: FORBIDDEN. Provider track may reopen only after: MATERIAL_EVIDENCE_TRIGGER_AND_SEPARATE_APPROVAL. Deferral review cadence: EVENT_DRIVEN_ONLY. Remote configurations eligible: 0. Remote configurations shortlisted: 0. Provider/model selection: NOT MADE. Remote controlled experiment readiness: NOT_READY. Provider/model activation: NOT AUTHORIZED. Provider/model call: NOT AUTHORIZED. Hermes installation/invocation: NOT AUTHORIZED. Provider account creation: NOT AUTHORIZED. Credential creation/use: NOT AUTHORIZED. Network endpoint activation: NOT AUTHORIZED. Experiment spending: NOT AUTHORIZED. Raw input/output persistence: NOT AUTHORIZED. Paper/live/execution authority: FORBIDDEN. Next phase: LOCAL_RESEARCH_WORKFLOW_VALUE_VALIDATION_AND_PAPER_TRADING_READINESS_DECISION. WP150 requires separate approval. WP150 was separately approved. Canonical document is `docs/hermes_remote_provider_track_deferral_and_revisit_criteria_decision.md`; WP149 adds no provider research, candidate, shortlist, selection, source, tools, fixtures, workflows, dependencies, locks, configuration, credentials, prompts, runtime, provider/model calls, endpoint activation, spending, storage, scheduled task, paper/live, execution/risk/order, or trading authority.
- Local research workflow value validation and paper-trading readiness decision status: DOCS_STATUS_MARKDOWN_TESTS_ONLY_LOCAL_RESEARCH_VALUE_AND_PAPER_READINESS_DECISION_MERGED; Review follow-up required: YES. Classification: B — positive readiness conclusion was not fully grounded in current structured fields. Local workflow stages inventoried: 20. Implemented and tested: 13. Limited/manual: 4. Contract/runbook only: 2. Synthetic only: 1. Absent local workflow stages: 0. Evidence-insufficient local workflow stages: 0. Local research workflow value-validation status: PARTIALLY_READY_BLOCKERS_IDENTIFIED. Research-value metric records: 39. Research-value metrics measured: 0. Research-value metrics measurable but not yet measured: 22. Research-value metrics not currently measurable: 17. Research throughput: 3 MEASURABLE_NOT_YET_MEASURED / 3 NOT_CURRENTLY_MEASURABLE. Candidate rejection quality: 6 MEASURABLE_NOT_YET_MEASURED / 1 NOT_CURRENTLY_MEASURABLE. Hypothesis quality: 2 MEASURABLE_NOT_YET_MEASURED / 5 NOT_CURRENTLY_MEASURABLE. Reproducibility: 6 MEASURABLE_NOT_YET_MEASURED / 1 NOT_CURRENTLY_MEASURABLE. Strategy-validation handoff quality: 5 MEASURABLE_NOT_YET_MEASURED / 2 NOT_CURRENTLY_MEASURABLE. Operator burden: 0 MEASURABLE_NOT_YET_MEASURED / 5 NOT_CURRENTLY_MEASURABLE. Research-value blockers: 7. Market data: PARTIALLY_READY. Replay/fill: ABSENT. Strategy input: NOT_READY. Order lifecycle: ABSENT. Accounting: ABSENT. Risk: ABSENT. Observability: ABSENT. Reconciliation: ABSENT. Operations: ABSENT. Paper-trading implementation readiness: NOT_READY_FOUNDATIONAL_GAPS. Paper-trading execution: NOT AUTHORIZED. Live-trading execution: FORBIDDEN. Capital at risk: USD 0. Orders submitted: 0. Credentials created/used: 0. External model calls: 0. Next phase: LOCAL_RESEARCH_WORKFLOW_VALUE_MEASUREMENT_HARNESS_CONTRACT. WP151 requires separate approval. WP151 was separately approved. Canonical document is `docs/local_research_workflow_value_validation_and_paper_trading_readiness_decision.md`; WP150 adds no external research, source, tools, fixtures, workflows, dependencies, locks, configuration, credentials, provider/model/Hermes calls, network probes, runtime, scheduler, paper engine, simulated orders/fills, accounting, risk, reconciliation, paper/live execution, capital, or trading authority.
- Local research workflow value measurement harness contract status: DOCS_STATUS_MARKDOWN_TESTS_ONLY_LOCAL_RESEARCH_VALUE_MEASUREMENT_HARNESS_CONTRACT_MERGED; Measurement harness contract status: COMPLETE_READY_FOR_BOUNDED_IMPLEMENTATION_WP. Measurement architecture: LOCAL_DETERMINISTIC_OPERATOR_INITIATED_TEMPORARY_HARNESS. Execution posture: OFFLINE_LOCAL_NO_PROVIDER_NO_MARKET_NETWORK. Authority posture: RESEARCH_MEASUREMENT_ONLY_NO_STRATEGY_NO_PAPER_NO_LIVE. Output posture: IN_MEMORY_OR_PYTEST_TEMPORARY_ONLY. Orchestration posture: EXPLICIT_SINGLE_RUN_NO_SCHEDULER. Initial harness metric scope: GROUNDED_22_METRICS_ONLY. Blocked metric posture: CONTRACT_DEFINED_IMPLEMENTATION_DEFERRED. Research-value metric records: 39. Research-value metrics measured: 0. Research-value metrics measurable but not yet measured: 22. Research-value metrics not currently measurable: 17. Wave 1 metrics: 22. Wave 2 metrics: 17. Workflow stages: 20. Corpus cases: 14. Corpus families: 14. Event types: 13. Run statuses: 9. Required repeats per selected case: 3. Allowed output modes: 3. WP150 blockers mapped: 7. Contract-resolved blockers: 7. Implementation-required blockers: 7. Separate schema decision required: NO. Separate schema implementation required: YES. Measurement harness implementation: NOT AUTHORIZED IN WP151. Measurement run: NOT AUTHORIZED IN WP151. Measurement receipts generated: 0. Persistent measurement output: NOT AUTHORIZED. Paper-trading implementation readiness: NOT_READY_FOUNDATIONAL_GAPS. Paper-trading execution: NOT AUTHORIZED. Live-trading execution: FORBIDDEN. Capital at risk: USD 0. Orders submitted: 0. Credentials created/used: 0. External model calls: 0. Scheduler/tasks: 0. Next phase: BOUNDED_LOCAL_RESEARCH_VALUE_MEASUREMENT_HARNESS_IMPLEMENTATION. WP152 required separate approval and was separately approved. Canonical document is `docs/local_research_workflow_value_measurement_harness_contract.md`; WP151 added no source, tools, fixtures, workflows, dependencies, locks, configuration, runtime, credentials, provider/model/Hermes, instrumentation, measurement harness, measurement run, persistent output, paper engine, scheduler, paper/live execution, risk/order authority, or trading behavior.
- Local research workflow value measurement harness implementation status: LOCAL_OFFLINE_DETERMINISTIC_WAVE_1_MEASUREMENT_HARNESS_MERGED; Review follow-up required: YES; Classification: F/G — implementation semantics and adversarial-test coverage; Follow-up resolution: exact six-outcome WP151 human-review vocabulary, one mutually exclusive final disposition per selected case, defer/correction/retry completion prevention, global abort precedence, action/event/receipt reconciliation, bounded event state/error vocabularies, recursive event/receipt safety validation, contextual forbidden-variant coverage, exactly three complete actual-metric measurement passes, non-circular RV-REP-06 derivation, canonical-pass receipt reconciliation, and exact selected-case/repeat/stage/event total ordering; Current PR reused: YES; Separate hardening WP required: NO; WP153 implemented: NO. Bounded Wave 1 harness implementation: IMPLEMENTED_AND_TESTED. Registry records: 39. Wave 1 metrics implemented: 22. Wave 2 metrics implemented: 0. Wave 2 metrics blocked: 17. Fixed corpus: SYNTHETIC_SANITIZED_OFFLINE_FIXED. Corpus cases: 14. Corpus families: 14. Workflow stages: 20. Event types: 13. Run statuses: 9. Safety gates: 12. Required repeats per selected case: 3. Output modes exercised: IN_MEMORY_ONLY and PYTEST_TMP_PATH_ONLY. Measurement runs accepted: 0. Measurement receipts accepted: 0. Product/runtime network calls: 0. Credentials accessed: 0. Provider/model/Hermes calls: 0. Paper/live orders: 0. Capital at risk: USD 0. Scheduler/tasks: 0. Persistent output: 0. Paper-trading implementation readiness: NOT_READY_FOUNDATIONAL_GAPS. Paper-trading execution: NOT AUTHORIZED. Live-trading execution: FORBIDDEN. Next sequence phase reconciled by the separately approved WP153 bounded synthetic dry run and receipt review; the merged WP152 harness accepted no project-level measurement run or receipt. Canonical implementation is `src/data_layer/local_research_value_measurement/`; the fixed corpus is `tests/fixtures/local_research_workflow_value_measurement_v1.json`; WP152 adds no Wave 2 schema, provider/model/Hermes, credential, strategy, paper/live, order, execution/risk, scheduler, dependency, database, telemetry, writer, or permanent-output behavior.
- Local research workflow value measurement dry run and receipt review status: LOCAL_OFFLINE_DETERMINISTIC_SYNTHETIC_DRY_RUN_AND_RECEIPT_REVIEW_MERGED; Synthetic project dry runs completed: 1; Synthetic research-memory receipts accepted: 1; Real workflow measurement runs accepted: 0; Real workflow research-value metrics measured: 0; run_id: WP153-DRY-RUN-001; operator_run_label: WP152_SYNTHETIC_VALIDATION; Case count: 14; Corpus families: 14; Repeat count: 3; Stage instances per repeat: 30; Event count: 392; Metric result count: 39; Wave 1 harness metrics implemented: 22; Wave 2 metrics implemented: 0; Wave 2 metrics blocked: 17; Wave 2 populated value fields: 0; Repeatability PASS results: 14; Safety gates: 12; Acknowledgement actions: 14; Other operator actions: 0; run_status: RUN_VALID_MEASUREMENT_COMPLETE; human_review_status: ACCEPT_MEASUREMENT_RECEIPT_FOR_RESEARCH_MEMORY_ONLY; Hard failures: 0; temporary_output_status: IN_MEMORY_ONLY; Run-created files: 0; corpus_content_sha256: 0133b3444aab0a4d045035e292cb46c675de682cee1cc8c5cb4e29fd5dfc3ced; event_stream_sha256: 31eca5ee6b7881029585f494de0740f04fd068ac9625b4cd8b387b41a87f3135; receipt_sha256: 5a60772bec6c582a83a1e36bfeaa60de4a7aff7840f8ec9b7f33ad9f17234750; public_result_sha256: f95101f9ed82ca32cc458f2133b8cb0c34e2adfccf0619b349c993fafcc8b514; Replay byte-equal: YES; Paper-trading readiness: NOT_READY_FOUNDATIONAL_GAPS; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; Persistent raw measurement output: 0; Capital at risk: USD 0; Orders submitted: 0; Credentials used: 0; External model calls: 0; Scheduler/tasks: 0; Next sequence phase reconciled by the separately approved WP154 architecture decision. Canonical document is `docs/local_research_workflow_value_measurement_dry_run_and_receipt_review.md`; the 22 Wave 1 MEASURED_VALID results are synthetic harness outputs over the fixed invented corpus and are not real research-value metrics; WP153 adds no source, fixture, contract, Wave 2 schema, provider/model/Hermes, credential, strategy, paper/live, order, execution/risk, scheduler, dependency, database, telemetry, writer, or generated-artifact behavior, and the WP152 harness and fixed corpus are byte-unchanged.
- Adoption architecture, dependency registry and alpha-factory roadmap status: DOCS_STATUS_TESTS_ONLY_ADOPTION_ARCHITECTURE_DEPENDENCY_REGISTRY_ALPHA_FACTORY_ROADMAP_MERGED; Finished-system architecture: MEASURABLE_ALPHA_FACTORY_PLUS_DETERMINISTIC_TRADING_KERNEL; Alpha lineage stages: 9; Adoption phases: 10 (A-J); Alpha priorities: 5; Dependency registry candidates: 15; Listed dependencies approved: 0; Dependencies installed or activated: 0; AI/Hermes authority: UNTRUSTED_ADVISORY_ONLY_NO_EXECUTE_VALIDATE_TRANSITION_SCHEDULE_AUTHORIZE; Deterministic kernel authority: EXCLUSIVE_FOR_IDENTITY_VALIDATION_LINEAGE_TRANSITIONS_REPLAY_FILL_COST_PAPER_ORDER_EXECUTION_RECONCILIATION_ACCOUNTING_RISK_CREDENTIALS_RUNTIME_INCIDENTS_ELIGIBILITY_LIVE_SAFETY; Paper-trading readiness: NOT_READY_FOUNDATIONAL_GAPS; Paper-trading execution: NOT AUTHORIZED; Restricted-live eligibility: NOT ESTABLISHED; Live-trading execution: FORBIDDEN; Capital at risk: USD 0; Provider/model/Hermes runtime calls: 0; Product/runtime network calls: 0; Credentials accessed: 0; Scheduler/tasks: 0; Source/dependency/lock/workflow changes: 0; Planning estimates only: YES; Next sequence phase reconciled by the separately approved WP155 point-in-time market research data foundation contract. Canonical document is `docs/adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in.md`; WP154 lists candidates for evaluation only and added no source, dependency, lock, workflow, runtime, credential, provider/model/Hermes call, product network, market-data collection, scheduler, strategy, paper/live, order, fill, accounting, risk, reconciliation, execution, capital, copied external code, or WP155 behavior.
- Point-in-time market research data foundation contract status: POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT_MERGED; Contract posture: CONTRACT_ONLY_NO_WRITER_NO_DEPENDENCY_NO_COLLECTION; Default visibility: AS_OF_INGESTION_TIME; Diagnostic visibility: AS_OF_OBSERVED_TIME_INGESTION_BOUNDED; Domain filter: EVENT_TIME_WINDOW_AFTER_VISIBILITY; History posture: NO_DESTRUCTIVE_HISTORY_REWRITE; Storage decision: PARQUET_ARROW_PREFERRED_BUT_NOT_INSTALLED; Initial partition contract: record_family / schema_major / ingestion_date_utc; Analytics decision: BENCHMARK_REQUIRED_NO_ADOPTION_DECISION; Canonical hash: SHA-256; Schema evolution: SEMVER_FAIL_CLOSED_APPEND_ONLY; AI/Hermes authority: ADVISORY_ONLY_NO_CANONICAL_DATA_AUTHORITY; External tool authority: NONE_FOR_PROJECT_SEMANTICS; Product/runtime network calls: 0; Credentials accessed: 0; Provider/model/Hermes runtime calls: 0; Scheduler/tasks: 0; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; Capital at risk: USD 0; Next sequence phase reconciled by the separately approved WP156 bounded point-in-time validator implementation. Canonical document is `docs/point_in_time_market_research_data_foundation_contract.md`; WP155 defines deterministic research-data semantics only and grants no writer, storage, dependency, collector, network, credential, strategy, paper/live, or execution authority.
- Point-in-time observation schema validator and synthetic fixture implementation status: LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION_MERGED; Foundation label: POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT; Supported schema: point-in-time-market-research-record@1.0.0; Record families: 3; Observation kinds: 3; Lifecycle states: 6; Record classifications: 8; Validation statuses: 6; Frozen public dataclasses: 8; Public functions: 8; Synthetic cases: 20; Maximum batch records: 256; Canonical JSON maximum bytes: 65536; Dependencies added: 0; Writers/readers/manifests/databases/query engines/collectors/migrations: 0; Existing Polymarket snapshot behavior changed: NO; Product/runtime network calls: 0; Credentials accessed: 0; Provider/model/Hermes runtime calls: 0; Scheduler/tasks: 0; Strategy/signal/paper/order/risk/execution authority: NONE; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; Capital at risk: USD 0; Next sequence phase reconciled by the separately approved WP157 bounded in-memory as-of query implementation; WP157 implemented: YES. Canonical document is `docs/point_in_time_observation_schema_validator_and_synthetic_fixture_implementation.md`.
- Bounded in-memory point-in-time record-set reconstruction and as-of query status: BOUNDED_IN_MEMORY_AS_OF_INGESTION_TIME_RECONSTRUCTION_MERGED; Foundation label: POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT; As-of query label: POINT_IN_TIME_RECORD_SET_RECONSTRUCTION; Consumes: valid WP156 public record objects only; Supported cutoff modes: 2; Supported result views: 3; Query statuses: 6; Exclusion reasons: 12; New frozen query dataclasses: 5; New public query functions: 3; Synthetic as-of query cases: 24; Default visibility contract: AS_OF_INGESTION_TIME; Observed diagnostic bound: INGESTION_BOUNDED; Maximum input records: 256; Maximum filter values per field: 128; Maximum total filter values: 512; Maximum result records per tuple: 256; Dependencies added: 0; Writers/readers/manifests/databases/query engines/collectors/migrations/persistence: 0; WP156 change: NARROW_ADDITIVE_REVIEW_ONLY_CONFLICT_HANDOFF_ALL_WP156_TESTS_PRESERVED; Existing Polymarket snapshot behavior changed: NO; Product/runtime network calls: 0; Credentials accessed: 0; Provider/model/Hermes runtime calls: 0; Scheduler/tasks: 0; Strategy/signal/paper/order/risk/execution authority: NONE; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; Capital at risk: USD 0; Next sequence phase reconciled by the separately approved WP158 append-only local manifest and deterministic dataset snapshot reference contract; WP158 implemented: YES. Canonical document is `docs/bounded_in_memory_point_in_time_record_set_reconstruction_and_as_of_query_implementation.md`.
- Append-only local manifest and deterministic dataset snapshot reference contract status: APPEND_ONLY_LOCAL_MANIFEST_AND_DETERMINISTIC_DATASET_SNAPSHOT_REFERENCE_CONTRACT_MERGED; Contract posture: CONTRACT_ONLY_NO_WRITER_NO_READER_NO_PERSISTENCE; Dataset snapshot reference schema: point-in-time-dataset-snapshot-reference@1.0.0; Local manifest entry schema: point-in-time-local-manifest-entry@1.0.0; Dataset derivation modes: 2; Manifest entry kinds: 3; Reference states: 3; Reason codes: 3; Reference identity prefix: datasetref:sha256:; Manifest entry identity prefix: manifestentry:sha256:; New src files: 0; New public exports: 0; Writers/readers/manifests/databases/query engines/collectors/migrations/persistence: 0; WP157 public surface changed: NO; Product/runtime network calls: 0; Credentials accessed: 0; Provider/model/Hermes runtime calls: 0; Scheduler/tasks: 0; Strategy/signal/paper/order/risk/execution authority: NONE; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; Capital at risk: USD 0; Next sequence phase reconciled by the separately approved WP159 V6 / XL23 draftability foundation and exact-scope enforcement; WP159 implemented as draft PR: YES; WP159 Ready for review: NO. Canonical document is `docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md`.
- Append-only local manifest and dataset snapshot reference validation status: APPEND_ONLY_LOCAL_MANIFEST_AND_DATASET_SNAPSHOT_REFERENCE_VALIDATION_MERGED; Implementation posture: BOUNDED_LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION; Source module: `src/data_layer/point_in_time_market_research/manifest_reference.py`; Realizes: the merged WP158 append-only local manifest and deterministic dataset snapshot reference contract; Dataset snapshot reference schema: point-in-time-dataset-snapshot-reference@1.0.0; Local manifest entry schema: point-in-time-local-manifest-entry@1.0.0; Dataset derivation modes: 2; Manifest entry kinds: 3; Reference states: 3; Reason codes: 3; Validation statuses: 8; Error codes: 15; Warning codes: 0; New frozen dataclasses: 5; New public functions: 3; Reference identity prefix: datasetref:sha256:; Manifest entry identity prefix: manifestentry:sha256:; Maximum manifest entries: 256; Maximum dataset references: 256; Maximum combined record IDs: 256; New src files: 1; Package export inventory grew by: 20; Writers/readers/manifests/databases/query engines/collectors/migrations/persistence: 0; WP156/WP157 public surface changed: NO; Product/runtime network calls: 0; Credentials accessed: 0; Provider/model/Hermes runtime calls: 0; Scheduler/tasks: 0; Strategy/signal/paper/order/risk/execution authority: NONE; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; Capital at risk: USD 0; Abandoned governance-oriented WP160 draft: NEVER_IMPLEMENTED; WP160 PR: 160; WP160 final head: 2b2ef59926d07d34372e3f2999c199ffc43bab2c; WP160 merge commit: a6f88051d13aca137dfe036784f1376b5dc0c635; Next sequence phase reconciled by the separately approved WP161 bounded SQLite persistence package; WP160 implemented and merged: YES; WP161 implemented as draft PR: YES. Canonical document is `docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md`.
- Bounded local SQLite manifest store status: POINT_IN_TIME_LOCAL_SQLITE_MANIFEST_STORE; Implementation posture: BOUNDED_LOCAL_SQLITE_TRANSACTIONAL_APPEND_AND_VERIFIED_READ; Source module: `src/data_layer/point_in_time_market_research/manifest_store.py`; Storage engine: Python standard-library sqlite3; Explicit caller-selected path only: YES; Store format: point-in-time-manifest-store; Schema version and user_version: 1; Application tables: 3; Journal mode: DELETE; Writable synchronous: FULL; Writable foreign_keys: ON; Transaction start: BEGIN IMMEDIATE; Read URI mode: ro; Existing-write URI mode: rw; Creation URI mode: rwc; Maximum dataset references: 256; Maximum manifest entries: 256; Maximum canonical payload bytes per row: 65536; New frozen dataclasses: 2; New public functions: 3; New public constants: 6; Package export inventory grew by: 11; Canonical payload digest: SHA-256; Integrity checks: integrity_check plus foreign_key_check; Idempotent retry uses UPDATE: NO; Public persisted-row DELETE path: NO; Schema migration: NOT AUTHORIZED; WAL: FORBIDDEN; Dependencies added: 0; Product/runtime network calls: 0; Credentials accessed: 0; Scheduler/tasks: 0; Strategy/signal/paper/order/risk/execution authority: NONE; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; Capital at risk: USD 0; WP161 implemented as draft PR: YES; WP161 Ready for review: NO; Merge authorized: NO; Next sequence phase: adapters and real/public dataset population separately gated. Canonical document is `docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md`.
- Dataset persistence adapter status: POINT_IN_TIME_RESEARCH_DATASET_PERSISTENCE_ADAPTER; Implementation posture: BOUNDED_DETERMINISTIC_WP156_WP157_TO_WP160_WP161_HANDOFF; Source module: `src/data_layer/point_in_time_market_research/dataset_persistence_adapter.py`; Bridges: WP156 validated record batch and WP157 as-of query result into a WP160 DatasetSnapshotReference plus a WP160 REGISTER ManifestEntry persisted through the WP161 SQLite manifest store; Upstream recomputed from caller records/spec: YES; Caller batch/query/reference/entry/sequence/previous-head trusted: NO; New frozen dataclasses: 1; New public functions: 2; New public constants: 4; Package export inventory grew by: 7; Statuses: ADAPTER_PERSISTED, ADAPTER_ALREADY_PERSISTED, ADAPTER_REJECTED; Error codes: 12; SQLite import in adapter: NO; Direct SQL in adapter: NO; Direct filesystem/open/pathlib/os in adapter: NO; Store initialized/migrated by adapter: NO; Wall-clock time read by adapter: NO; Raw record payload persistence: NO; External known-parent lineage context: NO; Automatic supersede/invalidate: NO; Dependencies added: 0; Product/runtime network calls: 0; Credentials accessed: 0; Scheduler/tasks: 0; Strategy/signal/paper/order/risk/execution authority: NONE; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; Capital at risk: USD 0; WP161 implemented and merged: YES; WP162 Ready for review: YES; Merge authorized: NO; WP161-D004 resolved for bounded reference-and-registration scope only: YES; Next sequence phase: durable raw/public point-in-time record materialization decision separately gated. Canonical document is `docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md`.
- Bounded durable point-in-time record store status: POINT_IN_TIME_DURABLE_RECORD_STORE; Implementation posture: BOUNDED_LOCAL_SQLITE_APPEND_ONLY_RECORD_PERSISTENCE_AND_MATERIALIZATION; Source module: `src/data_layer/point_in_time_market_research/record_store.py`; Storage engine: Python standard-library sqlite3; Explicit caller-selected path only: YES; Store format: point-in-time-record-store; Schema version and user_version: 1; Application tables: 2; Explicit indexes: 5; Journal mode: DELETE; Writable synchronous: FULL; Writable foreign_keys: ON; Transaction start: BEGIN IMMEDIATE; Read URI mode: ro; Existing-write URI mode: rw; Creation URI mode: rwc; Maximum records per append: 256; Maximum records in store: 4096; Maximum canonical full-record payload bytes per row: 131072; Maximum total canonical payload bytes: 134217728; New frozen dataclasses: 3; New public functions: 4; New public constants: 7; Package export inventory grew by: 14; Canonical full-record payload persisted: YES; Canonical payload digest: SHA-256; Ordinary self-validation through WP156 validate_record_batch: YES; Review-conflict self-validation through revalidate_review_conflict_record: YES; Complete cross-record lineage validated on append and load: YES; Conflict record ever ordinary authority: NO; Idempotent retry uses UPDATE: NO; Public persisted-row DELETE path: NO; Schema migration: NOT AUTHORIZED; WAL: FORBIDDEN; Parquet/Arrow/DuckDB/Polars adopted: NO; Raw HTTP/source-response bytes stored: NO; Real/public network collection performed: NO; VALIDATED_RECORD_BATCH materialization recomputes batch identity: YES; AS_OF_QUERY_RESULT materialization is ID-resolution only: YES; Dependencies added: 0; Product/runtime network calls: 0; Credentials accessed: 0; Scheduler/tasks: 0; Strategy/signal/paper/order/risk/execution authority: NONE; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; Capital at risk: USD 0; WP163 Ready for review: YES; Merge authorized: NO; WP162-D001 resolved for bounded SQLite record store and reference materialization scope: YES; Next sequence phase: WP164 bounded real/public Polymarket point-in-time data population separately gated. Canonical document is `docs/point_in_time_record_store_contract.md`.
- Bounded real/public initial Polymarket population status: POLYMARKET_REAL_PUBLIC_INITIAL_POINT_IN_TIME_POPULATION; Implementation posture: EXPLICIT_NETWORK_GET_ONLY_BOUNDED_INITIAL_SEED_NO_TRADING_AUTHORITY; Source module: `src/data_layer/point_in_time_market_research/polymarket_public_population.py`; Package class: DATA_LAYER_PUBLIC_POPULATION; Size class: L; Risk level: 1; Default network posture: OFF; Public GET-only network reads when explicitly enabled: YES; Endpoints: Gamma GET /markets and optional CLOB GET /book only; Authenticated endpoints used: NONE; POST /books used: NO; Trading/order/execution methods used: NONE; Local guard remains runtime request authority: YES; Maximum Gamma requests per run: 1; Maximum CLOB book requests per run: 20; Empty WP163 record store required for new population: YES; Non-empty store makes zero network calls: YES; Records built through WP156 build_market_observation only: YES; Whole batch validated before persistence: YES; Records persisted through WP163 append only: YES; Manifest registered through WP162 only: YES; Record write occurs before reference registration: YES; Registration failure recoverable offline without deletion or re-fetch: YES; Recovery performs zero network: YES; Raw HTTP/source-response bytes stored: NO; Old WP10 JSONL writer or local_data path used: NO; Direct network library in new module: NO; Scheduler/retry/backoff/sleep: NO; Incremental population into non-empty store: NO; New public constants: 4; New frozen dataclasses: 2; New public functions: 2; Package export inventory grew by: 8; Dependencies added: 0; Credentials accessed: 0; Capital at risk: USD 0; Strategy/signal/paper/order/risk/execution authority: NONE; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; WP162-D002 and WP163-D001 resolved for bounded initial-seed public population scope: YES; WP164 merged: YES; WP164 PR: 164; WP164 final head: 0f3f29e32f7bb404f1156afba83ea33c3ee5cb1b; WP164 merge commit: 652ac21547db42512e7f9360986e1616c6622384; WP164 Ready for review: YES; Merge authorized: NO; Next sequence phase: WP165 incremental/repeated public capture with committed cross-run lineage separately gated. Canonical document is `docs/polymarket_point_in_time_public_population_contract.md`.
- Bounded incremental cumulative Polymarket population status: POLYMARKET_BOUNDED_CUMULATIVE_INCREMENTAL_POINT_IN_TIME_POPULATION; Implementation posture: MANUAL_GET_ONLY_CUMULATIVE_256_RECORD_CROSS_RUN_LINEAGE_NO_TRADING_AUTHORITY; Source module: `src/data_layer/point_in_time_market_research/polymarket_incremental_population.py`; Package class: DATA_LAYER_PUBLIC_POPULATION; Size class: L; Risk level: 1; Predecessor: WP164 merged at final head 0f3f29e32f7bb404f1156afba83ea33c3ee5cb1b and merge commit 652ac21547db42512e7f9360986e1616c6622384; Default network posture: OFF; Public GET-only network reads when explicitly enabled: YES; Endpoints: Gamma GET /markets and optional CLOB GET /book only; Authenticated endpoints used: NONE; POST /books used: NO; Keyset/pagination used: NO; Data API used: NO; Trading/order/execution methods used: NONE; Local guard remains runtime request authority: YES; Cumulative record cap: 256; Populated and registered WP163 record store required: YES; Latest registered VALIDATED_RECORD_BATCH reference convergence proven before network: YES; Store strict-superset yields recoverable baseline-unregistered: YES; Worst-case capacity checked before any client call: YES; New captures classified PRIMARY_ASSERTION/EXACT_DUPLICATE/SOURCE_REVISION against latest prior: YES; Latest prior chosen by ingestion then observed then record_version_id: YES; Identity drift rejected: YES; External known_parent_record_ids passed through WP162: NO; Manifest/dataset snapshot reference schema migration: NONE; Complete cumulative batch validated before persistence: YES; Only new records appended through WP163: YES; Complete cumulative dataset registered through WP162: YES; New records appended before cumulative registration: YES; Old registered reference remains immutable: YES; Registration failure recoverable offline without deletion or re-fetch: YES; Recovery performs zero network: YES; Recovery accepts exactly one genuine orphan run reconstructed object-for-object: YES; Raw HTTP/source-response bytes stored: NO; Old WP10 JSONL writer or local_data path used: NO; Direct network library in new module: NO; Scheduler/retry/backoff/sleep: NO; New public constants: 4; New frozen dataclasses: 1; New public functions: 2; Package export inventory grew by: 7; Dependencies added: 0; Credentials accessed: 0; Capital at risk: USD 0; Strategy/signal/paper/order/risk/execution authority: NONE; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; WP164-D001 partially resolved for bounded cumulative internal-parent lineage scope: YES; WP162-D004 remains open: YES; WP164-D003 remains open: YES; WP165 Ready for review: YES; Merge authorized: NO; Next sequence phase: WP166 scalable public dataset expansion with committed external-parent/reference schema and Gamma keyset pagination separately gated. Canonical document is `docs/polymarket_incremental_point_in_time_population_contract.md`.
- Bounded scalable lineage-delta keyset Polymarket population status: POLYMARKET_SCALABLE_KEYSET_LINEAGE_DELTA_POPULATION; Implementation posture: MANUAL_ONE_PAGE_KEYSET_GET_ONLY_EXTERNAL_PARENT_COMMITTED_NO_TRADING_AUTHORITY; Source module: `src/data_layer/point_in_time_market_research/polymarket_scaled_population.py`; Package class: DATA_LAYER_PUBLIC_POPULATION; Size class: XL; Risk level: 1; Predecessor: WP165 merged at final head 883d806ce979b2671dc22378ff9d4faaac5bcf40 and merge commit 6cfb3a8913661401635e8b7ce1d55219098bb9dd; Default network posture: OFF; Public GET-only network reads when explicitly enabled: YES; Endpoints: Gamma GET /markets/keyset and optional CLOB GET /book only; Keyset endpoint repo-verified: NO; Keyset endpoint documented 2026-08-30: YES; Double opt-in required for real keyset use: YES; Authenticated endpoints used: NONE; Offset ever sent: NO; Trading/order/execution methods used: NONE; Local guard remains runtime request authority: YES; Maximum keyset page requests per invocation: 1; Maximum markets per page: 100; Maximum CLOB book requests per run: 20; Automatic cursor loop: NO; Only current records registered as v2 lineage-delta reference: YES; Direct external parents are earlier-registered records: YES; Physical history beyond 256 supported within WP163 4096 horizon: YES; v1 dataset snapshot references remain supported: YES; SQLite schema or user_version migration: NONE; Physical WP163 record-id set proven equal to registered ordinary-id union before network: YES; Capacity gates checked before any client call: YES; Current records appended before delta registration: YES; Registration failure recoverable offline without deletion or re-fetch: YES; Recovery performs zero network: YES; next_cursor part of immutable record identity: NO; Raw HTTP/source-response bytes stored: NO; Direct network library in new module: NO; Scheduler/retry/backoff/sleep: NO; New public constants: 4; New frozen dataclasses: 2; New public functions: 2; Package export inventory grew by: 8; Dependencies added: 0; Credentials accessed: 0; Capital at risk: USD 0; Strategy/signal/paper/order/risk/execution authority: NONE; Paper-trading execution: NOT AUTHORIZED; Live-trading execution: FORBIDDEN; WP162-D004 resolved for bounded registered external-parent context: YES; WP165-D001 resolved by lineage-delta within current physical horizon: YES; WP164-D003 and WP165-D002 partially resolved for manual one-page keyset: YES; WP166 Ready for review: YES; Merge authorized: NO; Next sequence phase: WP167 analytical research store and query layer separately gated. Canonical document is `docs/scalable_lineage_delta_and_keyset_population_contract.md`.
- Analytical research foundation status: LOCAL_OFFLINE_DERIVED_ANALYTICAL_MATERIALIZATION_AND_EXTERNAL_HISTORY_FOUNDATION; Implemented by: WP167; Source package: `src/data_layer/analytical_research/`; Package class: RUNTIME_DEPENDENCY_ANALYTICAL_RESEARCH_FOUNDATION; Size class: XL; Risk level: 3; New direct runtime dependencies: pyarrow==25.0.1, duckdb==1.5.5, polars==1.44.1; Python support floor: >=3.12,<3.15; Canonical PIT authority unchanged: YES; Derived Parquet analytical materialization only: YES; Logical dataset identity independent of physical Parquet bytes: YES; External pmxt v2 provenance classified THIRD_PARTY_NATIVE_FRAME_ARCHIVE: YES; External downloader: NONE; Product runtime network: NONE; DuckDB local execution: OBSERVATIONAL_PASS_OR_BLOCKED_BY_WINDOWS_SMART_APP_CONTROL; DuckDB/Polars parity validated by hosted CI: GREEN; No NautilusTrader/WebSocket/Data API/Hermes/strategy/paper/execution/live: YES; Canonical document is `docs/analytical_research_layer_contract.md`; WP167 Ready for review: YES_INDEPENDENTLY_CERTIFIED; Independent draftability certificate: PASS_ALL_TWELVE_LENSES; Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; Merge authorized: NO; Next phase: WP168 NautilusTrader offline kernel separately gated.
- Nautilus offline kernel foundation status: LOCAL_OFFLINE_NAUTILUS_EVENT_REPLAY_FOUNDATION; Implemented by: WP168; Source package: `src/research_runtime/nautilus_offline/`; Package class: OFFLINE_REPLAY_RUNTIME_FOUNDATION; Size class: XL; Risk level: 3; New direct runtime dependency: nautilus_trader==1.231.0; Python support floor: >=3.12,<3.15; Canonical PIT authority unchanged: YES; Nautilus catalog and replay are derived research runtime state only: YES; Replay source bound to WP167 ExternalDatasetDescriptor provenance: YES; External pmxt v2 provenance classified THIRD_PARTY_NATIVE_FRAME_ARCHIVE: YES; Receive-time-primary deterministic replay ordering: YES; NautilusTrader install-not-vendor LGPL-3.0: YES; No Polymarket extra: YES; No Redis: YES; Product runtime network: NONE; No live Nautilus data or execution client: YES; No authenticated Polymarket client/WebSocket/Data API/Hermes/strategy/paper/execution/live: YES; Event-replay proof only, no alpha/fill/executable-edge claim: YES; Canonical document is `docs/nautilus_offline_kernel_contract.md`; WP168 Ready for review: YES_INDEPENDENTLY_CERTIFIED; Independent draftability certificate: PASS_ALL_TWELVE_LENSES; Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; Merge authorized: NO; Next phase: WP169 public realtime WebSocket data plane separately gated.
- Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime status: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Fully autonomous trading agent status: EXCLUDED_FOR_NOW
- Polling status: MANUAL_EXPLICIT_NETWORK_BOUNDED_RUNNER_DEV_ONLY; SNAPSHOT_CAPTURE_MANUAL_EXPLICIT_NETWORK_BOUNDED_GUARD_ENFORCED_DEV_ONLY
- Scheduler status: NOT_STARTED
- Bot loop status: NOT_STARTED
- Sandbox status: OFFICIAL_CLIENT_SANDBOX_DEV_ONLY; DEV_ONLY_READ_ONLY_NO_CREDENTIALS
- Storage status: LOCAL_FILE_SNAPSHOTS_ONLY
- Catalog status: IN_MEMORY_LOCAL_ONLY
- Reporting status: LOCAL_REPORTS_ONLY
- Export status: LOCAL_EXPORTS_ONLY
- External repo audit status: WP2 COMPLETE - 14 concrete repositories audited; 1 non-specific legacy placeholder marked BLOCKED_OR_UNAVAILABLE
- Architecture status: WP3 documentation-only skeleton merged; WP8 adds approved read-only data-layer source under src/data_layer/polymarket/; WP9 adds contract probe tooling and validates three of four endpoint candidates; WP10 adds local file-based snapshot persistence (JSONL) under src/data_layer/polymarket/ and manual capture tool under tools/polymarket/; WP11 adds offline snapshot reader, in-memory market catalog, replay helpers, and manual inspection CLI under src/data_layer/polymarket/ and tools/polymarket/; WP12 adds offline snapshot quality gates, catalog quality metrics, and local report generation under src/data_layer/polymarket/ and tools/polymarket/; WP13 adds offline snapshot deduplication and sanitized local catalog exports under src/data_layer/polymarket/ and tools/polymarket/; WP14 adds official Python client dependency decision and boundary review docs/tests only; WP15 adds official-client sandbox tooling under tools/polymarket/official_client_sandbox/ only; WP16 adds offline polling policy and local rate-limit guard only; WP17 adds a manual finite explicit-network read-only polling runner only; WP18 adds guard-enforced manual snapshot capture using WP16 policy before Gamma and optional CLOB reads; WP19 adds offline guard-aware quality/reporting for WP18 guarded capture manifests; WP20 adds policy/docs/tests only for advisory AI-agent and Hermes read-only boundaries; WP21 adds schema/docs/tests only for a future local read-only agent context export; WP22 adds persistent Codex workflow guidance, templates, checklists, and tests only; WP23 adds a local/offline/read-only agent context JSON exporter only under src/data_layer/agent_context/ and tools/polymarket/; WP24 adds the local operator runbook and doc tests for safe manual exporter use only; WP25 adds deterministic local/offline/read-only report generation from WP23-compatible exports only; WP26 adds operator runbook docs/tests only for safe manual report-generator use; WP27 adds Agent/Hermes manual setup decision record docs/tests only; WP28 adds token-efficiency operating model, concise reporting rules, and reusable WP prompt blocks docs/tests only; WP29 adds design/docs/tests only for the local/offline/read-only diff/scope summary helper; WP30 adds the local/offline/read-only stdlib helper implementation at tools/git/diff_scope_summary.py, focused tests, and user-facing helper doc; WP31 adds design/docs/tests only for a future local/offline/read-only validation-output summary helper; WP32 adds the local/offline/read-only stdlib helper implementation at tools/validation/validation_output_summary.py, focused tests, and user-facing helper doc; WP33 adds docs-only design guidance at docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md for a future advisory code-index / blast-radius helper; WP34 adds the local/offline/read-only stdlib helper implementation at tools/git/code_blast_radius.py, focused tests, and user-facing helper doc; WP35 adds design/docs/tests only for a future local/offline/read-only memory/status snapshot helper at docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md; WP36 adds the local/offline/read-only stdlib helper implementation at tools/git/status_snapshot.py, focused tests, and user-facing helper doc; WP37 adds docs/tests only to consolidate the WP28-WP36 token-efficiency sequence, helper usage order, advisory-only limits, deferred helper gaps, protected-boundary reaffirmation, and next-WP gate; WP38 adds docs/tests only to resume advisory-agent planning through a local advisory handoff package with no runtime, Hermes, LLM, credential, trading, database, dashboard, scheduler, polling, or product behavior; WP39 adds docs/tests only to define the future local advisory consumer boundary and consumption model with no runtime, Hermes, LLM, network, account, trading, database, dashboard, scheduler, polling, dependency, source, tools, or product behavior; WP40 adds a local/offline/read-only deterministic advisory consumer prototype under tools/advisory/local_advisory_consumer.py with explicit local_data inputs only, stdout by default, optional ignored advisory output, and no runtime, LLM, Hermes, network, account, trading, database, dashboard, scheduler, polling, dependency, lock-file, or src/ changes; WP41 adds docs/tests only for human-operated advisory prompt/runbook templates and operator review steps with no runtime, prompt runner, LLM, Hermes, network, account, trading, database, dashboard, scheduler, polling, dependency, lock-file, tools/, or src/ changes; WP42 adds docs/tests only for human-operated advisory workflow hardening connecting WP40 and WP41 with evidence, stop/reject gates, decision logging, and future-WP conversion rules, with no runtime, prompt runner, LLM, Hermes, network, account, trading, database, dashboard, scheduler, polling, dependency, lock-file, tools/, or src/ changes; WP43 reconciles docs/project_status.md with actual repo truth after WP42 merge, adding a focused project-status docs test, with no runtime, dependency, lock-file, tools/, or src/ changes; WP44 adds docs-only design for a future Market Research Priority Scoring Layer at docs/market_research_priority_scoring_layer.md and a focused docs test, with no runtime, source, tools, dependency, or lock-file changes; WP45 adds docs/tests-only workflow/governance PR evidence reporting hardening across AGENTS.md, docs/ai/codex/ workflow docs, docs/work_package_template.md, docs/review_checklist.md, and a focused docs test, with no runtime, source, tools, dependency, or lock-file changes; WP46 adds a local/offline/stdlib governance helper at tools/git/pr_evidence_consistency_guard.py with focused tests under tests/tools/git/ and docs under docs/ai/codex/, with no runtime, source, dependency, or lock-file changes; WP47 hardens the guard with five new optional flags (--forbid-inline-test-counts, --forbid-placeholder-evidence, --require-current-final-marker, --forbid-stale-count-tokens, --require-posted-evidence-note) and updates workflow docs/tests/review checklists to enforce current-final evidence markers and forbid parenthetical test counts in file lists, with no runtime, source, dependency, or lock-file changes; WP48 adds docs/tests-only schema and output contract for the future Market Research Priority Scoring Layer at docs/market_research_priority_scoring_output_contract.md, defining top-level output schema, market object schema, score components, advisory-only labels, staleness/provenance/missing-data contracts, forbidden fields, safe and invalid examples, and future implementation gates, with no runtime, source, tools, dependency, or lock-file changes; WP49 adds a local/offline/read-only core scorer under src/data_layer/market_research_priority_scoring.py (stdlib-only, in-memory output only, no network, no file writes, no CLI, no export, no report writer, no runtime/product/trading behavior) with focused tests at tests/test_market_research_priority_scoring_core.py, and updates docs to reflect WP48 merged and WP49 core scorer on branch; WP50 adds docs-only research-data foundation direction lock and deferred items update with no source, tools, dependency, or lock-file changes; WP51 adds the local/offline/read-only stdlib feature extraction foundation at src/data_layer/market_research_priority_features.py, focused tests, and docs updates; WP52 adds docs-only long-term bot-completion roadmap and Side 4 onboarding lock with no source, tools, dependency, or lock-file changes; WP53 hardens src/data_layer/market_research_priority_features.py with provenance/staleness/missing-data enforcement (provenance_degraded flag, provenance_weakness_reasons, future-timestamp detection, missing_question/missing_market_status detection), focused tests, and docs updates with no new dependency or lock-file changes; WP54 hardens tools/git/pr_evidence_consistency_guard.py with a new --require-guard-result flag (category P — requires actual guard result line, checked categories, and exit code in both PR body and final comment), adds docs/ai/codex/WP_BUNDLING_POLICY.md with bundling policy and follow-up classification, and updates workflow/governance docs and tests with no src/, Polymarket-tooling, dependency, or lock-file changes; WP55 adds docs/tests only for resolution-rule ambiguity taxonomy and manual-label workflow with no source, tools, dependency, or lock-file changes; WP56 adds the local/offline/read-only schema validator at src/data_layer/resolution_ambiguity_labels.py and focused tests; WP57 adds local/offline/read-only resolution ambiguity label feature extraction to src/data_layer/market_research_priority_features.py and focused tests; WP58 adds CLAUDE_START_HERE.md, docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md, docs/ai/codex/NEGATIVE_TEST_MATRIX_POLICY.md, tools/git/posted_pr_evidence_verifier.py (read-only workflow helper), focused tests, and workflow/governance docs updates with no src/, Polymarket-tooling, dependency, or lock-file changes.
- Deferred items status: WP9 marks WP8-D001 READY_FOR_WP (three endpoints confirmed, CLOB /health unconfirmed); long-running runtime/data deferred items remain unchanged unless explicitly listed later; WP38 resolves WP37-D001 only for selecting and documenting the local advisory handoff path, not for runtime/product implementation; WP39 resolves WP38-D001 only for docs-only advisory runtime boundary and consumption design completion, not for advisory consumer implementation; WP40 resolves WP38-D002 and WP39-D001 only for the deterministic local/offline/read-only advisory consumer prototype scope, not for runtime/LLM/Hermes/trading implementation; WP41 resolves WP39-D002 and WP40-D001 only for docs-only advisory prompt/runbook package scope, not for runtime/LLM/Hermes/provider/account/trading implementation; WP42 resolves WP41-D001 only for docs-only advisory consumer integration review / operator workflow hardening scope; WP40-D002 remains OPEN because LLM/Hermes/provider integration is not designed or implemented; WP41-D002 remains OPEN because provider/Hermes decision refresh is not performed; WP42-D001 and WP42-D002 are OPEN; WP28-D001, WP30-D001, WP32-D001, WP34-D001, WP36-D001, and WP36-D002 remain OPEN; WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION; WP27-D001, WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain OPEN and unchanged; security checks are run/assessed in WP42; WP43 resolves no deferred items; all WP42-forward deferred items remain unchanged; security checks are run/assessed in WP43; WP44 resolves no existing deferred items; WP44 adds WP44-D001 (Market Research Priority Scoring implementation not started, OPEN, P3) and WP44-D002 (Score laundering mitigation not enforced by implementation, OPEN, P3); WP45 resolves no existing deferred items; security checks are run/assessed in WP45; WP46 resolves no existing deferred items; WP46 adds WP46-D001 (guard validates local PR body/final comment drafts only, not live GitHub PR data, OPEN, P4); security checks are run/assessed in WP46; WP47 resolves no existing deferred items; WP47 adds WP47-D001 (guard still does not fetch live GitHub PR body/comments, OPEN, P4; WP47 hardens local posted-evidence discipline and current-final markers but intentionally avoids GitHub API/network/auth behavior; any future requirement to validate already-posted GitHub content automatically is deferred to a future approved GitHub-aware helper WP with explicit network/auth boundary); security checks are run/assessed in WP47; WP48 resolves no existing deferred items; WP48 adds WP48-D001 (Market Research Priority Scoring implementation not started after schema/output contract, OPEN, P3) and WP48-D002 (schema/output contract not enforced by implementation yet, OPEN, P3); WP44-D001 and WP44-D002 remain OPEN because implementation is still not started; security checks are run/assessed in WP48; WP49 resolves WP44-D001, WP44-D002, WP48-D001, and WP48-D002 only for the local/offline/read-only core scorer scope; WP49 adds WP49-D001 (feature extraction from local/offline artifacts not started, OPEN, P3), WP49-D002 (CLI/export/report writer not started, OPEN, P3), and WP49-D003 (core scorer not integrated with advisory consumer or market catalog, OPEN, P3); security checks are run/assessed in WP49; WP50 resolves no existing deferred items; WP50 adds WP50-D001 (research direction locked, but implementation sequencing still requires explicit future WPs, OPEN, P3); security checks are run/assessed in WP50; WP51 resolves WP49-D001 only for the narrow local/offline/read-only basic feature extraction foundation scope; WP49-D002 and WP49-D003 remain OPEN; WP50-D001 remains OPEN; WP51 adds WP51-D001 (provenance/staleness hardening beyond foundation not started, OPEN, P3), WP51-D002 (resolution-rule ambiguity extraction not started, OPEN, P3), WP51-D003 (microstructure quality feature extraction beyond basic availability not started, OPEN, P3), and WP51-D004 (CLI/export/report writer not started, OPEN, P3); security checks are run/assessed in WP51; WP52 resolves no existing deferred items; WP52 adds WP52-D001 (long-term roadmap locked, but milestone implementation remains gated by explicit future WPs, OPEN, P3); security checks are run/assessed in WP52; WP53 resolves WP51-D001 only for the narrow provenance/staleness/missing-data hardening scope implemented in WP53; WP53 adds WP53-D001 (resolution-rule ambiguity extraction still not started, OPEN, P3), and WP53-D002 (microstructure quality feature extraction still not started, OPEN, P3); WP49-D002, WP49-D003, WP50-D001, WP51-D002, WP51-D003, WP51-D004, and WP52-D001 remain OPEN; security checks are run/assessed in WP53; WP54 resolves no existing implementation deferred items; WP54 adds WP54-D001 (GitHub-posted evidence still requires human or Claude manual verification because the guard remains local/offline and does not fetch live GitHub PR content, OPEN, P4); security checks are run/assessed in WP54; WP55 adds WP55-D001 and WP55-D002; security checks are run/assessed in WP55; WP56 adds WP56-D001; security checks are run/assessed in WP56; WP57 resolves WP55-D001 and WP56-D001 only for the narrow local/offline/read-only feature extraction from validated manual labels scope; WP57 adds WP57-D001 (resolution ambiguity feature extraction not yet integrated into scorer/report/advisory consumer, OPEN, P3); WP55-D002 remains OPEN; security checks are run/assessed in WP57; WP58 marks WP54-D001 and WP47-D001 as PARTIALLY_RESOLVED_PUBLIC_ONLY (public-repo posted evidence verifier added; authenticated/private GitHub verification remains unsupported); WP58 adds WP58-D001 (authenticated or private GitHub posted-evidence verification not implemented, OPEN, P4); security checks are run/assessed in WP58; WP59 adds WP59-D001 (local evidence-mode linter not implemented; future optional workflow helper, OPEN, P4) and WP59-D002 (docs/project_status.md slimming/history split not implemented; future workflow stabilization item, OPEN, P4); WP58-D001 narrowed to: public unauthenticated helper exists; private/authenticated support deferred; security checks are run/assessed in WP59. WP60A adds WP60A-D001 (full directory migration from docs/ai/codex/ to agent-neutral path not performed; deferred to future optional governance cleanup, OPEN, P4); security checks are run/assessed in WP60A. WP73 resolves WP72-D003 only for design/schema scope; implementation remains deferred. WP73 adds WP73-D001 (human review label record validator remains deferred, OPEN, P3), WP73-D002 (human review label fixture loader remains deferred, OPEN, P3), WP73-D003 (label/report integration remains deferred, OPEN, P3), and WP73-D004 (automated or LLM-based labeling remains forbidden/deferred, OPEN, P3). WP74 resolves WP73-D001 only for the local/offline/read-only label record validator scope (validate_human_review_label_record); WP73-D002, WP73-D003, and WP73-D004 remain OPEN. WP74 adds WP74-D001 (human review label fixture loader remains deferred, OPEN, P3), WP74-D002 (label/report integration remains deferred, OPEN, P3), WP74-D003 (label editor remains deferred, OPEN, P3), and WP74-D004 (automated or LLM-based labeling remains forbidden/deferred, OPEN, P3). WP75 resolves WP74-D001 and WP73-D002 only for the local/offline/read-only label fixture loader scope (load_human_review_label_fixtures); WP73-D003, WP73-D004, WP74-D002, WP74-D003, and WP74-D004 remain OPEN. WP75 adds WP75-D001 (label/report integration remains deferred, OPEN, P3), WP75-D002 (human review label editor remains deferred, OPEN, P3), WP75-D003 (automated or LLM-based labeling remains forbidden/deferred, OPEN, P3), and WP75-D004 (labels not used for scoring weight changes until explicit future WP, OPEN, P3).
- WP78 deferred items status: WP78 resolves WP76-D002 and WP77-D001 only for local/offline/read-only wallet trade event schema, static example, validator, and explicit-path fixture loader. WP78 adds WP78-D001 through WP78-D007 for remaining profiler, research queue, copyability, report, paper strategy, wallet API/network, and live-execution gaps.
- WP79 deferred items status: WP79 resolves WP78-D001 and WP78-D002 only for local/offline/read-only advisory wallet signal research profile and research queue annotation scope. WP79 adds WP79-D001 through WP79-D006 for remaining copyability delay simulator, report generator, paper strategy, wallet API/network, and live-execution gaps.
- WP80 deferred items status: WP80 resolves WP79-D001 and WP79-D002 (and WP76-D004, WP77-D004, WP77-D005, WP78-D003, WP78-D004) only for docs/schema/tests-only copyability delay simulator design and wallet intelligence report contract scope. WP80 adds WP80-D001 through WP80-D006 for remaining copyability delay implementation, report generator implementation, paper strategy, wallet API/network, and live-execution gaps.
- WP81 deferred items status: WP81 resolves WP80-D001 only for the local/offline/read-only copyability delay evaluator implementation scope (src/data_layer/wallet_copyability_delay_evaluation.py). WP80-D002 through WP80-D006 remain OPEN (wallet intelligence report generator, paper strategy, wallet API/network, and live-execution gaps). WP81 adds WP81-D001 (wallet intelligence report generator not started, OPEN, P3) and WP81-D002 (wallet signal paper strategy contract not started, OPEN, P3).
- Generated artifact status: WP6 guardrails active; WP7 gitleaks binary in ignored tools/.bin/ (not committed); local_data/ is ignored and generated outputs must not be committed; WP23 agent context exports output remains under ignored local_data/agent_context_exports/; WP25 agent context report output remains under ignored local_data/agent_context_reports/; WP40 optional advisory consumer output remains under ignored local_data/advisory_outputs/ only.
- Next intended WP: after WP81 merge, likely next WP is WP82 Wallet Intelligence Report Generator V1 (local/offline/read-only only; no live execution; no network ingestion; no wallet API client; no automatic copy-trading; no paper/live trading; no credentials; no execution).
- Human review label workflow status: DOCS_SCHEMA_TESTS_DESIGN_ONLY_MERGED
- Human review label record validator status: LOCAL_OFFLINE_READ_ONLY_VALIDATOR_MERGED
- Human review label fixture loader status: LOCAL_OFFLINE_READ_ONLY_FIXTURE_LOADER_MERGED
- Wallet intelligence roadmap status: DOCS_TESTS_ONLY_ROADMAP_LOCK_MERGED
- Wallet intelligence architecture/profile/signal contract status: DOCS_SCHEMA_TESTS_ONLY_CONTRACT_MERGED
- Wallet trade event fixture loader status: LOCAL_OFFLINE_READ_ONLY_FIXTURE_LOADER_MERGED
- Wallet signal research profiler status: LOCAL_OFFLINE_READ_ONLY_RESEARCH_PROFILER_MERGED
- Wallet copyability delay simulator design status: DOCS_SCHEMA_TESTS_ONLY_COPYABILITY_DELAY_DESIGN_MERGED
- Wallet intelligence report contract status: DOCS_SCHEMA_TESTS_ONLY_REPORT_CONTRACT_MERGED
- Wallet copyability delay evaluator status: LOCAL_OFFLINE_READ_ONLY_COPYABILITY_DELAY_EVALUATOR_MERGED
- Wallet intelligence report generator status: LOCAL_OFFLINE_READ_ONLY_REPORT_GENERATOR_MERGED
- Wallet signal paper strategy contract status: DOCS_SCHEMA_TESTS_ONLY_PAPER_STRATEGY_CONTRACT_MERGED; LOCAL_OFFLINE_READ_ONLY_VALIDATOR_MERGED; LOCAL_OFFLINE_READ_ONLY_CANDIDATE_FIXTURE_LOADER_MERGED
- Evidence architecture repair status: EVIDENCE_ARCHITECTURE_MODEL_D_MERGED; RESULT_OUTPUT_INVARIANT_STANDARD_MERGED; FOLLOWUP_PROMPT_STANDARD_MERGED; NO_PRODUCT_BEHAVIOR_CHANGED
- WP88 deferred items status: WP88-D001 (evidence architecture transition clarified with Model D, MERGED); WP88-D002 (result-object field coverage standard added, MERGED); WP88-D003 (manual serializer losslessness standard added, MERGED); WP88-D004 (root-cause-first follow-up prompt standard added, MERGED); WP88-DEFER-003 resolved on WP89 branch only for local/offline/read-only candidate review report generator scope
- WP82 deferred items status: WP82 resolves WP80-D002 and WP81-D001 only for the local/offline/read-only in-memory report generator scope. WP80-D003, WP81-D002, WP82-D001 (wallet signal paper strategy contract) remain OPEN as of WP82 merge. WP82 adds WP82-D001 (wallet signal paper strategy contract remains deferred, OPEN, P3) and WP82-D002 (wallet intelligence report export CLI remains deferred, OPEN, P3).
- WP83 deferred items status: WP83 resolves WP80-D003, WP81-D002, and WP82-D001 only for contract-definition scope only (docs/schema/tests-only). Paper strategy implementation, paper order model, paper portfolio ledger, paper fill model, paper PnL computation, network/API wallet ingestion, real wallet monitoring, automatic following behavior, live account access, credentials, scheduler, dashboard, and bot loop remain deferred. WP83 adds WP83-D001 (wallet signal paper strategy contract local validator not started, OPEN, P3).
- WP84 deferred items status: WP84 resolves WP83-D001 only for local/offline/read-only contract validator scope. Paper strategy implementation, paper order model, paper portfolio ledger, paper fill model, paper PnL computation, network/API wallet ingestion, real wallet monitoring, automatic following behavior, live account access, credentials, scheduler, dashboard, and bot loop remain deferred. WP84 adds WP84-D001 (wallet signal paper strategy contract candidate fixture loader not started, OPEN, P3).
- WP87 deferred items status: WP87 resolves WP84-D001 only for local/offline/read-only candidate fixture loader scope. Paper strategy implementation, paper order model, paper portfolio ledger, paper fill model, paper PnL computation, network/API wallet ingestion, real wallet monitoring, automatic following behavior, live account access, credentials, scheduler, dashboard, and bot loop remain deferred. WP89 resolves WP87-D001 on branch only for local/offline/read-only in-memory candidate review report generator scope.

## WP94 Candidate Review Workflow Local Smoke Receipt V1

WP94 - Candidate Review Workflow Local Smoke Receipt V1 is merged
(merge commit `e22212c7abaa2cb924bd2c43eeaae0695713633c`; historical branch
`wp94-candidate-review-workflow-local-smoke-receipt-v1`).

It reconciles repo truth after WP93 merge (PR #93, merge commit
`01d916242d3ba93c757bcf84f4195183b9ea2336`) and adds a local/offline smoke
receipt for the existing import-based candidate review workflow.

WP94 adds `docs/runbooks/candidate_review_workflow_local_smoke_receipt.md`,
`docs/status_entries/WP94.md`, and focused smoke receipt tests at
`tests/test_candidate_review_workflow_smoke_receipt.py`. It updates runbook,
project-status, repo-truth, workflow-docs, and architecture-boundary tests for
the WP94 evidence surface.

WP94 adds no source code, no tools, no CLI, no runtime behavior, no paper
engine, no order logic, no live execution, no credentials, no runtime/API/
product/account network behavior, no scheduler, no dashboard, no bot loop, no
dependency file, and no lock file. Generated report exports are temp/test-only
and are not committed.

WP94 resolves no deferred implementation item. WP90-D001 remains OPEN for
future paper strategy implementation. WP91-D001 and WP92-D001 remain OPEN for
any future GitHub-aware private evidence verifier.

## WP95 Post-WP94 Repo-Truth Reconciliation And Accepted Hermes Research-Brain Plan Lock-In

WP95 reconciles WP94 as merged and locks the accepted Hermes/research-brain
execution plan into repo truth at `docs/hermes_research_brain_execution_plan.md`.
The plan defines broad advisory research freedoms while preserving deterministic
control over execution, validation, risk, state, accounting, credentials, order
lifecycle, live safety, kill switch, audit logs, and strategy-promotion gates.

Hermes remains not installed, not connected, and not runtime-authorized. Live
trading remains disabled. WP95 creates no Hermes schema, validator, prompt pack,
runbook, exporter, runtime artifact, provider configuration, model call, memory,
scheduler, paper/live behavior, credential path, or order behavior.

Future material changes to the accepted Hermes/research-brain plan must update
repo-truth docs in the same WP or an approved follow-up. Chat memory and PR
comments alone are not authoritative. Dynamic PR state belongs in GitHub PR
metadata and the PR body; committed status docs remain stable post-merge.

The next substantive WP is Hermes Advisory Foundation And Research-Brain
Architecture V1.

## WP96 Hermes Advisory Foundation And Research-Brain Architecture V1

WP96 records the Hermes advisory foundation and research-brain architecture at
`docs/hermes_advisory_foundation_research_brain_architecture.md`. It elaborates
the accepted WP95 plan without overriding it.

The architecture keeps Hermes powerful as an adaptive research brain for market
research, edge discovery, hypothesis generation, experiment design, strategy
critique, future WP recommendations, failure analysis, performance-improvement
ideas, wallet/candidate review, regime monitoring, cross-market inconsistency
analysis, resolution-rule ambiguity review, and microstructure/slippage realism
review.

WP96 adds no Hermes install, connection, runtime dependency, provider/model
configuration, credentials, private endpoint access, API/product/account network
behavior, schema, validator, prompt pack, runbook, exporter, runtime artifact,
paper/live behavior, execution/order/risk module, scheduler, dashboard, bot
loop, source code, tools, dependency file, or lock file.

WP97 documents Phase 2 at
`docs/hermes_input_output_contracts_and_validator_requirements.md`. It defines
documentation-level input/output contract requirements and future deterministic
validator requirements only. It adds no machine-readable schema, source
validator, prompt pack, runbook, exporter, parser, context-packet generator,
Hermes runtime, provider/model configuration, credentials, private endpoint
access, API/product/account network behavior, paper/live behavior,
execution/order/risk module, scheduler, dashboard, bot loop, source code,
tools, dependency file, or lock file.

Next intended WP: Hermes input/output contracts and validator hardening was the
WP96 next-phase pointer and is completed by WP97.
Next intended WP: Hermes research prompt pack and operator runbooks was the WP97
next-phase pointer and is completed by WP98. The next intended WP after WP98 is
Hermes contract validator implementation or context-packet exporter
implementation if explicitly approved.

## WP98 Hermes Research Prompt Pack And Operator Runbooks V1

WP98 records the Hermes research prompt pack and operator runbooks foundation
at `docs/hermes_research_prompt_pack_and_operator_runbooks.md`. It is Phase 3
from the WP95/WP96 plan and does not override WP95, WP96, or WP97.

WP98 defines 10 manual-use-only research prompt families (broad market-edge
hypothesis generation, wallet/candidate review, resolution-rule ambiguity
analysis, cross-market inconsistency analysis, microstructure/slippage realism
critique, strategy critique, failure analysis/postmortem, performance-improvement
idea review, experiment design, and future WP recommendation), plus operator
preflight checklist, input preparation rules, prompt-injection policy, common
prompt wrapper requirements, common output requirements, output review checklist,
forbidden output matrix, human-review and deterministic handoff rules, failure/
stop conditions, manual setup dependency note, future implementation gates,
repo-truth update rule, and next WP sequence pointer.

Every prompt family requires advisory-only output, human-review-required flag,
evidence/provenance/staleness/uncertainty fields, falsification path,
deterministic validation handoff, rejected interpretations, and
forbidden-action statement. The forbidden-output matrix preserves all WP97
forbidden categories.

WP98 adds no Hermes install, connection, runtime dependency, provider/model
configuration, credentials, private endpoint access, prompt runner,
machine-readable schema, source validator, exporter, parser, context-packet
generator, runtime artifact, API/product/account network behavior, paper/live
behavior, execution/order/risk module, scheduler, dashboard, bot loop, source
code, tools, dependency file, or lock file.

Next intended WP after WP98: Hermes contract validator implementation WP, or
context-packet exporter implementation WP, each requiring a separately approved
WP. WP99 delivers the Hermes advisory output validator V1.

## WP99 Hermes Advisory Output Validator V1

WP99 implements the local/offline/read-only deterministic stdlib-only validator
for in-memory Hermes advisory output mappings. The validator module is at
`src/data_layer/hermes_advisory_output_validator.py`. It resolves the
deferred source-validator item from WP97 Section "Validator Requirements."

The validator enforces all WP97/WP98 advisory-output requirements: all nine
required boolean safety fields must be present and exactly True; all twelve
required text/list fields must be present and non-empty; confidence_level must
be LOW, MEDIUM, or HIGH; no forbidden output categories may appear in any key
or string value at any nesting depth; no raw/free-form metadata keys may appear
at any nesting depth; invalid outputs fail closed and return an empty
normalized_output; error messages use neutral codes and do not echo unsafe raw
input.

WP99 adds no Hermes install, connection, runtime, provider/model configuration,
credentials, private endpoint access, prompt runner, context-packet exporter,
report/export writer, CLI, network behavior, paper/live behavior,
execution/order/risk behavior, scheduler, dashboard, bot loop, dependency, or
lock-file change.

Next intended WP after WP99: Hermes Context-Packet Exporter Foundation V1,
requiring a separately approved WP.

## WP100 Hermes Context-Packet Exporter Foundation V1

WP100 implements the deterministic stdlib-only local/offline/read-only builder
for sanitized in-memory Hermes context packets. The builder module is at
`src/data_layer/hermes_context_packet_exporter.py`. It consumes only explicit
caller-supplied in-memory summaries and returns a frozen result object whose
invalid state always contains an empty packet.

The builder enforces required identity, source-reference, provenance,
staleness, warning, missing-data, summary, structured-context, safe routing,
review-step, and deterministic-owner concepts. It sets all required advisory
and non-authority flags, recursively rejects unsafe keys and string values,
rejects raw/free-form mapping keys at any depth, normalizes structured values
deterministically, and emits only neutral diagnostic codes that do not echo
unsafe caller content.

WP100 adds no Hermes install, connection, runtime, provider/model
configuration, prompt runner, prompt execution, CLI, file export/report writer,
product/runtime network behavior, credentials, private endpoints, account or
order state, paper/live behavior, execution/risk behavior, scheduler,
dashboard, bot loop, dependency, or lock-file change.

Next intended WP after WP100: Hermes Local/Offline Manual Simulation Or
Context-Packet Dry-Run Receipt V1, requiring a separately approved WP.

## WP93 Candidate Review Report Operator Runbook V1

WP93 - Candidate Review Report Operator Runbook V1 is merged
(merge commit `01d916242d3ba93c757bcf84f4195183b9ea2336`; historical branch
`wp93-candidate-review-report-operator-runbook-v1`).

It adds `docs/runbooks/candidate_review_report_operator_runbook.md` as a
docs-only operator runbook for the existing local/offline/import-based WP87,
WP89, and WP90 candidate review workflow.

WP93 also adds `docs/status_entries/WP93.md` and focused runbook docs tests.
It updates repo-truth docs and docs/status/boundary/roadmap consistency tests
only.

WP93 adds no source code, no tools, no CLI, no runtime behavior, no paper
engine, no order logic, no live execution, no credentials, no runtime/API/
product/account network behavior, no scheduler, no dashboard, no bot loop, no
dependency file, and no lock file.

WP93 resolves no deferred implementation item. WP90-D001 remains OPEN for
future paper strategy implementation. WP91-D001 and WP92-D001 remain OPEN for
any future GitHub-aware private evidence verifier.

## WP89 Wallet Signal Candidate Review Report V1

WP89 - Wallet Signal Candidate Review Report V1 is on branch
(`codex/wp89-wallet-signal-candidate-review-report-v1`).

It implements a local/offline/read-only candidate review report generator that
consumes the WP87 fixture-loader result contract and returns deterministic
frozen report dataclasses plus deterministic Markdown.

WP89 adds `src/data_layer/wallet_signal_candidate_review_report.py`,
`tests/test_wallet_signal_candidate_review_report.py`, and
`docs/status_entries/WP89.md`.

WP89 is local/offline/read-only. It adds no paper engine, no order logic,
no live execution, no credentials, no network/API behavior, no scheduler,
no dashboard, and no bot loop. It does not add dependencies or lock-file changes.

WP89 resolves WP87-D001 and WP88-DEFER-003 only for the in-memory local
candidate review report generator scope. Export, dashboard, paper strategy,
network ingestion, real wallet monitoring, account access, credentials,
scheduler, bot loop, and live execution remain deferred.

## WP88 Evidence Architecture And Result-Object Invariant Repair After WP87

WP88 - Evidence Architecture And Result-Object Invariant Repair After WP87 is merged
(merge commit `a3cf399b7158fd00af255f57c5bf5cd1024b2c86`).

It implements Side 12's Model D evidence architecture feedback as persistent repo truth.

WP88 is workflow/evidence architecture repair. No product behavior changed. No trading/paper/live/runtime/network/credential behavior changed.

WP88 adds:
- `docs/ai/codex/EVIDENCE_ARCHITECTURE.md` (Model D: PR body = current review surface; status fragment = stable non-self-referential record; final comment = transition-only pointer; evidence contradiction matrix)
- `docs/ai/codex/RESULT_OUTPUT_INVARIANT_STANDARD.md` (field-coverage gate; manual serializer losslessness rule; invalid-output no-echo full public result scan requirement)
- `docs/ai/codex/FOLLOWUP_PROMPT_STANDARD.md` (root-cause-first follow-up prompt template; classification before fix requirement)
- `docs/status_entries/WP88.md` (WP88 stable non-self-referential status fragment)

WP88 updates:
- `docs/status_entries/README.md` — non-self-referential model, contradiction matrix, `Validated implementation commit:` labeling
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md` — contradiction matrix checks, result-object field-coverage checks
- `docs/ai/codex/VALIDATION_MATRIX.md` — field-coverage gate section, Model D section
- `docs/ai/codex/README.md` — references to EVIDENCE_ARCHITECTURE.md, RESULT_OUTPUT_INVARIANT_STANDARD.md, FOLLOWUP_PROMPT_STANDARD.md
- `docs/work_package_template.md` — Evidence Architecture Model D section, Result Object Field-Coverage Gate section
- `.github/pull_request_template.md` — Evidence Architecture section
- `tests/test_codex_workflow_docs.py` — WP88 workflow tests

WP88 resolves WP88-D001 through WP88-D004 as MERGED (evidence architecture, field coverage, serializer losslessness, follow-up standard).

Protected boundaries remain unchanged:
- Live account activity: DISABLED
- Credentials: NOT_USED
- Execution: NOT_STARTED
- Authenticated client: FORBIDDEN_UNTIL_APPROVED_WP
- Hermes: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Scheduler: NOT_STARTED
- Bot loop: NOT_STARTED

## WP87 Wallet Signal Paper Strategy Candidate Fixture Loader V1

WP87 - Wallet Signal Paper Strategy Candidate Fixture Loader V1 is on branch
(`wp87-wallet-signal-paper-strategy-candidate-fixture-loader-v1`).

It implements the first local/offline/read-only fixture loader for wallet signal
paper strategy candidate contract records.

WP87 adds `src/data_layer/wallet_signal_paper_strategy_candidate_fixture_loader.py`,
`tests/test_wallet_signal_paper_strategy_candidate_fixture_loader.py`,
and `tests/fixtures/wallet_signal_paper_strategy_candidates/` (four fixture files).

WP87 is local/offline/read-only. It adds no paper strategy implementation,
no paper order model, no paper portfolio ledger, no paper fill model, no paper
PnL computation, no network/API wallet ingestion, no real wallet monitoring,
no automatic following behavior, no live account access, no credentials, no
scheduler, no dashboard, no bot loop, no Hermes/LLM runtime, no dependency or
lock-file changes, and no paper/live account activity behavior.

WP87 resolves WP84-D001 only for local/offline/read-only candidate fixture loader scope.
All other deferred items remain deferred.

Protected boundaries remain unchanged:
- Live account activity: DISABLED
- Credentials: NOT_USED
- Execution: NOT_STARTED
- Authenticated client: FORBIDDEN_UNTIL_APPROVED_WP
- Hermes: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Scheduler: NOT_STARTED
- Bot loop: NOT_STARTED

## WP84 Post-WP83 Repo-Truth Reconciliation And Wallet Signal Paper Strategy Contract Local Validator V1

WP84 - Post-WP83 Repo-Truth Reconciliation And Wallet Signal Paper Strategy
Contract Local Validator V1 is merged (PR #85, merge commit
`d350cf963205d4687341ecc44d657c2ac9cb7d8d`; historical branch
`wp84-wallet-signal-paper-strategy-contract-local-validator-v1`).

It reconciles repo truth after WP83 merge (PR #84, merge commit
`ac66cd582bf2a53cc29869b3e49ffdb7f020ea44`; PR #84 head SHA
`08874da0893c7c29567979b6cd1101833fd0b0c9`) and implements the first
local/offline/read-only wallet signal paper strategy contract validator.

WP84 adds `src/data_layer/wallet_signal_paper_strategy_contract_validator.py`
and `tests/test_wallet_signal_paper_strategy_contract_validator.py`.

WP84 is local/offline/read-only. It adds no paper strategy implementation,
no paper order model, no paper portfolio ledger, no paper fill model, no paper
PnL computation, no network/API wallet ingestion, no real wallet monitoring,
no automatic following behavior, no live account access, no credentials, no
scheduler, no dashboard, no bot loop, no Hermes/LLM runtime, no dependency or
lock-file changes, and no paper/live account activity behavior.

WP84 resolves WP83-D001 only for local/offline/read-only validator scope.
Paper strategy implementation and all other deferred items remain deferred.

Protected boundaries remain unchanged:
- Live account activity: DISABLED
- Credentials: NOT_USED
- Execution: NOT_STARTED
- Authenticated client: FORBIDDEN_UNTIL_APPROVED_WP
- Hermes: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Scheduler: NOT_STARTED
- Bot loop: NOT_STARTED

## WP83 Post-WP82 Repo-Truth Reconciliation And Wallet Signal Paper Strategy Contract V1

WP83 - Post-WP82 Repo-Truth Reconciliation And Wallet Signal Paper Strategy
Contract V1 is merged (PR #84, merge commit
`ac66cd582bf2a53cc29869b3e49ffdb7f020ea44`; historical branch
`wp83-wallet-signal-paper-strategy-contract-v1`).

It reconciles repo truth after WP82 merge (PR #83, merge commit
`5c2bd9df3182e6f0035750cd6faa3f6ec8144256`; PR #83 head SHA
`aa88f8d519a04db089cdd6b5b99a5fb3363bde79`) and defines the first
local/offline/read-only wallet signal paper strategy research candidate
contract in docs/schema/tests-only form.

WP83 adds `docs/wallet_signal_paper_strategy_contract.md`,
`docs/schemas/wallet_signal_paper_strategy_contract_v1.example.json`, and
`tests/test_wallet_signal_paper_strategy_contract_docs.py`.

WP83 is docs/schema/tests-only. It adds no source implementation, no tools
implementation, no wallet API client, no network ingestion, no real wallet
monitoring, no live copyability simulator, no PnL computation, no paper
strategy implementation, no paper order model, no paper portfolio ledger,
no paper fill model, no paper PnL calculation, no credentials, no scheduler,
no bot loop, no dashboard, no Hermes/LLM runtime, no dependency or lock-file
changes, and no paper/live account activity behavior.

WP83 resolves WP80-D003, WP81-D002, and WP82-D001 only for
contract-definition scope only. Implementation remains deferred.

Protected boundaries remain unchanged:
- Live account activity: DISABLED
- Credentials: NOT_USED
- Execution: NOT_STARTED
- Authenticated client: FORBIDDEN_UNTIL_APPROVED_WP
- Hermes: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Scheduler: NOT_STARTED
- Bot loop: NOT_STARTED

## WP82 Post-WP81 Repo-Truth Reconciliation And Wallet Intelligence Report Generator V1

WP82 - Post-WP81 Repo-Truth Reconciliation And Wallet Intelligence Report
Generator V1 is merged (PR #83, merge commit
`5c2bd9df3182e6f0035750cd6faa3f6ec8144256`; historical branch
`wp82-wallet-intelligence-report-generator-v1`).

It reconciled repo truth after WP81 merge (PR #82, merge commit
`4f77d5233e51e6379677fd5dec049de372f847a9`; PR #82 head SHA
`97db62d268b4eb99e31549b61f212803ab72742e`) and implemented the first
local/offline/read-only wallet intelligence report generator.

WP82 adds `src/data_layer/wallet_intelligence_report_generator.py` and
`tests/test_wallet_intelligence_report_generator.py`. It updates
`docs/wallet_intelligence_report_contract.md` to record WP82 as the first
local/offline/read-only in-memory report generator implementation.

WP82 is local/offline/read-only. It adds no network ingestion, no wallet
API client, no real wallet monitoring, no live copyability simulator, no
dollar PnL computation, no expected-return calculation, no paper strategy,
no credentials, no scheduler, no bot loop, no dashboard, no Hermes/LLM
runtime, no dependency or lock-file changes, and no paper/live account
activity behavior.

WP82 resolves WP80-D002 and WP81-D001 for the local/offline/read-only
in-memory report generator scope. WP80-D003 through WP80-D006 and WP81-D002
remain OPEN.

Protected boundaries remain unchanged.

## WP81 Post-WP80 Repo-Truth Reconciliation And Local Copyability Delay Evaluation From Validated Fixtures V1

WP81 - Post-WP80 Repo-Truth Reconciliation And Local Copyability Delay
Evaluation From Validated Fixtures V1 is on branch
(`wp81-local-copyability-delay-evaluation-from-fixtures`).

It reconciles repo truth after WP80 merge (PR #81, merge commit
`ee3d10296dce5504164b7e747b286e8fe5a09991`; PR #81 head SHA
`0f7b2defb6c2392f75be800286304577b800dbef`) and implements the first
local/offline/read-only copyability delay evaluator.

WP81 adds `src/data_layer/wallet_copyability_delay_evaluation.py` and
`tests/test_wallet_copyability_delay_evaluation.py`. It updates
`docs/wallet_copyability_delay_simulator_design.md` to record WP81 as the
first local/offline evaluator implementation.

WP81 is local/offline/read-only. It adds no network ingestion, no wallet API
client, no real wallet monitoring, no live copyability simulator, no dollar PnL
computation, no expected-return calculation, no paper-trading strategy, no
credentials, no scheduler, no bot loop, no dashboard, no LLM/AI agent runtime,
no dependency or lock-file changes, and no paper/live trading behavior.

WP81 resolves WP80-D001 only for the local/offline/read-only evaluator
implementation scope. WP80-D002 through WP80-D006 remain OPEN.

Protected boundaries remain unchanged.

## WP80 Post-WP79 Repo-Truth Reconciliation And Copyability Delay Simulator Design Plus Wallet Intelligence Report Contract

WP80 - Post-WP79 Repo-Truth Reconciliation And Copyability Delay Simulator
Design Plus Wallet Intelligence Report Contract is merged (PR #81, merge commit
`ee3d10296dce5504164b7e747b286e8fe5a09991`; historical branch
`wp80-copyability-delay-simulator-design-wallet-report-contract`).

It reconciles repo truth after WP79 merge (PR #80, merge commit
`4266aefa09da9b06a7e2f547aae70149c203da80`; PR #80 head SHA
`3b65ce56fd94364ad238d306f3bfd8176f3eaf27`) and creates the copyability delay
simulator design and wallet intelligence report contract in docs/schema/tests-only form.

WP80 adds `docs/wallet_copyability_delay_simulator_design.md`,
`docs/wallet_intelligence_report_contract.md`,
`docs/schemas/wallet_copyability_delay_evaluation_v1.example.json`,
`docs/schemas/wallet_intelligence_report_v1.example.json`, and
`tests/test_wallet_copyability_delay_report_contract_docs.py`.

WP80 is docs/schema/tests-only. It adds no source implementation, no tools
implementation, no wallet API client, no network ingestion, no real wallet
monitoring, no live copyability simulator, no PnL computation, no expected-return
calculation, no paper-trading strategy, no credentials, no scheduler, no bot
loop, no dashboard, no Hermes/LLM runtime, no dependency or lock-file changes,
and no paper/live trading behavior.

WP80 resolves WP79-D001 and WP79-D002 (and related WP76/WP77/WP78 copyability
and report deferred items) only for docs/schema/tests-only copyability delay
simulator design and wallet intelligence report contract scope.

Protected boundaries remain unchanged:
- Live trading: DISABLED
- Credentials: NOT_USED
- Execution: NOT_STARTED
- Authenticated client: FORBIDDEN_UNTIL_APPROVED_WP
- Hermes: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Scheduler: NOT_STARTED
- Bot loop: NOT_STARTED

## WP79 Post-WP78 Repo-Truth Reconciliation And Wallet Skill/Niche Profiler And Research Queue Integration V1

WP79 - Post-WP78 Repo-Truth Reconciliation And Wallet Skill/Niche Profiler And
Research Queue Integration V1 is merged (historical branch:
`wp79-wallet-skill-niche-profiler-research-queue-integration`; PR #80, merge
commit `4266aefa09da9b06a7e2f547aae70149c203da80`; PR #80 head SHA
`3b65ce56fd94364ad238d306f3bfd8176f3eaf27`).

It reconciles repo truth after WP78 merge (PR #79, merge commit
`7ff117f6caf78eab62e6a116db72b60d76d305f5`; PR #79 head SHA
`d59ed363d16262553314730af36812803076696e`) and creates the first local/offline
advisory wallet signal research profile and research queue annotation layer.

WP79 adds `src/data_layer/wallet_signal_research_profile.py`,
`tests/test_wallet_signal_research_profile.py`, and
`docs/wallet_signal_research_profile.md`.

WP79 is local/offline/read-only. It consumes only WP78 validated
`LoadedWalletTradeEventRecord` objects. It produces deterministic advisory
`WalletSignalResearchProfile` and `WalletResearchQueueAnnotation` frozen
dataclasses. It does not fetch network or API data, monitor real wallets,
compute copyability PnL, produce buy/sell signals, modify scoring weights,
place orders, write files, use credentials, or run paper/live trading.

WP79 resolves WP78-D001 (wallet skill/niche profiler) and WP78-D002 (wallet
research queue integration) only for the local/offline/read-only advisory
profiling and annotation scope.

Protected boundaries remain unchanged:
- Live trading: DISABLED
- Credentials: NOT_USED
- Execution: NOT_STARTED
- Authenticated client: FORBIDDEN_UNTIL_APPROVED_WP
- Hermes: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Scheduler: NOT_STARTED
- Bot loop: NOT_STARTED

## WP78 Post-WP77 Repo-Truth Reconciliation And Wallet Trade Event Snapshot Schema, Local Loader, And Validation

WP78 - Post-WP77 Repo-Truth Reconciliation And Wallet Trade Event Snapshot
Schema, Local Loader, And Validation is merged (historical branch:
`wp78-wallet-trade-event-snapshot-loader-validation`; PR #79 merge commit
`7ff117f6caf78eab62e6a116db72b60d76d305f5`; PR #79 head SHA
`d59ed363d16262553314730af36812803076696e`).

It reconciles repo truth after WP77 merge (PR #78, merge commit
`24badbfb7a9da06ee4c8ae94795e1f2c862af913`; PR #78 head SHA
`250ff5c0190453c615a28ad7d8a56e37615bffcc`) and creates the first
local/offline wallet trade event fixture layer.

WP78 adds `docs/wallet_trade_event_snapshot_schema.md`,
`docs/schemas/wallet_trade_event_snapshot_v1.example.json`,
`src/data_layer/wallet_trade_event_fixtures.py`, and
`tests/test_wallet_trade_event_fixtures.py`.

WP78 is local/offline/read-only. The loader accepts only explicit local JSON
object, JSON list, or direct-child `*.json` directory fixture inputs. It rejects
URL-like paths, invalid JSON, unsupported extensions, and non-object list
entries. It does not recursively scan directories and it does not auto-scan
`local_data/`.

WP78 adds no wallet API client, no network ingestion, no real wallet monitoring,
no wallet skill/niche profiler, no copyability delay simulator, no wallet
intelligence report generator, no research queue integration, no paper-trading
strategy, no credentials, no scheduler, no bot loop, no dashboard, no Hermes/LLM
runtime, no dependency or lock-file changes, and no paper/live trading behavior.

WP78 resolved WP76-D002 and WP77-D001 only for the local/offline/read-only
schema, static example, validator, and fixture loader scope. Wallet skill/niche
profiling, wallet research queue integration, copyability delay simulation,
wallet intelligence reporting, wallet signal paper strategy contracts, wallet
API/network ingestion, and direct wallet-driven live execution remain deferred.

Protected boundaries remain unchanged:
- Live trading: DISABLED
- Credentials: NOT_USED
- Execution: NOT_STARTED
- Authenticated client: FORBIDDEN_UNTIL_APPROVED_WP
- Hermes: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Scheduler: NOT_STARTED
- Bot loop: NOT_STARTED

## WP77 Post-WP76 Repo-Truth Reconciliation And Wallet Intelligence Architecture, Registry, Profile, And Signal Contract

WP77 - Post-WP76 Repo-Truth Reconciliation And Wallet Intelligence Architecture,
Registry, Profile, And Signal Contract is merged (historical branch:
`wp77-wallet-intelligence-architecture-registry-profile-contract`).

It reconciled repo truth after WP76 merge (PR #77, merge commit
`91cd26e4fe16d492fa2f7b319fba176ee60cd9d5`; PR #77 head SHA
`831a958cfef716e4974abe6620dfd02f66caff93`) and was merged by PR #78
(merge commit `24badbfb7a9da06ee4c8ae94795e1f2c862af913`; head SHA
`250ff5c0190453c615a28ad7d8a56e37615bffcc`). It created the first
wallet-intelligence architecture/profile/signal contract layer.

WP77 adds `docs/wallet_intelligence_architecture_and_signal_contract.md`
(advisory-only wallet registry, profile, signal, research-priority effect,
copyability, suspicious-flow, safety flag, and future-WP sequence contract),
`docs/schemas/wallet_intelligence_profile_v1.example.json`,
`docs/schemas/wallet_intelligence_signal_contract_v1.example.json`, and
`tests/test_wallet_intelligence_architecture_contract_docs.py`.

WP77 is docs/schema/tests-only. It adds no source implementation, no tools
implementation, no wallet loader, no wallet API client, no real wallet
monitoring, no copyability simulator, no research queue code integration, no
network ingestion, no credentials, no order placement, no cancels, no position
sizing, no risk override, no scheduler, no bot loop, no dashboard, no
Hermes/LLM execution authority, no dependency or lock-file changes, and no
paper/live trading behavior.

WP77 resolves WP76-D001 only for the docs/schema/tests architecture, registry,
profile, and signal-contract design scope. WP76-D002 through WP76-D007 remain
OPEN. WP77 adds WP77-D001 through WP77-D008 as future implementation and safety
deferred items.

Protected boundaries remain unchanged:
- Live trading: DISABLED
- Credentials: NOT_USED
- Execution: NOT_STARTED
- Authenticated client: FORBIDDEN_UNTIL_APPROVED_WP
- Hermes: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Scheduler: NOT_STARTED
- Bot loop: NOT_STARTED

## WP76 Post-WP75 Repo-Truth Reconciliation And Wallet Intelligence Roadmap Lock-In

WP76 - Post-WP75 Repo-Truth Reconciliation And Wallet Intelligence Roadmap Lock-In
is merged (historical branch: `wp76-wallet-intelligence-roadmap-lockin`; PR #77
merge commit `91cd26e4fe16d492fa2f7b319fba176ee60cd9d5`).

It reconciled repo truth after WP75 merge (PR #76, merge commit
`0160ac1c7087625a4596edd541524445bc004bd5`) and locks the accepted wallet
intelligence roadmap direction into repo truth.

WP76 added `docs/wallet_intelligence_research_signal_roadmap.md` (docs-only
planning lock: wallet intelligence is a first-class research signal layer, not
a blind copy-trading engine; defines core locked decision, role in architecture,
five wallet intelligence jobs, required wallet metrics, wallet signal categories,
copyability delay principle, research queue weighting policy target, suspicious-flow
boundary, updated near-term roadmap WP77–WP82, explicit non-goals, future
controlled live boundary, and deferred items WP76-D001 through WP76-D007). It adds
`tests/test_wallet_intelligence_roadmap_docs.py` (focused docs tests enforcing all
roadmap invariants). It updates repo-truth docs. It adds no source implementation,
no wallet registry, no wallet profile validator, no trade event loader, no
copyability simulator, no API/network access, no credentials, no execution, no
scheduler, no bot loop, no dashboard, no Hermes runtime, no dependency or
lock-file changes, and no paper/live trading behavior.

WP76 resolves no existing deferred items by implementation. WP76 adds WP76-D001
through WP76-D007 as new wallet-intelligence implementation deferred items.

WP76 is docs/tests-only. Wallet intelligence is now the accepted roadmap
direction. All protected boundaries remain unchanged:
- Live trading: DISABLED
- Credentials: NOT_USED
- Execution: NOT_STARTED
- Scheduler: NOT_STARTED
- Bot loop: NOT_STARTED
- Agent execution authority: FORBIDDEN

## WP75 Post-WP74 Repo-Truth Reconciliation And Local Human Review Label Fixture Loader V1

WP75 - Post-WP74 Repo-Truth Reconciliation And Local Human Review Label Fixture
Loader V1 is merged (PR #76 merged; merge commit
`0160ac1c7087625a4596edd541524445bc004bd5`; previously on branch
`wp75-local-human-review-label-fixture-loader-v1`).

Historical current phase after WP74 merge: WP75 - Post-WP74 Repo-Truth
Reconciliation And Local Human Review Label Fixture Loader V1.

It reconciled repo truth after WP74 merge and added a local/offline/read-only
human review label fixture loader.

WP75 adds `src/data_layer/human_review_label_fixture_loader.py` (stdlib-only
local/offline/read-only fixture loader; implements
`load_human_review_label_fixtures(path) -> HumanReviewLabelFixtureLoadResult`;
accepts single JSON object file, JSON list file, or direct-child *.json directory;
validates each loaded record with `validate_human_review_label_record` from WP74;
returns frozen deterministic `HumanReviewLabelFixtureLoadResult` and
`LoadedHumanReviewLabelRecord` dataclasses; rejects URL-like paths, unsupported
extensions, missing paths, invalid JSON, and non-object list entries; no file
writes, no network, no credentials, no automation, stdlib-only). It adds
`tests/test_human_review_label_fixture_loader.py` (47 focused tests). It updates
repo-truth docs.

WP75 resolves WP74-D001 and WP73-D002 only for the local/offline/read-only label
fixture loader scope. WP75 adds WP75-D001 through WP75-D004.

## WP73 Post-WP72 Repo-Truth Reconciliation And Human Review Label Workflow Design V1

WP73 - Post-WP72 Repo-Truth Reconciliation And Human Review Label Workflow Design V1
is on branch (`wp73-human-review-label-workflow-design-v1`).

It reconciles repo truth after WP72 merge and designs the human review label workflow for local
calibration records.

WP73 adds `docs/human_review_label_workflow_design.md` (design-only; defines manual research-usefulness
labeling purpose, label unit, allowed human review usefulness labels, confidence labels, primary reasons,
reason fields, workflow states, quality gates, calibration uses, forbidden calibration uses, and future
implementation phases; no implementation authorized). It adds
`docs/schemas/human_review_label_record_v1.example.json` (static advisory-only example label record
schema; contains identity, review, and safety sections; no trading/PnL/performance fields; marked
ADVISORY_ONLY_MANUAL_RESEARCH_REVIEW_LABEL and DESIGN_ONLY_NOT_IMPLEMENTED). It adds
`tests/test_human_review_label_workflow_docs.py` (focused docs tests enforcing design doc existence,
manual research-usefulness purpose, non-trade/non-profitability/non-buy-sell statements, label unit and
identity fields, allowed usefulness labels, workflow states, confidence labels, primary reasons, quality
gates, calibration uses and forbidden uses, future implementation phases, schema existence and required
fields, safety flags, no-forbidden-trading-fields, project status WP72 merged and WP73 on branch, repo
truth index includes new docs, deferred items WP73-D001 through WP73-D004, protected boundaries
unchanged, and no src/tools/ files modified). It updates repo-truth docs. It adds no source
implementation, no label editor/loader/validator, no report/export changes, no network, no credentials,
no database/dashboard, no scheduler, no LLM/agent labeling, no scoring weight changes, no dependency or
lock-file changes, and no paper/live trading behavior.

WP73 resolves no existing deferred items by implementation. WP73 adds WP73-D001 (human review label
record validator remains deferred), WP73-D002 (human review label fixture loader remains deferred),
WP73-D003 (label/report integration remains deferred), and WP73-D004 (automated or LLM-based labeling
remains forbidden/deferred).

## WP72 Post-WP71 Repo-Truth Reconciliation And Local Calibration Report Export V1

WP72 - Post-WP71 Repo-Truth Reconciliation And Local Calibration Report Export V1
is merged (PR #73 merged; merge commit `1550ba28f192a9c0f5512f1cf695cf06faa3318f`; previously on
branch `wp72-local-calibration-report-export-v1`).

It reconciles repo truth after WP71 merge and adds an explicit manual local calibration report
export tool.

WP72 adds `tools/calibration/local_calibration_report_export.py` (stdlib-only local/offline/read-only
manual export CLI; uses WP68 `load_resolved_outcome_fixtures` for input loading and WP71
`build_calibration_report_from_load_result` for report generation; supports --input (single JSON
object, JSON list, or direct-child *.json directory), --format (json|markdown), --output (optional
explicit local path; stdout by default); output path safety guard rejects writes into src/, tests/,
docs/, tools/, .github/ and symlink-resolved tracked directories; exit codes: 0=success, 1=load or
format error, 2=unsafe output path; advisory-only; no scheduler, no daemon, no database, no
dashboard, no network, no credentials, no paper/live trading). It adds `tools/calibration/__init__.py`.
It adds `tests/tools/calibration/test_local_calibration_report_export.py` (26 focused tests; 1
skipped on Windows symlink platforms) and `tests/tools/calibration/__init__.py`. It creates
`docs/calibration_report_operator_runbook.md` (operator runbook for safe manual use of the export
tool). It updates repo-truth docs only. It adds no network ingestion, no database/dashboard, no
scheduler, no paper/live trading, no credentials, no dependency or lock-file changes, and no other
runtime/product behavior.

WP72 partially resolves WP71-D001 (CLI/export now implemented for explicit manual local export only;
automated/scheduled export, dashboard/database export, and network ingestion remain deferred).

WP72 adds WP72-D001 (scheduled/automated calibration report generation remains deferred),
WP72-D002 (dashboard/database-backed calibration reports remain deferred), WP72-D003 (human review
label workflow implementation remains deferred), and WP72-D004 (report output is not used for
scoring weight changes until explicit future WP).

## WP71 Post-WP70 Repo-Truth Reconciliation And Local Calibration Report Generator Implementation V1

WP71 - Post-WP70 Repo-Truth Reconciliation And Local Calibration Report Generator Implementation V1
is merged (PR #72 merged; merge commit `6a97ca0b568b60e1c11072c9ecb825a57ff11271`; previously on branch
`wp71-local-calibration-report-generator-implementation-v1`).

It reconciles repo truth after WP70 merge and implements the local/offline/read-only in-memory
calibration report generator.

WP71 adds `src/data_layer/calibration_report_generator.py` (stdlib-only local/offline/read-only
report generator; implements `build_calibration_report(records) -> LocalCalibrationReport` and
`build_calibration_report_from_load_result(load_result) -> LocalCalibrationReport`; frozen
`LocalCalibrationReport` dataclass with all WP69 design contract sections; uses WP70
`compute_calibration_metrics` and `compute_calibration_metrics_from_load_result` to populate
summaries without duplicating metric logic; no file reads or writes; no network; no credentials;
stdlib-only). It adds `tests/test_calibration_report_generator.py` (61 focused tests covering
empty input, report type/scope safety booleans, valid/invalid/stale/missing records, all summary
sections, warnings determinism, forbidden interpretation notice, dataclass immutability,
non-signal boundary, forbidden scope, and WP70/WP68/WP67 compatibility). It updates repo-truth
docs only. It adds no CLI/export/file writer, no network ingestion, no database/dashboard, no
scheduler, no paper/live trading, no credentials, no dependency or lock-file changes, and no other
runtime/product behavior.

WP71 resolves WP70-D001 and WP69-D002 only for the narrow local/offline/read-only in-memory
report object scope. CLI/export/file writing, human review label workflow, scoring weight changes,
and paper/live performance metrics remain deferred.

WP71 adds WP71-D001 (CLI/export/report writer remains deferred), WP71-D002 (human review label
workflow implementation remains deferred), WP71-D003 (report output not used for scoring weight
changes until explicit future WP), and WP71-D004 (paper/live performance metrics remain
forbidden/deferred).

## WP70 Post-WP69 Repo-Truth Reconciliation And Local Calibration Metric Computation V1

WP70 - Post-WP69 Repo-Truth Reconciliation And Local Calibration Metric Computation V1 is merged
(PR #71 merged; merge commit `22b07ba6be7cb661065327cfd2d14ee903cfa58f`; previously on branch
`wp70-local-calibration-metric-computation-v1`).

It reconciles repo truth after WP69 merge and adds a local/offline/read-only calibration metric
computation helper.

WP70 adds `src/data_layer/calibration_metric_computation.py` (stdlib-only local/offline/read-only
metric computation helper; implements `compute_calibration_metrics(records) ->
CalibrationMetricComputationResult` and `compute_calibration_metrics_from_load_result(load_result)
-> CalibrationMetricComputationResult`; accepts raw calibration record dicts or WP68
`ResolvedOutcomeFixtureLoadResult`; uses WP67 validator for per-record valid/invalid/warning
counts; frozen deterministic `CalibrationMetricComputationResult` dataclass; no trading/performance
metrics; no file reads or writes; no network; no credentials). It adds
`tests/test_calibration_metric_computation.py` (75 focused tests). It updates repo-truth docs only.

WP70 resolves WP69-D001 only for the local/offline/read-only metric computation scope.
WP69-D002 through WP69-D004 remain deferred.

WP70 adds WP70-D001 (report generator implementation remains deferred), WP70-D002 (human review
label workflow remains deferred), WP70-D003 (metric results not used for scoring weight changes),
and WP70-D004 (paper/live performance metrics remain forbidden/deferred).

## WP69 Post-WP68 Repo-Truth Reconciliation And Calibration Report Generator Design V1

WP69 - Post-WP68 Repo-Truth Reconciliation And Calibration Report Generator Design V1 is on branch
(`wp69-calibration-report-generator-design-v1`).

It reconciles repo truth after WP68 merge and designs the local/offline/read-only calibration
report generator for future implementation.

WP69 adds `docs/calibration_report_generator_design.md` (calibration report purpose as
research-usefulness audit only; allowed inputs from WP68/WP67 components; safe report sections;
report output contract; allowed non-trading metrics; forbidden trading/performance metrics;
human interpretation guidance; future implementation phases; non-signal boundary; scope boundary).
It adds `docs/schemas/calibration_report_v1.example.json` (static advisory-only example report
output shape; no trading/PnL/performance fields; marked ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT
and DESIGN_ONLY_NOT_IMPLEMENTED). It adds `tests/test_calibration_report_design_docs.py` (focused
tests enforcing docs existence, research-usefulness purpose, non-trading boundary, allowed/forbidden
inputs, allowed/forbidden metrics, human interpretation guidance, future phases, deferred
implementation, schema no-forbidden-fields, project-status reconciliation, repo-truth index
coverage, deferred items, and protected boundaries). It updates repo-truth docs only. It adds no
report generator implementation, no calibration metric computation, no network, no credentials, no
dependency or lock-file changes, and no runtime/product behavior.

WP69 resolves WP68-D002 only for the narrow local/offline/read-only calibration report generator
design scope. WP67-D002 (report generator implementation), WP68-D001 (network ingestion),
WP68-D003 (metric computation), and WP68-D004 (scoring weight gate) remain deferred.

WP69 adds WP69-D001 (calibration metric computation implementation remains deferred),
WP69-D002 (calibration report generator implementation remains deferred),
WP69-D003 (human review label workflow implementation remains deferred), and
WP69-D004 (calibration report is not used for scoring weight changes until explicit future WP).

## WP68 Post-WP67 Repo-Truth Reconciliation And Local Resolved Outcome Fixture Loader V1

WP68 - Post-WP67 Repo-Truth Reconciliation And Local Resolved Outcome Fixture Loader V1 is merged
(PR #69 merged; merge commit `37a549cddf702a3b094bcb01a0d98d8980530c1c`; previously on branch `wp68-local-resolved-outcome-fixture-loader-v1`).

It reconciles repo truth after WP67 merge and adds a local/offline/read-only resolved outcome fixture loader based on the WP66 calibration harness design and the WP67 calibration record schema validator.

WP68 adds `src/data_layer/resolved_outcome_fixture_loader.py` (stdlib-only local/offline/read-only fixture loader; implements `load_resolved_outcome_fixtures(path) -> ResolvedOutcomeFixtureLoadResult`; accepts explicit local path to a single JSON object file, a JSON list file, or a direct-child *.json directory; validates each loaded record with `validate_calibration_record` from WP67; returns frozen deterministic `ResolvedOutcomeFixtureLoadResult` and `LoadedCalibrationRecord` dataclasses with loaded/valid/invalid/warning counts; rejects URL-like paths, unsupported extensions, missing paths, invalid JSON, and recursive directory scanning; no network, no file writes, no metric computation, no report generator, no advisory consumer integration). It adds `tests/test_resolved_outcome_fixture_loader.py` (37 focused tests). It updates repo-truth docs only. It adds no ingestion pipeline, no calibration report generator, no calibration metric computation, no database, no dashboard, no scheduler, no paper/live trading, no network, no credentials, no dependency or lock-file changes.

WP68 resolves WP67-D001 only for the narrow local/offline/read-only fixture loader scope. WP67-D002 (calibration report generator), WP67-D003 (human review label workflow implementation), and WP67-D004 (calibration records not used for scoring weight changes) remain deferred. WP66-D002 (resolved outcome ingestion), WP66-D003 (calibration report generator), and WP66-D004 (paper/live performance metrics) remain deferred.

WP68 adds WP68-D001 (network/API resolved outcome ingestion remains deferred), WP68-D002 (calibration report generator remains deferred), WP68-D003 (calibration metric computation remains deferred), and WP68-D004 (fixture loader is not used for scoring weight changes until explicit future WP).

## WP67 Post-WP66 Repo-Truth Reconciliation And Local Calibration Record Schema Validator V1

WP67 - Post-WP66 Repo-Truth Reconciliation And Local Calibration Record Schema Validator V1 is merged
(PR #68 merged; merge commit `23c4f6048819a902d19d726aa7c267a6131a3b2b`; previously on branch `wp67-local-calibration-record-schema-validator-v1`).

It reconciles repo truth after WP66 merge and adds a local/offline/read-only calibration record schema validator based on the WP66 calibration harness design and example schema.

WP67 adds `src/data_layer/calibration_record_validation.py` (stdlib-only local/offline/read-only validator; implements `validate_calibration_record` returning a frozen `CalibrationRecordValidationResult`; validates required top-level sections, identity fields, snapshot fields and offsets, research queue fields and bucket enum, resolved outcome fields, resolution status and source type enums, human review usefulness label enum, calibration validity fields, type checks, and forbidden trading/performance key detection; no network, no file writes, no ingestion, no report generator, no advisory consumer integration). It adds `tests/test_calibration_record_validation.py` (104 focused tests). It updates repo-truth docs only. It adds no ingestion pipeline, no calibration report generator, no database, no dashboard, no scheduler, no paper/live trading, no network, no credentials, no dependency or lock-file changes.

WP67 resolves WP66-D001 only for the narrow local/offline/read-only calibration record schema validator scope. WP66-D002 (resolved outcome ingestion), WP66-D003 (calibration report generator), and WP66-D004 (paper/live performance metrics) remain deferred.

WP67 adds WP67-D001 (local resolved outcome fixture loader remains deferred), WP67-D002 (calibration report generator remains deferred), WP67-D003 (human review label workflow implementation remains deferred), and WP67-D004 (calibration records not used for scoring weight changes until explicit future WP).

## WP66 Post-WP65 Repo-Truth Reconciliation And Calibration Harness Design / Resolved Outcome Requirements V1

WP66 - Post-WP65 Repo-Truth Reconciliation And Calibration Harness Design / Resolved Outcome Requirements V1 is merged
(PR #67 merged; merge commit `2d62589351a6aa1267ce90c7be69aed56fb97f81`; previously on branch `wp66-calibration-harness-design-resolved-outcome-requirements-v1`).

It reconciled repo truth after WP65 merge and designed the local/offline/read-only calibration framework for evaluating whether Market Research Priority outputs and the WP64/WP65 research queue are useful for human research triage.

WP66 adds `docs/calibration_harness_design.md` (calibration purpose, unit, metrics, human-review labels, snapshot timing offsets, calibration gates, non-signal boundary, and future implementation phases). It adds `docs/resolved_outcome_data_requirements.md` (minimum resolved-outcome fields, resolution status values, resolution source type values, non-signal boundary, local/offline scope constraint, and relationship to calibration record). It adds `docs/schemas/calibration_record_v1.example.json` (static advisory-only example schema with no trading/PnL/performance fields). It adds `tests/test_calibration_harness_docs.py` (focused tests enforcing docs existence, research-usefulness purpose, non-trading boundary, resolved outcome field requirements, human-review labels, future phases, and forbidden trading wording). It updates repo-truth docs only. It adds no source implementation, no ingestion, no API calls, no scheduler, no database, no dashboard, no network, no credentials, no paper/live trading, no advisory consumer integration, no scorer weight changes, no dependency or lock-file changes, and no runtime/product behavior.

WP66 adds WP66-D001 (calibration record validator implementation deferred), WP66-D002 (resolved outcome ingestion deferred), WP66-D003 (calibration report generator deferred), and WP66-D004 (paper/live performance metrics remain forbidden/deferred).

## WP65 Repo-Truth Reconciliation, Local Research Queue Export, Operator Runbook, And Wording Guardrails V1

WP65 - Repo-Truth Reconciliation, Local Research Queue Export, Operator Runbook, And Wording Guardrails V1 is merged
(PR #66 merged; merge commit `5c5b0c7ef8a2d1f094a2eff6dabbe6fd4be434f7`; previously on branch `wp65-local-research-queue-export-operator-runbook-v1`).

It reconciles repo truth after WP64 merge and turns the WP64 in-memory research queue objects into a manually invoked local export/briefing workflow.

WP65 adds `tools/research_queue/local_research_queue_export.py` (local/offline/read-only stdlib-only manual export CLI tool consuming WP64 report objects or market context lists; produces JSON or Markdown output to stdout or an explicit local path; advisory-only; no scheduler, no daemon, no database, no dashboard, no network, no credentials, no advisory consumer integration, no paper/live trading). It adds focused tests in `tests/tools/research_queue/test_local_research_queue_export.py`. It adds the operator runbook at `docs/research_queue_operator_runbook.md`. It updates repo-truth docs only. It adds no scorer weight changes, no dependency or lock-file changes, no runtime/product/trading behavior, no authenticated client, no network polling.

WP65 resolves the narrow part of WP49-D002 (CLI/export/report writer not started) for the local/offline/explicit/manual export scope only. Scheduled/automated export, dashboard/database-backed queue, and advisory consumer integration remain deferred.

## WP64 Repo-Truth Reconciliation, Research Queue Ranking, Local Human Review Report, And Research Session Packet V1

WP64 - Repo-Truth Reconciliation, Research Queue Ranking, Local Human Review Report, And Research Session Packet V1 is merged
(PR #65 merged; merge commit `7795efd45b19ab89c943bd49602449baa67411db`; previously on branch `wp64-research-queue-report-session-packet-v1`).

It reconciled repo truth after WP63 merge and added a local/offline/read-only research-output layer to turn prepared Market Research Priority outputs into an in-memory human review queue and compact research session packets.

WP64 adds `src/data_layer/market_research_priority_review_queue.py` (new stdlib-only local/offline/read-only module implementing `build_research_review_queue`, `build_local_human_review_report`, and `build_research_session_packet`). Each packet includes compact summaries of existing metadata: data_quality_summary, resolution_summary, microstructure_summary, cross_market_summary, source_hierarchy_summary. The queue is deterministically sorted by bucket priority, then by research_priority_score descending, then by market_id ascending. Buckets: REVIEW_FIRST, MANUAL_SOURCE_REVIEW_REQUIRED, REVIEW_LATER, DATA_QUALITY_BLOCKED, DEPRIORITIZED. Advisory-only. Not a trading signal.

WP64 adds focused tests in `tests/test_market_research_priority_review_queue.py`. It updates repo-truth docs only. It adds no database, dashboard, runtime, scheduler, bot loop, credentials, dependency, lock-file, scorer weight change, network, paper/live trading, execution, parser, report file writer, CLI, export, or advisory consumer integration.

## WP63 Repo-Truth Reconciliation And Resolution Source Hierarchy Metadata V1 For Research Priority Feature Extraction

WP63 - Repo-Truth Reconciliation And Resolution Source Hierarchy Metadata V1 For Research Priority Feature Extraction is merged
(PR #64 merged; merge commit `e1ab1aa7e0915a3c65afc9eb5a55c58292ef6910`; previously on branch `wp63-resolution-source-hierarchy-metadata-v1`).

It reconciles repo truth after WP62 merge and adds deterministic, metadata-only resolution source hierarchy metadata to `src/data_layer/market_research_priority_features.py`. Each prepared market_context receives a `resolution_source_hierarchy` sub-dict built from deterministic local field presence checks (resolution_date for timing, question text for source text and URL pattern detection). No resolution-rule parsing, no source authority judgment, no official-source monitoring, no automated interpretation.

WP63 adds focused tests in `tests/test_market_research_priority_features.py`. It updates repo-truth docs only. It adds no database, dashboard, runtime, scheduler, bot loop, credentials, dependency, lock-file, scorer weight, network, paper/live trading, execution, parser, report writer, or advisory consumer integration.

## WP62 Repo-Truth Reconciliation And Cross-Market Relationship Metadata V1 For Research Priority Feature Extraction

WP62 - Repo-Truth Reconciliation And Cross-Market Relationship Metadata V1 For Research Priority Feature Extraction is merged
(PR #63 merged; merge commit `c31c225e42a14e3b3575f8827148ddb8d4caeb09`; previously on branch `wp62-cross-market-relationship-metadata-v1`).

It reconciles repo truth after WP61 merge and adds deterministic, metadata-only cross-market relationship metadata to `src/data_layer/market_research_priority_features.py`. Each prepared market_context receives a `cross_market_relationships` sub-dict built from local deterministic key comparison (normalized question text, condition_id, token_id, category+resolution_date, outcome-label set). No semantic matching, no price comparison, no automated equivalence claim.

WP62 adds focused tests in `tests/test_market_research_priority_features.py`. It updates repo-truth docs only. It adds no database, dashboard, runtime, scheduler, bot loop, credentials, dependency, lock-file, scorer weight, network, paper/live trading, execution, parser, report writer, or advisory consumer integration.

## WP61 Architecture Direction Lock-In And Microstructure Quality V1 For Market Research Priority Feature Extraction

WP61 - Architecture Direction Lock-In And Microstructure Quality V1 For Market Research Priority Feature Extraction is merged
(PR #62 merged; merge commit `fa84711471fcd81a9f6a447584d0e5dd92e4f4c4`; previously on branch `wp61-architecture-lockin-and-microstructure-quality-v1`).

It reconciles repo truth after WP60A merge and creates `docs/architecture_decision_record.md`
with user-approved planning constraints: SQLite first, Postgres deferred; Streamlit first,
Grafana later, Next.js only if productizing; local development first, cheap VPS later; rules-based
plus research-score-driven strategy first; LLM read-only analyst/proposal layer only; and the
execution ladder research-only -> paper -> dry-run -> manual live approval -> restricted live.

WP61 updates `src/data_layer/market_research_priority_features.py` with a
`microstructure_quality` sub-dict in every prepared market context. The metadata is derived only
from already supplied local `OrderBookSnapshotRecord` objects. It records local order-book
availability, latest local snapshot selection, basic bid/ask side observability, visible local level
counts, stale/degraded local order-book timestamp state, safe warnings, and the advisory-only label.

WP61 adds focused tests in `tests/test_market_research_priority_features.py` and
`tests/test_architecture_direction_docs.py`. It updates repo-truth docs only. It adds no database,
dashboard, runtime, scheduler, bot loop, credentials, dependency, lock-file, scorer weight,
network, paper/live trading, execution, parser, report writer, or advisory consumer integration.

WP61 resolves WP51-D003 and WP53-D002 only for the narrow local/offline/read-only
Microstructure Quality V1 metadata scope. Later numeric modeling or downstream integration remains
deferred until explicitly approved.

## WP60A / WF-STAB-2 Agent-Neutral Startup Layer And Codex/Claude Adapter Alignment

WP60A / WF-STAB-2 - Agent-Neutral Startup Layer And Codex/Claude Adapter Alignment
is merged (PR #61 merged; merge commit `ace8331`; previously on branch `wp60a-agent-neutral-startup-layer`).
It reconciles repo truth after WP59 merge and introduces a shared agent-neutral startup entry point with
thin tool-specific adapters for Codex and Claude Code.

WP60A creates `AI_CODING_AGENT_START_HERE.md` (shared startup entry point for all AI coding agents).
It updates AGENTS.md to be explicitly shared (AI Coding Agent Rulebook).
It updates CODEX_START_HERE.md to be a Codex-specific adapter.
It updates CLAUDE_START_HERE.md to be a Claude Code-specific adapter.
It updates docs/ai/codex/README.md to clarify the historical shared workflow path.
It updates docs/codex_execution_guidelines.md with a compatibility note and shared-agent wording.
It updates docs/work_package_template.md and .github/pull_request_template.md with execution agent fields.

## WP59 / WF-STAB-1 Canonical WP Execution State Machine And Private-Repo Evidence Mode Opening After WP58 Merge

WP59 / WF-STAB-1 - Canonical WP Execution State Machine And Private-Repo Evidence Mode Opening After WP58 Merge
is merged (PR #60 merged; merge commit `8ddef24b3ef35054389323701a3fbcdac86121a3`).
It reconciled repo truth after WP58 merge and created the canonical WP execution state machine with three
evidence modes (PUBLIC_VERIFIER_PASS, PRIVATE_REPO_MANUAL_VERIFIED, BLOCKED_NOT_READY).

WP59 created `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` (canonical state machine for WP execution, evidence packaging, and review-readiness).
It updated startup docs (AGENTS.md, CODEX_START_HERE.md, CLAUDE_START_HERE.md, docs/ai/codex/README.md) to reference the state machine.
It updated mandatory evidence/reporting/validation/review docs to be evidence-mode-aware.

## WP58 Posted GitHub Evidence Verification, Claude Start Layer, And Workflow Execution Hardening After WP57 Merge

WP58 - Posted GitHub Evidence Verification, Claude Start Layer, And Workflow Execution Hardening After WP57 Merge
is merged (PR #59 merged; merge commit `c33748f84f0ec43ef82233f6a4b074083505c23d`).
It reconciled repo truth after WP57 merge and added durable workflow/governance hardening for
posted GitHub evidence verification, Claude Code startup guidance, and negative test matrix policy.

WP58 creates `CLAUDE_START_HERE.md` (Claude Code startup guidance, posted evidence rules, stop rules),
`docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md` (mandatory posted GitHub evidence workflow),
and `docs/ai/codex/NEGATIVE_TEST_MATRIX_POLICY.md` (negative test matrix policy for validators/scorers/parsers).
It adds `tools/git/posted_pr_evidence_verifier.py` (read-only manual GitHub PR evidence verifier),
`tests/tools/git/test_posted_pr_evidence_verifier.py` (focused tests with fake API responses),
`tests/test_posted_github_evidence_workflow_docs.py` (docs workflow tests),
`tests/test_negative_test_matrix_policy_docs.py` (docs tests),
and `tests/test_claude_start_here_docs.py` (docs tests).
It updates `AGENTS.md`, `CODEX_START_HERE.md`, `docs/codex_execution_guidelines.md`,
`docs/ai/codex/README.md`, `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`,
`docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`, `docs/ai/codex/VALIDATION_MATRIX.md`,
`docs/ai/codex/PR_REVIEW_CHECKLIST.md`, `docs/ai/codex/WP_EXECUTION_REPORT.md`,
`docs/ai/codex/WP_BUNDLING_POLICY.md`, `docs/ai/codex/PROTECTED_PATHS.md`,
`docs/work_package_template.md`, `docs/review_checklist.md`, `docs/testing_requirements.md`,
`.github/pull_request_template.md`, `docs/project_status.md`, `docs/repo_truth_index.md`,
and `docs/deferred_items_log.md`.

WP58 is a workflow/governance hardening WP. It adds no source under `src/`, no Polymarket/trading/advisory
tooling, no runtime, no dependency or lock-file changes, no Hermes/LLM/provider integration, no credentials,
no account access, no trading or paper trading, no database/dashboard/scheduler/polling/product behavior,
and no generated outputs committed. The posted PR evidence verifier is read-only, manual, workflow-only, and
uses only the public GitHub REST API (no authentication or tokens). Unit tests use fake GitHub API responses
and make no real network calls.

WP58 reconciles docs/project_status.md after WP57 merge (merge commit
3dd97a9 — exact SHA to be confirmed after merge). WP57 is now listed in merged WPs.

WP58 marks WP54-D001 and WP47-D001 as PARTIALLY_RESOLVED_PUBLIC_ONLY — the new public GitHub
manual read-only helper addresses the public-repo case; authenticated/private GitHub verification
remains unsupported. WP58 adds WP58-D001 (authenticated or private GitHub posted-evidence
verification not implemented; future optional helper may support a token only after explicit
secrets/auth policy review, OPEN, P4).

Security checks are run/assessed in WP58.

## WP57 Repo-Truth Reconciliation And Resolution Ambiguity Local Feature Extraction From Validated Manual Labels

WP57 - Repo-Truth Reconciliation And Resolution Ambiguity Local Feature Extraction From Validated Manual Labels
is on branch (`wp57-resolution-ambiguity-label-feature-extraction`).
It reconciles repo truth after WP56 merge and implements local/offline/read-only feature extraction
from already validated manual resolution ambiguity labels.

WP57 updates `src/data_layer/market_research_priority_features.py` to:
import and consume the WP56 validator (`validate_resolution_ambiguity_label`,
`load_resolution_ambiguity_label_records`, `ADVISORY_LABEL`); add
`build_resolution_ambiguity_label_index()` and `_build_resolution_ambiguity_summary()` helpers;
attach a safe `resolution_ambiguity` sub-dict to all market contexts; update
`extract_market_research_priority_context()`, `extract_market_research_priority_contexts()`,
and `extract_from_snapshot_dir()` to accept optional label input; and bump
`FEATURE_EXTRACTION_VERSION` to `"wp57-v1"`. It updates `tests/test_market_research_priority_features.py`
with WP57-specific tests. It also updates `docs/project_status.md`, `docs/repo_truth_index.md`,
`docs/deferred_items_log.md`, `docs/resolution_ambiguity_taxonomy_manual_label_workflow.md`,
`docs/research_data_foundation_direction.md`, `docs/long_term_bot_completion_roadmap.md`,
`docs/market_research_priority_scoring_layer.md`, and
`docs/market_research_priority_scoring_output_contract.md`.

WP57 is a local/offline/read-only research-label-feature-extraction WP. The feature extraction
module is stdlib-only (plus existing local WP56 module), in-memory output only, no network, no
file writes, no CLI, no export, no report writer, no automated parser, no LLM/Hermes/provider
extraction, no label generation, no inference of ambiguity categories from raw text, no scorer
algorithm or weight changes, no runtime/product/trading behavior, no credentials, no account
access, no trading or paper trading, no database/dashboard/scheduler/polling/product behavior,
and no generated outputs committed. No dependency or lock-file changes.

WP57 reconciles docs/project_status.md after WP56 merge (merge commit
a310e641eb790bd3906d054d703dd11945180e6c). WP56 is now listed in merged WPs.

WP57 resolves WP55-D001 and WP56-D001 only for the narrow local/offline/read-only feature
extraction from validated manual labels scope. WP55-D002 (automated parser) remains OPEN.
WP57 adds WP57-D001 (resolution ambiguity feature extraction not yet integrated into
scorer/report/advisory consumer, OPEN, P3).

Security checks are run/assessed in WP57.

## WP56 Repo-Truth Reconciliation And Resolution Ambiguity Manual Label Schema Validation Foundation

WP56 - Repo-Truth Reconciliation And Resolution Ambiguity Manual Label Schema Validation Foundation
is on branch (`wp56-resolution-ambiguity-label-schema-validation`).
It reconciles repo truth after WP55 merge and implements the local/offline/read-only manual label
schema validation foundation for the WP55 resolution ambiguity taxonomy.

WP56 adds `src/data_layer/resolution_ambiguity_labels.py` (stdlib-only, local/offline/read-only
schema validator) and `tests/test_resolution_ambiguity_labels.py` (51 focused tests). It updates
`docs/project_status.md`, `docs/repo_truth_index.md`, `docs/deferred_items_log.md`,
`docs/resolution_ambiguity_taxonomy_manual_label_workflow.md`,
`docs/research_data_foundation_direction.md`, `docs/long_term_bot_completion_roadmap.md`,
`docs/market_research_priority_scoring_layer.md`, and
`docs/market_research_priority_scoring_output_contract.md`. It also updates
`tests/test_project_status_docs.py`, `tests/test_codex_workflow_docs.py`, and
`tests/test_resolution_ambiguity_taxonomy_manual_label_workflow_docs.py`.

WP56 is a local/offline/read-only research-label-schema-validation WP. The validator module is
stdlib-only, in-memory output only, no network, no file writes (except optional reader for local
JSON/JSONL files), no CLI, no export, no report writer, no automated parser, no feature
extraction, no scorer integration, no runtime/product/trading behavior, no Hermes/LLM/provider
integration, no credentials, no account access, no trading or paper trading, no
database/dashboard/scheduler/polling/product behavior, and no generated outputs committed. No
dependency or lock-file changes.

WP56 reconciles docs/project_status.md after WP55 merge (merge commit
b019bb825924d52057225455886c3ca45af9e925). WP55 is now listed in merged WPs.

WP56 adds WP56-D001 (resolution ambiguity labels validated but not yet consumed by feature
extraction or scoring, OPEN, P3). WP55-D001 and WP55-D002 remain OPEN.

Security checks are run/assessed in WP56.

## WP55 Repo-Truth Reconciliation And Resolution Ambiguity Taxonomy / Manual-Label Workflow

WP55 - Repo-Truth Reconciliation And Resolution Ambiguity Taxonomy / Manual-Label Workflow
is merged (merge commit b019bb825924d52057225455886c3ca45af9e925).
It reconciles repo truth after WP54 merge and delivers a durable resolution-rule ambiguity
taxonomy, manual-label workflow, and label schema for human research data quality review.

WP55 creates `docs/resolution_ambiguity_taxonomy_manual_label_workflow.md` and updates
`docs/project_status.md`, `docs/repo_truth_index.md`, `docs/deferred_items_log.md`,
`docs/research_data_foundation_direction.md`, `docs/long_term_bot_completion_roadmap.md`,
`docs/market_research_priority_scoring_layer.md`, and
`docs/market_research_priority_scoring_output_contract.md`. It adds focused tests at
`tests/test_resolution_ambiguity_taxonomy_manual_label_workflow_docs.py` and updates
`tests/test_project_status_docs.py`.

WP55 is a docs/tests-only research-governance WP. It defines the resolution-rule ambiguity
taxonomy (14 categories), review status values, severity/confidence separation, manual label
schema (17 required fields), local/offline/read-only manual review workflow, future integration
gate, invalid/valid examples, and deferred items. It adds no source under `src/`, no
Polymarket/trading/advisory tooling, no automated parser, no feature extraction, no scorer
integration, no CLI/export/report writer, no runtime, no network, no dependency or lock-file
changes, no Hermes/LLM/provider integration, no credentials, no account access, no trading or
paper trading, no database/dashboard/scheduler/polling/product behavior, and no generated
outputs committed.

WP55 reconciles docs/project_status.md after WP54 merge (merge commit
fb45fb849b0641e2007ef66f50bfd5725354b8f0). WP54 is now listed in merged WPs.

WP55 narrows WP51-D002 and WP53-D001 (taxonomy/manual-label workflow addressed; automated
parser and feature extraction remain not started). WP55 adds WP55-D001 (ambiguity labels not
yet consumed by feature extraction, OPEN, P3) and WP55-D002 (automated resolution-rule parser
remains not started, OPEN, P3). WP55-D001 is narrowed by WP56 (schema validation implemented;
feature extraction from labels still not started).

Security checks are run/assessed in WP55.

## WP54 PR Evidence Follow-Up Defect And Bundled-WP Execution Policy Hardening After WP53 Merge

WP54 - PR Evidence Follow-Up Defect And Bundled-WP Execution Policy Hardening After WP53 Merge
is merged (merge commit fb45fb849b0641e2007ef66f50bfd5725354b8f0).
It reconciles repo truth after WP53 merge and locks follow-up process-defect classification,
bundled-WP execution policy, posted evidence self-check rules, and package size class guidance
into durable repo-truth docs and tests.

WP54 creates `docs/ai/codex/WP_BUNDLING_POLICY.md` and updates
`tools/git/pr_evidence_consistency_guard.py` (adds `--require-guard-result` flag, category P),
`tests/tools/git/test_pr_evidence_consistency_guard.py`,
`docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`,
`docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`,
`docs/ai/codex/PR_REVIEW_CHECKLIST.md`,
`docs/ai/codex/VALIDATION_MATRIX.md`,
`docs/work_package_template.md`,
`.github/pull_request_template.md`,
`docs/project_status.md`,
`docs/repo_truth_index.md`,
`docs/deferred_items_log.md`,
`docs/review_checklist.md`,
`docs/testing_requirements.md`, and
`tests/test_codex_workflow_docs.py`.

WP54 is a local/offline/stdlib workflow-governance helper hardening WP. It hardens
`tools/git/pr_evidence_consistency_guard.py` with a new `--require-guard-result` flag
and updates workflow/governance docs and tests. It adds no source under `src/`, no
Polymarket/trading/advisory tooling, no runtime, no network, no dependency or lock-file
changes, no Hermes/LLM/provider integration, no credentials, no account access, no trading
or paper trading, no database/dashboard/scheduler/polling/product behavior, and no generated
outputs committed.

WP54 reconciles docs/project_status.md after WP53 merge (merge commit
7514b1aded39c5f1ca0c5abae4fdae86b6c4f1d6). WP53 is now listed in merged WPs.

WP54 resolves no existing implementation deferred items. WP54 adds WP54-D001
(GitHub-posted evidence still requires human or Claude manual verification because the guard
remains local/offline and does not fetch live GitHub PR content, OPEN, P4).

Security checks are run/assessed in WP54.

## WP53 Repo-Truth Reconciliation And Provenance/Staleness/Missing-Data Enforcement Hardening

WP53 - Repo-Truth Reconciliation And Provenance/Staleness/Missing-Data Enforcement
Hardening is merged (merge commit 7514b1aded39c5f1ca0c5abae4fdae86b6c4f1d6).
It reconciled repo truth after WP52 merge and hardened local/offline/read-only
provenance, staleness, and missing-data enforcement in Market Research Priority
feature contexts.

WP53 updates `src/data_layer/market_research_priority_features.py` with explicit
provenance degraded flag (`provenance_degraded`), provenance weakness reasons,
future-timestamp detection in staleness, missing question and market_status detection,
and a quality-impacting vs informational provenance weakness separation. It updates
`docs/project_status.md`, `docs/repo_truth_index.md`, `docs/deferred_items_log.md`,
`docs/research_data_foundation_direction.md`, `docs/long_term_bot_completion_roadmap.md`,
`docs/market_research_priority_scoring_layer.md`, and
`docs/market_research_priority_scoring_output_contract.md`. It adds focused tests at
`tests/test_market_research_priority_features.py`.

WP53 is a local/offline/read-only source-implementation and docs/tests WP. It adds
no CLI/export/report writer, no advisory consumer integration, no market catalog
integration, no runtime/product/trading behavior, no Hermes/LLM/provider integration,
no credentials, no network, no account access, no trading or paper trading, no
database/dashboard/scheduler/polling/product behavior, and no generated outputs
committed. No dependency or lock-file changes.

WP53 reconciles docs/project_status.md after WP52 merge (merge commit
259fac091a3b8d0d22aaab13345f440d5a958af2). WP52 is now listed in merged WPs.

WP53 marks WP51-D001 RESOLVED (narrow provenance/staleness/missing-data hardening
scope only). WP53 adds WP53-D001 (resolution-rule ambiguity extraction still not
started, OPEN, P3) and WP53-D002 (microstructure quality feature extraction still
not started, OPEN, P3). WP49-D002, WP49-D003, WP50-D001, WP51-D002, WP51-D003,
WP51-D004, and WP52-D001 remain OPEN.

Security checks are run/assessed in WP53.

## WP52 Long-Term Bot Roadmap And Side 4 Onboarding Lock-In After WP51 Merge

WP52 - Long-Term Bot Roadmap And Side 4 Onboarding Lock-In After WP51 Merge is
merged (merge commit 259fac091a3b8d0d22aaab13345f440d5a958af2).
It reconciles repo truth after WP51 merge and locks the long-term bot-completion
roadmap plus Side 4.0 onboarding context into durable repo-truth documentation.

WP52 adds `docs/long_term_bot_completion_roadmap.md` as the new docs-only
roadmap and Side 4.0 onboarding lock. It updates `docs/project_status.md`,
`docs/repo_truth_index.md`, `docs/research_data_foundation_direction.md`, and
`docs/deferred_items_log.md`. It adds focused tests at
`tests/test_long_term_bot_completion_roadmap_docs.py`.

WP52 is a docs/tests-only WP. It adds no source under `src/`, no tools
implementation, no runtime, no network, no dependency or lock-file changes, no
Hermes/LLM/provider integration, no credentials, no account access, no trading
or paper trading, no database/dashboard/scheduler/polling/product behavior, and
no generated outputs committed.

WP52 reconciles docs/project_status.md after WP51 merge (merge commit
c57b9c0adcc044f8bd9ed01a6368f2fafdbe222f). WP51 is now listed in merged WPs.

WP52 adds WP52-D001 (long-term roadmap locked, but milestone implementation
remains gated by explicit future WPs, OPEN, P3). No existing implementation
deferred items are resolved by WP52.

Security checks are run/assessed in WP52.

## WP51 Market Research Priority Feature Extraction Foundation

WP51 - Market Research Priority Feature Extraction Foundation is merged
(merge commit c57b9c0adcc044f8bd9ed01a6368f2fafdbe222f).
It adds the first narrow local/offline/read-only feature-extraction foundation
for the Market Research Priority Scoring Layer implemented in WP49.

WP51 adds `src/data_layer/market_research_priority_features.py` as a new
stdlib-only local/offline/read-only feature extraction module. It adds focused
tests at `tests/test_market_research_priority_features.py` and updates
`docs/project_status.md`, `docs/repo_truth_index.md`,
`docs/deferred_items_log.md`, `docs/research_data_foundation_direction.md`,
`docs/market_research_priority_scoring_layer.md`, and
`tests/test_architecture_boundaries.py`.

WP51 bridges existing approved local/offline Polymarket snapshot artifacts into
prepared scorer input dictionaries. The feature module reads
`MarketMetadataSnapshotRecord`, `OrderBookSnapshotRecord`, and `SnapshotManifest`
objects; extracts basic metadata/provenance/staleness/missing-data feature
inputs; and produces prepared `run_context` and `market_context` dictionaries
compatible with `build_market_research_priority_output()` from WP49.

WP51 is a local/offline/read-only source-implementation WP. The feature
extraction module is stdlib-only, in-memory output only, no network, no file
writes, no CLI, no export, no report writer, no advisory consumer integration,
no runtime/product/trading behavior, no Hermes/LLM/provider integration, no
credentials, no account access, no trading or paper trading, no
database/dashboard/scheduler/polling/product behavior, and no generated outputs
committed. No dependency or lock-file changes.

WP51 reconciles docs/project_status.md after WP50 merge (merge commit
180a6547114824890851d6ba7e34ab96e7ddd4b8). WP50 is now listed in merged WPs.

WP51 marks WP49-D001 RESOLVED (narrow WP51 basic feature extraction foundation
scope only). WP51 adds WP51-D001 (provenance/staleness hardening beyond
foundation not started), WP51-D002 (resolution-rule ambiguity extraction not
started), WP51-D003 (microstructure quality feature extraction beyond basic
availability not started), and WP51-D004 (CLI/export/report writer not started).

Security checks are run/assessed in WP51.

## WP50 Research Data Foundation Direction Lock-In After WP49 Merge

WP50 - Research Data Foundation Direction Lock-In After WP49 Merge is merged
(merge commit 180a6547114824890851d6ba7e34ab96e7ddd4b8).
It reconciles repo truth after WP49 merge and locks the completed Polymarket
research-phase decisions into durable repo-truth documentation.

WP50 adds `docs/research_data_foundation_direction.md` as a new docs-only
direction lock recording the final research-phase decisions, approved near-term
sequence, blocked directions, non-signal semantics, and new-chat onboarding
summary. It updates `docs/project_status.md`, `docs/repo_truth_index.md`, and
`docs/deferred_items_log.md`, and adds a focused docs test at
`tests/test_research_data_foundation_direction_docs.py`.

WP50 is a docs/tests-only repo-truth reconciliation and research-direction
decision lock WP. It adds no runtime source under `src/`, no scoring
implementation, no feature extraction implementation, no CLI/export/report
writer, no dependency or lock-file changes, no Hermes/LLM/provider integration,
no credentials, no network/account access, no trading or paper trading, no
database/dashboard/scheduler/polling/product behavior, and no generated
outputs committed.

WP50 reconciles docs/project_status.md after WP49 merge (merge commit
3ee02a7c31a1d4f5d599fdb1d5ffa83d6fca1d6d). WP49 is now listed in merged WPs.

WP50 preserves WP49-D001, WP49-D002, and WP49-D003 as OPEN. WP50 adds
WP50-D001 (research direction locked, but implementation sequencing still
requires explicit future WPs, OPEN, P3).

Security checks are run/assessed in WP50.

## WP49 Market Research Priority Scoring Core Implementation

WP49 - Market Research Priority Scoring Core Implementation is merged
(merge commit 3ee02a7c31a1d4f5d599fdb1d5ffa83d6fca1d6d).
It implements the first minimal local/offline/read-only core scorer for the
Market Research Priority Scoring Layer defined in WP44 (design) and WP48
(output contract).

WP49 adds `src/data_layer/market_research_priority_scoring.py` as a new
stdlib-only local/offline/read-only core scorer module. It adds focused tests
at `tests/test_market_research_priority_scoring_core.py` and updates
`docs/market_research_priority_scoring_output_contract.md`,
`docs/market_research_priority_scoring_layer.md`, `docs/project_status.md`,
`docs/repo_truth_index.md`, `docs/deferred_items_log.md`, and
`tests/test_market_research_priority_scoring_output_contract_docs.py`.

WP49 is a local/offline/read-only source-implementation WP. The core scorer
is stdlib-only, in-memory output only, no network, no file writes, no CLI,
no export, no report writer, no feature extraction from real artifacts, no
advisory consumer integration, no runtime/product/trading behavior, no
Hermes/LLM/provider integration, no credentials, no account access, no
trading or paper trading, no database/dashboard/scheduler/polling/product
behavior, and no generated outputs committed. No dependency or lock-file
changes.

WP49 reconciles docs/project_status.md after WP48 merge (merge commit
9e9d6cb1434cb831006f75ed142899ff2ebc675b). WP48 is now listed in merged WPs.

WP49 resolves WP44-D001, WP44-D002, WP48-D001, and WP48-D002 only for the
local/offline/read-only core scorer scope. WP49 adds WP49-D001 (feature
extraction from local/offline artifacts not started, OPEN, P3), WP49-D002
(CLI/export/report writer not started, OPEN, P3), and WP49-D003 (core scorer
not integrated with advisory consumer or market catalog, OPEN, P3). All
WP48-forward deferred items that are not resolved by WP49 remain unchanged.

Security checks are run/assessed in WP49.

## WP48 Market Research Priority Scoring Schema / Output Contract

WP48 - Market Research Priority Scoring Schema / Output Contract is merged
(merge commit 9e9d6cb1434cb831006f75ed142899ff2ebc675b).
It defines the formal schema and output contract for the future local/offline/read-only
Market Research Priority Scoring Layer designed in WP44.

WP48 adds `docs/market_research_priority_scoring_output_contract.md` as a new binding
docs-only output contract. It updates `docs/market_research_priority_scoring_layer.md`
to reference the new contract and update status. It adds a focused docs test at
`tests/test_market_research_priority_scoring_output_contract_docs.py` and updates
`tests/test_market_research_priority_scoring_layer_docs.py`, `docs/project_status.md`,
`docs/repo_truth_index.md`, and `docs/deferred_items_log.md`.

WP48 is a docs/tests-only schema and output-contract WP. It adds no runtime source under
`src/`, no scoring implementation, no CLI tooling, no JSON writer, no report writer,
no dependency or lock-file changes, no Hermes/LLM/provider integration, no credentials,
no network/account access, no trading or paper trading, no database/dashboard/scheduler/
polling/product behavior, and no generated outputs committed.

WP48 reconciles docs/project_status.md after WP47 merge (merge commit
8436ce1c75b705b1154a6edcb9c4c1a7d0615ab4). WP47 is now listed in merged WPs.

WP48 resolves no existing deferred items. WP44-D001 and WP44-D002 remain OPEN because
implementation is still not started. WP48 adds WP48-D001 (Market Research Priority Scoring
implementation not started after schema/output contract, OPEN, P3) and WP48-D002
(schema/output contract not enforced by implementation yet, OPEN, P3). All WP47-forward
deferred items remain unchanged.

Security checks are run/assessed in WP48.

## WP47 Posted PR Evidence Review Hardening

WP47 - Posted PR Evidence Review Hardening is merged
(historical branch: `wp47-posted-pr-evidence-review-hardening`).
It hardened the PR evidence workflow so future PRs do not require repeated manual
follow-ups for stale PR body text, stale final comments, placeholder SHAs, stale
inline test counts, or ambiguity between old and current evidence comments.

WP47 updates `tools/git/pr_evidence_consistency_guard.py` with five new optional
flags: `--forbid-inline-test-counts`, `--forbid-placeholder-evidence`,
`--require-current-final-marker`, `--forbid-stale-count-tokens`, and
`--require-posted-evidence-note`. It updates
`tests/tools/git/test_pr_evidence_consistency_guard.py` with focused tests for
all new flags, and updates `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`,
`docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`,
`docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`,
`docs/ai/codex/WP_EXECUTION_REPORT.md`,
`docs/ai/codex/PR_REVIEW_CHECKLIST.md`,
`docs/ai/codex/VALIDATION_MATRIX.md`,
`docs/work_package_template.md`,
`docs/review_checklist.md`, and
`docs/project_status.md`. It also adds a new optional doc at
`docs/ai/codex/POSTED_PR_EVIDENCE_REVIEW_HARDENING.md` and updates
`docs/repo_truth_index.md` and `docs/deferred_items_log.md`.

WP47 is a local/offline stdlib governance-helper hardening WP. It adds no runtime
source under `src/`, no dependency or lock-file changes, no Hermes/LLM/provider
integration, no credentials, no network/account access, no trading or paper
trading, no database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP47 reconciles docs/project_status.md after WP46 merge (merge commit
47e349bdc6eb1eb084d9b944e8aa66874730e08b). WP46 is now listed in merged WPs.

WP47 resolves no existing deferred items. WP47 adds WP47-D001 (guard still does
not fetch live GitHub PR body/comments, OPEN, P4). All WP46-forward deferred
items remain unchanged.

Security checks are run/assessed in WP47.

## WP46 PR Evidence Consistency Guard Helper

WP46 - PR Evidence Consistency Guard Helper is merged
(historical branch: `wp46-pr-evidence-consistency-guard-helper`).
It adds a local/offline/stdlib-only CLI helper at
`tools/git/pr_evidence_consistency_guard.py` that checks PR body and final
comment drafts for consistency before Ready for review: YES.

WP46 adds `tools/git/pr_evidence_consistency_guard.py` as the guard helper,
`tests/tools/git/test_pr_evidence_consistency_guard.py` as focused tests,
and `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md` as the user-facing reference.
It updates `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`,
`docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`,
`docs/ai/codex/VALIDATION_MATRIX.md`,
`docs/ai/codex/WP_EXECUTION_REPORT.md`,
`docs/ai/codex/PR_REVIEW_CHECKLIST.md`,
`docs/work_package_template.md`,
`docs/review_checklist.md`,
`docs/project_status.md`,
`docs/repo_truth_index.md`, and
`docs/deferred_items_log.md`.

WP46 is a local/offline stdlib governance helper WP. It adds no runtime source
under `src/`, no dependency or lock-file changes, no Hermes/LLM/provider
integration, no credentials, no network/account access, no trading or paper
trading, no database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP46 resolves no existing deferred items. WP46 adds WP46-D001 (guard validates
local PR body/final comment drafts only, not live GitHub PR data). All
WP45-forward deferred items remain unchanged.

Security checks are run/assessed in WP46.

## WP45 Codex / Claude PR Evidence Reporting Hardening

WP45 - Codex / Claude PR Evidence Reporting Hardening is merged
(historical branch: `wp45-pr-evidence-reporting-hardening`).
It hardens workflow docs and review guidance so that exact PR evidence reporting
is mandatory for every future Codex / Claude Code work package.

WP45 adds `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` as a new central
workflow reference and updates `AGENTS.md`,
`docs/ai/codex/WP_EXECUTION_REPORT.md`,
`docs/ai/codex/PR_REVIEW_CHECKLIST.md`,
`docs/ai/codex/VALIDATION_MATRIX.md`,
`docs/ai/codex/CONCISE_REPORTING_RULES.md`,
`docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`,
`docs/work_package_template.md`,
`docs/review_checklist.md`,
`docs/repo_truth_index.md`, and
`docs/project_status.md`.
It adds a focused docs test at
`tests/test_pr_evidence_reporting_discipline_docs.py`.

WP45 is docs/test-only. It adds no implementation, helper tooling, workflow
runner, prompt runner, runtime source, tools implementation, dependency or
lock-file changes, LLM/Hermes provider integration, credentials,
network/account access, trading or paper trading,
database/dashboard/scheduler/polling/product behavior, and no generated outputs
committed.

WP45 resolves no existing deferred items. All WP44-forward deferred items remain
unchanged.

Security checks are run/assessed in WP45.

## WP44 Market Research Priority Scoring Layer Design

WP44 - Market Research Priority Scoring Layer Design is merged
(historical branch: `wp44-market-research-priority-scoring-layer-design`).
It adds `docs/market_research_priority_scoring_layer.md` as a docs-only design
for a future local/offline/read-only Market Research Priority Scoring Layer,
updates `docs/repo_truth_index.md` and `docs/deferred_items_log.md`, and adds
a focused docs test at
`tests/test_market_research_priority_scoring_layer_docs.py`.

WP44 is docs/test-only. It adds no implementation, schema, CLI, report writer,
scoring logic, workflow runner, prompt runner, runtime source, tools
implementation, dependency or lock-file changes, LLM/Hermes provider integration,
credentials, network/account access, trading or paper trading,
database/dashboard/scheduler/polling/product behavior, and no generated outputs
committed.

WP44 resolves no existing deferred items. WP44 adds WP44-D001 (Market Research
Priority Scoring implementation not started, OPEN, P3) and WP44-D002 (Score
laundering mitigation not enforced by implementation, OPEN, P3). WP40-D002,
WP41-D002, WP42-D001, WP42-D002, WP28-D001, WP30-D001, WP32-D001, WP34-D001,
WP36-D001, and WP36-D002 remain OPEN.

Security checks are run/assessed in WP44.

## WP40 Local Advisory Consumer Prototype Update

WP40 - Local Advisory Consumer Prototype is merged.
It adds `tools/advisory/local_advisory_consumer.py`,
`docs/local_advisory_consumer_prototype.md`, and focused tests for a
deterministic local/offline/read-only advisory consumer prototype.
Historical WP40 branch status before merge was
LOCAL_OFFLINE_READ_ONLY_ADVISORY_CONSUMER_ON_BRANCH; current WP40 status is
LOCAL_OFFLINE_READ_ONLY_ADVISORY_CONSUMER_MERGED.

The prototype consumes only explicitly provided local files under
`local_data/agent_context_exports/` and `local_data/agent_context_reports/`.
It writes no file by default and may write optional advisory output only under
ignored `local_data/advisory_outputs/`.

The prototype supports text and JSON output, sensitive-like content redaction,
review questions, risk/uncertainty notes, human-review checklist output, and
repo-truth/validation reminders. It is advisory-only and human-review-required.

WP40 adds no runtime source under `src/`, no dependency or lock-file changes,
no Hermes/LLM/provider integration, no credentials, no network/account access,
no trading or paper trading, no database/dashboard/scheduler/polling/product
behavior, and no generated outputs committed.

WP38-D002 and WP39-D001 are resolved only for this deterministic
local/offline/read-only advisory consumer prototype scope. WP39-D002 and
WP40-D001 are resolved by WP41 only for docs-only advisory prompt/runbook
package scope. WP40-D002 remains OPEN for the remaining LLM/Hermes/provider
integration gap.

Security checks were run/assessed in WP40.

## WP43 Repo-Truth Status Reconciliation After WP42 Merge

WP43 - Repo-Truth Status Reconciliation After WP42 Merge is on branch
(`wp43-repo-truth-status-reconciliation-after-wp42-merge`).
It updates `docs/project_status.md` to reflect WP42 merge (commit
6b93576842f862faafbc0b25d54104cd1826e28e) and adds a focused project-status
docs test at `tests/test_project_status_docs.py`.

WP43 is docs/test-only. It adds no implementation, workflow runner, prompt
runner, runtime source, tools implementation, dependency or lock-file changes,
LLM/Hermes provider integration, credentials, network/account access, trading or
paper trading, database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP43 resolves no deferred items. WP40-D002, WP41-D002, WP42-D001, WP42-D002,
WP28-D001, WP30-D001, WP32-D001, WP34-D001, WP36-D001, and WP36-D002 remain
OPEN.

Security checks are run/assessed in WP43.

## WP42 Advisory Consumer Operator Workflow Hardening Update

WP42 - Advisory Consumer Integration Review / Operator Workflow Hardening is
merged (merge commit 6b93576842f862faafbc0b25d54104cd1826e28e).
It adds `docs/advisory_consumer_operator_workflow.md` and focused docs tests
for the end-to-end human-operated advisory workflow.

The workflow connects repo-truth verification, explicit local artifact
selection, freshness/provenance checks, optional WP40 local advisory consumer
use, WP41 manual prompt/runbook use, forbidden-input and forbidden-output
rejection gates, decision logging, and conversion of any accepted observation
into a separate approved WP.

WP42 is docs/test-only. It adds no implementation, workflow runner, prompt
runner, runtime source, tools implementation, dependency or lock-file changes,
LLM/Hermes provider integration, credentials, network/account access, trading or
paper trading, database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP41-D001 is resolved only for docs-only advisory consumer integration review /
operator workflow hardening scope. WP40-D002 and WP41-D002 remain OPEN because
LLM/Hermes/provider integration and provider/Hermes decision refresh are not
designed, selected, or implemented.

Security checks are run/assessed in WP42.

Historical next-WP candidates after WP42 were WP43 - Provider/Hermes Decision Refresh, WP43 - Local Advisory Workflow Follow-Up, and another explicitly approved safe repo-truth WP. WP43 selects the repo-truth status reconciliation path only.

## WP41 Advisory Prompt/Runbook Package Update

WP41 - Advisory Prompt/Runbook Package is merged.
It adds `docs/advisory_prompt_runbook_package.md` and focused docs tests for
human-operated advisory prompt templates and operator review steps.

The package covers read-only market-state analysis, performance review from
local reports/exports, market research question planning, strategy hypothesis
narrative, and Codex / WP planning support. All outputs remain
ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.

WP41 is docs/test-only. It adds no implementation, prompt runner, runtime
source, tools implementation, dependency or lock-file changes, LLM/Hermes
provider integration, credentials, network/account access, trading or paper
trading, database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP39-D002 and WP40-D001 are resolved only for docs-only advisory prompt/runbook
package scope. WP40-D002 remains OPEN because LLM/Hermes/provider integration is
not designed or implemented. WP41 adds WP41-D001 and WP41-D002 for the remaining
advisory consumer workflow-hardening and provider/Hermes decision-refresh gaps.

Security checks are run/assessed in WP41.

Historical next-WP candidates after WP41 were WP42 - Advisory Prompt/Runbook Package Follow-Up, WP42 - Advisory Consumer Integration Review / Operator Workflow Hardening, and WP42 - Provider/Hermes Decision Refresh. WP42 selects the advisory consumer operator workflow hardening path only.

## WP39 Advisory Runtime Boundary And Consumption Design Update

WP39 - Advisory Runtime Boundary And Consumption Design is merged.
It adds `docs/advisory_runtime_boundary_consumption_design.md` and focused
docs tests to define the future local/offline/read-only advisory consumer
boundary and consumption model.
Historical WP39 planning also named WP40 - Advisory Runtime Boundary Design Follow-Up as an alternative follow-up label before the current WP40 prototype was selected.

WP38 - Local Advisory Handoff Package is merged. The previous WP38 alternative
next path, WP39 - Local Advisory Handoff Follow-Up, is historical context only;
WP39 selects the advisory runtime boundary and consumption design path.

The design defines allowed input sources, forbidden input sources, allowed
output types, forbidden output types, deterministic local advisory model,
LLM/Hermes separation, security/sanitization requirements, human-review
requirements, and future WP40 prototype constraints.

WP39 is docs/test-only. It adds no advisory consumer implementation, no runtime
source, no tools implementation, no dependencies, no lock files, no generated
outputs, no Hermes/LLM/provider runtime, no credentials, no network/account
access, no trading, no database/dashboard/scheduler/polling/product behavior,
and no protected-boundary change.

WP38-D001 is resolved only for docs-only design completion. WP38-D002 remains
OPEN because the local advisory consumer prototype is not implemented. WP39
adds WP39-D001 for the unimplemented local advisory consumer prototype and
WP39-D002 for the unimplemented advisory prompt/runbook package.

Security checks were run/assessed in WP39.

## WP37 Token Efficiency Sequence Closeout / Repo Truth Consolidation Update

WP37 - Token Efficiency Sequence Closeout / Repo Truth Consolidation is merged.
It added `docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md` and kept the
post-closeout next-WP gate explicit. Before WP38 was selected, the allowed
candidate paths included WP38 - Local Advisory Handoff Package, WP38 - Token Efficiency Closeout Follow-Up, or another explicitly approved safe repo-truth WP. WP38 selects the local advisory handoff package path only.

## WP33 Code Index / Blast-Radius Helper Design Update

WP33 is a Tier 1 docs-only code-index / blast-radius helper design package. It
creates `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md` and updates
`docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` and
`docs/project_status.md`, plus repo-truth review and testing guidance for the
design.

The design records guidance for a future advisory helper, including
source-of-truth boundary, allowed behavior, disallowed behavior, suggested
inputs/outputs, freshness/staleness rules, protected-boundary handling, future
CLI/JSON shape, future tests, manual-step rule, implementation prerequisites,
stop conditions, and future implementation requirements.

Manual steps for this package: none.

WP33 does not implement a code-index helper, does not create generated index
files, does not reduce validation, and does not implement validation wrappers,
command-running wrapper modes, memory files, runtime behavior, paper/live
behavior, OMS, risk, safe mode, schemas, validators, query-layer code, policy,
scoring, ranking, recommendations, approval, promotion/demotion, readiness,
lifecycle, or downstream authority.

After merge, the next token-efficiency improvement package may be drafted from
refreshed `main`, likely memory/status snapshot design, code-index
implementation, or another approved efficiency package, subject to no stop
trigger and no competing `docs/project_status.md` PR.

## WP34 Code Index / Blast-Radius Helper Implementation Update

WP34 is a local-tooling implementation WP. It implements the advisory helper
designed in WP33 under `tools/git/code_blast_radius.py`, adds focused tests
at `tests/tools/git/test_code_blast_radius.py`, and adds the user-facing
reference at `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER.md`.

The helper is:

- local/offline/read-only;
- standard-library only (no new dependency);
- on-demand scan mode only (no persistent index);
- advisory only (does not replace validation, security checks, or human review);
- no network, no command execution, no file mutation by default;
- optional output restricted to `local_data/code_blast_radius/`.

WP34 resolves WP30-D002 for the tested local/offline/read-only stdlib code-index
/ blast-radius helper scope. WP28-D001, WP30-D001, and WP32-D001 remain OPEN.
WP34 adds WP34-D001 for persistent snapshot/index file mode not implemented.

Security checks were run/assessed in WP34.

Manual steps for this package: none.

## WP36 Memory / Status Snapshot Helper Implementation Update

WP36 is a local-tooling implementation WP. It implements the advisory helper
designed in WP35 under `tools/git/status_snapshot.py`, adds focused tests
at `tests/tools/git/test_status_snapshot.py`, and adds the user-facing
reference at `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md`.

The helper is:

- local/offline/read-only;
- standard-library only (no new dependency);
- no command execution (reads local .git files directly; handles git worktrees);
- advisory only (does not replace repo truth, validation, security checks, or human review);
- no network, no command execution, no file mutation by default;
- optional output restricted to `local_data/status_snapshots/`.

Implemented features: text and JSON output, safe input allowlist, deferred item
digest, helper inventory, next WP candidates, protected boundary status,
staleness metadata, `--check-stale`, `--fail-on-stale`, sensitive redaction,
`--fail-on-sensitive-hit`. Markdown output deferred (exits 2). Input file hashes
deferred.

WP36 resolves WP35-D001 for the tested local/offline/read-only stdlib helper
scope. WP28-D001, WP30-D001, WP32-D001, and WP34-D001 remain OPEN.
WP36 adds WP36-D001 (Markdown output deferred) and WP36-D002 (input file hashes
deferred).

Security checks were run/assessed in WP36.

Manual steps for this package: none.

## WP35 Memory / Status Snapshot Helper Design Update

WP35 is a docs-only design package. It creates
`docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md` and updates
`docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md`,
`docs/ai/codex/README.md`, plus repo-truth and testing guidance for the design.

The design records guidance for a future advisory helper, including design
status, authority model, safe and prohibited input sources, intended future
modes, CLI shape, output structure, sanitization model, staleness model,
snapshot lifecycle and storage policy, relationship to existing helpers, future
implementation test plan, open design questions, and recommended next WP.

WP35 does not implement a memory/status snapshot helper, does not create
generated snapshot output, does not add persistent memory files, does not add
command runners, does not reduce validation, and does not implement network
access, Hermes, LLM, credentials, or trading functionality.

WP35 adds WP35-D001 for memory/status snapshot helper implementation not
started. WP28-D001, WP30-D001, WP32-D001, and WP34-D001 remain OPEN.

Security checks were run/assessed in WP35.

Manual steps for this package: none.

## Open Decisions

- Final live execution language and service boundaries remain undecided.
- Whether future architecture uses the official Python V2 client, TypeScript V2 client, or both behind internal adapters. The Python V2 client is candidate-only and not installed in WP14/WP15/WP16.
- Whether relayer clients are needed; they remain study-only until license and protected-boundary review.
- Whether cross-market/Kalshi work belongs in a later research-only WP.
- VPS or cloud deployment jurisdiction and operational model.
- Dashboard scope for first Streamlit prototype.
- Security tooling setup must run before runtime dependency integration, copied code, vendoring, or live/API execution.
- CLOB /health correct endpoint path unknown (WP9-D001).
- Rate-limit policy not confirmed (WP8-D002).
- Automated, scheduled, or higher-frequency public market-data polling requires a future approved WP with authoritative rate-limit evidence and repo-truth updates.
- AI-agent and Hermes integrations remain advisory-only. WP23 implements a local/offline/read-only context exporter only, WP24 documents safe manual operator use for that exporter, WP25 adds deterministic local/offline/read-only report generation only, and WP26 documents safe manual report-generator operation. Any future runtime selection, provider choice, command approval, network permission, memory policy, or installation requires future human approval and repo-truth work packages.
