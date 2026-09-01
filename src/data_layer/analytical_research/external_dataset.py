"""WP167 external-history provenance descriptor.

An ``ExternalDatasetDescriptor`` is deterministic, provenance-separated evidence
about immutable local external-history objects. It is EXTERNAL RESEARCH EVIDENCE
only and can never silently become canonical repo truth. Its identity is derived
from the source provenance (provider, dataset, source class, coverage, per-object
content hashes, schema fingerprint, timestamp semantics, event types, importer,
license) and is independent of any absolute local filesystem path.

This module performs no network access, constructs no client, downloads nothing,
and imports neither DuckDB nor NautilusTrader. Every result fixes
``advisory_only=True`` and ``no_execution_authority=True`` and never echoes an
absolute path, raw source row, exception text, or environment value.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from ..point_in_time_market_research import sha256_hex
from .research_dataset import analytical_canonical_bytes

# ── Locked labels, posture, and vocabularies ─────────────────────────────────

EXTERNAL_DATASET_LABEL = "EXTERNAL_HISTORY_PROVENANCE_DESCRIPTOR"
EXTERNAL_DATASET_POSTURE = (
    "LOCAL_OFFLINE_READ_ONLY_EXTERNAL_RESEARCH_EVIDENCE_NO_EXECUTION_AUTHORITY"
)

EXTERNAL_DATASET_SCHEMA_ID = "polymarket-external-history-descriptor"
EXTERNAL_DATASET_SCHEMA_VERSION = "1.0.0"

EXTERNAL_DATASET_ID_PREFIX = "externaldataset:sha256:"

SOURCE_CLASSES = (
    "NATIVE_OFFICIAL_CAPTURE",
    "OFFICIAL_HISTORICAL_EXPORT",
    "THIRD_PARTY_NATIVE_FRAME_ARCHIVE",
    "DERIVED_RESEARCH_DATASET",
    "BENCHMARK_ONLY",
)

EXTERNAL_DATASET_STATUSES = (
    "EXTERNAL_DESCRIPTOR_BUILT",
    "EXTERNAL_REJECTED",
)

EXTERNAL_DATASET_ERROR_CODES = (
    "EXTERNAL_DESCRIPTOR_INVALID",
    "EXTERNAL_SOURCE_FILE_INVALID",
    "EXTERNAL_SOURCE_SCHEMA_INVALID",
    "EXTERNAL_SOURCE_HASH_INVALID",
    "EXTERNAL_SOURCE_TIMESTAMP_INVALID",
    "EXTERNAL_SOURCE_EVENT_INVALID",
    "EXTERNAL_SOURCE_UNSUPPORTED",
    "EXTERNAL_QUERY_VALIDATION_FAILED",
)
_ERROR_ORDER = {code: index for index, code in enumerate(EXTERNAL_DATASET_ERROR_CODES)}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OBJECT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._=/-]{0,255}$")
_MAX_SCALAR = 512
_MAX_SOURCE_OBJECTS = 1024
_MAX_EVENT_TYPES = 64


# ── Public immutable dataclasses ─────────────────────────────────────────────


@dataclass(frozen=True)
class ExternalSourceObject:
    object_name: str
    source_sha256: str
    byte_length: int
    partition_identity: str


@dataclass(frozen=True)
class ExternalDatasetDescriptor:
    schema_id: str
    schema_version: str
    external_dataset_id: str
    provider_id: str
    dataset_name: str
    dataset_version: str
    source_class: str
    coverage_start: str
    coverage_end: str
    source_objects: tuple[ExternalSourceObject, ...]
    source_schema_fingerprint_sha256: str
    source_timestamp_semantics: str
    receive_timestamp_semantics: str
    event_types: tuple[str, ...]
    known_gap_policy: str
    quality_tier: str
    importer_id: str
    importer_version: str
    license_id: str
    attribution: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class ExternalDatasetBuildResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    descriptor: ExternalDatasetDescriptor | None
    advisory_only: bool
    no_execution_authority: bool


# ── Result constructors ──────────────────────────────────────────────────────


def _order(codes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(codes), key=lambda code: _ERROR_ORDER.get(code, len(_ERROR_ORDER))))


def _rejected(*codes: str) -> ExternalDatasetBuildResult:
    return ExternalDatasetBuildResult(
        is_valid=False,
        status="EXTERNAL_REJECTED",
        error_codes=_order(codes),
        descriptor=None,
        advisory_only=True,
        no_execution_authority=True,
    )


# ── Validation helpers ───────────────────────────────────────────────────────


def _valid_scalar(value: object) -> bool:
    return isinstance(value, str) and 0 < len(value) <= _MAX_SCALAR and value == value.strip()


def valid_utc_timestamp(value: object) -> datetime | None:
    """Return an aware UTC datetime for a canonical RFC3339 UTC string, else None."""

    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(None):
        return None
    return parsed.astimezone(timezone.utc)


def _valid_source_object(entry: object) -> bool:
    if type(entry) is not ExternalSourceObject:
        return False
    if not (_OBJECT_NAME_RE.fullmatch(entry.object_name) and "\\" not in entry.object_name):
        return False
    if entry.object_name.startswith("/") or re.match(r"^[A-Za-z]:", entry.object_name):
        return False
    if ".." in entry.object_name.split("/"):
        return False
    if not (isinstance(entry.source_sha256, str) and _SHA256_RE.fullmatch(entry.source_sha256)):
        return False
    if isinstance(entry.byte_length, bool) or not isinstance(entry.byte_length, int):
        return False
    if entry.byte_length <= 0:
        return False
    if not _valid_scalar(entry.partition_identity):
        return False
    return True


def _source_object_preimage(entry: ExternalSourceObject) -> dict[str, object]:
    return {
        "object_name": entry.object_name,
        "source_sha256": entry.source_sha256,
        "byte_length": entry.byte_length,
        "partition_identity": entry.partition_identity,
    }


def _descriptor_identity_preimage(
    *,
    provider_id: str,
    dataset_name: str,
    dataset_version: str,
    source_class: str,
    coverage_start: str,
    coverage_end: str,
    source_objects: tuple[ExternalSourceObject, ...],
    source_schema_fingerprint_sha256: str,
    source_timestamp_semantics: str,
    receive_timestamp_semantics: str,
    event_types: tuple[str, ...],
    known_gap_policy: str,
    quality_tier: str,
    importer_id: str,
    importer_version: str,
    license_id: str,
    attribution: str,
) -> dict[str, object]:
    # Source objects and event types are canonicalized into a stable order so the
    # identity is independent of input ordering; per-object content hashes remain,
    # so any source-byte mutation changes the identity. Absolute paths never enter
    # the preimage because object names are validated stable logical names.
    ordered_objects = sorted(
        (_source_object_preimage(entry) for entry in source_objects),
        key=lambda item: item["object_name"],
    )
    return {
        "schema_id": EXTERNAL_DATASET_SCHEMA_ID,
        "schema_version": EXTERNAL_DATASET_SCHEMA_VERSION,
        "provider_id": provider_id,
        "dataset_name": dataset_name,
        "dataset_version": dataset_version,
        "source_class": source_class,
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "source_objects": ordered_objects,
        "source_schema_fingerprint_sha256": source_schema_fingerprint_sha256,
        "source_timestamp_semantics": source_timestamp_semantics,
        "receive_timestamp_semantics": receive_timestamp_semantics,
        "event_types": sorted(event_types),
        "known_gap_policy": known_gap_policy,
        "quality_tier": quality_tier,
        "importer_id": importer_id,
        "importer_version": importer_version,
        "license_id": license_id,
        "attribution": attribution,
        "advisory_only": True,
        "no_execution_authority": True,
    }


def compute_external_dataset_id(preimage: dict[str, object]) -> str:
    # Uses the analytical outer canonicalizer (WP163 precedent), not the WP156
    # payload canonicalizer, so a preimage carrying up to the declared 1,024 source
    # objects is committed deterministically rather than rejected by the WP156
    # 256-item sequence limit.
    return EXTERNAL_DATASET_ID_PREFIX + sha256_hex(analytical_canonical_bytes(preimage))


# ── Public builder ───────────────────────────────────────────────────────────


def build_external_dataset_descriptor(
    *,
    provider_id: object,
    dataset_name: object,
    dataset_version: object,
    source_class: object,
    coverage_start: object,
    coverage_end: object,
    source_objects: object,
    source_schema_fingerprint_sha256: object,
    source_timestamp_semantics: object,
    receive_timestamp_semantics: object,
    event_types: object,
    known_gap_policy: object,
    quality_tier: object,
    importer_id: object,
    importer_version: object,
    license_id: object,
    attribution: object,
) -> ExternalDatasetBuildResult:
    """Build a deterministic, provenance-separated external-history descriptor."""

    scalars = (
        provider_id,
        dataset_name,
        dataset_version,
        coverage_start,
        coverage_end,
        source_timestamp_semantics,
        receive_timestamp_semantics,
        known_gap_policy,
        quality_tier,
        importer_id,
        importer_version,
        license_id,
        attribution,
    )
    if not all(_valid_scalar(value) for value in scalars):
        return _rejected("EXTERNAL_DESCRIPTOR_INVALID")
    if source_class not in SOURCE_CLASSES:
        return _rejected("EXTERNAL_DESCRIPTOR_INVALID")

    if not (
        isinstance(source_schema_fingerprint_sha256, str)
        and _SHA256_RE.fullmatch(source_schema_fingerprint_sha256)
    ):
        return _rejected("EXTERNAL_DESCRIPTOR_INVALID")

    start = valid_utc_timestamp(coverage_start)
    end = valid_utc_timestamp(coverage_end)
    if start is None or end is None or start > end:
        return _rejected("EXTERNAL_SOURCE_TIMESTAMP_INVALID")

    if type(event_types) not in (list, tuple):
        return _rejected("EXTERNAL_DESCRIPTOR_INVALID")
    events = tuple(event_types)
    if not (1 <= len(events) <= _MAX_EVENT_TYPES) or not all(
        _valid_scalar(value) for value in events
    ):
        return _rejected("EXTERNAL_SOURCE_EVENT_INVALID")
    if len(set(events)) != len(events):
        return _rejected("EXTERNAL_SOURCE_EVENT_INVALID")

    if type(source_objects) not in (list, tuple):
        return _rejected("EXTERNAL_DESCRIPTOR_INVALID")
    objects = tuple(source_objects)
    if not (1 <= len(objects) <= _MAX_SOURCE_OBJECTS):
        return _rejected("EXTERNAL_SOURCE_FILE_INVALID")
    if not all(_valid_source_object(entry) for entry in objects):
        return _rejected("EXTERNAL_SOURCE_FILE_INVALID")
    names = [entry.object_name for entry in objects]
    if len(set(names)) != len(names):
        return _rejected("EXTERNAL_SOURCE_FILE_INVALID")

    # Canonicalize the stored source objects and event types into the exact
    # deterministic order used for identity, so two calls with reordered inputs
    # return structurally equal descriptors, not merely equal ids.
    canonical_objects = tuple(sorted(objects, key=lambda entry: entry.object_name))
    canonical_events = tuple(sorted(events))

    preimage = _descriptor_identity_preimage(
        provider_id=provider_id,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        source_class=source_class,
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        source_objects=canonical_objects,
        source_schema_fingerprint_sha256=source_schema_fingerprint_sha256,
        source_timestamp_semantics=source_timestamp_semantics,
        receive_timestamp_semantics=receive_timestamp_semantics,
        event_types=canonical_events,
        known_gap_policy=known_gap_policy,
        quality_tier=quality_tier,
        importer_id=importer_id,
        importer_version=importer_version,
        license_id=license_id,
        attribution=attribution,
    )
    try:
        external_dataset_id = compute_external_dataset_id(preimage)
    except Exception:
        # Any unexpected identity-construction failure fails closed as a bounded,
        # non-echoing rejection rather than a raw exception.
        return _rejected("EXTERNAL_DESCRIPTOR_INVALID")

    descriptor = ExternalDatasetDescriptor(
        schema_id=EXTERNAL_DATASET_SCHEMA_ID,
        schema_version=EXTERNAL_DATASET_SCHEMA_VERSION,
        external_dataset_id=external_dataset_id,
        provider_id=provider_id,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        source_class=source_class,
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        source_objects=canonical_objects,
        source_schema_fingerprint_sha256=source_schema_fingerprint_sha256,
        source_timestamp_semantics=source_timestamp_semantics,
        receive_timestamp_semantics=receive_timestamp_semantics,
        event_types=canonical_events,
        known_gap_policy=known_gap_policy,
        quality_tier=quality_tier,
        importer_id=importer_id,
        importer_version=importer_version,
        license_id=license_id,
        attribution=attribution,
        advisory_only=True,
        no_execution_authority=True,
    )
    return ExternalDatasetBuildResult(
        is_valid=True,
        status="EXTERNAL_DESCRIPTOR_BUILT",
        error_codes=(),
        descriptor=descriptor,
        advisory_only=True,
        no_execution_authority=True,
    )
