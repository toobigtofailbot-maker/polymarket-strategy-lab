"""WP175D PMXT v2 -> WP170 experiment-OS bridge (local/offline, fail-closed).

Turns a validated :class:`PmxtV2ResearchLineage` (over explicitly selected existing
WP168 event digests) into a provenance-separated WP170
:class:`ExternalDatasetBinding` and a standard WP170 ``ResearchDatasetManifest``.

Honest provenance only: PMXT external history NEVER becomes a
``DatasetSnapshotReference`` or ``SOURCE_KIND_CANONICAL_PIT`` evidence. Sample
availability is bound to the real ``availability_time_ns`` (PMXT
``timestamp_received`` / existing ``ts_init``), never the source event time. This
module is the PMXT-specific public construction surface; ``experiment_os`` never
imports ``research_runtime``. No network, downloader, credential, scheduler,
strategy, paper, execution, or live authority is present.
"""

from __future__ import annotations

from src.data_layer.analytical_research import (
    EXTERNAL_MEMBER_ID_PREFIX,
    ExperimentControlResult,
    ExternalDatasetBinding,
    build_external_dataset_binding,
)
from src.data_layer.analytical_research.experiment_os import (
    _Failure,
    _rejected,
    _research_dataset_manifest,
    _utc_to_ns,
    _validate_public_record,
)

from .conversion import PmxtV2ResearchLineage

__all__ = [
    "build_pmxt_v2_dataset_binding",
    "build_pmxt_v2_research_dataset_manifest",
]


def _require_valid_lineage(lineage: object) -> PmxtV2ResearchLineage:
    if type(lineage) is not PmxtV2ResearchLineage or not lineage.is_valid:
        raise _Failure("DATASET_REFERENCE_INVALID")
    if (
        lineage.lineage_id is None
        or lineage.membership_digest is None
        or lineage.member_count is None
        or lineage.source_dataset_kind is None
        or lineage.source_external_dataset_id is None
        or lineage.instrument_id is None
        or lineage.conversion_policy_version is None
        or not isinstance(lineage.members, tuple)
        or lineage.member_count != len(lineage.members)
        or not lineage.members
    ):
        raise _Failure("DATASET_REFERENCE_INVALID")
    return lineage


def build_pmxt_v2_dataset_binding(
    lineage: object, code_version: object
) -> ExperimentControlResult:
    """Build a provenance-separated ExternalDatasetBinding from a valid lineage.

    Requires an exact :class:`PmxtV2ResearchLineage` PASS object (never arbitrary
    descriptor metadata alone). Returns the existing ``ExperimentControlResult``.
    """
    try:
        valid = _require_valid_lineage(lineage)
        return build_external_dataset_binding(
            valid.source_dataset_kind,
            valid.source_external_dataset_id,
            valid.lineage_id,
            valid.membership_digest,
            valid.member_count,
            valid.instrument_id,
            valid.conversion_policy_version,
            valid.first_event_time_ns,
            valid.last_event_time_ns,
            valid.first_availability_time_ns,
            valid.last_availability_time_ns,
            code_version,
        )
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")


def build_pmxt_v2_research_dataset_manifest(
    lineage: object,
    dataset_binding: object,
    feature_definitions: object,
    label_definition: object,
    sample_inputs: object,
    group_policy: object,
) -> ExperimentControlResult:
    """Build a standard WP170 ResearchDatasetManifest over external lineage members.

    Every sample ``source_record_version_ids`` must contain only
    ``externalmember:sha256:`` ids from THIS exact lineage; feature availability must
    be at or after the maximum real availability_time_ns of every cited member and
    at or before the decision time (all other WP170 target/label/group/duplicate
    rules are unchanged). Returns the existing ``ExperimentControlResult``.
    """
    try:
        valid = _require_valid_lineage(lineage)
        if type(dataset_binding) is not ExternalDatasetBinding:
            raise _Failure("DATASET_REFERENCE_INVALID")
        _validate_public_record(dataset_binding)
        # The binding must be the authentic binding of exactly this lineage.
        if (
            dataset_binding.source_external_dataset_id != valid.source_external_dataset_id
            or dataset_binding.source_lineage_id != valid.lineage_id
            or dataset_binding.source_membership_digest != valid.membership_digest
            or dataset_binding.source_member_count != valid.member_count
            or dataset_binding.instrument_id != valid.instrument_id
            or dataset_binding.conversion_policy_version != valid.conversion_policy_version
            or dataset_binding.first_event_time_ns != valid.first_event_time_ns
            or dataset_binding.last_event_time_ns != valid.last_event_time_ns
            or dataset_binding.first_availability_time_ns != valid.first_availability_time_ns
            or dataset_binding.last_availability_time_ns != valid.last_availability_time_ns
        ):
            raise _Failure("DATASET_REFERENCE_INVALID")
        # Reject a forged/tampered binding identity by rebuilding from the lineage.
        rebuilt = build_pmxt_v2_dataset_binding(valid, dataset_binding.code_version)
        if not rebuilt.is_valid or rebuilt.record != dataset_binding:
            raise _Failure("DATASET_REFERENCE_INVALID")

        members_by_id = {member.member_id: member for member in valid.members}
        if len(members_by_id) != len(valid.members):
            raise _Failure("DATASET_REFERENCE_INVALID")

        def _validate_source_ids(source_ids: tuple[str, ...]) -> None:
            # Only externalmember:sha256: ids bound to THIS exact lineage.
            for source_id in source_ids:
                if not source_id.startswith(EXTERNAL_MEMBER_ID_PREFIX) or source_id not in members_by_id:
                    raise _Failure("DATASET_REFERENCE_INVALID")

        def _validate_availability(source_ids: tuple[str, ...], feature_time: str) -> None:
            # Exact integer comparison: feature availability cannot precede the real
            # source availability (timestamp_received / ts_init) of any cited member.
            feature_ns = _utc_to_ns(feature_time)
            max_member_availability = max(
                members_by_id[source_id].availability_time_ns for source_id in source_ids
            )
            if feature_ns < max_member_availability:
                raise _Failure("FEATURE_TIMING_LEAKAGE")

        return _research_dataset_manifest(
            dataset_binding_id=dataset_binding.dataset_binding_id,
            validate_source_ids=_validate_source_ids,
            validate_availability=_validate_availability,
            feature_definitions=feature_definitions,
            label_definition=label_definition,
            sample_inputs=sample_inputs,
            group_policy=group_policy,
        )
    except _Failure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")
