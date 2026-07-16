# Hermes Candidate-Review Assisted Research Controlled Experiment Harness Contract, Prompt/Configuration Boundary, And Dry-Run Plan

## Purpose

WP144 defines the documentation-only contract for a possible future controlled
Hermes-assisted candidate-review research harness and a local no-provider
dry-run plan. It defines controller ownership, the exact controller state
machine, session-envelope and non-executable prompt/configuration boundaries,
the provider-adapter boundary, permissions, credentials, budgets, evidence,
teardown, failures, and promotion gates. It implements and executes none of
them.

## Position After WP143

WP141 remains the provider-neutral, runtime-inactive experiment contract.
WP142 remains the canonical fixed local synthetic/offline 20-case pack,
16-category rubric, and ten zero-tolerance hard gates. WP143 selects a future
local deterministic control plane with one ephemeral Hermes session, at most
two remote configurations plus one optional local baseline, one future
allowlisted provider endpoint, synthetic-only input, bounded cost and calls,
deterministic validation, and human review. WP144 converts those decisions into
an exact future harness contract and a dry-run plan without activation.

## Authority And Non-Authority

Harness contract status: DOCUMENTATION_ONLY_RUNTIME_INACTIVE

Controller authority: LOCAL_DETERMINISTIC_EXCLUSIVE

Hermes session posture: ONE_CASE_ONE_EPHEMERAL_SESSION

Provider adapter posture: ONE_EXPLICIT_CANDIDATE_CONFIGURATION_ONE_ALLOWLISTED_ENDPOINT

Prompt/configuration status: VERSIONED_NON_EXECUTABLE_CONTRACT_ONLY

Input posture: EXACT_VALIDATED_WP142_CASE_BUNDLE_ONLY

Output posture: UNTRUSTED_DRAFT_ONLY

Raw input/output persistence: FORBIDDEN_BY_DEFAULT

Sanitized experiment metadata: FUTURE_ALLOW_EXACT_FIELDS_ONLY

Network posture: DENY_ALL_EXCEPT_ONE_CONTROLLER_MEDIATED_PROVIDER_ENDPOINT

Tool posture: NO_BROWSER_NO_SEARCH_NO_SOURCE_FETCH_NO_SHELL_NO_TRADING_TOOLS

Memory posture: EPHEMERAL_SESSION_ONLY_DELETE_ON_TEARDOWN

Dry-run posture: LOCAL_NO_PROVIDER_NO_NETWORK_NO_CREDENTIAL

Deterministic validation and human review: MANDATORY

Hermes/provider/model activation: NOT AUTHORIZED

Paper/live/execution authority: FORBIDDEN

WP145 requires separate approval

The Centralized Boundary Group Reference in
`docs/ai/codex/PROTECTED_PATHS.md` remains binding. WP144 crosses none of
credentials/secrets, authenticated clients, wallet/account behavior, order
placement/cancel, execution gateway, paper engine, scheduler/bot loop,
runtime/daemon, dashboard/deployment, dependency/lock changes, external code
copying, or generated artifacts.

WP144 authorizes only this document, one Markdown-only focused test, one stable
status fragment, repo-truth reconciliation, and exact compatibility
registrations. It authorizes no controller, harness, adapter, sandbox,
endpoint allowlist, credential mechanism, prompt/configuration file, prompt
execution, provider/model call, fixture change, experiment run, source fetch,
raw storage, paper/live behavior, execution, risk, order, or trading change.

## Repository Inputs Reviewed

The contract reviews WP95's research-brain plan; WP96's advisory architecture;
WP97's input/output and deterministic-validator requirements; WP98's manual
prompt/operator foundation; the WP141 contract; the complete WP142 rubric,
fixture, tests, and status; the complete WP143 decision, test, and status;
project status; repo-truth index; protected paths; evidence architecture; and
the existing local adapter, dry-run, runbook, temp-only smoke, teardown, and
fail-closed precedents. Research/workbench artifacts remain non-authoritative.

## Selected Harness Architecture

The exact future conceptual flow is:

```text
manual operator start
→ local deterministic controller preflight
→ load one exact WP142 case
→ validate case/contracts/permissions/budgets
→ construct sanitized session envelope
→ start one ephemeral Hermes session
→ controller-mediated provider-adapter call
→ capture untrusted draft
→ deterministic WP133 validation
→ WP142 hard-gate/rubric evaluation
→ mandatory human review
→ sanitized evidence
→ teardown and deletion
```

This is future architecture only. No step is implemented or executed in
WP144. The operator starts one case manually; the controller remains the only
control plane; Hermes/model contributes only an untrusted draft in a later
approved experiment.

## Deterministic Controller Ownership

The future local deterministic controller exclusively owns:

- experiment and case selection;
- version selection;
- case loading;
- input validation;
- prompt/configuration assembly;
- permission, path, and endpoint enforcement;
- credential acquisition and model-invisible injection;
- budget, call, token, timeout, retry, and concurrency enforcement;
- session start and stop;
- input immutability;
- output capture;
- WP133 validation;
- WP142 hard-gate and rubric evaluation;
- human-review handoff;
- sanitized evidence;
- raw-output policy; and
- teardown, temporary-data deletion, and terminal-state selection.

Hermes/provider/model owns only untrusted-draft generation in a later
separately approved experiment. It owns no transition, validation, evaluation,
permission, credential, budget, retry, evidence, teardown, acceptance, or
downstream-record decision.

## Controller State Machine

The exact ordered future states are:

1. `NOT_STARTED`
2. `PREFLIGHT`
3. `CASE_LOADED`
4. `INPUT_VALIDATED`
5. `PERMISSIONS_VALIDATED`
6. `BUDGET_VALIDATED`
7. `SESSION_ENVELOPE_BUILT`
8. `EPHEMERAL_SESSION_READY`
9. `PROVIDER_INVOCATION_PENDING`
10. `UNTRUSTED_OUTPUT_CAPTURED`
11. `DETERMINISTIC_VALIDATION_COMPLETE`
12. `RUBRIC_EVALUATION_COMPLETE`
13. `HUMAN_REVIEW_COMPLETE`
14. `SANITIZED_EVIDENCE_COMPLETE`
15. `TEARDOWN_COMPLETE`
16. `COMPLETED`
17. `STOPPED_FAILED_CLOSED`

Rules: no state may be skipped; transitions are controller-only; every failure
transitions to `STOPPED_FAILED_CLOSED`; no automatic restart or background
continuation exists; unsafe or content-caused output is never retried;
teardown is mandatory on success and failure; and `COMPLETED` requires human
review, sanitized evidence, and teardown. A failure before session creation
still performs all applicable teardown confirmations. A terminal failure may
enter `STOPPED_FAILED_CLOSED` only after the mandatory teardown attempt; a
teardown failure remains failed-closed and is escalated.

## Session Envelope Boundary

Allowed conceptual fields only:

- experiment, configuration, and case IDs;
- fixture, rubric, WP141, and WP143 versions;
- exact synthetic question and request scope;
- supplied synthetic excerpts and labels;
- known uncertainty and missing data;
- authority and safety constraints;
- WP133 output-shape instructions;
- non-authority notice;
- human-review requirement;
- budget, timeout, and output limits; and
- permission-profile and output-policy IDs.

Forbidden fields and content:

- credentials or authorization headers;
- real market, account, wallet, order, or personal data;
- unrestricted repository context;
- arbitrary metadata;
- source URLs;
- commands;
- trading instructions;
- prior-session memory; and
- unapproved provider internals.

The envelope is conceptual documentation. WP144 creates no envelope schema,
builder, serializer, file, or runtime object.

## Prompt Boundary

A later prompt/configuration package must be versioned, deterministic,
bounded, and provider-neutral where possible. Every later prompt must state:

- untrusted draft only;
- no source access;
- no tools, shell, or repository access;
- no secrets;
- no downstream record creation;
- no recommendation, probability, or trading authority;
- uncertainty, missing data, falsification, and limitations are required;
- WP133 alignment is required;
- human review is mandatory; and
- token and output limits are binding.

It must not contain credentials, commands, hidden retrieval, tool invocation,
arbitrary repository context, self-modification, persistent memory,
autonomous-agent authority, or automatic acceptance. WP144 creates no
executable prompt, prompt template, prompt file, prompt runner, or prompt
execution.

## Configuration Boundary

Allowed conceptual configuration fields only are config/controller/Hermes
versions; candidate/provider/model/version identifiers; endpoint allowlist ID;
case/fixture/rubric/prompt versions; permission/memory/output-policy profiles;
timeouts and duration; token/call/retry/cost limits; concurrency; and mandatory
human-review and teardown requirements.

WP144 creates no JSON, YAML, TOML, `.env`, provider configuration, model
configuration, runtime configuration, or other executable configuration.

## Provider Adapter Boundary

A future adapter may only receive one controller-built sanitized request; use
one allowlisted endpoint; apply exact time and output limits; and return a
provider request ID, usage, cost, bounded errors, and untrusted output.

It may not read repository or local files; choose a model or endpoint; expose
secrets to Hermes/model; follow unapproved redirects; retry itself; use tools,
memory, or sources; persist output; validate or evaluate; create downstream
records; or trade. All retry decisions remain controller-owned. WP144
implements no adapter, interface, provider SDK, network client, or fake
adapter.

## Permission Enforcement Boundary

WP143 is preserved exactly: the future controller may read only one exact
WP142 case and exact WP141–WP143 metadata read-only; it has no general
repository or local-file access; it may use one ephemeral temporary directory;
it may not write the repository; shell, browser, search, source, and trading
tools are disabled; only one future provider endpoint may be allowlisted; all
other network is denied; persistent memory/output is denied; scheduler and
background modes are denied; retries are controller-bounded; and automatic
records and acceptance are denied. Enforcement unavailability is a pre-session
hard stop. WP144 implements no permission or sandbox mechanism.

## Credential Injection Boundary

Credentials remain outside the repository; operator-injected only after
preflight; temporary; least-privilege; single-provider; revocable; not logged;
not persisted; and invisible to Hermes/model. They are revoked or disabled
after completion. Credential values, headers, authorization errors, and
environment dumps may never enter prompts, envelopes, evidence, repository
files, logs, screenshots, or PR content. WP144 creates, reads, or selects no
credential, secret store, injection mechanism, provider account, or key.

## Budget, Timeout, Retry, And Concurrency Enforcement

The WP143 upper bounds remain exact:

- maximum remote configurations: `2`;
- gold cases: `20`;
- repeated runs per case: `3`;
- maximum primary calls: `120`;
- maximum retry calls: `20`;
- maximum total calls: `140`;
- total spend: `USD 100`;
- daily spend: `USD 25`;
- per-call spend: `USD 2`;
- input tokens per call: `50,000`;
- output tokens per call: `8,000`;
- request timeout: `180 seconds`;
- case-run duration: `300 seconds`;
- concurrency: `1`; and
- automatic top-up: forbidden.

Retry is permitted only for transport failure, a documented transient provider
error, or a timeout before usable output, and only when the controller approves
at most one retry for the affected run within the 20-retry cap. There is no
retry for unsafe output, validation failure, low rubric score, expected
refusal, unsupported content, or policy breach. The future adapter cannot
retry. Any projected or actual cap breach stops and tears down.

## Raw Output And Sanitized Evidence Policy

Raw input/output persistence is forbidden by default. During a later approved
session, raw content may exist only in memory or the exact ephemeral directory
for the minimum deterministic-validation and human-review time, then must be
deleted.

Future sanitized metadata may include only:

- experiment, case, run, and configuration versions;
- provider, model, version, and request ID;
- timing, tokens/compute, cost, and retry status;
- deterministic-validation and hard-gate results;
- normalized rubric score;
- human correction and reviewer outcome;
- stop reason;
- teardown result; and
- credential-revocation confirmation.

It must exclude secrets, headers, raw prompt/output, private data, source
content, arbitrary errors, and unrelated environment or filesystem data.
WP144 creates no evidence schema, storage, log, report, receipt, raw artifact,
or experiment result.

## Teardown Contract

Teardown is mandatory on every terminal path, in this exact order:

1. stop provider activity;
2. stop the Hermes session;
3. clear memory;
4. delete temporary files;
5. close handles and connections;
6. prevent continued retries;
7. record sanitized stop metadata;
8. confirm no repository mutation;
9. confirm no raw persistence;
10. record credential-revocation responsibility;
11. enter `TEARDOWN_COMPLETE`; and
12. enter `COMPLETED` or `STOPPED_FAILED_CLOSED`.

Teardown failure means failed-closed and escalation. It cannot be hidden,
retried indefinitely, or converted into completion.

## Failure Matrix

| Failure | Required response |
|---|---|
| Invalid case or version mismatch | Stop before session |
| Permission enforcement unavailable | Stop before session |
| Credential unavailable | Stop before session |
| Budget projection over cap | Stop before session |
| Endpoint not allowlisted | Stop before session |
| Provider/model identity mismatch | Stop and teardown |
| Unapproved redirect | Stop and teardown |
| Timeout/transport failure | At most one controller-approved retry |
| Unsafe output | No retry; failure review; teardown |
| Secret/private-data echo | Immediate stop and teardown |
| Source-access/tool/shell claim | Hard-gate failure; no retry |
| Input mutation | Immediate stop and teardown |
| WP133 validation failure | No automatic repair; review; teardown |
| Automatic downstream record | Immediate stop and teardown |
| Budget/call limit | Immediate stop and teardown |
| Raw persistence attempt | Immediate stop and teardown |
| Human stop | Immediate stop and teardown |
| Teardown failure | Failed-closed and escalation |

There is no hidden repair, regeneration, alternate-model fallback, or
content-caused retry.

## Local No-Provider Dry-Run Plan

This plan is defined but not executed.

### Stage A — static preflight

Verify versions, select one exact WP142 case, reject secrets/URLs/real data,
verify conceptual permissions and budgets, and prove the exact state order.

### Stage B — deterministic envelope

Build a future conceptual envelope and prove input immutability and absence of
every forbidden envelope field. No schema or envelope is built in WP144.

### Stage C — fake adapter boundary

A future test-only deterministic fake adapter returns fixed untrusted output.
It uses no provider SDK, network, credential, or reusable product adapter.
WP144 creates no fake adapter.

### Stage D — validation/evaluation

Apply existing WP133 validation where applicable, then WP142 hard gates and
rubric evaluation, and require human review. Create no downstream records.

### Stage E — teardown

Prove an empty or deleted temporary directory, no repository mutation, no
memory or persistence, no continued retry, and one deterministic terminal
state.

## Dry-Run Acceptance Matrix

| Acceptance criterion | Required proof in a future WP145 dry run |
|---|---|
| No provider/network/credential | Fake adapter only; no network or secret access |
| One WP142 case | Exactly one validated canonical case is selected |
| Exact state sequence | All applicable states occur in order with no skip |
| Input immutability | Original case bundle is unchanged |
| Untrusted output | Fake output is never treated as accepted |
| Validation and evaluation | WP133 where applicable, all WP142 gates/rubric, and human review are recorded |
| No downstream records | No automatic WP122/WP123 or other record exists |
| No repository writes | Tracked and untracked repository state is unchanged |
| Teardown complete | Temporary data is absent and terminal state is deterministic |

Every row must pass. No dry run occurs in WP144.

## Security And Privacy Invariants

- Synthetic WP142 input only; no real market, wallet, account, order, person,
  private, or confidential data.
- No credential, header, secret, or environment dump reaches Hermes/model or
  evidence.
- Default-deny files, paths, tools, memory, network, redirects, and writes.
- Exactly one controller-mediated future provider endpoint; no browser,
  search, source retrieval, shell, trading tools, or repository traversal.
- Original inputs are immutable; raw content is ephemeral and deleted.
- Provider/model output is untrusted; deterministic validation and human
  review are mandatory.
- No automatic downstream record, acceptance, recommendation, probability,
  ranking, strategy promotion, paper/live action, execution, risk, or order.
- Every failure closes and every terminal path attempts teardown.

## Promotion Gates

WP145 may be considered only after WP144 is merged and the controller, state,
envelope, prompt/configuration, adapter, permissions, credential, budget,
raw-output/evidence, teardown, failure, and local no-provider dry-run contracts
are accepted. WP145 remains separately approved and must pass protected-path,
scope, security, exact-inventory, deterministic-test, and human-review gates.

WP144 does not approve a provider experiment, Hermes installation, provider or
model activation, prompt execution, credentials, network calls, or spending.

## Explicit Deferred Capabilities

Deferred to separately approved future work: controller implementation;
harness implementation; Hermes installation/invocation; executable prompt or
configuration files; prompt execution; provider adapter; test-only fake
adapter; sandbox; permission/path/network enforcement; endpoint allowlist;
credential acquisition/injection/revocation mechanism; provider/model/account
selection or activation; remote or local model call; fixture modification;
WP142 case execution; dry-run execution; raw-output storage; evidence schema or
storage; source retrieval; citation verification; real research data; automatic
records or acceptance; paper/live behavior; execution, risk, orders, or
trading; and WP145 implementation.

## Output Surface Inventory

Allowed outputs are this Markdown contract/dry-run plan, one Markdown-only
focused test, one stable WP144 status fragment, project-status and repo-truth
updates, two exact documentation-guard registrations, and PR/status evidence.

Forbidden outputs include source or tool code; controller, harness, adapter,
sandbox, endpoint allowlist, credential or secret mechanism; JSON/YAML/TOML or
`.env` configuration; executable prompt; provider SDK; network/model call;
fixture or case output; runtime output; raw or persistent evidence; export,
report, CLI, scheduler, daemon, or bot loop; and recommendation, probability,
ranking, paper/live, execution, risk, order, or trading artifacts.

## Forbidden Interpretations

- Harness contract does not mean a harness exists.
- Controller ownership does not mean a controller exists or runs.
- State-machine documentation does not create executable states.
- Session envelope fields do not create a schema or serialized envelope.
- Prompt/configuration boundary does not create or execute a prompt/config.
- Adapter boundary does not create a real or fake adapter.
- Future endpoint allowlisting does not authorize network access.
- Credential injection boundary does not create, read, or authorize a secret.
- Budget caps do not authorize spend.
- Raw ephemeral handling does not authorize persistent output.
- Sanitized evidence fields do not create an evidence store.
- Dry-run plan does not mean a dry run occurred.
- Human review does not transfer deterministic authority.
- Hermes research does not authorize recommendation or trading.
- WP145 gating does not implement or pre-approve WP145.

## Future WP145 Boundary

`WP145 — Hermes Candidate-Review Assisted Research Local Deterministic Harness Skeleton, Fake Provider Adapter, And No-Network Dry-Run V1`

WP145 may implement only a local/offline test-oriented skeleton, the exact
state machine, one test-only deterministic fake adapter, one WP142 case, and
`tmp_path` proof. It must not install or invoke Hermes; call a provider or
model; use a credential; run all cases; persist output; fetch sources; trade;
or implement WP146. WP145 requires separate approval.

## Decision

Harness contract status: DOCUMENTATION_ONLY_RUNTIME_INACTIVE

Controller authority: LOCAL_DETERMINISTIC_EXCLUSIVE

Hermes session posture: ONE_CASE_ONE_EPHEMERAL_SESSION

Provider adapter posture: ONE_EXPLICIT_CANDIDATE_CONFIGURATION_ONE_ALLOWLISTED_ENDPOINT

Prompt/configuration status: VERSIONED_NON_EXECUTABLE_CONTRACT_ONLY

Input posture: EXACT_VALIDATED_WP142_CASE_BUNDLE_ONLY

Output posture: UNTRUSTED_DRAFT_ONLY

Raw input/output persistence: FORBIDDEN_BY_DEFAULT

Sanitized experiment metadata: FUTURE_ALLOW_EXACT_FIELDS_ONLY

Network posture: DENY_ALL_EXCEPT_ONE_CONTROLLER_MEDIATED_PROVIDER_ENDPOINT

Tool posture: NO_BROWSER_NO_SEARCH_NO_SOURCE_FETCH_NO_SHELL_NO_TRADING_TOOLS

Memory posture: EPHEMERAL_SESSION_ONLY_DELETE_ON_TEARDOWN

Dry-run posture: LOCAL_NO_PROVIDER_NO_NETWORK_NO_CREDENTIAL

Deterministic validation and human review: MANDATORY

Hermes/provider/model activation: NOT AUTHORIZED

Paper/live/execution authority: FORBIDDEN

WP145 requires separate approval

## Non-Authority Statement

WP144 defines documentation-only future boundaries and a dry-run plan. It
creates or executes no controller, harness, state machine, adapter, sandbox,
allowlist, prompt, configuration, Hermes runtime, provider SDK, provider/model
request, credential, network call, dry run, experiment result, fixture change,
raw persistence, source retrieval, downstream record, recommendation,
probability, ranking, paper/live behavior, execution, risk, order, trading
authority, or WP145 implementation.
