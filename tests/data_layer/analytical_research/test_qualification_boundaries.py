"""S10-QUAL-01 authority, import, side-effect, export and scope boundaries."""

from __future__ import annotations

import ast
import builtins
import dataclasses
import inspect
import json
import random
import socket
import subprocess
import time
from pathlib import Path

import pytest

import src.data_layer.analytical_research as ar
from src.data_layer.analytical_research import qualification as q
from tests.data_layer.analytical_research.test_qualification import (
    Lineage,
    af1_pass,
    binary_input,
    feature_plan,
    fresh,
    label_plan,
    manifest,
    mk_candidate,
    mk_episode,
    mk_family,
    mk_source,
    snapshot_of,
)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "src" / "data_layer" / "analytical_research" / "qualification.py"
SPEC = ROOT / "docs" / "wp_specs" / "S10-QUAL-01" / "wp_spec.json"

EXPECTED_EXPORTS = (
    "QUALIFICATION_SCHEMA_VERSION",
    "QUALIFICATION_CANDIDATE_SCHEMA_ID",
    "QUALIFICATION_STATUSES",
    "QUALIFICATION_MODES",
    "WALLET_DEPENDENCY_MODES",
    "QUALIFICATION_FEATURE_SOURCE_CLASSES",
    "QUALIFICATION_PROPER_SCORE_IDS",
    "EXECUTION_FEASIBILITY_CLASSES",
    "EXECUTION_FEASIBILITY_STATES",
    "QUALIFICATION_ERROR_CODES",
    "QualificationCandidate",
    "QualificationControlResult",
    "build_qualification_candidate",
    "validate_qualification_candidate",
    "qualification_candidate_to_mapping",
    "qualification_candidate_from_mapping",
)


@pytest.fixture
def lineage(tmp_path):
    path = fresh(tmp_path)
    source, candidate, family = mk_source(), mk_candidate(), mk_family()
    episode = mk_episode(candidate, family, source)
    return Lineage(path, source, candidate, family, episode,
                   snapshot_of(path, [source, candidate, family, episode]))


def _imports() -> set[str]:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.add("." * node.level + (node.module or ""))
    return found


# ── Q25 / Q26 no runtime surface ─────────────────────────────────────────────
def test_q25_imports_are_closed_to_local_offline_modules():
    assert _imports() == {
        "__future__", "dataclasses", "decimal", "hashlib", "json", "re", "typing",
        "..point_in_time_market_research.research_provenance",
        ".alpha_factory", ".alpha_factory_gate", ".alpha_factory_registry", ".experiment_os",
    }


def test_q25_q26_source_has_no_runtime_writer_clock_random_env_or_network_path():
    lowered = SOURCE.read_text(encoding="utf-8").lower()
    for token in (
        "open(", "write_text", "write_bytes", "sqlite3", "create table", ".now(", "utcnow",
        "time.time", "random.", "uuid", "os.environ", "getenv", "socket", "requests", "httpx",
        "urllib", "websocket", "subprocess", "hermes_controlled_runtime", "research_runtime",
        "wallet_intelligence", "paper_trading", "execution_gateway", "prefect", "firecrawl",
        "append_alpha_factory_records", "initialize_alpha_factory_registry",
        "load_and_verify_alpha_factory_registry", "build_preregistered_experiment",
        "build_feature_definition", "build_temporal_split_manifest", "experiment_registry",
    ):
        assert token not in lowered, token


def test_q25_builder_performs_no_side_effect(lineage, monkeypatch):
    receipt, manifests, value = af1_pass(), [manifest()], binary_input(lineage)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("side effect attempted")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(time, "time", forbidden)
    monkeypatch.setattr(random, "random", forbidden)
    result = q.build_qualification_candidate(lineage.snapshot, receipt, manifests, value)
    assert result.is_valid, result.error_codes
    assert q.validate_qualification_candidate(result.record).is_valid
    mapping = q.qualification_candidate_to_mapping(result.record)
    assert q.qualification_candidate_from_mapping(mapping).record == result.record


def test_q26_builder_signature_has_no_path_clock_seed_or_env_argument():
    assert list(inspect.signature(q.build_qualification_candidate).parameters) == [
        "alpha_registry_snapshot", "af1_gate_receipt", "provenance_manifests", "input_mapping",
    ]
    public = {name for name in dir(q) if not name.startswith("_") and callable(getattr(q, name))
              and getattr(getattr(q, name), "__module__", "") == q.__name__}
    assert public == {
        "QualificationCandidate", "QualificationControlResult", "build_qualification_candidate",
        "validate_qualification_candidate", "qualification_candidate_to_mapping",
        "qualification_candidate_from_mapping",
    }


# ── Q24 / Q27 record shape, exports and WP170 read-only posture ──────────────
def test_q24_record_and_result_fields_are_exact():
    assert [f.name for f in dataclasses.fields(q.QualificationCandidate)] == [
        "schema_id", "schema_version", "qualification_candidate_id", "candidate_version",
        "alpha_registry_head_entry_hash", "alpha_candidate_id", "hypothesis_family_id",
        "governing_research_episode_id", "af1_gate_receipt_id", "research_provenance_manifest_ids",
        "information_cutoff", "qualification_mode", "experiment_os_schema_version",
        "hypothesis_plan_json", "feature_plan_json", "label_plan_json", "dataset_split_plan_json",
        "sample_power_plan_json", "test_family_plan_json", "forecast_evaluation_plan_json",
        "execution_feasibility_plan_json", "wallet_dependency", "creation_provenance",
        "advisory_only", "human_review_required", "no_execution_authority",
        "no_strategy_authority", "no_qualification_authority",
    ]
    assert [f.name for f in dataclasses.fields(q.QualificationControlResult)] == [
        "is_valid", "status", "error_codes", "record", "advisory_only",
        "no_execution_authority", "no_strategy_authority", "no_qualification_authority",
    ]
    assert q.QualificationCandidate.__dataclass_params__.frozen
    assert q.QualificationControlResult.__dataclass_params__.frozen


def test_q24_closed_vocabularies_are_frozen():
    assert q.QUALIFICATION_SCHEMA_VERSION == "1.0.0"
    assert q.QUALIFICATION_CANDIDATE_SCHEMA_ID == "polymarket-qualification-candidate"
    assert q.QUALIFICATION_MODES == ("BINARY_PROBABILITY", "GENERIC_METRIC")
    assert q.WALLET_DEPENDENCY_MODES == ("NON_WALLET", "WALLET_DEPENDENT")
    assert q.QUALIFICATION_FEATURE_SOURCE_CLASSES == ("PUBLIC_NON_MARKET", "MARKET_PIT", "TIME_ONLY")
    assert q.QUALIFICATION_PROPER_SCORE_IDS == ("BRIER_SCORE", "LOG_LOSS")
    assert q.EXECUTION_FEASIBILITY_CLASSES == (
        "FEES", "RESOLUTION_RULES", "TICK_SIZE_MIN_ORDER", "SPREAD_DEPTH", "LATENCY", "PARTIAL_FILL",
    )
    assert q.EXECUTION_FEASIBILITY_STATES == ("AVAILABLE", "PARTIAL", "MISSING", "NOT_APPLICABLE")
    assert q.QUALIFICATION_ERROR_CODES[0] == "SCHEMA_UNSUPPORTED"
    assert q.QUALIFICATION_ERROR_CODES[-1] == "INTERNAL_VALIDATION_FAILED"
    assert len(q.QUALIFICATION_ERROR_CODES) == len(set(q.QUALIFICATION_ERROR_CODES)) == 25
    # No qualification decision, registry or wallet-gate vocabulary exists here.
    lowered = SOURCE.read_text(encoding="utf-8").lower()
    for token in ("qual_pass", "qualification_pass", "qualified", "walletgate:", "wallet_gate_receipt"):
        assert token not in lowered, token


def test_q27_package_exports_exact_qualification_surface():
    exported = [name for name in ar.__all__ if name in set(dir(q)) and getattr(ar, name) is getattr(q, name)
                and name in EXPECTED_EXPORTS]
    assert sorted(exported) == sorted(EXPECTED_EXPORTS)
    assert len(ar.__all__) == len(set(ar.__all__))
    for name in EXPECTED_EXPORTS:
        assert getattr(ar, name) is getattr(q, name)
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    defined = {node.name for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))}
    defined |= {target.id for node in tree.body if isinstance(node, ast.Assign)
                for target in node.targets if isinstance(target, ast.Name)}
    assert {name for name in ar.__all__ if name in defined} == set(EXPECTED_EXPORTS)


def test_q27_wp170_is_consumed_read_only():
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    wp170 = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module == "experiment_os"]
    assert len(wp170) == 1
    assert sorted(alias.name for alias in wp170[0].names) == [
        "CORRECTION_POLICIES", "EXPERIMENT_OS_SCHEMA_VERSION", "GROUP_POLICIES", "METRIC_DIRECTIONS",
    ]
    assert "SAFE_FEATURE_SOURCE_DEPENDENCIES" not in source
    assert "feature_definition_ids" not in source


# ── Q28 no raw / path / exception echo ───────────────────────────────────────
SENTINEL = "C:\\Users\\secret\\wallet-passphrase.txt"


def _flat(result) -> str:
    return repr(result) + json.dumps(list(result.error_codes))


def test_q28_rejections_expose_only_closed_codes(lineage):
    cases = [
        binary_input(lineage, label_plan=label_plan(label_ref=SENTINEL)),
        binary_input(lineage, feature_plan=feature_plan(feature_refs=[SENTINEL])),
        binary_input(lineage, creation_provenance=SENTINEL + " " * 2),
        binary_input(lineage, **{SENTINEL: 1}),
        {SENTINEL: object()},
    ]
    for value in cases:
        result = q.build_qualification_candidate(lineage.snapshot, af1_pass(), [manifest()], value)
        assert not result.is_valid and result.record is None
        assert set(result.error_codes) <= set(q.QUALIFICATION_ERROR_CODES)
        assert "secret" not in _flat(result).lower()


def test_q28_unexpected_exception_is_internal_failure_without_echo(lineage):
    class Hostile(dict):
        def keys(self):
            raise RuntimeError(SENTINEL)

    result = q.build_qualification_candidate(lineage.snapshot, af1_pass(), [manifest()], Hostile(a=1))
    assert result.error_codes == ("INTERNAL_VALIDATION_FAILED",)
    assert "secret" not in _flat(result).lower()
    with pytest.raises(ValueError) as caught:
        q.qualification_candidate_to_mapping(object())
    assert caught.value.args == ("FIELD_TYPE_INVALID",)


# ── Q30 exact scope ──────────────────────────────────────────────────────────
def test_q30_exact_fifteen_path_scope():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    required = spec["scope"]["required_changed_files"]
    allowed = spec["scope"]["allowed_changed_files"]
    assert required == allowed
    assert len(required) == len(set(required)) == spec["scope"]["max_changed_files"] == 15
    assert spec["scope"]["exact_scope_required"] is True
    for path in required:
        assert (ROOT / path).is_file(), path
    for forbidden in (
        "src/data_layer/analytical_research/experiment_os.py",
        "src/data_layer/analytical_research/experiment_registry.py",
        "src/data_layer/analytical_research/alpha_factory.py",
        "src/data_layer/analytical_research/alpha_factory_registry.py",
        "src/data_layer/analytical_research/alpha_factory_gate.py",
    ):
        assert forbidden not in required
    assert [p for p in required if p.startswith("src/")] == [
        "src/data_layer/analytical_research/__init__.py",
        "src/data_layer/analytical_research/qualification.py",
    ]
