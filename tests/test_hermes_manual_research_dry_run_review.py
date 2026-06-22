"""Focused tests for the WP102 Hermes manual research dry-run operator review."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, asdict, fields
from pathlib import Path

import pytest

from src.data_layer.hermes_context_packet_dry_run_receipt import (
    REQUIRED_READINESS_CHECKS,
    build_hermes_context_packet_dry_run_receipt,
)
from src.data_layer.hermes_context_packet_exporter import build_hermes_context_packet
from src.data_layer.hermes_manual_research_dry_run_review import (
    REQUIRED_SOURCE_REVIEW_CHECKS,
    HermesManualResearchDryRunReviewResult,
    build_hermes_manual_research_dry_run_review,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "data_layer" / "hermes_manual_research_dry_run_review.py"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP102.md"


# ── Helper builders ──────────────────────────────────────────────────────────


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


def _valid_receipt() -> dict[str, object]:
    packet = _valid_packet()
    result = build_hermes_context_packet_dry_run_receipt(
        receipt_id="receipt_001",
        packet=packet,
        reviewer_id="reviewer_001",
        dry_run_scope="manual packet readiness review",
        checked_source_refs=[
            "docs/hermes_input_output_contracts_and_validator_requirements.md",
            "docs/project_status.md",
        ],
        readiness_checks={key: True for key in REQUIRED_READINESS_CHECKS},
        stop_reasons=None,
        operator_notes=["Reviewed local source references."],
        related_repo_truth_refs=["docs/project_status.md"],
    )
    assert result.is_valid is True
    return dict(result.receipt)


def _valid_source_review_checks() -> dict[str, bool]:
    return {key: True for key in REQUIRED_SOURCE_REVIEW_CHECKS}


def _valid_kwargs() -> dict[str, object]:
    return {
        "review_id": "review_001",
        "dry_run_receipt": _valid_receipt(),
        "operator_id": "operator_001",
        "selected_research_family": "broad_market_hypothesis",
        "selected_operator_runbook_ref": (
            "docs/hermes_research_prompt_pack_and_operator_runbooks.md"
        ),
        "source_review_checks": _valid_source_review_checks(),
        "stop_reasons": None,
        "operator_notes": ["Reviewed local source references."],
        "related_repo_truth_refs": ["docs/project_status.md"],
    }


def _build(**overrides: object) -> HermesManualResearchDryRunReviewResult:
    kwargs = _valid_kwargs()
    kwargs.update(overrides)
    return build_hermes_manual_research_dry_run_review(**kwargs)  # type: ignore[arg-type]


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


# ── Test 1: Valid full pipeline from WP100 through WP102 ────────────────────


def test_valid_pipeline_from_wp100_through_wp102() -> None:
    result = _build()
    assert result.is_valid is True
    assert result.errors == ()
    assert result.warnings == ()
    assert result.review["review_id"] == "review_001"
    assert result.review["receipt_id"] == "receipt_001"
    assert result.review["packet_id"] == "packet_001"
    assert result.review["review_status"] == "READY_FOR_MANUAL_RESEARCH_REVIEW"
    assert result.review["review_type"] == "HERMES_MANUAL_RESEARCH_DRY_RUN_OPERATOR_REVIEW_V1"


# ── Test 2-8: Receipt safety flag violations ─────────────────────────────────


def test_receipt_with_prompt_execution_performed_true_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["prompt_execution_performed"] = True
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}
    assert result.errors


def test_receipt_with_hermes_runtime_used_true_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["hermes_runtime_used"] = True
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}
    assert result.errors


def test_receipt_with_model_or_provider_called_true_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["model_or_provider_called"] = True
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}
    assert result.errors


def test_receipt_with_file_written_true_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["file_written"] = True
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}
    assert result.errors


def test_receipt_with_network_used_true_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["network_used"] = True
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}
    assert result.errors


def test_receipt_with_paper_or_live_authority_true_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["paper_or_live_authority"] = True
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}
    assert result.errors


def test_receipt_with_execution_or_risk_authority_true_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["execution_or_risk_authority"] = True
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}
    assert result.errors


# ── Test 9: Missing receipt identity fields ──────────────────────────────────


@pytest.mark.parametrize("field", ("receipt_id", "packet_id", "packet_type"))
def test_missing_receipt_identity_field_fails_closed(field: str) -> None:
    receipt = _valid_receipt()
    del receipt[field]
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}
    assert result.errors


# ── Test 10: Missing source refs ─────────────────────────────────────────────


@pytest.mark.parametrize("field", ("source_refs", "checked_source_refs"))
def test_missing_receipt_source_ref_field_fails_closed(field: str) -> None:
    receipt = _valid_receipt()
    del receipt[field]
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}
    assert result.errors


def test_empty_source_refs_in_receipt_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["source_refs"] = ()
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}


# ── Test 11: Source-review checks validation ─────────────────────────────────


@pytest.mark.parametrize("check_name", REQUIRED_SOURCE_REVIEW_CHECKS)
def test_missing_source_review_check_fails_closed(check_name: str) -> None:
    checks = _valid_source_review_checks()
    del checks[check_name]
    result = _build(source_review_checks=checks)
    assert result.is_valid is False
    assert result.review == {}
    assert result.errors


@pytest.mark.parametrize("check_name", REQUIRED_SOURCE_REVIEW_CHECKS)
def test_false_source_review_check_fails_closed(check_name: str) -> None:
    checks = _valid_source_review_checks()
    checks[check_name] = False
    result = _build(source_review_checks=checks)
    assert result.is_valid is False
    assert result.review == {}
    assert result.errors


def test_extra_source_review_check_fails_closed() -> None:
    checks = _valid_source_review_checks()
    checks["extra_undeclared_check"] = True
    result = _build(source_review_checks=checks)
    assert result.is_valid is False
    assert result.review == {}
    assert result.errors


def test_non_bool_source_review_check_value_fails_closed() -> None:
    checks = dict(_valid_source_review_checks())
    checks["receipt_reviewed"] = 1  # type: ignore[assignment]
    result = _build(source_review_checks=checks)
    assert result.is_valid is False
    assert result.review == {}


def test_empty_source_review_checks_fails_closed() -> None:
    result = _build(source_review_checks={})
    assert result.is_valid is False
    assert result.review == {}


# ── Test 12: Stop reasons ────────────────────────────────────────────────────


def test_stop_reasons_prevent_ready_review() -> None:
    result = _build(stop_reasons=["Another comparison is needed before review."])
    assert result.is_valid is False
    assert result.review == {}
    assert any(error.startswith("stop_reasons_present_") for error in result.errors)


def test_multiple_stop_reasons_prevent_ready_review() -> None:
    result = _build(
        stop_reasons=[
            "Provenance gap detected.",
            "Source comparison incomplete.",
        ]
    )
    assert result.is_valid is False
    assert result.review == {}


# ── Test 13: Credential/private-key variants ─────────────────────────────────


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
def test_credential_variant_in_operator_notes_fails_without_echo(
    unsafe_phrase: str,
) -> None:
    result = _build(operator_notes=[f"DO_NOT_ECHO {unsafe_phrase}"])
    assert result.is_valid is False
    assert result.review == {}
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
def test_credential_variant_in_receipt_nested_values_fails_without_echo(
    unsafe_phrase: str,
) -> None:
    receipt = _valid_receipt()
    receipt["operator_notes"] = (f"DO_NOT_ECHO {unsafe_phrase}",)
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}
    full_surface = " ".join(_recursive_strings(result)).casefold()
    assert unsafe_phrase.casefold() not in full_surface
    assert "do_not_echo" not in full_surface


# ── Test 14: Order/execution/trade variants ──────────────────────────────────


@pytest.mark.parametrize(
    "unsafe_phrase",
    (
        "order_state",
        "live_position",
        "portfolio_position",
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
    ),
)
def test_order_execution_variant_in_operator_notes_fails_without_echo(
    unsafe_phrase: str,
) -> None:
    result = _build(operator_notes=[f"DO_NOT_ECHO {unsafe_phrase}"])
    assert result.is_valid is False
    assert result.review == {}
    full_surface = " ".join(_recursive_strings(result)).casefold()
    assert unsafe_phrase.casefold() not in full_surface
    assert "do_not_echo" not in full_surface


# ── Test 15: Runtime/prompt-runner/model-provider variants ───────────────────


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
        "live approved",
        "paper approved",
    ),
)
def test_runtime_variant_in_operator_notes_fails_without_echo(
    unsafe_phrase: str,
) -> None:
    result = _build(operator_notes=[f"DO_NOT_ECHO {unsafe_phrase}"])
    assert result.is_valid is False
    assert result.review == {}
    full_surface = " ".join(_recursive_strings(result)).casefold()
    assert unsafe_phrase.casefold() not in full_surface
    assert "do_not_echo" not in full_surface


# ── Test 16: Raw/free-form mapping keys ──────────────────────────────────────


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
def test_raw_mapping_key_in_receipt_nested_values_fails_closed(
    raw_key: str,
) -> None:
    receipt = _valid_receipt()
    receipt["operator_notes"] = ({raw_key: "opaque"},)  # type: ignore[assignment]
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}
    assert raw_key not in " ".join(_recursive_strings(result))


def test_recursive_raw_key_inside_receipt_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["operator_notes"] = ({"details": {"raw_payload": "x"}},)  # type: ignore[assignment]
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}


def test_raw_mapping_key_in_source_review_checks_fails_closed() -> None:
    checks = _valid_source_review_checks()
    checks["metadata"] = True  # type: ignore[assignment]
    result = _build(source_review_checks=checks)
    assert result.is_valid is False
    assert result.review == {}


# ── Test 17: Invalid output is empty and neutral ─────────────────────────────


def test_invalid_result_surfaces_are_empty_and_neutral() -> None:
    result = _build(review_id="SECRET_DO_NOT_ECHO")
    assert result.is_valid is False
    assert result.review == {}
    strings = _recursive_strings(result)
    assert "SECRET_DO_NOT_ECHO" not in strings
    assert all(
        text.startswith(
            (
                "unsafe_",
                "missing_",
                "invalid_",
                "stop_",
                "unsupported_",
            )
        )
        for text in result.errors
    )


def test_invalid_result_has_no_warnings() -> None:
    result = _build(stop_reasons=["comparison needed"])
    assert result.is_valid is False
    assert result.warnings == ()


# ── Test 18: Valid output contains no forbidden claims ───────────────────────


def test_valid_review_does_not_contain_forbidden_output_claims() -> None:
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
        "buy",
        "sell",
        "place order",
        "cancel order",
        "pr approval",
        "merge-ready",
        "live approved",
        "paper approved",
    )
    for text in strings:
        for phrase in forbidden:
            assert phrase not in text, (
                f"Forbidden phrase {phrase!r} found in valid review output"
            )


def test_valid_review_contains_no_trading_entry_exit_language() -> None:
    result = _build()
    assert result.is_valid is True
    items = _recursive_items(result)
    string_items = [item for item in items if isinstance(item, str)]
    forbidden_standalone = ("entry", "exit", "buy", "sell", "trade")
    for text in string_items:
        for word in forbidden_standalone:
            words_in_text = set(text.casefold().replace("-", " ").split())
            assert word not in words_in_text, (
                f"Forbidden word {word!r} found in valid review output string {text!r}"
            )


# ── Test 19: Source module imports stdlib only ────────────────────────────────


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


# ── Test 20: No network/file-write/subprocess/CLI/loop surface ───────────────


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


# ── Test 21: Result dataclass is frozen ──────────────────────────────────────


def test_result_is_frozen_dataclass() -> None:
    result = _build()
    with pytest.raises(FrozenInstanceError):
        result.is_valid = False  # type: ignore[misc]


def test_result_field_coverage_gate() -> None:
    result = _build()
    serialized = asdict(result)
    assert {
        field.name for field in fields(HermesManualResearchDryRunReviewResult)
    } <= set(serialized)


# ── Test 22: Public review surface inventory is exact and tested ─────────────


def test_review_public_surface_inventory() -> None:
    review = _build().review
    expected = {
        "review_id",
        "review_type",
        "review_status",
        "receipt_id",
        "receipt_type",
        "packet_id",
        "packet_type",
        "operator_id",
        "selected_research_family",
        "selected_operator_runbook_ref",
        "source_review_checks",
        "related_repo_truth_refs",
        "operator_notes",
        "advisory_only",
        "manual_review_required",
        "dry_run_only",
        "prompt_execution_performed",
        "hermes_runtime_used",
        "model_or_provider_called",
        "file_written",
        "network_used",
        "paper_or_live_authority",
        "execution_or_risk_authority",
        "credential_or_account_authority",
    }
    assert expected == set(review)


def test_review_contains_required_safety_flags() -> None:
    review = _build().review
    assert review["advisory_only"] is True
    assert review["manual_review_required"] is True
    assert review["dry_run_only"] is True
    assert review["prompt_execution_performed"] is False
    assert review["hermes_runtime_used"] is False
    assert review["model_or_provider_called"] is False
    assert review["file_written"] is False
    assert review["network_used"] is False
    assert review["paper_or_live_authority"] is False
    assert review["execution_or_risk_authority"] is False
    assert review["credential_or_account_authority"] is False


def test_review_source_review_checks_inventory() -> None:
    review = _build().review
    checks = review["source_review_checks"]
    assert set(checks) == set(REQUIRED_SOURCE_REVIEW_CHECKS)
    for key in REQUIRED_SOURCE_REVIEW_CHECKS:
        assert checks[key] is True


def test_required_source_review_check_inventory_matches_wp102_contract() -> None:
    assert set(REQUIRED_SOURCE_REVIEW_CHECKS) == {
        "receipt_reviewed",
        "source_refs_compared",
        "operator_runbook_compared",
        "research_family_allowed",
        "human_review_gate_checked",
        "no_prompt_execution_checked",
        "no_runtime_checked",
        "no_file_network_checked",
        "no_paper_live_checked",
        "no_execution_risk_checked",
    }


def test_output_surface_scan_covers_dataclass_and_nested_review() -> None:
    result = _build()
    items = _recursive_items(result)
    assert "review_id" in items
    assert "source_review_checks" in items
    assert "receipt_001" in items
    assert True in items
    assert False in items


# ── Additional validity / identity tests ─────────────────────────────────────


def test_valid_review_identity_fields_match_receipt() -> None:
    result = _build()
    assert result.review["receipt_id"] == "receipt_001"
    assert result.review["packet_id"] == "packet_001"
    assert result.review["receipt_type"] == "HERMES_CONTEXT_PACKET_DRY_RUN_RECEIPT_V1"


def test_valid_review_operator_fields_match_inputs() -> None:
    result = _build()
    assert result.review["operator_id"] == "operator_001"
    assert result.review["selected_research_family"] == "broad_market_hypothesis"
    assert result.review["review_status"] == "READY_FOR_MANUAL_RESEARCH_REVIEW"


def test_receipt_type_mismatch_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["receipt_type"] = "WRONG_RECEIPT_TYPE_V1"
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}


def test_receipt_status_mismatch_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["receipt_status"] = "NOT_READY"
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}


def test_receipt_with_dry_run_only_false_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["dry_run_only"] = False
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}


def test_receipt_with_manual_review_required_false_fails_closed() -> None:
    receipt = _valid_receipt()
    receipt["manual_review_required"] = False
    result = _build(dry_run_receipt=receipt)
    assert result.is_valid is False
    assert result.review == {}


def test_empty_review_id_fails_closed() -> None:
    result = _build(review_id="")
    assert result.is_valid is False
    assert result.review == {}


def test_empty_operator_id_fails_closed() -> None:
    result = _build(operator_id="")
    assert result.is_valid is False
    assert result.review == {}


def test_empty_research_family_fails_closed() -> None:
    result = _build(selected_research_family="")
    assert result.is_valid is False
    assert result.review == {}


def test_empty_runbook_ref_fails_closed() -> None:
    result = _build(selected_operator_runbook_ref="")
    assert result.is_valid is False
    assert result.review == {}


def test_none_receipt_fails_closed() -> None:
    result = _build(dry_run_receipt=None)  # type: ignore[arg-type]
    assert result.is_valid is False
    assert result.review == {}


# ── WP102 status entry ───────────────────────────────────────────────────────


def test_wp102_status_entry_exists_and_uses_stable_wording() -> None:
    assert STATUS_ENTRY.is_file()
    text = STATUS_ENTRY.read_text(encoding="utf-8")
    assert "PR: see GitHub PR metadata and PR body." in text
    assert "PR: TBD" not in text
    assert "TBD after merge" not in text
    assert "WP102 on branch" not in text
