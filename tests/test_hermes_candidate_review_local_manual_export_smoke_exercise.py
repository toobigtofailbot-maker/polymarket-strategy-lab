"""Focused WP111 smoke tests for temp-only local manual export exercise."""

from __future__ import annotations

import hashlib
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from src.data_layer.hermes_candidate_review_handoff_manual_export_artifact import (
    REQUIRED_ARTIFACT_SAFETY_FLAGS,
    build_candidate_review_manual_export_artifact,
)
from src.data_layer.hermes_candidate_review_handoff_manual_export_writer import (
    write_candidate_review_manual_export_artifact,
)
from src.data_layer.hermes_candidate_review_operator_handoff import (
    build_candidate_review_operator_handoff,
)


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_local_manual_export_smoke_exercise.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP111.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _valid_checklist() -> dict[str, bool]:
    return {
        "source_references_present": True,
        "source_references_manually_inspectable": True,
        "provenance_status_explicit": True,
        "staleness_status_explicit": True,
        "known_missing_data_explicit": True,
        "uncertainty_notes_explicit": True,
        "limitations_explicit": True,
        "falsification_checks_explicit": True,
        "next_research_step_explicit": True,
        "human_decision_record_explicit": True,
    }


def _valid_safety_flags() -> dict[str, bool]:
    return {
        "advisory_only": True,
        "human_review_required": True,
        "no_execution_authority": True,
        "no_runtime_authority": True,
        "no_credential_authority": True,
        "no_paper_or_live_authority": True,
        "no_prompt_execution": True,
        "no_file_or_network": True,
        "no_strategy_promotion_authority": True,
        "no_pr_approval_authority": True,
    }


def _safe_handoff_fixture() -> dict[str, Any]:
    return {
        "handoff_identity": {
            "handoff_id": "synthetic-handoff-111",
            "contract_version": "WP105-V1",
            "chain_identifier": "synthetic-candidate-review-chain",
            "generated_by": "wp111-smoke-test",
            "deterministic_owner": "local-offline",
        },
        "source_chain_summary": {
            "chain_stages": ["WP103", "WP101", "WP102", "WP104"],
            "summary": "Synthetic candidate review chain summary for local smoke coverage.",
        },
        "packet_stage_summary": {"passed": True, "reason_codes": []},
        "receipt_stage_summary": {
            "passed": True,
            "checked_source_refs": ["synthetic-ref-111"],
            "reason_codes": [],
        },
        "operator_review_stage_summary": {"passed": True, "reason_codes": []},
        "source_review_checklist": _valid_checklist(),
        "evidence_and_provenance": {
            "source_references": ["synthetic-ref-111"],
            "provenance_status": "SYNTHETIC_LOCAL_FIXTURE",
            "evidence_summary": "Synthetic reference reviewed for local smoke coverage.",
            "artifact_references": [],
        },
        "staleness_and_missing_data": {
            "staleness_status": "SYNTHETIC_CURRENT",
            "known_missing_data": [],
            "data_quality_warnings": [],
            "coverage_limits": [],
        },
        "uncertainty_and_limitations": {
            "uncertainty_notes": ["Synthetic fixture only."],
            "assumptions": ["Local pytest temporary directory only."],
            "limitations": ["No external data is used."],
            "boundary_notes": ["Manual review artifact smoke coverage only."],
        },
        "falsification_checks": {
            "checks": ["Synthetic fixture fields inspected."],
        },
        "human_decision_record": {
            "decision_label": "ACCEPT_FOR_MANUAL_RESEARCH_REVIEW",
            "operator_id": "synthetic-operator",
            "timestamp_note": "synthetic-date",
            "rationale": "Synthetic manual research review completed.",
        },
        "next_research_step": {
            "step_description": "Inspect synthetic source reference notes manually.",
            "step_type": "MANUAL_RESEARCH",
        },
        "safety_flags": _valid_safety_flags(),
        "rejection_reasons": [],
    }


def _assert_path_is_tmp_only(output_path: Path, tmp_path: Path) -> None:
    resolved_output = output_path.resolve()
    resolved_tmp = tmp_path.resolve()
    assert resolved_output.is_relative_to(resolved_tmp)

    forbidden_roots = [
        ROOT / "docs",
        ROOT / "src",
        ROOT / "tests",
        ROOT / "local_data",
    ]
    for forbidden_root in forbidden_roots:
        assert not resolved_output.is_relative_to(forbidden_root.resolve())


def _assert_fixture_contains_no_real_or_private_values(fixture: dict[str, Any]) -> None:
    serialized = repr(fixture).lower()
    for forbidden in (
        "wallet_id",
        "account_id",
        "private key",
        "api key",
        "secret",
        "order_id",
        "raw_metadata",
        "free_form_metadata",
        "model output",
        "prompt-runner",
        "paper state",
        "live state",
    ):
        assert forbidden not in serialized
    assert "synthetic" in serialized


def test_smoke_exercise_doc_exists_and_states_temp_only_pytest_scope() -> None:
    text = _normalized(_read(DOC)).lower()
    assert "temp-only pytest smoke exercise" in text
    assert "wp106 -> wp108 -> wp109" in text
    assert "`pytest` `tmp_path`" in text
    assert "synthetic safe fixture data only" in text
    assert "does not create, commit, preserve, or stage generated artifact files" in text


def test_smoke_exercise_doc_forbids_runtime_and_boundary_scope() -> None:
    text = _read(DOC).lower()
    for phrase in (
        "cli",
        "scheduler",
        "daemon",
        "background writer",
        "network",
        "api",
        "hermes runtime",
        "model",
        "provider",
        "prompt runner",
        "dashboard",
        "dependency",
        "workflow",
        "paper",
        "live",
        "execution",
        "risk",
        "order",
        "credentials",
        "account",
        "committed generated artifacts",
    ):
        assert phrase in text


def test_smoke_exercise_doc_forbids_misinterpretation_as_authority() -> None:
    text = _normalized(_read(DOC)).lower()
    for phrase in (
        "not a trade signal",
        "strategy recommendation",
        "paper or live readiness statement",
        "pr approval",
        "merge-readiness statement",
        "expected-return estimate",
        "position-sizing instruction",
        "runtime instruction",
        "execution authority",
    ):
        assert phrase in text


def test_smoke_exercise_writes_markdown_only_under_tmp_path(tmp_path: Path) -> None:
    fixture = _safe_handoff_fixture()
    _assert_fixture_contains_no_real_or_private_values(fixture)

    handoff_result = build_candidate_review_operator_handoff(fixture)
    assert handoff_result.is_valid is True

    artifact_result = build_candidate_review_manual_export_artifact(
        artifact_id="synthetic-artifact-111",
        handoff_result=handoff_result,
        operator_role="synthetic-operator",
    )
    assert artifact_result.is_valid is True

    output_path = tmp_path / "candidate_review_manual_export.md"
    _assert_path_is_tmp_only(output_path, tmp_path)

    result = write_candidate_review_manual_export_artifact(
        artifact_result=artifact_result,
        output_path=output_path,
    )

    assert result.is_valid is True
    assert output_path.exists()
    assert result.bytes_written > 0

    written_bytes = output_path.read_bytes()
    assert result.bytes_written == len(written_bytes)
    assert result.sha256 is not None
    assert re.fullmatch(r"[0-9a-f]{64}", result.sha256)
    assert result.sha256 == hashlib.sha256(written_bytes).hexdigest()

    content = written_bytes.decode("utf-8")
    assert "BOUNDARY NOTICE" in content
    assert "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED" in content
    for flag in REQUIRED_ARTIFACT_SAFETY_FLAGS:
        assert f"`{flag}`: True" in content

    for actionable_phrase in (
        "you should buy",
        "you should sell",
        "place an order",
        "submit an order",
        "increase position",
        "ready for live",
        "ready for paper",
        "approved for merge",
        "approved for execution",
        "use credentials",
    ):
        assert actionable_phrase not in content.lower()


def test_invalid_artifact_fails_closed_and_writes_no_file(tmp_path: Path) -> None:
    fixture = _safe_handoff_fixture()
    handoff_result = build_candidate_review_operator_handoff(fixture)
    artifact_result = build_candidate_review_manual_export_artifact(
        artifact_id="synthetic-artifact-111",
        handoff_result=handoff_result,
        operator_role="synthetic-operator",
    )
    invalid_artifact = replace(artifact_result, is_valid=False, artifact={})
    output_path = tmp_path / "candidate_review_manual_export.md"
    _assert_path_is_tmp_only(output_path, tmp_path)

    result = write_candidate_review_manual_export_artifact(
        artifact_result=invalid_artifact,
        output_path=output_path,
    )

    assert result.is_valid is False
    assert not output_path.exists()
    assert result.bytes_written == 0
    assert result.sha256 is None


def test_wp111_status_entry_exact_inventory_and_stable_wording() -> None:
    text = _read(STATUS_ENTRY)
    for path in (
        "docs/hermes_candidate_review_local_manual_export_smoke_exercise.md",
        "tests/test_hermes_candidate_review_local_manual_export_smoke_exercise.py",
        "docs/status_entries/WP111.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_hermes_candidate_review_local_manual_export_operator_runbook_docs.py",
        "tests/test_project_status_docs.py",
    ):
        assert path in text
    assert "Changed files (7):" in text
    for stale in (
        "WP111 on branch",
        "WP111 active branch",
        "TBD after merge",
        "PR: TBD",
        "count depends",
        "LOCAL_DRAFT_VERIFIED",
        "Head commit:",
    ):
        assert stale not in text
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_live_head.search(text) is None
    assert "Ready for review: YES only after final validation and posted evidence checks pass" in text


def test_project_status_records_wp111_without_runtime_activation() -> None:
    text = _read(PROJECT_STATUS)
    assert "WP111" in text
    assert "WP110" in next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert "Hermes candidate-review local manual export smoke exercise status" in text
    assert "DOCS_STATUS_TESTS_ONLY_TEMP_ONLY_LOCAL_MANUAL_EXPORT_SMOKE_EXERCISE_REVIEW_TARGET" in text
    for phrase in (
        "Live trading status: DISABLED",
        "Credentials status: NOT_USED",
        "Execution status: NOT_STARTED",
        "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "Agent runtime status: NOT_STARTED",
        "Agent execution authority: FORBIDDEN",
        "Scheduler status: NOT_STARTED",
        "Bot loop status: NOT_STARTED",
    ):
        assert phrase in text


def test_repo_truth_index_registers_wp111_surfaces() -> None:
    text = _read(INDEX)
    for path in (
        "docs/hermes_candidate_review_local_manual_export_smoke_exercise.md",
        "tests/test_hermes_candidate_review_local_manual_export_smoke_exercise.py",
        "docs/status_entries/WP111.md",
    ):
        assert path in text
