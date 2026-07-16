# Hermes Candidate-Review Assisted Research Provider, Runtime, Privacy, Permissions, And Budget Decision

## Purpose

WP143 records the provider, runtime, privacy, permissions, credential, and budget architecture under which a future controlled Hermes-assisted candidate-review research experiment may be considered. It decides governance and target architecture only; it does not implement or execute the architecture.

## Position After WP142

WP141 is the controlling provider-neutral, runtime-inactive experiment contract. WP142 supplies one fixed local synthetic/offline 20-case pack, a 16-category human-review rubric, and ten zero-tolerance hard gates. WP143 preserves those contracts, adds no provider performance evidence, and does not run the cases.

## Authority And Non-Authority

The Centralized Boundary Group Reference in `docs/ai/codex/PROTECTED_PATHS.md` remains binding. WP143 crosses none of credentials/secrets, authenticated clients, wallet/account behavior, order placement/cancel, execution gateway, paper engine, scheduler/bot loop, runtime/daemon, dashboard/deployment, dependency/lock changes, external code copying, or generated artifacts.

Authorized outputs are this decision record, one Markdown-only focused test, one stable status fragment, repo-truth reconciliation, and exact documentation allowlist registrations. WP143 grants no source, tool, workflow, dependency, configuration, prompt, runtime, provider/model activation, credential, network call, source retrieval, storage, recommendation, probability, ranking, paper/live, execution, risk, order, acceptance, or strategy-promotion authority.

## Repository Inputs Reviewed

The decision reviews WP95's accepted research-brain plan, WP96's advisory architecture, WP97's contract/validator requirements, WP98's manual prompt/operator foundation, the WP140 manual-workflow closeout, the WP141 experiment contract, the WP142 fixture/rubric document and exact JSON pack, their focused tests and status fragments, project status, repo-truth index, protected paths, evidence architecture, and current Hermes-document and status-chain guards.

The repository contains no sufficiently current accepted provider/model research naming eligible candidates. Exact provider/model naming is therefore `DEFERRED_CURRENT_EXTERNAL_RESEARCH_REQUIRED`; no vendor or model is invented or selected here.

## Decision Principles

- Keep deterministic case selection, input construction, permission enforcement, budget enforcement, timeout/retry enforcement, result capture, validation, gate evaluation, audit metadata, and termination local and authoritative.
- Treat Hermes and every model response as an untrusted draft producer only.
- Use synthetic WP142 data only, least privilege, fail-closed controls, deterministic validation, and mandatory human review.
- Make provider choice replaceable and bound candidate count, calls, cost, tokens, latency, retries, and concurrency.
- Grant no execution authority merely by documenting a future permission or budget.

## Runtime Architecture Options

| Option | Classification | Decision reason |
|---|---|---|
| Local-only Hermes with local model | `LOCAL_ONLY_LOCAL_MODEL: OPTIONAL_FUTURE_BASELINE_NOT_PRIMARY` | Strong privacy and cost baseline, but hardware capability and model quality are not established. |
| Local Hermes with remote model API | `LOCAL_HERMES_REMOTE_MODEL: SELECTED_TARGET_ARCHITECTURE` | Preserves local deterministic control while allowing replaceable, high-capability remote candidates under exact endpoint, permission, and budget controls. |
| Managed hosted agent environment | `MANAGED_HOSTED_AGENT: REJECTED_FOR_INITIAL_EXPERIMENT` | Weakens local permission enforcement and expands retention, tooling, repository, privacy, and audit surfaces. |
| Direct model API without Hermes | `DIRECT_MODEL_API_BASELINE: ALLOWED_AS_COMPARISON_BASELINE_ONLY` | May measure provider/model behavior but does not exercise Hermes agent behavior. |

No option is authorized to run by WP143.

## Selected Target Architecture

Assisted-research architecture: LOCAL_DETERMINISTIC_CONTROL_PLANE_WITH_EPHEMERAL_HERMES_SESSION

Model-access posture: PROVIDER_NEUTRAL_REMOTE_MODEL_CANDIDATES_WITH_OPTIONAL_LOCAL_BASELINE

The target is `LOCAL_DETERMINISTIC_CONTROL_PLANE + LOCAL_EPHEMERAL_HERMES_SESSION + ONE_APPROVED_REMOTE_MODEL_ENDPOINT + SYNTHETIC_WP142_CASE_INPUT + NO_BROWSER_SEARCH_OR_SOURCE_TOOLS + DETERMINISTIC_VALIDATION + MANDATORY_HUMAN_REVIEW`.

An operator would manually start one bounded session. The local deterministic controller would supply one explicit synthetic case or a later-approved bounded batch, enforce permissions/budgets/timeouts/retries, and terminate the session. There is no daemon, scheduler, background mode, autonomous retry loop, repository-wide access, shell, traversal, persistent memory, live source retrieval, model-visible credential, automatic downstream record creation, or paper/live/trading access.

Hermes installation/runtime activation: NOT AUTHORIZED

Deterministic validation and human review: MANDATORY

Paper/live/execution authority: FORBIDDEN

## Provider Decision Posture

Provider decision: SHORTLIST_MAXIMUM_TWO_REMOTE_CANDIDATES_PLUS_OPTIONAL_ONE_LOCAL_BASELINE

Provider activation: NOT AUTHORIZED

Provider activation is deferred to a separate approved experiment package. The future shortlist may contain one high-capability reasoning candidate, one lower-cost or latency-optimized remote candidate, and an optional local baseline only when hardware is documented. Maximum remote provider/model configurations: 2. Candidate names remain `DEFERRED_CURRENT_EXTERNAL_RESEARCH_REQUIRED` until current external research is separately approved and recorded. Candidate entries, if later named, are `CANDIDATE_ONLY` and do not activate an account or model.

## Provider Eligibility Criteria

Every remote candidate must pass every mandatory gate.

Contract and privacy gates: API/business terms exclude submitted API data from training by default or provide an equivalent no-training control; retention, deletion, data-processing jurisdiction, subprocessors, security, and incident reporting are documented; zero retention is preferred and standard retention may not exceed 30 days; account and key revocation are supported.

Technical gates: a stable versioned API and explicit model/version identifier; usage and cost reporting; configurable output limits; timeout support; request identifiers; documented errors; no mandatory provider-hosted tools, persistent memory, or repository connection; and ability to receive only the explicit synthetic case bundle.

Experiment-compatibility gates: the WP142 case size fits the envelope; output can be deterministically checked against the WP133 boundary; browsing/source retrieval is unnecessary; the WP142 rubric remains provider-neutral; no real or sensitive data is stored; and manual key revocation is supported. One failed mandatory criterion makes the candidate ineligible.

## Privacy And Data Classification

Experiment data classification: SYNTHETIC_OFFLINE_TEST_DATA_ONLY

Experiment data classification: SYNTHETIC_NON_PERSONAL_NON_CONFIDENTIAL

Provider training use: MUST_BE_DISABLED_OR_CONTRACTUALLY_EXCLUDED

Personal data: FORBIDDEN

Credentials in prompt or model-visible context: FORBIDDEN

Real wallet/account/order data: FORBIDDEN

Only invented WP142 material may enter the initial future experiment. No real market, wallet, account, order, person, company, event, private, provider, or confidential data is approved.

## Retention, Jurisdiction, Logging, And Deletion

Preferred provider retention: ZERO_RETENTION

Maximum acceptable standard retention: 30_DAYS

Jurisdiction: MUST_BE_DOCUMENTED_BEFORE ACTIVATION

Deletion: MUST_BE_DOCUMENTED_AND_OPERATOR_VERIFIED_AFTER_EXPERIMENT

Future local audit metadata may record case ID, fixture/rubric versions, candidate and model/version identifiers, start/end time, latency, tokens/compute, cost, retries, provider request ID, validation/hard-gate/human-review results, and stop reason. It may not record API keys, secrets, authorization headers, the full environment, unrelated filesystem metadata, personal/private/trading state, or raw provider payloads outside a separately approved evidence policy.

Raw inputs/outputs may exist only in memory or an ephemeral session directory during a future approved run. Stable raw-output persistence requires separate approval.

## Permission Matrix

These are future permissions, not active capabilities.

| Capability | Initial future experiment decision | Notes |
|---|---|---|
| Read explicit WP142 case bundle | ALLOW_READ_ONLY | One selected case or bounded approved batch |
| Read WP141/WP142 contract metadata | ALLOW_READ_ONLY_EXACT_FILES | No repository traversal |
| Read repository generally | DENY | No repo-wide context |
| Write repository | DENY | No commits or generated files |
| Read arbitrary local files | DENY | Exact input bundle only |
| Session temp directory | ALLOW_EPHEMERAL_READ_WRITE | Deleted after run |
| Persistent output directory | DENY | Separate approval required |
| Shell/command execution | DENY | No subprocess |
| Browser/search | DENY | First experiment is offline/synthetic |
| External source retrieval | DENY | Provider endpoint only |
| Provider API endpoint | FUTURE_ALLOWLIST_ONE_ENDPOINT | Not authorized in WP143 |
| Other outbound network | DENY | Fail closed |
| Tool calls | DENY | No tools in first experiment |
| Trading APIs | DENY | Always outside Hermes authority |
| Wallet/account endpoints | DENY | No private state |
| Environment access | DENY_EXCEPT_NAMED_SECRET_INJECTION_BY_CONTROLLER | Secret not model-visible |
| Persistent memory | DENY | No cross-session memory |
| Session memory | ALLOW_EPHEMERAL | Destroyed after run |
| Scheduler/background execution | DENY | Manual start only |
| Automatic retry | DENY | Controller-governed bounded retry only |
| Automatic downstream record creation | DENY | Human/deterministic workflow only |
| Automatic acceptance | DENY | Deterministic validation and human review mandatory |

Repository posture: NO_REPOSITORY_WIDE_ACCESS

File posture: EXPLICIT_READ_ONLY_INPUT_BUNDLE_AND_SESSION_TEMP_DIRECTORY_ONLY

Command and shell posture: DISABLED

Tool posture: NO_BROWSER_NO_SEARCH_NO_SOURCE_FETCH_NO_TRADING_TOOLS

## Credential And Secret Policy

Credential posture: OUT_OF_REPO_OPERATOR_INJECTED_LEAST_PRIVILEGE_REVOCABLE_SECRET

Credential storage: OUTSIDE_REPOSITORY

Credential delivery: OPERATOR_INJECTED_AT_SESSION_START

Credential visibility to Hermes/model: FORBIDDEN

Credential scope: LEAST_PRIVILEGE_SINGLE_PROVIDER_EXPERIMENT_ONLY

Credential lifetime: TEMPORARY_AND_REVOCABLE

Credential logging: FORBIDDEN

Credential persistence: FORBIDDEN

A future controller may receive a named secret through an external secret store or operator-controlled environment injection. Secrets may never enter repository files, Markdown, JSON fixtures, prompts, logs, screenshots, PR bodies, model-visible context, or authorization-error text. The operator must redact provider errors, revoke the experiment key after completion, document owner/revocation outside the repository, and never reuse production or trading credentials. WP143 creates no secret and selects no secret-store product.

## Memory Policy

Memory posture: EPHEMERAL_SESSION_MEMORY_ONLY

Persistent memory: FORBIDDEN

Cross-session memory: DISABLED

Provider-hosted memory: DISABLED

Hermes persistent memory: DISABLED

Session-local scratch memory: ALLOWED_EPHEMERAL

Memory deletion: MANDATORY_AT_SESSION_END

Each run must be reproducible from the fixed WP142 case, fixture/rubric versions, experiment configuration, provider/model version, controller version, and a later-approved prompt/config package. No run may rely on prior-run context.

## Network Policy

Network posture for the first future experiment: PROVIDER_ENDPOINT_ONLY_DENY_ALL_OTHER_NETWORK

Default outbound network: DENY

Permitted future outbound destination: ONE_EXPLICIT_PROVIDER_API_ENDPOINT

Browser/search endpoints: DENY

Source URLs: DENY

Redirects to unapproved domains: DENY

Provider-hosted tool execution: DENY

DNS/network failure behavior: FAIL_CLOSED

The first future experiment is synthetic and offline except for its single provider-model request path. WP143 authorizes no network call.

## File And Repository Policy

There is no repository-wide mount, `.git` access, source-tree traversal, home-directory or personal-file access, environment dump, arbitrary path input, model-controlled path or filename, symlink escape, archive extraction, or executable-file creation. A future deterministic controller must allow only the exact read-only input bundle and exact ephemeral temp directory, validate paths, prevent following symlinks outside that directory, and delete the directory after each run. No raw prompt/output persistence is authorized.

Raw prompt/output persistence: FORBIDDEN_UNLESS_SEPARATELY_APPROVED

WP143 implements none of these controls.

## Budget And Quota Envelope

Maximum remote provider/model configurations: 2

Optional local baseline configurations: 1

Gold cases: 20

Required repeated runs per case per remote configuration: 3

Maximum planned remote primary calls: 120

`20 cases × 3 runs × 2 remote configurations = 120`.

Maximum retry per failed case/run: 1

Maximum total retry calls: 20

Maximum total remote calls: 140

Retries are allowed only for provider transport failure, documented transient provider error, or deterministic timeout before usable output. They are forbidden for low quality, failed rubric score, unsafe output, content-caused validator rejection, or an expected refusal.

Maximum total experiment spend: USD 100

Maximum daily spend: USD 25

Maximum single-call spend: USD 2

Automatic top-up: FORBIDDEN

Budget warning threshold: 80_PERCENT

Budget hard stop: 100_PERCENT

Maximum input tokens per call: 50000

Maximum output tokens per call: 8000

Maximum request timeout: 180_SECONDS

Maximum end-to-end case-run duration: 300_SECONDS

Concurrent remote calls: 1

These are upper bounds. A later package may lower but not raise them without separate approval. Budget decision only: no spend is authorized by WP143.

## Cost Accounting Requirements

Every future call record must contain case ID, run number, candidate configuration ID, provider request ID, input tokens or equivalent, output tokens or equivalent, cached token/compute amount, latency, retry status, provider-reported cost, independently calculated estimated cost where possible, cumulative daily cost, cumulative experiment cost, budget warning status, and stop status. Cost records must exclude secrets and authorization headers. WP143 creates no provider invoice or paid usage.

## Experiment Stop Conditions

A future deterministic controller must stop immediately on any secret exposure; training use contrary to policy; unconfirmed retention or jurisdiction; non-allowlisted network attempt; browser/search/source/tool invocation; repository-wide, arbitrary-file, shell, or command access; persistent memory; unauthorized raw-output persistence; input mutation; automatic WP122/WP123 creation; validation or human-review bypass; authoritative recommendation/probability/trading/execution instruction; total cost at USD 100; daily cost at USD 25; estimated single-call cost above USD 2; total calls at 140; timeout breach; unidentified provider/model/version; unapproved model/version change; material terms/privacy change; or human stop decision.

## Candidate Evaluation Criteria

Eligibility is fail-closed across privacy/no-training, retention, jurisdiction, deletion, API stability, version identity, usage/cost reporting, endpoint restriction, tool-free operation, output-limit/timeout support, and budget compatibility.

Eligible candidates are compared using the WP142 hard-gate pass rate, expected-outcome rate, minimum and aggregate scores, deterministic WP133 validation rate, human correction burden, refusal quality, unsupported claims, fabricated citations, source-access misrepresentation, repeatability, latency, cost, and operational failure rate. The comparison may recommend a future experiment candidate only; it grants no production provider selection, persistent integration, model autonomy, runtime activation, or trading use.

## Promotion Gates

Before any controlled provider experiment starts, all gates must pass:

- Repository: WP141, WP142, and WP143 merged; project status and repo truth current; full suite green; no protected-path conflict.
- Architecture: local-control decision, eligibility evidence, exact endpoint allowlist, permission matrix, memory/file/credential/deletion policies accepted.
- Privacy: no-training, retention, jurisdiction, deletion, synthetic-only data, and no PII/secrets confirmed.
- Budget: prices reviewed at experiment time; projected maximum within USD 100; daily/per-call caps enforceable; no automatic top-up; operator approval recorded outside the repository.
- Safety: no shell/browser/search/source/persistent memory/trading tools; deterministic validation and human review mandatory; emergency stop and key revocation available.
- Evidence: exact provider/model/version, case/rubric, controller, and later prompt/config versions recorded; raw-output handling and evidence/reporting format separately approved.

Failure of one gate blocks the experiment.

## Options Considered

| Decision area | Selected posture | Rejected alternatives | Reason |
|---|---|---|---|
| Control plane | Local deterministic controller | Provider-managed autonomous control | Preserve deterministic authority |
| Hermes runtime | Local ephemeral session | Persistent daemon / hosted autonomous agent | Bounded permissions and cleanup |
| Model access | Max two remote candidates | One locked provider / unlimited candidates | Provider neutrality and bounded cost |
| Local model | Optional baseline | Required primary runtime | Hardware and quality not assumed |
| Data | Synthetic WP142 only | Real market/account/wallet data | Privacy and experiment isolation |
| Network | One provider endpoint only | Browser/search/source access | First experiment is offline/synthetic |
| Files | Exact read-only bundle + temp dir | Repo-wide or home-directory access | Least privilege |
| Commands | Disabled | Shell/tool execution | Prevent side effects |
| Memory | Ephemeral only | Persistent/provider memory | Repeatability and privacy |
| Credentials | Out-of-repo injected secret | Repo config or prompt secret | Secret safety |
| Raw output | No persistence by default | Automatic logging/storage | Privacy and scope control |
| Budget | USD 100 total hard cap | Open-ended spend | Bounded experiment |
| Concurrency | One remote call | Parallel calls | Cost and audit control |
| Trading | Forbidden | Advisory/execution crossover | Preserve deterministic safety boundary |

## Explicit Deferred Capabilities

Not implemented: Hermes installation; provider account selection; provider contract acceptance; model selection; API key creation; secret-store selection; prompt/config package; provider adapter; experiment controller; endpoint allowlist implementation; sandbox implementation; file permission enforcement; network enforcement; cost limiter implementation; logging implementation; raw-output policy implementation; provider call; WP142 case execution; provider comparison result; persistent storage; source retrieval; citation verification; real market or wallet research; paper/live trading; order placement or cancel; strategy promotion; and AI acceptance or risk authority.

These are separately gated future capabilities, not WP143 defects.

## Output Surface Inventory

Allowed outputs are one Markdown decision record, one Markdown-only focused test, one stable WP143 status fragment, project-status/repo-truth updates, exact documentation registrations, and PR/status evidence.

Forbidden outputs include source/tool/workflow code; provider SDK/config; model config; secret/credential; prompt; runtime harness; fixture execution; model/network/raw experiment output; storage/database; export/report; CLI/scheduler; recommendation/probability/ranking; and paper/live/execution/risk/order artifacts.

## Forbidden Interpretations

- Selected target architecture does not mean it is implemented.
- Provider candidates do not mean a provider is selected or activated.
- Remote model endpoint does not authorize a network call.
- Credential posture does not create or store a credential.
- USD 100 budget does not authorize spending.
- Session temp directory does not authorize persistent output.
- Ephemeral memory does not authorize persistent memory.
- Provider eligibility does not prove provider compliance.
- Candidate comparison does not authorize production use.
- Hermes research brain does not mean execution controller.
- Human review does not transfer deterministic authority.
- Future experiment does not authorize source fetching or trading.

## Future WP144 Boundary

`WP144 — Hermes Candidate-Review Assisted Research Controlled Experiment Harness Contract, Prompt/Configuration Boundary, And Dry-Run Plan V1`

WP144 may define the controller contract, Hermes invocation and prompt/configuration boundaries, provider-adapter interface, sandbox/permission enforcement, endpoint allowlist, secret injection, budget/timeout/retry controls, raw-output handling, WP142 test plan, and dry-run evidence. It must not install Hermes, create a real provider credential, call a paid model, execute all 20 cases, fetch sources, persist raw output, trade, or implement WP145 unless separately and explicitly authorized.

WP144 requires separate approval

## Decision

Assisted-research architecture: LOCAL_DETERMINISTIC_CONTROL_PLANE_WITH_EPHEMERAL_HERMES_SESSION

Model-access posture: PROVIDER_NEUTRAL_REMOTE_MODEL_CANDIDATES_WITH_OPTIONAL_LOCAL_BASELINE

Provider decision: SHORTLIST_MAXIMUM_TWO_REMOTE_CANDIDATES_PLUS_OPTIONAL_ONE_LOCAL_BASELINE

Provider activation: NOT AUTHORIZED

Hermes installation/runtime activation: NOT AUTHORIZED

Experiment data classification: SYNTHETIC_OFFLINE_TEST_DATA_ONLY

Network posture for the first future experiment: PROVIDER_ENDPOINT_ONLY_DENY_ALL_OTHER_NETWORK

Repository posture: NO_REPOSITORY_WIDE_ACCESS

File posture: EXPLICIT_READ_ONLY_INPUT_BUNDLE_AND_SESSION_TEMP_DIRECTORY_ONLY

Command and shell posture: DISABLED

Tool posture: NO_BROWSER_NO_SEARCH_NO_SOURCE_FETCH_NO_TRADING_TOOLS

Memory posture: EPHEMERAL_SESSION_MEMORY_ONLY

Persistent memory: FORBIDDEN

Raw prompt/output persistence: FORBIDDEN_UNLESS_SEPARATELY_APPROVED

Credential posture: OUT_OF_REPO_OPERATOR_INJECTED_LEAST_PRIVILEGE_REVOCABLE_SECRET

Deterministic validation and human review: MANDATORY

Paper/live/execution authority: FORBIDDEN

Maximum remote provider/model configurations: 2

Maximum total remote calls: 140

Maximum total experiment spend: USD 100

Maximum daily spend: USD 25

Maximum single-call spend: USD 2

Concurrent remote calls: 1

WP144 requires separate approval

## Non-Authority Statement

WP143 records only a future target architecture and governance envelope. No Hermes process, provider request, model call, account, SDK, credential, prompt execution, source retrieval, repository access grant, permission control, storage, spend, recommendation, probability, ranking, paper/live behavior, execution, risk, order activity, acceptance, or strategy promotion is created or authorized.
