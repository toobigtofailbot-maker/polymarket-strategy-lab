"""Markdown-only tests for the WP143 provider/runtime governance decision."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / (
    "hermes_candidate_review_assisted_research_provider_runtime_privacy_permissions_budget_decision.md"
)

HEADINGS = (
    "# Hermes Candidate-Review Assisted Research Provider, Runtime, Privacy, Permissions, And Budget Decision",
    "## Purpose", "## Position After WP142", "## Authority And Non-Authority",
    "## Repository Inputs Reviewed", "## Decision Principles",
    "## Runtime Architecture Options", "## Selected Target Architecture",
    "## Provider Decision Posture", "## Provider Eligibility Criteria",
    "## Privacy And Data Classification",
    "## Retention, Jurisdiction, Logging, And Deletion", "## Permission Matrix",
    "## Credential And Secret Policy", "## Memory Policy", "## Network Policy",
    "## File And Repository Policy", "## Budget And Quota Envelope",
    "## Cost Accounting Requirements", "## Experiment Stop Conditions",
    "## Candidate Evaluation Criteria", "## Promotion Gates",
    "## Options Considered", "## Explicit Deferred Capabilities",
    "## Output Surface Inventory", "## Forbidden Interpretations",
    "## Future WP144 Boundary", "## Decision", "## Non-Authority Statement",
)

DECISIONS = (
    "Assisted-research architecture: LOCAL_DETERMINISTIC_CONTROL_PLANE_WITH_EPHEMERAL_HERMES_SESSION",
    "Model-access posture: PROVIDER_NEUTRAL_REMOTE_MODEL_CANDIDATES_WITH_OPTIONAL_LOCAL_BASELINE",
    "Provider decision: SHORTLIST_MAXIMUM_TWO_REMOTE_CANDIDATES_PLUS_OPTIONAL_ONE_LOCAL_BASELINE",
    "Provider activation: NOT AUTHORIZED",
    "Hermes installation/runtime activation: NOT AUTHORIZED",
    "Experiment data classification: SYNTHETIC_OFFLINE_TEST_DATA_ONLY",
    "Network posture for the first future experiment: PROVIDER_ENDPOINT_ONLY_DENY_ALL_OTHER_NETWORK",
    "Repository posture: NO_REPOSITORY_WIDE_ACCESS",
    "File posture: EXPLICIT_READ_ONLY_INPUT_BUNDLE_AND_SESSION_TEMP_DIRECTORY_ONLY",
    "Command and shell posture: DISABLED",
    "Tool posture: NO_BROWSER_NO_SEARCH_NO_SOURCE_FETCH_NO_TRADING_TOOLS",
    "Memory posture: EPHEMERAL_SESSION_MEMORY_ONLY",
    "Persistent memory: FORBIDDEN",
    "Raw prompt/output persistence: FORBIDDEN_UNLESS_SEPARATELY_APPROVED",
    "Credential posture: OUT_OF_REPO_OPERATOR_INJECTED_LEAST_PRIVILEGE_REVOCABLE_SECRET",
    "Deterministic validation and human review: MANDATORY",
    "Paper/live/execution authority: FORBIDDEN",
    "Maximum remote provider/model configurations: 2",
    "Maximum total remote calls: 140",
    "Maximum total experiment spend: USD 100",
    "Maximum daily spend: USD 25",
    "Maximum single-call spend: USD 2",
    "Concurrent remote calls: 1",
    "WP144 requires separate approval",
)

PERMISSIONS = (
    ("Read explicit WP142 case bundle", "ALLOW_READ_ONLY"),
    ("Read WP141/WP142 contract metadata", "ALLOW_READ_ONLY_EXACT_FILES"),
    ("Read repository generally", "DENY"), ("Write repository", "DENY"),
    ("Read arbitrary local files", "DENY"),
    ("Session temp directory", "ALLOW_EPHEMERAL_READ_WRITE"),
    ("Persistent output directory", "DENY"),
    ("Shell/command execution", "DENY"), ("Browser/search", "DENY"),
    ("External source retrieval", "DENY"),
    ("Provider API endpoint", "FUTURE_ALLOWLIST_ONE_ENDPOINT"),
    ("Other outbound network", "DENY"), ("Tool calls", "DENY"),
    ("Trading APIs", "DENY"), ("Wallet/account endpoints", "DENY"),
    ("Environment access", "DENY_EXCEPT_NAMED_SECRET_INJECTION_BY_CONTROLLER"),
    ("Persistent memory", "DENY"), ("Session memory", "ALLOW_EPHEMERAL"),
    ("Scheduler/background execution", "DENY"), ("Automatic retry", "DENY"),
    ("Automatic downstream record creation", "DENY"),
    ("Automatic acceptance", "DENY"),
)


def _read() -> str:
    return DOC.read_text(encoding="utf-8")


def _section(heading: str) -> str:
    text = _read()
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end == -1 else text[start:end]


def test_exact_title_heading_order_and_decision_tokens() -> None:
    text = _read()
    assert tuple(line for line in text.splitlines() if line.startswith("#")) == HEADINGS
    assert all(token in text for token in DECISIONS)


def test_all_runtime_options_and_selected_local_control_are_exact() -> None:
    options = _section("## Runtime Architecture Options")
    for classification in (
        "LOCAL_ONLY_LOCAL_MODEL: OPTIONAL_FUTURE_BASELINE_NOT_PRIMARY",
        "LOCAL_HERMES_REMOTE_MODEL: SELECTED_TARGET_ARCHITECTURE",
        "MANAGED_HOSTED_AGENT: REJECTED_FOR_INITIAL_EXPERIMENT",
        "DIRECT_MODEL_API_BASELINE: ALLOWED_AS_COMPARISON_BASELINE_ONLY",
    ):
        assert classification in options
    selected = _section("## Selected Target Architecture")
    for phrase in (
        "LOCAL_DETERMINISTIC_CONTROL_PLANE", "LOCAL_EPHEMERAL_HERMES_SESSION",
        "ONE_APPROVED_REMOTE_MODEL_ENDPOINT", "SYNTHETIC_WP142_CASE_INPUT",
        "NO_BROWSER_SEARCH_OR_SOURCE_TOOLS", "DETERMINISTIC_VALIDATION",
        "MANDATORY_HUMAN_REVIEW", "manually start", "no daemon", "scheduler",
        "repository-wide access", "persistent memory", "model-visible credential",
    ):
        assert phrase in selected
    assert "No option is authorized to run by WP143" in options


def test_provider_shortlist_and_all_eligibility_categories_are_locked() -> None:
    posture = _section("## Provider Decision Posture")
    for phrase in (
        "Maximum remote provider/model configurations: 2",
        "high-capability reasoning candidate", "lower-cost or latency-optimized",
        "optional local baseline", "DEFERRED_CURRENT_EXTERNAL_RESEARCH_REQUIRED",
        "CANDIDATE_ONLY", "separate approved experiment package",
    ):
        assert phrase in posture
    eligibility = _section("## Provider Eligibility Criteria")
    for phrase in (
        "Contract and privacy gates", "no-training control", "retention", "deletion",
        "data-processing jurisdiction", "subprocessors", "incident reporting",
        "30 days", "revocation", "Technical gates", "stable versioned API",
        "model/version identifier", "usage and cost reporting", "output limits",
        "timeout support", "request identifiers", "documented errors",
        "provider-hosted tools", "persistent memory", "repository connection",
        "Experiment-compatibility gates", "WP142 case size", "WP133 boundary",
        "browsing/source retrieval", "provider-neutral", "manual key revocation",
        "ineligible",
    ):
        assert phrase in eligibility


def test_privacy_retention_jurisdiction_logging_and_deletion_are_complete() -> None:
    privacy = _section("## Privacy And Data Classification")
    for phrase in (
        "SYNTHETIC_NON_PERSONAL_NON_CONFIDENTIAL",
        "MUST_BE_DISABLED_OR_CONTRACTUALLY_EXCLUDED", "Personal data: FORBIDDEN",
        "Credentials in prompt or model-visible context: FORBIDDEN",
        "Real wallet/account/order data: FORBIDDEN", "invented WP142 material",
    ):
        assert phrase in privacy
    retention = _section("## Retention, Jurisdiction, Logging, And Deletion")
    for phrase in (
        "Preferred provider retention: ZERO_RETENTION",
        "Maximum acceptable standard retention: 30_DAYS",
        "MUST_BE_DOCUMENTED_BEFORE ACTIVATION",
        "MUST_BE_DOCUMENTED_AND_OPERATOR_VERIFIED_AFTER_EXPERIMENT",
        "case ID", "fixture/rubric versions", "provider request ID", "stop reason",
        "API keys", "authorization headers", "raw provider payloads",
        "ephemeral session directory", "Stable raw-output persistence requires separate approval",
    ):
        assert phrase in retention


def test_exact_permission_matrix_and_future_only_posture() -> None:
    section = _section("## Permission Matrix")
    assert "future permissions, not active capabilities" in section
    for capability, decision in PERMISSIONS:
        assert f"| {capability} | {decision} |" in section


def test_credential_memory_network_and_file_policies_are_complete() -> None:
    credentials = _section("## Credential And Secret Policy")
    for phrase in (
        "Credential storage: OUTSIDE_REPOSITORY",
        "Credential delivery: OPERATOR_INJECTED_AT_SESSION_START",
        "Credential visibility to Hermes/model: FORBIDDEN",
        "LEAST_PRIVILEGE_SINGLE_PROVIDER_EXPERIMENT_ONLY",
        "TEMPORARY_AND_REVOCABLE", "Credential logging: FORBIDDEN",
        "Credential persistence: FORBIDDEN", "revoke the experiment key",
        "never reuse production or trading credentials", "creates no secret",
    ):
        assert phrase in credentials
    memory = _section("## Memory Policy")
    for phrase in (
        "Cross-session memory: DISABLED", "Provider-hosted memory: DISABLED",
        "Hermes persistent memory: DISABLED", "Session-local scratch memory: ALLOWED_EPHEMERAL",
        "Memory deletion: MANDATORY_AT_SESSION_END", "No run may rely on prior-run context",
    ):
        assert phrase in memory
    network = _section("## Network Policy")
    for phrase in (
        "Default outbound network: DENY",
        "Permitted future outbound destination: ONE_EXPLICIT_PROVIDER_API_ENDPOINT",
        "Browser/search endpoints: DENY", "Source URLs: DENY",
        "Redirects to unapproved domains: DENY", "Provider-hosted tool execution: DENY",
        "DNS/network failure behavior: FAIL_CLOSED", "authorizes no network call",
    ):
        assert phrase in network
    files = _section("## File And Repository Policy")
    for phrase in (
        "no repository-wide mount", "`.git` access", "source-tree traversal",
        "home-directory", "environment dump", "arbitrary path input",
        "model-controlled path or filename", "symlink", "archive extraction",
        "executable-file creation", "exact read-only input bundle",
        "delete the directory", "implements none of these controls",
    ):
        assert phrase in files


def test_budget_calls_retries_money_tokens_latency_and_concurrency_are_exact() -> None:
    budget = _section("## Budget And Quota Envelope")
    for phrase in (
        "Optional local baseline configurations: 1", "Gold cases: 20",
        "Required repeated runs per case per remote configuration: 3",
        "Maximum planned remote primary calls: 120",
        "20 cases × 3 runs × 2 remote configurations = 120",
        "Maximum retry per failed case/run: 1", "Maximum total retry calls: 20",
        "provider transport failure", "documented transient provider error",
        "deterministic timeout", "forbidden for low quality", "unsafe output",
        "Automatic top-up: FORBIDDEN", "Budget warning threshold: 80_PERCENT",
        "Budget hard stop: 100_PERCENT", "Maximum input tokens per call: 50000",
        "Maximum output tokens per call: 8000", "Maximum request timeout: 180_SECONDS",
        "Maximum end-to-end case-run duration: 300_SECONDS",
        "no spend is authorized by WP143", "may lower but not raise",
    ):
        assert phrase in budget


def test_cost_accounting_stops_evaluation_and_promotion_gates_are_complete() -> None:
    accounting = _section("## Cost Accounting Requirements")
    for phrase in (
        "case ID", "run number", "candidate configuration ID", "provider request ID",
        "input tokens", "output tokens", "cached token/compute", "latency",
        "retry status", "provider-reported cost", "independently calculated",
        "cumulative daily cost", "cumulative experiment cost", "budget warning",
        "stop status", "exclude secrets", "no provider invoice",
    ):
        assert phrase in accounting
    stops = _section("## Experiment Stop Conditions")
    for phrase in (
        "secret exposure", "training use", "retention or jurisdiction",
        "non-allowlisted network", "browser/search/source/tool", "repository-wide",
        "shell", "persistent memory", "raw-output persistence", "input mutation",
        "automatic WP122/WP123", "validation or human-review bypass",
        "recommendation/probability/trading/execution", "USD 100", "USD 25",
        "USD 2", "140", "timeout", "provider/model/version", "terms/privacy",
        "human stop decision",
    ):
        assert phrase in stops
    evaluation = _section("## Candidate Evaluation Criteria")
    for phrase in (
        "fail-closed", "no-training", "hard-gate pass rate", "expected-outcome rate",
        "aggregate scores", "WP133 validation rate", "human correction burden",
        "refusal quality", "fabricated citations", "source-access misrepresentation",
        "repeatability", "latency", "cost", "operational failure rate",
        "no production provider selection",
    ):
        assert phrase in evaluation
    gates = _section("## Promotion Gates")
    for group in ("Repository:", "Architecture:", "Privacy:", "Budget:", "Safety:", "Evidence:"):
        assert group in gates
    for phrase in (
        "WP141, WP142, and WP143 merged", "exact endpoint allowlist", "no-training",
        "operator approval recorded outside", "no shell/browser/search/source",
        "emergency stop", "key revocation", "exact provider/model/version",
        "raw-output handling", "Failure of one gate blocks",
    ):
        assert phrase in gates


def test_options_deferrals_inventory_interpretations_and_wp144_gate_are_complete() -> None:
    options = _section("## Options Considered")
    for area in (
        "Control plane", "Hermes runtime", "Model access", "Local model", "Data",
        "Network", "Files", "Commands", "Memory", "Credentials", "Raw output",
        "Budget", "Concurrency", "Trading",
    ):
        assert f"| {area} |" in options
    deferred = _section("## Explicit Deferred Capabilities")
    for phrase in (
        "Hermes installation", "provider account selection", "provider contract acceptance",
        "model selection", "API key creation", "secret-store selection",
        "prompt/config package", "provider adapter", "experiment controller",
        "endpoint allowlist implementation", "sandbox implementation",
        "file permission enforcement", "network enforcement", "cost limiter",
        "logging implementation", "raw-output policy", "provider call",
        "WP142 case execution", "provider comparison result", "persistent storage",
        "source retrieval", "citation verification", "real market or wallet research",
        "paper/live trading", "order placement or cancel", "strategy promotion",
        "AI acceptance or risk authority",
    ):
        assert phrase in deferred
    inventory = _section("## Output Surface Inventory")
    for phrase in (
        "Markdown decision record", "Markdown-only focused test", "stable WP143 status",
        "source/tool/workflow", "provider SDK/config", "credential", "runtime harness",
        "fixture execution", "model/network/raw experiment output", "storage/database",
        "CLI/scheduler", "recommendation/probability/ranking",
        "paper/live/execution/risk/order",
    ):
        assert phrase in inventory
    interpretations = _section("## Forbidden Interpretations")
    assert len([line for line in interpretations.splitlines() if line.startswith("- ")]) == 12
    future = _section("## Future WP144 Boundary")
    assert "WP144 — Hermes Candidate-Review Assisted Research Controlled Experiment Harness Contract, Prompt/Configuration Boundary, And Dry-Run Plan V1" in future
    for phrase in (
        "must not install Hermes", "create a real provider credential", "call a paid model",
        "execute all 20 cases", "fetch sources", "persist raw output", "trade",
        "implement WP145", "WP144 requires separate approval",
    ):
        assert phrase in future


def test_reviewer_trap_authorizations_are_absent() -> None:
    text = _read().lower()
    for false_claim in (
        "hermes is installed", "provider is activated", "provider selected:",
        "model selected:", "provider call is authorized", "secret in the repository is authorized",
        "secret in model-visible content is authorized", "browser/search is authorized",
        "source retrieval is authorized", "repository-wide access is authorized",
        "shell commands are authorized", "persistent memory is authorized",
        "raw-output persistence is authorized by default", "automatic downstream records are authorized",
        "recommendation authority: granted", "probability authority: granted",
        "trading authority: granted", "wp144 is implemented",
    ):
        assert false_claim not in text
    assert "Maximum remote provider/model configurations: 3" not in text
    assert "Concurrent remote calls: 2" not in text
    assert "Maximum total experiment spend: USD 101" not in text


def test_docs_test_reads_markdown_only_and_imports_no_product_module() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    assert "from " + "src." not in source
    assert "import " + "src." not in source
    assert '.json")' + ".read_text" not in source
