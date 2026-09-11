"""WP170 public API, no-echo, negative-matrix, and authority boundaries."""

from __future__ import annotations

import ast
from dataclasses import asdict, fields, is_dataclass
import inspect
import json
from pathlib import Path
import subprocess

import src.data_layer.analytical_research as ar
from src.data_layer.analytical_research import experiment_registry as registry
from tests.data_layer.analytical_research.test_experiment_os_identity import feature

ROOT = Path(__file__).resolve().parents[3]
SOURCE_FILES = (
    ROOT / "src/data_layer/analytical_research/experiment_os.py",
    ROOT / "src/data_layer/analytical_research/experiment_registry.py",
)


def _strings(value):
    if is_dataclass(value) and not isinstance(value, type):
        return _strings(asdict(value))
    if isinstance(value, dict):
        return [item for key, val in value.items() for item in (_strings(key) + _strings(val))]
    if isinstance(value, (list, tuple)):
        return [item for val in value for item in _strings(val)]
    return [value] if isinstance(value, str) else []


def test_invalid_results_never_echo_payload_path_exception_or_secret(tmp_path, monkeypatch) -> None:
    sentinels = (
        "C:\\Users\\private\\wallet.txt",
        "sk_live_NEVER_ECHO_THIS",
        "SELECT secret FROM credentials",
        "Traceback: hostile failure",
    )
    results = []
    for sentinel in sentinels:
        results.append(ar.build_feature_definition({"feature_name": sentinel}))
        results.append(ar.initialize_experiment_registry(sentinel))
        results.append(ar.build_feature_definition({
            "feature_name": "invalid", "feature_version": "1", "description": sentinel,
            "source_dependencies": ["market_observation.best_bid"],
            "parameters": {"opaque": sentinel}, "lookback_rule": "INVALID",
            "availability_rule": "SOURCE_AVAILABILITY_TIME",
            "missing_data_policy": "REJECT", "transformation_version": "v",
            "no_future_information_rule": "FEATURE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME",
        }))
        results.append(ar.build_label_definition({
            "label_name": "invalid", "label_version": "1",
            "prediction_target": sentinel, "horizon_rule": "h",
            "target_time_rule": "t", "outcome_source_rule": "o",
            "availability_time_rule": "a", "censoring_rule": "c",
            "parameters": {"invalid": object()}, "code_version": "v",
        }))

    class ExplodingMapping(dict):
        def keys(self):
            raise RuntimeError(sentinels[-1])

    results.append(ar.build_feature_definition(ExplodingMapping()))
    registry_path = tmp_path / "registry.sqlite3"
    assert ar.initialize_experiment_registry(registry_path).is_valid
    monkeypatch.setattr(registry, "_connect", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError(sentinels[-1])))
    results.append(ar.load_and_verify_experiment_registry(registry_path))
    for result in results:
        public = json.dumps(asdict(result), sort_keys=True)
        assert result.is_valid is False
        assert getattr(result, "record", None) is None
        assert getattr(result, "snapshot", None) is None
        assert not any(sentinel in public for sentinel in sentinels)
        assert not any(sentinel in _strings(result) for sentinel in sentinels)
        assert "Traceback" not in public and "Exception" not in public


def test_public_api_signatures_fields_and_frozen_contract_are_exact() -> None:
    expected_signatures = {
        "build_dataset_binding": ("reference", "analytical_manifest", "code_version"),
        "build_feature_definition": ("input_mapping",),
        "build_label_definition": ("input_mapping",),
        "build_research_dataset_manifest": ("dataset_binding", "feature_definitions", "label_definition", "sample_inputs", "group_policy"),
        "build_temporal_split_manifest": ("dataset_manifest", "split_policy"),
        "build_alpha_hypothesis": ("input_mapping",),
        "build_metric_definition": ("input_mapping",),
        "build_baseline_definition": ("input_mapping",),
        "build_experiment_family": ("input_mapping",),
        "build_preregistered_experiment": ("hypothesis", "dataset_binding", "feature_definitions", "label_definition", "split_manifest", "primary_metric", "secondary_metrics", "baseline", "family", "plan"),
        "build_lifecycle_receipt": ("experiment", "prior_receipts", "action", "occurred_at", "provenance", "evidence_receipts"),
        "validate_lifecycle": ("experiment", "receipts"),
        "build_run_evidence_receipt": ("experiment", "dataset_manifest", "split_manifest", "baseline_definition", "lifecycle_receipts", "prior_evidence", "input_mapping"),
        "initialize_experiment_registry": ("path",),
        "append_experiment_records": ("path", "records"),
        "record_experiment_evidence": ("path", "experiment_id", "input_mapping"),
        "load_and_verify_experiment_registry": ("path",),
        "summarize_experiment_family": ("path", "family_id"),
    }
    for name, parameters in expected_signatures.items():
        assert tuple(inspect.signature(getattr(ar, name)).parameters) == parameters
    assert set(expected_signatures).issubset(ar.__all__)
    expected_fields = {
        ar.DatasetBinding: ("schema_id", "schema_version", "dataset_binding_id", "dataset_snapshot_reference_id", "dataset_snapshot_reference_json", "dataset_reference_schema_version", "analytical_logical_dataset_id", "analytical_identity_json", "analytical_schema_version", "materializer_version", "source_reference_id", "code_version", "advisory_only", "no_execution_authority"),
        ar.FeatureDefinition: ("schema_id", "schema_version", "feature_definition_id", "feature_name", "feature_version", "description", "source_dependencies", "parameters_json", "lookback_rule", "availability_rule", "missing_data_policy", "transformation_version", "no_future_information_rule", "advisory_only", "no_execution_authority"),
        ar.LabelDefinition: ("schema_id", "schema_version", "label_definition_id", "label_name", "label_version", "prediction_target", "horizon_rule", "target_time_rule", "outcome_source_rule", "availability_time_rule", "censoring_rule", "parameters_json", "code_version", "advisory_only", "no_execution_authority"),
        ar.ResearchSample: ("schema_id", "schema_version", "sample_id", "dataset_binding_id", "source_record_version_ids", "source_membership_digest", "market_id", "related_group_id", "leakage_group_id", "decision_time", "feature_availability_time", "target_time", "label_availability_time", "feature_set_id", "label_definition_id", "lineage_digest", "advisory_only", "no_execution_authority"),
        ar.ResearchDatasetManifest: ("schema_id", "schema_version", "research_dataset_manifest_id", "dataset_binding_id", "feature_definition_ids", "feature_set_id", "label_definition_id", "group_policy", "samples", "total_sample_count", "assignment_order", "advisory_only", "no_execution_authority"),
        ar.TemporalSplitManifest: ("schema_id", "schema_version", "split_plan_id", "split_plan_version", "split_assignment_id", "dataset_manifest_id", "dataset_binding_id", "feature_definition_ids", "feature_set_id", "label_definition_id", "formation_start", "selection_start", "oos_start", "end_time", "purge_rule", "embargo_seconds", "group_policy", "inclusion_policy", "min_samples_per_role", "formation_sample_ids", "selection_sample_ids", "oos_sample_ids", "purged_sample_ids", "embargoed_sample_ids", "assignment_hash", "advisory_only", "no_execution_authority"),
        ar.AlphaHypothesis: ("schema_id", "schema_version", "hypothesis_id", "hypothesis_name", "hypothesis_version", "predecessor_candidate_ids", "falsifiable_claim", "proposed_mechanism", "cohort", "horizon", "target", "falsification_condition", "human_review_state", "review_assertion", "code_version", "creation_provenance", "advisory_only", "no_execution_authority"),
        ar.MetricDefinition: ("schema_id", "schema_version", "metric_definition_id", "metric_name", "metric_version", "direction", "parameters_json", "code_version", "advisory_only", "no_execution_authority"),
        ar.BaselineDefinition: ("schema_id", "schema_version", "baseline_definition_id", "baseline_name", "baseline_version", "method_rule", "parameters_json", "same_partition_required", "acceptance_rule", "code_version", "advisory_only", "no_execution_authority"),
        ar.ExperimentFamily: ("schema_id", "schema_version", "experiment_family_id", "research_program", "cohort", "target", "metric_family", "correction_policy", "predecessor_family_id", "advisory_only", "no_execution_authority"),
        ar.PreregisteredExperiment: ("schema_id", "schema_version", "experiment_id", "experiment_family_id", "trial_number", "hypothesis_id", "dataset_binding_id", "research_dataset_manifest_id", "feature_definition_ids", "feature_set_id", "label_definition_id", "split_plan_id", "split_assignment_id", "primary_metric_id", "secondary_metric_ids", "baseline_id", "inclusion_exclusion_rules", "acceptance_thresholds_json", "search_space_json", "parameters_json", "random_seeds", "correction_policy", "cost_model_reference", "stop_failure_rules", "code_version", "creation_provenance", "preregistered_at", "advisory_only", "no_execution_authority"),
        ar.LifecycleReceipt: ("schema_id", "schema_version", "lifecycle_receipt_id", "experiment_id", "sequence_number", "previous_lifecycle_receipt_id", "action", "from_state", "to_state", "occurred_at", "provenance", "terminal_result_status", "advisory_only", "no_execution_authority"),
        ar.RunEvidenceReceipt: ("schema_id", "schema_version", "run_evidence_receipt_id", "experiment_id", "experiment_family_id", "trial_number", "dataset_binding_id", "research_dataset_manifest_id", "split_assignment_id", "membership_hash", "feature_set_id", "label_definition_id", "code_version", "parameters_json", "random_seeds", "evaluated_role", "metric_definition_ids", "baseline_id", "metric_results_json", "baseline_results_json", "candidate_criterion_met", "baseline_criterion_met", "uncertainty_state", "result_status", "oos_exposure_ordinal", "created_at", "creation_provenance", "advisory_only", "no_execution_authority"),
        ar.FamilySummary: ("schema_id", "schema_version", "experiment_family_id", "registered_experiment_ids", "trial_numbers", "evidence_receipt_ids", "evidence_statuses", "trial_statuses", "registered_trial_count", "evaluated_trial_count", "negative_trial_count", "inconclusive_trial_count", "advisory_only", "no_execution_authority"),
        ar.ExperimentControlResult: ("is_valid", "status", "error_codes", "record", "advisory_only", "no_execution_authority"),
        ar.ExperimentRegistryEntry: ("sequence_number", "record_kind", "record_id", "payload_sha256", "previous_entry_hash", "entry_hash", "record"),
        ar.ExperimentRegistrySnapshot: ("schema_id", "schema_version", "entries", "total_rows", "total_payload_bytes", "head_entry_hash", "advisory_only", "no_execution_authority"),
        ar.ExperimentRegistryResult: ("is_valid", "status", "error_codes", "snapshot", "inserted_record_ids", "idempotent_record_ids", "advisory_only", "no_execution_authority"),
    }
    for cls, names in expected_fields.items():
        assert tuple(field.name for field in fields(cls)) == names
        assert cls.__dataclass_params__.frozen is True
        assert cls.__name__ in ar.__all__
    caller = {"nested": [1, 2]}
    built = ar.build_feature_definition({
        "feature_name": "immutable", "feature_version": "1", "description": "immutable",
        "source_dependencies": ["market_observation.best_bid"], "parameters": caller,
        "lookback_rule": "POINT_IN_TIME", "availability_rule": "SOURCE_AVAILABILITY_TIME",
        "missing_data_policy": "REJECT", "transformation_version": "v",
        "no_future_information_rule": "FEATURE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME",
    }).record
    caller["nested"].append(3)
    assert built.parameters_json == '{"nested":[1,2]}'


def test_negative_matrix_closed_precedence_and_no_mutation(tmp_path) -> None:
    cases = (
        ar.build_feature_definition(None),
        ar.build_feature_definition({}),
        ar.build_feature_definition({"unknown": "x"}),
        ar.build_temporal_split_manifest(None, None),
        ar.append_experiment_records(tmp_path / "missing.sqlite3", ()),
    )
    allowed = set(ar.EXPERIMENT_OS_ERROR_CODES)
    for result in cases:
        assert not result.is_valid
        assert set(result.error_codes) <= allowed
        assert list(result.error_codes) == sorted(result.error_codes, key=ar.EXPERIMENT_OS_ERROR_CODES.index)
        assert getattr(result, "record", None) is None
        assert getattr(result, "snapshot", None) is None
    assert not (tmp_path / "missing.sqlite3").exists()


def test_source_has_no_dependency_network_credential_scheduler_or_trading_authority() -> None:
    forbidden_import_roots = {
        "requests", "httpx", "urllib", "socket", "websockets", "aiohttp",
        "subprocess", "sched", "asyncio", "nautilus_trader", "threading",
        "multiprocessing", "schedule", "apscheduler", "keyring", "web3",
    }
    forbidden_definitions = {
        "strategy", "place_order", "cancel_order", "submit_order", "paper_trade",
        "live_trade", "schedule_job", "run_daemon", "authenticate", "sign_order",
    }
    forbidden_calls = {"getenv", "putenv", "system", "popen", "startfile"}
    for path in SOURCE_FILES:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            node.names[0].name.split(".")[0] if isinstance(node, ast.Import) else (node.module or "").split(".")[0]
            for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
        }
        assert imports.isdisjoint(forbidden_import_roots)
        assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "compile"} for node in ast.walk(tree))
        assert not any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.name.casefold() in forbidden_definitions
            for node in ast.walk(tree)
        )
        assert not any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr.casefold() in forbidden_calls
            for node in ast.walk(tree)
        )
        assert "http://" not in source and "https://" not in source
    changed = subprocess.run(
        [
            "git", "diff", "--name-only",
            "17df81001171988e9ca49f92dc8fd170ecaa7103",
            "8e5d83f695d2f2ef38c9f30e3a8e95eb271718da", "--",
        ],
        cwd=ROOT, text=True, capture_output=True, check=True,
    ).stdout.splitlines()
    assert not any(Path(item).name in {"pyproject.toml", "uv.lock", "requirements.txt"} for item in changed)


def test_existing_research_priority_calibration_wallet_semantics_remain_non_signal() -> None:
    source = "\n".join(path.read_text(encoding="utf-8").lower() for path in SOURCE_FILES)
    assert "research_priority_score" not in source
    assert "wallet_research_signal" not in source
    assert "calibration usefulness" not in source
    assert not hasattr(ar, "Strategy")
    assert not hasattr(ar, "place_order")
