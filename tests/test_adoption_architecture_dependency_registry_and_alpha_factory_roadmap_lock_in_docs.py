"""Focused WP154 architecture/adoption-roadmap documentation regression."""

from __future__ import annotations

import pathlib
import json
import re
import subprocess


ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = (
    ROOT
    / "docs"
    / "adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in.md"
)
STATUS = ROOT / "docs" / "status_entries" / "WP154.md"
WP155_STATUS = ROOT / "docs" / "status_entries" / "WP155.md"
WP156_STATUS = ROOT / "docs" / "status_entries" / "WP156.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"
DEFERRED = ROOT / "docs" / "deferred_items_log.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, heading: str, next_heading: str) -> str:
    return text.split(heading, 1)[1].split(next_heading, 1)[0]


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def test_wp154_canonical_status_and_repo_truth_surfaces_exist() -> None:
    for path in (DOC, STATUS, PROJECT_STATUS, INDEX, DEFERRED):
        assert path.is_file()


def test_exact_finished_system_label_and_decision_posture() -> None:
    doc = _read(DOC)
    status = _read(STATUS)
    project = _read(PROJECT_STATUS)
    label = "MEASURABLE_ALPHA_FACTORY_PLUS_DETERMINISTIC_TRADING_KERNEL"
    assert label in doc
    assert label in status
    assert label in project
    assert "DECISION_AND_ROADMAP_ONLY" in doc
    assert "External dependencies installed or activated:\n0" in doc


def test_pr153_merge_lineage_is_exact() -> None:
    doc = _read(DOC)
    status = _read(STATUS)
    for value in (
        "53085b79aff84ab717af8be373dd70746ba20d11",
        "471239088cc91a90bc0002f86cc429163027eeeb",
        "current `main` equals the PR #153 merge commit",
    ):
        assert value in doc
    assert "EQUALS_PR153_MERGE_COMMIT" in status


def test_post_wp153_inventory_preserves_synthetic_and_absent_boundaries() -> None:
    section = _section(
        _read(DOC),
        "## 4. Repo Capability Inventory",
        "## 5. Locked Finished-System Architecture",
    )
    for state in (
        "IMPLEMENTED_AND_TESTED",
        "IMPLEMENTED_LIMITED_OR_MANUAL",
        "CONTRACT_OR_RUNBOOK_ONLY",
        "SYNTHETIC_TEST_ONLY",
        "ABSENT",
        "EXTERNALLY_PROPOSED",
        "SEPARATELY_GATED",
    ):
        assert state in section
    for phrase in (
        "zero real workflow runs",
        "zero real metrics measured",
        "replay/fill simulation | `ABSENT`",
        "portfolio/accounting/PnL | `ABSENT`",
        "deterministic risk/safe mode/kill switch | `ABSENT`",
        "reconciliation | `ABSENT`",
        "observability and operations | `ABSENT`",
    ):
        assert phrase in section


def test_authority_split_is_explicit_and_ai_hermes_has_no_control_authority() -> None:
    section = _section(
        _read(DOC),
        "## 5. Locked Finished-System Architecture",
        "## 6. Locked Alpha-Factory Lineage",
    )
    for role in (
        "market and source research",
        "hypothesis generation",
        "experiment-design suggestions",
        "critique",
        "post-mortem and",
        "operator decision support",
    ):
        assert role in section
    flat = _flat(section)
    for verb in (
        "execute",
        "validate",
        "sign",
        "transition",
        "schedule",
        "approve",
        "promote",
        "authorize",
    ):
        assert verb in flat
    assert (
        "AI/Hermes cannot execute, validate, sign, transition, schedule, approve, promote, or authorize."
        in flat
    )
    for authority in (
        "canonical data identity",
        "point-in-time data validation",
        "schema validation",
        "experiment registration",
        "candidate-state transitions",
        "replay and fill simulation",
        "accounting and PnL",
        "portfolio and risk limits",
        "credentials and secrets",
        "scheduler and runtime controls",
        "restricted-live eligibility",
        "live safety and kill switches",
    ):
        assert authority in section


def test_exact_nine_stage_lineage_is_unique_and_ordered() -> None:
    section = _section(
        _read(DOC),
        "## 6. Locked Alpha-Factory Lineage",
        "## 7. Locked Adoption Sequence",
    )
    expected = [
        "MARKET_OBSERVATION",
        "RESEARCH_CANDIDATE",
        "ALPHA_HYPOTHESIS",
        "PREREGISTERED_EXPERIMENT",
        "OUT_OF_SAMPLE_EVIDENCE",
        "COST_ADJUSTED_RESULT",
        "PAPER_ELIGIBLE_STRATEGY_PROPOSAL",
        "PAPER_EVIDENCE",
        "RESTRICTED_LIVE_ELIGIBILITY",
    ]
    actual = re.findall(r"^\d+\. `([A-Z_]+)`$", section, re.MULTILINE)
    assert actual == expected
    assert len(actual) == len(set(actual)) == 9
    for stage in expected:
        assert f"| `{stage}` |" in section
    assert "exact, ordered, and non-skippable" in section
    assert "Every transition requires deterministic" in section


def test_every_lineage_stage_has_fields_evidence_and_forbidden_interpretation() -> None:
    section = _section(
        _read(DOC),
        "## 6. Locked Alpha-Factory Lineage",
        "## 7. Locked Adoption Sequence",
    )
    rows = [
        line
        for line in section.splitlines()
        if re.match(r"^\| `[A-Z_]+` \|", line)
    ]
    assert len(rows) == 9
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        assert len(cells) == 4
        assert all(cells)


def test_exact_adoption_phases_a_through_j_are_unique_and_ordered() -> None:
    section = _section(
        _read(DOC),
        "## 7. Locked Adoption Sequence",
        "## 8. Locked First Alpha-Research Priorities",
    )
    actual = re.findall(r"^### PHASE ([A-J]) — (.+)$", section, re.MULTILINE)
    assert [phase for phase, _ in actual] == list("ABCDEFGHIJ")
    assert [title for _, title in actual] == [
        "POINT-IN-TIME DATA FOUNDATION",
        "OFFICIAL SDK COMPATIBILITY AND DATA-ADAPTER DECISION",
        "MARKET-RELATIONSHIP AND RESOLUTION-INTEGRITY GRAPH",
        "PREREGISTRATION AND EXPERIMENT REGISTRY",
        "FIRST FALSIFIABLE ALPHA PROGRAMS",
        "ISOLATED NAUTILUSTRADER SPIKE",
        "PAPER CORE",
        "OBSERVABILITY",
        "PREFECT RESEARCH-JOB ORCHESTRATION",
        "RESTRICTED LIVE",
    ]


def test_exact_five_alpha_priorities_are_unique_and_ordered() -> None:
    section = _section(
        _read(DOC),
        "## 8. Locked First Alpha-Research Priorities",
        "## 9. Dependency / Repository Adoption Registry",
    )
    actual = re.findall(r"^### PRIORITY ([1-5]) — ([A-Z0-9_]+)$", section, re.MULTILINE)
    assert actual == [
        ("1", "RESOLUTION_SOURCE_INTEGRITY_AND_RELATED_MARKET_CONSTRAINTS"),
        ("2", "WALLET_INTELLIGENCE_AND_BEHAVIOR_PERSISTENCE"),
        ("3", "CALIBRATION_AND_MARKET_DISAGREEMENT"),
        ("4", "MAKER_RESEARCH_AFTER_FILL_EVIDENCE"),
        ("5", "FAST_MARKET_INSTRUMENTATION_ONLY"),
    ]


def test_registry_contains_exact_required_candidate_ids_once_and_in_order() -> None:
    section = _section(
        _read(DOC),
        "## 9. Dependency / Repository Adoption Registry",
        "## 10. Primary Source Observation Register",
    )
    expected = [
        "POLYMARKET_PY_SDK",
        "POLYMARKET_PY_CLOB_V1",
        "POLYMARKET_PY_CLOB_V2",
        "POLYMARKET_RUST_V2",
        "POLYMARKET_REAL_TIME_DATA_CLIENT",
        "POLYMARKET_POLY_MARKET_MAKER",
        "PARQUET_ARROW",
        "DUCKDB",
        "POLARS",
        "MLFLOW",
        "NETWORKX",
        "NAUTILUSTRADER",
        "PREFECT",
        "OPENTELEMETRY",
        "PROMETHEUS_GRAFANA",
    ]
    actual = re.findall(r"^\| `([A-Z0-9_]+)` \|", section, re.MULTILINE)
    assert actual == expected
    assert len(actual) == len(set(actual)) == 15


def test_registry_has_required_fields_and_adoption_semantics() -> None:
    section = _section(
        _read(DOC),
        "## 9. Dependency / Repository Adoption Registry",
        "## 10. Primary Source Observation Register",
    )
    header = next(line for line in section.splitlines() if line.startswith("| candidate ID"))
    for field in (
        "candidate ID",
        "project/repository",
        "category / current official status",
        "proposed use",
        "prohibited use",
        "adoption decision / phase",
        "prerequisites",
        "license",
        "security/maintenance checks",
        "benchmark/spike",
        "exit/rejection criteria",
        "separate WP",
    ):
        assert field in header
    for statement in (
        "LISTED != APPROVED",
        "EVALUATE != ADOPT",
        "ADOPT != ACTIVATE",
        "ACTIVATE != AUTHORIZE",
        "PAPER_ELIGIBLE != PAPER_AUTHORIZED",
        "RESTRICTED_LIVE_ELIGIBLE != LIVE_AUTHORIZED",
    ):
        assert statement in section


def test_polymarket_sdk_status_is_current_caveated_and_not_activated() -> None:
    section = _section(
        _read(DOC),
        "## 9. Dependency / Repository Adoption Registry",
        "## 10. Primary Source Observation Register",
    )
    assert "repository archived" in section
    assert "DO_NOT_ADOPT_FOR_NEW_WORK" in section
    assert "developer-tooling docs call it beta" in section
    assert "package 0.2.0 metadata says production/stable" in section
    assert "EVALUATE_OFFICIAL_UNIFIED_SDK" in section
    assert "no activation" in section
    assert "No row is an installation or activation decision" in section


def test_nautilus_prefect_mlflow_and_observability_remain_separately_gated() -> None:
    doc = _read(DOC)
    for phrase in (
        "ISOLATED_COMPATIBILITY_SPIKE_AFTER_DATA_AND_CONTRACT_PREREQUISITES",
        "DEFER_UNTIL_IDEMPOTENT_RESEARCH_JOBS_EXIST",
        "EVALUATE_EXPERIMENT_METADATA_AND_ARTIFACT_TRACKING",
        "PREFERRED_INSTRUMENTATION_STANDARD_CANDIDATE",
        "PREFERRED_LATER_METRICS_DASHBOARD_ALERTING_CANDIDATES",
    ):
        assert phrase in doc
    assert "MLflow cannot become\npromotion authority" in _read(STATUS)


def test_sources_use_official_urls_and_exact_observation_date() -> None:
    section = _section(
        _read(DOC),
        "## 10. Primary Source Observation Register",
        "## 11. Tool-Adoption Decision Test",
    )
    urls = (
        "https://github.com/Polymarket/py-sdk",
        "https://github.com/Polymarket/py-clob-client",
        "https://github.com/Polymarket/py-clob-client-v2",
        "https://github.com/Polymarket/rs-clob-client-v2",
        "https://docs.polymarket.com/dev-tooling",
        "https://docs.polymarket.com/v2-migration",
        "https://duckdb.org/docs/stable/data/parquet/overview",
        "https://docs.pola.rs/user-guide/lazy/optimizations/",
        "https://arrow.apache.org/docs/format/Columnar.html",
        "https://parquet.apache.org/docs/overview/motivation/",
        "https://mlflow.org/docs/latest/tracking",
        "https://github.com/networkx/networkx",
        "https://nautilustrader.io/docs/latest/concepts/overview/",
        "https://docs.prefect.io/v3/concepts/deployments",
        "https://opentelemetry.io/docs/languages/python/",
        "https://prometheus.io/docs/introduction/overview/",
        "https://github.com/grafana/grafana",
    )
    for url in urls:
        assert url in section
    source_rows = [
        line
        for line in section.splitlines()
        if line.startswith("| ") and "https://" in line
    ]
    assert len(source_rows) >= 20
    assert all(line.endswith("| 2026-07-26 |") for line in source_rows)


def test_tool_adoption_decision_test_has_exact_fifteen_questions() -> None:
    section = _section(
        _read(DOC),
        "## 11. Tool-Adoption Decision Test",
        "## 12. Roadmap Lock-In",
    )
    questions = re.findall(r"^(\d+)\. .+\?$", section, re.MULTILINE)
    assert questions == [str(index) for index in range(1, 16)]
    assert "No dependency may be added" in section


def test_roadmap_ranges_are_explicitly_planning_estimates() -> None:
    section = _section(
        _read(DOC),
        "## 12. Roadmap Lock-In",
        "## 13. Explicit Deferrals",
    )
    for phrase in (
        "planning estimates, not commitments",
        "approximately 6–10 WPs after WP154",
        "approximately 12–20 additional WPs",
        "approximately 20–35 additional WPs",
        "approximately 35–55 WPs remaining",
        "approximately 45–70 WPs remaining",
        "approximately 12–18 months",
        "approximately 18–24 months",
    ):
        assert phrase in section


def test_all_fifteen_deferred_items_are_registered_with_required_fields() -> None:
    log = _read(DEFERRED)
    section = _section(
        log,
        "## WP154 Adoption Architecture, Dependency Registry And Alpha-Factory Roadmap Deferred Items",
        "## WP155 Point-In-Time Market Research Data Foundation Deferred Items",
    )
    ids = re.findall(r"^\| (WP154-D\d{3}) \|", section, re.MULTILINE)
    assert ids == [f"WP154-D{index:03d}" for index in range(1, 16)]
    header = next(line for line in section.splitlines() if line.startswith("| ID |"))
    for field in (
        "Trigger",
        "Prerequisite",
        "Forbidden early interpretation",
        "Separate approval requirement",
    ):
        assert field in header
    assert section.count("| YES —") == 15


def test_repo_truth_index_registers_canonical_status_and_focused_test() -> None:
    index = _read(INDEX)
    for path in (
        "docs/adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in.md",
        "docs/status_entries/WP154.md",
        "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
    ):
        assert path in index


def test_project_status_reconciles_wp153_and_has_one_wp154_review_target() -> None:
    project = _read(PROJECT_STATUS)
    current = next(
        line for line in project.splitlines() if line.startswith("- Current phase:")
    )
    merged = next(
        line for line in project.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP153" in merged
    assert current.count("current review target") == 1
    assert (
        "WP153 bounded local research workflow value measurement dry run and receipt review sole review target"
        not in project
    )
    assert (
        "LOCAL_OFFLINE_DETERMINISTIC_SYNTHETIC_DRY_RUN_AND_RECEIPT_REVIEW_REVIEW_TARGET"
        not in project
    )
    if WP156_STATUS.exists():
        assert "WP156" in merged
        assert "WP154" in merged
        assert "WP155" in merged
        # WP156 is merged; the current review target gates the next WP forward.
        assert "WP161" in current
        assert "Ready for review: YES" in current
    elif WP155_STATUS.exists():
        assert "WP155" in current
        assert "WP154" in merged
        assert (
            "DOCS_STATUS_TESTS_ONLY_ADOPTION_ARCHITECTURE_DEPENDENCY_REGISTRY_ALPHA_FACTORY_ROADMAP_MERGED"
            in project
        )
        assert "WP156 requires separate approval" in current
    else:
        assert "WP154" in current
        assert "WP154" not in merged
        assert (
            "DOCS_STATUS_TESTS_ONLY_ADOPTION_ARCHITECTURE_DEPENDENCY_REGISTRY_ALPHA_FACTORY_ROADMAP_REVIEW_TARGET"
            in project
        )
        assert "WP155 requires separate approval" in current


def test_status_fragment_is_stable_and_contains_required_execution_package_sections() -> None:
    status = _read(STATUS)
    headings = [
        "## Package Identity",
        "## Authorization Basis",
        "## Authority / Non-Authority Posture",
        "## Hard Merge Gate",
        "## Context Budget",
        "## Post-WP153 Capability Inventory",
        "## Finished-System Architecture Lock",
        "## Exact Alpha Lineage",
        "## Adoption Sequence And Alpha Priorities",
        "## Dependency Registry Decision",
        "## Roadmap And Planning Estimates",
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
    ]
    positions = [status.index(heading) for heading in headings]
    assert positions == sorted(positions)
    assert "PR: see GitHub PR metadata and PR body." in status
    assert "Current live PR head: see GitHub PR metadata and PR body" in status
    assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", status) is None
    assert "TBD" not in status


def test_false_capability_wording_negative_matrix_and_safe_wording_positive() -> None:
    text = _flat(_read(DOC)).lower()
    forbidden_false_claims = (
        "wp154 proves alpha",
        "wp154 guarantees profitability",
        "automatic hypothesis promotion is authorized",
        "ai/hermes may execute orders",
        "ai/hermes validates state transitions",
        "dependencies installed by wp154",
        "dependencies are active in wp154",
        "paper trading is ready now",
        "live trading is ready now",
        "credentials are activated",
        "product network activation is authorized",
        "trading scheduler authorization is granted",
        "wp155 is implemented",
    )
    for phrase in forbidden_false_claims:
        assert phrase not in text
    for safe_phrase in (
        "a hypothesis is not proven alpha",
        "research value is not profitability",
        "automatic copy trading is forbidden",
        "no row is an installation or activation decision",
        "wp154 does not implement wp155",
    ):
        assert safe_phrase in text


def test_no_dependency_paper_live_provider_network_or_wp155_authority_is_granted() -> None:
    doc = _read(DOC)
    for phrase in (
        "Dependency/lock changes: 0",
        "Paper-trading authority granted:\nNO",
        "Live-trading authority granted:\nNO",
        "No external source code was copied",
        "Provider/model/Hermes runtime calls: 0",
        "Scheduler/background tasks added: 0",
        "WP155 implemented:\nNO",
    ):
        assert phrase in doc or phrase in _read(STATUS)
    wp155_doc = ROOT / "docs" / "point_in_time_market_research_data_foundation_contract.md"
    if WP155_STATUS.exists():
        assert wp155_doc.is_file()
        assert "WP155 does not implement the data layer." in _read(wp155_doc)
        assert "WP156 is not implemented." in _read(wp155_doc)
    else:
        assert not wp155_doc.exists()


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

_WP162_AUTHORIZED_FILES = {
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


def test_exact_eight_file_scope_and_no_protected_implementation_change() -> None:
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
    changed = {
        line
        for line in (diff.stdout + untracked.stdout).splitlines()
        if line
    }
    if "docs/status_entries/WP162.md" in changed:
        assert changed == _WP162_AUTHORIZED_FILES
        return
    if "docs/status_entries/WP161.md" in changed:
        assert changed == _WP161_AUTHORIZED_FILES
        return
    if "docs/status_entries/WP160.md" in changed:
        # Functional WP160 owns its exact 17-file scope (fifteen authorized files
        # plus the two explicitly user-authorized package-export compatibility
        # regressions). The exact-set assertion preserves every protected-path
        # guarantee for this branch.
        assert changed == _WP160_AUTHORIZED_FILES
        return
    if "docs/status_entries/WP159.md" in changed:
        expected = set(json.loads(
            (ROOT / "docs/wp_specs/WP159/wp_spec.json").read_text(
                encoding="utf-8"
            )
        )["scope"]["required_changed_files"])
        assert len(expected) == 23
        assert changed == expected
        return
    if "docs/status_entries/WP158.md" in changed:
        assert changed == {
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
    elif "docs/status_entries/WP157.md" in changed:
        assert changed == {
            "docs/bounded_in_memory_point_in_time_record_set_reconstruction_and_as_of_query_implementation.md",
            "docs/deferred_items_log.md",
            "docs/project_status.md",
            "docs/repo_truth_index.md",
            "docs/status_entries/WP157.md",
            "src/data_layer/point_in_time_market_research/__init__.py",
            "src/data_layer/point_in_time_market_research/as_of_query.py",
            "src/data_layer/point_in_time_market_research/as_of_synthetic_cases.py",
            "src/data_layer/point_in_time_market_research/records.py",
            "tests/data_layer/point_in_time_market_research/test_as_of_query.py",
            "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
            "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
            "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
            "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
            "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
            "tests/test_project_status_docs.py",
            "tests/test_wallet_intelligence_architecture_contract_docs.py",
        }
    elif "docs/status_entries/WP156.md" in changed:
        assert changed == {
            "docs/deferred_items_log.md",
            "docs/point_in_time_observation_schema_validator_and_synthetic_fixture_implementation.md",
            "docs/project_status.md",
            "docs/repo_truth_index.md",
            "docs/status_entries/WP156.md",
            "src/data_layer/point_in_time_market_research/__init__.py",
            "src/data_layer/point_in_time_market_research/records.py",
            "src/data_layer/point_in_time_market_research/synthetic_corpus.py",
            "tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py",
            "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
            "tests/test_architecture_boundaries.py",
            "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
            "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
            "tests/test_point_in_time_market_research_data_foundation_contract_docs.py",
            "tests/test_project_status_docs.py",
            "tests/test_wallet_intelligence_architecture_contract_docs.py",
        }
    elif "docs/status_entries/WP155.md" in changed:
        assert changed == {
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
    elif changed:
        assert changed == {
            "docs/adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in.md",
            "docs/deferred_items_log.md",
            "docs/project_status.md",
            "docs/repo_truth_index.md",
            "docs/status_entries/WP154.md",
            "tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py",
            "tests/test_local_research_workflow_value_measurement_harness_contract_docs.py",
            "tests/test_project_status_docs.py",
        }
    assert not any(
        path.startswith(("tools/", "tests/fixtures/", ".github/workflows/", "config/"))
        or (
            path.startswith("src/")
            and not path.startswith("src/data_layer/point_in_time_market_research/")
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
