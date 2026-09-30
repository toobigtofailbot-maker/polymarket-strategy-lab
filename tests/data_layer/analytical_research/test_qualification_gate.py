"""S10-GATE-QUAL-01 deterministic qualification packet acceptance gate: focused oracles.

Deterministic SYNTHETIC fixtures only (synthetic Alpha lineages, synthetic
provenance manifests and S10-QUAL-01 synthetic candidate packets) plus the committed
canonical S10-GATE-AF1 receipt as a predecessor compatibility fixture. Every
QUAL_PASS / QUAL_FAIL / QUAL_INCONCLUSIVE below is a synthetic test-only outcome: no
real candidate is built, evaluated or qualified, no receipt is persisted, and no
network is touched.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from src.data_layer.analytical_research import alpha_factory_registry as afr
from src.data_layer.analytical_research import experiment_os as eo
from src.data_layer.analytical_research import qualification as q
from src.data_layer.analytical_research import qualification_gate as g
from tests.data_layer.analytical_research import test_qualification as tq
from tests.data_layer.analytical_research.test_qualification import (
    CANONICAL_AF1_RECEIPT_ID,
    MARKET_REF,
    PUBLIC_REF,
    TIME_REF,
    Lineage,
    af1_mapping,
    af1_pass,
    af1_with,
    binary_input,
    fabricated_append,
    feasibility_plan,
    fresh,
    generic_input,
    manifest,
    mk_candidate,
    mk_episode,
    mk_family,
    mk_source,
    power_plan,
    rehash,
    snapshot_of,
    with_plan,
)

FEATURE_EVIDENCE = ("evidence:weather-archive", "evidence:schedule", "evidence:pit-book",
                    "evidence:pit-trades")
LABEL_EVIDENCE = ("evidence:league-scores",)
POWER_EVIDENCE = ("evidence:power-analysis-v1",)
EXECUTION_EVIDENCE = ("evidence:fee-schedule", "evidence:rules", "evidence:tick")
ALL_EVIDENCE = FEATURE_EVIDENCE + LABEL_EVIDENCE + POWER_EVIDENCE + EXECUTION_EVIDENCE


# ── synthetic fixtures ───────────────────────────────────────────────────────
@pytest.fixture
def lineage(tmp_path):
    path = fresh(tmp_path)
    source, candidate, family = mk_source(), mk_candidate(), mk_family()
    episode = mk_episode(candidate, family, source)
    return Lineage(path, source, candidate, family, episode,
                   snapshot_of(path, [source, candidate, family, episode]))


def ready_manifest(refs=ALL_EVIDENCE, **over):
    return manifest(input_evidence_reference_ids=refs, **over)


def ready_power(**over):
    values = dict(available_sample_count=240, available_independent_group_count=80,
                  required_sample_count=200, required_independent_group_count=60)
    values.update(over)
    return power_plan(**values)


def ready_feasibility(**over):
    values = {"TICK_SIZE_MIN_ORDER": {"state": "AVAILABLE", "evidence_reference_ids": ["evidence:tick"]}}
    values.update(over)
    return feasibility_plan(**values)


def ready_input(lin, factory=binary_input, **over):
    values = dict(sample_power_plan=ready_power(), execution_feasibility_plan=ready_feasibility())
    values.update(over)
    return factory(lin, **values)


def candidate_for(lin, value=None, manifests=None, snapshot=None):
    result = q.build_qualification_candidate(
        lin.snapshot if snapshot is None else snapshot, af1_pass(),
        [ready_manifest()] if manifests is None else manifests,
        ready_input(lin) if value is None else value,
    )
    assert result.is_valid, result.error_codes
    return result.record


DEFAULT = object()


def gate(lin, candidate=DEFAULT, *, snapshot=DEFAULT, receipt=DEFAULT, manifests=DEFAULT):
    """Evaluate with synthetic ready defaults; an explicit None is passed through."""
    return g.evaluate_qualification_gate(
        candidate_for(lin) if candidate is DEFAULT else candidate,
        lin.snapshot if snapshot is DEFAULT else snapshot,
        af1_pass() if receipt is DEFAULT else receipt,
        [ready_manifest()] if manifests is DEFAULT else manifests,
    )


def admitted(result):
    assert result.is_valid, result.error_codes
    assert result.status == "QUALIFICATION_GATE_VALID"
    assert result.error_codes == ()
    return result.receipt


def rejected(result, code):
    assert not result.is_valid
    assert result.status == "QUALIFICATION_GATE_REJECTED"
    assert result.error_codes == (code,)
    # Structural rejection never manufactures a substantive disposition.
    assert result.receipt is None
    assert "QUAL_" not in repr(result)


def dims(receipt):
    return dict(receipt.dimension_statuses)


def regate(receipt, **changes):
    """Directly construct a changed receipt with a self-consistent identity."""
    draft = dataclasses.replace(receipt, **changes)
    return dataclasses.replace(draft, qualification_gate_receipt_id=g._digest(g._preimage(draft)))


# ── Q01 / Q02 identity and mapping roundtrip ─────────────────────────────────
def test_q01_receipt_identity_deterministic_and_exact_roundtrip(lineage):
    first, second = admitted(gate(lineage)), admitted(gate(lineage))
    assert first == second
    assert first.qualification_gate_receipt_id.startswith("qualificationgate:sha256:")
    assert len(first.qualification_gate_receipt_id.split(":")[-1]) == 64
    mapping = g.qualification_gate_receipt_to_mapping(first)
    assert list(mapping) == [f.name for f in dataclasses.fields(g.QualificationGateReceipt)]
    assert list(mapping["dimension_statuses"]) == list(g.QUALIFICATION_GATE_DIMENSIONS)
    assert isinstance(mapping["research_provenance_manifest_ids"], list)
    assert admitted(g.qualification_gate_receipt_from_mapping(json.loads(json.dumps(mapping)))) == first
    assert admitted(g.validate_qualification_gate_receipt(first)) is first
    # Caller mapping order of dimensions cannot alter canonical identity.
    reordered = dict(mapping, dimension_statuses=dict(reversed(list(mapping["dimension_statuses"].items()))))
    assert admitted(g.qualification_gate_receipt_from_mapping(reordered)) == first


@pytest.mark.parametrize("field,value", [
    ("candidate_version", "qual-v2"),
    ("candidate_information_cutoff", "2026-09-25T00:00:00Z"),
    ("current_alpha_registry_head_entry_hash", "alpharegistryentry:sha256:" + "1" * 64),
    ("af1_gate_receipt_id", "af1gate:sha256:" + "2" * 64),
    ("research_provenance_manifest_ids", ("researchmanifest:sha256:" + "3" * 64,)),
    ("qualification_candidate_id", "qualificationcandidate:sha256:" + "4" * 64),
])
def test_q02_included_field_mutation_changes_identity(lineage, field, value):
    receipt = admitted(gate(lineage))
    changed = regate(receipt, **{field: value})
    assert changed.qualification_gate_receipt_id != receipt.qualification_gate_receipt_id
    assert admitted(g.validate_qualification_gate_receipt(changed)) == changed
    # The same mutation without a re-derived identity is detected.
    rejected(g.validate_qualification_gate_receipt(dataclasses.replace(receipt, **{field: value})),
             "IDENTITY_DERIVATION_MISMATCH")


def test_q02_disposition_is_bound_into_identity(lineage):
    passing = admitted(gate(lineage))
    inconclusive = admitted(gate(lineage, candidate_for(lineage, ready_input(
        lineage, sample_power_plan=power_plan()))))
    assert passing.overall_disposition == "QUAL_PASS"
    assert inconclusive.overall_disposition == "QUAL_INCONCLUSIVE"
    assert passing.qualification_gate_receipt_id != inconclusive.qualification_gate_receipt_id


# ── Q03 closed mapping / forgery ─────────────────────────────────────────────
def test_q03_malformed_mappings_fail_closed(lineage):
    mapping = g.qualification_gate_receipt_to_mapping(admitted(gate(lineage)))
    dims_mapping = mapping["dimension_statuses"]
    cases = [
        (None, "FIELD_TYPE_INVALID"),
        ([("schema_id", mapping["schema_id"])], "FIELD_TYPE_INVALID"),
        (dict(mapping, unknown_field=1), "FIELD_VALUE_INVALID"),
        ({k: v for k, v in mapping.items() if k != "policy_version"}, "FIELD_VALUE_INVALID"),
        (dict(mapping, wp170_entry_eligible=1.0), "FIELD_TYPE_INVALID"),
        (dict(mapping, dimension_statuses=dict(dims_mapping, PACKET_INTEGRITY=1.5)), "FIELD_TYPE_INVALID"),
        (dict(mapping, wp170_entry_eligible=1), "FIELD_TYPE_INVALID"),
        (dict(mapping, research_provenance_manifest_ids=tuple(mapping["research_provenance_manifest_ids"])),
         "FIELD_TYPE_INVALID"),
        (dict(mapping, dimension_statuses=list(dims_mapping.items())), "FIELD_TYPE_INVALID"),
        (dict(mapping, dimension_statuses={k: v for k, v in dims_mapping.items() if k != "AUTHORITY_CONTAINMENT"}),
         "FIELD_VALUE_INVALID"),
        (dict(mapping, dimension_statuses=dict(dims_mapping, EXTRA="PASS")), "FIELD_VALUE_INVALID"),
        (dict(mapping, dimension_statuses=dict(dims_mapping, SAMPLE_POWER_READINESS="MAYBE")), "FIELD_VALUE_INVALID"),
        (dict(mapping, overall_disposition="QUAL_FAIL"), "FIELD_VALUE_INVALID"),
        (dict(mapping, wp170_entry_eligible=False), "FIELD_VALUE_INVALID"),
        (dict(mapping, schema_version="2.0.0"), "SCHEMA_UNSUPPORTED"),
        (dict(mapping, policy_version="qualification-gate-policy/9.9.9"), "SCHEMA_UNSUPPORTED"),
        (dict(mapping, no_live_authority=False), "AUTHORITY_INVARIANT_INVALID"),
        (dict(mapping, research_provenance_manifest_ids=[]), "FIELD_VALUE_INVALID"),
        (dict(mapping, candidate_information_cutoff="2026-09-26T00:00:00+00:00"), "FIELD_VALUE_INVALID"),
        (dict(mapping, qualification_gate_receipt_id="qualificationgate:sha256:" + "0" * 64),
         "IDENTITY_DERIVATION_MISMATCH"),
    ]
    for value, code in cases:
        rejected(g.qualification_gate_receipt_from_mapping(value), code)


def test_q03_self_consistent_rehash_forgeries_reject(lineage):
    passing = admitted(gate(lineage))
    inconclusive = admitted(gate(lineage, candidate_for(lineage, ready_input(
        lineage, sample_power_plan=power_plan()))))
    statuses = dict(passing.dimension_statuses)

    def with_dims(**over):
        return tuple((name, over.get(name, statuses[name])) for name in g.QUALIFICATION_GATE_DIMENSIONS)

    forgeries = [
        # Caller-supplied disposition / eligibility contradicting the dimensions.
        (regate(inconclusive, overall_disposition="QUAL_PASS", wp170_entry_eligible=True), "FIELD_VALUE_INVALID"),
        (regate(inconclusive, wp170_entry_eligible=True), "FIELD_VALUE_INVALID"),
        (regate(passing, wp170_entry_eligible=False), "FIELD_VALUE_INVALID"),
        (regate(passing, wp170_entry_eligible=1), "FIELD_TYPE_INVALID"),
        # Dimensions that can never appear in an emitted receipt.
        (regate(passing, dimension_statuses=with_dims(PACKET_INTEGRITY="FAIL"),
                overall_disposition="QUAL_FAIL", wp170_entry_eligible=False), "FIELD_VALUE_INVALID"),
        (regate(passing, dimension_statuses=with_dims(PIT_PROVENANCE_READINESS="FAIL"),
                overall_disposition="QUAL_FAIL", wp170_entry_eligible=False), "FIELD_VALUE_INVALID"),
        (regate(passing, dimension_statuses=with_dims(CURRENT_RESEARCH_LINEAGE="INCONCLUSIVE"),
                overall_disposition="QUAL_INCONCLUSIVE", wp170_entry_eligible=False), "FIELD_VALUE_INVALID"),
        (regate(passing, dimension_statuses=passing.dimension_statuses[::-1]), "FIELD_VALUE_INVALID"),
        (regate(passing, dimension_statuses=passing.dimension_statuses[:-1]), "FIELD_VALUE_INVALID"),
        (regate(passing, dimension_statuses=list(passing.dimension_statuses)), "FIELD_TYPE_INVALID"),
        # Authority broadening and schema drift.
        (regate(passing, no_gate_c_authority=False), "AUTHORITY_INVARIANT_INVALID"),
        (regate(passing, successor_authorization_required=False), "AUTHORITY_INVARIANT_INVALID"),
        (regate(passing, experiment_os_schema_version="9.9.9"), "SCHEMA_UNSUPPORTED"),
        (regate(passing, schema_id="polymarket-qualification-candidate"), "SCHEMA_UNSUPPORTED"),
        (regate(passing, alpha_candidate_id="alphafamily:sha256:" + "0" * 64), "FIELD_VALUE_INVALID"),
        (regate(passing, research_provenance_manifest_ids=list(passing.research_provenance_manifest_ids)),
         "FIELD_TYPE_INVALID"),
        (object(), "FIELD_TYPE_INVALID"),
    ]
    for record, code in forgeries:
        rejected(g.validate_qualification_gate_receipt(record), code)
    with pytest.raises(ValueError) as caught:
        g.qualification_gate_receipt_to_mapping(object())
    assert caught.value.args == ("FIELD_TYPE_INVALID",)


# ── Q04 candidate structural admission ───────────────────────────────────────
def test_q04_invalid_or_tampered_candidate_is_structural_rejection(lineage):
    record = candidate_for(lineage)
    cases = [
        (dataclasses.replace(record, creation_provenance="tampered"), "CANDIDATE_INVALID"),
        (rehash(record, wallet_dependency="WALLET_DEPENDENT"), "CANDIDATE_INVALID"),
        (rehash(record, experiment_os_schema_version="9.9.9"), "CANDIDATE_INVALID"),
        (with_plan(record, "sample_power_plan", lambda plan: plan.update(target_power="1.5")),
         "CANDIDATE_INVALID"),
        (q.qualification_candidate_to_mapping(record), "CANDIDATE_INVALID"),
        (object(), "CANDIDATE_INVALID"),
        (None, "CANDIDATE_INVALID"),
        (rehash(record, no_qualification_authority=False), "AUTHORITY_INVARIANT_INVALID"),
        (rehash(record, advisory_only=False), "AUTHORITY_INVARIANT_INVALID"),
    ]
    for value, code in cases:
        rejected(gate(lineage, value), code)


# ── Q05 / Q06 / Q07 append-only ancestry ─────────────────────────────────────
def test_q05_candidate_head_equal_current_head_is_valid_ancestry(lineage):
    receipt = admitted(gate(lineage))
    assert receipt.candidate_alpha_registry_head_entry_hash == lineage.snapshot.head_entry_hash
    assert receipt.current_alpha_registry_head_entry_hash == lineage.snapshot.head_entry_hash
    assert dims(receipt)["CURRENT_RESEARCH_LINEAGE"] == "PASS"


def test_q06_unrelated_alpha_append_keeps_older_head_as_valid_ancestor(lineage):
    record = candidate_for(lineage)
    other_candidate = mk_candidate(scope="nba-2026", mechanism="rest-days", subject="nba")
    other_family = mk_family(mechanism="rest-days")
    other_episode = mk_episode(other_candidate, other_family, lineage.source)
    current = snapshot_of(lineage.path, [other_candidate, other_family, other_episode])
    assert current.head_entry_hash != record.alpha_registry_head_entry_hash
    receipt = admitted(gate(lineage, record, snapshot=current))
    assert receipt.candidate_alpha_registry_head_entry_hash == lineage.snapshot.head_entry_hash
    assert receipt.current_alpha_registry_head_entry_hash == current.head_entry_hash
    assert dims(receipt)["CURRENT_RESEARCH_LINEAGE"] == "PASS"
    assert receipt.overall_disposition == "QUAL_PASS"


def test_q07_missing_or_non_ancestor_candidate_head_rejects(lineage, tmp_path):
    record = candidate_for(lineage)
    cases = [
        rehash(record, alpha_registry_head_entry_hash="alpharegistryentry:sha256:" + "0" * 64),
        # A real chain entry that predates the governing episode: history incompatible.
        rehash(record, alpha_registry_head_entry_hash=lineage.snapshot.entries[2].entry_hash),
        # Governing episode research_as_of after the candidate cutoff.
        rehash(record, information_cutoff="2026-09-19T00:00:00Z"),
    ]
    for value in cases:
        rejected(gate(lineage, value), "ALPHA_ANCESTRY_INVALID")
    # A candidate built on a different registry history is not an ancestor of this one.
    other_path = fresh(tmp_path, "other.sqlite3")
    unrelated = mk_family(mechanism="unrelated-first")
    other = snapshot_of(other_path, [unrelated, lineage.source, lineage.candidate, lineage.family,
                                     lineage.episode])
    foreign = candidate_for(lineage, snapshot=other)
    rejected(gate(lineage, foreign), "ALPHA_ANCESTRY_INVALID")
    admitted(gate(lineage, foreign, snapshot=other))


def test_q07_broken_or_fabricated_snapshot_is_registry_rejection(lineage, tmp_path):
    snap = lineage.snapshot
    empty = afr.initialize_alpha_factory_registry(str(tmp_path / "empty.sqlite3")).snapshot
    last = snap.entries[-1]
    successor = mk_episode(lineage.candidate, lineage.family, lineage.source,
                           predecessor=lineage.episode.research_episode_id, scope={"league": "nfl", "v": "2"})
    cases = [
        None,
        {"entries": []},
        empty,
        dataclasses.replace(snap, total_rows=snap.total_rows + 1),
        dataclasses.replace(snap, total_payload_bytes=snap.total_payload_bytes + 1),
        dataclasses.replace(snap, head_entry_hash=None),
        dataclasses.replace(snap, head_entry_hash="alpharegistryentry:sha256:" + "0" * 64),
        dataclasses.replace(snap, entries=snap.entries[::-1]),
        dataclasses.replace(snap, entries=list(snap.entries)),
        dataclasses.replace(snap, schema_version="9.9.9"),
        dataclasses.replace(snap, entries=(*snap.entries[:-1], dataclasses.replace(
            last, record=dataclasses.replace(lineage.episode, thesis="tampered")))),
        dataclasses.replace(snap, entries=(*snap.entries[:-1], dataclasses.replace(
            last, entry_hash="alpharegistryentry:sha256:" + "0" * 64)),
            head_entry_hash="alpharegistryentry:sha256:" + "0" * 64),
        dataclasses.replace(snap, entries=(*snap.entries[:-1], dataclasses.replace(last, payload_sha256="0" * 64))),
        # Fabricated (unhashed) append after the candidate head.
        fabricated_append(snap, successor),
    ]
    for case in cases:
        rejected(gate(lineage, snapshot=case), "ALPHA_REGISTRY_INVALID")
    for flag in ("advisory_only", "no_qualification_authority"):
        rejected(gate(lineage, snapshot=dataclasses.replace(snap, **{flag: False})),
                 "AUTHORITY_INVARIANT_INVALID")


# ── Q08 / Q09 / Q10 current research lineage ─────────────────────────────────
def test_q08_later_same_lineage_supportive_episode_fails_current_lineage(lineage):
    record = candidate_for(lineage)
    successor = mk_episode(lineage.candidate, lineage.family, lineage.source,
                           predecessor=lineage.episode.research_episode_id, scope={"league": "nfl", "v": "2"})
    current = snapshot_of(lineage.path, [successor])
    receipt = admitted(gate(lineage, record, snapshot=current))
    assert dims(receipt)["CURRENT_RESEARCH_LINEAGE"] == "FAIL"
    assert receipt.overall_disposition == "QUAL_FAIL"
    assert receipt.wp170_entry_eligible is False


@pytest.mark.parametrize("state", [
    "NO_EDGE_CURRENTLY", "HYPOTHESIS_FALSIFIED", "DATA_INSUFFICIENT", "EXECUTION_UNECONOMIC",
    "WATCH_FOR_CHANGE", "RESEARCH_STALE", "MECHANISM_FAMILY_EXHAUSTED",
])
def test_q09_non_supportive_current_leaf_fails_current_lineage(lineage, state):
    record = candidate_for(lineage)
    successor = mk_episode(lineage.candidate, lineage.family, lineage.source, state=state,
                           predecessor=lineage.episode.research_episode_id)
    receipt = admitted(gate(lineage, record, snapshot=snapshot_of(lineage.path, [successor])))
    assert dims(receipt)["CURRENT_RESEARCH_LINEAGE"] == "FAIL"
    assert receipt.overall_disposition == "QUAL_FAIL"


def test_q10_ambiguous_multiple_current_leaves_fail_current_lineage(lineage):
    record = candidate_for(lineage)
    twin = mk_episode(lineage.candidate, lineage.family, lineage.source, scope={"league": "nfl", "twin": "1"})
    receipt = admitted(gate(lineage, record, snapshot=snapshot_of(lineage.path, [twin])))
    assert dims(receipt)["CURRENT_RESEARCH_LINEAGE"] == "FAIL"
    assert receipt.overall_disposition == "QUAL_FAIL"


# ── Q11 / Q12 AF1 predecessor rebinding ──────────────────────────────────────
def test_q11_exact_bound_final_af1_pass_is_predecessor_pass(lineage):
    receipt = admitted(gate(lineage))
    assert receipt.af1_gate_receipt_id == CANONICAL_AF1_RECEIPT_ID
    assert dims(receipt)["PREDECESSOR_EVIDENCE"] == "PASS"
    assert af1_pass().evidence_state == "FINALIZED"


def test_q12_wrong_malformed_or_non_pass_af1_is_structural_rejection(lineage):
    receipt = af1_pass()
    record = candidate_for(lineage)
    cases = [
        (None, "AF1_RECEIPT_INVALID"),
        (af1_mapping(), "AF1_RECEIPT_INVALID"),
        (af1_with("BUDGET", "FAIL"), "AF1_RECEIPT_INVALID"),
        (af1_with("PIT_PROVENANCE", "INCONCLUSIVE"), "AF1_RECEIPT_INVALID"),
        (dataclasses.replace(receipt, overall_disposition="AF1_FAIL"), "AF1_RECEIPT_INVALID"),
        (dataclasses.replace(receipt, evidence_state="BLIND_REVIEW_REQUIRED"), "AF1_RECEIPT_INVALID"),
        (dataclasses.replace(receipt, dimension_statuses=receipt.dimension_statuses[:-1]), "AF1_RECEIPT_INVALID"),
        (dataclasses.replace(receipt, gate_receipt_id="af1gate:sha256:" + "0" * 64), "AF1_RECEIPT_INVALID"),
        (dataclasses.replace(receipt, no_qualification_authority=False), "AUTHORITY_INVARIANT_INVALID"),
        (dataclasses.replace(receipt, advisory_only=False), "AUTHORITY_INVARIANT_INVALID"),
    ]
    for value, code in cases:
        rejected(gate(lineage, record, receipt=value), code)
    # A valid AF1_PASS receipt that is not the one bound by the candidate.
    unbound = rehash(record, af1_gate_receipt_id="af1gate:sha256:" + "0" * 64)
    rejected(gate(lineage, unbound), "AF1_BINDING_INVALID")


# ── Q13 provenance structural binding ────────────────────────────────────────
def test_q13_provenance_exact_set_cutoff_and_dataset_rebinding(lineage):
    first = ready_manifest()
    second = ready_manifest(refs=("evidence:extra",), output_identity="output:second")
    pair = candidate_for(lineage, manifests=[first, second])
    admitted(gate(lineage, pair, manifests=[second, first]))
    single = candidate_for(lineage)
    good = ready_manifest()
    binding = [
        (pair, [first]),
        (single, [first, second]),
        (single, [good, good]),
        (single, [second]),
    ]
    for record, manifests in binding:
        rejected(gate(lineage, record, manifests=manifests), "PROVENANCE_BINDING_INVALID")
    # Manifest cutoff after the candidate cutoff (candidate re-derived with an earlier cutoff).
    rejected(gate(lineage, rehash(single, information_cutoff="2026-09-24T00:00:00Z")),
             "PROVENANCE_BINDING_INVALID")
    # A split dataset ref not covered by the bound manifests.
    uncovered = with_plan(single, "dataset_split_plan",
                          lambda plan: plan.update(dataset_snapshot_reference_ids=["datasetsnapshot:other"]))
    rejected(gate(lineage, uncovered), "PROVENANCE_BINDING_INVALID")
    invalid = [
        None, "manifest", [], [object()], [dataclasses.asdict(good)],
        [dataclasses.replace(good, dataset_refs=(*good.dataset_refs, "extra"))],
        [dataclasses.replace(good, research_provenance_manifest_id="researchmanifest:sha256:" + "0" * 64)],
    ]
    for manifests in invalid:
        rejected(gate(lineage, single, manifests=manifests), "PROVENANCE_INVALID")
    rejected(gate(lineage, single, manifests=[good] * 257), "LIMIT_EXCEEDED")


# ── Q14 / Q15 PIT provenance readiness ───────────────────────────────────────
@pytest.mark.parametrize("over", [
    {"dq_flags": ("STALE",)},
    {"dq_flags": ("MISSING", "SEQUENCE_GAP")},
    {"replay_fidelity": "PARTIAL"},
    {"replay_fidelity": "UNREPLAYABLE"},
    {"gap_summary": "two hours of book data unavailable"},
])
def test_q14_provenance_limitations_are_inconclusive(lineage, over):
    limited = ready_manifest(**over)
    receipt = admitted(gate(lineage, candidate_for(lineage, manifests=[limited]), manifests=[limited]))
    assert dims(receipt)["PIT_PROVENANCE_READINESS"] == "INCONCLUSIVE"
    assert receipt.overall_disposition == "QUAL_INCONCLUSIVE"
    assert receipt.wp170_entry_eligible is False


@pytest.mark.parametrize("replay", ["EXACT", "FAITHFUL"])
def test_q14_exact_or_faithful_replay_is_ready(lineage, replay):
    ready = ready_manifest(replay_fidelity=replay)
    receipt = admitted(gate(lineage, candidate_for(lineage, manifests=[ready]), manifests=[ready]))
    assert dims(receipt)["PIT_PROVENANCE_READINESS"] == "PASS"


@pytest.mark.parametrize("missing", [
    FEATURE_EVIDENCE[0], FEATURE_EVIDENCE[3], LABEL_EVIDENCE[0], POWER_EVIDENCE[0], EXECUTION_EVIDENCE[2],
])
def test_q15_every_declared_evidence_ref_must_be_provenance_bound(lineage, missing):
    partial = ready_manifest(refs=tuple(ref for ref in ALL_EVIDENCE if ref != missing))
    receipt = admitted(gate(lineage, candidate_for(lineage, manifests=[partial]), manifests=[partial]))
    assert dims(receipt)["PIT_PROVENANCE_READINESS"] == "INCONCLUSIVE"
    assert receipt.overall_disposition == "QUAL_INCONCLUSIVE"


def test_q15_noncritical_execution_refs_and_manifest_union_count(lineage):
    spread = {"state": "PARTIAL", "evidence_reference_ids": ["evidence:spread"]}
    value = ready_input(lineage, execution_feasibility_plan=ready_feasibility(SPREAD_DEPTH=spread))
    unbound = admitted(gate(lineage, candidate_for(lineage, value)))
    assert dims(unbound)["PIT_PROVENANCE_READINESS"] == "INCONCLUSIVE"
    assert dims(unbound)["EXECUTION_EVIDENCE_READINESS"] == "PASS"
    # Refs split across two manifests are bound through their union.
    first = ready_manifest(refs=ALL_EVIDENCE[:4])
    second = ready_manifest(refs=(*ALL_EVIDENCE[4:], "evidence:spread"), output_identity="output:second")
    union = admitted(gate(lineage, candidate_for(lineage, value, manifests=[first, second]),
                          manifests=[first, second]))
    assert dims(union)["PIT_PROVENANCE_READINESS"] == "PASS"
    assert union.overall_disposition == "QUAL_PASS"


# ── Q16 / Q17 sample / power readiness ───────────────────────────────────────
@pytest.mark.parametrize("over", [
    {},
    {"available_sample_count": 200, "available_independent_group_count": 60},
])
def test_q16_sufficient_declared_counts_pass(lineage, over):
    value = ready_input(lineage, sample_power_plan=ready_power(**over))
    receipt = admitted(gate(lineage, candidate_for(lineage, value)))
    assert dims(receipt)["SAMPLE_POWER_READINESS"] == "PASS"


def test_q16_three_role_boundary_equality_passes(lineage):
    value = ready_input(lineage, sample_power_plan=ready_power(available_sample_count=240, required_sample_count=90),
                        dataset_split_plan=dict(json.loads(candidate_for(lineage).dataset_split_plan_json),
                                                min_samples_per_role=80))
    receipt = admitted(gate(lineage, candidate_for(lineage, value)))
    assert dims(receipt)["SAMPLE_POWER_READINESS"] == "PASS"


@pytest.mark.parametrize("power,per_role", [
    ({"available_sample_count": 199}, 30),
    ({"available_independent_group_count": 59}, 30),
    ({"available_sample_count": 0, "available_independent_group_count": 0}, 30),
    ({}, 81),
])
def test_q17_any_shortfall_is_inconclusive_never_structural(lineage, power, per_role):
    split = dict(json.loads(candidate_for(lineage).dataset_split_plan_json), min_samples_per_role=per_role)
    value = ready_input(lineage, sample_power_plan=ready_power(**power), dataset_split_plan=split)
    receipt = admitted(gate(lineage, candidate_for(lineage, value)))
    assert dims(receipt)["SAMPLE_POWER_READINESS"] == "INCONCLUSIVE"
    assert receipt.overall_disposition == "QUAL_INCONCLUSIVE"
    assert receipt.wp170_entry_eligible is False


# ── Q18 / Q19 WP170 crossing readiness ───────────────────────────────────────
@pytest.mark.parametrize("factory", [binary_input, generic_input])
def test_q18_valid_binary_and_generic_packets_are_crossing_ready(lineage, factory):
    record = candidate_for(lineage, ready_input(lineage, factory))
    receipt = admitted(gate(lineage, record))
    assert dims(receipt)["WP170_CROSSING_READINESS"] == "PASS"
    assert receipt.experiment_os_schema_version == eo.EXPERIMENT_OS_SCHEMA_VERSION
    assert receipt.overall_disposition == "QUAL_PASS"
    # The gate never rewrites plan semantics.
    assert q.validate_qualification_candidate(record).record is record


def test_q19_gate_does_not_claim_wp170_can_encode_public_non_market_b1(lineage):
    record = candidate_for(lineage)
    forecast = json.loads(record.forecast_evaluation_plan_json)
    classes = json.loads(record.feature_plan_json)["feature_source_classes"]
    assert forecast["b1_feature_refs"] == sorted([PUBLIC_REF, TIME_REF])
    assert classes[PUBLIC_REF] == "PUBLIC_NON_MARKET" and classes[MARKET_REF] == "MARKET_PIT"
    # Current WP170 feature sources are market-observation fields only; B1 refs are not among them.
    assert all(dep.startswith("market_observation.") for dep in eo.SAFE_FEATURE_SOURCE_DEPENDENCIES)
    assert not set(forecast["b1_feature_refs"]) & set(eo.SAFE_FEATURE_SOURCE_DEPENDENCIES)
    receipt = admitted(gate(lineage, record))
    assert dims(receipt)["WP170_CROSSING_READINESS"] == "PASS"
    mapping = g.qualification_gate_receipt_to_mapping(receipt)
    assert not any("feature_definition" in key for key in mapping)


# ── Q20 / Q21 / Q22 execution-evidence foundation ────────────────────────────
def test_q20_critical_execution_foundation_available_and_bound_passes(lineage):
    receipt = admitted(gate(lineage))
    assert dims(receipt)["EXECUTION_EVIDENCE_READINESS"] == "PASS"


@pytest.mark.parametrize("name", ["FEES", "RESOLUTION_RULES", "TICK_SIZE_MIN_ORDER"])
@pytest.mark.parametrize("state", ["PARTIAL", "MISSING", "NOT_APPLICABLE"])
def test_q21_critical_execution_gap_is_inconclusive(lineage, name, state):
    refs = ["evidence:critical-partial"] if state == "PARTIAL" else []
    value = ready_input(lineage, execution_feasibility_plan=ready_feasibility(
        **{name: {"state": state, "evidence_reference_ids": refs}}))
    bound = ready_manifest(refs=(*ALL_EVIDENCE, "evidence:critical-partial"))
    receipt = admitted(gate(lineage, candidate_for(lineage, value, manifests=[bound]), manifests=[bound]))
    assert dims(receipt)["EXECUTION_EVIDENCE_READINESS"] == "INCONCLUSIVE"
    assert dims(receipt)["PIT_PROVENANCE_READINESS"] == "PASS"
    assert receipt.overall_disposition == "QUAL_INCONCLUSIVE"


def test_q21_available_but_unbound_critical_ref_is_inconclusive(lineage):
    value = ready_input(lineage, execution_feasibility_plan=ready_feasibility(
        FEES={"state": "AVAILABLE", "evidence_reference_ids": ["evidence:unbound-fees"]}))
    receipt = admitted(gate(lineage, candidate_for(lineage, value)))
    assert dims(receipt)["EXECUTION_EVIDENCE_READINESS"] == "INCONCLUSIVE"


@pytest.mark.parametrize("state", ["MISSING", "NOT_APPLICABLE", "PARTIAL"])
def test_q22_noncritical_execution_gaps_do_not_block_gate_pass(lineage, state):
    refs = ["evidence:noncritical"] if state == "PARTIAL" else []
    entry = {"state": state, "evidence_reference_ids": refs}
    value = ready_input(lineage, execution_feasibility_plan=ready_feasibility(
        SPREAD_DEPTH=entry, LATENCY=entry, PARTIAL_FILL=entry))
    bound = ready_manifest(refs=(*ALL_EVIDENCE, "evidence:noncritical"))
    receipt = admitted(gate(lineage, candidate_for(lineage, value, manifests=[bound]), manifests=[bound]))
    assert dims(receipt)["EXECUTION_EVIDENCE_READINESS"] == "PASS"
    assert receipt.overall_disposition == "QUAL_PASS"


# ── Q23 .. Q27 aggregation and authority ─────────────────────────────────────
def test_q23_fail_overrides_simultaneous_inconclusive(lineage):
    record = candidate_for(lineage, ready_input(lineage, sample_power_plan=power_plan()))
    successor = mk_episode(lineage.candidate, lineage.family, lineage.source, state="HYPOTHESIS_FALSIFIED",
                           predecessor=lineage.episode.research_episode_id)
    receipt = admitted(gate(lineage, record, snapshot=snapshot_of(lineage.path, [successor])))
    assert dims(receipt)["CURRENT_RESEARCH_LINEAGE"] == "FAIL"
    assert dims(receipt)["SAMPLE_POWER_READINESS"] == "INCONCLUSIVE"
    assert receipt.overall_disposition == "QUAL_FAIL"
    assert receipt.wp170_entry_eligible is False


def test_q24_no_fail_with_inconclusive_is_inconclusive(lineage):
    # The unmodified S10-QUAL-01 packet fixture declares a sample shortfall, a PARTIAL
    # tick-size class and evidence refs no manifest binds.
    record = candidate_for(lineage, binary_input(lineage), manifests=[manifest()])
    receipt = admitted(gate(lineage, record, manifests=[manifest()]))
    assert "FAIL" not in dims(receipt).values()
    assert dims(receipt)["PIT_PROVENANCE_READINESS"] == "INCONCLUSIVE"
    assert dims(receipt)["SAMPLE_POWER_READINESS"] == "INCONCLUSIVE"
    assert dims(receipt)["EXECUTION_EVIDENCE_READINESS"] == "INCONCLUSIVE"
    assert receipt.overall_disposition == "QUAL_INCONCLUSIVE"
    assert receipt.wp170_entry_eligible is False


def test_q25_all_eight_pass_is_synthetic_qual_pass(lineage):
    receipt = admitted(gate(lineage))
    assert [name for name, _status in receipt.dimension_statuses] == list(g.QUALIFICATION_GATE_DIMENSIONS)
    assert set(dims(receipt).values()) == {"PASS"}
    assert receipt.overall_disposition == "QUAL_PASS"
    assert receipt.wp170_entry_eligible is True


@pytest.mark.parametrize("statuses,expected", [
    ((), "QUAL_PASS"),
    (("INCONCLUSIVE",), "QUAL_INCONCLUSIVE"),
    (("FAIL",), "QUAL_FAIL"),
    (("INCONCLUSIVE", "FAIL"), "QUAL_FAIL"),
    (("FAIL", "INCONCLUSIVE", "INCONCLUSIVE"), "QUAL_FAIL"),
])
def test_q26_aggregation_precedence_and_eligibility(statuses, expected):
    names = ("CURRENT_RESEARCH_LINEAGE", "PIT_PROVENANCE_READINESS", "SAMPLE_POWER_READINESS")
    table = dict.fromkeys(g.QUALIFICATION_GATE_DIMENSIONS, "PASS")
    table.update(zip(names, statuses))
    assert g._aggregate(tuple(table.items())) == expected


def test_q27_receipt_and_control_result_authority_flags_are_exact(lineage):
    results = [gate(lineage), gate(lineage, receipt=af1_with("BUDGET", "FAIL"))]
    for result in results:
        for flag in ("no_strategy_authority", "no_paper_authority", "no_execution_authority",
                     "no_live_authority", "no_gate_c_authority"):
            assert getattr(result, flag) is True, flag
    receipt = admitted(results[0])
    for flag in ("successor_authorization_required", "no_strategy_authority", "no_paper_authority",
                 "no_execution_authority", "no_live_authority", "no_gate_c_authority"):
        assert getattr(receipt, flag) is True, flag
    # The gate receipt deliberately does not carry S10-QUAL-01's no_qualification_authority.
    assert not hasattr(receipt, "no_qualification_authority")


# ── Q28 / Q29 S10-QUAL-B0X-01 external-reconstruction B0 admission ──────────
EXTERNAL_ALL_EVIDENCE = tuple(
    ref for ref in ALL_EVIDENCE if ref not in {"evidence:pit-book", "evidence:pit-trades"}
) + tq.EXTERNAL_EVIDENCE


def external_ready(lin, **over):
    return ready_input(lin, factory=tq.external_input, **over)


def external_manifests():
    return [ready_manifest(refs=EXTERNAL_ALL_EVIDENCE, dataset_refs=(tq.EXTERNAL_DATASET_REF,))]


def external_gate(lin, value=None):
    record = candidate_for(lin, external_ready(lin) if value is None else value, manifests=external_manifests())
    return record, gate(lin, record, manifests=external_manifests())


def test_q28_valid_external_b0_candidate_is_admitted_without_gate_change(lineage):
    record, result = external_gate(lineage)
    receipt = admitted(result)
    assert json.loads(record.forecast_evaluation_plan_json)["b0_rule"] == tq.EXTERNAL_B0_RULE
    assert receipt.qualification_candidate_id == record.qualification_candidate_id
    # Same dimensions, same aggregation, same outcome as the canonical ready fixture.
    canonical = admitted(gate(lineage))
    assert [name for name, _status in receipt.dimension_statuses] == list(g.QUALIFICATION_GATE_DIMENSIONS)
    assert dims(receipt) == dims(canonical)
    assert receipt.overall_disposition == canonical.overall_disposition == "QUAL_PASS"
    # The gate never rewrites or reinterprets B0 semantics.
    assert q.validate_qualification_candidate(record).record is record
    assert json.loads(record.forecast_evaluation_plan_json) == json.loads(
        candidate_for(lineage, external_ready(lineage), manifests=external_manifests()).forecast_evaluation_plan_json
    )
    source = (tq.ROOT / "src" / "data_layer" / "analytical_research" / "qualification_gate.py").read_text(
        encoding="utf-8")
    for token in ("b0_rule", "PIT_MARKET_PROBABILITY_V1", "MARKET_PIT", "MARKET_EXTERNAL_RECONSTRUCTION",
                  "EXTERNAL_PIT"):
        assert token not in source, token


@pytest.mark.parametrize("over,dimension", [
    ({"sample_power_plan": ready_power(available_sample_count=199)}, "SAMPLE_POWER_READINESS"),
    ({"execution_feasibility_plan": ready_feasibility(
        FEES={"state": "MISSING", "evidence_reference_ids": []})}, "EXECUTION_EVIDENCE_READINESS"),
])
def test_q29_external_b0_dimensions_follow_existing_evidence_rules(lineage, over, dimension):
    _record, result = external_gate(lineage, external_ready(lineage, **over))
    external = admitted(result)
    canonical = admitted(gate(lineage, candidate_for(lineage, ready_input(lineage, **over))))
    assert dims(external) == dims(canonical)
    assert dims(external)[dimension] == "INCONCLUSIVE"
    assert external.overall_disposition == canonical.overall_disposition == "QUAL_INCONCLUSIVE"
    # An unbound external evidence ref is judged by the same provenance-binding rule.
    unbound = [ready_manifest(refs=ALL_EVIDENCE, dataset_refs=(tq.EXTERNAL_DATASET_REF,))]
    record = candidate_for(lineage, external_ready(lineage), manifests=unbound)
    assert dims(admitted(gate(lineage, record, manifests=unbound)))["PIT_PROVENANCE_READINESS"] == "INCONCLUSIVE"
