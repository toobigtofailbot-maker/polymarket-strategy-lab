"""WP170 falsifiable hypothesis, baseline, family, and preregistration tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import src.data_layer.analytical_research as ar
from tests.data_layer.analytical_research.test_experiment_os_identity import binding, feature, label
from tests.data_layer.analytical_research.test_experiment_os_samples_splits import manifest, split


def hypothesis(**overrides):
    value = {
        "hypothesis_name": "past_spread_predicts_resolution",
        "hypothesis_version": "1.0.0",
        "predecessor_candidate_ids": ["candidate:001"],
        "falsifiable_claim": "Past-only spread change exceeds the baseline criterion.",
        "proposed_mechanism": "Information diffusion appears in public quotes before resolution.",
        "cohort": "binary markets",
        "horizon": "one day",
        "target": "binary resolution",
        "falsification_condition": "Candidate fails the preregistered baseline rule.",
        "human_review_state": "REVIEWED",
        "review_assertion": "Human reviewed for research only.",
        "code_version": "commit:test",
        "creation_provenance": "human:test",
    }
    value.update(overrides)
    result = ar.build_alpha_hypothesis(value)
    assert result.is_valid, result.error_codes
    return result.record


def metric(**overrides):
    value = {
        "metric_name": "accuracy",
        "metric_version": "1.0.0",
        "direction": "HIGHER_IS_BETTER",
        "parameters": {"scale": "unit"},
        "code_version": "commit:test",
    }
    value.update(overrides)
    result = ar.build_metric_definition(value)
    assert result.is_valid, result.error_codes
    return result.record


def baseline(**overrides):
    value = {
        "baseline_name": "constant_prior",
        "baseline_version": "1.0.0",
        "method_rule": "Use the formation-set constant prior.",
        "parameters": {"prior": "formation_only"},
        "same_partition_required": True,
        "acceptance_rule": "CANDIDATE_GTE_BASELINE",
        "code_version": "commit:test",
    }
    value.update(overrides)
    result = ar.build_baseline_definition(value)
    assert result.is_valid, result.error_codes
    return result.record


def family(**overrides):
    value = {
        "research_program": "spread-resolution-program",
        "cohort": "binary markets",
        "target": "binary resolution",
        "metric_family": "classification",
        "correction_policy": "FAMILY_TRIAL_COUNT",
        "predecessor_family_id": None,
    }
    value.update(overrides)
    result = ar.build_experiment_family(value)
    assert result.is_valid, result.error_codes
    return result.record


def experiment_stack(**plan_overrides):
    data_binding = binding()
    features = [feature()]
    label_def = label()
    dataset = ar.build_research_dataset_manifest(
        data_binding, features, label_def,
        __import__("tests.data_layer.analytical_research.test_experiment_os_samples_splits", fromlist=["base_samples"]).base_samples(),
        "EXCLUSIVE",
    ).record
    split_result = split(dataset)
    plan = {
        "trial_number": 1,
        "inclusion_exclusion_rules": "Use exact registered membership only.",
        "acceptance_thresholds": {
            "primary_metric_operator": "GTE",
            "primary_metric_threshold": "0.6",
        },
        "search_space": {"window_seconds": [60]},
        "parameters": {"window_seconds": 60},
        "random_seeds": [7],
        "cost_model_reference": None,
        "stop_failure_rules": "Stop on invalid evidence.",
        "code_version": "commit:test",
        "creation_provenance": "human:test",
        "preregistered_at": "2025-12-31T00:00:00Z",
    }
    plan.update(plan_overrides)
    hypothesis_record = hypothesis()
    metric_record = metric()
    baseline_record = baseline()
    family_record = family()
    result = ar.build_preregistered_experiment(
        hypothesis_record, data_binding, features, label_def, split_result.record,
        metric_record, [], baseline_record, family_record, plan,
    )
    assert result.is_valid, result.error_codes
    return (
        data_binding, features[0], label_def, dataset, split_result.record,
        hypothesis_record, metric_record, baseline_record, family_record, result.record,
    )


def experiment(**plan_overrides):
    records = experiment_stack(**plan_overrides)
    return records[-1], records[4]


def test_hypothesis_is_stable_human_reviewed_and_non_authoritative() -> None:
    first = hypothesis()
    second = hypothesis()
    changed = hypothesis(falsifiable_claim="A different falsifiable claim.")
    assert first.hypothesis_id == second.hypothesis_id
    assert first.hypothesis_id != changed.hypothesis_id
    assert first.human_review_state == "REVIEWED"
    assert first.advisory_only and first.no_execution_authority
    rejected = ar.build_alpha_hypothesis({})
    assert rejected.error_codes == ("FIELD_MISSING",)


def test_preregistration_locks_every_required_field_and_is_immutable() -> None:
    original, _ = experiment()
    identical, _ = experiment()
    threshold_changed, _ = experiment(acceptance_thresholds={
        "primary_metric_operator": "GTE", "primary_metric_threshold": "0.7",
    })
    seed_changed, _ = experiment(random_seeds=[8])
    records = experiment_stack()
    data_binding, feature_record, label_record, dataset, split_record = records[:5]
    hypothesis_record, metric_record, baseline_record, family_record = records[5:9]
    changed_feature = feature(parameters={"window_seconds": 120})
    feature_dataset = ar.build_research_dataset_manifest(
        data_binding, [changed_feature], label_record,
        __import__("tests.data_layer.analytical_research.test_experiment_os_samples_splits", fromlist=["base_samples"]).base_samples(),
        "EXCLUSIVE",
    ).record
    feature_split = split(feature_dataset).record
    changed_label = label(label_version="1.0.1")
    label_dataset = ar.build_research_dataset_manifest(
        data_binding, [feature_record], changed_label,
        __import__("tests.data_layer.analytical_research.test_experiment_os_samples_splits", fromlist=["base_samples"]).base_samples(),
        "EXCLUSIVE",
    ).record
    label_split = split(label_dataset).record
    changed_split = split(dataset, embargo_seconds=1).record
    changed_baseline = baseline(baseline_version="1.0.1")
    plan = {
        "trial_number": 1,
        "inclusion_exclusion_rules": "Use exact registered membership only.",
        "acceptance_thresholds": {
            "primary_metric_operator": "GTE", "primary_metric_threshold": "0.6",
        },
        "search_space": {"window_seconds": [60]},
        "parameters": {"window_seconds": 60},
        "random_seeds": [7], "cost_model_reference": None,
        "stop_failure_rules": "Stop on invalid evidence.", "code_version": "commit:test",
        "creation_provenance": "human:test", "preregistered_at": "2025-12-31T00:00:00Z",
    }

    def build_variant(features, label_def, split_manifest, baseline_def):
        result = ar.build_preregistered_experiment(
            hypothesis_record, data_binding, features, label_def, split_manifest,
            metric_record, [], baseline_def, family_record, plan,
        )
        assert result.is_valid, result.error_codes
        return result.record

    variants = (
        threshold_changed, seed_changed,
        build_variant([changed_feature], label_record, feature_split, baseline_record),
        build_variant([feature_record], changed_label, label_split, baseline_record),
        build_variant([feature_record], label_record, changed_split, baseline_record),
        build_variant([feature_record], label_record, split_record, changed_baseline),
    )
    assert identical.experiment_id == original.experiment_id
    assert len({original.experiment_id, *(item.experiment_id for item in variants)}) == 7
    omitted_null = dict(plan)
    omitted_null.pop("cost_model_reference")
    assert ar.build_preregistered_experiment(
        hypothesis_record, data_binding, [feature_record], label_record, split_record,
        metric_record, [], baseline_record, family_record, omitted_null,
    ).error_codes == ("FIELD_MISSING",)
    assert original.parameters_json == '{"window_seconds":60}'
    assert original.random_seeds == (7,)
    with pytest.raises(FrozenInstanceError):
        original.trial_number = 2  # type: ignore[misc]


def test_baseline_identity_and_same_partition_rule_are_enforced() -> None:
    original = baseline()
    changed = baseline(acceptance_rule="CANDIDATE_LTE_BASELINE")
    assert original.baseline_definition_id != changed.baseline_definition_id
    rejected = ar.build_baseline_definition({
        "baseline_name": "bad", "baseline_version": "1", "method_rule": "bad",
        "parameters": {}, "same_partition_required": False,
        "acceptance_rule": "UNSUPPORTED", "code_version": "v",
    })
    assert rejected.error_codes == ("FIELD_VALUE_INVALID",)
    stack_records = experiment_stack()
    experiment_record = stack_records[-1]
    dataset_manifest = stack_records[3]
    split_record = stack_records[4]
    assert ar.membership_hash(split_record, "FORMATION") != ar.membership_hash(split_record, "SELECTION")
    assert experiment_record.baseline_id == original.baseline_definition_id
    from tests.data_layer.analytical_research.test_experiment_os_lifecycle_evidence import (
        evidence_input,
        lifecycle,
    )
    formation = lifecycle(experiment_record, 2)
    assert ar.build_run_evidence_receipt(
        experiment_record, manifest(policy="DECLARED_NO_ISOLATION"), split_record,
        original, formation, (), evidence_input(split_record, "FORMATION"),
    ).error_codes == ("SPLIT_INVALID",)
    failed_baseline = ar.build_run_evidence_receipt(
        experiment_record, dataset_manifest, split_record, original, formation, (),
        evidence_input(split_record, "FORMATION", baseline=False),
    )
    assert failed_baseline.is_valid
    assert failed_baseline.record.candidate_criterion_met is True
    assert failed_baseline.record.baseline_criterion_met is False
    assert failed_baseline.record.result_status == "EVIDENCE_NEGATIVE"
    mismatched = evidence_input(split_record, "FORMATION")
    mismatched["baseline_results"]["membership_hash"] = ar.membership_hash(
        split_record, "SELECTION",
    )
    assert ar.build_run_evidence_receipt(
        experiment_record, dataset_manifest, split_record, original, formation, (), mismatched,
    ).error_codes == ("FIELD_VALUE_INVALID",)

    forged = evidence_input(split_record, "FORMATION", baseline=True)
    forged["baseline_criterion_met"] = False
    assert ar.build_run_evidence_receipt(
        experiment_record, dataset_manifest, split_record, original, formation, (), forged,
    ).error_codes == ("FIELD_VALUE_INVALID",)
    boundary = evidence_input(split_record, "FORMATION", baseline=True)
    boundary["baseline_results"]["baseline_metric_value"] = "0.6"
    exact = ar.build_run_evidence_receipt(
        experiment_record, dataset_manifest, split_record, original, formation, (), boundary,
    )
    assert exact.is_valid and exact.record.baseline_criterion_met is True


def test_family_trial_ledger_cannot_silently_reset(tmp_path) -> None:
    family_record = family()
    same = family()
    other_policy = family(correction_policy="SINGLETON")
    first, _ = experiment(trial_number=1)
    second, _ = experiment(trial_number=2, parameters={"window_seconds": 120})
    assert family_record.experiment_family_id == same.experiment_family_id
    assert family_record.experiment_family_id != other_policy.experiment_family_id
    assert first.experiment_family_id == second.experiment_family_id
    assert first.experiment_id != second.experiment_id
    assert (first.trial_number, second.trial_number) == (1, 2)
    path = tmp_path / "registry.sqlite3"
    records = experiment_stack()
    assert ar.initialize_experiment_registry(path).is_valid
    assert ar.append_experiment_records(path, records).is_valid
    assert ar.append_experiment_records(path, (second,)).is_valid
    reset = experiment(trial_number=1, parameters={"window_seconds": 999})[0]
    assert ar.append_experiment_records(path, (reset,)).error_codes == ("TRIAL_FAMILY_CONFLICT",)
    renamed_without_predecessor = family(research_program="renamed-program")
    assert ar.append_experiment_records(
        path, (renamed_without_predecessor,),
    ).error_codes == ("TRIAL_FAMILY_CONFLICT",)
    metric_alias_without_predecessor = family(
        research_program="renamed-program", metric_family="classification-v2",
    )
    assert ar.append_experiment_records(
        path, (metric_alias_without_predecessor,),
    ).error_codes == ("TRIAL_FAMILY_CONFLICT",)
    for alias in (
        {"cohort": "Binary Markets"},
        {"cohort": "binary-markets"},
        {"cohort": "binary market"},
        {"cohort": "binary prediction markets"},
        {"target": "Binary-Resolutions"},
    ):
        assert ar.append_experiment_records(
            path, (family(**alias),),
        ).error_codes == ("TRIAL_FAMILY_CONFLICT",)
    chained = family(
        research_program="renamed-program",
        metric_family="classification-v2",
        predecessor_family_id=family_record.experiment_family_id,
    )
    plan = {
        "trial_number": 3,
        "inclusion_exclusion_rules": "Use exact registered membership only.",
        "acceptance_thresholds": {
            "primary_metric_operator": "GTE", "primary_metric_threshold": "0.6",
        },
        "search_space": {"window_seconds": [180]}, "parameters": {"window_seconds": 180},
        "random_seeds": [7], "cost_model_reference": None,
        "stop_failure_rules": "Stop on invalid evidence.", "code_version": "commit:test",
        "creation_provenance": "human:test", "preregistered_at": "2025-12-31T00:00:00Z",
    }
    chained_experiment = ar.build_preregistered_experiment(
        records[5], records[0], [records[1]], records[2], records[4], records[6],
        [], records[7], chained, plan,
    ).record
    assert ar.append_experiment_records(path, (chained_experiment, chained)).is_valid
    summary = ar.summarize_experiment_family(path, chained.experiment_family_id)
    assert summary.record.trial_numbers == (1, 2, 3)
    singleton_family = family(correction_policy="SINGLETON", metric_family="singleton-classification")
    singleton_two = ar.build_preregistered_experiment(
        records[5], records[0], [records[1]], records[2], records[4], records[6],
        [], records[7], singleton_family, dict(plan, trial_number=2),
    ).record
    singleton_path = tmp_path / "singleton.sqlite3"
    assert ar.initialize_experiment_registry(singleton_path).is_valid
    assert ar.append_experiment_records(
        singleton_path, records[:8] + (singleton_family, singleton_two),
    ).error_codes == ("TRIAL_FAMILY_CONFLICT",)
