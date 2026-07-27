"""Sanitized deterministic in-memory corpus for point-in-time validation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Callable

from .records import (
    SUPPORTED_SCHEMA_ID,
    SUPPORTED_SCHEMA_VERSION,
    PointInTimeBuildResult,
    build_market_observation,
    build_resolution_rule_snapshot,
    build_source_snapshot,
    canonical_json_bytes,
)


@dataclass(frozen=True)
class SyntheticPointInTimeCase:
    case_id: str
    case_family: str
    input_json: str
    related_case_ids: tuple[str, ...]
    expected_valid: bool
    expected_status: str
    expected_error_codes: tuple[str, ...]
    expected_warning_codes: tuple[str, ...]
    expected_record_family: str | None
    expected_record_version_id: str | None
    safety_notice: str


_SAFETY_NOTICE = (
    "SANITIZED_SYNTHETIC_ONLY_NO_EXECUTION_AUTHORITY_NO_REAL_MARKET_DATA"
)


def _common(
    family: str,
    *,
    snapshot_id: str,
    event_time: str | None,
    observed_time: str,
    ingestion_time: str,
    lifecycle: str = "NORMALIZED_ACCEPTED",
    classification: str = "PRIMARY_ASSERTION",
    parents: list[str] | None = None,
    supersedes: str | None = None,
    human_review: bool = False,
) -> dict[str, object]:
    return {
        "schema_id": SUPPORTED_SCHEMA_ID,
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "record_family": family,
        "snapshot_id": snapshot_id,
        "ingestion_batch_id": "batch:synthetic:wp156",
        "event_time": event_time,
        "observed_time": observed_time,
        "ingestion_time": ingestion_time,
        "lifecycle_state": lifecycle,
        "classification": classification,
        "lineage_parent_ids": [] if parents is None else parents,
        "supersedes_record_version_id": supersedes,
        "normalizer_version": "normalizer:wp156:v1",
        "validator_version": "validator:wp156:v1",
        "parameter_set_id": "parameters:wp156:synthetic:v1",
        "human_review_required": human_review,
    }


def _metadata(
    *,
    source_assertion_id: str = "assertion:metadata:001",
    observed_time: str = "2026-01-01T00:00:01Z",
    ingestion_time: str = "2026-01-01T00:00:02Z",
    classification: str = "PRIMARY_ASSERTION",
    parents: list[str] | None = None,
    supersedes: str | None = None,
    human_review: bool = False,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    record = _common(
        "MARKET_OBSERVATION",
        snapshot_id="snapshot:synthetic:metadata:001",
        event_time="2026-01-01T00:00:00Z",
        observed_time=observed_time,
        ingestion_time=ingestion_time,
        classification=classification,
        parents=parents,
        supersedes=supersedes,
        human_review=human_review,
    )
    record.update(
        {
            "observation_kind": "MARKET_METADATA",
            "platform_id": "platform:synthetic",
            "event_id": "event:synthetic:001",
            "market_id": "market:synthetic:001",
            "token_id": None,
            "source_id": "source:synthetic:public",
            "source_assertion_id": source_assertion_id,
            "source_snapshot_id": "source-snapshot:synthetic:metadata:001",
            "canonical_payload": payload
            or {
                "market_status": "OPEN_SYNTHETIC",
                "outcome_labels": ["YES_SYNTHETIC", "NO_SYNTHETIC"],
                "question_text": "Will the synthetic condition be true?",
            },
        }
    )
    return record


def _source(
    *,
    observed_time: str = "2026-01-01T00:00:01Z",
    ingestion_time: str = "2026-01-01T00:00:02Z",
    raw_hash: str = "1" * 64,
    classification: str = "PRIMARY_ASSERTION",
    lifecycle: str = "RAW_CAPTURED",
    parents: list[str] | None = None,
    supersedes: str | None = None,
    prior_source_snapshot_id: str | None = None,
) -> dict[str, object]:
    record = _common(
        "SOURCE_SNAPSHOT",
        snapshot_id="snapshot:synthetic:source:001",
        event_time=None,
        observed_time=observed_time,
        ingestion_time=ingestion_time,
        lifecycle=lifecycle,
        classification=classification,
        parents=parents,
        supersedes=supersedes,
    )
    record.update(
        {
            "source_id": "source:synthetic:public",
            "source_type": "SANITIZED_SYNTHETIC_SOURCE",
            "source_reference": "https://example.invalid/wp156/source",
            "media_type": "application/json",
            "raw_content_sha256": raw_hash,
            "byte_length": 128,
            "retrieval_method": "SYNTHETIC_IN_MEMORY",
            "retrieval_version": "retrieval:wp156:v1",
            "upstream_revision": None,
            "prior_source_snapshot_id": prior_source_snapshot_id,
            "access_classification": "SANITIZED_SYNTHETIC",
            "canonical_payload": {
                "content_class": "SANITIZED_SYNTHETIC",
                "source_notice": "No raw source content is retained.",
            },
        }
    )
    return record


def _rule(source_snapshot_id: str) -> dict[str, object]:
    record = _common(
        "RESOLUTION_RULE_SNAPSHOT",
        snapshot_id="snapshot:synthetic:rule:001",
        event_time=None,
        observed_time="2026-01-01T00:00:03Z",
        ingestion_time="2026-01-01T00:00:04Z",
    )
    record.update(
        {
            "platform_id": "platform:synthetic",
            "event_id": "event:synthetic:001",
            "market_id": "market:synthetic:001",
            "resolution_source_id": "resolution-source:synthetic:primary",
            "source_snapshot_id": source_snapshot_id,
            "rule_content_sha256": "2" * 64,
            "source_declared_effective_time": None,
            "ambiguity_labels": ["NONE_IDENTIFIED"],
            "source_hierarchy_rank": "PRIMARY_RESOLUTION_SOURCE",
            "human_review_state": "NOT_REVIEWED",
            "canonical_payload": {
                "normalized_rule_summary": "Synthetic condition resolves from synthetic evidence.",
                "sanitized": True,
            },
        }
    )
    return record


def _result(
    builder: Callable[[dict[str, object]], PointInTimeBuildResult],
    record: dict[str, object],
) -> PointInTimeBuildResult:
    return builder(record)


def _record_id(result: PointInTimeBuildResult) -> str:
    if not result.is_valid or result.record is None:
        raise AssertionError("SYNTHETIC_CORPUS_INTERNAL_BUILD_FAILURE")
    return result.record.envelope.record_version_id


def _case(
    case_id: str,
    case_family: str,
    input_record: dict[str, object],
    related: tuple[str, ...],
    result: PointInTimeBuildResult | None,
    *,
    expected_valid: bool | None = None,
    expected_status: str | None = None,
    expected_errors: tuple[str, ...] | None = None,
    expected_warnings: tuple[str, ...] | None = None,
    expected_family: str | None = None,
    expected_record_version_id: str | None = None,
) -> SyntheticPointInTimeCase:
    if result is not None:
        valid = result.is_valid
        status = result.status
        errors = result.error_codes
        warnings = result.warning_codes
        family = (
            result.record.envelope.record_family if result.record is not None else expected_family
        )
        record_id = (
            result.record.envelope.record_version_id
            if result.record is not None
            else expected_record_version_id
        )
    else:
        valid = bool(expected_valid)
        status = str(expected_status)
        errors = expected_errors or ()
        warnings = expected_warnings or ()
        family = expected_family
        record_id = expected_record_version_id
    return SyntheticPointInTimeCase(
        case_id=case_id,
        case_family=case_family,
        input_json=json.dumps(
            input_record,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ),
        related_case_ids=related,
        expected_valid=valid,
        expected_status=status,
        expected_error_codes=errors,
        expected_warning_codes=warnings,
        expected_record_family=family,
        expected_record_version_id=record_id,
        safety_notice=_SAFETY_NOTICE,
    )


def _build_cases() -> tuple[SyntheticPointInTimeCase, ...]:
    cases: list[SyntheticPointInTimeCase] = []

    c01_input = _metadata()
    c01_result = _result(build_market_observation, c01_input)
    c01_id = _record_id(c01_result)
    cases.append(
        _case(
            "PIT-C01-VALID-MARKET-METADATA",
            "MARKET_OBSERVATION",
            c01_input,
            (),
            c01_result,
        )
    )

    c02_input = _common(
        "MARKET_OBSERVATION",
        snapshot_id="snapshot:synthetic:book:001",
        event_time=None,
        observed_time="2026-01-01T00:00:05Z",
        ingestion_time="2026-01-01T00:00:06Z",
    )
    c02_input.update(
        {
            "observation_kind": "ORDER_BOOK",
            "platform_id": "platform:synthetic",
            "event_id": "event:synthetic:001",
            "market_id": "market:synthetic:001",
            "token_id": "token:synthetic:yes",
            "source_id": "source:synthetic:public",
            "source_assertion_id": "assertion:book:001",
            "source_snapshot_id": "source-snapshot:synthetic:book:001",
            "canonical_payload": {
                "asks": [{"price": "0.55", "size": "12.5"}],
                "bids": [{"price": "0.45", "size": "10"}],
                "minimum_order_size": "1",
                "tick_size": "0.01",
            },
        }
    )
    cases.append(
        _case(
            "PIT-C02-VALID-ORDER-BOOK-MISSING-EVENT-TIME",
            "MARKET_OBSERVATION",
            c02_input,
            (),
            _result(build_market_observation, c02_input),
        )
    )

    c03_input = _common(
        "MARKET_OBSERVATION",
        snapshot_id="snapshot:synthetic:trade:001",
        event_time="2026-01-01T00:00:06.123Z",
        observed_time="2026-01-01T00:00:07.123Z",
        ingestion_time="2026-01-01T00:00:08.123+00:00",
    )
    c03_input.update(
        {
            "observation_kind": "PUBLIC_TRADE",
            "platform_id": "platform:synthetic",
            "event_id": "event:synthetic:001",
            "market_id": "market:synthetic:001",
            "token_id": "token:synthetic:yes",
            "source_id": "source:synthetic:public",
            "source_assertion_id": "assertion:trade:001",
            "source_snapshot_id": "source-snapshot:synthetic:trade:001",
            "canonical_payload": {
                "price": "0.51",
                "side_observed": "BUY_OBSERVED",
                "size": "3.25",
                "transaction_reference": "transaction:synthetic:001",
            },
        }
    )
    cases.append(
        _case(
            "PIT-C03-VALID-PUBLIC-TRADE",
            "MARKET_OBSERVATION",
            c03_input,
            (),
            _result(build_market_observation, c03_input),
        )
    )

    c04_input = _source()
    c04_result = _result(build_source_snapshot, c04_input)
    c04_id = _record_id(c04_result)
    c04_source_snapshot_id = c04_result.record.envelope.source_snapshot_id  # type: ignore[union-attr]
    cases.append(
        _case(
            "PIT-C04-VALID-SOURCE-SNAPSHOT",
            "SOURCE_SNAPSHOT",
            c04_input,
            (),
            c04_result,
        )
    )

    c05_input = _rule(str(c04_source_snapshot_id))
    cases.append(
        _case(
            "PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT",
            "RESOLUTION_RULE_SNAPSHOT",
            c05_input,
            ("PIT-C04-VALID-SOURCE-SNAPSHOT",),
            _result(build_resolution_rule_snapshot, c05_input),
        )
    )

    c06_input = _metadata(
        source_assertion_id="assertion:metadata:late",
        observed_time="2026-01-02T00:00:00Z",
        ingestion_time="2026-01-02T00:00:01Z",
        classification="LATE_ARRIVAL",
    )
    cases.append(
        _case(
            "PIT-C06-VALID-LATE-ARRIVAL",
            "MARKET_OBSERVATION",
            c06_input,
            (),
            _result(build_market_observation, c06_input),
        )
    )

    c07_input = _source(
        observed_time="2026-01-01T00:01:00Z",
        ingestion_time="2026-01-01T00:01:01Z",
        raw_hash="3" * 64,
        classification="SOURCE_REVISION",
        parents=[c04_id],
        supersedes=c04_id,
        prior_source_snapshot_id=str(c04_source_snapshot_id),
    )
    c07_result = _result(build_source_snapshot, c07_input)
    c07_id = _record_id(c07_result)
    cases.append(
        _case(
            "PIT-C07-VALID-SOURCE-REVISION",
            "SOURCE_SNAPSHOT",
            c07_input,
            ("PIT-C04-VALID-SOURCE-SNAPSHOT",),
            c07_result,
        )
    )

    c08_input = _metadata(
        observed_time="2026-01-01T00:02:00Z",
        ingestion_time="2026-01-01T00:02:01Z",
        classification="PROJECT_CORRECTION",
        parents=[c01_id],
        supersedes=c01_id,
        payload={
            "market_status": "OPEN_SYNTHETIC",
            "outcome_labels": ["YES_SYNTHETIC", "NO_SYNTHETIC"],
            "question_text": "Will the corrected synthetic condition be true?",
        },
    )
    cases.append(
        _case(
            "PIT-C08-VALID-PROJECT-CORRECTION",
            "MARKET_OBSERVATION",
            c08_input,
            ("PIT-C01-VALID-MARKET-METADATA",),
            _result(build_market_observation, c08_input),
        )
    )

    c09_input = _source(
        observed_time="2026-01-01T00:03:00Z",
        ingestion_time="2026-01-01T00:03:01Z",
        raw_hash="4" * 64,
        classification="SOURCE_RETRACTION",
        lifecycle="RETRACTED_BY_SOURCE",
        parents=[c07_id],
        supersedes=c07_id,
        prior_source_snapshot_id=str(c07_result.record.envelope.source_snapshot_id),  # type: ignore[union-attr]
    )
    cases.append(
        _case(
            "PIT-C09-VALID-SOURCE-RETRACTION",
            "SOURCE_SNAPSHOT",
            c09_input,
            ("PIT-C04-VALID-SOURCE-SNAPSHOT", "PIT-C07-VALID-SOURCE-REVISION"),
            _result(build_source_snapshot, c09_input),
        )
    )

    c10_input = _metadata(
        observed_time="2026-01-01T00:04:00Z",
        ingestion_time="2026-01-01T00:04:01Z",
        classification="EXACT_DUPLICATE",
        parents=[c01_id],
    )
    cases.append(
        _case(
            "PIT-C10-VALID-EXACT-DUPLICATE",
            "MARKET_OBSERVATION",
            c10_input,
            ("PIT-C01-VALID-MARKET-METADATA",),
            _result(build_market_observation, c10_input),
        )
    )

    c11_input = _metadata(
        observed_time="2026-01-01T00:05:00Z",
        ingestion_time="2026-01-01T00:05:01Z",
        classification="SEMANTIC_DUPLICATE",
        parents=[c01_id],
        payload={
            "market_status": "OPEN_SYNTHETIC",
            "outcome_labels": ["YES_SYNTHETIC", "NO_SYNTHETIC"],
            "question_text": "Will the synthetic condition be true?",
            "source_representation": "ALTERNATE_SYNTHETIC",
        },
    )
    cases.append(
        _case(
            "PIT-C11-VALID-SEMANTIC-DUPLICATE",
            "MARKET_OBSERVATION",
            c11_input,
            ("PIT-C01-VALID-MARKET-METADATA",),
            _result(build_market_observation, c11_input),
        )
    )

    c12_input = _metadata(
        observed_time="2026-01-01T00:06:00Z",
        ingestion_time="2026-01-01T00:06:01Z",
        classification="CONFLICT",
        parents=[c01_id],
        human_review=True,
    )
    cases.append(
        _case(
            "PIT-C12-CONFLICT-REQUIRES-REVIEW",
            "MARKET_OBSERVATION",
            c12_input,
            ("PIT-C01-VALID-MARKET-METADATA",),
            _result(build_market_observation, c12_input),
            expected_family="MARKET_OBSERVATION",
        )
    )

    c13_input = _metadata()
    c13_input["observed_time"] = "2026-01-01T00:00:01"
    cases.append(
        _case(
            "PIT-C13-INVALID-NAIVE-TIME",
            "MARKET_OBSERVATION",
            c13_input,
            (),
            _result(build_market_observation, c13_input),
            expected_family="MARKET_OBSERVATION",
        )
    )

    c14_input = _metadata(
        observed_time="2026-01-01T00:00:02Z",
        ingestion_time="2026-01-01T00:00:01Z",
    )
    cases.append(
        _case(
            "PIT-C14-INVALID-INGESTION-BEFORE-OBSERVED",
            "MARKET_OBSERVATION",
            c14_input,
            (),
            _result(build_market_observation, c14_input),
            expected_family="MARKET_OBSERVATION",
        )
    )

    c15_input = _metadata()
    c15_input["schema_version"] = "2.0.0"
    cases.append(
        _case(
            "PIT-C15-INVALID-SCHEMA-MAJOR",
            "MARKET_OBSERVATION",
            c15_input,
            (),
            _result(build_market_observation, c15_input),
            expected_family="MARKET_OBSERVATION",
        )
    )

    c16_input = _metadata()
    c16_input["unexpected_field"] = "synthetic"
    cases.append(
        _case(
            "PIT-C16-INVALID-UNKNOWN-FIELD",
            "MARKET_OBSERVATION",
            c16_input,
            (),
            _result(build_market_observation, c16_input),
            expected_family="MARKET_OBSERVATION",
        )
    )

    c17_input = _metadata(
        payload={
            "market_status": "OPEN_SYNTHETIC",
            "outcome_labels": ["YES_SYNTHETIC", "NO_SYNTHETIC"],
            "question_text": "Neutral synthetic input.",
            "nested": {"api_key": "NEUTRAL_REDACTED_SYNTHETIC"},
        }
    )
    cases.append(
        _case(
            "PIT-C17-INVALID-NESTED-SECRET-KEY",
            "MARKET_OBSERVATION",
            c17_input,
            (),
            _result(build_market_observation, c17_input),
            expected_family="MARKET_OBSERVATION",
        )
    )

    c18_input = _metadata()
    payload18 = dict(c18_input["canonical_payload"])  # type: ignore[arg-type]
    payload18["probability"] = 0.5
    c18_input["canonical_payload"] = payload18
    cases.append(
        _case(
            "PIT-C18-INVALID-FLOAT-PAYLOAD",
            "MARKET_OBSERVATION",
            c18_input,
            (),
            _result(build_market_observation, c18_input),
            expected_family="MARKET_OBSERVATION",
        )
    )

    c19_input = {
        "batch_case": "LINEAGE_CYCLE",
        "record_ids": ["record:synthetic:cycle:a", "record:synthetic:cycle:b"],
        "parent_ids": ["record:synthetic:cycle:b", "record:synthetic:cycle:a"],
    }
    cases.append(
        _case(
            "PIT-C19-INVALID-LINEAGE-CYCLE",
            "BATCH",
            c19_input,
            (),
            None,
            expected_valid=False,
            expected_status="REJECTED_CONTRACT",
            expected_errors=("LINEAGE_CYCLE",),
        )
    )

    c20_input = _metadata(
        observed_time="2026-01-01T00:00:00.5Z",
        ingestion_time="2026-01-01T00:00:01Z",
        classification="PROJECT_CORRECTION",
        parents=[c01_id],
        supersedes=c01_id,
        payload={
            "market_status": "OPEN_SYNTHETIC",
            "outcome_labels": ["YES_SYNTHETIC", "NO_SYNTHETIC"],
            "question_text": "Backdated synthetic correction.",
        },
    )
    c20_wrapper = {
        "batch_case": "CORRECTION_BACKDATE",
        "parent_case_id": "PIT-C01-VALID-MARKET-METADATA",
        "correction_input": c20_input,
    }
    cases.append(
        _case(
            "PIT-C20-INVALID-CORRECTION-BACKDATE",
            "BATCH",
            c20_wrapper,
            ("PIT-C01-VALID-MARKET-METADATA",),
            None,
            expected_valid=False,
            expected_status="REJECTED_CONTRACT",
            expected_errors=("CORRECTION_VISIBILITY_VIOLATION",),
            expected_warnings=("PROJECT_CORRECTION_DECLARED",),
            expected_family="MARKET_OBSERVATION",
        )
    )

    return tuple(cases)


def get_synthetic_point_in_time_cases() -> tuple[SyntheticPointInTimeCase, ...]:
    """Return the exact ordered immutable 20-case synthetic corpus."""

    return _build_cases()


def load_synthetic_case_input(case_id: str) -> dict[str, object]:
    """Return a fresh mutable mapping decoded from a stored canonical input."""

    for case in _build_cases():
        if case.case_id == case_id:
            loaded = json.loads(case.input_json)
            if not isinstance(loaded, dict):
                raise ValueError("SYNTHETIC_CASE_INPUT_NOT_MAPPING")
            return loaded
    raise KeyError("SYNTHETIC_CASE_NOT_FOUND")
