"""Focused tests for WP115 Hermes candidate-review manual export CLI."""

from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import importlib
import io
import json
from pathlib import Path
from typing import Any

import pytest

from src.data_layer.hermes_candidate_review_handoff_manual_export_artifact import (
    REQUIRED_ARTIFACT_GROUPS,
    REQUIRED_ARTIFACT_SAFETY_FLAGS,
    build_candidate_review_manual_export_artifact,
)
from src.data_layer.hermes_candidate_review_operator_handoff import (
    build_candidate_review_operator_handoff,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "hermes_candidate_review_manual_export_cli.py"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP115.md"


def _module() -> Any:
    return importlib.import_module("tools.hermes_candidate_review_manual_export_cli")


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


def _valid_handoff_data() -> dict[str, Any]:
    return {
        "handoff_identity": {
            "handoff_id": "synthetic-handoff-001",
            "contract_version": "WP105-V1",
            "chain_identifier": "candidate-review-chain",
            "generated_by": "WP106-test",
            "deterministic_owner": "local/offline",
        },
        "source_chain_summary": {
            "chain_stages": ["WP103", "WP101", "WP102", "WP104"],
            "summary": "Candidate-review chain summary.",
        },
        "packet_stage_summary": {"passed": True, "reason_codes": []},
        "receipt_stage_summary": {
            "passed": True,
            "checked_source_refs": ["ref-001"],
            "reason_codes": [],
        },
        "operator_review_stage_summary": {"passed": True, "reason_codes": []},
        "source_review_checklist": _valid_checklist(),
        "evidence_and_provenance": {
            "source_references": ["ref-001"],
            "provenance_status": "MANUALLY_INSPECTED",
            "evidence_summary": "Manual review of source references.",
            "artifact_references": [],
        },
        "staleness_and_missing_data": {
            "staleness_status": "CURRENT",
            "known_missing_data": [],
            "data_quality_warnings": [],
            "coverage_limits": [],
        },
        "uncertainty_and_limitations": {
            "uncertainty_notes": ["None identified."],
            "assumptions": ["None."],
            "limitations": [],
            "boundary_notes": [],
        },
        "falsification_checks": {"checks": ["Checked source references."]},
        "human_decision_record": {
            "decision_label": "ACCEPT_FOR_MANUAL_RESEARCH_REVIEW",
            "operator_id": "synthetic-operator",
            "timestamp_note": "2026-06-30",
            "rationale": "Manual review completed.",
        },
        "next_research_step": {
            "step_description": "Review additional source references.",
            "step_type": "MANUAL_RESEARCH",
        },
        "safety_flags": {
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
        },
        "rejection_reasons": [],
    }


def _valid_artifact_result() -> Any:
    handoff = build_candidate_review_operator_handoff(_valid_handoff_data())
    assert handoff.is_valid is True
    result = build_candidate_review_manual_export_artifact(
        artifact_id="synthetic-artifact-001",
        handoff_result=handoff,
    )
    assert result.is_valid is True
    return result


def _valid_envelope() -> dict[str, Any]:
    result = _valid_artifact_result()
    return {
        "envelope_type": "HERMES_CANDIDATE_REVIEW_MANUAL_EXPORT_ARTIFACT_RESULT_V1",
        "source_wp": "WP108",
        "source_contract": "WP107",
        "produced_by": "hermes_candidate_review_handoff_manual_export_artifact_v1",
        "artifact_result": {
            "is_valid": result.is_valid,
            "artifact": result.artifact,
            "errors": list(result.errors),
            "warnings": list(result.warnings),
        },
        "safety_flags": {
            flag: True for flag in REQUIRED_ARTIFACT_SAFETY_FLAGS
        },
        "provenance_notice": "LOCAL_MANUAL_OFFLINE_SYNTHETIC_REVIEWED",
        "human_review_required": True,
    }


def _write_envelope(tmp_path: Path, envelope: dict[str, Any]) -> Path:
    path = tmp_path / "artifact_result.json"
    path.write_text(json.dumps(envelope, sort_keys=True), encoding="utf-8")
    return path


def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = _module().main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _assert_no_artifact_content(text: str) -> None:
    forbidden = (
        "Hermes Candidate-Review Handoff Manual Export Artifact",
        "synthetic-artifact-001",
        "synthetic-handoff-001",
        "Manual review completed",
        "buy",
        "sell",
        "trade",
        "order",
        "expected return",
        "position sizing",
        "approve pr",
        "merge ready",
        "credential",
        "private state",
    )
    lower = text.lower()
    for term in forbidden:
        assert term.lower() not in lower


def test_cli_module_exists_and_exposes_main() -> None:
    mod = _module()
    assert MODULE_PATH.is_file()
    assert callable(mod.main)
    assert mod.main([]) in (2, 3)


def test_parser_accepts_exact_arguments() -> None:
    parser = _module()._parser()
    options = {
        option
        for action in parser._actions
        for option in action.option_strings
        if option != "-h" and option != "--help"
    }
    assert options == {"--artifact-json", "--output", "--overwrite"}
    assert not any(isinstance(action, argparse._SubParsersAction) for action in parser._actions)


def test_valid_strict_envelope_writes_markdown_artifact(tmp_path: Path) -> None:
    envelope_path = _write_envelope(tmp_path, _valid_envelope())
    output_path = tmp_path / "manual_export.md"
    code, stdout, stderr = _run_cli([
        "--artifact-json", str(envelope_path),
        "--output", str(output_path),
    ])
    assert code == 0
    assert stderr == ""
    assert output_path.is_file()
    payload = json.loads(stdout)
    assert payload["status"] == "success"
    assert payload["output_path"] == str(output_path)
    assert payload["bytes_written"] == len(output_path.read_bytes())
    assert payload["sha256"] == hashlib.sha256(output_path.read_bytes()).hexdigest()
    assert payload["warnings"] == []
    _assert_no_artifact_content(stdout)


def test_success_stdout_bounded_and_stderr_empty(tmp_path: Path) -> None:
    envelope_path = _write_envelope(tmp_path, _valid_envelope())
    output_path = tmp_path / "manual_export.txt"
    code, stdout, stderr = _run_cli([
        "--artifact-json", str(envelope_path),
        "--output", str(output_path),
    ])
    assert code == 0
    assert stderr == ""
    assert len(stdout) < 500
    assert set(json.loads(stdout).keys()) == {
        "bytes_written", "output_path", "sha256", "status", "warnings"
    }
    _assert_no_artifact_content(stdout + stderr)


def test_written_file_contains_boundary_notice_and_safety_flags(tmp_path: Path) -> None:
    envelope_path = _write_envelope(tmp_path, _valid_envelope())
    output_path = tmp_path / "manual_export.md"
    code, _, _ = _run_cli(["--artifact-json", str(envelope_path), "--output", str(output_path)])
    assert code == 0
    content = output_path.read_text(encoding="utf-8")
    assert "BOUNDARY NOTICE" in content
    for flag in REQUIRED_ARTIFACT_SAFETY_FLAGS:
        assert flag in content


def test_result_sha256_matches_written_bytes(tmp_path: Path) -> None:
    envelope_path = _write_envelope(tmp_path, _valid_envelope())
    output_path = tmp_path / "manual_export.md"
    code, stdout, _ = _run_cli(["--artifact-json", str(envelope_path), "--output", str(output_path)])
    assert code == 0
    assert json.loads(stdout)["sha256"] == hashlib.sha256(output_path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("mutator", "expected_code"),
    [
        (lambda env: env.clear(), 2),
        (lambda env: env.pop("envelope_type"), 2),
        (lambda env: env.__setitem__("source_wp", "WP999"), 2),
        (lambda env: env.__setitem__("source_contract", "WP999"), 2),
        (lambda env: env["artifact_result"].__setitem__("is_valid", False), 2),
        (lambda env: env["artifact_result"].__setitem__("errors", ["BAD"]), 2),
        (lambda env: env["artifact_result"]["artifact"].pop(REQUIRED_ARTIFACT_GROUPS[0]), 2),
        (lambda env: env["safety_flags"].pop(REQUIRED_ARTIFACT_SAFETY_FLAGS[0]), 2),
        (lambda env: env["safety_flags"].__setitem__(REQUIRED_ARTIFACT_SAFETY_FLAGS[0], False), 2),
        (lambda env: env["artifact_result"]["artifact"].__setitem__("metadata", {}), 2),
        (lambda env: env.__setitem__("raw_model_output", "blocked"), 2),
        (lambda env: env.__setitem__("produced_by", "raw Hermes output"), 2),
        (lambda env: env.__setitem__("provenance_notice", "prompt runner output"), 2),
        (lambda env: env["artifact_result"]["artifact"]["manual_review_summary"].__setitem__("note", "buy now"), 2),
    ],
)
def test_invalid_envelopes_fail_closed(
    tmp_path: Path, mutator: Any, expected_code: int
) -> None:
    envelope = _valid_envelope()
    mutator(envelope)
    envelope_path = _write_envelope(tmp_path, envelope)
    output_path = tmp_path / "manual_export.md"
    code, stdout, stderr = _run_cli(["--artifact-json", str(envelope_path), "--output", str(output_path)])
    assert code == expected_code
    assert stdout == ""
    assert not output_path.exists()
    assert "raw Hermes output" not in stderr
    assert "buy now" not in stderr
    _assert_no_artifact_content(stderr)


def test_uri_like_input_path_fails_closed(tmp_path: Path) -> None:
    output_path = tmp_path / "manual_export.md"
    code, _, _ = _run_cli(["--artifact-json", "https://example.invalid/a.json", "--output", str(output_path)])
    assert code in (3, 4)
    assert not output_path.exists()


def test_uri_like_output_path_fails_closed(tmp_path: Path) -> None:
    envelope_path = _write_envelope(tmp_path, _valid_envelope())
    code, _, _ = _run_cli(["--artifact-json", str(envelope_path), "--output", "s3://bucket/out.md"])
    assert code in (3, 4)


def test_output_suffix_parent_and_overwrite_policies(tmp_path: Path) -> None:
    envelope_path = _write_envelope(tmp_path, _valid_envelope())
    bad_suffix = tmp_path / "manual_export.json"
    missing_parent = tmp_path / "missing" / "manual_export.md"
    existing = tmp_path / "manual_export.md"
    existing.write_text("original", encoding="utf-8")

    assert _run_cli(["--artifact-json", str(envelope_path), "--output", str(bad_suffix)])[0] == 3
    assert _run_cli(["--artifact-json", str(envelope_path), "--output", str(missing_parent)])[0] == 3
    assert _run_cli(["--artifact-json", str(envelope_path), "--output", str(existing)])[0] == 3
    code, _, _ = _run_cli([
        "--artifact-json", str(envelope_path),
        "--output", str(existing),
        "--overwrite",
    ])
    assert code == 0
    assert existing.read_text(encoding="utf-8") != "original"


@pytest.mark.parametrize("repo_dir", ["docs", "src", "tests", "tools", ".github", "local_data"])
def test_output_under_protected_repo_paths_rejected(repo_dir: str, tmp_path: Path) -> None:
    envelope_path = _write_envelope(tmp_path, _valid_envelope())
    target = ROOT / repo_dir / "wp115-protected-output.md"
    code, _, _ = _run_cli(["--artifact-json", str(envelope_path), "--output", str(target)])
    assert code == 4
    assert not target.exists()


def test_no_unsafe_echo_when_input_contains_forbidden_content(tmp_path: Path) -> None:
    envelope = _valid_envelope()
    envelope["artifact_result"]["artifact"]["manual_review_summary"]["unsafe"] = (
        "api key secret private key buy now"
    )
    envelope_path = _write_envelope(tmp_path, envelope)
    output_path = tmp_path / "manual_export.md"
    code, stdout, stderr = _run_cli(["--artifact-json", str(envelope_path), "--output", str(output_path)])
    assert code == 2
    assert stdout == ""
    assert not output_path.exists()
    for unsafe in ("api key", "secret", "private key", "buy now"):
        assert unsafe not in stderr.lower()


def test_source_imports_only_allowed_modules() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    allowed_stdlib = {"__future__", "argparse", "json", "pathlib", "sys", "typing"}
    approved_internal = {
        "src.data_layer.hermes_candidate_review_handoff_manual_export_artifact",
        "src.data_layer.hermes_candidate_review_handoff_manual_export_writer",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
            assert module is not None
            top = module.split(".")[0]
            assert top in allowed_stdlib or module in approved_internal, module


def test_source_has_no_forbidden_imports_or_modes() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_imports = {
        "requests", "httpx", "aiohttp", "urllib.request", "socket", "subprocess",
        "click", "typer", "flask", "fastapi", "rich", "pydantic", "boto3",
        "paramiko", "openai", "anthropic", "web3",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
            assert module is not None
            assert module not in forbidden_imports
            assert module.split(".")[0] not in forbidden_imports
    parser = _module()._parser()
    option_strings = {
        option
        for action in parser._actions
        for option in action.option_strings
    }
    forbidden_options = {
        "--batch", "--watch", "--scheduler", "--daemon", "--network", "--model",
        "--provider", "--hermes", "--credential", "--account", "--paper",
        "--live", "--execution", "--risk", "--order", "--dashboard", "--config",
    }
    assert option_strings.isdisjoint(forbidden_options)


def test_changed_file_inventory_status_and_repo_truth_registration() -> None:
    status = STATUS_ENTRY.read_text(encoding="utf-8")
    expected = (
        "tools/hermes_candidate_review_manual_export_cli.py",
        "tests/test_hermes_candidate_review_manual_export_cli.py",
        "docs/status_entries/WP115.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_command_surface_contract_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_wrapper_contract_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_chain_closeout_docs.py",
        "tests/test_architecture_boundaries.py",
        "tests/test_wallet_intelligence_architecture_contract_docs.py",
        "tests/test_advisory_runtime_boundary_consumption_design_docs.py",
        "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
        "tests/test_human_review_label_workflow_docs.py",
        "tests/test_local_advisory_handoff_package_docs.py",
    )
    assert "Changed files (15):" in status
    for path in expected:
        assert path in status
    index = INDEX.read_text(encoding="utf-8")
    for path in expected[:3]:
        assert path in index


def test_project_status_records_wp115_and_preserves_boundaries() -> None:
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert "WP114" in merged_line
    assert "WP115" in text
    assert (
        "LOCAL_OFFLINE_MANUAL_CLI_WRAPPER_REVIEW_TARGET" in text
        or "LOCAL_OFFLINE_MANUAL_CLI_WRAPPER_MERGED" in text
    )
    for phrase in (
        "Live trading status: DISABLED",
        "Credentials status: NOT_USED",
        "Execution status: NOT_STARTED",
        "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "Agent runtime status: NOT_STARTED",
        "Agent execution authority: FORBIDDEN",
        "Scheduler status: NOT_STARTED",
        "Bot loop status: NOT_STARTED",
        "no product/runtime network",
        "no credentials",
        "no paper/live",
        "no execution/risk",
        "no scheduler/dashboard/bot-loop",
        "no Hermes runtime/provider/model/prompt runner",
        "no dependency/workflow/lock-file",
        "no committed generated-artifact",
    ):
        assert phrase in text
