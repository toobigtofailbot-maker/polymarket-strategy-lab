"""Focused WP158 append-only local manifest and dataset snapshot reference
contract documentation regression.

WP158 is a contract-only package: documentation, status, repo truth, deferred
registration, and this focused test. It adds no `src` implementation, no writer,
no reader, no persistence, no dependency, no workflow, and no local/generated
artifact.
"""

from __future__ import annotations

import pathlib
import re
import subprocess


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
        "immutable, ordered, unique, and non-overlapping",
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
    flat = _flat(section)
    for included in (
        "schema ID and schema version",
        "derivation mode",
        "validated-batch SHA-256",
        "ordered ordinary record-version IDs",
        "ordered review-conflict record-version IDs",
        "query-spec SHA-256 or null",
        "cutoff mode or null",
        "result view or null",
        "validator version",
        "parameter-set ID",
        "human-review-required",
        "advisory-only",
        "no-execution-authority",
    ):
        assert included in flat
    for excluded in (
        "the self ID",
        "`created_from_manifest_entry_id`",
        "storage metadata",
        "all runtime / environment values",
    ):
        assert excluded in flat
    for canonical in (
        "canonical UTF-8 JSON",
        "explicit nulls",
        "deterministic array order",
        "no NaN or Infinity",
        "one-field hash sensitivity",
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
    flat = _flat(section)
    for included in (
        "manifest ID",
        "sequence number",
        "previous entry ID or null",
        "entry kind",
        "dataset-reference ID",
        "supersedes ID or null",
        "reference state",
        "reason code",
        "effective time",
        "parameter-set ID",
        "human-review-required",
    ):
        assert included in flat
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
        "| >0 | exact prior | SUPERSEDE | earlier same-chain entry | valid |",
        "| >0 | exact prior | SUPERSEDE | null/unknown/future | reject |",
        "| >0 | exact prior | INVALIDATE | earlier same-chain entry | valid with review |",
        "| >0 | exact prior | INVALIDATE | null/unknown/future | reject |",
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
        "| record-ID tuples | duplicate/overlap/wrong type | FIELD_VALUE_INVALID | no |",
        "| query fields | partial mode combination | REFERENCE_MODE_MISMATCH | no |",
        "| sequence | bool/negative/gap/duplicate | MANIFEST_SEQUENCE_INVALID | no |",
        "| previous ID | unknown/wrong manifest | MANIFEST_PREVIOUS_ENTRY_UNKNOWN | no |",
        "| supersedes | null/unknown/future/self | MANIFEST_SUPERSEDES_INVALID | no |",
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


def test_twelve_deterministic_examples_are_present_and_illustrative() -> None:
    section = _section(_read(DOC), "## 14. Deterministic Contract Examples", "## 15.")
    assert "illustrative and non-runtime" in section
    assert "fixed synthetic IDs only" in section
    numbers = re.findall(r"^(\d+)\. ", section, re.MULTILINE)
    assert numbers == [str(n) for n in range(1, 13)]
    flat = _flat(section)
    for concept in (
        "Validated ordinary batch reference",
        "As-of current-state reference",
        "Empty valid as-of result reference",
        "Review-conflict-only reference",
        "Mixed ordinary/review reference",
        "Genesis registration",
        "Second registration",
        "Supersede entry",
        "Invalidate entry",
        "Sequence gap",
        "Cross-manifest previous ID",
        "Review-conflict authority mixing",
    ):
        assert concept in flat


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
    assert "WP158" in current
    assert "WP157" in merged
    assert current.count("sole review target") == 1
    assert "WP159 requires separate approval" in current
    assert "WP159 implemented: NO" in current
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
