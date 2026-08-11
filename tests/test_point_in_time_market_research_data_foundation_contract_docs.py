"""Focused WP155 point-in-time data-foundation documentation regression."""

from __future__ import annotations

import pathlib
import json
import re
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "point_in_time_market_research_data_foundation_contract.md"
STATUS = ROOT / "docs" / "status_entries" / "WP155.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"
DEFERRED = ROOT / "docs" / "deferred_items_log.md"

EXPECTED_CHANGED = {
    "docs/deferred_items_log.md",
    "docs/point_in_time_market_research_data_foundation_contract.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/status_entries/WP155.md",
    "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
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


def test_exact_foundation_label_posture_and_non_authority() -> None:
    combined = f"{_read(DOC)}\n{_read(STATUS)}\n{_read(PROJECT_STATUS)}"
    for token in (
        "POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT",
        "CONTRACT_ONLY_NO_WRITER_NO_DEPENDENCY_NO_COLLECTION",
        "Capital at risk: USD 0",
        "WP156 is not implemented",
    ):
        assert token in combined
    assert "WP155 implements no schema class, validator, fixture, writer, reader" in combined


def test_pr154_merge_lineage_is_exact() -> None:
    combined = f"{_read(DOC)}\n{_read(STATUS)}"
    for sha in (
        "555a0e7defc0b96dee0f3bd1cef629b4c422b80b",
        "d5fccf764513f79dbe561db089c967f40bee418a",
    ):
        assert sha in combined
    assert "main` equaled the PR #154 merge commit" in combined


def test_repository_inventory_records_current_identity_time_and_formats() -> None:
    inventory = _section(_read(DOC), "## 3. Current Repository Inventory", "## 4.")
    for phrase in (
        "`market_id`, `condition_id`, `token_id`",
        "`captured_at_utc`",
        "append JSONL",
        "JSON manifest",
        "lexicographic `captured_at_utc`",
        "finite chronological inspection",
        "exact duplicates",
        "JSON, JSONL, CSV, Markdown, and text",
        "no tracked lock file",
        "Arrow, Parquet, DuckDB, and Polars are not installed",
    ):
        assert phrase in inventory
    for collision in (
        "`captured_at_utc`, `snapshot_timestamp`, `snapshot_time_utc`",
        "Gamma `id`, `conditionId`, CLOB `market`, `asset_id`",
        "source order-book `hash` is not the project canonical payload hash",
    ):
        assert collision in inventory


def test_six_domain_identity_families_and_classifications_are_complete() -> None:
    identity = _section(_read(DOC), "## 4. Canonical Identity Model", "## 5.")
    flat_identity = _flat(identity)
    domain_ids = (
        "platform_id",
        "event_id",
        "market_id",
        "token_id",
        "source_id",
        "resolution_source_id",
    )
    for field in domain_ids:
        assert f"`{field}`" in identity
    for classification in (
        "source-native",
        "deterministic-derived",
        "implementation-generated",
    ):
        assert classification in identity
    assert "Display names, titles, questions" in flat_identity
    assert "both inputs are quarantined with an identity-conflict code" in flat_identity


def test_nine_observation_snapshot_version_and_lineage_ids_are_complete() -> None:
    identity = _section(_read(DOC), "### 4.2", "## 5.")
    for field in (
        "observation_id",
        "snapshot_id",
        "source_snapshot_id",
        "resolution_rule_snapshot_id",
        "ingestion_batch_id",
        "schema_id",
        "record_version_id",
        "supersedes_record_version_id",
        "lineage_parent_ids",
    ):
        assert f"`{field}`" in identity
    assert "No random UUID is required for deterministic fixtures" in _flat(identity)


def test_three_time_semantics_are_exact_and_ordered() -> None:
    text = _read(DOC)
    section = _section(text, "## 5. Observation Envelope", "## 6.")
    ordered = [
        section.index("1. `event_time`"),
        section.index("2. `observed_time`"),
        section.index("3. `ingestion_time`"),
    ]
    assert ordered == sorted(ordered)
    flat_section = _flat(section)
    for phrase in (
        "Absence is explicit",
        "is never backdated to `event_time`",
        "must not precede `observed_time`",
        "timezone-aware RFC 3339",
        "canonical UTC offset is `Z`",
        "Naive local datetimes are invalid",
        "Precision is explicit and never fabricated",
        "Filesystem modification time is never a canonical time",
    ):
        assert phrase in flat_section


def test_default_ordering_and_visibility_are_ingestion_first() -> None:
    text = _read(DOC)
    times = _section(text, "### 5.4", "## 6.")
    positions = [
        times.index("1. `ingestion_time`"),
        times.index("2. `observed_time`"),
        times.index("3. `event_time`"),
        times.index("4. `record_version_id`"),
    ]
    assert positions == sorted(positions)
    visibility = _section(text, "## 6.", "## 7.")
    for phrase in (
        "not visible to an as-of query before its",
        "`AS_OF_INGESTION_TIME` — default reproducible research visibility",
        "`AS_OF_OBSERVED_TIME` — diagnostic comparison only",
        "`EVENT_TIME_WINDOW` — a domain-time filter applied only after visibility",
        "retain only versions with `ingestion_time <= T`",
        "never admits a version ingested after `T`",
        "apply any `EVENT_TIME_WINDOW` to the already-visible result",
    ):
        assert phrase in visibility


def test_append_only_lifecycle_is_complete() -> None:
    section = _section(_read(DOC), "## 7. Append-Only Lifecycle", "## 8.")
    assert "`NO_DESTRUCTIVE_HISTORY_REWRITE`" in section
    lifecycle = (
        "RAW_CAPTURED",
        "NORMALIZED_ACCEPTED",
        "QUARANTINED",
        "SUPERSEDED",
        "RETRACTED_BY_SOURCE",
        "INVALIDATED_BY_CONTRACT",
    )
    assert [section.index(f"`{state}`") for state in lifecycle] == sorted(
        section.index(f"`{state}`") for state in lifecycle
    )
    flat_section = _flat(section)
    assert "never an in-place update" in flat_section
    assert "Retraction is not deletion" in flat_section


def test_raw_normalized_and_quarantine_boundaries_are_distinct() -> None:
    section = _section(_read(DOC), "## 8.", "## 9.")
    flat_section = _flat(section)
    for heading in ("### 8.1 Raw", "### 8.2 Normalized", "### 8.3 Quarantine"):
        assert heading in section
    for phrase in (
        "exact source bytes/content",
        "makes no validity claim",
        "Unknown fields are never silently discarded",
        "are not visible in valid research views",
        "new deterministic validation result and a new record version",
    ):
        assert phrase in flat_section


def test_duplicate_revision_correction_retraction_and_conflict_are_distinct() -> None:
    section = _section(_read(DOC), "## 9.", "## 10.")
    classifications = (
        "EXACT_DUPLICATE",
        "SEMANTIC_DUPLICATE",
        "LATE_ARRIVAL",
        "SOURCE_REVISION",
        "PROJECT_CORRECTION",
        "SOURCE_RETRACTION",
        "CONFLICT",
    )
    assert [section.index(f"`{item}`") for item in classifications] == sorted(
        section.index(f"`{item}`") for item in classifications
    )
    assert "never backdate" in section
    assert "No classification authorizes destructive replacement" in section


def test_source_and_resolution_rule_snapshot_fields_are_complete() -> None:
    section = _section(_read(DOC), "## 10.", "## 11.")
    flat_section = _flat(section)
    for field in (
        "source_snapshot_id",
        "source_id",
        "observed_time",
        "ingestion_time",
        "resolution_rule_snapshot_id",
        "event_id",
        "market_id",
        "resolution_source_id",
        "source_snapshot_id",
    ):
        assert f"`{field}`" in section
    assert "A later clarification cannot be used in an earlier analysis" in flat_section
    assert "A URL or content hash alone is not a stable source snapshot" in flat_section


def test_hash_families_and_lineage_inclusion_exclusion_are_explicit() -> None:
    section = _section(_read(DOC), "## 11.", "## 12.")
    for phrase in (
        "SHA-256",
        "UTF-8",
        "deterministic field ordering",
        "explicit nulls",
        "no NaN or Infinity",
        "raw-content hash",
        "canonical payload hash",
        "record-version hash / ID",
        "query-result hash",
        "future file/manifest hash",
        "| Included | Excluded |",
        "Lineage cycles, missing parents, duplicate parents, and hash mismatch",
    ):
        assert phrase in section


def test_schema_evolution_is_semver_fail_closed_and_append_only() -> None:
    section = _section(_read(DOC), "## 12.", "## 13.")
    flat_section = _flat(section)
    for phrase in (
        "major: incompatible field or meaning change",
        "minor: backward-compatible optional/additive change",
        "patch: clarification or validation hardening",
        "Unknown major versions fail closed",
        "Unknown fields are never silently discarded",
        "Migration is append-only and lineage-preserving",
        "WP155 implements no migration",
    ):
        assert phrase in flat_section


def test_parquet_arrow_and_partition_decisions_are_exact() -> None:
    section = _section(_read(DOC), "## 13.", "## 14.")
    for phrase in (
        "`PARQUET_ARROW_PREFERRED_BUT_NOT_INSTALLED`",
        "one dataset per record family and schema major",
        "immutable files referenced by a manifest/catalog",
        "`record_family / schema_major / ingestion_date_utc`",
        "Raw question/title, URL, wallet address, token ID, market ID by default",
        "WP155 installs nothing and creates no writer or dataset",
    ):
        assert phrase in section


def test_duckdb_polars_benchmark_contract_is_correctness_first() -> None:
    section = _section(_read(DOC), "## 14.", "## 15.")
    flat_section = _flat(section)
    assert "`BENCHMARK_REQUIRED_NO_ADOPTION_DECISION`" in section
    for fixture in (
        "out-of-order event times",
        "late arrivals",
        "exact and semantic duplicates",
        "source revisions",
        "project corrections",
        "source retractions",
        "conflicting sources",
        "quarantine cases",
        "resolution-rule changes",
    ):
        assert fixture in flat_section
    for operation in (
        "as-of reconstruction",
        "event-time window after visibility",
        "latest visible version per entity",
        "correction chain",
        "deterministic result hash",
        "predicate filtering",
        "bounded event/market/token/source joins",
    ):
        assert operation in flat_section
    assert "correctness is the primary gate" in flat_section.lower()
    assert "DuckDB and Polars remain uninstalled" in flat_section


def test_validation_states_failures_and_no_look_ahead_matrix_are_complete() -> None:
    text = _read(DOC)
    validation = _section(text, "## 15.", "## 16.")
    for state in (
        "VALID",
        "VALID_WITH_WARNINGS",
        "QUARANTINED",
        "REJECTED_CONTRACT",
        "UNSUPPORTED_SCHEMA",
        "CONFLICT_REQUIRES_REVIEW",
    ):
        assert f"`{state}`" in validation
    assert "Failure is closed, deterministic, ordered, and bounded" in validation

    matrix = _section(text, "## 16.", "## 17.")
    for code in (
        "AS_OF_LOOK_AHEAD_VIOLATION",
        "CORRECTION_VISIBILITY_VIOLATION",
        "SOURCE_SNAPSHOT_AFTER_CUTOFF",
        "FUTURE_SELECTION_KNOWLEDGE",
        "INVALID_TIME_SOURCE",
        "MISSING_AS_OF_CUTOFF",
        "VISIBILITY_FILTER_MISSING",
    ):
        assert f"`{code}`" in matrix


def test_ai_hermes_and_external_tools_have_no_data_authority() -> None:
    section = _section(_read(DOC), "## 17.", "## 18.")
    flat_section = _flat(section)
    for phrase in (
        "deterministic data layer exclusively owns",
        "AI/Hermes may not create canonical IDs",
        "select accepted versions",
        "resolve conflicts",
        "promote quarantine data",
        "Arrow, Parquet, DuckDB, Polars, and external SDKs may not become authority",
    ):
        assert phrase in flat_section


def test_official_sources_and_observation_date_are_recorded() -> None:
    section = _section(_read(DOC), "## 20.", "## 21.")
    assert "Observed 2026-07-26" in section
    for url in (
        "https://arrow.apache.org/docs/format/Columnar.html",
        "https://parquet.apache.org/docs/",
        "https://duckdb.org/docs/stable/data/parquet/overview",
        "https://docs.pola.rs/user-guide/lazy/",
        "https://docs.polymarket.com/market-data/overview",
        "https://docs.polymarket.com/api-reference/events/list-events",
        "https://docs.polymarket.com/api-reference/markets/list-markets",
        "https://docs.polymarket.com/api-reference/market-data/get-order-book",
        "https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets",
        "https://docs.polymarket.com/concepts/resolution",
    ):
        assert url in section
    assert "do not supply repository semantics" in section


def test_deferred_reconciliation_is_contract_only_and_ten_items_are_open() -> None:
    log = _read(DEFERRED)
    section = _section(
        log,
        "## WP155 Point-In-Time Market Research Data Foundation Deferred Items",
        "## WP156 Bounded Point-In-Time Validator Deferred-Item Reconciliation",
    )
    flat_section = _flat(section)
    assert "WP154-D002 is `RESOLVED_CONTRACT_ONLY`" in flat_section
    assert "No schema class, writer, dataset, dependency" in flat_section
    assert "WP154-D003 remains `OPEN`" in flat_section
    ids = re.findall(r"^\| (WP155-D\d{3}) \|", section, re.MULTILINE)
    assert ids == [f"WP155-D{index:03d}" for index in range(1, 11)]
    header = next(line for line in section.splitlines() if line.startswith("| ID |"))
    for field in (
        "Trigger",
        "Prerequisite",
        "Forbidden early interpretation",
        "Separate approval requirement",
    ):
        assert field in header
    assert section.count("| YES —") == 10


def test_project_status_reconciles_wp155_and_has_one_wp156_review_target() -> None:
    project = _read(PROJECT_STATUS)
    current = next(
        line for line in project.splitlines() if line.startswith("- Current phase:")
    )
    merged = next(
        line for line in project.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP156" in merged
    assert "WP154" in merged
    assert "WP155" in merged
    assert current.count("sole draft PR review target") == 1
    assert (
        "WP154 adoption architecture, dependency registry and alpha-factory roadmap lock-in sole review target"
        not in project
    )
    # WP156 is merged; the current review target gates the next WP forward.
    assert "WP161" in current
    assert "Ready for review: NO" in current


def test_repo_truth_index_registers_canonical_status_and_focused_test() -> None:
    index = _read(INDEX)
    for path in (
        "docs/point_in_time_market_research_data_foundation_contract.md",
        "docs/status_entries/WP155.md",
        "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    ):
        assert path in index


def test_status_fragment_is_stable_model_d_and_has_required_sections() -> None:
    status = _read(STATUS)
    headings = (
        "## Package Identity",
        "## Authorization Basis",
        "## Authority / Non-Authority Posture",
        "## Hard Merge Gate",
        "## Context Budget",
        "## Repository Inventory",
        "## Contract Decisions",
        "## Append-Only And Boundary Result",
        "## Hash, Lineage, And Schema Result",
        "## Compatibility / Impossibility Check",
        "## Deferred Items",
        "## Output Surface And Scope",
        "## Requirement-To-Evidence Traceability",
        "## Validation",
        "## Model D Evidence",
        "## Stable Metadata",
        "## Follow-Up Classification",
        "## Next Phase",
        "## Ready For Review",
    )
    positions = [status.index(heading) for heading in headings]
    assert positions == sorted(positions)
    assert "PR: see GitHub PR metadata and PR body." in status
    assert "Current live PR head: see GitHub PR metadata and PR body" in status
    assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", status) is None
    assert "TBD" not in status
    assert "stable and non-self-referential" in status


def test_false_capability_statement_matrix_is_rejected() -> None:
    text = _flat(_read(DOC)).lower()
    forbidden_false_claims = (
        "wp155 implements the data layer.",
        "parquet storage is active.",
        "duckdb is adopted.",
        "polars is installed.",
        "historical records are updated in place.",
        "corrections apply retroactively.",
        "event time determines availability.",
        "latest data is safe for backtesting.",
        "quarantine data is valid research data.",
        "ai/hermes may resolve conflicts.",
        "wp155 authorizes market-data collection.",
        "wp155 enables paper trading.",
        "wp156 is implemented.",
    )
    for phrase in forbidden_false_claims:
        assert phrase not in text
    for safe_phrase in (
        "wp155 does not implement the data layer.",
        "parquet storage is not active.",
        "duckdb is not adopted.",
        "polars is not installed.",
        "historical records are not updated in place.",
        "corrections do not apply retroactively.",
        "quarantine data is not valid research data.",
        "wp156 is not implemented.",
    ):
        assert safe_phrase in text


_WP160_AUTHORIZED_FILES = {
    "docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/status_entries/WP160.md",
    "src/data_layer/point_in_time_market_research/__init__.py",
    "src/data_layer/point_in_time_market_research/manifest_reference.py",
    "tests/data_layer/point_in_time_market_research/test_as_of_query.py",
    "tests/data_layer/point_in_time_market_research/test_manifest_reference.py",
    "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
    "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    "tests/test_append_only_local_manifest_and_dataset_snapshot_reference_contract_docs.py",
    "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
    "tests/test_human_review_label_workflow_docs.py",
    "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
    "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
    "tests/test_project_status_docs.py",
    "tests/test_wallet_intelligence_architecture_contract_docs.py",
}

_WP161_AUTHORIZED_FILES = {
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


def test_exact_nine_file_scope_and_no_protected_change() -> None:
    if "docs/status_entries/WP161.md" in _changed_files():
        assert _changed_files() == _WP161_AUTHORIZED_FILES
        return
    if "docs/status_entries/WP160.md" in _changed_files():
        # Functional WP160 owns its exact 17-file scope; the exact-set assertion
        # preserves every protected-path guarantee for this branch.
        assert _changed_files() == _WP160_AUTHORIZED_FILES
        return
    merged_status = subprocess.run(
        ["git", "cat-file", "-e", "origin/main:docs/status_entries/WP155.md"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if merged_status.returncode == 0:
        # The exact nine-file assertion is a WP155 branch gate. Once WP155 is
        # present on origin/main, successor WPs own their own exact-scope gates.
        return
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
    assert changed == EXPECTED_CHANGED
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
    assert not changed & {
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        "Cargo.toml",
        "Cargo.lock",
    }


def test_wp156_has_not_been_implemented() -> None:
    assert not (ROOT / "src" / "data_layer" / "point_in_time_observation.py").exists()
    assert not (ROOT / "tests" / "fixtures" / "point_in_time_observations").exists()
    # WP155's immutable historical surfaces correctly state their own
    # pre-WP156 implementation state.
    combined = f"{_read(DOC)}\n{_read(STATUS)}"
    assert "WP156 requires separate approval" in combined
    assert "WP156 is not implemented." in combined
