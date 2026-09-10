"""WP170 sealed-OOS lifecycle, evidence, and negative-retention tests."""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json

import src.data_layer.analytical_research as ar
from src.data_layer.analytical_research import experiment_os as os_contract
from tests.data_layer.analytical_research.test_experiment_os_preregistration import (
    experiment,
    experiment_stack,
    family,
)
from tests.data_layer.analytical_research.test_experiment_os_identity import feature, label
from tests.data_layer.analytical_research.test_experiment_os_samples_splits import (
    base_samples,
    split,
)


def lifecycle(experiment_record, through: int = 5):
    receipts = []
    for index, action in enumerate(ar.LIFECYCLE_ACTIONS[:through]):
        result = ar.build_lifecycle_receipt(
            experiment_record, receipts, action, f"2026-04-0{index + 1}T00:00:00Z",
            "human:test", (),
        )
        assert result.is_valid, result.error_codes
        receipts.append(result.record)
    return receipts


def evidence_input(split_record, role, *, candidate=True, baseline=True, uncertainty="NONE", created="2026-04-10T00:00:00Z"):
    primary_value = "0.6" if candidate else "0.59"
    return {
        "metric_results": {
            "primary_metric_value": primary_value,
            "secondary_metric_values": {},
        },
        "baseline_results": {
            "baseline_metric_value": "0.5" if baseline else "0.7",
            "membership_hash": ar.membership_hash(split_record, role),
        },
        "baseline_membership_hash": ar.membership_hash(split_record, role),
        "candidate_criterion_met": candidate,
        "baseline_criterion_met": baseline,
        "uncertainty_state": uncertainty,
        "created_at": created,
        "creation_provenance": "human:test",
    }


def _stored_evidence(result):
    return [
        entry.record for entry in result.snapshot.entries
        if isinstance(entry.record, ar.RunEvidenceReceipt)
    ][-1]


def _initialize_with_stack(tmp_path, **plan_overrides):
    path = tmp_path / "registry.sqlite3"
    records = experiment_stack(**plan_overrides)
    assert ar.initialize_experiment_registry(path).is_valid
    appended = ar.append_experiment_records(path, records)
    assert appended.is_valid, appended.error_codes
    return path, records


def _append_lifecycle(path, experiment_record, through=5):
    receipts = lifecycle(experiment_record, through)
    appended = ar.append_experiment_records(path, receipts)
    assert appended.is_valid, appended.error_codes
    return receipts


def test_evidence_waits_for_every_registered_role_label(tmp_path) -> None:
    records = experiment_stack()
    experiment_record = records[-1]
    dataset_manifest, split_record, baseline_record = records[3], records[4], records[7]

    receipts = []
    for index, action in enumerate(ar.LIFECYCLE_ACTIONS[:5]):
        built = ar.build_lifecycle_receipt(
            experiment_record, receipts, action,
            f"2026-01-0{index + 1}T00:00:00Z", "human:test", (),
        )
        assert built.is_valid, built.error_codes
        receipts.append(built.record)

    formation_early = ar.build_run_evidence_receipt(
        experiment_record, dataset_manifest, split_record, baseline_record,
        receipts[:2], (),
        evidence_input(
            split_record, "FORMATION", created="2026-01-11T23:59:59Z",
        ),
    )
    assert formation_early.error_codes == ("LABEL_TIMING_INVALID",)
    formation_ready = ar.build_run_evidence_receipt(
        experiment_record, dataset_manifest, split_record, baseline_record,
        receipts[:2], (),
        evidence_input(
            split_record, "FORMATION", created="2026-01-12T00:00:00Z",
        ),
    )
    assert formation_ready.is_valid

    selection_early = ar.build_run_evidence_receipt(
        experiment_record, dataset_manifest, split_record, baseline_record,
        receipts[:3], (),
        evidence_input(
            split_record, "SELECTION", created="2026-02-11T23:59:59Z",
        ),
    )
    assert selection_early.error_codes == ("LABEL_TIMING_INVALID",)

    path = tmp_path / "registry.sqlite3"
    assert ar.initialize_experiment_registry(path).is_valid
    assert ar.append_experiment_records(path, records + tuple(receipts)).is_valid
    oos_early = ar.record_experiment_evidence(
        path, experiment_record.experiment_id,
        evidence_input(
            split_record, "OUT_OF_SAMPLE", created="2026-03-11T23:59:59Z",
        ),
    )
    assert oos_early.error_codes == ("LABEL_TIMING_INVALID",)
    assert ar.load_and_verify_experiment_registry(path).snapshot.total_rows == (
        len(records) + len(receipts)
    )


def test_public_evidence_rejects_reidentified_non_derivable_split() -> None:
    records = experiment_stack()
    experiment_record = records[-1]
    dataset_manifest, split_record, baseline_record = records[3], records[4], records[7]
    swapped = replace(
        split_record,
        formation_sample_ids=split_record.selection_sample_ids,
        selection_sample_ids=split_record.formation_sample_ids,
    )
    assignment = {
        "formation_sample_ids": list(swapped.formation_sample_ids),
        "selection_sample_ids": list(swapped.selection_sample_ids),
        "oos_sample_ids": list(swapped.oos_sample_ids),
        "purged_sample_ids": list(swapped.purged_sample_ids),
        "embargoed_sample_ids": list(swapped.embargoed_sample_ids),
    }
    swapped = replace(swapped, assignment_hash=os_contract._raw_hash(assignment))
    split_kind, split_prefix, _identity, split_preimage = (
        os_contract._identity_preimage(swapped)
    )
    swapped = replace(
        swapped,
        split_assignment_id=os_contract._digest(
            split_kind, split_prefix, split_preimage,
        ),
    )
    experiment_kind, experiment_prefix, _identity, experiment_preimage = (
        os_contract._identity_preimage(replace(
            experiment_record, split_assignment_id=swapped.split_assignment_id,
        ))
    )
    forged_experiment = replace(
        experiment_record,
        split_assignment_id=swapped.split_assignment_id,
        experiment_id=os_contract._digest(
            experiment_kind, experiment_prefix, experiment_preimage,
        ),
    )
    receipts = lifecycle(forged_experiment, 2)
    rejected = ar.build_run_evidence_receipt(
        forged_experiment, dataset_manifest, swapped, baseline_record, receipts, (),
        evidence_input(swapped, "FORMATION"),
    )
    assert rejected.error_codes == ("SPLIT_INVALID",)

    wrong_plan = replace(
        experiment_record,
        split_plan_id="splitplan:sha256:" + "0" * 64,
    )
    experiment_kind, experiment_prefix, _identity, experiment_preimage = (
        os_contract._identity_preimage(wrong_plan)
    )
    wrong_plan = replace(
        wrong_plan,
        experiment_id=os_contract._digest(
            experiment_kind, experiment_prefix, experiment_preimage,
        ),
    )
    wrong_plan_receipts = lifecycle(wrong_plan, 2)
    assert ar.build_run_evidence_receipt(
        wrong_plan, dataset_manifest, split_record, baseline_record,
        wrong_plan_receipts, (), evidence_input(split_record, "FORMATION"),
    ).error_codes == ("SPLIT_INVALID",)


def test_negative_and_inconclusive_trials_remain_in_family_summary(tmp_path) -> None:
    path, records = _initialize_with_stack(tmp_path)
    first, first_split = records[-1], records[4]
    second, second_split = experiment(trial_number=2, parameters={"window_seconds": 120})
    assert ar.append_experiment_records(path, (second,)).is_valid
    _append_lifecycle(path, first, 2)
    _append_lifecycle(path, second, 2)
    first_result = ar.record_experiment_evidence(
        path, first.experiment_id,
        evidence_input(first_split, "FORMATION", candidate=False),
    )
    second_result = ar.record_experiment_evidence(
        path, second.experiment_id,
        evidence_input(second_split, "FORMATION", uncertainty="INCONCLUSIVE"),
    )
    assert first_result.is_valid and second_result.is_valid
    first_receipts = lifecycle(first, 2)
    selection_started = ar.build_lifecycle_receipt(
        first, first_receipts, "START_SELECTION", "2026-04-10T00:00:00Z",
        "human:test", (),
    )
    assert selection_started.is_valid
    assert ar.append_experiment_records(path, (selection_started.record,)).is_valid
    later_positive = ar.record_experiment_evidence(
        path, first.experiment_id,
        evidence_input(first_split, "SELECTION", created="2026-04-11T00:00:00Z"),
    )
    assert later_positive.is_valid
    family_record = family()
    result = ar.summarize_experiment_family(path, family_record.experiment_family_id)
    assert result.is_valid
    assert result.record.trial_statuses == ("SELECTION_CRITERIA_MET", "EVIDENCE_INCONCLUSIVE")
    assert result.record.evidence_receipt_ids == (
        first_result.inserted_record_ids[0], second_result.inserted_record_ids[0],
        later_positive.inserted_record_ids[0],
    )
    assert result.record.evidence_statuses == (
        "EVIDENCE_NEGATIVE", "EVIDENCE_INCONCLUSIVE", "SELECTION_CRITERIA_MET",
    )
    assert result.record.negative_trial_count == 1
    assert result.record.inconclusive_trial_count == 1


def test_oos_release_requires_irreversible_selection_close() -> None:
    experiment_record, _ = experiment()
    backdated = ar.build_lifecycle_receipt(
        experiment_record, (), "LOCK_PREREGISTRATION", "2025-12-30T00:00:00Z",
        "human:test", (),
    )
    assert backdated.error_codes == ("PREREGISTRATION_STATE_INVALID",)
    locked = lifecycle(experiment_record, 1)
    premature = ar.build_lifecycle_receipt(
        experiment_record, locked, "RELEASE_OOS", "2026-04-02T00:00:00Z", "human:test", (),
    )
    assert premature.error_codes == ("OOS_SEALED_EXPOSURE_VIOLATION",)
    released = lifecycle(experiment_record, 5)
    assert released[-2].to_state == "SELECTION_CLOSED"
    assert released[-1].to_state == "OOS_RELEASED"
    assert not hasattr(released[-1], "oos_exposure_ordinal")
    identical_release = ar.build_lifecycle_receipt(
        experiment_record, released[:-1], "RELEASE_OOS", released[-1].occurred_at,
        "human:test", (),
    )
    assert identical_release.record.lifecycle_receipt_id == released[-1].lifecycle_receipt_id
    assert ar.validate_lifecycle(experiment_record, tuple(reversed(released))).error_codes == (
        "PREREGISTRATION_STATE_INVALID",
    )
    assert ar.build_lifecycle_receipt(
        experiment_record, released, "LOCK_PREREGISTRATION", "2026-04-06T00:00:00Z",
        "human:test", (),
    ).error_codes == ("PREREGISTRATION_STATE_INVALID",)


def test_first_look_oos_is_immutable_and_reuse_is_diagnostic(tmp_path) -> None:
    path, records = _initialize_with_stack(tmp_path)
    experiment_record, split_record = records[-1], records[4]
    receipts = _append_lifecycle(path, experiment_record, 5)
    direct = ar.build_run_evidence_receipt(
        experiment_record, records[3], split_record, records[7], receipts, (),
        evidence_input(split_record, "OUT_OF_SAMPLE"),
    )
    assert direct.error_codes == ("OOS_SEALED_EXPOSURE_VIOLATION",)
    first_result = ar.record_experiment_evidence(
        path, experiment_record.experiment_id,
        evidence_input(split_record, "OUT_OF_SAMPLE"),
    )
    exact_retry = ar.record_experiment_evidence(
        path, experiment_record.experiment_id,
        evidence_input(split_record, "OUT_OF_SAMPLE"),
    )
    assert exact_retry.status == "REGISTRY_APPEND_IDEMPOTENT"
    assert exact_retry.snapshot.total_rows == first_result.snapshot.total_rows
    reused_result = ar.record_experiment_evidence(
        path, experiment_record.experiment_id,
        evidence_input(split_record, "OUT_OF_SAMPLE", created="2026-04-11T00:00:00Z"),
    )
    assert first_result.is_valid and reused_result.is_valid
    first = _stored_evidence(first_result)
    reused = _stored_evidence(reused_result)
    assert first.result_status == "OOS_CRITERIA_MET_UNCOSTED"
    assert first.oos_exposure_ordinal == 1
    assert reused.result_status == "OOS_REUSED_DIAGNOSTIC"
    assert reused.oos_exposure_ordinal == 2
    close = ar.build_lifecycle_receipt(
        experiment_record, receipts, "CLOSE_EXPERIMENT", "2026-04-12T00:00:00Z",
        "human:test", (reused, first),
    )
    assert close.is_valid
    assert close.record.terminal_result_status == "OOS_CRITERIA_MET_UNCOSTED"
    closed = ar.append_experiment_records(path, (close.record,))
    assert closed.is_valid
    retry_after_close = ar.record_experiment_evidence(
        path, experiment_record.experiment_id,
        evidence_input(split_record, "OUT_OF_SAMPLE"),
    )
    assert retry_after_close.status == "REGISTRY_APPEND_IDEMPOTENT"
    assert retry_after_close.snapshot.total_rows == closed.snapshot.total_rows
    after_close = ar.record_experiment_evidence(
        path, experiment_record.experiment_id,
        evidence_input(split_record, "OUT_OF_SAMPLE", created="2026-04-13T00:00:00Z"),
    )
    assert after_close.error_codes == ("OOS_SEALED_EXPOSURE_VIOLATION",)


def test_evidence_requires_exact_role_state_and_chronology(tmp_path) -> None:
    path, records = _initialize_with_stack(tmp_path)
    experiment_record, split_record = records[-1], records[4]
    formation = _append_lifecycle(path, experiment_record, 2)
    backdated = evidence_input(
        split_record, "FORMATION", created="2026-04-01T23:59:59Z",
    )
    assert ar.record_experiment_evidence(
        path, experiment_record.experiment_id, backdated,
    ).error_codes == ("PREREGISTRATION_STATE_INVALID",)
    formation_request = evidence_input(
        split_record, "FORMATION", created="2026-04-02T00:00:00Z",
    )
    assert ar.record_experiment_evidence(
        path, experiment_record.experiment_id, formation_request,
    ).is_valid
    selection = lifecycle(experiment_record, 3)[-1]
    assert ar.append_experiment_records(path, (selection,)).is_valid
    assert ar.record_experiment_evidence(
        path, experiment_record.experiment_id, formation_request,
    ).status == "REGISTRY_APPEND_IDEMPOTENT"
    assert ar.record_experiment_evidence(
        path, experiment_record.experiment_id,
        evidence_input(split_record, "FORMATION", created="2026-04-03T00:00:00Z"),
    ).error_codes == ("PREREGISTRATION_STATE_INVALID",)
    assert ar.record_experiment_evidence(
        path, experiment_record.experiment_id,
        evidence_input(split_record, "SELECTION", created="2026-04-03T00:00:00Z"),
    ).is_valid
    close_selection = lifecycle(experiment_record, 4)[-1]
    assert ar.append_experiment_records(path, (close_selection,)).is_valid
    assert ar.record_experiment_evidence(
        path, experiment_record.experiment_id,
        evidence_input(split_record, "OUT_OF_SAMPLE", created="2026-04-04T00:00:00Z"),
    ).error_codes == ("OOS_SEALED_EXPOSURE_VIOLATION",)


def test_oos_release_without_evidence_contaminates_reused_membership(tmp_path) -> None:
    path, records = _initialize_with_stack(tmp_path)
    first, split_record = records[-1], records[4]
    _append_lifecycle(path, first, 5)
    second, _ = experiment(trial_number=2, parameters={"window_seconds": 120})
    assert ar.append_experiment_records(path, (second,)).is_valid
    _append_lifecycle(path, second, 5)
    result = ar.record_experiment_evidence(
        path, second.experiment_id,
        evidence_input(split_record, "OUT_OF_SAMPLE", created="2026-04-10T00:00:00Z"),
    )
    evidence = _stored_evidence(result)
    assert evidence.oos_exposure_ordinal == 2
    assert evidence.result_status == "OOS_REUSED_DIAGNOSTIC"


def test_oos_source_exposure_survives_feature_split_and_label_variants(tmp_path) -> None:
    path, records = _initialize_with_stack(tmp_path)
    original = records[-1]
    _append_lifecycle(path, original, 5)

    def plan(trial_number, parameter):
        return {
            "trial_number": trial_number,
            "inclusion_exclusion_rules": "Use exact registered membership only.",
            "acceptance_thresholds": {
                "primary_metric_operator": "GTE", "primary_metric_threshold": "0.6",
            },
            "search_space": {"window_seconds": [parameter]},
            "parameters": {"window_seconds": parameter}, "random_seeds": [7],
            "cost_model_reference": None, "stop_failure_rules": "Stop on invalid evidence.",
            "code_version": "commit:test", "creation_provenance": "human:test",
            "preregistered_at": "2025-12-31T00:00:00Z",
        }

    def variant(trial_number, feature_record, label_record, dataset, split_record):
        built = ar.build_preregistered_experiment(
            records[5], records[0], [feature_record], label_record, split_record,
            records[6], [], records[7], records[8], plan(trial_number, 60 + trial_number),
        )
        assert built.is_valid, built.error_codes
        return built.record

    changed_feature = feature(parameters={"window_seconds": 120})
    feature_manifest = ar.build_research_dataset_manifest(
        records[0], [changed_feature], records[2], base_samples(), "EXCLUSIVE",
    ).record
    feature_split = split(feature_manifest).record
    feature_experiment = variant(
        2, changed_feature, records[2], feature_manifest, feature_split,
    )
    assert ar.append_experiment_records(
        path, (changed_feature, feature_manifest, feature_split, feature_experiment),
    ).is_valid
    _append_lifecycle(path, feature_experiment, 5)
    feature_evidence = _stored_evidence(ar.record_experiment_evidence(
        path, feature_experiment.experiment_id,
        evidence_input(feature_split, "OUT_OF_SAMPLE", created="2026-04-11T00:00:00Z"),
    ))
    assert feature_evidence.oos_exposure_ordinal == 2
    assert feature_evidence.result_status == "OOS_REUSED_DIAGNOSTIC"

    boundary_split = split(
        records[3], formation_start="2026-01-02T00:00:00Z",
    ).record
    assert boundary_split.oos_sample_ids == records[4].oos_sample_ids
    assert boundary_split.split_assignment_id != records[4].split_assignment_id
    boundary_experiment = variant(
        3, records[1], records[2], records[3], boundary_split,
    )
    assert ar.append_experiment_records(
        path, (boundary_split, boundary_experiment),
    ).is_valid
    _append_lifecycle(path, boundary_experiment, 5)
    boundary_evidence = _stored_evidence(ar.record_experiment_evidence(
        path, boundary_experiment.experiment_id,
        evidence_input(boundary_split, "OUT_OF_SAMPLE", created="2026-04-12T00:00:00Z"),
    ))
    assert boundary_evidence.oos_exposure_ordinal == 3
    assert boundary_evidence.result_status == "OOS_REUSED_DIAGNOSTIC"

    changed_label = label(label_version="1.0.1")
    label_manifest = ar.build_research_dataset_manifest(
        records[0], [records[1]], changed_label, base_samples(), "EXCLUSIVE",
    ).record
    label_split = split(label_manifest).record
    label_experiment = variant(4, records[1], changed_label, label_manifest, label_split)
    assert ar.append_experiment_records(
        path, (changed_label, label_manifest, label_split, label_experiment),
    ).is_valid
    _append_lifecycle(path, label_experiment, 5)
    label_evidence = _stored_evidence(ar.record_experiment_evidence(
        path, label_experiment.experiment_id,
        evidence_input(label_split, "OUT_OF_SAMPLE", created="2026-04-13T00:00:00Z"),
    ))
    assert label_evidence.oos_exposure_ordinal == 4
    assert label_evidence.result_status == "OOS_REUSED_DIAGNOSTIC"


def test_prior_tuning_evidence_contaminates_rotated_oos_sources(tmp_path) -> None:
    path, records = _initialize_with_stack(tmp_path)
    original, original_split = records[-1], records[4]
    formation_receipts = _append_lifecycle(path, original, 2)
    formation_result = ar.record_experiment_evidence(
        path, original.experiment_id,
        evidence_input(original_split, "FORMATION", created="2026-04-02T00:00:00Z"),
    )
    assert formation_result.is_valid

    rotated_samples = base_samples()
    first_sources = rotated_samples[0]["source_record_version_ids"]
    rotated_samples[0] = dict(
        rotated_samples[0],
        source_record_version_ids=rotated_samples[2]["source_record_version_ids"],
    )
    rotated_samples[2] = dict(
        rotated_samples[2], source_record_version_ids=first_sources,
    )
    rotated_manifest = ar.build_research_dataset_manifest(
        records[0], [records[1]], records[2], rotated_samples, "EXCLUSIVE",
    ).record
    rotated_split = split(rotated_manifest).record
    plan = {
        "trial_number": 2,
        "inclusion_exclusion_rules": "Use exact registered membership only.",
        "acceptance_thresholds": {
            "primary_metric_operator": "GTE", "primary_metric_threshold": "0.6",
        },
        "search_space": {"window_seconds": [62]},
        "parameters": {"window_seconds": 62}, "random_seeds": [7],
        "cost_model_reference": None, "stop_failure_rules": "Stop on invalid evidence.",
        "code_version": "commit:test", "creation_provenance": "human:test",
        "preregistered_at": "2025-12-31T00:00:00Z",
    }
    rotated_experiment = ar.build_preregistered_experiment(
        records[5], records[0], [records[1]], records[2], rotated_split,
        records[6], [], records[7], records[8], plan,
    ).record
    assert ar.append_experiment_records(
        path, (rotated_manifest, rotated_split, rotated_experiment),
    ).is_valid
    _append_lifecycle(path, rotated_experiment, 5)
    result = ar.record_experiment_evidence(
        path, rotated_experiment.experiment_id,
        evidence_input(rotated_split, "OUT_OF_SAMPLE", created="2026-04-10T00:00:00Z"),
    )
    evidence = _stored_evidence(result)
    assert evidence.oos_exposure_ordinal == 2
    assert evidence.result_status == "OOS_REUSED_DIAGNOSTIC"


def test_post_oos_plan_change_creates_new_experiment_not_rewrite(tmp_path) -> None:
    path, records = _initialize_with_stack(tmp_path)
    original, split_record = records[-1], records[4]
    _append_lifecycle(path, original, 5)
    first_result = ar.record_experiment_evidence(
        path, original.experiment_id, evidence_input(split_record, "OUT_OF_SAMPLE"),
    )
    first = _stored_evidence(first_result)
    variant, _ = experiment(parameters={"window_seconds": 121}, trial_number=2)
    assert variant.experiment_id != original.experiment_id
    assert variant.experiment_family_id == original.experiment_family_id
    assert first.experiment_id == original.experiment_id
    assert first.experiment_id != variant.experiment_id
    assert ar.append_experiment_records(path, (variant,)).is_valid
    _append_lifecycle(path, variant, 5)
    variant_result = ar.record_experiment_evidence(
        path, variant.experiment_id,
        evidence_input(split_record, "OUT_OF_SAMPLE", created="2026-04-11T00:00:00Z"),
    )
    variant_evidence = _stored_evidence(variant_result)
    assert variant_evidence.oos_exposure_ordinal == 2
    assert variant_evidence.result_status == "OOS_REUSED_DIAGNOSTIC"
    assert _stored_evidence(ar.load_and_verify_experiment_registry(path)) != first


def test_run_receipt_identity_recomputes_from_all_committed_inputs(tmp_path) -> None:
    path, records = _initialize_with_stack(tmp_path)
    experiment_record, split_record = records[-1], records[4]
    _append_lifecycle(path, experiment_record, 5)
    receipt = _stored_evidence(ar.record_experiment_evidence(
        path, experiment_record.experiment_id,
        evidence_input(split_record, "OUT_OF_SAMPLE"),
    ))
    preimage = asdict(receipt)
    identity = preimage.pop("run_evidence_receipt_id")
    preimage.pop("advisory_only")
    preimage.pop("no_execution_authority")
    raw = json.dumps(
        {"run_evidence_receipt.identity_preimage": preimage}, ensure_ascii=False,
        separators=(",", ":"), sort_keys=True, allow_nan=False,
    ).encode("utf-8")
    assert identity == "runevidence:sha256:" + hashlib.sha256(raw).hexdigest()
    assert receipt.membership_hash == ar.membership_hash(split_record, "OUT_OF_SAMPLE")
    assert receipt.code_version == experiment_record.code_version
    assert receipt.parameters_json == experiment_record.parameters_json
