"""Sanitized deterministic in-memory synthetic corpus for as-of queries.

Every record is a valid WP156 public record object built with fixed
timestamps and no wall clock, random IDs, real market/account/wallet data, or
file paths. Conflict records are built through the WP156 review-only handoff
and are never authoritative. Expected result hashes are committed constants and
are never generated from the result under test.
"""

from __future__ import annotations

from .as_of_query import (
    EventTimeWindow,
    PointInTimeQuerySpec,
    SyntheticAsOfQueryCase,
)
from .records import (
    SUPPORTED_SCHEMA_ID,
    SUPPORTED_SCHEMA_VERSION,
    PointInTimeRecord,
    build_market_observation,
    build_resolution_rule_snapshot,
    build_review_conflict_record,
    build_source_snapshot,
)


_SAFETY_NOTICE = (
    "SANITIZED_SYNTHETIC_ONLY_NO_EXECUTION_AUTHORITY_NO_REAL_MARKET_DATA"
)

_METADATA_PAYLOAD = {
    "market_status": "OPEN_SYNTHETIC",
    "outcome_labels": ["YES_SYNTHETIC", "NO_SYNTHETIC"],
    "question_text": "Will the synthetic condition be true?",
}
_CORRECTION_PAYLOAD = {
    "market_status": "OPEN_SYNTHETIC",
    "outcome_labels": ["YES_SYNTHETIC", "NO_SYNTHETIC"],
    "question_text": "Will the corrected synthetic condition be true?",
}
_SEMANTIC_PAYLOAD = {
    "market_status": "OPEN_SYNTHETIC",
    "outcome_labels": ["YES_SYNTHETIC", "NO_SYNTHETIC"],
    "question_text": "Will the synthetic condition be true?",
    "source_representation": "ALTERNATE_SYNTHETIC",
}
_BOOK_PAYLOAD = {
    "asks": [{"price": "0.55", "size": "12.5"}],
    "bids": [{"price": "0.45", "size": "10"}],
    "minimum_order_size": "1",
    "tick_size": "0.01",
}


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
        "ingestion_batch_id": "batch:synthetic:wp157",
        "event_time": event_time,
        "observed_time": observed_time,
        "ingestion_time": ingestion_time,
        "lifecycle_state": lifecycle,
        "classification": classification,
        "lineage_parent_ids": [] if parents is None else parents,
        "supersedes_record_version_id": supersedes,
        "normalizer_version": "normalizer:wp157:v1",
        "validator_version": "validator:wp157:v1",
        "parameter_set_id": "parameters:wp157:synthetic:v1",
        "human_review_required": human_review,
    }


def _meta(
    *,
    source_assertion_id: str,
    observed_time: str,
    ingestion_time: str,
    event_time: str | None = "2026-01-01T00:00:00Z",
    classification: str = "PRIMARY_ASSERTION",
    parents: list[str] | None = None,
    supersedes: str | None = None,
    human_review: bool = False,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    record = _common(
        "MARKET_OBSERVATION",
        snapshot_id="snapshot:synthetic:metadata:001",
        event_time=event_time,
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
            "canonical_payload": payload or dict(_METADATA_PAYLOAD),
        }
    )
    return record


def _book(*, observed_time: str, ingestion_time: str) -> dict[str, object]:
    record = _common(
        "MARKET_OBSERVATION",
        snapshot_id="snapshot:synthetic:book:001",
        event_time=None,
        observed_time=observed_time,
        ingestion_time=ingestion_time,
    )
    record.update(
        {
            "observation_kind": "ORDER_BOOK",
            "platform_id": "platform:synthetic",
            "event_id": "event:synthetic:001",
            "market_id": "market:synthetic:001",
            "token_id": "token:synthetic:yes",
            "source_id": "source:synthetic:public",
            "source_assertion_id": "assertion:book:001",
            "source_snapshot_id": "source-snapshot:synthetic:book:001",
            "canonical_payload": dict(_BOOK_PAYLOAD),
        }
    )
    return record


def _source(
    *,
    observed_time: str,
    ingestion_time: str,
    raw_hash: str,
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
            "source_reference": "https://example.invalid/wp157/source",
            "media_type": "application/json",
            "raw_content_sha256": raw_hash,
            "byte_length": 128,
            "retrieval_method": "SYNTHETIC_IN_MEMORY",
            "retrieval_version": "retrieval:wp157:v1",
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


def _rule(*, source_snapshot_id: str, observed_time: str, ingestion_time: str) -> dict[str, object]:
    record = _common(
        "RESOLUTION_RULE_SNAPSHOT",
        snapshot_id="snapshot:synthetic:rule:001",
        event_time=None,
        observed_time=observed_time,
        ingestion_time=ingestion_time,
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


def _require(result: object) -> PointInTimeRecord:
    record = getattr(result, "record", None)
    if record is None or not getattr(result, "is_valid", False):
        raise AssertionError("SYNTHETIC_AS_OF_CORPUS_INTERNAL_BUILD_FAILURE")
    return record


def build_synthetic_as_of_records() -> dict[str, PointInTimeRecord]:
    """Build the deterministic named record set used by the as-of query cases."""

    records: dict[str, PointInTimeRecord] = {}

    meta_primary = _require(
        build_market_observation(
            _meta(
                source_assertion_id="assertion:metadata:001",
                observed_time="2026-01-01T00:00:01Z",
                ingestion_time="2026-01-01T00:00:02Z",
            )
        )
    )
    records["MKT-META-PRIMARY"] = meta_primary
    primary_id = meta_primary.envelope.record_version_id

    records["MKT-META-CORRECTION"] = _require(
        build_market_observation(
            _meta(
                source_assertion_id="assertion:metadata:001",
                observed_time="2026-01-01T00:02:00Z",
                ingestion_time="2026-01-01T00:02:01Z",
                classification="PROJECT_CORRECTION",
                parents=[primary_id],
                supersedes=primary_id,
                payload=dict(_CORRECTION_PAYLOAD),
            )
        )
    )

    records["MKT-EXACT-DUP"] = _require(
        build_market_observation(
            _meta(
                source_assertion_id="assertion:metadata:001",
                observed_time="2026-01-01T00:04:00Z",
                ingestion_time="2026-01-01T00:04:01Z",
                classification="EXACT_DUPLICATE",
                parents=[primary_id],
            )
        )
    )

    records["MKT-SEMANTIC-DUP"] = _require(
        build_market_observation(
            _meta(
                source_assertion_id="assertion:metadata:001",
                observed_time="2026-01-01T00:05:00Z",
                ingestion_time="2026-01-01T00:05:01Z",
                classification="SEMANTIC_DUPLICATE",
                parents=[primary_id],
                payload=dict(_SEMANTIC_PAYLOAD),
            )
        )
    )

    records["MKT-CONFLICT"] = _require(
        build_review_conflict_record(
            _meta(
                source_assertion_id="assertion:metadata:001",
                observed_time="2026-01-01T00:06:00Z",
                ingestion_time="2026-01-01T00:06:01Z",
                classification="CONFLICT",
                parents=[primary_id],
                human_review=True,
            )
        )
    )

    records["MKT-LATE"] = _require(
        build_market_observation(
            _meta(
                source_assertion_id="assertion:metadata:late",
                observed_time="2026-01-01T00:04:00Z",
                ingestion_time="2026-01-01T00:04:01Z",
                classification="LATE_ARRIVAL",
            )
        )
    )

    records["MKT-BOOK-NOEVENT"] = _require(
        build_market_observation(
            _book(
                observed_time="2026-01-01T00:00:05Z",
                ingestion_time="2026-01-01T00:00:06Z",
            )
        )
    )

    source_primary = _require(
        build_source_snapshot(
            _source(
                observed_time="2026-01-01T00:00:01Z",
                ingestion_time="2026-01-01T00:00:02Z",
                raw_hash="1" * 64,
            )
        )
    )
    records["SRC-PRIMARY"] = source_primary
    source_primary_id = source_primary.envelope.record_version_id
    source_primary_snapshot = source_primary.envelope.source_snapshot_id

    source_revision = _require(
        build_source_snapshot(
            _source(
                observed_time="2026-01-01T00:01:00Z",
                ingestion_time="2026-01-01T00:01:01Z",
                raw_hash="3" * 64,
                classification="SOURCE_REVISION",
                parents=[source_primary_id],
                supersedes=source_primary_id,
                prior_source_snapshot_id=source_primary_snapshot,
            )
        )
    )
    records["SRC-REVISION"] = source_revision
    source_revision_id = source_revision.envelope.record_version_id

    records["SRC-RETRACTION"] = _require(
        build_source_snapshot(
            _source(
                observed_time="2026-01-01T00:03:00Z",
                ingestion_time="2026-01-01T00:03:01Z",
                raw_hash="4" * 64,
                classification="SOURCE_RETRACTION",
                lifecycle="RETRACTED_BY_SOURCE",
                parents=[source_revision_id],
                supersedes=source_revision_id,
                prior_source_snapshot_id=source_revision.envelope.source_snapshot_id,
            )
        )
    )

    records["RULE-PRIMARY"] = _require(
        build_resolution_rule_snapshot(
            _rule(
                source_snapshot_id=str(source_primary_snapshot),
                observed_time="2026-01-01T00:00:03Z",
                ingestion_time="2026-01-01T00:00:04Z",
            )
        )
    )

    return records


def _spec(
    query_id: str,
    *,
    cutoff_mode: str = "AS_OF_INGESTION_TIME",
    cutoff_time: str,
    result_view: str,
    record_families: tuple[str, ...] = (),
    observation_kinds: tuple[str, ...] = (),
    platform_ids: tuple[str, ...] = (),
    event_ids: tuple[str, ...] = (),
    market_ids: tuple[str, ...] = (),
    token_ids: tuple[str, ...] = (),
    source_ids: tuple[str, ...] = (),
    resolution_source_ids: tuple[str, ...] = (),
    event_time_window: EventTimeWindow | None = None,
    include_conflicts_for_review: bool = False,
    include_retracted_history: bool = False,
) -> PointInTimeQuerySpec:
    return PointInTimeQuerySpec(
        query_id=query_id,
        cutoff_mode=cutoff_mode,
        cutoff_time=cutoff_time,
        result_view=result_view,
        record_families=record_families,
        observation_kinds=observation_kinds,
        platform_ids=platform_ids,
        event_ids=event_ids,
        market_ids=market_ids,
        token_ids=token_ids,
        source_ids=source_ids,
        resolution_source_ids=resolution_source_ids,
        event_time_window=event_time_window,
        include_conflicts_for_review=include_conflicts_for_review,
        include_retracted_history=include_retracted_history,
        parameter_set_id="parameters:wp157:synthetic:v1",
    )


# ── Committed constants: expected result hashes and outcomes ─────────────────
# These are deterministic committed constants. They are never generated from the
# result under test; they are computed once and pinned. See WP157 Section 18.

_EXPECTED_RESULT_SHA256: dict[str, str] = {
    "ASOF-C01-BEFORE-FIRST-INGESTION": "4bcb569b2d7a7999668426d781ab2df72b254fd5e14d537dd2f604604afc11b7",
    "ASOF-C02-PRIMARY-VISIBLE": "132fcb803da8483d2bf3710a52d112bd5314872cc0e85cded3fe40eed4d8e3df",
    "ASOF-C03-BEFORE-CORRECTION": "e76d0350ccde5654edd82dcad73914e2bf4212c66e8c83270219665b491c4d46",
    "ASOF-C04-AFTER-CORRECTION": "0faaf23db93381932245b6f6ec5d7683951c9a1c09fc101a18d476abca2b3dc8",
    "ASOF-C05-BEFORE-SOURCE-REVISION": "d08f77706c6bdc2b9a61bde7762fe3271874de1b0e21fecab1c63a467849c1a7",
    "ASOF-C06-AFTER-SOURCE-REVISION": "99a7d3900795697dd52c62f46a1738bb02ce49984d27301d6063e7433b3f6cd0",
    "ASOF-C07-BEFORE-RETRACTION": "172ea15f6c2b03ca6d8f86fd7a798b4ae66bec844a03054cea230f888b0f131c",
    "ASOF-C08-AFTER-RETRACTION": "1056acf1cda643ad7cd409980dd60b4930edda06bea6b29a44f62f0ec8689ffa",
    "ASOF-C09-LATE-ARRIVAL-NOT-BACKDATED": "9ad894a7ecf378fe0bdf464af697c8072c9257a8b080286f3db50ddc53218297",
    "ASOF-C10-OBSERVED-DIAGNOSTIC-INGESTION-BOUNDED": "8768abe712377475c658acd7c77449b0dfe0d321fffff94f807f76225a1c75da",
    "ASOF-C11-EVENT-WINDOW-AFTER-VISIBILITY": "361fd7061f4641cfc63ee32d0ffbe9eef4ddf55b9292ce62588a8936cb224977",
    "ASOF-C12-MISSING-EVENT-TIME-EXCLUDED": "c2e42d6a1e1635384165de538f94afadd2f8bf8f7e67476111a64bd6bfe9ce3a",
    "ASOF-C13-MISSING-EVENT-TIME-INCLUDED": "63c007cf947e3fec0ce10104816a4a92f09e06191607697f8e06b824348d2f57",
    "ASOF-C14-ENTITY-FILTER": "0902fbf2a2216f22bd99a837b1bbb055424fd99908845c67c9dd397d597795c2",
    "ASOF-C15-FAMILY-AND-KIND-FILTER": "537de31414f08bc3bb57f8addc19890d43290554ba0237df4302d1f708586614",
    "ASOF-C16-VISIBLE-HISTORY": "3a91beb5b0b59fa685712343fb2067a99ee40d9b24dade687158f1011a1053e2",
    "ASOF-C17-ENTITY-TIMELINE": "8f6ded466dc74b2f5059b461a6513f4e92429187d949d3aaaa1c4a46829c3153",
    "ASOF-C18-CONFLICT-EXCLUDED": "bd34549e6b6a006efee368ba8f1884c58a28cfab551ade4bcec7eb6d09ef4497",
    "ASOF-C19-CONFLICT-REVIEW-ONLY": "706716c78032e81b2f363500fe0121537c6e2263b21052004feafd7062974fb7",
    "ASOF-C20-INVALID-BATCH-REJECTED": "",
    "ASOF-C21-INVALID-SPEC-REJECTED": "",
    "ASOF-C22-INPUT-PERMUTATION-INVARIANT": "38f7491732ecf592d489f47f98eb0eb21cfb06888556b831456036e5ef44dd51",
    "ASOF-C23-EMPTY-VALID-RECEIPT": "04951396abae62ead93d118a15fa527a5c93ab4e8d098e20642f29055cacefae",
    "ASOF-C24-FUTURE-RULE-SNAPSHOT-EXCLUDED": "1c34dbdd2e686504d39cd60ddb3d6d9b7809ee4380d489efaba159fb0e27fa91",
}


def _rid(records: dict[str, PointInTimeRecord], *names: str) -> tuple[str, ...]:
    return tuple(records[name].envelope.record_version_id for name in names)


def _case_specs() -> tuple[tuple[str, tuple[str, ...], PointInTimeQuerySpec, dict[str, object]], ...]:
    """Return (case_id, record_case_ids, spec, expectations) for each case.

    Expectations use record-case-id references for the id tuples so that the
    committed identities are derived from the deterministic input records, never
    from the query result under test.
    """

    return (
        (
            "ASOF-C01-BEFORE-FIRST-INGESTION",
            ("MKT-META-PRIMARY",),
            _spec(
                "query:asof:c01",
                cutoff_time="2026-01-01T00:00:00Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
            ),
            {
                "valid": True,
                "status": "QUERY_EMPTY",
                "errors": (),
                "warnings": ("EMPTY_RESULT",),
                "authoritative": (),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C02-PRIMARY-VISIBLE",
            ("MKT-META-PRIMARY",),
            _spec(
                "query:asof:c02",
                cutoff_time="2026-01-01T00:00:02Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": ("MKT-META-PRIMARY",),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C03-BEFORE-CORRECTION",
            ("MKT-META-PRIMARY", "MKT-META-CORRECTION"),
            _spec(
                "query:asof:c03",
                cutoff_time="2026-01-01T00:02:00Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": ("MKT-META-PRIMARY",),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C04-AFTER-CORRECTION",
            ("MKT-META-PRIMARY", "MKT-META-CORRECTION"),
            _spec(
                "query:asof:c04",
                cutoff_time="2026-01-01T00:02:01Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": ("MKT-META-CORRECTION",),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C05-BEFORE-SOURCE-REVISION",
            ("SRC-PRIMARY", "SRC-REVISION"),
            _spec(
                "query:asof:c05",
                cutoff_time="2026-01-01T00:01:00Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": ("SRC-PRIMARY",),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C06-AFTER-SOURCE-REVISION",
            ("SRC-PRIMARY", "SRC-REVISION"),
            _spec(
                "query:asof:c06",
                cutoff_time="2026-01-01T00:01:01Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": ("SRC-REVISION",),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C07-BEFORE-RETRACTION",
            ("SRC-PRIMARY", "SRC-REVISION", "SRC-RETRACTION"),
            _spec(
                "query:asof:c07",
                cutoff_time="2026-01-01T00:03:00Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": ("SRC-REVISION",),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C08-AFTER-RETRACTION",
            ("SRC-PRIMARY", "SRC-REVISION", "SRC-RETRACTION"),
            _spec(
                "query:asof:c08",
                cutoff_time="2026-01-01T00:03:01Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
            ),
            {
                "valid": True,
                "status": "QUERY_EMPTY",
                "errors": (),
                "warnings": ("EMPTY_RESULT",),
                "authoritative": (),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C09-LATE-ARRIVAL-NOT-BACKDATED",
            ("MKT-LATE",),
            _spec(
                "query:asof:c09",
                cutoff_time="2026-01-01T00:00:03Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
            ),
            {
                "valid": True,
                "status": "QUERY_EMPTY",
                "errors": (),
                "warnings": ("EMPTY_RESULT",),
                "authoritative": (),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C10-OBSERVED-DIAGNOSTIC-INGESTION-BOUNDED",
            ("MKT-META-PRIMARY", "MKT-LATE"),
            _spec(
                "query:asof:c10",
                cutoff_mode="AS_OF_OBSERVED_TIME_DIAGNOSTIC",
                cutoff_time="2026-01-01T00:00:03Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
            ),
            {
                "valid": True,
                "status": "QUERY_VALID_WITH_WARNINGS",
                "errors": (),
                "warnings": ("OBSERVED_TIME_DIAGNOSTIC_MODE",),
                "authoritative": ("MKT-META-PRIMARY",),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C11-EVENT-WINDOW-AFTER-VISIBILITY",
            ("MKT-META-PRIMARY", "MKT-BOOK-NOEVENT"),
            _spec(
                "query:asof:c11",
                cutoff_time="2026-01-01T00:00:06Z",
                result_view="VISIBLE_HISTORY",
                event_time_window=EventTimeWindow(
                    start_inclusive="2026-01-01T00:00:00Z",
                    end_exclusive="2026-01-01T00:00:01Z",
                    include_missing_event_time=False,
                ),
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": (),
                "history": ("MKT-META-PRIMARY",),
                "review": (),
            },
        ),
        (
            "ASOF-C12-MISSING-EVENT-TIME-EXCLUDED",
            ("MKT-BOOK-NOEVENT",),
            _spec(
                "query:asof:c12",
                cutoff_time="2026-01-01T00:00:06Z",
                result_view="VISIBLE_HISTORY",
                event_time_window=EventTimeWindow(
                    start_inclusive="2026-01-01T00:00:00Z",
                    end_exclusive="2026-01-01T00:01:00Z",
                    include_missing_event_time=False,
                ),
            ),
            {
                "valid": True,
                "status": "QUERY_EMPTY",
                "errors": (),
                "warnings": ("EMPTY_RESULT",),
                "authoritative": (),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C13-MISSING-EVENT-TIME-INCLUDED",
            ("MKT-BOOK-NOEVENT",),
            _spec(
                "query:asof:c13",
                cutoff_time="2026-01-01T00:00:06Z",
                result_view="VISIBLE_HISTORY",
                event_time_window=EventTimeWindow(
                    start_inclusive="2026-01-01T00:00:00Z",
                    end_exclusive="2026-01-01T00:01:00Z",
                    include_missing_event_time=True,
                ),
            ),
            {
                "valid": True,
                "status": "QUERY_VALID_WITH_WARNINGS",
                "errors": (),
                "warnings": ("EVENT_TIME_MISSING_INCLUDED",),
                "authoritative": (),
                "history": ("MKT-BOOK-NOEVENT",),
                "review": (),
            },
        ),
        (
            "ASOF-C14-ENTITY-FILTER",
            ("MKT-META-PRIMARY", "SRC-PRIMARY", "RULE-PRIMARY"),
            _spec(
                "query:asof:c14",
                cutoff_time="2026-01-01T00:00:06Z",
                result_view="VISIBLE_HISTORY",
                market_ids=("market:synthetic:001",),
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": (),
                "history": ("MKT-META-PRIMARY", "RULE-PRIMARY"),
                "review": (),
            },
        ),
        (
            "ASOF-C15-FAMILY-AND-KIND-FILTER",
            ("MKT-META-PRIMARY", "MKT-BOOK-NOEVENT", "SRC-PRIMARY"),
            _spec(
                "query:asof:c15",
                cutoff_time="2026-01-01T00:00:06Z",
                result_view="VISIBLE_HISTORY",
                record_families=("MARKET_OBSERVATION",),
                observation_kinds=("MARKET_METADATA",),
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": (),
                "history": ("MKT-META-PRIMARY",),
                "review": (),
            },
        ),
        (
            "ASOF-C16-VISIBLE-HISTORY",
            ("MKT-META-PRIMARY", "MKT-META-CORRECTION"),
            _spec(
                "query:asof:c16",
                cutoff_time="2026-01-01T00:02:01Z",
                result_view="VISIBLE_HISTORY",
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": (),
                "history": ("MKT-META-PRIMARY", "MKT-META-CORRECTION"),
                "review": (),
            },
        ),
        (
            "ASOF-C17-ENTITY-TIMELINE",
            ("MKT-META-PRIMARY", "MKT-META-CORRECTION"),
            _spec(
                "query:asof:c17",
                cutoff_time="2026-01-01T00:02:01Z",
                result_view="ENTITY_TIMELINE",
                market_ids=("market:synthetic:001",),
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": ("MKT-META-CORRECTION",),
                "history": ("MKT-META-PRIMARY", "MKT-META-CORRECTION"),
                "review": (),
            },
        ),
        (
            "ASOF-C18-CONFLICT-EXCLUDED",
            ("MKT-META-PRIMARY", "MKT-CONFLICT"),
            _spec(
                "query:asof:c18",
                cutoff_time="2026-01-01T00:06:01Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
                include_conflicts_for_review=False,
            ),
            {
                "valid": True,
                "status": "QUERY_VALID_WITH_WARNINGS",
                "errors": (),
                "warnings": ("CONFLICTS_EXCLUDED_FROM_AUTHORITY",),
                "authoritative": ("MKT-META-PRIMARY",),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C19-CONFLICT-REVIEW-ONLY",
            ("MKT-META-PRIMARY", "MKT-CONFLICT"),
            _spec(
                "query:asof:c19",
                cutoff_time="2026-01-01T00:06:01Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
                include_conflicts_for_review=True,
            ),
            {
                "valid": True,
                "status": "QUERY_CONFLICT_REQUIRES_REVIEW",
                "errors": (),
                "warnings": (),
                "authoritative": ("MKT-META-PRIMARY",),
                "history": (),
                "review": ("MKT-CONFLICT",),
            },
        ),
        (
            "ASOF-C20-INVALID-BATCH-REJECTED",
            ("__TAMPERED__",),
            _spec(
                "query:asof:c20",
                cutoff_time="2026-01-01T00:06:01Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
            ),
            {
                "valid": False,
                "status": "QUERY_REJECTED_RECORD_BATCH",
                "errors": ("RECORD_BATCH_INVALID",),
                "warnings": (),
                "authoritative": (),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C21-INVALID-SPEC-REJECTED",
            ("MKT-META-PRIMARY",),
            _spec(
                "query:asof:c21",
                cutoff_time="2026-01-01T00:00:02",
                result_view="AUTHORITATIVE_CURRENT_STATE",
            ),
            {
                "valid": False,
                "status": "QUERY_REJECTED_SPEC",
                "errors": ("CUTOFF_TIME_INVALID",),
                "warnings": (),
                "authoritative": (),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C22-INPUT-PERMUTATION-INVARIANT",
            ("MKT-META-PRIMARY", "MKT-META-CORRECTION", "SRC-PRIMARY"),
            _spec(
                "query:asof:c22",
                cutoff_time="2026-01-01T00:02:01Z",
                result_view="VISIBLE_HISTORY",
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": (),
                "history": ("MKT-META-PRIMARY", "SRC-PRIMARY", "MKT-META-CORRECTION"),
                "review": (),
            },
        ),
        (
            "ASOF-C23-EMPTY-VALID-RECEIPT",
            ("MKT-META-PRIMARY",),
            _spec(
                "query:asof:c23",
                cutoff_time="2026-01-01T00:00:06Z",
                result_view="AUTHORITATIVE_CURRENT_STATE",
                market_ids=("market:synthetic:999",),
            ),
            {
                "valid": True,
                "status": "QUERY_EMPTY",
                "errors": (),
                "warnings": ("EMPTY_RESULT",),
                "authoritative": (),
                "history": (),
                "review": (),
            },
        ),
        (
            "ASOF-C24-FUTURE-RULE-SNAPSHOT-EXCLUDED",
            ("MKT-META-PRIMARY", "RULE-PRIMARY"),
            _spec(
                "query:asof:c24",
                cutoff_time="2026-01-01T00:00:03Z",
                result_view="VISIBLE_HISTORY",
            ),
            {
                "valid": True,
                "status": "QUERY_VALID",
                "errors": (),
                "warnings": (),
                "authoritative": (),
                "history": ("MKT-META-PRIMARY",),
                "review": (),
            },
        ),
    )


def build_synthetic_as_of_query_cases() -> tuple[SyntheticAsOfQueryCase, ...]:
    """Return the exact ordered immutable 24-case synthetic as-of query corpus."""

    records = build_synthetic_as_of_records()
    cases: list[SyntheticAsOfQueryCase] = []
    for case_id, record_case_ids, spec, expected in _case_specs():
        cases.append(
            SyntheticAsOfQueryCase(
                case_id=case_id,
                record_case_ids=record_case_ids,
                query_spec=spec,
                expected_valid=bool(expected["valid"]),
                expected_status=str(expected["status"]),
                expected_error_codes=tuple(expected["errors"]),  # type: ignore[arg-type]
                expected_warning_codes=tuple(expected["warnings"]),  # type: ignore[arg-type]
                expected_authoritative_ids=_rid(records, *expected["authoritative"]),  # type: ignore[misc]
                expected_history_ids=_rid(records, *expected["history"]),  # type: ignore[misc]
                expected_review_conflict_ids=_rid(records, *expected["review"]),  # type: ignore[misc]
                expected_result_sha256=_EXPECTED_RESULT_SHA256[case_id],
                safety_notice=_SAFETY_NOTICE,
            )
        )
    return tuple(cases)


def build_synthetic_as_of_query_records_for_case(
    case_id: str,
) -> tuple[PointInTimeRecord, ...]:
    """Return the fresh record objects for one case, in committed order.

    ``ASOF-C20`` returns a deliberately tampered invalid record so that the
    query rejects the batch closed; every other case returns valid WP156
    records referenced by committed record-case id.
    """

    from dataclasses import replace

    records = build_synthetic_as_of_records()
    for candidate_id, record_case_ids, _spec_obj, _expected in _case_specs():
        if candidate_id != case_id:
            continue
        resolved: list[PointInTimeRecord] = []
        for name in record_case_ids:
            if name == "__TAMPERED__":
                base = records["MKT-META-PRIMARY"]
                resolved.append(replace(base, platform_id="platform:synthetic:tampered"))
            else:
                resolved.append(records[name])
        return tuple(resolved)
    raise KeyError("SYNTHETIC_AS_OF_QUERY_CASE_NOT_FOUND")
