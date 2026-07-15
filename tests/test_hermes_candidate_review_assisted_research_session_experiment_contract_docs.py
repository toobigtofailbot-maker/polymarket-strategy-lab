"""Focused Markdown-only tests for the WP141 experiment contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / (
    "hermes_candidate_review_assisted_research_session_experiment_contract.md"
)

HEADINGS = [
    "# Hermes Candidate-Review Assisted Research Session Experiment Contract",
    "## Purpose",
    "## Position After WP140",
    "## Status And Authority",
    "## Experiment Objective",
    "## Provider-Neutral And Runtime-Inactive Posture",
    "## Existing Deterministic Contracts",
    "## Approved Input Families",
    "## Required Input Preconditions",
    "## Prohibited Inputs",
    "## Assisted Draft Output Boundary",
    "## WP133 Shape Alignment",
    "## Untrusted-Draft Rule",
    "## Source And Citation Disclosure Requirements",
    "## Claim-To-Source Traceability Requirements",
    "## Uncertainty, Missing-Data, And Falsification Requirements",
    "## Refusal And Failure Behavior",
    "## Human Review Rubric",
    "## Deterministic Validation Gates",
    "## Experiment Case Families",
    "## Quality Metrics",
    "## Cost And Latency Accounting",
    "## Repeatability And Comparison Requirements",
    "## Privacy, Credential, And Repository Boundaries",
    "## Experiment Stop Conditions",
    "## Promotion Criteria",
    "## Explicit Deferred Capabilities",
    "## Output Surface Inventory",
    "## Forbidden Interpretations",
    "## Future WP142 Boundary",
    "## Decision",
    "## Non-Authority Statement",
]

WP133_FIELDS = (
    "response_id", "source_wp_context", "source_request_reference",
    "source_briefing_packet_reference", "selected_candidate_reference",
    "response_label", "research_question", "research_question_type",
    "question_restatement", "source_summary", "resolution_rule_analysis",
    "evidence_for", "evidence_against", "source_conflicts", "uncertainties",
    "known_missing_data", "falsification_checks_performed", "limitations",
    "what_would_change_the_conclusion", "operator_review_notes",
    "cited_source_references", "source_assessment_labels", "completion_labels",
    "response_sections", "operator_next_manual_step", "reviewer_acknowledgement",
    "human_review_required", "created_by_operator_note", "non_authority_notice",
    "safety_flags",
)


def _read() -> str:
    return DOC.read_text(encoding="utf-8")


def _raw_section(heading: str) -> str:
    text = _read()
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end == -1 else text[start:end]


def _section(heading: str) -> str:
    return " ".join(_raw_section(heading).split())


def test_exact_title_and_heading_order() -> None:
    lines = _read().splitlines()
    assert lines[0] == HEADINGS[0]
    assert [line for line in lines if line.startswith("#")] == HEADINGS


def test_locked_decisions_and_foundation_relationships_are_exact() -> None:
    text = _read()
    for statement in (
        "Experiment contract status: PROVIDER_NEUTRAL_RUNTIME_INACTIVE",
        "Assisted output status: UNTRUSTED_DRAFT_ONLY",
        "Deterministic validation: MANDATORY_BEFORE_ACCEPTANCE",
        "Human review: MANDATORY_BEFORE_ANY_DOWNSTREAM_HANDOFF",
        "Hermes installation/runtime activation: NOT AUTHORIZED",
        "Provider/model selection: NOT AUTHORIZED",
        "Network/source fetching: NOT AUTHORIZED",
        "Persistence/storage: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN",
        "WP142 requires separate approval",
    ):
        assert statement in text
    position = _section("## Position After WP140")
    for wp in ("WP95", "WP96", "WP97", "WP98", "WP118–WP139", "WP140"):
        assert wp in position


def test_approved_inputs_preconditions_and_prohibited_inputs_are_complete() -> None:
    approved = _section("## Approved Input Families")
    for phrase in (
        "valid WP121 research-question record", "valid WP132 manual research request",
        "valid WP130 briefing reference or sanitized briefing content",
        "operator-supplied source-reference bundle",
        "operator-supplied synthetic source excerpts for offline evaluation",
        "exact safety and non-authority constraints", "experiment case ID",
        "caller-supplied and are not verified",
    ):
        assert phrase in approved
    preconditions = _section("## Required Input Preconditions")
    for phrase in (
        "WP121 validation", "WP132 validation", "lineage is consistent",
        "`human_review_required`", "source, citation, word, timeout, and retry budgets",
        "known uncertainties and missing data", "refusal and failure behavior",
        "approved for that case", "No missing input may be inferred",
    ):
        assert phrase in preconditions
    prohibited = _section("## Prohibited Inputs")
    for phrase in (
        "API keys", "tokens", "passwords", "private keys", "seed phrases",
        "mnemonic phrases", "passphrases", "private endpoints", "wallet/account/order/",
        "secret-bearing runtime logs", "unrestricted repository access",
        "uncontrolled file trees", "raw arbitrary metadata", "direct trading-state input",
        "auto-discovered or unapproved URLs", "executable order instructions",
        "hidden system prompts", "provider-specific configuration",
        "unapproved personal data",
    ):
        assert phrase in prohibited


def test_wp133_alignment_names_all_30_fields_and_remains_untrusted() -> None:
    alignment = _raw_section("## WP133 Shape Alignment")
    assert len(WP133_FIELDS) == 30
    for index, field in enumerate(WP133_FIELDS, start=1):
        assert f"{index}. `{field}`" in alignment
    assert "WP141 creates no schema, validator, or draft" in alignment
    boundary = _section("## Assisted Draft Output Boundary")
    for phrase in (
        "Matching WP133 keys does not make the draft valid",
        "existing deterministic WP133 validator must run separately",
        "original inputs must remain unchanged",
        "No WP122 receipt or WP123 decision or task may be created automatically",
        "may not claim factual correctness, recommendation, probability",
        "may not be persisted without separate approval",
    ):
        assert phrase in boundary
    rule = _raw_section("## Untrusted-Draft Rule")
    assert [line.split(". ", 1)[0] for line in rule.splitlines() if line[:1].isdigit()] == [
        str(index) for index in range(1, 8)
    ]
    assert "No assisted system may approve itself" in rule


def test_disclosure_traceability_uncertainty_and_failure_are_complete() -> None:
    disclosure = _section("## Source And Citation Disclosure Requirements")
    for phrase in (
        "supplied reference", "supplied excerpt", "unavailable source",
        "access not attempted", "primary source", "official source", "secondary source",
        "conflicting source", "stale source", "undated source",
        "unsupported material claim", "missing citation", "citation/source mismatch",
        "not source or citation verification",
    ):
        assert phrase in disclosure
    traceability = _section("## Claim-To-Source Traceability Requirements")
    for phrase in (
        "claim ID or reference", "supporting sources", "contradicting sources",
        "support status", "citation status", "uncertainty note", "human-review status",
        "no machine-readable traceability schema",
    ):
        assert phrase in traceability
    uncertainty = _section("## Uncertainty, Missing-Data, And Falsification Requirements")
    for phrase in (
        "uncertainties", "missing data", "source conflicts", "assumptions", "limitations",
        "falsification checks performed", "falsification checks not performed",
        "what evidence would change the conclusion", "refusal or defer reason",
        "must not reward unsupported confidence",
    ):
        assert phrase in uncertainty
    failure = _section("## Refusal And Failure Behavior")
    for phrase in (
        "missing or invalid inputs", "unsafe content", "forbidden authority language",
        "insufficient supplied material", "conflicting sources", "unsupported claims",
        "source reference without supplied offline content", "timeout/budget/retry limits",
        "unavailable provider/tool/runtime", "output-shape failure",
        "deterministic rejection", "human-review rejection", "must not fabricate sources",
        "echo secrets or unsafe input", "create downstream records",
    ):
        assert phrase in failure


def test_human_review_and_deterministic_gates_are_complete() -> None:
    review = _section("## Human Review Rubric")
    categories = (
        "question fidelity", "scope compliance", "source disclosure",
        "citation completeness", "claim/source traceability", "evidence for",
        "evidence against", "conflicting-source handling", "uncertainty quality",
        "missing-data disclosure", "falsification effort", "limitations",
        "unsupported claims", "refusal appropriateness",
        "usefulness for the next manual step", "absence of forbidden authority",
    )
    for index, category in enumerate(categories, start=1):
        assert f"{index}. {category}" in review
    for outcome in (
        "acceptable for deterministic WP133 validation", "needs source recheck",
        "needs citation review", "needs evidence review", "needs scope reduction",
        "deferred", "rejected unsafe/forbidden",
    ):
        assert outcome in review
    gates = _section("## Deterministic Validation Gates")
    for phrase in (
        "inputs were valid before the run", "WP133 validation passes",
        "safety flags are exact", "unknown, raw, and free-form fields are rejected",
        "fails closed without echo", "recommendation, probability, and execution authority",
        "human review is complete", "WP122/WP123 artifacts are separately authored",
    ):
        assert phrase in gates


def test_case_families_metrics_and_zero_incidence_gates_are_complete() -> None:
    cases = _section("## Experiment Case Families")
    for case in (
        "complete supported case", "conflicting-source case", "known-missing-data case",
        "resolution ambiguity case", "source-provenance weakness case",
        "falsification-focused case", "insufficient supplied material",
        "unsupported claim request", "unsafe authority request",
        "credential/private-data trap", "out-of-scope request", "timeout/budget limit",
        "fabricated-citation temptation", "stale-source ambiguity",
        "contradictory excerpts", "misleading source title",
        "prompt-injection-like excerpt", "embedded trading instruction",
        "raw-metadata/extras attempt", "overconfident weakly supported conclusion",
        "WP141 creates no cases or fixture data",
    ):
        assert case in cases
    metrics = _section("## Quality Metrics")
    for metric in (
        "WP133 shape compliance", "validator pass rate", "source-disclosure completeness",
        "citation completeness", "claim/source traceability", "unsupported-claim rate",
        "fabricated-source incidence", "fabricated-citation incidence",
        "conflict disclosure", "uncertainty quality", "missing-data disclosure",
        "falsification coverage", "limitation quality", "appropriate refusal",
        "unsafe-output incidence", "secret/unsafe echo incidence",
        "human-review usefulness", "human correction burden", "manual time saved",
        "repeatability",
    ):
        assert metric in metrics
    for gate in (
        "forbidden authority incidence: `0`", "credential/private-data leakage: `0`",
        "unsafe-input echo: `0`", "fabricated citation: `0`",
        "fabricated source-access claim: `0`", "automatic downstream-record creation: `0`",
        "deterministic validator bypass: `0`", "input mutation: `0`",
        "persistent output without approval: `0`", "human review required: `100%`",
    ):
        assert gate in metrics
    assert "does not invent unsupported performance percentages" in metrics


def test_cost_repeatability_privacy_stops_promotion_and_deferrals_are_complete() -> None:
    cost = _section("## Cost And Latency Accounting")
    for phrase in (
        "provider, model, and version identity", "local or remote mode",
        "input/output token or equivalent counts", "end-to-end latency",
        "retries and failures", "actual or estimated cost", "budget cap",
        "cache use", "operator and reviewer time", "case ID", "rubric version",
        "prompt-pack version", "validator version", "repeated-run variance",
        "authorizes no paid call",
    ):
        assert phrase in cost
    repeatability = _section("## Repeatability And Comparison Requirements")
    for phrase in ("fixed case IDs", "unchanged approved inputs", "identical budgets",
                   "repeated runs", "variance reporting", "separate human-review records"):
        assert phrase in repeatability
    privacy = _section("## Privacy, Credential, And Repository Boundaries")
    for phrase in (
        "no credentials", "unrestricted repository read", "repository write",
        "command access", "environment-variable access", "personal-file access",
        "browser-history access", "external upload without approval",
        "persistent memory without approval", "retention, privacy, jurisdiction, logging, and deletion",
    ):
        assert phrase in privacy
    stops = _section("## Experiment Stop Conditions")
    for phrase in (
        "detected secret or credential", "forbidden authority request or output",
        "unrecorded source-access claim", "fabricated source or citation",
        "automatic acceptance or downstream creation", "repeated deterministic rejection",
        "unsafe echo", "input mutation", "budget or timeout cap", "unauthorized persistence",
        "non-repeatable provider behavior", "human safety/usefulness rejection",
        "repo-truth/evidence inconsistency",
    ):
        assert phrase in stops
    promotion = _section("## Promotion Criteria")
    for phrase in (
        "authorizes no runtime promotion", "WP142 is approved",
        "deterministically enforceable under a separate WP", "privacy and retention",
        "provider and model options are compared", "budget is approved",
        "network/source permissions", "file, command, and memory permissions",
        "zero-incidence gates", "human reviewers accept the rubric",
        "repo truth is updated through a separate WP",
    ):
        assert phrase in promotion
    deferred = _section("## Explicit Deferred Capabilities")
    for phrase in (
        "Hermes installation", "provider/model selection", "prompt execution", "API keys",
        "source retrieval", "citation verification", "market or wallet ingestion",
        "automated selection", "persistent memory", "file writing", "scheduler/background",
        "paid API use", "paper/live trading", "order lifecycle", "strategy promotion",
        "AI acceptance or risk authority",
    ):
        assert phrase in deferred


def test_forbidden_interpretations_wp142_gate_and_no_implementation_are_exact() -> None:
    interpretations = _section("## Forbidden Interpretations")
    for phrase in (
        "experiment contract does not mean executed experiment",
        "assisted output does not mean accepted output",
        "WP133 alignment does not mean WP133 validity",
        "source reference does not mean source verification",
        "citation present does not mean claim supported",
        "human useful does not mean factually correct",
        "provider-neutral does not mean providers equivalent",
        "promotion criteria do not mean promotion authorization",
        "future network permission does not mean current network access",
        "research brain does not mean execution controller",
    ):
        assert phrase in interpretations
    future = _section("## Future WP142 Boundary")
    assert "WP142 — Hermes Candidate-Review Assisted Research Experiment Gold-Case Fixture Pack And Evaluation Rubric V1" in future
    assert "WP142 requires separate approval" in future
    for prohibition in (
        "may not install Hermes", "select a provider", "call a model", "fetch sources",
        "use credentials", "persist runtime output", "trade", "implement WP143",
    ):
        assert prohibition in future
    inventory = _section("## Output Surface Inventory")
    for phrase in (
        "no source", "schema", "validator", "prompt", "fixture", "smoke test",
        "runtime", "credential", "fetched source", "stored output", "model response",
        "trading artifact",
    ):
        assert phrase in inventory


def test_reviewer_trap_authorizations_are_absent() -> None:
    text = _read().lower()
    forbidden_authorizations = (
        "hermes runtime is authorized", "provider selected:", "model selected:",
        "credentials are authorized", "prompt execution is authorized",
        "source fetching is authorized", "sources are verified",
        "assisted output status: trusted", "automatic wp122 receipt is authorized",
        "automatic wp123 decision is authorized", "persistence is authorized",
        "recommendation authority: granted", "probability authority: granted",
        "ranking authority: granted", "trading authority: granted",
        "wp142 is implemented by wp141",
    )
    for phrase in forbidden_authorizations:
        assert phrase not in text


def test_docs_test_reads_markdown_only_and_imports_no_product_module() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    assert "from " + "src." not in source
    assert "import " + "src." not in source
    assert ".py\").read_text" not in source
