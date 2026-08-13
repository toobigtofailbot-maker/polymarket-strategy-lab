"""Focused deterministic tests for the WP157 bounded as-of query layer.

Local, offline, stdlib-only, in-memory. No file, network, credential,
scheduler, strategy, paper, or execution behavior is exercised.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import ast
import inspect
import pathlib

import pytest

import src.data_layer.point_in_time_market_research as pit
from src.data_layer.point_in_time_market_research import as_of_query as Q
from src.data_layer.point_in_time_market_research import as_of_synthetic_cases as CASES
from src.data_layer.point_in_time_market_research import records as R
from src.data_layer.point_in_time_market_research.as_of_synthetic_cases import (
    _meta,
    build_synthetic_as_of_query_records_for_case as records_for,
    build_synthetic_as_of_records,
)


ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_DIR = ROOT / "src" / "data_layer" / "point_in_time_market_research"


def _records() -> dict:
    return build_synthetic_as_of_records()


def _base_spec(**overrides) -> Q.PointInTimeQuerySpec:
    params = dict(
        query_id="query:test:base",
        cutoff_mode="AS_OF_INGESTION_TIME",
        cutoff_time="2026-01-01T00:00:06Z",
        result_view="AUTHORITATIVE_CURRENT_STATE",
        record_families=(),
        observation_kinds=(),
        platform_ids=(),
        event_ids=(),
        market_ids=(),
        token_ids=(),
        source_ids=(),
        resolution_source_ids=(),
        event_time_window=None,
        include_conflicts_for_review=False,
        include_retracted_history=False,
        parameter_set_id="parameters:wp157:synthetic:v1",
    )
    params.update(overrides)
    return Q.PointInTimeQuerySpec(**params)


# ── Public surface, vocabularies, immutability (Section 19: 1-4) ─────────────


def test_public_package_exports_exact_supported_surface() -> None:
    assert pit.__all__ == (
        "FOUNDATION_LABEL",
        "IMPLEMENTATION_POSTURE",
        "SUPPORTED_SCHEMA_ID",
        "SUPPORTED_SCHEMA_VERSION",
        "SUPPORTED_RECORD_FAMILIES",
        "SUPPORTED_OBSERVATION_KINDS",
        "LIFECYCLE_STATES",
        "RECORD_CLASSIFICATIONS",
        "VALIDATION_STATUSES",
        "PointInTimeEnvelope",
        "MarketObservationRecord",
        "SourceSnapshotRecord",
        "ResolutionRuleSnapshotRecord",
        "QuarantineDescriptor",
        "PointInTimeBuildResult",
        "PointInTimeBatchValidationResult",
        "SyntheticPointInTimeCase",
        "canonical_json_bytes",
        "sha256_hex",
        "build_market_observation",
        "build_source_snapshot",
        "build_resolution_rule_snapshot",
        "validate_record_batch",
        "get_synthetic_point_in_time_cases",
        "load_synthetic_case_input",
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
        # WP160 bounded in-memory manifest chain and dataset snapshot reference
        # validation surface (appended by the separately approved successor WP).
        "MANIFEST_REFERENCE_LABEL",
        "MANIFEST_REFERENCE_POSTURE",
        "DATASET_REFERENCE_SCHEMA_ID",
        "DATASET_REFERENCE_SCHEMA_VERSION",
        "MANIFEST_ENTRY_SCHEMA_ID",
        "MANIFEST_ENTRY_SCHEMA_VERSION",
        "DATASET_DERIVATION_MODES",
        "MANIFEST_ENTRY_KINDS",
        "REFERENCE_STATES",
        "MANIFEST_REASON_CODES",
        "MANIFEST_REFERENCE_VALIDATION_STATUSES",
        "MANIFEST_REFERENCE_ERROR_CODES",
        "DatasetSnapshotReference",
        "ManifestEntry",
        "DatasetSnapshotReferenceBuildResult",
        "ManifestEntryBuildResult",
        "ManifestChainValidationResult",
        "build_dataset_snapshot_reference",
        "build_manifest_entry",
        "validate_manifest_chain",
        # WP161 bounded local SQLite transactional manifest store.
        "MANIFEST_STORE_LABEL",
        "MANIFEST_STORE_POSTURE",
        "MANIFEST_STORE_FORMAT_ID",
        "MANIFEST_STORE_SCHEMA_VERSION",
        "MANIFEST_STORE_STATUSES",
        "MANIFEST_STORE_ERROR_CODES",
        "ManifestStoreSnapshot",
        "ManifestStoreResult",
        "initialize_manifest_store",
        "append_manifest_store_batch",
        "load_and_verify_manifest_store",
        # WP162 bounded deterministic WP156/WP157 -> WP160 -> WP161 dataset
        # persistence and registration adapters (appended by the separately
        # approved successor WP).
        "DATASET_PERSISTENCE_ADAPTER_LABEL",
        "DATASET_PERSISTENCE_ADAPTER_POSTURE",
        "DATASET_PERSISTENCE_ADAPTER_STATUSES",
        "DATASET_PERSISTENCE_ADAPTER_ERROR_CODES",
        "DatasetPersistenceAdapterResult",
        "persist_validated_record_batch_snapshot",
        "persist_as_of_query_snapshot",
    )


def test_locked_labels_and_vocabularies_are_exact() -> None:
    assert pit.AS_OF_QUERY_LABEL == "POINT_IN_TIME_RECORD_SET_RECONSTRUCTION"
    assert (
        pit.AS_OF_QUERY_POSTURE
        == "BOUNDED_IN_MEMORY_AS_OF_INGESTION_TIME_RECONSTRUCTION"
    )
    assert pit.SUPPORTED_CUTOFF_MODES == (
        "AS_OF_INGESTION_TIME",
        "AS_OF_OBSERVED_TIME_DIAGNOSTIC",
    )
    assert pit.SUPPORTED_RESULT_VIEWS == (
        "AUTHORITATIVE_CURRENT_STATE",
        "VISIBLE_HISTORY",
        "ENTITY_TIMELINE",
    )
    assert pit.QUERY_STATUSES == (
        "QUERY_VALID",
        "QUERY_VALID_WITH_WARNINGS",
        "QUERY_EMPTY",
        "QUERY_REJECTED_SPEC",
        "QUERY_REJECTED_RECORD_BATCH",
        "QUERY_CONFLICT_REQUIRES_REVIEW",
    )
    assert pit.EXCLUSION_REASONS == (
        "AFTER_INGESTION_CUTOFF",
        "AFTER_OBSERVED_CUTOFF",
        "BEFORE_EVENT_WINDOW",
        "AFTER_EVENT_WINDOW",
        "EVENT_TIME_MISSING",
        "SUPERSEDED_AT_CUTOFF",
        "RETRACTED_AT_CUTOFF",
        "CONFLICT_REQUIRES_REVIEW",
        "INVALID_RECORD_BATCH",
        "ENTITY_FILTER_MISMATCH",
        "RECORD_FAMILY_FILTER_MISMATCH",
        "OBSERVATION_KIND_FILTER_MISMATCH",
    )


@pytest.mark.parametrize(
    "public_type",
    (
        Q.EventTimeWindow,
        Q.PointInTimeQuerySpec,
        Q.PointInTimeQueryReceipt,
        Q.PointInTimeRecordSetResult,
        Q.SyntheticAsOfQueryCase,
    ),
)
def test_public_dataclasses_are_frozen(public_type) -> None:
    assert public_type.__dataclass_params__.frozen is True


def test_spec_retains_only_immutable_tuple_filters_and_no_mutation() -> None:
    spec = _base_spec(record_families=("MARKET_OBSERVATION",))
    for field in Q._FILTER_FIELDS:
        assert isinstance(getattr(spec, field), tuple)
    with pytest.raises(FrozenInstanceError):
        spec.query_id = "changed"  # type: ignore[misc]


def test_result_and_receipt_safety_flags_are_fixed_true() -> None:
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"]], _base_spec()
    )
    assert result.receipt is not None
    assert result.receipt.advisory_only is True
    assert result.receipt.no_execution_authority is True
    assert result.receipt.query_engine_version == "point-in-time-as-of-query@1.0.0"


# ── Query-spec canonicalization and fixed hashes (Section 19: 5) ─────────────


def test_query_spec_hash_is_fixed_for_filter_and_window_specs() -> None:
    filter_spec = CASES._case_specs()[13][2]  # ASOF-C14 entity filter
    window_spec = CASES._case_specs()[10][2]  # ASOF-C11 event window
    assert (
        Q.query_spec_sha256(filter_spec)
        == "e9321ae5ce30e2635bb498fc9c2754119d8ae89ce6fb068da10fc0126083cf1a"
    )
    assert (
        Q.query_spec_sha256(window_spec)
        == "a8a7a74036f275bd18e8254dba728f3c5fe38f3e83cf34e213e400c0356f51ed"
    )


def test_query_spec_hash_includes_explicit_nulls_and_empty_tuples() -> None:
    spec = _base_spec()
    mapping = Q._spec_mapping(spec)
    assert mapping["event_time_window"] is None
    assert mapping["record_families"] == []
    # Reordering filter identity would change the hash: sanity monotonicity.
    other = _base_spec(query_id="query:test:other")
    assert Q.query_spec_sha256(spec) != Q.query_spec_sha256(other)


# ── Corpus-driven behavioral matrix (Section 19: many) ───────────────────────


ALL_CASES = pit.get_synthetic_as_of_query_cases()


def test_exact_twenty_four_case_corpus_order() -> None:
    expected = (
        "ASOF-C01-BEFORE-FIRST-INGESTION",
        "ASOF-C02-PRIMARY-VISIBLE",
        "ASOF-C03-BEFORE-CORRECTION",
        "ASOF-C04-AFTER-CORRECTION",
        "ASOF-C05-BEFORE-SOURCE-REVISION",
        "ASOF-C06-AFTER-SOURCE-REVISION",
        "ASOF-C07-BEFORE-RETRACTION",
        "ASOF-C08-AFTER-RETRACTION",
        "ASOF-C09-LATE-ARRIVAL-NOT-BACKDATED",
        "ASOF-C10-OBSERVED-DIAGNOSTIC-INGESTION-BOUNDED",
        "ASOF-C11-EVENT-WINDOW-AFTER-VISIBILITY",
        "ASOF-C12-MISSING-EVENT-TIME-EXCLUDED",
        "ASOF-C13-MISSING-EVENT-TIME-INCLUDED",
        "ASOF-C14-ENTITY-FILTER",
        "ASOF-C15-FAMILY-AND-KIND-FILTER",
        "ASOF-C16-VISIBLE-HISTORY",
        "ASOF-C17-ENTITY-TIMELINE",
        "ASOF-C18-CONFLICT-EXCLUDED",
        "ASOF-C19-CONFLICT-REVIEW-ONLY",
        "ASOF-C20-INVALID-BATCH-REJECTED",
        "ASOF-C21-INVALID-SPEC-REJECTED",
        "ASOF-C22-INPUT-PERMUTATION-INVARIANT",
        "ASOF-C23-EMPTY-VALID-RECEIPT",
        "ASOF-C24-FUTURE-RULE-SNAPSHOT-EXCLUDED",
    )
    assert tuple(case.case_id for case in ALL_CASES) == expected
    assert len(ALL_CASES) == 24


@pytest.mark.parametrize("case", ALL_CASES, ids=[c.case_id for c in ALL_CASES])
def test_synthetic_case_matches_engine_and_fixed_expectations(case) -> None:
    records = records_for(case.case_id)
    result = Q.query_point_in_time_record_set(records, case.query_spec)
    assert result.is_valid is case.expected_valid
    assert result.status == case.expected_status
    assert result.error_codes == case.expected_error_codes
    assert result.warning_codes == case.expected_warning_codes
    if result.receipt is None:
        assert case.expected_result_sha256 == ""
        assert case.expected_authoritative_ids == ()
        assert case.expected_history_ids == ()
        assert case.expected_review_conflict_ids == ()
        return
    receipt = result.receipt
    assert receipt.authoritative_record_version_ids == case.expected_authoritative_ids
    assert receipt.history_record_version_ids == case.expected_history_ids
    assert receipt.review_conflict_record_version_ids == case.expected_review_conflict_ids
    assert receipt.result_sha256 == case.expected_result_sha256
    # Conflicts never enter authoritative or history tuples.
    assert all(
        r.envelope.classification != "CONFLICT" for r in result.authoritative_records
    )
    assert all(
        r.envelope.classification != "CONFLICT" for r in result.history_records
    )
    assert all(
        r.envelope.classification == "CONFLICT" for r in result.review_conflict_records
    )


@pytest.mark.parametrize("case", ALL_CASES, ids=[c.case_id for c in ALL_CASES])
def test_exclusion_counts_reconcile_for_every_case(case) -> None:
    result = Q.query_point_in_time_record_set(records_for(case.case_id), case.query_spec)
    if result.receipt is None:
        return
    receipt = result.receipt
    # Canonical order, all reasons present, integers only.
    assert tuple(r for r, _ in receipt.exclusion_counts) == pit.EXCLUSION_REASONS
    assert all(isinstance(c, int) for _, c in receipt.exclusion_counts)
    assert sum(c for _, c in receipt.exclusion_counts) == receipt.excluded_count
    primary = (
        receipt.authoritative_result_count
        if case.query_spec.result_view == "AUTHORITATIVE_CURRENT_STATE"
        else receipt.history_result_count
    )
    assert (
        primary + receipt.review_conflict_count + receipt.excluded_count
        == receipt.validated_unique_record_count
    )


# ── Visibility, temporal integrity (Section 19: 7-15) ────────────────────────


def test_ingestion_visibility_before_at_after_cutoff() -> None:
    primary = _records()["MKT-META-PRIMARY"]
    before = Q.query_point_in_time_record_set(
        [primary], _base_spec(cutoff_time="2026-01-01T00:00:01Z")
    )
    at = Q.query_point_in_time_record_set(
        [primary], _base_spec(cutoff_time="2026-01-01T00:00:02Z")
    )
    after = Q.query_point_in_time_record_set(
        [primary], _base_spec(cutoff_time="2026-01-01T00:00:03Z")
    )
    assert before.status == "QUERY_EMPTY"
    assert before.receipt.exclusion_counts[0] == ("AFTER_INGESTION_CUTOFF", 1)
    assert at.authoritative_records == (primary,)
    assert after.authoritative_records == (primary,)


def test_observed_diagnostic_never_includes_after_ingestion_record() -> None:
    recs = records_for("ASOF-C10-OBSERVED-DIAGNOSTIC-INGESTION-BOUNDED")
    result = Q.query_point_in_time_record_set(
        recs,
        CASES._case_specs()[9][2],
    )
    ids = result.receipt.authoritative_record_version_ids
    late = _records()["MKT-LATE"].envelope.record_version_id
    assert late not in ids
    assert "OBSERVED_TIME_DIAGNOSTIC_MODE" in result.warning_codes


def test_future_correction_does_not_change_earlier_cutoff() -> None:
    recs = records_for("ASOF-C03-BEFORE-CORRECTION")
    primary = _records()["MKT-META-PRIMARY"]
    result = Q.query_point_in_time_record_set(
        recs, _base_spec(cutoff_time="2026-01-01T00:02:00Z")
    )
    assert result.authoritative_records == (primary,)


def test_future_retraction_does_not_remove_earlier_state() -> None:
    recs = records_for("ASOF-C07-BEFORE-RETRACTION")
    revision = _records()["SRC-REVISION"]
    result = Q.query_point_in_time_record_set(
        recs, _base_spec(cutoff_time="2026-01-01T00:03:00Z")
    )
    assert result.authoritative_records == (revision,)


def test_late_arrival_event_time_before_cutoff_does_not_backdate() -> None:
    late = _records()["MKT-LATE"]
    # Cutoff after the late record's event time but before its ingestion time.
    result = Q.query_point_in_time_record_set(
        [late], _base_spec(cutoff_time="2026-01-01T00:00:03Z")
    )
    assert result.status == "QUERY_EMPTY"
    assert result.authoritative_records == ()


def test_exact_duplicate_does_not_create_second_authoritative_state() -> None:
    recs = (_records()["MKT-META-PRIMARY"], _records()["MKT-EXACT-DUP"])
    result = Q.query_point_in_time_record_set(
        recs, _base_spec(cutoff_time="2026-01-01T00:05:00Z")
    )
    assert result.authoritative_records == (_records()["MKT-META-PRIMARY"],)
    assert result.receipt.exclusion_counts[_exc_index("SUPERSEDED_AT_CUTOFF")][1] == 1


def test_semantic_duplicate_is_history_only_with_warning() -> None:
    recs = (_records()["MKT-META-PRIMARY"], _records()["MKT-SEMANTIC-DUP"])
    result = Q.query_point_in_time_record_set(
        recs, _base_spec(cutoff_time="2026-01-01T00:05:01Z")
    )
    assert "SEMANTIC_DUPLICATE_HISTORY_ONLY" in result.warning_codes
    assert result.authoritative_records == (_records()["MKT-META-PRIMARY"],)


def _exc_index(reason: str) -> int:
    return pit.EXCLUSION_REASONS.index(reason)


# ── Filters (Section 19: 22) ─────────────────────────────────────────────────


def test_every_filter_family_is_deterministic() -> None:
    records = _records()
    market = records["MKT-META-PRIMARY"]
    source = records["SRC-PRIMARY"]
    rule = records["RULE-PRIMARY"]
    book = records["MKT-BOOK-NOEVENT"]
    all_recs = [market, source, rule, book]
    cutoff = "2026-01-01T00:00:06Z"

    def history_ids(**flt):
        result = Q.query_point_in_time_record_set(
            all_recs, _base_spec(cutoff_time=cutoff, result_view="VISIBLE_HISTORY", **flt)
        )
        return set(result.receipt.history_record_version_ids)

    assert history_ids(record_families=("SOURCE_SNAPSHOT",)) == {
        source.envelope.record_version_id
    }
    assert history_ids(observation_kinds=("ORDER_BOOK",)) == {
        book.envelope.record_version_id
    }
    assert history_ids(token_ids=("token:synthetic:yes",)) == {
        book.envelope.record_version_id
    }
    assert history_ids(
        resolution_source_ids=("resolution-source:synthetic:primary",)
    ) == {rule.envelope.record_version_id}
    assert history_ids(platform_ids=("platform:synthetic",)) == {
        market.envelope.record_version_id,
        rule.envelope.record_version_id,
        book.envelope.record_version_id,
    }


def test_filter_precedence_assigns_single_primary_reason() -> None:
    records = _records()
    source = records["SRC-PRIMARY"]
    # A source record fails family, then would fail entity; family wins.
    result = Q.query_point_in_time_record_set(
        [source],
        _base_spec(
            cutoff_time="2026-01-01T00:00:06Z",
            result_view="VISIBLE_HISTORY",
            record_families=("MARKET_OBSERVATION",),
            source_ids=("source:synthetic:other",),
        ),
    )
    counts = dict(result.receipt.exclusion_counts)
    assert counts["RECORD_FAMILY_FILTER_MISMATCH"] == 1
    assert counts["ENTITY_FILTER_MISMATCH"] == 0


# ── Ordering and permutation invariance (Section 19: 23, 24, 30) ─────────────


def test_input_permutation_invariance() -> None:
    recs = list(records_for("ASOF-C22-INPUT-PERMUTATION-INVARIANT"))
    spec = CASES._case_specs()[21][2]
    baseline = Q.query_point_in_time_record_set(recs, spec)
    for permutation in (
        list(reversed(recs)),
        [recs[2], recs[0], recs[1]],
        [recs[1], recs[2], recs[0]],
    ):
        other = Q.query_point_in_time_record_set(permutation, spec)
        assert other.receipt == baseline.receipt
        assert other.history_records == baseline.history_records


def test_identical_execution_equality() -> None:
    recs = records_for("ASOF-C17-ENTITY-TIMELINE")
    spec = CASES._case_specs()[16][2]
    first = Q.query_point_in_time_record_set(recs, spec)
    second = Q.query_point_in_time_record_set(records_for("ASOF-C17-ENTITY-TIMELINE"), spec)
    assert first.receipt == second.receipt
    assert first == second


def test_duplicate_input_object_does_not_double_count() -> None:
    primary = _records()["MKT-META-PRIMARY"]
    result = Q.query_point_in_time_record_set(
        [primary, primary], _base_spec(cutoff_time="2026-01-01T00:00:06Z")
    )
    assert result.receipt.validated_unique_record_count == 1
    assert result.authoritative_records == (primary,)


# ── Empty valid result (Section 19: 25) ──────────────────────────────────────


def test_empty_valid_result_has_receipt_and_deterministic_hash() -> None:
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"]],
        _base_spec(market_ids=("market:synthetic:999",)),
    )
    assert result.is_valid is True
    assert result.status == "QUERY_EMPTY"
    assert result.authoritative_records == ()
    assert result.receipt is not None
    assert result.receipt.result_sha256


# ── No caller mutation and no side effects (Section 19: 31, 32) ──────────────


def test_no_caller_mutation() -> None:
    recs = list(records_for("ASOF-C16-VISIBLE-HISTORY"))
    snapshot = list(recs)
    Q.query_point_in_time_record_set(recs, CASES._case_specs()[15][2])
    assert recs == snapshot


def test_no_file_side_effects(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    before = set(p.name for p in tmp_path.iterdir())
    for case in ALL_CASES:
        Q.query_point_in_time_record_set(records_for(case.case_id), case.query_spec)
    after = set(p.name for p in tmp_path.iterdir())
    assert before == after


# ── Negative / adversarial: query spec (Section 20: 1-14) ────────────────────


def test_spec_wrong_object_type_rejected() -> None:
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"]], {"query_id": "x"}
    )
    assert result.status == "QUERY_REJECTED_SPEC"
    assert result.error_codes == ("QUERY_SPEC_TYPE_INVALID",)
    assert result.receipt is None


@pytest.mark.parametrize(
    "overrides,expected",
    (
        ({"query_id": ""}, "QUERY_ID_INVALID"),
        ({"query_id": "a b"}, "QUERY_ID_INVALID"),
        ({"query_id": "a" * 257}, "QUERY_ID_INVALID"),
        ({"cutoff_mode": "AS_OF_WALL_CLOCK"}, "CUTOFF_MODE_UNSUPPORTED"),
        ({"cutoff_time": "2026-01-01T00:00:00"}, "CUTOFF_TIME_INVALID"),
        ({"cutoff_time": "2026-01-01T00:00:00+05:00"}, "CUTOFF_TIME_INVALID"),
        ({"cutoff_time": "not-a-time"}, "CUTOFF_TIME_INVALID"),
        ({"result_view": "SUMMARY"}, "RESULT_VIEW_UNSUPPORTED"),
        ({"record_families": ("UNKNOWN_FAMILY",)}, "FILTER_VALUE_INVALID"),
        ({"observation_kinds": ("UNKNOWN_KIND",)}, "FILTER_VALUE_INVALID"),
        ({"parameter_set_id": "bad id"}, "PARAMETER_SET_ID_INVALID"),
    ),
)
def test_spec_scalar_and_filter_rejections(overrides, expected) -> None:
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"]], _base_spec(**overrides)
    )
    assert result.status == "QUERY_REJECTED_SPEC"
    assert expected in result.error_codes
    assert result.receipt is None


def test_spec_filter_list_instead_of_tuple_rejected() -> None:
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"]], _base_spec(market_ids=["market:synthetic:001"])
    )
    assert "FILTER_TYPE_INVALID" in result.error_codes


def test_spec_non_string_filter_rejected() -> None:
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"]], _base_spec(market_ids=(123,))
    )
    assert "FILTER_VALUE_INVALID" in result.error_codes


def test_spec_duplicate_filter_rejected() -> None:
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"]],
        _base_spec(market_ids=("market:synthetic:001", "market:synthetic:001")),
    )
    assert "FILTER_DUPLICATE" in result.error_codes


def test_spec_unsorted_filter_rejected() -> None:
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"]],
        _base_spec(market_ids=("market:synthetic:002", "market:synthetic:001")),
    )
    assert "FILTER_ORDER_INVALID" in result.error_codes


def test_entity_timeline_requires_entity_filter() -> None:
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"]],
        _base_spec(result_view="ENTITY_TIMELINE", platform_ids=("platform:synthetic",)),
    )
    assert "ENTITY_TIMELINE_FILTER_REQUIRED" in result.error_codes


@pytest.mark.parametrize(
    "window,expected",
    (
        (Q.EventTimeWindow(None, None, False), "EVENT_WINDOW_INVALID"),
        (
            Q.EventTimeWindow("2026-01-01T00:00:00", None, False),
            "EVENT_WINDOW_INVALID",
        ),
        (
            Q.EventTimeWindow(
                "2026-01-01T00:00:02Z", "2026-01-01T00:00:01Z", False
            ),
            "EVENT_WINDOW_ORDER_INVALID",
        ),
        (
            Q.EventTimeWindow(
                "2026-01-01T00:00:01Z", "2026-01-01T00:00:01Z", False
            ),
            "EVENT_WINDOW_ORDER_INVALID",
        ),
    ),
)
def test_event_window_rejections(window, expected) -> None:
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"]],
        _base_spec(result_view="VISIBLE_HISTORY", event_time_window=window),
    )
    assert result.status == "QUERY_REJECTED_SPEC"
    assert expected in result.error_codes


def test_retracted_history_incompatible_with_current_state() -> None:
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"]],
        _base_spec(include_retracted_history=True),
    )
    assert "RETRACTED_HISTORY_INCOMPATIBLE_WITH_CURRENT_STATE" in result.error_codes


def test_filter_limit_enforced() -> None:
    values = tuple(sorted(f"market:synthetic:{i:04d}" for i in range(129)))
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"]], _base_spec(market_ids=values)
    )
    assert "FILTER_LIMIT_EXCEEDED" in result.error_codes


# ── Negative / adversarial: record batch (Section 20: 15-27) ─────────────────


def test_non_wp156_record_object_rejected() -> None:
    result = Q.query_point_in_time_record_set([object()], _base_spec())
    assert result.status == "QUERY_REJECTED_RECORD_BATCH"
    assert result.error_codes == ("RECORD_BATCH_INVALID",)
    assert result.receipt is None


def test_tampered_record_rejects_batch() -> None:
    tampered = replace(
        _records()["MKT-META-PRIMARY"], platform_id="platform:synthetic:tampered"
    )
    result = Q.query_point_in_time_record_set([tampered], _base_spec())
    assert result.status == "QUERY_REJECTED_RECORD_BATCH"
    assert result.authoritative_records == ()


def test_unknown_superseded_parent_rejects_batch() -> None:
    # Revision present without its parent -> WP156 batch invalid.
    revision = _records()["SRC-REVISION"]
    result = Q.query_point_in_time_record_set([revision], _base_spec())
    assert result.status == "QUERY_REJECTED_RECORD_BATCH"


def test_conflict_without_review_permission_is_excluded_not_authoritative() -> None:
    recs = records_for("ASOF-C18-CONFLICT-EXCLUDED")
    result = Q.query_point_in_time_record_set(
        recs, _base_spec(cutoff_time="2026-01-01T00:06:01Z")
    )
    conflict_id = _records()["MKT-CONFLICT"].envelope.record_version_id
    assert conflict_id not in result.receipt.authoritative_record_version_ids
    assert conflict_id not in result.receipt.history_record_version_ids
    assert conflict_id not in result.receipt.review_conflict_record_version_ids
    counts = dict(result.receipt.exclusion_counts)
    assert counts["CONFLICT_REQUIRES_REVIEW"] == 1


def test_structurally_invalid_conflict_rejects_batch() -> None:
    tampered_conflict = replace(
        _records()["MKT-CONFLICT"], market_id="market:synthetic:tampered"
    )
    result = Q.query_point_in_time_record_set(
        [_records()["MKT-META-PRIMARY"], tampered_conflict],
        _base_spec(cutoff_time="2026-01-01T00:06:01Z", include_conflicts_for_review=True),
    )
    assert result.status == "QUERY_REJECTED_RECORD_BATCH"
    assert "CONFLICT_NOT_AUTHORIZED_FOR_REVIEW" in result.error_codes


def test_conflict_is_structurally_valid_review_record() -> None:
    from src.data_layer.point_in_time_market_research.records import (
        revalidate_review_conflict_record,
    )

    assert revalidate_review_conflict_record(_records()["MKT-CONFLICT"]) == ()


# ── Temporal integrity (Section 20: 28-33) ───────────────────────────────────


def test_future_rule_snapshot_cannot_appear_earlier() -> None:
    recs = records_for("ASOF-C24-FUTURE-RULE-SNAPSHOT-EXCLUDED")
    result = Q.query_point_in_time_record_set(
        recs, _base_spec(cutoff_time="2026-01-01T00:00:03Z", result_view="VISIBLE_HISTORY")
    )
    rule_id = _records()["RULE-PRIMARY"].envelope.record_version_id
    assert rule_id not in result.receipt.history_record_version_ids
    counts = dict(result.receipt.exclusion_counts)
    assert counts["AFTER_INGESTION_CUTOFF"] == 1


def test_event_window_cannot_make_invisible_record_visible() -> None:
    # Correction ingested after cutoff, event window wide open: still invisible.
    recs = records_for("ASOF-C03-BEFORE-CORRECTION")
    result = Q.query_point_in_time_record_set(
        recs,
        _base_spec(
            cutoff_time="2026-01-01T00:02:00Z",
            result_view="VISIBLE_HISTORY",
            event_time_window=Q.EventTimeWindow(
                "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", True
            ),
        ),
    )
    correction_id = _records()["MKT-META-CORRECTION"].envelope.record_version_id
    assert correction_id not in result.receipt.history_record_version_ids


# ── Determinism / accounting / bounds (Section 20: 34-41) ────────────────────


def test_rejected_output_contains_no_raw_caller_values() -> None:
    tampered = replace(
        _records()["MKT-META-PRIMARY"], platform_id="platform:synthetic:secretvalue"
    )
    result = Q.query_point_in_time_record_set([tampered], _base_spec())
    blob = repr(result)
    assert "secretvalue" not in blob
    assert result.receipt is None


def test_input_batch_limit_enforced() -> None:
    primary = _records()["MKT-META-PRIMARY"]
    result = Q.query_point_in_time_record_set([primary] * 257, _base_spec())
    assert result.status == "QUERY_REJECTED_RECORD_BATCH"


def test_reversed_input_same_receipt_and_hash() -> None:
    recs = list(records_for("ASOF-C16-VISIBLE-HISTORY"))
    spec = CASES._case_specs()[15][2]
    a = Q.query_point_in_time_record_set(recs, spec)
    b = Q.query_point_in_time_record_set(list(reversed(recs)), spec)
    assert a.receipt.result_sha256 == b.receipt.result_sha256


# ── Boundary / no-look-ahead source guards (Section 20: 41-46) ───────────────


_FORBIDDEN_TOKENS = (
    "import os",
    "import io",
    "import socket",
    "urllib",
    "requests",
    "subprocess",
    "import random",
    "import uuid",
    "pyarrow",
    "parquet",
    "duckdb",
    "polars",
    "pydantic",
    "datetime.now",
    "utcnow",
    "time.time",
    "open(",
)


@pytest.mark.parametrize("module_name", ("as_of_query.py", "as_of_synthetic_cases.py"))
def test_source_has_no_forbidden_side_effect_tokens(module_name) -> None:
    text = (SRC_DIR / module_name).read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in text, f"{module_name} contains forbidden token {token!r}"


@pytest.mark.parametrize("module_name", ("as_of_query.py", "as_of_synthetic_cases.py"))
def test_source_imports_are_stdlib_or_intrapackage(module_name) -> None:
    tree = ast.parse((SRC_DIR / module_name).read_text(encoding="utf-8"))
    allowed_roots = {
        "__future__",
        "collections",
        "dataclasses",
        "datetime",
        "re",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in allowed_roots
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # intra-package relative import
            assert node.module is not None
            assert node.module.split(".")[0] in allowed_roots


def test_legacy_snapshot_modules_untouched_by_import() -> None:
    # Importing the query layer must not require or alter legacy snapshot code.
    import importlib

    module = importlib.import_module(
        "src.data_layer.point_in_time_market_research.as_of_query"
    )
    assert module.AS_OF_QUERY_LABEL == "POINT_IN_TIME_RECORD_SET_RECONSTRUCTION"


def test_wp158_not_implemented() -> None:
    assert not (SRC_DIR / "manifest.py").exists()
    assert not (SRC_DIR / "dataset_snapshot_reference.py").exists()


# ── Blocker A: query-spec validation never raises (fail-closed) ──────────────


class _Unhashable:
    __hash__ = None  # type: ignore[assignment]


@pytest.mark.parametrize("field", Q._FILTER_FIELDS)
@pytest.mark.parametrize(
    "bad",
    (
        ["market:synthetic:001"],
        {"market:synthetic:001"},
        {"market:synthetic:001": 1},
        b"market",
        7,
        ({"k": "v"},),
        (["x"],),
        ({"x"},),
        (_Unhashable(),),
        ("market:synthetic:001", 7),
        ({"a"}, {"b"}),
    ),
)
def test_malformed_filter_never_raises_and_rejects_spec(field, bad) -> None:
    spec = _base_spec(**{field: bad})
    result = Q.query_point_in_time_record_set([_records()["MKT-META-PRIMARY"]], spec)
    assert result.status == "QUERY_REJECTED_SPEC"
    assert result.receipt is None
    assert result.error_codes
    for code in result.error_codes:
        assert code in Q.ERROR_CODES


@pytest.mark.parametrize(
    "overrides",
    (
        {"cutoff_mode": ["AS_OF_INGESTION_TIME"]},
        {"cutoff_mode": {"x"}},
        {"cutoff_mode": _Unhashable()},
        {"result_view": ["AUTHORITATIVE_CURRENT_STATE"]},
        {"result_view": {"x"}},
        {"query_id": ["x"]},
        {"query_id": _Unhashable()},
        {"parameter_set_id": {"x"}},
        {"cutoff_time": ["x"]},
        {"cutoff_time": _Unhashable()},
    ),
)
def test_malformed_scalar_spec_fields_never_raise(overrides) -> None:
    spec = _base_spec(**overrides)
    result = Q.query_point_in_time_record_set([_records()["MKT-META-PRIMARY"]], spec)
    assert result.status == "QUERY_REJECTED_SPEC"
    assert result.receipt is None


def test_two_non_orderable_filter_values_reject_without_raise() -> None:
    spec = _base_spec(market_ids=({"a"}, {"b"}))
    result = Q.query_point_in_time_record_set([_records()["MKT-META-PRIMARY"]], spec)
    assert result.status == "QUERY_REJECTED_SPEC"
    assert "FILTER_VALUE_INVALID" in result.error_codes


def test_rejected_spec_never_echoes_marker_filter_value() -> None:
    spec = _base_spec(market_ids=("zz-marker-secret", 7))
    result = Q.query_point_in_time_record_set([_records()["MKT-META-PRIMARY"]], spec)
    assert result.status == "QUERY_REJECTED_SPEC"
    assert "zz-marker-secret" not in repr(result)


# ── Blocker B: public builder boundary / private conflict path ───────────────

_PUBLIC_BUILDERS = (
    "build_market_observation",
    "build_source_snapshot",
    "build_resolution_rule_snapshot",
)


@pytest.mark.parametrize("builder_name", _PUBLIC_BUILDERS)
def test_public_builder_signature_matches_merged_wp156(builder_name) -> None:
    sig = inspect.signature(getattr(R, builder_name))
    assert list(sig.parameters) == ["input_record"]
    assert "allow_review_conflict" not in sig.parameters


@pytest.mark.parametrize("builder_name", _PUBLIC_BUILDERS)
def test_public_builder_rejects_conflict_keyword(builder_name) -> None:
    with pytest.raises(TypeError):
        getattr(R, builder_name)({}, allow_review_conflict=True)


def _solo_conflict_input(source_assertion_id: str = "assertion:conflict:solo", **overrides):
    params = dict(
        source_assertion_id=source_assertion_id,
        observed_time="2026-01-01T00:06:00Z",
        ingestion_time="2026-01-01T00:06:01Z",
        classification="CONFLICT",
        human_review=True,
    )
    params.update(overrides)
    return _meta(**params)


def _solo_conflict(source_assertion_id: str = "assertion:conflict:solo", **overrides):
    result = R.build_review_conflict_record(
        _solo_conflict_input(source_assertion_id, **overrides)
    )
    assert result.is_valid and result.record is not None
    return result.record


def test_standard_builder_rejects_valid_conflict_input() -> None:
    result = R.build_market_observation(_solo_conflict_input())
    assert result.is_valid is False
    assert "CONFLICT_REQUIRES_HUMAN_REVIEW" in result.error_codes


def test_private_review_handoff_accepts_only_structural_conflict() -> None:
    ok = R.build_review_conflict_record(_solo_conflict_input())
    assert ok.is_valid and ok.record.envelope.classification == "CONFLICT"
    non_conflict = _meta(
        source_assertion_id="assertion:noncon",
        observed_time="2026-01-01T00:00:01Z",
        ingestion_time="2026-01-01T00:00:02Z",
    )
    assert R.build_review_conflict_record(non_conflict).is_valid is False
    tampered = replace(ok.record, market_id="market:synthetic:tampered")
    assert R.revalidate_review_conflict_record(tampered) != ()


# ── Blocker C: conflict-only batch requires review authorization ─────────────


def test_conflict_only_batch_requires_review_authorization() -> None:
    conflict = _solo_conflict()
    rejected = Q.query_point_in_time_record_set(
        [conflict],
        _base_spec(cutoff_time="2026-01-01T00:06:01Z", include_conflicts_for_review=False),
    )
    assert rejected.status == "QUERY_REJECTED_RECORD_BATCH"
    assert "CONFLICT_NOT_AUTHORIZED_FOR_REVIEW" in rejected.error_codes
    assert rejected.receipt is None

    reviewed = Q.query_point_in_time_record_set(
        [conflict],
        _base_spec(cutoff_time="2026-01-01T00:06:01Z", include_conflicts_for_review=True),
    )
    assert reviewed.status == "QUERY_CONFLICT_REQUIRES_REVIEW"
    assert (
        conflict.envelope.record_version_id
        in reviewed.receipt.review_conflict_record_version_ids
    )


def test_conflict_only_invisible_future_behavior() -> None:
    conflict = _solo_conflict()
    reviewed = Q.query_point_in_time_record_set(
        [conflict],
        _base_spec(cutoff_time="2026-01-01T00:00:00Z", include_conflicts_for_review=True),
    )
    assert reviewed.status == "QUERY_EMPTY"
    assert reviewed.receipt is not None
    assert dict(reviewed.receipt.exclusion_counts)["AFTER_INGESTION_CUTOFF"] == 1
    rejected = Q.query_point_in_time_record_set(
        [conflict],
        _base_spec(cutoff_time="2026-01-01T00:00:00Z", include_conflicts_for_review=False),
    )
    assert rejected.status == "QUERY_REJECTED_RECORD_BATCH"


def test_tampered_conflict_full_query_rejection() -> None:
    tampered = replace(_solo_conflict(), market_id="market:synthetic:tampered")
    result = Q.query_point_in_time_record_set(
        [tampered],
        _base_spec(cutoff_time="2026-01-01T00:06:01Z", include_conflicts_for_review=True),
    )
    assert result.status == "QUERY_REJECTED_RECORD_BATCH"
    assert "CONFLICT_NOT_AUTHORIZED_FOR_REVIEW" in result.error_codes


# ── Blocker D: full-input review-aware batch identity ────────────────────────


def _review_spec(**overrides):
    params = dict(cutoff_time="2026-01-01T00:06:01Z", include_conflicts_for_review=True)
    params.update(overrides)
    return _base_spec(**params)


def test_conflict_only_batch_hash_differs_from_empty_input() -> None:
    empty = Q.query_point_in_time_record_set([], _review_spec())
    conflict_only = Q.query_point_in_time_record_set([_solo_conflict()], _review_spec())
    assert (
        empty.receipt.validated_batch_sha256
        != conflict_only.receipt.validated_batch_sha256
    )


def test_adding_review_conflict_changes_batch_and_result_hash() -> None:
    primary = _records()["MKT-META-PRIMARY"]
    a = _solo_conflict("assertion:conflict:a")
    b = _solo_conflict("assertion:conflict:b")
    base = Q.query_point_in_time_record_set([primary, a], _review_spec())
    more = Q.query_point_in_time_record_set([primary, a, b], _review_spec())
    assert (
        base.receipt.validated_batch_sha256 != more.receipt.validated_batch_sha256
    )
    assert base.receipt.result_sha256 != more.receipt.result_sha256


def test_replacing_conflict_identity_changes_hashes_even_when_excluded() -> None:
    primary = _records()["MKT-META-PRIMARY"]
    a = _solo_conflict("assertion:conflict:a")
    b = _solo_conflict("assertion:conflict:b")
    excl = _base_spec(
        cutoff_time="2026-01-01T00:06:01Z", include_conflicts_for_review=False
    )
    with_a = Q.query_point_in_time_record_set([primary, a], excl)
    with_b = Q.query_point_in_time_record_set([primary, b], excl)
    assert with_a.status == "QUERY_VALID_WITH_WARNINGS"
    assert with_b.status == "QUERY_VALID_WITH_WARNINGS"
    assert (
        with_a.receipt.validated_batch_sha256 != with_b.receipt.validated_batch_sha256
    )
    assert with_a.receipt.result_sha256 != with_b.receipt.result_sha256


def test_conflict_batch_and_result_hash_permutation_invariant() -> None:
    primary = _records()["MKT-META-PRIMARY"]
    a = _solo_conflict("assertion:conflict:a")
    b = _solo_conflict("assertion:conflict:b")
    base = Q.query_point_in_time_record_set([primary, a, b], _review_spec())
    perm = Q.query_point_in_time_record_set([b, primary, a], _review_spec())
    assert base.receipt.validated_batch_sha256 == perm.receipt.validated_batch_sha256
    assert base.receipt.result_sha256 == perm.receipt.result_sha256


def test_conflict_unknown_parent_rejects_batch() -> None:
    orphan = _solo_conflict(
        "assertion:conflict:orphan", parents=["record:sha256:" + "0" * 64]
    )
    result = Q.query_point_in_time_record_set([orphan], _review_spec())
    assert result.status == "QUERY_REJECTED_RECORD_BATCH"
    assert "RECORD_BATCH_INVALID" in result.error_codes


def test_identical_duplicate_conflict_is_deterministic() -> None:
    # An identical duplicate conflict is deduplicated to one unique record and
    # acknowledged through the validated-batch identity; the result is stable.
    a = _solo_conflict("assertion:conflict:a")
    first = Q.query_point_in_time_record_set([a, a], _review_spec())
    second = Q.query_point_in_time_record_set([a, a], _review_spec())
    assert first.receipt.validated_unique_record_count == 1
    assert first.receipt.review_conflict_record_version_ids == (
        a.envelope.record_version_id,
    )
    assert first.receipt.result_sha256 == second.receipt.result_sha256


@pytest.mark.parametrize(
    "view", ("AUTHORITATIVE_CURRENT_STATE", "VISIBLE_HISTORY")
)
def test_conflict_never_in_authoritative_or_history_tuples(view) -> None:
    primary = _records()["MKT-META-PRIMARY"]
    a = _solo_conflict("assertion:conflict:a")
    result = Q.query_point_in_time_record_set(
        [primary, a], _review_spec(result_view=view)
    )
    aid = a.envelope.record_version_id
    assert aid not in result.receipt.authoritative_record_version_ids
    assert aid not in result.receipt.history_record_version_ids
    assert aid in result.receipt.review_conflict_record_version_ids


# ── Blocker E: visible superseding child requires a visible parent ───────────


def _lineage_pair(child_classification: str):
    primary = R.build_market_observation(
        _meta(
            source_assertion_id="assertion:lineage:001",
            observed_time="2026-01-01T00:00:01Z",
            ingestion_time="2026-01-01T00:00:02Z",
            event_time="2026-01-01T00:00:00Z",
        )
    ).record
    child = R.build_market_observation(
        _meta(
            source_assertion_id="assertion:lineage:001",
            observed_time="2026-01-01T00:02:00Z",
            ingestion_time="2026-01-01T00:02:01Z",
            event_time="2026-01-01T05:00:00Z",
            classification=child_classification,
            parents=[primary.envelope.record_version_id],
            supersedes=primary.envelope.record_version_id,
        )
    ).record
    return primary, child


@pytest.mark.parametrize("child_classification", ("PROJECT_CORRECTION", "SOURCE_REVISION"))
def test_window_excluded_parent_with_visible_child_rejects(child_classification) -> None:
    primary, child = _lineage_pair(child_classification)
    spec = _base_spec(
        cutoff_time="2026-01-01T00:02:01Z",
        result_view="VISIBLE_HISTORY",
        event_time_window=Q.EventTimeWindow(
            "2026-01-01T04:00:00Z", "2026-01-01T06:00:00Z", False
        ),
    )
    result = Q.query_point_in_time_record_set([primary, child], spec)
    assert result.status == "QUERY_REJECTED_RECORD_BATCH"
    assert "VISIBLE_CHILD_PARENT_NOT_VISIBLE" in result.error_codes
    assert result.receipt is None


def test_visible_parent_and_visible_correction_succeed() -> None:
    primary, correction = _lineage_pair("PROJECT_CORRECTION")
    spec = _base_spec(
        cutoff_time="2026-01-01T00:02:01Z",
        result_view="VISIBLE_HISTORY",
        event_time_window=Q.EventTimeWindow(
            "2026-01-01T00:00:00Z", "2026-01-01T06:00:00Z", False
        ),
    )
    result = Q.query_point_in_time_record_set([primary, correction], spec)
    assert result.is_valid is True
    ids = result.receipt.history_record_version_ids
    assert primary.envelope.record_version_id in ids
    assert correction.envelope.record_version_id in ids


@pytest.mark.parametrize("child_classification", ("PROJECT_CORRECTION", "SOURCE_REVISION"))
def test_future_invisible_child_leaves_parent_authoritative(child_classification) -> None:
    primary, child = _lineage_pair(child_classification)
    # Cutoff before the child ingestion: the child is not visible, so no
    # visible-parent check applies and the parent remains authoritative.
    spec = _base_spec(cutoff_time="2026-01-01T00:02:00Z")
    result = Q.query_point_in_time_record_set([primary, child], spec)
    assert result.receipt.authoritative_record_version_ids == (
        primary.envelope.record_version_id,
    )


# ── Blocker F: chronological event-time ordering ─────────────────────────────


def _event_record(source_assertion: str, event_time: str):
    return R.build_market_observation(
        _meta(
            source_assertion_id=source_assertion,
            observed_time="2026-01-01T00:00:01Z",
            ingestion_time="2026-01-01T00:00:02Z",
            event_time=event_time,
        )
    ).record


def test_event_time_ordering_is_chronological_not_lexicographic() -> None:
    zero = _event_record("assertion:evt:zero", "2026-01-01T00:00:00Z")
    frac = _event_record("assertion:evt:frac", "2026-01-01T00:00:00.1Z")
    spec = _base_spec(cutoff_time="2026-01-01T00:00:06Z", result_view="VISIBLE_HISTORY")
    result = Q.query_point_in_time_record_set([frac, zero], spec)
    ids = list(result.receipt.history_record_version_ids)
    assert ids.index(zero.envelope.record_version_id) < ids.index(
        frac.envelope.record_version_id
    )


def _fractional_records():
    return [
        _event_record("assertion:evt:a", "2026-01-01T00:00:00Z"),
        _event_record("assertion:evt:b", "2026-01-01T00:00:00.001Z"),
        _event_record("assertion:evt:c", "2026-01-01T00:00:00.1Z"),
        _event_record("assertion:evt:d", "2026-01-01T00:00:00.5Z"),
    ]


def test_multiple_fractional_precisions_order_chronologically() -> None:
    recs = _fractional_records()
    spec = _base_spec(cutoff_time="2026-01-01T00:00:06Z", result_view="VISIBLE_HISTORY")
    result = Q.query_point_in_time_record_set(list(reversed(recs)), spec)
    expected = tuple(r.envelope.record_version_id for r in recs)
    assert result.receipt.history_record_version_ids == expected


def test_fractional_event_order_permutation_invariant() -> None:
    recs = _fractional_records()
    spec = _base_spec(cutoff_time="2026-01-01T00:00:06Z", result_view="VISIBLE_HISTORY")
    forward = Q.query_point_in_time_record_set(recs, spec)
    backward = Q.query_point_in_time_record_set(list(reversed(recs)), spec)
    assert (
        forward.receipt.history_record_version_ids
        == backward.receipt.history_record_version_ids
    )
    assert forward.receipt.result_sha256 == backward.receipt.result_sha256


def test_normalized_offset_event_time_orders_with_z_form() -> None:
    # "+00:00" normalizes to canonical "Z"; ordering must match the Z form.
    z_form = _event_record("assertion:evt:z", "2026-01-01T00:00:03Z")
    offset = _event_record("assertion:evt:o", "2026-01-01T00:00:03.5+00:00")
    spec = _base_spec(cutoff_time="2026-01-01T00:00:06Z", result_view="VISIBLE_HISTORY")
    result = Q.query_point_in_time_record_set([offset, z_form], spec)
    ids = list(result.receipt.history_record_version_ids)
    assert ids.index(z_form.envelope.record_version_id) < ids.index(
        offset.envelope.record_version_id
    )
