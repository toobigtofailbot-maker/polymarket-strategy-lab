# S10-LIVE-CANARY-UA-01 Status Entry

## Identity

- WP ID: S10-LIVE-CANARY-UA-01
- Title: Public Polymarket User-Agent Transport Repair
- Triggered by: S10-LIVE-CANARY-AUTH-01 continuation on 2026-10-06 (verified from Windows and from
  the execution host)
- Package class / size / risk: PUBLIC_POLYMARKET_TRANSPORT_COMPATIBILITY_REPAIR / M / 3
- Governance track: RUNTIME; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-live-canary-ua-01-public-user-agent
- Frozen base: f9a0bae6a69d008862e6466f1fe532bc9416de5d (PR #220 merge)
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- MERGE AUTHORITY: KARL ONLY
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Verified Trigger

- The merged public transports set no explicit User-Agent, so urllib sends its implicit
  `Python-urllib/3.x` value.
- Gamma `/markets/<id>`: HTTP 403 through the merged request; HTTP 200 for the same request with an
  explicit User-Agent.
- CLOB `/book?token_id=<id>`: HTTP 403 through the merged request; reachable with an explicit
  User-Agent.
- `https://polymarket.com/api/geoblock`: HTTP 403 through the merged request.
- Effect: `fetch_public_venue_snapshot(..., opener=None)` reports Gamma and CLOB source state
  UNAVAILABLE, so no JIT execution intent can be built, and LIVE-ORCH preflight/canary would block.
- Same compatibility class as S10-DEPLOY-EXEC-01R2 / PR #217.

## Repair

- Fixed User-Agent: `wp169-public-market-truth/1.0` (the already-established project value).
- `src/execution_feasibility/public_market.py` `public_get`: request headers are exactly
  `Accept: application/json` and `User-Agent: wp169-public-market-truth/1.0`.
- `src/execution_gateway/gate_c.py` `query_geoblock`: request headers are exactly
  `Accept: application/json` and `User-Agent: wp169-public-market-truth/1.0`.
- No caller header argument and no environment/config override.
- Unchanged: endpoints and host allowlist, GET/HTTPS guards, path/query shape, empty ProxyHandler,
  redirect rejection, 5-second timeouts, Gamma/CLOB byte caps, geoblock 64 KiB read cap, exactly two
  public requests per acquisition, non-200 handling, source-state/error classification, parsing,
  proof validation, no retry/backoff/fallback, no credentials/cookies/authorization header.

## Offline Regression Evidence

- `test_s10_live_canary_ua_01_public_venue_requests_send_fixed_user_agent`: both Gamma and CLOB
  requests carry exactly the fixed Accept + User-Agent; GET, exact URLs, timeout 5; no
  Authorization/Cookie.
- `test_s10_live_canary_ua_01_no_implicit_or_overridable_headers`: the pre-repair request shape
  yields `Python-urllib/...`; the repaired requests never do; no header parameter exists; environment
  variables cannot inject or override headers.
- `test_s10_live_canary_ua_01_geoblock_request_sends_fixed_user_agent`: fixed URL, GET, timeout 5,
  fixed Accept + User-Agent, read cap `64 * 1024`, valid `blocked=false` proof.
- `test_s10_live_canary_ua_01_geoblock_has_no_implicit_or_overridable_headers`: implicit-UA negative
  control, fixed `(url, now_ns)` signature, foreign URL rejected `ACCESS_PROOF_INVALID`, no
  environment injection, `blocked=true` still parsed.
- `test_r016_two_fixed_host_get_requests_only`: its exact header-set assertion is updated from
  `{"accept"}` to `{"accept", "user-agent"}`; every other assertion is unchanged.
- Negative control: with the two source files restored to the frozen base, all five tests above fail;
  with the repair they pass.
- No test contacts the network.

## Validation

- Focused execution-feasibility, gate-c and live-orch suites, RUNTIME readiness `--check-diff`,
  hygiene, security checks, the local full suite and the final exact-head hosted CI are recorded in
  the PR body.
- No runtime Polymarket success is claimed until post-merge deployment and runtime verification.

## Exact Scope (7 paths)

- docs/status_entries/S10-LIVE-CANARY-UA-01.md
- docs/wp_specs/S10-LIVE-CANARY-UA-01/wp_prompt.txt
- docs/wp_specs/S10-LIVE-CANARY-UA-01/wp_spec.json
- src/execution_feasibility/public_market.py
- src/execution_gateway/gate_c.py
- tests/execution_feasibility/test_execution_feasibility.py
- tests/execution_gateway/test_gate_c.py

## Authority / Non-Authority Posture

- Hermes invocations: 0 (directional research and strategy assessment both remain unconsumed)
- Deployment during this WP: NO
- Credentials / authenticated Polymarket account access: NO
- Signing / orders: 0
- Capital: USD 0
- Live: DISABLED
- Live canary: SUSPENDED

## Successor

- After Karl merges: record the merge SHA; do not resume canary packages bound to f9a0bae.
- Side16 issues a SHA-only canary rebind/continuation package; deploy and bind the new release and
  require strict `EXECUTION_HOST_CURRENT`; run a fresh public Gamma/CLOB + geoblock smoke on the
  execution host; only then resume the directional-Hermes -> lifecycle/Hermes-assessment ->
  JIT Gate-C -> parent-preflight flow.
