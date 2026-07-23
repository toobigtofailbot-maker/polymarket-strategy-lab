import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / (
    "hermes_candidate_review_assisted_research_mandatory_provider_evidence_"
    "resolution_and_research_refresh_decision.md"
)
STATUS = REPO_ROOT / "docs/status_entries/WP148.md"
PROJECT_STATUS = REPO_ROOT / "docs/project_status.md"
REPO_TRUTH = REPO_ROOT / "docs/repo_truth_index.md"

TITLE = (
    "# Hermes Candidate-Review Assisted Research Mandatory Provider Evidence "
    "Resolution And Research Refresh Decision"
)
HEADINGS = [
    TITLE,
    "## Purpose",
    "## Position After WP147",
    "## Authority And Non-Authority",
    "## Repository Inputs Reviewed",
    "## Research Method",
    "## Research Cut-Off And Freshness",
    "## Source Hierarchy",
    "## Refreshed Source Registry",
    "## Evidence Classification",
    "## OpenAI Provider-Side Deletion Evidence",
    "## OpenAI Credential Lifecycle Evidence",
    "## Anthropic Deletion Evidence",
    "## Anthropic Subprocessor And Security Evidence",
    "## Google Preliminary Evidence Refresh",
    "## Mandatory Gate Resolution Matrix",
    "## Candidate Eligibility Recalculation",
    "## Eligible Candidate Result",
    "## Provider Decision",
    "## Optional Local-Baseline Pivot",
    "## Readiness Decision",
    "## Next Phase Decision",
    "## Promotion Gates",
    "## Explicit Deferred Capabilities",
    "## Output Surface Inventory",
    "## Forbidden Interpretations",
    "## Future WP149 Boundary",
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
ALLOWED_STATES = {
    "PASS",
    "FAIL",
    "EVIDENCE_INSUFFICIENT",
    "OPERATOR_ONLY_UNVERIFIED",
    "CONTRACT_DEPENDENT_NOT_OPERATOR_VERIFIED",
    "NOT_APPLICABLE",
}
DECISION_TOKENS = (
    "WP148 evidence-resolution status: COMPLETE_EVIDENCE_STILL_INSUFFICIENT",
    "Candidate eligibility result: EVIDENCE_INSUFFICIENT_NO_ELIGIBLE_CANDIDATE",
    "Remote configurations deeply researched: 3",
    "Remote configurations eligible: 0",
    "Remote configurations shortlisted: 0",
    "Provider/model selection: NOT MADE",
    "Local baseline pivot decision: DEFER_HARDWARE_EVIDENCE_MISSING",
    "Remote controlled experiment readiness: NOT_READY",
    "Next phase: REMOTE_PROVIDER_TRACK_DEFER_OR_RESEARCH_REFRESH_LATER_DECISION",
    "Provider/model activation: NOT AUTHORIZED",
    "Provider/model call: NOT AUTHORIZED",
    "Hermes installation/invocation: NOT AUTHORIZED",
    "Provider account creation: NOT AUTHORIZED",
    "Credential creation/use: NOT AUTHORIZED",
    "Network endpoint activation: NOT AUTHORIZED",
    "Experiment spending: NOT AUTHORIZED",
    "Raw input/output persistence: NOT AUTHORIZED",
    "Paper/live/execution authority: FORBIDDEN",
    "WP149 requires separate approval",
)
REMOTE_CANDIDATES = (
    "OAI-SOL-RESPONSES",
    "OAI-LUNA-RESPONSES",
    "ANT-SONNET-MESSAGES",
)


def _read(path: Path = DOC) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, heading: str, next_heading: str) -> str:
    return text.split(heading, 1)[1].split(next_heading, 1)[0]


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _source_records(text: str) -> list[dict[str, str]]:
    registry = _section(
        text, "## Refreshed Source Registry", "## Evidence Classification"
    )
    body = registry.split("```text", 1)[1].split("```", 1)[0]
    records = []
    for raw_record in re.split(r"\n---\n", body.strip()):
        record = {}
        for line in raw_record.splitlines():
            if ": " in line:
                key, value = line.split(": ", 1)
                record[key] = value
        records.append(record)
    return records


def _matrix_rows(text: str) -> list[dict[str, str]]:
    section = _section(
        text,
        "## Mandatory Gate Resolution Matrix",
        "## Candidate Eligibility Recalculation",
    )
    lines = [
        line
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("|---")
    ]
    headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
    return [
        dict(zip(headers, [cell.strip() for cell in line.strip("|").split("|")]))
        for line in lines[1:]
    ]


def _mandatory_pass(
    state: str,
    sources: list[dict[str, str]],
    *,
    directly_relevant: bool = True,
    login_only: bool = False,
    contract_dependent: bool = False,
    automatic_expiry_only: bool = False,
    exact_credential_chain: bool = True,
) -> bool:
    return (
        state == "PASS"
        and directly_relevant
        and bool(sources)
        and any(source["source_tier"] == "TIER_1" for source in sources)
        and all(source["direct_or_inferred"] == "DIRECT" for source in sources)
        and all(source["freshness_status"] == "CURRENT_AT_CUTOFF" for source in sources)
        and not login_only
        and not contract_dependent
        and not automatic_expiry_only
        and exact_credential_chain
    )


def _eligible(candidate_id: str, rows: list[dict[str, str]]) -> bool:
    candidate_rows = [
        row for row in rows if candidate_id in row["Candidate"].split(",")
    ]
    return bool(candidate_rows) and all(
        row["WP148 state"] in {"PASS", "NOT_APPLICABLE"} for row in candidate_rows
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
        r"Research cut-off: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text
    )


def test_refreshed_source_registry_is_complete_unique_current_and_https():
    records = _source_records(_read())
    source_by_id = {record["source_id"]: record for record in records}
    assert len(records) == 11
    assert len({record["source_id"] for record in records}) == len(records)
    for record in records:
        assert list(record) == SOURCE_FIELDS
        assert all(record[field] for field in SOURCE_FIELDS)
        assert record["canonical_url"].startswith("https://")
        assert re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
            record["accessed_at_utc"],
        )
        assert record["accessed_at_utc"] <= "2026-07-23T16:10:31Z"
        assert record["source_tier"] in {"TIER_1", "TIER_2"}
        assert record["direct_or_inferred"] in {"DIRECT", "ANALYST_INFERENCE"}
        assert record["freshness_status"] == "CURRENT_AT_CUTOFF"
        assert "google.com/search" not in record["canonical_url"].lower()
    assert sum(record["source_tier"] == "TIER_1" for record in records) == 10
    assert sum(record["source_tier"] == "TIER_2" for record in records) == 1
    assert source_by_id["ANT-R02"]["source_tier"] == "TIER_2"
    assert {
        record["source_id"]
        for record in records
        if record["source_tier"] == "TIER_2"
    } == {"ANT-R02"}
    assert all(record["direct_or_inferred"] == "DIRECT" for record in records)


def test_anthropic_help_article_is_tier2_supplement_only_and_outcome_is_unchanged():
    text = _read()
    source_by_id = {
        record["source_id"]: record for record in _source_records(text)
    }
    ant_r01 = source_by_id["ANT-R01"]
    ant_r02 = source_by_id["ANT-R02"]
    assert ant_r02["source_tier"] == "TIER_2"
    assert ant_r02["direct_or_inferred"] == "DIRECT"
    assert ant_r02["freshness_status"] == "CURRENT_AT_CUTOFF"
    assert "supplemental confirmation only" in ant_r02["notes"]
    assert "cannot independently satisfy a mandatory gate" in ant_r02["notes"]
    assert "does not prove operator-verifiable deletion" in ant_r02["notes"]

    # ANT-R02 alone cannot satisfy PASS, but may supplement Tier 1 ANT-R01.
    assert not _mandatory_pass("PASS", [ant_r02])
    assert _mandatory_pass("PASS", [ant_r01, ant_r02])

    rows = _matrix_rows(text)
    for gate in ("provider-side deletion", "operator verification"):
        row = next(
            row
            for row in rows
            if row["Candidate"] == "ANT-SONNET-MESSAGES"
            and row["Gate"] == gate
        )
        assert row["WP148 state"] == "EVIDENCE_INSUFFICIENT"
        assert "ANT-R02" in row["Source IDs"].split(",")
    assert not _eligible("ANT-SONNET-MESSAGES", rows)
    assert "Remote configurations eligible: 0" in text
    assert "Remote configurations shortlisted: 0" in text


def test_resolution_matrix_has_every_required_row_and_supported_state():
    text = _read()
    rows = _matrix_rows(text)
    assert len(rows) == 16
    required = {
        "provider-side deletion",
        "operator verification",
        "exact credential type",
        "project scope",
        "permission restriction",
        "rotation/replacement",
        "revocation/deletion",
        "operator-verifiable revocation",
        "subprocessors",
        "security program",
        "incident notification",
        "API deletion",
        "API/business-policy distinction",
    }
    assert required.issubset({row["Gate"] for row in rows})
    source_by_id = {
        record["source_id"]: record for record in _source_records(text)
    }
    for row in rows:
        assert row["WP147 state"] in ALLOWED_STATES
        assert row["WP148 state"] in ALLOWED_STATES
        source_ids = row["Source IDs"].split(",")
        assert all(source_id in source_by_id for source_id in source_ids)
        if row["WP148 state"] == "PASS":
            assert _mandatory_pass(
                row["WP148 state"],
                [source_by_id[source_id] for source_id in source_ids],
            )


def test_eligibility_is_derived_from_all_mandatory_rows_and_fails_closed():
    text = _read()
    rows = _matrix_rows(text)
    candidate_results = [
        _eligible(candidate, rows) for candidate in REMOTE_CANDIDATES
    ]
    assert candidate_results == [
        False,
        False,
        False,
    ]
    for candidate in REMOTE_CANDIDATES:
        candidate_rows = [
            row for row in rows if candidate in row["Candidate"].split(",")
        ]
        assert any(
            row["WP148 state"]
            not in {"PASS", "NOT_APPLICABLE"}
            for row in candidate_rows
        )
    assert "Remote configurations eligible: 0" in text
    assert "Remote configurations shortlisted: 0" in text
    assert "WP148 never emits a shortlist" in text
    eligible_count = sum(candidate_results)
    expected_next_phase = (
        "ELIGIBLE_CANDIDATE_SHORTLIST_AND_CONFIGURATION_DECISION"
        if eligible_count
        else "REMOTE_PROVIDER_TRACK_DEFER_OR_RESEARCH_REFRESH_LATER_DECISION"
    )
    assert f"Next phase: {expected_next_phase}" in text


def test_negative_evidence_matrix_cannot_manufacture_a_pass():
    tier1 = {
        "source_tier": "TIER_1",
        "direct_or_inferred": "DIRECT",
        "freshness_status": "CURRENT_AT_CUTOFF",
    }
    tier2 = {**tier1, "source_tier": "TIER_2"}
    inferred = {**tier1, "direct_or_inferred": "ANALYST_INFERENCE"}

    # 1. store=false alone does not pass provider-side deletion.
    assert not _mandatory_pass(
        "EVIDENCE_INSUFFICIENT", [tier1], directly_relevant=False
    )
    # 2. Thirty-day expiry alone does not pass operator verification.
    assert not _mandatory_pass(
        "PASS", [tier1], automatic_expiry_only=True
    )
    # 3. Approval/agreement-dependent ZDR or MAM does not mean eligibility.
    assert not _mandatory_pass(
        "CONTRACT_DEPENDENT_NOT_OPERATOR_VERIFIED",
        [tier1],
        contract_dependent=True,
    )
    # 4. Tier 2 key restriction alone cannot satisfy a mandatory gate.
    assert not _mandatory_pass("PASS", [tier2])
    # 5. Mixed service-account and user-key evidence is not one exact chain.
    assert not _mandatory_pass(
        "PASS", [tier1, tier1], exact_credential_chain=False
    )
    # 6. Login-only trust evidence cannot pass.
    assert not _mandatory_pass("PASS", [tier1], login_only=True)
    # Inference-only evidence cannot pass either.
    assert not _mandatory_pass("PASS", [inferred])


def test_outcome_invariants_cover_missing_row_eligible_but_zero_shortlist_and_scope():
    text = _read()
    # 7. The real matrix has a missing mandatory row for every deep candidate.
    assert not any(_eligible(candidate, _matrix_rows(text)) for candidate in REMOTE_CANDIDATES)
    # 8. Even a hypothetical eligible candidate still produces no WP148 shortlist.
    hypothetical_eligible_count = 1
    assert hypothetical_eligible_count == 1
    assert (
        "Even if one candidate had become eligible, WP148 would still emit zero shortlist entries."
        in _normalized(text)
    )
    assert "Remote configurations shortlisted: 0" in text
    # 9. Cost or compatibility cannot compensate for mandatory failure.
    assert "Hermes compatibility and cost remain non-compensating" in text
    # 10. WP148 cannot implement WP149.
    assert "WP148 cannot be interpreted as implementing WP149." in text
    assert "WP149 requires separate approval" in text


def test_provider_specific_conclusions_preserve_exact_fail_closed_meaning():
    text = _read()
    openai = _section(
        text,
        "## OpenAI Provider-Side Deletion Evidence",
        "## OpenAI Credential Lifecycle Evidence",
    )
    credential = _section(
        text,
        "## OpenAI Credential Lifecycle Evidence",
        "## Anthropic Deletion Evidence",
    )
    anthropic = _section(
        text,
        "## Anthropic Deletion Evidence",
        "## Anthropic Subprocessor And Security Evidence",
    )
    anthropic_security = _section(
        text,
        "## Anthropic Subprocessor And Security Evidence",
        "## Google Preliminary Evidence Refresh",
    )
    google = _section(
        text,
        "## Google Preliminary Evidence Refresh",
        "## Mandatory Gate Resolution Matrix",
    )
    for phrase in (
        "application_state_creation_prevented",
        "abuse_monitoring_retention_default",
        "provider_side_deletion_method: EVIDENCE_INSUFFICIENT",
        "operator_verification_method: EVIDENCE_INSUFFICIENT",
        "ZDR_or_MAM_eligibility: CONTRACT_DEPENDENT_NOT_OPERATOR_VERIFIED",
        "`store=false` does not delete abuse-monitoring records",
    ):
        assert phrase in openai
    for phrase in (
        "credential_type: OPENAI_WORKLOAD_IDENTITY_ACCESS_TOKEN",
        "project_scope: PASS",
        "endpoint_or_permission_restriction: PASS",
        "rotation_or_replacement: PASS",
        "revocation_or_deletion: EVIDENCE_INSUFFICIENT",
        "operator_verification_method: EVIDENCE_INSUFFICIENT",
        "cannot be combined",
        "A role is not a credential",
        "deleting a service account revokes every associated key",
    ):
        assert phrase in _normalized(credential)
    assert "Thirty-day automatic expiry alone cannot satisfy operator verification." in anthropic
    normalized_anthropic_security = _normalized(anthropic_security)
    assert "20 entries" in normalized_anthropic_security
    assert "within 48 hours" in normalized_anthropic_security
    assert "change to PASS" in normalized_anthropic_security
    assert "remains preliminary rather than deeply researched" in google


def test_document_status_project_and_repo_truth_surfaces_agree():
    surfaces = {
        "document": _read(),
        "status": _read(STATUS),
        "project": _read(PROJECT_STATUS),
        "repo_truth": _read(REPO_TRUTH),
    }
    for token in DECISION_TOKENS:
        for name in ("document", "status", "project"):
            assert token in surfaces[name], (name, token)
    for token in (
        "Refreshed source count: 11",
        "Tier 1 source count: 10",
        "Tier 2 source count: 1",
        "Tier 2 source IDs: ANT-R02",
    ):
        for name, surface in surfaces.items():
            assert token in surface, (name, token)
    for path in (
        "docs/hermes_candidate_review_assisted_research_mandatory_provider_evidence_resolution_and_research_refresh_decision.md",
        "tests/test_hermes_candidate_review_assisted_research_mandatory_provider_evidence_resolution_and_research_refresh_decision_docs.py",
        "docs/status_entries/WP148.md",
    ):
        assert path in surfaces["repo_truth"]
    assert "WP148" in surfaces["project"] and "REVIEW_TARGET" in surfaces["project"]
    assert "WP147" in surfaces["project"] and "MERGED" in surfaces["project"]


def test_non_authority_and_output_inventory_remain_docs_status_tests_only():
    text = _read()
    inventory = _section(
        text, "## Output Surface Inventory", "## Forbidden Interpretations"
    )
    assert "No source, tool, fixture, workflow" in inventory
    for token in DECISION_TOKENS[8:]:
        assert token in text
    assert "execution, OMS, reconciliation, risk caps" in text
    assert "This current public research and evidence-resolution decision has no execution" in text
