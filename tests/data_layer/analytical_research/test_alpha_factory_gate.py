from __future__ import annotations

from dataclasses import replace

import pytest

from src.data_layer.analytical_research.alpha_factory_gate import (
    AF1_DIMENSIONS,
    AF1_REVIEW_REASON_CODES,
    AF1BenchmarkManifest,
    AF1BlindReviewRecord,
    AF1GateReceipt,
    AF1RealCaseEvidence,
    AF1SeededCaseResult,
    af1_record_from_mapping,
    af1_record_to_mapping,
    aggregate_af1_disposition,
    build_af1_benchmark_manifest,
    build_af1_blind_review_record,
    build_af1_gate_receipt,
    build_af1_real_case_evidence,
    build_af1_seeded_case_result,
    evaluate_seeded_af1_cases,
    validate_af1_record,
)


SHA = "1" * 64
COMMIT = "2" * 40
FLAGS = {
    "advisory_only": True,
    "human_review_required": True,
    "no_execution_authority": True,
    "no_strategy_authority": True,
    "no_qualification_authority": True,
}


def manifest():
    return build_af1_benchmark_manifest({
        "schema_id": "af1-benchmark-manifest", "schema_version": "1.0.0", "manifest_id": "",
        "wp_id": "S10-GATE-AF1", "base_sha": COMMIT, "phase_a_commit_sha": COMMIT,
        "wp_prompt_sha256": SHA, "wp_spec_sha256": SHA, "gate_contract_sha256": SHA,
        "runtime_authorization_envelope_sha256": SHA,
        "public_population_result_sha256": SHA,
        "population_manifest_id": "manifest:s10-gate-af1:benchmark:1.0.0",
        "parameter_set_id": "params:s10-gate-af1:benchmark-population:1.0.0",
        "normalizer_version": "normalizer:s10-gate-af1:wp164:1.0.0",
        "validator_version": "validator:s10-gate-af1:wp164:1.0.0",
        "alpha_discovery_policy_id": "alphadiscoverypolicy:sha256:" + SHA,
        "analysis_temporal_mode": "HISTORICAL_REPLAY",
        "alpha_memory_temporal_posture": "HISTORICAL_AVAILABILITY_UNPROVEN",
        "alpha_registry_head_entry_hash": None, "cutoff": "2026-09-23T00:00:00Z",
        "universe_snapshot_id": "alphauniverse:sha256:" + SHA,
        "research_queue_snapshot_id": "alphaqueue:sha256:" + SHA,
        "requested_market_count": 25, "requested_order_book_count": 1,
        "actual_market_count": 3, "actual_order_book_count": 1,
        "provider_label": "provider", "model_label": "model", "hermes_invocation_policy_id": "policy",
        "max_provider_calls": 3, "max_case_cost_usd": "5", "max_aggregate_cost_usd": "15",
        "retry_limit": 0, "coverage_terminal": "COMPLETE",
        "selected_core_triage_id": "triage:core", "selected_exploration_triage_id": "triage:explore",
        "selected_audit_triage_id": "triage:audit", **FLAGS,
    })


def seeded(case="S1_DUPLICATE"):
    return build_af1_seeded_case_result({
        "schema_id": "af1-seeded-case-result", "schema_version": "1.0.0", "seeded_case_result_id": "",
        "case_id": case, "status": "PASS", "reason_codes": [case + "_ORACLE_PASS"],
        "failure_evidence_refs": [], "alpha_discovery_policy_id": "policy",
        "phase_a_commit_sha": COMMIT, "wp_prompt_sha256": SHA, "wp_spec_sha256": SHA,
        "gate_contract_sha256": SHA, **FLAGS,
    })


def real():
    return build_af1_real_case_evidence({
        "schema_id": "af1-real-case-evidence", "schema_version": "1.0.0", "real_case_evidence_id": "",
        "manifest_id": manifest().manifest_id, "case_id": "AF1-C1", "selected_triage_id": "triage:core",
        "campaign_id": "campaign", "blind_artifact_id": "blind", "run_receipt_id": "receipt",
        "run_terminal_status": "RESEARCH_DRAFT_VALIDATED", "session_evidence_id": "session",
        "session_evidence_status": "AVAILABLE", "requested_provider_label": "provider",
        "requested_model_label": "model", "verified_provider_label": "provider",
        "verified_model_label": "model", "backend_telemetry_status": "UNAVAILABLE",
        "accepted_estimated_cost_usd": "1", "review_body_sha256": SHA, "terminal_reason": None, **FLAGS,
    })


def review():
    return build_af1_blind_review_record({
        "schema_id": "af1-blind-review-record", "schema_version": "1.0.0", "blind_review_record_id": "",
        "real_case_evidence_id": real().real_case_evidence_id, "case_id": "AF1-C1", "review_slot": "REVIEW-01",
        "review_body_sha256": SHA, "reviewer_alias": "SIDE12", "label": "USEFUL_RESEARCH_OUTPUT",
        "reason_codes": [AF1_REVIEW_REASON_CODES[0]], **FLAGS,
    })


def receipt():
    seeded_ids = tuple(seeded(case).seeded_case_result_id for case in (
        "S1_DUPLICATE", "S2_NEGATIVE_SCOPE", "S3_REOPEN", "S4_PIT", "S5_CLAIM_EVIDENCE",
        "S6_PROVIDER_BACKEND_GAP", "S7_BUDGET", "S8_AUTHORITY",
    ))
    return build_af1_gate_receipt({
        "schema_id": "af1-gate-receipt", "schema_version": "1.0.0", "gate_receipt_id": "",
        "phase_a_commit_sha": COMMIT, "wp_prompt_sha256": SHA, "wp_spec_sha256": SHA,
        "gate_contract_sha256": SHA, "runtime_authorization_envelope_sha256": SHA,
        "public_population_result_sha256": SHA,
        "manifest_id": manifest().manifest_id, "seeded_case_result_ids": list(seeded_ids),
        "real_case_evidence_ids": [], "blind_review_record_ids": [], "evidence_state": "FINALIZED",
        "terminal_reason": "BENCHMARK_REQUIRED_LANE_ABSENT",
        "dimension_statuses": {name: "PASS" for name in AF1_DIMENSIONS},
        "overall_disposition": "AF1_PASS", **FLAGS,
    })


@pytest.mark.parametrize("factory,record_type", [(manifest, AF1BenchmarkManifest), (seeded, AF1SeededCaseResult), (real, AF1RealCaseEvidence), (review, AF1BlindReviewRecord), (receipt, AF1GateReceipt)])
def test_five_records_strict_roundtrip(factory, record_type):
    record = factory()
    mapping = af1_record_to_mapping(record)
    assert af1_record_from_mapping(record_type, mapping) == record
    with pytest.raises(ValueError, match="CLOSED_SCHEMA"):
        af1_record_from_mapping(record_type, {**mapping, "undeclared_authority": True})
    id_field = next(field for field in mapping if field.endswith("_id") and field.startswith(("manifest", "seeded", "real", "blind", "gate")))
    with pytest.raises(ValueError, match="IDENTITY"):
        af1_record_from_mapping(record_type, {**mapping, id_field: "forged"})


def test_gate_receipt_identity_binds_graph_and_order_is_canonical():
    original = receipt()
    mapping = af1_record_to_mapping(original)
    reordered = {**mapping, "dimension_statuses": dict(reversed(list(mapping["dimension_statuses"].items()))), "gate_receipt_id": ""}
    assert build_af1_gate_receipt(reordered).gate_receipt_id == original.gate_receipt_id
    changed = {**mapping, "manifest_id": "af1manifest:sha256:" + "3" * 64, "gate_receipt_id": ""}
    assert build_af1_gate_receipt(changed).gate_receipt_id != original.gate_receipt_id


def test_population_result_digest_is_manifest_and_receipt_identity_material():
    original_manifest = manifest()
    changed_manifest_mapping = af1_record_to_mapping(original_manifest)
    changed_manifest_mapping["manifest_id"] = ""
    changed_manifest_mapping["public_population_result_sha256"] = "3" * 64
    changed_manifest = build_af1_benchmark_manifest(changed_manifest_mapping)
    assert changed_manifest.manifest_id != original_manifest.manifest_id

    original_receipt = receipt()
    changed_receipt_mapping = af1_record_to_mapping(original_receipt)
    changed_receipt_mapping["gate_receipt_id"] = ""
    changed_receipt_mapping["public_population_result_sha256"] = "3" * 64
    changed_receipt = build_af1_gate_receipt(changed_receipt_mapping)
    assert changed_receipt.gate_receipt_id != original_receipt.gate_receipt_id


def test_a1_manifest_null_receipt_binds_population_result_digest():
    mapping = af1_record_to_mapping(receipt())
    mapping.update({
        "gate_receipt_id": "", "manifest_id": None,
        "terminal_reason": "PUBLIC_POPULATION_EXTERNAL_UNAVAILABLE",
        "overall_disposition": "AF1_PASS",
    })
    first = build_af1_gate_receipt(mapping)
    mapping["gate_receipt_id"] = ""
    mapping["public_population_result_sha256"] = "4" * 64
    second = build_af1_gate_receipt(mapping)
    assert first.manifest_id is None and first.gate_receipt_id != second.gate_receipt_id


def test_correctly_rehashed_semantic_forgery_fails():
    direct = replace(manifest(), alpha_registry_head_entry_hash="3" * 64)
    direct = replace(direct, manifest_id="")
    from src.data_layer.analytical_research.alpha_factory_gate import _identity
    direct = replace(direct, manifest_id=_identity(direct))
    with pytest.raises(ValueError, match="POSTURE"):
        validate_af1_record(direct)


def test_exact_seeded_corpus_and_disposition_precedence():
    results = evaluate_seeded_af1_cases(
        phase_a_commit_sha=COMMIT, wp_prompt_sha256=SHA, wp_spec_sha256=SHA,
        gate_contract_sha256=SHA, alpha_discovery_policy_id="policy",
    )
    assert tuple(item.case_id for item in results) == (
        "S1_DUPLICATE", "S2_NEGATIVE_SCOPE", "S3_REOPEN", "S4_PIT", "S5_CLAIM_EVIDENCE",
        "S6_PROVIDER_BACKEND_GAP", "S7_BUDGET", "S8_AUTHORITY",
    )
    assert aggregate_af1_disposition({name: "PASS" for name in AF1_DIMENSIONS}) == "AF1_PASS"
    assert aggregate_af1_disposition({name: ("INCONCLUSIVE" if name == AF1_DIMENSIONS[0] else "PASS") for name in AF1_DIMENSIONS}) == "AF1_INCONCLUSIVE"
    assert aggregate_af1_disposition({name: ("FAIL" if name == AF1_DIMENSIONS[0] else "INCONCLUSIVE") for name in AF1_DIMENSIONS}) == "AF1_FAIL"


def test_af1_record_roundtrip_identity_and_semantic_symmetry():
    for factory, record_type in ((manifest, AF1BenchmarkManifest), (seeded, AF1SeededCaseResult), (real, AF1RealCaseEvidence), (review, AF1BlindReviewRecord), (receipt, AF1GateReceipt)):
        record = factory()
        assert af1_record_from_mapping(record_type, af1_record_to_mapping(record)) == record


def test_seeded_oracle_matrix_s1_through_s8():
    results = evaluate_seeded_af1_cases(
        phase_a_commit_sha=COMMIT, wp_prompt_sha256=SHA, wp_spec_sha256=SHA,
        gate_contract_sha256=SHA, alpha_discovery_policy_id="policy",
    )
    assert len(results) == 8
    assert all(item.status == "PASS" and item.reason_codes == (item.case_id + "_ORACLE_PASS",) for item in results)


def test_gate_dimension_aggregation_is_closed_and_non_numeric():
    assert aggregate_af1_disposition({name: "PASS" for name in AF1_DIMENSIONS}) == "AF1_PASS"
    with pytest.raises(ValueError, match="DIMENSIONS"):
        aggregate_af1_disposition({name: 1 for name in AF1_DIMENSIONS})


def test_blind_review_body_uses_only_retained_typed_hermes_fields_and_opaque_slots():
    item = review()
    assert item.review_slot == "REVIEW-01"
    assert item.review_body_sha256 == SHA
    assert not hasattr(item, "provider_label") and not hasattr(item, "selected_lane")


def test_review_decision_recomputes_body_hashes_slots_and_closed_labels():
    mapping = af1_record_to_mapping(review())
    mapping["label"] = "UNKNOWN_LABEL"
    mapping["blind_review_record_id"] = ""
    with pytest.raises(ValueError, match="REVIEW_INVALID"):
        build_af1_blind_review_record(mapping)


# ── Post-WP164A reconciliation oracles ────────────────────────────────────────

from src.data_layer.analytical_research.alpha_factory_gate import (  # noqa: E402
    AF1_REAL_CASE_TERMINAL_REASONS,
    AF1_TERMINAL_DIMENSION_OVERRIDES,
    derive_af1_dimension_statuses,
    derive_af1_review_usefulness,
)


def _seeded_all(status_for=None):
    results = []
    for case in (
        "S1_DUPLICATE", "S2_NEGATIVE_SCOPE", "S3_REOPEN", "S4_PIT", "S5_CLAIM_EVIDENCE",
        "S6_PROVIDER_BACKEND_GAP", "S7_BUDGET", "S8_AUTHORITY",
    ):
        status = (status_for or {}).get(case, "PASS")
        results.append(build_af1_seeded_case_result({
            "schema_id": "af1-seeded-case-result", "schema_version": "1.0.0", "seeded_case_result_id": "",
            "case_id": case, "status": status, "reason_codes": [f"{case}_ORACLE_{status}"],
            "failure_evidence_refs": [] if status == "PASS" else ["evidence:failure"],
            "alpha_discovery_policy_id": "policy", "phase_a_commit_sha": COMMIT,
            "wp_prompt_sha256": SHA, "wp_spec_sha256": SHA, "gate_contract_sha256": SHA, **FLAGS,
        }))
    return tuple(results)


EXPECTED_OVERRIDES = {
    "PUBLIC_POPULATION_EXTERNAL_UNAVAILABLE": {"PIT_PROVENANCE": "INCONCLUSIVE", "COVERAGE_SELECTION_ACCOUNTING": "INCONCLUSIVE"},
    "BENCHMARK_REQUIRED_LANE_ABSENT": {"COVERAGE_SELECTION_ACCOUNTING": "INCONCLUSIVE"},
    "RESEARCH_OUTPUT_INVALID": {"CLAIM_EVIDENCE_SUPPORT": "FAIL"},
    "USAGE_EVIDENCE_INVALID": {"CLAIM_EVIDENCE_SUPPORT": "INCONCLUSIVE", "BUDGET": "FAIL"},
    "PROVIDER_MODEL_MISMATCH": {"CLAIM_EVIDENCE_SUPPORT": "INCONCLUSIVE", "BUDGET": "INCONCLUSIVE", "AUTHORITY_CONTAINMENT": "FAIL"},
    "SUCCESSFUL_RUN_COST_UNKNOWN": {"BUDGET": "FAIL"},
    "CASE_COST_LIMIT_BREACH": {"BUDGET": "FAIL"},
    "AGGREGATE_COST_LIMIT_BREACH": {"BUDGET": "FAIL"},
    "UNEXPECTED_RESEARCH_TOOL": {"AUTHORITY_CONTAINMENT": "FAIL"},
    "AUTHORITY_BOUNDARY_BREACH": {"CLAIM_EVIDENCE_SUPPORT": "INCONCLUSIVE", "AUTHORITY_CONTAINMENT": "FAIL"},
}


@pytest.mark.parametrize("reason,expected", sorted(EXPECTED_OVERRIDES.items()))
def test_closed_terminal_dimension_overrides_emit_all_ten(reason, expected):
    statuses = derive_af1_dimension_statuses(terminal_reason=reason, seeded_results=_seeded_all())
    assert tuple(statuses) == AF1_DIMENSIONS
    assert statuses["RESEARCH_USEFULNESS_REPRODUCIBILITY"] == "INCONCLUSIVE"
    for name in AF1_DIMENSIONS[:-1]:
        assert statuses[name] == expected.get(name, "PASS"), name
    disposition = aggregate_af1_disposition(statuses)
    assert disposition == ("AF1_FAIL" if "FAIL" in expected.values() else "AF1_INCONCLUSIVE")


@pytest.mark.parametrize("known,budget", [(True, "PASS"), (False, "INCONCLUSIVE")])
def test_runtime_unavailable_budget_requires_known_within_limits(known, budget):
    statuses = derive_af1_dimension_statuses(
        terminal_reason="CONTROLLED_RUNTIME_UNAVAILABLE_TRUTHFULLY_CAPTURED",
        seeded_results=_seeded_all(), known_within_limits=known,
    )
    assert statuses["BUDGET"] == budget
    assert statuses["RUNTIME_FAILURE_VISIBILITY"] == "PASS"
    assert statuses["CLAIM_EVIDENCE_SUPPORT"] == "INCONCLUSIVE"
    with pytest.raises(ValueError):
        derive_af1_dimension_statuses(terminal_reason="CONTROLLED_RUNTIME_UNAVAILABLE_TRUTHFULLY_CAPTURED", seeded_results=_seeded_all())
    with pytest.raises(ValueError):
        derive_af1_dimension_statuses(terminal_reason="RESEARCH_OUTPUT_INVALID", seeded_results=_seeded_all(), known_within_limits=True)


def test_override_table_covers_every_real_case_reason_exactly_once():
    names = [reason for reason, _ in AF1_TERMINAL_DIMENSION_OVERRIDES]
    assert len(names) == len(set(names))
    assert set(AF1_REAL_CASE_TERMINAL_REASONS) <= set(names)
    with pytest.raises(ValueError):
        derive_af1_dimension_statuses(terminal_reason="PENDING_RUNTIME", seeded_results=_seeded_all())


def test_seeded_failure_is_concrete_baseline_fail_not_a_placeholder():
    statuses = derive_af1_dimension_statuses(
        terminal_reason="BENCHMARK_REQUIRED_LANE_ABSENT",
        seeded_results=_seeded_all({"S4_PIT": "FAIL"}),
    )
    assert statuses["PIT_PROVENANCE"] == "FAIL"
    assert "BASELINE" not in statuses.values()


@pytest.mark.parametrize("labels,replay,expected", [
    (("USEFUL_RESEARCH_OUTPUT",) * 3, True, "PASS"),
    (("USEFUL_RESEARCH_OUTPUT",) * 3, False, "FAIL"),
    (("USEFUL_RESEARCH_OUTPUT", "PARTIALLY_USEFUL_RESEARCH_OUTPUT", "USEFUL_RESEARCH_OUTPUT"), True, "FAIL"),
    (("NOT_USEFUL_RESEARCH_OUTPUT", "REVIEW_BLOCKED_INSUFFICIENT_CONTEXT", "USEFUL_RESEARCH_OUTPUT"), True, "FAIL"),
    (("REVIEW_BLOCKED_INSUFFICIENT_CONTEXT", "USEFUL_RESEARCH_OUTPUT", "USEFUL_RESEARCH_OUTPUT"), True, "INCONCLUSIVE"),
])
def test_usefulness_reproducibility_derivation(labels, replay, expected):
    assert derive_af1_review_usefulness(labels, replay_consistent=replay) == expected
    statuses = derive_af1_dimension_statuses(
        terminal_reason="BLIND_REVIEW_COMPLETED", seeded_results=_seeded_all(),
        review_labels=labels, replay_consistent=replay,
    )
    assert statuses["RESEARCH_USEFULNESS_REPRODUCIBILITY"] == expected
    with pytest.raises(ValueError):
        derive_af1_review_usefulness(labels[:2], replay_consistent=True)


@pytest.mark.parametrize("coverage,selected,valid", [
    ("COMPLETE", ("a", "b", "c"), True),
    ("COMPLETE", ("a", "b", None), False),
    ("REQUIRED_LANE_ABSENT", ("a", "b", None), True),
    ("REQUIRED_LANE_ABSENT", ("a", "b", "c"), False),
    ("REQUIRED_LANE_NOT_RESEARCH_EXECUTABLE", ("a", "b", "c"), True),
    ("REQUIRED_LANE_NOT_RESEARCH_EXECUTABLE", (None, "b", "c"), False),
    ("SOMETHING_ELSE", ("a", "b", "c"), False),
])
def test_manifest_coverage_terminal_is_closed(coverage, selected, valid):
    mapping = af1_record_to_mapping(manifest())
    mapping.update(
        manifest_id="", coverage_terminal=coverage, selected_core_triage_id=selected[0],
        selected_exploration_triage_id=selected[1], selected_audit_triage_id=selected[2],
    )
    if valid:
        build_af1_benchmark_manifest(mapping)
    else:
        with pytest.raises(ValueError, match="SELECTION"):
            build_af1_benchmark_manifest(mapping)


@pytest.mark.parametrize("field,value", [
    ("requested_market_count", 24), ("requested_order_book_count", 0), ("actual_market_count", 0),
    ("retry_limit", 1), ("max_provider_calls", 4),
])
def test_manifest_binds_exact_limits_and_actual_counts(field, value):
    mapping = af1_record_to_mapping(manifest())
    mapping.update(manifest_id="", **{field: value})
    with pytest.raises(ValueError):
        build_af1_benchmark_manifest(mapping)


@pytest.mark.parametrize("updates", [
    {"terminal_reason": "PUBLIC_POPULATION_EXTERNAL_UNAVAILABLE"},  # A1 with a manifest
    {"manifest_id": None},  # non-A1 without manifest
    {"public_population_result_sha256": None},
    {"runtime_authorization_envelope_sha256": None},
    {"terminal_reason": "BLIND_REVIEW_COMPLETED"},  # review path without 3+3
    {"terminal_reason": "RESEARCH_OUTPUT_INVALID"},  # real-case terminal with 0 cases
    {"evidence_state": "PENDING_RUNTIME"},
])
def test_gate_receipt_graph_matches_terminal_path(updates):
    mapping = af1_record_to_mapping(receipt())
    mapping.update(gate_receipt_id="", **updates)
    mapping["overall_disposition"] = "AF1_PASS"
    with pytest.raises(ValueError, match="RECEIPT"):
        build_af1_gate_receipt(mapping)


def test_review_body_mutation_changes_downstream_identity_and_order_does_not():
    base = af1_record_to_mapping(review())
    changed = {**base, "review_body_sha256": "9" * 64, "blind_review_record_id": ""}
    assert build_af1_blind_review_record(changed).blind_review_record_id != base["blind_review_record_id"]
    reordered = {**dict(reversed(list(base.items()))), "blind_review_record_id": "",
                 "reason_codes": list(reversed(base["reason_codes"]))}
    assert build_af1_blind_review_record(reordered).blind_review_record_id == base["blind_review_record_id"]
