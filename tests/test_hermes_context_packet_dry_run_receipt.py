"""Focused tests for the WP101 Hermes context-packet dry-run receipt."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, asdict, fields
from pathlib import Path

import pytest

from src.data_layer.hermes_context_packet_dry_run_receipt import (
    REQUIRED_PACKET_FIELDS,
    REQUIRED_PACKET_SAFETY_FLAGS,
    REQUIRED_READINESS_CHECKS,
    HermesContextPacketDryRunReceiptResult,
    build_hermes_context_packet_dry_run_receipt,
)
from src.data_layer.hermes_context_packet_exporter import build_hermes_context_packet


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "data_layer" / "hermes_context_packet_dry_run_receipt.py"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP101.md"


def _valid_packet() -> dict[str, object]:
    result = build_hermes_context_packet(
        packet_id="packet_001",
        packet_type="repo_truth_summary",
        artifact_id="artifact_001",
        artifact_type="local_summary",
        source_refs=[
            "docs/hermes_input_output_contracts_and_validator_requirements.md",
            "docs/project_status.md",
        ],
        provenance_status="verified_local_source",
        staleness_status="current_at_manual_review",
        data_quality_warnings=["coverage_is_limited"],
        known_missing_data=["later_observations"],
        summary="Bounded local evidence summary for analyst review.",
        context_sections={
            "evidence": {
                "finding": "The reviewed artifact is internally consistent.",
                "sample_count": 3,
            },
            "limits": ["Only the supplied local summary was considered."],
        },
        recommended_prompt_family="repo review",
        recommended_next_review_step="Compare the cited source manually.",
        deterministic_owner="repository validator",
        uncertainty_notes=["Coverage remains bounded."],
        assumptions=["The cited source is current."],
        falsification_checks=["Compare against the cited source."],
        operator_notes=["Retain the reviewer receipt."],
        validator_requirements_reference=(
            "docs/hermes_input_output_contracts_and_validator_requirements.md"
        ),
        related_repo_truth_refs=["docs/project_status.md"],
    )
    assert result.is_valid is True
    return dict(result.packet)


def _valid_readiness_checks() -> dict[str, bool]:
    return {key: True for key in REQUIRED_READINESS_CHECKS}


def _valid_kwargs() -> dict[str, object]:
    return {
        "receipt_id": "receipt_001",
        "packet": _valid_packet(),
        "reviewer_id": "reviewer_001",
        "dry_run_scope": "manual packet readiness review",
        "checked_source_refs": [
            "docs/hermes_input_output_contracts_and_validator_requirements.md",
            "docs/project_status.md",
        ],
        "readiness_checks": _valid_readiness_checks(),
        "stop_reasons": None,
        "operator_notes": ["Reviewed local source references."],
        "related_repo_truth_refs": ["docs/project_status.md"],
    }


def _build(**overrides: object) -> HermesContextPacketDryRunReceiptResult:
    kwargs = _valid_kwargs()
    kwargs.update(overrides)
    return build_hermes_context_packet_dry_run_receipt(**kwargs)  # type: ignore[arg-type]


def _recursive_items(value: object) -> tuple[object, ...]:
    if isinstance(value, dict):
        collected: list[object] = []
        for key, nested in value.items():
            collected.extend(_recursive_items(key))
            collected.extend(_recursive_items(nested))
        return tuple(collected)
    if isinstance(value, (list, tuple)):
        return tuple(item for nested in value for item in _recursive_items(nested))
    if hasattr(value, "__dataclass_fields__"):
        return _recursive_items(asdict(value))
    return (value,)


def _recursive_strings(value: object) -> tuple[str, ...]:
    return tuple(item for item in _recursive_items(value) if isinstance(item, str))


def test_valid_context_packet_builds_ready_receipt() -> None:
    result = _build()
    assert result.is_valid is True
    assert result.errors == ()
    assert result.receipt["receipt_id"] == "receipt_001"
    assert result.receipt["packet_id"] == "packet_001"
    assert result.receipt["receipt_status"] == "READY_FOR_MANUAL_REVIEW"


def test_receipt_contains_required_safety_flags() -> None:
    receipt = _build().receipt
    assert receipt["dry_run_only"] is True
    assert receipt["manual_review_required"] is True
    assert receipt["prompt_execution_performed"] is False
    assert receipt["hermes_runtime_used"] is False
    assert receipt["model_or_provider_called"] is False
    assert receipt["file_written"] is False
    assert receipt["network_used"] is False
    assert receipt["paper_or_live_authority"] is False
    assert receipt["execution_or_risk_authority"] is False


def test_receipt_public_surface_inventory() -> None:
    receipt = _build().receipt
    expected = {
        "receipt_id",
        "receipt_type",
        "receipt_status",
        "packet_id",
        "packet_type",
        "artifact_id",
        "artifact_type",
        "source_refs",
        "checked_source_refs",
        "related_repo_truth_refs",
        "reviewer_id",
        "dry_run_scope",
        "provenance_status",
        "staleness_status",
        "recommended_research_family",
        "recommended_next_review_step",
        "readiness_checks",
        "operator_notes",
        "dry_run_only",
        "manual_review_required",
        "prompt_execution_performed",
        "hermes_runtime_used",
        "model_or_provider_called",
        "file_written",
        "network_used",
        "paper_or_live_authority",
        "execution_or_risk_authority",
    }
    assert expected == set(receipt)


def test_result_is_frozen_dataclass() -> None:
    result = _build()
    with pytest.raises(FrozenInstanceError):
        result.is_valid = False  # type: ignore[misc]


def test_result_field_coverage_gate() -> None:
    result = _build()
    serialized = asdict(result)
    assert {
        field.name for field in fields(HermesContextPacketDryRunReceiptResult)
    } <= set(serialized)


def test_required_packet_field_inventory_matches_wp101_contract() -> None:
    assert {
        "packet_id",
        "packet_type",
        "artifact_id",
        "artifact_type",
        "source_refs",
        "provenance_status",
        "staleness_status",
        "summary",
        "context_sections",
        "recommended_research_family",
        "recommended_next_review_step",
    } == set(REQUIRED_PACKET_FIELDS)


@pytest.mark.parametrize("flag", REQUIRED_PACKET_SAFETY_FLAGS)
def test_packet_missing_safety_flag_fails_closed(flag: str) -> None:
    packet = _valid_packet()
    del packet[flag]
    result = _build(packet=packet)
    assert result.is_valid is False
    assert result.receipt == {}
    assert all(flag not in error for error in result.errors)


@pytest.mark.parametrize("flag", REQUIRED_PACKET_SAFETY_FLAGS)
def test_packet_false_safety_flag_fails_closed(flag: str) -> None:
    packet = _valid_packet()
    packet[flag] = False
    result = _build(packet=packet)
    assert result.is_valid is False
    assert result.receipt == {}


@pytest.mark.parametrize("field", REQUIRED_PACKET_FIELDS)
def test_packet_missing_required_field_fails_closed(field: str) -> None:
    packet = _valid_packet()
    del packet[field]
    result = _build(packet=packet)
    assert result.is_valid is False
    assert result.receipt == {}


def test_checked_source_refs_must_be_non_empty() -> None:
    result = _build(checked_source_refs=[])
    assert result.is_valid is False
    assert result.receipt == {}


def test_checked_source_refs_must_reference_packet_or_repo_truth_docs() -> None:
    result = _build(checked_source_refs=["docs/not_registered_for_receipt.md"])
    assert result.is_valid is False
    assert result.receipt == {}


@pytest.mark.parametrize("check_name", REQUIRED_READINESS_CHECKS)
def test_missing_readiness_check_fails_closed(check_name: str) -> None:
    checks = _valid_readiness_checks()
    del checks[check_name]
    result = _build(readiness_checks=checks)
    assert result.is_valid is False
    assert result.receipt == {}


@pytest.mark.parametrize("check_name", REQUIRED_READINESS_CHECKS)
def test_false_readiness_check_fails_closed(check_name: str) -> None:
    checks = _valid_readiness_checks()
    checks[check_name] = False
    result = _build(readiness_checks=checks)
    assert result.is_valid is False
    assert result.receipt == {}


def test_extra_readiness_check_fails_closed() -> None:
    checks = _valid_readiness_checks()
    checks["extra_check"] = True
    result = _build(readiness_checks=checks)
    assert result.is_valid is False
    assert result.receipt == {}


def test_stop_reasons_prevent_ready_receipt() -> None:
    result = _build(stop_reasons=["Needs another manual source comparison."])
    assert result.is_valid is False
    assert result.receipt == {}
    assert any(error.startswith("stop_reasons_present_") for error in result.errors)


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
        "expected return",
        "edge",
        "alpha",
        "fair value",
        "signal",
        "trade signal",
        "opportunity",
        "scheduler",
        "daemon",
        "bot loop",
        "runtime",
        "prompt runner",
        "run prompt",
        "model call",
        "provider config",
        "network call",
        "file write",
        "merge-ready",
        "approve PR",
        "risk override",
        "override risk",
        "bypass risk",
        "kill switch override",
        "live approved",
        "paper approved",
        "account_data",
        "order_state",
        "live_position",
        "wallet_balance",
        "portfolio_position",
    ),
)
def test_forbidden_variant_in_packet_fails_closed_without_echo(
    unsafe_phrase: str,
) -> None:
    packet = _valid_packet()
    packet["context_sections"] = {"evidence": f"DO_NOT_ECHO {unsafe_phrase}"}
    result = _build(packet=packet)
    assert result.is_valid is False
    assert result.receipt == {}
    full_surface = " ".join(_recursive_strings(result)).casefold()
    assert unsafe_phrase.casefold() not in full_surface
    assert "do_not_echo" not in full_surface


@pytest.mark.parametrize(
    "unsafe_phrase",
    (
        "secret",
        "place order",
        "prompt runner",
        "risk override",
    ),
)
def test_forbidden_variant_in_receipt_inputs_fails_without_echo(
    unsafe_phrase: str,
) -> None:
    result = _build(operator_notes=[f"DO_NOT_ECHO {unsafe_phrase}"])
    assert result.is_valid is False
    assert result.receipt == {}
    full_surface = " ".join(_recursive_strings(result)).casefold()
    assert unsafe_phrase.casefold() not in full_surface
    assert "do_not_echo" not in full_surface


@pytest.mark.parametrize(
    "raw_key",
    (
        "metadata",
        "raw_metadata",
        "raw_response",
        "prompt",
        "raw_prompt",
        "freeform",
        "free_form",
        "raw_payload",
        "model_response",
    ),
)
def test_raw_mapping_keys_fail_closed(raw_key: str) -> None:
    packet = _valid_packet()
    packet["context_sections"] = {"evidence": {raw_key: "opaque"}}
    result = _build(packet=packet)
    assert result.is_valid is False
    assert result.receipt == {}
    assert raw_key not in " ".join(_recursive_strings(result))


def test_raw_mapping_key_in_readiness_checks_fails_closed() -> None:
    checks = _valid_readiness_checks()
    checks["metadata"] = True
    result = _build(readiness_checks=checks)
    assert result.is_valid is False
    assert result.receipt == {}


def test_recursive_unsafe_key_inside_packet_fails_closed() -> None:
    packet = _valid_packet()
    packet["context_sections"] = {"evidence": [{"details": {"raw_payload": "x"}}]}
    result = _build(packet=packet)
    assert result.is_valid is False
    assert result.receipt == {}


def test_invalid_result_surfaces_are_empty_and_neutral() -> None:
    result = _build(receipt_id="SECRET_DO_NOT_ECHO")
    assert result.is_valid is False
    assert result.receipt == {}
    strings = _recursive_strings(result)
    assert "SECRET_DO_NOT_ECHO" not in strings
    assert all(
        text.startswith(("unsafe_", "missing_", "invalid_", "unverified_", "stop_"))
        for text in result.errors
    )


def test_valid_receipt_does_not_contain_forbidden_output_claims() -> None:
    result = _build()
    strings = tuple(text.casefold() for text in _recursive_strings(result))
    forbidden = (
        "prompt output",
        "model output",
        "raw hermes response",
        "approve pr",
        "merge ready",
        "risk override",
        "trade signal",
        "position size",
        "expected return",
        "entry",
        "exit",
        "buy",
        "sell",
        "place order",
        "cancel order",
    )
    for text in strings:
        for phrase in forbidden:
            assert phrase not in text


def test_output_surface_scan_covers_dataclass_and_nested_receipt() -> None:
    result = _build()
    items = _recursive_items(result)
    assert "receipt_id" in items
    assert "readiness_checks" in items
    assert "packet_001" in items
    assert True in items
    assert False in items


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
    assert call_names.isdisjoint({"open", "exec", "eval", "compile", "input"})
    assert attribute_calls.isdisjoint(
        {"write", "write_text", "write_bytes", "run", "Popen", "system"}
    )


def test_source_has_no_cli_or_long_running_loop() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "if __name__" not in source
    assert not any(isinstance(node, ast.While) for node in ast.walk(tree))


def test_wp101_status_entry_exists_and_uses_stable_wording() -> None:
    assert STATUS_ENTRY.is_file()
    text = STATUS_ENTRY.read_text(encoding="utf-8")
    assert "PR: see GitHub PR metadata and PR body." in text
    assert "PR: TBD" not in text
    assert "TBD after merge" not in text
    assert "WP101 on branch" not in text
