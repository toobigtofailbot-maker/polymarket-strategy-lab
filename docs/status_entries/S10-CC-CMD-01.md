# S10-CC-CMD-01 Status Entry

## Identity

- WP ID: S10-CC-CMD-01
- Title: Protected Operator Commands
- Package class / size / risk: PROTECTED_CONTROL_CENTER_LIFECYCLE_GOVERNANCE_COMMANDS / L / 4
- Governance track: PROTECTED; readiness basis INDEPENDENT_CERTIFICATE
- Certified package (committed byte-identical):
  - `wp_prompt.txt` sha256 `0a1ee824b76de93194e27dbfee6de1be6cf1241e98d1c604afccd3755f330b36`
  - `wp_spec.json` sha256 `b8ad0d75783c2d648d5dd90885d430a951581854faf96a4882230e509f2b3c62`
  - `draftability_certificate.json` sha256 `92e9aeab10eacd31d30b4fd856bb9c2845c606905cb692c7e2fb68322f7d7dca`
    (reviewer-owned; never created, edited or recertified by the implementer)
- Implementation authority: an explicit Side17 owner-level authorization of the exact certified REV B
  bytes and the exact 20-path scope, under Karl's delegated project authority. It is not merge, risk,
  capital, deployment or trading authority.
- Branch: claude/s10-cc-cmd-01-protected-operator-commands
- Frozen base: a78809ddb62cf143ac85ee297e87f961aa9b61f9
- Predecessor: PR #227 / S10-CC-STREAM-01 (head f344979f8f620519175defe627a5829b569b665d), merged at
  the base
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Ready for review: NO until all final evidence passes (live value in the PR body)
- Merge authorized: NO (Karl only; review owner Side17)
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Capability (default-off protected lifecycle-governance commands)

- Exactly five commands, each mapped to one existing canonical StrategyLifecycle record:
  - `STRATEGY_PAUSE`: APPLY `PAUSE_NEW_EXPOSURE` restriction;
  - `STRATEGY_RESUME`: CLEAR of one exact `PAUSE_NEW_EXPOSURE` restriction;
  - `STRATEGY_QUARANTINE`: health receipt to `QUARANTINED`;
  - `POLICY_ACTIVATE`: ACTIVATE of an existing effective, unexpired policy;
  - `POLICY_REVOKE`: REVOKE of the exact active policy.
- The lifecycle record is the durable receipt and audit event. There is no command database or queue.
- New module `src/operator_cockpit_commands.py`. It imports only stdlib `dataclasses`, `getpass`,
  `hashlib`, `hmac`, `re`, `secrets`, `sys`, `time`, `pathlib` and `typing`, plus the public
  StrategyLifecycle builders, models and evaluator and the two new store helpers. It owns:
  - in-memory operator auth: TTY `getpass` bootstrap, SHA-256 secret digest, at most one 900 s bearer
    session stored as a digest, and a five-failure process lock;
  - strict request normalization and the confirmation phrases;
  - deterministic `cccmd:<operator>:sha256:<digest>` identity;
  - candidate building, preview-based preconditions (including the target-plus-global capacity
    classification), conditional append, and the sanitized receipt/closed errors.
- `src/strategy_lifecycle/store.py` adds `preview_strategy_lifecycle_record` (read-only) and
  `conditional_append_strategy_lifecycle_record` (`BEGIN IMMEDIATE`). Both resolve an exact
  byte-identical existing record as `IDEMPOTENT_REPLAY` before the expected-head comparison. A stale
  head writes nothing. The public `append_strategy_lifecycle_record` and the schema are unchanged.
- `src/operator_cockpit.py`:
  - `CockpitConfig.command_auth` (appended, default `None`, safe repr);
  - CORS methods/headers become exactly `GET, POST` / `Content-Type, Authorization` (origins
    unchanged);
  - four routes `GET /api/commands/status`, `POST /api/commands/session`,
    `POST /api/commands/session/revoke`, `POST /api/commands/execute` (31 `/api` routes in total);
  - bounded JSON command bodies;
  - the `--enable-commands` / `--operator-id` CLI;
  - CLI errors never echo an argv value;
  - the execute route re-authenticates after the body read, so a concurrent revoke, login or lock wins.
- `src/operator_cockpit_ops.py`: the read-only `/api/ops/portfolio` projection adds `policies` (every
  verified policy in append order). `active_policy`, capacity, reservations and the non-authority flags
  are unchanged. No mutation logic lives there.
- Frontend:
  - `api.ts` adds strict command DTOs, the strict `["cc","commands","status"]` query,
    `parseOpsPolicies`, the frozen `newCommandRequest` and one no-retry `postCommand` transport;
  - `app.tsx` adds the shell `CommandSessionProvider` (memory-only token), the sidebar posture and
    unlock, the fresh-OPS-head confirmation flow, and Strategy detail and OPS policy controls;
  - `styles.css` and Storybook are unchanged.
- Contract: `docs/control_center_command_contract.md`.

## Historical Compatibility Edits (narrow)

- `tests/test_operator_cockpit.py`: the exact `/api` route set grows from 27 to 31 by the four command
  routes only.
- `tests/test_operator_cockpit_research.py`: both route counts change 27 → 31. The global POST ban
  becomes: app.tsx has none, and api.ts has exactly the one command transport POST. The
  research/Hermes/Alpha views stay mutation-free: the only command reference in the research vertical
  is the single Strategy detail mount, and the Hermes and Alpha sections reference no command
  surface. The `>Pause<`-style label bans are unchanged.
- `tests/test_operator_cockpit_ops.py`:
  - the route count changes 27 → 31;
  - `policies` joins the exact top-level key set, and a new catalogue test is added;
  - the global POST ban narrows the same way;
  - the OPS section may only mount `<PolicyCommands portfolio={data} />`;
  - the Arm/Halt/Cancel/Trade/Reconcile/Revoke label bans are unchanged.
- `tests/test_operator_cockpit_stream.py`:
  - the `CockpitConfig` field list adds `command_auth`;
  - the route count changes 27 → 31;
  - the decorator guard allows exactly the three command POST routes;
  - the frontend no-POST guard narrows to the central command transport. The stream section and
    controller stay GET/EventSource-only and command-free.
- `tests/test_architecture_boundaries.py`: one exact `src/operator_cockpit_commands.py` allowlist
  entry with PROTECTED/risk-4 lifecycle-command wording (no wildcard).

## Exact Scope (20 paths)

- docs/control_center_command_contract.md, docs/project_status.md, docs/repo_truth_index.md,
  docs/status_entries/S10-CC-CMD-01.md
- docs/wp_specs/S10-CC-CMD-01/{wp_prompt.txt, wp_spec.json, draftability_certificate.json}
- src/operator_cockpit.py, src/operator_cockpit_commands.py, src/strategy_lifecycle/store.py,
  src/operator_cockpit_ops.py
- src/operator_cockpit_frontend/src/{api.ts, app.tsx}
- tests/strategy_lifecycle/test_strategy_lifecycle.py, tests/test_operator_cockpit_commands.py,
  tests/test_operator_cockpit.py, tests/test_operator_cockpit_research.py,
  tests/test_operator_cockpit_ops.py, tests/test_operator_cockpit_stream.py,
  tests/test_architecture_boundaries.py

## Authority / Non-Authority Posture

- Boundary groups (`docs/ai/codex/PROTECTED_PATHS.md`):
  - credentials/secrets: crossed only for the local, ephemeral, in-memory Control Center operator
    secret (TTY getpass, digest only; synthetic sentinels in tests). No trading, API, wallet or
    private-key credential.
  - Not crossed: authenticated clients; wallet/account behavior; order placement/cancel; execution
    gateway; paper engine; scheduler/bot loop; runtime/daemon; dashboard/deployment; dependency/lock
    changes; external code copying; generated artifacts.
- StrategyLifecycle writes go only through the existing builders and the conditional store primitive.
  The exact five records exist and nothing more: no policy or allocation creation, editing or
  migration, and no `PAPER_ONLY` / `ACTIVE_BUDGET_CAP` browser mutation.
- Paper, gateway, Gate C, LIVE-ORCH, Hermes, alpha and data-layer sources: unchanged; mutations 0.
- Product network 0; account reads 0; Hermes/provider calls 0; orders/signatures 0; capital USD 0.
  Live: DISABLED.
- No dependency, lockfile, workflow, styles or Storybook change.

## Deferred Command Classes

Side17 must decide, before S10-CC-PROD-01 implementation, whether these need a narrow S10-CC-CMD-02 or
stay CLI/backend-only:
- paper pause/resume/kill;
- gateway/runtime disable;
- incident acknowledgement;
- Hermes reassessment.

CMD-01 neither authorizes nor silently requires CMD-02.

## Successor Boundary

After Side17 review and Karl merge, the next separately gated package is S10-CC-PROD-01 (Private
Production Control Center). CMD-01 does not claim PROD/private deployment is complete.

## Validation

Validation results are recorded in the PR body:
- focused command tests (C01-C16) and lifecycle store tests;
- cockpit / research / OPS / STREAM / architecture compatibility tests;
- Control Center frontend `npm ci`, typecheck, build and unchanged Storybook build, plus `npm audit`;
- readiness `--check-diff` with the certificate, and the exact 20/20 scope;
- forbidden-family diff proof;
- security and generated-artifact checks;
- one authoritative local full suite;
- the independent exact-head implementation review;
- the final exact-head hosted matrix.
