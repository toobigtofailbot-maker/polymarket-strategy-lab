# S10-CC-CMD-01 — Control Center Protected Operator Command Contract

Status: S10-CC-CMD-01 implementation contract (PROTECTED, risk 4, exact 20-path L scope). The
package is `docs/wp_specs/S10-CC-CMD-01/`, which holds the independently certified `wp_prompt.txt`,
`wp_spec.json` and `draftability_certificate.json`. The stable record is
`docs/status_entries/S10-CC-CMD-01.md`. Merge NOT AUTHORIZED (Karl only).

This contract turns the read-only, auto-refreshing Control Center into a bounded
lifecycle-governance console. It is **default-off**. It adds exactly five canonical StrategyLifecycle
governance commands behind ephemeral local operator authentication. It adds no paper, execution
gateway, Gate C, LIVE-ORCH, Hermes/provider, product-network, account, order, capital or deployment
authority.

## 1. End state and permanent separations

```text
browser operator intent
→ ephemeral local operator authentication
→ POST /api/commands/execute
→ exact current lifecycle head + domain preconditions
→ conditional canonical lifecycle append
→ durable content-addressed lifecycle receipt/hash chain
→ sanitized HTTP command receipt
→ explicit HTTP query-family invalidation/reread
```

```text
browser state != canonical authority
command bearer token != trading credential
PortfolioAuthorityPolicy != Gate-C/live permit
strategy resume != order permission
policy activation != live activation
command receipt != second source of lifecycle truth
SSE delivery != command correctness
```

The canonical StrategyLifecycle record is the durable receipt and audit event. There is no command
database, queue, journal or retry worker. The HTTP response is only a sanitized projection of the
canonical result.

## 2. Operator authentication (default-off, in memory)

- `CockpitConfig.command_auth: CommandAuth | None = None` is appended after every existing field, so
  positional construction is unchanged. Its repr is `CommandAuth(operator_id='<id>')` and never shows
  digest, secret or token material. Only `bootstrap_command_auth` can construct a `CommandAuth`.
- Commands are enabled only by `--enable-commands --operator-id <id>` on a TTY.
  - The operator id must match `^op-[a-z0-9][a-z0-9_-]{0,30}$`.
  - The resulting `command_ref` must also pass the existing bounded non-secret opaque-reference
    validation. This rejects, for example, `op-secret1` or `op-bearer`.
  - The command secret is read once through `getpass.getpass`. It is never read from argv,
    environment, file, query, cookie or browser storage.
  - The secret must be 32..256 printable characters.
  - The process keeps only its SHA-256 digest. Comparison uses `hmac.compare_digest`.
  - The raw secret variable is deleted at the end of bootstrap.
  - `--operator-id` without `--enable-commands` is rejected.
  - Bootstrap failures print only a closed code: `OPERATOR_ID_INVALID`, `TTY_REQUIRED` or
    `SECRET_INVALID`.
  - Cockpit CLI errors never echo an argv value (unrecognized, ambiguous and invalid-value
    messages use a closed diagnostic; only exact safe bootstrap/port diagnostics are retained),
    so a mistyped secret is not printed back under either Python repr quote style.
- Frozen session contract: `SESSION_TTL_SECONDS = 900`, `MAX_ACTIVE_SESSIONS = 1`,
  `SESSION_TOKEN_BYTES = 32`, `MAX_FAILED_LOGINS = 5`.
  - The bearer token comes from stdlib `secrets.token_urlsafe(32)`: 43 URL-safe characters.
  - The raw token is returned once. The server stores only its SHA-256 digest.
  - A successful login replaces any prior session. Revoke ends the current session.
  - Expiry at `expires_at_ms` returns `SESSION_EXPIRED` once, then `AUTH_REQUIRED`.
  - A process restart forgets every session. There is no refresh endpoint.
- Failed-login lock: five cumulative failed secrets per process lock authentication until the process
  restarts (`AUTH_LOCKED`). The lock also ends any current session. There is no sleep or backoff
  loop. Malformed login bodies are `INVALID_COMMAND` and are not counted as guesses.
- The operator login is local-only Control Center authentication. It grants no Polymarket, account,
  wallet, order, Gate-C or live permission.

## 3. CORS / CSRF posture

- The existing loopback origins (`http://127.0.0.1:5173`, `http://localhost:5173`) remain the only CORS
  origins. Methods are exactly `GET`, `POST`. Headers are exactly `Content-Type`, `Authorization`.
- There are no wildcard origins, no credentialed CORS, no cookies and no ambient browser auth. Every
  mutation requires an explicit `Authorization: Bearer <token>` header, so CMD-01 adds no cookie-CSRF
  surface and no CSRF token subsystem.
- Production private ingress remains S10-CC-PROD-01.

## 4. Exact API surface (31 `/api` routes in total)

| Route | Purpose |
|---|---|
| `GET /api/commands/status` | Safe non-secret status. Any query → `INVALID_COMMAND`. |
| `POST /api/commands/session` | Exact body `{"secret": "<string>"}` → `operator_id`, `session_token`, `expires_at_ms`. |
| `POST /api/commands/session/revoke` | Bearer required, empty body → `{"schema_version":"1.0.0","status":"SESSION_REVOKED","active_session":false}`. |
| `POST /api/commands/execute` | Bearer required, exact command body → sanitized receipt. |

Status keys are exactly:
- `read_only: false`
- `commands_enabled`
- `auth_mode: "EPHEMERAL_BEARER_SESSION"`
- `session_ttl_seconds: 900`
- `active_session`
- `supported_commands` (the exact five kinds)
- `no_product_network`, `no_account_access`, `no_order_authority`, `no_gate_c_authority` and
  `no_live_authority`, all `true`

Command POST bodies must use the `application/json` media type, are bounded to 4096 bytes and take no
query. Bodies are decoded with strict JSON: duplicate keys, floats, NaN and Infinity are rejected.

Precedence:
1. disabled → `COMMANDS_DISABLED`;
2. bearer authentication (`AUTH_REQUIRED` / `SESSION_EXPIRED`);
3. body transport;
4. request shape (`INVALID_COMMAND`) and then `INVALID_CONFIRMATION`.

There is no automatic server-side retry of any step. The execute route authenticates the bearer
again after the body is read, so a revoke, replacement login or lock that lands during the read
always wins; nothing after that check awaits.

## 5. Command identity and time

- The browser supplies a safe integer `issued_at_ms = Date.now()`.
- The backend rejects booleans, non-integers, negatives and values above `2^53 - 1`.
- The time must fall inside the authenticated session window `[started_at_ms, expires_at_ms)` and
  may be at most 5 seconds ahead of the server clock.
- `created_time_ns = issued_at_ms * 1_000_000`, with an overflow check against the canonical time
  domain.
- `command_digest = sha256(canonical compact JSON {"command": <normalized request>, "operator_id": <id>})`.
- `command_ref = cccmd:<operator_id>:sha256:<64hex>`.
- There is no caller-provided idempotency key.
- The exact same authenticated request always reconstructs the exact same lifecycle record. Every
  state-derived value is carried explicitly in the request: `previous_health_state` and
  `previous_active_policy_id`.

## 6. Execute request shapes

Common exact fields: `command_kind`, `expected_lifecycle_store_head_entry_hash` (64 lowercase hex or
`null` for the empty store), `issued_at_ms` and `confirmation_phrase`. Unknown, extra or missing keys
fail closed.

| Kind | Target fields | Confirmation | Canonical record |
|---|---|---|---|
| `STRATEGY_PAUSE` | `strategy_version_id` | `CONFIRM-PAUSE` | `StrategyRestrictionReceipt` APPLY `PAUSE_NEW_EXPOSURE`, key `cc.pause.<first24(command_digest)>`, cap null |
| `STRATEGY_RESUME` | `strategy_version_id`, `restriction_key` | `CONFIRM-RESUME` | `StrategyRestrictionReceipt` CLEAR `PAUSE_NEW_EXPOSURE`, cap null |
| `STRATEGY_QUARANTINE` | `strategy_version_id`, `previous_health_state` | `CONFIRM-QUARANTINE` | `StrategyHealthReceipt` → `QUARANTINED` |
| `POLICY_ACTIVATE` | `policy_id`, `previous_active_policy_id` (string or explicit null) | `CONFIRM-ACTIVATE-POLICY` | `PortfolioPolicyReceipt` ACTIVATE |
| `POLICY_REVOKE` | `policy_id` | `CONFIRM-REVOKE-POLICY` | `PortfolioPolicyReceipt` REVOKE (previous = policy) |

Every record is built through the existing public builders:
- `decision_ref` / `human_authorization_ref` = `command_ref`;
- `evidence_refs = ()`;
- `created_time_ns` = the derived command time.

## 7. Execution order — exact retry before mutable preconditions

```text
derive command_ref/digest
→ build the exact canonical candidate from request fields + fixed command semantics only
→ preview_strategy_lifecycle_record(path, record, expected_head)
   → IDEMPOTENT_REPLAY: success immediately; current-state preconditions are NOT re-run
   → STALE_HEAD: STALE_STATE (zero writes)
   → REJECTED: sanitized canonical failure
   → PREVIEW_READY: continue
→ command-specific pre/postconditions on the preview before/candidate snapshots
→ conditional_append_strategy_lifecycle_record(path, same record, same expected head)
```

Command-specific preconditions apply to new `PREVIEW_READY` mutations only:

- **Pause:**
  - the target exists;
  - its health is not `RETIRED`;
  - no active `PAUSE_NEW_EXPOSURE` restriction exists (pauses never stack).
- **Resume:**
  - the target exists;
  - its health is neither `QUARANTINED` nor `RETIRED`;
  - the exact requested restriction is active, has kind exactly `PAUSE_NEW_EXPOSURE` and has a null
    cap. `PAPER_ONLY` and `ACTIVE_BUDGET_CAP` are never cleared.
  - One `evaluate_portfolio_capacity(candidate_snapshot, created_time_ns)`:
    - strategy-local universe = the union of every `strategy_result.reason_codes`;
    - global reasons = top-level `reason_codes` − strategy-local universe.
  - Resume requires no global reasons. If the target holds an active positive allocation, its own
    result must also be `PORTFOLIO_CAPACITY_VALID`.
  - Unrelated strategy-local blockers therefore never deadlock a safe resume.
  - Top-level reasons that are not strategy-local still block, by the frozen formula. These include
    pool/capital/active-strategy overflow, and also `POLICY_NOT_ACTIVE`, `POLICY_NOT_EFFECTIVE` and
    `POLICY_EXPIRED`.
- **Quarantine:**
  - the target exists;
  - its current health equals the requested `previous_health_state` (any builder-accepted state,
    including `NEW`);
  - that state is neither `QUARANTINED` nor `RETIRED`.
  - There is no Gate-C, gateway or order side effect.
- **Policy activate:**
  - the target policy exists in the verified catalogue;
  - the current `active_policy_id` equals the requested `previous_active_policy_id`;
  - the target is not already active;
  - `effective_from_ns <= command time`;
  - the command time is before `expires_at_ns` when the policy has one.
  - One capacity evaluation on the candidate. Activation is rejected when any global reason exists,
    or when any strategy-local reason other than `HEALTH_BLOCKS_ACTIVE_RISK` /
    `RESTRICTION_BLOCKS_ACTIVE_RISK` exists. So `ALLOCATION_POLICY_MISMATCH`, `ALLOCATION_INVALID`,
    `PER_STRATEGY_LIMIT_EXCEEDED` and `ACTIVE_BUDGET_CAP_EXCEEDED` all block.
  - Activation never creates or edits a policy and never migrates or edits an allocation.
- **Policy revoke:** the requested policy is exactly the current active policy.

## 8. Store primitive (`src/strategy_lifecycle/store.py`)

The public `append_strategy_lifecycle_record(path, record)` is unchanged. There is no schema, trigger,
application-id or migration change. Two narrow helpers are added:

- `preview_strategy_lifecycle_record(path, record, expected_head_entry_hash)`:
  - read-only verified load;
  - closed states `PREVIEW_READY | IDEMPOTENT_REPLAY | STALE_HEAD | REJECTED`;
  - an exact byte-identical existing record → `IDEMPOTENT_REPLAY` before the head comparison;
  - the same record ID with a different payload → `IDENTITY_CONFLICT`;
  - otherwise the loaded head must equal the expected head;
  - the candidate replays on a copied state, under the existing limits;
  - `PREVIEW_READY` returns the verified pre-append snapshot/head and the candidate snapshot, whose
    head is the exact hash a commit would produce;
  - zero writes.
- `conditional_append_strategy_lifecycle_record(path, record, expected_head_entry_hash)`, inside
  `BEGIN IMMEDIATE`:
  1. full verification;
  2. exact duplicate → `IDEMPOTENT_REPLAY` (rollback);
  3. stale head → `STALE_HEAD` (rollback, zero writes);
  4. candidate replay and limits;
  5. one hash-chained row;
  6. reload/verify;
  7. commit → `COMMITTED` with the committed record id and resulting head.

## 9. Idempotent retry and stale state

- The same operator and the exact same request produce the same `command_ref` and the same lifecycle
  record ID.
- A lost-response retry of a committed request returns `IDEMPOTENT_REPLAY` with no second row, even
  after the head has advanced. This holds for all five commands, including after a quarantine or
  activation has changed the very state its precondition checked.
- A stale expected head with no exact existing record returns `STALE_STATE` with zero writes.

## 10. Sanitized receipt and closed failures

The success receipt has exactly these keys:
- `schema_version: "1.0.0"`
- `status` (`COMMITTED` | `IDEMPOTENT_REPLAY`)
- `command_ref`, `command_kind`, `operator_id`
- `canonical_record_kind`, `canonical_record_id`
- `lifecycle_store_head_entry_hash`
- `issued_at_ms`
- the five `no_*` authority flags, all `true`

It carries no path, raw body, secret, bearer token, SQL, exception, credential or private account data.

Failures are `{"error": {"code": <code>}}` with HTTP status:

| Code | HTTP status |
|---|---|
| `COMMANDS_DISABLED` | 403 |
| `AUTH_REQUIRED` | 401 |
| `AUTH_FAILED` | 401 |
| `AUTH_LOCKED` | 403 |
| `SESSION_EXPIRED` | 401 |
| `INVALID_COMMAND` | 400 |
| `INVALID_CONFIRMATION` | 400 |
| `STALE_STATE` | 409 |
| `COMMAND_PRECONDITION_FAILED` | 409 |
| `SOURCE_UNAVAILABLE` | 503 |
| `INTERNAL_ERROR` | 500 |

`COMMAND_PRECONDITION_FAILED` may add `canonical_error_code` from the closed StrategyLifecycle
vocabulary only (for example `HEALTH_TRANSITION_INVALID`). The response never contains raw exception
text.

## 11. Frontend

- `styles.css` is unchanged. The command surface reuses the existing Button, StatusPill, DetailList,
  notice and state classes.
- One shell-level `CommandSessionProvider` holds the raw bearer token in React state only. It is the
  only caller of the command transport. There is no TanStack cache entry, browser storage, cookie or
  URL token.
- The secret input lives in local `UnlockCommands` state and is cleared when the login attempt
  completes.
- Sidebar posture: `Commands: Disabled`, `Commands: Locked` (shows the secret input and **Unlock**) or
  `Commands: Unlocked · <operator-id>` (shows **Lock commands**, which revokes).
- `api.ts`:
  - strict DTOs;
  - the strictly validated global `["cc","commands","status"]` query;
  - `parseOpsPolicies`, a runtime-validated catalogue (missing or malformed → no activation choice);
  - `newCommandRequest`, the one place `issued_at_ms` is minted; the result is frozen;
  - one same-origin `postCommand` transport (`credentials: "omit"`, `cache: "no-store"`, no retry):
    `COMMAND_MUTATION_RETRY = false`.
- Each action reads `GET /api/ops/portfolio` fresh (`fetchQuery`, `staleTime: 0`) and binds its
  expected head from that response. Strategy actions also re-read their strategy detail at review time,
  so the confirmed target fields (`previous_health_state`, the exact pause key) and the displayed
  current state are fresh. SSE state and the Strategy Detail response are never the command
  head.
- The confirmation surface shows the target identity and current canonical state. The exact phrase
  must be typed before submit.
- Strategy detail (only when unlocked):
  - **Pause new exposure**;
  - **Resume · clear pause `<key>`**, only for an exact visible `PAUSE_NEW_EXPOSURE` restriction with
    no cap;
  - **Quarantine**.
- OPS (only when unlocked):
  - **Activate selected policy**, chosen only from the verified `policies` catalogue (no free-form
    id);
  - **Revoke active policy**.
- Every outcome re-reads `familyKey("strategies")` and `familyKey("ops")` over HTTP. Correctness never
  waits for SSE.
- The last sanitized receipt of the current session (kind, status, canonical record id) stays visible
  in the command sections after the re-read. It is cleared when the session ends.
  Unlock/lock advance a memory-only epoch. Late login or command responses from a previous epoch
  cannot unlock, overwrite the receipt or invalidate a newer session. A success receipt must match
  the authenticated session operator, exact command kind/time, command-specific canonical kind/id,
  complete content-addressed reference and non-null 64-hex committed store head; malformed receipts
  remain ambiguous outcomes and never become displayed success.
- Stale state shows a safe message and requires a new review and confirmation.
- After an ambiguous transport outcome (`NETWORK_UNAVAILABLE`, `INTERNAL_ERROR`,
  `MALFORMED_RESPONSE`), only **Retry same request** is offered. It re-sends the exact same frozen
  request on the same session.
- There is no Arm, Halt, Trade, Cancel, Reconcile, Run-Hermes, policy-editor or allocation-editor
  control.
- Storybook is unchanged and compatibility-only. Stories do not mock `/api/commands/status`, so the
  closed MSW catch-all leaves commands `Disabled`, with no mutation affordance, no secret and no token.

## 12. Non-authority and deferred command classes

There is no paper mutation, execution gateway, Gate C / LIVE-ORCH permit/arm/halt/admission/reconcile,
Hermes/provider invocation, product network, authenticated account read, order create/cancel/sign/
submit, capital, scheduler/daemon/worker, dependency/lock/workflow change, deployment or merge.
Capital/orders: USD 0 / 0.

The following command classes are explicitly deferred. Before S10-CC-PROD-01 implementation, Side18
must decide whether they need a narrow S10-CC-CMD-02 extension or stay CLI/backend-only. CMD-01 neither
authorizes nor silently requires CMD-02:
- paper pause/resume/kill;
- gateway/runtime disable;
- incident acknowledgement;
- Hermes reassessment.

No command package may add free-form order entry around strategy, portfolio, risk, Gate C or
execution-gateway authority.

## 13. Operational notes

- Command auth is local-only and ephemeral. Restarting the cockpit always relocks it.
- PROD/private deployment is not complete: production private ingress, TLS, Tailscale, monitoring and
  deployment remain S10-CC-PROD-01.
