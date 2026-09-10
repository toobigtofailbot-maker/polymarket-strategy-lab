"""WP170 exact SQLite schema, append-only history, and tamper tests."""

from __future__ import annotations

from dataclasses import replace
import os
import sqlite3

import src.data_layer.analytical_research as ar
from src.data_layer.analytical_research import experiment_registry as registry
from src.data_layer.analytical_research import experiment_os as os_contract
from tests.data_layer.analytical_research.test_experiment_os_identity import binding, feature, label, reference
from tests.data_layer.analytical_research.test_experiment_os_preregistration import (
    baseline,
    experiment_stack,
    family,
    hypothesis,
    metric,
)
from tests.data_layer.analytical_research.test_experiment_os_samples_splits import base_samples, split
from tests.data_layer.analytical_research.test_experiment_os_lifecycle_evidence import (
    evidence_input,
    lifecycle,
)


def stack():
    return experiment_stack()


def _reidentify(record):
    kind, prefix, _identity, preimage = os_contract._identity_preimage(record)
    id_field = os_contract._RECORD_ID_FIELD[type(record)][2]
    return replace(record, **{id_field: os_contract._digest(kind, prefix, preimage)})


def test_registry_schema_append_idempotency_and_conflict_are_exact(tmp_path) -> None:
    path = tmp_path / "registry.sqlite3"
    initialized = ar.initialize_experiment_registry(path)
    assert initialized.status == "REGISTRY_INITIALIZED"
    records = stack()
    appended = ar.append_experiment_records(path, list(reversed(records)))
    assert appended.is_valid, appended.error_codes
    assert appended.status == "REGISTRY_APPEND_COMMITTED"
    assert appended.snapshot.total_rows == len(records)
    kinds = tuple(entry.record_kind for entry in appended.snapshot.entries)
    assert kinds == tuple(item[0] for item in ar.RECORD_KIND_TYPES[:10])
    retry = ar.append_experiment_records(path, records)
    assert retry.status == "REGISTRY_APPEND_IDEMPOTENT"
    assert retry.snapshot.head_entry_hash == appended.snapshot.head_entry_hash
    assert retry.snapshot.total_rows == len(records)
    hostile = replace(records[1], description="changed but stale identity")
    rejected = ar.append_experiment_records(path, (hostile,))
    assert not rejected.is_valid and rejected.snapshot is None
    loaded = ar.load_and_verify_experiment_registry(path)
    assert loaded.is_valid and loaded.snapshot.total_rows == len(records)
    connection = sqlite3.connect(path)
    try:
        objects = connection.execute(
            "SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ).fetchall()
        assert objects == [
            ("table", "experiment_records"), ("table", "registry_meta"),
            ("trigger", "experiment_records_no_delete"),
            ("trigger", "experiment_records_no_update"),
        ]
        assert connection.execute("PRAGMA application_id").fetchone() == (ar.REGISTRY_APPLICATION_ID,)
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("delete",)
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
        ).fetchall() == []
    finally:
        connection.close()

    duplicate_path = tmp_path / "duplicate.sqlite3"
    assert ar.initialize_experiment_registry(duplicate_path).is_valid
    duplicate = ar.append_experiment_records(duplicate_path, (records[0], records[0]))
    assert duplicate.status == "REGISTRY_APPEND_COMMITTED"
    assert duplicate.inserted_record_ids == (records[0].dataset_binding_id,)
    assert duplicate.idempotent_record_ids == (records[0].dataset_binding_id,)
    assert duplicate.snapshot.total_rows == 1

    order_path = tmp_path / "order.sqlite3"
    assert ar.initialize_experiment_registry(order_path).is_valid
    ordered = ar.append_experiment_records(order_path, records)
    assert tuple(
        (entry.record_kind, entry.record_id, entry.entry_hash)
        for entry in ordered.snapshot.entries
    ) == tuple(
        (entry.record_kind, entry.record_id, entry.entry_hash)
        for entry in appended.snapshot.entries
    )


def test_registry_complete_history_tamper_fails_closed(tmp_path) -> None:
    mutations = {
        "extra_index": ("CREATE INDEX hostile_index ON experiment_records(record_kind)",),
        "missing_trigger": ("DROP TRIGGER experiment_records_no_delete",),
        "payload": (
            "DROP TRIGGER experiment_records_no_update",
            "UPDATE experiment_records SET payload_json='{}' WHERE sequence_number=0",
            registry._CREATE_NO_UPDATE,
        ),
        "sequence": (
            "DROP TRIGGER experiment_records_no_update",
            "UPDATE experiment_records SET sequence_number=50 WHERE sequence_number=0",
            registry._CREATE_NO_UPDATE,
        ),
        "chain": (
            "DROP TRIGGER experiment_records_no_update",
            "UPDATE experiment_records SET entry_hash='registryentry:sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff' WHERE sequence_number=0",
            registry._CREATE_NO_UPDATE,
        ),
    }
    for name, statements in mutations.items():
        path = tmp_path / f"{name}.sqlite3"
        assert ar.initialize_experiment_registry(path).is_valid
        assert ar.append_experiment_records(path, stack()).is_valid
        connection = sqlite3.connect(path)
        try:
            for statement in statements:
                connection.execute(statement)
            connection.commit()
        finally:
            connection.close()
        result = ar.load_and_verify_experiment_registry(path)
        assert not result.is_valid and result.snapshot is None
        assert result.error_codes in {
            ("REGISTRY_SCHEMA_CONFLICT",), ("REGISTRY_INTEGRITY_TAMPER",),
        }


def test_registry_revalidation_rejects_pre_label_evidence_timestamp(tmp_path) -> None:
    path = tmp_path / "pre_label.sqlite3"
    records = stack()
    experiment_record, split_record = records[-1], records[4]
    assert ar.initialize_experiment_registry(path).is_valid
    assert ar.append_experiment_records(path, records).is_valid
    receipts = []
    for index, action in enumerate(ar.LIFECYCLE_ACTIONS[:5]):
        built = ar.build_lifecycle_receipt(
            experiment_record, receipts, action,
            f"2026-01-0{index + 1}T00:00:00Z", "human:test", (),
        )
        assert built.is_valid
        receipts.append(built.record)
    assert ar.append_experiment_records(path, receipts).is_valid
    recorded = ar.record_experiment_evidence(
        path, experiment_record.experiment_id,
        evidence_input(
            split_record, "OUT_OF_SAMPLE", created="2026-03-12T00:00:00Z",
        ),
    )
    assert recorded.is_valid
    evidence_entry = recorded.snapshot.entries[-1]
    forged = _reidentify(replace(
        evidence_entry.record, created_at="2026-03-11T23:59:59Z",
    ))
    kind, record_id, payload, payload_sha = registry._serialize(forged)
    entry_hash = registry._entry_hash(
        evidence_entry.sequence_number, kind, record_id, payload_sha,
        evidence_entry.previous_entry_hash,
    )
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP TRIGGER experiment_records_no_update")
        connection.execute(
            "UPDATE experiment_records SET record_id=?,payload_json=?,payload_sha256=?,entry_hash=? WHERE sequence_number=?",
            (record_id, payload, payload_sha, entry_hash, evidence_entry.sequence_number),
        )
        connection.execute(registry._CREATE_NO_UPDATE)
        connection.commit()
    finally:
        connection.close()
    rejected = ar.load_and_verify_experiment_registry(path)
    assert rejected.error_codes == ("LABEL_TIMING_INVALID",)
    assert rejected.snapshot is None


def test_registry_row_object_and_store_bounds_trigger_before_write(tmp_path, monkeypatch) -> None:
    path = tmp_path / "registry.sqlite3"
    assert ar.initialize_experiment_registry(path).is_valid
    first = stack()[0]
    assert ar.append_experiment_records(path, (first,)).is_valid
    current = ar.load_and_verify_experiment_registry(path).snapshot
    monkeypatch.setattr(registry, "MAX_REGISTRY_RECORDS", 1)
    retry = ar.append_experiment_records(path, (first,))
    assert retry.status == "REGISTRY_APPEND_IDEMPOTENT"
    second = stack()[1]
    rejected = ar.append_experiment_records(path, (second,))
    assert rejected.error_codes == ("LIMIT_EXCEEDED",)
    monkeypatch.setattr(registry, "MAX_REGISTRY_RECORDS", 4096)
    monkeypatch.setattr(registry, "MAX_STORE_PAYLOAD_BYTES", current.total_payload_bytes)
    assert ar.append_experiment_records(path, (first,)).is_valid
    assert ar.append_experiment_records(path, (second,)).error_codes == ("LIMIT_EXCEEDED",)
    monkeypatch.setattr(registry, "MAX_STORE_PAYLOAD_BYTES", 16_777_216)
    monkeypatch.setattr(registry, "MAX_RECORD_PAYLOAD_BYTES", 1)
    assert ar.append_experiment_records(path, (second,)).error_codes == ("LIMIT_EXCEEDED",)
    monkeypatch.setattr(registry, "MAX_RECORD_PAYLOAD_BYTES", 262_144)
    assert ar.append_experiment_records(
        path, (first,) * (ar.MAX_APPEND_BATCH + 1),
    ).error_codes == ("LIMIT_EXCEEDED",)
    oversize = ar.build_feature_definition({
        "feature_name": "large", "feature_version": "1", "description": "large",
        "source_dependencies": ["market_observation.best_bid"],
        "parameters": {f"k{index:04}": "y" * 64 for index in range(4000)},
        "lookback_rule": "POINT_IN_TIME", "availability_rule": "SOURCE_AVAILABILITY_TIME",
        "missing_data_policy": "REJECT", "transformation_version": "v",
        "no_future_information_rule": "FEATURE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME",
    })
    assert oversize.error_codes == ("LIMIT_EXCEEDED",)


def test_registry_referential_order_and_link_policy_fail_closed(tmp_path) -> None:
    path = tmp_path / "registry.sqlite3"
    assert ar.initialize_experiment_registry(path).is_valid
    experiment = stack()[-1]
    missing_dependencies = ar.append_experiment_records(path, (experiment,))
    assert missing_dependencies.error_codes == ("TRIAL_FAMILY_CONFLICT",)
    assert ar.load_and_verify_experiment_registry(path).snapshot.total_rows == 0
    wrong_suffix = ar.initialize_experiment_registry(tmp_path / "bad.db")
    assert not wrong_suffix.is_valid and wrong_suffix.snapshot is None
    assert ar.initialize_experiment_registry(
        tmp_path / "missing" / "registry.sqlite3"
    ).error_codes == ("FIELD_VALUE_INVALID",)
    directory_target = tmp_path / "directory.sqlite3"
    directory_target.mkdir()
    assert ar.initialize_experiment_registry(directory_target).error_codes == (
        "FIELD_VALUE_INVALID",
    )
    foreign = tmp_path / "foreign.sqlite3"
    connection = sqlite3.connect(foreign)
    try:
        connection.execute("CREATE TABLE foreign_table(value TEXT)")
        connection.commit()
    finally:
        connection.close()
    before = foreign.read_bytes()
    assert ar.initialize_experiment_registry(foreign).error_codes == (
        "REGISTRY_SCHEMA_CONFLICT",
    )
    assert foreign.read_bytes() == before
    linked_source = tmp_path / "linked_source.sqlite3"
    assert ar.initialize_experiment_registry(linked_source).is_valid
    hardlink = tmp_path / "hardlink.sqlite3"
    os.link(linked_source, hardlink)
    assert ar.load_and_verify_experiment_registry(hardlink).error_codes == (
        "FIELD_VALUE_INVALID",
    )
    symlink_target = tmp_path / "symlink_target.sqlite3"
    assert ar.initialize_experiment_registry(symlink_target).is_valid
    symlink = tmp_path / "symlink.sqlite3"
    try:
        symlink.symlink_to(symlink_target)
    except OSError:
        assert os.name == "nt"
    else:
        assert ar.load_and_verify_experiment_registry(symlink).error_codes == (
            "FIELD_VALUE_INVALID",
        )


def test_registry_revalidation_rejects_rehashed_semantic_and_cross_record_forgery(tmp_path) -> None:
    path = tmp_path / "registry.sqlite3"
    assert ar.initialize_experiment_registry(path).is_valid

    malformed = _reidentify(replace(feature(), parameters_json="[]"))
    result = ar.append_experiment_records(path, (malformed,))
    assert result.error_codes == ("FIELD_VALUE_INVALID",)
    assert ar.load_and_verify_experiment_registry(path).snapshot.total_rows == 0

    records = stack()
    second_binding = ar.build_dataset_binding(reference(), None, "commit:other").record
    forged_experiment = _reidentify(
        replace(records[-1], dataset_binding_id=second_binding.dataset_binding_id)
    )
    result = ar.append_experiment_records(
        path, records[:-1] + (second_binding, forged_experiment)
    )
    assert result.error_codes == ("TRIAL_FAMILY_CONFLICT",)
    assert ar.load_and_verify_experiment_registry(path).snapshot.total_rows == 0

    valid_records = stack()
    assert ar.append_experiment_records(path, valid_records[:-1]).is_valid
    wrong_direction = _reidentify(replace(
        valid_records[-1],
        acceptance_thresholds_json=(
            '{"primary_metric_operator":"LTE","primary_metric_threshold":"0.6"}'
        ),
    ))
    assert ar.append_experiment_records(path, (wrong_direction,)).error_codes == (
        "TRIAL_FAMILY_CONFLICT",
    )
    wrong_cohort_hypothesis = hypothesis(cohort="other cohort")
    assert ar.append_experiment_records(path, (wrong_cohort_hypothesis,)).is_valid
    wrong_family_lineage = _reidentify(replace(
        valid_records[-1], hypothesis_id=wrong_cohort_hypothesis.hypothesis_id,
    ))
    assert ar.append_experiment_records(path, (wrong_family_lineage,)).error_codes == (
        "TRIAL_FAMILY_CONFLICT",
    )
    assert ar.append_experiment_records(path, (valid_records[-1],)).is_valid
    lifecycle_record = lifecycle(valid_records[-1], 1)[0]
    invalid_state = _reidentify(replace(lifecycle_record, action="RESET_TO_UNSEEN"))
    assert ar.append_experiment_records(path, (invalid_state,)).error_codes == (
        "PREREGISTRATION_STATE_INVALID",
    )


def test_registry_enforces_oos_evidence_before_terminal_close_and_seals_closed_history(tmp_path) -> None:
    path = tmp_path / "registry.sqlite3"
    assert ar.initialize_experiment_registry(path).is_valid
    records = stack()
    experiment_record = records[-1]
    split_record = records[4]
    assert ar.append_experiment_records(path, records).is_valid
    receipts = lifecycle(experiment_record, 5)
    assert ar.append_experiment_records(path, receipts).is_valid
    direct = os_contract._build_run_evidence_receipt(
        experiment_record, records[3], split_record, records[7], receipts, (),
        evidence_input(split_record, "OUT_OF_SAMPLE"),
        allow_oos=True, prior_oos_release_count=0,
    ).record
    close = ar.build_lifecycle_receipt(
        experiment_record, receipts, "CLOSE_EXPERIMENT", "2026-04-12T00:00:00Z",
        "human:test", (direct,),
    ).record

    premature_close = ar.append_experiment_records(path, (close,))
    assert premature_close.error_codes == ("OOS_SEALED_EXPOSURE_VIOLATION",)
    assert ar.append_experiment_records(path, (direct,)).error_codes == (
        "OOS_SEALED_EXPOSURE_VIOLATION",
    )
    recorded = ar.record_experiment_evidence(
        path, experiment_record.experiment_id,
        evidence_input(split_record, "OUT_OF_SAMPLE"),
    )
    assert recorded.is_valid
    evidence = next(
        entry.record for entry in recorded.snapshot.entries
        if isinstance(entry.record, ar.RunEvidenceReceipt)
    )
    assert evidence == direct
    assert ar.append_experiment_records(path, (close,)).is_valid

    forged_later = _reidentify(replace(
        evidence,
        run_evidence_receipt_id=evidence.run_evidence_receipt_id,
        result_status="OOS_REUSED_DIAGNOSTIC",
        oos_exposure_ordinal=2,
        created_at="2026-04-13T00:00:00Z",
    ))
    sealed = ar.append_experiment_records(path, (forged_later,))
    assert sealed.error_codes == ("OOS_SEALED_EXPOSURE_VIOLATION",)
