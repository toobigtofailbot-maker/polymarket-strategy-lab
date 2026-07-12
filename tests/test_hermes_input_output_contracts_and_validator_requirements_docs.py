"""Focused docs tests for WP97 Hermes contract and validator requirements."""

from __future__ import annotations

import pathlib
import re
import subprocess


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_DOC = REPO_ROOT / "docs" / "hermes_input_output_contracts_and_validator_requirements.md"
ARCH_DOC = REPO_ROOT / "docs" / "hermes_advisory_foundation_research_brain_architecture.md"
PLAN_DOC = REPO_ROOT / "docs" / "hermes_research_brain_execution_plan.md"
STATUS_DOC = REPO_ROOT / "docs" / "project_status.md"
STATUS_ENTRY = REPO_ROOT / "docs" / "status_entries" / "WP97.md"
REPO_TRUTH_INDEX = REPO_ROOT / "docs" / "repo_truth_index.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: pathlib.Path) -> str:
    return " ".join(_read(path).split())


def test_contract_doc_exists_and_is_registered() -> None:
    assert CONTRACT_DOC.is_file()
    index_text = _read(REPO_TRUTH_INDEX)
    assert "docs/hermes_input_output_contracts_and_validator_requirements.md" in index_text
    assert "tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py" in index_text
    assert STATUS_ENTRY.is_file()


def test_status_and_authority_are_docs_level_only() -> None:
    text = _flat(CONTRACT_DOC)
    required = (
        "WP97_REPO_TRUTH_DOCUMENTATION_LEVEL_CONTRACT_REQUIREMENTS",
        "docs/status/tests-only contract and validator requirements lock-in",
        "Runtime authority: NONE",
        "Execution authority: NONE",
        "Paper authority: NONE",
        "Live authority: NONE",
        "Credential authority: NONE",
        "This document defines documentation-level Hermes input/output contract requirements",
        "It is not a machine-readable schema",
        "not a runtime artifact",
        "not a prompt pack",
        "not an operator runbook",
        "not an exporter",
        "not a parser",
        "not a source-code validator",
        "Hermes remains not installed",
    )
    for phrase in required:
        assert phrase in text


def test_wp95_wp96_relationship_and_phase_two_are_explicit() -> None:
    text = _flat(CONTRACT_DOC)
    assert "WP95 is the accepted Hermes research-brain execution plan" in text
    assert "WP96 is the Hermes advisory foundation architecture" in text
    assert "WP97 documents Phase 2" in text
    assert "It does not override WP95 or WP96" in text


def test_input_families_and_required_input_fields_are_present() -> None:
    text = _read(CONTRACT_DOC)
    for phrase in (
        "repo-truth summary packet",
        "market research candidate packet",
        "wallet/candidate review packet",
        "resolution ambiguity packet",
        "cross-market relationship packet",
        "microstructure/slippage realism packet",
        "paper-result/failure-review packet",
        "performance-review packet",
        "experiment-design packet",
        "source artifact references",
        "provenance fields",
        "staleness fields",
        "data-quality warnings",
        "known missing-data fields",
        "advisory-only notice",
        "human-review-required flag",
        "deterministic owner",
        "forbidden-use notice",
    ):
        assert phrase in text


def test_output_families_and_required_output_fields_are_present() -> None:
    text = _read(CONTRACT_DOC)
    for phrase in (
        "research hypothesis",
        "experiment proposal",
        "market/candidate critique",
        "wallet-signal critique",
        "cross-market inconsistency note",
        "resolution ambiguity warning",
        "microstructure realism critique",
        "strategy critique",
        "failure-analysis note",
        "performance-improvement idea",
        "future-WP suggestion",
        "advisory-only output",
        "human-review-required flag",
        "evidence summary",
        "source artifact references",
        "confidence or uncertainty statement",
        "assumptions",
        "falsification path",
        "deterministic validation handoff",
        "rejected interpretation warning",
        "forbidden-action statement",
    ):
        assert phrase in text


def test_common_field_concepts_are_present() -> None:
    text = _read(CONTRACT_DOC)
    for phrase in (
        "`artifact_id` or equivalent reference",
        "`artifact_type`",
        "`source_refs`",
        "`provenance_status`",
        "`staleness_status`",
        "`data_quality_warnings`",
        "`human_review_required`",
        "`advisory_only`",
        "`forbidden_use_notice`",
        "`confidence_level`",
        "`uncertainty_notes`",
        "`assumptions`",
        "`falsification_checks`",
        "`deterministic_validation_handoff`",
        "`recommended_next_review_step`",
    ):
        assert phrase in text


def test_forbidden_output_matrix_contains_required_categories() -> None:
    text = _read(CONTRACT_DOC)
    for phrase in (
        "buy/sell/hold/enter/exit instruction",
        "position sizing",
        "allocation",
        "entry price / exit price / limit price as instruction",
        "stop loss / take profit as instruction",
        "order placement/cancel/sign/submit instruction",
        "risk override",
        "live readiness approval",
        "paper/live execution decision",
        "strategy promotion approval",
        "config mutation",
        "scheduler/bot-loop instruction",
        "credential request",
        "private endpoint request",
        "account data request",
        "PR approval",
        "merge-readiness claim",
        "final decision authority",
    ):
        assert phrase in text


def test_validator_requirements_are_recursive_fail_closed_and_no_echo() -> None:
    text = _read(CONTRACT_DOC)
    for phrase in (
        "recursive scan over top-level fields",
        "recursive scan over nested keys",
        "recursive scan over nested values",
        "scan over metadata/free-form text",
        "scan over warnings",
        "scan over limitations",
        "scan over advisory notices",
        "scan over examples",
        "scan over Markdown examples",
        "no raw unsafe echo from invalid inputs into public result fields",
        "safe quarantine/diagnostic policy",
        "negative-test matrix requirement",
        "invalid examples must become tests",
        "fail-closed behavior",
        "validators auto-applying, executing, scheduling, mutating config, approving PRs",
    ):
        assert phrase in text


def test_human_review_and_future_gates_are_explicit() -> None:
    text = _read(CONTRACT_DOC)
    for phrase in (
        "Hermes output is advisory only",
        "Accepted Hermes output may become a future human-reviewed WP",
        "Hermes cannot directly mutate repo truth",
        "Human review and deterministic validation are required",
        "actual machine-readable schemas",
        "source validators",
        "prompt packs",
        "operator runbooks",
        "context-packet exporters",
        "Hermes runtime/manual run process",
        "paper assistant integration",
        "live review assistant integration",
    ):
        assert phrase in text


def test_broad_research_freedom_and_deterministic_core_are_preserved() -> None:
    text = _read(CONTRACT_DOC)
    for phrase in (
        "powerful adaptive research brain",
        "market research",
        "edge discovery",
        "hypothesis generation",
        "experiment design",
        "strategy critique",
        "future WP recommendations",
        "failure analysis",
        "performance-improvement ideas",
        "wallet and candidate review",
        "regime monitoring",
        "cross-market inconsistency analysis",
        "resolution-rule ambiguity review",
        "microstructure/slippage realism review",
        "deterministic core remains responsible for execution",
        "risk",
        "credentials",
        "order lifecycle",
        "strategy-promotion gates",
    ):
        assert phrase in text


def test_plan_and_architecture_cross_reference_wp97_contract_doc() -> None:
    for path in (PLAN_DOC, ARCH_DOC):
        text = _read(path)
        assert "docs/hermes_input_output_contracts_and_validator_requirements.md" in text
    assert "WP97 documents Phase 2" in _read(ARCH_DOC)
    assert "documented by WP97" in _read(PLAN_DOC)


def test_project_status_records_wp97_stable_target_state() -> None:
    text = _read(STATUS_DOC)
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert "WP97" in merged_line
    assert "Hermes input/output contracts and validator requirements status" in text
    assert "docs/hermes_input_output_contracts_and_validator_requirements.md" in text
    assert "Next intended WP: Hermes research prompt pack and operator runbooks" in text


def test_status_docs_reject_wp97_stale_branch_placeholders() -> None:
    project_text = _read(STATUS_DOC)
    status_text = _read(STATUS_ENTRY)
    for text in (project_text, status_text):
        for phrase in (
            "WP97 on branch",
            "WP97 active branch",
            "Merge commit: TBD after merge",
            "PR: TBD",
            "Ready for review: YES paired with missing PR metadata",
        ):
            assert phrase not in text
        assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", text, re.IGNORECASE) is None


def test_status_entry_is_stable_and_boundary_complete() -> None:
    text = _read(STATUS_ENTRY)
    for phrase in (
        "PR: see GitHub PR metadata and PR body.",
        "Current live PR head: see GitHub PR metadata and PR body",
        "stable and non-self-referential",
        "Validated implementation commit:",
        "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED",
        "Ready for review: YES",
        "docs/hermes_input_output_contracts_and_validator_requirements.md",
        "No Hermes runtime, install, provider/model config, credential, machine-readable schema, source validator, prompt pack, runbook, exporter",
    ):
        assert phrase in text


def test_no_actual_hermes_implementation_artifacts_added() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
        text=True,
        timeout=60,
    ).stdout.splitlines()
    forbidden_patterns = (
        re.compile(r"(^|/)hermes.*schema.*\.(json|yaml|yml|py)$", re.IGNORECASE),
        re.compile(r"(^|/)hermes.*validator.*\.py$", re.IGNORECASE),
        re.compile(r"(^|/)hermes.*prompt", re.IGNORECASE),
        re.compile(r"(^|/)hermes.*runbook", re.IGNORECASE),
        re.compile(r"(^|/)hermes.*exporter.*\.py$", re.IGNORECASE),
        re.compile(r"(^|/)hermes.*runtime", re.IGNORECASE),
        re.compile(r"(^|/)hermes.*context.*packet", re.IGNORECASE),
        re.compile(r"^docs/ai/hermes/", re.IGNORECASE),
        re.compile(r"^docs/roadmap/.*hermes", re.IGNORECASE),
        re.compile(r"^tools/hermes/", re.IGNORECASE),
        re.compile(r"^src/.*/hermes", re.IGNORECASE),
    )
    allowed = {
        "docs/hermes_readonly_boundary.md",
        "docs/hermes_research_brain_execution_plan.md",
        "docs/hermes_advisory_foundation_research_brain_architecture.md",
        "docs/hermes_input_output_contracts_and_validator_requirements.md",
        "docs/status_entries/WP97.md",
        "tests/test_hermes_advisory_foundation_architecture_docs.py",
        "tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py",
        # WP98: docs-only prompt pack and runbook (authorized docs/tests, not implementation)
        "docs/hermes_research_prompt_pack_and_operator_runbooks.md",
        "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
        # WP99: local/offline/read-only deterministic validator (explicitly authorized)
        "src/data_layer/hermes_advisory_output_validator.py",
        "tests/test_hermes_advisory_output_validator.py",
        # WP100: local/offline/read-only deterministic context-packet builder
        "src/data_layer/hermes_context_packet_exporter.py",
        "tests/test_hermes_context_packet_exporter.py",
        # WP101: local/offline/read-only deterministic dry-run receipt helper
        "src/data_layer/hermes_context_packet_dry_run_receipt.py",
        "tests/test_hermes_context_packet_dry_run_receipt.py",
        # WP102: local/offline/read-only deterministic manual operator review helper
        "src/data_layer/hermes_manual_research_dry_run_review.py",
        "tests/test_hermes_manual_research_dry_run_review.py",
        # WP103: local/offline/read-only deterministic candidate-review context packet adapter
        "src/data_layer/hermes_candidate_review_context_packet_integration.py",
        "tests/test_hermes_candidate_review_context_packet_integration.py",
        # WP104: local/offline/read-only deterministic candidate-review manual chain smoke
        "src/data_layer/hermes_candidate_review_manual_chain_smoke.py",
        "tests/test_hermes_candidate_review_manual_chain_smoke.py",
        # WP106: local/offline/read-only deterministic in-memory candidate-review operator handoff object
        "src/data_layer/hermes_candidate_review_operator_handoff.py",
        "tests/test_hermes_candidate_review_operator_handoff.py",
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
        # WP110: docs/status/tests-only operator runbook for manual WP109 writer use
        "docs/hermes_candidate_review_local_manual_export_operator_runbook.md",
        # WP116: docs/status/tests-only operator runbook for manual WP115 CLI use
        "docs/hermes_candidate_review_local_manual_export_cli_operator_runbook.md",
        # WP119: docs/status/tests-only research workflow runbook
        "docs/hermes_candidate_review_research_workflow_runbook.md",
        # WP125: docs/status/tests-only operator runbook for the WP121-WP124 chain
        "docs/hermes_candidate_review_manual_research_session_package_operator_runbook.md",
        # WP126: local/offline/read-only in-memory research candidate queue validator
        "src/data_layer/hermes_candidate_review_research_candidate_queue.py",
        # WP127: docs/status/tests-only operator runbook for manual WP126 queue use
        "docs/hermes_candidate_review_research_candidate_queue_operator_runbook.md",
        # WP128: explicit-human-selection-only in-memory queue selection/question handoff validator
        "src/data_layer/hermes_candidate_review_manual_queue_selection_handoff.py",
        "src/data_layer/hermes_candidate_review_manual_research_briefing_packet.py",
        # WP132: explicit-caller-content-only in-memory manual research request validator
        "src/data_layer/hermes_candidate_review_manual_research_request.py",
        # WP133: explicit-caller-content-only in-memory manual research response validator
        "src/data_layer/hermes_candidate_review_manual_research_response.py",
        # WP129: docs/status/tests-only manual queue-selection-to-question chain runbook
        "docs/hermes_candidate_review_manual_queue_selection_research_question_chain_operator_runbook.md",
        # WP131: docs/status/tests-only manual research briefing packet runbook
        "docs/hermes_candidate_review_manual_research_briefing_packet_operator_runbook.md",
    }
    findings = []
    for path in tracked:
        normalized = path.replace("\\", "/")
        if normalized in allowed:
            continue
        if any(pattern.search(normalized) for pattern in forbidden_patterns):
            findings.append(normalized)
    assert findings == []
