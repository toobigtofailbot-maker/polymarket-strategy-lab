"""WP170 sample lineage and leakage-safe temporal split tests."""

from __future__ import annotations

import src.data_layer.analytical_research as ar
from tests.data_layer.analytical_research.test_experiment_os_identity import (
    binding,
    feature,
    label,
    source_record_id,
)


def sample(
    suffix: str, decision: str, target: str, available: str, *,
    feature_time: str | None = None, group: str | None = None,
):
    return {
        "source_record_version_ids": [source_record_id(suffix)],
        "market_id": f"market:{suffix}",
        "related_group_id": f"event:{suffix}",
        "leakage_group_id": group,
        "decision_time": decision,
        "feature_availability_time": feature_time or decision,
        "target_time": target,
        "label_availability_time": available,
    }


def base_samples(*, exclusive: bool = True):
    groups = ("group:a", "group:b", "group:c") if exclusive else (None, None, None)
    return [
        sample("a1", "2026-01-10T00:00:00Z", "2026-01-11T00:00:00Z", "2026-01-12T00:00:00Z", group=groups[0]),
        sample("b2", "2026-02-10T00:00:00Z", "2026-02-11T00:00:00Z", "2026-02-12T00:00:00Z", group=groups[1]),
        sample("c3", "2026-03-10T00:00:00Z", "2026-03-11T00:00:00Z", "2026-03-12T00:00:00Z", group=groups[2]),
    ]


def manifest(samples=None, *, policy="EXCLUSIVE"):
    result = ar.build_research_dataset_manifest(
        binding(), [feature()], label(), samples or base_samples(exclusive=policy == "EXCLUSIVE"), policy
    )
    assert result.is_valid, result.error_codes
    return result.record


def split(dataset=None, **overrides):
    policy = {
        "split_plan_version": "1.0.0",
        "formation_start": "2026-01-01T00:00:00Z",
        "selection_start": "2026-02-01T00:00:00Z",
        "oos_start": "2026-03-01T00:00:00Z",
        "end_time": "2026-04-01T00:00:00Z",
        "purge_rule": "PURGE_LABEL_AVAILABILITY_AT_OR_AFTER_NEXT_BOUNDARY",
        "embargo_seconds": 0,
        "group_policy": "EXCLUSIVE",
        "inclusion_policy": "DECISION_TIME_HALF_OPEN",
        "min_samples_per_role": 1,
    }
    policy.update(overrides)
    return ar.build_temporal_split_manifest(dataset or manifest(), policy)


def test_sample_manifest_identity_lineage_and_reorder_determinism() -> None:
    samples = base_samples()
    first = manifest(samples)
    second = manifest(list(reversed(samples)))
    assert first.research_dataset_manifest_id == second.research_dataset_manifest_id
    assert tuple(item.sample_id for item in first.samples) == tuple(sorted(item.sample_id for item in first.samples))
    assert all(item.dataset_binding_id == first.dataset_binding_id for item in first.samples)
    duplicate = manifest(samples + [dict(samples[0])])
    assert duplicate.research_dataset_manifest_id == first.research_dataset_manifest_id
    conflict = dict(samples[0])
    conflict["market_id"] = "market:changed"
    rejected = ar.build_research_dataset_manifest(binding(), [feature()], label(), samples + [conflict], "EXCLUSIVE")
    assert rejected.error_codes == ("DATASET_REFERENCE_INVALID",)
    unknown = dict(samples[0], source_record_version_ids=[source_record_id("unknown")])
    assert ar.build_research_dataset_manifest(
        binding(), [feature()], label(), [unknown], "EXCLUSIVE"
    ).error_codes == ("DATASET_REFERENCE_INVALID",)
    assert first.samples[0].source_membership_digest != first.samples[0].lineage_digest


def test_feature_availability_after_decision_is_rejected() -> None:
    samples = base_samples()
    samples[0] = sample(
        "a1", "2026-01-10T00:00:00Z", "2026-01-11T00:00:00Z",
        "2026-01-12T00:00:00Z", feature_time="2026-01-10T00:00:01Z", group="group:a",
    )
    result = ar.build_research_dataset_manifest(binding(), [feature()], label(), samples, "EXCLUSIVE")
    assert result.error_codes == ("FEATURE_TIMING_LEAKAGE",)
    assert result.record is None
    noncanonical = dict(base_samples()[0], decision_time="2026-01-10T00:00:00+00:00")
    assert ar.build_research_dataset_manifest(
        binding(), [feature()], label(), [noncanonical], "EXCLUSIVE"
    ).error_codes == ("FIELD_VALUE_INVALID",)


def test_temporal_three_role_assignment_is_deterministic_and_disjoint() -> None:
    first = split()
    second = split(manifest(list(reversed(base_samples()))))
    assert first.is_valid and second.is_valid
    assert first.record.split_assignment_id == second.record.split_assignment_id
    roles = [set(first.record.formation_sample_ids), set(first.record.selection_sample_ids), set(first.record.oos_sample_ids)]
    assert all(roles[i].isdisjoint(roles[j]) for i in range(3) for j in range(i + 1, 3))
    assert all(len(role) == 1 for role in roles)
    boundary_samples = [
        sample("a1", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", "2026-01-03T00:00:00Z", group="group:a"),
        sample("b2", "2026-02-01T00:00:00Z", "2026-02-02T00:00:00Z", "2026-02-03T00:00:00Z", group="group:b"),
        sample("c3", "2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z", "2026-03-03T00:00:00Z", group="group:c"),
        sample("d4", "2026-04-01T00:00:00Z", "2026-04-02T00:00:00Z", "2026-04-03T00:00:00Z", group="group:d"),
    ]
    exact = split(manifest(boundary_samples))
    by_market = {item.market_id: item.sample_id for item in manifest(boundary_samples).samples}
    assert exact.is_valid
    assert by_market["market:a1"] in exact.record.formation_sample_ids
    assert by_market["market:b2"] in exact.record.selection_sample_ids
    assert by_market["market:c3"] in exact.record.oos_sample_ids
    assert by_market["market:d4"] not in {
        *exact.record.formation_sample_ids,
        *exact.record.selection_sample_ids,
        *exact.record.oos_sample_ids,
    }
    assert split(end_time="2026-03-10T00:00:00Z").error_codes == ("SPLIT_INVALID",)
    assert ar.build_temporal_split_manifest(manifest(), {}).error_codes == ("FIELD_MISSING",)


def test_overlapping_information_window_is_purged() -> None:
    samples = base_samples()
    overlap = sample(
        "d4", "2026-01-31T00:00:00Z", "2026-02-01T00:00:00Z",
        "2026-02-02T00:00:00Z", group="group:d",
    )
    dataset = manifest(samples + [overlap])
    result = split(dataset)
    overlap_id = next(item.sample_id for item in dataset.samples if item.market_id == "market:d4")
    assert result.is_valid
    assert overlap_id in result.record.purged_sample_ids
    assert overlap_id not in result.record.formation_sample_ids


def test_configured_embargo_excludes_boundary_samples() -> None:
    samples = base_samples()
    boundary = sample(
        "d4", "2026-02-01T00:00:00Z", "2026-02-01T01:00:00Z",
        "2026-02-01T02:00:00Z", group="group:d",
    )
    buffer_end = sample(
        "e5", "2026-02-02T00:00:00Z", "2026-02-02T01:00:00Z",
        "2026-02-02T02:00:00Z", group="group:e",
    )
    dataset = manifest(samples + [boundary, buffer_end])
    result = split(dataset, embargo_seconds=86400)
    ids = {item.market_id: item.sample_id for item in dataset.samples}
    assert result.is_valid
    assert ids["market:d4"] in result.record.embargoed_sample_ids
    assert ids["market:e5"] in result.record.selection_sample_ids


def test_group_policy_is_explicit_and_cross_role_groups_reject() -> None:
    samples = base_samples()
    samples[1] = dict(samples[1], leakage_group_id="group:a")
    rejected_manifest = manifest(samples)
    rejected = split(rejected_manifest)
    assert rejected.error_codes == ("GROUP_LEAKAGE_VIOLATION",)
    for key in ("market_id", "related_group_id"):
        collision = base_samples()
        collision[1] = dict(collision[1], **{key: collision[0][key]})
        assert split(manifest(collision)).error_codes == ("GROUP_LEAKAGE_VIOLATION",)
    no_isolation = manifest(base_samples(exclusive=False), policy="DECLARED_NO_ISOLATION")
    accepted = split(no_isolation, group_policy="DECLARED_NO_ISOLATION")
    assert accepted.is_valid
    missing = dict(base_samples()[0])
    missing.pop("leakage_group_id")
    result = ar.build_research_dataset_manifest(binding(), [feature()], label(), [missing], "EXCLUSIVE")
    assert result.error_codes == ("FIELD_MISSING",)
    assert ar.build_research_dataset_manifest(
        binding(), [feature()], label(), base_samples(), None,
    ).error_codes == ("FIELD_TYPE_INVALID",)


def test_source_record_membership_cannot_cross_temporal_roles() -> None:
    for policy in ("EXCLUSIVE", "DECLARED_NO_ISOLATION"):
        samples = base_samples(exclusive=policy == "EXCLUSIVE")
        samples[0] = dict(
            samples[0],
            source_record_version_ids=[source_record_id("a1"), source_record_id("c3")],
        )
        dataset = manifest(samples, policy=policy)
        result = split(dataset, group_policy=policy)
        assert result.error_codes == ("SPLIT_INVALID",)
