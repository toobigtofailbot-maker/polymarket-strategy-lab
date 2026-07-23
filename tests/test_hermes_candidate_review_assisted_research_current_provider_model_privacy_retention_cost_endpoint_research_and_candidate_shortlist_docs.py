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
    "Research cut-off:\n2026-07-22T23:49:02Z",
    "Candidate pool posture:\nCURRENT_AUTHORITATIVE_FIRST_PARTY_RESEARCH_ONLY",
    "Provider decision:\nNO_PROVIDER_SELECTED_EVIDENCE_INSUFFICIENT",
    "Candidate shortlist decision:\nEVIDENCE_INSUFFICIENT_NO_SHORTLIST",
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
    "Next phase:\nMANDATORY_EVIDENCE_RESOLUTION_AND_RESEARCH_REFRESH_DECISION",
    "WP148 requires separate approval and is not authorized as candidate selection while the shortlist count is zero",
    "Local baseline decision:\nDEFERRED_HARDWARE_EVIDENCE_MISSING",
]

RESEARCH_CUTOFF = "2026-07-22T23:49:02Z"
CANDIDATE_IDS = (
    "OAI-SOL-RESPONSES",
    "OAI-LUNA-RESPONSES",
    "ANT-SONNET-MESSAGES",
)
CANDIDATE_ALIASES = ("ANT-SONNET5-MESSAGES", "GOO-GEMINI35FLASH")
PREFERRED_GATES = {"ZDR availability (preferred)"}

# This explicit gate-to-source contract makes "directly relevant" deterministic.
# Registry metadata still controls tier, directness, and freshness.
DIRECT_TIER1_BY_GATE = {
    "Exact identity": {"OAI-001", "OAI-002", "ANT-001"},
    "Public availability/prerequisites": {"OAI-001", "OAI-002", "ANT-001", "ANT-002"},
    "Version/lifecycle/deprecation": {"OAI-001", "OAI-002", "ANT-001", "ANT-009"},
    "API no-training": {"OAI-003", "ANT-003"},
    "Default/configurable retention <=30 days": {"OAI-003", "ANT-004", "ANT-006"},
    # No current source proves per-experiment operator-verifiable provider deletion.
    "Deletion/operator-verifiable control": set(),
    "Jurisdiction/region evidence": {"OAI-003", "OAI-009", "ANT-005"},
    "Current public subprocessors": {"OAI-009", "ANT-010"},
    "Security/incident evidence": {"OAI-008", "ANT-003", "ANT-010"},
    "Exact host/path and redirects": {"OAI-001", "OAI-002", "OAI-004", "ANT-002", "HERMES-002"},
    "Hosted tools not mandatory": {"OAI-004", "ANT-002", "ANT-006"},
    "Persistent hosted memory not mandatory": {"OAI-003", "OAI-004", "ANT-006"},
    "Repository connection not required": {"OAI-004", "ANT-002"},
    "Request identity": {"OAI-005", "ANT-007"},
    "Usage reporting": {"OAI-004", "ANT-005", "ANT-008"},
    "Reproducible cost reporting": {"OAI-001", "OAI-002", "OAI-004", "ANT-001", "ANT-008"},
    "Configurable output cap": {"OAI-001", "OAI-002", "OAI-004", "ANT-001", "ANT-002"},
    "Controller timeout compatibility": {"HERMES-003"},
    "Documented errors/transients": {"OAI-005", "ANT-007"},
    "Rate-limit behavior": {"OAI-001", "OAI-002", "OAI-006", "ANT-007", "ANT-008"},
    "Key create/scope/rotate/revoke": {"ANT-008"},
    "Secret isolation from model context": {"HERMES-001", "OAI-010", "OAI-012", "ANT-008"},
    "Synthetic WP142 input/no tools": {"OAI-004", "ANT-002", "ANT-006"},
    "WP133 bounded plain/structured output": {"OAI-001", "OAI-002", "OAI-004", "ANT-001", "ANT-002"},
    "Hermes compatibility": {"HERMES-001", "HERMES-002", "HERMES-003"},
    "Current input/output pricing": {"OAI-001", "OAI-002", "ANT-001", "ANT-005"},
    "Per-call <=USD2": {"OAI-001", "OAI-002", "ANT-001", "ANT-005"},
    "Total <=USD100": {"OAI-001", "OAI-002", "ANT-001", "ANT-005"},
    "Daily executable <=USD25": {"OAI-001", "OAI-002", "ANT-001", "ANT-005"},
    "Material caveats disclosed": {
        "OAI-003", "OAI-006", "OAI-008", "OAI-009",
        "ANT-004", "ANT-005", "ANT-006", "ANT-007", "ANT-008", "ANT-009",
    },
}


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


def _source_by_id(text: str) -> dict[str, dict[str, str]]:
    return {record["source_id"]: record for record in _source_records(text)}


def _status(cell: str) -> str:
    return cell.split(",", 1)[0].split(" ", 1)[0]


def _source_ids(cell: str) -> list[str]:
    return re.findall(r"\b(?:HERMES|OAI|ANT)-\d{3}\b", cell)


def _cell_has_direct_tier1(
    gate: str, cell: str, source_by_id: dict[str, dict[str, str]]
) -> bool:
    if _status(cell) != "PASS":
        return False
    cited = _source_ids(cell)
    if not cited or any(source_id not in source_by_id for source_id in cited):
        return False
    if any(
        source_by_id[source_id]["freshness_status"] == "EVIDENCE_INSUFFICIENT"
        for source_id in cited
    ):
        return False
    relevant = DIRECT_TIER1_BY_GATE[gate].intersection(cited)
    return any(
        source_by_id[source_id]["source_tier"] == "TIER_1"
        and source_by_id[source_id]["direct_or_inferred"] == "DIRECT"
        and source_by_id[source_id]["freshness_status"] == "CURRENT_AT_CUTOFF"
        for source_id in relevant
    )


def _candidate_passes_mandatory_rows(
    rows: list[list[str]],
    candidate_column: int,
    source_by_id: dict[str, dict[str, str]],
) -> bool:
    return all(
        _status(row[candidate_column]) == "PASS"
        and _cell_has_direct_tier1(row[0], row[candidate_column], source_by_id)
        for row in rows
        if row[0] not in PREFERRED_GATES
    )


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
    assert len(records) >= 23
    assert len({record["source_id"] for record in records}) == len(records)
    for record in records:
        assert list(record) == SOURCE_FIELDS
        assert all(record[field] for field in SOURCE_FIELDS)
        assert record["canonical_url"].startswith("https://")
        assert record["source_tier"] in {"TIER_1", "TIER_2"}
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", record["accessed_at_utc"])
        assert record["accessed_at_utc"] <= RESEARCH_CUTOFF
        assert record["direct_or_inferred"] in {"DIRECT", "ANALYST_INFERENCE"}
        assert "google.com/search" not in record["canonical_url"].lower()
    assert sum(record["source_tier"] == "TIER_2" for record in records) == 1
    source_by_id = _source_by_id(_read())
    assert source_by_id["OAI-007"]["source_tier"] == "TIER_2"
    for source_id in ("OAI-003", "OAI-010", "OAI-011", "OAI-012"):
        assert source_by_id[source_id]["accessed_at_utc"] == RESEARCH_CUTOFF
        assert source_by_id[source_id]["source_tier"] == "TIER_1"
        assert source_by_id[source_id]["direct_or_inferred"] == "DIRECT"
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
    assert "Remote configurations eligible: 0" in text
    assert "Remote configurations shortlisted: 0" in text
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
    assert "candidate_id:" not in shortlist
    assert "EVIDENCE_INSUFFICIENT_NO_SHORTLIST" in shortlist


def test_mandatory_matrix_uses_only_supported_states_and_fails_closed():
    text = _read()
    rows = _eligibility_rows(text)
    source_by_id = _source_by_id(text)
    assert len(rows) == 31
    allowed = {"PASS", "FAIL", "EVIDENCE_INSUFFICIENT", "NOT_APPLICABLE"}
    for row in rows:
        assert len(row) == 4
        for cell in row[1:]:
            assert _status(cell) in allowed
            cited = _source_ids(cell)
            assert cited
            assert all(source_id in source_by_id for source_id in cited)
            if row[0] not in PREFERRED_GATES and _status(cell) == "PASS":
                assert _cell_has_direct_tier1(row[0], cell, source_by_id)

    eligible = [
        candidate_id
        for column, candidate_id in enumerate(CANDIDATE_IDS, start=1)
        if _candidate_passes_mandatory_rows(rows, column, source_by_id)
    ]
    assert eligible == []
    assert "Remote configurations eligible: 0" in text
    assert "Remote configurations shortlisted: 0" in text
    assert "Candidate shortlist decision:\nEVIDENCE_INSUFFICIENT_NO_SHORTLIST" in text
    assert "candidate_id:" not in _section(
        text, "## Candidate Shortlist", "## Candidate-Specific Blockers"
    )
    assert "`EVIDENCE_INSUFFICIENT` never acts as PASS." in text
    for candidate_id in CANDIDATE_IDS:
        assert f"{candidate_id}: `NOT_SHORTLISTABLE_EVIDENCE_INSUFFICIENT`" in text


def test_evidence_tier_and_deletion_negative_regressions():
    text = _read()
    source_by_id = _source_by_id(text)
    rows = _eligibility_rows(text)

    # Tier 2 alone cannot satisfy a mandatory key-lifecycle gate.
    assert not _cell_has_direct_tier1(
        "Key create/scope/rotate/revoke", "PASS (OAI-007)", source_by_id
    )
    # Partial Tier 1 plus Tier 2 still cannot complete the exact OpenAI key chain.
    assert not _cell_has_direct_tier1(
        "Key create/scope/rotate/revoke",
        "PASS (OAI-010, OAI-011, OAI-012; OAI-007 Tier 2 supplement)",
        source_by_id,
    )
    # A Tier 2 source may supplement, but not replace, directly relevant Tier 1.
    assert _cell_has_direct_tier1(
        "Exact identity", "PASS (OAI-001, OAI-007 Tier 2 supplement)", source_by_id
    )
    # Analyst inference cannot replace direct evidence.
    assert not _cell_has_direct_tier1(
        "Exact host/path and redirects", "PASS (ANALYST_INFERENCE)", source_by_id
    )
    # Request-shape proof does not prove provider-side deletion.
    assert not _cell_has_direct_tier1(
        "Deletion/operator-verifiable control",
        "PASS, store=false plus request-manifest verification (OAI-003; ANALYST_INFERENCE)",
        source_by_id,
    )
    # One unresolved mandatory row makes every affected candidate non-shortlistable.
    for candidate_column in range(1, 4):
        assert not _candidate_passes_mandatory_rows(
            rows, candidate_column, source_by_id
        )


def test_candidate_ids_and_cost_values_are_canonical_across_repo_surfaces():
    text = _read()
    status = (REPO_ROOT / "docs/status_entries/WP147.md").read_text(encoding="utf-8")
    project = (REPO_ROOT / "docs/project_status.md").read_text(encoding="utf-8")
    repo_truth = (REPO_ROOT / "docs/repo_truth_index.md").read_text(encoding="utf-8")
    combined = "\n".join((text, status, project, repo_truth))
    for alias in CANDIDATE_ALIASES:
        assert alias not in combined
    for candidate_id in ("ANT-SONNET-MESSAGES", "GGL-FLASH-DEVELOPER"):
        assert candidate_id in combined
    for token in (
        "expected_us_geo_cost: USD 0.0594",
        "stress_us_geo_cost: USD 0.2970",
        "Remote configurations eligible: 0",
        "Remote configurations shortlisted: 0",
        "EVIDENCE_INSUFFICIENT_NO_SHORTLIST",
    ):
        assert token in text
        assert token in status
        assert token in project


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
        "No ZDR or MAM eligibility is assumed",
        "Consumer policy is never API evidence",
        "`application_state_creation_prevented`",
        "`abuse_monitoring_retention`",
        "`provider_side_deletion_method`",
        "`operator_verification_method`",
        "`ZDR_or_MAM_eligibility`",
        "request manifest can verify only the request shape",
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
    assert "OAI-010 through OAI-012" in text
    assert "OAI-007 may supplement but cannot cure the remaining gap" in text
    assert "`deleted` boolean" in text
    assert "never placed in prompts/model context/logs/artifacts" in text


def test_cost_formulas_and_all_wp143_caps_are_preserved_without_spend_authority():
    text = _read()
    pricing = _section(text, "## Pricing And Cost Model", "## WP143 Budget Compatibility")
    budget = _section(text, "## WP143 Budget Compatibility", "## Optional Local Baseline")
    assert "call_cost = input_tokens / 1,000,000 * input_rate" in pricing
    for amount in ("$0.100", "$0.490", "$0.020", "$0.098", "$0.0594", "$0.297"):
        assert amount in pricing
    assert "expected_us_geo_cost: USD 0.0594" in pricing
    assert "stress_us_geo_cost: USD 0.2970" in pricing
    for phrase in (
        "120-call primary scenario",
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
        "WP148 requires separate approval and is not authorized as candidate selection while the shortlist count is zero",
        "Next phase:\nMANDATORY_EVIDENCE_RESOLUTION_AND_RESEARCH_REFRESH_DECISION",
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
    assert "This research and no-shortlist decision have no execution authority" in text
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
