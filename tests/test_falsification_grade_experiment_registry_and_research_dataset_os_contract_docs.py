"""WP170 contract, package-evidence, status, and successor-boundary guards."""

from __future__ import annotations

import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "falsification_grade_experiment_registry_and_research_dataset_os_contract.md"
STATUS = ROOT / "docs" / "project_status.md"
REPO_TRUTH = ROOT / "docs" / "repo_truth_index.md"
DEFERRED = ROOT / "docs" / "deferred_items_log.md"
ROADMAP = ROOT / "docs" / "long_term_bot_completion_roadmap.md"
ADOPTION = ROOT / "docs" / "adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in.md"
FRAGMENT = ROOT / "docs" / "status_entries" / "WP170.md"
PACKAGE = ROOT / "docs" / "wp_specs" / "WP170"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_wp169_merge_is_reconciled_and_wp170_is_current() -> None:
    """R001: exact predecessor merge truth and current WP are consistent."""
    status = _read(STATUS)
    repo_truth = _read(REPO_TRUTH)
    fragment = _read(FRAGMENT)
    current = next(line for line in status.splitlines() if line.startswith("- Current phase:"))
    merged = next(line for line in status.splitlines() if line.startswith("- Merged WPs:"))
    for text in (current, repo_truth, fragment):
        assert "WP169" in text
        assert "PR #170" in text or "WP169 PR: 170" in text
        assert "c4a09aeb33e4c271feb709622660e5e58a00b642" in text
        assert "17df81001171988e9ca49f92dc8fd170ecaa7103" in text
    assert "WP169" in merged
    assert "WP170" in current
    assert "current review target" in current
    assert "WP171_INTERACTIVE_OPERATOR_COCKPIT_SEPARATELY_GATED" in current


def test_contract_declares_exact_capability_identity_and_non_authority() -> None:
    contract = _read(CONTRACT)
    for token in (
        "FALSIFICATION_GRADE_EXPERIMENT_REGISTRY_AND_RESEARCH_DATASET_OS",
        "DatasetBinding",
        "FeatureDefinition",
        "LabelDefinition",
        "ResearchSample",
        "TemporalSplitManifest",
        "PreregisteredExperiment",
        "RunEvidenceReceipt",
        "datasetbinding:sha256:",
        "splitplan:sha256:",
        "runevidence:sha256:",
        "PURGE_LABEL_AVAILABILITY_AT_OR_AFTER_NEXT_BOUNDARY",
        "DECISION_TIME_HALF_OPEN",
        "OOS_REUSED_DIAGNOSTIC",
        "wp170-experiment-registry",
        "application_id=1464877424",
        "MAX_REGISTRY_RECORDS=4096",
        "MAX_APPEND_BATCH=256",
        "Canonical PIT authority unchanged: YES",
        "Paper-trading execution is NOT AUTHORIZED",
        "Live-trading execution is FORBIDDEN",
        "Merge authorized: NO",
    ):
        assert token in contract, token
    assert "TBD" not in contract
    assert "..." not in contract


def test_package_prompt_spec_and_certificate_are_hash_bound() -> None:
    prompt = (PACKAGE / "wp_prompt.txt").read_bytes()
    spec_raw = (PACKAGE / "wp_spec.json").read_bytes()
    spec = json.loads(spec_raw)
    certificate = json.loads((PACKAGE / "draftability_certificate.json").read_bytes())
    assert hashlib.sha256(prompt).hexdigest() == "66e428610f19219c5fd0592cbe5258052be57eff38f590f452d31a5349722ec4"
    assert hashlib.sha256(spec_raw).hexdigest() == "93caf676d890cf9cea0602ff07a65009cd1976a705d083ce6e60d1590005eeaa"
    assert spec["identity"]["wp_id"] == "WP170"
    assert spec["scope"]["max_changed_files"] == 26
    assert spec["scope"]["required_changed_files"] == spec["scope"]["allowed_changed_files"]
    assert certificate["wp_text_sha256"] == hashlib.sha256(prompt).hexdigest()
    assert certificate["wp_spec_sha256"] == hashlib.sha256(spec_raw).hexdigest()
    assert certificate["result"] == "PASS"
    assert certificate["implementability_simulation"] == "PASS"
    assert len(certificate["covered_lenses"]) == 12
    assert all(item["result"] == "PASS" for item in certificate["covered_lenses"])
    assert certificate["unresolved_decisions"] == []


def test_existing_research_priority_calibration_wallet_semantics_remain_non_signal() -> None:
    """R026: predecessor research semantics remain advisory and non-signal."""
    contract = _read(CONTRACT)
    for term in (
        "priority",
        "calibration",
        "relationship",
        "resolution",
        "label",
        "wallet",
        "advisory non-signal inputs",
    ):
        assert term in contract, term
    for prohibited_claim in (
        "research records are trading signals",
        "automatic trade recommendation",
        "authorizes live trading",
    ):
        assert prohibited_claim not in contract.lower()


def test_contract_status_repo_truth_deferred_and_roadmaps_are_consistent() -> None:
    """R027: every canonical evidence surface agrees on scope and boundaries."""
    contract = _read(CONTRACT)
    status = _read(STATUS)
    repo_truth = _read(REPO_TRUTH)
    deferred = _read(DEFERRED)
    roadmap = _read(ROADMAP)
    adoption = _read(ADOPTION)
    fragment = _read(FRAGMENT)
    for text in (contract, status, repo_truth, fragment):
        assert "WP170" in text
        assert "26" in text
        assert "WP171" in text
    assert "RESOLVED_BOUNDED_WP170_FALSIFICATION_GRADE_EXPERIMENT_OS" in deferred
    for item in ("WP167-D005", "WP168-D002", "WP169-D002"):
        assert item in deferred
    assert "WP170 — Falsification-Grade Experiment Registry & Research Dataset OS" in roadmap
    assert "(current review target)" in roadmap
    assert "WP171 — Interactive Operator Cockpit" in roadmap
    assert "WP170 adds no direct or transitive runtime dependency" in adoption
    assert "New direct runtime dependency: NONE" in status
    assert "Product/runtime network calls: 0" in status
    assert "WP171" in fragment and "WP178" in fragment
    assert "separately gated and unimplemented" in fragment
