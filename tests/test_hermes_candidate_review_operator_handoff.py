"""Focused tests for the WP106 Hermes candidate-review operator handoff object.

Tests the in-memory handoff validator and builder added in WP106 per the WP105
operator handoff contract. Verifies required groups, safety flags, decision
labels, source-review checklist, forbidden content rejection, raw/free-form
metadata rejection, fail-closed behavior, and no-unsafe-echo policy.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import re
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "data_layer" / "hermes_candidate_review_operator_handoff.py"


def _import_module():
    mod_name = "hermes_candidate_review_operator_handoff"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _import_module()

build_handoff = _mod.build_candidate_review_operator_handoff
validate_handoff = _mod.validate_candidate_review_operator_handoff
assert_handoff = _mod.assert_candidate_review_operator_handoff
ALLOWED_LABELS = _mod.ALLOWED_HANDOFF_DECISION_LABELS
REQUIRED_GROUPS = _mod.REQUIRED_HANDOFF_GROUPS
REQUIRED_FLAGS = _mod.REQUIRED_HANDOFF_SAFETY_FLAGS
HandoffResult = _mod.HermesCandidateReviewOperatorHandoffResult


# ---------------------------------------------------------------------------
# Minimal valid handoff fixture
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


def _valid_handoff(decision_label: str = "ACCEPT_FOR_MANUAL_RESEARCH_REVIEW") -> dict[str, Any]:
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
        "packet_stage_summary": {
            "passed": True,
            "reason_codes": [],
        },
        "receipt_stage_summary": {
            "passed": True,
            "checked_source_refs": ["ref-001"],
            "reason_codes": [],
        },
        "operator_review_stage_summary": {
            "passed": True,
            "reason_codes": [],
        },
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
            "timestamp_note": "2026-06-23",
            "rationale": "Manual review completed. Proceeding.",
        },
        "next_research_step": {
            "step_description": "Review additional source references.",
            "step_type": "MANUAL_RESEARCH",
        },
        "safety_flags": _valid_safety_flags(),
        "rejection_reasons": [],
    }


# ---------------------------------------------------------------------------
# Test 1: Valid minimal handoff builds successfully
# ---------------------------------------------------------------------------


def test_valid_minimal_handoff_builds_successfully():
    result = build_handoff(_valid_handoff())
    assert result.is_valid is True
    assert result.errors == ()
    assert result.handoff != {}
    assert result.decision_label == "ACCEPT_FOR_MANUAL_RESEARCH_REVIEW"


# ---------------------------------------------------------------------------
# Test 2: Valid handoff includes exactly the required top-level groups
# ---------------------------------------------------------------------------


def test_valid_handoff_includes_all_required_groups():
    result = build_handoff(_valid_handoff())
    assert result.is_valid is True
    for group in REQUIRED_GROUPS:
        assert group in result.handoff, f"Missing group: {group}"


# ---------------------------------------------------------------------------
# Test 3: Valid handoff preserves all required safety flags
# ---------------------------------------------------------------------------


def test_valid_handoff_preserves_required_safety_flags():
    result = build_handoff(_valid_handoff())
    assert result.is_valid is True
    for flag in REQUIRED_FLAGS:
        assert result.safety_flags.get(flag) is True, f"Missing flag: {flag}"
    assert result.handoff["safety_flags"] == {f: True for f in REQUIRED_FLAGS}


# ---------------------------------------------------------------------------
# Test 4: Each allowed decision label is accepted
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", sorted(ALLOWED_LABELS))
def test_each_allowed_decision_label_accepted(label):
    data = _valid_handoff(decision_label=label)
    # For non-ACCEPT labels, checklist bool values may be False
    if label != "ACCEPT_FOR_MANUAL_RESEARCH_REVIEW":
        data["source_review_checklist"]["source_references_present"] = False
    result = build_handoff(data)
    assert result.is_valid is True
    assert result.decision_label == label


# ---------------------------------------------------------------------------
# Test 5: Unknown decision label is rejected fail-closed
# ---------------------------------------------------------------------------


def test_unknown_decision_label_rejected_fail_closed():
    data = _valid_handoff()
    data["human_decision_record"]["decision_label"] = "UNKNOWN_LABEL_XYZ"
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "INVALID_DECISION_LABEL" in result.errors


# ---------------------------------------------------------------------------
# Test 6: Missing required conceptual group is rejected fail-closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("group", REQUIRED_GROUPS)
def test_missing_required_group_rejected_fail_closed(group):
    data = _valid_handoff()
    del data[group]
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "MISSING_REQUIRED_GROUP" in result.errors


# ---------------------------------------------------------------------------
# Test 7: Missing or false safety flag is rejected fail-closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag", REQUIRED_FLAGS)
def test_missing_safety_flag_rejected_fail_closed(flag):
    data = _valid_handoff()
    flags = _valid_safety_flags()
    del flags[flag]
    data["safety_flags"] = flags
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "INVALID_SAFETY_FLAG" in result.errors


@pytest.mark.parametrize("flag", REQUIRED_FLAGS)
def test_false_safety_flag_rejected_fail_closed(flag):
    data = _valid_handoff()
    flags = _valid_safety_flags()
    flags[flag] = False
    data["safety_flags"] = flags
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "INVALID_SAFETY_FLAG" in result.errors


# ---------------------------------------------------------------------------
# Test 8: Conflicting authority field is rejected fail-closed
# ---------------------------------------------------------------------------


def test_conflicting_authority_field_rejected_fail_closed():
    data = _valid_handoff()
    flags = _valid_safety_flags()
    flags["no_execution_authority"] = False
    data["safety_flags"] = flags
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "INVALID_SAFETY_FLAG" in result.errors


# ---------------------------------------------------------------------------
# Test 9: Missing required source-review checklist key is rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", [
    "source_references_present",
    "source_references_manually_inspectable",
    "provenance_status_explicit",
    "staleness_status_explicit",
    "known_missing_data_explicit",
    "uncertainty_notes_explicit",
    "limitations_explicit",
    "falsification_checks_explicit",
    "next_research_step_explicit",
    "human_decision_record_explicit",
])
def test_missing_checklist_key_rejected(key):
    data = _valid_handoff()
    checklist = _valid_checklist()
    del checklist[key]
    data["source_review_checklist"] = checklist
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "INVALID_SOURCE_REVIEW_CHECKLIST" in result.errors


# ---------------------------------------------------------------------------
# Test 10: False required source-review checklist key rejected for ACCEPT label
# ---------------------------------------------------------------------------


def test_false_checklist_key_rejected_for_accept_label():
    data = _valid_handoff(decision_label="ACCEPT_FOR_MANUAL_RESEARCH_REVIEW")
    checklist = _valid_checklist()
    checklist["source_references_present"] = False
    data["source_review_checklist"] = checklist
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "INVALID_SOURCE_REVIEW_CHECKLIST" in result.errors


def test_false_checklist_key_allowed_for_reject_label():
    data = _valid_handoff(decision_label="REJECT_FOR_INSUFFICIENT_EVIDENCE")
    checklist = _valid_checklist()
    checklist["source_references_present"] = False
    data["source_review_checklist"] = checklist
    result = build_handoff(data)
    assert result.is_valid is True


# ---------------------------------------------------------------------------
# Test 11: Forbidden trade/order/execution variants rejected recursively
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("forbidden_key,forbidden_value", [
    ("buy", "some value"),
    ("sell", "some value"),
    ("order", "place order instruction"),
    ("trade", "some trade data"),
    ("execute", "execute this"),
    ("position", "long position"),
    ("stop_loss", "0.05"),
    ("take_profit", "0.10"),
])
def test_forbidden_trade_execution_keys_rejected_recursively(forbidden_key, forbidden_value):
    data = _valid_handoff()
    data["evidence_and_provenance"][forbidden_key] = forbidden_value
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "FORBIDDEN_CONTENT" in result.errors


def test_forbidden_trade_value_in_nested_dict_rejected():
    data = _valid_handoff()
    data["staleness_and_missing_data"]["note"] = "buy yes immediately"
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "FORBIDDEN_CONTENT" in result.errors


# ---------------------------------------------------------------------------
# Test 12: Forbidden expected-return/edge/fair-value/tradability variants rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [
    "expected return is 0.12",
    "the edge here is significant",
    "fair value estimate",
    "tradability score",
    "tradable market",
    "confidence to trade",
    "trade ready signal",
])
def test_forbidden_scoring_readiness_values_rejected(value):
    data = _valid_handoff()
    data["evidence_and_provenance"]["note"] = value
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "FORBIDDEN_CONTENT" in result.errors


# ---------------------------------------------------------------------------
# Test 13: Forbidden paper/live/readiness variants rejected recursively
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [
    "live ready for deployment",
    "paper ready to test",
    "alpha signal detected",
])
def test_forbidden_paper_live_values_rejected(value):
    data = _valid_handoff()
    data["uncertainty_and_limitations"]["note"] = value
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "FORBIDDEN_CONTENT" in result.errors


# ---------------------------------------------------------------------------
# Test 14: Forbidden PR approval/merge-readiness variants rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [
    "approve pr immediately",
    "approve pull request",
    "merge ready now",
    "strategy promotion approved",
    "risk override granted",
])
def test_forbidden_pr_approval_values_rejected(value):
    data = _valid_handoff()
    data["falsification_checks"]["note"] = value
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "FORBIDDEN_CONTENT" in result.errors


# ---------------------------------------------------------------------------
# Test 15: Forbidden credential/private-key/API-key/secret/wallet variants rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [
    "credential required",
    "private key abc123",
    "api key is needed",
    "the secret passphrase",
    "passphrase for account",
    "wallet address",
    "private endpoint access",
    "account endpoint url",
])
def test_forbidden_credential_values_rejected(value):
    data = _valid_handoff()
    data["handoff_identity"]["note"] = value
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "FORBIDDEN_CONTENT" in result.errors


# ---------------------------------------------------------------------------
# Test 16: Forbidden runtime/provider/model/prompt/scheduler/bot-loop variants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [
    "provider configuration needed",
    "model call required",
    "prompt execution requested",
    "prompt runner active",
    "hermes runtime start",
    "scheduler trigger",
    "bot loop iteration",
    "daemon process running",
    "network poller active",
    "file writer output",
    "report writer needed",
    "exporter module",
])
def test_forbidden_runtime_model_prompt_values_rejected(value):
    data = _valid_handoff()
    data["next_research_step"]["note"] = value
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "FORBIDDEN_CONTENT" in result.errors


# ---------------------------------------------------------------------------
# Test 17: Raw/free-form metadata keys are rejected recursively
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw_key", [
    "raw_metadata",
    "free_form_metadata",
    "caller_metadata",
    "arbitrary_metadata",
    "raw_input",
    "untrusted_input",
    "notes_raw",
    "warnings_raw",
    "reason_text_raw",
    "custom",
    "extras",
    "metadata",
    "freeform",
])
def test_raw_metadata_keys_rejected_recursively(raw_key):
    data = _valid_handoff()
    data["evidence_and_provenance"][raw_key] = {"some": "data"}
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "RAW_METADATA_NOT_ALLOWED" in result.errors


def test_nested_raw_metadata_rejected():
    data = _valid_handoff()
    data["source_chain_summary"]["details"] = {"metadata": "some raw data"}
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}
    assert "RAW_METADATA_NOT_ALLOWED" in result.errors


# ---------------------------------------------------------------------------
# Test 18: Invalid outputs do not echo unsafe caller input
# ---------------------------------------------------------------------------


def test_invalid_output_does_not_echo_unsafe_input_in_errors():
    unsafe_payload = "buy yes at market price with private_key=abc123"
    data = _valid_handoff()
    data["evidence_and_provenance"]["note"] = unsafe_payload
    result = build_handoff(data)
    assert result.is_valid is False
    for err in result.errors:
        assert unsafe_payload not in err
        assert "abc123" not in err
        assert "private" not in err.lower() or err == err.upper()


def test_invalid_output_does_not_echo_unsafe_input_in_warnings():
    unsafe_payload = "sell everything now with api_key=secret999"
    data = _valid_handoff()
    data["uncertainty_and_limitations"]["note"] = unsafe_payload
    result = build_handoff(data)
    assert result.is_valid is False
    for w in result.warnings:
        assert unsafe_payload not in w
        assert "secret999" not in w


def test_invalid_output_handoff_is_empty():
    data = _valid_handoff()
    data["evidence_and_provenance"]["note"] = "buy yes at market"
    result = build_handoff(data)
    assert result.is_valid is False
    assert result.handoff == {}


# ---------------------------------------------------------------------------
# Test 19: Invalid output handoff is empty
# ---------------------------------------------------------------------------


def test_invalid_handoff_is_always_empty_dict():
    for label in ("UNKNOWN_LABEL", None, "", 42):
        data = _valid_handoff()
        data["human_decision_record"]["decision_label"] = label
        result = build_handoff(data)
        if not result.is_valid:
            assert result.handoff == {}, f"Non-empty handoff for invalid input: {label}"


# ---------------------------------------------------------------------------
# Test 20: assert helper raises neutral error without unsafe echo
# ---------------------------------------------------------------------------


def test_assert_helper_raises_on_invalid_handoff():
    data = _valid_handoff()
    del data["handoff_identity"]
    with pytest.raises(ValueError) as exc_info:
        assert_handoff(data)
    msg = str(exc_info.value)
    assert "INVALID_CANDIDATE_REVIEW_OPERATOR_HANDOFF" in msg
    assert "MISSING_REQUIRED_GROUP" in msg


def test_assert_helper_does_not_echo_unsafe_input():
    unsafe = "buy yes api_key=supersecret"
    data = _valid_handoff()
    data["evidence_and_provenance"]["note"] = unsafe
    with pytest.raises(ValueError) as exc_info:
        assert_handoff(data)
    msg = str(exc_info.value)
    assert "supersecret" not in msg
    assert unsafe not in msg


def test_assert_helper_returns_result_on_valid_handoff():
    data = _valid_handoff()
    result = assert_handoff(data)
    assert result.is_valid is True


# ---------------------------------------------------------------------------
# Test 21: Module uses approved imports only
# ---------------------------------------------------------------------------


def test_module_uses_approved_imports_only():
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    approved_modules = {
        "__future__",
        "dataclasses",
        "typing",
        "collections",
        "collections.abc",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                base = alias.name.split(".")[0]
                assert base in approved_modules, (
                    f"Non-approved import: {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base = node.module.split(".")[0]
                assert base in approved_modules, (
                    f"Non-approved from-import: {node.module}"
                )


# ---------------------------------------------------------------------------
# Test 22: Module source contains no forbidden behaviors
# ---------------------------------------------------------------------------


def test_module_source_contains_no_forbidden_behaviors():
    source = MODULE_PATH.read_text(encoding="utf-8")
    import re as _re

    # These patterns check for actual import statements or function calls
    # that would introduce file I/O, network, subprocess, or credentials.
    # They must NOT appear as actual code (import or call), not as string literals.
    forbidden_import_patterns = [
        r"^\s*import\s+pathlib\b",
        r"^\s*import\s+requests\b",
        r"^\s*import\s+urllib\b",
        r"^\s*import\s+http\b",
        r"^\s*import\s+socket\b",
        r"^\s*import\s+subprocess\b",
        r"^\s*import\s+os\b",
        r"^\s*import\s+dotenv\b",
        r"^\s*from\s+pathlib\b",
        r"^\s*from\s+requests\b",
        r"^\s*from\s+urllib\b",
        r"^\s*from\s+http\b",
        r"^\s*from\s+socket\b",
        r"^\s*from\s+subprocess\b",
        r"^\s*from\s+os\b",
        r"^\s*from\s+dotenv\b",
    ]
    # These check for actual function call patterns in non-comment, non-string code
    forbidden_call_patterns = [
        r"\bopen\s*\(",
        r"\bos\.environ\b",
        r"\bsubprocess\.",
    ]
    for pattern in forbidden_import_patterns:
        assert not _re.search(pattern, source, _re.MULTILINE), (
            f"Forbidden import found in source: {pattern}"
        )
    # For call patterns, strip docstrings and comments first
    code_only = _re.sub(r'""".*?"""', '', source, flags=_re.DOTALL)
    code_only = _re.sub(r"'''.*?'''", '', code_only, flags=_re.DOTALL)
    code_only = '\n'.join(
        line for line in code_only.splitlines()
        if not line.strip().startswith('#')
    )
    # Strip string literals to avoid matching forbidden words inside string constants
    code_no_strings = _re.sub(r'"[^"]*"', '""', code_only)
    code_no_strings = _re.sub(r"'[^']*'", "''", code_no_strings)
    for pattern in forbidden_call_patterns:
        assert not _re.search(pattern, code_no_strings), (
            f"Forbidden call pattern found in source code: {pattern}"
        )


# ---------------------------------------------------------------------------
# Test 23: Documentation contract references WP106
# ---------------------------------------------------------------------------


def test_contract_doc_references_wp106_implementation_started():
    contract_path = ROOT / "docs" / "hermes_candidate_review_operator_handoff_contract.md"
    assert contract_path.is_file()
    text = contract_path.read_text(encoding="utf-8")
    assert "WP106" in text


# ---------------------------------------------------------------------------
# Test 24: Project status records WP106 and preserves protected boundaries
# ---------------------------------------------------------------------------


def test_project_status_records_wp106_and_preserves_boundaries():
    status_path = ROOT / "docs" / "project_status.md"
    text = status_path.read_text(encoding="utf-8")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP106" in merged_line
    for phrase in (
        "Live trading status: DISABLED",
        "Credentials status: NOT_USED",
        "Execution status: NOT_STARTED",
        "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "Scheduler status: NOT_STARTED",
        "Bot loop status: NOT_STARTED",
        "Agent execution authority: FORBIDDEN",
    ):
        assert phrase in text, f"Missing protected boundary phrase: {phrase}"


# ---------------------------------------------------------------------------
# Test 25: WP106 status entry lists exact changed files and no dynamic wording
# ---------------------------------------------------------------------------


def test_wp106_status_entry_exists_and_lists_exact_changed_files():
    status_entry = ROOT / "docs" / "status_entries" / "WP106.md"
    assert status_entry.is_file()
    text = status_entry.read_text(encoding="utf-8")
    for path in (
        "src/data_layer/hermes_candidate_review_operator_handoff.py",
        "tests/test_hermes_candidate_review_operator_handoff.py",
        "docs/hermes_candidate_review_operator_handoff_contract.md",
        "docs/status_entries/WP106.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_hermes_candidate_review_operator_handoff_contract_docs.py",
        "tests/test_hermes_advisory_foundation_architecture_docs.py",
        "tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py",
        "tests/test_architecture_boundaries.py",
    ):
        assert path in text, f"Missing expected file in status entry: {path}"
    assert "Package size class: L (16 changed files" in text
    for stale in (
        "count depends",
        "TBD after merge",
        "WP106 on branch",
        "WP106 active branch",
        "Head commit:",
        "LOCAL_DRAFT_VERIFIED",
    ):
        assert stale not in text, f"Stale wording in WP106 status entry: {stale}"
    assert "Ready for review: YES" in text
    assert "stable and non-self-referential" in text
