"""Focused Markdown-only tests for the WP140 closeout decision record."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / (
    "hermes_candidate_review_manual_six_record_workflow_closeout_and_"
    "assisted_research_transition_decision_record.md"
)

HEADINGS = [
    "# Hermes Candidate-Review Manual Six-Record Workflow Closeout And Assisted-Research Transition Decision Record",
    "## Purpose",
    "## Position After WP139",
    "## Authority And Non-Authority",
    "## Repository Layers Reviewed",
    "## Manual Workflow Coverage",
    "## Closeout Criteria",
    "## Manual Workflow Closeout Decision",
    "## Default Chain-Extension Decision",
    "## Options Considered",
    "## Selected Next Phase",
    "## Why Hermes Runtime Is Not Activated",
    "## Deterministic Authority Boundary",
    "## Future WP141 Experiment Contract",
    "## Future Input Boundary",
    "## Future Output Boundary",
    "## Future Quality And Evaluation Questions",
    "## Explicit Deferred Capabilities",
    "## No Source, Smoke, Or Runtime Change",
    "## Output Surface Inventory",
    "## Forbidden Interpretations",
    "## Stop Conditions",
    "## Future Gates",
    "## Decision",
    "## Non-Authority Statement",
]


def _read() -> str:
    return DOC.read_text(encoding="utf-8")


def _section(heading: str) -> str:
    text = _read()
    start = text.index(heading)
    following = [text.find("\n## ", start + len(heading))]
    end = min(index for index in following if index != -1) if any(
        index != -1 for index in following
    ) else len(text)
    return text[start:end]


def test_exact_title_and_heading_order() -> None:
    text = _read()
    assert text.splitlines()[0] == HEADINGS[0]
    assert [line for line in text.splitlines() if line.startswith("#")] == HEADINGS


def test_locked_closeout_decisions_are_exact() -> None:
    text = _read()
    for statement in (
        "Manual six-record workflow status: CLOSED_COMPLETE_ENOUGH_FOR_BOUNDED_MANUAL_USE",
        "Default manual-chain extension: STOP",
        "Next phase: HERMES_ASSISTED_RESEARCH_EXPERIMENT_CONTRACT",
        "Hermes installation/runtime activation: NOT AUTHORIZED",
        "Deterministic validation and safety authority: UNCHANGED",
        "Hermes paper/live/execution authority: FORBIDDEN",
        "WP141 requires separate approval",
        "WP140 changes no source",
        "WP140 implements no smoke",
        "WP140 activates no runtime",
    ):
        assert statement in text


def test_six_record_topology_and_full_manual_coverage_are_recorded() -> None:
    text = _read()
    topology = (
        "WP121 research-question record\n"
        "→ WP132 manual research request\n"
        "→ WP133 manual research response\n"
        "→ WP122 advisory-output validation receipt\n"
        "→ WP123 human decision record\n"
        "→ WP123 follow-up research task record"
    )
    assert topology in text
    coverage = _section("## Manual Workflow Coverage")
    for surface in (
        "intake", "selection", "briefing", "question", "request", "response",
        "validation", "human-decision", "follow-up-task",
    ):
        assert surface in coverage
    assert "No evidence-backed missing lineage record" in coverage


def test_closeout_criteria_table_is_complete() -> None:
    section = _section("## Closeout Criteria")
    rows = (
        ("Explicit candidate intake", "WP118", "SATISFIED"),
        ("Candidate queue/selection", "WP124–WP129", "SATISFIED"),
        ("Briefing contract/operator proof", "WP130–WP131", "SATISFIED"),
        ("Explicit research request", "WP132", "SATISFIED"),
        ("Explicit research response", "WP133–WP134", "SATISFIED"),
        ("Request-response linkage", "WP135", "SATISFIED"),
        ("Question/receipt lineage decision", "WP136", "SATISFIED"),
        ("Four-record structural proof", "WP137", "SATISFIED"),
        ("Human-decision/task extension decision", "WP138", "SATISFIED"),
        ("Six-record structural proof", "WP139", "SATISFIED"),
        ("Deterministic validation authority", "WP95–WP99/contracts", "PRESERVED"),
        ("Human review", "manual records", "REQUIRED"),
        ("Runtime/model/provider behavior", "none", "NOT STARTED"),
        ("Source fetching/verification", "none", "NOT IMPLEMENTED"),
        ("Storage/persistence", "none in this phase", "NOT IMPLEMENTED"),
        ("Trading authority", "deterministic core only", "FORBIDDEN TO HERMES"),
    )
    for criterion, evidence, result in rows:
        assert f"| {criterion} | {evidence} | {result} |" in section


def test_options_stop_default_extension_and_select_provider_neutral_contract() -> None:
    section = _section("## Options Considered")
    for phrase in (
        "Continue adding manual lineage records | REJECTED AS DEFAULT",
        "Install or activate Hermes immediately | REJECTED",
        "Harden WP121/WP122/WP123 now | DEFERRED TO SEPARATE GAP-DRIVEN PACKAGE",
        "Define a provider-neutral assisted-research experiment contract | SELECTED",
    ):
        assert phrase in section
    assert "No seventh record" in _section("## Default Chain-Extension Decision")
    selected = _section("## Selected Next Phase")
    assert "provider-neutral, runtime-inactive contract-definition package" in selected
    assert "not authorization to implement or run it in WP140" in selected


def test_wp141_input_and_output_boundaries_are_fail_closed() -> None:
    inputs = _section("## Future Input Boundary")
    for phrase in (
        "valid WP121 research-question record",
        "valid WP132 manual research request",
        "valid WP130 briefing reference or sanitized briefing content",
        "operator-supplied synthetic/reference bundle",
        "raw secrets", "private account/order state", "automatic source expansion",
        "uncontrolled repository access", "direct trading-state input",
    ):
        assert phrase in inputs
    outputs = _section("## Future Output Boundary")
    for phrase in (
        "untrusted research draft corresponding to the WP133 response shape",
        "untrusted until deterministic validation and human review",
        "no automatic WP133 acceptance",
        "no automatic WP122 receipt",
        "no automatic WP123 decision or task generation",
        "no persistence unless separately approved",
        "may not bypass WP133 validation",
    ):
        assert phrase in outputs


def test_all_future_quality_questions_are_required() -> None:
    section = _section("## Future Quality And Evaluation Questions")
    for metric in (
        "schema compliance", "citation completeness", "source provenance disclosure",
        "claim-to-source traceability", "unsupported-claim rate",
        "uncertainty-calibration language", "missing-data disclosure",
        "falsification effort", "refusal quality",
        "hallucination/unsupported-content incidence", "human-review usefulness",
        "time saved versus manual research", "latency", "token/compute/API cost",
        "repeatability", "deterministic-validator pass rate",
    ):
        assert metric in section
    assert "No metric grants acceptance, trading, or execution authority" in section


def test_deferred_capabilities_and_deterministic_authority_are_complete() -> None:
    deferred = _section("## Explicit Deferred Capabilities")
    for capability in (
        "Hermes installation", "model/provider selection", "API keys",
        "internet browsing", "source retrieval", "citation verification",
        "wallet-analysis execution", "market-data ingestion",
        "automated candidate selection", "scheduler/background research",
        "storage/database", "report publication", "paper/live trading",
        "order placement/cancel", "strategy promotion", "AI risk override",
    ):
        assert capability in deferred
    authority = _section("## Deterministic Authority Boundary")
    for owner in (
        "input/output validation", "acceptance/rejection", "risk", "state",
        "accounting", "credentials", "order lifecycle", "paper/live controls",
        "live safety", "strategy promotion",
    ):
        assert owner in authority


def test_reviewer_traps_remain_forbidden() -> None:
    text = _read()
    required_prohibitions = (
        "No seventh record",
        "No model or provider is selected or configured",
        "may not install Hermes, select or configure a provider/model, create credentials",
        "no automatic WP133 acceptance",
        "no automatic WP122 receipt",
        "no automatic WP123 decision or task generation",
        "cannot accept itself or bypass deterministic and human review",
        "Hermes paper/live/execution authority: FORBIDDEN",
        "selected next phase is not implemented by WP140",
        "not factual readiness",
        "not trading readiness",
    )
    for phrase in required_prohibitions:
        assert phrase in text
    forbidden_authorizations = (
        "seventh record is authorized",
        "Hermes runtime is activated",
        "provider selected:",
        "model selected:",
        "credentials are authorized",
        "source fetching is authorized",
        "automatic WP133 acceptance is authorized",
        "automatic WP122 receipt is authorized",
        "automatic WP123 decision is authorized",
        "Hermes controls deterministic validation",
        "Hermes may place paper or live trades",
        "WP141 is implemented by WP140",
        "factually ready",
        "trading ready",
    )
    lowered = text.lower()
    for phrase in forbidden_authorizations:
        assert phrase.lower() not in lowered


def test_docs_test_reads_markdown_only_and_imports_no_product_module() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    assert "from " + "src." not in source
    assert "import " + "src." not in source
