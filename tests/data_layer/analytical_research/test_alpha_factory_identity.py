"""WP175N deterministic identity, fingerprint, and architecture-isolation tests."""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import pathlib

import pytest

from src.data_layer.analytical_research import alpha_factory as af
from tests.data_layer.analytical_research.test_alpha_factory_records import (
    candidate_input,
    episode_input,
    family_input,
    source_input,
)

# ── Independent identity oracle (does NOT call production _semantic_preimage/_digest) ──
_KIND_PREFIX_ID = {
    af.ResearchSourceReference: ("research_source_reference", "alphasource:sha256:", "source_reference_id"),
    af.OpportunityCandidate: ("opportunity_candidate", "alphacandidate:sha256:", "candidate_id"),
    af.HypothesisFamily: ("hypothesis_family", "alphafamily:sha256:", "hypothesis_family_id"),
    af.ResearchEpisode: ("research_episode", "alphaepisode:sha256:", "research_episode_id"),
}


def independent_id(record, *, omit_authority_flags: bool = False) -> str:
    kind, prefix, id_field = _KIND_PREFIX_ID[type(record)]
    flags = {"advisory_only", "no_execution_authority", "no_strategy_authority", "no_qualification_authority"}
    preimage = {}
    for field in dataclasses.fields(record):
        if field.name == id_field:
            continue
        if omit_authority_flags and field.name in flags:
            continue
        value = getattr(record, field.name)
        preimage[field.name] = list(value) if isinstance(value, tuple) else value
    wrapped = {f"{kind}.identity_preimage": preimage}
    raw = json.dumps(wrapped, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return prefix + hashlib.sha256(raw).hexdigest()


def _one_of_each():
    src = af.build_research_source_reference(source_input()).record
    cand = af.build_opportunity_candidate(candidate_input()).record
    fam = af.build_hypothesis_family(family_input()).record
    ep = af.build_research_episode(episode_input()).record
    return src, cand, fam, ep

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
ALPHA_SRC = REPO_ROOT / "src" / "data_layer" / "analytical_research" / "alpha_factory.py"
ALPHA_REGISTRY_SRC = REPO_ROOT / "src" / "data_layer" / "analytical_research" / "alpha_factory_registry.py"


# ── R004 novelty semantic duplicate ──────────────────────────────────────────
def test_prose_variants_share_novelty_fingerprint():
    a = af.build_opportunity_candidate(candidate_input(title="A", thesis="one", research_question="q1?"))
    b = af.build_opportunity_candidate(candidate_input(title="B totally different", thesis="two", research_question="q2?"))
    assert a.record.novelty_fingerprint == b.record.novelty_fingerprint
    # Prose changes still produce distinct immutable records.
    assert a.record.candidate_id != b.record.candidate_id


def test_novelty_fingerprint_excludes_prose():
    base = af.build_opportunity_candidate(candidate_input())
    changed = af.build_opportunity_candidate(candidate_input(mechanism_hint="a very different hint"))
    assert base.record.novelty_fingerprint == changed.record.novelty_fingerprint


def test_novelty_fingerprint_changes_with_structured_dimensions():
    base = af.build_opportunity_candidate(candidate_input())
    changed = af.build_opportunity_candidate(
        candidate_input(
            novelty_dimensions={
                "subject_keys": ["nfl", "weather"],
                "scope_key": "nfl-regular-2026",
                "mechanism_key": "different-mechanism",
            }
        )
    )
    assert base.record.novelty_fingerprint != changed.record.novelty_fingerprint


def test_novelty_fingerprint_prefix():
    assert af.build_opportunity_candidate(candidate_input()).record.novelty_fingerprint.startswith(
        "alphanovelty:sha256:"
    )


# ── R005 family mechanism duplicate ──────────────────────────────────────────
def test_producer_and_prose_do_not_change_mechanism_fingerprint():
    a = af.build_hypothesis_family(family_input(family_name="Name A", falsifiable_theme="theme A"))
    b = af.build_hypothesis_family(family_input(family_name="Name B", falsifiable_theme="theme B"))
    assert a.record.mechanism_fingerprint == b.record.mechanism_fingerprint


def test_mechanism_fingerprint_changes_with_dimensions():
    a = af.build_hypothesis_family(family_input())
    b = af.build_hypothesis_family(family_input(mechanism_dimensions={"driver": "humidity"}))
    assert a.record.mechanism_fingerprint != b.record.mechanism_fingerprint


def test_mechanism_fingerprint_prefix():
    assert af.build_hypothesis_family(family_input()).record.mechanism_fingerprint.startswith(
        "alphamechanism:sha256:"
    )


# ── R015 canonical JSON key-order independence ───────────────────────────────
def test_mapping_key_order_does_not_change_identity():
    a = af.build_hypothesis_family(family_input(mechanism_dimensions={"a": 1, "b": 2}))
    b = af.build_hypothesis_family(family_input(mechanism_dimensions={"b": 2, "a": 1}))
    assert a.record.mechanism_fingerprint == b.record.mechanism_fingerprint
    assert a.record.hypothesis_family_id == b.record.hypothesis_family_id
    assert a.record.mechanism_dimensions_json == b.record.mechanism_dimensions_json


# ── R016 identity excludes environment ───────────────────────────────────────
def test_identity_is_pure_content_no_environment():
    # No timestamp-of-write, path, pid, host, or session enters identity: repeated
    # construction in the same process yields the identical id.
    ids = {af.build_research_source_reference(source_input()).record.source_reference_id for _ in range(5)}
    assert len(ids) == 1


def test_authority_flags_included_in_identity_and_required_true():
    # Finding A: the record-ID preimage is the complete logical record except its own
    # ID, so the advisory/no-authority booleans DO participate in identity.
    for record in _one_of_each():
        assert record.advisory_only is True
        # Independent oracle including flags matches; omitting them does not.
        kind, prefix, id_field = _KIND_PREFIX_ID[type(record)]
        assert getattr(record, id_field) == independent_id(record)
        assert getattr(record, id_field) != independent_id(record, omit_authority_flags=True)


# ── I01 independent identity oracle for all four record types ─────────────────
def test_independent_identity_oracle_all_four_records():
    for record in _one_of_each():
        _kind, _prefix, id_field = _KIND_PREFIX_ID[type(record)]
        assert getattr(record, id_field) == independent_id(record)


# ── I03 round-trip mapping equality for all four records ──────────────────────
def test_record_to_from_mapping_roundtrip_all_four():
    for record in _one_of_each():
        mapping = af.record_to_mapping(record)
        rebuilt = af.record_from_mapping(type(record), mapping)
        assert rebuilt == record


# ── R017 Alpha / WP170 type separation ───────────────────────────────────────
def test_alpha_types_are_not_wp170_types():
    from src.data_layer.analytical_research import experiment_os as wp170

    assert af.HypothesisFamily is not wp170.ExperimentFamily
    assert not hasattr(af, "AlphaHypothesis")
    assert not hasattr(af, "ExperimentFamily")
    assert not hasattr(af, "PreregisteredExperiment")


# ── R018 no direct Hermes coupling / R019 no network (AST) ───────────────────
def _imported_modules(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
    return modules


@pytest.mark.parametrize("path", [ALPHA_SRC, ALPHA_REGISTRY_SRC])
def test_no_hermes_or_research_runtime_import(path):
    for module in _imported_modules(path):
        assert "hermes" not in module.lower()
        assert "research_runtime" not in module


@pytest.mark.parametrize("path", [ALPHA_SRC, ALPHA_REGISTRY_SRC])
def test_no_network_imports(path):
    forbidden = {"socket", "http", "http.client", "urllib.request", "requests", "ssl", "ftplib", "asyncio"}
    modules = _imported_modules(path)
    assert modules & forbidden == set(), modules & forbidden
    # urllib.parse (URL structural validation only) is permitted; urllib.request is not.
    assert "urllib.request" not in modules


# ── R020/R021/R022 no prioritization / scheduler / qualification ─────────────
@pytest.mark.parametrize("path", [ALPHA_SRC, ALPHA_REGISTRY_SRC])
def test_no_prioritization_scheduler_or_qualification_surface(path):
    # Structural surfaces only: economic/authority *words* legitimately appear as
    # rejected-vocabulary constants (proving they are forbidden, not used); R013
    # covers that rejection. Here we assert no rank/score/schedule/qualify code path.
    text = path.read_text(encoding="utf-8").lower()
    for token in (
        "def rank", "def score", "def prioriti", "priority_queue", "def promote",
        "def qualify", "def preregister", "import threading", "import sched",
        "asyncio", "def schedule", "cron",
    ):
        assert token not in text, token
