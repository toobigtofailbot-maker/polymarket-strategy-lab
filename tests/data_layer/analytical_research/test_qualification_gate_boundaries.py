"""S10-GATE-QUAL-01 authority, import, side-effect, export, status and scope boundaries."""

from __future__ import annotations

import ast
import builtins
import dataclasses
import inspect
import json
import os
import random
import socket
import subprocess
import time
from pathlib import Path

import pytest

import src.data_layer.analytical_research as ar
from src.data_layer.analytical_research import qualification as q
from src.data_layer.analytical_research import qualification_gate as g
from tests.data_layer.analytical_research.test_qualification_gate import (
    af1_pass,
    candidate_for,
    ready_manifest,
)
from tests.data_layer.analytical_research.test_qualification_gate import (
    lineage,  # noqa: F401  (pytest fixture)
)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "src" / "data_layer" / "analytical_research" / "qualification_gate.py"
SPEC = ROOT / "docs" / "wp_specs" / "S10-GATE-QUAL-01" / "wp_spec.json"
FRAGMENT = ROOT / "docs" / "status_entries" / "S10-GATE-QUAL-01.md"
CONTRACT = ROOT / "docs" / "qualification_gate_contract.md"
PREDECESSOR_HEAD = "652a2181926ac6f92f72d0013af99ec5e24ba892"
PREDECESSOR_MERGE = "b5cfb9846ff78af2d1a260843d5f2f1a67639305"

EXPECTED_EXPORTS = (
    "QUALIFICATION_GATE_SCHEMA_VERSION",
    "QUALIFICATION_GATE_RECEIPT_SCHEMA_ID",
    "QUALIFICATION_GATE_POLICY_VERSION",
    "QUALIFICATION_GATE_STATUSES",
    "QUALIFICATION_GATE_DIMENSIONS",
    "QUALIFICATION_GATE_DIMENSION_STATUSES",
    "QUALIFICATION_GATE_DISPOSITIONS",
    "QUALIFICATION_GATE_ERROR_CODES",
    "QualificationGateReceipt",
    "QualificationGateControlResult",
    "evaluate_qualification_gate",
    "validate_qualification_gate_receipt",
    "qualification_gate_receipt_to_mapping",
    "qualification_gate_receipt_from_mapping",
)
QUAL_01_EXPORTS = (
    "QUALIFICATION_SCHEMA_VERSION", "QUALIFICATION_CANDIDATE_SCHEMA_ID", "QUALIFICATION_STATUSES",
    "QUALIFICATION_MODES", "WALLET_DEPENDENCY_MODES", "QUALIFICATION_FEATURE_SOURCE_CLASSES",
    "QUALIFICATION_PROPER_SCORE_IDS", "EXECUTION_FEASIBILITY_CLASSES", "EXECUTION_FEASIBILITY_STATES",
    "QUALIFICATION_ERROR_CODES", "QualificationCandidate", "QualificationControlResult",
    "build_qualification_candidate", "validate_qualification_candidate",
    "qualification_candidate_to_mapping", "qualification_candidate_from_mapping",
)


def _imports() -> set[str]:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.add("." * node.level + (node.module or ""))
    return found


# ── Q28 / Q29 no runtime surface ─────────────────────────────────────────────
def test_q28_imports_are_closed_to_local_offline_modules():
    assert _imports() == {
        "__future__", "dataclasses", "decimal", "hashlib", "json", "re", "typing",
        "..point_in_time_market_research.research_provenance", ".",
        ".alpha_factory", ".alpha_factory_gate", ".experiment_os", ".qualification",
    }
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    relative_module = [node for node in ast.walk(tree)
                       if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module is None]
    assert [alias.name for node in relative_module for alias in node.names] == ["alpha_factory_registry"]


def test_q28_q29_source_has_no_runtime_writer_clock_random_env_or_network_path():
    lowered = SOURCE.read_text(encoding="utf-8").lower()
    for token in (
        "open(", "write_text", "write_bytes", "sqlite3", "create table", ".now(", "utcnow",
        "time.time", "random.", "uuid", "os.environ", "getenv", "socket", "requests", "httpx",
        "urllib", "websocket", "subprocess", "hermes_controlled_runtime", "research_runtime",
        "wallet_intelligence", "paper_trading", "execution_gateway", "prefect", "firecrawl",
        "append_alpha_factory_records", "initialize_alpha_factory_registry",
        "load_and_verify_alpha_factory_registry", "build_preregistered_experiment",
        "build_feature_definition", "build_temporal_split_manifest", "experiment_registry",
        "build_qualification_candidate", "safe_feature_source_dependencies", "pnl", "slippage",
        "position_size", "expected_return", "place_order", "cancel_order",
    ):
        assert token not in lowered, token


def test_q29_evaluation_performs_no_side_effect(lineage, monkeypatch):
    candidate, receipt, manifests = candidate_for(lineage), af1_pass(), [ready_manifest()]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("side effect attempted")

    for target, name in ((builtins, "open"), (socket, "socket"), (socket, "create_connection"),
                         (subprocess, "Popen"), (time, "time"), (random, "random"), (os, "getenv")):
        monkeypatch.setattr(target, name, forbidden)
    result = g.evaluate_qualification_gate(candidate, lineage.snapshot, receipt, manifests)
    assert result.is_valid, result.error_codes
    assert result.receipt.overall_disposition == "QUAL_PASS"
    mapping = g.qualification_gate_receipt_to_mapping(result.receipt)
    assert g.qualification_gate_receipt_from_mapping(mapping).receipt == result.receipt
    assert g.validate_qualification_gate_receipt(result.receipt).is_valid


def test_q29_signatures_have_no_path_clock_seed_or_env_argument():
    assert list(inspect.signature(g.evaluate_qualification_gate).parameters) == [
        "candidate", "alpha_registry_snapshot", "af1_gate_receipt", "provenance_manifests",
    ]
    public = {name for name in dir(g) if not name.startswith("_") and callable(getattr(g, name))
              and getattr(getattr(g, name), "__module__", "") == g.__name__}
    assert public == {
        "QualificationGateReceipt", "QualificationGateControlResult", "evaluate_qualification_gate",
        "validate_qualification_gate_receipt", "qualification_gate_receipt_to_mapping",
        "qualification_gate_receipt_from_mapping",
    }


# ── Q30 record shape, vocabularies, exports, read-only predecessors ──────────
def test_q30_receipt_and_result_fields_are_exact():
    assert [f.name for f in dataclasses.fields(g.QualificationGateReceipt)] == [
        "schema_id", "schema_version", "qualification_gate_receipt_id", "policy_version",
        "qualification_candidate_id", "candidate_version", "candidate_information_cutoff",
        "candidate_alpha_registry_head_entry_hash", "current_alpha_registry_head_entry_hash",
        "alpha_candidate_id", "hypothesis_family_id", "governing_research_episode_id",
        "af1_gate_receipt_id", "research_provenance_manifest_ids", "experiment_os_schema_version",
        "dimension_statuses", "overall_disposition", "wp170_entry_eligible",
        "successor_authorization_required", "no_strategy_authority", "no_paper_authority",
        "no_execution_authority", "no_live_authority", "no_gate_c_authority",
    ]
    assert [f.name for f in dataclasses.fields(g.QualificationGateControlResult)] == [
        "is_valid", "status", "error_codes", "receipt", "no_strategy_authority",
        "no_paper_authority", "no_execution_authority", "no_live_authority", "no_gate_c_authority",
    ]
    assert g.QualificationGateReceipt.__dataclass_params__.frozen
    assert g.QualificationGateControlResult.__dataclass_params__.frozen


def test_q30_closed_vocabularies_are_frozen():
    assert g.QUALIFICATION_GATE_SCHEMA_VERSION == "1.0.0"
    assert g.QUALIFICATION_GATE_RECEIPT_SCHEMA_ID == "polymarket-qualification-gate-receipt"
    assert g.QUALIFICATION_GATE_POLICY_VERSION == "qualification-gate-policy/1.0.0"
    assert g.QUALIFICATION_GATE_STATUSES == ("QUALIFICATION_GATE_VALID", "QUALIFICATION_GATE_REJECTED")
    assert g.QUALIFICATION_GATE_DIMENSIONS == (
        "PACKET_INTEGRITY", "CURRENT_RESEARCH_LINEAGE", "PREDECESSOR_EVIDENCE",
        "PIT_PROVENANCE_READINESS", "SAMPLE_POWER_READINESS", "WP170_CROSSING_READINESS",
        "EXECUTION_EVIDENCE_READINESS", "AUTHORITY_CONTAINMENT",
    )
    assert g.QUALIFICATION_GATE_DIMENSION_STATUSES == ("PASS", "FAIL", "INCONCLUSIVE")
    assert g.QUALIFICATION_GATE_DISPOSITIONS == ("QUAL_PASS", "QUAL_FAIL", "QUAL_INCONCLUSIVE")
    assert g.QUALIFICATION_GATE_ERROR_CODES == (
        "SCHEMA_UNSUPPORTED", "FIELD_TYPE_INVALID", "FIELD_VALUE_INVALID",
        "IDENTITY_DERIVATION_MISMATCH", "CANDIDATE_INVALID", "ALPHA_REGISTRY_INVALID",
        "ALPHA_ANCESTRY_INVALID", "AF1_RECEIPT_INVALID", "AF1_BINDING_INVALID",
        "PROVENANCE_INVALID", "PROVENANCE_BINDING_INVALID", "AUTHORITY_INVARIANT_INVALID",
        "LIMIT_EXCEEDED", "INTERNAL_VALIDATION_FAILED",
    )
    # The current AF1 receipt is predecessor evidence only, never a product constant.
    assert "281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2" not in SOURCE.read_text(
        encoding="utf-8")


def test_q30_package_exports_exact_gate_surface_and_qual_01_unchanged():
    assert len(ar.__all__) == len(set(ar.__all__))
    for name in EXPECTED_EXPORTS:
        assert name in ar.__all__ and getattr(ar, name) is getattr(g, name), name
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    defined = {node.name for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))}
    defined |= {target.id for node in tree.body if isinstance(node, ast.Assign)
                for target in node.targets if isinstance(target, ast.Name)}
    assert {name for name in ar.__all__ if name in defined} == set(EXPECTED_EXPORTS)
    for name in QUAL_01_EXPORTS:
        assert name in ar.__all__ and getattr(ar, name) is getattr(q, name), name
    assert list(inspect.signature(q.build_qualification_candidate).parameters) == [
        "alpha_registry_snapshot", "af1_gate_receipt", "provenance_manifests", "input_mapping",
    ]


def test_q30_wp170_and_qual_01_are_consumed_read_only():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    by_module = {node.module: sorted(alias.name for alias in node.names)
                 for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.level == 1}
    assert by_module["experiment_os"] == ["EXPERIMENT_OS_SCHEMA_VERSION"]
    assert by_module["qualification"] == ["QualificationCandidate", "validate_qualification_candidate"]
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    for frozen in ("src/data_layer/analytical_research/qualification.py",
                   "src/data_layer/analytical_research/experiment_os.py",
                   "src/data_layer/analytical_research/experiment_registry.py"):
        assert frozen not in spec["scope"]["allowed_changed_files"], frozen


# ── Q28 no raw / path / exception echo ───────────────────────────────────────
SENTINEL = "C:\\Users\\secret\\wallet-passphrase.txt"


def _flat(result) -> str:
    return repr(result) + json.dumps(list(result.error_codes))


def test_q28_rejections_expose_only_closed_codes(lineage):
    candidate = candidate_for(lineage)
    cases = [
        (SENTINEL, lineage.snapshot, af1_pass(), [ready_manifest()]),
        (candidate, {SENTINEL: 1}, af1_pass(), [ready_manifest()]),
        (candidate, lineage.snapshot, SENTINEL, [ready_manifest()]),
        (candidate, lineage.snapshot, af1_pass(), [SENTINEL]),
        (candidate, lineage.snapshot, af1_pass(), SENTINEL),
    ]
    for args in cases:
        result = g.evaluate_qualification_gate(*args)
        assert not result.is_valid and result.receipt is None
        assert set(result.error_codes) <= set(g.QUALIFICATION_GATE_ERROR_CODES)
        assert "secret" not in _flat(result).lower()
    forged = g.qualification_gate_receipt_from_mapping({SENTINEL: object()})
    assert forged.error_codes == ("FIELD_VALUE_INVALID",)
    assert "secret" not in _flat(forged).lower()


def test_q28_unexpected_exception_is_internal_failure_without_echo(lineage, monkeypatch):
    def hostile(*_args, **_kwargs):
        raise RuntimeError(SENTINEL)

    monkeypatch.setattr(g, "_admit_candidate", hostile)
    result = g.evaluate_qualification_gate(None, lineage.snapshot, af1_pass(), [ready_manifest()])
    assert result.error_codes == ("INTERNAL_VALIDATION_FAILED",) and result.receipt is None
    assert "secret" not in _flat(result).lower()


# ── Q31 docs / status truth ──────────────────────────────────────────────────
def test_q31_status_and_contract_record_predecessor_and_no_real_result():
    fragment = " ".join(FRAGMENT.read_text(encoding="utf-8").split())
    contract = " ".join(CONTRACT.read_text(encoding="utf-8").split())
    for text in (PREDECESSOR_HEAD, PREDECESSOR_MERGE, "PR #197", "REAL QUALIFICATION CANDIDATE EVALUATED: NO",
                 "REAL QUALIFICATION GATE RECEIPT PERSISTED: NO", "Merge authorized: NO"):
        assert text in fragment, text
    for text in ("QUAL_PASS", "QUAL_FAIL", "QUAL_INCONCLUSIVE", "synthetic", "NOT AUTHORIZED",
                 "Merge: NOT AUTHORIZED"):
        assert text in contract, text
    for stale in ("real candidate qualified: YES", "Merge authorized: YES", "Gate C: AUTHORIZED",
                  "WP170 experiment/OOS: STARTED"):
        assert stale not in fragment and stale not in contract, stale


# ── Q32 exact scope ──────────────────────────────────────────────────────────
def test_q32_exact_fifteen_path_scope():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    required = spec["scope"]["required_changed_files"]
    allowed = spec["scope"]["allowed_changed_files"]
    assert required == allowed
    assert len(required) == len(set(required)) == spec["scope"]["max_changed_files"] == 15
    assert spec["scope"]["exact_scope_required"] is True
    for path in required:
        assert (ROOT / path).is_file(), path
    assert [p for p in required if p.startswith("src/")] == [
        "src/data_layer/analytical_research/__init__.py",
        "src/data_layer/analytical_research/qualification_gate.py",
    ]
    assert spec["identity"]["required_predecessor"] == {
        "pr_number": 197, "head_sha": PREDECESSOR_HEAD, "merge_sha": PREDECESSOR_MERGE,
    }
    for key in ("network", "credentials", "scheduler", "hermes_runtime", "strategy", "paper",
                "execution", "live", "dependencies", "workflow_files"):
        assert spec["authority"][key] is False, key
    assert "merge" in spec["successor_boundary"]["forbidden_in_this_wp"]


@pytest.mark.parametrize("path", [
    "src/data_layer/analytical_research/qualification.py",
    "src/data_layer/analytical_research/experiment_os.py",
    "src/data_layer/analytical_research/experiment_registry.py",
])
def test_q32_frozen_predecessor_modules_are_out_of_scope(path):
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert path not in spec["scope"]["required_changed_files"]
