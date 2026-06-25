"""Focused tests for WP108 Hermes candidate-review handoff manual export artifact builder.

Tests the in-memory artifact builder added in WP108 per the WP107 local manual export
contract. Verifies required artifact groups, safety flags, decision labels, handoff
input validation, forbidden content rejection, raw/free-form metadata rejection,
fail-closed behavior, no-unsafe-echo policy, deterministic output, and approved-import
constraints.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import math
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "data_layer" / "hermes_candidate_review_handoff_manual_export_artifact.py"
WP106_MODULE_PATH = ROOT / "src" / "data_layer" / "hermes_candidate_review_operator_handoff.py"


def _import_artifact_module():
    mod_name = "hermes_candidate_review_handoff_manual_export_artifact"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _import_wp106_module():
    mod_name = "hermes_candidate_review_operator_handoff"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, WP106_MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _import_artifact_module()
_wp106 = _import_wp106_module()

build_artifact = _mod.build_candidate_review_manual_export_artifact
ArtifactResult = _mod.CandidateReviewManualExportArtifactResult
REQUIRED_GROUPS = _mod.REQUIRED_ARTIFACT_GROUPS
REQUIRED_FLAGS = _mod.REQUIRED_ARTIFACT_SAFETY_FLAGS

build_handoff = _wp106.build_candidate_review_operator_handoff
HandoffResult = _wp106.HermesCandidateReviewOperatorHandoffResult


# ---------------------------------------------------------------------------
# WP106 fixture helpers
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


def _valid_handoff_result(decision_label: str = "ACCEPT_FOR_MANUAL_RESEARCH_REVIEW") -> HandoffResult:
    return build_handoff(_valid_handoff_data(decision_label))


def _valid_artifact_result(**kwargs: Any) -> ArtifactResult:
    defaults: dict[str, Any] = {
        "artifact_id": "artifact-001",
        "handoff_result": _valid_handoff_result(),
    }
    defaults.update(kwargs)
    return build_artifact(**defaults)


# ---------------------------------------------------------------------------
# Test 1: Valid WP106 handoff result creates valid in-memory artifact
# ---------------------------------------------------------------------------


def test_valid_handoff_creates_valid_artifact():
    result = _valid_artifact_result()
    assert result.is_valid is True
    assert result.errors == ()
    assert result.artifact != {}


# ---------------------------------------------------------------------------
# Test 2: Artifact has exactly the 12 required conceptual groups
# ---------------------------------------------------------------------------


def test_artifact_has_exactly_required_groups():
    result = _valid_artifact_result()
    assert result.is_valid is True
    artifact = result.artifact
    assert set(artifact.keys()) == set(REQUIRED_GROUPS), (
        f"Expected {sorted(REQUIRED_GROUPS)}, got {sorted(artifact.keys())}"
    )


# ---------------------------------------------------------------------------
# Test 3: Artifact contains required safety flags with correct True values
# ---------------------------------------------------------------------------


def test_artifact_safety_flags_all_true():
    result = _valid_artifact_result()
    assert result.is_valid is True
    flags = result.artifact["safety_flags"]
    for flag in REQUIRED_FLAGS:
        assert flags.get(flag) is True, f"Missing or false safety flag: {flag}"
    assert len(flags) == len(REQUIRED_FLAGS)


# ---------------------------------------------------------------------------
# Test 4: Artifact identity references WP108 and WP107 contract
# ---------------------------------------------------------------------------


def test_artifact_identity_references_wp108_and_wp107():
    result = _valid_artifact_result()
    identity = result.artifact["artifact_identity"]
    assert identity["source_wp"] == "WP108"
    assert identity["source_contract"] == "WP107"
    assert identity["artifact_type"] == "candidate_review_manual_export_artifact"
    assert identity["in_memory_only"] is True
    assert identity["deterministic_owner"] == "deterministic_core"
    assert identity["artifact_id"] == "artifact-001"


# ---------------------------------------------------------------------------
# Test 5: Source handoff identity copied from safe WP106 identity fields only
# ---------------------------------------------------------------------------


def test_source_handoff_identity_contains_only_safe_identity_fields():
    result = _valid_artifact_result()
    source_id = result.artifact["source_handoff_identity"]
    expected_keys = {"handoff_id", "chain_identifier", "contract_version", "generated_by"}
    assert set(source_id.keys()) == expected_keys
    assert source_id["handoff_id"] == "test-handoff-001"
    assert source_id["chain_identifier"] == "candidate-review-chain"
    assert source_id["contract_version"] == "WP105-V1"
    assert source_id["generated_by"] == "WP106-test"


# ---------------------------------------------------------------------------
# Test 6: No raw/free-form metadata keys appear in output artifact
# ---------------------------------------------------------------------------


_RAW_KEYS = {
    "raw_metadata", "free_form_metadata", "caller_metadata", "arbitrary_metadata",
    "raw_input", "untrusted_input", "notes_raw", "warnings_raw", "reason_text_raw",
    "custom", "extras", "metadata", "freeform", "extra", "context", "custom_fields",
    "raw_response", "model_response", "prompt", "completion", "raw", "free_form", "arbitrary",
}


def _collect_keys(obj: object) -> set[str]:
    found: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(str(k).lower())
            found |= _collect_keys(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found |= _collect_keys(item)
    return found


def test_no_raw_metadata_keys_in_artifact_output():
    result = _valid_artifact_result()
    all_keys = _collect_keys(result.artifact)
    overlap = all_keys & _RAW_KEYS
    assert overlap == set(), f"Raw/free-form metadata keys found in artifact: {overlap}"


# ---------------------------------------------------------------------------
# Test 7: Invalid handoff result fails closed with empty artifact
# ---------------------------------------------------------------------------


def test_invalid_handoff_result_fails_closed():
    invalid = HandoffResult(
        is_valid=False,
        handoff={},
        errors=("SOME_ERROR",),
        warnings=(),
        safety_flags={},
        decision_label=None,
    )
    result = build_artifact(artifact_id="artifact-001", handoff_result=invalid)
    assert result.is_valid is False
    assert result.artifact == {}
    assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# Test 8: Non-HandoffResult type fails closed
# ---------------------------------------------------------------------------


def test_non_handoff_result_type_fails_closed():
    class FakeHandoff:
        is_valid = True
        handoff = {}
        errors = ()
        warnings = ()
        safety_flags = {}
        decision_label = None
    for bad_input in (None, {}, "string", 42, [], FakeHandoff()):
        result = build_artifact(artifact_id="artifact-001", handoff_result=bad_input)
        assert result.is_valid is False
        assert result.artifact == {}


# ---------------------------------------------------------------------------
# Test 9: Missing required WP106 group fails closed
# ---------------------------------------------------------------------------


def test_missing_wp106_group_fails_closed():
    data = _valid_handoff_data()
    del data["evidence_and_provenance"]
    handoff = build_handoff(data)
    # WP106 itself will fail closed, so handoff is invalid
    result = build_artifact(artifact_id="artifact-001", handoff_result=handoff)
    assert result.is_valid is False
    assert result.artifact == {}


# ---------------------------------------------------------------------------
# Test 10: Missing or false safety flag in WP106 handoff fails closed
# ---------------------------------------------------------------------------


def test_missing_wp106_safety_flag_fails_closed():
    data = _valid_handoff_data()
    data["safety_flags"]["advisory_only"] = False
    handoff = build_handoff(data)
    result = build_artifact(artifact_id="artifact-001", handoff_result=handoff)
    assert result.is_valid is False
    assert result.artifact == {}


# ---------------------------------------------------------------------------
# Test 11: Invalid decision label fails closed
# ---------------------------------------------------------------------------


def test_invalid_decision_label_fails_closed():
    data = _valid_handoff_data()
    data["human_decision_record"]["decision_label"] = "INVALID_LABEL"
    handoff = build_handoff(data)
    result = build_artifact(artifact_id="artifact-001", handoff_result=handoff)
    assert result.is_valid is False
    assert result.artifact == {}


# ---------------------------------------------------------------------------
# Tests 12-17: Forbidden content families fail closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("forbidden_term", [
    "buy now",
    "sell immediately",
    "place an order",
    "execute a trade",
    "trading signal",
])
def test_forbidden_trade_order_execution_variants_fail_closed(forbidden_term):
    result = build_artifact(artifact_id=forbidden_term, handoff_result=_valid_handoff_result())
    assert result.is_valid is False
    assert result.artifact == {}


@pytest.mark.parametrize("forbidden_term", [
    "expected return 0.5",
    "positive edge identified",
    "alpha signal",
    "fair value 0.6",
    "tradable market",
    "tradability confirmed",
])
def test_forbidden_return_edge_tradability_variants_fail_closed(forbidden_term):
    result = build_artifact(artifact_id=forbidden_term, handoff_result=_valid_handoff_result())
    assert result.is_valid is False
    assert result.artifact == {}


@pytest.mark.parametrize("forbidden_term", [
    "live ready status",
    "paper ready for deployment",
    "deployment ready confirmation",
])
def test_forbidden_paper_live_readiness_variants_fail_closed(forbidden_term):
    result = build_artifact(artifact_id=forbidden_term, handoff_result=_valid_handoff_result())
    assert result.is_valid is False
    assert result.artifact == {}


@pytest.mark.parametrize("forbidden_term", [
    "approve pr now",
    "merge ready",
])
def test_forbidden_pr_approval_merge_ready_variants_fail_closed(forbidden_term):
    result = build_artifact(artifact_id=forbidden_term, handoff_result=_valid_handoff_result())
    assert result.is_valid is False
    assert result.artifact == {}


@pytest.mark.parametrize("forbidden_term", [
    "store credential here",
    "my private key is",
    "api key value",
    "secret passphrase",
    "wallet address",
])
def test_forbidden_credential_private_key_variants_fail_closed(forbidden_term):
    result = build_artifact(artifact_id=forbidden_term, handoff_result=_valid_handoff_result())
    assert result.is_valid is False
    assert result.artifact == {}


@pytest.mark.parametrize("forbidden_term", [
    "provider model call",
    "prompt execution run",
    "prompt runner start",
    "hermes runtime activate",
    "scheduler job",
    "bot loop start",
    "daemon process",
    "network poller",
])
def test_forbidden_runtime_provider_prompt_variants_fail_closed(forbidden_term):
    result = build_artifact(artifact_id=forbidden_term, handoff_result=_valid_handoff_result())
    assert result.is_valid is False
    assert result.artifact == {}


# ---------------------------------------------------------------------------
# Test 18: Unsafe caller text is not echoed in errors, warnings, or artifact
# ---------------------------------------------------------------------------


def test_unsafe_caller_text_not_echoed():
    unsafe_id = "BUY_SIGNAL_EXECUTE_NOW"
    result = build_artifact(artifact_id=unsafe_id, handoff_result=_valid_handoff_result())
    assert result.is_valid is False
    assert result.artifact == {}
    for err in result.errors:
        assert unsafe_id not in err
        assert "BUY" not in err.upper() or err.startswith("FORBIDDEN") or err.startswith("INVALID")
    for warn in result.warnings:
        assert unsafe_id not in warn


# ---------------------------------------------------------------------------
# Test 19: Raw/free-form nested mapping keys in handoff fail closed
# ---------------------------------------------------------------------------


def test_raw_metadata_key_in_handoff_fails_closed():
    data = _valid_handoff_data()
    data["evidence_and_provenance"]["metadata"] = {"some": "data"}
    handoff = build_handoff(data)
    # WP106 itself will reject this, so handoff is invalid
    result = build_artifact(artifact_id="artifact-001", handoff_result=handoff)
    assert result.is_valid is False
    assert result.artifact == {}


# ---------------------------------------------------------------------------
# Test 20: Output ordering is deterministic
# ---------------------------------------------------------------------------


def test_output_is_deterministic():
    r1 = _valid_artifact_result()
    r2 = _valid_artifact_result()
    assert r1.artifact == r2.artifact
    assert list(r1.artifact.keys()) == list(r2.artifact.keys())


# ---------------------------------------------------------------------------
# Test 21: Result dataclass is frozen
# ---------------------------------------------------------------------------


def test_result_dataclass_is_frozen():
    result = _valid_artifact_result()
    assert result.is_valid is True
    with pytest.raises((AttributeError, TypeError)):
        result.is_valid = False  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        result.artifact = {}  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Test 22: Module imports only stdlib and approved WP106 internal module
# ---------------------------------------------------------------------------


def test_module_imports_only_stdlib_and_approved_wp106():
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    allowed_internal = {
        "src.data_layer.hermes_candidate_review_operator_handoff",
    }
    stdlib_modules = {
        "from __future__",
        "__future__",
        "dataclasses",
        "typing",
        "collections",
        "collections.abc",
        "math",
        "re",
        "os",
        "sys",
        "pathlib",
        "importlib",
        "functools",
        "itertools",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod and not any(mod == s or mod.startswith(s + ".") for s in stdlib_modules):
                    assert mod in allowed_internal, (
                        f"Forbidden import in WP108 module: {mod}"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in (
                        "requests", "httpx", "aiohttp", "click", "argparse", "typer",
                        "flask", "fastapi", "boto3", "paramiko",
                    ), f"Forbidden top-level import: {alias.name}"


# ---------------------------------------------------------------------------
# Test 23: Module has no file/network/subprocess/CLI imports or behavior
# ---------------------------------------------------------------------------


_FORBIDDEN_IMPORTS_IN_MODULE = (
    "requests", "httpx", "aiohttp", "websocket",
    "argparse", "click", "typer",
    "subprocess", "socket", "urllib.request",
)

_FORBIDDEN_BUILTINS_IN_MODULE = ("open(",)


def test_module_has_no_forbidden_io_or_cli_imports():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in _FORBIDDEN_IMPORTS_IN_MODULE:
        assert f"import {forbidden}" not in source, f"Forbidden import: {forbidden}"
    for forbidden in _FORBIDDEN_BUILTINS_IN_MODULE:
        assert forbidden not in source, f"Forbidden builtin call: {forbidden}"


# ---------------------------------------------------------------------------
# Test 24: Module has no os/pathlib/open/write/read/socket/http usage
# ---------------------------------------------------------------------------


_FORBIDDEN_PATTERNS = (
    "os.path",
    "os.write",
    "os.open",
    "pathlib.Path",
    ".write(",
    ".read(",
    "socket.socket",
    "http.client",
    "urllib.request.urlopen",
    "subprocess.run",
    "subprocess.Popen",
)


def test_module_has_no_filesystem_or_network_patterns():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for pattern in _FORBIDDEN_PATTERNS:
        assert pattern not in source, f"Forbidden pattern in module: {pattern}"


# ---------------------------------------------------------------------------
# Test 25: No artifact writer, no filesystem path argument, no CLI surface
# ---------------------------------------------------------------------------


def test_no_artifact_writer_no_path_arg_no_cli():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "output_path" not in source
    assert "file_path" not in source
    assert "write_artifact" not in source
    assert "argparse" not in source
    assert "click" not in source
    assert "if __name__" not in source or "__main__" not in source


def test_function_signature_has_no_path_parameter():
    sig = inspect.signature(build_artifact)
    param_names = list(sig.parameters.keys())
    assert "output_path" not in param_names
    assert "file_path" not in param_names
    assert "path" not in param_names


# ---------------------------------------------------------------------------
# Test 26: Each allowed WP106 decision label produces a valid artifact
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", sorted(_wp106.ALLOWED_HANDOFF_DECISION_LABELS))
def test_each_allowed_decision_label_produces_valid_artifact(label):
    data = _valid_handoff_data(decision_label=label)
    if label != "ACCEPT_FOR_MANUAL_RESEARCH_REVIEW":
        data["source_review_checklist"]["source_references_present"] = False
    handoff = build_handoff(data)
    result = build_artifact(artifact_id="artifact-001", handoff_result=handoff)
    assert result.is_valid is True
    assert result.artifact["manual_review_summary"]["decision_label"] == label


# ---------------------------------------------------------------------------
# Test 27: Empty artifact_id fails closed
# ---------------------------------------------------------------------------


def test_empty_artifact_id_fails_closed():
    for bad_id in ("", "   ", None):
        if bad_id is None:
            result = build_artifact(artifact_id=None, handoff_result=_valid_handoff_result())  # type: ignore[arg-type]
        else:
            result = build_artifact(artifact_id=bad_id, handoff_result=_valid_handoff_result())
        assert result.is_valid is False
        assert result.artifact == {}


# ---------------------------------------------------------------------------
# Test 28: chain_stage_summary contains all 6 expected stages
# ---------------------------------------------------------------------------


def test_chain_stage_summary_contains_all_stages():
    result = _valid_artifact_result()
    stages = result.artifact["chain_stage_summary"]["stages"]
    assert result.artifact["chain_stage_summary"]["stage_count"] == 6
    assert len(stages) == 6
    # All stages are builder-controlled neutral codes
    for stage in stages:
        assert isinstance(stage, str)
        assert stage.startswith("WP10")


# ---------------------------------------------------------------------------
# Test 29: forbidden_scope_notice is present and non-empty string
# ---------------------------------------------------------------------------


def test_forbidden_scope_notice_is_present_and_non_empty():
    result = _valid_artifact_result()
    notice = result.artifact["forbidden_scope_notice"]
    assert isinstance(notice, str)
    assert len(notice) > 50
    assert "ADVISORY_ONLY" in notice
    assert "human review" in notice.lower()


# ---------------------------------------------------------------------------
# Test 30: safety_flags group has exactly the 13 WP107 required flags
# ---------------------------------------------------------------------------


def test_artifact_safety_flags_count_and_keys():
    result = _valid_artifact_result()
    flags = result.artifact["safety_flags"]
    assert set(flags.keys()) == set(REQUIRED_FLAGS)
    assert len(flags) == 13
    for flag in REQUIRED_FLAGS:
        assert flags[flag] is True


# ---------------------------------------------------------------------------
# Test 31: in_memory_only flag is in artifact_identity, not safety_flags
# ---------------------------------------------------------------------------


def test_in_memory_only_in_artifact_identity_not_safety_flags():
    result = _valid_artifact_result()
    assert result.artifact["artifact_identity"]["in_memory_only"] is True
    assert "in_memory_only" not in result.artifact["safety_flags"]


# ---------------------------------------------------------------------------
# Test 32: human_decision_record_summary does not include raw rationale text
# ---------------------------------------------------------------------------


def test_human_decision_record_summary_no_raw_rationale():
    result = _valid_artifact_result()
    hdr = result.artifact["human_decision_record_summary"]
    assert "rationale" not in hdr or isinstance(hdr.get("rationale"), int)
    assert "rationale_length_chars" in hdr
    assert isinstance(hdr["rationale_length_chars"], int)
    assert hdr["rationale_length_chars"] >= 0


# ---------------------------------------------------------------------------
# Test 33: Status entry exists (WP108.md)
# ---------------------------------------------------------------------------


def test_wp108_status_entry_exists():
    path = ROOT / "docs" / "status_entries" / "WP108.md"
    assert path.is_file(), "docs/status_entries/WP108.md must exist"


# ---------------------------------------------------------------------------
# Test 34: Status entry does not contain stale wording
# ---------------------------------------------------------------------------


def test_wp108_status_entry_no_stale_wording():
    import re
    path = ROOT / "docs" / "status_entries" / "WP108.md"
    text = path.read_text(encoding="utf-8")
    stale_phrases = (
        "WP108 on branch",
        "WP108 active branch",
        "Merge commit: TBD after merge",
        "PR: TBD",
        "count depends",
        "TBD after merge",
        "LOCAL_DRAFT_VERIFIED",
    )
    for phrase in stale_phrases:
        assert phrase not in text, f"Stale wording in WP108.md: {phrase!r}"
    fixed_sha = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_sha.search(text) is None


# ---------------------------------------------------------------------------
# Test 35: Module source confirms no forbidden boundary violations
# ---------------------------------------------------------------------------


def test_module_source_no_forbidden_io_network_cli():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for token in ("import requests", "import httpx", "import aiohttp",
                  "import click", "import argparse", "import typer",
                  "import subprocess", "open(", "Path.write",
                  ".write_text(", ".write_bytes("):
        assert token not in source, f"Forbidden token in module source: {token!r}"
