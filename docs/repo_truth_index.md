# Repo Truth Index

## S10-LIVE-ORCH-01 Restricted Live Orchestration + First-Live Canary Core (current protected implementation target)

The contract is `docs/live_orchestration_contract.md`; the single new module is
`src/execution_gateway/live_orch.py` over the existing `gate_b.py`, `gate_c.py`, `gateway.py` and
`store.py` boundaries; the EXEC-FEAS repair touches `src/execution_feasibility/models.py`,
`src/execution_feasibility/evaluator.py` and `docs/execution_feasibility_contract.md`; the focused
tests are `tests/execution_gateway/test_live_orch.py` plus `test_gate_b.py`, `test_gate_c.py`,
`test_gateway.py`, `test_store_recovery.py` and
`tests/execution_feasibility/test_execution_feasibility.py`; the certified package is
`docs/wp_specs/S10-LIVE-ORCH-01/` (prompt, spec and independent draftability certificate); and the
stable record is `docs/status_entries/S10-LIVE-ORCH-01.md`. Frozen base
`3f4d9ed91c0e96b9fc19389ac59e01f079caa3fe` (PR #218 / S10-DEPLOY-EXEC-01R3 merged: YES, head
`b1779f5bc6e945eedfa1ba0692a9e1baca779973`). PROTECTED, risk 4, exact 27-path XL scope, independent certificate.
S10-DEPLOY-EXEC-01: MERGED (PR #214; repairs PR #215, #217 and #218). One manual foreground
orchestrator (`preflight` / `canary` / `reconcile`) consumes one exact current
ExploratoryGateCPermit read-only, requires strict execution-host currentness, a fresh geoblock pass,
exact Deposit Wallet identity, fresh bounded account truth (100-item bound), a fresh compatible
public venue snapshot and the frozen USD 100 / 5 / 30 / 70 envelope, persists a durable
LIVE_ORCH_ADMISSION before CREATE_STARTED, transmits at most one BUY CREATE (SELL rejected
SIDE_UNSUPPORTED_FIRST_CANARY) and reconciles partial fills, settlement statuses, cancel ambiguity
(new attempt identity per round, at most three rounds) and restart into a restart-safe
multi-episode ledger inside the existing gateway journal. Unknown CREATE responses are AMBIGUOUS;
the EXEC-FEAS minimum order is two independent dimensions (Gamma USDC notional, CLOB shares).
Dormant capability only: implementation/CI real product network, credentials, account access,
orders and capital are 0; merge does not activate live trading; the first real canary
S10-LIVE-CANARY-01 needs a separate exact-merge Karl authorization. WP175 remains the historical
manual canary path; ALPHA-03 and DATA-03 remain separate and non-blocking; the Control Center
remains separate and non-canonical; live DISABLED; capital/orders USD 0 / 0; merge NOT AUTHORIZED.

## S10-CC-FOUND-01 Control Center Frontend Foundation (merged historical predecessor: PR #223)

FAST, risk 2, exact 20-path L scope (REV A), deterministic readiness, no certificate. Frozen base
`71a83bf1d989b5e0bb8a4feab72132756d1eef15` (PR #221 / S10-LIVE-CANARY-UA-01 merged: YES, head
`c76b6eeb9157ab578c2655701ab9950d1bd474bd`). Foundation only: the five existing read-only cockpit views
in `src/operator_cockpit_frontend/` move onto a Control Center frontend foundation with unchanged
domain semantics: `src/api.ts` (typed DTOs, same-origin `/api`, GET only, closed safe error codes,
`["cc", family]` query keys, one conservative QueryClient with no retry, focus/reconnect refetch or
polling), `src/app.tsx` (shell, React Router declarative routes `/overview`, `/markets`,
`/experiments`, `/paper`, `/audit`, five views, source-owned primitives, active-family manual
refresh), `src/main.tsx`, `src/styles.css` (semantic tokens), `vite.config.ts` (loopback-only `/api`
dev proxy) and Storybook/MSW deterministic reference states (`.storybook/`,
`public/mockServiceWorker.js`, `src/foundation.stories.tsx`). Exact new pins: react-router 8.4.0,
@tanstack/react-query 5.104.0, storybook 10.6.1, @storybook/react-vite 10.6.1, msw 2.15.0 (addon v3
peer requires msw 2.x), msw-storybook-addon 3.0.3. The `cockpit-frontend` CI job adds only
`npm run build-storybook`. `src/operator_cockpit.py` and its 14 GET-only routes are unchanged; the
REV A slot `tests/test_operator_cockpit.py` carries only the two historical frontend-guard updates
(exact dependency dictionaries; `"Overview"` label location). The Control Center remains
presentation only and non-canonical; it is parallel to the live-network lane, which stays separately
blocked on execution-network / geoblock resolution. No realtime, Strategy/Hermes/OPS read model,
protected command, deployment, credential, account, product network, execution or live authority;
live DISABLED; capital/orders USD 0 / 0. Package: `docs/wp_specs/S10-CC-FOUND-01/`; stable record:
`docs/status_entries/S10-CC-FOUND-01.md`. Successor S10-CC-RESEARCH-01 is separately gated; merge
NOT AUTHORIZED (Karl only).

## S10-CC-RESEARCH-01 Control Center StrategyLifecycle + Hermes Research Vertical (merged historical predecessor: PR #224)

FAST, risk 2, exact 15-path L scope (13 issued paths plus Side17-approved amendments A
`tests/test_architecture_boundaries.py` and A2 `tests/test_operator_cockpit.py`), deterministic
readiness, no certificate. Frozen base `780bf84144439ebc6b1b53f468f257d70707014c` (PR #223 /
S10-CC-FOUND-01 merged: YES, head `786d060089c71cc7f26e1b3d543c65011b950b58`). Read-only research
vertical: `src/operator_cockpit_research.py` projects canonical state read only through
`load_strategy_lifecycle_store` and `load_hermes_strategy_manager_store` (no `sqlite3`, open, append,
init, second validator or second context hash); `src/operator_cockpit.py` appends two optional config
fields / CLI flags and exactly four GET routes (`/api/strategies`, `/api/strategies/{strategy_version_id}`,
`/api/hermes/assessments`, `/api/hermes/assessments/{assessment_id}`) beside the unchanged fourteen.
Context status `CURRENT` / `STALE_CONTEXT` / `TARGET_MISSING` is derived only with
`strategy_lifecycle_context_fingerprint` and is display only; the latest assessment comes only from the
verified manager mapping; lineage is exact root-to-target parents; strategy routes stay usable with a
null latest assessment when Hermes is unavailable. The frontend adds `/strategies` and `/hermes`
workspaces with Storybook/MSW states and unchanged conservative Query defaults. Hermes assessments are
soft research judgments, never approval, portfolio, Gate-C, execution or live authority. No Alpha read
model or inferred Alpha linkage (S10-CC-RESEARCH-02 separately gated). Hermes invocations 0; provider
calls 0; strategy/paper mutations 0; dependency/workflow change 0; no credential, account, product
network, execution or live authority; live DISABLED; capital/orders USD 0 / 0. Contract:
`docs/control_center_strategy_hermes_research_contract.md`; package: `docs/wp_specs/S10-CC-RESEARCH-01/`;
stable record: `docs/status_entries/S10-CC-RESEARCH-01.md`. Merged via PR #224 (head
`4dd11f1b35bf49cb14d3e03d257f775926ddf116`, merge `e8fbba6436020d543816e1be3fd45ad9c74dffd7`); its
Alpha exclusion is superseded by S10-CC-RESEARCH-02's verified read-only Alpha projections.

## S10-CC-RESEARCH-02 Control Center Alpha Factory + Evidence / Research Lineage (merged historical predecessor: PR #225)

FAST, risk 2, exact 15-path L scope, deterministic readiness, no certificate. Frozen base
`e8fbba6436020d543816e1be3fd45ad9c74dffd7` (PR #224 / S10-CC-RESEARCH-01 merged: YES, head
`4dd11f1b35bf49cb14d3e03d257f775926ddf116`). Read-only Alpha research projection: the existing
`src/operator_cockpit_research.py` reads Alpha Factory memory only through
`load_and_verify_alpha_factory_registry` and Alpha Discovery evidence only through
`load_and_verify_alpha_discovery_registry` (no `sqlite3`, open, append, init, repair, second validator
or path discovery); `src/operator_cockpit.py` appends two optional config fields / CLI flags and exactly
six GET routes (`/api/alpha/memory`, `/api/alpha/candidates`, `/api/alpha/candidates/{candidate_id}`,
`/api/alpha/episodes/{research_episode_id}`, `/api/alpha/discovery/queue`,
`/api/alpha/discovery/triage/{market_triage_decision_id}`), 24 `/api` routes in total. Candidates follow
registry sequence; lineage, source references and research leaves (several allowed) come from one
verified snapshot; deterministic evidence refs stay opaque. The latest recorded discovery queue is the
greatest registry sequence; the observed universe stays bounded with external completeness `UNPROVEN`;
triage Alpha resolution uses only stored `matched_*` ids under an exact bound-head match (`NOT_BOUND` /
`UNAVAILABLE` / `HEAD_MISMATCH` / `RESOLVED`); the two sources are independent. The frontend adds one
`/alpha` workspace (Research Memory + Discovery Queue) with the `alpha` query family, manual refresh and
Storybook/MSW states. `RESEARCH_SUPPORTIVE` is never qualification, executable edge, profitability or
trading authority; discovery priority is research allocation, never strategy selection or trade priority.
No new persistence, Strategy/Hermes inferred Alpha join, qualification/AF1 history synthesis, Alpha
mutation, Hermes invocation, product network, credential, dependency/workflow change, execution or live
authority; live DISABLED; capital/orders USD 0 / 0. Contract:
`docs/control_center_alpha_research_contract.md`; package: `docs/wp_specs/S10-CC-RESEARCH-02/`; stable
record: `docs/status_entries/S10-CC-RESEARCH-02.md`. Merged via PR #225 (head
`d4075ea344a318897e5cd755eb691a2bd45daa89`, merge `2685429aca6c0b655308a562a693d3075c1994a4`).

## S10-CC-OPS-01 Control Center Portfolio / Risk / Runtime Operations Read Model (merged historical predecessor: PR #226)

FAST, risk 2, exact 16-path L scope, deterministic readiness, no certificate. Frozen base
`2685429aca6c0b655308a562a693d3075c1994a4` (PR #225 / S10-CC-RESEARCH-02 merged: YES, head
`d4075ea344a318897e5cd755eb691a2bd45daa89`). Read-only portfolio-operations projection: the new pure
module `src/operator_cockpit_ops.py` reads StrategyLifecycle only through `load_strategy_lifecycle_store`
and evaluates capacity only through the canonical `evaluate_portfolio_capacity`, called exactly once per
request at one backend `time.time_ns()` value (no `sqlite3`, open, append, init, second validator or
capacity arithmetic; no paper, gateway, LIVE-ORCH, Gate-C, EXEC-FEAS, deployment or network import).
`src/operator_cockpit.py` adds exactly one GET route `/api/ops/portfolio` over the existing
`strategy_lifecycle_path` (25 `/api` routes in total; any query `INVALID_INPUT`; closed
`SOURCE_UNAVAILABLE`). The response carries the exact same-snapshot active policy with all 17 money/count
limits (or `null`), the canonical capacity result (no active policy and canonical rejections are HTTP 200
domain states), budget reservations with window truth, health, the exact per-strategy capacity result and
active restrictions, and fixed non-authority flags. The frontend adds one `/ops` workspace with the `ops`
query family and five OPS-owned keys that compose the existing `/api/paper/summary`, `/api/paper/risk`,
`/api/gateway/status` and `/api/gateway/audit` projections unchanged, with independent source panels,
manual refresh and six Storybook/MSW states. Budget reservations are not actual account exposure; paper
stays `SIMULATED PAPER ONLY` and is never merged with reservation economics; recorded gateway state is
never current account, host or network truth, Gate-C eligibility or live readiness; no incident/alert
registry, EXEC-FEAS/Gate-C history, LIVE-ORCH drill-down, host-currentness or geoblock request. No
StrategyLifecycle, paper or gateway source change or mutation, new persistence, credential, product
network, dependency/workflow change, execution or live authority; live DISABLED; capital/orders USD 0 / 0.
Contract: `docs/control_center_ops_read_model_contract.md`; package: `docs/wp_specs/S10-CC-OPS-01/`;
stable record: `docs/status_entries/S10-CC-OPS-01.md`. Merged via PR #226 (head
`90d30129ce0f3282395b6f319ce25c622191d39b`, merge `7bba7f0d6657364b9358d1a4a96807f024db0533`).

## S10-CC-STREAM-01 Control Center Streaming / Freshness / Gap / Resync Layer (merged historical predecessor)

RUNTIME, risk 3, exact 17-path L scope, deterministic readiness, no certificate. Frozen base
`7bba7f0d6657364b9358d1a4a96807f024db0533` (PR #226 / S10-CC-OPS-01 merged: YES, head
`90d30129ce0f3282395b6f319ce25c622191d39b`). Default-off, request-scoped, same-origin auto-refresh
transport: the new transport-only module `src/operator_cockpit_stream.py` (stdlib only; no canonical
store, filesystem, environment, network-client or WebSocket import; no persistence) and the appended
`CockpitConfig.streaming_enabled` kill switch (exact bool, default `False`, enabled only by the explicit
`--enable-streaming` CLI flag). `src/operator_cockpit.py` adds exactly two GET routes,
`/api/stream/status` (exact transport-only configuration; any query `INVALID_INPUT`) and
`/api/stream/events?family=<QueryFamily>` (one closed family query validated before enablement; valid but
disabled `503 STREAM_DISABLED`; enabled `text/event-stream`), for 27 `/api` routes in total. The only
loop is one SSE wait/emit generator per connected request: a fresh `ccstream:` id, sequence 1 and
`RESYNC_REQUIRED` first, then a 5-second base tick emitting `REFRESH_DUE` at the fixed family cadence
(overview 10, market 5, experiments 30, strategies 30, hermes 30, alpha 30, ops 5, paper 5, audit 10
seconds) or `HEARTBEAT`, with a +1 connection-local sequence and decimal-string `server_time_ns`; it
stops on disconnect or cancellation with no retry, background task, replay buffer or persisted history.
The frontend adds one centralized shell `StreamRefreshController` that owns the only browser stream for
the active family; a new connection id or a same-connection sequence gap resyncs the active family over
HTTP, `RESYNC_REQUIRED`/`REFRESH_DUE` invalidate only `familyKey(activeFamily)`, `HEARTBEAT` invalidates
nothing, malformed events are dropped, and manual Refresh and the conservative Query defaults are
unchanged. Storybook answers `/api/stream/status` with the exact disabled DTO for every story. Transport
state is never domain freshness, source change, market-data gap, account/host/network currentness,
incident state or execution/live authority. No canonical source change or mutation, credential, account
read, product network, dependency/workflow change, command, deployment, execution or live authority;
live DISABLED; capital/orders USD 0 / 0. Contract: `docs/control_center_streaming_contract.md`; package:
`docs/wp_specs/S10-CC-STREAM-01/`; stable record: `docs/status_entries/S10-CC-STREAM-01.md`. Successors
S10-CC-CMD-01 and S10-CC-PROD-01 are separately gated. STREAM-01 merged via PR #227
(head `f344979f8f620519175defe627a5829b569b665d`, merge
`a78809ddb62cf143ac85ee297e87f961aa9b61f9`); no successor merge is authorized.

## S10-CC-CMD-01 Protected Operator Commands (current Control Center implementation target, open branch)

PROTECTED, risk 4, exact 20-path L scope, readiness `IMPLEMENTATION_READY` on the independent
certificate (`docs/wp_specs/S10-CC-CMD-01/draftability_certificate.json`, sha256
`92e9aeab10eacd31d30b4fd856bb9c2845c606905cb692c7e2fb68322f7d7dca`; reviewer-owned). Historical certified base
`a78809ddb62cf143ac85ee297e87f961aa9b61f9` (PR #227 / S10-CC-STREAM-01 merged: YES, head
`f344979f8f620519175defe627a5829b569b665d`). Implementation was explicitly authorized by Side17 for the
exact certified bytes and scope. Default-off protected lifecycle-governance commands: exactly five
canonical StrategyLifecycle commands (`STRATEGY_PAUSE`, `STRATEGY_RESUME`, `STRATEGY_QUARANTINE`,
`POLICY_ACTIVATE`, `POLICY_REVOKE`), each one existing canonical record built through the public builders
by the new module `src/operator_cockpit_commands.py`; the lifecycle record is the durable receipt and no
command database exists. Commands are default-off (`CockpitConfig.command_auth` appended, default `None`;
`--enable-commands --operator-id <id>` on a TTY only) with ephemeral operator auth only: a `getpass`
command secret kept as a SHA-256 digest, at most one in-memory 900 s bearer session stored as a digest,
a five-failure process lock, and no cookie, browser storage or argv/environment/file secret. Loopback
CORS allows exactly `GET`/`POST` and `Content-Type`/`Authorization`. `src/operator_cockpit.py` adds
`GET /api/commands/status`, `POST /api/commands/session`, `POST /api/commands/session/revoke` and
`POST /api/commands/execute` (31 `/api` routes in total). `src/strategy_lifecycle/store.py` adds the
read-only `preview_strategy_lifecycle_record` and the `BEGIN IMMEDIATE`
`conditional_append_strategy_lifecycle_record`, which resolve an exact lost-response retry as
`IDEMPOTENT_REPLAY` before the expected-head comparison and write nothing on a stale head (public append
and schema unchanged). The read-only `/api/ops/portfolio` projection adds the verified `policies`
catalogue. The frontend keeps the bearer token in React memory only, binds every confirmation to a fresh
`/api/ops/portfolio` head, requires the exact confirmation phrase, never auto-retries a mutation and
re-reads the strategies/ops families over HTTP after every outcome; styles and Storybook are unchanged.
Deferred command classes (Side18 decision before S10-CC-PROD-01; no S10-CC-CMD-02 authorized): paper
pause/resume/kill, gateway/runtime disable, incident acknowledgement and Hermes reassessment. No product
network, account, order, Gate-C, LIVE-ORCH, paper, execution, Hermes, dependency/workflow, deployment
or live authority; PROD/private deployment is not complete; live DISABLED; capital/orders USD 0 / 0.
Contract: `docs/control_center_command_contract.md`; package: `docs/wp_specs/S10-CC-CMD-01/`; stable
record: `docs/status_entries/S10-CC-CMD-01.md`. Successor S10-CC-PROD-01 is separately gated; merge NOT
AUTHORIZED (Karl only).

Continuation baseline: `101c7f44604553cf2f8d2166725b266435ab4047` (PR #229 merged).
Side18 owns continuation review; the three certified artifacts remain unchanged.
New-head readiness, independent review and validation belong in PR #228.

## S10-GOV-COPY-01 Unchanged Copy-Origin Exact-Scope Policy (merged governance predecessor: PR #229)

FAST / Risk 1 / M, exact nine paths, frozen base `a78809ddb62cf143ac85ee297e87f961aa9b61f9`.
PR #227 / S10-CC-STREAM-01 is merged (head `f344979f8f620519175defe627a5829b569b665d`).
Side18 adopted the exact frozen prompt/spec; Karl authorized bounded Codex execution after deterministic readiness.
`tools/git/diff_scope_summary.py` excludes unchanged `C` origin provenance only from allowed-file
scope. All copy-origin safety/authority and rename-origin policies remain; independently changed
sources and destinations, unique count, required presence, Git detection/parser and output contracts
remain unchanged. The successor rule in `docs/ai/codex/WP_SPEC_STANDARD.md` supersedes only that
historical WP159 classification; historical WP159 artifacts are untouched. User guide:
`docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER.md`; regressions:
`tests/tools/git/test_diff_scope_summary.py`; package: `docs/wp_specs/S10-GOV-COPY-01/`;
stable record: `docs/status_entries/S10-GOV-COPY-01.md`.
GOV-COPY left PR #228 / CMD-01 separately blocked at `807449e65f6dd1ccacd286e4091c8a3db21b20ef`;
this WP neither changes its source/metadata nor authorizes its baseline migration or recertification.
PR #229 merged by Karl at `101c7f44604553cf2f8d2166725b266435ab4047`
(feature head `1715c53abdabd9dc205be138151e1bd6c22e8b85`). Side18/Karl subsequently
authorized the bounded PROTECTED continuation with unchanged certified artifacts, mechanical
carry-forward gates and separate final implementation review; old-head CI is not new-head evidence. No runtime, dependencies, CI, helper/product network,
credentials, scheduler, paper, execution, trading or live authority; capital/orders USD 0 / 0.
Side18 independently reviews; Karl alone merges. Current evidence/readiness belongs in the PR body.


## S10-CI-SEC-01 Dependency-Security CI Closure (current bounded security closure, open branch)

FAST, risk 2, exact 8-path scope, deterministic readiness, no certificate. Frozen base
`f9a0bae6a69d008862e6466f1fe532bc9416de5d` (PR #220 / S10-CI-OPT-01 merged: YES, head
`d6899e205f0652c7314216016d95cd17e6f01f46`). Security/tooling CI closure only. The cockpit lock
`src/operator_cockpit_frontend/package-lock.json` is patched from `source-map-js` 1.2.1
(GHSA-68fv-2mgg-jv7q) to 1.2.2 with no other lock movement and `package.json` unchanged; that
lockfile is the only `src/**` path and the sole reason for `source_runtime` authority. In
`.github/workflows/ci.yml` exactly `dependency-audit` and `ndfd-grib-dependency-audit` run
`python -m pip_audit --ignore-vuln CVE-2026-104851`; every other finding still fails. The exception
exists only because stable `nautilus_trader==1.231.0` exact-pins `fsspec==2026.2.0`. Removal trigger:
remove the exception when a separately authorized, stable, project-compatible NautilusTrader upgrade
resolves a non-vulnerable `fsspec` (at least 2026.6.0) and that closure passes compatibility,
`pip check`, dependency audit and full validation; a Nautilus prerelease alone is not a removal path.
No Python pin, `pyproject.toml`, forced `fsspec`, runtime/product, credential, network, scheduler,
strategy, paper, execution, live or capital authority. Focused regressions are in
`tests/test_codex_workflow_docs.py`; the package is `docs/wp_specs/S10-CI-SEC-01/` and the stable
record is `docs/status_entries/S10-CI-SEC-01.md`. Successor: PR #221 / S10-LIVE-CANARY-UA-01 is
updated to the new main and gets fresh exact-head CI (separately gated); live DISABLED;
capital/orders USD 0 / 0; merge NOT AUTHORIZED.

## S10-CI-OPT-01 Local-First CI Cost Optimization (workflow-governance review target)

FAST, risk 2, exact 9-path scope, deterministic readiness, no certificate. Frozen base
`7dc323df2aa5820621cc2e6cf89a1d91827ed122` (PR #219 / S10-LIVE-ORCH-01 merged: YES, head
`30a5d70aaf385450cd8a9644773e6ecd25a10b9a`). `.github/workflows/ci.yml` now runs only on
`pull_request` opened / synchronize / reopened / ready_for_review, skips every top-level job while
the pull request is a draft, no longer re-runs the full matrix on push to main, and cancels stale
same-PR runs through `ci-pr-<number>` concurrency. The final hosted matrix is unchanged: the same
nine jobs, OS/Python matrices, audits, strict DuckDB, NDFD strict, focused tests and full pytest.
Canonical local-first guidance lives in `docs/ai/codex/VALIDATION_MATRIX.md` ("Local-First
Validation And Final Hosted CI") and `docs/ai/codex/WP_DRAFTING_STANDARD.md` ("Hosted CI
planning"); focused regression tests are in `tests/test_codex_workflow_docs.py`; the package is
`docs/wp_specs/S10-CI-OPT-01/` and the stable record is `docs/status_entries/S10-CI-OPT-01.md`.
No product source, `tools/`, dependency, credential, product-network, scheduler, strategy, paper,
execution or live authority. S10-LIVE-CANARY-01 remains the separately gated live successor (NOT
AUTHORIZED); live DISABLED; capital/orders USD 0 / 0; merge NOT AUTHORIZED.

## S10-DEPLOY-EXEC-01 Execution-Host Runtime Substrate & Coexistence Proof (merged historical predecessor: PR #214)

PR #214 merged: YES at `fe4e2f1557dec5667d32fa1479f0bfc7ead1c940` (head `9871dddf98565b16194209f032cf8279bfbd34f1`); repairs PR #215, #217 and #218 merged. The text below is the
implementation-time record.

The contract is `docs/execution_host_runtime_contract.md`; the implementation extends the merged
S10-DEPLOY-01 `tools/deployment/` baseline in place (`runtime_baseline.py`,
`bootstrap_ubuntu_24_04.sh`, `README.md`) and adds one unit,
`tools/deployment/systemd/polymarket-execution-critical-probe.service`; the focused tests are
`tests/deployment/test_runtime_baseline.py`; the frozen package is
`docs/wp_specs/S10-DEPLOY-EXEC-01/` (prompt and spec); and the stable record is
`docs/status_entries/S10-DEPLOY-EXEC-01.md`. Base `0392c2d2080a656d8ffd69f42abf8ad91d1f90e2` (PR #213 /
S10-GATE-C-EXPLORE-01 merged: YES, head `342dfeb24652eccb1b6bdf237039b268115b1fb7`). RUNTIME, risk 3, exact 18-path scope.
S10-GATE-C-EXPLORE-01: MERGED. The package adds a sanitized execution-host binding and currentness
contract (pseudonymous pmhost-v1 host id and pmboot-v1 boot id, exact release SHA, release manifest
hash, critical-probe unit hash), one non-economic critical-probe service in the existing
`polymarket-critical.slice` with Restart=on-failure / RestartSec=1s that bootstrap installs but
leaves disabled and inactive, a closed research-versus-critical coexistence evaluator and closed
terminal Phase-B evidence semantics. Execution-capable host substrate only; no `src/` change,
credential, authenticated client, account state, GateCLivePermit, A3 state, signing, order, OMS,
reconciliation, capital or live authority. `docs/research_platform_runtime_baseline_contract.md` and
the research/critical slice values are unchanged. Phase A proves the repository mechanism only; the
real AlphaVPS host proof is a separately authorized Phase B after merge and is NOT PERFORMED. The
AlphaVPS host is purchased/provisioned per Karl (operator-reported, not repository-observed);
project deployment on it is not performed. No automatic upgrade or second host: Karl decides.
S10-LIVE-ORCH-01 is the next core successor after execution-host substrate proof and is NOT
STARTED; ALPHA-03 and DATA-03 remain separate and non-blocking; the Control Center remains separate
and non-canonical; live DISABLED; capital/orders USD 0 / 0; merge NOT AUTHORIZED.

## S10-GATE-C-EXPLORE-01 Exploratory Gate C Policy Permit Core (merged historical predecessor: PR #213)

PR #213 merged: YES at `0392c2d2080a656d8ffd69f42abf8ad91d1f90e2` (head `342dfeb24652eccb1b6bdf237039b268115b1fb7`); formerly the current
protected implementation target. The contract is `docs/exploratory_gate_c_contract.md`; the implementation is the new three-file
stdlib-only source package `src/exploratory_gate_c/` (`__init__.py`, `models.py`, `evaluator.py`);
the focused tests are `tests/exploratory_gate_c/test_exploratory_gate_c.py`; the frozen certified
package is `docs/wp_specs/S10-GATE-C-EXPLORE-01/` (prompt, spec and independent draftability
certificate); and the stable record is `docs/status_entries/S10-GATE-C-EXPLORE-01.md`. Base
`35db4f05347b8b27f7bd0296cf9b1b0627e58d12` (PR #212 / S10-EXEC-FEAS-01 merged: YES, head
`99f3c3c8acc09ae3b5646f785446d69a7b8b2290`). PROTECTED, risk 4, exact 18-path scope. S10-EXEC-FEAS-01: MERGED.
The package is the first V2.1 deterministic exploratory execution-eligibility Gate C: it loads the
existing STRAT-LIFE and Hermes strategy-manager stores only through their verified read-only
loaders and binds the exact StrategyVersion, active global PortfolioAuthorityPolicy, current
EXPLORATORY_LIVE allocation, STRAT-LIFE portfolio capacity, the latest compatible Hermes assessment
and an exactly re-derived FEASIBLE/LIMITED EXEC-FEAS intent/snapshot/assessment into an
ExploratoryGateCDecision and, only when PERMIT_ELIGIBLE, an exact-intent ExploratoryGateCPermit.
Eligibility authority only; no network, account, geoblock, credential, signing, order, persistence
or live authority. The exploratory permit is necessary-but-not-sufficient future evidence, not
live activation; later protected runtime must revalidate account, access, reconciliation and
runtime identity. WP175 remains the separate historical/manual real restricted-live canary and
`src/execution_gateway/` is unchanged; no legacy WP175 Gate-C live permit is issued and no A3
state is entered. S10-DEPLOY-EXEC-01 is the next core successor after review and merge and is NOT
STARTED; S10-LIVE-ORCH-01 is later; S10-CC-OPS-01 may begin only after this package merges, as a
separate package; S10-CC-FOUND-01 is parallel/independent; ALPHA-03 is parallel and non-blocking;
DATA-03 is unchanged and non-blocking; S10-DEPLOY-01 host activation is separate; live DISABLED;
capital/orders USD 0 / 0; merge NOT AUTHORIZED.

## S10-EXEC-FEAS-01 Current Public Execution Feasibility Core (merged historical predecessor: PR #212)

PR #212 merged: YES at `35db4f05347b8b27f7bd0296cf9b1b0627e58d12` (head `99f3c3c8acc09ae3b5646f785446d69a7b8b2290`); formerly the current bounded
implementation target. The contract is `docs/execution_feasibility_contract.md`; the implementation is the new four-file
stdlib-only source package `src/execution_feasibility/` (`__init__.py`, `models.py`,
`public_market.py`, `evaluator.py`); the focused tests are
`tests/execution_feasibility/test_execution_feasibility.py`; the frozen package is
`docs/wp_specs/S10-EXEC-FEAS-01/`; and the stable record is
`docs/status_entries/S10-EXEC-FEAS-01.md`. Base `4519aab3d7f8424fc74c59104cc4e7afe0ff11b8` (PR #211 / S10-HERMES-STRAT-01 merged:
YES, head `9439283768b78b7302290ba6b8611e3477aa3c6a`). RUNTIME, risk 3, exact 17-path scope. The package answers one narrow question:
can this exact proposed execution intent be mechanically supported by currently observable public
Polymarket venue state? It binds one exact StrategyVersion read-only (execution_rule_sha256 derived
from its canonical execution_rule), and produces three immutable content-addressed records:
ExecutionIntent, PublicExecutionVenueSnapshot and ExecutionFeasibilityAssessment (FEASIBLE /
LIMITED / INCONCLUSIVE / NOT_FEASIBLE). Public acquisition is exactly two fixed-host unauthenticated
HTTPS GETs (Gamma `/markets/<id>` and CLOB `/book?token_id=<id>`) with no redirects, no retries and
capped bodies; tests use a fake transport and real external calls during implementation/CI are 0.
Public current mechanics only; no persistence; no account state; no order authority; no Gate-C
authority; no live authority. It is not WP172 executable edge (EXECUTABLE_EDGE_PASS is unchanged)
and makes no profitability claim. S10-STRAT-LIFE-01: MERGED. S10-HERMES-STRAT-01: MERGED.
S10-GATE-C-EXPLORE-01 is the next core package after EXEC-FEAS review and merge and is NOT
AUTHORIZED / NOT STARTED. ALPHA-03 is parallel and non-blocking; DATA-03 is unchanged and
non-blocking; S10-CC-FOUND-01 is a parallel lane not started by this package; S10-DEPLOY-01 host
activation is separate; Gate C is unchanged; live DISABLED; no credentials, scheduler, paper,
execution, live, capital or orders (USD 0 / 0); merge NOT AUTHORIZED.

## S10-HERMES-STRAT-01 Hermes Strategy Manager Core (merged historical predecessor: PR #211)

PR #211 merged this package at `4519aab3d7f8424fc74c59104cc4e7afe0ff11b8` (head `9439283768b78b7302290ba6b8611e3477aa3c6a`). The original package record follows.

The contract is `docs/hermes_strategy_manager_contract.md`; the implementation is
`src/research_runtime/hermes_controlled_runtime/strategy_manager.py` plus an additive default-off
strategy mode in the existing `models.py`, `policy.py` and `controller.py`; the frozen package is
`docs/wp_specs/S10-HERMES-STRAT-01/`; and the stable record is
`docs/status_entries/S10-HERMES-STRAT-01.md`. Base `dab28ee45c1f8267248d52601c90d3f3509034f9` (PR #210 / S10-STRAT-LIFE-01 merged:
YES, head `d3c98d7530c8cec6b65e5d76492f1d7da8edf783`). RUNTIME, risk 3, exact 22-path scope (XL_FOR_SCOPE_ONLY under Scope Amendment
01: two historical Hermes compatibility guards gain exact path exceptions only; authority expansion
NONE). The raw generic controlled Hermes research primitive stays research-only and untrusted; the
new HERMES-STRAT layer turns verified STRAT-LIFE context + bounded evidence + one existing
controlled Hermes run + the strategy-mode output contract + deterministic repository validation
into a canonical soft Hermes strategy decision with strategy-local fingerprint, run-record lineage
and an append-only predecessor chain (manager store application id 1213418801). It never writes the
STRAT-LIFE store, mutates no PortfolioAuthorityPolicy, creates no child StrategyVersion and makes
zero real provider/model calls. S10-STRAT-LIFE-01: MERGED. S10-EXEC-FEAS-01 is the next core package
after HERMES-STRAT review and merge. S10-CC-FOUND-01 is NOT AUTHORIZED / NOT STARTED until
HERMES-STRAT merges; the Control Center remains NOT STARTED. ALPHA-03 is parallel and non-blocking;
DATA-03 is unchanged and non-blocking; S10-DEPLOY-01 host activation is separate; Gate C is
unchanged; live DISABLED; no credentials, scheduler, paper, execution, live, capital or orders
(USD 0 / 0); merge NOT AUTHORIZED.

## S10-STRAT-LIFE-01 Strategy Lifecycle + Global Portfolio Authority Core (merged historical predecessor: PR #210)

PR #210 merged this package at `dab28ee45c1f8267248d52601c90d3f3509034f9` (head `d3c98d7530c8cec6b65e5d76492f1d7da8edf783`). The original package record follows.

V2.1 target architecture: ACCEPTED; the canonical record is the V2.1 section of
`docs/architecture_decision_record.md`. The contract is
`docs/strategy_lifecycle_portfolio_authority_contract.md`; the implementation is the stdlib-only
`src/strategy_lifecycle/` package; the frozen package is `docs/wp_specs/S10-STRAT-LIFE-01/`; and the
stable record is `docs/status_entries/S10-STRAT-LIFE-01.md`. Base
`02eeed13dc0b9552e5685f48198d060e78c797e1` (PR #209 / S10-DEPLOY-01 merged: YES, head
`3e9d595e014275662e90b5f22809f66b3e82cb39`). RUNTIME, risk 3, exact 20-path L scope. It adds
immutable content-addressed strategy family/version identity and lineage, mechanical
bounded-vs-material adaptation classification, advisory evidence posture, strategy health,
strategy-local restrictions, risk allocations, one human-authorized global
PortfolioAuthorityPolicy with activation/revocation receipts, deterministic portfolio
budget/capacity accounting and one append-only hash-chained SQLite lifecycle store (application id
1398033457) derived by verified replay. WP61/WP95/WP154 universal target assumptions are
superseded as future target architecture with history retained. Current runtime is unchanged:
controlled Hermes research mode stays research-only until S10-HERMES-STRAT-01; Gate C,
qualification, WP170, formal WP172 and both WP173 paper modes are unchanged. S10-DEPLOY-01 repo
implementation: MERGED; host activation: NOT YET PERFORMED / separately gated. DATA-03 is unchanged
and non-blocking. ALPHA-03 is separate and parallel, not a known-candidate prerequisite. No network,
credentials, scheduler, Hermes runtime, paper, execution, live, capital or orders (USD 0 / 0);
merge NOT AUTHORIZED.

## S10-DEPLOY-01 Research Platform Runtime Baseline (merged historical predecessor: PR #209)

PR #209 merged this package at `02eeed13dc0b9552e5685f48198d060e78c797e1` (head
`3e9d595e014275662e90b5f22809f66b3e82cb39`); host activation is NOT YET PERFORMED and remains a
separately gated human operator closure. The original package record follows.

The contract is `docs/research_platform_runtime_baseline_contract.md`; the implementation is
under `tools/deployment/`; the frozen package is `docs/wp_specs/S10-DEPLOY-01/`; and the stable
record is `docs/status_entries/S10-DEPLOY-01.md`. Base
`0b14c951c4546ebc28e0d129643da4ad4615ce2e` (PR #208 / S10-PAPER-RESEARCH-01 merged,
head `d5f61c086cbef74010856be88134e04c0e81a06d`). RUNTIME, risk 3, exact 19-path L scope.
The package implements a credential-free tracked-file release builder/verifier, Ubuntu 24.04
x86-64 systemd bootstrap, persistent `/var/lib/polymarket` state, exact research/critical slices,
sanitized once-per-minute host telemetry, SQLite-aware hashed backup, isolated integrity-checked
restore drills, an explicit SSH-port deny-inbound firewall contract, and one bounded post-merge
public WP169 smoke. It adds no dependency, workflow or `src/` change. Provider purchase,
provisioning, remote login and activation are deferred to a separately authorized post-merge
human closure. This zero-capital research baseline may precede DATA-03 and candidate-specific
WP172; a later execution coexistence/hardening proof still requires a real WP172 PASS before
production-hosted serious paper/live. DATA-03 stays unchanged on its current operator environment.
No credentials, authenticated clients, product recurring scheduler, paper session, execution,
Gate C, live trading, capital or orders; merge NOT AUTHORIZED.

## S10-PAPER-RESEARCH-01 Generic Research-Paper + Evidence Loop Bridge (current bounded implementation target)

The contract is `docs/serious_paper_trading_contract.md`; the implementation is the additive
`ResearchPaperStrategyBinding`, `PaperEngine.create_research`, research intent scope enforcement,
`src/research_runtime/paper_performance_bridge.py`, and the finite local `research-init` /
`research-snapshot` CLI commands. The frozen package is
`docs/wp_specs/S10-PAPER-RESEARCH-01/`; the stable evidence record is
`docs/status_entries/S10-PAPER-RESEARCH-01.md`. Base
`d7166f947d764c4fbda65a7d8092d3984a37c7a7` (PR #207 / S10-DEPLOY-PLAN-01 merged,
head `48a4e69e4083b04d88e4e16457e03e713314834d`). RUNTIME, risk 3, exact 21-path XL
scope. Research paper is a non-qualifying learning tier: it reuses WP173 deterministic
simulation machinery but cannot create WP170/WP172 evidence, satisfy Gate C, authorize execution,
or promote live. Legacy qualified WP173 bindings/stores remain compatible without migration.
Snapshots bind the exact verified store event head and state hash, are advisory-only, and may be
adapted through the existing Hermes deterministic-project-evidence builder or referenced opaquely
by existing Alpha `deterministic_evidence_refs`; no provider/model invocation or Alpha registry
mutation occurs. DATA-03 is untouched and remains the separate confirmatory weather lane; the
weather first-look cohort beginning `2026-10-15T00:00:00Z` is not exposed. No candidate-specific
strategy, weather paper, scheduler, dependency/workflow, credential, product network, production
Gate-C, execution or live change; capital/orders 0; merge NOT AUTHORIZED.

## S10-DEPLOY-PLAN-01 Production VPS Hosting Direction Lock (historical planning predecessor)

PR #207 merged this FAST, risk-1, exact 13-path planning package at
`d7166f947d764c4fbda65a7d8092d3984a37c7a7` from base
`d45d9587401faddd2ba92f33cb84f2988b6cfe70` after PR #206. Its frozen package is
`docs/wp_specs/S10-DEPLOY-PLAN-01/` and its stable record is
`docs/status_entries/S10-DEPLOY-PLAN-01.md`. It selected AlphaVPS, Sofia, C8G (4 vCPU / 8 GB
ECC RAM / 75 GB NVMe RAID-10), Ubuntu 24.04 LTS x86-64, and one consolidated future VPS,
superseding the WP61 cheap-VPS shorthand and the open provider decision. Its old serial
WP172-before-deployment timing is superseded by S10-DEPLOY-01: research hosting may begin as a
zero-capital baseline now, while real WP172 PASS still gates later execution coexistence proof.
DATA-03 remains unmoved. The historical package granted no purchase, provisioning, deployment,
credential, scheduler, paper, execution, live, Gate C, capital, or order authority.

## S10-QUAL-DATA-03 Prospective Weather Qualification OOS Accrual + Execution-Terms Capture (merged historical predecessor: PR #206)

PR #206 / S10-QUAL-DATA-03 merged at `d45d9587401faddd2ba92f33cb84f2988b6cfe70` with head
`b7d77f95df093b259a2a2b809ffe20308539e397` at GitHub server merge time `2026-10-01T15:08:12Z`. DATA03 implementation
state remains DATA03_IMPLEMENTED_NOT_STARTED; the Attempt 03 source probe is PROBE_PASS; the next immediate runtime
action is the zero-network DATA-03 prepare, and there is no real accrue before `2026-10-15T00:00:00Z`. DATA-03 remains
on the current operator environment. The historical implementation-target record follows unchanged.

The canonical contract is `docs/qualification_weather_oos_accrual_contract.md`; the pure module is
`src/data_layer/analytical_research/qualification_oos_accrual.py`; the only network owner is the manual operator
`tools/qualification/run_s10_qual_data_03.py` (`prepare`, `probe-sources`, `accrue`, `seal`, `verify-final`); the status
fragment is `docs/status_entries/S10-QUAL-DATA-03.md`; the frozen package is `docs/wp_specs/S10-QUAL-DATA-03/`. Base
`75e17927155dc7ffb5aebfba2f1d97ddd5c2f8b9` (PR #205 / S10-QUAL-PLAN-01 merged, head `11244eed9686b01e29ede83ea6578bb0a781db6f`). RUNTIME, risk 3, exact
15-path scope. It implements the DATA-03 seal frozen by S10-QUAL-PLAN-01 (plan SHA-256
`3b2a99abea8bbd18794c8117d6c1ab696ac817217cd5713367b2ee9a76aa9463`) without analytic change: the frozen 11/12 UTC census (a failed
discovery read never closes the census), PENDING_LABEL_FINALITY without timeout, label-free row ids, the external B0
and q/L sealed as canonical decimal strings, the hash-chained multi-run ledger, the stable chronological 50-date
prefix, the one-way `oosmembership` seal, the closed visible-report firewall, MR12 execution-terms capture from the frozen
fee page and the N2 + 150 <= 256 provenance pre-gate. Code-merge state DATA03_IMPLEMENTED_NOT_STARTED: one bounded
pre-OOS probe only (Source probe: PROBE_PASS on the Attempt 03 full-network recovery probe within the five-host
contract; historical Attempts 01/02 were environment egress denials; S10-QUAL-DATA-03-D007 resolved); no real accrue run before `2026-10-15T00:00:00Z`; no forecast, fit, score, QualificationCandidate,
qualification-gate run or WP170 object; no scheduler or background watcher. PLAN-01, DATA-01/02 code, qualification
contracts, `.github/**` and dependencies are unchanged; WP170/WP172/WP173 remain not started. Live disabled; Gate C is
NOT AUTHORIZED; capital/orders 0; merge NOT AUTHORIZED.

## S10-QUAL-PLAN-01 Weather Qualification Prospective Plan Freeze (merged historical predecessor: PR #205)

PR #205 / S10-QUAL-PLAN-01 merged at `75e17927155dc7ffb5aebfba2f1d97ddd5c2f8b9` with head `11244eed9686b01e29ede83ea6578bb0a781db6f` at GitHub server
merge time `2026-10-01T02:39:26Z`, before the freeze deadline (freeze valid); its frozen plan is bound unchanged by
S10-QUAL-DATA-03. The historical implementation-target record follows unchanged.

The canonical contract is `docs/qualification_weather_plan_freeze_contract.md`; the frozen plan is
`docs/qualification_plans/S10-QUAL-PLAN-01/weather_plan_v1.json` (plan SHA-256
`3b2a99abea8bbd18794c8117d6c1ab696ac817217cd5713367b2ee9a76aa9463`, sha256 of the exact bytes); the power analysis is
`docs/qualification_plans/S10-QUAL-PLAN-01/power_analysis_v1.md`; the status fragment is
`docs/status_entries/S10-QUAL-PLAN-01.md`; the frozen package is `docs/wp_specs/S10-QUAL-PLAN-01/`. Base
`e2edb21e25e7841376c3cb51c27a622fbc0cbc83` (PR #204 / S10-QUAL-B0X-01 merged, head
`debcfdf723505b67a1280ac9f303d5abd293c998`). FAST, risk 2, exact 13-path docs/tests scope. It is an analytic-plan
freeze only: oos_start `2026-10-15T00:00:00Z`, freeze deadline `2026-10-14T00:00:00Z` judged by the GitHub server
merge timestamp plus merge SHA (a later merge is OOS_START_FREEZE_WINDOW_MISSED), cap `2027-02-12T00:00:00Z`;
DATA-02 dates are permanently HISTORICAL_NON_OOS. It freezes the hypothesis, the external B0, the B1/B2 features, the
label, the Firth logistic model and solver, the splits and floors, the power plan (50 target dates), the fixed-sequence
Brier family, the DATA-03 seal/exposure rules, the execution-evidence meaning and the WP170 handoff; every
data-dependent candidate field is a closed mechanical rule (MR01-MR15). WP170 remains the sole preregistration/OOS
authority: no PreregisteredExperiment, lifecycle record, QualificationCandidate or qualification-gate receipt is
created, no data is accessed and no model is fitted or scored. `src/**`, `tools/**`, `.github/**` and dependencies are
unchanged; WP170/WP172/WP173 remain not started. S10-QUAL-DATA-03 is the next expected package only after this WP
merges at or before the freeze deadline (separately gated). Live disabled; Gate C is NOT AUTHORIZED; capital/orders 0;
merge NOT AUTHORIZED.

## S10-QUAL-B0X-01 External-Reconstruction B0 Qualification Contract Extension (merged historical predecessor: PR #204)

PR #204 / S10-QUAL-B0X-01 merged at `e2edb21e25e7841376c3cb51c27a622fbc0cbc83` with head
`debcfdf723505b67a1280ac9f303d5abd293c998`; its external B0 rule is bound unchanged by the S10-QUAL-PLAN-01 plan.
The historical implementation-target record follows unchanged.

The canonical contract is `docs/qualification_candidate_contract.md` (section 8); the source is
`src/data_layer/analytical_research/qualification.py`; the status fragment is `docs/status_entries/S10-QUAL-B0X-01.md`;
the frozen package is `docs/wp_specs/S10-QUAL-B0X-01/`. Base `ebd6f84c95e30451fe1c9ad431e405c57c113074` (PR #203 /
S10-QUAL-DATA-02 merged, head `b9e2e6995ee232720d0516b1fa234dec8bdac5e3`). FAST, risk 2, exact 14-path scope (size
class L in the machine spec: the drafted S class exceeds the guard's S<=5 limit; M<=10 also cannot cover the
frozen 14-path scope, so L<=20 is the smallest valid size class; scope, FAST track, risk and authority are
unchanged). It adds exactly one
external-reconstruction B0 rule `EXTERNAL_PIT_MARKET_PROBABILITY_V1` and exactly one feature source class
`MARKET_EXTERNAL_RECONSTRUCTION`; canonical `PIT_MARKET_PROBABILITY_V1` / `MARKET_PIT` are unchanged. B2 market-added
refs must carry the B0 rule's own class (canonical -> MARKET_PIT, external -> MARKET_EXTERNAL_RECONSTRUCTION; mixed
rejects); both market classes reject in B1; parameters and fallback mechanics are identical. The external rule is a
third-party reconstruction observed by capture `timestamp_received`; archive Last-Modified / public_available_time
never backdates availability, and external evidence is never MARKET_PIT, SOURCE_KIND_CANONICAL_PIT, a
DatasetSnapshotReference or local-first-seen evidence (no import bridge). QUALIFICATION_SCHEMA_VERSION stays 1.0.0
and canonical candidate ids are unchanged. `qualification_gate.py`, `__init__.py`, the DATA-02 sources/operators
and WP170 are unchanged. It resolves S10-QUAL-DATA-01-D001. No network or data acquisition; no real
QualificationCandidate is created and no qualification gate is run; WP170/WP172/WP173 remain not started.
S10-QUAL-REAL-01 is the next expected package only after this WP merges (separately gated). Live disabled; Gate C is
NOT AUTHORIZED; capital/orders 0; merge NOT AUTHORIZED.

## S10-QUAL-DATA-02 Weather Qualification Corpus Completion (merged historical predecessor: PR #203)

PR #203 / S10-QUAL-DATA-02 merged at `ebd6f84c95e30451fe1c9ad431e405c57c113074` with head `b9e2e6995ee232720d0516b1fa234dec8bdac5e3`; its sealed
QUAL_DATA_READY corpus is unchanged and stays never canonical PIT; its B0 compatibility status is answered by
S10-QUAL-B0X-01. The historical implementation-target record follows unchanged.

The canonical contract is `docs/qualification_weather_corpus_completion_contract.md`; the operator is
`tools/qualification/run_s10_qual_data_02.py`; the status fragment is `docs/status_entries/S10-QUAL-DATA-02.md`;
the frozen package is `docs/wp_specs/S10-QUAL-DATA-02/`. Base `6f67bac990d8ab338f1b87140ae077e9df4172dd` (PR #202 / S10-QUAL-DATA-01
merged, head `33c031f41626550294eb6667620b4ce75589d719`). RUNTIME, risk 3, exact 15-path scope; no dependency, workflow,
qualification, gate, provenance or public-client change; `run_s10_qual_data_01.py`, `pendulumflow_v3.py` and
`nws_ndfd_history.py` unchanged; the only core change is the additive market-exclusion code
LABEL_V3_SOURCE_READ_FAILED. The completion operator is the only network owner (https GET/HEAD/Range to the
four S10-QUAL-DATA-01 hosts; frozen 429/503 backoff; new-network caps 12,288 attempts / 6 GiB). It completes the
frozen S10-QUAL-DATA-01 corpus from the verified PR #202 run-01 seed: failed seed entries are never admitted,
only hash-valid successful raw artifacts are used as a cache and the whole corpus is re-derived with the D011
failed-read rules. PendulumFlow v3 stays THIRD_PARTY_NATIVE_FRAME_ARCHIVE and never canonical PIT;
b0_contract_compatibility stays EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION. The terminal is
QUAL_DATA_READY or QUAL_DATA_INSUFFICIENT; the single completion run terminated QUAL_DATA_READY (bundle
`weatherqualbundle:sha256:a5911ab05cc8c650377447aa46f65f3b2002fc458e3c51a64f8705b1adcc69ae`, logical dataset
`weatherqualdataset:sha256:a3e98a35ea052e1dfeb5225239a74beaee47d04111ebb34e6d27717490d9ac39`; 783 evidence-complete rows over 32 target dates;
verify-final VERIFIED with zero network). No QualificationCandidate is created and no qualification gate is
run; WP170/WP172/WP173 remain not started. Live disabled; Gate C is NOT AUTHORIZED; capital/orders 0; merge NOT
AUTHORIZED.

## S10-QUAL-DATA-01 Weather Qualification Data Readiness (merged historical predecessor: PR #202)

PR #202 / S10-QUAL-DATA-01 merged at `6f67bac990d8ab338f1b87140ae077e9df4172dd` with head `33c031f41626550294eb6667620b4ce75589d719`; its QUAL_DATA_INSUFFICIENT run-01 is
the verified seed of S10-QUAL-DATA-02 (D011/D012 dispositioned there). The historical implementation-target record
follows unchanged.

The canonical contract is `docs/qualification_weather_data_readiness_contract.md`; the operator is
`tools/qualification/run_s10_qual_data_01.py`; the status fragment is `docs/status_entries/S10-QUAL-DATA-01.md`;
the frozen package is `docs/wp_specs/S10-QUAL-DATA-01/`. Base `77738717fee422fe83d8bb2b7765c36dfbe6b283`
(PR #201 / S10-NDFD-GRIB-01 merged, head `cd70800d40f60f4ec20f5b17e107cc56643562a2`). RUNTIME, risk 3, exact
20-path scope; no dependency, workflow, qualification, gate, provenance or public-client change. Offline
modules `src/data_layer/analytical_research/pendulumflow_v3.py`, `nws_ndfd_history.py` and
`qualification_data_readiness.py` make zero network calls; the foreground operator is the only network owner
(https GET/HEAD/Range to archive.pendulumflow.com, noaa-ndfd-pds.s3.amazonaws.com, gamma-api.polymarket.com via
the existing public client, api.weather.gov; frozen budgets). S10-QUAL-DATA-01 is data formation/readiness
only for the PR #200 RESEARCH_SUPPORTIVE daily-rain lineage: target dates 2026-08-18..2026-09-26,
checkpoints MARKET_OBSERVABLE_PLUS_60M_V1 and TARGET_CLIMATE_DAY_START_V1, 24 h market-history and 48 h NDFD
lookbacks. PendulumFlow v3 is THIRD_PARTY_NATIVE_FRAME_ARCHIVE / EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION and
never canonical PIT; b0_contract_compatibility is EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION unless
canonical PIT is independently bound. The terminal is QUAL_DATA_READY or QUAL_DATA_INSUFFICIENT; the authoritative
replacement run terminated QUAL_DATA_INSUFFICIENT (FROZEN_BUDGET_EXHAUSTED; bundle `weatherqualbundle:sha256:ceca0252b4d41cf9b49591bb3a65ed9e0b79d9321b269ecbab86f5a90ea085e1`, logical dataset
`weatherqualdataset:sha256:9058a05354390ca7e61bcb47871f93b925e99571f7cc48f40b057eb0e8454413`; 212 evidence-complete rows over 12 target dates; verify-final VERIFIED with zero network).
The earlier QUAL_DATA_READY run is retained as SUPERSEDED_DEFECTIVE_RUN_D008_D009 evidence (rule-parser coverage
defect S10-QUAL-DATA-01-D008, truncated manifests D009); see the status fragment. No QualificationCandidate is created and no qualification gate
is run; WP170/WP172/WP173 remain not started. Live disabled; Gate C is NOT AUTHORIZED; capital/orders 0;
merge NOT AUTHORIZED.

## S10-NDFD-GRIB-01 NDFD GRIB2 Decoder Dependency Enablement (merged historical predecessor: PR #201)

PR #201 / S10-NDFD-GRIB-01 merged at `77738717fee422fe83d8bb2b7765c36dfbe6b283` with head
`cd70800d40f60f4ec20f5b17e107cc56643562a2`; the optional ndfd-grib decoder capability is retained and consumed
unchanged by S10-QUAL-DATA-01. The historical implementation-target record follows unchanged.

The canonical contract is `docs/ndfd_grib_decoder_dependency_contract.md`; the status fragment is
`docs/status_entries/S10-NDFD-GRIB-01.md`; the frozen package is `docs/wp_specs/S10-NDFD-GRIB-01/`.
Base `3d3e3b673e53dae4d2e3b28a6816264b205bb015` (PR #200 / S10-ALPHA-REAL-01 merged, head
`80faf1dcb32d760a15c5de3c008cd2aefa3a6f12`). RUNTIME, risk 3, exact 19-path scope, no src/ change. It
resolves only the S10-QUAL-DATA-01 `NDFD_DEPENDENCY_REQUIRED` decoder blocker. S10-NDFD-GRIB-01 enables
optional offline NDFD GRIB2 decoding only: one optional `pyproject.toml` extra `ndfd-grib` with exact
pins `eccodes==2.48.0` (Python 3.12) and `eccodeslib==2.48.0.26` (non-Windows Python 3.12), binary
wheels only, no source build, no vendored decoder and no lock file. `requires-python` (>=3.12,<3.15),
the six base pins and the test/cockpit extras are unchanged; global Python support remains 3.12-3.14.
The NDFD decoder capability is proven only on ubuntu-24.04 / windows-2022 Python 3.12 (dedicated hosted
`ndfd-grib-compat` jobs plus `ndfd-grib-dependency-audit` pip-audit); Python 3.13/3.14, macOS and ARM
are not claimed. The committed official fixture `tests/fixtures/ndfd_grib/ndfd_pop12_reference.grib2`
(first GRIB2 message of `noaa-ndfd-pds` `wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031046`, SHA-256
`ecdac869039c2342f8a8ff8c57aa4fef602728e3257d0de7af5c091047c719ea`; templates 3.30/4.9/5.3) is a
compatibility oracle only and not canonical research evidence; frozen decode fingerprint
`0b5e478b2fff21519adbe12a993f0f3106f449343640f0fb521e4e8f792653ec`. No product/runtime network. S10-QUAL-DATA-01
may be redrafted/resumed next; S10-QUAL-DATA-01 itself remains unimplemented by this WP. No
QualificationCandidate exists yet and no real qualification gate receipt exists yet; WP170/WP172/WP173
remain not started for this weather candidate. Live disabled; Gate C is NOT AUTHORIZED; capital/orders
0; merge NOT AUTHORIZED.

## S10-ALPHA-REAL-01 First Real Non-Wallet Alpha Evidence Seed (merged historical predecessor: PR #200)

PR #200 / S10-ALPHA-REAL-01 merged at `3d3e3b673e53dae4d2e3b28a6816264b205bb015` with head
`80faf1dcb32d760a15c5de3c008cd2aefa3a6f12`; the RESEARCH_SUPPORTIVE non-wallet Alpha seed is retained.
The historical implementation-target record follows unchanged.

The canonical contract is `docs/alpha_real_non_wallet_seed_contract.md`; the operator is
`tools/alpha/run_s10_alpha_real_01.py`; the status fragment is `docs/status_entries/S10-ALPHA-REAL-01.md`;
the frozen package is `docs/wp_specs/S10-ALPHA-REAL-01/`. Base `f74e183a514d21a28013bf433c79126a68c72389`
(PR #199 / S10-TEST-WS-01 merged, head `99c300421f3404a68b573674d1d6d09e8c363412`). RUNTIME, risk 3, exact
12-path scope, no src/ change. The manual foreground operator (prepare, verify-local, run-real, verify-run,
build-review-bundle, verify-review, finalize-alpha, verify-final) targets the frozen NWS-resolved Polymarket
daily-rain research program. After Karl's separate runtime activation it performs at most one controlled
Hermes v0.21.3 research-child launch through the merged `run_controlled_hermes_research` (context mode off),
recaptures and revalidates the full research draft tool-side, takes one Side13 result-state decision and
appends exactly one non-wallet Alpha source/candidate/family/episode lineage to a dedicated ignored
registry with an exact record-set idempotency check. Post-runtime verified result (attempt-01, consumed,
exactly one research-child launch at Phase-A head `4db1cb8e4ffa9cb6122f064faab82d379c74ad44`, envelope
`eee8003c216cfd892f54666c030520ec2b8920d20a52d222401e3e7f48c24af0`): receipt
`hermesresearchreceipt:sha256:69037db6d6df59283da89110998ef17d2854c73c29052039b20acb89ac6cbd0f`,
projection SHA-256 `d23f304d57eef4d6dc05ee73afe98227d15dbc5a4334aa630569084b17b78064`, review bundle
SHA-256 `14ec89f6760d3d2ae0b2c4751ddc8ec647d1e65b2350735d1b5810e622478be6`, Side13 decision
RESEARCH_SUPPORTIVE, final terminal ALPHA_REAL_01_SUPPORTIVE; 12 usable sources, candidate
`alphacandidate:sha256:2d1523c8086acf536ad07512e1eaffed9cb9405b65e83c87b89b40ba77ee3add`, family
`alphafamily:sha256:136000bd56f2fc27cf490cf675ddf2715b0acfc1ee934aa5cdf2579925c208d8`, episode
`alphaepisode:sha256:2e4c0f484649930ba2677bc360070f0e9ba6ef0e09ecd23b383a32ff3b69000c`; dedicated ignored
registry 15 rows, head `alpharegistryentry:sha256:4b9a20f7f0e931dfea7cced80a64d7a4be7ccc58e265dbb9ebde15edb2d79847`;
protected AF1/H1 evidence unchanged. RESEARCH_SUPPORTIVE is not qualification, OOS success, executable edge,
profitability, paper, live or Gate C authority, and is not a claim that weather information beats market
probability; qualification/data readiness is NOT proven. S10-QUAL-REAL-01 is NOT AUTHORIZED; it is now
DRAFT-ELIGIBLE only (verified unique current RESEARCH_SUPPORTIVE leaf) and must independently establish real
dataset refs, PIT provenance, sample/power, a B0/B1/B2 or generic metric plan, critical execution evidence and
exact AF1 binding. No QualificationCandidate was created and no qualification gate was run. QualificationCandidate construction, S10-GATE-QUAL-01 evaluation, WP170/WP172/WP173,
wallet evidence, H1 #5 and Gate C are NOT AUTHORIZED; capital/orders 0; merge NOT AUTHORIZED.

## S10-TEST-WS-01 Deterministic Reconnect Synchronization in Market WebSocket Tests (merged historical predecessor: PR #199)

PR #199 / S10-TEST-WS-01 merged at `f74e183a514d21a28013bf433c79126a68c72389` with head
`99c300421f3404a68b573674d1d6d09e8c363412`; the tests-only reconnect synchronization repair is retained.
The historical implementation-target record follows unchanged.

The status fragment is `docs/status_entries/S10-TEST-WS-01.md`; the package is
`docs/wp_specs/S10-TEST-WS-01/`. Base `d7891ed63b4c58c9cc150cd0c750c262ca8e5a74` (PR #198 /
S10-GATE-QUAL-01 merged, head `ec97a25b3e3174bfa71e3799110e729247dfa026`). FAST, risk 1, exact 8-path
scope, tests-only. The four WP169 reconnect tests in
`tests/data_layer/polymarket/test_market_truth_websocket.py` no longer infer completion of the real 1s
reconnect backoff from fixed wall-clock sleeps; they await the observable condition itself (reconnect
subscription payload emitted on the second connection, HEALED gap evidence persisted, bounded socket #2
open events), each bounded by a finite 30s timeout that stops the runner and fails clearly. The product
backoff is exercised unchanged: no src/ change, no `_BACKOFF_SCHEDULE` change, no injection API, no
dependency or workflow change. Strategy, paper, execution, live and Gate C remain NOT AUTHORIZED;
capital/orders 0; merge NOT AUTHORIZED.

## S10-GATE-QUAL-01 Deterministic Qualification Packet Acceptance Gate (merged historical predecessor: PR #198)

PR #198 / S10-GATE-QUAL-01 merged at `d7891ed63b4c58c9cc150cd0c750c262ca8e5a74` with head
`ec97a25b3e3174bfa71e3799110e729247dfa026`; the gate remains the deterministic qualification acceptance
gate. The historical implementation-target record follows unchanged.

The canonical contract is `docs/qualification_gate_contract.md`; the single module is
`src/data_layer/analytical_research/qualification_gate.py`; the status fragment is
`docs/status_entries/S10-GATE-QUAL-01.md`. Base `b5cfb9846ff78af2d1a260843d5f2f1a67639305` (PR #197 /
S10-QUAL-01 merged, head `652a2181926ac6f92f72d0013af99ec5e24ba892`). FAST, risk 2, exact 15-path
scope. The gate re-validates an existing NON-WALLET QualificationCandidate, re-proves the supplied
Alpha snapshot against the registry hash chain, accepts a candidate-bound Alpha head that is an
append-only ancestor of (or equal to) the current head, re-binds the exact AF1 receipt and exact
provenance manifest set, and evaluates eight closed dimensions into one content-addressed
QualificationGateReceipt with QUAL_PASS / QUAL_FAIL / QUAL_INCONCLUSIVE (FAIL precedence;
wp170_entry_eligible iff QUAL_PASS). Structural rejections return no receipt and are never
relabelled QUAL_FAIL or QUAL_INCONCLUSIVE. QUAL_PASS is qualification-only and never predictive edge,
OOS success, executable edge, profitability, paper, live or Gate C authority. Current WP170 B1
public-non-market FeatureDefinition capability is not claimed; qualification.py, experiment_os.py
and experiment_registry.py are unchanged. No real candidate was created or evaluated and no real
QualificationGateReceipt exists or is persisted; synthetic outcomes are test fixtures only. First
real candidate/evaluation, WP170 experiment/OOS, wallet qualification, H1 #5 and Gate C are NOT
AUTHORIZED; WP172/WP173 are NOT STARTED; capital/orders 0; merge NOT AUTHORIZED.

## S10-QUAL-01 Deterministic Qualification Candidate Packet (merged historical predecessor: PR #197)

PR #197 / S10-QUAL-01 merged at `b5cfb9846ff78af2d1a260843d5f2f1a67639305` with head
`652a2181926ac6f92f72d0013af99ec5e24ba892`; the packet remains the non-qualifying substrate. The
historical implementation-target record follows unchanged.

The canonical contract is `docs/qualification_candidate_contract.md`; the single module is
`src/data_layer/analytical_research/qualification.py`; the status fragment is
`docs/status_entries/S10-QUAL-01.md`. Base `3b877a01ed797d26fddf81a8936c880692573028` (PR #196 /
S10-GATE-AF1 merged, head `d456dafc407d7b079b642fc34cd10781690eb8b0`). FAST, risk 2, exact
15-path scope. S10-QUAL-01 implements the deterministic NON-WALLET QualificationCandidate
substrate: one immutable content-addressed advisory packet binding a unique current
RESEARCH_SUPPORTIVE Alpha lineage leaf, an AF1_PASS receipt with all ten dimensions PASS,
verified ResearchProvenanceManifest ids and cutoffs, frozen hypothesis / feature / label /
dataset-split / sample-power / test-family plans, the B0/B1/B2 forecast-evaluation interface
and execution-feasibility evidence availability. It adds no registry, file writer, operator,
provenance family, Alpha memory or gate receipt. S10-QUAL-01 itself produces NO qualification
PASS/FAIL/INCONCLUSIVE decision and no real candidate is qualified by it. AF1_PASS remains
research-system gate success only. Qualification feature refs are logical refs; the current
WP170 FeatureDefinition surface is not claimed to support B1 public-non-market inputs, and
feature/model implementation remains WP170. WP170 remains the preregistration/OOS authority.
Wallet-dependent packets fail WALLET_GATE_REQUIRED until S10-WALLET-03 / S10-WALLET-04 /
S10-GATE-WALLET-01 exist. Next and separately gated: S10-GATE-QUAL-01. S10-GATE-QUAL-01,
wallet qualification, H1 #5 and Gate C are NOT AUTHORIZED; WP170 experiment/OOS and WP172/WP173
are NOT STARTED; capital/orders 0; merge NOT AUTHORIZED.

## S10-GATE-AF1 research-system gate (finalized: AF1_PASS; Attempt-04 CONSUMED)

The canonical contract is `docs/alpha_factory_research_system_gate_contract.md`;
records are in `src/data_layer/analytical_research/alpha_factory_gate.py`; the sole
manual runtime boundary is `tools/alpha/run_s10_gate_af1.py`. Local-evidence defect
correction 01 preserves historical commit `af07264a` while invalidating its attempted
runtime evidence and envelope `0f7a2680...`. The historical `current` workspace is
quarantined. The corrected contract uses only `retry_limit=0`, creates an exclusive
pre-call population sentinel, immediately persists the complete typed coordinator
result, and binds `public_population_result_sha256` into canonical manifest/receipt
identity. No new population or provider call, H1 #5, successor, merge, or trading
authority is granted. A later attempt requires a new explicit authorization bound to
a fresh Phase-A commit, fresh digests, and a fresh workspace.

Post-WP164A reconciliation rebases the AF1 package onto `70f867bdcd5e97b0dc05d4008c2c023feb461658`
with immediate predecessor PR #193 (runtime-certified head
`1c7de22f31cd093771d6bc0748c440ad5284b105`). It freezes the complete 38-field WP164A population
result, success on actual returned counts rather than request limits, retained
`EVENT_TIME_MISSING_ALLOWED` warnings, fresh-status `POPULATION_ALREADY_REGISTERED` rejection, one
canonical `captured_at_utc` cutoff, the HISTORICAL_REPLAY Alpha posture, the selected
`question_text` coverage precondition, and an absolute `ContextArtifactStore` root. At that
recertification AF1 Attempt-03 was not yet authorized (historical expected stop
`AF1_RUNTIME_AUTHORIZATION_REQUIRED`).

Post-S10-HERMES-CTX-02 reconciliation replays the AF1 package onto `15097f70f5f5358879fde73b2b30d26ecdb80402` (PR #194, head
`f6b337ce1d4581516c3d10d792034f00043a8a74`). The shared research-home check now admits only the exact pinned stock SOUL.md;
AF1 semantics, the 38-key envelope and the pre-sentinel Hermes preflight are unchanged; AF1
Attempt-03 was then authorized and executed on Phase-A head `777b33d5e3eb3ae6814716f45f3dc6a8a673ed16`.

Post-S10-HERMES-CTX-03 reconciliation replays the AF1 package onto
`1ccf42df0e95586b98c79a0bf912343f9c34df31` (PR #195, head
`ddc25d189359b6e365edcf08c762cb0552b7170a`). AF1 Attempt-03 is permanently CONSUMED: TRUE_STOP /
`PHASE_B_LOCAL_EVIDENCE_DEFECT`, AF1 gate result NONE (never AF1 PASS, FAIL or INCONCLUSIVE); its one
public population succeeded (25/1, built 26, inserted 26, result SHA-256
`fcf5a085aef0954f91812f53231405b9746e583886ea950ca2cd91bc0cf9dc8e`) and the C1 request failed in the
shared secret scanner before any Hermes launch (provider/model/Firecrawl calls 0, cost USD 0). PR #195
repaired that shared root cause. AF1 adds a live-shaped cross-layer regression (canonical
`market:polymarket:<decimal>`, `event:polymarket:0x<64 lowercase hex>` and canonical CLOB token id
refs (polymarket token namespace + ~77-digit decimal) reach the offline fake Hermes backend through
`run_blind_phase`).
The successor runtime instance is AF1 Attempt-04 (`s10-gate-af1-attempt-04`): the operator rejects
`attempt-01`..`attempt-03` and admits only `attempt-04`, with no automatic increment; Attempt-04
uses a fresh bounded 25/1 population into new empty stores and never reuses Attempt-03 stores.
The 38-key envelope, gate criteria, limits, `retry_limit=0`, budgets and authority are unchanged.
At that refreeze Attempt-04 was not yet authorized (historical Phase-A stop for Attempt-04).

Final truth: AF1 Attempt-04 ran on runtime execution head `dead42658e8fc9139d82f772e1f2fff67ba07674` and is CONSUMED. Its one
public population succeeded (25 markets / 1 book actual, built 26, inserted 26,
`VALID_WITH_WARNINGS` with `EVENT_TIME_MISSING_ALLOWED`, result SHA-256 `9adb1b68420afbd15172a92dca57aec2feffc6b39df82753d97ae15b311534cc`, cutoff
`2026-09-28T01:54:02.507161Z`); all three cases reached `RESEARCH_DRAFT_VALIDATED` (3 controller invocations, no
retry/replacement/fallback/fourth call; openai-codex / gpt-5.6-sol; receipt-reported accepted cost
USD 0.0 per case; backend telemetry NOT_DIRECTLY_ATTESTED; Firecrawl count UNKNOWN). The independent
Side12 blind review (decision SHA-256 `eba65849219faf65f27849a6b5be0fe1c1cf27e0cc47bb3ada084afb77d99bc3`, bundle SHA-256 `12058c282bd24d332bb767b7a75c201e4f0b9fcbdebdf0f7cb09c07672a8e74f`) labelled all three
`USEFUL_RESEARCH_OUTPUT`. Deterministic finalization produced `AF1_PASS` with all ten dimensions
PASS and receipt `af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2`; the byte-identical committed evidence is
`docs/gate_evidence/S10-GATE-AF1/af1_gate_evidence.json`. AF1_PASS is research-system gate success
only: it proves no profitability, expected return, qualification, OOS validity, executable edge,
paper/live readiness or Gate C. Non-wallet S10-QUAL-01 is now separately eligible to be drafted and
authorized; wallet-specific and ALPHA-03/HERMES-SI paths stay separately gated; none is authorized.
The post-runtime publication head differs from the runtime execution head only by the explicit
Side13/Karl lifecycle-test recovery amendment (three AF1 lifecycle/status tests plus the six
evidence/status docs). No additional AF1 attempt, H1 #5, Gate C, capital, orders or merge is authorized.

## S10-HERMES-CTX-03 Canonical Public Polymarket Identifier Secret-Scanner Compatibility Repair (current bounded compatibility repair)

The canonical package is `docs/wp_specs/S10-HERMES-CTX-03/`; the stable fragment is
`docs/status_entries/S10-HERMES-CTX-03.md`. The frozen base is PR #194's merge commit
`15097f70f5f5358879fde73b2b30d26ecdb80402`. The shared runtime surface is
`src/research_runtime/hermes_controlled_runtime/models.py` (`build_research_run_request`,
field `public_market_context` only); focused T01-T12 and T15 evidence is in
`tests/research_runtime/hermes_controlled_runtime/test_models.py` and T13-T14 in
`tests/research_runtime/hermes_controlled_runtime/test_context_controller.py`; the canonical
semantics are recorded in `docs/hermes_controlled_research_runtime_contract.md`.

Trigger: S10-GATE-AF1 Attempt-03 is CONSUMED with terminal TRUE_STOP /
PHASE_B_LOCAL_EVIDENCE_DEFECT and AF1 gate result NONE; its public population succeeded, then
the first blind case failed `REQUEST_SECRET_DETECTED` in the request builder before any Hermes
launch (Hermes/provider/model calls 0, Firecrawl calls 0, accepted provider cost USD 0).
Compatibility rule: inside `public_market_context` only, exact complete canonical public
identifiers `market:polymarket:<decimal>`, `event:polymarket:0x<exactly 64 lowercase hex>`,
`event:polymarket:market-<decimal>` and the canonical CLOB token id form (polymarket token
namespace + decimal; exact grammar in the contract) survive the generic
long-hex rule, which remains a global secret rule; every occurrence of the literal
namespace `event:polymarket:` there must begin an exact canonical event id or fail closed;
bare long-hex, wallet/account-shaped,
credential, wrong-namespace and malformed values remain fail-closed, every other request field
keeps the ordinary strict scan, and request identity uses the original bytes. No schema,
invocation policy identity, provider, model, retry, output-parsing, network, credential,
dependency or workflow change. Successor boundary: after Side13 review and Karl's merge only,
AF1 is reconciled onto repaired main with its own live-shaped fixture, a new Phase-A head, and
an explicit successor-attempt semantics closure before any new runtime authorization; this
package authorizes no successor AF1 attempt. H1 #5, Gate C, capital, and orders are unchanged.

## S10-HERMES-CTX-02 Pinned Default SOUL.md Compatibility Repair (current bounded compatibility repair)

The canonical package is `docs/wp_specs/S10-HERMES-CTX-02/`; the stable fragment is
`docs/status_entries/S10-HERMES-CTX-02.md`. The frozen base is PR #193's merge commit
`70f867bdcd5e97b0dc05d4008c2c023feb461658`. The only source change is a private exact-bytes
verifier in `src/research_runtime/hermes_controlled_runtime/runner.py` used by
`is_clean_research_home_control_plane`; focused T01-T14 evidence is in
`tests/research_runtime/hermes_controlled_runtime/test_runner.py`; the canonical semantics are
recorded in `docs/hermes_controlled_research_runtime_contract.md`.

Trigger: S10-GATE-AF1 Phase-B `HERMES_HOME_CONTROL_PLANE_INVALID`. Pinned Hermes v0.21.3
(tag v2026.9.14, commit 345cd2b) seeds its stock SOUL.md into every initialized home, so the
former universal SOUL.md rejection could never pass. SOUL.md is now admitted only as the exact
pinned stock default (667 bytes, SHA-256
`36c1f5a2e92cd1d018311eaf4c8f1e8886672eae78212e033c681d0e3d5d506f`, regular non-symlink file,
no normalization); every other SOUL.md and every other clean-home rule stays fail-closed, and
`.env`/`auth.json` values are never opened. No provider, model, Firecrawl, Polymarket, OAuth,
credential, dependency, workflow, policy, argv, retry, telemetry, or context-protocol change.
AF1 Attempt-03 remains unconsumed and not authorized. PR #194 merged this repair at
`15097f70f5f5358879fde73b2b30d26ecdb80402`; S10-GATE-AF1 is reconciled onto it and awaits only a fresh exact authorization. H1 #5, Gate C,
capital, and orders are unchanged.

## WP164A Public Population Compatibility Repair (merged runtime-certified dependency)

The canonical package is `docs/wp_specs/WP164A/`; implementation is a narrow additive repair to
`src/data_layer/point_in_time_market_research/polymarket_public_population.py`; canonical behavior
remains in `docs/polymarket_point_in_time_public_population_contract.md`; focused evidence remains
in `tests/data_layer/point_in_time_market_research/test_polymarket_public_population.py`; and the
stable fragment is `docs/status_entries/WP164A.md`. The frozen base is PR #192's merge commit
`9332aa2b2591d7e3fb015ae10165f063aeb8fa1d`, whose WP156A implementation head is
`053f7dd73d27262f84dc0651d05e0fe737cadd33`.

WP164A preserves the complete typed WP156 batch result after validation and the closed safe fields
from a completed invalid WP156 build result, retains truthful completed stage counts and already
derived run provenance on later rejection, and maps raw Gamma lifecycle booleans locally to exactly `open` or
`closed`, rejecting every other shape. Its 25-market/1-book proof is synthetic and offline. Phase A
makes zero real public-product calls and does not modify `PolymarketPublicClient`, WP156, Alpha,
Hermes, credentials, scheduler, dependencies, workflows, paper, execution, or live paths.
AF1 Attempt-01 and Attempt-02 are historical invalidated/consumed evidence only; WP164A
public-smoke Attempt-01 and Attempt-02 are permanently consumed.

Current WP164A truth (post-smoke, post-merge): WP164A public-smoke Attempt-03 was separately
authorized and executed on exact tested head `1c7de22f31cd093771d6bc0748c440ad5284b105` before
PR #193 merged it as `70f867bdcd5e97b0dc05d4008c2c023feb461658`; the tested head is contained in
merged main with zero file difference, and PR #193 exact-head hosted CI passed. Attempt-03 is
CONSUMED with terminal `WP164A_PUBLIC_SMOKE_COMPLETE_SUCCESS`: 25 markets fetched, 1 order book
fetched, 26 records built, 26 inserted; batch valid with 26 unique accepted, 0 quarantined,
0 duplicates, and warning `EVENT_TIME_MISSING_ALLOWED` retained; exactly 1 coordinator invocation
and 0 retries/replacements. Those counts are historical runtime evidence, not future guarantees.
WP164A dependency certification is COMPLETE and S10-GATE-AF1 is no longer blocked by WP164A.
AF1 Attempt-03 itself remains NOT AUTHORIZED. There is no WP164A Attempt-04; the single-use
WP164A operator binding its historical pre-merge base is expectedly non-runnable after merge. The
frozen WP164A prompt/spec/operator/status fragment keep their pre-smoke Phase-A wording (including
the historical stop `WP164A_PUBLIC_SMOKE_AUTHORIZATION_REQUIRED`) as historical authorization
evidence only.

## WP156A Large Canonical Payload Batch Fingerprint Correction (merged historical truth)

WP156A is the FAST-track, Risk-2, exact 12-file upstream correction on frozen main
`46bc862018208b30971228ed719c7e9337142b41`. Its package is
`docs/wp_specs/WP156A/`, stable evidence fragment is
`docs/status_entries/WP156A.md`, implementation change is confined to the private
`_record_fingerprint` in
`src/data_layer/point_in_time_market_research/records.py`, and focused evidence is
in the existing WP156 and WP164 test modules.

Consumed WP164A public-smoke Attempt-02 remains permanently consumed after terminal
`WP164A_PUBLIC_SMOKE_BATCH_INVALID` with 25 markets, one book, 26 built records,
zero inserted records, and exact batch error
`RECORD_VERSION_HASH_COLLISION_OR_MISMATCH`. WP156A deterministically reproduces
the upstream contradiction: an ordinary valid ORDER_BOOK payload tree can serialize
above 4,096 characters, while the legacy private fingerprint re-wrapped that complete
serialization as one bounded string and raised `PAYLOAD_STRING_LIMIT_EXCEEDED`.

The correction replaces only that payload contribution with the SHA-256 of the exact
UTF-8 serialized payload plus its exact UTF-8 byte length. Every true WP156 bound,
record-version and canonical-payload identity, canonical batch material, duplicate and
lineage semantic, public dataclass, and error/warning vocabulary remains unchanged.
Permanent tests retain the legacy contradiction oracle, corrected large-record success,
duplicate/tamper behavior, and offline WP164 large-book persistence/registration.

No product/network, public smoke, AF1, Hermes/provider, credential, scheduler, strategy,
paper, execution, live, order, capital, dependency, lock, workflow, or merge authority
is created by the implementation package. The SIDE12 WP156A final one-shot closure later
grants contingent PR/CI/merge authority only after every exact-head hard gate passes.
WP164A reconciliation and a new zero-network Phase-A candidate were separately gated.
AF1 Attempt-03 remains unauthorized.

The definitive pre-smoke Phase-A SHA
`17ce49aa96c798244d852fc5daf16299bee79ef9` and historical candidate
`31379495e70dee1a0d698300e3371911af62de3a` remain ancestors. WP164A public
smoke Attempt-01 is consumed as `WP164A_PUBLIC_SMOKE_LOCAL_EVIDENCE_DEFECT` and
cannot be retried. Build-diagnostic correction 02 remains inside the exact 13
paths and performs zero network calls. Its six additive build fields retain only
kind, status, errors, warnings, quarantine id, and structural input fingerprint.
The offline 257-level book oracle proves `PAYLOAD_SEQUENCE_LIMIT_EXCEEDED` after
25 successful metadata builds without truncation, persistence, or batch
validation. Attempt-02 is permanently consumed and cannot be retried.

Execution-surface correction 03 expanded the exact package from 13 to 14 paths by
adding only `tools/polymarket/run_wp164a_public_smoke.py`. The first state-drift
checkpoint at `53da1d50fb8a91ecdb32cd44611241f0062925ff` made no call. The definitive
pre-reconciliation head `5a7044147c018389402e71f35a759e1d621c4b25` later consumed Attempt-02 and ended
`WP164A_PUBLIC_SMOKE_BATCH_INVALID` with 25 markets, one book, 26 built, zero inserted,
`RECORD_VERSION_HASH_COLLISION_OR_MISMATCH`, 25 accepted, zero quarantine, and zero duplicate.
Merged WP156A corrects that upstream fingerprint defect. The operator is the sole future
Attempt-03 surface and freezes the exact four-option
command, the four `wp164a:public-smoke:1.0.0` provenance labels, 25/1 limits,
one call, zero retry, exact sibling paths, four artifact names, six terminals,
and the exact 28-key `wp164a-public-smoke-authorization-envelope/1.0.0` schema.
The post-WP156A reconciliation adds full offline operator-chain proofs for exact 25/1,
large-book, fewer-count, zero-book, closed failure, one-call, and zero-retry behavior. It performs
zero public/product calls and stops for a new commit-bound Attempt-03 human authorization using
`I_AUTHORIZE_EXACT_WP164A_PUBLIC_SMOKE_ATTEMPT_03` and
`local_data/wp164a_public_smoke/<NEW_SHA>/attempt-03`.

Follow-up 01 expands the exact governed scope from 11 to 13 paths solely to maintain the historical
WP165/WP166 test fixtures that reuse WP164 parsing. Their central raw Gamma helpers now use exact
live-shaped `active=True` and `closed=False`; no WP165/WP166 production source or lifecycle grammar
is changed. Historical failed candidate `31379495e70dee1a0d698300e3371911af62de3a` remains an
ancestor of the definitive correction candidate.

## S10-ALPHA-02 PIT Alpha Discovery Control Plane (merged historical truth)

The canonical contract is `docs/alpha_discovery_control_plane_contract.md`; implementation is
`src/data_layer/analytical_research/alpha_discovery.py` and the separate append-only registry
`src/data_layer/analytical_research/alpha_discovery_registry.py`, with additive exports from
`src/data_layer/analytical_research/__init__.py`. Focused evidence is in
`tests/data_layer/analytical_research/test_alpha_discovery.py`,
`tests/data_layer/analytical_research/test_alpha_discovery_registry.py`, and
`tests/data_layer/analytical_research/test_alpha_discovery_boundaries.py`. The exact 17-path FAST,
Risk-2 package is `docs/wp_specs/S10-ALPHA-02/`; its stable evidence fragment is
`docs/status_entries/S10-ALPHA-02.md`. The frozen base is PR #190's merge commit
`a2fba4d770cd6fac1cfb551419d040d65768a8e9`, whose implementation head is
`2d53af9b3a51f8f9a27334e8bc3b2c40efe6864a`.

ALPHA-02 implements deterministic local/offline observed-PIT-universe snapshots, typed material
change, explicit historical-versus-current Alpha-memory posture, exact canonical PIT subject
matching, complete current-market triage/skip evidence, bounded core/exploration/audit research
allocation, inert prospective capture requests, and separate append-only discovery memory. It does
not prove exhaustive external market completeness: coverage is `BOUNDED_OBSERVED_UNIVERSE` and
external completeness is `UNPROVEN`. It does not fetch markets, invoke Hermes, schedule campaigns,
mutate ALPHA-01, qualify research, compute expected return, create a strategy, place paper/live
orders, or authorize Gate C/capital. H1 #5 and merge remain NOT AUTHORIZED. After separate review
and merge, `S10-GATE-AF1` is the current Phase-A research-system gate target; its deterministic
records, seeded oracles, and zero-network operator boundary are defined in
`docs/alpha_factory_research_system_gate_contract.md`. Real public population, Hermes-provider
activation, blind review, successors, and merge remain separately authorized; ALPHA-03/04 and
downstream layers remain separately gated.

## S10-WALLET-02 PIT Wallet Profiles (merged historical truth)

The canonical contract is `docs/wallet_profile_snapshot_contract.md`; implementation is
`src/data_layer/wallet_intelligence/profile.py` with additive exports from the package
`__init__.py`; focused evidence is `tests/data_layer/wallet_intelligence/test_profile.py`;
the exact 17-path package is `docs/wp_specs/S10-WALLET-02/`; stable branch evidence is
`docs/status_entries/S10-WALLET-02.md`. The frozen base is PR #189's merge commit
`45b6cb4db7fc5e8ac2ae21145bf00be658740025`; S10-HERMES-CTX-01 is merged historical truth
with implementation head `bf346a65cf1b93b5e61d2420a8da1629be2bd191`.

S10-WALLET-02 reads and verifies an existing WALLET-01 ledger without mutation and emits
immutable content-addressed discovery cohorts, PIT market contexts, and
`WalletProfileSnapshot` evidence. Historical action time never proves knowability.
Independent-group sample strength, deterministic Jeffreys shrinkage, descriptive
specialization, direct-evidence archetypes, and PIT-safe public-account relationships are
research evidence only. The WP79 fixture-era profile remains compatibility history and is
not canonical real-evidence profiling. WALLET-03 retains copyability economics;
WALLET-04 retains incremental-value evidence. No product network, Hermes, credentials,
qualification, strategy, paper, execution, live, order, capital, or Gate-C authority is
created. H1 #5 remains NOT AUTHORIZED. S10-WALLET-02 merged through PR #190 at
`a2fba4d770cd6fac1cfb551419d040d65768a8e9`; S10-ALPHA-02 is now the separately authorized
bounded implementation target.

## S10-HERMES-CTX-01 Blind-First Context Broker (merged historical truth)

The canonical contract is `docs/hermes_context_broker_reconciliation_contract.md`; stable
branch evidence is `docs/status_entries/S10-HERMES-CTX-01.md`; the exact 34-path machine
package is `docs/wp_specs/S10-HERMES-CTX-01/`. Source is the additive context protocol,
store, broker, reconciliation, controller, and session-evidence modules under
`src/research_runtime/hermes_controlled_runtime/`, with focused tests in the matching test
package. PR #188 / S10-WALLET-01 is merged at
`7495427820c892497e9c195a8b130c2d32102c67`. No real Hermes/provider/Firecrawl, credential,
wallet/market network, paper/live, or economic action is authorized. H1 #5, HERMES-SI,
Gate C, merge, and successor implementation remain unauthorized. After merge/review the
next mandatory package is S10-WALLET-02; S10-ALPHA-02 remains after WALLET-02.

## WP175N Multi-Lane Alpha Factory Core (current review target)

WP175N / Side11 capability handle S10-ALPHA-01 is the FAST-track, risk-2, exact 16-file
bounded implementation of the first canonical Alpha Factory research-memory substrate. It
adds a standalone record model `src/data_layer/analytical_research/alpha_factory.py` and a
bounded append-only SQLite registry
`src/data_layer/analytical_research/alpha_factory_registry.py`, exported from
`src/data_layer/analytical_research/__init__.py`, plus the canonical contract
`docs/alpha_factory_core_contract.md` and focused tests
`tests/data_layer/analytical_research/test_alpha_factory_records.py`,
`tests/data_layer/analytical_research/test_alpha_factory_identity.py`,
`tests/data_layer/analytical_research/test_alpha_factory_registry.py`, and
`tests/data_layer/analytical_research/test_alpha_factory_boundaries.py`. Four frozen
content-addressed record types (ResearchSourceReference, OpportunityCandidate,
HypothesisFamily, ResearchEpisode) record public source references, research-worthy
opportunity candidates, hypothesis/mechanism families, and immutable research episodes with
primitive multi-lane evidence (COMPOSITE is derived, not stored), nine closed result states
with a per-state evidence matrix, exact-scope negative evidence, append-only reopen,
deterministic novelty/mechanism fingerprints, producer provenance, and recursive
secret/authority/binary-float rejection. The separate append-only SQLite registry uses
format id `s10-alpha-factory-registry`, integer schema version 1, and application id
`1464877425` (proven unique and distinct from WP170's `1464877424`), with a per-entry
SHA-256 hash chain, append-only triggers, caller-order-independent atomic append,
projected-history cross-reference validation, and read-only verified load. WP170
`experiment_os.py`/`experiment_registry.py` and application id `1464877424` are UNCHANGED;
`HypothesisFamily` is not `ExperimentFamily`. This registration grants no
provider/model/Hermes runtime, Firecrawl, OAuth, network, scheduler, prioritization,
qualification, economic, strategy, paper, live, credential, signing, order, or Gate-C
authority. S10-GATE-H1 is `GENUINE_H1_PASS` (accepted H1 #4; historical real H1 invocations
4; H1 #5 NOT AUTHORIZED; remote Firecrawl HTTP independently proven: NO). The immediate
software successor after WP175N merge is S10-WALLET-01, then S10-HERMES-CTX-01; the
wallet-intelligence roadmap anchor (WALLET-01..WALLET-04 + GATE-WALLET-01) persists with a
conditional, non-global wallet gate. Gate C is NOT AUTHORIZED and merge is not authorized
pending Side11 exact-head review.

## WP175M Hermes Draft Prompt Contract Alignment And Schema Diagnostics (current review target)

WP175M / Side11 capability handle S10-HERMES-01E is the RUNTIME-track, risk-3, exact
15-file bounded alignment of the Hermes draft prompt/output contract and sanitized
schema-failure observability on `claude/wp175m-draft-contract-alignment`, based on merged
WP175L / PR #185 merged at `b36155201304126339482ea74e77181466181b9c`. Its source changes
are `src/research_runtime/hermes_controlled_runtime/models.py`, `policy.py`,
`controller.py`, and `__init__.py`; `response_capture.py`, `runner.py`, dependencies,
locks, and workflows are unchanged.

Historical real H1 research invocations consumed = 3. H1 #3 — the THIRD real S10-GATE-H1
run — was consumed and, from the runtime/usage perspective, completed a real controlled
research/model interaction (Hermes child exit 0, not timed out, stderr empty, VALID usage
report with `api_call_count` 5), yet its terminal result was `OUTPUT_SCHEMA_INVALID` /
`DRAFT_FIELD_MISSING`. Read-only forensics uniquely identified the persisted session by
the exact frozen request id: the final JSON had correct `schema_version` and `request_id`
but all other canonical required fields absent, an alternative structured schema improvised
(`as_of`, `completeness`, `cross_category_assessment`, `evidence_map`, `generated_at`,
`research_category`, `research_question`, `scope`, `sources`), validator first missing
canonical field `advisory_only`, and `web_search`/`web_extract` observed with no unexpected
tools. Remote Firecrawl HTTP is NOT independently proven (runtime tool telemetry is
`UNAVAILABLE_ON_PINNED_V0_21_3`). The `title_generation` usage-row lesson: `session_model_usage`
aggregates an auxiliary title-generation row, so exact aggregate equality is not a safe
session-identity method; the main research route usage matched the receipt.

H1 #3 exact root cause: `PROMPT_OUTPUT_CONTRACT_SCHEMA_NOT_ACTUALLY_EMBEDDED` — the
permanent instruction referenced a "provided research-draft schema", but the envelope
supplied only `draft_schema_version`, never the deterministic field contract
`validate_research_draft` enforces. WP175M fixes the contract BEFORE generation:
`models.py` owns `build_research_draft_output_schema` derived from the SAME constants the
validator enforces (STOP CONTRACT_VALIDATOR_DRIFT); `_DRAFT_LIST_FIELDS` becomes the public
`DRAFT_LIST_FIELDS` plus a canonical ordered `DRAFT_REQUIRED_TOP_LEVEL_FIELDS`; the schema
embeds every required field, authority `const: true` flags, confidence/source-class enums,
validator-aligned bounds, and the exact request id and draft schema version as constants.
`policy.py` bumps the instruction to `hermes-research-system-instruction/1.1.0` (schema
authoritative, exact field names, no aliases, real substantive research) and the envelope
carries an authoritative `draft_output_schema`. Authority-flag injection is DECLINED (all
draft authority flags remain MODEL-OUTPUT REQUIRED and exactly `true`); there is NO
substantive post-hoc repair (a wrong schema still fails closed). Sanitized diagnostics
(`inspect_research_draft_structure`) retain only static canonical field-name tokens and
fixed statuses, never rejected values or a raw session id. The receipt is bumped
`hermes-research-run-receipt/1.2.0` -> `hermes-research-run-receipt/1.3.0` with additive
`prompt_envelope_sha256`, `draft_output_contract_sha256`, draft diagnostics, and
`usage_session_id_digest`. With valid usage the actual provider/model are preserved before
draft validation, so a schema failure keeps `verified_provider` `openai-codex` /
`verified_model` `gpt-5.6-sol` while the terminal status stays `OUTPUT_SCHEMA_INVALID`; the
mismatch precedence after a valid draft is unchanged. The Hermes pin, provider `openai-codex`,
model `gpt-5.6-sol`, the `web`-only toolset, retry/managed profile, runtime envelope,
request identity, and the frozen H1 request id
`d977b2073c685c64a6398475ba437aa9cc63be517b2260c513ffd4e9ba795b69` are UNCHANGED. H1 #4 is
NOT AUTHORIZED, S10-ALPHA-01 is BLOCKED, Gate C is NOT AUTHORIZED, Alpha Factory is NOT
STARTED, WP176 is NOT STARTED, and merge is NOT AUTHORIZED. The relevant post-merge gate is
a controlled structured-output contract validation using the exact patched runtime; three
real H1 invocations (H1 #1, H1 #2, H1 #3) are already consumed, so any fourth real
S10-GATE-H1 run (H1 #4) remains a separate human/governance decision that WP175M does not
authorize.

## WP175L Sanitized Windows Runtime Envelope And Startup Preflight (merged, PR #185)

WP175L / Side11 capability handle S10-HERMES-01D is the RUNTIME-track, risk-3, exact
12-file bounded correction of the controlled Hermes wrapper runtime environment and
startup preflight on `claude/wp175l-sanitized-windows-runtime`, based on merged WP175K /
PR #184 at `473fcd4e6fa95f1230fd29d384f8be736e5085e1`. Its source changes are
`src/research_runtime/hermes_controlled_runtime/runner.py` and `controller.py`;
`models.py`, `policy.py`, `response_capture.py`, `__init__.py`, dependencies, locks, and
workflows are unchanged.

Historical real H1 research invocations consumed = 2. H1 #2's confirmed root cause is
`CONTROLLED_WINDOWS_RUNTIME_ENVIRONMENT_INSUFFICIENT_FOR_HERMES_PROFILE_INITIALIZATION`:
the merged runner built the controlled child from a tiny neutral whitelist plus
`HERMES_HOME`/`HERMES_MANAGED_DIR` and did not forward ordinary Windows home/runtime
context, so the pinned chain
`hermes_cli/main.py::_apply_profile_override` -> `hermes_constants.get_default_hermes_root`
-> `_get_platform_default_hermes_home` (which reads `LOCALAPPDATA`, else
`Path.home()/"AppData"/"Local"`) raised `RuntimeError: Could not determine home
directory.` and research/provider-binding/Firecrawl were NOT_REACHED. `hermes --version`
passed because it is answered by the fast-version path before profile initialization.
WP175K was SUCCESSFUL AS OBSERVABILITY HARDENING because its sanitized evidence exposed
this. WP175L replaces `_minimal_env` with a deterministic platform-aware HYBRID SANITIZED
RUNTIME ENVELOPE (`_build_sanitized_runtime_env`) — an explicit benign allowlist, never
`os.environ.copy()`. Side11's exact-head review of `c73934c` raised BLOCKING Finding E:
forwarding the REAL per-user `LOCALAPPDATA`/`USERPROFILE` let pinned
`hermes_cli/main.py::_apply_profile_override` read a sticky personal
`%LOCALAPPDATA%\hermes\active_profile` and re-home the explicit H1 `HERMES_HOME`. The
hybrid envelope therefore forwards only real benign MACHINE/runtime values (`COMSPEC`,
`PATHEXT`, `WINDIR`, `OS`, `PROCESSOR_ARCHITECTURE`, `NUMBER_OF_PROCESSORS`, `PROGRAMDATA`,
`PROGRAMFILES`, `PROGRAMFILES(X86)`, `COMMONPROGRAMFILES`), and SYNTHESIZES the per-user
Windows identity roots (`USERPROFILE`, `HOMEDRIVE`, `HOMEPATH`, `APPDATA`, `LOCALAPPDATA`)
under a backend-owned ephemeral runtime-user root — never the real parent values — so
`Path.home()` works, the pinned default root resolves under a controlled `LOCALAPPDATA`
(`<root>\AppData\Local\hermes`) that carries no unrelated `active_profile`, and the
explicit H1 `HERMES_HOME` stays authoritative. The secret-name rejection is retained and
an explicit interpreter/shell/capability injection denylist is added, so no ambient
provider credential or injection variable reaches the child. WP175L also adds an OFFLINE
startup/profile-init preflight (`hermes --help`,
which exercises the profile/default-home path the `--version` fast path skips) that uses
the same sanitized envelope and a throwaway `HERMES_HOME`; a launch failure, timeout, or
nonzero exit is terminal `STARTUP_PREFLIGHT_FAILED` with `transport_attempt_count` 0 and
consumes no H1 research slot. Provider `openai-codex`, model `gpt-5.6-sol`, the `web`-only
toolset, retry/fallback posture, managed config, request/draft/receipt schemas, and the
controller research failure precedence are UNCHANGED. H1 #3 is NOT AUTHORIZED,
S10-ALPHA-01 is BLOCKED, Gate C is NOT AUTHORIZED, Alpha Factory is NOT STARTED, WP176 is
NOT STARTED, and merge is NOT AUTHORIZED. The relevant post-merge gate is a controlled
startup preflight using the exact patched runner; two real H1 invocations (H1 #1, H1 #2)
are already consumed, so any third real S10-GATE-H1 run (H1 #3) remains a separate
human/governance decision that WP175L does not authorize.

## WP175K Sanitized Hermes Failure-Evidence Capture Hardening (merged, PR #184)

WP175K / Side11 capability handle S10-HERMES-01C is the RUNTIME-track, risk-3,
exact 14-file bounded evidence-capture hardening on
`claude/wp175k-hermes-failure-evidence-hardening`, based on merged WP175J / PR #183 at
`e4323305a9ab6d8434ad451942420606f9252ff9`. Its source changes are
`src/research_runtime/hermes_controlled_runtime/runner.py`, `controller.py`, and
`models.py`; policy identity, managed config, request/draft schemas, dependencies,
locks, and workflows are unchanged.

After WP175J merged, the one authorized S10-GATE-H1 real research invocation ran exactly
once and ended FAIL_RUNTIME_CONTRACT / EXIT_CODE_NONZERO (exit code 1, not timed out,
usage evidence MISSING, validated research NONE, 0 sources); S10-GATE-H1 single
authorized real invocation consumed = 1. DIAG-01 = ROOT_CAUSE_NARROWED_NOT_CONFIRMED and
DIAG-02 = PREACCOUNTING_PATHS_PASS_ROOT_CAUSE_STILL_UNRECOVERABLE proved (with zero
network/provider/Firecrawl calls) that every testable pre-accounting path passes and
that the decisive child stderr had been intentionally discarded, leaving the exit-1
mechanism unrecoverable from retained evidence. WP175K fixes only that observability
gap: a deterministic in-runner sanitizer retains a small, secret-scrubbed, path-scrubbed
diagnostic tail excerpt (MAX_SANITIZED_STDERR_EXCERPT_BYTES = 4096) plus usage-file
presence while still discarding raw stderr, and the receipt schema is bumped additively
`hermes-research-run-receipt/1.1.0` -> `hermes-research-run-receipt/1.2.0` with new
fields `stderr_captured_byte_len`, `stderr_sanitization_status`, `stderr_excerpt`,
`stderr_excerpt_truncated`, `stderr_redaction_applied`, `usage_file_present`, and
`usage_file_truncated`. Raw stderr remains forbidden in every receipt, artifact, log,
and return value; the sanitized bounded excerpt is the only diagnostic text surface;
residual secret-like content fails closed to no excerpt and a sanitizer fault fails
closed without changing terminal status or retry. Controller failure precedence, the
research argv, provider `openai-codex`, model `gpt-5.6-sol`, the `web`-only toolset, the
retry/fallback posture, and the frozen H1 request are UNCHANGED. WP175K does not repair
the unknown exit-1 mechanism, activate the runtime, authorize any H1 rerun, or unlock
Alpha. H1 rerun is NOT AUTHORIZED, S10-ALPHA-01 is BLOCKED, Gate C is NOT AUTHORIZED,
Alpha Factory is NOT STARTED, WP176 is NOT STARTED, and merge is NOT AUTHORIZED. The
immediate successor is a separate human/governance decision on whether the failed first
run plus this evidence hardening justifies a second real S10-GATE-H1 run; a software
correction does not itself recreate H1 authorization.

## WP175J Hermes Version Banner Preflight Parser Correction (merged, PR #183)

WP175J / Side11 capability handle S10-HERMES-01B is the RUNTIME-track, risk-3,
exact 12-file bounded correction on `codex/wp175j-hermes-version-banner-parser`,
based on merged WP175I / PR #182 at `0bc994c6659c6175ed7cf45cb7149ead51774344`.
Its only source change is `src/research_runtime/hermes_controlled_runtime/policy.py`;
controller, runner, policy identity, managed config, request/receipt schemas,
dependencies, locks, and workflows are unchanged.

The exact banner `Hermes Agent v0.21.3 (2026.9.14)` exposed a deterministic parser
defect: the generic word-boundary semver search skipped `v0.21.3` and selected release
date `2026.9.14`. WP175J binds package-version identity to a Hermes-branded label and
rejects release-date-only, unbranded, and malformed tokens. The AppContainer launcher
issue was setup-only and resolved separately; the non-virtualized pinned CLI succeeds.
H1 remains blocked and unconsumed until correction merge, Side11 review, and a fresh
human one-run checkpoint: real H1 research invocations 0, provider/API calls 0,
Firecrawl research calls 0, RUNTIME ACTIVATED NO. The immediate successor is resumed
S10-GATE-H1; only genuine H1 PASS plus Side11 review unlocks S10-ALPHA-01. Gate C is
NOT AUTHORIZED, Alpha Factory is NOT STARTED, WP176 is NOT STARTED, and merge is NOT AUTHORIZED.

## WP175I Controlled Research Profile Enforcement (merged, PR #182)

WP175I / Side10 capability handle S10-HERMES-01A is the RUNTIME-track, risk-3, exact
15-file controlled research profile correction on
`claude/wp175i-hermes-controlled-profile-enforcement`, based on the merged WP175H /
PR #181 commit `3e5dd322800e656f942d46c768fc93aa7ac2e7ea`. Deterministic readiness is
`IMPLEMENTATION_READY` without an independent certificate; readiness and this committed
target truth grant no merge, runtime-activation, or live authority.

WP175I corrects the merged WP175H external runtime so pristine pinned Hermes v0.21.3
(tag v2026.9.14, commit 345cd2b, UNCHANGED) runs under one mechanically enforced
controlled research profile. It removes `--safe-mode` from the real research invocation
(exact tagged `--safe-mode` sets `HERMES_SAFE_MODE=1`, which makes `hermes_cli/plugins.py`
skip plugin discovery and suppress the bundled `plugins/web/firecrawl` backend H1
requires) while retaining `--ignore-user-config` and `--ignore-rules`, and replaces the
lost isolation with a deterministic repo-owned non-secret managed-scope `config.yaml`
injected through an ephemeral `HERMES_MANAGED_DIR`. The managed overlay pins Firecrawl
for `web_search` and `web_extract`, forces keyless fallback/rescue and web cache off,
empties `fallback_providers`, sets `agent.api_max_retries` to 1, sets `plugins.enabled`
and `hooks` empty and `updates.check` false, and sets `web.provider_tier.firecrawl` to
`paid`; the Hermes invocation policy schema is bumped to 2.0.0 and the managed-config
SHA-256 is committed into the policy identity. A fail-closed research-home control-plane
preflight rejects a present `config.yaml` or non-empty user plugins before spawn. The
first S10-GATE-H1 attempt stopped at static preflight FAIL / SOFTWARE_GAP with 0 real
research invocations, 0 OAuth, and 0 Firecrawl-secret use, so the H1 authorization was
not consumed; S10-GATE-H1 resumes only after WP175I merge and Side10 review.
`models.py` and `response_capture.py` are unchanged; no dependency, workflow, credential,
capital, or order activity exists; Gate C is NOT AUTHORIZED and WP176 is NOT STARTED.

## WP175H Controlled Hermes Research Runtime Core (merged, PR #181)

WP175H / Side10 capability handle S10-HERMES-01 is the RUNTIME-track, risk-3, exact
24-file controlled Hermes research runtime core on
`claude/wp175h-hermes-controlled-research-runtime`, based on the merged WP175E /
PR #180 commit `22557ee3b0beeeb13a3c3b626ae8f30e11967364`. Deterministic readiness
is `IMPLEMENTATION_READY` without an independent certificate; readiness and this
committed target truth grant no merge, runtime-activation, or live authority.

`src/research_runtime/hermes_controlled_runtime/` adds the first repo-owned,
dormant-by-default control plane around one bounded, one-shot, web-only EXTERNAL
Hermes research session pinned to Hermes Agent v0.21.3 (tag v2026.9.14, commit
345cd2b). It provides an immutable content-addressed request, a frozen
non-broadenable invocation policy allowing exactly the `web` toolset (web_search +
web_extract), a compact research envelope, a backend protocol with a deterministic
no-process fake and an isolated argv-only ephemeral-cwd external backend, a bounded
plain-stdout response and usage-file parser, an authoritative untrusted-draft schema/safety validator,
and a sanitized no-authority receipt requiring human review. Hermes prose is
untrusted research content, never canonical economic truth; the repository
validator is authoritative and fails closed with no raw payload, stderr,
environment, secret, or path in canonical evidence.

CODE COMPLETE: YES; RUNTIME ACTIVATED: NO. `REAL_HERMES_BINARY_NOT_PRESENT` is an
activation prerequisite, not a code blocker; tests use a fake executable and make
zero paid/provider calls. Project code never reads, stores, injects, logs,
transforms, validates, or echoes a provider secret or trading credential. No
dependency, lock, or workflow file changes; WP170/WP172/WP173/WP175 and the legacy
WP99/WP133/WP145 advisory validators are unchanged. This package creates no
opportunity candidate, probability thesis, fair value, side, entry/exit, position
size, strategy promotion, Alpha Factory state, or trade recommendation. Gate C is
NOT AUTHORIZED, WP176 Mature Controlled Live is NOT STARTED, credentials and real
orders are 0, capital at risk is USD 0, and merge is NOT AUTHORIZED. The first real
provider-backed / public-web run is separately gated as S10-GATE-H1 Controlled
Public Research Pilot; if it succeeds, S10-ALPHA-01 Multi-Lane Alpha Factory Core
follows. Both are NOT STARTED and gain no trading authority. Normative contract:
`docs/hermes_controlled_research_runtime_contract.md`.

## WP175E Native Continuity-Attested Market Truth Bridge (current review target)

WP175E / Side10 S10-DATA-03 is the FAST, risk-2, exact 20-file continuation on
`claude/wp175e-market-truth-adapter-66a6bd`, based on the merged WP175D / PR #179
commit `195cc1a42b73d08185f96c613d9a95154f919102`. Deterministic readiness is
`IMPLEMENTATION_READY` without an independent certificate; readiness and this
committed target truth grant no merge or live authority.

S10-EVID-01B completed `EVIDENCE_INCONCLUSIVE`. Genuine PMXT v2 remains valid
external research evidence, but the tested candidate missed first-look OOS
criteria and PMXT `known_gap_policy=AS_CAPTURED` remains continuity-incomplete.
WP175E does not reclassify PMXT, retune the candidate, expose new OOS, or rerun
the evidence gate.

The additive WP169 read surface verifies accepted WS observations against their
durable raw occurrence, recovers the durable session id, and returns bounded
deterministically ordered immutable observation/session/gap evidence. WP169
`APPLICATION_ID`, `USER_VERSION`, DDL, indexes, checkpoint chain, append
semantics, and existing APIs remain unchanged; there is no migration.

`NativeContinuityAttestation` derives capture identity and continuity from the
durable WS session, initial ready full-book snapshot, exact observation order,
uninterrupted STREAMING epoch, and balanced gap history. No caller capture id or
continuity boolean exists. Every disconnect/regression/hash/parse/queue/storage/
reorg gap and every reconnect/session transition prevents completeness. A later
start after a durable HEALED event and at a later full snapshot may form a fresh
epoch without rewriting history. `NativeMarketTruthWindow` is separately
content-addressed under `nativemarkettruthwindow:sha256:` and uses only accepted
WS book/trade evidence with integer receive-time nanoseconds and exact Decimal
arithmetic; non-WS APIs, quarantined, and unsupported records have no native
order-book authority.

Existing PMXT `MarketTruthWindow` fields, identity preimage, builder, and gap
rule are unchanged. WP172 admits the exact PMXT/native union without changing
classification precedence or fee/fill/capacity/net-edge gates. WP173 replay
admits the same union without changing `PaperStrategyBinding`, fill, accounting,
risk, reconciliation, or paper/live separation.

WP169-D001 is narrowed/resolved only for the delivered WP169-native -> WP172
bridge extent; a generic PIT -> Nautilus adapter remains absent and unclaimed.
WP175 remains merged dormant, Gate C is NOT AUTHORIZED,
`LIVE_PATH_EVIDENCE_READY` is NOT CLAIMED, WP176 is NOT STARTED, credentials and
real orders are 0, capital at risk is USD 0, and merge is NOT AUTHORIZED. After
merge, the successor is a separately gated prospective evidence run that first
preregisters a fresh candidate before forward OOS/native capture. Normative
contract: `docs/native_continuity_attested_market_truth_bridge_contract.md`.

## WP175D External Historical Research Bridge (current review target)

WP175D (Side10 capability S10-DATA-02) is the FAST, risk-2, local/offline external
historical research bridge on `codex/wp175d-external-historical-research-bridge`,
based on merged WP175 PR #178 at merge commit
`489c6f9548c39cb3bcb2196a81d5352a0d1dd653` (WP175 merged dormant). It is an exact
24-file package (`max_changed_files=24`, `exact_scope_required=true`), FAST readiness
`IMPLEMENTATION_READY` with no independent certificate required under current
governance.

WP175D closes the root cause behind `LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE`:
WP170 accepts only canonical-PIT lineage, and canonical PIT visibility is
ingestion-time authoritative and must not be backdated. The bridge turns a validated
PMXT v2 `PmxtV2ResearchLineage` (a bounded, content-addressed selection over existing
WP168 ordered event digests) into a provenance-separated `ExternalDatasetBinding`
(schema id `polymarket-external-dataset-binding`, source kind
`WP167_EXTERNAL_DATASET_DESCRIPTOR`, never `SOURCE_KIND_CANONICAL_PIT` and never a
`DatasetSnapshotReference`) and a standard WP170 `ResearchDatasetManifest` whose
external samples cite only bound `externalmember:sha256:` ids. External sample
availability is bound to `timestamp_received` / `ts_init`, never the source event
time. `ConvertedEventStream` identity, canonical `DatasetBinding` behavior, and the
`build_dataset_binding` signature are unchanged; one shared canonical row order/digest
implementation drives conversion and the research lineage.

`ExternalDatasetBinding` persists under the EXISTING `DATASET_BINDING` record kind by
exact `schema_id` subtype dispatch; `REGISTRY_FORMAT_ID`, `REGISTRY_SCHEMA_VERSION`,
`REGISTRY_APPLICATION_ID`, the SQLite schema, and the `DATASET_BINDING` CHECK
vocabulary are unchanged, and old canonical registries remain readable with no
migration. `build_preregistered_experiment` accepts either binding subtype with an
unchanged public signature and unchanged OOS/lifecycle semantics. Canonical PIT
authority unchanged: YES. Capital at risk: USD 0. Network/downloader/credentials/
paper/strategy/execution/live: NONE.

WP175-D002 / S10-DATA-02 closes only when WP175D is merged. The first post-WP175D
action is the separately gated S10-EVID-01 genuine strategy evidence production gate
(WP170 -> WP172 -> WP173), not automatic live activation. WP175 Gate-C activation
remains NOT AUTHORIZED and `LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE` remains
true until genuine evidence exists. Canonical WP176 Mature Controlled Live is NOT
renumbered, implemented, or authorized by WP175D and is NOT STARTED. Merge
authorized: NO. The normative capability contract is
`docs/external_historical_research_bridge_contract.md`.

## WP175 Restricted Live Canary (merged dormant via PR #178)

WP175 is the protected PR #178 implementation package on
`codex/wp175-restricted-live-canary`, based on merged WP174B PR #177. The
Side10-authorized 30-path package is `IMPLEMENTATION_READY` and Phase A/B implementation
is authorized for certified bytes; readiness does not authorize Gate-C
activation or merge. A3 is available only inside the manual foreground Gate-C
session after a single-use actual-clean-head arm receipt backed by the canonical
per-wallet ledger. Startup and restart remain
`A0_DISABLED`. The canary is one strategy, one binary market, LIMIT-only, one
create attempt, automatic bounded authoritative reconciliation, and the fixed risk envelope in
`docs/restricted_live_canary_contract.md`.

The genuine WP172/WP173 strategy qualification prerequisite is currently
`LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE`. No real secret, real CREATE,
venue mutation, or capital was used by implementation or tests; Gate-C
activation is pending a separate exact-head human decision. Capital at risk is
USD 0. WP176 remains the
separately gated owner of mature/unattended live operation and scaling.

Dormant merge versus live activation are distinct. The inert, fully disabled
Gate-C implementation is mergeable as dormant capability with
`FINAL_MERGE_SMOKE_CREATE_ATTEMPTS=0` — no real economic CREATE, secret, capital,
or strategy qualification is a merge prerequisite — pending a separate Karl
exact-head merge authorization, while live trading stays disabled and startup
stays `A0_DISABLED`. The single real CREATE
(`FIRST_LIVE_ACTIVATION_CANARY_CREATE_ATTEMPTS=1`) is reserved for the post-merge
first live activation canary. `LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE` is
therefore an activation-only blocker, not a dormant-merge blocker; producing
genuine qualification evidence depends on the separately gated external historical
research bridge recorded as deferred item WP175-D002 (Side10 ID S10-DATA-02),
which WP175 neither implements nor depends on.

Repo-truth files are authoritative project memory. They override chat memory, old handoffs, and ad hoc instructions unless explicitly updated by a later approved work package.

## Authority Hierarchy

1. `AGENTS.md` - AI coding agent rulebook and protected operating rules (shared; applies to Codex, Claude Code, and all future AI coding agents).
1b. `AI_CODING_AGENT_START_HERE.md` - shared startup entry point for all AI coding agents; mandatory startup sequence, precedence order, evidence mode rules, and stop rules. Read immediately after `AGENTS.md`.
2. `docs/project_charter.md` - project objective, scope, risk posture, and strategic direction.
3. `docs/project_status.md` - current phase, branch, merged WPs, and open decisions.
4. `docs/deferred_items_log.md` - deferred material issues, unavailable tools, blocked security checks, and postponed decisions.
5. `CODEX_START_HERE.md` - Codex-specific startup adapter; read after `AI_CODING_AGENT_START_HERE.md`.
5b. `CLAUDE_START_HERE.md` (see item 55) - Claude Code-specific startup adapter; read after `AI_CODING_AGENT_START_HERE.md`; includes Claude-specific posted evidence rules and stop rules.
6. `docs/ai/codex/README.md` - shared AI coding agent workflow guidance (historical path `docs/ai/codex/`; applies to Codex, Claude Code, and future agents unless a file says otherwise).
7. `docs/ai/codex/WP_EXECUTION_REPORT.md` - mandatory WP final report PR comment format.
8. `docs/ai/codex/VALIDATION_MATRIX.md` - package-class validation guidance.
9. `docs/ai/codex/PR_REVIEW_CHECKLIST.md` - Codex PR review discipline.
10. `docs/ai/codex/PROJECT_STATUS_UPDATE_RULES.md` - current-WP status wording rules.
11. `docs/ai/codex/PROTECTED_PATHS.md` - Codex protected path and boundary guidance.
12. `docs/source_repo_registry.md` - candidate external source repositories and audit status.
13. `docs/repo_reuse_strategy.md` - allowed external repo reuse paths and constraints.
14. `docs/repo_reuse_decision_matrix.md` - WP2 candidate repository reuse decisions.
15. `docs/official_python_client_dependency_decision.md` - WP14 official Python client dependency decision.
16. `docs/polymarket_client_boundary_review.md` - WP14 official client boundary rules.
17. `docs/ai_agent_integration_policy.md` - WP20 AI-agent advisory-only integration policy.
18. `docs/hermes_readonly_boundary.md` - WP20 Hermes read-only boundary and manual setup policy.
19. `docs/agent_model_registry.md` - WP20 allowed advisory agent role registry.
20. `docs/agent_context_export_schema.md` - WP21 read-only advisory agent context export schema contract.
21. `docs/agent_context_exporter.md` - WP23 local/offline/read-only agent context exporter boundary and usage.
22. `docs/agent_context_exporter_operator_runbook.md` - WP24 local operator runbook for safe manual exporter use.
23. `docs/agent_context_report_generator.md` - WP25 local/offline/read-only analyst report generator boundary and usage.
24. `docs/agent_context_report_operator_runbook.md` - WP26 local operator runbook for safe manual analyst report generation.
25. `docs/agent_hermes_manual_setup_decision_record.md` - WP27 decision record defining manual setup gates and approval steps before any future Hermes or agent runtime work.
26. `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` - WP28 token-efficiency operating model: context hygiene, validation-output summarization, concise reporting, reusable prompt-block rules, and future helper-tool design gates.
27. `docs/ai/codex/CONCISE_REPORTING_RULES.md` - WP28 mandatory concise final-report format and omission rules for Codex and Claude Code.
28. `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md` - WP28 reusable standard blocks for preflight, security, validation, reporting, safety, generated artifacts, and stop/escalation.
29. `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md` - WP29 design-only document for the local/offline/read-only diff scope summary helper; WP30 added implementation decisions in Section 14.
30. `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER.md` - WP30 user-facing reference for the implemented local/offline/read-only diff scope summary helper (`tools/git/diff_scope_summary.py`).
31. `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md` - WP31 design document for the local/offline/read-only validation-output summary helper; WP32 added implementation decisions in Section 17.
32. `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER.md` - WP32 user-facing reference for the implemented local/offline/read-only validation output summary helper (`tools/validation/validation_output_summary.py`).
33. `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md` - WP33 design document for the advisory code-index / blast-radius helper; WP34 added implementation decisions in Section 19.
34. `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER.md` - WP34 user-facing reference for the implemented local/offline/read-only code-index / blast-radius advisory helper (`tools/git/code_blast_radius.py`).
35. `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md` - WP35 design document for the local/offline/read-only memory/status snapshot helper; WP36 added implementation decisions in Section 19.
36. `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md` - WP36 user-facing reference for the implemented local/offline/read-only memory/status snapshot helper (`tools/git/status_snapshot.py`).
37. `docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md` - WP37 docs-only closeout for the WP28-WP36 token-efficiency helper sequence; defines advisory helper usage order, deferred helper gaps, protected-boundary reaffirmation, and the next-WP resumption gate.
38. `docs/local_advisory_handoff_package.md` - WP38 docs-only local advisory handoff package defining allowed advisory capabilities, forbidden runtime/trading capabilities, manual setup status, and the recommended post-WP38 path.
39. `docs/advisory_runtime_boundary_consumption_design.md` - WP39 docs-only advisory runtime boundary and local advisory consumption design for future local/offline/read-only advisory consumers.
40. `docs/local_advisory_consumer_prototype.md` - WP40 local/offline/read-only deterministic advisory consumer prototype usage and boundary reference.
41. `docs/advisory_prompt_runbook_package.md` - WP41 docs-only human-operated advisory prompt/runbook package for safe local/offline/read-only advisory use.
42. `docs/advisory_consumer_operator_workflow.md` - WP42 docs-only operator workflow hardening for safe human-operated use of the local advisory consumer and prompt/runbook package.
43. `docs/market_research_priority_scoring_layer.md` - WP44 docs-only design for the future local/offline/read-only Market Research Priority Scoring Layer; defines research_priority_score, allowed/forbidden inputs and outputs, score laundering risk, staleness/provenance requirements, human-review requirements, and future implementation gates. Updated in WP48 to reference the output contract.
44. `docs/market_research_priority_scoring_output_contract.md` - WP48 docs-only schema and output contract for the future local/offline/read-only Market Research Priority Scoring Layer; defines top-level output schema, market object schema, score components, advisory-only labels, staleness/provenance/missing-data contracts, forbidden fields, safe and invalid examples, and future implementation gates. Updated in WP49 to reflect core scorer on branch.
45. `src/data_layer/market_research_priority_scoring.py` - WP49 local/offline/read-only core scorer for the Market Research Priority Scoring Layer; stdlib-only, in-memory output only, no network, no file writes, no CLI, no export, no feature extraction, no advisory consumer integration, no runtime/product/trading behavior; implements compute_research_priority_score, build_market_research_priority_output, validate_market_research_priority_output, assert_market_research_priority_output, and contains_forbidden_output_fields per the WP48 contract.
46. `docs/research_data_foundation_direction.md` - WP50 docs-only direction lock recording final research-phase decisions after WP49 merge; authoritative for: final research-phase direction, approved near-term research-data foundation candidate sequence, blocked directions and non-signal boundaries, and onboarding future chats for scoring/research-foundation work. It does not override docs/project_status.md for current state, docs/deferred_items_log.md for deferred items, or docs/market_research_priority_scoring_output_contract.md for schema/output contract. Updated in WP51 to reflect WP50 merge and WP51 feature extraction foundation on branch.
47. `src/data_layer/market_research_priority_features.py` - WP51 local/offline/read-only feature extraction foundation; WP53 data-integrity hardening (provenance_degraded flag, provenance_weakness_reasons, provenance_warning, future_timestamp_detected, missing_question, missing_market_status detection); WP57 resolution ambiguity label feature extraction (build_resolution_ambiguity_label_index, resolution_ambiguity sub-dict in all market contexts, optional resolution_ambiguity_label_index parameter, optional resolution_ambiguity_labels parameter, optional resolution_ambiguity_label_path in extract_from_snapshot_dir); WP61 Microstructure Quality V1 metadata (`microstructure_quality` sub-dict in every market context, derived only from already supplied local OrderBookSnapshotRecord objects, advisory-only, no scorer weight change); WP62 Cross-Market Relationship Metadata V1 (`cross_market_relationships` sub-dict in every market context, deterministic metadata-only local key comparison — normalized question, condition_id, token_id, category+resolution_date, outcome-label set — no semantic matching, no price comparison, no automated equivalence claim, advisory-only, no scorer weight change); WP63 Resolution Source Hierarchy Metadata V1 (`resolution_source_hierarchy` sub-dict always present in every market context, deterministic local field presence checks — resolution_date for timing, question text for source text and URL pattern detection — no resolution-rule parsing, no source authority judgment, no official-source monitoring, advisory-only, no scorer weight change); stdlib-only plus existing local WP56 module, in-memory output only, no network, no file writes, no CLI, no export/report, no parser, no automated extraction, no scorer weight changes; bridges MarketMetadataSnapshotRecord, OrderBookSnapshotRecord, and SnapshotManifest objects into prepared run_context and market_context dicts compatible with the WP49 core scorer; implements build_manifest_index, index_order_books_by_token_id, build_cross_market_relationship_index, build_resolution_ambiguity_label_index, extract_market_research_priority_context, extract_market_research_priority_contexts, build_market_research_priority_run_context, and extract_from_snapshot_dir per the WP48 output contract, WP51 scope, WP53 hardening, WP57 feature extraction, WP61 microstructure metadata, WP62 cross-market relationship metadata, and WP63 resolution source hierarchy metadata.
48. `docs/long_term_bot_completion_roadmap.md` - WP52 docs-only long-term bot-completion roadmap and Side 4.0 onboarding lock (merged); authoritative for: long-term bot-completion roadmap, milestone and WP-range planning estimates, Side 4.0 onboarding context, and phase sequencing at planning level. Does not override `docs/project_status.md` for current state, `docs/deferred_items_log.md` for deferred items, `docs/research_data_foundation_direction.md` for locked near-term research-data direction, `docs/market_research_priority_scoring_output_contract.md` for score/output schema, or any future approved implementation WP. Planning guidance only — not authorization for any future phase.
48b. `docs/architecture_decision_record.md` - WP61 architecture direction lock-in; authoritative planning constraints only for SQLite first/Postgres deferred, Streamlit first/Grafana later/Next.js only if productizing, local development first/cheap VPS later, rules-based plus research-score-driven strategy first, LLM read-only analyst/proposal layer only, and phased execution ladder. It adds no implementation authority for database, dashboard, runtime, deployment, scheduler, credentials, paper/live trading, or execution behavior. Its WP61 "cheap VPS later" hosting shorthand is historical context only, superseded by the S10-DEPLOY-PLAN-01 Production VPS Hosting Direction Lock section of the same file and `docs/production_vps_hosting_direction.md`.
49. `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` - WP45 mandatory PR evidence reporting discipline for Codex and Claude Code; defines exact validation command requirements, no-ellipsis rule, network usage wording distinction, PR body and final comment consistency requirements, stale count correction gate, and reviewer action for evidence defects. Updated in WP54 with posted evidence self-check rule.
50. `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md` - WP46 user-facing reference for the local/offline/stdlib PR evidence consistency guard (`tools/git/pr_evidence_consistency_guard.py`); defines purpose, non-goals, CLI usage, guard checks, pass/fail behavior, limitations, and relationship to WP45 evidence reporting discipline. Updated in WP47 with new flags (K–O), required workflow, and WP47 hardening limitations. Updated in WP54 with posted evidence self-check limitation note and new flag P (`--require-guard-result`).
51. `docs/ai/codex/POSTED_PR_EVIDENCE_REVIEW_HARDENING.md` - WP47 optional reference doc describing the failure pattern from PR #47, current-final evidence marker, posted evidence vs draft evidence, why inline test counts are forbidden, reviewer workflow, Claude Code / Codex workflow, known limitation (no GitHub API fetch), and deferred WP47-D001.
52. `docs/ai/codex/WP_BUNDLING_POLICY.md` - WP54 bundled-WP execution policy; defines risk-class bundling principle, package size classes (S/M/L/XL), allowed and forbidden bundle examples, L-package requirements, stop/report triggers, follow-up process-defect classification categories, and posted evidence self-check rule.
53. `docs/resolution_ambiguity_taxonomy_manual_label_workflow.md` - WP55 docs-only resolution-rule ambiguity taxonomy and manual-label workflow for human research data quality; defines 14 taxonomy categories, 6 review status values, ambiguity severity tiers, reviewer confidence separation, 17-field manual label schema, local/offline/read-only manual review workflow, future integration gate, invalid/valid examples, and deferred items; research-data-quality metadata only; no parser, no automated extraction, no feature extraction, no scorer integration in WP55. Updated in WP56 to reflect WP55 merged and WP56 schema validation on branch. Updated in WP57 to reflect WP56 merged and WP57 local feature extraction from validated labels on branch; WP57 cross-reference added; automated parser remains not started.
47b. `src/data_layer/market_research_priority_review_queue.py` - WP64 local/offline/read-only stdlib research-output packaging module; implements `build_research_review_queue`, `build_local_human_review_report`, and `build_research_session_packet`; consumes prepared market_context dicts and/or scored market objects from the WP49/WP51–WP63 pipeline; produces in-memory human research triage objects only (queue packets, report, session packets); deterministic bucket assignment (REVIEW_FIRST, MANUAL_SOURCE_REVIEW_REQUIRED, REVIEW_LATER, DATA_QUALITY_BLOCKED, DEPRIORITIZED), deterministic sort (bucket priority, score descending, market_id ascending), advisory-only labels, compact sub-dict summaries of existing metadata; stdlib-only, no network, no file writes, no CLI, no export/report writer, no scorer weight change, no trading behavior.
54. `src/data_layer/resolution_ambiguity_labels.py` - WP56 local/offline/read-only stdlib schema validator for WP55 resolution ambiguity label records; validates all 17 required fields, allowed enum values, manual-review gate, advisory label, forbidden-use notice, source artifact references, and ISO-8601 timestamp; provides validate_resolution_ambiguity_label, validate_resolution_ambiguity_labels, and load_resolution_ambiguity_label_records; stdlib-only, no network, no file writes, no parser, no feature extraction, no scorer integration, no runtime behavior. Consumed by WP57 feature extraction.
55. `CLAUDE_START_HERE.md` - WP58 Claude Code startup guidance; mandatory startup sequence, Claude-specific posted evidence verification rules, and stop rules for workflow-only WPs. Updated in WP59 to reference the state machine, add drift prevention rule for private-repo evidence mode, and clarify that exit 3 is not itself a process defect. Updated in WP60A to be a Claude Code-specific adapter that references `AI_CODING_AGENT_START_HERE.md` for shared startup rules.
56. `docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md` - WP58 mandatory posted GitHub evidence verification policy. Updated in WP59 to define three evidence modes (PUBLIC_VERIFIER_PASS, PRIVATE_REPO_MANUAL_VERIFIED, BLOCKED_NOT_READY), required fields for each mode, and failure examples for false PASS reporting.
63b. `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` - WP59 canonical WP execution state machine; defines 13 phases (receive WP through post-merge reconciliation), three evidence modes, required fields per mode, evidence mode summary table, and cross-references; applies to Claude Code and Codex.
57. `docs/ai/codex/NEGATIVE_TEST_MATRIX_POLICY.md` - WP58 negative test matrix policy for WPs that add or modify validators, scorers, parsers, schema validators, boundary guards, evidence guards, or semantic wording filters; defines 15 required matrix categories and enforcement rules.
58. `tools/git/posted_pr_evidence_verifier.py` - WP58 read-only manual GitHub PR evidence verifier; checks live GitHub PR body and latest current-final evidence comment via the public GitHub REST API; no authentication, no write operations, workflow-only.
59. `tests/tools/git/test_posted_pr_evidence_verifier.py` - WP58 focused tests for the posted PR evidence verifier using fake GitHub API responses; no real network in unit tests.
60. `tests/test_posted_github_evidence_workflow_docs.py` - WP58 docs workflow tests for posted GitHub evidence verification policy and workflow files.
61. `tests/test_negative_test_matrix_policy_docs.py` - WP58 docs tests for the negative test matrix policy.
62. `tests/test_claude_start_here_docs.py` - WP58 docs tests for CLAUDE_START_HERE.md startup guidance.
62b. `tests/test_market_research_priority_review_queue.py` - WP64 focused tests for the local/offline/read-only research review queue, local human review report, and research session packet; 62 tests covering module safety, bucket logic, sort order, review reasons, caution flags, report summary counts, session packet structure, non-signal boundary, advisory labels, and scorer compatibility.
62c. `tools/research_queue/local_research_queue_export.py` - WP65 local/offline/read-only stdlib manual export CLI; consumes WP64 LOCAL_HUMAN_REVIEW_REPORT_V1 objects or lists of market context dicts; produces deterministic JSON or Markdown output to stdout or an explicit local path; supports --input, --format json|markdown, --output, --generated-at-utc, --max-items; no network, no credentials, no scheduler, no database, no dashboard, no advisory consumer integration, no scoring changes; advisory-only; human-operated only; exit codes: 0=success, 1=validation error, 2=unsafe output path.
62d. `tests/tools/research_queue/test_local_research_queue_export.py` - WP65 focused tests for the local research queue export tool; 26 tests covering JSON/Markdown output, WP64 report passthrough, --output to tmp_path, error exits (missing file, non-JSON, unsupported format, unsafe path), advisory/forbidden notices, bucket grouping, report shape, no forbidden wording, no network imports, no credentials, no database imports, WP64 compatibility, scorer compatibility, generated_at override, max-items cap, and module safety.
62e. `docs/research_queue_operator_runbook.md` - WP65 operator runbook for safe manual use of the local research queue export tool; covers purpose, advisory notice, preconditions, example commands, supported flags, input expectations, output expectations, bucket reading guide, safe manual review workflow, non-signal boundary, forbidden interpretations, troubleshooting, and what the tool does not do.
62f. `docs/calibration_harness_design.md` - WP66 local/offline/read-only calibration harness design; defines calibration purpose (research-usefulness audit, not trading performance), calibration unit (one market context at one snapshot time), allowed calibration metrics, forbidden metrics, human review usefulness labels, snapshot timing offset requirements, calibration gates, non-signal boundary, and future implementation phases (Phase 1 design only in WP66). Calibration output is research-usefulness audit data only; not a signal, not a backtest, not a profitability measure.
62g. `docs/resolved_outcome_data_requirements.md` - WP66 local/offline/read-only resolved outcome data requirements design; defines minimum required fields for a future resolved outcome record (market_id, condition_id, resolved_outcome, resolution_status, resolution_time_utc, resolution_source_url_or_reference, resolution_source_type, resolution_rule_text_snapshot_available, resolution_dispute_or_ambiguity_flag, final_market_status, outcome_token_mapping_verified), resolution status values, resolution source type values, non-signal boundary, local/offline scope constraint, and relationship to calibration record. Resolved outcome ingestion not implemented; no API calls authorized.
62h. `docs/schemas/calibration_record_v1.example.json` - WP66 static advisory-only example calibration record schema; shows identity, snapshot metadata, research queue state, resolved outcome, human review, and calibration validity fields; contains no trading/PnL/performance fields; marked ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT and DESIGN_ONLY_NOT_IMPLEMENTED.
62i. `src/data_layer/calibration_record_validation.py` - WP67 local/offline/read-only stdlib calibration record schema validator; implements `validate_calibration_record(record) -> CalibrationRecordValidationResult`; validates required top-level sections (_notice, _schema_version, _status, identity, snapshot_metadata, research_queue_state, resolved_outcome, human_review, calibration_validity), required sub-fields, enum values (snapshot offsets, research queue buckets, resolution statuses, resolution source types, human review usefulness labels), type checks (string, bool, int/float, list), and forbidden trading/performance key detection (pnl, profit, roi, expected_return, win_rate, sharpe, trade_signal, buy, sell, position_size, entry, exit, fill_probability, slippage, edge, alpha, opportunity, arbitrage); result is a frozen dataclass; no network, no file writes, no ingestion, no report generator, stdlib-only.
62j. `tests/test_calibration_record_validation.py` - WP67 focused tests for the calibration record schema validator; 104 tests covering: valid example schema passes, missing top-level sections, missing identity/snapshot/resolved-outcome fields, invalid enum values (offsets, buckets, resolution statuses, source types, usefulness labels), research_priority_score bounds and None-when-excluded, forbidden trading/performance key detection (pnl, expected_return, all forbidden keys, nested keys), outcome_token_mapping_verified False warning, result frozen/deterministic, no network imports, no file writes, no local_data/.env references.
62k. `src/data_layer/resolved_outcome_fixture_loader.py` - WP68 local/offline/read-only stdlib resolved outcome fixture loader; implements `load_resolved_outcome_fixtures(path) -> ResolvedOutcomeFixtureLoadResult`; accepts explicit local path to a single JSON object file, a JSON list file, or a direct-child *.json directory; validates each loaded record with `validate_calibration_record` from WP67; returns frozen deterministic `ResolvedOutcomeFixtureLoadResult` and `LoadedCalibrationRecord` dataclasses with loaded/valid/invalid/warning counts; rejects URL-like paths, unsupported extensions, missing paths, invalid JSON, and non-object list entries; does not scan directories recursively; does not fetch outcomes from any network source; does not compute calibration metrics, trading performance, or signal quality; does not write files; no network, no credentials, stdlib-only.
62l. `tests/test_resolved_outcome_fixture_loader.py` - WP68 focused tests for the resolved outcome fixture loader; 37 tests covering: single valid JSON object, JSON list in list order, directory sorted by filename, non-recursive directory behavior, missing path error, invalid JSON error, unsupported extension rejection, URL-like path rejection, non-object list entry error, invalid record counted invalid via WP67 validator, warning counts included, frozen dataclasses, no network imports, no credential/auth imports, no file write calls, no recursive scan patterns, no forbidden metric fields, no forbidden metric imports, WP67 validator compatibility, source path matches input, empty directory error, multiple/mixed valid/invalid counts, advisory label presence, non-json files ignored, list order preserved, tuple types, string/Path equivalence, empty JSON object invalid, forbidden key produces validator warning, docs compatibility imports.
62m. `docs/calibration_report_generator_design.md` - WP69 local/offline/read-only calibration report generator design; defines report purpose (research-usefulness audit only, not profitability/trading/backtest/paper-live/signal report); allowed inputs from WP68/WP67 components (validated calibration records, human review usefulness labels, research queue buckets, data-quality fields, snapshot timing metadata); forbidden inputs (account trades, positions, orders, fills, wallet balances, execution logs, paper/live ledger, PnL fields); safe report sections (report identity, input summary, validation summary, coverage summary, missingness summary, staleness summary, resolution-source completeness, manual-review burden, bucket summary, human-review usefulness label summary, post-resolution audit warnings, excluded-record summary, data-quality notes, forbidden interpretation notice, future work); report output contract (LOCAL_CALIBRATION_REPORT_V1, ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT, report_scope flags, input_summary, validation_summary, coverage_summary, missingness_summary, staleness_summary, resolution_source_summary, manual_review_summary, bucket_summary, human_review_usefulness_summary, excluded_record_summary, warnings, forbidden_interpretation_notice); allowed metrics (record_count, valid_record_count, invalid_record_count, warning_count, coverage_rate, missing_required_field_rate, staleness_rate, manual_review_required_rate, source_metadata_available_rate, resolution_source_missing_rate, ambiguity_review_required_rate, bucket_distribution, human_review_usefulness_label_distribution, excluded_record_count, post_resolution_audit_warning_count); forbidden metrics (profit, PnL, ROI, expected return, Sharpe, win rate, trade hit rate, fill quality, slippage, edge, alpha, arbitrage, strategy return, portfolio return); human interpretation guidance (allowed: research usefulness, data quality, bucket coverage; forbidden: trading signal, expected return, position sizing, profitability); future phases (Phase 5 metric computation NOT STARTED, Phase 6 report generator NOT STARTED, Phase 7 human review workflow NOT STARTED); no implementation authorized.
62n. `docs/schemas/calibration_report_v1.example.json` - WP69 static advisory-only example calibration report output shape; shows report_type (LOCAL_CALIBRATION_REPORT_V1), advisory_label (ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT), report_scope flags, input_summary, validation_summary, coverage_summary, missingness_summary, staleness_summary, resolution_source_summary, manual_review_summary, bucket_summary, human_review_usefulness_summary, excluded_record_summary, warnings, post_resolution_audit_warning_count, and forbidden_interpretation_notice; contains no trading/PnL/performance/strategy/portfolio/edge/alpha fields; marked ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT and DESIGN_ONLY_NOT_IMPLEMENTED.
62o. `tests/test_calibration_report_design_docs.py` - WP69 focused tests for the calibration report generator design docs; covers: design doc existence, research-usefulness purpose, non-trading/non-profitability/non-backtest/non-paper-live statements, allowed input categories defined, forbidden input categories excluded, safe report sections, output contract fields, allowed metrics, forbidden metrics (PnL/ROI/expected-return/win-rate/Sharpe), non-signal boundary section, human interpretation guidance, future phases deferred, schema no-forbidden-trading-fields, project status WP68 merged and WP69 on branch, repo truth index includes new docs, deferred items WP69-D001 through WP69-D004, protected boundaries unchanged, architecture boundary no new src/tools files. Updated in WP70 to reflect WP69 merged and WP70 calibration metric computation on branch. Updated in WP71 to include calibration_report_generator.py file existence check.
62p. `src/data_layer/calibration_metric_computation.py` - WP70 local/offline/read-only stdlib calibration metric computation helper; implements `compute_calibration_metrics(records) -> CalibrationMetricComputationResult` and `compute_calibration_metrics_from_load_result(load_result) -> CalibrationMetricComputationResult`; accepts raw calibration record dicts or WP68 `ResolvedOutcomeFixtureLoadResult`; uses WP67 validator for per-record valid/invalid/warning counts; computes allowed research-quality metrics only: record_count, valid_record_count, invalid_record_count, warning_count, coverage_rate, missing_required_field_rate, staleness_rate, manual_review_required_rate, source_metadata_available_rate, resolution_source_missing_rate, ambiguity_review_required_rate, bucket_distribution, human_review_usefulness_label_distribution, excluded_record_count, post_resolution_audit_warning_count; result is a frozen deterministic dataclass with advisory label and warnings tuple; conservative high-rate warnings (no_records, all_records_invalid, missing_required_field_rate_high, resolution_source_missing_rate_high, manual_review_required_rate_high) at threshold 0.5; does not compute profit, PnL, ROI, expected return, win rate, Sharpe, or any trading/performance metric; does not read or write files; does not access the network; stdlib-only, no credentials.
62q. `tests/test_calibration_metric_computation.py` - WP70 focused tests for the calibration metric computation helper; 75 tests covering: empty input zero counts/rates and no_records warning, one valid record coverage_rate=1.0, one invalid record missing_required_field_rate=1.0, mixed valid/invalid counts and rates, missing_required_field_rate_high warning trigger, manual_source_review_required flag rate, resolution_ambiguity_manual_review_required flag rate, source_metadata_available rate, resolution_source_missing rate and warning trigger, bucket_distribution sorted correctness, human_review_usefulness_label_distribution sorted correctness, excluded_record_count, post_resolution_audit_warning_count (dispute flag and outcome_token_mapping_verified=False), frozen dataclass, deterministic warnings tuple, no network library imports, no file read/write patterns, no credential usage patterns, no forbidden trading/performance output fields, WP67 validator compatibility, WP68 loader compatibility, calibration report design compatibility (no report generator imports), project status module importable, dataclass field completeness, compute_calibration_metrics_from_load_result compatibility, staleness rate stale/valid/missing offset.
62r. `src/data_layer/calibration_report_generator.py` - WP71 local/offline/read-only stdlib calibration report generator; implements `build_calibration_report(records) -> LocalCalibrationReport` and `build_calibration_report_from_load_result(load_result) -> LocalCalibrationReport`; accepts raw calibration record dicts or WP68 `ResolvedOutcomeFixtureLoadResult`; uses WP70 `compute_calibration_metrics` and `compute_calibration_metrics_from_load_result` to populate sections without duplicating metric logic; frozen `LocalCalibrationReport` dataclass with all WP69 design sections (report_type LOCAL_CALIBRATION_REPORT_V1, advisory_label ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT, report_scope safety booleans, input_summary, validation_summary, coverage_summary, missingness_summary, staleness_summary, resolution_source_summary, manual_review_summary, bucket_summary, human_review_usefulness_summary, excluded_record_summary, warnings tuple, forbidden_interpretation_notice); FORBIDDEN_REPORT_FIELDS frozenset exposed for boundary tests; does not read or write files; does not access the network; does not compute trading/performance metrics; stdlib-only, no credentials.
62s. `tests/test_calibration_report_generator.py` - WP71 focused tests for the calibration report generator; 61 tests covering: empty input report type/advisory label/warnings/input_summary/forbidden notice, report scope safety booleans (local_offline_read_only/no_network/no_trading/no_profitability_metrics/no_paper_trading/no_live_trading/no_order_or_position_inputs/no_file_writes/no_strategy_output), valid records input_summary and coverage_rate, invalid records missingness_summary and all_records_invalid warning, stale records staleness_rate, missing resolution source rate, manual review required rate, ambiguity review rate, bucket_distribution pass-through, human_review_usefulness_label_distribution pass-through, excluded_record_count, post_resolution_audit_warning_count, metric warnings in report warnings, sorted/deterministic warnings tuple, forbidden interpretation notice (advisory-only/not-trading/not-backtest/not-profitability wording), frozen dataclass immutability, equal reports on equal input, all required section fields, no network library imports, no file write patterns, no credential patterns, FORBIDDEN_REPORT_FIELDS constant, dataclass fields not in forbidden set, report summary keys not in forbidden set, load_result integration, WP70/WP68/WP67 compatibility.
62t. `tools/calibration/local_calibration_report_export.py` - WP72 local/offline/read-only stdlib manual export CLI; uses WP68 `load_resolved_outcome_fixtures` for input loading and WP71 `build_calibration_report_from_load_result` for in-memory report generation; supports --input (single JSON object file, JSON list file, or direct-child *.json directory), --format json|markdown, --output (optional explicit local path; stdout default), --include-invalid-records; output path safety guard rejects writes into src/, tests/, docs/, tools/, .github/ and symlink-resolved tracked directories; exit codes: 0=success, 1=load or format error, 2=unsafe output path; advisory-only; no scheduler, no daemon, no database, no dashboard, no network, no credentials, no paper/live trading, stdlib-only.
62u. `tests/tools/calibration/test_local_calibration_report_export.py` - WP72 focused tests for the local calibration report export tool; 26 tests (1 skipped on Windows for symlink) covering: single JSON object to JSON stdout, JSON list to JSON stdout, directory of *.json files to JSON stdout, markdown output to stdout, JSON to explicit tmp_path file, markdown to explicit tmp_path file, unsupported format exit, missing input exit 1, URL-like input exit 1, unsafe output path src/ exit 2, absolute docs/ path exit 2, symlink-to-tracked-dir exit 2 (or skip), advisory notice in markdown, forbidden interpretation notice in markdown, all required markdown sections, all required WP71 JSON fields, no forbidden trading/performance JSON keys, no network library imports, no credential imports, no scheduler import patterns, no recursive directory scan, no source module modification, calibration_report_generator importable, calibration_metric_computation importable, resolved_outcome_fixture_loader importable, calibration_record_validation importable, record count correctness.
62v. `docs/calibration_report_operator_runbook.md` - WP72 operator runbook for safe manual use of the local calibration report export tool; covers purpose, advisory notice, prerequisites, local input fixture expectations (single JSON object, JSON list, direct-child *.json directory), JSON example command, markdown example command, stdout behavior, explicit output path behavior, recommended ignored output location under local_data/calibration_reports/, how to read report sections, what the report does not mean, forbidden interpretations, troubleshooting, no network, no credentials, no scheduler, no dashboard/database, no trading.
62w. `docs/human_review_label_workflow_design.md` - WP73 design-only human review label workflow for local calibration records; defines manual research-usefulness labeling purpose (not trade/profitability/buy-sell), label unit and identity fields, allowed human review usefulness labels (USEFUL_RESEARCH_TARGET, PARTIALLY_USEFUL_RESEARCH_TARGET, NOT_USEFUL_DATA_TOO_WEAK, NOT_USEFUL_RESOLUTION_TOO_AMBIGUOUS, NOT_USEFUL_DUPLICATE_OR_OVERLAP, NOT_REVIEWED, REVIEW_BLOCKED_INSUFFICIENT_CONTEXT), confidence labels (LOW/MEDIUM/HIGH/NOT_APPLICABLE), primary reasons, reason fields (primary_reason, secondary_reasons, review_notes, confidence_level, requires_followup_review), workflow states (NOT_REVIEWED/IN_REVIEW/LABEL_APPLIED/NEEDS_SECOND_REVIEW/EXCLUDED_FROM_CALIBRATION), quality gates, allowed/forbidden calibration uses, and future implementation phases; no implementation authorized; no source/tools/network/credentials changes.
62x. `docs/schemas/human_review_label_record_v1.example.json` - WP73 static advisory-only example human review label record schema; shows _notice (ADVISORY_ONLY_MANUAL_RESEARCH_REVIEW_LABEL), _schema_version, _status, identity (market_id/condition_id/question/snapshot_time_utc), review (review_time_utc/reviewer_id_or_alias/workflow_state/human_review_usefulness_label/confidence_level/primary_reason/secondary_reasons/requires_followup_review/review_notes), and safety (manual_only/not_automated/no_trading_signal/no_score_change/no_execution) sections; no trading/PnL/performance fields; marked ADVISORY_ONLY_MANUAL_RESEARCH_REVIEW_LABEL and DESIGN_ONLY_NOT_IMPLEMENTED.
62y. `tests/test_human_review_label_workflow_docs.py` - WP73 focused docs tests for the human review label workflow design; covers design doc existence, manual research-usefulness purpose, non-trade/non-profitability/non-buy-sell statements, label unit and identity fields, allowed usefulness labels, workflow states, confidence labels, primary reasons, quality gates, calibration uses and forbidden uses, future implementation phases, schema existence and required fields, safety flags, no-forbidden-trading-fields, project status WP73 merged and WP74 on branch, repo truth index includes new docs and validator, deferred items WP73-D001 through WP73-D004, protected boundaries unchanged, and no dependency files modified. Updated in WP74 to reflect WP73 merged and WP74 validator on branch.
62z. `src/data_layer/human_review_label_validation.py` - WP74 local/offline/read-only stdlib human review label record validator; implements `validate_human_review_label_record(record) -> HumanReviewLabelValidationResult`; validates required top-level sections (_notice, _schema_version, _status, identity, review, safety), required identity fields (market_id, condition_id, question, snapshot_time_utc), required review fields (review_time_utc, reviewer_id_or_alias, workflow_state, human_review_usefulness_label, confidence_level, primary_reason, secondary_reasons, requires_followup_review, review_notes), allowed enum values (workflow states: NOT_REVIEWED/IN_REVIEW/LABEL_APPLIED/NEEDS_SECOND_REVIEW/EXCLUDED_FROM_CALIBRATION; forbidden workflow states: AUTO_LABELED_BY_LLM/AUTO_LABELED/LLM_LABELED; usefulness labels: USEFUL_RESEARCH_TARGET/PARTIALLY_USEFUL_RESEARCH_TARGET/NOT_USEFUL_DATA_TOO_WEAK/NOT_USEFUL_RESOLUTION_TOO_AMBIGUOUS/NOT_USEFUL_DUPLICATE_OR_OVERLAP/NOT_REVIEWED/REVIEW_BLOCKED_INSUFFICIENT_CONTEXT; confidence levels: LOW/MEDIUM/HIGH/NOT_APPLICABLE; primary reasons: SOURCE_CLARITY/RESOLUTION_RULE_CLARITY/DATA_COMPLETENESS/MARKET_OVERLAP_CONTEXT/QUEUE_BUCKET_RELEVANCE/AMBIGUITY_TOO_HIGH/SOURCE_MISSING/OUTCOME_MAPPING_UNCLEAR/DUPLICATE_OR_OVERLAP/NOT_ENOUGH_CONTEXT), required safety flags all True (manual_only/not_automated/no_trading_signal/no_score_change/no_execution; safety section excluded from forbidden-key scan), cross-field rules as invalid or warning (LABEL_APPLIED+NOT_REVIEWED label → invalid; NOT_REVIEWED workflow+non-NOT_REVIEWED label → warning; LABEL_APPLIED+NOT_APPLICABLE confidence → invalid; NEEDS_SECOND_REVIEW+requires_followup_review=False → warning), forbidden key scan (pnl/profit/roi/expected_return/win_rate/sharpe/trade_signal/buy/sell/position_size/entry/exit/fill_probability/slippage/edge/alpha/opportunity/arbitrage/auto_label/llm_label/automated_label/score_change/execution), forbidden string value scan (AUTO_LABELED_BY_LLM/TRADE_SIGNAL/BUY/SELL/PROFITABLE); result is a frozen deterministic dataclass; stdlib-only, no network, no file reads/writes, no credentials, no LLM/agent libraries.
62z2. `tests/test_human_review_label_validation.py` - WP74 focused tests for the human review label record validator; 77 tests covering: valid example schema passes, valid base record passes, missing top-level identity/review/safety sections fail, missing identity.market_id/condition_id/snapshot_time_utc fail, missing review.reviewer_id_or_alias/review_time_utc fail, invalid workflow_state fails, AUTO_LABELED_BY_LLM workflow state fails, invalid usefulness label fails, invalid confidence level fails, invalid primary reason fails, secondary_reasons must be list, invalid secondary reason fails, requires_followup_review must be bool, missing safety flag fails (all flags), safety flag false fails (all flags), LABEL_APPLIED+NOT_REVIEWED label fails, NOT_REVIEWED workflow+other label warns, NEEDS_SECOND_REVIEW+followup_false warns, forbidden key pnl/expected_return/profit flagged, forbidden automation value AUTO_LABELED_BY_LLM flagged, safety.no_execution allowed (not flagged), result frozen and deterministic, no network imports, no file I/O, no credentials, no LLM imports, parametrized valid enum values, advisory label presence, empty record fails, wrong _notice/_schema_version invalid.
62z3. `src/data_layer/human_review_label_fixture_loader.py` - WP75 local/offline/read-only stdlib human review label fixture loader; implements `load_human_review_label_fixtures(path) -> HumanReviewLabelFixtureLoadResult`; accepts explicit local path to a single JSON object file, a JSON list file, or a direct-child *.json directory; validates each loaded record with `validate_human_review_label_record` from WP74; returns frozen deterministic `HumanReviewLabelFixtureLoadResult` and `LoadedHumanReviewLabelRecord` dataclasses with loaded/valid/invalid/warning counts; rejects URL-like paths, unsupported extensions, missing paths, invalid JSON, and non-object list entries; does not scan directories recursively; does not create or edit labels; does not automate labels or use LLM/agent labeling; does not fetch data from any network source; does not compute calibration metrics, trading performance, or signal quality; does not write files; no network, no credentials, stdlib-only.
62z4. `tests/test_human_review_label_fixture_loader.py` - WP75 focused tests for the human review label fixture loader; 47 tests covering: single valid JSON object, JSON list in list order, directory sorted by filename, non-recursive directory behavior, missing path error, invalid JSON error, unsupported extension rejection (txt, jsonl), URL-like path rejection (http, https, ftp), non-object list entry error, invalid record counted invalid via WP74 validator, warning counts included (cross-field violation), frozen dataclasses (result, record, validation), no network imports, no file write calls, no credential/auth/env imports, no LLM/agent imports, no recursive scan patterns, no label creation/editing, no forbidden metric fields, no trading metric source patterns, WP74 validator compatibility, WP73 docs compatibility, project status/docs compatibility, tuple types, source path matching, string/Path equivalence, empty JSON object invalid, empty directory error, non-json files ignored, multiple valid counts, mixed valid/invalid counts, list order preserved, advisory label presence, forbidden key produces validator warning, no metric computation imports, ftp URL rejected, loaded record source path matching, directory sort order verified, empty list zero records.
62z5. `docs/wallet_intelligence_research_signal_roadmap.md` - WP76 docs-only wallet intelligence research signal roadmap; defines wallet intelligence as a first-class research signal layer (not a blind copy-trading engine); core locked decision (wallet activity may increase research priority but must not directly trigger live execution); six research pillars; five wallet intelligence jobs; required wallet metrics (realized/unrealized profit, trade count, market count, trade sizes, profit by category/holding period/liquidity, profit before/after news, entry vs price/resolution, copy-after-1s/5s/30s/2m/10m PnL, max drawdown, largest win/loss); wallet signal categories (SPECIALIST_ENTRY, MULTI_WALLET_CLUSTER, EARLY_ENTRY_BEFORE_PRICE_MOVE, LATE_CHASER, MARKET_MAKER_FLOW, ARBITRAGE_FLOW, SUSPICIOUS_TIMING, LOW_SAMPLE_OUTLIER, UNCOPYABLE_FAST_FLOW); copyability delay principle and required delay windows (1s/5s/30s/2m/10m); research queue influence target range 25%–35%, direct trade-decision influence 0% until authorization; suspicious-flow boundary (SUSPICIOUS_TIMING → human-review-required only); near-term roadmap WP77–WP82; explicit non-goals (no auto copy-trading, live execution, order placement, cancels, position sizing, risk override, parameter auto-change, strategy auto-approval, credentials, network ingestion, wallet API client, dashboard, scheduler, bot loop, Hermes/LLM execution authority); future live boundary conditions (requires delayed-copy evidence, paper-trading evidence, risk-gate approval, live-trading authorization, credential boundary, execution gateway, kill switch, monitoring, human approval); deferred items WP76-D001 through WP76-D007; planning guidance only, not authorization for any future implementation.
62z6. `tests/test_wallet_intelligence_roadmap_docs.py` - WP76 focused docs tests for the wallet intelligence research signal roadmap; covers: roadmap doc exists, research signal layer not blind copy-trading, wallet activity may affect research priority, wallet activity must not directly trigger live execution, five wallet intelligence jobs, all required wallet metrics, all five delay windows (1s/5s/30s/2m/10m), copyability constraint factors (spread/slippage/fees/liquidity/size), all nine wallet signal categories, suspicious-flow boundary with human-review-required, research-queue influence range 25%–35%, direct trade-decision influence 0%, near-term WP77–WP81 in roadmap, forbidden auto copy-trading/live execution/order placement/cancels/position sizing/risk override/parameter auto-change/credentials/scheduler/bot loop/dashboard/Hermes-LLM execution authority, repo truth index references roadmap doc and test file, deferred items WP76-D001 through WP76-D007, WP76 as current phase/branch, WP75 merged with PR #76 merge commit, protected boundaries unchanged (live trading disabled, credentials not used, execution not started, agent execution authority forbidden), no wallet src/ modules, no wallet tools/ client, no wallet dependencies.
62z7. `docs/wallet_intelligence_architecture_and_signal_contract.md` - WP77 docs-only wallet intelligence architecture and signal contract; defines wallet intelligence as advisory research-signal architecture only; documents architecture position, future watched-wallet registry concepts, allowed and forbidden registry statuses, profile contract groups, wallet signal fields, allowed signal categories, allowed research-priority effects, forbidden trade-like effect values, copyability statuses, suspicious-flow boundary, safety flags, future sequence WP78-WP82, and non-goals. It authorizes no wallet loader, no wallet API client, no network ingestion, no real wallet monitoring, no automatic copy-trading, no paper/live trading, no credentials, no execution, no scheduler, no bot loop, no dashboard, and no Hermes/LLM execution authority.
62z8. `docs/schemas/wallet_intelligence_profile_v1.example.json` - WP77 static advisory-only wallet profile design example; placeholder wallet identity only; includes identity, sample_size, profitability, specialization, entry_quality, copyability, risk, signal_policy, review, and safety sections; safety flags all true; design example only, not a validator or implementation.
62z9. `docs/schemas/wallet_intelligence_signal_contract_v1.example.json` - WP77 static advisory-only wallet signal contract design example; placeholder wallet identity only; includes signal, wallet_reference, market_reference, observation, classification, research_priority_effect, copyability_context, and safety sections; direction_observed is historical observation only and not a buy/sell instruction; safety flags all true; design example only, not a validator or implementation.
62z10. `tests/test_wallet_intelligence_architecture_contract_docs.py` - WP77 focused docs/schema tests for the wallet intelligence architecture/profile/signal contract; parses static JSON examples, verifies required doc sections and status lists, enforces safety flags, checks no forbidden exact trade-like keys in examples, verifies repo-truth/deferred/status references, and checks the WP77 diff does not touch src/, tools/, dependency files, or lock files.
62z11. `docs/wallet_trade_event_snapshot_schema.md` - WP78 local/offline wallet trade event snapshot schema and loader/validator contract; defines wallet trade events as advisory observations only, required sections and fields, allowed source types, allowed historical direction values, safety flags, validation behavior, explicit local loader inputs, non-recursive directory loading, and forbidden scope. It authorizes no network/API ingestion, no credentials, no wallet monitoring, no copyability simulation, no wallet skill profiling, no research queue integration, no paper/live trading, and no execution behavior.
62z12. `docs/schemas/wallet_trade_event_snapshot_v1.example.json` - WP78 static advisory-only wallet trade event snapshot example; placeholder wallet identity only; includes event, wallet_reference, market_reference, observation, context, review, and safety sections; safety flags all true; design example only, not a live data source or execution input.
62z13. `src/data_layer/wallet_trade_event_fixtures.py` - WP78 local/offline/read-only stdlib wallet trade event fixture validator and explicit-path loader; implements `validate_wallet_trade_event_snapshot` and `load_wallet_trade_event_fixtures`; accepts single JSON object files, JSON list files, or direct-child `*.json` directories; rejects URL-like paths, unsupported extensions, invalid JSON, and non-object list entries; validates required fields, allowed source types, allowed historical directions, safety flags, forbidden trade-like keys, and credential-like keys; frozen deterministic dataclasses; no network, no file writes, no credentials, no wallet API client, no monitoring, no skill scoring, no copyability, no research queue integration, no strategy, no paper/live PnL, and no execution behavior.
62z14. `tests/test_wallet_trade_event_fixtures.py` - WP78 focused tests for the wallet trade event schema example, validator, loader, negative-test matrix, deterministic counts, frozen dataclasses, non-recursive directory loading, URL rejection, module safety boundaries, and forbidden computation/non-execution constraints.
62z15. `src/data_layer/wallet_signal_research_profile.py` - WP79 local/offline/read-only stdlib wallet signal research profile builder; implements `build_wallet_signal_research_profiles` and `build_wallet_research_queue_annotations`; consumes only WP78 validated `LoadedWalletTradeEventRecord` objects; groups records by (wallet_id_or_address, market_id, condition_id); produces deterministic advisory `WalletSignalResearchProfile` and `WalletResearchQueueAnnotation` frozen dataclasses with sample_size_status, signal_category, wallet_specialization_match, suspicious_flow_status, copyability_status, research_priority_effect, human_review_required, warnings, advisory labels, and advisory notice; FORBIDDEN_OUTPUT_VALUES frozenset guards all outputs; no network, no file writes, no credentials, no LLM/agent libraries, no copyability PnL, no buy/sell signals, no scoring weight changes, no paper/live trading, stdlib-only.
62z16. `docs/wallet_signal_research_profile.md` - WP79 advisory-only wallet signal research profile doc; states profiles are advisory research metadata only, derived from local WP78 fixture records, do not prove wallet skill or copyability, do not fetch network data, do not create trade recommendations, suspicious flow is research-watch-only or human-review-required, direct live execution remains forbidden.
62z17. `tests/test_wallet_signal_research_profile.py` - WP79 focused tests for the wallet signal research profile builder, annotation builder, advisory labels, frozen dataclasses, deterministic sort, no forbidden trade-like values in outputs, no network imports, no file writes, no credential imports, no LLM imports, no PnL computation, docs checks, repo-truth and deferred-items checks, project status reconciliation.
62z18. `docs/wallet_copyability_delay_simulator_design.md` - WP80 docs-only copyability delay simulator design; defines core copyability delay principle (wallet not copyable unless delayed-copy evaluation remains favorable after realistic delay, spread, slippage, fees, liquidity limits, and size constraints); required delay windows (1s/5s/30s/2m/10m); allowed evaluation inputs (local/offline validated fixtures only); forbidden inputs (live API wallet feed, authenticated account data, real-time order placement, private keys, execution feed, scheduler loop); required constraint factors (spread, slippage, fees, liquidity, size); allowed advisory output fields; allowed advisory evaluation statuses (NOT_EVALUATED/INSUFFICIENT_CONTEXT/RESEARCH_PROMISING/RESEARCH_WEAK/UNCOPYABLE_FAST_FLOW/UNCOPYABLE_TOO_ILLIQUID/SUSPICIOUS_FLOW_DO_NOT_COPY/HUMAN_REVIEW_REQUIRED); forbidden output fields (BUY/SELL/TRADE/EXECUTE/OPEN_POSITION/CLOSE_POSITION/POSITION_SIZE/EXPECTED_RETURN/PROFIT_TARGET/STOP_LOSS/TAKE_PROFIT/LIVE_SIGNAL/AUTO_COPY/PNL_TARGET); suspicious-flow boundary (must not become a strategy to follow privileged or suspicious information); forbidden implementation scope; future WP sequence (WP81-WP84); safety flags all true. Design guidance only, not implementation authorization.
62z19. `docs/wallet_intelligence_report_contract.md` - WP80 docs-only wallet intelligence report contract; defines a wallet intelligence report as a human review report (not a trade recommendation, not a buy/sell signal, not a position sizing output, not a copy-trading instruction); required report sections (report_identity, input_summary, wallet_signal_summary, copyability_delay_design_summary, research_queue_implications, suspicious_flow_review, limitations, deferred_items, safety); forbidden report content (BUY/SELL/TRADE/EXECUTE/OPEN_POSITION/CLOSE_POSITION/POSITION_SIZE/EXPECTED_RETURN/PROFIT_TARGET/STOP_LOSS/TAKE_PROFIT/LIVE_SIGNAL/AUTO_COPY/PNL_TARGET); suspicious-flow boundary in reports (must not become a strategy to follow privileged or suspicious information; required_action=HUMAN_REVIEW_REQUIRED; blocked_from_automation=true); safety flags all true; future WP sequence (WP81-WP84). Contract design only; report generator deferred to WP82.
62z20. `docs/schemas/wallet_copyability_delay_evaluation_v1.example.json` - WP80 static advisory-only copyability delay evaluation design example; placeholder wallet identity only; includes _meta (schema_type WALLET_COPYABILITY_DELAY_EVALUATION_V1, all 8 allowed evaluation statuses listed, safety flags all true), evaluation_identity (design_example_only=true), wallet_reference (PLACEHOLDER), market_reference (PLACEHOLDER), signal_context, five delay window evaluation entries (1_second/5_seconds/30_seconds/2_minutes/10_minutes, each with evaluation_status NOT_EVALUATED or INSUFFICIENT_CONTEXT, human_review_required=true), and overall_evaluation (NOT_EVALUATED, safety flags all true); no forbidden trade-like keys; design example only, not a live evaluation or trade signal.
62z21. `docs/schemas/wallet_intelligence_report_v1.example.json` - WP80 static advisory-only wallet intelligence report design example; placeholder identity only; includes _meta (schema_type WALLET_INTELLIGENCE_ADVISORY_REPORT_V1, safety flags all true), report_identity (report_type=WALLET_INTELLIGENCE_ADVISORY_REPORT_V1, design_example_only=true), input_summary (zero counts, NOT_VALIDATED), wallet_signal_summary (zero counts, advisory notice), copyability_delay_design_summary (all five delay windows listed, all status counts zero, advisory notice), research_queue_implications (zero counts, advisory notice), suspicious_flow_review (empty, advisory notice), limitations (no live data notice, no trading signal notice), deferred_items (expected_return_computation forbidden, position_sizing forbidden, strategy_signal forbidden, live_copyability_simulation deferred to WP81, paper_trading_candidate deferred to WP83), safety flags all true; no forbidden trade-like keys; design example only, not a live report or trade signal.
62z22. `tests/test_wallet_copyability_delay_report_contract_docs.py` - WP80 focused docs/schema tests for the copyability delay simulator design and wallet intelligence report contract; covers: design docs and static examples exist, static examples parse as valid JSON, all five required delay windows documented, spread/slippage/fees/liquidity/size constraint factors documented, forbidden live API/authenticated data/execution feed/scheduler loop present in design doc, all 8 advisory evaluation statuses present in design doc and schema, forbidden trade-like fields documented in design doc, all 9 required report sections present in report contract and schema, all 7 safety flags present and true in both schemas, placeholder wallet identity in schemas, no forbidden trade-like keys in schemas, no credential patterns in schemas, suspicious-flow boundary present in both docs with required wording, future WP sequence (WP81-WP84) in both docs and roadmap, repo truth index references new docs/schemas/test files, deferred items log records copyability simulator and report generator deferrals for WP80, project status marks WP80 current phase and branch, related wallet docs still state no auto-copying/no live execution, no new src/tools/dependency/lock-file/local_data changes.
62z23. `src/data_layer/wallet_copyability_delay_evaluation.py` - WP81 local/offline/read-only stdlib wallet copyability delay evaluator; implements `evaluate_copyability_delay` and `DelayWindowObservation`/`WalletCopyabilityDelayEvaluation` frozen dataclasses; consumes only in-memory WP78 `LoadedWalletTradeEventRecord` objects and local `DelayWindowObservation` fixtures; groups by (wallet_id_or_address, market_id, condition_id); evaluates all five delay windows (1_second/5_seconds/30_seconds/2_minutes/10_minutes); produces only advisory evaluations with eight allowed statuses (NOT_EVALUATED/INSUFFICIENT_CONTEXT/RESEARCH_PROMISING/RESEARCH_WEAK/UNCOPYABLE_FAST_FLOW/UNCOPYABLE_TOO_ILLIQUID/SUSPICIOUS_FLOW_DO_NOT_COPY/HUMAN_REVIEW_REQUIRED); suspicious-flow boundary enforced (SUSPICIOUS_FLOW_DO_NOT_COPY, human_review_required=True); INSUFFICIENT_CONTEXT when delay obs missing or price/context unavailable; FORBIDDEN_OUTPUT_VALUES frozenset guards all outputs; no dollar PnL, no expected return, no position size, no buy/sell/live/trade signals; no network, no file writes, no credentials, no LLM/AI agent imports, no scoring weight changes, no paper/live trading; stdlib-only.
62z24. `tests/test_wallet_copyability_delay_evaluation.py` - WP81 focused tests for the wallet copyability delay evaluator; 127 tests covering: valid event + matching delay fixture produces advisory evaluation; all five delay windows supported; missing delay context yields INSUFFICIENT_CONTEXT; missing liquidity/spread/fee/size context creates warnings; suspicious-flow input yields SUSPICIOUS_FLOW_DO_NOT_COPY and human_review_required=True; no dollar PnL field on dataclass; no expected-return field; no buy/sell/entry/exit/position-size fields; no trade-ready/copy-ready/live-ready advisory labels; dataclasses are frozen; deterministic ordering; invalid records ignored or warned; no network library imports (AST-checked); no file writes; no credential terms; no LLM/AI agent imports (AST-checked); no scoring weight mutation; docs/status updates (project_status/deferred_items/simulator_design/repo_truth all verified); full end-to-end pipeline checks.
62z25. `src/data_layer/wallet_intelligence_report_generator.py` - WP82 local/offline/read-only stdlib wallet intelligence report generator; implements `build_wallet_intelligence_report` and `WalletIntelligenceReport` frozen dataclass; consumes only in-memory WP79 `WalletSignalResearchProfile`/`WalletResearchQueueAnnotation` and WP81 `WalletCopyabilityDelayEvaluation` records plus optional explicit local metadata; produces deterministic advisory `WalletIntelligenceReport` with required sections (report_identity, input_summary, wallet_signal_summary, copyability_delay_summary, research_queue_implications, suspicious_flow_review, limitations, deferred_items, safety, warnings); advisory_label=ADVISORY_ONLY_WALLET_INTELLIGENCE_REPORT; all seven safety flags true; deterministic signal_category_distribution and evaluation_status_distribution counts; human_review_required_count and suspicious_flow_count surfaced; FORBIDDEN_OUTPUT_VALUES frozenset guards all outputs; no dollar PnL, no expected return, no position size, no buy/sell/live/trade signals; no network, no file writes, no credentials, no LLM/AI agent imports, no scoring weight changes, no paper/live trading; stdlib-only.
62z26. `tests/test_wallet_intelligence_report_generator.py` - WP82 focused tests for the wallet intelligence report generator; 96 tests covering: report can be built from local profiles and evaluations; report output has required sections; safety flags all true; signal category counts are deterministic; evaluation status counts are deterministic; human-review-required count is present; suspicious-flow count is present; insufficient-context count is present; warnings are deterministic; advisory label is present and correct; no dollar PnL field; no expected-return field; no buy/sell/entry/exit/position-size fields; no trade-ready/copy-ready/live-ready labels; dataclass is frozen; deterministic ordering for multiple inputs; no network library imports; no file writes; no credentials/auth clients; no LLM/Hermes imports; no scoring weight mutation; docs section checks; full integration smoke test.
62z27. `docs/wallet_signal_paper_strategy_contract.md` - WP83 docs-only wallet signal paper strategy contract; defines wallet-signal paper strategy contract records as advisory research queue records only (not strategy instructions, not allocation records, not order records, not implementation authorization); required contract sections (contract_identity, source_report_reference, source_signal_context, copyability_delay_context, eligibility_review, suspicious_flow_review, insufficient_context_review, human_review, deferred_items, safety, warnings, advisory_notice); allowed eligibility statuses (NOT_ELIGIBLE_INSUFFICIENT_CONTEXT, NOT_ELIGIBLE_SUSPICIOUS_FLOW, NOT_ELIGIBLE_SAFETY_FLAG_FAILURE, HUMAN_REVIEW_REQUIRED, RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN); required safety flags all true (manual_research_only, not_automated_copy_trading, no_live_execution, no_order_placement, no_position_sizing, no_risk_override, no_parameter_auto_change, no_paper_engine_created, no_account_action); blocking gate precedence (missing source reference → NOT_ELIGIBLE_INSUFFICIENT_CONTEXT, any safety flag failure → NOT_ELIGIBLE_SAFETY_FLAG_FAILURE, suspicious flow → NOT_ELIGIBLE_SUSPICIOUS_FLOW, missing copyability context → NOT_ELIGIBLE_INSUFFICIENT_CONTEXT, insufficient context warning → HUMAN_REVIEW_REQUIRED, all gates pass → RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN); safety flag precedence table; source reference policy (local placeholder IDs only); raw metadata pass-through forbidden; deferred items kept deferred (paper strategy implementation, paper order model, paper portfolio ledger, paper fill model, paper PnL computation, network wallet ingestion, real wallet monitoring, passive following scope, live access capability, credential access, scheduler or loop, dashboard); normative forbidden output term ban list (section 12 only); design guidance only, not implementation authorization.
62z28. `docs/schemas/wallet_signal_paper_strategy_contract_v1.example.json` - WP83 static advisory-only wallet signal paper strategy contract design example; placeholder identifiers only (wallet_placeholder_001, market_placeholder_001, condition_placeholder_001); includes _meta (schema_type WALLET_SIGNAL_PAPER_STRATEGY_CONTRACT_V1, design_example_only, all nine safety flags true), contract_identity, source_report_reference (placeholder IDs, no real addresses), source_signal_context (advisory labels only), copyability_delay_context (RESEARCH_PROMISING advisory label only), eligibility_review (eligibility_status RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN, gate results all true), suspicious_flow_review (no suspicious flow, empty records list), insufficient_context_review (no warnings), human_review (required true, placeholder label IDs), deferred_items (all capabilities deferred or forbidden with neutral wording), safety (all nine flags true), warnings (neutral advisory wording), advisory_notice; no forbidden trade-like keys or values; no generic metadata object; no real wallet addresses; design example only, not a live contract or instruction record.
62z29. `tests/test_wallet_signal_paper_strategy_contract_docs.py` - WP83 focused docs/schema tests for the wallet signal paper strategy contract; 46+ tests covering: contract doc exists, schema exists, JSON parses, required sections present (in JSON and markdown), safety flags all true (safety section and _meta.safety), contract doc lists all safety flags, allowed statuses only in JSON, forbidden statuses absent from JSON, allowed statuses listed in contract doc, recursive JSON key/value scan for forbidden output terms, forbidden variant matrix (buy/sell, execution, position sizing, expected return, risk targets, auto behavior, strategy leak, live leak), ban-list section exists, markdown forbidden terms only in ban-list section, raw metadata policy present, no generic metadata key in JSON, safety precedence table present, precedence table has human review, blocking gate precedence section present, deferred items present in JSON, deferred items mentioned in markdown, placeholders only in JSON, no real wallet addresses in JSON, source reference advisory present, no src/ implementation for WP83 (excluding WP84 validator), WP84 validator file exists, WP84 focused tests exist, repo truth index references WP83 docs/schema/test, project status reflects WP83/WP84, WP82 in merged WPs, wallet paper strategy contract status, live trading disabled, credentials not used, deferred items log resolves WP83 items, deferred items log marks paper strategy contract resolved, advisory purpose statement, no implementation authorized, human review required, live trading still disabled, no new dependency files.
62z30. `src/data_layer/wallet_signal_paper_strategy_contract_validator.py` - WP84 local/offline/read-only wallet signal paper strategy contract validator; validates in-memory candidate records against WP83 contract rules; returns frozen ContractValidationResult (is_valid, status VALID_CONTRACT_RECORD/INVALID_CONTRACT_RECORD, errors tuple, warnings tuple, normalized_record, advisory_label ADVISORY_ONLY_WALLET_SIGNAL_PAPER_STRATEGY_CONTRACT_VALIDATION); rejects: missing required sections, unknown eligibility statuses, forbidden eligibility statuses, missing/false safety flags, raw/free-form metadata keys at any nesting depth, forbidden output terms in keys/values recursively, eligibility status mismatches with blocking-gate precedence (gate order: missing source reference → NOT_ELIGIBLE_INSUFFICIENT_CONTEXT, safety flag failure → NOT_ELIGIBLE_SAFETY_FLAG_FAILURE, suspicious flow → NOT_ELIGIBLE_SUSPICIOUS_FLOW, missing copyability context → NOT_ELIGIBLE_INSUFFICIENT_CONTEXT, insufficient context warnings → HUMAN_REVIEW_REQUIRED, all gates pass → RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN), human_review_required not true; safety flag exception keys not rejected (not_automated_copy_trading, no_live_execution, no_order_placement, no_position_sizing); stdlib-only; no network; no file I/O; no credentials; no paper strategy; no account-action output; added in WP84.
62z31. `tests/test_wallet_signal_paper_strategy_contract_validator.py` - WP84 focused tests for the contract validator; 55 tests covering: valid record passes, advisory label correct, normalized record present, all required sections individually missing fail, empty record fails all sections, each safety flag individually false fails, each safety flag individually missing fails, safety section not mapping fails, all 8 forbidden statuses fail, unknown status fails, 8 reviewer-trap records from WP84 Section 7 (expected_return, position_size, buy_signal, execution_ready, paper_trading_candidate, strategy_signal, source_metadata with expected_return, metadata with nested position_size), recursive forbidden terms at depth 3, forbidden term in list value, forbidden term in nested key, buy/sell values rejected, live signal value rejected, pnl_target key rejected, safety flag exception keys not rejected, all 7 raw metadata-like keys rejected, nested raw metadata key rejected, deeply nested metadata key rejected, source_report_reference required, empty source_report_reference triggers precedence, copyability_delay_context required, empty copyability triggers precedence mismatch, suspicious flow precedence (detected true), suspicious flow with correct status passes, suspicious flow records list triggers precedence, safety flag failure precedence, safety flag failure with correct status, safety flag false overrides suspicious flow, insufficient context precedence, insufficient context with correct status passes, missing source ref takes precedence over safety failure, neutral error wording, error messages are strings, frozen dataclass, errors/warnings are tuples, status is string, advisory label never forbidden, no network/file I/O imports (AST check), no non-stdlib imports, human_review_required false fails, human_review_required missing fails, deferred_items section must be present, advisory_notice must be present, validator is idempotent.
63. `docs/architecture_principles.md` - platform architecture principles.
64. `docs/architecture_skeleton.md` - WP3 non-runtime architecture skeleton.
65. `docs/runtime_boundaries.md` - protected runtime boundary rules.
66. `docs/interface_contracts.md` - conceptual interface contracts for future implementation.
67. `docs/mode_separation.md` - historical, read-only, paper, and live mode separation.
68. `docs/security_tooling_requirements.md` - required future security and dependency-audit tooling gates.
69. `docs/security_tooling_status.md` - current security-tool availability and scan status.
70. `docs/security_tooling_installation.md` - approved security-tool installation and verification guidance.
71. `docs/security_tooling_completion.md` - WP5 project-local security tooling and Remote Main Sync Gate outcomes.
72. `docs/data_semantics.md` - shared data definitions.
73. `docs/wallet_copy_trading_semantics.md` - wallet and copy-trading terminology.
74. `docs/risk_semantics.md` - risk definitions and initial posture.
75. `docs/live_trading_authorization.md` - live trading gate and authorization table.
76. `docs/security_and_secrets.md` - credential and incident rules.
77. `docs/codex_execution_guidelines.md` - work-package execution process.
78. `docs/work_package_template.md` - reusable WP template.
79. `docs/review_checklist.md` - review readiness checklist.
80. `docs/testing_requirements.md` - current and future test requirements.

62z32. `docs/ai/codex/WP_DRAFTING_STANDARD.md` - WP86 execution-package drafting standard for all WPs (WP86+); defines mandatory front matter, authority/non-authority posture fields, hard merge gate sequence, context budget structure, compatibility/impossibility check, concrete stop conditions by risk class, validation by package class, requirement-to-evidence traceability, evidence model tokens (LOCAL_DRAFT_VERIFIED/POSTED_GITHUB_API_VERIFIED/MANUAL_UI_VERIFIED), review self-diagnosis for not-merge-ready reviews, worktree-first execution standard, shared Claude/Codex layer clarification, prompt wrapper non-canonical status, safety/evidence precedence table, forbidden variant matrix for output WPs, and raw metadata pass-through policy.
62z33. `docs/status_entries/README.md` - WP86 committed per-WP evidence fragment convention (WP86+); updated by WP91 and WP93 final follow-up; defines status entry purpose, when to create, required format (WP<NN>.md with identity, authority posture, scope boundary, validation summary, guard summary, deferred items, next WP pointer, ready for review), stable-only PR identity and current-live-head policy (`see GitHub PR metadata and PR body`), evidence distinction policy (LOCAL_DRAFT_VERIFIED/POSTED_GITHUB_API_VERIFIED/MANUAL_UI_VERIFIED/NOT_VERIFIED), final comment policy (final GitHub PR comments optional/non-canonical after WP91; WP86–WP90 transition policy noted as historical), and relationship to other evidence docs.
62z34. `docs/status_entries/WP86.md` - WP86 committed status fragment for the execution-package discipline adoption WP; records identity, authority posture, scope boundary, validation summary, deferred items, next WP pointer (WP87), and ready for review.
62z35. `src/data_layer/wallet_signal_paper_strategy_candidate_fixture_loader.py` - WP87 local/offline/read-only wallet signal paper strategy candidate fixture loader; loads candidate contract record JSON fixtures from explicit local paths (single JSON file or direct-child *.json directory); validates each record with the WP84 contract validator; returns frozen CandidateFixtureLoadResult (root_path, total_files, loaded_files, valid_records, invalid_records, malformed_files, items tuple of CandidateFixtureLoadItem, errors, warnings, advisory_label); each CandidateFixtureLoadItem holds fixture_path, load_status, validation_status, is_valid, errors, warnings, normalized_record (empty dict for invalid/malformed); allowed load statuses: LOADED_VALID_CONTRACT_RECORD, LOADED_INVALID_CONTRACT_RECORD, MALFORMED_FIXTURE_FILE, MISSING_FIXTURE_PATH, UNSUPPORTED_FIXTURE_PATH; invalid/malformed errors never echo raw file content or unsafe values; stdlib-only; no network; no file writes; no credentials; no paper strategy; no account-action output; added in WP87.
62z36. `tests/test_wallet_signal_paper_strategy_candidate_fixture_loader.py` - WP87 focused tests for the candidate fixture loader; tests covering: valid fixture loads and produces one valid item, valid item has non-empty normalized_record, valid item load_status is LOADED_VALID_CONTRACT_RECORD, missing path returns safe result, malformed JSON produces MALFORMED_FIXTURE_FILE item without raw JSON echo, forbidden-status fixture is invalid and loader output does not echo 'TRADE_READY', forbidden-metadata fixture is invalid and output does not echo 'position_size'/'expected_return'/raw values, invalid normalized_record is always empty, full result recursively contains no forbidden terms for all four fixture files, directory loads deterministically in sorted order, load_status values are from allowlist, allowed status constants do not contain forbidden terms, unsupported file type rejected safely, URL-like path rejected, loader has no forbidden imports (AST check), loader does not write files (regex check), result and item are frozen dataclasses, all results include advisory_label with ADVISORY, empty directory returns safe error result, status fragment WP87.md exists and references loader module; added in WP87.
62z37. `tests/fixtures/wallet_signal_paper_strategy_candidates/` - WP87 test fixture directory; contains four fixture files: valid_candidate.json (complete valid contract record, all 12 required sections, all 9 safety flags true, RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN eligibility status, placeholder IDs only), invalid_forbidden_status.json (reviewer-trap: TRADE_READY eligibility status, fails validation), invalid_forbidden_metadata.json (reviewer-trap: raw 'metadata' key with nested position_size and 'source_metadata' key with expected_return, fails validation), malformed_json.json (intentionally invalid JSON syntax, fails to parse); all fixtures safe to commit; no real wallet addresses; no real market IDs; added in WP87.
62z38. `docs/status_entries/WP87.md` - WP87 committed status fragment; records identity, authority posture, scope boundary, validation summary, deferred items (WP84-D001 resolved, WP87-D001 added), next WP pointer (WP88), and ready for review.

62z39. `docs/ai/codex/EVIDENCE_ARCHITECTURE.md` - WP88 evidence architecture Model D; updated by WP91; defines PR body as current review evidence surface, status fragment as stable non-self-referential record (must not track current live PR head as fixed SHA), final GitHub comment as optional/non-canonical reviewer clarification after WP91 (was transition-only pointer during WP86–WP90), evidence source hierarchy, evidence contradiction matrix (invalid combinations that block merge; absence of final comment not invalid after WP91), and final comment transition policy (ended with WP91).

62z40. `docs/ai/codex/RESULT_OUTPUT_INVARIANT_STANDARD.md` - WP88 result object and output invariant standard; defines field-coverage gate for all future result/report/loader/validator WPs (enumerate all public fields, classify each, test coverage, scan invalid objects); manual serializer losslessness rule (forbidden unless field-coverage test proves losslessness); invalid-output no-echo rule (full public result object scanned recursively, not only errors field); required unsafe fixture classes; field-coverage gate section for WP template.

62z41. `docs/ai/codex/FOLLOWUP_PROMPT_STANDARD.md` - WP88 follow-up prompt standard; requires root-cause classification before fix description; nine classification categories (A–I); required follow-up template with classification, current live facts, root cause (why, not what), required correction, forbidden scope, validation, ready rule, and required response fields; reviewer check for same-PR follow-ups.

62z42. `docs/status_entries/WP88.md` - WP88 committed status fragment; stable non-self-referential model; records identity, authority posture, scope boundary, validation summary, deferred items (WP88-D001 through WP88-D004 and WP88-DEFER-001 through WP88-DEFER-003), next WP pointer (WP89), and ready for review.

62z43. `src/data_layer/wallet_signal_candidate_review_report.py` - WP89 local/offline/read-only candidate review report generator; consumes only an in-memory WP87 `CandidateFixtureLoadResult`; returns frozen `CandidateReviewReportItem`, `CandidateReviewReportSummary`, and `CandidateReviewReport` dataclasses; implements `build_wallet_signal_candidate_review_report`, `render_wallet_signal_candidate_review_report`, and `candidate_review_report_to_dict`; summarizes valid, invalid, malformed, missing, and unsupported fixture-loader outcomes with neutral reason codes and deterministic Markdown; uses `dataclasses.asdict` for full public-field serialization; no file reads, no file writes, no network/API behavior, no credentials, no scheduler/dashboard/bot loop, no paper engine, no live execution, and no dependency changes.

62z44. `tests/test_wallet_signal_candidate_review_report.py` - WP89 focused tests for the candidate review report generator; covers valid and mixed loader results, deterministic ordering and Markdown, no report-time file I/O, no network/runtime imports, neutral invalid/malformed/missing/unsupported reason codes, no echo of forbidden status/metadata/raw malformed input, serializer coverage for every public report/summary/item field, full report object and Markdown forbidden-variant scans, allowlisted status values, safe field names, safe boundary notices, WP87 loader-result contract use, frozen dataclasses, and source-level no-write checks.

62z45. `docs/status_entries/WP89.md` - WP89 committed status fragment; stable non-self-referential Model D record for the candidate review report generator; records identity, authority posture, scope boundary, validation summary, deferred items, next WP pointer (WP90), and ready-for-review state.

62z46. `src/data_layer/wallet_signal_candidate_review_report_export.py` - WP90 local/offline/read-only candidate review report export layer; consumes a WP89 `CandidateReviewReport` object; writes deterministic Markdown and JSON files under an operator-specified local output directory; returns frozen `CandidateReviewReportExportFile` and `CandidateReviewReportExportResult` dataclasses; implements `export_wallet_signal_candidate_review_report`, `render_candidate_review_report_json`, and `candidate_review_report_export_result_to_dict`; allowlisted fixed filenames only (candidate_review_report.md, candidate_review_report.json); no user-provided filenames in V1; path traversal blocked by fixed-filename design; all writes stay under resolved output directory; deterministic overwrite; SHA-256 checksums and byte counts for written files; stdlib-only; no network, no credentials, no scheduler, no paper engine, no live execution, no report content modification, no dependency changes.

62z47. `tests/test_wallet_signal_candidate_review_report_export.py` - WP90 focused tests for the candidate review report export layer; 26 tests covering: Markdown file write, JSON file write, both formats by default, format selection, deterministic output, deterministic overwrite, writes only under output directory, relative path safety, SHA-256 and byte counts, sorted JSON keys and trailing newline, Markdown matches renderer output, no forbidden network/runtime imports (AST check), no forbidden import patterns (regex check), no writes outside temp output dir (monkeypatched), no forbidden terms in generated Markdown (all four fixtures), no forbidden terms in generated JSON (all four fixtures), no forbidden terms in full export result object (all four fixtures), serializer covers all public result fields, serializer covers all public file fields, export/write status allowlisted, field names safe, advisory notice safe, WP89 report contract use, invalid-fixture no unsafe content in any surface, no user home/absolute paths in file content, path traversal inputs ignored by fixed-filename design.

62z48. `docs/status_entries/WP90.md` - WP90 committed status fragment; stable non-self-referential Model D record for the candidate review report export layer; records identity, authority posture, scope boundary, result object invariants, validation summary, deferred items, next WP pointer (WP91), and ready-for-review state.

62z49. `docs/ai/codex/FINAL_COMMENT_POLICY.md` - WP91 final comment policy; defines final comment mode as OPTIONAL_REVIEW_CLARIFICATION after WP91; explains why mandatory final comments are retired (WP87–WP90 showed stale-head follow-up loops); documents forbidden combinations (optional comment claiming canonical authority, comment contradicting PR body); provides recommended wording for voluntarily posted final comments; historical context for WP86–WP90 transition.

62z50. `docs/status_entries/WP91.md` - WP91 committed status fragment; stable non-self-referential record for the final comment transition retirement decision WP; records identity, authority posture, final comment policy decision (mandatory final comments RETIRED after WP90), scope boundary, validation summary, deferred items (WP88-DEFER-002 and WP90-D002 RESOLVED, WP91-D001 added), next WP pointer (WP92), and ready-for-review state.

62z51. `docs/ai/codex/REPO_TRUTH_POLICY_GUARD.md` - WP92 repo-truth policy guard; defines active canonical policy-doc set, old-policy phrase sweep list (14 phrases that must not appear as active post-WP91 policy), phrase-hit classification labels (ACTIVE_POST_WP91_POLICY / HISTORICAL_WP86_WP90_ONLY / REMOVED / REWRITTEN_TO_POST_WP91_POLICY / OPTIONAL_NON_CANONICAL_COMMENT), product WP one-shot readiness gate, policy WP one-shot readiness gate, final comment policy after WP91, status-fragment consistency rules, result-object/output gate reminders, and required PR-body evidence format.

62z52. `docs/status_entries/WP92.md` - WP92 committed status fragment; stable non-self-referential record for the repo-truth policy guard and one-shot execution gate WP; records identity, authority posture, scope boundary, validation summary, deferred items, next WP pointer (WP93), and ready-for-review state.

62z53. `docs/runbooks/candidate_review_report_operator_runbook.md` - WP93 docs-only operator runbook for the existing local/offline/import-based candidate review workflow; documents local fixture input expectations, WP87 `load_wallet_signal_paper_strategy_candidate_fixtures`, WP89 `build_wallet_signal_candidate_review_report`, WP90 `export_wallet_signal_candidate_review_report`, local report export to fixed Markdown/JSON filenames, safe interpretation language, validation commands, troubleshooting, path-safety guidance, and boundary checklist; adds no CLI, source code, tools, runtime/paper/live/credential/network/API/account behavior, scheduler/dashboard/bot loop, dependency, or lock-file change.

62z54. `docs/status_entries/WP93.md` - WP93 committed status fragment; stable non-self-referential record for the candidate review report operator runbook WP; records identity, authority posture, scope boundary, validation summary, guard summary, deferred items, next WP pointer, and ready-for-review state.

62z55. `docs/runbooks/candidate_review_workflow_local_smoke_receipt.md` - WP94 local/offline smoke receipt for the existing import-only candidate review workflow; verifies WP87 `load_wallet_signal_paper_strategy_candidate_fixtures`, WP89 `build_wallet_signal_candidate_review_report`, WP89 `render_wallet_signal_candidate_review_report`, WP89 `candidate_review_report_to_dict`, WP90 `export_wallet_signal_candidate_review_report`, and WP90 `candidate_review_report_export_result_to_dict` through docs/tests and temp-only local export smoke coverage; adds no CLI, source code, tools, runtime/paper/live/credential/network/API/account behavior, scheduler/dashboard/bot loop, dependency, lock-file change, strategy promotion, candidate ranking for execution, expected-return computation, or position-size computation.

62z56. `docs/status_entries/WP94.md` - WP94 committed status fragment; stable non-self-referential record for the candidate review workflow local smoke receipt WP; records identity, authority posture, scope boundary, validation summary, guard summary, deferred items, next WP pointer, and ready-for-review state.

62z57. `docs/hermes_research_brain_execution_plan.md` - WP95 canonical accepted Hermes/research-brain execution plan; governs the broad advisory research philosophy, deterministic-core responsibilities, forbidden Hermes authority, phased sequence, manual-step checkpoints, cost controls, and future plan-change rule. Material changes to this plan must update repo-truth docs in the same WP or an approved follow-up; chat memory and PR comments alone are not authoritative. Related policy and boundary context remains in `docs/ai_agent_integration_policy.md`, `docs/hermes_readonly_boundary.md`, `docs/agent_hermes_manual_setup_decision_record.md`, `docs/local_advisory_handoff_package.md`, and `docs/advisory_runtime_boundary_consumption_design.md`. Planning guidance only; no Hermes runtime, paper, execution, live, credential, scheduler, or order authority.

62z58. `docs/status_entries/WP95.md` - WP95 stable committed status fragment for post-WP94 repo-truth reconciliation and accepted Hermes research-brain plan lock-in.

62z59. `docs/hermes_advisory_foundation_research_brain_architecture.md` - WP96 canonical Hermes advisory foundation and research-brain architecture; elaborates WP95 Phase 1 with the corrected powerful adaptive research-brain philosophy, broad research freedoms, H0-H10 architecture mode map, authority matrix, deterministic-core responsibilities, forbidden Hermes authority, architecture-level future input/output families, forbidden-output matrix, and next-WP pointer to Hermes input/output contracts and validator hardening. Planning guidance only; no Hermes runtime, install, provider/model configuration, credentials, private endpoints, schema files, validator modules, prompt packs, runbooks, exporters, runtime artifacts, paper/live behavior, execution/order/risk behavior, scheduler, dashboard, bot loop, source, tools, dependency, or lock-file authority.

62z60. `docs/status_entries/WP96.md` - WP96 stable committed status fragment for the Hermes advisory foundation and research-brain architecture lock-in.

62z61. `tests/test_hermes_advisory_foundation_architecture_docs.py` - WP96 focused docs tests for architecture doc existence and repo-truth registration, WP95 relationship, broad Hermes research freedom, H0-H10 mode map, authority matrix, deterministic-core responsibilities, forbidden Hermes authority, architecture-only input/output families, forbidden-output matrix, stable status wording, and absence of actual Hermes schema/validator/prompt/runbook/exporter implementation artifacts.

62z62. `docs/hermes_input_output_contracts_and_validator_requirements.md` - WP97 canonical documentation-level Hermes input/output contract requirements and future validator requirements; defines input family requirements, output family requirements, common field concepts, forbidden-output matrix, recursive validator requirements, no-raw-unsafe-echo policy, human-review and deterministic-handoff requirements, plan-change rule, and future implementation gates. Documentation-level only; no machine-readable schema, source validator, prompt pack, runbook, exporter, parser, context-packet generator, Hermes runtime, provider/model configuration, credentials, private endpoints, paper/live behavior, execution/order/risk behavior, scheduler, dashboard, bot loop, source, tools, dependency, or lock-file authority.

62z63. `docs/status_entries/WP97.md` - WP97 stable committed status fragment for the Hermes input/output contracts and validator requirements lock-in.

62z64. `tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py` - WP97 focused docs tests for contract doc existence and registration, WP95/WP96 relationship, input/output family requirements, common fields, forbidden-output matrix, recursive validator requirements, no-raw-unsafe-echo policy, stable status wording, project-status target state, broad Hermes research freedom, deterministic-core responsibilities, and absence of actual Hermes schema/validator/prompt/runbook/exporter/runtime artifacts.

62z65. `docs/hermes_research_prompt_pack_and_operator_runbooks.md` - WP98 canonical Hermes research prompt pack and operator runbooks; defines 10 manual-use-only research prompt families (broad market-edge hypothesis generation, wallet/candidate review, resolution-rule ambiguity analysis, cross-market inconsistency analysis, microstructure/slippage realism critique, strategy critique, failure analysis/postmortem, performance-improvement idea review, experiment design, future WP recommendation); includes operator preflight checklist, input preparation rules, prompt-injection and untrusted-input policy, common prompt wrapper requirements, common output requirements (advisory-only, human-review-required, evidence/provenance/staleness/uncertainty, falsification-path, deterministic-validation-handoff, forbidden-action-statement), output review checklist, forbidden prompt/output matrix (preserves all WP97 forbidden categories), human-review and deterministic handoff rules, failure/stop conditions, manual setup dependency note, future implementation gates, repo-truth update rule, and next WP sequence pointer. Planning/runbook guidance only; no Hermes runtime, install, provider/model configuration, credentials, prompt runner, machine-readable schema, source validator, exporter, parser, context-packet generator, runtime artifacts, paper/live behavior, execution/order/risk behavior, scheduler, dashboard, bot loop, source, tools, dependency, or lock-file authority.

62z66. `docs/status_entries/WP98.md` - WP98 stable committed status fragment for the Hermes research prompt pack and operator runbooks lock-in.

62z67. `tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py` - WP98 focused docs tests for prompt pack doc existence and registration, status and authority no-runtime-artifacts, WP95/WP96/WP97 relationship, manual-use-only rule, operator preflight checklist, input preparation rules, prompt-injection policy, common prompt wrapper requirements, common output requirements, all 10 prompt family templates, advisory-only and human-review-required language in every template, deterministic validation handoff, falsification path, evidence/provenance/staleness/uncertainty in every template, no-PR-approval and no-strategy-promotion in every template, forbidden-action-statement in every template, broad research usefulness, output review checklist, forbidden output matrix, WP97 forbidden categories preserved, human-review and deterministic handoff rules, failure/stop conditions, manual setup dependency note, future implementation gates, repo-truth update rule, next WP sequence pointer, stable status wording, project status registration, no src/tools/workflow/dependency files changed, no forbidden runtime artifacts added.

62z68. `src/data_layer/hermes_advisory_output_validator.py` - WP99 local/offline/read-only deterministic stdlib-only validator for in-memory Hermes advisory output mappings; implements `validate_hermes_advisory_output` returning a frozen `HermesAdvisoryOutputValidationResult` dataclass; enforces all nine required boolean safety fields (advisory_only, human_review_required, no_execution_authority, no_risk_override, no_credential_request, no_order_or_cancel_or_sign_or_submit, no_paper_live_decision, no_strategy_promotion_approval, no_pr_approval_or_merge_readiness_claim) and all twelve required text/list fields; validates confidence_level allowlist (LOW/MEDIUM/HIGH); recursively scans all keys and string values for 33 forbidden output term substrings; recursively rejects 11 raw/free-form metadata keys at any nesting depth; returns empty normalized_output for invalid results; errors use neutral codes and do not echo unsafe raw input; no Hermes runtime, prompt runner, exporter, CLI, network, credentials, paper/live, execution/risk, scheduler, dashboard, bot loop, dependency, or lock-file behavior.

62z69. `tests/test_hermes_advisory_output_validator.py` - WP99 focused tests for the Hermes advisory output validator; covers all trap categories from WP99 Section 17: required-field failures (all boolean and text fields), forbidden action phrases (all 29 trap phrases from the WP), recursive scan (nested dict/list, warnings, limitations, examples, Markdown-like text), raw metadata rejection (all 11 keys, nested), no unsafe echo (all public result surfaces), valid path (minimal valid output passes, normalized_output populated, confidence level allowlist), source-level boundary (AST/regex confirms stdlib-only imports, no file writes, no subprocess, no network, no runtime patterns), and status/doc trap (WP99 status fragment existence and stable wording).

62z70. `docs/status_entries/WP99.md` - WP99 stable committed status fragment for the Hermes advisory output validator V1.

62z71. `src/data_layer/hermes_context_packet_exporter.py` - WP100 local/offline/read-only deterministic stdlib-only Hermes context-packet builder foundation; implements `build_hermes_context_packet` returning frozen `HermesContextPacketBuildResult`; consumes explicit in-memory summaries only; requires identity, source-reference, provenance, staleness, warning, missing-data, summary, structured-context, safe routing, review-step, and deterministic-owner concepts; sets advisory-only, human-review-required, and non-authority flags; recursively rejects forbidden keys/string values and raw/free-form mapping keys; invalid input returns an empty packet with neutral no-echo diagnostics; no Hermes runtime, prompt runner, CLI, file I/O, network/API, credentials, private/account/order state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior.

62z72. `tests/test_hermes_context_packet_exporter.py` - WP100 focused positive, negative-matrix, recursive rejection, no-unsafe-echo, determinism, result-field-coverage, stdlib-only, and protected-boundary tests for the Hermes context-packet builder foundation.

62z73. `docs/status_entries/WP100.md` - WP100 stable committed status fragment for the Hermes context-packet exporter foundation V1.

62z74. `src/data_layer/hermes_context_packet_dry_run_receipt.py` - WP101 local/offline/read-only deterministic stdlib-only Hermes context-packet dry-run receipt helper; implements `build_hermes_context_packet_dry_run_receipt` returning frozen `HermesContextPacketDryRunReceiptResult`; consumes an explicit in-memory WP100 packet, checked source refs, reviewer identity, dry-run scope, exact readiness checks, optional stop reasons, operator notes, and related repo-truth refs only; validates WP100 safety flags, required packet fields, checked source refs, readiness checks, stop-reason precedence, recursive forbidden text, recursive raw/free-form mapping keys, fail-closed empty invalid receipts, and no unsafe echo; valid receipts set dry-run/manual-review/no-runtime/no-model/no-file/no-network/no-paper-live/no-execution-risk flags; no Hermes runtime, prompt runner, CLI, file I/O, network/API, credentials, private/account/order state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior.

62z75. `tests/test_hermes_context_packet_dry_run_receipt.py` - WP101 focused positive, negative-matrix, recursive rejection, no-unsafe-echo, output-surface, result-field-coverage, stdlib-only, and protected-boundary tests for the Hermes context-packet dry-run receipt helper.

62z76. `docs/status_entries/WP101.md` - WP101 stable committed status fragment for the Hermes context-packet dry-run receipt V1.

62z77. `src/data_layer/hermes_manual_research_dry_run_review.py` - WP102 local/offline/read-only deterministic stdlib-only Hermes manual research dry-run operator review helper; implements `build_hermes_manual_research_dry_run_review` returning frozen `HermesManualResearchDryRunReviewResult`; consumes an explicit in-memory WP101 dry-run receipt, reviewer identity, selected research family and runbook ref, exact source-review checks, optional stop reasons, operator notes, and related repo-truth refs only; validates receipt type/status/safety flags, required receipt identity/source-ref fields, exact source-review checks, stop-reason precedence, recursive forbidden text, recursive raw/free-form mapping keys, fail-closed empty invalid reviews, and no unsafe echo; valid reviews set dry-run/manual-review/no-runtime/no-model/no-file/no-network/no-paper-live/no-execution-risk/no-credential flags; no Hermes runtime, prompt runner, CLI, file I/O, network/API, credentials, private/account/order state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior.

62z78. `tests/test_hermes_manual_research_dry_run_review.py` - WP102 focused positive, negative-matrix, recursive rejection, no-unsafe-echo, output-surface, result-field-coverage, stdlib-only, and protected-boundary tests for the Hermes manual research dry-run operator review helper.

62z79. `docs/status_entries/WP102.md` - WP102 stable committed status fragment for the Hermes manual research dry-run operator review V1.

62z80. `src/data_layer/hermes_candidate_review_context_packet_integration.py` - WP103 local/offline/read-only deterministic (stdlib-only plus approved WP100 internal import) Hermes candidate-review context packet integration adapter; implements `build_candidate_review_hermes_context_packet` returning `HermesContextPacketBuildResult` from WP100; accepts explicit in-memory candidate-review report data (packet_id, report_identity, source_refs, advisory_notice, human_review_required, review_status, provenance_status, staleness_status, recommended_next_review_step, and optional fields); pre-validates all inputs for forbidden credential/trade/execution/runtime/raw-mapping-key content, maps safe fields to WP100 `build_hermes_context_packet`, returns advisory-only/human-review-required/no-authority packet; fail-closed empty invalid packets; no unsafe echo; no Hermes runtime, prompt runner, CLI, file I/O, network/API, credentials, private/account/order state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior.

62z81. `tests/test_hermes_candidate_review_context_packet_integration.py` - WP103 focused positive, negative-matrix, no-unsafe-echo, output-surface-inventory, approved-import-only, and protected-boundary tests for the Hermes candidate-review context packet integration adapter.

62z82. `docs/status_entries/WP103.md` - WP103 stable committed status fragment for the Hermes candidate-review context packet integration V1.

62z83. `src/data_layer/hermes_candidate_review_manual_chain_smoke.py` - WP104 local/offline/read-only deterministic (stdlib-only plus approved WP103/WP101/WP102 internal imports) Hermes candidate-review manual chain smoke helper; implements `run_candidate_review_manual_chain_smoke` returning frozen `HermesChainSmokeResult`; composes WP103 candidate-review context packet adapter, WP101 dry-run receipt helper, and WP102 manual research dry-run review helper in memory; stage-cascade fail-closed design: invalid input fails at first failing stage with neutral stage-namespaced error codes; safety flags always True describing advisory-only posture; no unsafe echo in errors; no Hermes runtime, prompt runner, CLI, file I/O, network/API, credentials, private/account/order state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior.

62z84. `tests/test_hermes_candidate_review_manual_chain_smoke.py` - WP104 focused positive, negative-matrix, stage-cascade failure, no-unsafe-echo, output-surface, result-field-coverage, stdlib-only, and protected-boundary tests for the Hermes candidate-review manual chain smoke helper.

62z85. `docs/status_entries/WP104.md` - WP104 stable committed status fragment for the Hermes candidate-review manual chain smoke V1.

62z86. `docs/hermes_candidate_review_operator_handoff_contract.md` - WP105 canonical documentation-level Hermes candidate-review operator handoff contract; defines the human-operator contract around the WP103 -> WP101 -> WP102 -> WP104 candidate-review research chain, required conceptual handoff groups, required safety flags, allowed research decision labels, forbidden interpretation, forbidden output/wording matrix, raw metadata/free-form mapping policy, no-unsafe-echo policy, fail-closed policy, future implementation gates, operator runbook summary, and non-goals; docs/status/tests-only; no source implementation, report writer, exporter, CLI, Hermes runtime/provider/model/prompt runner, network/API/product/account behavior, credentials, paper/live, execution/risk/order, scheduler/dashboard/bot-loop, dependency, workflow, or generated-artifact behavior.

62z87. `tests/test_hermes_candidate_review_operator_handoff_contract_docs.py` - WP105 focused docs tests for the Hermes candidate-review operator handoff contract; verifies doc existence, WP99-WP104 relationship, advisory-only and human-review-required language, no execution/runtime/credential/paper-live/prompt/file-network authority, required conceptual groups, allowed decision labels, forbidden interpretation, forbidden wording matrix, raw metadata/free-form policy, no-unsafe-echo policy, fail-closed policy, future implementation gates, constrained readiness/approval wording, absence of current runtime/export behavior claims, repo-truth registration, project-status boundary preservation, and WP105 status entry inventory/stable wording.

62z88. `docs/status_entries/WP105.md` - WP105 stable committed status fragment for the Hermes candidate-review operator handoff contract V1.

62z89. `src/data_layer/hermes_candidate_review_operator_handoff.py` - WP106 local/offline/read-only deterministic stdlib-only in-memory operator handoff object implementation for the WP105 operator handoff contract; implements `build_candidate_review_operator_handoff`, `validate_candidate_review_operator_handoff`, and `assert_candidate_review_operator_handoff`; validates required conceptual groups, required safety flags (all True), allowed research decision labels, source-review checklist fields, recursive forbidden-content scan, recursive raw/free-form metadata key scan, fail-closed empty invalid handoffs with neutral error codes, and no-unsafe-echo policy; does not widen any WP105 authority; no Hermes runtime, prompt runner, CLI, file I/O, network/API, credentials, private/account/order state, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior.

62z90. `tests/test_hermes_candidate_review_operator_handoff.py` - WP106 focused tests for the Hermes candidate-review in-memory operator handoff object; covers valid minimal handoff, required groups, safety flags, all allowed decision labels, unknown label rejection, missing group rejection, missing/false safety flags, conflicting authority rejection, missing/false checklist keys, forbidden content recursion (trade/order/execution, expected-return/edge/tradability, paper/live, PR-approval/merge-ready, credential/wallet, runtime/provider/prompt), raw/free-form metadata key rejection, no-unsafe-echo in errors/warnings, empty invalid handoff dict, assert helper neutral error, approved imports only, no forbidden behaviors in module source, contract doc WP106 reference, project status WP106 boundary preservation, WP106 status entry stable inventory.

62z91. `docs/status_entries/WP106.md` - WP106 stable committed status fragment for the Hermes candidate-review in-memory operator handoff object V1. WP106 is an implementation of the WP105 operator handoff contract and does not widen any WP105 authority.

62z92. `docs/hermes_candidate_review_handoff_local_manual_export_contract.md` - WP107 canonical docs/status/tests-only future local manual export contract for valid WP106 handoff outputs; defines the permitted future export artifact purpose, permitted future inputs (valid WP106 handoff result only), permitted output shape (12 required conceptual groups), required safety flags (13 flags), required human-review wording, forbidden interpretation, forbidden output wording matrix, raw metadata/free-form data policy, no-unsafe-echo policy, future implementation gate, validation expectations for future source implementation, operator runbook summary, and deferred items; no source implementation, file writer/export/report writer, CLI, Hermes runtime/provider/model/prompt runner, network/API/product/account behavior, credentials, paper/live, execution/risk/order, scheduler/dashboard/bot-loop, dependency, workflow, or generated-artifact behavior.

62z93. `tests/test_hermes_candidate_review_handoff_local_manual_export_contract_docs.py` - WP107 focused docs tests for the Hermes candidate-review handoff local manual export contract; verifies doc existence, WP107 docs/status/tests-only status, no exporter/writer implemented in WP107, WP105/WP106 relationship, valid WP106 handoff output requirement, local/offline/manual scope, fail-closed behavior, no-unsafe-echo policy, raw/free-form metadata rejection, all 12 required artifact conceptual groups, all 13 required safety flags, all 8 allowed decision labels, forbidden output wording families, separate approved WP requirement for file/export/report writer/CLI, Hermes runtime/prompt/model/provider/network/credential/paper/live/execution/risk/scheduler/dashboard/bot-loop/dependency/workflow authority forbidden, project status WP107 boundary preservation, repo truth index WP107 registration, WP107 status entry stable inventory, no stale wording, no src implementation.

62z94. `docs/status_entries/WP107.md` - WP107 stable committed status fragment for the Hermes candidate-review handoff local manual export contract V1. WP107 is docs/status/tests-only; no source implementation, file writer, report writer, exporter, CLI, Hermes runtime/provider/model/prompt runner, network/API/product/account behavior, credentials, paper/live, execution/risk/order, scheduler/dashboard/bot-loop, dependency, workflow, or generated-artifact behavior is added.

62z95. `src/data_layer/hermes_candidate_review_handoff_manual_export_artifact.py` - WP108 local/offline/read-only deterministic stdlib-only (plus approved WP106 internal import) Hermes candidate-review handoff manual export artifact builder; implements `build_candidate_review_manual_export_artifact` returning frozen `CandidateReviewManualExportArtifactResult`; accepts valid WP106 `HermesCandidateReviewOperatorHandoffResult`, validates required groups, safety flags, decision label, forbidden content (recursive), raw-metadata keys (recursive); returns deterministic 12-group artifact dict per WP107 contract with all 13 required safety flags True and in_memory_only flag in artifact_identity; fail-closed empty invalid artifacts with neutral error codes; no unsafe echo; no file I/O, network, subprocess, CLI, credentials, paper/live, execution/risk, scheduler, dashboard, bot-loop, runtime, or Hermes behavior.

62z96. `tests/test_hermes_candidate_review_handoff_manual_export_artifact.py` - WP108 focused tests for the Hermes candidate-review handoff in-memory manual export artifact builder; covers valid artifact creation, required 12 groups, 13 safety flags, WP108/WP107 identity, source handoff identity extraction, no raw/free-form metadata keys, invalid handoff fail-closed, non-HandoffResult type fail-closed, missing group fail-closed, missing/false safety flag fail-closed, invalid decision label fail-closed, forbidden content families (trade/order/execution, expected-return/edge/tradability, paper/live/readiness, PR-approval/merge-ready, credential/wallet, runtime/provider/prompt/scheduler/bot-loop), unsafe caller text not echoed, raw/free-form nested key fail-closed, deterministic output, frozen dataclass, stdlib-only import constraint, no file/network/subprocess/CLI patterns, no path arg, all allowed decision labels accepted, empty artifact_id fail-closed, chain stage summary, forbidden scope notice, safety flags count, in_memory_only placement, human decision record no raw rationale, status entry existence, status entry no stale wording, module source boundary confirmation.

62z97. `docs/status_entries/WP108.md` - WP108 stable committed status fragment for the Hermes candidate-review handoff in-memory manual export artifact builder V1. WP108 is a local/offline/read-only in-memory implementation; no file writer, report writer, exporter, CLI, Hermes runtime/provider/model/prompt runner, network/API/product/account behavior, credentials, paper/live, execution/risk/order, scheduler/dashboard/bot-loop, dependency, workflow, or generated-artifact behavior is added.

62z98. `src/data_layer/hermes_candidate_review_handoff_manual_export_writer.py` - WP109 local/offline/manual-only deterministic stdlib-only (plus approved WP108 internal import) Hermes candidate-review handoff manual export file writer; implements `write_candidate_review_manual_export_artifact` returning frozen `CandidateReviewManualExportWriteResult`; accepts valid WP108 `CandidateReviewManualExportArtifactResult`; validates input type, is_valid, all 12 required artifact groups, all 13 required safety flags; rejects URI-scheme output paths, unsupported suffixes (.md and .txt only), missing parent directories, existing files without overwrite=True; writes deterministic UTF-8 Markdown artifact with all 13 required sections plus boundary notice; returns bytes_written, sha256, and output_path; fail-closed with neutral error codes; no unsafe echo; no CLI, scheduler, daemon, background writer, Hermes runtime, prompt runner, network/API, credentials, paper/live, execution/risk, scheduler/dashboard, bot-loop, dependency, or lock-file behavior; no committed generated artifact files.

62z99. `tests/test_hermes_candidate_review_handoff_manual_export_writer.py` - WP109 focused tests for the Hermes candidate-review handoff local manual export file writer; 35 tests covering valid artifact writes Markdown file, result fields (is_valid/bytes_written/sha256), deterministic content across paths, all 13 required Markdown sections, boundary notice, all 13 safety flags in written file, invalid artifact fail-closed, unsupported input type fail-closed, missing artifact group fail-closed, missing/false safety flag fail-closed, forbidden wording families (via WP108 builder), raw metadata keys (via WP108 builder), unsafe caller text not echoed, existing path no-overwrite, overwrite=True, unsupported suffix fail-closed (.json with expected_suffix=.json), .txt suffix accepted, URL-like output paths fail-closed, stdlib-only import constraint, no network/subprocess/CLI imports, no CLI surface, no Hermes/model/provider imports, project status records WP109, WP109 status entry exists, status entry lists exact changed-file inventory, status entry no stale wording, architecture boundaries includes WP109 source module.

62z100. `docs/status_entries/WP109.md` - WP109 stable committed status fragment for the Hermes candidate-review handoff local manual export file writer V1. WP109 introduces only a local/offline/manual-only explicit file writer for valid WP108 artifacts; no CLI, scheduler, daemon, background writer, Hermes runtime, prompt runner, network exporter, model/provider integration, credential path, paper/live path, execution/risk path, or product runtime path is added; no generated artifact files are committed.

62z101. `docs/hermes_candidate_review_local_manual_export_operator_runbook.md` - WP110 docs/status/tests-only operator runbook for manual use of the WP109 local file writer to export valid WP108 candidate-review manual export artifacts. It defines allowed inputs, explicit operator-supplied local `.md`/`.txt` output path rules, parent-directory preflight, generated-artifact no-commit rules, safe import-based usage, operator review checklist, failure handling, forbidden scope, and future gates. It adds no source implementation, CLI, scheduler, daemon, background writer, automatic report/export pipeline, network/API/product/account behavior, Hermes runtime/provider/model/prompt runner, credentials/private state, paper/live/execution/risk/order behavior, dashboard, bot loop, dependency, workflow, or committed generated artifact behavior.

62z102. `tests/test_hermes_candidate_review_local_manual_export_operator_runbook_docs.py` - WP110 focused docs tests for the local manual export operator runbook; verifies runbook existence, manual/local/offline posture, forbidden runtime/automation scope, explicit local output path and parent-directory requirements, `.md`/`.txt` suffix rules, no committed generated artifacts, forbidden interpretation as trade signal/expected return/position sizing/paper-live readiness/strategy promotion/PR approval/merge readiness, human-review requirement, failure handling, safe illustrative code example, exact WP110 status inventory/stable wording, project-status boundary preservation, and repo-truth registration.

62z103. `docs/status_entries/WP110.md` - WP110 stable committed status fragment for the Hermes candidate-review local manual export operator runbook V1. WP110 is docs/status/tests-only; no source implementation, CLI, scheduler, daemon, background writer, automatic report/export pipeline, network/API/product/account behavior, Hermes runtime/provider/model/prompt runner, credentials/private state, paper/live/execution/risk/order behavior, dashboard, bot loop, dependency, workflow, or committed generated artifact behavior is added.

62z104. `docs/hermes_candidate_review_local_manual_export_smoke_exercise.md` - WP111 docs/status/tests-only temp-only smoke exercise documentation for the existing WP106 -> WP108 -> WP109 manual export path. It states pytest `tmp_path` only, synthetic safe fixture data only, no committed generated artifacts, and no CLI, report/export pipeline, automation, scheduler, daemon, background writer, Hermes runtime/provider/model/prompt runner, network/API/product/account behavior, credentials/private state, paper/live/execution/risk/order behavior, dashboard, bot loop, dependency, workflow, or lock-file authority.

62z105. `tests/test_hermes_candidate_review_local_manual_export_smoke_exercise.py` - WP111 focused smoke/docs/status tests for the temp-only local manual export smoke exercise; verifies the smoke doc, builds a valid synthetic WP106 handoff, builds a valid WP108 artifact, writes it through the existing WP109 writer only under pytest `tmp_path`, checks bytes and sha256, checks safety notices and flags, confirms invalid artifacts fail closed with no file, and verifies project-status and repo-truth registration.

62z106. `docs/status_entries/WP111.md` - WP111 stable committed status fragment for the Hermes candidate-review local manual export temp-only smoke exercise V1. WP111 is docs/status/tests-only; no source implementation, CLI, scheduler, daemon, background writer, automatic report/export pipeline, network/API/product/account behavior, Hermes runtime/provider/model/prompt runner, credentials/private state, paper/live/execution/risk/order behavior, dashboard, bot loop, dependency, workflow, or committed generated artifact behavior is added.

62z107. `docs/hermes_candidate_review_local_manual_export_chain_closeout.md` - WP112 docs/status/tests-only closeout and next-phase decision record for the bounded WP106 -> WP108 -> WP109 -> WP110 -> WP111 local manual export chain. It records supported manual-only local/offline use, evidence of local coherence, output surfaces, forbidden interpretation, open deferred directions, and future phase options; it authorizes no source implementation, CLI, scheduler, daemon, background writer, automation, report pipeline, network/API/product/account behavior, Hermes runtime/provider/model/prompt runner, credentials/private state, paper/live/execution/risk/order behavior, dashboard, bot loop, dependency, workflow, lock-file, or committed generated artifact behavior.

62z108. `tests/test_hermes_candidate_review_local_manual_export_chain_closeout_docs.py` - WP112 focused docs/status tests for the local manual export chain closeout; verifies doc existence, WP106 -> WP108 -> WP109 -> WP110 -> WP111 chain order, manual-only local/offline bounded use, no WP112 source/tool/runtime changes, output surface inventory, no committed generated artifacts, forbidden scope matrix, future options as separate not-authorized WPs, open deferred directions, human review, WP112 status entry inventory/stable wording, project-status boundary preservation, repo-truth registration, and no WP112 src file addition.

62z109. `docs/status_entries/WP112.md` - WP112 stable committed status fragment for the Hermes candidate-review local manual export chain closeout and next-phase decision record V1. WP112 is docs/status/tests-only; no source implementation, tools, CLI, scheduler, daemon, background writer, automatic report/export pipeline, network/API/product/account behavior, Hermes runtime/provider/model/prompt runner, credentials/private state, paper/live/execution/risk/order behavior, dashboard, bot loop, dependency, workflow, lock-file, or committed generated artifact behavior is added.

62z110. `docs/hermes_candidate_review_local_manual_export_cli_wrapper_contract.md` - WP113 docs/status/tests-only future CLI-wrapper contract for the completed WP106 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 local manual export chain. It defines only the safety contract for a possible future manual/local/offline operator convenience wrapper around the existing WP109 local manual export writer; it authorizes no CLI implementation, source module, tool, command parser, command runner, shell wrapper, scheduler, daemon, background writer, automation, report pipeline, network/API/product/account behavior, Hermes runtime/provider/model/prompt runner, credentials/private state, paper/live/execution/risk/order behavior, dashboard, bot loop, dependency, workflow, lock-file, copied external code, or committed generated artifact behavior.

62z111. `tests/test_hermes_candidate_review_local_manual_export_cli_wrapper_contract_docs.py` - WP113 focused docs/status tests for the local manual export CLI wrapper contract; verifies doc existence, docs/status/tests-only posture, no CLI implementation, WP106 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 chain context and WP107 contract layer, manual/local/offline/operator-only boundaries, explicit `.md`/`.txt` output path and existing-parent requirement, forbidden automation/runtime/network/Hermes/credential/paper-live/execution-risk-order scope, forbidden signal/readiness/approval/authority interpretations, fail-closed input requirements, raw model output/raw dictionaries/raw metadata/private state/runtime log rejection, no unsafe echo, human review, separate approved future implementation WP gate, WP113 status inventory/stable wording, project-status boundary preservation, repo-truth registration, and no WP113 source file addition.

62z112. `docs/status_entries/WP113.md` - WP113 stable committed status fragment for the Hermes candidate-review local manual export CLI wrapper contract V1. WP113 is docs/status/tests-only; no source implementation, tools, CLI implementation, command parser, command runner, shell wrapper, scheduler, daemon, background writer, automatic report/export pipeline, network/API/product/account behavior, Hermes runtime/provider/model/prompt runner, credentials/private state, paper/live/execution/risk/order behavior, dashboard, bot loop, dependency, workflow, lock-file, copied external code, or committed generated artifact behavior is added.

62z113. `docs/hermes_candidate_review_local_manual_export_cli_command_surface_contract.md` - WP114 docs/status/tests-only future CLI command-surface and strict input-handoff contract for a possible local/manual/offline wrapper around the existing WP109 local manual export writer. It defines the conceptual future command shape (`--artifact-json`, `--output`, optional `--overwrite` only), strict WP108 artifact-result snapshot handoff envelope, input rejection rules, output behavior, exit-code policy, fail-closed behavior, future negative-test matrix, human-review requirement, and non-authority posture; it authorizes no CLI implementation, source module, tool, command parser, command runner, shell wrapper, JSON parser implementation, scheduler, daemon, background writer, automation, report pipeline, network/API/product/account behavior, Hermes runtime/provider/model/prompt runner, credentials/private state, paper/live/execution/risk/order behavior, dashboard, bot loop, dependency, workflow, lock-file, copied external code, or committed generated artifact behavior.

62z114. `tests/test_hermes_candidate_review_local_manual_export_cli_command_surface_contract_docs.py` - WP114 focused docs/status tests for the CLI command-surface and input-handoff contract; verifies doc existence, docs/status/tests-only posture, no implementation authority, WP106 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 -> WP113 chain context and WP107 contract layer, exact future command surface, forbidden modes/options, strict WP108 input envelope, fail-closed input rejection, output behavior, exit-code policy, failure behavior, future negative-test matrix, human-review requirement, WP114 status inventory/stable wording, project-status boundary preservation, repo-truth registration, and no WP114 source or tools file addition.

62z115. `docs/status_entries/WP114.md` - WP114 stable committed status fragment for the Hermes candidate-review local manual export CLI command surface and input handoff contract V1. WP114 is docs/status/tests-only; no source implementation, tools, CLI implementation, command parser, command runner, shell wrapper, JSON parser implementation, scheduler, daemon, background writer, automatic report/export pipeline, network/API/product/account behavior, Hermes runtime/provider/model/prompt runner, credentials/private state, paper/live/execution/risk/order behavior, dashboard, bot loop, dependency, workflow, lock-file, copied external code, or committed generated artifact behavior is added.

62z116. `tools/hermes_candidate_review_manual_export_cli.py` - WP115 stdlib-only local/offline/manual CLI wrapper around the existing WP109 writer. It accepts exactly `--artifact-json`, `--output`, and optional `--overwrite`; validates a strict local WP108 artifact-result JSON envelope; reconstructs `CandidateReviewManualExportArtifactResult`; delegates rendering/writing to `write_candidate_review_manual_export_artifact`; rejects URI-like, protected repo, tracked repo, local_data, and generated-artifact paths; prints only bounded neutral stdout/stderr summaries; no source implementation under `src/`, no product/runtime/API/account network behavior, no credentials/private state, no account/order/private state, no paper/live/execution/risk/order behavior, no scheduler/dashboard/bot-loop/runtime/daemon behavior, no Hermes runtime/provider/model/prompt runner behavior, no dependency/workflow/lock-file changes, and no committed generated-artifact behavior.

62z117. `tests/test_hermes_candidate_review_manual_export_cli.py` - WP115 focused CLI tests covering exact parser surface, valid strict envelope export through pytest `tmp_path`, bounded success stdout, empty success stderr, written WP109 boundary notice and safety flags, sha256 consistency, invalid envelope failures, missing/wrong source fields, invalid artifact result shape, required group and safety-flag failures, raw/free-form metadata and forbidden wording rejection, URI/protected/output path failures, overwrite behavior, no unsafe echo, no artifact-content stdout/stderr, source import allowlist, forbidden import/mode scan, changed-file inventory, project-status boundary preservation, and repo-truth registration.

62z118. `docs/status_entries/WP115.md` - WP115 stable committed status fragment for the Hermes candidate-review local manual export CLI wrapper implementation V1. WP115 implements only the local/offline/manual wrapper around the existing WP109 writer for strict WP108 artifact-result envelopes; no source implementation under `src/`, no product/runtime/API/account network behavior, no credentials/private state, no paper/live/execution/risk/order behavior, no scheduler/dashboard/bot-loop/runtime/daemon behavior, no Hermes runtime/provider/model/prompt runner behavior, no dependency/workflow/lock-file changes, and no committed generated-artifact behavior is added.

62z119. `docs/hermes_candidate_review_local_manual_export_cli_operator_runbook.md` - WP116 docs/status/tests-only operator runbook for safe manual use of the existing WP115 local/offline/manual CLI wrapper. It records the exact command shape, strict WP108 artifact-result JSON envelope preflight, explicit local `.md`/`.txt` output path preflight, success/failure behavior, cleanup rules, human-review requirement, forbidden interpretation, and future gates. It adds no CLI modification, no source implementation, no runtime/Hermes/network/credential/paper/live/execution/scheduler/dashboard/dependency behavior, and no committed generated artifacts.

62z120. `docs/hermes_candidate_review_local_manual_export_cli_smoke_receipt.md` - WP116 concise docs/status/tests-only smoke receipt for the existing WP115 CLI temp-path command path. It states that WP115 focused tests already prove pytest `tmp_path` CLI coherence and that WP116 adds no implementation or generated artifact content.

62z121. `tests/test_hermes_candidate_review_local_manual_export_cli_operator_runbook_docs.py` - WP116 focused docs/status tests for the CLI operator runbook, smoke receipt, status fragment, project-status registration, repo-truth-index registration, and changed-file inventory boundary.

62z122. `docs/status_entries/WP116.md` - WP116 stable committed status fragment for the Hermes candidate-review local manual export CLI operator runbook and smoke receipt V1. WP116 is docs/status/tests-only; no CLI modification, no source implementation under `src/`, no product/runtime/API/account network behavior, no credentials/private state, no paper/live/execution/risk/order behavior, no scheduler/dashboard/bot-loop/runtime/daemon behavior, no Hermes runtime/provider/model/prompt runner behavior, no dependency/workflow/lock-file changes, and no committed generated-artifact behavior is added.

62z123. `docs/hermes_candidate_review_local_manual_export_cli_chain_closeout.md` - WP117 docs/status/tests-only CLI chain closeout and research-workflow transition decision record for the completed WP106 -> WP107 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 -> WP113 -> WP114 -> WP115 -> WP116 local/manual export and CLI convenience chain. It records that the chain is complete enough for bounded operator use, supports only manual/local/offline/human-reviewed export of already-valid WP108 artifact-result envelopes through the WP115 CLI or lower-level import path, frames the WP115 CLI as a convenience wrapper and not automation, and records the next recommended phase as Hermes-assisted candidate-review research workflow, not paper/live trading. It authorizes no implementation, no WP115 CLI modification, no source under `src/`, no tools behavior, no automated report/export pipeline, no network/API/product/account behavior, no Hermes runtime/provider/model/prompt runner, no credentials/private state, no paper/live/execution/risk/order behavior, no dashboard, no scheduler/bot loop, no dependency/workflow/lock-file change, no copied external code, and no committed generated artifact behavior.

62z124. `tests/test_hermes_candidate_review_local_manual_export_cli_chain_closeout_docs.py` - WP117 focused docs/status tests for the CLI chain closeout and transition decision record; verifies doc existence, completed-chain order, docs/status/tests-only posture, no implementation authority, bounded manual/local/offline/human-reviewed support, WP115 CLI convenience-wrapper boundary, generated-artifact no-commit rule, human-review requirement, forbidden interpretation matrix, deferred future directions, next-phase decision, status fragment inventory/stable wording, project-status WP117 target and WP116 merged state, repo-truth registration, and forbidden changed-file inventory exclusions.

62z125. `docs/status_entries/WP117.md` - WP117 stable committed status fragment for the Hermes candidate-review local manual export CLI chain closeout and research-workflow transition decision record V1. WP117 is docs/status/tests-only; no implementation change, no WP115 CLI modification, no source implementation under `src/`, no product/runtime/API/account network behavior, no credentials/private state, no paper/live/execution/risk/order behavior, no scheduler/dashboard/bot-loop/runtime/daemon behavior, no Hermes runtime/provider/model/prompt runner behavior, no dependency/workflow/lock-file changes, and no committed generated-artifact behavior is added.

62z126. `docs/hermes_candidate_review_research_workflow_intake_contract.md` - WP118 docs/status/tests-only Hermes candidate-review research workflow intake contract V1. It defines manual/local/offline/advisory-only human-reviewed packet-selection discipline for future Hermes-assisted candidate-review research preparation from already-valid upstream candidate-review artifacts or packets. It authorizes no parser, loader, runner, output schema, writer, validator, storage, CLI behavior, automation, Hermes runtime/provider/model/prompt runner behavior, network/API/product/account behavior, credentials/private state, paper/live/execution/risk/order behavior, scheduler/dashboard/bot-loop/runtime/daemon behavior, dependency/workflow/lock-file changes, or committed generated artifacts.

62z127. `tests/test_hermes_candidate_review_research_workflow_intake_contract_docs.py` - WP118 focused docs/status tests for the Hermes candidate-review research workflow intake contract; verifies doc existence, docs/status/tests-only posture, chain context through WP117, supported manual/local/offline/advisory-only/human-reviewed intake, allowed conceptual input surfaces, no parser/loader/implementation authority, required preflight checks, non-executing research triage criteria, future output concepts without implementation, forbidden interpretation matrix, future gates, status fragment inventory/stable wording, project-status WP118 target and WP117 merged state, repo-truth registration, and forbidden changed-file inventory exclusions.

62z128. `docs/status_entries/WP118.md` - WP118 stable committed status fragment for the Hermes candidate-review research workflow intake contract V1. WP118 is docs/status/tests-only; no implementation, no runtime, no automation, no Hermes execution, no trading, and no committed generated artifacts are added.

62z129. `docs/hermes_candidate_review_research_workflow_runbook.md` - WP119 docs/status/tests-only Hermes candidate-review research workflow runbook V1. It documents the manual/local/offline/advisory-only operator workflow after WP118 intake and before future schemas/storage/implementation. It defines operator preconditions, manual workflow steps, neutral non-executing research-question rules, manual Hermes prompt adaptation boundaries, advisory output review boundaries, conceptual human decision categories, cleanup/repo hygiene, future gates, and non-authority posture. It authorizes no implementation, runtime, automation, Hermes execution, trading, storage, or committed generated artifacts.

62z130. `tests/test_hermes_candidate_review_research_workflow_runbook_docs.py` - WP119 focused docs/status tests for the Hermes candidate-review research workflow runbook; verifies doc existence, docs/status/tests-only posture, WP118 intake-contract reference, completed WP106 -> WP117 chain context, operator preconditions, manual workflow steps, research-question allowed/forbidden families, manual Hermes prompt adaptation boundary, advisory output review boundary, conceptual human decision categories, cleanup/repo hygiene, future gates, status fragment inventory/stable wording, project-status WP119 target and WP118 merged state, repo-truth registration, and forbidden changed-file inventory exclusions.

62z131. `docs/status_entries/WP119.md` - WP119 stable committed status fragment for the Hermes candidate-review research workflow runbook V1. WP119 is docs/status/tests-only; no implementation, no runtime, no automation, no Hermes execution, no trading, and no committed generated artifacts are added.

62z132. `docs/hermes_candidate_review_research_question_record_contract.md` - WP120 docs/status/tests-only Hermes candidate-review research question record contract V1. It defines conceptual future field concepts, allowed non-executing research question types, forbidden research question types, evidence/preflight requirements, human review requirements, future gates, and non-authority posture for future manual/local/offline/advisory-only planning records after WP118 intake and WP119 runbook. It authorizes no record object, schema class, parser, writer, loader, storage path, CLI behavior, validator change, Hermes prompt runner, model/provider integration, automation, report pipeline, dashboard, paper/live behavior, execution/risk/order behavior, credentials, workflow, dependency, generated artifact, source implementation, or tools behavior.

62z133. `tests/test_hermes_candidate_review_research_question_record_contract_docs.py` - WP120 focused docs/status tests for the Hermes candidate-review research question record contract; verifies doc existence, docs/status/tests-only posture, WP118 intake and WP119 runbook context, conceptual required fields, no schema/storage implementation, allowed and forbidden research question types, evidence/preflight requirements, human review, future gates, status fragment inventory/stable wording, project-status WP120 target and WP119 merged state, repo-truth registration, and forbidden changed-file inventory exclusions.

62z134. `docs/status_entries/WP120.md` - WP120 stable committed status fragment for the Hermes candidate-review research question record contract V1. WP120 is docs/status/tests-only; no implementation, no runtime, no automation, no Hermes execution, no trading, and no committed generated artifacts are added.

62z135. `src/data_layer/hermes_candidate_review_research_question_record.py` - WP121 stdlib-only local/offline/read-only in-memory Hermes candidate-review research question record validator/build/assert module implementing the WP120 contract for explicit caller-supplied mappings only. It enforces required fields, allowed research question types, required preflight flags, required non-authority safety flags, human review, non-authority notice safety, recursive raw/free-form metadata rejection, recursive forbidden-content rejection, fail-closed empty invalid records, and no unsafe echo in invalid result surfaces. It adds no parser, loader, writer, storage path, CLI, report/export pipeline, Hermes runtime/provider/model/prompt runner, product/runtime/API/account network behavior, credentials/private state, paper/live/execution/risk/order behavior, scheduler/dashboard/bot-loop/runtime/daemon behavior, dependency/workflow/lock-file changes, or committed generated artifacts.

62z136. `tests/test_hermes_candidate_review_research_question_record.py` - WP121 focused validator tests for the in-memory research question record module; covers stdlib-only imports, valid minimal records, sanitized safety flags, required fields, allowed/unknown research question types, exact `WALLET_SIGNAL_UNCERTAINTY` enum handling, wallet/account/private-state data rejection, human-review and safety/preflight enforcement, non-authority notice enforcement, forbidden trade/action/scoring/readiness/credential/runtime/prompt/scheduler/dashboard/storage/CLI terms, recursive raw/free-form metadata keys, nested forbidden keys and values, no unsafe echo across invalid result fields, neutral assert errors, build/validate alias behavior, result field coverage, no file/network/subprocess/CLI/env/dependency behavior, changed-file inventory, project-status reconciliation, and repo-truth registration.

62z137. `docs/status_entries/WP121.md` - WP121 stable committed status fragment for the Hermes candidate-review research question record implementation packet V1. WP121 is a Tier 2 bundled local/offline/manual implementation packet adding one in-memory stdlib-only validator module, focused tests, and repo-truth/status reconciliation only; no runtime, automation, Hermes execution, trading, parser/loader/writer/storage, CLI, report/export pipeline, dependency, workflow, or committed generated artifacts are added.

62z138. `src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py` - WP122 stdlib-only local/offline/read-only in-memory Hermes candidate-review advisory output validation receipt validator/build/assert module for explicit caller-supplied mappings only. It enforces required receipt fields, allowed receipt labels, required review flags, required non-authority safety flags, human review, non-authority notice safety, recursive raw/free-form metadata rejection, recursive forbidden-content rejection, fail-closed empty invalid receipts, and no unsafe echo in invalid result surfaces. It adds no parser, loader, writer, storage path, CLI, report/export pipeline, Hermes runtime/provider/model/prompt runner, product/runtime/API/account network behavior, credentials/private state, paper/live/execution/risk/order behavior, scheduler/dashboard/bot-loop/runtime/daemon behavior, dependency/workflow/lock-file changes, or committed generated artifacts.

62z139. `tests/test_hermes_candidate_review_advisory_output_validation_receipt.py` - WP122 focused validator tests for the in-memory advisory output validation receipt module; covers stdlib-only imports, valid minimal receipts, allowed/unknown receipt labels, sanitized safety flags, required fields, human-review and safety/review-flag enforcement, non-authority notice enforcement, forbidden trade/action/scoring/readiness/authority/credential/runtime/prompt/scheduler/dashboard/storage/CLI terms, recursive raw/free-form metadata keys, nested forbidden keys and values, no unsafe echo across invalid result fields, neutral assert errors, validation precedence, build/validate alias behavior, result field coverage, no file/network/subprocess/CLI/env/dependency behavior, project-status reconciliation, protected boundary preservation, and repo-truth registration.

62z140. `docs/status_entries/WP122.md` - WP122 stable committed status fragment for the Hermes candidate-review advisory output validation receipt packet V1. WP122 is a Tier 2 bundled local/offline/manual implementation packet adding one in-memory stdlib-only validator module, focused tests, and repo-truth/status reconciliation only; no runtime, automation, Hermes execution, trading, parser/loader/writer/storage, CLI, report/export pipeline, dependency, workflow, or committed generated artifacts are added.

62z141. `src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py` - WP123 stdlib-only local/offline/read-only in-memory Hermes candidate-review human decision and follow-up research task record validator/build/assert module for explicit caller-supplied mappings only. It enforces required decision/task fields, allowed decision/task labels, required non-authority safety flags, human review, non-authority notice safety, recursive raw/free-form metadata rejection, recursive forbidden-content rejection, fail-closed empty decision/task records, and no unsafe echo in invalid result surfaces. It adds no parser, loader, writer, storage path, CLI, report/export pipeline, Hermes runtime/provider/model/prompt runner, product/runtime/API/account network behavior, credentials/private state, paper/live/execution/risk/order behavior, scheduler/dashboard/bot-loop/runtime/daemon behavior, dependency/workflow/lock-file changes, or committed generated artifacts.

62z142. `tests/test_hermes_candidate_review_human_decision_follow_up_record.py` - WP123 focused validator tests for the in-memory human decision and follow-up task record module; covers stdlib-only imports, valid records, allowed/unknown labels, sanitized safety flags, required fields, human-review enforcement, non-authority notice enforcement, forbidden trade/action/scoring/readiness/authority/credential/runtime/prompt/scheduler/dashboard/storage/CLI terms, recursive raw/free-form metadata keys, nested forbidden keys and values, no unsafe echo across invalid result fields, neutral assert errors, build/validate alias behavior, result field coverage, no file/network/subprocess/CLI/env/dependency behavior, project-status reconciliation, and repo-truth registration.

62z143. `docs/status_entries/WP123.md` - WP123 stable committed status fragment for the Hermes candidate-review human decision and follow-up record packet V1. WP123 is a Tier 2 bundled local/offline/manual implementation packet adding one in-memory stdlib-only validator module, focused tests, and repo-truth/status reconciliation only; no runtime, automation, Hermes execution, trading, parser/loader/writer/storage, CLI, report/export pipeline, dependency, workflow, or committed generated artifacts are added.

62z144. `src/data_layer/hermes_candidate_review_manual_research_session_package.py` - WP124 stdlib-only local/offline/read-only in-memory Hermes candidate-review manual research session package validator/build/assert module. It combines explicit caller-supplied research question, advisory receipt, human decision, and manual follow-up task records; enforces required fields, nested shapes, allowed session labels, exact safety flags, human review, non-authority notice safety, recursive raw/free-form metadata rejection, recursive forbidden-content rejection, fail-closed empty invalid packages, and no unsafe echo. It adds no parser, loader, writer, storage, CLI, report/export pipeline, Hermes runtime/provider/model/prompt runner, network, credentials/private state, paper/live/execution/risk/order behavior, automation, dependency/workflow/lock-file changes, or committed generated artifacts.

62z145. `tests/test_hermes_candidate_review_manual_research_session_package.py` - WP124 focused validator tests covering stdlib-only imports, valid packages, all labels, required fields and shapes, exact human-review and safety flags, notice safety, sanitized outputs, build/assert behavior, result fields, recursive forbidden terms and raw metadata, nested reviewer traps, fail-closed neutral diagnostics, and no unsafe echo.

62z146. `docs/status_entries/WP124.md` - WP124 stable committed status fragment for the Hermes candidate-review manual research session package builder V1. WP124 is a Tier 2 bundled local/offline/manual implementation packet adding one in-memory stdlib-only validator module, focused tests, and repo-truth/status reconciliation only.

62z147. `docs/hermes_candidate_review_manual_research_session_package_operator_runbook.md` - WP125 manual/local/offline/advisory-only operator runbook for the completed WP121 -> WP122 -> WP123 -> WP124 in-memory record/session chain; documents synthetic fixture, human-review, repo-hygiene, forbidden-interpretation, and future-gate boundaries.

62z148. `tests/test_hermes_candidate_review_manual_research_session_package_operator_runbook_docs.py` - WP125 focused documentation test for the operator runbook and its explicit non-authority boundaries.

62z149. `tests/test_hermes_candidate_review_manual_research_session_package_temp_smoke.py` - WP125 temp-only synthetic smoke test exercising the existing WP121-WP124 builders in memory, including fail-closed no-echo trap coverage and an empty pytest `tmp_path` assertion.

62z150. `docs/status_entries/WP125.md` - WP125 stable committed status fragment for the docs/status/tests plus temp-only smoke package; no source, runtime, persistence, export/report, CLI, network, credential, automation, or trading authority.

62z151. `src/data_layer/hermes_candidate_review_research_candidate_queue.py` - WP126 stdlib-only local/offline/read-only in-memory research candidate queue item/package validator, builder, and assert contract for explicit caller-supplied mappings; fail-closed neutral diagnostics, recursive forbidden-content/raw-metadata rejection, exact safety flags, and no unsafe echo; no runtime, network, persistence, automation, scoring, discovery, or trading authority.

62z152. `tests/test_hermes_candidate_review_research_candidate_queue.py` - WP126 focused positive and negative tests for queue item/package labels, fields, shapes, safety flags, notices, recursive forbidden families, raw metadata, mutation safety, fail-closed no-echo results, assert helpers, and result dataclasses.

62z153. `docs/status_entries/WP126.md` - WP126 stable committed status fragment for the Tier 2 local/offline/manual in-memory research candidate queue implementation packet.

62z154. `docs/hermes_candidate_review_research_candidate_queue_operator_runbook.md` - WP127 manual/local/offline/advisory-only operator runbook for safe explicit in-memory use of the merged WP126 candidate item and non-empty queue package contract; documents synthetic fixture, human-review, cleanup, forbidden-interpretation, and future-gate boundaries.

62z155. `tests/test_hermes_candidate_review_research_candidate_queue_operator_runbook_docs.py` - WP127 focused documentation test for the queue operator runbook structure and explicit non-authority boundaries.

62z156. `tests/test_hermes_candidate_review_research_candidate_queue_temp_smoke.py` - WP127 temp-only synthetic smoke test for a valid WP126 candidate item and non-empty queue package, fail-closed no-echo trap behavior, exact safety flags, and an empty pytest `tmp_path`.

62z157. `docs/status_entries/WP127.md` - WP127 stable committed status fragment for the docs/status/tests plus temp-only smoke package; no source, runtime, persistence, export/report, CLI, automation, discovery, ingestion, scoring/ranking, credential, or trading authority.

62z158. `src/data_layer/hermes_candidate_review_manual_queue_selection_handoff.py` - WP128 stdlib-only deterministic in-memory validator/build/assert contract for explicit human queue selection/rejection records and caller-supplied proposed research-question handoffs; exact safety flags, recursive forbidden/raw-metadata rejection, fail-closed neutral no-echo behavior, and no automated selection, ranking, scoring, priority, discovery, ingestion, question-generation, persistence, runtime, prompt, or trading authority.

62z159. `tests/test_hermes_candidate_review_manual_queue_selection_handoff.py` - WP128 focused positive, negative-matrix, and reviewer-trap coverage for manual selection and research-question handoff contracts.

62z160. `docs/status_entries/WP128.md` - WP128 stable committed status fragment for the Tier 2 explicit-human-selection-only in-memory implementation packet.

62z161. `docs/hermes_candidate_review_manual_queue_selection_research_question_chain_operator_runbook.md` - WP129 manual/local/offline/advisory-only runbook for the explicit-human-selection-only WP126 → WP128 → WP121 in-memory compatibility chain.

62z162. `tests/test_hermes_candidate_review_manual_queue_selection_research_question_chain_operator_runbook_docs.py` - WP129 focused documentation test for required chain structure and non-authority boundaries.

62z163. `tests/test_hermes_candidate_review_manual_queue_selection_research_question_chain_temp_smoke.py` - WP129 temp-only synthetic smoke and reviewer-trap coverage for manual queue selection, caller-supplied question handoff, and manual WP121 record assembly with no output.

62z164. `docs/status_entries/WP129.md` - WP129 stable committed status fragment for the docs/status/tests plus temp-only synthetic smoke package; no source, adapter, automation, persistence, runtime, network, credential, or trading authority.

62z165. `src/data_layer/hermes_candidate_review_manual_research_briefing_packet.py` - WP130 stdlib-only deterministic in-memory validator/build/assert contract for explicit caller-supplied manual research briefing packets; preserves safe research-question content, enforces exact labels/fields/safety flags and bounded notice handling, rejects recursive forbidden/raw metadata, and fails closed without unsafe echo; no prompt, model/provider/Hermes, response/finding generation, network, ingestion, scoring, priority, recommendation, persistence, CLI, runtime, or trading authority.

62z166. `tests/test_hermes_candidate_review_manual_research_briefing_packet.py` - WP130 focused positive, negative-matrix, and reviewer-trap coverage for the manual research briefing packet contract.

62z167. `docs/status_entries/WP130.md` - WP130 stable committed status fragment for the Tier 2 explicit-caller-content-only in-memory implementation packet.

62z168. `docs/hermes_candidate_review_manual_research_briefing_packet_operator_runbook.md` - WP131 manual, local, offline operator runbook for constructing and inspecting one synthetic WP130 packet in memory only.

62z169. `tests/test_hermes_candidate_review_manual_research_briefing_packet_operator_runbook_docs.py` - WP131 exact-heading, schema, and non-authority documentation checks.

62z170. `tests/test_hermes_candidate_review_manual_research_briefing_packet_temp_smoke.py` - WP131 temp-only synthetic positive, negative-shape, unsafe-no-echo, unknown-field, and AST reviewer-trap smoke coverage.

62z171. `docs/status_entries/WP131.md` - WP131 stable committed status fragment for the docs/status/tests plus temp-only synthetic smoke package.

62z172. `src/data_layer/hermes_candidate_review_manual_research_request.py` - WP132 stdlib-only deterministic in-memory validator/build/assert contract for explicit caller-supplied manual research requests; enforces exact fields, label families, bounded integers, safety flags, notice concepts, recursive forbidden/raw content rejection, and neutral fail-closed no-echo output without prompt, model, tool, network, storage, runtime, or trading authority.

62z173. `tests/test_hermes_candidate_review_manual_research_request.py` - WP132 focused positive, negative-matrix, bounded-integer, notice, immutability, no-echo, and reviewer-trap coverage for the manual research-request contract.

62z174. `docs/status_entries/WP132.md` - WP132 stable committed status fragment for the Tier 2 explicit-caller-content-only in-memory implementation packet.

62z175. `src/data_layer/hermes_candidate_review_manual_research_response.py` - WP133 stdlib-only deterministic in-memory validator/build/assert contract for explicit caller-supplied manual research responses; enforces exact fields, label families, human review, safety flags, notice concepts, recursive forbidden/raw content rejection, and neutral fail-closed no-echo output without source/citation verification, prompt, model, tool, network, storage, runtime, recommendation, probability, or trading authority.

62z176. `tests/test_hermes_candidate_review_manual_research_response.py` - WP133 focused positive, exhaustive negative-matrix, notice, immutability, no-echo, field-coverage, and reviewer-trap coverage for the manual research-response contract.

62z177. `docs/status_entries/WP133.md` - WP133 stable committed status fragment for the Tier 2 explicit-caller-content-only in-memory implementation packet.

62z178. `docs/hermes_candidate_review_manual_research_response_operator_runbook.md` - WP134 manual/local/offline operator runbook for explicit construction and inspection through the merged WP133 API, with no adapter, generation, verification, I/O, runtime, or trading authority.

62z179. `tests/test_hermes_candidate_review_manual_research_response_operator_runbook_docs.py` - WP134 exact-heading, API, schema, shape, and non-authority documentation checks.

62z180. `tests/test_hermes_candidate_review_manual_research_response_temp_smoke.py` - WP134 synthetic in-memory positive, negative-shape, flag, no-echo, unknown-authority-field, AST reviewer-trap, and empty-temp-directory smoke coverage.

62z181. `docs/status_entries/WP134.md` - WP134 stable committed status fragment for the docs/status/tests plus temp-only synthetic smoke package.

62z182. `docs/hermes_candidate_review_manual_research_request_response_session_chain_operator_runbook.md` - WP135 manual/local/offline request-to-response compatibility runbook for independently constructing and validating explicit WP132 request and WP133 response mappings, followed by eight manual test-only linkage comparisons; no adapter, automatic transfer, chain/session product object, generation, verification, I/O, runtime, or trading authority.

62z183. `tests/test_hermes_candidate_review_manual_research_request_response_session_chain_operator_runbook_docs.py` - WP135 focused documentation tests for exact heading order, both public APIs and schemas, eight linkage relationships, independent-contract semantics, and non-authority boundaries.

62z184. `tests/test_hermes_candidate_review_manual_research_request_response_session_chain_temp_smoke.py` - WP135 synthetic in-memory positive linkage, valid-but-mismatched, representative invalid no-echo, exact assertion, AST reviewer-trap, independent-fixture, and empty-temp-directory smoke coverage.

62z185. `docs/status_entries/WP135.md` - WP135 stable committed status fragment for the docs/status/tests plus temp-only synthetic manual request-to-response chain smoke package.

62z186. `docs/hermes_candidate_review_manual_request_response_validation_receipt_chain_contract_and_smoke_decision_record.md` - WP136 compatibility decision rejecting a direct WP132-to-WP133-to-WP122 smoke, requiring explicit WP121 research-question lineage, and specifying only a future separately approved four-record synthetic topology with no source or smoke implementation.

62z187. `tests/test_hermes_candidate_review_manual_request_response_validation_receipt_chain_contract_and_smoke_decision_record_docs.py` - WP136 focused Markdown-only tests for exact headings, all fourteen future linkage assertions, explicit non-linkages, WP122 caveats, field non-reinterpretation, and non-authority boundaries.

62z188. `docs/status_entries/WP136.md` - WP136 stable committed status fragment for the docs/status/tests-only compatibility contract and smoke-decision package.

62z189. `docs/hermes_candidate_review_manual_research_question_request_response_validation_receipt_four_record_chain_operator_runbook.md` - WP137 manual/local/offline four-record lineage runbook for independently authored WP121, WP132, WP133, and WP122 records with fourteen post-validation comparisons and no adapter, transfer, verification, I/O, runtime, or trading authority.

62z190. `tests/test_hermes_candidate_review_manual_research_question_request_response_validation_receipt_four_record_chain_operator_runbook_docs.py` - WP137 focused documentation tests for exact headings, four APIs, fixture independence, fourteen relationships, non-linkages, mismatch/human-review/no-echo matrices, compatibility caveats, and non-authority boundaries.

62z191. `tests/test_hermes_candidate_review_manual_research_question_request_response_validation_receipt_four_record_chain_temp_smoke.py` - WP137 synthetic in-memory positive lineage, thirteen valid-but-inconsistent cases, four human-review failures, four unsafe no-echo cases, AST independence traps, and empty-temp-directory coverage.

62z192. `docs/status_entries/WP137.md` - WP137 stable committed status fragment for the docs/status/tests plus temp-only synthetic four-record manual-lineage smoke package.

62z193. `docs/hermes_candidate_review_manual_four_record_lineage_human_decision_follow_up_chain_contract_and_smoke_decision_record.md` - WP138 compatibility decision approving only for a separate WP the future WP121-to-WP132-to-WP133-to-WP122-to-WP123-decision-to-WP123-follow-up-task synthetic topology, distinguishing direct from inherited lineage, and adding no source or smoke implementation.

62z194. `tests/test_hermes_candidate_review_manual_four_record_lineage_human_decision_follow_up_chain_contract_and_smoke_decision_record_docs.py` - WP138 focused Markdown-only tests for exact headings, WP123 public surfaces, eighteen future relationships, explicit non-linkages, direct-versus-inherited lineage, compatibility caveats, field non-reinterpretation, and non-authority boundaries.

62z195. `docs/status_entries/WP138.md` - WP138 stable committed status fragment for the docs/status/tests-only compatibility contract and future six-record smoke decision package.

62z196. `docs/hermes_candidate_review_manual_six_record_research_lineage_human_decision_follow_up_task_operator_runbook.md` - WP139 manual/local/offline operator runbook for six independently authored WP121, WP132, WP133, WP122, WP123-decision, and WP123-follow-up-task records with eighteen post-validation relationships, sixteen explicit non-linkages, and no adapter, generation, I/O, runtime, or authority expansion.

62z197. `tests/test_hermes_candidate_review_manual_six_record_research_lineage_human_decision_follow_up_task_operator_runbook_docs.py` - WP139 focused Markdown-only tests for exact headings, six API families, fixture independence, eighteen relationships, sixteen non-linkages, seventeen mismatch cases, human-review/no-echo matrices, WP123 caveats, and non-authority boundaries.

62z198. `tests/test_hermes_candidate_review_manual_six_record_research_lineage_human_decision_follow_up_task_temp_smoke.py` - WP139 synthetic in-memory positive six-record lineage, seventeen exactly-one-false mismatch cases, six human-review failures, six unsafe no-echo cases, AST independence traps, forbidden-output-key checks, and empty-temp-directory coverage.

62z199. `docs/status_entries/WP139.md` - WP139 stable committed status fragment for the docs/status/tests plus temp-only synthetic six-record manual-lineage, human-decision, and follow-up-task smoke package.

62z200. `docs/hermes_candidate_review_manual_six_record_workflow_closeout_and_assisted_research_transition_decision_record.md` - WP140 docs/status/tests-only decision record closing the bounded six-record manual candidate-review workflow as complete enough for controlled manual/local/offline use, stopping default manual-chain extension, and selecting a separately gated provider-neutral assisted-research experiment contract while preserving deterministic and human authority.

62z201. `tests/test_hermes_candidate_review_manual_six_record_workflow_closeout_and_assisted_research_transition_decision_record_docs.py` - WP140 focused Markdown-only tests for exact headings and locked decisions, workflow coverage, complete closeout criteria, provider-neutral WP141 input/output and evaluation boundaries, deferred capabilities, deterministic authority, no-source/no-smoke/no-runtime posture, and reviewer traps.

62z202. `docs/status_entries/WP140.md` - WP140 stable committed status fragment for the docs/status/tests-only manual six-record workflow closeout and assisted-research transition decision package.

62z203. `docs/hermes_candidate_review_assisted_research_session_experiment_contract.md` - WP141 provider-neutral, runtime-inactive experiment contract defining already-valid sanitized inputs, an untrusted WP133-aligned draft boundary, source/citation disclosure, deterministic and human review gates, quality/cost/latency/repeatability/privacy measurement, stop conditions, promotion criteria, and a separately gated WP142 boundary without runtime or trading authority.

62z204. `tests/test_hermes_candidate_review_assisted_research_session_experiment_contract_docs.py` - WP141 focused Markdown-only tests for exact structure, locked decisions, all 30 WP133 fields, input/output boundaries, disclosure and traceability, review and validation gates, complete case/metric inventories, zero-incidence gates, privacy/stops/promotion, WP142 gating, and reviewer traps.

62z205. `docs/status_entries/WP141.md` - WP141 stable committed status fragment for the docs/status/tests-only provider-neutral, runtime-inactive assisted-research experiment contract package.

62z206. `docs/hermes_candidate_review_assisted_research_experiment_gold_case_fixture_pack_and_evaluation_rubric.md` - WP142 canonical local synthetic/offline test-only 20-case gold-case pack and 16-category human-review rubric; records the 6/6/8 family split, expected safe outcomes, disclosures, forbidden behaviors, three-level scale, ten zero-tolerance hard gates, applicability rules, normative future thresholds, privacy/no-verification boundaries, and separately gated WP143 without runtime or trading authority.

62z207. `tests/fixtures/hermes_candidate_review_assisted_research_gold_cases.json` - WP142 sole static UTF-8 synthetic/offline test-only fixture data file; contains exactly 20 ordered cases, exact authority posture, rubric, thresholds, expected outcomes, required disclosures, forbidden behaviors, applicable categories, and all-true hard-gate expectations; no real source, URL, market, wallet, account, person, provider, credential, prompt, model output, timestamp, or runtime configuration.

62z208. `tests/test_hermes_candidate_review_assisted_research_experiment_gold_case_fixture_pack_docs.py` - WP142 focused Markdown-only tests for exact structure, locked decisions, 20 case IDs and 6/6/8 counts, outcomes, disclosure and prohibition inventories, rubric, scale, applicability, gates, thresholds, evaluation concepts, synthetic/privacy/no-verification boundaries, output inventory, forbidden interpretations, WP143 gate, and no implementation claims.

62z209. `tests/test_hermes_candidate_review_assisted_research_experiment_gold_case_fixture_pack.py` - WP142 test-only static fixture/rubric validation and in-memory negative mutation suite; verifies exact keys, versions, IDs, counts, outcomes, disclosures, categories, scale, gates, applicability, thresholds, arithmetic, synthetic safety, immutability, and no side effects without product imports, network, or writes.

62z210. `docs/status_entries/WP142.md` - WP142 stable committed status fragment for the docs/status/tests plus sole static synthetic fixture package.

62z211. `docs/hermes_candidate_review_assisted_research_provider_runtime_privacy_permissions_budget_decision.md` - WP143 canonical provider/runtime/privacy/permissions/budget governance decision selecting a future local deterministic control plane with an ephemeral Hermes session, at most two provider-neutral remote candidates plus one optional local baseline, synthetic-only data, one-endpoint future network allowlisting, least-privilege file/credential/memory posture, exact 140-call and USD 100/25/2 caps, deterministic validation, human review, and promotion gates without runtime, provider, credential, product-network, storage, or trading activation.

62z212. `tests/test_hermes_candidate_review_assisted_research_provider_runtime_privacy_permissions_budget_decision_docs.py` - WP143 focused Markdown-only tests for exact structure and decisions, four runtime options, provider eligibility, privacy/retention/jurisdiction/deletion, the complete permission matrix, credential/memory/network/file policies, budget/call/retry/token/latency caps, accounting, stops, evaluation/promotion gates, deferrals, output boundaries, reviewer traps, and the separately gated WP144 boundary.

62z213. `docs/status_entries/WP143.md` - WP143 stable committed status fragment for the documentation/status/tests-only provider, runtime, privacy, permissions, credential, and budget architecture decision package.

62z214. `docs/hermes_candidate_review_assisted_research_controlled_experiment_harness_contract_prompt_configuration_boundary_and_dry_run_plan.md` - WP144 canonical documentation-only, runtime-inactive future harness contract and local no-provider dry-run plan; defines local deterministic exclusive controller ownership, the exact 17-state failed-closed state machine, synthetic session-envelope and non-executable prompt/configuration boundaries, a one-endpoint provider-adapter boundary, WP143 permission/credential/budget preservation, forbidden-by-default raw persistence, exact future sanitized metadata, mandatory teardown, an 18-row failure matrix, five dry-run stages, promotion gates, and separately gated WP145 without implementation or trading authority.

62z215. `tests/test_hermes_candidate_review_assisted_research_controlled_experiment_harness_contract_prompt_configuration_boundary_and_dry_run_plan_docs.py` - WP144 focused Markdown-only tests for exact structure and locked posture, conceptual flow, controller ownership, 17 states, envelope/prompt/config/adapter boundaries, WP143 permissions/credentials/budgets, retry and timeout limits, raw/evidence policy, teardown, failure matrix, five dry-run stages and acceptance, security invariants, deferrals, output inventory, reviewer traps, and the separately gated WP145 boundary.

62z216. `docs/status_entries/WP144.md` - WP144 stable committed status fragment for the documentation/status/tests-only harness contract, prompt/configuration boundary, and dry-run-plan package.

62z217. `src/data_layer/hermes_candidate_review_assisted_research_local_dry_run_harness.py` - WP145 local/offline/test-oriented deterministic in-memory controller skeleton for exactly one caller-supplied `GC-P01-COMPLETE-SUPPORTED` WP142 case; exposes exact input validation, immutable sanitized session-envelope construction, an inert precomputed plain synthetic-response handoff with zero external callable invocations, existing WP133 deterministic validation, exact positive-case label/completion enforcement, explicit derivation of all ten WP142 hard gates, recursive source-access claim scanning across validated text surfaces, explicit caller-supplied human-review acknowledgement, sanitized result assertion, and mandatory success/failure teardown across the exact 17-state model; returns frozen sanitized results with neutral no-echo diagnostics and no filesystem I/O, network, credentials, Hermes/provider/model call, source access, retry, stable output, downstream records, paper/live, execution/risk/order, or trading behavior.

62z218. `tests/test_hermes_candidate_review_assisted_research_local_dry_run_harness.py` - WP145 focused positive, negative-matrix, state/order, input/permission/budget/output-policy, immutable-envelope, callable/custom-container rejection without execution, exact positive outcome, explicit ten-gate derivation, injected false-gate rejection, recursive scalar/sequence source-claim scanning, WP133 reuse, no-echo, human-review, sanitized-evidence, teardown, deterministic repeat, field-coverage, AST/no-I/O/no-network/no-Hermes/no-provider/no-random/no-storage, exact source-inventory, and protected-boundary tests.

62z219. `tests/test_hermes_candidate_review_assisted_research_local_dry_run_harness_temp_smoke.py` - WP145 pytest `tmp_path` smoke for exactly one unchanged existing WP142 case and one precomputed plain synthetic response, including the full positive state trace plus callable-rejection-without-execution, invalid-output, unsafe-no-echo, and failed-review variants; every variant invokes no external callable, leaves `tmp_path` empty, preserves fixture/input immutability, performs teardown, and creates no network/credential/Hermes/provider/persistence/downstream/trading behavior.

62z220. `docs/hermes_candidate_review_assisted_research_local_dry_run_harness_operator_note.md` - WP145 operator note defining the local skeleton posture, exact one-case procedure, 17-state controller, precomputed fake-response boundary, existing WP133 validation, exact positive outcome and derived-gate enforcement, explicit human review, sanitized evidence, teardown/failure behavior, pytest temp-only proof, forbidden interpretations, and separately gated WP146 closeout/readiness-decision boundary.

62z221. `docs/status_entries/WP145.md` - WP145 stable committed status fragment for the local/offline/test-oriented deterministic one-case harness skeleton, test-only precomputed fake response, and no-network dry-run package.

62z222. `docs/hermes_candidate_review_assisted_research_local_harness_closeout_and_controlled_remote_experiment_readiness_decision.md` - WP146 canonical docs-only closeout/readiness decision accepting the corrected merged WP145 one-case local harness as bounded test-only control evidence, closing the local harness phase, classifying a controlled remote experiment as `NOT_READY`, identifying missing current provider/model/privacy/retention/cost/endpoint evidence as the primary blocker, requiring current external research before remote implementation, denying activation and implementation authority, and separately gating WP147.

62z223. `tests/test_hermes_candidate_review_assisted_research_local_harness_closeout_and_controlled_remote_experiment_readiness_decision_docs.py` - WP146 focused Markdown-only regression for exact structure, locked closeout/readiness decisions, final WP145 evidence and follow-up reconciliation, local completeness and remote blocking matrices, external-research requirement, denied remote implementation, WP147 boundary, deferrals, forbidden interpretations, and no implementation/provider/credential/network/spend/storage/trading authority.

62z224. `docs/status_entries/WP146.md` - WP146 stable committed status fragment for the docs/status/tests-only local-harness closeout and controlled remote-experiment readiness decision package.

62z225. `docs/hermes_candidate_review_assisted_research_current_provider_model_privacy_retention_cost_endpoint_research_and_candidate_shortlist.md` - WP147 canonical current first-party research record for a bounded four-configuration preliminary pool, three deeply researched exact remote configurations, PR147-FU1 Tier 1 key-lifecycle reconciliation, separate application-state and abuse-monitoring deletion findings, zero eligible/zero shortlisted configurations with `EVIDENCE_INSUFFICIENT_NO_SHORTLIST`, canonical `ANT-SONNET-MESSAGES` and `GGL-FLASH-DEVELOPER` IDs, exact `expected_us_geo_cost: USD 0.0594` and `stress_us_geo_cost: USD 0.2970`, fail-closed evidence gaps, WP143-compatible cost calculations, hardware-evidence local-baseline deferral, persistent `NOT_READY`, and separately gated/unimplemented WP148 with no activation, implementation, credential, spend, storage, or trading authority.

62z226. `tests/test_hermes_candidate_review_assisted_research_current_provider_model_privacy_retention_cost_endpoint_research_and_candidate_shortlist_docs.py` - WP147 Markdown-only focused regression for exact structure/decisions, ISO research cutoff, complete official HTTPS registry metadata, deterministic matrix-citation-to-registry parsing, directly relevant Tier 1/DIRECT/current evidence for every mandatory PASS, Tier-2-only/inference-only/unresolved-source rejection, request-manifest versus provider-deletion separation, derived zero eligibility/shortlist counts, canonical ID/cost consistency, API-policy/privacy/retention/deletion/jurisdiction/subprocessor/security coverage, endpoint/Hermes/key feasibility, WP143 caps, hardware-evidence deferral, `NOT_READY`, WP148 gating, and no implementation/activation/spend/storage/trading authority.

62z227. `docs/status_entries/WP147.md` - WP147 stable committed status fragment for the public-research/documentation/status/tests-only current provider/model evidence and candidate-shortlist package.

62z228. `docs/hermes_candidate_review_assisted_research_mandatory_provider_evidence_resolution_and_research_refresh_decision.md` - WP148 canonical current public evidence-resolution record with `Refreshed source count: 11`, `Tier 1 source count: 10`, `Tier 2 source count: 1`, and `Tier 2 source IDs: ANT-R02`; OpenAI provider-side deletion and exact workload-identity token revocation remain insufficient; Anthropic deletion remains insufficient while its current public subprocessors and detailed security/incident evidence pass; Google remains preliminary and deletion-insufficient; eligibility recomputes to three deeply researched, zero eligible, zero shortlisted, no provider selection, `NOT_READY`, hardware-evidence local deferral, and a separately gated remote-provider-track deferral/revisit decision for WP149.

62z229. `tests/test_hermes_candidate_review_assisted_research_mandatory_provider_evidence_resolution_and_research_refresh_decision_docs.py` - WP148 Markdown-only focused regression for exact structure and decisions, complete unique current HTTPS source metadata, exact 11/10/1 Tier totals with ANT-R02 as the only Tier 2 source, Tier 2 supplemental-only semantics, mandatory Tier 1/DIRECT/current PASS evidence, all 16 resolution rows, fail-closed candidate derivation, and the required negative matrix covering `store=false`, automatic expiry, approval-dependent ZDR/MAM, mixed credential chains, login-only evidence, a missing mandatory row, hypothetical eligibility with zero shortlist, non-compensating cost/Hermes evidence, WP149 gating, cross-surface consistency, and no implementation authority.

62z230. `docs/status_entries/WP148.md` - WP148 stable committed status fragment for the current public-research/documentation/status/tests-only mandatory provider evidence-resolution and research-refresh decision package.

62z231. `docs/hermes_remote_provider_track_deferral_and_revisit_criteria_decision.md` - WP149 canonical governance decision setting the remote-provider track to `DEFERRED_PENDING_MATERIAL_NEW_EVIDENCE`, forbidding automatic/periodic/elapsed-time and unchanged-source research loops, defining public/operator/contractual/architecture trigger classes, objective freshness and mandatory-gate materiality, a sanitized bounded revisit packet, an event-driven-only cadence, exact fail-closed reopen states and forbidden activation transitions, persistent zero eligible/shortlisted and no-selection `NOT_READY` truth, and the separately gated provider-independent `LOCAL_RESEARCH_WORKFLOW_VALUE_VALIDATION_AND_PAPER_TRADING_READINESS_DECISION` next phase without provider, Hermes, scheduled-task, paper/live, execution, or trading authority.

62z232. `tests/test_hermes_remote_provider_track_deferral_and_revisit_criteria_decision_docs.py` - WP149 Markdown-only focused regression for exact title/headings and decision tokens; merged WP148 truth; allowed triggers and required non-triggers; objective freshness/materiality and complete sanitized packet fields/outcomes; elapsed-time/model/price/benchmark/Tier-2/login-only/unchanged-evidence negative cases; event-driven cadence; exact reopen states and forbidden direct transitions; provider-independent WP150 boundary; cross-surface consistency; stable status metadata; exact eight-file output inventory; and no provider research, candidate addition, activation, scheduling, source/tool/runtime/configuration/credential/paper/live/execution/trading authority.

62z233. `docs/status_entries/WP149.md` - WP149 stable committed status fragment for the documentation/status/Markdown-only tests remote-provider-track deferral, material-evidence revisit contract, anti-loop governance, event-driven cadence, fail-closed state transition, and provider-independent next-phase decision package.

62z234. `docs/local_research_workflow_value_validation_and_paper_trading_readiness_decision.md` - WP150 canonical provider-independent readiness decision inventorying 20 local deterministic research stages as 13 implemented/tested, four limited/manual, two contract/runbook-only, and one synthetic-only; grounding all 39 research-value metrics to current artifacts, exact fields or deterministic derivations, bounded current corpus/rubric coverage, and blockers; deriving zero measured, 22 measurable-but-not-yet-measured, and 17 not-currently-measurable metrics; recording `PARTIALLY_READY_BLOCKERS_IDENTIFIED` with seven research-value blockers; assessing market data as partial, strategy input as not ready, and replay/fill, order lifecycle, accounting, risk, observability, reconciliation, and operations as absent; preserving `NOT_READY_FOUNDATIONAL_GAPS`, zero paper/live authority, capital, orders, credentials, and model calls; and selecting the separately gated `LOCAL_RESEARCH_WORKFLOW_VALUE_MEASUREMENT_HARNESS_CONTRACT` next phase for missing field/schema, grounding, mapping, corpus, receipt, and deterministic-scoring contracts without implementing WP151.

62z235. `tests/test_local_research_workflow_value_validation_and_paper_trading_readiness_decision_docs.py` - WP150 Markdown-only focused regression for exact title/headings and decisions; merged WP149 remote deferral; complete 20-stage records and allowed capability states; all 39 metric-grounding rows; derived state totals; repository existence of every measurable artifact and corpus/rubric path; exact field/derivation and bounded coverage gates; future-field, runbook, free-form, WP142-scope, and proposed-WP151 negative cases; zero measured receipts; derived partial readiness; 17 complete blockers including seven research-value blockers; nine fail-closed paper domains; exact value-measurement WP151 boundary; six-file output inventory; cross-surface consistency; stable Model D status metadata; and no source/tool/fixture/workflow/dependency/configuration/runtime/provider/credential/paper/live/execution authority.

62z236. `docs/status_entries/WP150.md` - WP150 stable committed status fragment for the documentation/status/Markdown-only tests local research workflow value-measurement readiness and paper-trading foundational-gap decision package.

62z237. `docs/local_research_workflow_value_measurement_harness_contract.md` - WP151 canonical documentation-only contract preserving the exact WP150 39-metric registry and 22/17 Wave 1/Wave 2 split; mapping applicability across all 20 local workflow stages; defining a fixed 14-case/14-family synthetic sanitized offline corpus; fixing run, event, operator-action, receipt, scoring, three-repeat, temporary-output, human-review, safety, mutation, and seven-blocker contracts; deciding `COMPLETE_READY_FOR_BOUNDED_IMPLEMENTATION_WP`, `GROUNDED_22_METRICS_ONLY`, and `CONTRACT_DEFINED_IMPLEMENTATION_DEFERRED`; and separately gating Wave 1-only WP152 without implementing a fixture, harness, measurement, receipt, writer, schema change, runtime, provider/model/Hermes, paper/live, execution, or scheduler behavior.

62z238. `tests/test_local_research_workflow_value_measurement_harness_contract_docs.py` - WP151 Markdown-only focused regression proving exact title/headings and decisions; identity/state equality with all 39 WP150 metrics; exact 22 concrete Wave 1 and 17 blocked Wave 2 rows; complete 20-stage applicability and 14-case corpus coverage; complete run/event/action/receipt schemas, formulas, statuses, repeats, output modes, human review, 12 safety gates, and 21 mutations; all seven blocker targets; Wave 1-only WP152 boundary; six-file scope; stable Model D status; and no implementation or deferred-log change.

62z239. `docs/status_entries/WP151.md` - WP151 stable committed status fragment for the documentation/status/Markdown-only tests local research workflow value measurement harness contract and separately gated Wave 1-only implementation decision.

62z240. `src/data_layer/local_research_value_measurement/` - WP152 local/offline/import-side-effect-free stdlib-only deterministic Wave 1 value-measurement package preserving the exact 39-record registry, implementing only the 22 Wave 1 count/rate/boolean/set/repeatability derivations, keeping all 17 Wave 2 records blocked and value-empty, and enforcing exact run/event/operator-action/metric-result/receipt contracts, three repeats, 20 stages, 12 safety gates, no-echo failures, input immutability, and in-memory or pytest-temporary-only output. The WP152 F/G review correction uses only the six exact WP151 human-review outcomes, requires one mutually exclusive final review disposition per selected case, gives abort global precedence, makes defer/correction/retry prevent completion, reconciles actions with events and receipts, and applies exact structural vocabularies plus contextual recursive safety validation to event and receipt output surfaces. It executes exactly three complete actual-metric measurement passes; compares normalized outputs, metric applicability/results, safety flags, and run status; derives RV-REP-06 without circularity; builds and semantically validates a receipt against one canonical equality-proven pass; and enforces exact selected-case, repeat, stage-pair, validation, review, disposition, and terminal event order. It adds no writer, CLI, scheduler, provider/model/Hermes, credential, strategy, paper/live, order, execution/risk, database, telemetry, or runtime integration.

62z241. `tests/fixtures/local_research_workflow_value_measurement_v1.json` - WP152 fixed ordered 14-case/14-family `SYNTHETIC_SANITIZED_OFFLINE_FIXED` corpus using only invented safe logical identifiers and structured deterministic observations, with no URL fetch, real person, wallet, account, order, credential, current timestamp, random identifier, absolute path, provider/model response, or recommendation content.

62z242. `tests/test_local_research_workflow_value_measurement_harness.py` - WP152 focused regression proving exact WP151 registry, stage map, six human-review outcomes, and event state/error-code vocabularies; exact 39/22/17, 20-stage, 14-case, 13-event, nine-status, 12-gate, and three-repeat identities; all five Wave 1 formulas; Wave 2 blocking; exact run/event/action/result/receipt shapes; mutually exclusive final dispositions; duplicate/conflict rejection; abort and defer/correction/retry precedence; action/event/receipt reconciliation; broad contextual forbidden variants across corpus, event, and receipt surfaces; safe structural/non-authority positives; exactly three full-pass executions; actual count/rate/boolean/set/applicability/failure-code/safety/output/status drift rejection; canonical receipt count/rate/boolean/set/applicability/failure/repeatability mutation rejection; boolean-count and non-canonical set-coverage rejection; selected-case identity/order reconciliation; complete-but-reordered stage/case/repeat/review event rejection; safety precedence; no-echo; caller and fixture immutability; empty pytest-temporary output; import-side-effect freedom; and the complete missing/unknown/duplicate/version/event/duration/denominator/action/retry/network/credential/provider/Hermes/authority/persistence/repeatability/review/receipt/mutation negative matrix.

62z243. `docs/status_entries/WP152.md` - WP152 stable committed status fragment for the bounded local deterministic Wave 1 value-measurement harness implementation, fixed synthetic corpus, focused mutation tests, zero accepted project measurement run or receipt, unchanged paper/live prohibition, and separately gated WP153 dry-run/receipt-review phase.

62z244. `docs/local_research_workflow_value_measurement_dry_run_and_receipt_review.md` - WP153 canonical record of exactly one project-authorized synthetic in-memory dry run of the merged WP152 harness over the fixed 14-case corpus (run_id `WP153-DRY-RUN-001`, label `WP152_SYNTHETIC_VALIDATION`, 3 repeats, 392 events, 39 metric results, 22 Wave 1 `MEASURED_VALID`, 17 Wave 2 `BLOCKED_WAVE_2` with zero populated value fields, 14 `PASS` repeatability, all 12 safety gates true, 14 `ACKNOWLEDGE` and zero other operator actions), its independent event/receipt validation, its `ACCEPT_MEASUREMENT_RECEIPT_FOR_RESEARCH_MEMORY_ONLY` human-review outcome, deterministic canonical SHA-256 evidence for the event stream, receipt, and public result, no-persistence proof (`IN_MEMORY_ONLY`, zero run-created files, no committed raw artifact), and the explicit synthetic-versus-real distinction that real workflow measurement runs and real research-value metrics measured remain zero and paper/live readiness is unchanged.

62z245. `docs/status_entries/WP153.md` - WP153 stable committed status fragment recording one accepted synthetic project dry run and research-memory receipt, the 14/3/39 and 22/17/0 split, all 12 safety gates, zero raw persistent output, zero real workflow measurement runs, zero real research-value metrics measured, unchanged paper/live authority, and the separately gated WP154 adoption-architecture/dependency-registry/alpha-factory roadmap lock-in next phase.

62z246. `tests/test_local_research_workflow_value_measurement_dry_run_and_receipt_review.py` - WP153 focused replay regression reproducing the exact synthetic dry run through the public WP152 package surface only, asserting exact public result fields, independent event and receipt validation, unchanged inputs, the exact 39/22/17 split with empty Wave 2 values, 14 `PASS` repeatability, 12 true safety flags, 14 acknowledgement and zero other action counts, canonical SHA-256 equality with the committed WP153 document and status fragment, byte-equal second in-memory replay as regression evidence only, absence of any time/random/environment/path value, absence of forbidden positive-capability text, and zero run-created files.

62z247. `docs/adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in.md` - WP154 canonical docs-only architecture decision locking `MEASURABLE_ALPHA_FACTORY_PLUS_DETERMINISTIC_TRADING_KERNEL`; the exact nine-stage non-skippable alpha lineage; the deterministic-versus-AI/Hermes authority split; ordered adoption Phases A–J; ordered alpha priorities 1–5; a 15-candidate primary-source-observed adoption registry with license, security, benchmark, rejection, and separate-WP gates; a 15-question adoption test; planning-only roadmap estimates; 15 explicit deferrals; and the separately gated/unimplemented WP155 point-in-time data-foundation contract, with no dependency installation, source/runtime/product-network/credential/paper/live/scheduler/execution authority, or external source-code copy.

62z248. `docs/status_entries/WP154.md` - WP154 stable committed status fragment recording exact PR153 lineage, the post-WP153 capability inventory, architecture/lineage/adoption/priority/registry locks, primary-source caveats, eight-file docs/status/tests scope, planning estimates, explicit deferrals, unchanged protected boundaries, and separately gated WP155.

62z249. `tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py` - WP154 focused deterministic documentation regression proving canonical/status/index/deferred surfaces; exact finished-system label; unique ordered nine-stage lineage, ten adoption phases, five priorities, and 15 registry candidates; explicit AI/Hermes prohibition and deterministic-kernel authority; current official-client archive/beta-status tension; separately gated NautilusTrader/Prefect/MLflow; primary URLs and observation dates; planning-only estimates; negative semantic wording matrix; stale-review-target rejection; exact eight-file compatibility scope; and absence of source/dependency/lock/workflow/WP155 implementation.

62z250. `docs/point_in_time_market_research_data_foundation_contract.md` - WP155 canonical contract locking `POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT` and `CONTRACT_ONLY_NO_WRITER_NO_DEPENDENCY_NO_COLLECTION`; canonical platform/event/market/token/source/resolution-source and observation/snapshot/schema/record-version identities; exact event/observed/ingestion time; ingestion-time as-of visibility; append-only lifecycle; raw/normalized/quarantine boundaries; duplicate/revision/correction/retraction/conflict semantics; source and resolution-rule snapshots; SHA-256 serialization and lineage; fail-closed schema evolution; `PARQUET_ARROW_PREFERRED_BUT_NOT_INSTALLED`; `record_family / schema_major / ingestion_date_utc`; `BENCHMARK_REQUIRED_NO_ADOPTION_DECISION`; no-look-ahead matrix; current official-source register; deterministic data authority; and separately gated WP156.

62z251. `docs/status_entries/WP155.md` - WP155 stable committed status fragment recording exact PR154 lineage, merged-state data identity/time/storage inventory, contract decisions, nine-file docs/status/tests compatibility scope, WP154-D002 contract-only reconciliation, WP154-D003 open benchmark status, WP155-D001 through WP155-D010 deferrals, pre-existing clean-main branch-scope test failures and repair classification, unchanged protected boundaries, and separately gated WP156.

62z252. `tests/test_point_in_time_market_research_data_foundation_contract_docs.py` - WP155 focused deterministic documentation regression proving canonical/status/index/deferred surfaces; exact identity and three-time models; ingestion-time as-of ordering; append-only lifecycle; raw/normalized/quarantine boundaries; duplicate/revision/correction/retraction/conflict distinctions; source/rule snapshots; SHA-256 hash preimages and lineage; schema evolution; Arrow/Parquet and partition decisions; DuckDB/Polars correctness-first benchmark; no-look-ahead negative matrix; deterministic data authority; official URLs and observation date; exact nine-file scope; negative false-capability wording; and absence of source/dependency/lock/workflow/config/tool/fixture/WP156 implementation.

62z253. `docs/point_in_time_observation_schema_validator_and_synthetic_fixture_implementation.md` - WP156 canonical implementation record for `LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION`; records exact PR155 lineage, the isolated three-family/three-kind public API, eight frozen dataclasses, bounded canonical JSON and SHA-256 preimages, derived IDs, strict UTC three-time validation, market/source/rule builders, safe no-echo quarantine, finite 256-record lineage/supersession validation, exact sanitized 20-case in-memory corpus, one clean-main-proven WP155 branch-scope compatibility repair, unchanged legacy Polymarket snapshot behavior, zero dependency/persistence/query/collector/network/credential/scheduler/strategy/paper/live/execution authority, deferred reconciliation, validation matrix, and separately gated/unimplemented WP157.

62z254. `docs/status_entries/WP156.md` - WP156 stable non-self-referential committed status fragment recording PR155 merge lineage, exact 11-file scope, authority/non-authority posture, clean-main compatibility probe, public implementation surface, deferred items, validation/field-coverage/negative-matrix gates, Model D evidence, one-shot readiness gate, and the separately gated WP157 pointer.

62z255. `src/data_layer/point_in_time_market_research/` - WP156 isolated stdlib-only, local/offline, in-memory point-in-time validation package. The public surface exposes exact locked constants, frozen envelopes/records/results/cases, bounded canonical JSON and SHA-256, builders for market observations, source snapshots, and resolution-rule snapshots, a finite lineage/supersession batch validator, and an exact deterministic sanitized 20-case corpus. It performs no file I/O, network, credential access, environment/clock/random lookup, scheduling, persistence, query/as-of reconstruction, migration, collection, strategy, paper/live, order, risk, accounting, reconciliation, or execution behavior and does not modify legacy `src/data_layer/polymarket/` behavior.

62z256. `tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py` - WP156 focused positive, negative, mutation, fixed-hash, lineage, no-echo, field-coverage, no-side-effect, import-boundary, exact-corpus, and legacy-compatibility regression, maintained by WP157 only for the additive review-only conflict handoff surface and the successor exact-scope guard. It covers exact public exports/vocabularies; frozen objects; caller-reference isolation; canonical bytes and every bound; floats/NaN/Infinity and unsupported types; fixed SHA-256; exact IDs; strict UTC times; three builders; recursive secret/authority rejection; decimal strings; source/rule allowlists; safe quarantine; revisions/corrections/retractions/duplicates/conflicts; cycle/unknown-parent/backdate/hash/batch-bound failures; exact 20-case order; fresh case loads; no file creation; forbidden imports/calls; and the authorized-only WP157 as-of query surface.

62z257. `docs/bounded_in_memory_point_in_time_record_set_reconstruction_and_as_of_query_implementation.md` - WP157 canonical implementation record for `BOUNDED_IN_MEMORY_AS_OF_INGESTION_TIME_RECONSTRUCTION`; records exact PR156 merge lineage, the exact public query surface and locked vocabularies, the immutable query spec/receipt/result dataclasses, the query-spec canonical hash, the WP156 batch and review-only conflict handoff, the exact visibility order of operations, filter and event-window semantics, entity keys and lineage state-chain semantics, current/history/timeline views, deterministic ordering, exclusion accounting and reconciliation, the result receipt/hash preimage, the exact 24-case synthetic corpus, the no-look-ahead negative matrix, no-side-effect evidence, WP155/WP156 and legacy-snapshot compatibility, explicit non-authority, the exact changed-file scope, and separately gated/unimplemented WP158.

62z258. `docs/status_entries/WP157.md` - WP157 stable non-self-referential committed status fragment recording PR156 merge lineage, exact 12-file scope, authority/non-authority posture, the batch/conflict-review handoff, deferred reconciliation, requirement-to-evidence traceability, Model D evidence, one-shot readiness gate, and the separately gated WP158 pointer.

62z259. `src/data_layer/point_in_time_market_research/as_of_query.py` - WP157 isolated stdlib-only, local/offline, in-memory point-in-time reconstruction and as-of query engine. It exposes exact locked constants, frozen `EventTimeWindow`/`PointInTimeQuerySpec`/`PointInTimeQueryReceipt`/`PointInTimeRecordSetResult`/`SyntheticAsOfQueryCase`, query-spec canonicalization and SHA-256, default ingestion-time visibility with an ingestion-bounded diagnostic observed-time cutoff, post-visibility entity/family/kind filters and event-time windows, explicit-lineage supersession/correction/revision/retraction state, deterministic conflict exclusion and optional review-only conflict output, deterministic ordering, exclusion accounting, and an exact result receipt/hash. It performs no file I/O, network, credential access, environment/clock/random lookup, scheduling, persistence, migration, collection, strategy, paper/live, order, risk, accounting, reconciliation, or execution behavior and does not modify legacy `src/data_layer/polymarket/` behavior.

62z260. `src/data_layer/point_in_time_market_research/as_of_synthetic_cases.py` - WP157 sanitized deterministic in-memory synthetic as-of query corpus built only from valid WP156 records with fixed timestamps; exposes the exact ordered 24-case `SyntheticAsOfQueryCase` set with committed constant result hashes that are never generated from the result under test, plus fresh record reconstruction per case. No wall clock, random IDs, real market/account/wallet data, file paths, or execution authority.

62z261. `tests/data_layer/point_in_time_market_research/test_as_of_query.py` - WP157 focused positive, negative, adversarial, fixed-hash, permutation-invariance, reconciliation, no-side-effect, and import-boundary regression. It covers exact exports/vocabularies; frozen spec/receipt/result; query-spec canonical hash; UTC cutoff validation; ingestion visibility and ingestion-bounded diagnostic; event-window-after-visibility and missing-event include/exclude; correction/revision/retraction/late-arrival/duplicate/conflict state; current/history/timeline views; every filter family and precedence; deterministic ordering and permutation invariance; empty valid receipt; exact exclusion counts and reconciliation; exact result hashes; spec/batch rejection matrix; conflict-review handoff; no raw echo; batch/result bounds; forbidden imports/tokens; and unimplemented WP158.

62z262. `docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md` - WP158 canonical contract-only document locking `APPEND_ONLY_LOCAL_MANIFEST_AND_DETERMINISTIC_DATASET_SNAPSHOT_REFERENCE_CONTRACT` and `CONTRACT_ONLY_NO_WRITER_NO_READER_NO_PERSISTENCE`; records exact PR157 merge lineage; the closed canonically ordered schema-id/version, derivation-mode, entry-kind, reference-state, and reason-code vocabularies; the immutable dataset snapshot reference field set, forbidden-field list, query-mode rules, and `datasetref:sha256:` identity preimage with self-ID and `created_from_manifest_entry_id` exclusions; the append-only manifest entry field set and `manifestentry:sha256:` identity preimage with self-ID/storage/runtime exclusions; the schema `1.0.0` reserved-null `created_from_manifest_entry_id` rule with the reference immutability invariant; the explicit REGISTER/SUPERSEDE/INVALIDATE subject-and-target semantics (transition entries carry the target's dataset-reference ID; replacements register separately) with state-transition integrity; the append-chain truth table rejecting branching, gaps, cycles, backward mutation, latest-by-time resolution, and repeated/mismatched/cross-manifest transitions; the public-API-unchanged matrix; the semantic commitment matrix over every reference and manifest field; the failure/no-echo matrix; twelve concrete machine-readable JSON examples (nine valid, three invalid) with fixed synthetic IDs, 64-hex hashes, explicit nulls, and fixed-null v1.0.0 backlinks; the exact reference and manifest identity-preimage mappings and canonical JSON rules under which every example self ID and the examples 6–11 chain links are true recomputable `sha256` digests; the locked cross-tuple-overlap failure precedence (`REVIEW_CONFLICT_AUTHORITY_FORBIDDEN` over within-tuple `FIELD_VALUE_INVALID`); explicit non-authority, storage boundary, and next-gate statements; and separately gated/unimplemented WP159. It defines no writer, reader, persistence, dependency, workflow, or execution authority and adds no `src` file or package export.

62z263. `docs/status_entries/WP158.md` - WP158 stable non-self-referential committed status fragment recording PR157 merge lineage, contract-only authority/non-authority posture, the locked contract surface and identity prefixes, the exact 11-file docs/status/tests scope, WP157-D001 through WP157-D010 open reconciliation, WP158-D001 through WP158-D010 deferrals, requirement-to-evidence traceability, Model D evidence, self-diagnosis, one-shot readiness gate, unchanged WP157 public surface, and the separately gated WP159 pointer.

62z264. `tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py` - WP158 focused deterministic documentation regression proving canonical/status/index/deferred surfaces; exact label/posture and PR157 merge lineage; schema ids/versions; closed canonically ordered vocabularies; complete dataset reference and manifest entry field sets, forbidden fields, and identity prefixes/preimages/exclusions; the append-chain truth table; the public-API-unchanged matrix and unchanged WP157 `__init__` surface; the semantic commitment matrix; the failure/no-echo matrix; the reserved-null v1.0.0 backlink and immutability invariant; the SUPERSEDE/INVALIDATE subject-target semantics; the exact identity-preimage mappings with a stdlib-only recomputation oracle proving every example self ID and the examples 6–11 chain links are true `sha256` digests, one-field identity sensitivity, and the locked Example-12 cross-tuple-overlap precedence; twelve `json.loads`-parsed examples verified for required fields, hash/ID shapes, mode-conditional nulls, non-overlapping tuples, conflict-derived review flag, exact transition target semantics, safety-true flags, single-fault invalids, and valid/invalid error-code discipline; non-authority/storage/next-gate; absence of any new manifest/reference `src` module; ten open WP158 deferred items; stable Model D status wording; no dependency/workflow/generated-artifact/local-data change; and the exact contract-only 11-file scope.

62z265. `docs/ai/codex/WP_SPEC_STANDARD.md` - WP159 canonical machine-readable work-package specification standard; authoritative for the V3 three-artifact topology, strict JSON and bounds, exact schema keys and nested types, reserved cross-WP artifact paths, diff-helper classifier parity, closed identity derivations and canonical-example coverage, deterministic failure/serialization rules, generic normal independent certificate contract, the exact byte-bound one-time WP159 bootstrap waiver, and the separately gated WP160/WP161 boundary.

62z266. `tools/wp/wp_spec_guard.py` - WP159 local/offline/read-only stdlib guard for `polymarket-work-package-spec@1.0.0`; exposes the locked import APIs, validates generic normal certificates, reserves cross-WP package artifacts, matches exact-scope protected/generated/dependency classifiers, closes derivation/example references, and accepts the waiver only for the code-bound final WP159 prompt/spec bytes and locked identity; produces sanitized deterministic `polymarket-wp-spec-guard-result@1.0.0` and has no subprocess, network, environment, write, product, or execution authority.

62z267. `tests/tools/wp/test_wp_spec_guard.py` - WP159 focused adversarial guard regression covering exact APIs, schema, type/bounds, strict JSON, cycle/depth/non-finite handling, reserved artifact and path/set/authority semantics, fixed error precedence, no-echo behavior, closed generic canonical derivation truth, exact WP159-only immutable waiver negatives, generic normal-certificate positives and negatives, phase gates, hashes, and deterministic serialization.

62z268. `tools/git/diff_scope_summary.py` - existing local diff-scope helper extended by WP159 with schema-2 WP-spec exact mode while preserving schema-1 legacy behavior; exact mode includes tracked/untracked paths, rename/copy source and destination policy, deletions, required presence, maximum count, authority, protected/generated/dependency checks, whitespace checks, and fail-closed git operation handling.

62z269. `docs/wp_specs/WP159/wp_prompt.txt` and `docs/wp_specs/WP159/wp_spec.json` - exact immutable explicitly authorized V6 / XL23 WP159 prompt/specification bytes identified by SHA-256 `7dfd1e826b688873c3303dcf89d13522d82620840b17f1a40812c3ceb2c74911` and `2300bd295bdd0f679857d2aec0d007d296ef05421095e77e69937b457ad094b3`, which are also locked in the one-time guard constants and waiver record.

62z270. `docs/wp_specs/WP159/draftability_certificate.json` - explicit-user-authorization low-risk draft-PR implementation waiver; not a PASS certificate, not review-readiness authority, not merge authority, and requires independent live-PR review.

62z271. `docs/status_entries/WP159.md` - stable Model D WP159 V6 / XL23 status fragment recording WP158 lineage, distinct primary and repository validation classes, exact 23-file scope, immutable package hashes, exact one-time waiver posture, implementation surface, unchanged protected boundaries, `BLOCKED_NOT_READY` evidence posture, and separately gated WP160/WP161 successors.

62z272. `tests/tools/git/test_diff_scope_summary.py` - existing helper regression extended by WP159 with legacy compatibility plus exact command arrays, NUL parsing, tracked/untracked set semantics, rename/copy sources, deletion presence, count, authority, ambiguous CLI rejection, git-failure exit 2, and exact-failure exit 1.

62z273. `src/data_layer/point_in_time_market_research/manifest_reference.py` - WP160 bounded, local, offline, stdlib-only, in-memory validator realizing the merged WP158 append-only local manifest and deterministic dataset snapshot reference contract; implements the frozen `DatasetSnapshotReference`, `ManifestEntry`, and three result dataclasses; `build_dataset_snapshot_reference`, `build_manifest_entry`, and `validate_manifest_chain`; the locked labels, schema id/version pairs, closed vocabularies, validation statuses, and fifteen ordered error codes with an always-empty warning tuple; deterministic `datasetref:sha256:` and `manifestentry:sha256:` identity derivation matching the contract preimages; recompute-and-compare integrity; mode-conditional query rules; cross-authority-overlap precedence; the single-manifest hash-linked append chain, reference registry, register/supersede/invalidate state machine, and human-review binding; bounded fail-closed no-echo results; and no writer, reader, persistence, network, credential, scheduler, strategy, paper, or execution authority.
62z274. `docs/status_entries/WP160.md` - WP160 stable non-self-referential committed status fragment recording PR159 merge lineage, the functional `DATA_LAYER_VALIDATOR` posture, the abandoned governance-oriented WP160 draft as never implemented, the exact 17-file scope (fifteen functional plus two explicitly user-authorized package-export compatibility regressions), the implemented public surface, unchanged WP156/WP157 surface, Model D evidence, and the separately gated WP161 successor.
62z275. `tests/data_layer/point_in_time_market_research/test_manifest_reference.py` - WP160 focused deterministic regression covering exact labels/posture/vocabularies/error codes and package exports; valid and fail-closed reference, entry, and chain results; independent identity recomputation and the twelve contract-example canonicalization cross-check; mode/overlap/backlink/human-review/safety rules; sequence, link, cycle, registry, transition, duplicate-registration, terminal, and review-binding chain rules; recursive no-echo; caller-input immutability; frozen dataclasses; and complete dataclass field coverage.
62z276. WP160 addendum (Section 19) in `docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md` - records the functional WP160 implementation label/posture, exact source module and public API, bounds, builder-versus-chain responsibility, reference-registry requirement, input-order rule, duplicate-registration rejection, human-review binding, fail-closed error-code precedence, no writer/reader/persistence authority, and the WP161 successor boundary, without disturbing the historical WP158 contract or its twelve examples.
62z277. `src/data_layer/point_in_time_market_research/manifest_store.py` - WP161 bounded local SQLite manifest store; standard-library `sqlite3` only; explicit caller-selected regular non-symlink path; exact three-table schema and `user_version=1`; DELETE journal, FULL synchronous writes, enabled foreign keys, `timeout=0.0`, and explicit `BEGIN IMMEDIATE`; canonical complete-dataclass JSON plus SHA-256; transactional append and deterministic idempotent retry; read-only reopen, exact-schema/integrity/foreign-key verification, WP160 builder reconstruction, identity comparison, redundant-column comparison, and complete-chain revalidation; 256-row and 65,536-byte bounds; closed no-echo errors; and no migration, WAL, analytics, network, credential, strategy, paper, execution, or live authority.
62z278. WP161 addendum (Section 20) in `docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md` - canonical persistence record for the WP161 label/posture, exact public API and SQL schema, SQLite configuration and URI modes, explicit-path contract, canonical payload rules, atomic transaction and fail-fast locking, idempotency, verified read, append-only guarantee, bounds, corruption/no-echo posture, and separately gated successor boundary.
62z279. `docs/status_entries/WP161.md` - stable Model D WP161 status fragment recording merged WP160 lineage, `DATA_LAYER_PERSISTENCE` authority/non-authority posture, centralized protected-boundary references, exact 18-file scope, SQLite schema/configuration/transaction semantics, R001-R032 traceability, negative-test matrix, draft-only review posture, and the prohibition on merge without independent review and explicit user authorization.
62z280. `tests/data_layer/point_in_time_market_research/test_manifest_store.py` - WP161 focused deterministic temp-only regression covering public constants/dataclasses/exports, explicit path and batch boundaries, exact schema/configuration, initialize/reopen/idempotency, transactional append and complete-chain validation, rollback injection, writer contention, corruption/tamper matrices, row bounds, read-only byte stability, recursive no-echo/field coverage, and source/SQL safety.
62z281. WP161 merged: PR #161; WP161 final implementation head `e1c2fb64a1231e6040a8830bcd533fd414675dbf`; WP161 merge commit `2ac6975d0710bbdfd73e940bb6f1ef47bdc51d65`. WP162 registered as the current review target: bounded deterministic adapters bridge a WP156 validated record batch and a WP157 as-of query result into a WP160 `DatasetSnapshotReference` plus a WP160 REGISTER `ManifestEntry`, persisted through the WP161 SQLite manifest store. Raw/real point-in-time records are still not durably persisted by this adapter.
62z282. `src/data_layer/point_in_time_market_research/dataset_persistence_adapter.py` - WP162 bounded, local, offline, stdlib-only, deterministic adapter module; re-runs the authoritative upstream WP156/WP157 computation from caller records/spec; builds the WP160 reference/entry identities from the exact WP158/WP160 preimages and rebuilds them through the public WP160 builders; loads and verifies the WP161 store, derives sequence/previous-head from the verified snapshot, and appends through the WP161 public `append_manifest_store_batch`; idempotent detection of an already-registered identical snapshot; and no SQLite import, direct SQL, filesystem/env/clock access, store initialization/migration, raw record persistence, external known-parent context, auto supersede/invalidate, network, credential, strategy, paper, or execution authority.
62z283. `docs/status_entries/WP162.md` - stable Model D WP162 status fragment recording merged WP161 lineage, the `DATA_LAYER_ADAPTER` authority/non-authority posture, the exact 19-file scope, the implemented adapter public surface, the locked batch/as-of mapping and provenance rules, verified-store precondition, idempotency/registration-conflict semantics, R001-R036 traceability, the negative-test matrix, the NON-DRAFT ready-for-review posture, and the prohibition on merge without independent review and explicit user authorization.
62z284. `tests/data_layer/point_in_time_market_research/test_dataset_persistence_adapter.py` - WP162 focused deterministic temp-only regression covering exact constants/statuses/error-codes/exports, both adapters' success and rejection matrices, hostile-container/subclass/generator boundaries, provenance mismatch, the three as-of result-view mappings, empty and review-conflict results, independent reference/entry identity recomputation and one-field sensitivity, verified-store precondition and missing/corrupt store, manifest-id/idempotency/registration-conflict/unregistered-then-register rules, monkeypatched upstream/builder/store fail-closed no-echo, no-mutation invariance, and the no-SQL/no-filesystem/no-clock authority source scan.
62z285. WP162 addendum (Section 21) in `docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md` - canonical adapter record for the WP162 label/posture, exact public API, batch derivation, as-of result-view mapping, explicit parameter-set/validator-version consistency rule, reference/entry identity derivation then WP160 rebuild, verified-store-must-already-exist precondition, manifest-id handling, sequence/previous-head derivation, exact REGISTER entry construction, already-persisted idempotency and effective-time registration conflict, WP161-only append, and the no-raw-persistence/no-external-parent/no-auto-transition/no-wall-clock/no-new-SQL/network/trading boundary.
62z286. WP162 merged: PR #162; WP162 final implementation head `b101f5c81be447404750c178dc2ed9edfc7fa764`; WP162 merge commit `5e914b92a6a957dcd982702f3d47de6b64f5a691`. WP163 registered as the current review target: a bounded durable local SQLite record store (`src/data_layer/point_in_time_market_research/record_store.py`) that persists the actual immutable WP156/WP157 point-in-time record objects and their canonical full-record payloads, revalidates every reconstructed record and its complete cross-record lineage, and materializes a WP160 `DatasetSnapshotReference` into the exact durable record objects it names. WP161 remains the manifest/reference store; WP163 is the distinct actual-record store. No Parquet/DuckDB is adopted and no real/public network collection has occurred.
62z287. `src/data_layer/point_in_time_market_research/record_store.py` - WP163 bounded local SQLite point-in-time record store; standard-library `sqlite3` only; explicit caller-selected regular non-symlink path; exact two-table (`record_store_meta`, `records`) schema with five explicit indexes and `user_version=1`; DELETE journal, FULL synchronous writes, enabled foreign keys, `timeout=0.0`, and explicit `BEGIN IMMEDIATE`; canonical complete-record JSON payload plus SHA-256; append-only transactional insert with deterministic idempotent retry and same-ID conflict rejection; read-only reopen with exact schema/integrity verification, strict payload decode/reconstruct, indexed-column comparison, WP156 ordinary self-validation and review-only conflict self-validation, and complete cross-record lineage validation; deterministic `DatasetSnapshotReference` materialization (VALIDATED_RECORD_BATCH recomputes the WP156 batch identity; AS_OF_QUERY_RESULT resolves reference IDs only); 256/4096-record and 131072/128 MiB byte bounds; closed no-echo errors; and no migration, WAL, analytics, Parquet/Arrow/DuckDB/Polars, network, credential, strategy, paper, execution, or live authority.
62z288. `docs/point_in_time_record_store_contract.md` - WP163 canonical contract for the durable point-in-time record store: label/posture, SQLite durability rationale, exact public API, schema/indexes, bounds, canonical full-record payload, ordinary vs review-conflict integrity, complete lineage, append-only/idempotency, transaction/lock posture, corruption/no-echo, `DatasetSnapshotReference` materialization with batch-mode full recomputation and the honest as-of ID-resolution-only limitation, and the no-network/no-manifest-schema-change/no-Parquet/no-DuckDB successor boundary.
62z289. `docs/status_entries/WP163.md` - stable Model D WP163 status fragment recording merged WP162 lineage, the `DATA_LAYER_PERSISTENCE` authority/non-authority posture, the exact 20-file scope (nineteen record-store package files plus the append-only contract-docs changed-file scope guard kept future-safe), the implemented record-store public surface, schema/bounds, ordinary/conflict integrity rules, both materialization modes, R001-R040 traceability, the NON-DRAFT ready-for-review posture, and the prohibition on merge without independent review and explicit user authorization.
62z290. `tests/data_layer/point_in_time_market_research/test_record_store.py` - WP163 focused deterministic temp-only regression covering public constants/dataclasses/exports, hostile path and container boundaries, exact schema/configuration/index verification, initialize/reopen/idempotency, ordinary and review-conflict self-validation, the complete lineage matrix, transactional rollback/lock contention, the corruption/tamper matrix, read-only byte stability, both materialization modes, missing/authority-mismatch materialization, recursive no-echo, and the production SQL source safety scan.

62z291. WP163 merged: PR #163; WP163 final implementation head `98d8e5813efddddca87608c6965bbbb5346cb371`; WP163 merge commit `889a249c54aac589d952827425eadfc0aae1606a`. WP164 registered as the current review target: the first bounded real/public Polymarket population path (`src/data_layer/point_in_time_market_research/polymarket_public_population.py`) that, only when `allow_network=True`, performs existing GET-only Gamma `GET /markets` and optional CLOB `GET /book` reads under the existing conservative local guard, normalizes public responses into immutable WP156 records, validates the batch, appends it into an empty WP163 store, and registers the exact validated batch through WP162 into WP161. The old WP10 JSONL capture remains historical and is not the WP164 write authority; WP163 remains the durable record store and WP161 the manifest store.

62z292. `src/data_layer/point_in_time_market_research/polymarket_public_population.py` - WP164 bounded real/public initial Polymarket point-in-time population coordinator and offline registration recovery; label `POLYMARKET_REAL_PUBLIC_INITIAL_POINT_IN_TIME_POPULATION`; posture `EXPLICIT_NETWORK_GET_ONLY_BOUNDED_INITIAL_SEED_NO_TRADING_AUTHORITY`; default network posture OFF with a valid dry-run result; empty-record-store initial-seed only; existing `default_polling_policy`/`RateLimitGuard` remain the runtime request authority consulted before every GET; only the existing GET-only public client `get_markets`/`get_order_book_snapshot` methods used; deterministic content-addressed `snapshot`/`ingest` run identities independent of response order; records-first then WP162 reference-second ordering; offline recovery after a committed append; no direct network library, credential, authenticated endpoint, `POST /books`, order/trading method, WP10 JSONL writer, `local_data/` path, scheduler, retry, or sleep; closed no-echo results with `advisory_only=True` and `no_execution_authority=True`.

62z293. `docs/polymarket_point_in_time_public_population_contract.md` - WP164 canonical contract for the bounded real/public initial population: label/posture, official public endpoint basis and GET-only/no-authentication boundary, local-guard runtime authority, initial-seed-only design and empty-store requirement, exact public API, Gamma and optional CLOB normalization, deterministic run identities/order, WP156 batch validation, records-first then registration ordering, offline registration recovery, no cross-file atomicity claim, no old JSONL write, no raw-response persistence, no scheduler/retry, no incremental lineage, no credentials/trading, and the WP164-D001..D007 successor boundary.

62z294. `docs/status_entries/WP164.md` - stable Model D WP164 status fragment recording merged WP163 lineage, the `DATA_LAYER_PUBLIC_POPULATION` authority/non-authority posture, the exact 20-file scope, the public API and endpoint/GET-only boundary, the empty-store initial seed, the offline recovery behavior, the NON-DRAFT ready-for-review posture, and the prohibition on merge without independent review and explicit user authorization.

62z295. `tests/data_layer/point_in_time_market_research/test_polymarket_public_population.py` - WP164 focused deterministic no-network regression covering the exact public surface and eight-symbol export tail, the zero-network dry run, store preconditions before network, fake-client Gamma and optional CLOB population, guard denial before Gamma and before books, malformed/duplicate/ambiguous response rejection, deterministic response-order-independent identities, WP156 batch validation, WP163 append, WP162 registration, records-first ordering, partial-registration offline recovery, no-echo, and the AST/token-aware no-network/no-auth/no-order/no-scheduler source scan.

62z296. WP164 merged: PR #164; WP164 final implementation head `0f3f29e32f7bb404f1156afba83ea33c3ee5cb1b`; WP164 merge commit `652ac21547db42512e7f9360986e1616c6622384`. WP165 registered as the current review target: the first bounded safe REPEATED real/public Polymarket capture after the WP164 initial seed (`src/data_layer/point_in_time_market_research/polymarket_incremental_population.py`) that captures into an already-populated and already-registered WP163 store, proves the latest registered VALIDATED_RECORD_BATCH reference converges exactly with the registered store portion before any network, reuses the WP164 GET-only Gamma/CLOB capture boundary under the unchanged guard, classifies each new capture into PRIMARY_ASSERTION/EXACT_DUPLICATE/SOURCE_REVISION against the latest prior for the same WP156 entity, validates the complete prior-plus-new cumulative batch, appends only the new records through WP163, and registers the complete cumulative dataset as one WP160 reference through WP162. Every cross-run parent stays committed inside the same cumulative snapshot (<=256 records); no external known-parent schema, keyset/pagination, scheduler, credential, or trading authority is introduced. The scalable external-parent/reference-schema extension beyond 256 and Gamma keyset coverage remain unimplemented successors.

62z297. `src/data_layer/point_in_time_market_research/polymarket_incremental_population.py` - WP165 bounded incremental/repeated public Polymarket cumulative cross-run lineage capture coordinator and offline registration recovery; label `POLYMARKET_BOUNDED_CUMULATIVE_INCREMENTAL_POINT_IN_TIME_POPULATION`; posture `MANUAL_GET_ONLY_CUMULATIVE_256_RECORD_CROSS_RUN_LINEAGE_NO_TRADING_AUTHORITY`; default network posture OFF with a valid dry-run result; nonempty registered WP163 baseline required with exact latest-reference convergence proven before network; deterministic WP165 content-addressed `snapshot`/`ingest` run identities independent of response order; PRIMARY_ASSERTION/EXACT_DUPLICATE/SOURCE_REVISION classification against the latest prior with identity-drift rejection; complete cumulative WP156 validation with no external known parents; append-new-then-register-cumulative ordering with post-append offline recovery of exactly one orphan run; reuses only the allowlisted sibling-private WP164 capture helpers and the WP164 config; no direct network library, credential, authenticated endpoint, `POST /books`, keyset/pagination, Data API, order/trading method, WP10 JSONL writer, `local_data/` path, scheduler, retry, or sleep; closed no-echo results with `advisory_only=True` and `no_execution_authority=True`.

62z298. `docs/polymarket_incremental_point_in_time_population_contract.md` - WP165 canonical contract for the bounded incremental cumulative-lineage capture: label/posture, the cumulative-in-one-reference technique and why WP162-D004 stays open, baseline convergence proof, exact public API and reused WP164 config, deterministic run identity, the three lineage classifications and latest-prior selection, identity-drift rejection, append-new/register-cumulative ordering, registration failure and offline recovery, closed diagnostics/no-echo, no keyset/scheduler/auth/trading, the allowlisted WP164 import boundary, and the WP165-D001..D007 successor boundary.

62z299. `docs/status_entries/WP165.md` - stable Model D WP165 status fragment recording merged WP164 lineage, the `DATA_LAYER_PUBLIC_POPULATION` authority/non-authority posture, the exact 20-file scope, the seven-symbol public API, the cumulative <=256 technique with WP162-D004 kept open, the lineage/recovery behavior, the NON-DRAFT ready-for-review posture, and the prohibition on merge without independent review and explicit user authorization.

62z300. `tests/data_layer/point_in_time_market_research/test_polymarket_incremental_population.py` - WP165 focused deterministic no-network regression covering the exact public surface and seven-symbol export tail, the zero-network dry run, store/manifest/reference baseline preconditions before network, orphan-store block, mixed provenance, worst-case capacity, Gamma/book guard denial, fetch/parse failures writing nothing, the three Gamma and order-book lineage classifications with exact parents and supersedes, latest-parent selection across history, changed-event and token-moved-market drift rejection, cumulative validation with no external known parents, append-new/immutable-old-reference semantics, append-failure and registration-failure recoverability, genuine/forged/multi-batch offline recovery, response-order-independent identities, the WP164 private-import allowlist, and the AST/token-aware no-network/no-auth/no-order/no-scheduler/no-keyset source scan.

62z301. WP165 merged: PR #165; WP165 final implementation head `883d806ce979b2671dc22378ff9d4faaac5bcf40`; WP165 merge commit `6cfb3a8913661401635e8b7ce1d55219098bb9dd`. WP166 registered as the current review target: scalable lineage-delta references and manual keyset market-universe expansion. A backward-compatible schema-2.0.0 `LINEAGE_DELTA_RECORD_BATCH` dataset snapshot reference registers only the current records with an explicit external direct-parent id set already committed by an earlier manifest entry plus the prior manifest-head backlink, removing WP165's cumulative-256 ceiling so physical history grows to the WP163 4096-record and WP161 256-entry/reference horizons; v1 references remain byte-for-byte identity- and behavior-compatible with no SQLite schema migration. One manual `GET /markets/keyset` page (<=100 markets, documented 2026-08-30 but repo-unverified, behind a double opt-in) plus at most 20 CLOB books captures a page and returns the response `next_cursor` for a later manual invocation with no automatic loop, scheduler, credential, or trading authority. WP162-D004 is resolved for the registered external-parent context, WP165-D001 is resolved within the current physical horizon, and WP164-D003/WP165-D002 are partially resolved for the manual one-page keyset. The analytical research store and query layer remains the unimplemented WP167 successor.

62z302. `src/data_layer/point_in_time_market_research/polymarket_scaled_population.py` - WP166 bounded scalable one-page keyset lineage-delta public Polymarket capture coordinator and offline registration recovery; label `POLYMARKET_SCALABLE_KEYSET_LINEAGE_DELTA_POPULATION`; posture `MANUAL_ONE_PAGE_KEYSET_GET_ONLY_EXTERNAL_PARENT_COMMITTED_NO_TRADING_AUTHORITY`; default network posture OFF with a valid dry-run result; a double opt-in (`allow_network` and `allow_documented_unverified_keyset`) gates real use of the documented-but-repo-unverified keyset endpoint; nonempty registered baseline required with the physical WP163 record-id set proven equal to the registered ordinary-id union before network; capacity gates (WP163 4096, WP161 256 entries/references, current-page 256) before any client call; deterministic WP166 `snapshot`/`ingest` run identities committing `after_cursor`/`page_limit` but never `next_cursor`; one keyset page then optional deterministic books; classification against the entire registered history; append-current-then-register-v2-delta ordering with post-append offline recovery of exactly one orphan page; reuses only the allowlisted sibling-private WP164 capture helpers; no direct network library, credential, authenticated endpoint, automatic cursor loop, Data API, order/trading method, WP10 JSONL writer, `local_data/` path, scheduler, retry, or sleep; closed no-echo results with `advisory_only=True` and `no_execution_authority=True`.

62z303. `docs/scalable_lineage_delta_and_keyset_population_contract.md` - WP166 canonical contract for the scalable lineage-delta references and manual keyset expansion: the schema-2.0.0 v2 reference and v1 identity compatibility, the `known_parent_records` external parent-object semantics, the manifest-chain parent-context authority with the 4096 bound and two closed errors, mixed v1/v2 persistence with no SQLite migration, the WP162 lineage-delta adapter with three closed errors, WP163 v2 materialization, the GET-only keyset endpoint/policy, the double opt-in coordinator, run identity/boundaries/capacity/persistence order, offline recovery, closed diagnostics, and the WP167 successor boundary.

62z304. `docs/status_entries/WP166.md` - stable Model D WP166 status fragment recording merged WP165 lineage, the `DATA_LAYER_PUBLIC_POPULATION` authority/non-authority posture, the exact 33-file scope, the v2 reference/keyset/coordinator surface, the double opt-in, physical-history-beyond-256 scaling within the WP163/WP161 horizons, the deferred-item resolutions, the NON-DRAFT ready-for-review posture, and the prohibition on merge without independent review and explicit user authorization.

62z305. `tests/data_layer/point_in_time_market_research/test_polymarket_scaled_population.py` - WP166 focused deterministic no-network regression covering the exact public surface and eight-symbol export tail, the config boundary, the zero-network dry run, the double opt-in, one keyset GET with no cursor loop and no offset, the response-wrapper and cursor grammar, 100-market pages and over-limit rejection, optional books with deterministic ordering and a single book-failure aborting the page, the three lineage classifications with exact external parents, v2 references containing only current records, materialization convergence, physical history beyond 256 within bounded manifest, capacity gates before network, append-failure and registration-failure recoverability, offline recovery, wrong-cursor and multi-page orphan rejection, no-URL/path/cursor echo, and the AST/token-aware no-network/no-scheduler/no-retry/no-auth/no-trading source scan.

62z306. WP166 merged: PR #166; WP166 final implementation head `f310d96c2f5c9ae6ec589239e945ab5746463911`; WP166 merge commit `35f4042a595ae58bf8b71a986eaefac0d3fe3dc8`. WP167 registered as the current review target: analytics, external history and materialization foundation. WP167 is the project's first runtime-dependency package: it adds exactly `pyarrow==25.0.1`, `duckdb==1.5.5`, and `polars==1.44.1` and moves the Python support floor to `>=3.12,<3.15`. It establishes a local, offline, read-only-against-canonical, derived-data analytical plane at `src/data_layer/analytical_research/`: verified WP160/WP163 dataset snapshot references materialize into deterministic derived Parquet whose logical identity is defined by canonical record content and explicit row order, never by physical Parquet bytes, with physical integrity evidence recorded separately. A provenance-separated `ExternalDatasetDescriptor` classifies immutable local external-history objects; the representative source is the pmxt Polymarket Orderbook Archive v2, always `THIRD_PARTY_NATIVE_FRAME_ARCHIVE`, validated from explicitly supplied local Parquet paths with no downloader and no network. DuckDB and Polars provide read-only queries with parity checks. Canonical SQLite records and manifests remain the sole integrity authority. WP167 was reclassified from L to XL under explicit user authorization because the mandated new source package and honest current-phase advancement require updating `tests/test_architecture_boundaries.py`, `tests/test_project_status_docs.py`, and seven historical scope/reconciliation governance guards (`tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py`, `tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py`, `tests/test_local_research_workflow_value_measurement_harness_contract_docs.py`, `tests/test_point_in_time_market_research_data_foundation_contract_docs.py`, `tests/test_wallet_intelligence_architecture_contract_docs.py`, `tests/test_human_review_label_workflow_docs.py`, `tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py`) with the narrowest WP167 branch, giving an exact 29-file governed scope while preserving every historical WP's exact-scope assertions. Local DuckDB native availability is observational and environment-dependent; Windows Smart App Control may block the pinned native module in some local states and is never disabled or weakened by WP167, so the exact final local observation is recorded in the PR body rather than encoded as permanent repo truth; hosted strict CI (ubuntu-24.04 and windows-2022, Python 3.12 and 3.14) is the authoritative cross-platform DuckDB proof and must be green at the exact final PR head before independent review. No NautilusTrader, WebSocket runtime, Data API, Hermes runtime, strategy, paper, credentials, execution, live, or scheduler authority is added. The NautilusTrader offline kernel remains the unimplemented WP168 successor.

62z307. `src/data_layer/analytical_research/` - WP167 analytical research package. `research_dataset.py` materializes verified canonical PIT dataset snapshot references into derived Parquet (`market_observations`, `source_snapshots`, `resolution_rule_snapshots`, `review_conflicts`), computes logical vs physical identity, verifies partition file integrity, checks the exact dependency pins and Python floor, and provides DuckDB (lazy-imported) and Polars query helpers. `external_dataset.py` builds the deterministic, path-independent `ExternalDatasetDescriptor`. `pmxt_v2.py` is the representative local-only pmxt v2 adapter with bounded batched schema/event/timestamp/decimal/side validation and no network. Canonical contract: `docs/analytical_research_layer_contract.md`; focused tests under `tests/data_layer/analytical_research/`; hosted compatibility evidence: `.github/workflows/ci.yml`.

62z308. `docs/analytical_research_layer_contract.md` - WP167 canonical contract: canonical PIT authority unchanged, derived Parquet as analytical materialization only, provenance-separated external history, PyArrow/DuckDB/Polars responsibilities, logical vs physical identity, pmxt local-only with no downloader, no product network, no NautilusTrader/WebSocket/Data API/Hermes/strategy/paper/execution/live, hosted CI as compatibility evidence not deployment, and the WP168 successor boundary.

62z309. WP167 merged: PR #167; WP167 final implementation head `557127fc04b75e75bb5594ab47df10a25f94d72d`; WP167 merge commit `b79049e9330cc3a94721f0b0653b48f66e31551b`. WP168 registered as the current review target: the NautilusTrader offline kernel, ParquetDataCatalog and deterministic replay foundation. WP168 adds exactly `nautilus_trader==1.231.0` (base install; no `polymarket` extra `py-clob-client-v2`, no Redis, no network) alongside the WP167 pins and keeps the Python floor `>=3.12,<3.15`. It establishes a local, offline, read-only-against-canonical research runtime at `src/research_runtime/nautilus_offline/` (a new top-level research-runtime boundary): verified WP167 pmxt-v2 external history — bound to the WP167 `ExternalDatasetDescriptor` provenance with a strict 1:1 source-object mapping and revalidated `source_sha256` hashes — is deterministically mapped to a Polymarket `BinaryOption` and Nautilus market-data objects, registered in a local `ParquetDataCatalog`, queried, and replayed through a bounded offline `BacktestEngine` into a repo-controlled, path-independent, mutation-sensitive `NautilusReplayReceipt`. Ordering is receive-time-primary `(ts_init, ts_event, event_kind_rank, canonical_row_digest, canonical_row_bytes)` with a frozen `event_kind_rank` and deterministic duplicate multiplicity; identity constants `wp168-nautilus-pmxt-v2-conversion/1.0.0`, `polymarket-nautilus-offline-replay-receipt`@`1.0.0`, and prefix `nautilusreplay:sha256:` are frozen. NautilusTrader is installed from upstream, not vendored or modified (LGPL-3.0 notices preserved). Exact governed scope is 35 files (schema maximum) with an explicit 36th-file STOP, preserving every historical WP's exact-scope assertions. Canonical WP167/PIT truth is unchanged; the Nautilus catalog/replay output is derived research runtime state only. It is an event-replay proof only and adds no alpha, executable-edge, realistic-fill, paper-readiness, or live-readiness claim, and no live Nautilus data/execution client, authenticated Polymarket client, WebSocket, Data API, Hermes, strategy, order/fill, paper, live, or scheduler authority. The public realtime WebSocket data plane remains the unimplemented WP169 successor.

62z310. `src/research_runtime/nautilus_offline/` - WP168 offline NautilusTrader kernel package. `runtime_compatibility.py` proves the exact `nautilus_trader==1.231.0` pin, the supported Python range, and importability of the required offline modules with a closed fail-closed result. `instruments.py` maps a frozen `BinaryOptionMarketContext` to a Polymarket `BinaryOption` (venue POLYMARKET, USDC, `AssetClass.ALTERNATIVE`) with a frozen absent-value policy and no fabricated metadata. `conversion.py` validates WP167 external provenance and pmxt-v2 event semantics and emits the canonical ordered event stream. `catalog.py` builds and queries a local `ParquetDataCatalog`. `replay.py` runs the bounded offline replay and emits the `NautilusReplayReceipt`. Canonical contract: `docs/nautilus_offline_kernel_contract.md`; focused tests under `tests/research_runtime/nautilus_offline/`; hosted compatibility evidence: `.github/workflows/ci.yml`.

62z311. `docs/nautilus_offline_kernel_contract.md` - WP168 canonical contract: the frozen public API and immutable result dataclasses, WP167 external-dataset provenance binding, receive-time-primary deterministic ordering and canonical serialization, the finest-tick single-instrument policy, `ParquetDataCatalog` and offline `BacktestEngine` replay semantics, the closed error taxonomy/precedence, install-not-vendor LGPL-3.0 posture, and the WP169/WP170 successor boundaries.

62z312. `docs/status_entries/WP168.md` - stable Model D WP168 status fragment recording merged WP167 lineage, the `OFFLINE_REPLAY_RUNTIME_FOUNDATION` authority/non-authority posture, the exact 35-file scope, the offline replay kernel surface, the receive-time-primary determinism and external-provenance binding, the independent PASS certificate and `wp_spec_guard` exit 0, the review-ready posture, and the prohibition on merge without independent review and explicit user authorization.

62z313. WP168 merged: PR #168; WP168 final implementation head `d323a4ba29e7b460517aec2145e5aeb195fcfb62`; WP168 merge commit `f6416a34ef366ac41b4c874ac149cd1dcba671bc`. WP168G registered as the current review target: a workflow-governance readiness-hardening interstitial that adds one deterministic, local/offline, read-only pre-implementation package-readiness gate and the minimum workflow reconciliation so a future WP cannot become implementation-ready merely because its prompt/spec hashes and certificate are syntactically valid. WP168G adds no source/product runtime, dependency, lock-file, `.github/workflows/`, network, credential, scheduler, Hermes, strategy, paper, order-simulation, execution, or live authority. Exact governed scope is 23 files (XL); the package was re-scoped L -> XL under explicit user authorization to generalize three historical full-changed-set scope-registration guards to machine-spec authority. Readiness is never authorization: `IMPLEMENTATION_READY` is technical package readiness only and never grants the user's `AUTHORIZED` transition. The public realtime WebSocket and public activity/wallet data plane remains the unimplemented, separately gated WP169 successor, and WP170 remains the experiment-registry / feature-label identity successor after WP169; WP168G renumbers neither.

62z314. `tools/wp/wp_readiness_gate.py` - WP168G pre-implementation package-readiness gate. Stdlib-only, import-safe, deterministic, bounded, local/offline, read-only; performs no environment inspection, no network, no product-runtime import, and executes no tests. It imports and reuses `tools/wp/wp_spec_guard.py` (it does not duplicate the machine-spec/certificate validator) and additionally validates prompt structure and closed placeholder vocabulary, parses the single well-formed `NORMATIVE_RULE_MATRIX_V1` block and runs a structured semantic-contradiction sweep (same domain/subject/condition may not carry incompatible action/effect; distinct domains are intentionally distinct keys), checks the canonical state chain and that readiness is not authorization, enforces exact-scope authority and the successor boundary, and performs two-phase evidence-plan verification: pre-implementation target coherence where a missing named node is a `PLANNED_NEW_NODE` only when its exact test file is in `required_changed_files` (whether or not that file already exists on base), and post-implementation `--check-diff` exact-node existence plus bounded AST assertion adequacy (`assert` / `pytest.raises` / same-module helper recursion to depth 4). Output is a sanitized closed result (`IMPLEMENTATION_READY` / `NOT_IMPLEMENTATION_READY` / `USAGE_ERROR`, closed error codes, trusted counts) with no raw prompt/spec/test/body/exception/git echo. Exit contract: 0 ready, 1 not ready, 2 usage/file error. Focused tests: `tests/tools/wp/test_wp_readiness_gate.py`.

62z315. WP168G workflow reconciliation and narrow guard correction. `tools/wp/wp_spec_guard.py` gains a narrow exact-path authority mapping so `.github/pull_request_template.md` requires both `workflow_governance` and `canonical_evidence_policy`; no other `.github/` path is authorized and `.github/workflows/` authority, schema/version, error vocabulary/precedence, certificate/hash semantics, generated/protected-path rules, package-size limits, and the WP159 waiver are all unchanged. `tools/git/pr_evidence_consistency_guard.py` implements the post-WP91 canonical policy: `--pr-body` required and canonical, `--final-comment` optional and non-canonical (contradiction-checked only when supplied, never required to duplicate commands/helpers/head/Ready/network facts, `--require-current-final-marker` applies only when a comment is supplied); existing two-surface invocations remain accepted and duplicated-fact contradiction checks remain fail-closed. `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md`, `docs/ai/codex/VALIDATION_MATRIX.md`, `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`, and `.github/pull_request_template.md` are reconciled to this policy and to the non-authority readiness gate. The three historical tool-scope guards (`tests/test_human_review_label_workflow_docs.py`, `tests/test_wallet_intelligence_architecture_contract_docs.py`, `tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py`) derive authorized governance-tool paths from the active WP machine spec instead of a WP159-only exception.

62z316. `docs/status_entries/WP168G.md` - stable Model D WP168G status fragment recording merged WP168 lineage and merge SHA, the `WORKFLOW_GOVERNANCE_READINESS_HARDENING` authority/non-authority posture, the exact 23-file XL scope, the new non-authority readiness gate and narrow PR-template guard correction, the PR-body-required/final-comment-optional reconciliation, the historical scope-guard migration, the readiness-is-not-authorization invariant and unchanged canonical authorization chain, the review-ready posture, the reserved WP169/WP170 successors, and the prohibition on merge without independent review and explicit user authorization.

Codex workflow docs are authoritative for Codex execution guidance, but they do not outrank `AGENTS.md`, `docs/project_status.md`, `docs/deferred_items_log.md`, or active work-package constraints.

Any material policy or architecture change must update the relevant repo-truth file in the same WP.

62z317. WP168G merged: PR #169; WP168G final implementation head `2c67941b984a9a43da34a0038027961110d5f395`; WP168G merge commit `877367235a6b3df79374f18d59641f8f1af7b7eb`. WP169 registered as the current review target: the public market-truth realtime data plane at `src/data_layer/polymarket/`. WP169 adds exactly `websockets==17.1` (BSD-3-Clause; install-not-vendor) alongside the preserved WP167/WP168 pins and keeps the Python floor `>=3.12,<3.15`. It preserves exact raw bytes before normalization, normalizes supported Market WebSocket events without floats, maintains per-asset book readiness with disconnect/timestamp-regression/hash-conflict gaps healed only by a fresh full snapshot, persists append-only raw envelopes, normalized observations, sessions, gaps, and checkpoints (append-only history hash chain) in bounded local SQLite, collects public unauthenticated Data/Gamma/CLOB GET pages with closed Retry-After handling, decodes public Polygon V2 OrderFilled logs with confirmation and reorg handling, and promotes only eligible accepted observations through the existing canonical PIT builder. New source modules `market_truth.py`, `market_truth_store.py`, `market_truth_websocket.py`, `market_truth_data_api.py`, `market_truth_onchain.py`, and `market_truth_runtime.py`, plus the manual CLI `tools/polymarket/run_public_market_truth.py`. Canonical contract: `docs/public_market_truth_realtime_data_plane_contract.md`. Canonical PIT authority is unchanged and no direct PIT-to-Nautilus adapter is claimed. Exact governed scope is 35 files (schema maximum) with an explicit 36th-file STOP. No credentials, authenticated access, signing, orders, OMS, strategy, paper, live, Hermes, dashboard, or scheduler authority. WP170 (falsification-grade experiment registry and research-dataset OS) remains the unimplemented, separately gated successor.

62z318. WP169 merged: PR #170; WP169 final implementation head `c4a09aeb33e4c271feb709622660e5e58a00b642`; WP169 merge commit `17df81001171988e9ca49f92dc8fd170ecaa7103`. WP170 registered as the current review target: the falsification-grade experiment registry and research dataset OS under `src/data_layer/analytical_research/`. WP170 binds existing PIT and analytical identities without changing their authority; freezes immutable feature, label, sample, dataset, split, hypothesis, metric, baseline, family, preregistration, lifecycle, and run-evidence identities; applies strict UTC half-open formation/selection/OOS partitions with purge, embargo, group-isolation, and minimum-role rules; seals OOS until irreversible selection close and explicit release; marks every later OOS use diagnostic; retains negative, inconclusive, invalidated, successful, and diagnostic trials; and persists the exact record set in a bounded explicit-path append-only tamper-evident SQLite registry with complete-history verification. Exact governed scope is 26 files (XL, risk 2) under explicit authorization, including the Section 8F recertified historical source-scope guard compatibility edit. No dependency, lock-file, product network, credential, authentication, signing, scheduler, Hermes runtime, strategy, expected-return ranking, cost-adjusted result authority, paper, OMS, execution, risk, live, or successor capability is added. WP171 (Interactive Operator Cockpit) remains the next separately gated successor.

62z319. `src/data_layer/analytical_research/experiment_os.py` and `src/data_layer/analytical_research/experiment_registry.py` - WP170 deterministic experiment-control and registry implementation. `experiment_os.py` provides frozen dataclasses, closed non-echoing results, canonical bounded JSON identities, current PIT/analytical binding revalidation, feature/label/sample lineage, leakage-safe temporal splits, human-reviewed falsifiable hypotheses, baseline/family/trial preregistration, irreversible lifecycle receipts, and role-membership-bound evidence. `experiment_registry.py` provides an explicit lowercase-`.sqlite3` caller path, exact format/application/schema identity, two-table/two-trigger append-only schema, deterministic order-independent transactional append, idempotency, payload and chain verification, 4096-row/262144-byte-record/16777216-byte-store/256-record-batch bounds, complete dependency-order and cross-record checks, and family summaries. Every surface is local/offline and advisory with no execution authority.

62z320. `docs/falsification_grade_experiment_registry_and_research_dataset_os_contract.md` - WP170 canonical contract: authority and protected boundaries; exact machine-spec API authority; closed statuses/errors; type-namespaced identity derivation; existing dataset binding; feature/label/sample semantics; strict half-open temporal splits, purge, embargo, grouping, and membership hashes; family/trial/preregistration control; one-way lifecycle and sealed OOS evidence; exact SQLite schema, record kinds, append order, bounds, and cross-record verification; compatibility and WP171 successor boundary.

62z321. `docs/status_entries/WP170.md` and `docs/wp_specs/WP170/` - stable WP170 status and immutable package evidence. The prompt SHA-256 is `66e428610f19219c5fd0592cbe5258052be57eff38f590f452d31a5349722ec4`; frozen recertified spec SHA-256 is `93caf676d890cf9cea0602ff07a65009cd1976a705d083ce6e60d1590005eeaa`; the separate-context draftability certificate records `PASS_ALL_TWELVE_LENSES` with zero unresolved findings. Readiness is technical package readiness only; merge remains prohibited without independent live PR review and explicit user authorization.

62z322. WP170 merged: PR #171; final implementation head `8e5d83f695d2f2ef38c9f30e3a8e95eb271718da`; merge commit `434af62f0891959d145b631a77b472b3e80915d3`. WP171 is the current review target: Interactive Operator Cockpit MVP. It adds one local loopback-only read-only FastAPI/React view over caller-selected WP169 and WP170 SQLite evidence. Exact scope is 26 files (XL for scope budget only, explicitly authorized). It adds optional `fastapi==0.141.1` and `uvicorn==0.52.4`, plus a locked React `19.3.0`, ReactDOM `19.3.0`, Vite `8.3.0`, TypeScript `7.0.2` frontend on Node `24.18.0` LTS. No authoritative store write, external product-runtime network, credentials, authentication, signing, strategy, promotion, order, portfolio, risk, paper, execution, live trading, Hermes runtime/model/provider, scheduler, daemon, deployment, or successor capability is added.

62z323. `src/operator_cockpit.py` and `src/operator_cockpit_frontend/` - WP171 implementation. The backend has immutable caller-selected paths; validated SQLite URI read-only WP169 access; existing complete-history validated WP170 registry access; exactly six GET domain routes; default-50/min-1/max-100 list limits; bounded newest-first safe projections; and closed non-echoing errors. The frontend has exactly Overview, Market Truth, Experiments, and Audit / Health views with loading, empty, success, source-error, experiment-detail, and manual-refresh states. Canonical contract: `docs/interactive_operator_cockpit_contract.md`.

62z324. `docs/status_entries/WP171.md` and `docs/wp_specs/WP171/` - stable WP171 status and immutable package evidence. Prompt SHA-256 `f689ef77c43c46fc18f392e63f2b7770dc946a822cfe7cc25fa66717afee6e78`; spec SHA-256 `bed88b96d70d7c2854318f24362e9fc5cde975ded5826eab13fadc2942c4d408`; independent certificate result `PASS_ALL_TWELVE_LENSES` with no unresolved decisions and passing implementability simulation. Evidence mode is `PRIVATE_REPO_MANUAL_VERIFIED`; the PR body is canonical. WP172 — Hermes Runtime + Alpha Factory remains separately gated and unimplemented.

62z325. WP171 merged: PR #172; final implementation head `a650c08ab233e47beca7565a5bb8df11a4f41d02`; merge commit `d6a15e4007fe3ced5a7d059ec3fcdec496d2dc7d`. WP171G is the one-time Lean Agent Execution Governance transition review target. It replaces universal independent pre-implementation certification with mechanically derived FAST, RUNTIME, and PROTECTED tracks while retaining the unchanged human authorization boundary, deterministic readiness, exact-diff enforcement, failed-check blocking, hosted CI, and mandatory independent Side PR review. Every new governed prompt carries one normative machine-readable authority mirror whose risk level and all sixteen authority booleans must exactly equal the spec before routing; prose cannot broaden it. Certificate-free FAST/RUNTIME results report the certificate/package guard as not run. Historical valid certified packages remain accepted without mirror retrofit. WP171G itself uses the legacy strict independent certificate workflow one final time. It adds no product runtime, dependency, credential, network-runtime, Hermes-runtime, strategy, paper, execution, or live authority.

62z326. `tools/wp/wp_readiness_gate.py` first parses exactly one canonical prompt governance-authority mirror and requires its Risk 0–4 value and all sixteen booleans to equal schema-1.0.0 spec authority. It then derives the unchanged minimum governance track: PROTECTED for Risk 4 or credentials/execution/live; otherwise RUNTIME for Risk 3 or network/scheduler/Hermes-runtime/paper; FAST otherwise. A prompt may select a stricter track, never a weaker one. FAST/RUNTIME deterministic readiness does not require or claim an independent LLM certificate and reports the package guard as null/not run when none was supplied. PROTECTED retains the existing exact-hash independent certificate. Historical valid certified packages before WP171G remain accepted as legacy PROTECTED without a mirror retrofit. WP172 — Alpha + Executable Edge MVP is the next separately gated package and is not started by WP171G.

62z327. WP171G merged: PR #173; final implementation head `140f5d23b771c7596eb0aa716eebbb7a376e0f7d`; merge commit `82546d8390540f68cd427149e29bc67069513754`. WP172 is the current review target under the first FAST-track workflow: deterministic contract compilation and readiness, no draftability certificate, focused/adjacent edit-time validation, one stable-candidate authoritative suite/hosted CI, one PR, and mandatory independent Side review.

62z328. `src/research_runtime/executable_edge/` is the WP172 local/offline executable-edge research boundary. It validates and binds WP170 first-look OOS evidence and exact cost-model reference, adapts hash-bound WP168 pmxt-v2 receive-time-ordered book/trade truth, models explicit fees/latency/TTL/queue/markout/size-grid/threshold assumptions, preserves partial taker depth and conservative maker queue fills, classifies PASS/FAIL/INCONCLUSIVE/DIAGNOSTIC_ONLY, and persists canonical tamper-evident assessments to explicit local paths without overwriting different bytes. Every identity uses exact canonical JSON and SHA-256; all economics use `Decimal`/integer arithmetic.

62z329. `docs/executable_edge_contract.md`, `docs/status_entries/WP172.md`, and `docs/wp_specs/WP172/` are the WP172 canonical contract, stable status, and certificate-free FAST package. Exact changed-file scope is 18 after one consolidated same-capability addition of the mechanically discovered architecture full-source-set guard. No product/runtime network, credentials, account state, paper execution, real execution, live trading, Hermes, scheduler, daemon, service, dependency, or lock-file authority is added. The parked obsolete Hermes WP172 worktree is superseded and not on the critical path. WP173 — Serious Paper Trading System remains separately gated and unstarted.

62z330. WP172 merged: PR #174; final implementation head `39363e5a081b6737104260725b1b0c8fcffe9196`; merge commit `418bae72f24b0694eccc657ed5dc3f90a3f38f2a`. WP173 is the current review target under the RUNTIME track: Serious Paper Trading System + Paper Cockpit. It has deterministic certificate-free readiness, an exact 31-file scope, simulated-paper authority only, and mandatory independent implementation and Side review before merge. The obsolete Hermes-labelled WP172 remains superseded and off the critical path.

62z331. `src/paper_trading/` is the WP173 deterministic paper boundary. Exact eligible WP172 assessment/cost/trace/market-lineage bindings control immutable intents; every order persists hard ALLOW/DENY risk before OPEN; aggressive depth and passive trade-flow queue fills preserve WP172 fees, spread, slippage, latency, TTL, and markout semantics; Decimal spot accounting enforces cash/position reservations and session/UTC-day PnL; and a dedicated caller-selected SQLite journal provides transactional hash-chained evidence, checkpoint comparison, replay validation, restart equality, and `RECONCILIATION_BLOCKED`. Replay validates exact WP172 evidence. LIVE_STORE reads accepted canonical WP169 observations through SQLite `mode=ro` only and creates no market client.

62z332. `docs/serious_paper_trading_contract.md`, `docs/status_entries/WP173.md`, and `docs/wp_specs/WP173/` are the canonical contract, stable status, and certificate-free RUNTIME package. The existing cockpit adds exactly six GET-only paper projections and one Paper Operations view while remaining loopback/read-only. No dependency, lock, workflow, credential, authentication, wallet, signing, private account, venue order, real execution, live, Hermes/model authority, OS scheduler/service, or external product-network capability is added. WP174 — Auth / Signing / Execution Gateway is separately gated and unstarted; WP175 Restricted Live Canary and WP176 Mature Controlled Live remain later gates.

62z333. WP173 merged: PR #175; final implementation head `79e2953dee8754dc8d09781edd647202dee834aa`; merge commit `e0202750c1e6f2a3a885aa6efa04bbd8d0b2291a`. WP174 is the current PROTECTED-track review target. Its independent certificate binds the exact prompt/spec bytes and establishes `DRAFTABILITY_PASS`; the certificate-installed canonical gate separately reports `IMPLEMENTATION_READY`; explicit Gate A authorization permits only the certified 24-path XL implementation. XL authority is scope-size only. Readiness is not authority. Merge remains unauthorized pending review evidence.

62z334. `src/execution_gateway/` is WP174's narrow repo-owned protected gateway over the official `polymarket-client==0.10.0`, with `websockets==15.0.1`, deterministic LIMIT construction, fixture-only would-submit and mutation-attempt evidence, reference-only credential configuration, public signing identity, authoritative reconciliation state, heartbeat/user-stream/rate/access controls, and tamper-evident SQLite recovery. Runtime authority is exactly A0 DISABLED, A1 READ ONLY, or A2 SHADOW. The SDK mutation adapter is constructor-locked behind Gate B; no real secret is loaded and no real create/cancel call is reachable.

62z335. `docs/status_entries/WP174.md` and `docs/wp_specs/WP174/` are the WP174 stable status and immutable certified package evidence. The operator cockpit adds two backend-only bounded GET projections over caller-selected gateway SQLite evidence. WP173 remains read-only and behaviorally preserved. A3 RESTRICTED LIVE is absent; real secrets and venue mutations require a separate Gate B; capital/live authority requires Gate C through separately certified and authorized WP175, which WP174 does not start.

62z336. WP174 merged: PR #176; final implementation head `6fff7fefd8f936824a7586f94d452ca073b225dd`; merge commit `dbb4ee0e21e409c4639edc44cce17696a5b15156`. WP174B is the current PROTECTED-track review target: Gate-B Production Credential, Signing & Real-Mutation Enablement. Its independent certificate binds the exact prompt/spec bytes and establishes `DRAFTABILITY_PASS`; the certificate-installed canonical gate separately reports `IMPLEMENTATION_READY`; the bounded WP174B authorization permits only the certified 22-path XL implementation. Readiness is not authority. Merge remains unauthorized pending review evidence. WP174B closes WP174-D001 and does not start WP174-D002 / WP175.

62z337. `src/execution_gateway/gate_b.py` and `src/execution_gateway/gate_b_operator.py` are the WP174B repo-owned Gate-B boundary over the unchanged official `polymarket-client==0.10.0`. They add an ephemeral no-echo signer-key provider and opaque lease, a Deposit Wallet identity policy at signature type 3 that authenticates an already-deployed wallet without deployment or approvals, an in-memory authenticated session holding the raw client privately, a real local LIMIT signing probe that never posts, a real cancellation transport with attempt identity and single-transmit ambiguity handling, a sanitized content-addressed verification receipt, and a manual no-echo operator command. Runtime authority stays exactly A0 DISABLED, A1 READ ONLY, or A2 SHADOW; the Gate-B capability state B0 through B4 is orthogonal and never grants authority. No real secret or L2 credential is persisted; every real economic create/post is constructor-locked behind a Gate-C permit and fails closed with `GATE_C_REQUIRED` before dispatch.

62z338. `docs/status_entries/WP174B.md` and `docs/wp_specs/WP174B/` are the WP174B stable status and immutable certified package evidence, and the operator cockpit gains one backend-only bounded read-only Gate-B projection. No dependency, lock, or workflow file changes. A3 RESTRICTED LIVE is absent and capital at risk is USD 0; the one real Gate-B network mutation proof is a single empty-wallet `cancel_all` run by the operator in a separate no-echo terminal with only a sanitized receipt consumed. WP175 Restricted Live Canary and WP176 Mature Controlled Live remain later separately gated phases that WP174B does not start.

62z339. S10-WALLET-01 (Public Wallet / Point-in-Time Wallet Evidence Foundation) adds the shared research provenance / PIT / DQ / replay core at `src/data_layer/point_in_time_market_research/research_provenance.py` and the new `src/data_layer/wallet_intelligence/` package (`contracts.py`, `reconciliation.py`, `ledger.py`, `public_ingest.py`, `__init__.py`). It extends the existing GET-only `src/data_layer/polymarket/public_client.py` with bounded public Data API v2 wallet reads (`/v2/trades`, `/v2/activity`, `/v2/activity/combos`) and adds hard bounds plus disabled-by-default wallet feed policies to `src/data_layer/polymarket/polling_policy.py`. The wallet evidence ledger uses a unique SQLite application id `0x57414C31`, distinct from the Alpha Factory registry (1464877425) and WP170 (1464877424). Contract: `docs/wallet_public_evidence_foundation_contract.md`; status: `docs/status_entries/S10-WALLET-01.md`; machine spec: `docs/wp_specs/S10-WALLET-01/wp_spec.json` and `docs/wp_specs/S10-WALLET-01/wp_prompt.txt`. Focused tests: `tests/data_layer/point_in_time_market_research/test_research_provenance.py`, `tests/data_layer/wallet_intelligence/test_contracts.py`, `tests/data_layer/wallet_intelligence/test_reconciliation.py`, `tests/data_layer/wallet_intelligence/test_ledger.py`, `tests/data_layer/wallet_intelligence/test_public_ingest.py`, plus the extended `tests/data_layer/polymarket/test_public_client.py` and `tests/data_layer/polymarket/test_polling_policy.py`. It is evidence-only: no qualification, ranking, promotion, copyability, order, signing, paper, live, scheduler, Hermes, or WP170 authority; credentials/private keys/authenticated API remain 0; Gate C remains NOT AUTHORIZED; WALLET-02 and HERMES-CTX-01 are NOT STARTED.


## S10-CI-OPT-02 Risk-Based Local-First CI Optimization (current implementation target)

Karl authorized the exact corrected frozen 13-path FAST/Risk 2 package after deterministic readiness. PR #228 / S10-CC-CMD-01 is MERGED at e3e8673024c6921e794df8bf0aa4fcea3825dab1; PR #229 is an earlier merged ancestor. The base-owned classifier prefers eligible Tier 2 research/app/noncritical deployment without automatic Risk3/RUNTIME escalation, requires Tier 3 for actual sensitive impact and keeps routing OFF. Initial bootstrap runs all nine legacy legs plus classify/ci-final-gate. No product source, runtime, config, dependency, credential, trading or activation authority changes. main was observed unprotected; required-status enforcement and routing activation remain Karl-only separately gated post-merge actions. Merge authorized: NO. Exact final validation and posted evidence belong in the PR body; stable record: docs/status_entries/S10-CI-OPT-02.md. S10-CC-PROD-01 is separately gated.


## S10-CC-PROD-01 Private Production Control Center (current repository implementation target)

This current entry supersedes older Control Center/CI in-review target descriptions:
S10-CC-CMD-01 is merged via PR #228; S10-CI-OPT-02 is merged via PR #230 at
`10320087b9c16672d42fd0eaa50ded7e349b7a3a` (head
`f004c545e0ddd1d483c16d17045b880926d0c59e`). Karl authorized exact corrected
S10-CC-PROD-01 implementation after deterministic certificate-free RUNTIME readiness.
The contract is `docs/control_center_production_contract.md`; source is the existing
`src/operator_cockpit.py` with opt-in `frontend_dist`/`--frontend-dist`; the dormant
unit is `tools/deployment/systemd/polymarket-control-center.service`; existing test
families are `tests/test_operator_cockpit.py` and `tests/deployment/test_runtime_baseline.py`.
Operator guidance is in `tools/deployment/README.md`; frozen package and stable record
are `docs/wp_specs/S10-CC-PROD-01/` and `docs/status_entries/S10-CC-PROD-01.md`.
Exactly thirteen required/allowed paths. Existing 31 APIs/commands/SSE, SHA release,
base bootstrap, SSH-only UFW, slices and backup/recovery are preserved. Static assets
are built from the exact verified SHA and staged outside immutable tracked releases.
No host/service/Tailscale activation, GitHub settings, dependencies/locks/workflows,
credentials, accounts, trading, orders or capital. Post-merge private host proof is
Karl-only operator work; S10-ALPHA-03 remains separate. Merge authorized: NO.

Scope Amendment 01: Side18 approved exactly two compatibility-only edits in the
existing stream/command test modules: obsolete CockpitConfig field-order assertions
now include the appended frontend_dist. Exact scope is 13; architecture, behavior
and runtime authority remain unchanged.


## S10-CC-UX-01 Obsidian Research Interactive Prototype (current repository implementation target)

This current entry supersedes older Control Center in-review target descriptions:
S10-CC-PROD-01 is merged via PR #231 at `7d77af8b45e5eafec0855fc30e17b167a5178636`.
Karl authorized the exact REV B1 nine-file FAST/Risk 2 package after deterministic readiness.
Frozen package: `docs/wp_specs/S10-CC-UX-01/`; stable record:
`docs/status_entries/S10-CC-UX-01.md`. Source is presentation-only in the existing
`src/operator_cockpit_frontend/src/app.tsx`, `styles.css` and `foundation.stories.tsx`; the
existing guard `tests/test_operator_cockpit_stream.py` changes only its story count (35 -> 36).
The four frontend source modules, nine routes, read-only APIs, SSE, C16 closed command status
and production serving are preserved. No backend, dependency, workflow, host, credential,
trading or capital change. Visual approval and S10-CC-UX-02 rollout are Karl-only. Merge authorized: NO.

## S10-WALLET-03 PIT wallet observability and conditional cost research (local review pending)

`docs/wallet_copyability_research_contract.md` defines the research-only contract;
`src/data_layer/wallet_intelligence/copyability.py` and additive exports in
`src/data_layer/wallet_intelligence/__init__.py` implement bounded read-only source
verification followed by deterministic in-memory calculations.
`tests/data_layer/wallet_intelligence/test_copyability.py` provides synthetic
source/PIT/cost/reconciliation/integrity/authority negatives. Governed REV3 files
are `docs/wp_specs/S10-WALLET-03/wp_prompt.txt` and `wp_spec.json`; stable evidence
is `docs/status_entries/S10-WALLET-03.md`. Existing WALLET-01/02 sources are
unchanged. The profile is canonically rederived against an existing verified
read-only ledger, not authenticated by its mapping hash alone. Retained quote
bytes and registered provenance distinguish observed from scenario-only evidence;
scenario fees/depth requirements do not prove follower fills or profitability.
No store, provider, credential, strategy, execution, paper or live authority is
added. Side19 acceptance and hosted CI are pending; no merge-ready or
LOCAL_ACCEPTED claim is made. ALPHA-03/04 are preserved independently, and WALLET-04
retains ownership of wallet incrementality against non-wallet controls.
Karl's exact eleven-file amendment authorizes the named historical source guard;
both approved modules must exist, and missing/third matched paths reject (D007
resolved). Original commit 3bcce95a2f33b2ab1af976a29787a99c3fa38a37 is preserved as
an ancestor. Final full-suite environment preflight/result and Side19 assessment
remain separately evidenced; no hosted checks, acceptance or merge is presumed.
