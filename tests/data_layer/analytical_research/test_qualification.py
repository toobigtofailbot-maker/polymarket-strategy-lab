"""S10-QUAL-01 deterministic qualification candidate packet: focused oracles.

Synthetic Alpha/provenance fixtures plus the committed canonical S10-GATE-AF1
receipt as a predecessor compatibility fixture. Nothing here qualifies a real
candidate, constructs a WP170 experiment record, or touches any network.
"""

from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path

import pytest

from src.data_layer.analytical_research import alpha_factory_gate as af1
from src.data_layer.analytical_research import alpha_factory_registry as afr
from src.data_layer.analytical_research import experiment_os as eo
from src.data_layer.analytical_research import qualification as q
from src.data_layer.point_in_time_market_research.research_provenance import (
    build_research_provenance_manifest,
)
from tests.data_layer.analytical_research.test_alpha_factory_registry import (
    fresh,
    mk_candidate,
    mk_episode,
    mk_family,
    mk_source,
)

ROOT = Path(__file__).resolve().parents[3]
AF1_EVIDENCE = ROOT / "docs" / "gate_evidence" / "S10-GATE-AF1" / "af1_gate_evidence.json"
CANONICAL_AF1_RECEIPT_ID = (
    "af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2"
)
DATASET_REF = "datasetsnapshot:pit-2026-09-fixture"
CUTOFF = "2026-09-26T00:00:00Z"
PUBLIC_REF = "feat.public.weather-forecast"
TIME_REF = "feat.time.hours-to-close"
MARKET_REF = "feat.market.pit-midpoint"


# ── fixtures ─────────────────────────────────────────────────────────────────
def snapshot_of(path, records):
    result = afr.append_alpha_factory_records(path, records)
    assert result.is_valid, result.error_codes
    return result.snapshot


@dataclasses.dataclass
class Lineage:
    path: str
    source: object
    candidate: object
    family: object
    episode: object
    snapshot: object


@pytest.fixture
def lineage(tmp_path):
    path = fresh(tmp_path)
    source, candidate, family = mk_source(), mk_candidate(), mk_family()
    episode = mk_episode(candidate, family, source)
    return Lineage(path, source, candidate, family, episode,
                   snapshot_of(path, [source, candidate, family, episode]))


def af1_mapping():
    return json.loads(AF1_EVIDENCE.read_text(encoding="utf-8"))["gate_receipt"]


def af1_pass():
    return af1.af1_record_from_mapping(af1.AF1GateReceipt, af1_mapping())


def af1_with(dimension, status):
    mapping = af1_mapping()
    mapping["dimension_statuses"] = dict(mapping["dimension_statuses"], **{dimension: status})
    mapping["overall_disposition"] = af1.aggregate_af1_disposition(mapping["dimension_statuses"])
    mapping["gate_receipt_id"] = ""
    return af1.build_af1_gate_receipt(mapping)


def manifest(cutoff="2026-09-25T00:00:00Z", dataset_refs=(DATASET_REF,), **over):
    values = dict(
        repo_code_identity="repo:qual-fixture", information_cutoff=cutoff,
        output_identity="output:qual-fixture", output_hash="d" * 64,
        dataset_refs=dataset_refs,
    )
    values.update(over)
    return build_research_provenance_manifest(**values)


def hypothesis_plan(**over):
    plan = {
        "hypothesis_name": "cold-weather-unders",
        "hypothesis_version": "v1",
        "falsifiable_claim": "Cold forecasts predict lower totals than priced.",
        "proposed_mechanism": "Temperature suppresses scoring.",
        "cohort": "nfl-2026 outdoor games",
        "horizon": "kickoff minus 24h",
        "target": "total-points-under",
        "falsification_condition": "No Brier improvement over B0 out of sample.",
        "human_review_state": "REVIEWED",
        "review_assertion": "Reviewed by research lead.",
        "code_version": "code-v1",
    }
    plan.update(over)
    return plan


def feature_plan(**over):
    plan = {
        "feature_refs": [PUBLIC_REF, TIME_REF, MARKET_REF],
        "feature_source_classes": {
            PUBLIC_REF: "PUBLIC_NON_MARKET", TIME_REF: "TIME_ONLY", MARKET_REF: "MARKET_PIT",
        },
        "feature_evidence_refs": {
            PUBLIC_REF: ["evidence:weather-archive"], TIME_REF: ["evidence:schedule"],
            MARKET_REF: ["evidence:pit-book", "evidence:pit-trades"],
        },
        "availability_rule": "FEATURE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME",
        "no_future_information_rule": "NO_POST_DECISION_OR_POST_OUTCOME_INFORMATION",
        "missing_data_policy": "Exclude samples lacking any declared feature.",
    }
    plan.update(over)
    return plan


def label_plan(**over):
    plan = {
        "label_ref": "label.total-under",
        "prediction_target": "binary under outcome",
        "horizon_rule": "event completion",
        "target_time_rule": "official final score time",
        "outcome_source_rule": "official league box score",
        "availability_time_rule": "available after official final",
        "censoring_rule": "postponed games censored",
        "evidence_reference_ids": ["evidence:league-scores"],
    }
    plan.update(over)
    return plan


def split_plan(**over):
    plan = {
        "dataset_snapshot_reference_ids": [DATASET_REF],
        "group_policy": "EXCLUSIVE",
        "event_grouping_rule": "LEAKAGE_MARKET_RELATED_EXCLUSIVE",
        "formation_start": "2024-09-01T00:00:00Z",
        "selection_start": "2025-01-01T00:00:00Z",
        "oos_start": "2025-09-01T00:00:00Z",
        "end_time": "2026-02-01T00:00:00Z",
        "purge_rule": "PURGE_LABEL_AVAILABILITY_AT_OR_AFTER_NEXT_BOUNDARY",
        "embargo_seconds": 86400,
        "inclusion_policy": "DECISION_TIME_HALF_OPEN",
        "min_samples_per_role": 30,
    }
    plan.update(over)
    return plan


def power_plan(**over):
    plan = {
        "analysis_unit": "game",
        "available_sample_count": 120,
        "available_independent_group_count": 40,
        "required_sample_count": 200,
        "required_independent_group_count": 60,
        "power_method": "declared two-sided paired Brier difference",
        "power_analysis_reference_id": "evidence:power-analysis-v1",
        "target_power": "0.8",
        "significance_level": "0.05",
        "minimum_detectable_effect": "0.01",
    }
    plan.update(over)
    return plan


def family_plan(**over):
    plan = {
        "research_program": "s10-weather",
        "metric_family": "proper-scores",
        "primary_metric_name": "BRIER_SCORE",
        "primary_metric_direction": "LOWER_IS_BETTER",
        "secondary_metric_names": ["LOG_LOSS"],
        "correction_policy": "FAMILY_TRIAL_COUNT",
        "multiplicity_method": "declared Holm over family trials",
        "family_size": 3,
        "acceptance_thresholds": {
            "primary_metric_operator": "LTE", "primary_metric_threshold": "0.24",
        },
        "baseline_acceptance_rule": "CANDIDATE_LTE_BASELINE",
    }
    plan.update(over)
    return plan




def forecast_plan(**over):
    plan = {
        "applicability": "REQUIRED",
        "b0_rule": "PIT_MARKET_PROBABILITY_V1",
        "b0_parameters": {"max_midpoint_spread": "0.05", "max_last_trade_age_seconds": 900},
        "b1_feature_refs": [PUBLIC_REF, TIME_REF],
        "b2_feature_refs": [MARKET_REF, PUBLIC_REF, TIME_REF],
        "b2_market_added_feature_refs": [MARKET_REF],
        "primary_proper_score": "BRIER_SCORE",
        "calibration_diagnostic": "reliability diagram, ten equal-count bins",
        "same_oos_membership_required": True,
        "b1_vs_b0_required": True,
        "b2_vs_b0_required": True,
        "b2_vs_b1_incrementality_required": True,
    }
    plan.update(over)
    return plan


def feasibility_plan(**over):
    plan = {
        "FEES": {"state": "AVAILABLE", "evidence_reference_ids": ["evidence:fee-schedule"]},
        "RESOLUTION_RULES": {"state": "AVAILABLE", "evidence_reference_ids": ["evidence:rules"]},
        "TICK_SIZE_MIN_ORDER": {"state": "PARTIAL", "evidence_reference_ids": ["evidence:tick"]},
        "SPREAD_DEPTH": {"state": "MISSING", "evidence_reference_ids": []},
        "LATENCY": {"state": "NOT_APPLICABLE", "evidence_reference_ids": []},
        "PARTIAL_FILL": {"state": "MISSING", "evidence_reference_ids": []},
    }
    plan.update(over)
    return plan


def binary_input(lin, **over):
    value = {
        "candidate_version": "qual-v1",
        "alpha_candidate_id": lin.candidate.candidate_id,
        "hypothesis_family_id": lin.family.hypothesis_family_id,
        "governing_research_episode_id": lin.episode.research_episode_id,
        "information_cutoff": CUTOFF,
        "qualification_mode": "BINARY_PROBABILITY",
        "hypothesis_plan": hypothesis_plan(),
        "feature_plan": feature_plan(),
        "label_plan": label_plan(),
        "dataset_split_plan": split_plan(),
        "sample_power_plan": power_plan(),
        "test_family_plan": family_plan(),
        "forecast_evaluation_plan": forecast_plan(),
        "execution_feasibility_plan": feasibility_plan(),
        "wallet_dependency": "NON_WALLET",
        "creation_provenance": "synthetic S10-QUAL-01 fixture",
    }
    value.update(over)
    return value


def generic_input(lin, **over):
    value = binary_input(
        lin,
        qualification_mode="GENERIC_METRIC",
        forecast_evaluation_plan={"applicability": "NOT_APPLICABLE"},
        test_family_plan=family_plan(
            primary_metric_name="hit-rate", primary_metric_direction="HIGHER_IS_BETTER",
            secondary_metric_names=[], correction_policy="SINGLETON", family_size=1,
            acceptance_thresholds={
                "primary_metric_operator": "GTE", "primary_metric_threshold": "0.55",
            },
            baseline_acceptance_rule="CANDIDATE_GTE_BASELINE",
        ),
    )
    value.update(over)
    return value


def build(lin, value=None, *, receipt=None, manifests=None, snapshot=None):
    return q.build_qualification_candidate(
        lin.snapshot if snapshot is None else snapshot,
        af1_pass() if receipt is None else receipt,
        [manifest()] if manifests is None else manifests,
        binary_input(lin) if value is None else value,
    )


def ok(result):
    assert result.is_valid, result.error_codes
    assert result.status == "QUALIFICATION_CANDIDATE_VALID"
    return result.record


def rejected(result, code):
    assert not result.is_valid
    assert result.status == "QUALIFICATION_CANDIDATE_REJECTED"
    assert result.error_codes == (code,)
    assert result.record is None


def rehash(record, **changes):
    """Directly construct a changed record with a self-consistent identity."""
    draft = dataclasses.replace(record, **changes)
    return dataclasses.replace(draft, qualification_candidate_id=q._digest(q._preimage(draft)))


def with_plan(record, name, mutate):
    plan = json.loads(getattr(record, f"{name}_json"))
    mutate(plan)
    return rehash(record, **{f"{name}_json": q._plan_json(plan)})


# ── Q01 / Q02 identity and roundtrip ─────────────────────────────────────────
def test_q01_identity_deterministic_and_mapping_roundtrip(lineage):
    first, second = ok(build(lineage)), ok(build(lineage))
    assert first == second
    assert first.qualification_candidate_id.startswith("qualificationcandidate:sha256:")
    assert len(first.qualification_candidate_id.split(":")[-1]) == 64
    mapping = q.qualification_candidate_to_mapping(first)
    assert list(mapping) == [field.name for field in dataclasses.fields(q.QualificationCandidate)]
    assert isinstance(mapping["research_provenance_manifest_ids"], list)
    assert ok(q.qualification_candidate_from_mapping(json.loads(json.dumps(mapping)))) == first
    assert ok(q.validate_qualification_candidate(first)) is first


def test_q01_caller_order_is_canonicalized(lineage):
    base = ok(build(lineage))
    shuffled = binary_input(
        lineage,
        feature_plan=feature_plan(feature_refs=[TIME_REF, MARKET_REF, PUBLIC_REF]),
        forecast_evaluation_plan=forecast_plan(
            b1_feature_refs=[TIME_REF, PUBLIC_REF], b2_feature_refs=[TIME_REF, MARKET_REF, PUBLIC_REF],
        ),
    )
    shuffled["feature_plan"]["feature_evidence_refs"][MARKET_REF] = ["evidence:pit-trades", "evidence:pit-book"]
    assert ok(build(lineage, shuffled)).qualification_candidate_id == base.qualification_candidate_id
    stored = json.loads(base.feature_plan_json)
    assert stored["feature_refs"] == sorted([PUBLIC_REF, TIME_REF, MARKET_REF])
    assert base.feature_plan_json == json.dumps(stored, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@pytest.mark.parametrize("key,value", [
    ("candidate_version", "qual-v2"),
    ("creation_provenance", "other provenance"),
    ("information_cutoff", "2026-09-26T00:00:01Z"),
    ("hypothesis_plan", hypothesis_plan(cohort="nfl-2026 all games")),
    ("feature_plan", feature_plan(missing_data_policy="Impute nothing; drop sample.")),
    ("label_plan", label_plan(censoring_rule="postponed games dropped")),
    ("dataset_split_plan", split_plan(embargo_seconds=3600)),
    ("sample_power_plan", power_plan(available_sample_count=121)),
    ("test_family_plan", family_plan(family_size=4)),
    ("forecast_evaluation_plan", forecast_plan(calibration_diagnostic="ECE, 15 bins")),
    ("execution_feasibility_plan", feasibility_plan(LATENCY={"state": "MISSING", "evidence_reference_ids": []})),
])
def test_q02_included_field_mutation_changes_identity(lineage, key, value):
    base = ok(build(lineage))
    changed = ok(build(lineage, binary_input(lineage, **{key: value})))
    assert changed.qualification_candidate_id != base.qualification_candidate_id


def test_q02_bound_external_ids_change_identity(lineage):
    base = ok(build(lineage))
    other = ok(build(lineage, manifests=[manifest(), manifest(output_hash="e" * 64)]))
    assert other.research_provenance_manifest_ids != base.research_provenance_manifest_ids
    assert other.qualification_candidate_id != base.qualification_candidate_id


def test_q02_record_field_change_without_rehash_rejects(lineage):
    record = ok(build(lineage))
    changed = dataclasses.replace(record, creation_provenance="tampered")
    rejected(q.validate_qualification_candidate(changed), "IDENTITY_DERIVATION_MISMATCH")


def test_q02_direct_rehash_cannot_bypass_semantics(lineage):
    record = ok(build(lineage))
    bad = with_plan(record, "hypothesis_plan", lambda p: p.update(human_review_state="DRAFT"))
    rejected(q.validate_qualification_candidate(bad), "HYPOTHESIS_PLAN_INVALID")
    bad = with_plan(record, "forecast_evaluation_plan", lambda p: p.update(b1_feature_refs=[MARKET_REF]))
    rejected(q.validate_qualification_candidate(bad), "FORECAST_PLAN_INVALID")
    rejected(q.validate_qualification_candidate(rehash(record, qualification_mode="GENERIC_METRIC")),
             "FORECAST_PLAN_INVALID")
    rejected(q.validate_qualification_candidate(rehash(record, experiment_os_schema_version="2.0.0")),
             "SCHEMA_UNSUPPORTED")
    rejected(q.validate_qualification_candidate(rehash(record, schema_id="other")), "SCHEMA_UNSUPPORTED")


# ── Q03 closed schema / floats / canonical JSON ──────────────────────────────
def test_q03_input_mapping_closed_schema(lineage):
    rejected(build(lineage, binary_input(lineage, extra_field="x")), "FIELD_VALUE_INVALID")
    value = binary_input(lineage)
    del value["creation_provenance"]
    rejected(build(lineage, value), "FIELD_MISSING")
    rejected(build(lineage, ["not", "a", "mapping"]), "FIELD_TYPE_INVALID")


@pytest.mark.parametrize("value", [0.8, float("nan"), float("inf")])
def test_q03_binary_float_rejected_recursively(lineage, value):
    rejected(build(lineage, binary_input(lineage, sample_power_plan=power_plan(target_power=value))),
             "FIELD_TYPE_INVALID")
    nested = feasibility_plan()
    nested["FEES"] = {"state": "AVAILABLE", "evidence_reference_ids": [value]}
    rejected(build(lineage, binary_input(lineage, execution_feasibility_plan=nested)), "FIELD_TYPE_INVALID")


def test_q03_from_mapping_and_nested_json_fail_closed(lineage):
    record = ok(build(lineage))
    mapping = q.qualification_candidate_to_mapping(record)
    rejected(q.qualification_candidate_from_mapping({**mapping, "extra": 1}), "FIELD_VALUE_INVALID")
    missing = dict(mapping)
    del missing["label_plan_json"]
    rejected(q.qualification_candidate_from_mapping(missing), "FIELD_MISSING")
    rejected(q.qualification_candidate_from_mapping(
        {**mapping, "research_provenance_manifest_ids": tuple(mapping["research_provenance_manifest_ids"])}
    ), "FIELD_TYPE_INVALID")
    pretty = json.dumps(json.loads(record.label_plan_json), indent=1, sort_keys=True)
    rejected(q.validate_qualification_candidate(rehash(record, label_plan_json=pretty)), "FIELD_VALUE_INVALID")
    dup = record.label_plan_json[:-1] + ',"label_ref":"label.other"}'
    rejected(q.validate_qualification_candidate(rehash(record, label_plan_json=dup)), "FIELD_VALUE_INVALID")
    floaty = record.sample_power_plan_json.replace('"available_sample_count":120', '"available_sample_count":120.0')
    assert floaty != record.sample_power_plan_json
    rejected(q.validate_qualification_candidate(rehash(record, sample_power_plan_json=floaty)), "FIELD_VALUE_INVALID")
    nan = record.sample_power_plan_json.replace('"available_sample_count":120', '"available_sample_count":NaN')
    rejected(q.validate_qualification_candidate(rehash(record, sample_power_plan_json=nan)), "FIELD_VALUE_INVALID")
    rejected(q.validate_qualification_candidate(rehash(record, feature_plan_json="[]")), "FIELD_VALUE_INVALID")
    rejected(q.validate_qualification_candidate(mapping), "FIELD_TYPE_INVALID")


# ── Q04 / Q05 Alpha lineage crossing ─────────────────────────────────────────
def test_q04_exact_current_supportive_leaf_crossing(lineage):
    record = ok(build(lineage))
    assert record.alpha_registry_head_entry_hash == lineage.snapshot.head_entry_hash
    assert record.alpha_candidate_id == lineage.candidate.candidate_id
    assert record.hypothesis_family_id == lineage.family.hypothesis_family_id
    assert record.governing_research_episode_id == lineage.episode.research_episode_id


def test_q04_successor_supportive_leaf_is_current(lineage):
    successor = mk_episode(lineage.candidate, lineage.family, lineage.source,
                           predecessor=lineage.episode.research_episode_id, scope={"league": "nfl", "v": "2"})
    snapshot = snapshot_of(lineage.path, [successor])
    ok(build(lineage, binary_input(lineage, governing_research_episode_id=successor.research_episode_id),
             snapshot=snapshot))
    # The superseded predecessor is now stale.
    rejected(build(lineage, snapshot=snapshot), "ALPHA_CURRENT_LEAF_INVALID")


def test_q05_missing_and_mismatched_lineage_rejects(lineage):
    other_candidate = mk_candidate(scope="nba-2026", mechanism="rest-days", subject="nba")
    other_family = mk_family(mechanism="rest-days")
    other_episode = mk_episode(other_candidate, other_family, lineage.source)
    snapshot = snapshot_of(lineage.path, [other_candidate, other_family, other_episode])
    for key, value in (
        ("alpha_candidate_id", "alphacandidate:sha256:" + "0" * 64),
        ("hypothesis_family_id", "alphafamily:sha256:" + "0" * 64),
        ("governing_research_episode_id", "alphaepisode:sha256:" + "0" * 64),
        ("alpha_candidate_id", other_candidate.candidate_id),
        ("hypothesis_family_id", other_family.hypothesis_family_id),
        ("governing_research_episode_id", other_episode.research_episode_id),
        # A family id supplied as candidate id (wrong record kind).
        ("alpha_candidate_id", "alphacandidate:" + lineage.family.hypothesis_family_id.split(":", 1)[1]),
    ):
        rejected(build(lineage, binary_input(lineage, **{key: value}), snapshot=snapshot),
                 "ALPHA_LINEAGE_INVALID")
    rejected(build(lineage, binary_input(lineage, alpha_candidate_id="not-an-alpha-id")), "FIELD_VALUE_INVALID")


def test_q05_ambiguous_leaves_reject(lineage):
    twin = mk_episode(lineage.candidate, lineage.family, lineage.source, scope={"league": "nfl", "twin": "1"})
    snapshot = snapshot_of(lineage.path, [twin])
    rejected(build(lineage, snapshot=snapshot), "ALPHA_CURRENT_LEAF_INVALID")
    rejected(build(lineage, binary_input(lineage, governing_research_episode_id=twin.research_episode_id),
                   snapshot=snapshot), "ALPHA_CURRENT_LEAF_INVALID")


@pytest.mark.parametrize("state", [s for s in (
    "NO_EDGE_CURRENTLY", "HYPOTHESIS_FALSIFIED", "DATA_INSUFFICIENT", "EXECUTION_UNECONOMIC",
    "WATCH_FOR_CHANGE", "RESEARCH_STALE", "MECHANISM_FAMILY_EXHAUSTED",
)])
def test_q05_non_supportive_current_leaf_rejects(lineage, state):
    successor = mk_episode(lineage.candidate, lineage.family, lineage.source, state=state,
                           predecessor=lineage.episode.research_episode_id)
    snapshot = snapshot_of(lineage.path, [successor])
    rejected(build(lineage, binary_input(lineage, governing_research_episode_id=successor.research_episode_id),
                   snapshot=snapshot), "ALPHA_RESULT_STATE_INVALID")
    rejected(build(lineage, snapshot=snapshot), "ALPHA_CURRENT_LEAF_INVALID")


def test_q05_reopen_leaf_is_not_supportive(tmp_path):
    path = fresh(tmp_path)
    source, candidate, family = mk_source(), mk_candidate(), mk_family()
    watch = mk_episode(candidate, family, source, state="WATCH_FOR_CHANGE")
    reopen = mk_episode(candidate, family, source, state="REOPEN_TRIGGERED",
                        reopened=watch.research_episode_id, predecessor=watch.research_episode_id)
    lin = Lineage(path, source, candidate, family, reopen,
                  snapshot_of(path, [source, candidate, family, watch, reopen]))
    rejected(build(lin), "ALPHA_RESULT_STATE_INVALID")


def fabricated_append(snapshot, record):
    last = snapshot.entries[-1]
    entry = afr.AlphaFactoryRegistryEntry(
        len(snapshot.entries), "RESEARCH_EPISODE", record.research_episode_id, "f" * 64,
        last.entry_hash, "alpharegistryentry:sha256:" + "e" * 64, record,
    )
    return dataclasses.replace(snapshot, entries=(*snapshot.entries, entry),
                               total_rows=snapshot.total_rows + 1, head_entry_hash=entry.entry_hash)


def test_q05_cross_family_lineage_rejects(lineage):
    other_family = mk_family(mechanism="wind-scoring")
    snapshot = snapshot_of(lineage.path, [other_family])
    # A different family's episode naming this lineage's leaf as predecessor (the
    # registry forbids this; the crossing re-proves it rather than trusting it).
    cross = mk_episode(lineage.candidate, other_family, lineage.source,
                       predecessor=lineage.episode.research_episode_id)
    rejected(build(lineage, snapshot=fabricated_append(snapshot, cross)), "ALPHA_LINEAGE_INVALID")


def test_q05_registry_snapshot_integrity(lineage, tmp_path):
    snap = lineage.snapshot
    empty = afr.initialize_alpha_factory_registry(str(tmp_path / "empty.sqlite3")).snapshot
    cases = [
        None,
        {"entries": []},
        empty,
        dataclasses.replace(snap, advisory_only=False),
        dataclasses.replace(snap, no_qualification_authority=False),
        dataclasses.replace(snap, total_rows=snap.total_rows + 1),
        dataclasses.replace(snap, head_entry_hash=None),
        dataclasses.replace(snap, head_entry_hash="alpharegistryentry:sha256:" + "0" * 64),
        dataclasses.replace(snap, entries=snap.entries[::-1]),
        dataclasses.replace(snap, entries=(*snap.entries[:-1], dataclasses.replace(
            snap.entries[-1], record=dataclasses.replace(lineage.episode, thesis="tampered")))),
    ]
    for case in cases:
        rejected(build(lineage, snapshot=case) if case is not None else q.build_qualification_candidate(
            None, af1_pass(), [manifest()], binary_input(lineage)), "ALPHA_REGISTRY_INVALID")


def test_q05_alpha_lane_priority_is_not_an_input(lineage):
    rejected(build(lineage, binary_input(lineage, research_lane="CORE")), "FIELD_VALUE_INVALID")


# ── Q06 / Q07 AF1 binding ────────────────────────────────────────────────────
def test_q06_canonical_af1_pass_receipt_is_bound_by_id(lineage):
    receipt = af1_pass()
    assert receipt.gate_receipt_id == CANONICAL_AF1_RECEIPT_ID
    assert dict(receipt.dimension_statuses) == {name: "PASS" for name in af1.AF1_DIMENSIONS}
    assert ok(build(lineage, receipt=receipt)).af1_gate_receipt_id == CANONICAL_AF1_RECEIPT_ID


def test_q06_receipt_id_is_not_a_hardcoded_product_constant():
    source = (ROOT / "src" / "data_layer" / "analytical_research" / "qualification.py").read_text(encoding="utf-8")
    assert CANONICAL_AF1_RECEIPT_ID.split(":")[-1] not in source


@pytest.mark.parametrize("status", ["FAIL", "INCONCLUSIVE"])
def test_q07_non_pass_af1_rejects(lineage, status):
    receipt = af1_with("BUDGET", status)
    af1.validate_af1_record(receipt)
    rejected(build(lineage, receipt=receipt), "AF1_NOT_PASS")


def test_q07_malformed_or_authority_invalid_af1_rejects(lineage):
    receipt = af1_pass()
    for case in (
        None,
        af1_mapping(),
        dataclasses.replace(receipt, overall_disposition="AF1_FAIL"),
        dataclasses.replace(receipt, no_qualification_authority=False),
        dataclasses.replace(receipt, advisory_only=False),
        dataclasses.replace(receipt, dimension_statuses=receipt.dimension_statuses[:-1]),
        dataclasses.replace(receipt, gate_receipt_id="af1gate:sha256:" + "0" * 64),
    ):
        rejected(build(lineage, receipt=case) if case is not None else q.build_qualification_candidate(
            lineage.snapshot, None, [manifest()], binary_input(lineage)), "AF1_RECEIPT_INVALID")


# ── Q08 provenance / cutoff ──────────────────────────────────────────────────
def test_q08_manifest_ids_sorted_unique_and_limitations_preserved(lineage):
    partial = manifest(output_hash="e" * 64, dq_flags=["PARTIALLY_OBSERVED", "SEQUENCE_GAP"],
                       replay_fidelity="PARTIAL", gap_summary="book gap 2025-10-02")
    base = manifest()
    record = ok(build(lineage, manifests=[partial, base, base]))
    assert record.research_provenance_manifest_ids == tuple(sorted(
        {partial.research_provenance_manifest_id, base.research_provenance_manifest_id}))
    # The packet binds manifests by id only: no field could upgrade a limitation.
    names = {field.name for field in dataclasses.fields(q.QualificationCandidate)}
    assert not names & {"dq_flags", "replay_fidelity", "gap_summary", "data_quality"}


def test_q08_manifest_cutoff_may_equal_candidate_cutoff(lineage):
    ok(build(lineage, manifests=[manifest(cutoff=CUTOFF)]))


def test_q08_provenance_rejections(lineage):
    good = manifest()
    for case in (
        [],
        "researchmanifest:sha256:" + "0" * 64,
        [af1_mapping()],
        [dataclasses.replace(good, dataset_refs=(DATASET_REF, "extra"))],
        [dataclasses.replace(good, research_provenance_manifest_id="researchmanifest:sha256:" + "0" * 64)],
        [manifest(dataset_refs=("datasetsnapshot:other",))],
    ):
        rejected(build(lineage, manifests=case), "PROVENANCE_INVALID")
    rejected(build(lineage, manifests=[good] * (q.MAX_QUALIFICATION_PROVENANCE_MANIFESTS + 1)),
             "LIMIT_EXCEEDED")


@pytest.mark.parametrize("cutoff", [
    "2026-09-26T00:00:00+00:00", "2026-09-26T00:00:00.100Z", "2026-09-26", "not-a-time",
    "2026-09-26T00:00:00.1234567Z",
])
def test_q08_candidate_cutoff_must_be_canonical_utc(lineage, cutoff):
    rejected(build(lineage, binary_input(lineage, information_cutoff=cutoff)), "CUTOFF_INVALID")


def test_q08_cutoff_ordering(lineage):
    rejected(build(lineage, manifests=[manifest(cutoff="2026-09-26T00:00:00.000000001Z")]), "CUTOFF_INVALID")
    rejected(build(lineage, manifests=[manifest(), manifest(cutoff="2026-09-27T00:00:00Z")]), "CUTOFF_INVALID")
    # Governing research_as_of (2026-09-20) may not follow the candidate cutoff.
    rejected(build(lineage, binary_input(lineage, information_cutoff="2026-09-19T00:00:00Z"),
                   manifests=[manifest(cutoff="2026-09-18T00:00:00Z")]), "CUTOFF_INVALID")


# ── Q09 – Q12 closed plan contracts ──────────────────────────────────────────
def plan_rejects(lin, key, plan, code, **over):
    rejected(build(lin, binary_input(lin, **{key: plan}, **over)), code)


@pytest.mark.parametrize("mutation", [
    {"human_review_state": "DRAFT"},
    {"human_review_state": "reviewed"},
    {"hypothesis_name": "has space"},
    {"hypothesis_version": ""},
    {"code_version": "x" * 513},
    {"falsifiable_claim": " padded"},
    {"cohort": "x" * 4097},
    {"target": 5},
    {"predecessor_candidate_ids": ["alphacandidate:sha256:" + "a" * 64]},
])
def test_q09_hypothesis_reviewed_contract(lineage, mutation):
    plan_rejects(lineage, "hypothesis_plan", hypothesis_plan(**mutation), "HYPOTHESIS_PLAN_INVALID")


def test_q09_hypothesis_missing_key_rejects(lineage):
    plan = hypothesis_plan()
    del plan["review_assertion"]
    plan_rejects(lineage, "hypothesis_plan", plan, "HYPOTHESIS_PLAN_INVALID")


def feature_case(**changes):
    plan = feature_plan()
    for key, value in changes.items():
        plan[key] = value
    return plan


@pytest.mark.parametrize("plan", [
    feature_case(feature_source_classes={PUBLIC_REF: "PUBLIC_NON_MARKET", TIME_REF: "TIME_ONLY"}),
    feature_case(feature_evidence_refs={PUBLIC_REF: ["e:1"], TIME_REF: ["e:2"], MARKET_REF: ["e:3"], "x": ["e:4"]}),
    feature_case(feature_source_classes={PUBLIC_REF: "WALLET", TIME_REF: "TIME_ONLY", MARKET_REF: "MARKET_PIT"}),
    feature_case(feature_evidence_refs={PUBLIC_REF: [], TIME_REF: ["e:2"], MARKET_REF: ["e:3"]}),
    feature_case(feature_evidence_refs={PUBLIC_REF: ["e:1", "e:1"], TIME_REF: ["e:2"], MARKET_REF: ["e:3"]}),
    feature_case(availability_rule="SOURCE_AVAILABILITY_TIME"),
    feature_case(no_future_information_rule="FEATURE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME"),
    feature_case(missing_data_policy=""),
    feature_case(feature_refs=[]),
    feature_case(feature_refs=[PUBLIC_REF, PUBLIC_REF, TIME_REF, MARKET_REF]),
    feature_case(feature_refs=["C:/features/x", TIME_REF, MARKET_REF]),
    feature_case(feature_definition_ids=["feature:sha256:" + "a" * 64]),
])
def test_q10_feature_plan_rejections(lineage, plan):
    plan_rejects(lineage, "feature_plan", plan, "FEATURE_PLAN_INVALID")


def test_q10_label_is_never_a_decision_time_feature(lineage):
    plan_rejects(lineage, "label_plan", label_plan(label_ref=PUBLIC_REF), "LABEL_PLAN_INVALID")


@pytest.mark.parametrize("mutation", [
    {"label_ref": "..\\labels\\x"},
    {"label_ref": ""},
    {"evidence_reference_ids": []},
    {"evidence_reference_ids": ["e:1", "e:1"]},
    {"censoring_rule": ""},
    {"outcome_source_rule": None},
    {"label_source_url": "https://example.test"},
])
def test_q11_label_plan_closed_schema(lineage, mutation):
    plan_rejects(lineage, "label_plan", label_plan(**mutation), "LABEL_PLAN_INVALID")


@pytest.mark.parametrize("mutation", [
    {"group_policy": "DECLARED_NO_ISOLATION"},
    {"group_policy": "INCLUSIVE"},
    {"event_grouping_rule": "LEAKAGE_ONLY"},
    {"selection_start": "2024-09-01T00:00:00Z"},
    {"oos_start": "2024-12-31T00:00:00Z"},
    {"end_time": "2025-09-01T00:00:00Z"},
    {"formation_start": "2024-09-01T00:00:00+00:00"},
    {"purge_rule": "NONE"},
    {"inclusion_policy": "DECISION_TIME_CLOSED"},
    {"embargo_seconds": -1},
    {"embargo_seconds": True},
    {"embargo_seconds": "0"},
    {"min_samples_per_role": 0},
    {"dataset_snapshot_reference_ids": []},
    {"oos_sample_ids": ["s1"]},
])
def test_q12_exclusive_grouping_and_ordered_boundaries(lineage, mutation):
    plan_rejects(lineage, "dataset_split_plan", split_plan(**mutation), "DATASET_SPLIT_PLAN_INVALID")


def test_q12_event_grouping_keys_are_existing_wp170_sample_keys():
    sample_fields = {field.name for field in dataclasses.fields(eo.ResearchSample)}
    assert set(q.SPLIT_EVENT_GROUPING_KEYS) <= sample_fields
    assert "EXCLUSIVE" in eo.GROUP_POLICIES
    compatible = set(split_plan()) - {"dataset_snapshot_reference_ids", "event_grouping_rule"}
    assert compatible == set(eo._SPLIT_KEYS) - {"split_plan_version"}


# ── Q13 / Q14 sample-power facts ─────────────────────────────────────────────
@pytest.mark.parametrize("available", [0, 199, 200, 10_000])
def test_q13_power_facts_never_self_qualify(lineage, available):
    record = ok(build(lineage, binary_input(lineage, sample_power_plan=power_plan(
        available_sample_count=available, available_independent_group_count=0))))
    assert json.loads(record.sample_power_plan_json)["available_sample_count"] == available
    assert record.no_qualification_authority is True
    names = {field.name for field in dataclasses.fields(q.QualificationCandidate)}
    assert not {name for name in names if "pass" in name or "decision" in name or "qualified" in name}
    assert set(q.QUALIFICATION_STATUSES) == {"QUALIFICATION_CANDIDATE_VALID", "QUALIFICATION_CANDIDATE_REJECTED"}


@pytest.mark.parametrize("mutation", [
    {"available_sample_count": -1},
    {"available_independent_group_count": True},
    {"required_sample_count": 0},
    {"required_independent_group_count": "60"},
    {"target_power": "0"},
    {"target_power": "1.5"},
    {"target_power": "0.80"},
    {"target_power": "-0"},
    {"significance_level": "1"},
    {"significance_level": "0"},
    {"minimum_detectable_effect": "0"},
    {"minimum_detectable_effect": "-0.01"},
    {"minimum_detectable_effect": "1e-2"},
    {"power_method": ""},
    {"power_analysis_reference_id": "/tmp/power.json"},
    {"passes_power": True},
])
def test_q14_power_invalid_domains_reject(lineage, mutation):
    plan_rejects(lineage, "sample_power_plan", power_plan(**mutation), "POWER_PLAN_INVALID")


def test_q14_power_boundary_values_accept(lineage):
    ok(build(lineage, binary_input(lineage, sample_power_plan=power_plan(target_power="1", significance_level="0.001"))))


# ── Q15 test family / WP170 compatibility ────────────────────────────────────
@pytest.mark.parametrize("mutation", [
    {"primary_metric_direction": "HIGHER_IS_BETTER"},
    {"acceptance_thresholds": {"primary_metric_operator": "GTE", "primary_metric_threshold": "0.24"}},
    {"acceptance_thresholds": {"primary_metric_operator": "LTE", "primary_metric_threshold": "abc"}},
    {"acceptance_thresholds": {"primary_metric_operator": "LTE"}},
    {"baseline_acceptance_rule": "CANDIDATE_GTE_BASELINE"},
    {"correction_policy": "SINGLETON"},
    {"correction_policy": "BONFERRONI"},
    {"family_size": 0},
    {"secondary_metric_names": ["BRIER_SCORE"]},
    {"secondary_metric_names": ["LOG_LOSS", "LOG_LOSS"]},
    {"multiplicity_method": ""},
])
def test_q15_test_family_rejections(lineage, mutation):
    code = "TEST_FAMILY_PLAN_INVALID"
    plan_rejects(lineage, "test_family_plan", family_plan(**mutation), code)


def test_q15_singleton_and_generic_higher_is_better(lineage):
    ok(build(lineage, binary_input(lineage, test_family_plan=family_plan(
        correction_policy="SINGLETON", family_size=1, secondary_metric_names=[]))))
    ok(build(lineage, generic_input(lineage)))


def test_q15_vocabulary_matches_current_wp170(lineage):
    record = ok(build(lineage))
    plan = json.loads(record.test_family_plan_json)
    assert plan["primary_metric_direction"] in eo.METRIC_DIRECTIONS
    assert plan["correction_policy"] in eo.CORRECTION_POLICIES
    assert set(q._BASELINE_RULE_FOR_DIRECTION.values()) == set(eo._BASELINE_ACCEPTANCE_RULES)
    # The frozen threshold mapping is exactly what WP170 preregistration accepts.
    assert eo._threshold_mapping(plan["acceptance_thresholds"], plan["primary_metric_direction"]) == \
        plan["acceptance_thresholds"]
    # Hypothesis plan + derived predecessor ids + creation provenance == AlphaHypothesis inputs.
    assert set(json.loads(record.hypothesis_plan_json)) | {"predecessor_candidate_ids", "creation_provenance"} == \
        set(eo._HYPOTHESIS_KEYS)
    assert record.experiment_os_schema_version == eo.EXPERIMENT_OS_SCHEMA_VERSION == "1.0.0"


# ── Q16 – Q21 forecast evaluation ────────────────────────────────────────────
def test_q16_generic_metric_exact_not_applicable(lineage):
    record = ok(build(lineage, generic_input(lineage)))
    assert record.forecast_evaluation_plan_json == '{"applicability":"NOT_APPLICABLE"}'
    for plan in (
        {"applicability": "REQUIRED"},
        {"applicability": "NOT_APPLICABLE", "b0_rule": "PIT_MARKET_PROBABILITY_V1"},
        {},
        forecast_plan(),
    ):
        rejected(build(lineage, generic_input(lineage, forecast_evaluation_plan=plan)), "FORECAST_PLAN_INVALID")


def test_q17_binary_probability_complete_b0_b1_b2(lineage):
    plan = json.loads(ok(build(lineage)).forecast_evaluation_plan_json)
    assert plan["b0_rule"] == "PIT_MARKET_PROBABILITY_V1"
    assert plan["b1_feature_refs"] == sorted([PUBLIC_REF, TIME_REF])
    assert plan["b2_market_added_feature_refs"] == [MARKET_REF]
    assert plan["b2_feature_refs"] == sorted([PUBLIC_REF, TIME_REF, MARKET_REF])
    assert all(plan[key] is True for key in q._FORECAST_REQUIRED_TRUE)
    rejected(build(lineage, binary_input(lineage, forecast_evaluation_plan={"applicability": "NOT_APPLICABLE"})),
             "FORECAST_PLAN_INVALID")


def forecast_rejects(lin, code="FORECAST_PLAN_INVALID", **mutation):
    rejected(build(lin, binary_input(lin, forecast_evaluation_plan=forecast_plan(**mutation))), code)


def test_q18_b1_rejects_market_pit_feature(lineage):
    forecast_rejects(lineage, b1_feature_refs=[MARKET_REF, PUBLIC_REF],
                     b2_feature_refs=[MARKET_REF, PUBLIC_REF, TIME_REF])
    forecast_rejects(lineage, b1_feature_refs=["feat.unknown", PUBLIC_REF],
                     b2_feature_refs=["feat.unknown", MARKET_REF, PUBLIC_REF])
    forecast_rejects(lineage, b1_feature_refs=[])


def test_q19_b2_is_exact_b1_plus_explicit_market_pit(lineage):
    forecast_rejects(lineage, b2_feature_refs=[MARKET_REF, PUBLIC_REF])
    forecast_rejects(lineage, b2_feature_refs=[MARKET_REF, PUBLIC_REF, TIME_REF, "feat.extra"])
    forecast_rejects(lineage, b2_market_added_feature_refs=[])
    forecast_rejects(lineage, b2_market_added_feature_refs=[PUBLIC_REF], b2_feature_refs=[PUBLIC_REF, TIME_REF])
    forecast_rejects(lineage, b2_market_added_feature_refs=[MARKET_REF, MARKET_REF])


@pytest.mark.parametrize("key", [
    "same_oos_membership_required", "b1_vs_b0_required", "b2_vs_b0_required",
    "b2_vs_b1_incrementality_required",
])
@pytest.mark.parametrize("value", [False, None, "true", 1])
def test_q20_comparison_booleans_mandatory(lineage, key, value):
    forecast_rejects(lineage, **{key: value})


def test_q20_proper_score_and_metric_binding(lineage):
    forecast_rejects(lineage, primary_proper_score="ACCURACY")
    forecast_rejects(lineage, primary_proper_score="LOG_LOSS")  # test family primary is BRIER_SCORE
    forecast_rejects(lineage, calibration_diagnostic="")
    forecast_rejects(lineage, b0_rule="WEBSITE_DISPLAYED_PROBABILITY")
    ok(build(lineage, binary_input(
        lineage, forecast_evaluation_plan=forecast_plan(primary_proper_score="LOG_LOSS"),
        test_family_plan=family_plan(primary_metric_name="LOG_LOSS", secondary_metric_names=["BRIER_SCORE"]),
    )))
    rejected(build(lineage, binary_input(lineage, test_family_plan=family_plan(
        primary_metric_name="hit-rate"))), "FORECAST_PLAN_INVALID")


@pytest.mark.parametrize("params", [
    {"max_midpoint_spread": "1.01", "max_last_trade_age_seconds": 900},
    {"max_midpoint_spread": "-0.1", "max_last_trade_age_seconds": 900},
    {"max_midpoint_spread": "0.050", "max_last_trade_age_seconds": 900},
    {"max_midpoint_spread": "0.05", "max_last_trade_age_seconds": -1},
    {"max_midpoint_spread": "0.05", "max_last_trade_age_seconds": "900"},
    {"max_midpoint_spread": "0.05"},
    {"max_midpoint_spread": "0.05", "max_last_trade_age_seconds": 900, "use_website_price": True},
])
def test_q21_b0_parameters_canonical_and_bounded(lineage, params):
    forecast_rejects(lineage, b0_parameters=params)


@pytest.mark.parametrize("params", [
    {"max_midpoint_spread": "0", "max_last_trade_age_seconds": 0},
    {"max_midpoint_spread": "1", "max_last_trade_age_seconds": 86400},
])
def test_q21_b0_parameter_bounds_inclusive(lineage, params):
    ok(build(lineage, binary_input(lineage, forecast_evaluation_plan=forecast_plan(b0_parameters=params))))


# ── Q22 execution feasibility ────────────────────────────────────────────────
def feasibility_case(**entries):
    plan = feasibility_plan()
    for key, value in entries.items():
        if value is None:
            del plan[key]
        else:
            plan[key] = value
    return plan


@pytest.mark.parametrize("plan", [
    feasibility_case(LATENCY=None),
    feasibility_case(EXPECTED_RETURN={"state": "MISSING", "evidence_reference_ids": []}),
    feasibility_case(FEES={"state": "AVAILABLE", "evidence_reference_ids": []}),
    feasibility_case(FEES={"state": "PARTIAL", "evidence_reference_ids": []}),
    feasibility_case(SPREAD_DEPTH={"state": "MISSING", "evidence_reference_ids": ["e:1"]}),
    feasibility_case(LATENCY={"state": "NOT_APPLICABLE", "evidence_reference_ids": ["e:1"]}),
    feasibility_case(FEES={"state": "SUFFICIENT", "evidence_reference_ids": ["e:1"]}),
    feasibility_case(FEES={"state": "AVAILABLE", "evidence_reference_ids": ["e:1"], "pnl": "0"}),
    feasibility_case(FEES={"state": "AVAILABLE"}),
])
def test_q22_execution_feasibility_classes_and_state_refs(lineage, plan):
    plan_rejects(lineage, "execution_feasibility_plan", plan, "EXECUTION_FEASIBILITY_INVALID")


def test_q22_feasibility_is_evidence_availability_only(lineage):
    plan = json.loads(ok(build(lineage)).execution_feasibility_plan_json)
    assert set(plan) == set(q.EXECUTION_FEASIBILITY_CLASSES)
    assert all(set(entry) == {"state", "evidence_reference_ids"} for entry in plan.values())


# ── Q23 wallet boundary ──────────────────────────────────────────────────────
def test_q23_wallet_dependent_requires_wallet_gate(lineage):
    rejected(build(lineage, binary_input(lineage, wallet_dependency="WALLET_DEPENDENT")), "WALLET_GATE_REQUIRED")
    # Fails closed before any other crossing: no wallet shortcut through valid inputs.
    rejected(q.build_qualification_candidate(None, None, None, binary_input(
        lineage, wallet_dependency="WALLET_DEPENDENT")), "WALLET_GATE_REQUIRED")
    rejected(build(lineage, binary_input(lineage, wallet_dependency="WALLET")), "FIELD_VALUE_INVALID")
    rejected(build(lineage, binary_input(lineage, wallet_dependency="WALLET_DEPENDENT",
                                         wallet_gate_receipt_id="walletgate:sha256:" + "a" * 64)),
             "FIELD_VALUE_INVALID")
    record = ok(build(lineage))
    rejected(q.validate_qualification_candidate(rehash(record, wallet_dependency="WALLET_DEPENDENT")),
             "WALLET_GATE_REQUIRED")


# ── Q24 authority invariants ─────────────────────────────────────────────────
@pytest.mark.parametrize("flag", [
    "advisory_only", "human_review_required", "no_execution_authority",
    "no_strategy_authority", "no_qualification_authority",
])
def test_q24_every_candidate_authority_flag_true(lineage, flag):
    record = ok(build(lineage))
    assert getattr(record, flag) is True
    rejected(q.validate_qualification_candidate(rehash(record, **{flag: False})), "AUTHORITY_INVARIANT_INVALID")
    rejected(q.validate_qualification_candidate(rehash(record, **{flag: 1})), "AUTHORITY_INVARIANT_INVALID")


def test_q24_result_authority_flags_always_true(lineage):
    for result in (build(lineage), build(lineage, {"bad": 1})):
        assert (result.advisory_only, result.no_execution_authority, result.no_strategy_authority,
                result.no_qualification_authority) == (True, True, True, True)


def test_q24_input_is_not_mutated(lineage):
    value = binary_input(lineage)
    before = copy.deepcopy(value)
    ok(build(lineage, value))
    assert value == before
