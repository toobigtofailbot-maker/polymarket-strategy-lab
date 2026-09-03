"""Focused WP158 append-only local manifest and dataset snapshot reference
contract documentation regression.

WP158 is a contract-only package: documentation, status, repo truth, deferred
registration, and this focused test. It adds no `src` implementation, no writer,
no reader, no persistence, no dependency, no workflow, and no local/generated
artifact.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess


# Independent, standard-library-only canonicalization + derivation oracle.
# This intentionally does NOT import any WP159 implementation (none exists); it
# recomputes derived IDs from the exact preimage mappings locked in the contract
# (Sections 7 and 9) so the doc's example self IDs are proven true, not merely
# prefix/length shaped.

_REFERENCE_PREIMAGE_KEYS = (
    "schema_id",
    "schema_version",
    "derivation_mode",
    "validated_batch_sha256",
    "ordinary_record_version_ids",
    "review_conflict_record_version_ids",
    "query_spec_sha256",
    "query_result_sha256",
    "cutoff_mode",
    "cutoff_time",
    "result_view",
    "query_engine_version",
    "validator_version",
    "parameter_set_id",
    "human_review_required",
    "advisory_only",
    "no_execution_authority",
)

_MANIFEST_PREIMAGE_KEYS = (
    "schema_id",
    "schema_version",
    "manifest_id",
    "sequence_number",
    "previous_manifest_entry_id",
    "entry_kind",
    "dataset_snapshot_reference_id",
    "supersedes_manifest_entry_id",
    "reference_state",
    "reason_code",
    "effective_time",
    "parameter_set_id",
    "human_review_required",
    "advisory_only",
    "no_execution_authority",
)


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _derive_reference_id(obj: dict) -> str:
    preimage = {k: obj[k] for k in _REFERENCE_PREIMAGE_KEYS}
    return "datasetref:sha256:" + hashlib.sha256(
        _canonical_json_bytes(preimage)
    ).hexdigest()


def _derive_manifest_entry_id(obj: dict) -> str:
    preimage = {k: obj[k] for k in _MANIFEST_PREIMAGE_KEYS}
    return "manifestentry:sha256:" + hashlib.sha256(
        _canonical_json_bytes(preimage)
    ).hexdigest()


def _is_reference(obj: dict) -> bool:
    return obj["schema_id"] == "point-in-time-dataset-snapshot-reference"


LOCKED_FAILURE_CATEGORIES = {
    "SCHEMA_UNSUPPORTED",
    "FIELD_MISSING",
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "ID_DERIVATION_MISMATCH",
    "REFERENCE_MODE_MISMATCH",
    "REVIEW_CONFLICT_AUTHORITY_FORBIDDEN",
    "MANIFEST_SEQUENCE_INVALID",
    "MANIFEST_PREVIOUS_ENTRY_UNKNOWN",
    "MANIFEST_CHAIN_MISMATCH",
    "MANIFEST_SUPERSEDES_INVALID",
    "MANIFEST_CYCLE",
    "MANIFEST_ID_COLLISION_OR_MISMATCH",
    "DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH",
    "SAFETY_POSTURE_INVALID",
}

REFERENCE_REQUIRED_FIELDS = {
    "schema_id",
    "schema_version",
    "dataset_snapshot_reference_id",
    "derivation_mode",
    "validated_batch_sha256",
    "ordinary_record_version_ids",
    "review_conflict_record_version_ids",
    "query_spec_sha256",
    "query_result_sha256",
    "cutoff_mode",
    "cutoff_time",
    "result_view",
    "query_engine_version",
    "validator_version",
    "parameter_set_id",
    "created_from_manifest_entry_id",
    "human_review_required",
    "advisory_only",
    "no_execution_authority",
}

MANIFEST_REQUIRED_FIELDS = {
    "schema_id",
    "schema_version",
    "manifest_entry_id",
    "manifest_id",
    "sequence_number",
    "previous_manifest_entry_id",
    "entry_kind",
    "dataset_snapshot_reference_id",
    "supersedes_manifest_entry_id",
    "reference_state",
    "reason_code",
    "effective_time",
    "parameter_set_id",
    "human_review_required",
    "advisory_only",
    "no_execution_authority",
}

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _json_examples() -> list[dict]:
    """Parse every ```json fenced block in the canonical doc."""
    blocks = re.findall(r"```json\n(.*?)\n```", _read(DOC), re.DOTALL)
    return [json.loads(block) for block in blocks]


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "append_only_local_manifest_and_dataset_snapshot_reference_contract.md"
STATUS = ROOT / "docs" / "status_entries" / "WP158.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"
DEFERRED = ROOT / "docs" / "deferred_items_log.md"

EXPECTED_CHANGED = {
    "docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md",
    "docs/deferred_items_log.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/status_entries/WP158.md",
    "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
    "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
    "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
    "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    "tests/test_project_status_docs.py",
}

# Functional WP160 implements the WP158 contract as a bounded in-memory
# validator. Its exact authorized changed-file scope (17 paths under explicit
# user authorization for the two additional package-export compatibility
# regressions) is checked here without weakening any dependency, workflow,
# fixture, or protected-path assertion.
WP160_AUTHORIZED_FILES = {
    "src/data_layer/point_in_time_market_research/manifest_reference.py",
    "src/data_layer/point_in_time_market_research/__init__.py",
    "tests/data_layer/point_in_time_market_research/test_manifest_reference.py",
    "tests/data_layer/point_in_time_market_research/test_as_of_query.py",
    "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
    "docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md",
    "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
    "tests/test_project_status_docs.py",
    "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
    "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    "tests/test_wallet_intelligence_architecture_contract_docs.py",
    "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
    "tests/test_human_review_label_workflow_docs.py",
    "docs/status_entries/WP160.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
}

WP161_AUTHORIZED_FILES = {
    "src/data_layer/point_in_time_market_research/manifest_store.py",
    "src/data_layer/point_in_time_market_research/__init__.py",
    "tests/data_layer/point_in_time_market_research/test_manifest_store.py",
    "tests/data_layer/point_in_time_market_research/test_as_of_query.py",
    "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
    "docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md",
    "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
    "tests/test_project_status_docs.py",
    "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
    "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    "tests/test_wallet_intelligence_architecture_contract_docs.py",
    "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
    "tests/test_human_review_label_workflow_docs.py",
    "docs/status_entries/WP161.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/deferred_items_log.md",
}

WP162_AUTHORIZED_FILES = {
    "src/data_layer/point_in_time_market_research/dataset_persistence_adapter.py",
    "src/data_layer/point_in_time_market_research/__init__.py",
    "tests/data_layer/point_in_time_market_research/test_dataset_persistence_adapter.py",
    "tests/data_layer/point_in_time_market_research/test_manifest_store.py",
    "tests/data_layer/point_in_time_market_research/test_as_of_query.py",
    "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
    "docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md",
    "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
    "tests/test_project_status_docs.py",
    "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
    "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    "tests/test_wallet_intelligence_architecture_contract_docs.py",
    "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
    "tests/test_human_review_label_workflow_docs.py",
    "docs/status_entries/WP162.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/deferred_items_log.md",
}

# WP163 uses a separate canonical contract document rather than an addendum to the
# append-only contract, so this file is only touched to keep this changed-file
# scope guard future-safe; that self-reference makes the WP163 authorized set 20
# files (the 19 record-store package files plus this guard).
# WP164 uses a separate canonical public-population contract document and its own
# focused docs test; this changed-file scope guard is touched only to keep the
# WP164 branch future-safe, which makes the WP164 authorized set exactly 20 files.
# WP165 uses a separate canonical incremental-population contract document and its
# own focused docs test; this changed-file scope guard is touched only to keep the
# WP165 branch future-safe, which makes the WP165 authorized set exactly 20 files.
# WP166 uses a separate canonical scalable-lineage-delta/keyset contract document
# and its own focused docs test; this changed-file scope guard is touched only to
# keep the WP166 branch future-safe. WP166 spans a larger 33-file scope because it
# extends the shared record/manifest/adapter/record-store layers plus the public
# client and polling policy, and adds the new scaled-population coordinator module.
WP168_AUTHORIZED_FILES = {
    "docs/wp_specs/WP168/wp_prompt.txt",
    "docs/wp_specs/WP168/wp_spec.json",
    "docs/wp_specs/WP168/draftability_certificate.json",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    "src/research_runtime/README.md",
    "src/research_runtime/nautilus_offline/__init__.py",
    "src/research_runtime/nautilus_offline/runtime_compatibility.py",
    "src/research_runtime/nautilus_offline/instruments.py",
    "src/research_runtime/nautilus_offline/conversion.py",
    "src/research_runtime/nautilus_offline/catalog.py",
    "src/research_runtime/nautilus_offline/replay.py",
    "tests/research_runtime/nautilus_offline/test_runtime_compatibility.py",
    "tests/research_runtime/nautilus_offline/test_instruments.py",
    "tests/research_runtime/nautilus_offline/test_conversion.py",
    "tests/research_runtime/nautilus_offline/test_catalog.py",
    "tests/research_runtime/nautilus_offline/test_replay.py",
    "docs/nautilus_offline_kernel_contract.md",
    "tests/test_nautilus_offline_kernel_contract_docs.py",
    "docs/status_entries/WP168.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/deferred_items_log.md",
    "docs/security_tooling_status.md",
    "docs/adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in.md",
    "tests/test_architecture_boundaries.py",
    "tests/test_project_status_docs.py",
    "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
    "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
    "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    "tests/test_wallet_intelligence_architecture_contract_docs.py",
    "tests/test_human_review_label_workflow_docs.py",
    "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
    "tests/data_layer/analytical_research/test_dependency_runtime_compatibility.py",
}


WP167_AUTHORIZED_FILES = {
    "docs/wp_specs/WP167/wp_prompt.txt",
    "docs/wp_specs/WP167/wp_spec.json",
    "docs/wp_specs/WP167/draftability_certificate.json",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    "src/data_layer/analytical_research/__init__.py",
    "src/data_layer/analytical_research/research_dataset.py",
    "src/data_layer/analytical_research/external_dataset.py",
    "src/data_layer/analytical_research/pmxt_v2.py",
    "tests/data_layer/analytical_research/test_research_dataset.py",
    "tests/data_layer/analytical_research/test_external_dataset.py",
    "tests/data_layer/analytical_research/test_pmxt_v2.py",
    "tests/data_layer/analytical_research/test_dependency_runtime_compatibility.py",
    "docs/analytical_research_layer_contract.md",
    "tests/test_analytical_research_layer_contract_docs.py",
    "docs/status_entries/WP167.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/deferred_items_log.md",
    "docs/security_tooling_status.md",
    "tests/test_architecture_boundaries.py",
    "tests/test_project_status_docs.py",
    "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
    "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
    "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    "tests/test_wallet_intelligence_architecture_contract_docs.py",
    "tests/test_human_review_label_workflow_docs.py",
    "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
}


WP166_AUTHORIZED_FILES = {
    "src/data_layer/point_in_time_market_research/records.py",
    "src/data_layer/point_in_time_market_research/manifest_reference.py",
    "src/data_layer/point_in_time_market_research/manifest_store.py",
    "src/data_layer/point_in_time_market_research/dataset_persistence_adapter.py",
    "src/data_layer/point_in_time_market_research/record_store.py",
    "src/data_layer/polymarket/public_client.py",
    "src/data_layer/polymarket/polling_policy.py",
    "src/data_layer/point_in_time_market_research/polymarket_scaled_population.py",
    "src/data_layer/point_in_time_market_research/__init__.py",
    "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
    "tests/data_layer/point_in_time_market_research/test_manifest_reference.py",
    "tests/data_layer/point_in_time_market_research/test_manifest_store.py",
    "tests/data_layer/point_in_time_market_research/test_dataset_persistence_adapter.py",
    "tests/data_layer/point_in_time_market_research/test_record_store.py",
    "tests/data_layer/polymarket/test_public_client.py",
    "tests/data_layer/polymarket/test_polling_policy.py",
    "tests/data_layer/point_in_time_market_research/test_polymarket_scaled_population.py",
    "tests/data_layer/point_in_time_market_research/test_polymarket_incremental_population.py",
    "tests/data_layer/point_in_time_market_research/test_as_of_query.py",
    "docs/scalable_lineage_delta_and_keyset_population_contract.md",
    "tests/test_scalable_lineage_delta_and_keyset_population_contract_docs.py",
    "docs/status_entries/WP166.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/deferred_items_log.md",
    "tests/test_project_status_docs.py",
    "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
    "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    "tests/test_wallet_intelligence_architecture_contract_docs.py",
    "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
    "tests/test_human_review_label_workflow_docs.py",
    "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
}

WP165_AUTHORIZED_FILES = {
    "src/data_layer/point_in_time_market_research/polymarket_incremental_population.py",
    "src/data_layer/point_in_time_market_research/__init__.py",
    "tests/data_layer/point_in_time_market_research/test_polymarket_incremental_population.py",
    "tests/data_layer/point_in_time_market_research/test_polymarket_public_population.py",
    "tests/data_layer/point_in_time_market_research/test_as_of_query.py",
    "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
    "docs/polymarket_incremental_point_in_time_population_contract.md",
    "tests/test_polymarket_incremental_point_in_time_population_contract_docs.py",
    "tests/test_project_status_docs.py",
    "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
    "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    "tests/test_wallet_intelligence_architecture_contract_docs.py",
    "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
    "tests/test_human_review_label_workflow_docs.py",
    "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
    "docs/status_entries/WP165.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/deferred_items_log.md",
}


WP164_AUTHORIZED_FILES = {
    "src/data_layer/point_in_time_market_research/polymarket_public_population.py",
    "src/data_layer/point_in_time_market_research/__init__.py",
    "tests/data_layer/point_in_time_market_research/test_polymarket_public_population.py",
    "tests/data_layer/point_in_time_market_research/test_record_store.py",
    "tests/data_layer/point_in_time_market_research/test_as_of_query.py",
    "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
    "docs/polymarket_point_in_time_public_population_contract.md",
    "tests/test_polymarket_point_in_time_public_population_contract_docs.py",
    "tests/test_project_status_docs.py",
    "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
    "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    "tests/test_wallet_intelligence_architecture_contract_docs.py",
    "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
    "tests/test_human_review_label_workflow_docs.py",
    "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
    "docs/status_entries/WP164.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/deferred_items_log.md",
}


WP163_AUTHORIZED_FILES = {
    "src/data_layer/point_in_time_market_research/record_store.py",
    "src/data_layer/point_in_time_market_research/__init__.py",
    "tests/data_layer/point_in_time_market_research/test_record_store.py",
    "tests/data_layer/point_in_time_market_research/test_dataset_persistence_adapter.py",
    "tests/data_layer/point_in_time_market_research/test_as_of_query.py",
    "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
    "docs/point_in_time_record_store_contract.md",
    "tests/test_point_in_time_record_store_contract_docs.py",
    "tests/test_project_status_docs.py",
    "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
    "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    "tests/test_wallet_intelligence_architecture_contract_docs.py",
    "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
    "tests/test_human_review_label_workflow_docs.py",
    "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
    "docs/status_entries/WP163.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/deferred_items_log.md",
}


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _section(text: str, start: str, end: str | None = None) -> str:
    start_index = text.index(start)
    if end is None:
        return text[start_index:]
    return text[start_index : text.index(end, start_index + len(start))]


def _changed_files() -> set[str]:
    diff = subprocess.run(
        ["git", "diff", "--name-only", "origin/main"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return {
        line.replace("\\", "/")
        for line in (diff.stdout + untracked.stdout).splitlines()
        if line
    }


def test_canonical_status_and_repo_truth_surfaces_exist() -> None:
    for path in (DOC, STATUS, PROJECT_STATUS, INDEX, DEFERRED):
        assert path.is_file()


def test_exact_label_posture_and_capital_at_risk() -> None:
    combined = f"{_read(DOC)}\n{_read(STATUS)}\n{_read(PROJECT_STATUS)}"
    for token in (
        "APPEND_ONLY_LOCAL_MANIFEST_AND_DETERMINISTIC_DATASET_SNAPSHOT_REFERENCE_CONTRACT",
        "CONTRACT_ONLY_NO_WRITER_NO_READER_NO_PERSISTENCE",
        "Capital at risk: USD 0",
    ):
        assert token in combined


def test_predecessor_merge_lineage_is_exact() -> None:
    combined = f"{_read(DOC)}\n{_read(STATUS)}"
    for token in (
        "4785a561dca8bb87dcd55fd352686543a9dbceec",
        "583a0ab0bd85810f2865eb15553a58d44bd9f65f",
        "PR: #157",
    ):
        assert token in combined


def test_schema_ids_and_versions_are_exact() -> None:
    section = _section(_read(DOC), "## 5. Locked Vocabularies", "## 6.")
    for token in (
        "point-in-time-dataset-snapshot-reference",
        "point-in-time-local-manifest-entry",
        "`1.0.0`",
    ):
        assert token in section


def test_locked_vocabularies_are_complete_and_canonically_ordered() -> None:
    section = _section(_read(DOC), "## 5. Locked Vocabularies", "## 6.")

    derivation = (
        "VALIDATED_RECORD_BATCH",
        "AS_OF_QUERY_RESULT",
    )
    kinds = (
        "REGISTER_DATASET_SNAPSHOT_REFERENCE",
        "SUPERSEDE_DATASET_SNAPSHOT_REFERENCE",
        "INVALIDATE_DATASET_SNAPSHOT_REFERENCE",
    )
    states = (
        "ACTIVE_REFERENCE",
        "SUPERSEDED_REFERENCE",
        "INVALIDATED_REFERENCE",
    )
    reasons = (
        "INITIAL_REGISTRATION",
        "SOURCE_SUPERSEDED",
        "REFERENCE_INVALIDATED",
    )
    for vocabulary in (derivation, kinds, states, reasons):
        positions = [section.index(item) for item in vocabulary]
        assert positions == sorted(positions)


def test_dataset_reference_required_fields_are_complete() -> None:
    section = _section(_read(DOC), "## 6. Dataset Snapshot Reference Contract", "## 7.")
    for field in (
        "schema_id",
        "schema_version",
        "dataset_snapshot_reference_id",
        "derivation_mode",
        "validated_batch_sha256",
        "ordinary_record_version_ids",
        "review_conflict_record_version_ids",
        "query_spec_sha256",
        "query_result_sha256",
        "cutoff_mode",
        "cutoff_time",
        "result_view",
        "query_engine_version",
        "validator_version",
        "parameter_set_id",
        "created_from_manifest_entry_id",
        "human_review_required",
        "advisory_only",
        "no_execution_authority",
    ):
        assert f"`{field}`" in section
    flat = _flat(section)
    for rule in (
        "always required",
        "The record-version ID tuples are immutable and ordered",
        "Cross-authority overlap takes precedence over the generic within-tuple duplicate rule",
        "never become authoritative",
        "excluded from reference identity to avoid",
        "fixed `true`",
    ):
        assert rule in flat


def test_dataset_reference_forbidden_fields_are_explicit() -> None:
    section = _section(_read(DOC), "### 6.3 Forbidden Fields", "## 7.")
    flat = _flat(section)
    for token in (
        "raw payload",
        "source text",
        "question/rule text",
        "prices/sizes",
        "wallet/account/credential identifiers",
        "strategy/signal/trade fields",
        "filesystem path",
        "hostname",
        "process ID",
        "runtime duration",
        "current time",
        "object representation",
    ):
        assert token in flat


def test_dataset_reference_identity_prefix_preimage_and_exclusions() -> None:
    section = _section(_read(DOC), "## 7. Dataset Snapshot Reference Identity", "## 8.")
    assert '"datasetref:sha256:" + SHA-256(canonical_preimage)' in section
    # Exact preimage mapping keys are present (checked more fully by the oracle
    # test); here we confirm identity prefix, exclusions, and canonical rules.
    mapping = _section(section, "### 7.1 Exact Preimage Mapping", "### 7.2")
    for key in _REFERENCE_PREIMAGE_KEYS:
        assert f'"{key}"' in mapping
    flat = _flat(section)
    for excluded in (
        "the self ID",
        "`created_from_manifest_entry_id`",
        "storage metadata",
        "all runtime / environment values",
    ):
        assert excluded in flat
    for canonical in (
        "UTF-8 encoding",
        "lexicographically sorted",
        "explicit nulls preserved",
        "`allow_nan=False`",
        "One-field hash sensitivity holds",
    ):
        assert canonical in flat


def test_manifest_entry_required_fields_and_rules_are_complete() -> None:
    section = _section(_read(DOC), "## 8. Manifest Entry Contract", "## 9.")
    for field in (
        "schema_id",
        "schema_version",
        "manifest_entry_id",
        "manifest_id",
        "sequence_number",
        "previous_manifest_entry_id",
        "entry_kind",
        "dataset_snapshot_reference_id",
        "supersedes_manifest_entry_id",
        "reference_state",
        "reason_code",
        "effective_time",
        "parameter_set_id",
        "human_review_required",
        "advisory_only",
        "no_execution_authority",
    ):
        assert f"`{field}`" in section
    flat = _flat(section)
    for rule in (
        "non-negative integer; a boolean is invalid",
        "0 requires `previous_manifest_entry_id` null",
        "requires the exact prior entry ID",
        "One `manifest_id` per chain",
        "sequence / link based, never effective-time based",
        "cannot rewrite prior entries",
    ):
        assert rule in flat


def test_manifest_entry_identity_prefix_preimage_and_exclusions() -> None:
    section = _section(_read(DOC), "## 9. Manifest Entry Identity", "## 10.")
    assert '"manifestentry:sha256:" + SHA-256(canonical_preimage)' in section
    mapping = _section(section, "### 9.1 Exact Preimage Mapping", "### 9.2")
    for key in _MANIFEST_PREIMAGE_KEYS:
        assert f'"{key}"' in mapping
    flat = _flat(section)
    for excluded in (
        "the self ID",
        "file offset",
        "file path",
        "storage engine",
        "write time",
        "host / process / runtime values",
    ):
        assert excluded in flat


def test_append_chain_truth_table_is_complete() -> None:
    section = _section(_read(DOC), "## 10. Append-Chain Truth Table", "## 11.")
    for row in (
        "| 0 | null | REGISTER | null | valid genesis |",
        "| 0 | non-null | any | any | reject |",
        "| >0 | null | any | any | reject |",
        "| >0 | exact prior | REGISTER | null | valid append |",
        "| >0 | unknown prior | any | any | reject |",
        "| >0 | prior from other manifest | any | any | reject |",
        "| >0 | exact prior | SUPERSEDE | earlier same-chain effective entry, same subject | valid |",
        "| >0 | exact prior | SUPERSEDE | null/unknown/future/self | reject |",
        "| >0 | exact prior | SUPERSEDE | target dataset-reference ID ≠ entry's | reject |",
        "| >0 | exact prior | SUPERSEDE | target already superseded/invalidated | reject |",
        "| >0 | exact prior | INVALIDATE | earlier same-chain effective entry, same subject | valid with review |",
        "| >0 | exact prior | INVALIDATE | null/unknown/future/self | reject |",
        "| >0 | exact prior | INVALIDATE | target dataset-reference ID ≠ entry's | reject |",
        "| >0 | exact prior | INVALIDATE | target already superseded/invalidated | reject |",
        "| duplicate sequence | any | any | any | reject |",
        "| duplicate ID/different content | any | any | any | reject |",
        "| cycle | any | any | any | reject |",
    ):
        assert row in section
    flat = _flat(section)
    for rejected in (
        "branching",
        "multiple heads",
        "sequence gaps",
        "cycles",
        "backward mutation",
        "implicit latest-by-time resolution",
    ):
        assert rejected in flat
    # The chain head is explicitly distinct from a subject reference's state.
    assert "distinct from any subject reference's effective state" in flat


def test_public_api_matrix_is_unchanged() -> None:
    section = _section(_read(DOC), "## 11. Public API Matrix", "## 12.")
    assert "WP158 changes no Python public API." in section
    for row in (
        "| WP156 record builders | unchanged |",
        "| `validate_record_batch` | unchanged |",
        "| WP157 query functions | unchanged |",
        "| WP157 public dataclasses/constants | unchanged |",
        "| manifest writer/reader/verifier | not implemented |",
        "| new package exports | none |",
    ):
        assert row in section
    assert "No new `src` file is added and no package-root export is added." in section
    for symbol in (
        "query_point_in_time_record_set",
        "PointInTimeQuerySpec",
        "PointInTimeRecordSetResult",
        "get_synthetic_as_of_query_cases",
    ):
        assert symbol in section


def test_semantic_commitment_matrix_covers_every_field() -> None:
    section = _section(_read(DOC), "## 12. Semantic Commitment Matrix", "## 13.")
    assert "identity-committed, derived/recomputed, or explicitly excluded" in _flat(
        section
    )
    reference_fields = (
        "schema_id",
        "schema_version",
        "dataset_snapshot_reference_id",
        "derivation_mode",
        "validated_batch_sha256",
        "ordinary_record_version_ids",
        "review_conflict_record_version_ids",
        "query_spec_sha256",
        "query_result_sha256",
        "cutoff_mode",
        "cutoff_time",
        "result_view",
        "query_engine_version",
        "validator_version",
        "parameter_set_id",
        "created_from_manifest_entry_id",
        "human_review_required",
        "advisory_only",
        "no_execution_authority",
    )
    manifest_fields = (
        "manifest_entry_id",
        "manifest_id",
        "sequence_number",
        "previous_manifest_entry_id",
        "entry_kind",
        "supersedes_manifest_entry_id",
        "reference_state",
        "reason_code",
        "effective_time",
    )
    for field in reference_fields + manifest_fields:
        assert f"`{field}`" in section
    # Both self-IDs and created_from must be explicitly excluded from identity.
    assert "NO (self)" in section
    assert "NO (circularity)" in section


def test_failure_no_echo_matrix_is_complete() -> None:
    section = _section(_read(DOC), "## 13. Failure / No-Echo Matrix", "## 14.")
    for category in (
        "SCHEMA_UNSUPPORTED",
        "FIELD_MISSING",
        "FIELD_TYPE_INVALID",
        "FIELD_VALUE_INVALID",
        "ID_DERIVATION_MISMATCH",
        "REFERENCE_MODE_MISMATCH",
        "REVIEW_CONFLICT_AUTHORITY_FORBIDDEN",
        "MANIFEST_SEQUENCE_INVALID",
        "MANIFEST_PREVIOUS_ENTRY_UNKNOWN",
        "MANIFEST_CHAIN_MISMATCH",
        "MANIFEST_SUPERSEDES_INVALID",
        "MANIFEST_CYCLE",
        "MANIFEST_ID_COLLISION_OR_MISMATCH",
        "DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH",
        "SAFETY_POSTURE_INVALID",
    ):
        assert f"`{category}`" in section
    for row in (
        "| IDs | empty/oversized/malformed | FIELD_VALUE_INVALID | no |",
        "| hashes | malformed/wrong derivation | ID_DERIVATION_MISMATCH | no |",
        "| record-ID tuples | within-tuple duplicate or wrong member type | FIELD_VALUE_INVALID | no |",
        "| record-ID tuples | overlap between ordinary and review tuples | REVIEW_CONFLICT_AUTHORITY_FORBIDDEN | no |",
        "| reserved backlink | non-null `created_from_manifest_entry_id` in 1.0.0 | FIELD_VALUE_INVALID | no |",
        "| query fields | partial mode combination | REFERENCE_MODE_MISMATCH | no |",
        "| sequence | bool/negative/gap/duplicate | MANIFEST_SEQUENCE_INVALID | no |",
        "| previous ID | unknown | MANIFEST_PREVIOUS_ENTRY_UNKNOWN | no |",
        "| previous ID | belongs to other manifest | MANIFEST_CHAIN_MISMATCH | no |",
        "| supersedes | null/unknown/future/self/non-effective/already-terminal | MANIFEST_SUPERSEDES_INVALID | no |",
        "| supersedes | target dataset-reference ID ≠ entry's | MANIFEST_SUPERSEDES_INVALID | no |",
        "| safety flags | false/non-bool | SAFETY_POSTURE_INVALID | no |",
        "| unexpected fields | any | FIELD_VALUE_INVALID | no |",
    ):
        assert row in section
    flat = _flat(section)
    for forbidden in (
        "raw caller values",
        "payload/source content",
        "exception text",
        "traceback",
        "local path",
        "environment data",
    ):
        assert forbidden in flat
    # Deterministic failure precedence for the record-version tuples.
    assert (
        "an overlap between `ordinary_record_version_ids` and `review_conflict_record_version_ids` is reported as `REVIEW_CONFLICT_AUTHORITY_FORBIDDEN`, which takes precedence over the generic within-tuple `FIELD_VALUE_INVALID` duplicate rule"
        in flat
    )


# ── Derived-ID truth: examples recompute from the exact locked preimages ──────


def test_preimage_mappings_are_locked_in_the_contract() -> None:
    ref = _section(_read(DOC), "### 7.1 Exact Preimage Mapping", "### 7.2")
    man = _section(_read(DOC), "### 9.1 Exact Preimage Mapping", "### 9.2")
    for key in _REFERENCE_PREIMAGE_KEYS:
        assert f'"{key}"' in ref
    # Excluded keys must NOT appear in the reference preimage mapping block.
    assert '"dataset_snapshot_reference_id"' not in ref
    assert '"created_from_manifest_entry_id"' not in ref
    for key in _MANIFEST_PREIMAGE_KEYS:
        assert f'"{key}"' in man
    assert '"manifest_entry_id"' not in man
    canon = _flat(_section(_read(DOC), "### 7.3 Canonicalization And Derivation", "## 8."))
    for rule in (
        "`sort_keys=True`",
        'separators exactly `(",", ":")`',
        "`ensure_ascii=False`",
        "`allow_nan=False`",
        '"datasetref:sha256:" + sha256(canonical_json_bytes(preimage_mapping)).hexdigest()',
    ):
        assert rule in canon


def test_every_example_self_id_recomputes_from_its_preimage() -> None:
    for ex in _json_examples():
        obj = ex["input"]
        if _is_reference(obj):
            assert obj["dataset_snapshot_reference_id"] == _derive_reference_id(obj), (
                ex["example_id"]
            )
        else:
            assert obj["manifest_entry_id"] == _derive_manifest_entry_id(obj), (
                ex["example_id"]
            )


def test_examples_6_through_11_chain_links_are_actual_recomputed_ids() -> None:
    by = {ex["example_id"]: ex["input"] for ex in _json_examples()}
    g = by["WP158-EXAMPLE-06"]
    s = by["WP158-EXAMPLE-07"]
    u = by["WP158-EXAMPLE-08"]
    v = by["WP158-EXAMPLE-09"]
    gap = by["WP158-EXAMPLE-10"]
    cross = by["WP158-EXAMPLE-11"]

    id6 = _derive_manifest_entry_id(g)
    id7 = _derive_manifest_entry_id(s)
    id8 = _derive_manifest_entry_id(u)
    id9 = _derive_manifest_entry_id(v)

    assert g["previous_manifest_entry_id"] is None
    assert s["previous_manifest_entry_id"] == id6
    assert u["previous_manifest_entry_id"] == id7
    assert u["supersedes_manifest_entry_id"] == id6
    assert v["previous_manifest_entry_id"] == id8
    assert v["supersedes_manifest_entry_id"] == id7
    # Invalid entries still link to the actual recomputed IDs so their intended
    # defect (sequence gap / cross-manifest) is the only fault.
    assert gap["previous_manifest_entry_id"] == id9
    assert gap["sequence_number"] == 5  # gap after seq 3 head
    assert cross["previous_manifest_entry_id"] == id6
    assert cross["manifest_id"] == "manifest:wp158-synthetic-chain-b"


def test_one_field_identity_mutation_changes_the_derived_id() -> None:
    by = {ex["example_id"]: ex["input"] for ex in _json_examples()}
    ref = dict(by["WP158-EXAMPLE-01"])
    ref["validated_batch_sha256"] = "f" * 64
    assert _derive_reference_id(ref) != by["WP158-EXAMPLE-01"]["dataset_snapshot_reference_id"]

    man = dict(by["WP158-EXAMPLE-06"])
    man["effective_time"] = "2099-01-01T00:00:00Z"
    assert _derive_manifest_entry_id(man) != by["WP158-EXAMPLE-06"]["manifest_entry_id"]


def test_reserved_backlink_cannot_change_content_under_same_id() -> None:
    # created_from_manifest_entry_id is excluded from identity AND fixed null in
    # 1.0.0, so it can never legally vary under the same reference ID.
    for ex in _json_examples():
        obj = ex["input"]
        if _is_reference(obj):
            assert obj["created_from_manifest_entry_id"] is None
            assert "created_from_manifest_entry_id" not in _REFERENCE_PREIMAGE_KEYS


def test_example_12_is_single_fault_cross_authority_overlap() -> None:
    obj = {ex["example_id"]: ex["input"] for ex in _json_examples()}["WP158-EXAMPLE-12"]
    # The single intended fault is a cross-tuple overlap.
    overlap = set(obj["ordinary_record_version_ids"]) & set(
        obj["review_conflict_record_version_ids"]
    )
    assert overlap
    # No within-tuple duplicate (that would be a different, competing fault).
    assert len(obj["ordinary_record_version_ids"]) == len(
        set(obj["ordinary_record_version_ids"])
    )
    assert len(obj["review_conflict_record_version_ids"]) == len(
        set(obj["review_conflict_record_version_ids"])
    )
    # Self ID is correctly derived; the defect is not an ID mismatch.
    assert obj["dataset_snapshot_reference_id"] == _derive_reference_id(obj)
    # Deterministic precedence: overlap maps only to the authority category.
    ex12 = {ex["example_id"]: ex for ex in _json_examples()}["WP158-EXAMPLE-12"]
    assert ex12["expected_error_codes"] == ["REVIEW_CONFLICT_AUTHORITY_FORBIDDEN"]


def test_invalid_examples_are_single_fault_with_correct_self_ids() -> None:
    by = {ex["example_id"]: ex for ex in _json_examples()}
    for eid, expected in (
        ("WP158-EXAMPLE-10", "MANIFEST_SEQUENCE_INVALID"),
        ("WP158-EXAMPLE-11", "MANIFEST_CHAIN_MISMATCH"),
        ("WP158-EXAMPLE-12", "REVIEW_CONFLICT_AUTHORITY_FORBIDDEN"),
    ):
        ex = by[eid]
        assert ex["expected_valid"] is False
        assert ex["expected_error_codes"] == [expected]
        obj = ex["input"]
        # Correct self ID: the fault is never an accidental ID-derivation mismatch.
        if _is_reference(obj):
            assert obj["dataset_snapshot_reference_id"] == _derive_reference_id(obj)
            assert set(obj) == REFERENCE_REQUIRED_FIELDS
        else:
            assert obj["manifest_entry_id"] == _derive_manifest_entry_id(obj)
            assert set(obj) == MANIFEST_REQUIRED_FIELDS
        # Safety posture intact (not a competing safety fault).
        assert obj["advisory_only"] is True
        assert obj["no_execution_authority"] is True


# ── Blocker A: reserved-null v1.0.0 backlink and reference immutability ───────


def test_reserved_null_backlink_rule_and_immutability_invariant() -> None:
    rules = _flat(_section(_read(DOC), "### 6.2 Rules", "### 6.3"))
    assert "reserved field in schema version" in rules
    assert "MUST be present and MUST be null" in rules
    assert "never populated after registration" in rules
    assert "Registration provenance is one-way" in rules
    assert (
        "non-null `created_from_manifest_entry_id` under schema `1.0.0` is rejected with `FIELD_VALUE_INVALID`"
        in rules
    )
    invariant = _flat(
        _section(_read(DOC), "### 6.4 Reference Immutability Invariant", "## 7.")
    )
    assert "immutable after `dataset_snapshot_reference_id` is derived" in invariant
    assert "no excluded mutable field may create a same-ID / different-content ambiguity" in invariant
    matrix_row = _section(_read(DOC), "| `created_from_manifest_entry_id` |", "\n")
    assert "reserved in 1.0.0: required present and null" in matrix_row
    assert "fixed-null check" in matrix_row


# ── Blocker B: SUPERSEDE / INVALIDATE subject and target semantics ────────────


def test_supersede_invalidate_subject_target_semantics() -> None:
    section = _flat(_section(_read(DOC), "### 8.3 Entry-Kind Subject And Target Semantics", "## 9."))
    # REGISTER
    assert "is the newly registered subject reference" in section
    # SUPERSEDE / INVALIDATE are state-transition records for the target
    assert "a state-transition record for an already-registered subject, not a replacement-registration record" in section
    assert section.count(
        "MUST equal the target entry's `dataset_snapshot_reference_id`"
    ) >= 2
    assert "MUST be registered separately with its own `REGISTER_DATASET_SNAPSHOT_REFERENCE` entry" in section
    assert "neither infers nor requires a replacement" in section
    # State-transition integrity
    assert "already terminally" in section
    assert "no repeated terminal transition" in section
    assert "self-target" in section
    assert "The append-chain head and the subject-reference state are separate concepts" in section


def test_twelve_json_examples_parse_and_satisfy_invariants() -> None:
    examples = _json_examples()
    assert len(examples) == 12

    ids = [ex["example_id"] for ex in examples]
    assert ids == [f"WP158-EXAMPLE-{n:02d}" for n in range(1, 13)]
    assert len(set(ids)) == 12

    valid_count = 0
    invalid_count = 0
    for ex in examples:
        assert set(ex) == {"example_id", "expected_valid", "expected_error_codes", "input"}
        assert isinstance(ex["expected_valid"], bool)
        assert isinstance(ex["expected_error_codes"], list)
        obj = ex["input"]
        assert isinstance(obj, dict)

        # Object-kind detection by schema_id.
        schema_id = obj["schema_id"]
        assert schema_id in {
            "point-in-time-dataset-snapshot-reference",
            "point-in-time-local-manifest-entry",
        }
        assert obj["schema_version"] == "1.0.0"

        # Safety booleans present and fixed true on every example.
        assert obj["advisory_only"] is True
        assert obj["no_execution_authority"] is True

        # No forbidden keys / unsafe marker values anywhere in the object.
        forbidden_keys = {
            "payload",
            "source_text",
            "question_text",
            "rule_text",
            "price",
            "size",
            "wallet",
            "account",
            "credential",
            "api_key",
            "path",
            "hostname",
            "pid",
            "process_id",
        }
        assert not (set(obj) & forbidden_keys)

        if schema_id == "point-in-time-dataset-snapshot-reference":
            assert set(obj) == REFERENCE_REQUIRED_FIELDS
            # Reserved-null v1.0.0 backlink on every reference.
            assert obj["created_from_manifest_entry_id"] is None
            assert obj["dataset_snapshot_reference_id"].startswith("datasetref:sha256:")
            assert _HEX64.match(obj["dataset_snapshot_reference_id"].split(":")[-1])
            assert _HEX64.match(obj["validated_batch_sha256"])
            # Record-version IDs are prefixed and 64-hex; tuples never overlap
            # UNLESS this is the authority-mixing negative example.
            ordinary = obj["ordinary_record_version_ids"]
            review = obj["review_conflict_record_version_ids"]
            for rid in ordinary + review:
                assert rid.startswith("record:sha256:")
                assert _HEX64.match(rid.split(":")[-1])
            if ex["expected_valid"]:
                assert not (set(ordinary) & set(review))
                # Conflict-derived human-review flag.
                assert obj["human_review_required"] is bool(review)
            # Explicit null rules by derivation mode.
            query_fields = (
                "query_spec_sha256",
                "query_result_sha256",
                "cutoff_mode",
                "cutoff_time",
                "result_view",
                "query_engine_version",
            )
            if obj["derivation_mode"] == "VALIDATED_RECORD_BATCH":
                assert all(obj[f] is None for f in query_fields)
            else:
                assert obj["derivation_mode"] == "AS_OF_QUERY_RESULT"
                assert all(obj[f] is not None for f in query_fields)
        else:
            assert set(obj) == MANIFEST_REQUIRED_FIELDS
            assert obj["manifest_entry_id"].startswith("manifestentry:sha256:")
            assert _HEX64.match(obj["manifest_entry_id"].split(":")[-1])
            assert obj["dataset_snapshot_reference_id"].startswith("datasetref:sha256:")
            assert isinstance(obj["sequence_number"], int) and not isinstance(
                obj["sequence_number"], bool
            )
            kind = obj["entry_kind"]
            # Exact REGISTER / SUPERSEDE / INVALIDATE target semantics on valid entries.
            if ex["expected_valid"]:
                if kind == "REGISTER_DATASET_SNAPSHOT_REFERENCE":
                    assert obj["supersedes_manifest_entry_id"] is None
                    assert obj["reference_state"] == "ACTIVE_REFERENCE"
                    assert obj["reason_code"] == "INITIAL_REGISTRATION"
                elif kind == "SUPERSEDE_DATASET_SNAPSHOT_REFERENCE":
                    assert obj["supersedes_manifest_entry_id"] is not None
                    assert obj["reference_state"] == "SUPERSEDED_REFERENCE"
                    assert obj["reason_code"] == "SOURCE_SUPERSEDED"
                elif kind == "INVALIDATE_DATASET_SNAPSHOT_REFERENCE":
                    assert obj["supersedes_manifest_entry_id"] is not None
                    assert obj["reference_state"] == "INVALIDATED_REFERENCE"
                    assert obj["reason_code"] == "REFERENCE_INVALIDATED"
                    assert obj["human_review_required"] is True
                else:  # pragma: no cover - closed vocabulary
                    raise AssertionError(f"unexpected entry_kind {kind}")

        # Valid/invalid classification and error-code discipline.
        if ex["expected_valid"]:
            assert ex["expected_error_codes"] == []
            valid_count += 1
        else:
            assert ex["expected_error_codes"]
            assert set(ex["expected_error_codes"]) <= LOCKED_FAILURE_CATEGORIES
            invalid_count += 1

    assert valid_count == 9
    assert invalid_count == 3


def test_supersede_and_invalidate_examples_target_same_subject() -> None:
    by_id = {ex["example_id"]: ex["input"] for ex in _json_examples()}
    genesis = by_id["WP158-EXAMPLE-06"]
    second = by_id["WP158-EXAMPLE-07"]
    supersede = by_id["WP158-EXAMPLE-08"]
    invalidate = by_id["WP158-EXAMPLE-09"]

    # Coherent single chain, exact previous-ID links, ascending sequence.
    for entry in (genesis, second, supersede, invalidate):
        assert entry["manifest_id"] == "manifest:wp158-synthetic-chain-a"
    assert genesis["sequence_number"] == 0
    assert genesis["previous_manifest_entry_id"] is None
    assert second["previous_manifest_entry_id"] == genesis["manifest_entry_id"]
    assert supersede["previous_manifest_entry_id"] == second["manifest_entry_id"]
    assert invalidate["previous_manifest_entry_id"] == supersede["manifest_entry_id"]

    # Transition entries carry the SAME subject reference as their target entry.
    assert supersede["supersedes_manifest_entry_id"] == genesis["manifest_entry_id"]
    assert supersede["dataset_snapshot_reference_id"] == genesis["dataset_snapshot_reference_id"]
    assert invalidate["supersedes_manifest_entry_id"] == second["manifest_entry_id"]
    assert invalidate["dataset_snapshot_reference_id"] == second["dataset_snapshot_reference_id"]


def test_non_authority_storage_boundary_and_next_gate() -> None:
    section = _section(_read(DOC), "## 15. Non-Authority And Storage Boundaries", "## 16.")
    flat = _flat(section)
    for phrase in (
        "selects no storage container",
        "authorizes no writer, no reader, no verifier, and no persistence",
        "grants no strategy, signal, paper, order, risk, reconciliation, accounting, or execution authority",
        "Review conflicts are never authoritative",
        "inherits WP157 ingestion-time semantics unchanged",
        "WP158 does not implement WP159",
    ):
        assert phrase in flat


def test_wp159_is_named_but_not_implemented() -> None:
    section = _flat(
        _section(_read(DOC), "## 17. Next Separately Gated Package", "## 18.")
    )
    assert "WP159" in section
    assert "requires separate approval and is not implemented" in section
    assert "WP159 is not implemented in this package." in section


def test_compatibility_terms_and_no_persistence_runtime_claims() -> None:
    text = _read(DOC)
    for token in ("WP155", "WP156", "WP157"):
        assert token in text
    lowered = _flat(text).lower()
    for forbidden_claim in (
        "the writer is implemented",
        "persistence is active",
        "arrow/parquet is installed",
        "duckdb is adopted",
        "polars is installed",
        "review conflicts are authoritative",
        "wp159 is implemented",
    ):
        assert forbidden_claim not in lowered


def test_no_new_implementation_module_or_manifest_source_exists() -> None:
    data_layer = ROOT / "src" / "data_layer"
    for forbidden in (
        data_layer / "point_in_time_manifest.py",
        data_layer / "dataset_snapshot_reference.py",
        data_layer / "point_in_time_market_research" / "manifest.py",
        data_layer / "point_in_time_market_research" / "dataset_snapshot_reference.py",
        data_layer / "point_in_time_market_research" / "manifest_entry.py",
    ):
        assert not forbidden.exists()


def test_wp157_public_surface_is_unchanged() -> None:
    init = ROOT / "src" / "data_layer" / "point_in_time_market_research" / "__init__.py"
    text = init.read_text(encoding="utf-8")
    for symbol in (
        "AS_OF_QUERY_LABEL",
        "AS_OF_QUERY_POSTURE",
        "SUPPORTED_CUTOFF_MODES",
        "SUPPORTED_RESULT_VIEWS",
        "QUERY_STATUSES",
        "EXCLUSION_REASONS",
        "EventTimeWindow",
        "PointInTimeQuerySpec",
        "PointInTimeQueryReceipt",
        "PointInTimeRecordSetResult",
        "SyntheticAsOfQueryCase",
        "query_point_in_time_record_set",
        "get_synthetic_as_of_query_cases",
        "load_synthetic_as_of_query_case",
    ):
        assert symbol in text


def test_repo_truth_index_registers_canonical_status_and_focused_test() -> None:
    index = _read(INDEX)
    for path in (
        "docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md",
        "docs/status_entries/WP158.md",
        "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
    ):
        assert path in index


def test_project_status_registers_wp158_review_target_and_next_gate() -> None:
    project = _read(PROJECT_STATUS)
    current = next(
        line for line in project.splitlines() if line.startswith("- Current phase:")
    )
    merged = next(
        line for line in project.splitlines() if line.startswith("- Merged WPs:")
    )
    if (ROOT / "docs" / "status_entries" / "WP168.md").exists():
        # WP168 is the current review target following merged WP167.
        assert "WP168" in current
        assert "WP167" in merged
        assert current.count("current review target") == 1
        return
    if (ROOT / "docs" / "status_entries" / "WP167.md").exists():
        # WP167 is the current review target; it advances past the WP158/WP160-era markers.
        assert "WP167" in current
        assert "WP166" in merged
        assert current.count("current review target") == 1
        assert (
            "Append-only local manifest and deterministic dataset snapshot reference contract status:"
            in project
        )
        return
    assert "WP161" in current
    assert "WP160" in merged
    assert current.count("current review target") == 1
    assert "Ready for review: YES" in current
    assert "Manifest and dataset snapshot reference validator implemented by: WP160" in current
    assert (
        "Append-only local manifest and deterministic dataset snapshot reference contract status:"
        in project
    )


def test_deferred_reconciliation_is_contract_only_and_ten_items_are_open() -> None:
    log = _read(DEFERRED)
    section = _section(
        log,
        "## WP158 Append-Only Local Manifest And Deterministic Dataset Snapshot Reference Deferred Items",
    )
    ids = re.findall(r"^\| (WP158-D\d{3}) \|", section, re.MULTILINE)
    assert ids == [f"WP158-D{index:03d}" for index in range(1, 11)]
    flat = _flat(section)
    for phrase in (
        "Manifest writer",
        "reader/verifier",
        "Storage path",
        "Atomic append",
        "Crash recovery",
        "Schema migration",
        "Compaction",
        "Arrow/Parquet",
        "DuckDB/Polars",
        "Signing",
    ):
        assert phrase in flat


def test_status_fragment_is_stable_model_d() -> None:
    status = _read(STATUS)
    assert "PR: see GitHub PR metadata and PR body." in status
    assert "Current live PR head: see GitHub PR metadata and PR body" in status
    assert "stable and non-self-referential" in status
    assert "Ready for review: YES only after final committed-head validation" in status
    assert "TBD" not in status
    assert "LOCAL_DRAFT_VERIFIED" not in status
    assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", status) is None


def test_no_dependency_workflow_or_generated_artifact_in_scope() -> None:
    changed = _changed_files()
    if "docs/status_entries/WP168.md" in changed:
        # WP168 owns its exact 35-file XL scope; dependency (pyproject.toml) and
        # workflow (.github/workflows/ci.yml) files are explicitly authorized for WP168.
        assert changed == WP168_AUTHORIZED_FILES
        return
    if "docs/status_entries/WP167.md" in changed:
        # WP167 owns its exact 27-file XL scope; dependency (pyproject.toml) and
        # workflow (.github/workflows/ci.yml) files are explicitly authorized for WP167.
        assert changed == WP167_AUTHORIZED_FILES
        return
    if "docs/status_entries/WP166.md" in changed:
        # WP166 authorizes source and test paths within its exact 33-file scope;
        # dependency, workflow, tool, fixture, config, and generated-artifact
        # paths remain forbidden.
        assert changed == WP166_AUTHORIZED_FILES
        assert not (changed & {
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "Cargo.toml",
            "Cargo.lock",
        })
        assert not any(
            path.startswith(
                (
                    "tools/",
                    "tests/fixtures/",
                    ".github/workflows/",
                    "config/",
                    "local_data/",
                )
            )
            for path in changed
        )
        return
    if "docs/status_entries/WP165.md" in changed:
        # WP165 authorizes source and test paths within its exact 20-file scope;
        # dependency, workflow, tool, fixture, config, and generated-artifact
        # paths remain forbidden.
        assert changed == WP165_AUTHORIZED_FILES
        assert not (changed & {
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "Cargo.toml",
            "Cargo.lock",
        })
        assert not any(
            path.startswith(
                (
                    "tools/",
                    "tests/fixtures/",
                    ".github/workflows/",
                    "config/",
                    "local_data/",
                )
            )
            for path in changed
        )
        return
    if "docs/status_entries/WP164.md" in changed:
        # WP164 authorizes source and test paths within its exact 20-file scope;
        # dependency, workflow, tool, fixture, config, and generated-artifact
        # paths remain forbidden.
        assert changed == WP164_AUTHORIZED_FILES
        assert not (changed & {
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "Cargo.toml",
            "Cargo.lock",
        })
        assert not any(
            path.startswith(
                (
                    "tools/",
                    "tests/fixtures/",
                    ".github/workflows/",
                    "config/",
                    "local_data/",
                )
            )
            for path in changed
        )
        return
    if "docs/status_entries/WP163.md" in changed:
        # WP163 authorizes source and test paths within its exact 20-file scope;
        # dependency, workflow, tool, fixture, config, and generated-artifact
        # paths remain forbidden.
        assert changed == WP163_AUTHORIZED_FILES
        assert not (changed & {
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "Cargo.toml",
            "Cargo.lock",
        })
        assert not any(
            path.startswith(
                (
                    "tools/",
                    "tests/fixtures/",
                    ".github/workflows/",
                    "config/",
                    "local_data/",
                )
            )
            for path in changed
        )
        return
    if "docs/status_entries/WP162.md" in changed:
        assert changed == WP162_AUTHORIZED_FILES
        assert not any(
            path.startswith(("tools/", "tests/fixtures/", ".github/workflows/", "local_data/"))
            for path in changed
        )
        assert not (changed & {"requirements.txt", "pyproject.toml", "package.json"})
        return
    if "docs/status_entries/WP161.md" in changed:
        assert changed == WP161_AUTHORIZED_FILES
        assert not any(
            path.startswith(("tools/", "tests/fixtures/", ".github/workflows/", "local_data/"))
            for path in changed
        )
        assert not (changed & {"requirements.txt", "pyproject.toml", "package.json"})
        return
    if "docs/status_entries/WP160.md" in changed:
        # Functional WP160 owns its exact 17-file scope; source and test paths
        # are authorized, but dependency, workflow, tool, fixture, config, and
        # generated-artifact paths remain forbidden.
        assert changed == WP160_AUTHORIZED_FILES
        assert not (changed & {
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "Cargo.toml",
            "Cargo.lock",
        })
        assert not any(
            path.startswith(
                (
                    "tools/",
                    "tests/fixtures/",
                    ".github/workflows/",
                    "config/",
                    "local_data/",
                )
            )
            for path in changed
        )
        return
    if "docs/status_entries/WP159.md" in changed:
        expected = set(json.loads(
            (ROOT / "docs/wp_specs/WP159/wp_spec.json").read_text(
                encoding="utf-8"
            )
        )["scope"]["required_changed_files"])
        assert len(expected) == 23
        assert changed == expected
        assert not any(path.startswith("src/") for path in changed)
        return
    assert not (changed & {
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        "Cargo.toml",
        "Cargo.lock",
    })
    assert not any(
        path.startswith(
            (
                "src/",
                "tools/",
                "tests/fixtures/",
                ".github/workflows/",
                "config/",
                "local_data/",
            )
        )
        for path in changed
    )


def test_exact_scope_is_docs_and_tests_only() -> None:
    changed = _changed_files()
    if "docs/status_entries/WP159.md" in changed:
        expected = set(json.loads(
            (ROOT / "docs/wp_specs/WP159/wp_spec.json").read_text(
                encoding="utf-8"
            )
        )["scope"]["required_changed_files"])
        assert len(expected) == 23
        assert changed == expected
        return
    # Once WP158 is present on origin/main, successor WPs own their own scope
    # gates; until then this branch owns the exact contract-only file set.
    merged = subprocess.run(
        ["git", "cat-file", "-e", "origin/main:docs/status_entries/WP158.md"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if merged.returncode == 0:
        return
    assert changed == EXPECTED_CHANGED


def test_wp160_implementation_addendum_is_recorded() -> None:
    # The functional WP160 realization is recorded as a clearly marked addendum
    # that does not disturb the historical WP158 contract or its twelve examples.
    assert len(_json_examples()) == 12
    section = _flat(_section(_read(DOC), "## 19. WP160 Implementation Addendum"))
    for phrase in (
        "APPEND_ONLY_LOCAL_MANIFEST_AND_DATASET_SNAPSHOT_REFERENCE_VALIDATION",
        "BOUNDED_LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION",
        "src/data_layer/point_in_time_market_research/manifest_reference.py",
        "build_dataset_snapshot_reference",
        "build_manifest_entry",
        "validate_manifest_chain",
        "DatasetSnapshotReference",
        "ManifestEntry",
        "re-derives and revalidates every supplied entry",
        "must resolve to a registry reference",
        "Input order is authoritative",
        "registered exactly once",
        "MANIFEST_SUPERSEDES_INVALID",
        "must equal the referenced",
        "implements no manifest writer, reader, verifier",
        "WP161",
    ):
        assert phrase in section
    # The addendum must not fabricate merged persistence or WP161 authority.
    lowered = section.lower()
    for forbidden in (
        "writer is implemented",
        "persistence is active",
        "wp161 is implemented",
    ):
        assert forbidden not in lowered


def test_wp161_sqlite_persistence_addendum_is_recorded() -> None:
    assert len(_json_examples()) == 12
    section = _flat(_section(_read(DOC), "## 20. WP161 Bounded SQLite Persistence Addendum"))
    for phrase in (
        "POINT_IN_TIME_LOCAL_SQLITE_MANIFEST_STORE",
        "BOUNDED_LOCAL_SQLITE_TRANSACTIONAL_APPEND_AND_VERIFIED_READ",
        "manifest_store.py",
        "initialize_manifest_store",
        "append_manifest_store_batch",
        "load_and_verify_manifest_store",
        "CREATE TABLE store_meta",
        "CREATE TABLE dataset_references",
        "CREATE TABLE manifest_entries",
        "PRAGMA user_version",
        "journal_mode=DELETE",
        "synchronous=FULL",
        "foreign_keys=ON",
        "BEGIN IMMEDIATE",
        "mode=rwc",
        "mode=rw",
        "mode=ro",
        "canonical_json_bytes",
        "sha256_hex",
        "integrity_check",
        "foreign_key_check",
        "STORE_APPEND_IDEMPOTENT",
        "65,536",
        "exposes no UPDATE or DELETE path",
        "no path, raw payload, SQL, exception, traceback, or OS detail is echoed",
        "no migration",
        "no WAL",
        "no network",
        "no live-trading behavior",
    ):
        assert phrase.lower() in section.lower()


def test_wp162_dataset_persistence_adapter_addendum_is_recorded() -> None:
    assert len(_json_examples()) == 12
    section = _flat(
        _section(_read(DOC), "## 21. WP162 Dataset Persistence Adapter Addendum")
    )
    for phrase in (
        "POINT_IN_TIME_RESEARCH_DATASET_PERSISTENCE_ADAPTER",
        "BOUNDED_DETERMINISTIC_WP156_WP157_TO_WP160_WP161_HANDOFF",
        "dataset_persistence_adapter.py",
        "persist_validated_record_batch_snapshot",
        "persist_as_of_query_snapshot",
        "DatasetPersistenceAdapterResult",
        "ADAPTER_PERSISTED",
        "ADAPTER_ALREADY_PERSISTED",
        "ADAPTER_REJECTED",
        "validate_record_batch",
        "canonical_batch_sha256",
        "query_point_in_time_record_set",
        "AUTHORITATIVE_CURRENT_STATE",
        "VISIBLE_HISTORY",
        "ENTITY_TIMELINE",
        "parameter_set_id",
        "validator_version",
        "canonical_json_bytes",
        "sha256_hex",
        "build_dataset_snapshot_reference",
        "build_manifest_entry",
        "load_and_verify_manifest_store",
        "STORE_LOADED_VERIFIED",
        "append_manifest_store_batch",
        "without writing",
        "ADAPTER_REGISTRATION_CONFLICT",
        "must already exist",
        "no wall clock",
        "no raw record or source payload",
        "no external known-parent context",
        "automatic supersede or invalidate",
        "imports no SQLite and issues no direct SQL",
        "separately gated successor work",
    ):
        assert phrase.lower() in section.lower()
    # The adapter addendum must not fabricate raw-record persistence or merge.
    lowered = section.lower()
    for forbidden in (
        "raw records themselves are stored",
        "merge authorized: yes",
        "live-trading",
    ):
        assert forbidden not in lowered
