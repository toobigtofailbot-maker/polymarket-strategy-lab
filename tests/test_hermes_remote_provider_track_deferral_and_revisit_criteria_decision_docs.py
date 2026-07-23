import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs/hermes_remote_provider_track_deferral_and_revisit_criteria_decision.md"
STATUS = REPO_ROOT / "docs/status_entries/WP149.md"
PROJECT_STATUS = REPO_ROOT / "docs/project_status.md"
REPO_TRUTH = REPO_ROOT / "docs/repo_truth_index.md"

TITLE = "# Hermes Remote Provider Track Deferral And Revisit Criteria Decision"
HEADINGS = [
    TITLE,
    "## Purpose",
    "## Position After WP148",
    "## Authority And Non-Authority",
    "## Repository Inputs Reviewed",
    "## Deferral Decision",
    "## Meaning Of Deferral",
    "## Material Revisit Triggers",
    "## Non-Triggers",
    "## Materiality Standard",
    "## Revisit Evidence Packet",
    "## Public Evidence Trigger",
    "## Operator Evidence Trigger",
    "## Contractual Evidence Trigger",
    "## Provider Architecture Trigger",
    "## Local Hardware Trigger",
    "## Anti-Loop Rules",
    "## Deferral Review Cadence",
    "## Reopen State Transition",
    "## Productive Next Phase",
    "## Promotion Gates",
    "## Explicit Deferred Capabilities",
    "## Output Surface Inventory",
    "## Forbidden Interpretations",
    "## Future WP150 Boundary",
    "## Decision",
    "## Non-Authority Statement",
]
DECISION_TOKENS = (
    "Remote provider track status:\nDEFERRED_PENDING_MATERIAL_NEW_EVIDENCE",
    "Automatic periodic provider re-research:\nFORBIDDEN",
    "Repeated unchanged provider research:\nFORBIDDEN",
    "Scheduled periodic provider sweep:\nFORBIDDEN",
    "Reopen based only on elapsed time:\nFORBIDDEN",
    "Provider track may reopen only after:\nMATERIAL_EVIDENCE_TRIGGER_AND_SEPARATE_APPROVAL",
    "Deferral review cadence:\nEVENT_DRIVEN_ONLY",
    "Remote configurations eligible:\n0",
    "Remote configurations shortlisted:\n0",
    "Provider/model selection:\nNOT MADE",
    "Remote controlled experiment readiness:\nNOT_READY",
    "Provider/model activation:\nNOT AUTHORIZED",
    "Provider/model call:\nNOT AUTHORIZED",
    "Hermes installation/invocation:\nNOT AUTHORIZED",
    "Provider account creation:\nNOT AUTHORIZED",
    "Credential creation/use:\nNOT AUTHORIZED",
    "Network endpoint activation:\nNOT AUTHORIZED",
    "Experiment spending:\nNOT AUTHORIZED",
    "Raw input/output persistence:\nNOT AUTHORIZED",
    "Paper/live/execution authority:\nFORBIDDEN",
    "Next phase:\nLOCAL_RESEARCH_WORKFLOW_VALUE_VALIDATION_AND_PAPER_TRADING_READINESS_DECISION",
    "WP150 requires separate approval",
)
PRIOR_TRUTH_TOKENS = (
    "WP148 evidence-resolution status:\nCOMPLETE_EVIDENCE_STILL_INSUFFICIENT",
    "Candidate eligibility result:\nEVIDENCE_INSUFFICIENT_NO_ELIGIBLE_CANDIDATE",
    "Remote configurations deeply researched:\n3",
    "Remote configurations eligible:\n0",
    "Remote configurations shortlisted:\n0",
    "Provider/model selection:\nNOT MADE",
    "Local baseline pivot decision:\nDEFER_HARDWARE_EVIDENCE_MISSING",
    "Remote controlled experiment readiness:\nNOT_READY",
)
PACKET_FIELDS = (
    "trigger_id",
    "trigger_type",
    "candidate_or_architecture",
    "affected_mandatory_gate",
    "previous_state",
    "new_evidence_summary",
    "source_or_operator_evidence_type",
    "evidence_date",
    "freshness_status",
    "why_material",
    "remaining_unresolved_gates",
    "sanitization_status",
)
PACKET_RESULTS = (
    "ACCEPTED_FOR_SEPARATE_RESEARCH_WP",
    "REJECTED_NO_MATERIAL_CHANGE",
    "REJECTED_UNSAFE_OR_UNSANITIZED",
)
STATES = (
    "DEFERRED_PENDING_MATERIAL_NEW_EVIDENCE",
    "REVISIT_PACKET_PROPOSED",
    "REVISIT_PACKET_REJECTED",
    "REVISIT_PACKET_ACCEPTED_PENDING_SEPARATE_WP",
    "RESEARCH_REFRESH_AUTHORIZED",
    "RESEARCH_REFRESH_COMPLETE_NO_ELIGIBLE_CANDIDATE",
    "RESEARCH_REFRESH_COMPLETE_ELIGIBLE_CANDIDATE_EXISTS",
)


def _read(path: Path = DOC) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, heading: str, next_heading: str) -> str:
    return text.split(heading, 1)[1].split(next_heading, 1)[0]


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_exact_title_heading_order_and_all_decision_tokens():
    text = _read()
    headings = [
        line
        for line in text.splitlines()
        if line.startswith("# ") or line.startswith("## ")
    ]
    assert headings == HEADINGS
    assert text.startswith(TITLE + "\n")
    normalized = _normalized(text)
    for token in DECISION_TOKENS:
        assert _normalized(token) in normalized
    for token in PRIOR_TRUTH_TOKENS:
        assert _normalized(token) in normalized


def test_deferral_meaning_is_inactive_not_closed_or_permanent_rejection():
    text = _read()
    section = _section(text, "## Meaning Of Deferral", "## Material Revisit Triggers")
    for phrase in (
        "no active provider candidate",
        "no provider shortlist or provider/model selection",
        "no scheduled periodic re-research",
        "no provider implementation or remote experiment",
        "no account, credential, endpoint, model-call, or spend work",
        "no claim that an evidence-insufficient provider is permanently unsuitable",
        "does not abandon the Hermes research architecture",
        "does not prove model quality",
        "approve paper trading",
    ):
        assert phrase in _normalized(section)
    decision = _section(text, "## Deferral Decision", "## Meaning Of Deferral")
    assert "The remote-provider track is inactive and deferred. It is not closed" in decision


def test_allowed_material_triggers_and_local_hardware_separation():
    text = _read()
    trigger = _section(text, "## Material Revisit Triggers", "## Non-Triggers")
    normalized = _normalized(trigger)
    for phrase in (
        "current first-party public source",
        "sanitized operator evidence packet",
        "current sanitized contractual artifact",
        "official provider or deployment architecture change",
        "Actual operator hardware evidence",
        "does not reopen the remote provider track",
    ):
        assert phrase in normalized
    for heading in (
        "## Public Evidence Trigger",
        "## Operator Evidence Trigger",
        "## Contractual Evidence Trigger",
        "## Provider Architecture Trigger",
        "## Local Hardware Trigger",
    ):
        assert heading in text


def test_every_required_non_trigger_is_explicit_and_fail_closed():
    text = _read()
    section = _section(text, "## Non-Triggers", "## Materiality Standard")
    normalized = _normalized(section)
    non_triggers = (
        "passage of a week, month, quarter, or year by itself",
        "a model release without relevant privacy, deletion, or credential evidence",
        "a price reduction",
        "a benchmark improvement",
        "social-media discussion",
        "provider marketing",
        "a help article repeating existing evidence",
        "Tier 2 repetition of already-known evidence",
        "a renamed model alias",
        "an unsupported claim from sales or support",
        "a login-only control without sanitized operator evidence",
        "unchanged provider documentation",
        "a new Codex session",
        "a new WP number",
        "user impatience",
        "a desire to force a shortlist",
        "the fact that the local harness is complete",
        "the fact that remote readiness remains zero",
        "general industry adoption",
        "another provider having similar policies",
        "cost compatibility",
        "Hermes API compatibility",
    )
    for phrase in non_triggers:
        assert phrase in normalized
    assert "multiple items occur together" in normalized
    assert "unless a separate material evidence artifact" in normalized


def test_negative_reopen_matrix_rejects_time_model_price_benchmark_and_repetition():
    text = _read()
    non_triggers = _section(text, "## Non-Triggers", "## Materiality Standard")
    anti_loop = _section(text, "## Anti-Loop Rules", "## Deferral Review Cadence")
    cases = {
        "elapsed_time_only": "passage of a week, month, quarter, or year by itself",
        "new_model_only": "a model release without relevant privacy, deletion, or credential evidence",
        "cheaper_price_only": "a price reduction",
        "benchmark_gain_only": "a benchmark improvement",
        "repeated_help_article": "a help article repeating existing evidence",
        "tier2_repetition": "Tier 2 repetition of already-known evidence",
        "unsupported_sales_support": "an unsupported claim from sales or support",
        "login_only_claim": "a login-only control without sanitized operator evidence",
        "unchanged_docs": "unchanged provider documentation",
        "new_wp_number": "a new WP number",
    }
    assert all(phrase in non_triggers for phrase in cases.values())
    assert "Reopen based only on elapsed time:\nFORBIDDEN" in anti_loop
    assert "avoid repeating unchanged sources" in anti_loop


def test_materiality_requires_mandatory_gate_change_and_complete_fields():
    text = _read()
    section = _section(text, "## Materiality Standard", "## Revisit Evidence Packet")
    assert (
        "could change at least one named mandatory row from a non-passing state "
        "to `PASS`" in _normalized(section)
    )
    for field in PACKET_FIELDS:
        assert re.search(rf"(?m)^{re.escape(field)}$", section)
    for phrase in (
        "changes only a preferred criterion",
        "cost, or performance",
        "cannot affect eligibility",
        "is stale or unverifiable",
        "assumes enterprise access",
        "different API, account, credential, contract, region, or deployment posture",
    ):
        assert phrase in _normalized(section)


def test_freshness_requirements_are_objective_and_time_alone_is_not_material():
    text = _read()
    section = _section(text, "## Materiality Standard", "## Revisit Evidence Packet")
    normalized = _normalized(section)
    for phrase in (
        "public evidence must still be in force",
        "no more than 30 calendar days",
        "undated live public page",
        "no more than 7 calendar days",
        "account rate/spend limits",
        "contractual evidence must be current and effective",
        "Superseded evidence is stale regardless of age",
        "freshness alone is never materiality",
    ):
        assert phrase in normalized


def test_revisit_packet_contract_is_complete_and_unsafe_content_is_rejected():
    text = _read()
    section = _section(text, "## Revisit Evidence Packet", "## Public Evidence Trigger")
    required_items = (
        "the exact candidate, provider, API, model, or architecture",
        "the exact mandatory gate affected",
        "the previous evidence state",
        "the new source or sanitized operator evidence",
        "the source date or effective date",
        "the access date",
        "the source tier or operator-evidence class",
        "the direct-versus-inferred classification",
        "the account or contract dependency",
        "why the evidence could change eligibility",
        "known remaining blockers",
        "confirmation that no secret or personal data is included",
    )
    normalized = _normalized(section)
    for item in required_items:
        assert item in normalized
    for result in PACKET_RESULTS:
        assert result in section
    assert "Acceptance means only that a separately approved bounded research WP may be proposed." in normalized
    assert "WP149 processes no real packet." in normalized


def test_operator_and_contract_evidence_remain_sanitized_specific_and_nonactivating():
    text = _read()
    operator = _section(text, "## Operator Evidence Trigger", "## Contractual Evidence Trigger")
    contractual = _section(text, "## Contractual Evidence Trigger", "## Provider Architecture Trigger")
    for phrase in (
        "account eligibility",
        "exact retention controls",
        "exact ZDR/MAM enrollment",
        "exact key scope and revocation",
        "deletion verification",
        "region/jurisdiction configuration",
        "current account rate/spend limits",
        "No secret, API key, token, account ID, invoice, personal data, raw provider content",
        "account-specific",
        "not transferable",
    ):
        assert phrase in _normalized(operator)
    for phrase in (
        "current executed or reviewable agreement, DPA, or order form",
        "supplied by the operator",
        "sanitized before repository use",
        "separately reviewed",
        "non-transferable",
        "insufficient by itself to activate",
    ):
        assert phrase in _normalized(contractual)


def test_event_driven_cadence_authorizes_no_schedule_or_automatic_sweep():
    text = _read()
    section = _section(text, "## Deferral Review Cadence", "## Reopen State Transition")
    assert "Deferral review cadence:\nEVENT_DRIVEN_ONLY" in section
    for phrase in (
        "creates no task, reminder, monitor, schedule, recurring sweep, daemon, or background loop",
        "major Hermes architecture review",
        "operator-identified provider-policy change",
        "paper-trading phase transition",
        "security/privacy governance review",
        "documented hardware upgrade",
        "does not itself reopen research",
    ):
        assert phrase in _normalized(section)


def test_state_machine_is_exact_and_direct_activation_transitions_are_forbidden():
    text = _read()
    section = _section(text, "## Reopen State Transition", "## Productive Next Phase")
    code_block = section.split("```text", 1)[1].split("```", 1)[0]
    assert tuple(line for line in code_block.splitlines() if line) == STATES
    for phrase in (
        "deferred → provider selected",
        "deferred → remote implementation",
        "proposed → model call",
        "accepted → credential creation",
        "eligible candidate exists → activation",
        "any state → paper/live trading",
    ):
        assert phrase in section
    assert "only after separate WP approval" in section
    assert "requires separate shortlisting, selection, control, implementation, dry-run, and promotion decisions" in _normalized(section)


def test_packet_acceptance_eligibility_and_next_phase_grant_no_direct_authority():
    text = _read()
    forbidden = _section(text, "## Forbidden Interpretations", "## Future WP150 Boundary")
    for phrase in (
        "An accepted revisit packet is not research authorization",
        "Research authorization is not model-call authorization",
        "Eligibility is not shortlisting",
        "Shortlisting is not selection",
        "Selection is not activation",
        "Local workflow validation is not paper-trading approval",
        "Paper-trading readiness is not paper-trading execution",
        "WP149 does not implement WP150",
        "No execution/risk/order/trading authority changes",
    ):
        assert phrase in forbidden


def test_next_phase_is_provider_independent_and_wp150_is_separately_gated():
    text = _read()
    next_phase = _section(text, "## Productive Next Phase", "## Promotion Gates")
    wp150 = _section(text, "## Future WP150 Boundary", "## Decision")
    assert "LOCAL_RESEARCH_WORKFLOW_VALUE_VALIDATION_AND_PAPER_TRADING_READINESS_DECISION" in next_phase
    assert "The next phase is provider-independent." in next_phase
    assert "may not start paper trading" in next_phase
    assert "WP150 — Local Research Workflow Value Validation And Paper-Trading Readiness Decision V1" in wp150
    assert "WP150 requires separate approval" in wp150
    assert "must not start paper trading" in wp150
    assert "must not" in wp150 and "implement WP151" in wp150


def test_no_candidate_research_or_provider_identity_is_added():
    text = _read()
    provider_architecture = _section(
        text, "## Provider Architecture Trigger", "## Local Hardware Trigger"
    )
    assert "WP149 adds no provider candidate" in provider_architecture
    assert "WP149 performs no provider research" in text
    for candidate_id in (
        "OAI-SOL-RESPONSES",
        "OAI-LUNA-RESPONSES",
        "ANT-SONNET-MESSAGES",
        "GGL-FLASH-DEVELOPER",
    ):
        assert candidate_id not in text


def test_output_inventory_and_non_authority_add_no_implementation_surface():
    text = _read()
    inventory = _section(text, "## Output Surface Inventory", "## Forbidden Interpretations")
    expected_paths = (
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_wallet_intelligence_architecture_contract_docs.py",
    )
    for path in expected_paths:
        assert path in inventory
    assert "three additions and four documentation/test updates" in inventory
    assert "zero source, tool, fixture, workflow, dependency, lock, configuration, credential" in _normalized(inventory)
    non_authority = text.split("## Non-Authority Statement", 1)[1]
    assert "has no execution authority" in non_authority
    assert "does not research, add, shortlist, select, activate, install, configure, call" in _normalized(non_authority)


def test_authorized_document_status_project_and_repo_truth_surfaces_agree():
    surfaces = {
        "document": _read(),
        "status": _read(STATUS),
        "project": _read(PROJECT_STATUS),
        "repo_truth": _read(REPO_TRUTH),
    }
    normalized = {name: _normalized(text) for name, text in surfaces.items()}
    for token in DECISION_TOKENS:
        normalized_token = _normalized(token)
        for name in ("document", "status", "project"):
            assert normalized_token in normalized[name], (name, normalized_token)
    for path in (
        "docs/hermes_remote_provider_track_deferral_and_revisit_criteria_decision.md",
        "tests/test_hermes_remote_provider_track_deferral_and_revisit_criteria_decision_docs.py",
        "docs/status_entries/WP149.md",
    ):
        assert path in surfaces["repo_truth"]
    assert "WP149" in surfaces["project"] and "REVIEW_TARGET" in surfaces["project"]
    assert "WP148" in surfaces["project"] and "MERGED" in surfaces["project"]


def test_status_fragment_is_stable_and_has_required_structure():
    status = _read(STATUS)
    expected_headings = [
        "# WP149 — Hermes Remote Provider Track Deferral And Revisit Criteria Decision V1",
        "## Package Identity",
        "## Authorization Basis",
        "## Authority / Non-Authority",
        "## Merge Gate",
        "## Repository Inputs Reviewed",
        "## Repository Discovery",
        "## Deferral Decision",
        "## Meaning Of Deferral",
        "## Revisit Triggers",
        "## Non-Triggers",
        "## Materiality Standard",
        "## Revisit Evidence Packet",
        "## Anti-Loop Rules",
        "## Deferral Review Cadence",
        "## Reopen State Machine",
        "## Productive Next Phase",
        "## Promotion Gates",
        "## Deferred Capabilities",
        "## Changed Files",
        "## Requirement-To-Evidence",
        "## Validation",
        "## Model D Evidence",
        "## Stable Metadata",
        "## Follow-Up Classification",
        "## Ready For Review",
    ]
    headings = [
        line
        for line in status.splitlines()
        if line.startswith("# ") or line.startswith("## ")
    ]
    assert headings == expected_headings
    for forbidden in ("TBD", "LOCAL_DRAFT_VERIFIED", "Head commit:", "future mergeability"):
        assert forbidden not in status
    assert re.search(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", status, re.IGNORECASE
    ) is None
    assert "PR: see GitHub PR metadata and PR body." in status
    assert "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED" in status
    assert "Evidence architecture: Model D" in status


def test_predecessor_truth_remains_registered_without_reinterpretation():
    text = _read()
    assert "Evidence insufficiency is not provider impossibility." in text
    assert "Remote configurations deeply researched:\n3" in text
    assert text.count("Remote configurations eligible:\n0") >= 2
    assert text.count("Remote configurations shortlisted:\n0") >= 2
    assert text.count("Provider/model selection:\nNOT MADE") >= 2
    assert text.count("Remote controlled experiment readiness:\nNOT_READY") >= 2
