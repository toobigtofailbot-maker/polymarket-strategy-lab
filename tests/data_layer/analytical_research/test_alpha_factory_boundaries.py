"""WP175N conservative bounds, reopen append-only lineage, and repo-truth docs."""

from __future__ import annotations

import pathlib

import pytest

from src.data_layer.analytical_research import alpha_factory as af
from src.data_layer.analytical_research import alpha_factory_registry as afr
from tests.data_layer.analytical_research.test_alpha_factory_records import (
    candidate_input,
    episode_input,
    family_input,
)
from tests.data_layer.analytical_research.test_alpha_factory_registry import (
    fresh,
    mk_candidate,
    mk_episode,
    mk_family,
    mk_source,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def _doc(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _flat(rel: str) -> str:
    """Doc text with runs of whitespace collapsed, so hard-wrapped phrases match."""
    return " ".join((REPO_ROOT / rel).read_text(encoding="utf-8").split())


# ── R037 bounds: at-bound passes, one-over fails ─────────────────────────────
def test_text_at_and_over_bound():
    ok = af.build_hypothesis_family(family_input(family_name="x" * af.MAX_ALPHA_TEXT_CHARS))
    assert ok.is_valid
    over = af.build_hypothesis_family(family_input(family_name="x" * (af.MAX_ALPHA_TEXT_CHARS + 1)))
    assert not over.is_valid and over.error_codes[0] == "FIELD_VALUE_INVALID"


def test_sequence_at_and_over_bound():
    ok = af.build_opportunity_candidate(
        candidate_input(subject_refs=[f"s-{i}" for i in range(af.MAX_ALPHA_SEQUENCE_ITEMS)])
    )
    assert ok.is_valid
    over = af.build_opportunity_candidate(
        candidate_input(subject_refs=[f"s-{i}" for i in range(af.MAX_ALPHA_SEQUENCE_ITEMS + 1)])
    )
    assert not over.is_valid and over.error_codes[0] == "LIMIT_EXCEEDED"


def _nested(depth: int) -> dict:
    node: dict = {"leaf": 1}
    for _ in range(depth - 1):
        node = {"child": node}
    return node


def test_mapping_depth_at_and_over_bound():
    ok = af.build_hypothesis_family(family_input(mechanism_dimensions=_nested(af.MAX_ALPHA_MAPPING_DEPTH)))
    assert ok.is_valid, ok.error_codes
    over = af.build_hypothesis_family(family_input(mechanism_dimensions=_nested(af.MAX_ALPHA_MAPPING_DEPTH + 2)))
    assert not over.is_valid and over.error_codes[0] == "LIMIT_EXCEEDED"


def test_mapping_keys_over_bound():
    big = {f"k{i}": i for i in range(af.MAX_ALPHA_MAPPING_KEYS + 1)}
    over = af.build_hypothesis_family(family_input(mechanism_dimensions=big))
    assert not over.is_valid and over.error_codes[0] == "LIMIT_EXCEEDED"


def test_append_batch_at_and_over_bound(tmp_path):
    path = fresh(tmp_path)
    at_bound = [
        af.build_research_source_reference(
            {
                "source_kind": "PUBLIC_HTTPS", "source_class": "OFFICIAL",
                "source_locator": f"https://docs.polymarket.com/doc-{i}",
                "title": f"doc {i}", "observed_at": "2026-09-20T00:00:00Z",
                "content_sha256": None, "provenance": "human",
            }
        ).record
        for i in range(afr.MAX_ALPHA_APPEND_BATCH)
    ]
    result = afr.append_alpha_factory_records(path, at_bound)
    assert result.is_valid and result.snapshot.total_rows == afr.MAX_ALPHA_APPEND_BATCH
    over = at_bound + [
        af.build_research_source_reference(
            {
                "source_kind": "PUBLIC_HTTPS", "source_class": "OFFICIAL",
                "source_locator": "https://docs.polymarket.com/over",
                "title": "over", "observed_at": "2026-09-20T00:00:00Z",
                "content_sha256": None, "provenance": "human",
            }
        ).record
    ]
    path2 = fresh(tmp_path, "over.sqlite3")
    over_result = afr.append_alpha_factory_records(path2, over)
    assert not over_result.is_valid and over_result.error_codes[0] == "LIMIT_EXCEEDED"


# ── R011 reopen append-only lineage ──────────────────────────────────────────
def _committed_negative_episode(path, cand, fam, src):
    ep = mk_episode(cand, fam, src, state="NO_EDGE_CURRENTLY")
    afr.append_alpha_factory_records(path, [src, cand, fam, ep])
    return ep


def test_reopen_appends_new_episode_without_mutating_prior(tmp_path):
    path = fresh(tmp_path)
    src, cand, fam = mk_source(), mk_candidate(), mk_family()
    prior = _committed_negative_episode(path, cand, fam, src)
    before = afr.load_and_verify_alpha_factory_registry(path).snapshot
    prior_entry = next(e for e in before.entries if e.record_id == prior.research_episode_id)

    reopen = mk_episode(
        cand, fam, src, state="REOPEN_TRIGGERED", reopened=prior.research_episode_id,
    )
    result = afr.append_alpha_factory_records(path, [reopen])
    assert result.is_valid, result.error_codes
    after = afr.load_and_verify_alpha_factory_registry(path).snapshot
    after_prior = next(e for e in after.entries if e.record_id == prior.research_episode_id)
    # Prior episode row is byte-identical; a new immutable episode was appended.
    assert after_prior.entry_hash == prior_entry.entry_hash
    assert after_prior.payload_sha256 == prior_entry.payload_sha256
    assert after.total_rows == before.total_rows + 1


def test_reopen_targeting_supportive_episode_rejected(tmp_path):
    path = fresh(tmp_path)
    src, cand, fam = mk_source(), mk_candidate(), mk_family()
    supportive = mk_episode(cand, fam, src, state="RESEARCH_SUPPORTIVE")
    afr.append_alpha_factory_records(path, [src, cand, fam, supportive])
    reopen = mk_episode(cand, fam, src, state="REOPEN_TRIGGERED", reopened=supportive.research_episode_id)
    result = afr.append_alpha_factory_records(path, [reopen])
    assert not result.is_valid and result.error_codes[0] == "REOPEN_INVALID"


def test_reopen_wrong_candidate_rejected(tmp_path):
    path = fresh(tmp_path)
    src, cand, fam = mk_source(), mk_candidate(), mk_family()
    other_cand = mk_candidate(scope="nba-2026", mechanism="pace", subject="nba")
    prior = _committed_negative_episode(path, cand, fam, src)
    afr.append_alpha_factory_records(path, [other_cand])
    reopen = mk_episode(other_cand, fam, src, state="REOPEN_TRIGGERED", reopened=prior.research_episode_id)
    result = afr.append_alpha_factory_records(path, [reopen])
    assert not result.is_valid and result.error_codes[0] == "REOPEN_INVALID"


def test_negative_evidence_is_scope_bound_not_global_blacklist(tmp_path):
    # Two episodes, same candidate/family, different exact_scope, both NO_EDGE: both
    # persist as distinct immutable records — negative evidence never globalises.
    path = fresh(tmp_path)
    src, cand, fam = mk_source(), mk_candidate(), mk_family()
    ep_a = mk_episode(cand, fam, src, state="NO_EDGE_CURRENTLY", scope={"league": "nfl", "week": "1"})
    ep_b = mk_episode(cand, fam, src, state="NO_EDGE_CURRENTLY", scope={"league": "nfl", "week": "2"})
    assert ep_a.research_episode_id != ep_b.research_episode_id
    result = afr.append_alpha_factory_records(path, [src, cand, fam, ep_a, ep_b])
    assert result.is_valid and result.snapshot.total_rows == 5


# ── multi-lane is derived, never a stored identity input ─────────────────────
def test_multi_lane_is_derived_not_stored():
    single = af.build_opportunity_candidate(candidate_input(evidence_lanes=["WEATHER"]))
    multi = af.build_opportunity_candidate(candidate_input(evidence_lanes=["WEATHER", "FUNDAMENTAL"]))
    assert len(single.record.evidence_lanes) == 1
    assert len(multi.record.evidence_lanes) >= 2  # is_multi_lane is a derived property
    assert "COMPOSITE" not in af.EVIDENCE_LANES


# ── R038-R050 canonical repo-truth doc facts ─────────────────────────────────
CONTRACT = "docs/alpha_factory_core_contract.md"
ROADMAP = "docs/long_term_bot_completion_roadmap.md"
STATUS = "docs/project_status.md"
ADOPTION = "docs/adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in.md"


def test_docs_track_h1_pass_truth():
    contract = _flat(CONTRACT)
    assert "GENUINE_H1_PASS" in contract
    assert "Accepted H1: H1 #4" in contract
    assert "Historical real H1 research invocations consumed: 4" in contract
    assert "H1 #5 is NOT AUTHORIZED" in contract


def test_docs_track_firecrawl_contract_vs_telemetry():
    contract = _flat(CONTRACT)
    # Configured Firecrawl-only contract is asserted, but remote HTTP telemetry is NOT.
    assert "Firecrawl-only web backend" in contract
    assert "remote Firecrawl HTTP" in contract
    assert "does NOT independently expose downstream Firecrawl HTTP telemetry" in contract


def test_docs_track_separate_authorization_model():
    contract = _flat(CONTRACT)
    assert "separate explicit human authorization" in contract
    assert "NO automatic controller rerun" in contract


def test_docs_persist_wallet_track():
    contract = _flat(CONTRACT)
    for token in ("S10-WALLET-01", "S10-WALLET-02", "S10-WALLET-03", "S10-WALLET-04", "S10-GATE-WALLET-01"):
        assert token in contract


def test_docs_wallet_gate_conditional():
    contract = _flat(CONTRACT)
    assert "S10-GATE-WALLET-01 IS CONDITIONAL" in contract
    assert "not a global qualification blocker" in contract


def test_docs_immediate_successor_is_wallet_then_hermes_ctx():
    contract = _flat(CONTRACT)
    assert "immediate software successor after WP175N MERGE is S10-WALLET-01" in contract
    assert "S10-HERMES-CTX-01" in contract


def test_docs_alpha02_ownership():
    contract = _flat(CONTRACT)
    assert "S10-ALPHA-02" in contract and "material-change detection" in contract
    assert "automatic reopen" in contract and "prioritization" in contract


def test_docs_alpha03_ownership():
    contract = _flat(CONTRACT)
    assert "S10-ALPHA-03" in contract
    assert "scheduler" in contract and "budgets/rates" in contract


def test_docs_hermes_si_parallel_rule():
    contract = _flat(CONTRACT)
    assert "S10-HERMES-SI-01" in contract
    assert "accepted AF1 benchmark material" in contract


def test_docs_old_wp180_wp181_superseded():
    contract = _flat(CONTRACT)
    assert "WP180/WP181" in contract
    assert "SUPERSEDED" in contract
    assert "WP176A-E" in contract


def test_docs_gate_c_not_authorized_and_no_authority():
    contract = _flat(CONTRACT)
    assert "Gate C is NOT AUTHORIZED" in contract
    assert "no provider/model/Hermes runtime" in contract
    assert "Merge authorized: NO" in contract


def test_project_status_blast_radius_discipline():
    status_lines = _doc(STATUS).splitlines()
    # Legacy first current-phase compatibility line is preserved (contains WP130).
    current_phase = next(line for line in status_lines if line.startswith("- Current phase:"))
    assert "WP130" in current_phase
    # An additive authoritative WP175N block exists at the top.
    assert any(line.startswith("# WP175N current review target:") for line in status_lines)


def test_adoption_supersession_is_additive_not_history_rewrite():
    adoption = _flat(ADOPTION)
    assert "Supersession" in adoption
    assert "it does not rewrite" in adoption and "history" in adoption
    assert "remains valid" in adoption
