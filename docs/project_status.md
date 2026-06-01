# Project Status

- Current phase: WP41 - Advisory Prompt/Runbook Package
- Repo state: Advisory prompt/runbook package on branch
- Merged WPs: WP1, WP2, WP3, WP4, WP5, WP6, WP7, WP8, WP9, WP10, WP10-Follow-up, WP11, WP12, WP13, WP14, WP15, WP16, WP17, WP18, WP19, WP20, WP21, WP22, WP23, WP24, WP25, WP26, WP27, WP28, WP29, WP30, WP31, WP32, WP33, WP34, WP35, WP36, WP37, WP38, WP39, WP40
- Current branch: `wp41-advisory-prompt-runbook-package`
- API integration status: STDLIB_READ_ONLY_PUBLIC_DATA_ACTIVE; MANUAL_EXPLICIT_NETWORK_POLLING_RUNNER_DEV_ONLY; MANUAL_GUARD_ENFORCED_SNAPSHOT_CAPTURE_DEV_ONLY
- Runtime dependency integration status: NOT_STARTED_FOR_NEW_RUNTIME_DEPENDENCIES
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
- Advisory prompt/runbook package status: DOCS_ONLY_ADVISORY_PROMPT_RUNBOOK_ON_BRANCH
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
- Architecture status: WP3 documentation-only skeleton merged; WP8 adds approved read-only data-layer source under src/data_layer/polymarket/; WP9 adds contract probe tooling and validates three of four endpoint candidates; WP10 adds local file-based snapshot persistence (JSONL) under src/data_layer/polymarket/ and manual capture tool under tools/polymarket/; WP11 adds offline snapshot reader, in-memory market catalog, replay helpers, and manual inspection CLI under src/data_layer/polymarket/ and tools/polymarket/; WP12 adds offline snapshot quality gates, catalog quality metrics, and local report generation under src/data_layer/polymarket/ and tools/polymarket/; WP13 adds offline snapshot deduplication and sanitized local catalog exports under src/data_layer/polymarket/ and tools/polymarket/; WP14 adds official Python client dependency decision and boundary review docs/tests only; WP15 adds official-client sandbox tooling under tools/polymarket/official_client_sandbox/ only; WP16 adds offline polling policy and local rate-limit guard only; WP17 adds a manual finite explicit-network read-only polling runner only; WP18 adds guard-enforced manual snapshot capture using WP16 policy before Gamma and optional CLOB reads; WP19 adds offline guard-aware quality/reporting for WP18 guarded capture manifests; WP20 adds policy/docs/tests only for advisory AI-agent and Hermes read-only boundaries; WP21 adds schema/docs/tests only for a future local read-only agent context export; WP22 adds persistent Codex workflow guidance, templates, checklists, and tests only; WP23 adds a local/offline/read-only agent context JSON exporter only under src/data_layer/agent_context/ and tools/polymarket/; WP24 adds the local operator runbook and doc tests for safe manual exporter use only; WP25 adds deterministic local/offline/read-only report generation from WP23-compatible exports only; WP26 adds operator runbook docs/tests only for safe manual report-generator use; WP27 adds Agent/Hermes manual setup decision record docs/tests only; WP28 adds token-efficiency operating model, concise reporting rules, and reusable WP prompt blocks docs/tests only; WP29 adds design/docs/tests only for the local/offline/read-only diff/scope summary helper; WP30 adds the local/offline/read-only stdlib helper implementation at tools/git/diff_scope_summary.py, focused tests, and user-facing helper doc; WP31 adds design/docs/tests only for a future local/offline/read-only validation-output summary helper; WP32 adds the local/offline/read-only stdlib helper implementation at tools/validation/validation_output_summary.py, focused tests, and user-facing helper doc; WP33 adds docs-only design guidance at docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md for a future advisory code-index / blast-radius helper; WP34 adds the local/offline/read-only stdlib helper implementation at tools/git/code_blast_radius.py, focused tests, and user-facing helper doc; WP35 adds design/docs/tests only for a future local/offline/read-only memory/status snapshot helper at docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md; WP36 adds the local/offline/read-only stdlib helper implementation at tools/git/status_snapshot.py, focused tests, and user-facing helper doc; WP37 adds docs/tests only to consolidate the WP28-WP36 token-efficiency sequence, helper usage order, advisory-only limits, deferred helper gaps, protected-boundary reaffirmation, and next-WP gate; WP38 adds docs/tests only to resume advisory-agent planning through a local advisory handoff package with no runtime, Hermes, LLM, credential, trading, database, dashboard, scheduler, polling, or product behavior; WP39 adds docs/tests only to define the future local advisory consumer boundary and consumption model with no runtime, Hermes, LLM, network, account, trading, database, dashboard, scheduler, polling, dependency, source, tools, or product behavior; WP40 adds a local/offline/read-only deterministic advisory consumer prototype under tools/advisory/local_advisory_consumer.py with explicit local_data inputs only, stdout by default, optional ignored advisory output, and no runtime, LLM, Hermes, network, account, trading, database, dashboard, scheduler, polling, dependency, lock-file, or src/ changes; WP41 adds docs/tests only for human-operated advisory prompt/runbook templates and operator review steps with no runtime, prompt runner, LLM, Hermes, network, account, trading, database, dashboard, scheduler, polling, dependency, lock-file, tools/, or src/ changes.
- Deferred items status: WP9 marks WP8-D001 READY_FOR_WP (three endpoints confirmed, CLOB /health unconfirmed); long-running runtime/data deferred items remain unchanged unless explicitly listed later; WP38 resolves WP37-D001 only for selecting and documenting the local advisory handoff path, not for runtime/product implementation; WP39 resolves WP38-D001 only for docs-only advisory runtime boundary and consumption design completion, not for advisory consumer implementation; WP40 resolves WP38-D002 and WP39-D001 only for the deterministic local/offline/read-only advisory consumer prototype scope, not for runtime/LLM/Hermes/trading implementation; WP41 resolves WP39-D002 and WP40-D001 only for docs-only advisory prompt/runbook package scope, not for runtime/LLM/Hermes/provider/account/trading implementation; WP40-D002 remains OPEN because LLM/Hermes/provider integration is not designed or implemented; WP41-D001 and WP41-D002 are OPEN; WP28-D001, WP30-D001, WP32-D001, WP34-D001, WP36-D001, and WP36-D002 remain OPEN; WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION; WP27-D001, WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain OPEN and unchanged; security checks are run/assessed in WP41.
- Generated artifact status: WP6 guardrails active; WP7 gitleaks binary in ignored tools/.bin/ (not committed); local_data/ is ignored and generated outputs must not be committed; WP23 agent context exports output remains under ignored local_data/agent_context_exports/; WP25 agent context report output remains under ignored local_data/agent_context_reports/; WP40 optional advisory consumer output remains under ignored local_data/advisory_outputs/ only.
- Next intended WP: after WP41, candidate next WPs are WP42 - Advisory Prompt/Runbook Package Follow-Up, if gaps remain; WP42 - Advisory Consumer Integration Review / Operator Workflow Hardening, if the user wants to improve the local human-operated workflow without LLM/Hermes/runtime; WP42 - Provider/Hermes Decision Refresh, only if explicitly approved by the user; or another explicitly approved safe repo-truth WP. Do not suggest database, dashboard, strategy runtime, paper trading, live trading, official-client runtime integration, scheduler, wallet/copy-trading, production polling, Hermes install, LLM provider runtime, or agent runtime as next WP.

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

## WP41 Advisory Prompt/Runbook Package Update

WP41 - Advisory Prompt/Runbook Package is on branch.
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
