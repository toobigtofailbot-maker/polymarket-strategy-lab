# Hermes Real-Provider Stage B Contract (S10-HERMES-AUTO-02-REAL-01)

Dormant, local/offline seam. It is not a provider call, not a model-origin proof, not live
authority and not a scheduler. Governing package: `docs/wp_specs/S10-HERMES-AUTO-02-REAL-01/`.

## Chain

```
AUTO-02 cycle_request (verified tool surface, menu/schema/cutoff/clocks)  -> StageBRequest
  -> build_real01_request(+ exact model-input bytes)                       -> Real01Request (real01:sha256:)
  -> run_real01_attempt: reserve real01-<id>.reserved BEFORE dispatch
  -> OfflineCodexWireTransport: one pinned child, in-memory httpx MockTransport
  -> verify_offline_wire + classify_wire_report                            -> one terminal real01-<id>.json
  -> origin record (real01origin:sha256:)  OFFLINE_WIRE_SIMULATED / MODEL_IDENTITY_UNVERIFIED
  -> autonomous_feedback.admit_real01_choice -> AUTO-01 evaluate_once(real_origin_evidence=...)
  -> REJECTED REAL_ORIGIN_UNVERIFIED (non-executable, before any store read)
```

## Route seam

`real_provider_stage_b.ROUTE` is the single replaceable route. Its values are pinned Hermes
v0.21.3 (`345cd2b057a452236de401d3534b8502a7465e8d`), `openai-codex`, `codex_responses`,
`https://chatgpt.com/backend-api/codex` and `gpt-5.6-sol`. It is a compatibility candidate,
not a guarantee of current access, terms, billing or model availability. A different
provider needs a new approval. There is no provider framework.

## R001 final wire

The child builds the native `AIAgent(enabled_toolsets=[])` with a placeholder bearer, a
sterile temporary home and denied sockets. It serializes the request with native
`build_api_kwargs` and the native Codex sanitizer and transform bypass. It then sends the
request once through the pinned OpenAI SDK's `responses.create(stream=True)` into
`httpx.MockTransport`. The capture is the effective POST after SDK transformation. Raw
body, prompt and headers are never retained; only digests, key names and verdict facts are.

The verdict requires all of the following:

- `POST https://chatgpt.com/backend-api/codex/responses`;
- body keys inside `{include, input, instructions, model, prompt_cache_key, reasoning,
  store, stream}`, with no `tools`, `tool_choice` or `parallel_tool_calls`;
- `include` limited to `reasoning.encrypted_content`;
- the requested model and `stream=true`;
- the exact instruction and model-input digests;
- SDK `max_retries=0` and `x-stainless-retry-count: 0`;
- zero socket attempts in the dispatch phase.

The same capture, run with the default `None` toolsets, must see tools (positive control).
That control agent's vision check tries `models.dev:443`, which is denied before DNS and
is the only control-phase target accepted.

Exact-pin findings (offline, 2026-10-16):

- AIAgent init performs an authenticated `GET /backend-api/codex/models` catalogue probe
  carrying the bearer. A sterile `config.yaml` with `model.context_length` suppresses it.
  Without that config this is a secondary authenticated egress.
- Native `run_codex_stream` retries transport errors once (`max_stream_retries = 1`), and
  `run_conversation` recovers tool calls. Neither is used.
- Across 16 offline scenarios (success, tool and built-in tool items, two replies,
  incomplete, missing terminal, empty SSE, stream error, model mismatch, missing usage,
  malformed JSON, 429, 503, read timeout, connect error), each produced exactly one
  generation POST.

## R002 one attempt

The request id is reserved with an exclusive create before the transport is touched.
Every dispatch writes exactly one terminal: a 429, 5xx, timeout, crash or ambiguous error
consumes the attempt. A reservation without a terminal (interrupted, or a concurrent
caller) is `ATTEMPT_ALREADY_RESERVED`, with no dispatch. A replay returns the stored
terminal without dispatching. A tampered terminal is `JOURNAL_INVALID`. Application
retries are 0, there is no fallback, and no auxiliary, title or refresh inference runs.

## R003 origin record

The record binds the following:

- request and Stage B ids, pin and tool fingerprint;
- route, endpoint and expected model;
- wire stage, verdict and body digest/bytes;
- the generation-request count and SDK retries;
- dispatch and finish clocks;
- HTTP/error class and raw-output digest;
- the fixture server model, response-id digest and usage.

Fixture fields are labelled `FIXTURE_UNTRUSTED`. The native assembler's `.model` echoes
the requested model (`assembler_model_is_request_echo=true`). Missing usage is
`USAGE_UNKNOWN`, never zero. Cost is `COST_UNKNOWN` / price `UNVERIFIED`. Every record is:

- `OFFLINE_WIRE_SIMULATED` / `PROVIDER_NOT_INVOKED`;
- `MODEL_IDENTITY_UNVERIFIED` / `MODEL_ORIGIN_UNVERIFIED`;
- `REAL_ORIGIN_UNVERIFIED`.

No path in this module can produce a verified label. A present but different server model
is `MODEL_MISMATCH`.

## R004 strict output

Every classification below ends the attempt, with no retry:

- Any non-message output item (function, built-in or server tool) is
  `TOOL_CALL_ATTEMPT_INVALID`.
- More than one or zero messages is `RESPONSE_SHAPE_INVALID`.
- Anything but exactly one `response.completed` is `RESPONSE_INCOMPLETE`.
- The 16,384-byte cap applies, and the output must be strict JSON (`strict_json_loads`).
- Reported output tokens above the cap are `USAGE_CAP_EXCEEDED`; this provisional bound is
  for the activation WP to replace.
- A finish after the deadline is `DEADLINE_EXCEEDED`.

`NO_TRADE` is valid. A valid offline classification is never alpha, qualification or
profitability evidence.

## R005 AUTO-01 seam

`evaluate_once(real_origin_evidence=...)` and `autonomous_feedback.verify_real_origin_evidence`
fail closed with `REAL_ORIGIN_UNVERIFIED` after strict choice validation and before any
store, EXEC-FEAS or Gate C call. That holds for offline records, relabelled or re-digested
dicts and forged results. Combining it with `producer_evidence` is
`PRODUCER_EVIDENCE_CONFLICT`. Calls without the new argument are byte-identical to merged
`7c62419` for legacy and offline-producer inputs.

## Activation gate (not authorized here)

`S10-HERMES-AUTO-02-REAL-01-ACTIVATION` is a separate PROTECTED one-call experiment. It
needs:

- independently certified WP hashes;
- Karl's consent;
- current provider, model, endpoint, terms and privacy;
- operator-scoped credential injection;
- a socket allowlist of exactly the generation endpoint;
- hard call, token, timeout and spend limits.

It must also keep the sterile context-length config. The Codex OAuth route exposes no
independently authenticated model identity in this capture, so the expected outcome is
`MODEL_IDENTITY_UNVERIFIED` unless a server-attested field is actually observed. A direct
API route may be chosen at that gate without rebuilding this core. A failed or
inconclusive paid call is never re-sent.

## ACTIVATION: official ChatGPT-plan OAuth route (S10-HERMES-AUTO-02-REAL-01-ACTIVATION)

Governing package: `docs/wp_specs/S10-HERMES-AUTO-02-REAL-01-ACTIVATION/` (PROTECTED, with an
independent certificate). Module: `oauth_plan_stage_b.py`. This module is the only approved real
route. The REAL-01 offline Codex seam above stays unchanged and can never be admitted.

### Route

The route is the official Sign in with ChatGPT plan-usage flow for a locally run personal app:

- The user's OAuth access token is sent as a bearer to `POST https://api.openai.com/v1/responses`.
- The model is pinned to `gpt-6.1-sol` and is used only if the account catalogue
  `GET /v1/models` lists it.
- There is no API key, no ChatGPT `backend-api` endpoint, no purchased credits and no fallback
  provider or model.
- The pinned Hermes agent is built with `provider=custom`, `api_mode=codex_responses` and
  `base_url=https://api.openai.com/v1`.

### Child phases

Each phase runs in one pinned Hermes v0.21.3 child with a sterile home and stripped environment.
The parent never reads a token.

- `login` (attended): runs the official flow. It sends `client_id=dynamic_agent_client` with an
  `agent_name_hint` and a persisted `ext_agent_host_id` (`urn:uuid:`), or the saved issued
  `client_id` on later sign-ins. It uses PKCE S256, state, nonce and the `resource` parameter,
  with the scopes `openid profile email offline_access resource.invoke
  chatgpt.tokens.use.direct`. The callback goes to a loopback listener at
  `http://127.0.0.1:<port>/auth/callback`; this is the flow's callback listener, not an OAuth
  server. The user consents in their own browser. The child then exchanges the code at
  `https://auth.openai.com/api/accounts/oauth/token` and validates the ID token against the
  published JWKS (issuer, audience = issued client id, expiry, nonce) using PyJWT inside the pin
  venv; no repository dependency is added. Credentials are stored atomically in a user-scoped
  directory outside the repository, and the transport refuses any repository path.
- `preflight`: performs at most one counted pre-inference token refresh, then checks granted
  scopes and the access-token audience, issuer and client. It then runs the catalogue
  `GET /v1/models`, which is discovery and not entitlement proof.
- `dispatch`: builds `AIAgent(enabled_toolsets=[])` with every socket denied. A pre-send httpx
  hook re-checks the final post-SDK body. Exactly one POST then goes out under an
  `api.openai.com:443`-only socket allowlist, with SDK `max_retries=0`, `trust_env=False` and
  TLS verification on. There is no refresh, retry or fallback.

### R001 eligibility

`evaluate_preflight` requires all of the following:

- the pin;
- no `*API_KEY*` environment variable;
- only official control-plane calls (the catalogue, plus at most one refresh);
- the full scope set, including `chatgpt.tokens.use.direct`;
- the access-token audience, issuer and client binding;
- a fresh token;
- catalogue HTTP 200 with the exact slug listed;
- real mode;
- the operator's attestation
  `{purchased_credits_disabled: true, model_visible_in_chatgpt: true, source: OPERATOR_ATTESTATION}`.

Purchased-credit state has no API, so operator attestation is the only evidence for it. Any gap
gives `PLAN_USAGE_UNVERIFIED` and zero dispatch. The eligibility must be at most 15 minutes old
at dispatch.

### R002 final wire

The body keys must lie between `{input, instructions, model, store, stream}` and that set plus
`{include, prompt_cache_key, reasoning}`.

- `store=false` and `stream=true`.
- `input` is one `user` item; instructions go in `instructions`, never a system item.
- There are no `tools`, `tool_choice` or `parallel_tool_calls`.
- None of the preview-unsupported fields are sent: `background`, `conversation`,
  `max_output_tokens`, `max_tool_calls`, `metadata`, `moderation`, `multi_agent`, `prompt`,
  `prompt_cache_retention`, `safety_identifier`, `temperature`, `top_logprobs`, `top_p`,
  `truncation`, `user`, `previous_response_id`, `service_tier`.
- The instruction and input digests must be exact.

The Responses `input` (the model input) is at most 2,048 UTF-8 bytes. The instructions are a
fixed constant bound by their digest.

### R003 one attempt

A journal namespace admits one dispatch ever. `oauthplan-attempt.reserved` is created
exclusively before the child starts. Each outcome is handled as follows:

| Outcome | Result |
|---|---|
| Any 429, 5xx, timeout, crash, `response.failed`, tool item or invalid output | Consumes the attempt |
| Replay | Returns the stored terminal, never a witness |
| A different request on the same journal | `JOURNAL_ALREADY_CONSUMED` |
| Reservation without a terminal | `ATTEMPT_ALREADY_RESERVED` |

Control-plane calls (login, refresh, catalogue) are counted separately from the single
generation request.

### R004 provenance

Every classification fails closed:

- Non-`message`/`reasoning` items are `TOOL_CALL_ATTEMPT_INVALID`.
- Reasoning-only or multiple messages are `RESPONSE_SHAPE_INVALID`.
- Only `response.completed` is accepted.
- 401/403 is `PROVIDER_AUTH_OR_ENTITLEMENT_DENIED`, and `response.failed` (for example
  `subscription_sharing_usage_limit_exceeded`) is `PROVIDER_RESPONSE_FAILED`.
- The client stops at 16,384 output bytes or 45 s. These are client limits, not provider
  quotas. No provider output-token cap exists on this route, so `USAGE_CAP_EXCEEDED` does not
  apply here.
- The output must be strict JSON.

A result is `REAL_ORIGIN_VERIFIED` / `OAUTH_AUTHENTICATED_HTTP` only when all of these hold:
real mode, witnessed eligibility, one answered generation request, a provider response id, the
exact server model slug and provider-reported usage. A dated snapshot slug, missing usage or a
missing id is `REAL_TRANSPORT_OBSERVED_MODEL_OR_USAGE_UNVERIFIED`. Every record carries:

- `PROVIDER_REPORTED_NOT_CRYPTOGRAPHIC`;
- `INCLUDED_PLAN_USAGE_NO_DOLLAR_AMOUNT_INFERRED`, with no dollar amount;
- execution authority `NONE`.

Response and request ids are stored hashed.

### R005 AUTO-01

`autonomous_feedback.verify_real_origin_evidence` admits only a live, non-replayed result
witnessed by `oauth_plan_stage_b`. `evaluate_once(real_origin_evidence=...)` then binds the exact
choice bytes, the menu digest, the cutoff and deadline, and the observed issue/finish window. It
runs the unchanged native EXEC-FEAS / Gate C mechanics and labels the receipt
`REAL_OAUTH_ORIGIN_BOUND`. The result is at best `ELIGIBLE_PREVIEW`
(`NON_EXECUTABLE_WITHOUT_SEPARATE_LIVE_AUTHORITY`), and `NO_TRADE` is valid. Offline REAL-01
records, mock-transport, replayed, relabelled or forged results still reject with
`REAL_ORIGIN_UNVERIFIED` before any store read. Legacy and offline-producer calls are unchanged.


## Historical blocked checkpoint (superseded by amended S10-HERMES-SEC-PROFILE-01)

The independent certificate and exact prompt/spec passed native pre-implementation gates on the frozen PR #250 base `f2b8916fe2bd377b0790278f4be5dad85568d367`. Karl requested execution of the certified WP on 2026-10-23. The sixteen-file draft implementation is incomplete and NOT_MERGE_READY; no full-suite, final independent review or acceptance CI PASS is claimed.

The shared profile guard rejected the earlier local shadow: it had **83 distributions**, while the certified Windows profile binds **68**. The 15 extras include pip, edge-tts, boto3/botocore and their dependencies. Creation timestamps coincide with the earlier predraft native probe. The earlier 67-row zero-match audit preceded that probe and does not attest its later changed environment. The original source/lock bytes and all five candidate target versions remained unchanged; installed inventory did not.

A fresh task-owned scratch install from the exact candidate lock restored the approved **68-distribution profile** (`75e3bcea7af741fe599594a744eeb043d494973f79a5291286e60b325a17e4a8`), with `uv sync --locked` and `uv pip check` both exit 0. A socket-denied native reproduction with supported `security.allow_lazy_installs: false` and a child-process audit guard kept that profile identical before/after. It observed **0 explicit-empty tools and 17 control tools**, not the certified 18; `text_to_speech` was absent. No production installation or account/provider operation occurred.

The smallest proposed correction is independent review of a narrowly amended, recertified prompt/spec: explicitly disable lazy installation in every sterile child home, prevent installer subprocess escape, compare inventory before/after probing, and freeze the genuinely observed sealed control toolset instead of asserting the historical 18. Do not add unreviewed optional dependencies or relax identity validation to preserve a count. The current certificate/prompt/spec bytes remain unchanged; no amendment is implemented under them. Linux evidence remains separately gated and unobserved.

D005 remains OPEN. Credentials/OAuth, host promotion, model/account endpoints, capital/orders and merge remain unauthorized. LIVE TRADING STATUS: DISABLED. USD 0; orders 0.


A second immutable-artifact blocker was observed before committing: repository `* text=auto` normalizes the supplied CRLF JSON. Certified working spec SHA256 `318b958031c69b6792336761f822b24534f61d9ae939f00e2a9275a33677917f` becomes staged LF SHA256 `13a37ece07fbd9f8141a6cce9ca404bf33c4ec44749ef272a1f1146b990d5ff1`; policy `df4bb5bdf20249614e1887a64c9d6d71e03834668be67ae765e837ec2af41ac7` becomes `eba64a49fa0d6215278b34e96725e195fb1549d143673117c992b6ae52935680`. Prompt and certificate bytes do not change. Staging was undone; no normalized artifact was committed, and no Git filter/plumbing or seventeenth .gitattributes edit was used. Reissue the amended prompt/spec/policy with LF raw bytes and an independent certificate covering those exact bytes. No PR, commit, push, full-suite or hosted acceptance run was performed after this hard stop; the implementation remains an uncommitted local checkpoint.


## S10-HERMES-SEC-PROFILE-01 amended implementation (2026-10-23)

Karl explicitly authorized resuming the same sixteen-file uncommitted checkpoint.
The newly independent Side21 certificate, prompt and spec pass the native guard and
IMPLEMENTATION_READY gate. Current normative policy SHA256 is
`eba64a49fa0d6215278b34e96725e195fb1549d143673117c992b6ae52935680`.
The previous certificate/hash and 18-tool criteria in the historical checkpoint
above are superseded; its 83-package drift and earlier audit remain historical facts.

The shared verifier reads the exact pin-owned interpreter's isolated metadata,
requires the complete approved inventory and immutable dependency inputs, and
rechecks after native children. All sterile configs disable lazy installs and
stripped environments set HERMES_DISABLE_LAZY_INSTALLS=1. Offline probe/fake-wire
and mock OAuth children deny process execution before Hermes imports. Future
separately authorized real OAuth retains its browser opener; no real login runs here.
Windows requires the exact seventeen observed default tools and zero explicit tools.
Linux's 64-distribution policy is a derived equality target, with native tool count
UNOBSERVED; installation, audit and native proof precede separate host promotion.
Owner-controlled immutable source is assumed; race-proof hostile-host attestation
is not claimed.

Mandatory profile digests bind StageBRequest, Real01Request, OAuthPlanRequest,
preflight eligibility, wire reports, origin/provenance records and their canonical
hashes. Legacy missing-profile evidence is ineligible without rewriting history.
ID-token/JWKS parsing uses a single sanitized ID_TOKEN_INVALID path, RS256 and
required claims, fresh options, a 64-KiB token limit, 1-MiB streamed JWKS limit,
at most 100 keys and one matching RSA signature key. Explicit null alg/use rejects;
absent optional members remain supported. PyJWT's historical no-published-fix
advisory caveat remains; bounded regressions do not establish a universal vendor fix.
Four-format Pillow smoke tests do not prove every optional image route safe.

Current Windows candidate: 68 installed distributions, 67 audited requirements
(editable Hermes excluded), dependency consistency exit 0 and post-probe audit exit
0 with zero known vulnerabilities. Full-suite and exact-head CI results remain the
PR's live evidence; no completion or merge readiness is inferred from these checks.
D005 OPEN; OAuth/credentials NOT AUTHORIZED; LIVE TRADING STATUS: DISABLED;
USD 0; orders 0. Production and retained host pin are untouched.


Security scan qualification: Semgrep 1.176.1 scanned all four changed source modules
with p/python and p/security-audit (200 applicable rules, zero scan errors). One
subprocess-injection alert at capture_offline_wire is a FALSE POSITIVE under the
explicit immutable owner-controlled pin assumption: verified pin-owned executable,
constant Python program, list argv with shell disabled, and untrusted scenario/model
bytes confined to stdin. R001 rejects out-of-pin/metacharacter executable paths before
launch; R002 denies subprocess/shell escapes; R003 denies mismatched wire launch.
No scanner exclusion, suppression or security risk acceptance was added. Independent
implementation review remains required. Gitleaks source scan found zero leaks;
whole working-tree scan reports 19 alerts, all on unchanged baseline lines, including
historical negative fixtures. Existing findings are not reported as a clean
whole-repository scan. No new finding line was introduced.


Final local validation: sealed Windows native focused suite25 passed without skips;
R001-R007 each pass as exact separate commands; adjacent95 and architecture51 pass.
After native construction, the matching68-distribution inventory and67-row audit
remain exact, audit exit0 with zero known vulnerabilities. The existing local Linux
image ran the complete repository suite offline with strict DuckDB, no installation:
14028 passed,15 skipped,125 warnings,exit0. Windows broad validation was interrupted
after the same pyarrow._dataset Application Control block reproduced on untouched
main; it is not PASS. The offline Linux repository suite is not Linux Hermes
installation/security-profile/control-count evidence. Actual final-head hosted CI,
posted evidence and independent Side21 review are governed by the live PR body;
merge remains Karl-only after required independent approval.


## Final tracked-tree CI blocker (supersedes local acceptance inference)

Required run39995853674 on c767f9850f5dd9d2612385355f829051637e255b fails
all four compatibility jobs,three tests per job,through the same historical IO
artifact guard. Its git ls-files check rejects the newly tracked profile JSON.
The local14028-pass broad snapshot and25-pass focused run preceded tracking that
new file; they do not establish committed-tree acceptance. This was a preventable
tracked-artifact discovery/validation-copy gap,not a CI environment excuse.
The historical guard path is outside the certified16; a minimal exact allowlist
addition requires independently recertifying17 paths and renewed owner authority.
The in-scope feedback source-snapshot assertion must account for the addition.
No forbidden guard edit or test skip occurred. PR251 is draft,not ready and not
merge-ready. D009 records the blocker. Native readiness still describes package
structure only; it cannot override required CI failure or authorize scope expansion.
Production,OAuth/credentials,trading and D005 boundaries remain unchanged.


## S10-HERMES-SEC-PROFILE-01 certified scope17 continuation (2026-10-23)

Karl explicitly authorized the independently certified17-path amendment on existing
draft PR251. New prompt SHA256:
`13ca60c7658bdee15754276b4fcd8b7440420d53c18f88f82efb40d1b0c8596f`;
spec:`288f3b098be859d2d9eae2918d2e0554c5d4df86c335e51e4ee5037bf77380bd`;
certificate:`a992de97ef0cb7dd3df8274f3e0faae13ae83403ac8db2a1926da9088c4b9862`.
Policy SHA256 remains
`eba64a49fa0d6215278b34e96725e195fb1549d143673117c992b6ae52935680`.
Native spec guard PASS and PROTECTED readiness IMPLEMENTATION_READY,scope17.

D009's missing-path authority is resolved by independent recertification. The exact
tracked-artifact allowlist adds only docs/hermes_runtime_security_profile.json;
JSON/Python shadow siblings remain forbidden. The existing in-scope historical
snapshot subtracts only those exact additions,and exercises both sibling negatives.
All four runtime source modules and the other three native test modules are
byte-identical to the preserved prior implementation. The three previously failing
historical guard/wrapper tests now pass on the complete actual tracked tree.
Historical scope16 CI failure is retained as failure,not reclassified as PASS.

D002/D009 acceptance is pending fresh full tracked-tree local validation,security
checks and one new exact-head full hosted CI. This is an implementation checkpoint,
not final independent acceptance. Linux Hermes promotion remains D004,separately
gated and UNOBSERVED; optional inactive routing C081 issue remains D008. No new
runtime/dependency/credential/host authority,no eighteenth path,skip or guard
weakening. D005 OPEN;LIVE TRADING STATUS:DISABLED;real capital USD0;orders0.
