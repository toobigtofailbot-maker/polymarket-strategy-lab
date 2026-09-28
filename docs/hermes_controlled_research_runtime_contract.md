# Controlled Hermes Research Runtime Core Contract (WP175H / S10-HERMES-01)

> S10-HERMES-CTX-01 additive pinned-runtime correction: top-level `-z` does not route
> through the normal chat flag path that applies context/memory suppression, so
> `--ignore-rules` alone is not proof that `skip_context_files` or `skip_memory` took
> effect. The managed v0.21.3 profile therefore explicitly disables memory, user profile,
> compression, auxiliary title/background activity, project skill discovery, external
> skill dirs, lazy installation, and private URLs. Missing dependencies fail closed.
> Research-home name-only preflight also rejects MEMORY/USER/AGENTS/CLAUDE/GEMINI,
> `.cursorrules`, and non-empty profile-local skills. SOUL.md is a proven prompt input
> and is governed by the S10-HERMES-CTX-02 exact-stock-only rule below; the other names
> are defense in depth, not a claim that each loads on every one-shot.
>
> S10-HERMES-CTX-02 pinned default SOUL.md compatibility (exact-stock-only): pinned
> Hermes v0.21.3 (tag v2026.9.14, commit 345cd2b) necessarily seeds its stock
> `DEFAULT_SOUL_MD` into any initialized home, so a universal SOUL.md rejection is
> structurally incompatible with the pinned runtime. The research-home preflight
> therefore admits SOUL.md ONLY when it is a regular, non-symlink file whose raw bytes
> are exactly the pinned auto-seeded stock default, verified by exact raw-byte length
> **667** and SHA-256
> **`36c1f5a2e92cd1d018311eaf4c8f1e8886672eae78212e033c681d0e3d5d506f`** with no
> normalization of whitespace, BOM, line endings, Unicode, or encoding. That file carries
> no user-authored customization; the exception does NOT mean arbitrary SOUL files are
> trusted. Every custom, modified, truncated, extended, symlinked, non-regular, or
> unreadable SOUL.md remains fail-closed, and there is no legacy-template, prefix, fuzzy,
> or caller-supplied-digest path. All other profile-context names, `config.yaml`,
> non-empty `plugins/`, and non-empty `skills/` remain rejected as before. `.env` and
> `auth.json` remain permitted credential stores whose values this preflight never
> opens or inspects; SOUL.md is the only file whose bytes it reads. The check is
> admission verification only (never deletes, rewrites, or replaces SOUL.md) and is
> repeated before every invocation, so a post-preflight mutation fails before spawn.
> No provider, model, toolset, managed-profile, argv, retry, fallback, telemetry,
> context-protocol, or authority behavior changes.
>
> S10-HERMES-CTX-03 canonical public Polymarket identifier compatibility
> (public_market_context only): request secret scanning remains fail-closed, and the
> generic long-hex rule `\b0x[a-fA-F0-9]{40,}\b` stays in the global secret rules. The
> repository's canonical public event identity can be `event:polymarket:0x` + 64 hex (the
> condition id), and the context controller serializes canonical `subject_refs` and exact
> scope into `public_market_context`, so the generic rule rejected a public identifier
> (AF1 Attempt-03 stopped `REQUEST_SECRET_DETECTED` before any Hermes launch). Inside
> `public_market_context` ONLY, exact complete canonical public identifiers
> `market:polymarket:<decimal>`, `event:polymarket:0x<exactly 64 lowercase hex>`,
> `event:polymarket:market-<decimal>` and `token:polymarket:<decimal>` (decimal: non-empty,
> no leading zero), delimited by start/end, whitespace, quotes, brackets, commas, `=`
> before or a JSON-escape backslash after, are masked in a validation-only copy before the
> full secret scan; every occurrence of the literal namespace `event:polymarket:` must begin
> an exact, delimited canonical event id or the request fails `REQUEST_SECRET_DETECTED`
> (malformed canonical-looking event ids, including word-glued forms the generic rule would
> miss, fail closed); every other secret rule also runs over the original text, and the
> authority scan runs over the original text. Bare long-hex values, wallet/account-shaped
> `0x` + 40 hex, wrong namespaces, other hex lengths, uppercase hex, extra token
> characters, and every credential marker remain rejected; the same values in any other
> request field remain rejected by the ordinary strict scan. The exception does not
> authorize wallet, account, or credential material, and there is no global or
> caller-configurable allowlist. The stored `public_market_context` and the
> content-addressed request identity use the original unmasked bytes. No schema version,
> invocation policy identity, provider, model, toolset, retry, output-parsing, or authority
> behavior changes.
> Exact-session `state.db` evidence is now projected read-only by repository code. Pinned
> local URL checks are enforced before dispatch and on returned final URLs, but remote
> Firecrawl HTTP/redirect telemetry remains UNAVAILABLE, remote private-target proof is
> UNKNOWN, same-provider recovery is UNKNOWN_POSSIBLE, and exact physical provider attempt
> count remains UNKNOWN where direct evidence is absent. See
> `docs/hermes_context_broker_reconciliation_contract.md`.

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
  `public_market_context` alone uses the S10-HERMES-CTX-03 canonical public Polymarket
  identifier rule recorded above.
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

## 8. WP175I controlled research profile (S10-HERMES-01A)

WP175I corrects the research invocation so pristine pinned Hermes v0.21.3 (tag
v2026.9.14, commit 345cd2b, UNCHANGED) runs under one mechanically enforced controlled
research profile. Verified by read-only inspection of the exact tagged source with zero
runtime/provider call.

Research argv change. The real one-shot argv is exactly `hermes --ignore-user-config
--ignore-rules --provider P --model M --toolsets web --usage-file <bare relative name>
-z <bounded prompt>`. `--safe-mode` is REMOVED: on exact tagged v0.21.3 it sets
`HERMES_SAFE_MODE=1`, and `hermes_cli/plugins.py` then skips plugin discovery,
suppressing the bundled `plugins/web/firecrawl` backend (`kind: backend`,
`provides_web_providers: [firecrawl]`) that H1 requires. `--ignore-user-config` and
`--ignore-rules` are retained.

Controlled managed scope. For every external research invocation the backend creates a
fresh ephemeral managed-scope directory (distinct from the empty cwd, the repository,
`local_data`, and the research `HERMES_HOME`), writes exactly one non-secret
`config.yaml` holding the deterministic managed bytes, and sets `HERMES_MANAGED_DIR`
itself (never inherited, never caller-supplied). Both ephemeral directories are removed
on success, timeout, and launch failure. The `-z` one-shot (`hermes_cli/oneshot.py`)
calls `hermes_cli.config.load_config()`, whose `_merge_managed_overlay` deep-merges the
managed config leaf-over-leaf on top of exact tagged defaults
(`hermes_cli/managed_scope.py`), so the managed layer survives the one-shot path;
`get_managed_dir()` honors `HERMES_MANAGED_DIR` only when the directory exists and
parses `config.yaml` with `yaml.safe_load`, so canonical JSON is valid YAML.

Managed config (exact tagged keys). `updates.check` false; `fallback_providers` empty;
`agent.api_max_retries` 1; `web.backend` / `web.search_backend` / `web.extract_backend`
firecrawl; `web.keyless_fallback` false; `web.keyless_rescue` false; `web.cache_enabled`
false; `web.provider_tier.firecrawl` paid; `plugins.enabled` empty; `hooks` empty.
`tools/web_tools.py` resolves `web.search_backend` / `web.extract_backend` strictly with
no probe, so Firecrawl is pinned for both `web_search` and `web_extract`;
`agent/web_search_registry.py` and `tools/web_tools_rescue.py` read
`web.keyless_fallback` / `web.keyless_rescue`, so the keyless ring and the one-shot
keyless rescue are both disabled; with the H1 Firecrawl key present the keyed direct
path is used, and with it absent H1 fails rather than silently using a keyless route.
The Hermes invocation policy schema is bumped to `hermes-invocation-policy/2.0.0` and the
deterministic managed-config SHA-256 is committed into the policy identity, so a
one-field broadening of any managed control changes the policy id.

Compensating isolation without safe mode. Exact `--toolsets web`; `--ignore-rules`; a
dedicated research `HERMES_HOME` whose `config.yaml` is absent and whose user plugins are
absent or empty (fail-closed preflight, names only, no credential read; an `.env` /
`auth.json` credential store alone is permitted); an ephemeral empty cwd distinct from
the managed dir; `HERMES_ENABLE_PROJECT_PLUGINS` and `HERMES_MANAGED_DIR` never inherited
from the parent; managed `plugins.enabled` empty and `hooks` empty; no MCP or custom
toolset; no repo mount. Truthful wording: `CUSTOM_USER_PROJECT_PLUGIN_LOADING =
FORBIDDEN`; `PINNED_BUNDLED_BACKEND_DISCOVERY = ALLOWED_FOR_WEB_PROVIDER_REGISTRATION`;
`EXPOSED_AGENT_TOOLSET = WEB_ONLY`. Exact tagged `plugins_discovery.gate_manifest`
auto-loads the bundled Firecrawl backend while gating non-bundled plugins on the
`plugins.enabled` allow-list (an explicit empty list is nothing enabled, not the
key-missing grandfather case) and project plugins on `HERMES_ENABLE_PROJECT_PLUGINS`.

Retry posture. Exactly one research invocation per attempt; zero WP175H outer transport
retries; one ordinary provider attempt via `agent.api_max_retries` 1 (exact tagged
`agent/agent_init.py` clamps to one and `agent/conversation_loop.py` loops
`while retry_count < max_retries`); the primary OpenAI client is created with SDK
`max_retries=0` (`_create_openai_client`, proven by tagged
`tests/agent/test_create_openai_client_disables_sdk_retries.py`); no provider/model
fallback (`fallback_config.get_fallback_chain` returns none for the empty chain); no
web-backend fallback/rescue. One bounded same-provider primary transport recovery
(`agent/agent_runtime_helpers.py` `try_recover_primary_transport`) may rebuild the
primary client once after the single ordinary attempt exhausts on a transient transport
error -- same provider, same model, same web backend, no second controller invocation.
This narrow recovery is documented as an H1 evidence limitation and is never suppressed
by a Hermes fork.

Authority. No real provider, OAuth, Firecrawl-secret, or public-web activity occurs
during WP175I; capital at risk USD 0; orders 0; Gate C NOT AUTHORIZED; runtime activated
NO. `models.py` and `response_capture.py`, and the WP175H receipt/provider/model/cost/
schema/safety fail-closed semantics, are unchanged. The successor resumes S10-GATE-H1
only after WP175I merge and Side10 review; the prior H1 attempt consumed zero real
research invocations, so its authorization is unspent.

## 9. WP175J branded version-banner preflight correction (S10-HERMES-01B)

Exact tagged `hermes --version` output carries both identities in one banner:
`Hermes Agent v0.21.3 (2026.9.14)`. Version authority is only the package version
attached to the case-insensitive Hermes-branded label (`Hermes Agent` or retained
legacy `hermes-agent`); the release-date token is never version authority. The parser
is intentionally branded and fail-closed, has no generic semantic-version fallback,
and rejects release-date-only, unbranded, and malformed package tokens. Bytes remain
UTF-8 decoded fail-closed and supported-version comparison remains exactly `0.21.3`.
Version-probe launch, timeout, nonzero-exit, and stdout-truncation gates are unchanged.
The isolated update-disabled preflight performs no provider, Firecrawl, or public-web
research call and does not activate the dormant runtime.

## 10. WP175K sanitized failure-evidence capture (S10-HERMES-01C)

Raw child stderr is never stored in a receipt, artifact, log, or return value. The
external backend may transiently hold bounded child stderr in memory only to SANITIZE
it before constructing the invocation outcome. A deterministic in-runner sanitizer
decodes fail-closed, normalizes newlines and strips unsafe control characters, redacts
secret-bearing structures (named/JSON secret assignments, Authorization/Bearer/Basic
material, PEM private-key blocks, `sk-`/`ghp_`/`github_pat_`/`xox*` token prefixes,
JWT-shaped tokens, URL userinfo, and URL query/fragment material), scrubs local
filesystem identity (user home, repository, research `HERMES_HOME`, ephemeral cwd,
managed dir, and Windows/UNC/`/home`/`/Users`/temp paths) to `<PATH>`, and keeps only a
bounded diagnostic TAIL of at most `MAX_SANITIZED_STDERR_EXCERPT_BYTES` (4096) UTF-8
bytes. The sanitized status is one of `EMPTY`, `AVAILABLE`, `AVAILABLE_REDACTED`,
`BLOCKED_UNSAFE`, or `SANITIZER_ERROR`: residual secret-like content in the final
excerpt fails closed to no excerpt (`BLOCKED_UNSAFE`) and any sanitizer fault fails
closed (`SANITIZER_ERROR`). No sanitizer outcome changes process-exit classification,
terminal status, or retry.

The receipt schema is bumped additively from `hermes-research-run-receipt/1.1.0` to
`hermes-research-run-receipt/1.2.0`, adding content-addressed evidence fields
`stderr_captured_byte_len`, `stderr_sanitization_status`, `stderr_excerpt`,
`stderr_excerpt_truncated`, `stderr_redaction_applied`, `usage_file_present`, and
`usage_file_truncated`. `usage_file_present` is true iff Hermes wrote any usage-file
bytes (a zero-byte existing file counts as present); the strict usage parser remains
independently authoritative for validity. The sanitized excerpt is the only diagnostic
text surface; the controller failure precedence, request and draft schemas, policy
identity, managed config, provider/model, `web`-only toolset, and retry posture are
unchanged, and this capture hardening does not activate the dormant runtime.

## WP175M draft prompt contract alignment and schema diagnostics

H1 #3 — the third real S10-GATE-H1 run — completed a real controlled research/model
interaction (Hermes child exit 0, valid usage, `api_call_count` 5) but failed terminal
`OUTPUT_SCHEMA_INVALID` / `DRAFT_FIELD_MISSING`: the permanent system instruction told
Hermes to match a "provided research-draft schema", but the envelope supplied only
`draft_schema_version`, never the deterministic field contract `validate_research_draft`
enforces, so the model improvised an alternative structured schema and the validator
failed closed at first missing canonical field `advisory_only`. Read-only forensics
confirmed `web_search`/`web_extract` activity with no unexpected tools under a
Firecrawl-pinned managed configuration; runtime tool telemetry is
`UNAVAILABLE_ON_PINNED_V0_21_3`, so a remote Firecrawl HTTP transaction is NOT
independently proven. The `session_model_usage` aggregate includes an auxiliary
`title_generation` usage row, so exact aggregate equality is not a safe session-identity
method; the main research route usage matched the receipt.

WP175M fixes the contract BEFORE generation. `models.py` owns a canonical
machine-generated draft output contract, `build_research_draft_output_schema(*,
expected_request_id, max_sources)`, derived from the SAME constants
`validate_research_draft` enforces: the private list-field collection is promoted to the
public `DRAFT_LIST_FIELDS`, a canonical ordered `DRAFT_REQUIRED_TOP_LEVEL_FIELDS` places
`schema_version`/`request_id` first then the authority flags (`advisory_only` first) then
the substantive fields, and the generated schema embeds every required field, each
authority flag as `const: true`, the confidence and source-class enums, validator-aligned
length/cardinality bounds, a non-empty `falsification_checks_performed`, a min-1
`source_references` capped at `min(max_sources, MAX_SOURCES_ABSOLUTE)`, and the exact draft
schema version and request id as constants. The generated required set is identical to the
validator's required set, and no constraint the validator does not enforce is invented.
`PERMANENT_SYSTEM_INSTRUCTION_VERSION` is bumped to
`hermes-research-system-instruction/1.1.0`; the instruction states the envelope's
`draft_output_schema` is authoritative, the response is exactly one JSON object, canonical
field names must be used exactly (no aliases such as `sources`, `evidence_map`,
`completeness`, or `cross_category_assessment`), every authority boolean is exactly `true`,
and substantive fields must reflect real (never fabricated) research. `HermesResearchEnvelope`
carries `draft_output_schema` in `as_mapping()`, `to_query_bytes()`, `to_prompt_string()`,
and `envelope_digest`. Authority-flag injection is declined: all draft authority flags
remain model-output required; there is no substantive post-hoc repair, so a wrong
substantive schema still fails closed.

Sanitized schema-failure diagnostics (`inspect_research_draft_structure`) retain only
static canonical field-name tokens and fixed statuses (`AVAILABLE`,
`UNAVAILABLE_INVALID_OUTPUT`; the controller default is `NOT_REACHED`) and never a rejected
value, arbitrary model key, or raw session id. The receipt schema is bumped additively
`hermes-research-run-receipt/1.2.0` -> `hermes-research-run-receipt/1.3.0`, adding
content-addressed `prompt_envelope_sha256`, `draft_output_contract_sha256`,
`draft_diagnostics_status`, `draft_present_required_fields`,
`draft_missing_required_fields`, `draft_first_missing_field`, and `usage_session_id_digest`
(SHA-256 of a valid usage report's session id; the raw session id is never retained).
Pre-research and no-draft paths use deterministic fail-closed defaults. With valid usage
the controller records the actual provider/model before draft validation, so a schema
failure preserves `verified_provider`/`verified_model` while the terminal status stays
`OUTPUT_SCHEMA_INVALID`; the provider/model mismatch terminal gate still runs after draft
validation. Request identity, policy identity, the frozen H1 request id, provider/model,
`web`-only toolset, retry posture, managed config, the draft payload schema
`hermes-research-draft/1.0.0`, and the WP175L runtime envelope are unchanged, and this
alignment does not activate the dormant runtime.

Finding G exact alignment: the generated contract and the validator share the remaining
primitives so the model-facing schema describes precisely the validator's accepted set. A
canonical `DRAFT_NON_WHITESPACE_PATTERN` (`\S`) backs both the validator's
non-whitespace checks for `research_summary` and source titles and the corresponding
schema `pattern`s (so a whitespace-only value is rejected by both, not just the
validator), and a single canonical `DRAFT_SOURCE_URL_PATTERN`
(`^[hH][tT][tT][pP][sS]://[^\s/$.?#].[^\s]*$`) compiles the validator's `_URL_RE` and is
embedded verbatim as the schema URL `pattern`; the previously invented `format: uri`
constraint is removed. This narrows nothing and broadens nothing in validator behavior.
