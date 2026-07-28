"""Focused docs tests for WP98 Hermes research prompt pack and operator runbooks."""

from __future__ import annotations

import pathlib
import re
import subprocess


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PROMPT_PACK_DOC = REPO_ROOT / "docs" / "hermes_research_prompt_pack_and_operator_runbooks.md"
ARCH_DOC = REPO_ROOT / "docs" / "hermes_advisory_foundation_research_brain_architecture.md"
CONTRACT_DOC = REPO_ROOT / "docs" / "hermes_input_output_contracts_and_validator_requirements.md"
PLAN_DOC = REPO_ROOT / "docs" / "hermes_research_brain_execution_plan.md"
STATUS_DOC = REPO_ROOT / "docs" / "project_status.md"
STATUS_ENTRY = REPO_ROOT / "docs" / "status_entries" / "WP98.md"
REPO_TRUTH_INDEX = REPO_ROOT / "docs" / "repo_truth_index.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: pathlib.Path) -> str:
    return " ".join(_read(path).split())


# ── Existence and registration ──────────────────────────────────────────────

def test_prompt_pack_doc_exists() -> None:
    assert PROMPT_PACK_DOC.is_file()


def test_status_entry_exists() -> None:
    assert STATUS_ENTRY.is_file()


def test_prompt_pack_doc_is_registered_in_repo_truth_index() -> None:
    index_text = _read(REPO_TRUTH_INDEX)
    assert "docs/hermes_research_prompt_pack_and_operator_runbooks.md" in index_text


def test_prompt_pack_test_file_is_registered_in_repo_truth_index() -> None:
    index_text = _read(REPO_TRUTH_INDEX)
    assert "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py" in index_text


# ── Status and authority ──────────────────────────────────────────────────

def test_status_and_authority_forbid_runtime_artifacts() -> None:
    text = _flat(PROMPT_PACK_DOC)
    required = (
        "WP98_REPO_TRUTH_RESEARCH_PROMPT_PACK_AND_OPERATOR_RUNBOOKS",
        "docs/status/tests-only human-readable prompt pack and operator runbook foundation",
        "Runtime authority: NONE",
        "Execution authority: NONE",
        "Paper authority: NONE",
        "Live authority: NONE",
        "Credential authority: NONE",
        "Hermes installation, connection, provider, and model authority: NONE",
        "Prompt runner authority: NONE",
        "Machine-readable schema authority: NONE",
        "Automated prompt execution authority: NONE",
        "does not install Hermes",
        "does not connect Hermes",
        "does not run prompts",
        "does not call models",
        "does not execute any prompt template",
        "does not create machine-readable contracts",
        "does not create validators",
        "does not create exporters",
        "does not authorize Hermes runtime use",
        "Hermes remains not installed",
    )
    for phrase in required:
        assert phrase in text, f"Missing required phrase: {phrase!r}"


# ── WP95/WP96/WP97 relationship ─────────────────────────────────────────

def test_wp95_wp96_wp97_relationship_and_phase_three_are_explicit() -> None:
    text = _flat(PROMPT_PACK_DOC)
    assert "WP95 is the accepted Hermes research-brain execution plan" in text
    assert "WP96 is the Hermes advisory foundation architecture" in text
    assert "WP97 is the Hermes input/output contract requirements" in text
    assert "WP98 is Phase 3" in text
    assert "does not override WP95, WP96, or WP97" in text
    assert "docs/hermes_research_brain_execution_plan.md" in text
    assert "docs/hermes_advisory_foundation_research_brain_architecture.md" in text
    assert "docs/hermes_input_output_contracts_and_validator_requirements.md" in text


# ── Manual-use-only rule ──────────────────────────────────────────────────

def test_manual_use_only_rule_is_present() -> None:
    text = _flat(PROMPT_PACK_DOC)
    required = (
        "manual-use-only",
        "No prompt may be executed by an automated runner",
        "scheduler",
        "bot loop",
        "script",
        "does not involve a human operator",
        "Hermes is not installed",
        "no authorized runtime provider or model",
    )
    for phrase in required:
        assert phrase in text, f"Missing required phrase: {phrase!r}"


# ── Operator preflight checklist ──────────────────────────────────────────

def test_operator_preflight_checklist_is_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    required = (
        "Operator Preflight Checklist",
        "not authorized for automated execution",
        "sanitized context",
        "No private account data",
        "private keys",
        "provenance notes",
        "staleness notes",
        "Hermes output is advisory only",
        "human review",
        "deterministic validation",
        "approved WP",
        "prompt injection risk",
    )
    for phrase in required:
        assert phrase in text, f"Missing required phrase: {phrase!r}"


# ── Input preparation rules ────────────────────────────────────────────────

def test_input_preparation_rules_are_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    required = (
        "Input Preparation Rules",
        "source_refs",
        "provenance_status",
        "staleness_status",
        "data_quality_warnings",
        "known_missing_data",
        "advisory_only: true",
        "human_review_required: true",
        "forbidden_use_notice",
        "private keys",
        "API credentials",
        "authenticated account data",
    )
    for phrase in required:
        assert phrase in text, f"Missing required phrase: {phrase!r}"


# ── Prompt-injection policy ────────────────────────────────────────────────

def test_prompt_injection_policy_is_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    required = (
        "Prompt-Injection And Untrusted-Input Policy",
        "Untrusted input includes",
        "external API response text",
        "user-submitted strings",
        "prompt injection is suspected",
        "discard the output",
        "report the incident",
    )
    for phrase in required:
        assert phrase in text, f"Missing required phrase: {phrase!r}"


# ── Common prompt wrapper requirements ────────────────────────────────────

def test_common_prompt_wrapper_requirements_are_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    flat = _flat(PROMPT_PACK_DOC)
    required_in_read = (
        "Common Prompt Wrapper Requirements",
        "ADVISORY RESEARCH PROMPT",
        "HUMAN REVIEW REQUIRED",
        "Advisory notice:",
        "Human review required: YES",
        "No execution authority: YES",
        "No risk override: YES",
    )
    for phrase in required_in_read:
        assert phrase in text, f"Missing required phrase: {phrase!r}"
    required_in_flat = (
        "not an instruction",
        "not a signal",
        "not a trade direction",
        "not a position size",
        "not an allocation",
        "not an order",
        "not a risk override",
        "not an execution decision",
        "not a paper/live authorization",
        "not a strategy promotion",
        "not a config change",
        "not a scheduler instruction",
        "not a credential request",
        "not a PR approval",
    )
    for phrase in required_in_flat:
        assert phrase in flat, f"Missing required phrase in flat text: {phrase!r}"


# ── Common output requirements ────────────────────────────────────────────

def test_common_output_requirements_are_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    required = (
        "Common Output Requirements",
        "advisory_only",
        "human_review_required",
        "no_execution_authority",
        "no_risk_override",
        "no_credential_request",
        "no_order_or_cancel_or_sign_or_submit",
        "no_paper_live_decision",
        "no_strategy_promotion_approval",
        "no_pr_approval_or_merge_readiness_claim",
        "evidence_summary",
        "source_refs",
        "provenance_status",
        "staleness_status",
        "confidence_level",
        "uncertainty_notes",
        "assumptions",
        "falsification_path",
        "deterministic_validation_handoff",
        "rejected_interpretations",
        "forbidden_action_statement",
        "next_human_review_step",
    )
    for phrase in required:
        assert phrase in text, f"Missing required phrase: {phrase!r}"


# ── Ten prompt families ───────────────────────────────────────────────────

def test_all_ten_prompt_families_are_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    families = (
        "Family 1: Broad Market-Edge Hypothesis Generation",
        "Family 2: Wallet/Candidate Review",
        "Family 3: Resolution-Rule Ambiguity Analysis",
        "Family 4: Cross-Market Inconsistency Analysis",
        "Family 5: Microstructure/Slippage Realism Critique",
        "Family 6: Strategy Critique",
        "Family 7: Failure Analysis / Postmortem",
        "Family 8: Performance-Improvement Idea Review",
        "Family 9: Experiment Design",
        "Family 10: Future WP Recommendation",
    )
    for family in families:
        assert family in text, f"Missing prompt family: {family!r}"


def test_every_prompt_family_template_has_advisory_only() -> None:
    text = _read(PROMPT_PACK_DOC)
    # Count occurrences of "advisory_only: true" in templates — one per family at minimum
    count = text.count("advisory_only: true")
    assert count >= 10, f"Expected at least 10 occurrences of 'advisory_only: true', got {count}"


def test_every_prompt_family_template_has_human_review_required() -> None:
    text = _read(PROMPT_PACK_DOC)
    count = text.count("human_review_required: true")
    assert count >= 10, f"Expected at least 10 occurrences of 'human_review_required: true', got {count}"


def test_every_prompt_family_template_has_no_execution_authority() -> None:
    text = _read(PROMPT_PACK_DOC)
    count = text.count("no_execution_authority: true")
    assert count >= 10, f"Expected at least 10 occurrences of 'no_execution_authority: true', got {count}"


def test_every_prompt_family_template_has_no_risk_override() -> None:
    text = _read(PROMPT_PACK_DOC)
    count = text.count("no_risk_override: true")
    assert count >= 10, f"Expected at least 10 occurrences of 'no_risk_override: true', got {count}"


def test_every_prompt_family_template_has_deterministic_validation_handoff() -> None:
    text = _read(PROMPT_PACK_DOC)
    count = text.count("deterministic_validation_handoff")
    assert count >= 10, f"Expected at least 10 occurrences of 'deterministic_validation_handoff', got {count}"


def test_every_prompt_family_template_has_falsification_path() -> None:
    text = _read(PROMPT_PACK_DOC)
    count = text.count("falsification_path")
    assert count >= 10, f"Expected at least 10 occurrences of 'falsification_path', got {count}"


def test_every_prompt_family_template_has_evidence_provenance_staleness() -> None:
    text = _read(PROMPT_PACK_DOC)
    # Each family template requests evidence (per-template in output structure)
    assert text.count("evidence_summary") >= 10
    assert text.count("uncertainty_notes") >= 10
    assert text.count("assumptions") >= 10
    # provenance and staleness appear in common sections and input/output requirements
    assert text.count("provenance") >= 3, f"Expected provenance >= 3, got {text.count('provenance')}"
    assert text.count("staleness") >= 3, f"Expected staleness >= 3, got {text.count('staleness')}"
    # provenance_status and staleness_status specifically in the common output requirements
    assert "provenance_status" in text
    assert "staleness_status" in text


def test_every_prompt_family_template_has_no_pr_approval_claim() -> None:
    text = _read(PROMPT_PACK_DOC)
    count = text.count("no_pr_approval_or_merge_readiness_claim")
    assert count >= 10, f"Expected at least 10 occurrences of 'no_pr_approval_or_merge_readiness_claim', got {count}"


def test_every_prompt_family_template_has_no_strategy_promotion() -> None:
    text = _read(PROMPT_PACK_DOC)
    count = text.count("no_strategy_promotion_approval")
    assert count >= 10, f"Expected at least 10 occurrences of 'no_strategy_promotion_approval', got {count}"


def test_every_prompt_family_template_has_forbidden_action_statement() -> None:
    text = _read(PROMPT_PACK_DOC)
    count = text.count("forbidden_action_statement")
    assert count >= 10, f"Expected at least 10 occurrences of 'forbidden_action_statement', got {count}"


# ── Prompt templates preserve broad research usefulness ──────────────────

def test_prompt_families_preserve_broad_research_usefulness() -> None:
    flat = _flat(PROMPT_PACK_DOC)
    required = (
        "market research",
        "edge discovery",
        "hypothesis generation",
        "strategy critique",
        "failure analysis",
        "wallet",
        "candidate review",
        "cross-market inconsistency analysis",
        "resolution-rule ambiguity",
        "microstructure",
        "slippage realism",
        "performance-improvement",
        "experiment design",
        "future WP recommendation",
    )
    for phrase in required:
        assert phrase in flat, f"Missing research family phrase: {phrase!r}"


def test_hermes_is_not_a_passive_summarizer() -> None:
    text = _flat(PROMPT_PACK_DOC)
    # Guardrails must not reduce research usefulness — doc should acknowledge broad scope
    assert "broad" in text
    assert "research" in text
    assert "advisory research" in text


# ── Output review checklist ────────────────────────────────────────────────

def test_output_review_checklist_is_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    required = (
        "Output Review Checklist",
        "advisory_only: true",
        "human_review_required: true",
        "no_execution_authority: true",
        "evidence_summary",
        "source_refs",
        "confidence_level",
        "uncertainty_notes",
        "assumptions",
        "falsification_path",
        "deterministic_validation_handoff",
        "forbidden_action_statement",
        "next_human_review_step",
        "forbidden language from Section 11",
        "skip human review",
        "override safety rules",
        "access credentials",
        "place orders",
        "approve a PR",
        "discard",
    )
    for phrase in required:
        assert phrase in text, f"Missing review checklist phrase: {phrase!r}"


# ── Forbidden prompt/output matrix ────────────────────────────────────────

def test_forbidden_output_matrix_is_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    required = (
        "Forbidden Prompt/Output Matrix",
        "Buy/sell/hold/enter/exit instructions",
        "Position sizing",
        "Allocation",
        "Entry/exit/limit price as instruction",
        "Stop loss/take profit as instruction",
        "Order placement/cancel/sign/submit",
        "Risk override",
        "Live readiness approval",
        "Paper/live execution decision",
        "Strategy promotion approval",
        "Config mutation",
        "Scheduler/bot-loop instruction",
        "Credential request",
        "Private endpoint request",
        "Account data request",
        "PR approval",
        "Merge-readiness claim",
        "Final decision authority",
    )
    for phrase in required:
        assert phrase in text, f"Missing forbidden matrix phrase: {phrase!r}"


def test_forbidden_matrix_preserves_wp97_forbidden_categories() -> None:
    # These exact categories from WP97 must be in the WP98 forbidden matrix
    text = _read(PROMPT_PACK_DOC)
    wp97_categories = (
        "buy/sell/hold/enter/exit",
        "position sizing",
        "allocation",
        "entry price",
        "exit price",
        "limit price",
        "stop loss",
        "take profit",
        "order placement",
        "cancel",
        "sign",
        "submit",
        "risk override",
        "live readiness approval",
        "paper/live execution decision",
        "strategy promotion approval",
        "config mutation",
        "scheduler",
        "bot-loop",
        "credential request",
        "private endpoint request",
        "account data request",
        "PR approval",
        "merge-readiness claim",
        "final decision authority",
    )
    flat = _flat(PROMPT_PACK_DOC)
    for category in wp97_categories:
        assert category.lower() in flat.lower(), f"Missing WP97 forbidden category: {category!r}"


# ── Human review and deterministic handoff rules ────────────────────────

def test_human_review_and_deterministic_handoff_rules_are_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    required = (
        "Human-Review And Deterministic Handoff Rules",
        "Human review:",
        "Deterministic validation:",
        "Approved WP:",
        "Hermes cannot:",
        "directly mutate repo truth",
        "approve its own WP",
        "approve a PR or claim merge readiness",
        "mutate configs or parameters",
        "authorize paper or live execution",
        "override risk gates",
        "issue orders, cancels, signs, or submissions",
        "request or handle credentials",
        "access private endpoints or account data",
        "start or stop the scheduler or bot loop",
    )
    for phrase in required:
        assert phrase in text, f"Missing handoff rule phrase: {phrase!r}"


# ── Failure/stop conditions ────────────────────────────────────────────────

def test_failure_stop_conditions_are_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    flat = _flat(PROMPT_PACK_DOC)
    required_in_read = (
        "Failure / Stop Conditions",
        "missing `advisory_only: true`",
        "missing `human_review_required: true`",
        "forbidden category from Section 11",
        "trade instruction",
        "position size",
        "or an order",
        "private keys",
        "cancel an order",
        "sign a transaction",
        "mutate repo truth",
        "prompt injection",
        "Discard the affected output",
        "Document the stop condition",
    )
    for phrase in required_in_read:
        assert phrase in text, f"Missing stop condition phrase: {phrase!r}"
    required_in_flat = (
        "claims to approve a PR",
        "approve a PR or a strategy",
        "instructs the operator to skip human review",
        "override safety",
        "requests credentials",
        "instructs the operator to place an order",
        "claims merge readiness",
    )
    for phrase in required_in_flat:
        assert phrase in flat, f"Missing stop condition phrase in flat text: {phrase!r}"


# ── Manual setup dependency note ──────────────────────────────────────────

def test_manual_setup_dependency_note_is_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    flat = _flat(PROMPT_PACK_DOC)
    required_in_read = (
        "Manual Setup Dependency Note",
        "does not install Hermes",
        "does not connect Hermes",
        "does not authorize any Hermes runtime use",
        "credential management",
        "context-packet exporter implementation",
        "source validators",
        "docs/agent_hermes_manual_setup_decision_record.md",
    )
    for phrase in required_in_read:
        assert phrase in text, f"Missing manual setup phrase: {phrase!r}"
    assert "provider and model selection" in flat, "Missing 'provider and model selection' in flat text"


# ── Future implementation gates ────────────────────────────────────────────

def test_future_implementation_gates_are_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    required = (
        "Future Implementation Gates",
        "WP98 explicitly defers",
        "Hermes installation and provider/model configuration",
        "prompt runner implementation",
        "automated prompt execution",
        "context-packet exporter implementation",
        "source validators for input/output contract enforcement",
        "machine-readable schemas for prompt pack validation",
        "paper assistant integration",
        "live review assistant integration",
        "scheduler or bot-loop automation",
        "requires a separately approved WP",
    )
    for phrase in required:
        assert phrase in text, f"Missing implementation gate phrase: {phrase!r}"


# ── Repo-truth update rule ────────────────────────────────────────────────

def test_repo_truth_update_rule_is_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    flat = _flat(PROMPT_PACK_DOC)
    assert "Repo-Truth Update Rule" in text
    assert "Material changes to this prompt pack" in text
    assert "same WP or an approved follow-up" in flat
    assert "Chat memory and PR comments alone are not authoritative" in flat


# ── Next WP sequence pointer ──────────────────────────────────────────────

def test_next_wp_sequence_pointer_is_present() -> None:
    text = _read(PROMPT_PACK_DOC)
    assert "Next WP Sequence Pointer" in text
    assert "Hermes contract validator implementation" in text
    assert "Context-packet exporter implementation" in text
    assert "separately approved WP" in text


# ── Stable status wording in committed docs ───────────────────────────────

def test_status_entry_has_no_tbd_after_merge_wording() -> None:
    text = _read(STATUS_ENTRY)
    assert "Merge commit: TBD after merge" not in text
    assert "PR: TBD" not in text


def test_status_entry_uses_stable_see_github_wording() -> None:
    text = _read(STATUS_ENTRY)
    assert "see GitHub PR metadata and PR body" in text
    assert "see GitHub PR metadata after merge" in text


def test_status_entry_does_not_encode_live_head_sha() -> None:
    # Status fragments must not embed a fixed live PR head SHA
    text = _read(STATUS_ENTRY)
    assert "Current live PR head: see GitHub PR metadata and PR body" in text
    sha_pattern = re.compile(r"Current live PR head:\s+[0-9a-f]{40}")
    assert not sha_pattern.search(text)


def test_prompt_pack_doc_has_no_branch_live_wording() -> None:
    text = _read(PROMPT_PACK_DOC)
    assert "WP98 on branch" not in text
    assert "WP98 active branch" not in text
    assert "Merge commit: TBD after merge" not in text


# ── Project status consistency ─────────────────────────────────────────────

def test_project_status_records_wp98_as_target_state() -> None:
    text = _read(STATUS_DOC)
    assert "WP98" in text


def test_project_status_hermes_prompt_pack_status_is_registered() -> None:
    text = _read(STATUS_DOC)
    assert "Hermes research prompt pack" in text.lower() or "hermes research prompt pack" in text.lower()


def test_project_status_hermes_not_installed() -> None:
    text = _read(STATUS_DOC)
    assert "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY" in text


def test_project_status_live_trading_disabled() -> None:
    text = _read(STATUS_DOC)
    assert "Live trading status: DISABLED" in text


def test_project_status_credentials_not_used() -> None:
    text = _read(STATUS_DOC)
    assert "Credentials status: NOT_USED" in text


def test_project_status_execution_not_started() -> None:
    text = _read(STATUS_DOC)
    assert "Execution status: NOT_STARTED" in text


def test_project_status_scheduler_not_started() -> None:
    text = _read(STATUS_DOC)
    assert "Scheduler status: NOT_STARTED" in text


def test_project_status_bot_loop_not_started() -> None:
    text = _read(STATUS_DOC)
    assert "Bot loop status: NOT_STARTED" in text


def test_project_status_wp98_in_merged_wps_list() -> None:
    text = _read(STATUS_DOC)
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP98" in merged_line


# ── No forbidden runtime artifacts added ─────────────────────────────────

def test_no_src_implementation_for_wp98() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "main..HEAD"],
        capture_output=True, text=True,
        cwd=str(REPO_ROOT),
    )
    changed_files = result.stdout.strip().splitlines()
    later_authorized_src = {
        "src/data_layer/hermes_advisory_output_validator.py",
        "src/data_layer/hermes_context_packet_exporter.py",
        "src/data_layer/hermes_context_packet_dry_run_receipt.py",
        "src/data_layer/hermes_manual_research_dry_run_review.py",
        # WP103: local/offline/read-only deterministic candidate-review context packet adapter
        "src/data_layer/hermes_candidate_review_context_packet_integration.py",
        # WP104: local/offline/read-only deterministic candidate-review manual chain smoke
        "src/data_layer/hermes_candidate_review_manual_chain_smoke.py",
        # WP106: local/offline/read-only deterministic in-memory candidate-review operator handoff object
        "src/data_layer/hermes_candidate_review_operator_handoff.py",
        # WP108: local/offline/read-only in-memory candidate-review handoff manual export artifact builder
        "src/data_layer/hermes_candidate_review_handoff_manual_export_artifact.py",
        # WP109: local/offline/manual-only explicit file writer for valid WP108 artifacts
        "src/data_layer/hermes_candidate_review_handoff_manual_export_writer.py",
        # WP121: local/offline/read-only in-memory research question record validator
        "src/data_layer/hermes_candidate_review_research_question_record.py",
        # WP122: local/offline/read-only in-memory advisory output validation receipt validator
        "src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py",
        # WP123: local/offline/read-only in-memory human decision and follow-up record validator
        "src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py",
        # WP124: local/offline/read-only in-memory manual research session package validator
        "src/data_layer/hermes_candidate_review_manual_research_session_package.py",
        # WP128: explicit-human-selection-only in-memory queue selection/question handoff validator
        "src/data_layer/hermes_candidate_review_manual_queue_selection_handoff.py",
        "src/data_layer/hermes_candidate_review_manual_research_briefing_packet.py",
            # WP133: local/offline/read-only in-memory manual research response validator
            "src/data_layer/hermes_candidate_review_manual_research_response.py",
            # WP145: local/offline test-oriented deterministic one-case harness
            "src/data_layer/hermes_candidate_review_assisted_research_local_dry_run_harness.py",
            # WP152: bounded local/offline deterministic Wave 1 measurement harness
                "src/data_layer/local_research_value_measurement/__init__.py",
                "src/data_layer/local_research_value_measurement/harness.py",
                # WP156: bounded local/offline deterministic point-in-time validator
                "src/data_layer/point_in_time_market_research/__init__.py",
                "src/data_layer/point_in_time_market_research/records.py",
                "src/data_layer/point_in_time_market_research/synthetic_corpus.py",
                # WP157: bounded in-memory point-in-time as-of query implementation
                "src/data_layer/point_in_time_market_research/as_of_query.py",
                "src/data_layer/point_in_time_market_research/as_of_synthetic_cases.py",
            }
    for f in changed_files:
        assert not f.startswith("src/") or f in later_authorized_src, (
            f"Forbidden src/ file changed: {f}"
        )
        allowed_later_tools = {
            "tools/hermes_candidate_review_manual_export_cli.py",
        }
        assert not f.startswith("tools/") or f in allowed_later_tools, (
            f"Forbidden tools/ file changed: {f}"
        )
        assert not f.startswith(".github/workflows/"), f"Forbidden workflow file changed: {f}"
        forbidden_deps = (
            "requirements.txt", "pyproject.toml", "package.json",
            "package-lock.json", "poetry.lock", "Cargo.toml", "Cargo.lock",
        )
        for dep in forbidden_deps:
            assert f != dep, f"Forbidden dependency file changed: {f}"


def test_prior_hermes_docs_still_exist_and_canonical() -> None:
    assert PLAN_DOC.is_file()
    assert ARCH_DOC.is_file()
    assert CONTRACT_DOC.is_file()


def test_prompt_pack_doc_does_not_imply_hermes_can_run_automatically() -> None:
    text = _read(PROMPT_PACK_DOC)
    forbidden_claims = (
        "Hermes can run automatically",
        "Hermes will call the model",
        "automatically executes",
        "runs on a schedule",
        "bot loop executes",
        "prompt runner executes",
    )
    for claim in forbidden_claims:
        assert claim not in text, f"Forbidden automatic-execution claim found: {claim!r}"


def test_prompt_pack_doc_does_not_imply_hermes_mutates_repo_truth() -> None:
    text = _read(PROMPT_PACK_DOC)
    forbidden_claims = (
        "Hermes may update repo truth",
        "Hermes can merge",
        "Hermes approves the PR",
        "Hermes approves strategy",
        "Hermes mutates config",
    )
    for claim in forbidden_claims:
        assert claim not in text, f"Forbidden repo-mutation claim found: {claim!r}"
