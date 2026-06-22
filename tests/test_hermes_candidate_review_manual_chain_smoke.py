"""Focused tests for the WP104 Hermes candidate-review manual chain smoke."""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

import pytest

from src.data_layer.hermes_candidate_review_manual_chain_smoke import (
    HermesChainSmokeResult,
    run_candidate_review_manual_chain_smoke,
)
from src.data_layer.hermes_context_packet_dry_run_receipt import (
    REQUIRED_READINESS_CHECKS,
)
from src.data_layer.hermes_manual_research_dry_run_review import (
    REQUIRED_SOURCE_REVIEW_CHECKS,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT / "src" / "data_layer" / "hermes_candidate_review_manual_chain_smoke.py"
)
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP104.md"


# ── Helper builders ──────────────────────────────────────────────────────────


def _valid_packet_kwargs() -> dict[str, object]:
    return {
        "packet_id": "smoke_packet_001",
        "report_identity": "candidate_review_report_001",
        "source_refs": [
            "docs/project_status.md",
            "docs/repo_truth_index.md",
        ],
        "advisory_notice": "Advisory review context. Human review required before any use.",
        "human_review_required": True,
        "review_status": "REVIEW_VALIDATED_RECORD",
        "provenance_status": "verified_local_fixture",
        "staleness_status": "current_at_manual_review",
        "recommended_next_review_step": "Compare the cited source manually before use.",
    }


def _valid_receipt_kwargs() -> dict[str, object]:
    return {
        "receipt_id": "smoke_receipt_001",
        "reviewer_id": "smoke_reviewer_001",
        "dry_run_scope": "candidate_review_chain_smoke",
        "readiness_checks": {k: True for k in REQUIRED_READINESS_CHECKS},
    }


def _valid_review_kwargs() -> dict[str, object]:
    return {
        "review_id": "smoke_review_001",
        "operator_id": "smoke_operator_001",
        "selected_research_family": "candidate_review_manual_research",
        "selected_operator_runbook_ref": (
            "docs/hermes_research_prompt_pack_and_operator_runbooks.md"
        ),
        "source_review_checks": {k: True for k in REQUIRED_SOURCE_REVIEW_CHECKS},
    }


def _valid_kwargs() -> dict[str, object]:
    return {**_valid_packet_kwargs(), **_valid_receipt_kwargs(), **_valid_review_kwargs()}


def _smoke(**overrides: object) -> HermesChainSmokeResult:
    kwargs = _valid_kwargs()
    kwargs.update(overrides)
    return run_candidate_review_manual_chain_smoke(**kwargs)  # type: ignore[arg-type]


def _recursive_strings(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        parts: list[str] = []
        for k, v in value.items():
            parts.extend(_recursive_strings(k))
            parts.extend(_recursive_strings(v))
        return tuple(parts)
    if isinstance(value, (list, tuple)):
        return tuple(s for item in value for s in _recursive_strings(item))
    return ()


# ── A. Positive path ─────────────────────────────────────────────────────────


def test_valid_chain_produces_valid_smoke_result() -> None:
    result = _smoke()
    assert result.is_valid is True


def test_valid_result_all_stage_flags_true() -> None:
    result = _smoke()
    assert result.packet_valid is True
    assert result.receipt_valid is True
    assert result.review_valid is True


def test_valid_result_types_are_populated() -> None:
    result = _smoke()
    assert result.packet_type is not None
    assert result.receipt_type is not None
    assert result.review_type is not None
    assert isinstance(result.packet_type, str)
    assert isinstance(result.receipt_type, str)
    assert isinstance(result.review_type, str)


def test_valid_result_no_errors_no_warnings() -> None:
    result = _smoke()
    assert result.errors == ()
    assert result.warnings == ()


def test_valid_result_type_values_are_expected_constants() -> None:
    result = _smoke()
    assert "CANDIDATE_REVIEW" in result.packet_type  # type: ignore[operator]
    assert "DRY_RUN_RECEIPT" in result.receipt_type  # type: ignore[operator]
    assert "OPERATOR_REVIEW" in result.review_type  # type: ignore[operator]


def test_valid_result_with_optional_fields() -> None:
    result = _smoke(
        key_findings=["The reviewed candidate passed local contract validation."],
        limitations=["Only the supplied local fixture was considered."],
        uncertainty_notes=["Coverage remains bounded."],
        assumptions=["The cited source is current."],
        falsification_checks=["Compare against the cited source directly."],
        data_quality_warnings=["coverage_is_limited"],
        known_missing_data=["later_observations_not_available"],
        report_reference="candidate_review_report_001",
        related_repo_truth_refs=["docs/project_status.md"],
    )
    assert result.is_valid is True


# ── B. Safety flags — always True regardless of outcome ──────────────────────


def test_valid_result_all_safety_flags_true() -> None:
    result = _smoke()
    assert result.advisory_only is True
    assert result.manual_review_required is True
    assert result.no_execution_authority is True
    assert result.no_runtime_authority is True
    assert result.no_credential_authority is True
    assert result.no_paper_or_live_authority is True
    assert result.no_prompt_execution is True
    assert result.no_file_or_network is True


def test_safety_flags_true_even_on_packet_stage_failure() -> None:
    result = _smoke(report_identity="order_123")  # "order" is forbidden
    assert result.is_valid is False
    assert result.advisory_only is True
    assert result.manual_review_required is True
    assert result.no_execution_authority is True
    assert result.no_runtime_authority is True
    assert result.no_credential_authority is True
    assert result.no_paper_or_live_authority is True
    assert result.no_prompt_execution is True
    assert result.no_file_or_network is True


def test_safety_flags_true_even_on_receipt_stage_failure() -> None:
    bad_checks = {k: False for k in REQUIRED_READINESS_CHECKS}
    result = _smoke(readiness_checks=bad_checks)
    assert result.is_valid is False
    assert result.advisory_only is True
    assert result.manual_review_required is True
    assert result.no_execution_authority is True


def test_safety_flags_true_even_on_review_stage_failure() -> None:
    bad_checks = {k: False for k in REQUIRED_SOURCE_REVIEW_CHECKS}
    result = _smoke(source_review_checks=bad_checks)
    assert result.is_valid is False
    assert result.advisory_only is True
    assert result.manual_review_required is True
    assert result.no_execution_authority is True


# ── C. Stage failure behavior ─────────────────────────────────────────────────


def test_unsafe_packet_input_fails_closed_at_packet_stage() -> None:
    result = _smoke(report_identity="order_123")
    assert result.is_valid is False
    assert result.packet_valid is False
    assert result.receipt_valid is False
    assert result.review_valid is False


def test_missing_required_packet_field_fails_at_packet_stage() -> None:
    result = _smoke(review_status="")
    assert result.is_valid is False
    assert result.packet_valid is False


def test_human_review_required_false_fails_at_packet_stage() -> None:
    result = _smoke(human_review_required=False)
    assert result.is_valid is False
    assert result.packet_valid is False
    assert result.receipt_valid is False
    assert result.review_valid is False


def test_packet_stage_failure_returns_none_types() -> None:
    result = _smoke(report_identity="credential_data")
    assert result.packet_type is None
    assert result.receipt_type is None
    assert result.review_type is None


def test_invalid_readiness_checks_fail_at_receipt_stage() -> None:
    # All False readiness checks → WP101 rejects
    bad_checks = {k: False for k in REQUIRED_READINESS_CHECKS}
    result = _smoke(readiness_checks=bad_checks)
    assert result.is_valid is False
    assert result.packet_valid is True
    assert result.receipt_valid is False
    assert result.review_valid is False


def test_incomplete_readiness_checks_fail_at_receipt_stage() -> None:
    # Missing some required keys
    partial_checks = {"packet_validated": True}
    result = _smoke(readiness_checks=partial_checks)
    assert result.is_valid is False
    assert result.packet_valid is True
    assert result.receipt_valid is False


def test_receipt_stage_failure_populates_packet_type_only() -> None:
    bad_checks = {k: False for k in REQUIRED_READINESS_CHECKS}
    result = _smoke(readiness_checks=bad_checks)
    assert result.packet_type is not None
    assert result.receipt_type is None
    assert result.review_type is None


def test_invalid_source_review_checks_fail_at_review_stage() -> None:
    bad_checks = {k: False for k in REQUIRED_SOURCE_REVIEW_CHECKS}
    result = _smoke(source_review_checks=bad_checks)
    assert result.is_valid is False
    assert result.packet_valid is True
    assert result.receipt_valid is True
    assert result.review_valid is False


def test_incomplete_source_review_checks_fail_at_review_stage() -> None:
    partial_checks = {"receipt_reviewed": True}
    result = _smoke(source_review_checks=partial_checks)
    assert result.is_valid is False
    assert result.packet_valid is True
    assert result.receipt_valid is True
    assert result.review_valid is False


def test_review_stage_failure_populates_packet_and_receipt_types() -> None:
    bad_checks = {k: False for k in REQUIRED_SOURCE_REVIEW_CHECKS}
    result = _smoke(source_review_checks=bad_checks)
    assert result.packet_type is not None
    assert result.receipt_type is not None
    assert result.review_type is None


def test_packet_stage_failure_has_packet_stage_prefixed_errors() -> None:
    result = _smoke(report_identity="order_123")
    assert result.errors
    assert all(e.startswith("packet_stage_") for e in result.errors)


def test_receipt_stage_failure_has_receipt_stage_prefixed_errors() -> None:
    bad_checks = {k: False for k in REQUIRED_READINESS_CHECKS}
    result = _smoke(readiness_checks=bad_checks)
    assert result.errors
    assert all(e.startswith("receipt_stage_") for e in result.errors)


def test_review_stage_failure_has_review_stage_prefixed_errors() -> None:
    bad_checks = {k: False for k in REQUIRED_SOURCE_REVIEW_CHECKS}
    result = _smoke(source_review_checks=bad_checks)
    assert result.errors
    assert all(e.startswith("review_stage_") for e in result.errors)


# ── D. No unsafe echo ─────────────────────────────────────────────────────────

_CREDENTIAL_VARIANTS = [
    "credential_data",
    "api_key_value",
    "private_key_xyz",
    "secret_value",
    "passphrase_abc",
]

_EXECUTION_VARIANTS = [
    "order_123",
    "buy_signal",
    "sell_signal",
    "trade_value",
]

_RUNTIME_VARIANTS = [
    "runtime_config",
    "scheduler_ref",
]

_RAW_KEY_VARIANTS = [
    "metadata",
    "raw metadata",
    "freeform",
    "completion",
]


@pytest.mark.parametrize("unsafe_identity", _CREDENTIAL_VARIANTS)
def test_credential_variants_not_echoed_in_errors(unsafe_identity: str) -> None:
    result = _smoke(report_identity=unsafe_identity)
    assert result.is_valid is False
    all_strings = _recursive_strings({"errors": result.errors, "warnings": result.warnings})
    lowered_identity = unsafe_identity.lower().replace("_", " ")
    for s in all_strings:
        assert lowered_identity not in s.lower()
        assert unsafe_identity.lower() not in s.lower()


@pytest.mark.parametrize("unsafe_identity", _EXECUTION_VARIANTS)
def test_execution_variants_not_echoed_in_errors(unsafe_identity: str) -> None:
    result = _smoke(report_identity=unsafe_identity)
    assert result.is_valid is False
    all_strings = _recursive_strings({"errors": result.errors, "warnings": result.warnings})
    unsafe_lower = unsafe_identity.lower().replace("_", " ")
    for s in all_strings:
        assert unsafe_lower not in s.lower()


@pytest.mark.parametrize("unsafe_identity", _RUNTIME_VARIANTS)
def test_runtime_variants_not_echoed_in_errors(unsafe_identity: str) -> None:
    result = _smoke(report_identity=unsafe_identity)
    assert result.is_valid is False
    all_strings = _recursive_strings({"errors": result.errors, "warnings": result.warnings})
    unsafe_lower = unsafe_identity.lower().replace("_", " ")
    for s in all_strings:
        assert unsafe_lower not in s.lower()


@pytest.mark.parametrize("raw_key", _RAW_KEY_VARIANTS)
def test_raw_mapping_keys_not_echoed_in_errors(raw_key: str) -> None:
    result = _smoke(report_identity=raw_key)
    assert result.is_valid is False
    all_strings = _recursive_strings({"errors": result.errors, "warnings": result.warnings})
    for s in all_strings:
        assert raw_key.lower() not in s.lower()


def test_result_errors_contain_only_neutral_codes() -> None:
    result = _smoke(report_identity="order_123")
    for e in result.errors:
        # Neutral codes: prefix_word_NNN or prefix_word_word_NNN
        assert e.startswith("packet_stage_") or e.startswith("receipt_stage_") or e.startswith("review_stage_")
        # No caller content in errors
        assert "order_123" not in e
        assert "order" not in e.split("_stage_")[1].split("_")[:-1]  # only in prefix


# ── E. Output inventory ───────────────────────────────────────────────────────


def test_result_has_exact_top_level_fields() -> None:
    expected = {
        "is_valid",
        "packet_valid",
        "receipt_valid",
        "review_valid",
        "packet_type",
        "receipt_type",
        "review_type",
        "errors",
        "warnings",
        "advisory_only",
        "manual_review_required",
        "no_execution_authority",
        "no_runtime_authority",
        "no_credential_authority",
        "no_paper_or_live_authority",
        "no_prompt_execution",
        "no_file_or_network",
    }
    actual = {f.name for f in fields(HermesChainSmokeResult)}
    assert actual == expected


def test_result_is_frozen_dataclass() -> None:
    result = _smoke()
    with pytest.raises((AttributeError, TypeError)):
        result.is_valid = False  # type: ignore[misc]


def test_valid_result_contains_no_trade_like_field_names() -> None:
    forbidden_field_substrings = (
        "buy", "sell", "order", "position", "live_approved",
        "paper_approved", "execution_result", "alpha",
    )
    field_names = {f.name for f in fields(HermesChainSmokeResult)}
    for name in field_names:
        for forbidden in forbidden_field_substrings:
            assert forbidden not in name, f"Field '{name}' contains forbidden substring '{forbidden}'"


def test_valid_result_no_pr_approval_semantics() -> None:
    result = _smoke()
    all_strings = _recursive_strings({
        "packet_type": result.packet_type,
        "receipt_type": result.receipt_type,
        "review_type": result.review_type,
    })
    forbidden = (
        "approve pr", "merge ready", "live approved", "paper approved",
        "strategy promoted", "live readiness", "paper readiness",
    )
    for s in all_strings:
        for phrase in forbidden:
            assert phrase not in s.lower()


# ── F. Import and boundary tests ──────────────────────────────────────────────


def test_smoke_module_imports_only_stdlib_and_approved_internal() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_external = {
        "os", "socket", "subprocess", "urllib", "requests", "httpx",
        "aiohttp", "pathlib", "flask", "django", "fastapi",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden_external, (
                        f"Forbidden import: {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                top = module.split(".")[0]
                assert top not in forbidden_external, (
                    f"Forbidden import from: {module}"
                )


def test_smoke_module_has_no_file_write_surface() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                pytest.fail("Found open() call — no file I/O allowed")
            if isinstance(node.func, ast.Attribute) and node.func.attr in (
                "write", "writelines", "read", "readline", "readlines",
            ):
                pytest.fail(f"Found .{node.func.attr}() call — no file I/O allowed")


def test_smoke_module_has_no_cli_surface() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "argparse" not in source
    assert "sys.argv" not in source
    assert "click" not in source
    assert "__main__" not in source


def test_smoke_module_has_no_daemon_or_while_loop() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            pytest.fail("Found while loop — no daemon/loop behavior allowed")


def test_smoke_module_has_no_network_or_subprocess_surface() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    forbidden_patterns = (
        "socket", "subprocess", "urllib", "requests", "httpx",
        "aiohttp", "http.client", "urllib.request",
    )
    for pattern in forbidden_patterns:
        assert pattern not in source, (
            f"Found network/subprocess pattern: {pattern}"
        )


def test_smoke_module_imports_only_approved_internal_modules() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    approved_internal_prefixes = (
        "src.data_layer.hermes_candidate_review_context_packet_integration",
        "src.data_layer.hermes_context_packet_dry_run_receipt",
        "src.data_layer.hermes_manual_research_dry_run_review",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("src."):
                assert any(module == prefix for prefix in approved_internal_prefixes), (
                    f"Unapproved internal import: {module}"
                )


def test_result_type_is_hermes_chain_smoke_result() -> None:
    result = _smoke()
    assert isinstance(result, HermesChainSmokeResult)


def test_failed_result_type_is_also_hermes_chain_smoke_result() -> None:
    result = _smoke(report_identity="order_invalid")
    assert isinstance(result, HermesChainSmokeResult)


# ── G. Status entry tests ─────────────────────────────────────────────────────


def test_wp104_status_entry_exists() -> None:
    assert STATUS_ENTRY.is_file(), f"Missing: {STATUS_ENTRY}"


def test_wp104_status_entry_has_no_stale_dynamic_wording() -> None:
    text = STATUS_ENTRY.read_text(encoding="utf-8")
    stale_phrases = (
        "WP104 on branch",
        "WP104 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
        "Guard input source: LOCAL_DRAFT_VERIFIED",
        "Head commit:",
    )
    for phrase in stale_phrases:
        assert phrase not in text, f"Status entry contains stale wording: {phrase!r}"


def test_wp104_status_entry_references_source_and_test_files() -> None:
    text = STATUS_ENTRY.read_text(encoding="utf-8")
    assert "hermes_candidate_review_manual_chain_smoke.py" in text
    assert "test_hermes_candidate_review_manual_chain_smoke.py" in text


def test_wp104_status_entry_is_ready_for_review() -> None:
    text = STATUS_ENTRY.read_text(encoding="utf-8")
    assert "Ready for review: YES" in text


def test_wp104_status_entry_has_stable_pr_wording() -> None:
    text = STATUS_ENTRY.read_text(encoding="utf-8")
    assert "see GitHub PR metadata and PR body" in text
    assert "stable and non-self-referential" in text
