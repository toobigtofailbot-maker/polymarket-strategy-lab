"""Focused tests for the shared research provenance / PIT / DQ / replay core.

These use an INDEPENDENT test-side canonical identity oracle (they do not call
the production identity helpers to compute the expected id) so the tests cannot
be satisfied by a circular reimplementation.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from src.data_layer.point_in_time_market_research import research_provenance as rp


# ---------------------------------------------------------------------------
# Independent test-side canonical JSON + sha256 oracle.
# ---------------------------------------------------------------------------
def _oracle_canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _oracle_sha256(value: object) -> str:
    return hashlib.sha256(_oracle_canonical(value)).hexdigest()


def _pit(**kwargs):
    return rp.build_pit_timestamps(**kwargs)


def _raw(**overrides):
    params = dict(
        source_system="POLYMARKET_DATA_API_V2",
        endpoint="/v2/trades",
        retrieval_method="GET/urllib",
        content_sha256="a" * 64,
        byte_length=42,
        media_type="application/json",
        pit=_pit(local_first_seen_time="2026-01-02T00:00:00Z"),
        dq_flags=["OK"],
        replay_fidelity="FAITHFUL",
        request_parameters={"user": "0xabc", "taker_only": "false"},
    )
    params.update(overrides)
    return rp.build_raw_evidence_reference(**params)


# ---------------------------------------------------------------------------
# Timestamps (9.1).
# ---------------------------------------------------------------------------
def test_timestamp_canonicalizes_plus_zero_offset_to_z():
    assert rp.canonicalize_utc_timestamp("2026-01-01T00:00:00+00:00") == "2026-01-01T00:00:00Z"


def test_timestamp_drops_trailing_fraction_zeros():
    assert rp.canonicalize_utc_timestamp("2026-01-01T00:00:00.500000Z") == "2026-01-01T00:00:00.5Z"


def test_timestamp_naive_rejected():
    with pytest.raises(ValueError):
        rp.canonicalize_utc_timestamp("2026-01-01T00:00:00")


def test_timestamp_non_utc_offset_rejected_as_not_utc():
    with pytest.raises(ValueError) as exc:
        rp.canonicalize_utc_timestamp("2026-01-01T00:00:00+05:00")
    assert str(exc.value) == "TIMESTAMP_NOT_UTC"


def test_timestamp_non_string_rejected():
    with pytest.raises(ValueError):
        rp.canonicalize_utc_timestamp(1735689600)


def test_build_pit_timestamps_rejects_unknown_field():
    with pytest.raises(ValueError):
        rp.build_pit_timestamps(not_a_field="2026-01-01T00:00:00Z")


def test_pit_time_fields_exact_set():
    assert rp.PIT_TIME_FIELDS == (
        "event_time",
        "chain_block_time",
        "source_publish_time",
        "public_available_time",
        "local_first_seen_time",
        "ingestion_time",
        "confirmation_or_finality_time",
        "correction_or_revision_time",
        "resolution_time",
    )


# ---------------------------------------------------------------------------
# Data quality vocabulary (9.2) - R-W14 exact table.
# ---------------------------------------------------------------------------
def test_dq_exact_expected_set_equals_production():
    expected = {
        "OK",
        "MISSING",
        "STALE",
        "DELAYED",
        "CORRECTED",
        "BACKFILLED",
        "PARTIALLY_OBSERVED",
        "DUPLICATED",
        "SEQUENCE_GAP",
        "TIMESTAMP_UNCERTAIN",
        "SOURCE_UNAVAILABLE",
        "SCHEMA_DRIFT",
        "SOURCE_DISAGREEMENT",
        "REORGED",
        "UNFINALIZED",
        "IDENTITY_AMBIGUOUS",
        "COST_BASIS_INCOMPLETE",
        "BOOK_UNAVAILABLE",
    }
    assert set(rp.DATA_QUALITY_FLAGS) == expected
    assert list(rp.DATA_QUALITY_FLAGS) == sorted(rp.DATA_QUALITY_FLAGS)


def test_dq_ok_cannot_coexist_with_non_ok():
    with pytest.raises(ValueError):
        rp.canonicalize_dq_flags(["OK", "STALE"])


def test_dq_unknown_rejects():
    with pytest.raises(ValueError):
        rp.canonicalize_dq_flags(["NOT_A_FLAG"])


def test_dq_empty_rejects():
    with pytest.raises(ValueError):
        rp.canonicalize_dq_flags([])


def test_dq_multiple_non_ok_preserved_and_sorted_deduped():
    assert rp.canonicalize_dq_flags(
        ["SEQUENCE_GAP", "PARTIALLY_OBSERVED", "SEQUENCE_GAP"]
    ) == ("PARTIALLY_OBSERVED", "SEQUENCE_GAP")


# ---------------------------------------------------------------------------
# Replay fidelity (9.3) + RawEvidenceReference (9.4).
# ---------------------------------------------------------------------------
def test_replay_fidelity_closed_set():
    assert rp.REPLAY_FIDELITY_STATES == ("EXACT", "FAITHFUL", "PARTIAL", "UNREPLAYABLE")


def test_exact_replay_requires_durable_raw_reference():
    with pytest.raises(ValueError) as exc:
        _raw(replay_fidelity="EXACT")
    assert str(exc.value) == "REPLAY_FIDELITY_EXACT_WITHOUT_RAW"
    ref = _raw(replay_fidelity="EXACT", raw_snapshot_ref="blob://snapshot/1")
    assert ref.replay_fidelity == "EXACT"


def test_raw_evidence_reference_has_no_ingest_run_key_field():
    # R-B01 / R-B05: RawEvidenceReference schema carries no run key.
    fields = set(rp.RawEvidenceReference.__dataclass_fields__)
    assert "ingest_run_key" not in fields


def test_raw_evidence_reference_identity_matches_independent_oracle():
    ref = _raw()
    expected = rp.RAW_EVIDENCE_REFERENCE_ID_PREFIX + _oracle_sha256(ref.logical_preimage())
    assert ref.raw_evidence_reference_id == expected
    assert rp.verify_raw_evidence_reference_identity(ref)


def test_raw_evidence_reference_identity_changes_on_semantic_change():
    a = _raw()
    b = _raw(byte_length=43)
    assert a.raw_evidence_reference_id != b.raw_evidence_reference_id


def test_raw_evidence_reference_request_param_order_does_not_change_identity():
    a = _raw(request_parameters={"user": "0xabc", "taker_only": "false"})
    b = _raw(request_parameters=[("taker_only", "false"), ("user", "0xabc")])
    assert a.raw_evidence_reference_id == b.raw_evidence_reference_id


def test_raw_evidence_reference_rejects_bad_hash():
    with pytest.raises(ValueError):
        _raw(content_sha256="notahash")


def test_raw_evidence_reference_rejects_negative_byte_length():
    with pytest.raises(ValueError):
        _raw(byte_length=-1)


# ---------------------------------------------------------------------------
# ResearchProvenanceManifest (9.5) - R-W16 / R-V2-01 non-circular.
# ---------------------------------------------------------------------------
def _manifest(**overrides):
    params = dict(
        repo_code_identity="repo:sha256:deadbeef",
        information_cutoff="2026-01-03T00:00:00Z",
        output_identity="output:1",
        output_hash="b" * 64,
        input_evidence_reference_ids=["rawevidence:sha256:" + "c" * 64],
    )
    params.update(overrides)
    return rp.build_research_provenance_manifest(**params)


def test_manifest_identity_matches_independent_oracle():
    m = _manifest()
    expected = rp.RESEARCH_PROVENANCE_MANIFEST_ID_PREFIX + _oracle_sha256(m.logical_preimage())
    assert m.research_provenance_manifest_id == expected
    assert rp.verify_research_provenance_manifest_identity(m)


def test_manifest_identity_changes_on_input_change():
    a = _manifest()
    b = _manifest(gap_summary="one page missing")
    assert a.research_provenance_manifest_id != b.research_provenance_manifest_id


def test_manifest_has_no_ingest_run_key_field():
    fields = set(rp.ResearchProvenanceManifest.__dataclass_fields__)
    assert "ingest_run_key" not in fields


def test_manifest_core_has_no_wallet_extension_backreference_fields():
    # The core manifest must not carry any field that points back to a wallet or
    # domain extension: direction is one-way (extension -> manifest).
    fields = " ".join(rp.ResearchProvenanceManifest.__dataclass_fields__).lower()
    for forbidden in ("wallet_extension", "wallet_provenance_extension", "domain_extension"):
        assert forbidden not in fields


def test_manifest_identity_is_computable_without_any_extension():
    # Building a manifest and recomputing its id involves no extension input at all.
    m = _manifest()
    recomputed = rp.RESEARCH_PROVENANCE_MANIFEST_ID_PREFIX + _oracle_sha256(
        m.logical_preimage()
    )
    assert recomputed == m.research_provenance_manifest_id


# ---------------------------------------------------------------------------
# Replay admissibility table (9.6) - R-V2-07 / R-W05 cases A-I.
# ---------------------------------------------------------------------------
def _admit(cutoff, **ev):
    return rp.evaluate_replay_admissibility(cutoff, rp.ObservabilityEvidence(**ev))


def test_admissibility_case_A_event_before_but_first_seen_after():
    r = _admit(
        "2026-01-01T12:00:00Z",
        event_time="2026-01-01T00:00:00Z",
        local_first_seen_time="2026-01-02T00:00:00Z",
    )
    assert (r.status, r.basis) == ("NOT_ADMISSIBLE", "NOT_YET_SEEN")


def test_admissibility_case_B_public_unknown_first_seen_before():
    r = _admit("2026-01-03T00:00:00Z", local_first_seen_time="2026-01-02T00:00:00Z")
    assert (r.status, r.basis) == ("ADMISSIBLE", "LOCAL_FIRST_SEEN")


def test_admissibility_case_C_correction_after_cutoff():
    r = _admit("2026-01-03T00:00:00Z", is_correction_after_cutoff=True)
    assert (r.status, r.basis) == ("NOT_ADMISSIBLE", "CORRECTION_AFTER_CUTOFF")


def test_admissibility_case_D_backfill_before_first_seen_cutoff():
    r = _admit(
        "2026-01-01T00:00:00Z",
        local_first_seen_time="2026-01-02T00:00:00Z",
        is_backfilled=True,
    )
    assert r.status == "NOT_ADMISSIBLE"
    assert "BACKFILLED" in r.retained_dq_flags


def test_admissibility_case_E_backfill_after_exact_first_seen_cutoff():
    r = _admit(
        "2026-01-03T00:00:00Z",
        local_first_seen_time="2026-01-02T00:00:00Z",
        is_backfilled=True,
    )
    assert (r.status, r.basis) == ("ADMISSIBLE", "LOCAL_FIRST_SEEN")
    assert "BACKFILLED" in r.retained_dq_flags


def test_admissibility_case_F_source_unavailable_but_persisted_first_seen():
    r = _admit(
        "2026-01-03T00:00:00Z",
        local_first_seen_time="2026-01-02T00:00:00Z",
        source_unavailable=True,
        persisted=True,
    )
    assert r.status == "ADMISSIBLE"
    assert "SOURCE_UNAVAILABLE" in r.retained_dq_flags


def test_admissibility_case_G_source_unavailable_no_observability():
    r = _admit("2026-01-03T00:00:00Z", source_unavailable=True)
    assert (r.status, r.basis) == ("NOT_ADMISSIBLE", "NO_OBSERVABILITY_EVIDENCE")


def test_admissibility_case_H_uncertain_decisive_first_seen():
    r = _admit(
        "2026-01-03T00:00:00Z",
        local_first_seen_time="2026-01-02T00:00:00Z",
        decisive_clock_uncertain=True,
    )
    assert (r.status, r.basis) == ("INDETERMINATE", "TIMESTAMP_UNCERTAIN")


def test_admissibility_case_I_uncertain_event_time_only_with_exact_first_seen():
    r = _admit(
        "2026-01-03T00:00:00Z",
        event_time="2026-01-01T00:00:00Z",
        local_first_seen_time="2026-01-02T00:00:00Z",
        decisive_clock_uncertain=False,
    )
    assert (r.status, r.basis) == ("ADMISSIBLE", "LOCAL_FIRST_SEEN")


def test_admissibility_public_available_path():
    r = _admit("2026-01-03T00:00:00Z", public_available_time="2026-01-02T00:00:00Z")
    assert (r.status, r.basis) == ("ADMISSIBLE", "PUBLIC_AVAILABLE")


def test_admissibility_event_time_alone_never_admissible():
    r = _admit("2026-01-03T00:00:00Z", event_time="2026-01-01T00:00:00Z")
    assert r.status == "NOT_ADMISSIBLE"


def test_observable_at_alias_matches():
    ev = rp.ObservabilityEvidence(local_first_seen_time="2026-01-02T00:00:00Z")
    assert rp.observable_at("2026-01-03T00:00:00Z", ev).status == "ADMISSIBLE"
