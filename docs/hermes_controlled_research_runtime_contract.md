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
- Frozen one-shot command shape (argv only, never a shell string), matching the
  exact tagged v0.21.3 CLI verified against `hermes_cli/_parser.py` and
  `hermes_cli/oneshot.py` at commit `345cd2b`. `-z/--oneshot`, `--provider`,
  `--model`, `--toolsets`, `--usage-file`, `--safe-mode`, `--ignore-user-config`,
  and `--ignore-rules` are all top-level flags. v0.21.3 does **not** support
  `--format stream-json` or `--input-file`; it carries the prompt as the `-z` argv
  element and writes machine-readable usage/cost to `--usage-file`:

  ```
  hermes --safe-mode --ignore-user-config --ignore-rules
    --provider <label> --model <label> --toolsets web
    --usage-file <bare-name> -z <deterministic-research-envelope>
  ```

- **No iteration cap on the pinned one-shot path.** `--max-turns` is **not** a
  top-level flag in v0.21.3 — it exists only on the `chat` subparser — and the
  tagged `-z` implementation constructs the agent with no `max_iterations`
  override. WP175H therefore passes no `--max-turns`, carries no `max_turns`
  request field, and claims no `-z` iteration cap. The honest posture is
  `iteration_cap = UNAVAILABLE_ON_PINNED_V0_21_3_ONESHOT`. The hard runtime
  controls that do remain are: a single external invocation (zero automatic paid
  research retries), an external wall-clock timeout, a stdout byte cap, a
  usage-file byte cap, a validated-output source-count cap, the exact one-shot
  argv, the exact web-only toolset, the provider/model pin, no accepted automatic
  fallback, and a post-run usage/cost acceptance gate.
- Version is read from a bounded, **update-check-disabled** `hermes --version`
  preflight. Raw `hermes --version` is not intrinsically offline: exact tagged
  `hermes_cli/_startup_fast.py::print_fast_version_info(check_updates=True)` calls
  `banner.check_for_updates(passive=True)`, which can reach GitHub. The probe runs in
  a throwaway `HERMES_HOME` whose `config.yaml` sets `updates.check: false`, so the
  tagged `check_for_updates` returns before any network access; the probe home is
  deleted on teardown and forwards no provider secret. A real external run is invalid
  unless the probe launched, did not time out, **exited 0**, did not truncate its
  version stdout, and reported exactly `0.21.3`.
- Exact tagged `-z` internally enables one-shot approval bypass, so approval
  prompts are **not** a safety boundary
  (`APPROVAL_BYPASS_PRESENT_BUT_NO_MUTATING_TOOL_SURFACE`). Safety rests on the
  exact web-only toolset, safe-mode, ignore-user-config, ignore-rules, no repo
  mount, no mutating tool family, an ephemeral cwd, a dedicated research-only
  Hermes home, and the deterministic no-authority validator.

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
- The forwardable research `HERMES_HOME` is validated against a **stable repository
  root derived from this module's install location, not `os.getcwd()`**: a home
  inside the repository tree is rejected regardless of the caller's working
  directory (case-normalized), along with a `local_data` tree, a relative path, or a
  traversal marker.
- The `-z` prompt is bounded by raw UTF-8 byte count and, additionally, the
  **assembled Windows command line** (computed with `subprocess.list2cmdline`, which
  mirrors exact Windows argv quoting) is bounded below the `CreateProcess` 32767-char
  ceiling, so quote/backslash-heavy content that expands under quoting fails closed
  before spawn. Nothing is ever shell-quoted manually and `shell=True` is never used.
- The prompt envelope is compact and deterministic: one permanent system
  instruction plus the validated request. It never loads the repository, AGENTS.md,
  full project history, project memory, or the Alpha Factory database.

## 4. Request / policy / output / receipt

- **Request** (`HermesResearchRunRequest`): immutable, content-addressed over
  canonical public fields; rejects unknown fields, binary floats where numeric
  canonicality matters, over-bound values, path traversal/absolute paths, embedded
  secrets, and authority-escalation content, without echoing rejected content.
- **Policy** (`HermesInvocationPolicy`): frozen constants (`allowed_toolsets =
  ("web",)`, `tool_enforcement = STATIC_EXACT_TOOLSET_POLICY`, `output_mode =
  PLAIN_STDOUT_PLUS_USAGE_FILE`, `iteration_cap =
  UNAVAILABLE_ON_PINNED_V0_21_3_ONESHOT`, `approval_authority =
  APPROVAL_BYPASS_PRESENT_BUT_NO_MUTATING_TOOL_SURFACE`, ignore-user-config,
  ignore-rules, safe-mode, one-shot, shell false, ephemeral empty cwd, repo mount
  false, no mcp/plugins/cron/delegation/browser/file/terminal/code-execution, **max
  transport retries 0**, max concurrency 1).
- **Output and success evidence**: v0.21.3 returns the final research draft as
  plain stdout text and machine-readable usage/cost in the `--usage-file` JSON
  report; it emits no runtime tool-call event stream. A successful run requires, in
  order: process **exit code exactly 0** (any other code fails closed even with
  syntactically valid stdout, with no retry); **neither authoritative surface
  truncated** — a truncated stdout or usage-file prefix can be syntactically valid
  but is not the real output, so it fails closed before parsing and can never yield a
  successful receipt; a captured non-empty bounded final
  response; a **valid usage report** as mandatory success evidence (`completed`
  exactly true, `failed` exactly false, and valid non-negative `input_tokens`,
  `output_tokens`, `total_tokens`, `api_calls` integers plus present `model`,
  `provider`, `session_id`; a missing/malformed usage report is
  `USAGE_EVIDENCE_INVALID`); authoritative untrusted-draft schema/safety
  validation; **verified provider/model binding** (`usage.provider ==
  request.provider_label` and `usage.model == request.model_label`, else
  `PROVIDER_MODEL_MISMATCH`); and a post-run cost-acceptance gate (below). Hermes
  output is untrusted bytes; the repository validator is authoritative. Every
  no-authority flag must be present and true: `advisory_only`,
  `human_review_required`, `no_execution_authority`, `no_risk_override`,
  `no_credential_request`, `no_order_or_cancel_or_sign_or_submit`,
  `no_paper_live_decision`, `no_strategy_promotion_approval`,
  `no_pr_approval_or_merge_readiness_claim`. Empty or fabricated citation
  structures fail closed. No fair probability, expected return, side, entry/exit,
  position size, executable trade, strategy promotion, or Alpha candidate id is
  produced. Invalid JSON/schema fails closed; there is no try-again-until-it-passes.
- **Cost semantics (post-run)**: the `--usage-file` is POST-RUN accounting, so
  WP175H does not claim a pre-spend hard USD stop. `max_accepted_estimated_cost_usd`
  is a post-run acceptance threshold. Real v0.21.3 writes `estimated_cost_usd` as a
  JSON **number** (exact tagged `agent/turn_usage.py` folds
  `float(cost_result.amount_usd)` into `session_estimated_cost_usd`,
  `agent/turn_finalizer.py` copies it, `hermes_cli/oneshot.py::_write_usage_file`
  `json.dumps` it), so the usage document is parsed with `parse_float=Decimal` (no
  binary float in evidence), `NaN`/`Infinity` are rejected anywhere, and only a
  non-negative int or finite `Decimal` cost is admitted — a JSON string cost is not
  accepted. Cost acceptance validates the exact tagged pair
  (`agent/usage_pricing.py` @ `345cd2b`): `cost_status ∈ {actual, estimated,
  included, unknown}` and `cost_source ∈ {provider_cost_api,
  provider_generation_api, provider_models_api, official_docs_snapshot,
  user_override, custom_contract, none}`. An out-of-vocabulary `cost_status`/
  `cost_source`, a missing/invalid `estimated_cost_usd`, or a `cost_status` of
  `unknown` is `COST_EVIDENCE_UNAVAILABLE` (a missing cost is **never** treated as
  zero). `included` requires an amount of exactly `0` (the `none` source is valid,
  mirroring the tagged subscription-included case); `actual`/`estimated` require a
  known priced source that is never `none`. A known cost above the threshold is
  `BUDGET_EXCEEDED`; only a known, finite, in-threshold cost is accepted. Actual
  pre-spend protection at S10-GATE-H1 comes from a single invocation, the hard
  wall-clock timeout, an explicit low-cost provider/model, provider/account-side
  spend controls, and a human-authorized pilot.
- **Receipt** (`HermesResearchRunReceipt`): immutable, content-addressed, and
  sanitized. It records the exact Hermes version, requested provider/model labels,
  the VERIFIED actual usage provider/model on success, `iteration_cap_status`, UTC
  bounds, terminal status, process exit code, transport attempts,
  timeout/truncation flags, the configured toolset with `tool_enforcement`,
  `runtime_tool_telemetry = UNAVAILABLE_ON_PINNED_V0_21_3` (no fabricated tool-call
  telemetry), and `approval_authority`, source url count and digests, output/safety
  validation status, usage-evidence status with `completed`/`failed`/token/api-call
  counts and `estimated_cost_usd`/`cost_status`/`cost_source` from the usage file if
  safely available, budget status, `human_review_required = true`, all
  execution/live/credential/risk/paper authority flags false, and
  `activation_state` in `CODE_COMPLETE_NOT_REMOTE_ACTIVATED` or
  `CONTROLLED_RESEARCH_RUN_COMPLETE`. It never contains an API key/token, auth
  header, environment dump, raw stderr, raw provider payload, home/repo path,
  private data, trading credential, or order/account state.

## 5. Budget, retry, teardown

First-runtime hard bounds: one research request per controller execution;
concurrency 1; **zero automatic paid research retries** (`max_transport_retries =
0`). A paid provider call can already spend before a timeout/transport failure and
v0.21.3 emits accounting only after/best-effort, so a failed or timed-out run is
never automatically repeated — it returns a sanitized failure receipt and stops for
human/Side decision. Repository absolute maxima: `max_wall_seconds <= 300`,
`max_output_bytes <= 1_000_000`, `max_sources <= 30`,
`max_accepted_estimated_cost_usd <= 5`, `max_transport_retries <= 0`. There is no
`max_turns` maximum because the pinned one-shot path exposes no iteration cap. A
real run stops when any cap is reached; there is no auto-top-up and no fallback
provider.

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
