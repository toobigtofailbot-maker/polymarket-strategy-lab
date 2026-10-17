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
