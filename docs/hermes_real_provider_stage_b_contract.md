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
