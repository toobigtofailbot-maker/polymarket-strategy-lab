"""Focused docs tests for the WP166 scalable-lineage-delta/keyset canonical contract."""

from __future__ import annotations

import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = (
    REPO_ROOT / "docs" / "scalable_lineage_delta_and_keyset_population_contract.md"
)
MODULE = (
    REPO_ROOT
    / "src"
    / "data_layer"
    / "point_in_time_market_research"
    / "polymarket_scaled_population.py"
)


def _contract() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def test_contract_document_exists() -> None:
    assert CONTRACT.is_file()
    assert MODULE.is_file()


def test_label_and_posture_are_exact() -> None:
    text = _contract()
    assert "POLYMARKET_SCALABLE_KEYSET_LINEAGE_DELTA_POPULATION" in text
    assert (
        "MANUAL_ONE_PAGE_KEYSET_GET_ONLY_EXTERNAL_PARENT_COMMITTED_NO_TRADING_AUTHORITY"
        in text
    )


def test_v2_reference_schema_facts_are_documented() -> None:
    text = _contract()
    assert 'DATASET_REFERENCE_SCHEMA_VERSION_LINEAGE = "2.0.0"' in text
    assert 'DATASET_REFERENCE_SUPPORTED_SCHEMA_VERSIONS = ("1.0.0", "2.0.0")' in text
    assert "LINEAGE_DELTA_RECORD_BATCH" in text
    assert "external_parent_record_version_ids" in text
    flat = _flat(text)
    assert "byte-for-byte identity" in flat
    assert "created_from_manifest_entry_id" in flat


def test_known_parent_records_semantics_documented() -> None:
    flat = _flat(_contract())
    assert "known_parent_records" in flat
    assert "always names the CURRENT records only" in flat
    assert "sorted(parent ids)" in flat


def test_chain_and_adapter_error_codes_documented() -> None:
    text = _contract()
    for code in (
        "REFERENCE_PARENT_CONTEXT_INVALID",
        "REFERENCE_PARENT_CONTEXT_UNCOMMITTED",
        "ADAPTER_PARENT_CONTEXT_INVALID",
        "ADAPTER_PARENT_CONTEXT_UNREGISTERED",
        "ADAPTER_PARENT_CONTEXT_HEAD_CHANGED",
    ):
        assert code in text
    assert "4096" in text


def test_no_sqlite_migration_documented() -> None:
    flat = _flat(_contract())
    assert "No SQLite table, column, index, or `PRAGMA user_version` changes" in flat
    assert "no migration script" in flat.lower()


def test_keyset_endpoint_facts_are_documented() -> None:
    text = _contract()
    assert "/markets/keyset" in text
    assert "gamma_markets_keyset" in text
    assert "2026-08-30" in text
    flat = _flat(text)
    assert "documented `limit` range 1..100" in flat
    assert "`offset` is explicitly rejected" in flat
    assert "documented-but-repo-unverified" in flat
    assert "no automatic cursor loop" in flat.lower() or "There is no automatic cursor loop" in flat


def test_polling_policy_budget_documented() -> None:
    flat = _flat(_contract())
    assert "max_requests_per_window=6" in flat
    assert "max_markets_per_run=100" in flat
    assert "allow_automated_loop=False" in flat
    assert "requires_explicit_network=True" in flat


def test_double_opt_in_documented() -> None:
    flat = _flat(_contract())
    assert "Double opt-in" in _contract()
    assert "allow_documented_unverified_keyset" in flat
    assert "allow_unverified_endpoints=True" in flat
    assert "lone `allow_network=True` is rejected before any client construction" in flat


def test_run_identity_excludes_next_cursor() -> None:
    flat = _flat(_contract())
    assert "next_cursor` is never part of the immutable record identity" in flat
    assert "snapshot:sha256:" in flat and "ingest:sha256:" in flat


def test_capacity_and_persistence_order_documented() -> None:
    flat = _flat(_contract())
    assert "physical_count + page_limit + order_books_limit <= 4096" in flat
    assert "SCALED_CAPACITY_EXCEEDED" in flat
    assert "recovery_required=True" in flat
    assert "never re-fetches" in flat


def test_recovery_and_successor_documented() -> None:
    flat = _flat(_contract())
    assert "SCALED_ALREADY_REGISTERED" in flat
    assert "1..120 orphan records" in flat
    assert "SCALED_RECOVERY_INVALID" in flat
    assert "WP167" in flat
    assert "merge-authorized" in flat


def test_module_matches_contract_label_and_posture() -> None:
    module = MODULE.read_text(encoding="utf-8")
    assert "POLYMARKET_SCALABLE_KEYSET_LINEAGE_DELTA_POPULATION" in module
    assert (
        "MANUAL_ONE_PAGE_KEYSET_GET_ONLY_EXTERNAL_PARENT_COMMITTED_NO_TRADING_AUTHORITY"
        in module
    )
