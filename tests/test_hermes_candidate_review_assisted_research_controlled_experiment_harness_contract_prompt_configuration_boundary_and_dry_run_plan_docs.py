"""Markdown-only tests for the WP144 harness contract and dry-run plan."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / (
    "hermes_candidate_review_assisted_research_controlled_experiment_harness_"
    "contract_prompt_configuration_boundary_and_dry_run_plan.md"
)

HEADINGS = (
    "# Hermes Candidate-Review Assisted Research Controlled Experiment Harness Contract, Prompt/Configuration Boundary, And Dry-Run Plan",
    "## Purpose", "## Position After WP143", "## Authority And Non-Authority",
    "## Repository Inputs Reviewed", "## Selected Harness Architecture",
    "## Deterministic Controller Ownership", "## Controller State Machine",
    "## Session Envelope Boundary", "## Prompt Boundary",
    "## Configuration Boundary", "## Provider Adapter Boundary",
    "## Permission Enforcement Boundary", "## Credential Injection Boundary",
    "## Budget, Timeout, Retry, And Concurrency Enforcement",
    "## Raw Output And Sanitized Evidence Policy", "## Teardown Contract",
    "## Failure Matrix", "## Local No-Provider Dry-Run Plan",
    "## Dry-Run Acceptance Matrix", "## Security And Privacy Invariants",
    "## Promotion Gates", "## Explicit Deferred Capabilities",
    "## Output Surface Inventory", "## Forbidden Interpretations",
    "## Future WP145 Boundary", "## Decision", "## Non-Authority Statement",
)

DECISIONS = (
    "Harness contract status: DOCUMENTATION_ONLY_RUNTIME_INACTIVE",
    "Controller authority: LOCAL_DETERMINISTIC_EXCLUSIVE",
    "Hermes session posture: ONE_CASE_ONE_EPHEMERAL_SESSION",
    "Provider adapter posture: ONE_EXPLICIT_CANDIDATE_CONFIGURATION_ONE_ALLOWLISTED_ENDPOINT",
    "Prompt/configuration status: VERSIONED_NON_EXECUTABLE_CONTRACT_ONLY",
    "Input posture: EXACT_VALIDATED_WP142_CASE_BUNDLE_ONLY",
    "Output posture: UNTRUSTED_DRAFT_ONLY",
    "Raw input/output persistence: FORBIDDEN_BY_DEFAULT",
    "Sanitized experiment metadata: FUTURE_ALLOW_EXACT_FIELDS_ONLY",
    "Network posture: DENY_ALL_EXCEPT_ONE_CONTROLLER_MEDIATED_PROVIDER_ENDPOINT",
    "Tool posture: NO_BROWSER_NO_SEARCH_NO_SOURCE_FETCH_NO_SHELL_NO_TRADING_TOOLS",
    "Memory posture: EPHEMERAL_SESSION_ONLY_DELETE_ON_TEARDOWN",
    "Dry-run posture: LOCAL_NO_PROVIDER_NO_NETWORK_NO_CREDENTIAL",
    "Deterministic validation and human review: MANDATORY",
    "Hermes/provider/model activation: NOT AUTHORIZED",
    "Paper/live/execution authority: FORBIDDEN",
    "WP145 requires separate approval",
)

STATES = (
    "NOT_STARTED", "PREFLIGHT", "CASE_LOADED", "INPUT_VALIDATED",
    "PERMISSIONS_VALIDATED", "BUDGET_VALIDATED", "SESSION_ENVELOPE_BUILT",
    "EPHEMERAL_SESSION_READY", "PROVIDER_INVOCATION_PENDING",
    "UNTRUSTED_OUTPUT_CAPTURED", "DETERMINISTIC_VALIDATION_COMPLETE",
    "RUBRIC_EVALUATION_COMPLETE", "HUMAN_REVIEW_COMPLETE",
    "SANITIZED_EVIDENCE_COMPLETE", "TEARDOWN_COMPLETE", "COMPLETED",
    "STOPPED_FAILED_CLOSED",
)


def _read() -> str:
    return DOC.read_text(encoding="utf-8")


def _section(heading: str) -> str:
    text = _read()
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end == -1 else text[start:end]


def _flat_section(heading: str) -> str:
    return " ".join(_section(heading).split())


def test_exact_title_heading_order_and_locked_decisions() -> None:
    text = _read()
    headings = tuple(
        line for line in text.splitlines()
        if line.startswith("#") and not line.startswith("### ")
    )
    assert headings == HEADINGS
    assert all(token in text for token in DECISIONS)


def test_exact_conceptual_flow_is_future_only() -> None:
    section = _section("## Selected Harness Architecture")
    steps = (
        "manual operator start", "local deterministic controller preflight",
        "load one exact WP142 case", "validate case/contracts/permissions/budgets",
        "construct sanitized session envelope", "start one ephemeral Hermes session",
        "controller-mediated provider-adapter call", "capture untrusted draft",
        "deterministic WP133 validation", "WP142 hard-gate/rubric evaluation",
        "mandatory human review", "sanitized evidence", "teardown and deletion",
    )
    positions = [section.index(step) for step in steps]
    assert positions == sorted(positions)
    assert "future architecture only" in section
    assert "No step is implemented or executed" in section


def test_controller_exclusively_owns_every_control_surface() -> None:
    section = _section("## Deterministic Controller Ownership")
    for phrase in (
        "experiment and case selection", "version selection", "case loading",
        "input validation", "prompt/configuration assembly",
        "permission, path, and endpoint enforcement",
        "credential acquisition and model-invisible injection",
        "budget, call, token, timeout, retry, and concurrency enforcement",
        "session start and stop", "input immutability", "output capture",
        "WP133 validation", "WP142 hard-gate and rubric evaluation",
        "human-review handoff", "sanitized evidence", "raw-output policy",
        "teardown, temporary-data deletion, and terminal-state selection",
        "owns only untrusted-draft generation",
    ):
        assert phrase in section


def test_exact_seventeen_states_order_and_fail_closed_rules() -> None:
    section = _section("## Controller State Machine")
    flat = " ".join(section.split())
    numbered = tuple(
        line.split("`", 2)[1] for line in section.splitlines()
        if line[:1].isdigit() and "`" in line
    )
    assert numbered == STATES
    for phrase in (
        "no state may be skipped", "transitions are controller-only",
        "every failure transitions to `STOPPED_FAILED_CLOSED`",
        "no automatic restart or background continuation",
        "never retried", "teardown is mandatory on success and failure",
        "`COMPLETED` requires human review, sanitized evidence, and teardown",
        "teardown failure remains failed-closed",
    ):
        assert phrase in flat


def test_session_envelope_allowed_and_forbidden_fields_are_complete() -> None:
    section = _flat_section("## Session Envelope Boundary")
    for phrase in (
        "experiment, configuration, and case IDs",
        "fixture, rubric, WP141, and WP143 versions",
        "exact synthetic question and request scope",
        "supplied synthetic excerpts and labels", "known uncertainty and missing data",
        "authority and safety constraints", "WP133 output-shape instructions",
        "non-authority notice", "human-review requirement",
        "budget, timeout, and output limits", "permission-profile and output-policy IDs",
        "credentials or authorization headers", "real market, account, wallet, order",
        "unrestricted repository context", "arbitrary metadata", "source URLs",
        "commands", "trading instructions", "prior-session memory",
        "unapproved provider internals", "creates no envelope schema",
    ):
        assert phrase in section


def test_prompt_and_configuration_requirements_and_prohibitions_are_exact() -> None:
    prompt = _flat_section("## Prompt Boundary")
    for phrase in (
        "versioned, deterministic", "provider-neutral where possible",
        "untrusted draft only", "no source access", "no tools, shell, or repository access",
        "no secrets", "no downstream record creation",
        "no recommendation, probability, or trading authority",
        "uncertainty, missing data, falsification, and limitations",
        "WP133 alignment", "human review is mandatory", "token and output limits",
        "credentials, commands, hidden retrieval, tool invocation",
        "arbitrary repository context", "self-modification", "persistent memory",
        "autonomous-agent authority", "automatic acceptance",
        "creates no executable prompt",
    ):
        assert phrase in prompt
    config = _flat_section("## Configuration Boundary")
    for phrase in (
        "config/controller/Hermes versions", "candidate/provider/model/version identifiers",
        "endpoint allowlist ID", "case/fixture/rubric/prompt versions",
        "permission/memory/output-policy profiles", "timeouts and duration",
        "token/call/retry/cost limits", "concurrency",
        "human-review and teardown requirements", "no JSON, YAML, TOML, `.env`",
    ):
        assert phrase in config


def test_adapter_permissions_and_credentials_preserve_wp143() -> None:
    adapter = _flat_section("## Provider Adapter Boundary")
    for phrase in (
        "one controller-built sanitized request", "one allowlisted endpoint",
        "exact time and output limits", "provider request ID, usage, cost",
        "read repository or local files", "choose a model or endpoint",
        "expose secrets", "unapproved redirects", "retry itself",
        "use tools, memory, or sources", "persist output", "validate or evaluate",
        "create downstream records", "trade", "implements no adapter",
    ):
        assert phrase in adapter
    permissions = _flat_section("## Permission Enforcement Boundary")
    for phrase in (
        "one exact WP142 case", "exact WP141–WP143 metadata read-only",
        "no general repository or local-file access", "one ephemeral temporary directory",
        "may not write the repository", "shell, browser, search, source, and trading tools",
        "one future provider endpoint", "all other network is denied",
        "persistent memory/output is denied", "scheduler and background modes are denied",
        "automatic records and acceptance are denied", "hard stop",
    ):
        assert phrase in permissions
    credentials = _flat_section("## Credential Injection Boundary")
    for phrase in (
        "outside the repository", "operator-injected only after preflight", "temporary",
        "least-privilege", "single-provider", "revocable", "not logged",
        "not persisted", "invisible to Hermes/model", "revoked or disabled",
        "creates, reads, or selects no credential",
    ):
        assert phrase in credentials


def test_budget_retry_timeout_and_concurrency_are_exact() -> None:
    section = _flat_section("## Budget, Timeout, Retry, And Concurrency Enforcement")
    for phrase in (
        "maximum remote configurations: `2`", "gold cases: `20`",
        "repeated runs per case: `3`", "maximum primary calls: `120`",
        "maximum retry calls: `20`", "maximum total calls: `140`",
        "total spend: `USD 100`", "daily spend: `USD 25`",
        "per-call spend: `USD 2`", "input tokens per call: `50,000`",
        "output tokens per call: `8,000`", "request timeout: `180 seconds`",
        "case-run duration: `300 seconds`", "concurrency: `1`",
        "automatic top-up: forbidden", "transport failure",
        "documented transient provider error", "timeout before usable output",
        "at most one retry", "no retry for unsafe output", "validation failure",
        "low rubric score", "expected refusal", "unsupported content", "policy breach",
        "future adapter cannot retry",
    ):
        assert phrase in section


def test_raw_policy_sanitized_evidence_and_teardown_are_complete() -> None:
    evidence = _flat_section("## Raw Output And Sanitized Evidence Policy")
    for phrase in (
        "Raw input/output persistence is forbidden by default",
        "only in memory or the exact ephemeral directory",
        "experiment, case, run, and configuration versions",
        "provider, model, version, and request ID", "timing, tokens/compute, cost",
        "deterministic-validation and hard-gate results", "normalized rubric score",
        "human correction and reviewer outcome", "stop reason", "teardown result",
        "credential-revocation confirmation", "exclude secrets, headers, raw prompt/output",
        "private data, source content, arbitrary errors", "creates no evidence schema",
    ):
        assert phrase in evidence
    teardown = _flat_section("## Teardown Contract")
    steps = (
        "stop provider activity", "stop the Hermes session", "clear memory",
        "delete temporary files", "close handles and connections",
        "prevent continued retries", "record sanitized stop metadata",
        "confirm no repository mutation", "confirm no raw persistence",
        "record credential-revocation responsibility", "enter `TEARDOWN_COMPLETE`",
        "enter `COMPLETED` or `STOPPED_FAILED_CLOSED`",
    )
    positions = [teardown.index(step) for step in steps]
    assert positions == sorted(positions)
    assert "Teardown failure means failed-closed and escalation" in teardown


def test_failure_matrix_has_every_exact_response_and_no_hidden_repair() -> None:
    section = _section("## Failure Matrix")
    rows = (
        ("Invalid case or version mismatch", "Stop before session"),
        ("Permission enforcement unavailable", "Stop before session"),
        ("Credential unavailable", "Stop before session"),
        ("Budget projection over cap", "Stop before session"),
        ("Endpoint not allowlisted", "Stop before session"),
        ("Provider/model identity mismatch", "Stop and teardown"),
        ("Unapproved redirect", "Stop and teardown"),
        ("Timeout/transport failure", "At most one controller-approved retry"),
        ("Unsafe output", "No retry; failure review; teardown"),
        ("Secret/private-data echo", "Immediate stop and teardown"),
        ("Source-access/tool/shell claim", "Hard-gate failure; no retry"),
        ("Input mutation", "Immediate stop and teardown"),
        ("WP133 validation failure", "No automatic repair; review; teardown"),
        ("Automatic downstream record", "Immediate stop and teardown"),
        ("Budget/call limit", "Immediate stop and teardown"),
        ("Raw persistence attempt", "Immediate stop and teardown"),
        ("Human stop", "Immediate stop and teardown"),
        ("Teardown failure", "Failed-closed and escalation"),
    )
    assert all(f"| {failure} | {response} |" in section for failure, response in rows)
    assert "no hidden repair, regeneration, alternate-model fallback" in section


def test_five_dry_run_stages_and_acceptance_criteria_are_complete() -> None:
    plan = _section("## Local No-Provider Dry-Run Plan")
    flat = " ".join(plan.split())
    stages = (
        "### Stage A — static preflight", "### Stage B — deterministic envelope",
        "### Stage C — fake adapter boundary", "### Stage D — validation/evaluation",
        "### Stage E — teardown",
    )
    positions = [plan.index(stage) for stage in stages]
    assert positions == sorted(positions)
    for phrase in (
        "versions", "one exact WP142 case", "secrets/URLs/real data",
        "input immutability", "forbidden envelope field", "test-only deterministic fake adapter",
        "no provider SDK, network, credential", "existing WP133 validation",
        "WP142 hard gates and rubric", "human review", "no downstream records",
        "empty or deleted temporary directory", "no repository mutation",
        "deterministic terminal state", "not executed",
    ):
        assert phrase in flat
    matrix = _flat_section("## Dry-Run Acceptance Matrix")
    for phrase in (
        "No provider/network/credential", "One WP142 case", "Exact state sequence",
        "Input immutability", "Untrusted output", "Validation and evaluation",
        "No downstream records", "No repository writes", "Teardown complete",
        "Every row must pass", "No dry run occurs in WP144",
    ):
        assert phrase in matrix


def test_security_promotion_deferrals_inventory_and_wp145_are_bounded() -> None:
    security = _flat_section("## Security And Privacy Invariants")
    for phrase in (
        "Synthetic WP142 input only", "No credential, header, secret",
        "Default-deny files, paths, tools, memory, network, redirects, and writes",
        "Exactly one controller-mediated future provider endpoint",
        "Original inputs are immutable", "raw content is ephemeral and deleted",
        "output is untrusted", "deterministic validation and human review",
        "No automatic downstream record", "Every failure closes",
    ):
        assert phrase in security
    promotion = _flat_section("## Promotion Gates")
    for phrase in (
        "WP145 may be considered only after WP144 is merged", "controller, state",
        "prompt/configuration", "raw-output/evidence", "local no-provider dry-run",
        "separately approved", "does not approve a provider experiment",
    ):
        assert phrase in promotion
    deferred = _flat_section("## Explicit Deferred Capabilities")
    for phrase in (
        "controller implementation", "harness implementation", "Hermes installation/invocation",
        "executable prompt or configuration files", "provider adapter",
        "test-only fake adapter", "sandbox", "endpoint allowlist",
        "credential acquisition/injection/revocation mechanism", "provider/model/account",
        "WP142 case execution", "dry-run execution", "raw-output storage",
        "evidence schema or storage", "source retrieval", "automatic records or acceptance",
        "paper/live behavior", "execution, risk, orders, or trading", "WP145 implementation",
    ):
        assert phrase in deferred
    inventory = _flat_section("## Output Surface Inventory")
    assert "Allowed outputs" in inventory and "Forbidden outputs" in inventory
    future = _flat_section("## Future WP145 Boundary")
    assert "WP145 — Hermes Candidate-Review Assisted Research Local Deterministic Harness Skeleton, Fake Provider Adapter, And No-Network Dry-Run V1" in future
    for phrase in (
        "local/offline test-oriented skeleton", "exact state machine",
        "test-only deterministic fake adapter", "one WP142 case", "`tmp_path` proof",
        "must not install or invoke Hermes", "call a provider or model", "use a credential",
        "run all cases", "persist output", "fetch sources", "trade", "implement WP146",
        "WP145 requires separate approval",
    ):
        assert phrase in future


def test_forbidden_interpretations_and_reviewer_traps_reject_activation_claims() -> None:
    interpretations = _section("## Forbidden Interpretations")
    assert len([line for line in interpretations.splitlines() if line.startswith("- ")]) == 15
    text = _read().lower()
    for false_claim in (
        "controller is implemented", "harness is implemented", "adapter is implemented",
        "fake adapter is implemented", "prompt is executable", "configuration is executable",
        "hermes runtime is activated", "provider is activated", "model is activated",
        "credential is created", "network call is authorized", "dry run was executed",
        "persistent memory is authorized", "raw persistence is authorized by default",
        "automatic downstream records are authorized", "automatic acceptance is authorized",
        "trading authority is granted", "wp145 is implemented",
    ):
        assert false_claim not in text


def test_docs_test_reads_markdown_only_and_imports_no_product_module() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    assert "from " + "src." not in source
    assert "import " + "src." not in source
    assert "sub" + "process" not in source
    assert "." + "json" not in source
