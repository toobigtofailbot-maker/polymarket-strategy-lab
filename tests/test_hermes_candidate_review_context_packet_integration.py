"""Focused tests for the WP103 Hermes candidate-review context packet integration."""

from __future__ import annotations

import ast
from dataclasses import asdict, fields
from pathlib import Path

import pytest

from src.data_layer.hermes_candidate_review_context_packet_integration import (
    build_candidate_review_hermes_context_packet,
)
from src.data_layer.hermes_context_packet_exporter import (
    HermesContextPacketBuildResult,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT / "src" / "data_layer" / "hermes_candidate_review_context_packet_integration.py"
)
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP103.md"


# ── Helper builders ──────────────────────────────────────────────────────────


def _valid_kwargs() -> dict[str, object]:
    return {
        "packet_id": "candidate_packet_001",
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
        "data_quality_warnings": ["coverage_is_limited"],
        "known_missing_data": ["later_observations_not_available"],
        "key_findings": ["The reviewed candidate passed local contract validation."],
        "limitations": ["Only the supplied local fixture was considered."],
        "report_reference": "candidate_review_report_001",
        "uncertainty_notes": ["Coverage remains bounded."],
        "assumptions": ["The cited source is current."],
        "falsification_checks": ["Compare against the cited source directly."],
        "related_repo_truth_refs": ["docs/project_status.md"],
    }


def _build(**overrides: object) -> HermesContextPacketBuildResult:
    kwargs = _valid_kwargs()
    kwargs.update(overrides)
    return build_candidate_review_hermes_context_packet(**kwargs)  # type: ignore[arg-type]


def _recursive_items(value: object) -> tuple[object, ...]:
    if isinstance(value, dict):
        collected: list[object] = []
        for key, nested in value.items():
            collected.extend(_recursive_items(key))
            collected.extend(_recursive_items(nested))
        return tuple(collected)
    if isinstance(value, (list, tuple)):
        return tuple(item for nested in value for item in _recursive_items(nested))
    return (value,)


def _recursive_strings(value: object) -> tuple[str, ...]:
    return tuple(item for item in _recursive_items(value) if isinstance(item, str))


# ── Test 1: Valid in-memory candidate-review report → valid context packet ───


def test_valid_candidate_review_report_produces_valid_context_packet() -> None:
    result = _build()
    assert result.is_valid is True
    assert result.errors == ()
    assert result.packet
    assert result.packet["packet_id"] == "candidate_packet_001"
    assert result.packet["packet_type"] == "CANDIDATE_REVIEW_CONTEXT_PACKET_V1"
    assert result.packet["artifact_type"] == "candidate_review_advisory_report"


def test_valid_result_uses_wp100_packet_builder() -> None:
    result = _build()
    assert result.is_valid is True
    assert isinstance(result, HermesContextPacketBuildResult)
    assert result.packet["recommended_research_family"] == "candidate_review_manual_research"
    assert result.packet["deterministic_owner"] == "candidate_review_context_packet_adapter"


# ── Test 2: Missing candidate/report identity fails closed ───────────────────


@pytest.mark.parametrize("empty_val", ("", "   "))
def test_empty_report_identity_fails_closed(empty_val: str) -> None:
    result = _build(report_identity=empty_val)
    assert result.is_valid is False
    assert result.packet == {}
    assert result.errors


def test_none_report_identity_fails_closed() -> None:
    result = _build(report_identity=None)  # type: ignore[arg-type]
    assert result.is_valid is False
    assert result.packet == {}
    assert result.errors


# ── Test 3: Missing source refs fails closed ─────────────────────────────────


def test_empty_source_refs_fails_closed() -> None:
    result = _build(source_refs=[])
    assert result.is_valid is False
    assert result.packet == {}
    assert result.errors


def test_none_source_refs_fails_closed() -> None:
    result = _build(source_refs=None)  # type: ignore[arg-type]
    assert result.is_valid is False
    assert result.packet == {}
    assert result.errors


def test_source_refs_with_empty_string_item_fails_closed() -> None:
    result = _build(source_refs=["docs/project_status.md", ""])
    assert result.is_valid is False
    assert result.packet == {}
    assert result.errors


# ── Test 4: human_review_required != True fails closed ──────────────────────


@pytest.mark.parametrize("bad_val", (False, None, 0, 1, "True", "true"))
def test_human_review_required_not_true_fails_closed(bad_val: object) -> None:
    result = _build(human_review_required=bad_val)
    assert result.is_valid is False
    assert result.packet == {}
    assert result.errors


# ── Test 5: Missing other required fields fails closed ───────────────────────


@pytest.mark.parametrize(
    "field",
    (
        "advisory_notice",
        "review_status",
        "provenance_status",
        "staleness_status",
        "recommended_next_review_step",
        "packet_id",
    ),
)
def test_missing_required_text_field_fails_closed(field: str) -> None:
    result = _build(**{field: ""})
    assert result.is_valid is False
    assert result.packet == {}
    assert result.errors


# ── Test 6: Credential/account variants fail without echo ───────────────────


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
        "account_data",
        "wallet_balance",
    ),
)
def test_credential_variant_in_report_identity_fails_without_echo(
    unsafe_phrase: str,
) -> None:
    result = _build(report_identity=f"DO_NOT_ECHO {unsafe_phrase}")
    assert result.is_valid is False
    assert result.packet == {}
    full_surface = " ".join(_recursive_strings(result)).casefold()
    assert unsafe_phrase.casefold() not in full_surface
    assert "do_not_echo" not in full_surface


@pytest.mark.parametrize(
    "unsafe_phrase",
    (
        "secret",
        "credential",
        "wallet private",
        "passphrase",
    ),
)
def test_credential_variant_in_key_findings_fails_without_echo(
    unsafe_phrase: str,
) -> None:
    result = _build(key_findings=[f"DO_NOT_ECHO {unsafe_phrase}"])
    assert result.is_valid is False
    assert result.packet == {}
    full_surface = " ".join(_recursive_strings(result)).casefold()
    assert unsafe_phrase.casefold() not in full_surface
    assert "do_not_echo" not in full_surface


# ── Test 7: Order/execution/trade variants fail without echo ─────────────────


@pytest.mark.parametrize(
    "unsafe_phrase",
    (
        "buy",
        "sell",
        "trade",
        "execute",
        "execution",
        "order",
        "place order",
        "cancel order",
        "position",
        "position size",
        "entry",
        "exit",
        "stop loss",
        "take profit",
        "expected return",
        "fair value",
        "edge",
        "alpha",
        "signal",
        "trade signal",
        "opportunity",
        "live approved",
        "paper approved",
    ),
)
def test_trade_execution_variant_in_review_status_fails_without_echo(
    unsafe_phrase: str,
) -> None:
    result = _build(review_status=f"DO_NOT_ECHO {unsafe_phrase}")
    assert result.is_valid is False
    assert result.packet == {}
    full_surface = " ".join(_recursive_strings(result)).casefold()
    assert unsafe_phrase.casefold() not in full_surface
    assert "do_not_echo" not in full_surface


@pytest.mark.parametrize(
    "unsafe_phrase",
    (
        "buy",
        "sell",
        "alpha",
        "edge",
        "expected return",
        "position size",
        "trade signal",
    ),
)
def test_trade_execution_variant_in_limitations_fails_without_echo(
    unsafe_phrase: str,
) -> None:
    result = _build(limitations=[f"DO_NOT_ECHO {unsafe_phrase}"])
    assert result.is_valid is False
    assert result.packet == {}
    full_surface = " ".join(_recursive_strings(result)).casefold()
    assert unsafe_phrase.casefold() not in full_surface
    assert "do_not_echo" not in full_surface


# ── Test 8: Runtime/prompt/model variants fail without echo ──────────────────


@pytest.mark.parametrize(
    "unsafe_phrase",
    (
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
    ),
)
def test_runtime_variant_in_advisory_notice_fails_without_echo(
    unsafe_phrase: str,
) -> None:
    result = _build(advisory_notice=f"DO_NOT_ECHO {unsafe_phrase}")
    assert result.is_valid is False
    assert result.packet == {}
    full_surface = " ".join(_recursive_strings(result)).casefold()
    assert unsafe_phrase.casefold() not in full_surface
    assert "do_not_echo" not in full_surface


@pytest.mark.parametrize(
    "unsafe_phrase",
    (
        "scheduler",
        "runtime",
        "bot loop",
        "prompt runner",
    ),
)
def test_runtime_variant_in_uncertainty_notes_fails_without_echo(
    unsafe_phrase: str,
) -> None:
    result = _build(uncertainty_notes=[f"DO_NOT_ECHO {unsafe_phrase}"])
    assert result.is_valid is False
    assert result.packet == {}
    full_surface = " ".join(_recursive_strings(result)).casefold()
    assert unsafe_phrase.casefold() not in full_surface
    assert "do_not_echo" not in full_surface


# ── Test 9: Raw/free-form mapping key values fail closed ─────────────────────


@pytest.mark.parametrize(
    "raw_key_value",
    (
        "metadata",
        "raw_metadata",
        "source_metadata",
        "raw_response",
        "model_response",
        "raw_prompt",
        "prompt",
        "freeform",
        "free_form",
        "raw_payload",
        "completion",
    ),
)
def test_raw_mapping_key_as_report_identity_fails_closed(raw_key_value: str) -> None:
    result = _build(report_identity=raw_key_value)
    assert result.is_valid is False
    assert result.packet == {}
    assert raw_key_value.replace("_", " ") not in " ".join(_recursive_strings(result)).casefold()


@pytest.mark.parametrize(
    "raw_key_value",
    (
        "metadata",
        "raw_payload",
        "prompt",
        "freeform",
        "raw_response",
    ),
)
def test_raw_mapping_key_in_key_findings_fails_closed(raw_key_value: str) -> None:
    result = _build(key_findings=[raw_key_value])
    assert result.is_valid is False
    assert result.packet == {}


def test_raw_mapping_key_in_source_refs_fails_closed() -> None:
    result = _build(source_refs=["metadata"])
    assert result.is_valid is False
    assert result.packet == {}


def test_raw_mapping_key_in_limitations_fails_closed() -> None:
    result = _build(limitations=["prompt"])
    assert result.is_valid is False
    assert result.packet == {}


def test_raw_mapping_key_in_rejection_reasons_fails_closed() -> None:
    result = _build(rejection_reasons=["raw_payload"])
    assert result.is_valid is False
    assert result.packet == {}


# ── Test 10: Invalid output is empty and neutral ─────────────────────────────


def test_invalid_result_packet_is_empty() -> None:
    result = _build(report_identity="SECRET_DO_NOT_ECHO api_key")
    assert result.is_valid is False
    assert result.packet == {}
    strings = _recursive_strings(result)
    assert "SECRET_DO_NOT_ECHO" not in strings
    assert "api_key" not in strings
    assert all(
        text.startswith(
            (
                "unsafe_",
                "missing_",
                "invalid_",
                "unsupported_",
            )
        )
        for text in result.errors
    )


def test_invalid_result_has_no_caller_content_in_errors() -> None:
    result = _build(advisory_notice="DO_NOT_ECHO secret credential value")
    assert result.is_valid is False
    full_surface = " ".join(_recursive_strings(result)).casefold()
    assert "do_not_echo" not in full_surface
    assert "credential" not in full_surface
    assert "secret" not in full_surface


# ── Test 11: Output surface contains no forbidden claims ─────────────────────


def test_valid_packet_does_not_contain_forbidden_output_claims() -> None:
    result = _build()
    strings = tuple(text.casefold() for text in _recursive_strings(result))
    forbidden = (
        "prompt output",
        "model output",
        "approve pr",
        "merge ready",
        "risk override",
        "trade signal",
        "position size",
        "expected return",
        "place order",
        "cancel order",
        "live approved",
        "paper approved",
        "buy yes",
        "sell now",
    )
    for text in strings:
        for phrase in forbidden:
            assert phrase not in text, (
                f"Forbidden phrase {phrase!r} found in valid packet output"
            )


def test_valid_packet_contains_no_trading_entry_exit_language() -> None:
    result = _build()
    assert result.is_valid is True
    string_items = [item for item in _recursive_items(result) if isinstance(item, str)]
    forbidden_standalone = ("buy", "sell", "entry", "exit")
    for text in string_items:
        for word in forbidden_standalone:
            words_in_text = set(text.casefold().replace("-", " ").replace("_", " ").split())
            assert word not in words_in_text, (
                f"Forbidden word {word!r} found in valid packet string {text!r}"
            )


# ── Test 12: Packet surface inventory is exact ───────────────────────────────


def test_packet_top_level_key_inventory() -> None:
    result = _build()
    assert result.is_valid is True
    expected_top_level_keys = {
        "packet_id",
        "packet_type",
        "artifact_id",
        "artifact_type",
        "provenance_status",
        "staleness_status",
        "summary",
        "recommended_research_family",
        "recommended_next_review_step",
        "deterministic_owner",
        "source_refs",
        "data_quality_warnings",
        "known_missing_data",
        "context_sections",
        "uncertainty_notes",
        "assumptions",
        "falsification_checks",
        "operator_notes",
        "related_repo_truth_refs",
        "advisory_only",
        "human_review_required",
        "forbidden_use_notice",
        "no_execution_authority",
        "no_runtime_authority",
        "no_credential_authority",
        "no_paper_or_live_authority",
    }
    assert set(result.packet) == expected_top_level_keys


def test_context_sections_key_inventory() -> None:
    result = _build()
    assert result.is_valid is True
    expected_context_keys = {
        "advisory_notice",
        "candidate_review_identity",
        "key_findings",
        "limitations",
        "report_reference",
        "review_status",
    }
    assert set(result.packet["context_sections"]) == expected_context_keys


def test_packet_contains_required_advisory_safety_flags() -> None:
    result = _build()
    assert result.is_valid is True
    assert result.packet["advisory_only"] is True
    assert result.packet["human_review_required"] is True
    assert result.packet["no_execution_authority"] is True
    assert result.packet["no_runtime_authority"] is True
    assert result.packet["no_credential_authority"] is True
    assert result.packet["no_paper_or_live_authority"] is True
    assert isinstance(result.packet["forbidden_use_notice"], str)
    assert result.packet["forbidden_use_notice"]


def test_packet_artifact_type_and_packet_type_are_safe_constants() -> None:
    result = _build()
    assert result.is_valid is True
    assert result.packet["packet_type"] == "CANDIDATE_REVIEW_CONTEXT_PACKET_V1"
    assert result.packet["artifact_type"] == "candidate_review_advisory_report"
    assert "signal" not in result.packet["artifact_type"]
    assert "live" not in result.packet["packet_type"]


# ── Test 13: Optional fields omitted do not cause failures ───────────────────


def test_valid_result_with_only_required_fields() -> None:
    result = build_candidate_review_hermes_context_packet(
        packet_id="candidate_packet_002",
        report_identity="candidate_review_report_002",
        source_refs=["docs/project_status.md"],
        advisory_notice="Advisory review context. Human review required before any use.",
        human_review_required=True,
        review_status="REVIEW_VALIDATED_RECORD",
        provenance_status="verified_local_fixture",
        staleness_status="current_at_manual_review",
        recommended_next_review_step="Compare the cited source manually before use.",
    )
    assert result.is_valid is True
    assert result.errors == ()
    assert result.packet


def test_valid_result_context_sections_without_optional_fields() -> None:
    result = build_candidate_review_hermes_context_packet(
        packet_id="candidate_packet_003",
        report_identity="candidate_review_report_003",
        source_refs=["docs/project_status.md"],
        advisory_notice="Advisory review context. Human review required before any use.",
        human_review_required=True,
        review_status="REVIEW_VALIDATED_RECORD",
        provenance_status="verified_local_fixture",
        staleness_status="current_at_manual_review",
        recommended_next_review_step="Compare the cited source manually before use.",
    )
    assert result.is_valid is True
    expected_minimal_context_keys = {
        "advisory_notice",
        "candidate_review_identity",
        "review_status",
    }
    assert set(result.packet["context_sections"]) == expected_minimal_context_keys


# ── Test 14: Source module has only stdlib + approved internal imports ────────


def test_source_imports_are_stdlib_or_approved_internal_only() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    allowed_roots = {
        "__future__",
        "collections",
        "src",
    }
    assert imported_roots <= allowed_roots


def test_source_approved_internal_import_is_only_wp100() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    from_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("src"):
            from_imports.add(node.module)
    assert from_imports == {"src.data_layer.hermes_context_packet_exporter"}


def test_source_has_no_forbidden_stdlib_imports() -> None:
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


# ── Test 15: No network/file-write/subprocess/CLI/loop surface ───────────────


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


def test_source_has_no_network_or_subprocess_imports() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in ("import socket", "import requests", "import httpx", "import subprocess"):
        assert forbidden not in source


# ── Test 16: Result is a HermesContextPacketBuildResult ─────────────────────


def test_result_type_is_context_packet_build_result() -> None:
    result = _build()
    assert isinstance(result, HermesContextPacketBuildResult)


def test_result_field_coverage_gate() -> None:
    result = _build()
    serialized = asdict(result)
    assert {
        field.name for field in fields(HermesContextPacketBuildResult)
    } <= set(serialized)


# ── Test 17: Status entry file exists and is stable ─────────────────────────


def test_status_entry_file_exists() -> None:
    assert STATUS_ENTRY.is_file(), f"Status entry not found: {STATUS_ENTRY}"


def test_status_entry_has_no_dynamic_branch_wording() -> None:
    text = STATUS_ENTRY.read_text(encoding="utf-8")
    for phrase in (
        "WP103 on branch",
        "WP103 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
    ):
        assert phrase not in text
