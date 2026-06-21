"""Focused tests for the WP100 Hermes context-packet builder foundation."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, asdict, fields
from pathlib import Path

import pytest

from src.data_layer.hermes_context_packet_exporter import (
    FORBIDDEN_USE_NOTICE,
    HermesContextPacketBuildResult,
    build_hermes_context_packet,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "data_layer" / "hermes_context_packet_exporter.py"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP100.md"


def _valid_kwargs() -> dict[str, object]:
    return {
        "packet_id": "packet_001",
        "packet_type": "repo_truth_summary",
        "artifact_id": "artifact_001",
        "artifact_type": "local_summary",
        "source_refs": [
            "docs/hermes_input_output_contracts_and_validator_requirements.md"
        ],
        "provenance_status": "verified_local_source",
        "staleness_status": "current_at_manual_review",
        "data_quality_warnings": ["coverage_is_limited"],
        "known_missing_data": ["later_observations"],
        "summary": "Bounded local evidence summary for analyst review.",
        "context_sections": {
            "evidence": {
                "finding": "The reviewed artifact is internally consistent.",
                "sample_count": 3,
            },
            "limits": ["Only the supplied local summary was considered."],
        },
        "recommended_prompt_family": "repo review",
        "recommended_next_review_step": "Compare the cited source manually.",
        "deterministic_owner": "repository validator",
        "uncertainty_notes": ["Coverage remains bounded."],
        "assumptions": ["The cited source is current."],
        "falsification_checks": ["Compare against the cited source."],
        "operator_notes": ["Retain the reviewer receipt."],
        "validator_requirements_reference": (
            "docs/hermes_input_output_contracts_and_validator_requirements.md"
        ),
        "related_repo_truth_refs": ["docs/project_status.md"],
    }


def _build(**overrides: object) -> HermesContextPacketBuildResult:
    kwargs = _valid_kwargs()
    kwargs.update(overrides)
    return build_hermes_context_packet(**kwargs)  # type: ignore[arg-type]


def _recursive_strings(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        collected: list[str] = []
        for key, nested in value.items():
            collected.extend(_recursive_strings(key))
            collected.extend(_recursive_strings(nested))
        return tuple(collected)
    if isinstance(value, (list, tuple)):
        return tuple(text for item in value for text in _recursive_strings(item))
    if hasattr(value, "__dataclass_fields__"):
        return _recursive_strings(asdict(value))
    return ()


def test_valid_minimal_packet_passes_and_is_populated() -> None:
    result = _build()
    assert result.is_valid is True
    assert result.packet["packet_id"] == "packet_001"
    assert result.packet["context_sections"]
    assert result.errors == ()


def test_packet_is_always_advisory_and_human_review_required() -> None:
    packet = _build().packet
    assert packet["advisory_only"] is True
    assert packet["human_review_required"] is True
    assert packet["no_execution_authority"] is True
    assert packet["no_runtime_authority"] is True
    assert packet["no_credential_authority"] is True
    assert packet["no_paper_or_live_authority"] is True
    assert packet["forbidden_use_notice"] == FORBIDDEN_USE_NOTICE


def test_packet_contains_all_required_wp100_contract_fields() -> None:
    required_fields = {
        "packet_id",
        "packet_type",
        "artifact_id",
        "artifact_type",
        "source_refs",
        "provenance_status",
        "staleness_status",
        "data_quality_warnings",
        "known_missing_data",
        "advisory_only",
        "human_review_required",
        "forbidden_use_notice",
        "deterministic_owner",
        "no_execution_authority",
        "no_runtime_authority",
        "no_credential_authority",
        "no_paper_or_live_authority",
        "summary",
        "context_sections",
        "recommended_research_family",
        "recommended_next_review_step",
    }
    assert required_fields <= set(_build().packet)


def test_evidence_provenance_and_missing_data_are_preserved() -> None:
    packet = _build().packet
    assert packet["source_refs"] == (
        "docs/hermes_input_output_contracts_and_validator_requirements.md",
    )
    assert packet["provenance_status"] == "verified_local_source"
    assert packet["staleness_status"] == "current_at_manual_review"
    assert packet["data_quality_warnings"] == ("coverage_is_limited",)
    assert packet["known_missing_data"] == ("later_observations",)


def test_safe_routing_field_avoids_raw_prompt_field() -> None:
    packet = _build().packet
    assert packet["recommended_research_family"] == "repo review"
    assert "recommended_prompt_family" not in packet


def test_context_mapping_is_normalized_deterministically() -> None:
    first = _build(context_sections={"z_section": "Later", "a_section": "Earlier"})
    second = _build(context_sections={"a_section": "Earlier", "z_section": "Later"})
    assert list(first.packet["context_sections"]) == ["a_section", "z_section"]
    assert first.packet == second.packet


def test_result_is_frozen_dataclass() -> None:
    result = _build()
    with pytest.raises(FrozenInstanceError):
        result.is_valid = False  # type: ignore[misc]


def test_result_field_coverage_gate() -> None:
    result = _build()
    serialized = asdict(result)
    assert {field.name for field in fields(HermesContextPacketBuildResult)} <= set(
        serialized
    )


@pytest.mark.parametrize(
    "field",
    ("packet_id", "packet_type", "artifact_id", "artifact_type"),
)
def test_missing_required_identity_field_fails(field: str) -> None:
    result = _build(**{field: ""})
    assert result.is_valid is False
    assert result.packet == {}


def test_none_required_identity_field_fails_closed() -> None:
    result = _build(packet_id=None)
    assert result.is_valid is False
    assert result.packet == {}


@pytest.mark.parametrize("field", ("provenance_status", "staleness_status"))
def test_missing_provenance_or_staleness_fails(field: str) -> None:
    result = _build(**{field: " "})
    assert result.is_valid is False
    assert result.packet == {}


def test_empty_source_refs_fails() -> None:
    result = _build(source_refs=[])
    assert result.is_valid is False
    assert result.packet == {}


def test_missing_source_refs_fails() -> None:
    result = _build(source_refs=None)
    assert result.is_valid is False
    assert result.packet == {}


@pytest.mark.parametrize(
    ("field", "value"),
    (("summary", ""), ("context_sections", {})),
)
def test_missing_summary_or_context_sections_fails(field: str, value: object) -> None:
    result = _build(**{field: value})
    assert result.is_valid is False
    assert result.packet == {}


def test_required_warning_and_missing_data_sequences_must_have_valid_types() -> None:
    assert _build(data_quality_warnings="none").is_valid is False
    assert _build(known_missing_data=[1]).is_valid is False


def test_empty_required_warning_and_missing_data_sequences_are_explicitly_allowed() -> None:
    result = _build(data_quality_warnings=[], known_missing_data=[])
    assert result.is_valid is True
    assert result.packet["data_quality_warnings"] == ()
    assert result.packet["known_missing_data"] == ()


def test_optional_notes_may_be_omitted_with_neutral_warnings() -> None:
    result = _build(
        uncertainty_notes=None,
        assumptions=None,
        falsification_checks=None,
        operator_notes=None,
        validator_requirements_reference=None,
        related_repo_truth_refs=None,
    )
    assert result.is_valid is True
    assert len(result.warnings) == 6
    assert all(
        warning.startswith("optional_field_omitted_") for warning in result.warnings
    )


@pytest.mark.parametrize(
    "unsafe_phrase",
    (
        "buy",
        "sell",
        "trade",
        "execute",
        "execution",
        "place order",
        "cancel order",
        "entry",
        "exit",
        "stop loss",
        "take profit",
        "position size",
        "position_size",
        "expected return",
        "expected_return",
        "edge",
        "alpha",
        "fair value",
        "fair_value",
        "signal",
        "trade signal",
    ),
)
def test_forbidden_action_variant_in_top_level_text_fails(unsafe_phrase: str) -> None:
    result = _build(summary=f"Unsafe fixture {unsafe_phrase} marker")
    assert result.is_valid is False
    assert result.packet == {}


def test_forbidden_phrase_in_nested_dict_value_fails() -> None:
    result = _build(context_sections={"evidence": {"finding": "buy"}})
    assert result.is_valid is False
    assert result.packet == {}


def test_forbidden_phrase_in_nested_key_fails() -> None:
    result = _build(context_sections={"evidence": {"position_size": 1}})
    assert result.is_valid is False
    assert result.packet == {}


def test_forbidden_phrase_in_list_value_fails() -> None:
    result = _build(context_sections={"evidence": ["alpha"]})
    assert result.is_valid is False
    assert result.packet == {}


@pytest.mark.parametrize(
    "unsafe_phrase",
    (
        "api_key",
        "api key",
        "secret",
        "token",
        "passphrase",
        "mnemonic",
        "private_key",
        "private key",
        "wallet private",
        "credential",
    ),
)
def test_credential_private_variant_fails_without_echo(unsafe_phrase: str) -> None:
    raw = f"DO_NOT_ECHO_{unsafe_phrase}_VALUE"
    result = _build(context_sections={"evidence": raw})
    assert result.is_valid is False
    assert result.packet == {}
    assert raw not in " ".join(_recursive_strings(result))


@pytest.mark.parametrize(
    "unsafe_key",
    (
        "metadata",
        "raw_metadata",
        "raw_response",
        "prompt",
        "raw_prompt",
        "freeform",
        "free_form",
        "raw_payload",
    ),
)
def test_raw_mapping_key_fails_at_context_top_level(unsafe_key: str) -> None:
    result = _build(context_sections={unsafe_key: {"value": "opaque"}})
    assert result.is_valid is False
    assert result.packet == {}


def test_raw_mapping_key_fails_nested_in_dict_and_list() -> None:
    result = _build(
        context_sections={"evidence": [{"details": {"raw_response": "opaque"}}]}
    )
    assert result.is_valid is False
    assert result.packet == {}


@pytest.mark.parametrize(
    "unsafe_key",
    ("account_data", "order_state", "live_position", "wallet_balance"),
)
def test_account_order_or_live_position_key_fails(unsafe_key: str) -> None:
    result = _build(context_sections={unsafe_key: "opaque"})
    assert result.is_valid is False
    assert result.packet == {}


@pytest.mark.parametrize(
    "unsafe_phrase",
    (
        "scheduler",
        "daemon",
        "bot loop",
        "bot_loop",
        "runtime",
        "prompt runner",
        "run prompt",
        "model call",
        "provider config",
    ),
)
def test_runtime_control_variant_fails(unsafe_phrase: str) -> None:
    assert _build(summary=f"Unsafe {unsafe_phrase} fixture").is_valid is False


@pytest.mark.parametrize(
    "unsafe_phrase",
    (
        "merge-ready",
        "approve PR",
        "risk override",
        "override risk",
        "bypass risk",
        "kill switch override",
    ),
)
def test_approval_or_override_variant_fails(unsafe_phrase: str) -> None:
    assert _build(summary=f"Unsafe {unsafe_phrase} fixture").is_valid is False


def test_case_insensitive_forbidden_variant_fails() -> None:
    assert _build(summary="Unsafe BUY fixture").is_valid is False


def test_safe_allowed_wording_is_not_overblocked() -> None:
    result = _build(summary="Advisory research summary for manual analyst review.")
    assert result.is_valid is True


def test_invalid_result_full_surface_does_not_echo_unsafe_input() -> None:
    raw = "SECRET_DO_NOT_ECHO_7429"
    result = _build(context_sections={"evidence": {"value": raw}})
    assert result.is_valid is False
    assert result.packet == {}
    full_surface = " ".join(_recursive_strings(result))
    assert raw not in full_surface
    assert "SECRET" not in full_surface
    assert all(error.startswith("unsafe_") for error in result.errors)


def test_raw_mapping_key_error_does_not_echo_key() -> None:
    raw_key = "raw_response"
    result = _build(context_sections={raw_key: "opaque"})
    assert result.is_valid is False
    assert raw_key not in " ".join(_recursive_strings(result))


def test_wrong_nested_key_type_fails_closed() -> None:
    result = _build(context_sections={1: "safe"})
    assert result.is_valid is False
    assert result.packet == {}


def test_empty_nested_key_fails_closed() -> None:
    result = _build(context_sections={" ": "safe"})
    assert result.is_valid is False
    assert result.packet == {}


def test_conflicting_normalized_nested_keys_fail_closed() -> None:
    result = _build(context_sections={"evidence": "first", " evidence ": "second"})
    assert result.is_valid is False
    assert result.packet == {}


def test_unsupported_nested_value_fails_closed() -> None:
    result = _build(context_sections={"evidence": object()})
    assert result.is_valid is False
    assert result.packet == {}


def test_nonfinite_number_fails_closed() -> None:
    result = _build(context_sections={"metric": float("nan")})
    assert result.is_valid is False
    assert result.packet == {}


def test_recursive_container_fails_closed() -> None:
    recursive: list[object] = []
    recursive.append(recursive)
    result = _build(context_sections={"evidence": recursive})
    assert result.is_valid is False
    assert result.packet == {}


def test_source_imports_are_stdlib_only() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert imported_roots <= {
        "__future__",
        "collections",
        "dataclasses",
        "math",
        "typing",
    }


def test_source_has_no_network_file_runtime_or_subprocess_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_roots = {
        "aiohttp",
        "httpx",
        "os",
        "pathlib",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert imported_roots.isdisjoint(forbidden_roots)


def test_source_has_no_file_write_or_process_call_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attribute_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert call_names.isdisjoint({"open", "exec", "eval", "compile"})
    assert attribute_calls.isdisjoint(
        {"write", "write_text", "write_bytes", "run", "Popen", "system"}
    )


def test_source_has_no_cli_or_long_running_loop() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "if __name__" not in source
    assert not any(isinstance(node, ast.While) for node in ast.walk(tree))


def test_wp100_status_entry_exists_and_uses_stable_wording() -> None:
    assert STATUS_ENTRY.is_file()
    text = STATUS_ENTRY.read_text(encoding="utf-8")
    assert "PR: see GitHub PR metadata and PR body." in text
    assert "PR: TBD" not in text
    assert "TBD after merge" not in text
    assert "WP100 on branch" not in text
