# Hermes delegated specialists contract (S10-HERMES-DELEGATED-SPECIALISTS-01)

Status: offline engineering capability. Acceptance: `OFFLINE_IMPLEMENTATION_COMPLETE_REAL_PROVIDER_ACCEPTANCE_PENDING`.
Evidence class: `OFFLINE_NATIVE_DELEGATION_TEST_ONLY`. Real provider invocations: zero.

## 1. What this path does

One dormant, opt-in chain:

1. A restricted native Hermes parent runs inside the exact pinned Hermes v0.21.3 checkout. Pin facts: tag
   `v2026.9.14`, commit `345cd2b057a452236de401d3534b8502a7465e8d`. Toolsets: `web` and `delegation`.
2. The host makes one synchronous call to the genuine upstream
   `tools.delegate_tool.delegate_task(tasks=[A3, A4], parent_agent=parent, background=False)`.
3. Two real upstream leaf children run. Task index 0 is the FORECASTER (A3) and index 1 the FALSIFIER (A4).
4. A host-owned witness records child construction and the terminal result.
5. The native SRC-01 cold verifier (`tools.alpha.run_source_grounding.verify`) and per-question
   `research_cooperation.assess_question` check the children's citations.
6. One advisory `ResearchEpisode` is built and appended:
   `alpha_factory.build_research_episode` → `alpha_factory_registry.append_alpha_factory_records` →
   cold `load_and_verify_alpha_factory_registry`.

| Piece | Path |
|---|---|
| Delegated profile | `src/research_runtime/hermes_controlled_runtime/policy.py` (`DelegatedSpecialistsPolicy`) |
| Bounded worker launch | `src/research_runtime/hermes_controlled_runtime/runner.py` (`run_pinned_python_worker`) |
| Witness producer and validator | `src/research_runtime/hermes_controlled_runtime/delegated_specialists.py` |
| Operator | `tools/alpha/run_hermes_delegated_specialists.py` (`run` / `verify`) |

## 2. Two disjoint profiles

- `HermesInvocationPolicy` (H1) is unchanged.
  - It stays web-only with `delegation=False`.
  - Policy id: `hermesinvocationpolicy:sha256:18b8f788…5e81`.
  - Managed config SHA-256: `7937426d…133cf`.
  - The test that pins it is R001.
- `DelegatedSpecialistsPolicy` is a separate frozen dataclass and is never a default.
  - It has its own id prefix, `hermesdelegatedpolicy:sha256:`.
  - Its constructor raises `PolicyBroadeningError` on any change to these fields:
    - toolsets, tools or roles;
    - transport or background;
    - concurrency (2), spawn depth (1), orchestrator (off), MCP inheritance (off);
    - auto-approve (off), independent completions (off), automatic retry (off).
  - It also raises on any cap outside its narrowing-only bounds.
  - Its managed config is the H1 managed posture plus pinned `delegation.*` keys. The H1 posture means no fallback provider, no plugins, hooks, memory or lazy installs, and update checks off.

## 3. Witness seam

Both seam facts below were verified at the exact pin:

- Upstream `_build_children` reaches `tools.delegate_tool._build_child_agent`, and `_Batch.run_child` reaches `_run_single_child`.
- Both are call-time module-attribute lookups.

For one run only, the worker replaces those two attributes with observers that call the original pinned
functions, then restores them in `finally`. The witness records `restored`.

- **Construction observer.** This runs before any inference. It records:
  - the real post-init child: `session_id`, `_parent_session_id`, `_subagent_id`, `_delegate_depth` and `_delegate_role`;
  - the effective model-facing `valid_tool_names` and tool schemas;
  - the goal digest.

  It raises if any of these is wrong: the task index or goal, the child tools (must be exactly `web_extract`, `web_search`), leaf depth 1, or the parent lineage. Upstream `_build_children` then aborts, so no child runs.
- **Completion observer.** This records the native result entry: status, exit reason, truncation, API calls, tokens, the cost status and the summary digest.
  - Cost is `UNKNOWN` unless upstream reports a known cost status.
  - Runs that land after the batch returns are counted as late and refused.
- **Provider boundary.** The only transport is the offline scripted client installed at `agent.process_bootstrap.OpenAI`, the upstream single client chokepoint. Each request is routed by a host nonce marker in the task goal. Unrouted requests are refused, and so is any parent model call.
- **Isolation.** The worker starts the pinned venv with `-I -B` and a closed environment allowlist. Its home, managed directory and working directory are ephemeral, outside the repository, and removed afterwards.
  - An audit hook denies every subprocess and every socket entry point.
  - The only expected network attempts are the denied `127.0.0.1:9` sentinel probes.
  - The pinned checkout must be clean: `.git/HEAD` equals the commit, and nine LF-normalized seam files match frozen SHA-256 values. A `<pin>/.env` refuses the run.

Model text, stdout, background handles and hook callbacks are never provenance. Roles come only from the task index, and response and origin ids only from the witnessed `_subagent_id`.

## 4. Validation (closed codes; any code = no witness, no grounding, no Alpha append)

| Area | Refusal codes |
|---|---|
| Pin | `PINNED_RUNTIME_UNAVAILABLE`, `PIN_COMMIT_MISMATCH`, `PIN_SOURCE_MISMATCH`, `PIN_ENV_FILE_PRESENT` |
| Worker | `WORKER_TIMEOUT`, `WORKER_LAUNCH_FAILED`, `WITNESS_MISSING`, `WORKER_EXIT_NONZERO` |
| Request binding | `WITNESS_REQUEST_MISMATCH` |
| Config | `CONFIG_KNOB_MISMATCH` |
| Tools | `PARENT_TOOLS_NOT_ALLOWED`, `CHILD_TOOLS_NOT_ALLOWED`, `MODEL_FACING_TOOLS_NOT_ALLOWED`, `PRE_INFERENCE_REFUSAL` |
| Lineage | `CHILD_CONSTRUCTION_INVALID`, `CHILD_IDENTITY_DUPLICATE_OR_MISSING`, `CHILD_ROLE_INDEX_INVALID`, `CHILD_RUN_UNOBSERVED_CONSTRUCTION`, `TASK_IDENTITY_INVALID` |
| Completion | `CHILD_CALLS_INCOMPLETE`, `CHILD_NOT_COMPLETED`, `DELEGATE_TASK_ERROR`, `DELEGATE_RESULT_NOT_COMPLETED`, `LATE_CHILD_PUBLICATION` |
| Budget | `CHILD_USAGE_UNKNOWN`, `CHILD_BUDGET_EXCEEDED`, `CHILD_MODEL_CALLS_UNACCOUNTED`, `CHILD_OUTPUT_INVALID`, `CHILD_COST_UNKNOWN` (when the policy requires cost certainty) |
| Boundary | `OFFLINE_BOUNDARY_VIOLATION`, `OBSERVER_NOT_RESTORED`, `DEFENSE_PROBE_NEVER_ACCEPTED` |

`DEFENSE_PROBE_NEVER_ACCEPTED` covers the test-only probe that skips the parent gate. It exists only to show that the construction observer stops a composite child before inference.

There is one parent, one batch, two children and no retry. Valid witnesses are sealed in memory as `DelegationWitness`, content-addressed with `hermesdelegationwitness:sha256:`. `claim_witness` claims a witness once:

- a forged or self-assigned witness returns `WITNESS_NOT_HOST_ISSUED`;
- an edited one returns `WITNESS_TAMPERED`;
- a replayed one returns `WITNESS_ALREADY_CONSUMED`;
- a witness reloaded after a restart is never claimable.

## 5. Grounded cooperation and Alpha consumer

- Each child summary must be strict JSON with exactly the key `{"claims": [...]}`. Role, origin or scope self-claims are refused.
- The operator builds native submissions and calls `assess_question` against the frozen SRC-01 ledger. That checks quotes, allowlist, market binding, cutoff, injection-shaped content and the native rule hash.
- Only `CITATIONS_VERIFIED_REVIEW_REQUIRED` or `DISAGREEMENT_REVIEW_REQUIRED` may append.
- The target registry must extend the grounding's frozen `alpha.sqlite3` entry-hash chain, which rejects an outsider registry or a missing predecessor. The candidate, family and source references must already exist there.
- The episode itself:
  - result state `DATA_INSUFFICIENT`, producer type `OTHER_VALIDATED_ADVISORY`, confidence `very_low`, `human_review_required=True`;
  - all three no-authority flags are true;
  - the evidence regime is `OFFLINE_NATIVE_DELEGATION_TEST_ONLY`;
  - its references are the SRC-01 receipt id, the cooperation digest and a session-independent `hermesdelegationbinding:sha256:` binding.
- The same inputs re-run with new child sessions give `REGISTRY_APPEND_IDEMPOTENT`.
- `verify` cold re-derives grounding, cooperation and episode from the frozen inputs and the recorded witness body. It never re-issues a witness and never appends.
- `HERMES_CONTROLLED_RESEARCH` classification needs a separate real-provider acceptance.

## 6. Non-authority

The tool and tests never touch:

- a provider, model, OAuth, Firecrawl or Polymarket network;
- credentials;
- wallets or accounts;
- Alpha discovery, qualification, strategy, paper or order paths;
- schedulers, hosts or deployment.

The historical `run_hermes_cooperation` 40-case synthetic operator and `research_cooperation` are unchanged.

The pinned-native tests need `POLYMARKET_HERMES_PIN_ROOT`. Hosted CI has no pin, so those tests skip there. See the deferred items.
