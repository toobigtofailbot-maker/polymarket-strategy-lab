"""Focused tests for WP109 Hermes candidate-review handoff manual export writer.

Tests the local/manual file writer added in WP109. Verifies that valid WP108
artifact results produce a Markdown file, result fields are correct, written
content is deterministic, required Markdown sections and safety flags are
present, boundary notice is present, invalid inputs fail closed, and the module
has no forbidden imports or CLI surface.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
WRITER_MODULE_PATH = ROOT / "src" / "data_layer" / "hermes_candidate_review_handoff_manual_export_writer.py"
ARTIFACT_MODULE_PATH = ROOT / "src" / "data_layer" / "hermes_candidate_review_handoff_manual_export_artifact.py"
WP106_MODULE_PATH = ROOT / "src" / "data_layer" / "hermes_candidate_review_operator_handoff.py"


# ---------------------------------------------------------------------------
# Module loaders
# ---------------------------------------------------------------------------


def _load(mod_name: str, path: Path) -> Any:
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


_writer = _load("hermes_candidate_review_handoff_manual_export_writer", WRITER_MODULE_PATH)
_artifact_mod = _load("hermes_candidate_review_handoff_manual_export_artifact", ARTIFACT_MODULE_PATH)
_wp106 = _load("hermes_candidate_review_operator_handoff", WP106_MODULE_PATH)

write_artifact = _writer.write_candidate_review_manual_export_artifact
WriteResult = _writer.CandidateReviewManualExportWriteResult

build_artifact = _artifact_mod.build_candidate_review_manual_export_artifact
ArtifactResult = _artifact_mod.CandidateReviewManualExportArtifactResult
REQUIRED_ARTIFACT_GROUPS = _artifact_mod.REQUIRED_ARTIFACT_GROUPS
REQUIRED_ARTIFACT_SAFETY_FLAGS = _artifact_mod.REQUIRED_ARTIFACT_SAFETY_FLAGS

build_handoff = _wp106.build_candidate_review_operator_handoff
HandoffResult = _wp106.HermesCandidateReviewOperatorHandoffResult


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


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


def _valid_handoff_data(decision_label: str = "ACCEPT_FOR_MANUAL_RESEARCH_REVIEW") -> dict[str, Any]:
    return {
        "handoff_identity": {
            "handoff_id": "test-handoff-001",
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
        "falsification_checks": {
            "checks": ["Checked for contradicting references."],
        },
        "human_decision_record": {
            "decision_label": decision_label,
            "operator_id": "test-operator",
            "timestamp_note": "2026-06-24",
            "rationale": "Manual review completed. Proceeding.",
        },
        "next_research_step": {
            "step_description": "Review additional source references.",
            "step_type": "MANUAL_RESEARCH",
        },
        "safety_flags": _valid_safety_flags(),
        "rejection_reasons": [],
    }


def _valid_handoff_result(decision_label: str = "ACCEPT_FOR_MANUAL_RESEARCH_REVIEW") -> Any:
    return build_handoff(_valid_handoff_data(decision_label))


def _valid_artifact_result(**kwargs: Any) -> Any:
    defaults: dict[str, Any] = {
        "artifact_id": "artifact-001",
        "handoff_result": _valid_handoff_result(),
    }
    defaults.update(kwargs)
    return build_artifact(**defaults)


# ---------------------------------------------------------------------------
# Test 1: Valid WP108 artifact result writes a Markdown file
# ---------------------------------------------------------------------------


def test_valid_artifact_result_writes_file(tmp_path: Path) -> None:
    artifact = _valid_artifact_result()
    out = tmp_path / "export.md"
    result = write_artifact(artifact_result=artifact, output_path=out)
    assert result.is_valid is True
    assert out.exists()


# ---------------------------------------------------------------------------
# Test 2: Result fields: is_valid=True, bytes_written > 0, sha256 length 64
# ---------------------------------------------------------------------------


def test_write_result_fields_valid(tmp_path: Path) -> None:
    artifact = _valid_artifact_result()
    out = tmp_path / "export.md"
    result = write_artifact(artifact_result=artifact, output_path=out)
    assert result.is_valid is True
    assert result.bytes_written > 0
    assert result.sha256 is not None
    assert len(result.sha256) == 64
    assert result.errors == ()


# ---------------------------------------------------------------------------
# Test 3: Written content is deterministic across repeated writes to different paths
# ---------------------------------------------------------------------------


def test_write_content_is_deterministic(tmp_path: Path) -> None:
    artifact = _valid_artifact_result()
    out1 = tmp_path / "export1.md"
    out2 = tmp_path / "export2.md"
    r1 = write_artifact(artifact_result=artifact, output_path=out1)
    r2 = write_artifact(artifact_result=artifact, output_path=out2)
    assert r1.sha256 == r2.sha256
    assert out1.read_bytes() == out2.read_bytes()


# ---------------------------------------------------------------------------
# Test 4: Required Markdown sections are present
# ---------------------------------------------------------------------------


def test_required_markdown_sections_present(tmp_path: Path) -> None:
    artifact = _valid_artifact_result()
    out = tmp_path / "export.md"
    write_artifact(artifact_result=artifact, output_path=out)
    content = out.read_text(encoding="utf-8")
    required_sections = [
        "# Hermes Candidate-Review Handoff Manual Export Artifact",
        "## Artifact Identity",
        "## Source Handoff Identity",
        "## Chain Stage Summary",
        "## Manual Review Summary",
        "## Evidence and Provenance Summary",
        "## Staleness and Missing-Data Summary",
        "## Uncertainty and Limitations Summary",
        "## Falsification Summary",
        "## Human Decision Record Summary",
        "## Next Manual Research Step",
        "## Safety Flags",
        "## Forbidden Scope Notice",
    ]
    for section in required_sections:
        assert section in content, f"Missing section: {section!r}"


# ---------------------------------------------------------------------------
# Test 5: Boundary notice is present
# ---------------------------------------------------------------------------


def test_boundary_notice_present(tmp_path: Path) -> None:
    artifact = _valid_artifact_result()
    out = tmp_path / "export.md"
    write_artifact(artifact_result=artifact, output_path=out)
    content = out.read_text(encoding="utf-8")
    assert "BOUNDARY NOTICE" in content
    assert "advisory only" in content.lower()
    assert "Human review is required" in content
    assert "NOT a trade signal" in content


# ---------------------------------------------------------------------------
# Test 6: All required WP108 safety flags are represented
# ---------------------------------------------------------------------------


def test_all_required_safety_flags_in_written_file(tmp_path: Path) -> None:
    artifact = _valid_artifact_result()
    out = tmp_path / "export.md"
    write_artifact(artifact_result=artifact, output_path=out)
    content = out.read_text(encoding="utf-8")
    for flag in REQUIRED_ARTIFACT_SAFETY_FLAGS:
        assert flag in content, f"Missing safety flag in output: {flag!r}"


# ---------------------------------------------------------------------------
# Test 7: Invalid WP108 artifact result fails closed and writes no file
# ---------------------------------------------------------------------------


def test_invalid_artifact_result_fails_closed(tmp_path: Path) -> None:
    invalid_artifact = ArtifactResult(is_valid=False, artifact={}, errors=("SOURCE_HANDOFF_NOT_VALID",))
    out = tmp_path / "export.md"
    result = write_artifact(artifact_result=invalid_artifact, output_path=out)
    assert result.is_valid is False
    assert not out.exists()
    assert result.bytes_written == 0
    assert result.sha256 is None


# ---------------------------------------------------------------------------
# Test 8: Unsupported input type fails closed and writes no file
# ---------------------------------------------------------------------------


def test_unsupported_input_type_fails_closed(tmp_path: Path) -> None:
    out = tmp_path / "export.md"
    result = write_artifact(artifact_result={"is_valid": True, "artifact": {}}, output_path=out)
    assert result.is_valid is False
    assert not out.exists()
    assert "UNSUPPORTED_INPUT_SHAPE" in result.errors


# ---------------------------------------------------------------------------
# Test 9: Missing artifact group fails closed and writes no file
# ---------------------------------------------------------------------------


def test_missing_artifact_group_fails_closed(tmp_path: Path) -> None:
    valid = _valid_artifact_result()
    incomplete_artifact = dict(valid.artifact)
    del incomplete_artifact["safety_flags"]
    broken_result = ArtifactResult(
        is_valid=True,
        artifact=incomplete_artifact,
        errors=(),
        warnings=(),
    )
    out = tmp_path / "export.md"
    result = write_artifact(artifact_result=broken_result, output_path=out)
    assert result.is_valid is False
    assert not out.exists()


# ---------------------------------------------------------------------------
# Test 10: Missing/false safety flag fails closed and writes no file
# ---------------------------------------------------------------------------


def test_missing_safety_flag_fails_closed(tmp_path: Path) -> None:
    valid = _valid_artifact_result()
    artifact_copy = dict(valid.artifact)
    bad_flags = dict(artifact_copy["safety_flags"])
    bad_flags["advisory_only"] = False
    artifact_copy["safety_flags"] = bad_flags
    broken = ArtifactResult(is_valid=True, artifact=artifact_copy, errors=(), warnings=())
    out = tmp_path / "export.md"
    result = write_artifact(artifact_result=broken, output_path=out)
    assert result.is_valid is False
    assert not out.exists()


# ---------------------------------------------------------------------------
# Test 11–15: Forbidden wording in artifact content fails closed (via WP108 builder)
# These tests verify that WP108 builder already rejects forbidden content, so
# only valid artifacts reach the writer. The writer validates the artifact is
# a valid, properly structured WP108 result.
# ---------------------------------------------------------------------------


def test_forbidden_trade_order_fails_at_builder_level() -> None:
    data = _valid_handoff_data()
    data["human_decision_record"]["timestamp_note"] = "buy now"
    result = build_handoff(data)
    assert result.is_valid is False


def test_forbidden_expected_return_fails_at_builder_level() -> None:
    data = _valid_handoff_data()
    data["human_decision_record"]["timestamp_note"] = "expected return is high"
    result = build_handoff(data)
    assert result.is_valid is False


def test_forbidden_paper_live_readiness_fails_at_builder_level() -> None:
    data = _valid_handoff_data()
    data["human_decision_record"]["timestamp_note"] = "live ready"
    result = build_handoff(data)
    assert result.is_valid is False


def test_forbidden_credential_fails_at_builder_level() -> None:
    data = _valid_handoff_data()
    data["human_decision_record"]["timestamp_note"] = "api key here"
    result = build_handoff(data)
    assert result.is_valid is False


def test_forbidden_prompt_model_fails_at_builder_level() -> None:
    data = _valid_handoff_data()
    data["human_decision_record"]["timestamp_note"] = "prompt runner invoked"
    result = build_handoff(data)
    assert result.is_valid is False


# ---------------------------------------------------------------------------
# Test 16: Raw/free-form metadata keys fail closed at builder level
# ---------------------------------------------------------------------------


def test_raw_metadata_key_fails_at_builder_level() -> None:
    data = _valid_handoff_data()
    data["raw_metadata"] = {"notes": "some notes"}
    result = build_handoff(data)
    assert result.is_valid is False


# ---------------------------------------------------------------------------
# Test 17: Unsafe caller text is not echoed in errors/warnings
# ---------------------------------------------------------------------------


def test_unsafe_caller_text_not_echoed_in_errors(tmp_path: Path) -> None:
    unsafe = "XSSINJECT<script>alert(1)</script>"
    invalid_artifact = ArtifactResult(is_valid=False, artifact={}, errors=(unsafe,))
    out = tmp_path / "export.md"
    result = write_artifact(artifact_result=invalid_artifact, output_path=out)
    assert result.is_valid is False
    for err in result.errors:
        assert unsafe not in err


# ---------------------------------------------------------------------------
# Test 18: Existing output path is not overwritten by default
# ---------------------------------------------------------------------------


def test_existing_path_not_overwritten_by_default(tmp_path: Path) -> None:
    artifact = _valid_artifact_result()
    out = tmp_path / "export.md"
    out.write_text("original content", encoding="utf-8")
    result = write_artifact(artifact_result=artifact, output_path=out)
    assert result.is_valid is False
    assert "OUTPUT_PATH_EXISTS_NO_OVERWRITE" in result.errors
    assert out.read_text(encoding="utf-8") == "original content"


# ---------------------------------------------------------------------------
# Test 19: overwrite=True overwrites deterministically
# ---------------------------------------------------------------------------


def test_overwrite_true_overwrites_file(tmp_path: Path) -> None:
    artifact = _valid_artifact_result()
    out = tmp_path / "export.md"
    out.write_text("original", encoding="utf-8")
    result = write_artifact(artifact_result=artifact, output_path=out, overwrite=True)
    assert result.is_valid is True
    assert out.read_text(encoding="utf-8") != "original"
    assert result.bytes_written > 0


# ---------------------------------------------------------------------------
# Test 20: Unsupported suffix fails closed and writes no file
# ---------------------------------------------------------------------------


def test_unsupported_suffix_fails_closed(tmp_path: Path) -> None:
    artifact = _valid_artifact_result()
    out = tmp_path / "export.json"
    result = write_artifact(artifact_result=artifact, output_path=out, expected_suffix=".json")
    assert result.is_valid is False
    assert not out.exists()
    assert "UNSUPPORTED_OUTPUT_SUFFIX" in result.errors


def test_txt_suffix_accepted_when_expected_suffix_is_txt(tmp_path: Path) -> None:
    artifact = _valid_artifact_result()
    out = tmp_path / "export.txt"
    result = write_artifact(artifact_result=artifact, output_path=out, expected_suffix=".txt")
    assert result.is_valid is True
    assert out.exists()


# ---------------------------------------------------------------------------
# Test 21: URL-like output paths fail closed and write no file
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("url_path", [
    "http://example.com/export.md",
    "https://example.com/export.md",
    "s3://mybucket/export.md",
    "gs://mybucket/export.md",
    "ftp://example.com/export.md",
])
def test_url_like_output_path_fails_closed(url_path: str, tmp_path: Path) -> None:
    artifact = _valid_artifact_result()
    result = write_artifact(artifact_result=artifact, output_path=url_path)
    assert result.is_valid is False
    assert "URI_SCHEME_NOT_ALLOWED_IN_OUTPUT_PATH" in result.errors


# ---------------------------------------------------------------------------
# Test 22: Module imports are stdlib-only plus approved WP108 import
# ---------------------------------------------------------------------------


def test_module_imports_stdlib_only_plus_approved_wp108_import() -> None:
    source = WRITER_MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    stdlib_allowed = {
        "dataclasses", "hashlib", "os", "pathlib", "typing",
        "__future__",
    }
    approved_internal = {
        "src.data_layer.hermes_candidate_review_handoff_manual_export_artifact",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
            else:
                mod = node.names[0].name if node.names else ""
            top = mod.split(".")[0]
            full = mod
            assert (
                top in stdlib_allowed
                or full in approved_internal
                or mod in approved_internal
            ), f"Forbidden import: {mod!r}"


# ---------------------------------------------------------------------------
# Test 23: Module has no network/subprocess/CLI imports
# ---------------------------------------------------------------------------


def test_module_has_no_network_subprocess_cli_imports() -> None:
    source = WRITER_MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_imports = {
        "requests", "httpx", "aiohttp", "urllib.request", "socket",
        "subprocess", "argparse", "click", "typer", "flask", "fastapi",
        "boto3", "paramiko",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
            else:
                mod = node.names[0].name if node.names else ""
            assert mod not in forbidden_imports, f"Forbidden import found: {mod!r}"
            top = mod.split(".")[0]
            assert top not in forbidden_imports, f"Forbidden import found: {top!r}"


# ---------------------------------------------------------------------------
# Test 24: Module has no argparse/click/typer/__main__ CLI surface
# ---------------------------------------------------------------------------


def test_module_has_no_cli_surface() -> None:
    source = WRITER_MODULE_PATH.read_text(encoding="utf-8")
    assert "argparse" not in source
    assert "click" not in source
    assert "typer" not in source
    assert '__main__' not in source


# ---------------------------------------------------------------------------
# Test 25: Module does not import Hermes/model/provider/network libraries
# ---------------------------------------------------------------------------


def test_module_has_no_hermes_model_provider_imports() -> None:
    source = WRITER_MODULE_PATH.read_text(encoding="utf-8")
    forbidden_terms = [
        "anthropic", "openai", "langchain", "llm", "hermes_runtime",
        "hermes_client", "boto3", "paramiko", "aiohttp", "httpx",
        "requests",
    ]
    lower = source.lower()
    for term in forbidden_terms:
        assert term not in lower, f"Forbidden library reference found: {term!r}"


# ---------------------------------------------------------------------------
# Test 26: Project status records WP109
# ---------------------------------------------------------------------------


def test_project_status_records_wp109() -> None:
    status = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    assert "WP109" in status


# ---------------------------------------------------------------------------
# Test 27: WP109 status entry exists
# ---------------------------------------------------------------------------


def test_wp109_status_entry_exists() -> None:
    entry = ROOT / "docs" / "status_entries" / "WP109.md"
    assert entry.is_file(), f"Missing: {entry}"


# ---------------------------------------------------------------------------
# Test 28: WP109 status entry lists exact changed-file inventory
# ---------------------------------------------------------------------------


def test_wp109_status_entry_lists_exact_changed_file_inventory() -> None:
    entry = ROOT / "docs" / "status_entries" / "WP109.md"
    text = entry.read_text(encoding="utf-8")
    expected_files = [
        "src/data_layer/hermes_candidate_review_handoff_manual_export_writer.py",
        "tests/test_hermes_candidate_review_handoff_manual_export_writer.py",
        "docs/status_entries/WP109.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_architecture_boundaries.py",
    ]
    for path in expected_files:
        assert path in text, f"Missing from WP109 status entry: {path!r}"


# ---------------------------------------------------------------------------
# Test 29: WP109 status entry does not contain dynamic/stale wording
# ---------------------------------------------------------------------------


def test_wp109_status_entry_no_stale_wording() -> None:
    import re
    entry = ROOT / "docs" / "status_entries" / "WP109.md"
    text = entry.read_text(encoding="utf-8")
    for stale_phrase in (
        "count depends",
        "TBD after merge",
        "WP109 active branch",
        "WP109 on branch",
        "LOCAL_DRAFT_VERIFIED",
    ):
        assert stale_phrase not in text, f"Stale wording found: {stale_phrase!r}"
    assert "Ready for review: YES" in text
    assert "stable and non-self-referential" in text
    fixed_sha = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_sha.search(text) is None


# ---------------------------------------------------------------------------
# Test 30: Architecture boundaries allowlist includes only the new WP109 source module
# ---------------------------------------------------------------------------


def test_architecture_boundaries_includes_wp109_source_module() -> None:
    boundaries = (ROOT / "tests" / "test_architecture_boundaries.py").read_text(encoding="utf-8")
    assert "hermes_candidate_review_handoff_manual_export_writer.py" in boundaries
