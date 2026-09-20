"""WP175N record-model construction, validation, and result-state discipline."""

from __future__ import annotations

from dataclasses import fields

import pytest

from src.data_layer.analytical_research import alpha_factory as af


# ── builders / fixtures ──────────────────────────────────────────────────────
def source_input(**over):
    base = {
        "source_kind": "PUBLIC_HTTPS",
        "source_class": "OFFICIAL",
        "source_locator": "https://docs.polymarket.com/rules",
        "title": "Resolution rules",
        "observed_at": "2026-09-20T00:00:00Z",
        "content_sha256": None,
        "provenance": "human_research",
    }
    base.update(over)
    return base


def candidate_input(**over):
    base = {
        "candidate_version": "v1",
        "title": "Weather edge in NFL unders",
        "research_question": "Does cold weather bias overs?",
        "thesis": "Cold suppresses scoring.",
        "subject_refs": ["subject-a", "subject-b"],
        "evidence_lanes": ["WEATHER", "FUNDAMENTAL"],
        "scope_key": "nfl-regular-2026",
        "mechanism_hint": "temperature suppresses scoring",
        "novelty_dimensions": {
            "subject_keys": ["nfl", "weather"],
            "scope_key": "nfl-regular-2026",
            "mechanism_key": "cold-scoring-suppression",
        },
        "discovery_provenance": "human_research",
        "human_review_required": True,
    }
    base.update(over)
    return base


def family_input(**over):
    base = {
        "family_version": "v1",
        "family_name": "Cold-weather scoring suppression",
        "mechanism_key": "cold-scoring-suppression",
        "mechanism_dimensions": {"driver": "temperature", "lanes": ["weather"]},
        "falsifiable_theme": "cold reduces total points",
        "predecessor_family_id": None,
        "creation_provenance": "human_research",
        "human_review_required": True,
    }
    base.update(over)
    return base


def episode_input(**over):
    base = {
        "episode_version": "v1",
        "candidate_id": "alphacandidate:sha256:" + "a" * 64,
        "hypothesis_family_id": "alphafamily:sha256:" + "b" * 64,
        "predecessor_episode_id": None,
        "reopened_episode_id": None,
        "result_state": "RESEARCH_SUPPORTIVE",
        "confidence_label": "moderate",
        "evidence_lanes": ["WEATHER"],
        "exact_scope": {"league": "nfl", "season": "2026"},
        "evidence_regime": {"window": "2020-2025"},
        "research_question": "Does cold bias overs?",
        "thesis": "Cold suppresses scoring.",
        "tested_assumptions": ["temperature measured pre-kickoff"],
        "evidence_for": ["historical unders in cold"],
        "evidence_against": [],
        "uncertainties": ["dome games"],
        "known_missing_data": [],
        "falsification_checks_performed": ["checked warm-weather control"],
        "limitations": ["small sample"],
        "what_would_change_the_conclusion": ["a warm-weather over run"],
        "suggested_next_research_steps": ["expand cohort"],
        "source_reference_ids": ["alphasource:sha256:" + "c" * 64],
        "deterministic_evidence_refs": ["det-evidence-1"],
        "material_change_basis": [],
        "producer_type": "HUMAN_RESEARCH",
        "producer_version": "human-v1",
        "producer_receipt_ref": None,
        "research_as_of": "2026-09-20T00:00:00Z",
        "creation_provenance": "human_research",
        "human_review_required": True,
    }
    base.update(over)
    return base


# ── R001 source determinism ──────────────────────────────────────────────────
def test_source_identity_is_deterministic():
    a = af.build_research_source_reference(source_input())
    b = af.build_research_source_reference(source_input())
    assert a.is_valid and b.is_valid
    assert a.record.source_reference_id == b.record.source_reference_id
    assert a.record.source_reference_id.startswith("alphasource:sha256:")


def test_source_one_field_change_changes_identity():
    a = af.build_research_source_reference(source_input())
    b = af.build_research_source_reference(source_input(title="Different title"))
    assert a.record.source_reference_id != b.record.source_reference_id


# ── R002 URL / locator boundary ──────────────────────────────────────────────
def test_https_source_accepted_and_normalised():
    result = af.build_research_source_reference(
        source_input(source_locator="HTTPS://Docs.Polymarket.com/Rules")
    )
    assert result.is_valid
    assert result.record.source_locator == "https://docs.polymarket.com/Rules"


@pytest.mark.parametrize(
    "locator",
    [
        "http://docs.polymarket.com/rules",
        "file:///etc/passwd",
        "/local/path/rules.md",
        "https://user:pw@docs.polymarket.com/rules",
        "https://docs.polymarket.com/rules?api_key=SECRET",
        "https://docs.polymarket.com/rules?token=abc",
        "https://localhost/rules",
    ],
)
def test_https_source_rejected(locator):
    result = af.build_research_source_reference(source_input(source_locator=locator))
    assert not result.is_valid
    assert result.record is None
    assert result.error_codes and result.error_codes[0] in {"FIELD_VALUE_INVALID", "FORBIDDEN_CONTENT"}


def test_repo_evidence_locator_rejects_path():
    result = af.build_research_source_reference(
        source_input(source_kind="REPO_EVIDENCE_ID", source_class="REPO_EVIDENCE", source_locator="C:/data/x")
    )
    assert not result.is_valid


def test_blockchain_locator_rejects_private_material():
    result = af.build_research_source_reference(
        source_input(
            source_kind="PUBLIC_BLOCKCHAIN", source_class="PUBLIC_BLOCKCHAIN",
            source_locator="tx:mnemonic-leak",
        )
    )
    assert not result.is_valid and result.error_codes[0] == "FORBIDDEN_CONTENT"


# ── R003 candidate closed semantics ──────────────────────────────────────────
_FORBIDDEN_ECONOMIC_FIELDS = {
    "probability", "fair_value", "fairvalue", "side", "size", "expected_value",
    "ev", "strategy", "promote", "promotion", "approve", "order", "position",
    "signal", "portfolio", "execution", "edge", "pnl", "price", "stake",
}


@pytest.mark.parametrize("record_type", [af.OpportunityCandidate, af.ResearchEpisode, af.HypothesisFamily, af.ResearchSourceReference])
def test_records_carry_no_economic_or_execution_fields(record_type):
    names = {field.name for field in fields(record_type)}
    assert names & _FORBIDDEN_ECONOMIC_FIELDS == set()


def test_candidate_valid_and_advisory_flags_true():
    result = af.build_opportunity_candidate(candidate_input())
    assert result.is_valid
    record = result.record
    assert record.advisory_only and record.no_execution_authority
    assert record.no_strategy_authority and record.no_qualification_authority
    assert record.candidate_id.startswith("alphacandidate:sha256:")


def test_candidate_novelty_scope_must_match_top_level_scope():
    result = af.build_opportunity_candidate(
        candidate_input(
            novelty_dimensions={
                "subject_keys": ["nfl"], "scope_key": "OTHER", "mechanism_key": "m",
            }
        )
    )
    assert not result.is_valid and result.error_codes[0] == "FIELD_VALUE_INVALID"


# ── R006 primitive lane set ──────────────────────────────────────────────────
def test_composite_is_not_a_stored_lane():
    assert "COMPOSITE" not in af.EVIDENCE_LANES


def test_unknown_lane_rejected():
    result = af.build_opportunity_candidate(candidate_input(evidence_lanes=["NOT_A_LANE"]))
    assert not result.is_valid and result.error_codes[0] == "LANE_INVALID"


def test_duplicate_lane_rejected():
    result = af.build_opportunity_candidate(candidate_input(evidence_lanes=["WEATHER", "WEATHER"]))
    assert not result.is_valid and result.error_codes[0] == "LANE_INVALID"


def test_lane_input_order_does_not_change_identity_or_storage():
    a = af.build_opportunity_candidate(candidate_input(evidence_lanes=["WEATHER", "FUNDAMENTAL"]))
    b = af.build_opportunity_candidate(candidate_input(evidence_lanes=["FUNDAMENTAL", "WEATHER"]))
    assert a.record.candidate_id == b.record.candidate_id
    assert a.record.evidence_lanes == ("FUNDAMENTAL", "WEATHER")


# ── R007 global episode discipline ───────────────────────────────────────────
def test_episode_requires_non_empty_falsification_checks():
    result = af.build_research_episode(episode_input(falsification_checks_performed=[]))
    assert not result.is_valid and result.error_codes[0] == "RESULT_EVIDENCE_INVALID"


def test_episode_requires_some_evidence_reference():
    result = af.build_research_episode(
        episode_input(source_reference_ids=[], deterministic_evidence_refs=[])
    )
    assert not result.is_valid and result.error_codes[0] == "RESULT_EVIDENCE_INVALID"


# ── R008 state evidence matrix ───────────────────────────────────────────────
_STATE_MIN = {
    "RESEARCH_SUPPORTIVE": {"evidence_for": ["x"]},
    "NO_EDGE_CURRENTLY": {"evidence_against": ["x"]},
    "HYPOTHESIS_FALSIFIED": {"evidence_against": ["x"]},
    "DATA_INSUFFICIENT": {"known_missing_data": ["x"]},
    "EXECUTION_UNECONOMIC": {"evidence_against": ["x"], "deterministic_evidence_refs": ["det-1"]},
    "WATCH_FOR_CHANGE": {"what_would_change_the_conclusion": ["x"]},
    "RESEARCH_STALE": {"material_change_basis": ["x"]},
    "MECHANISM_FAMILY_EXHAUSTED": {"evidence_against": ["x"]},
}


@pytest.mark.parametrize("state,extra", list(_STATE_MIN.items()))
def test_each_state_accepts_with_required_fields(state, extra):
    base = episode_input(
        result_state=state, evidence_for=[], evidence_against=[], known_missing_data=[],
        what_would_change_the_conclusion=[], material_change_basis=[],
    )
    base.update(extra)
    result = af.build_research_episode(base)
    assert result.is_valid, (state, result.error_codes)


@pytest.mark.parametrize("state,extra", list(_STATE_MIN.items()))
def test_each_state_rejects_without_required_fields(state, extra):
    base = episode_input(
        result_state=state, evidence_for=[], evidence_against=[], known_missing_data=[],
        what_would_change_the_conclusion=[], material_change_basis=[],
        deterministic_evidence_refs=["det-1"], source_reference_ids=["alphasource:sha256:" + "c" * 64],
    )
    result = af.build_research_episode(base)
    assert not result.is_valid and result.error_codes[0] == "RESULT_EVIDENCE_INVALID"


def test_reopen_triggered_requires_reopened_episode_id():
    result = af.build_research_episode(
        episode_input(result_state="REOPEN_TRIGGERED", material_change_basis=["x"], reopened_episode_id=None)
    )
    assert not result.is_valid and "REOPEN_INVALID" in result.error_codes


def test_non_reopen_forbids_reopened_episode_id():
    result = af.build_research_episode(
        episode_input(reopened_episode_id="alphaepisode:sha256:" + "d" * 64)
    )
    assert not result.is_valid and "REOPEN_INVALID" in result.error_codes


# ── R009 confidence vocabulary ───────────────────────────────────────────────
@pytest.mark.parametrize("label", af.ALPHA_FACTORY_CONFIDENCE_LABELS)
def test_confidence_labels_accepted(label):
    assert af.build_research_episode(episode_input(confidence_label=label)).is_valid


def test_unknown_confidence_rejected():
    result = af.build_research_episode(episode_input(confidence_label="extreme"))
    assert not result.is_valid and result.error_codes[0] == "FIELD_VALUE_INVALID"


# ── R010 exact-scope negative memory ─────────────────────────────────────────
def test_scope_one_field_difference_changes_episode_identity():
    a = af.build_research_episode(episode_input(exact_scope={"league": "nfl"}))
    b = af.build_research_episode(episode_input(exact_scope={"league": "nba"}))
    assert a.record.research_episode_id != b.record.research_episode_id


def test_regime_one_field_difference_changes_episode_identity():
    a = af.build_research_episode(episode_input(evidence_regime={"window": "2020-2025"}))
    b = af.build_research_episode(episode_input(evidence_regime={"window": "2021-2025"}))
    assert a.record.research_episode_id != b.record.research_episode_id


# ── R012 producer provenance ─────────────────────────────────────────────────
def test_hermes_producer_requires_receipt():
    result = af.build_research_episode(
        episode_input(producer_type="HERMES_CONTROLLED_RESEARCH", producer_receipt_ref=None)
    )
    assert not result.is_valid and result.error_codes[0] == "RESULT_EVIDENCE_INVALID"


def test_hermes_producer_with_receipt_ok():
    result = af.build_research_episode(
        episode_input(producer_type="HERMES_CONTROLLED_RESEARCH", producer_receipt_ref="hermes-receipt-1")
    )
    assert result.is_valid


def test_human_producer_requires_source_reference():
    result = af.build_research_episode(
        episode_input(
            producer_type="HUMAN_RESEARCH", source_reference_ids=[],
            deterministic_evidence_refs=["det-1"],
        )
    )
    assert not result.is_valid and result.error_codes[0] == "RESULT_EVIDENCE_INVALID"


def test_deterministic_producer_requires_deterministic_ref():
    result = af.build_research_episode(
        episode_input(producer_type="DETERMINISTIC_ANALYSIS", deterministic_evidence_refs=[])
    )
    assert not result.is_valid and result.error_codes[0] == "RESULT_EVIDENCE_INVALID"


def test_producer_receipt_ref_rejects_path():
    result = af.build_research_episode(
        episode_input(producer_type="HERMES_CONTROLLED_RESEARCH", producer_receipt_ref="/tmp/receipt")
    )
    assert not result.is_valid


# ── R013 recursive secret / authority key rejection ──────────────────────────
@pytest.mark.parametrize("key", ["api_key", "API_KEY", "authorization", "mnemonic", "access_token"])
def test_nested_secret_keys_rejected_without_echo(key):
    result = af.build_hypothesis_family(family_input(mechanism_dimensions={"outer": {key: "zzz"}}))
    assert not result.is_valid
    assert result.error_codes == ("FORBIDDEN_CONTENT",)
    assert result.record is None


@pytest.mark.parametrize("key", ["place_order", "sign_transaction", "auto_trade", "position_size", "execute"])
def test_nested_authority_keys_rejected(key):
    result = af.build_research_episode(episode_input(exact_scope={"nested": {key: True}}))
    assert not result.is_valid and result.error_codes == ("FORBIDDEN_CONTENT",)


# ── R014 binary float rejection ──────────────────────────────────────────────
@pytest.mark.parametrize(
    "dims",
    [{"a": 1.5}, {"a": {"b": 2.0}}, {"a": {"b": {"c": [1, 2.5]}}}],
)
def test_binary_float_rejected_at_every_depth(dims):
    result = af.build_hypothesis_family(family_input(mechanism_dimensions=dims))
    assert not result.is_valid and result.error_codes[0] == "FIELD_TYPE_INVALID"
