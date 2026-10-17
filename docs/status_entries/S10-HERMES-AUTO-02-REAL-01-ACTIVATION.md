# S10-HERMES-AUTO-02-REAL-01-ACTIVATION — one attended ChatGPT-plan OAuth Stage B decision

**Authority:** Karl's bounded authorization in the certified package, 2026-10-17, with ChatGPT OAuth only (no API key and no purchased credits).
**Executor:** Claude Code.
**Branch:** `claude/s10-hermes-auto02-real01-oauth-activation`.
**Frozen main:** `e6865aca7f996c355390d58d6fed121a74f206dd`.
**Predecessor:** PR #242, head `aefe5b17435c66d0080af6fef3da1740712a2c74`, merged at frozen main.

**Governance:** PROTECTED, risk 4.
**Independent certificate:** `draftability_certificate.json` (SHA-256 `ba420c2b…67b6`), committed unchanged and bound to `wp_prompt.txt` `95768470…f714` and `wp_spec.json` `350086d7…71fb`.
**Native readiness:** `IMPLEMENTATION_READY`, re-run by the executor before any edit.

**State:** IMPLEMENTED_LOCAL. The single attended OAuth attempt runs against this exact committed head. Its terminal (or proof of no call) is recorded only in the external evidence ZIP, so this fragment never changes after the run. Merge ready: NO (Karl merges manually after SIDE20).

## Scope

Exactly thirteen paths:

- One new Hermes child module, `oauth_plan_stage_b.py`.
- Additive admission in `autonomous_feedback.py` and AUTO-01 `autonomous_opportunity_cycle.py`.
- Three focused test files.
- The contract `docs/hermes_real_provider_stage_b_contract.md`, extended.
- This fragment.
- The certificate, prompt and spec.
- Exact literals plus hostile-sibling negatives in the two historical Hermes guards.

The architecture guard, the REAL-01 offline module and its tests, dependencies, CI and configuration are unchanged.

## Design

The route and checks follow the official Sign in with ChatGPT plan-usage documentation, checked 2026-10-17:

- **Sign-in:** dynamic registration, PKCE, loopback callback, JWKS ID-token validation.
- **Credentials:** stored in a user-scoped directory outside the repository.
- **Discovery:** the catalogue is read via `GET /v1/models`.
- **Inference:** exactly one `POST https://api.openai.com/v1/responses`, with `store=false` and `stream=true`. Unsupported preview fields, including `max_output_tokens`, are never sent.
- **Wire:** the native `AIAgent(enabled_toolsets=[])` builds the request offline, and a pre-send hook checks it.
- **Journal:** a single-use namespace, reserved before dispatch.
- **Origin:** only provider-reported id, exact model and usage give `REAL_ORIGIN_VERIFIED`, which remains not cryptographic.
- **Admission:** AUTO-01 admits only a witnessed result and yields at most a non-executable preview.

## Evidence

The external terminal ZIP for CURRENT SIDE20 records:

- the final SHA;
- test counts;
- the sanitized OAuth preflight;
- the single-attempt receipt or proof of no call;
- the skills ledger.

This fragment does not anticipate those results.

No API key, purchased credits, alternate provider, wallet, market or account call, order, capital, scheduler, VPS or deployment.
