import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / (
    "hermes_candidate_review_assisted_research_current_provider_model_privacy_"
    "retention_cost_endpoint_research_and_candidate_shortlist.md"
)

TITLE = (
    "# Hermes Candidate-Review Assisted Research Current Provider/Model, Privacy, "
    "Retention, Cost, And Endpoint Research With Candidate Shortlist"
)

HEADINGS = [
    TITLE,
    "## Purpose",
    "## Position After WP146",
    "## Authority And Non-Authority",
    "## Repository Inputs Reviewed",
    "## Research Method",
    "## Research Cut-Off And Freshness",
    "## Source Hierarchy",
    "## Source Registry",
    "## Candidate Pool Construction",
    "## Hermes Compatibility Evidence",
    "## Mandatory Eligibility Criteria",
    "## Remote Candidate Evidence",
    "## Privacy, Training, Retention, And Deletion",
    "## Jurisdiction, Subprocessors, And Security",
    "## API, Model Version, Errors, Limits, And Observability",
    "## Endpoint And Network Restriction Feasibility",
    "## Credential And Key-Lifecycle Evidence",
    "## Pricing And Cost Model",
    "## WP143 Budget Compatibility",
    "## Optional Local Baseline",
    "## Candidate Eligibility Matrix",
    "## Eligible Candidate Comparison",
    "## Candidate Shortlist",
    "## Candidate-Specific Blockers",
    "## Cross-Cutting Remote-Implementation Blockers",
    "## Readiness Decision",
    "## Promotion Gates",
    "## Explicit Deferred Capabilities",
    "## Output Surface Inventory",
    "## Forbidden Interpretations",
    "## Future WP148 Boundary",
    "## Decision",
    "## Non-Authority Statement",
]

SOURCE_FIELDS = [
    "source_id",
    "candidate_id",
    "evidence_category",
    "publisher",
    "document_title",
    "canonical_url",
    "accessed_at_utc",
    "document_effective_date_or_last_updated",
    "source_tier",
    "claim_supported",
    "direct_or_inferred",
    "freshness_status",
    "notes",
]

DECISION_TOKENS = [
    "WP147 research status:\nCOMPLETE",
    "Research cut-off:\n2026-07-22T21:55:02Z",
    "Candidate pool posture:\nCURRENT_AUTHORITATIVE_FIRST_PARTY_RESEARCH_ONLY",
    "Provider decision:\nSHORTLIST_MAXIMUM_TWO_REMOTE_CANDIDATES_PLUS_OPTIONAL_ONE_LOCAL_BASELINE",
    "Candidate shortlist decision:\nSHORTLIST_TWO_ELIGIBLE_REMOTE_CONFIGURATIONS",
    "Remote controlled experiment readiness: NOT_READY",
    "Provider/model activation: NOT AUTHORIZED",
    "Provider/model call: NOT AUTHORIZED",
    "Hermes installation/invocation: NOT AUTHORIZED",
    "Provider account creation: NOT AUTHORIZED",
    "Credential creation/use: NOT AUTHORIZED",
    "Network endpoint activation: NOT AUTHORIZED",
    "Experiment spending: NOT AUTHORIZED",
    "Raw input/output persistence: NOT AUTHORIZED",
    "Paper/live/execution authority: FORBIDDEN",
    "Next phase:\nCANDIDATE_SELECTION_CONFIGURATION_PRIVACY_EVIDENCE_AND_OPERATOR_APPROVAL_DECISION",
    "WP148 requires separate approval",
    "Local baseline decision:\nDEFERRED_HARDWARE_EVIDENCE_MISSING",
]


def _read() -> str:
    return DOC.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _section(text: str, heading: str, next_heading: str) -> str:
    return text.split(heading, 1)[1].split(next_heading, 1)[0]


def _source_records(text: str) -> list[dict[str, str]]:
    registry = _section(text, "## Source Registry", "## Candidate Pool Construction")
    body = registry.split("```text", 1)[1].split("```", 1)[0]
    records = []
    for raw_record in re.split(r"\n---\n", body.strip()):
        record: dict[str, str] = {}
        for line in raw_record.splitlines():
            if ": " in line:
                key, value = line.split(": ", 1)
                record[key] = value
        records.append(record)
    return records


def _eligibility_rows(text: str) -> list[list[str]]:
    matrix = _section(
        text, "## Candidate Eligibility Matrix", "## Eligible Candidate Comparison"
    )
    rows = []
    for line in matrix.splitlines():
        if line.startswith("| ") and not line.startswith("|---"):
            rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows[1:]


def test_exact_title_heading_order_and_decision_tokens():
    text = _read()
    headings = [
        line
        for line in text.splitlines()
        if line.startswith("# ") or line.startswith("## ")
    ]
    assert headings == HEADINGS
    assert text.startswith(TITLE + "\n")
    for token in DECISION_TOKENS:
        assert token in text
    assert re.search(
        r"Research cut-off:\n\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text
    )


def test_source_registry_has_complete_official_https_metadata():
    records = _source_records(_read())
    assert len(records) >= 20
    assert len({record["source_id"] for record in records}) == len(records)
    for record in records:
        assert list(record) == SOURCE_FIELDS
        assert all(record[field] for field in SOURCE_FIELDS)
        assert record["canonical_url"].startswith("https://")
        assert record["source_tier"] in {"TIER_1", "TIER_2"}
        assert record["accessed_at_utc"] == "2026-07-22T21:55:02Z"
        assert record["direct_or_inferred"] in {"DIRECT", "ANALYST_INFERENCE"}
        assert "google.com/search" not in record["canonical_url"].lower()
    assert sum(record["source_tier"] == "TIER_2" for record in records) == 1
    assert all(
        record["source_tier"] == "TIER_1"
        for record in records
        if record["evidence_category"].startswith(
            ("API data", "retention", "no training", "subprocessors", "security")
        )
    )


def test_candidate_counts_identities_and_registry_support_are_bounded():
    text = _read()
    assert "Preliminary pool count: 4." in text
    assert "Deep research count: 3." in text
    assert "Remote configurations researched deeply: 3" in text
    assert "Remote configurations eligible: 2" in text
    assert "Remote configurations shortlisted: 2" in text
    assert "Local baseline evaluated: NO" in text

    expected = {
        "OAI-SOL-RESPONSES": ("OpenAI", "Responses API", "gpt-5.6-sol"),
        "OAI-LUNA-RESPONSES": ("OpenAI", "Responses API", "gpt-5.6-luna"),
        "ANT-SONNET-MESSAGES": ("Anthropic", "Claude Messages API", "claude-sonnet-5"),
    }
    records = _source_records(text)
    registry_ids = " ".join(record["candidate_id"] for record in records)
    remote = _section(text, "## Remote Candidate Evidence", "## Privacy, Training")
    for candidate_id, identity in expected.items():
        assert candidate_id in registry_ids
        assert candidate_id in remote
        assert all(value in remote for value in identity)

    shortlist = _section(text, "## Candidate Shortlist", "## Candidate-Specific Blockers")
    assert shortlist.count("candidate_id:") == 2
    assert "ANT-SONNET-MESSAGES" not in shortlist
    assert "GGL-FLASH-DEVELOPER" not in shortlist


def test_mandatory_matrix_uses_only_supported_states_and_fails_closed():
    rows = _eligibility_rows(_read())
    assert len(rows) == 31
    allowed = {"PASS", "FAIL", "EVIDENCE_INSUFFICIENT", "NOT_APPLICABLE"}
    for row in rows:
        assert len(row) == 4
        for cell in row[1:]:
            status = cell.split(",", 1)[0].split(" ", 1)[0]
            assert status in allowed

    # The two shortlisted configurations must pass every mandatory row.
    assert all(row[1].startswith("PASS") for row in rows)
    assert all(row[2].startswith("PASS") for row in rows)
    assert any(row[3].startswith("EVIDENCE_INSUFFICIENT") for row in rows)
    assert "`EVIDENCE_INSUFFICIENT` never acts as PASS." in _read()
    assert "ANT-SONNET-MESSAGES: `NOT_SHORTLISTABLE_EVIDENCE_INSUFFICIENT`" in _read()


def test_privacy_retention_deletion_jurisdiction_and_security_are_covered():
    text = _read()
    privacy = _section(
        text,
        "## Privacy, Training, Retention, And Deletion",
        "## Jurisdiction, Subprocessors, And Security",
    )
    legal = _section(
        text,
        "## Jurisdiction, Subprocessors, And Security",
        "## API, Model Version, Errors, Limits, And Observability",
    )
    for phrase in (
        "not used for training",
        "up to 30 days",
        "`store=false`",
        "automatic input/output deletion within 30 days",
        "No ZDR eligibility is assumed",
        "Consumer policy is never API evidence",
    ):
        assert phrase in _normalized(text)
    for phrase in (
        "processing locations",
        "subprocessors",
        "security measures",
        "incident response/breach notice",
        "EVIDENCE_INSUFFICIENT",
    ):
        assert phrase in legal
    assert "consumer" not in privacy.lower() or "consumer" in text.lower()


def test_endpoint_hermes_key_and_observability_feasibility_is_exact():
    text = _read()
    endpoint = _section(
        text,
        "## Endpoint And Network Restriction Feasibility",
        "## Credential And Key-Lifecycle Evidence",
    )
    assert "`https://api.openai.com/v1/responses`" in endpoint
    assert "`https://api.anthropic.com/v1/messages`" in endpoint
    assert "Controller must disable redirects" in endpoint
    assert "A redirect is never followed" in _normalized(endpoint)
    assert "documentation requires no redirect" in endpoint
    assert "Research browsing hosts are not runtime allowlist candidates" in _normalized(endpoint)
    assert "PASS_CODEX_RESPONSES" in text
    assert "native `anthropic_messages`" in text
    assert "provider-wide and model-specific request timeouts" in text.lower()
    assert "request IDs" in text
    assert "token usage" in text
    assert "Account limits are not assumed" in text
    assert "workspace-scoped keys" in text
    assert "never placed in prompts/model context/logs/artifacts" in text


def test_cost_formulas_and_all_wp143_caps_are_preserved_without_spend_authority():
    text = _read()
    pricing = _section(text, "## Pricing And Cost Model", "## WP143 Budget Compatibility")
    budget = _section(text, "## WP143 Budget Compatibility", "## Optional Local Baseline")
    assert "call_cost = input_tokens / 1,000,000 * input_rate" in pricing
    for amount in ("$0.100", "$0.490", "$0.020", "$0.098", "$0.0594", "$0.297"):
        assert amount in pricing
    for phrase in (
        "120-call primary plan",
        "60 calls",
        "$7.20",
        "$35.28",
        "140-call envelope",
        "$41.16",
        "20 calls/day",
        "$5.88/day",
        "50,000 input",
        "8,000 output",
        "180 seconds",
        "300 seconds",
        "Concurrent calls | 1",
        "USD 2 maximum",
        "USD 25 maximum",
        "USD 100 maximum",
        "Automatic top-up | FORBIDDEN",
        "Experiment spending: NOT AUTHORIZED",
    ):
        assert phrase in budget or phrase in pricing


def test_local_baseline_is_deferred_without_hardware_invention():
    text = _read()
    local = _section(text, "## Optional Local Baseline", "## Candidate Eligibility Matrix")
    normalized_local = _normalized(local)
    assert "Local baseline decision:\nDEFERRED_HARDWARE_EVIDENCE_MISSING" in local
    for fact in (
        "CPU model/instruction set",
        "physical RAM and available RAM",
        "GPU vendor/model",
        "GPU VRAM",
        "usable local storage",
        "driver/runtime support",
        "thermal/power constraints",
    ):
        assert fact in normalized_local
    assert "No runtime, model, license, quantization, throughput, or fit is inferred" in normalized_local


def test_readiness_wp148_and_all_non_authority_boundaries_remain_locked():
    text = _read()
    for phrase in (
        "Remote controlled experiment readiness: NOT_READY",
        "WP148 requires separate approval",
        "Provider/model activation: NOT AUTHORIZED",
        "Provider/model call: NOT AUTHORIZED",
        "Hermes installation/invocation: NOT AUTHORIZED",
        "Provider account creation: NOT AUTHORIZED",
        "Credential creation/use: NOT AUTHORIZED",
        "Network endpoint activation: NOT AUTHORIZED",
        "Experiment spending: NOT AUTHORIZED",
        "Raw input/output persistence: NOT AUTHORIZED",
        "Paper/live/execution authority: FORBIDDEN",
        "No provider/model is activated, selected for production, or approved for\ntrading.",
    ):
        assert phrase in text
    assert "This research and shortlist have no execution authority" in text
    assert "runtime execution, OMS, reconciliation, risk caps" in text


def test_output_inventory_is_docs_status_tests_only_and_has_no_runtime_claim():
    text = _read()
    inventory = _normalized(
        _section(text, "## Output Surface Inventory", "## Forbidden Interpretations")
    )
    for phrase in (
        "one canonical Markdown research record",
        "one Markdown-only focused test",
        "one stable status fragment",
        "project-status and repo-truth-index reconciliation",
        "No source, tool, fixture, workflow, dependency, lock",
    ):
        assert phrase in inventory
    assert "No account or key was created" in text
    assert "No call was made" in text
    assert "No endpoint was activated or\ncalled in WP147" in text
