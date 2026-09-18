# Controlled Hermes Research Runtime Core Contract (WP175H / S10-HERMES-01)

Package class: `CONTROLLED_EXTERNAL_HERMES_RESEARCH_RUNTIME_CORE`.

This is the canonical contract for the first repo-owned, dormant-by-default,
deterministic control plane around one bounded, one-shot, web-only EXTERNAL Hermes
research session. It is a narrow reusable research primitive. It is NOT the Alpha
Factory and it holds no trading, paper, execution, live, credential, scheduler, or
merge authority.

- CODE COMPLETE: YES
- RUNTIME ACTIVATED: NO
- Real provider/model call count: 0
- The first real provider-backed / public-web run is separately gated as
  **S10-GATE-H1** (Controlled Public Research Pilot); if it succeeds,
  **S10-ALPHA-01** (Multi-Lane Alpha Factory Core) follows. Both are NOT STARTED.

## 1. Pinned external contract

- External runtime: `NousResearch/hermes-agent`.
- Required version: **Hermes Agent v0.21.3**, release tag **v2026.9.14**, release
  commit `345cd2b`, release date 2026-09-14. Never `main`, an unpinned rolling
  tag, or `latest`.
- `REAL_HERMES_BINARY_NOT_PRESENT` on the build machine is an activation
  prerequisite, not a code blocker. Tests use a fake executable and make zero
  paid/provider calls.
- Frozen one-shot command shape (argv only, never a shell string):

  ```
  hermes chat --oneshot --provider <label> --model <label> --toolsets web
    --ignore-user-config --ignore-rules --safe-mode --max-turns <n>
    --format stream-json --input-file <bare-name>
  ```

- A real external run is invalid unless the reported version matches exactly.

## 2. Tool isolation

The only permitted built-in toolset is exactly `web`, which resolves to
`web_search` and `web_extract`. Forbidden tool families include terminal, file,
browser, code_execution, delegation, memory, session_search, cronjob, messaging,
Home Assistant, project, MCP servers, plugins, shell hooks, arbitrary skills, X
authenticated tooling, and any trading/account/wallet integration. The composite
`safe` toolset is not used. The policy is non-broadenable: constructing a policy
that enables any forbidden control fails closed.

## 3. Filesystem, credential, and prompt isolation

- The external backend runs from a fresh empty temporary working directory created
  by `mkdtemp`; it never mounts the repository, a `local_data` path, or a user home
  path, and it deletes the temporary directory on teardown.
- Project code never reads, stores, injects, logs, transforms, validates, or echoes
  a provider secret or any trading credential. Provider/model labels are non-secret
  audit strings only; this package does not select or activate a provider.
- The prompt envelope is compact and deterministic: one permanent system
  instruction plus the validated request. It never loads the repository, AGENTS.md,
  full project history, project memory, or the Alpha Factory database.

## 4. Request / policy / output / receipt

- **Request** (`HermesResearchRunRequest`): immutable, content-addressed over
  canonical public fields; rejects unknown fields, binary floats where numeric
  canonicality matters, over-bound values, path traversal/absolute paths, embedded
  secrets, and authority-escalation content, without echoing rejected content.
- **Policy** (`HermesInvocationPolicy`): frozen constants (`allowed_toolsets =
  ("web",)`, ignore-user-config, ignore-rules, safe-mode, one-shot, stream-json,
  shell false, ephemeral empty cwd, repo mount false, no mcp/plugins/cron/
  delegation/browser/file/terminal/code-execution, max transport retries 1, max
  concurrency 1).
- **Output**: Hermes returns one JSON research draft. It is untrusted bytes; the
  repository validator is authoritative. Every no-authority flag must be present and
  true: `advisory_only`, `human_review_required`, `no_execution_authority`,
  `no_risk_override`, `no_credential_request`,
  `no_order_or_cancel_or_sign_or_submit`, `no_paper_live_decision`,
  `no_strategy_promotion_approval`, `no_pr_approval_or_merge_readiness_claim`. Empty
  or fabricated citation structures fail closed. No fair probability, expected
  return, side, entry/exit, position size, executable trade, strategy promotion, or
  Alpha candidate id is produced. Invalid JSON/schema fails closed; there is no
  try-again-until-it-passes.
- **Receipt** (`HermesResearchRunReceipt`): immutable, content-addressed, and
  sanitized. It records the exact Hermes version, reported provider/model labels,
  UTC bounds, terminal status, transport attempts, timeout/truncation flags,
  tool-call counts, source url count and digests, output/safety validation status,
  token/cost if available, budget status, `human_review_required = true`, all
  execution/live/credential/risk/paper authority flags false, and
  `activation_state` in `CODE_COMPLETE_NOT_REMOTE_ACTIVATED` or
  `CONTROLLED_RESEARCH_RUN_COMPLETE`. It never contains an API key/token, auth
  header, environment dump, raw stderr, raw provider payload, home/repo path,
  private data, trading credential, or order/account state.

## 5. Budget, retry, teardown

First-runtime hard bounds: one research request per controller execution;
concurrency 1; at most one transport retry, permitted only for a process transport
failure or a timeout before usable output — never for poor research, a failed
validator, unsafe output, a bad citation, low confidence, or an unwanted
conclusion. Repository absolute maxima: `max_turns <= 40`, `max_wall_seconds <=
300`, `max_output_bytes <= 1_000_000`, `max_sources <= 30`,
`max_estimated_cost_usd <= 5`, `max_transport_retries <= 1`. A real run stops when
any cap is reached; there is no auto-top-up and no fallback provider.

## 6. Compatibility

WP170 preregistration/OOS, WP172 classification/cost/fill/capacity, WP173 paper
binding/accounting/risk/reconciliation, WP175 Gate-C qualification, WP175D/WP175E
history/native-continuity, and the legacy WP99/WP133 advisory validators and
WP141–WP145 synthetic experiment history remain unchanged. This package creates no
alternate deterministic evidence authority; Hermes is untrusted research input.

## 7. Successor boundary

After merge only, S10-GATE-H1 must resolve the installed Hermes artifact, the
provider/model choice, the current account/privacy/retention posture, an
out-of-repo research-only credential, projected cost, the exact request, and
explicit public-web network authorization before any real remote run. It does not
activate Gate C and does not start S10-ALPHA-01 or WP176. Merge authorized: NO.
