"""WP175N append-only Alpha Factory registry: schema, hash chain, atomic append."""

from __future__ import annotations

import dataclasses
import sqlite3

import pytest

from src.data_layer.analytical_research import alpha_factory as af
from src.data_layer.analytical_research import alpha_factory_registry as afr
from src.data_layer.analytical_research import experiment_registry as wp170_registry
from tests.data_layer.analytical_research.test_alpha_factory_records import (
    candidate_input,
    episode_input,
    family_input,
    source_input,
)


# ── record helpers with correct cross-references ─────────────────────────────
def mk_source(title="Rules"):
    r = af.build_research_source_reference(source_input(title=title, source_locator=f"https://docs.polymarket.com/{title}"))
    assert r.is_valid, r.error_codes
    return r.record


def mk_candidate(scope="nfl-2026", mechanism="cold-scoring", subject="nfl"):
    r = af.build_opportunity_candidate(
        candidate_input(
            scope_key=scope, mechanism_hint=f"hint {mechanism}",
            novelty_dimensions={"subject_keys": [subject], "scope_key": scope, "mechanism_key": mechanism},
        )
    )
    assert r.is_valid, r.error_codes
    return r.record


def mk_family(mechanism="cold-scoring", predecessor=None, name="Family", dims=None):
    r = af.build_hypothesis_family(
        family_input(
            family_name=name, mechanism_key=mechanism, predecessor_family_id=predecessor,
            mechanism_dimensions=dims or {"driver": mechanism},
        )
    )
    assert r.is_valid, r.error_codes
    return r.record


def mk_episode(candidate, family, source, *, state="RESEARCH_SUPPORTIVE", predecessor=None, reopened=None, scope=None):
    over = dict(
        candidate_id=candidate.candidate_id,
        hypothesis_family_id=family.hypothesis_family_id,
        source_reference_ids=[source.source_reference_id],
        result_state=state,
        predecessor_episode_id=predecessor,
        reopened_episode_id=reopened,
        evidence_for=["ef"], evidence_against=["ea"], known_missing_data=["km"],
        what_would_change_the_conclusion=["wc"], material_change_basis=["mc"],
        deterministic_evidence_refs=["det-1"],
    )
    if scope is not None:
        over["exact_scope"] = scope
    r = af.build_research_episode(episode_input(**over))
    assert r.is_valid, r.error_codes
    return r.record


def fresh(tmp_path, name="af.sqlite3"):
    path = tmp_path / name
    result = afr.initialize_alpha_factory_registry(str(path))
    assert result.is_valid, result.error_codes
    return str(path)


# ── R023 application id uniqueness ───────────────────────────────────────────
def test_application_id_is_frozen_and_distinct_from_wp170():
    assert afr.ALPHA_REGISTRY_APPLICATION_ID == 1464877425
    assert afr.ALPHA_REGISTRY_APPLICATION_ID != wp170_registry.REGISTRY_APPLICATION_ID
    assert afr.ALPHA_REGISTRY_FORMAT_ID == "s10-alpha-factory-registry"
    assert afr.ALPHA_REGISTRY_SCHEMA_VERSION == 1


def test_db_pragmas_match_contract(tmp_path):
    path = fresh(tmp_path)
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("PRAGMA application_id").fetchone() == (1464877425,)
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("delete",)
    finally:
        connection.close()


# ── R024 registry schema ─────────────────────────────────────────────────────
def test_exact_object_set(tmp_path):
    path = fresh(tmp_path)
    connection = sqlite3.connect(path)
    try:
        objects = connection.execute(
            "SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ).fetchall()
    finally:
        connection.close()
    assert objects == [
        ("table", "alpha_registry_meta"),
        ("table", "alpha_registry_records"),
        ("trigger", "alpha_registry_records_no_delete"),
        ("trigger", "alpha_registry_records_no_update"),
    ]


def test_append_only_triggers_block_update_and_delete(tmp_path):
    path = fresh(tmp_path)
    src = mk_source()
    afr.append_alpha_factory_records(path, [src])
    connection = sqlite3.connect(path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE alpha_registry_records SET record_id='x'")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM alpha_registry_records")
    finally:
        connection.close()


# ── R025 exclusive init ──────────────────────────────────────────────────────
def test_reinitialize_reports_already_initialized(tmp_path):
    path = fresh(tmp_path)
    assert afr.initialize_alpha_factory_registry(path).status == "REGISTRY_ALREADY_INITIALIZED"


def test_append_to_missing_path_rejects_without_creating(tmp_path):
    path = str(tmp_path / "missing.sqlite3")
    result = afr.append_alpha_factory_records(path, [mk_source()])
    assert not result.is_valid and result.error_codes[0] == "REGISTRY_SCHEMA_CONFLICT"
    assert not (tmp_path / "missing.sqlite3").exists()


def test_path_contract_rejects_non_sqlite3_suffix(tmp_path):
    result = afr.initialize_alpha_factory_registry(str(tmp_path / "store.db"))
    assert not result.is_valid


# ── R026 foreign db fail closed ──────────────────────────────────────────────
def test_foreign_db_rejected_and_not_overwritten(tmp_path):
    path = tmp_path / "foreign.sqlite3"
    connection = sqlite3.connect(str(path))
    try:
        connection.execute("CREATE TABLE unrelated (x INTEGER)")
        connection.commit()
    finally:
        connection.close()
    before = path.read_bytes()
    result = afr.initialize_alpha_factory_registry(str(path))
    assert not result.is_valid and result.error_codes[0] == "REGISTRY_SCHEMA_CONFLICT"
    assert path.read_bytes() == before


# ── R027 hash chain tamper ───────────────────────────────────────────────────
@pytest.mark.parametrize("mutation", ["payload", "entry_hash", "previous", "sequence"])
def test_hash_chain_tamper_detected(tmp_path, mutation):
    path = fresh(tmp_path)
    src, cand = mk_source(), mk_candidate()
    afr.append_alpha_factory_records(path, [src, cand])
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA writable_schema=OFF")
        if mutation == "payload":
            connection.execute("UPDATE alpha_registry_records SET payload_json=payload_json||' ' WHERE sequence_number=0")
        elif mutation == "entry_hash":
            connection.execute("UPDATE alpha_registry_records SET entry_hash='alpharegistryentry:sha256:'||substr(entry_hash,27) WHERE sequence_number=1")
        elif mutation == "previous":
            connection.execute("UPDATE alpha_registry_records SET previous_entry_hash=NULL WHERE sequence_number=1")
        else:
            connection.execute("UPDATE alpha_registry_records SET sequence_number=5 WHERE sequence_number=1")
        connection.commit()
    except sqlite3.IntegrityError:
        # Append-only triggers block the tamper entirely — also acceptable.
        connection.close()
        return
    finally:
        connection.close()
    result = afr.load_and_verify_alpha_factory_registry(path)
    assert not result.is_valid and result.error_codes[0] == "REGISTRY_INTEGRITY_TAMPER"


# ── R028 load read-only ──────────────────────────────────────────────────────
def test_load_does_not_alter_file_bytes(tmp_path):
    path = fresh(tmp_path)
    afr.append_alpha_factory_records(path, [mk_source(), mk_candidate()])
    import pathlib

    before = pathlib.Path(path).read_bytes()
    result = afr.load_and_verify_alpha_factory_registry(path)
    assert result.is_valid
    assert pathlib.Path(path).read_bytes() == before


# ── R029 caller-order-independent append ─────────────────────────────────────
def test_batch_permutations_yield_identical_head(tmp_path):
    src, cand, fam = mk_source(), mk_candidate(), mk_family()
    ep = mk_episode(cand, fam, src)
    heads = set()
    inserted_sets = set()
    for index, order in enumerate(([src, cand, fam, ep], [ep, fam, cand, src], [fam, ep, src, cand])):
        path = fresh(tmp_path, f"perm_{index}.sqlite3")
        result = afr.append_alpha_factory_records(path, order)
        assert result.is_valid, result.error_codes
        heads.add(result.snapshot.head_entry_hash)
        inserted_sets.add(result.inserted_record_ids)
    assert len(heads) == 1
    assert len(inserted_sets) == 1


# ── R030 projected cross references ──────────────────────────────────────────
def test_same_batch_dependencies_resolve_regardless_of_order(tmp_path):
    src, cand, fam = mk_source(), mk_candidate(), mk_family()
    ep = mk_episode(cand, fam, src)
    path = fresh(tmp_path)
    # Episode listed first, before its candidate/family/source in the same batch.
    result = afr.append_alpha_factory_records(path, [ep, src, fam, cand])
    assert result.is_valid and result.snapshot.total_rows == 4


def test_episode_without_resolvable_candidate_rejected(tmp_path):
    src, cand, fam = mk_source(), mk_candidate(), mk_family()
    ep = mk_episode(cand, fam, src)
    path = fresh(tmp_path)
    result = afr.append_alpha_factory_records(path, [ep, src, fam])  # candidate missing
    assert not result.is_valid and result.error_codes[0] == "REFERENCE_INVALID"


# ── R031 cycle rejection ─────────────────────────────────────────────────────
def test_family_predecessor_missing_rejected(tmp_path):
    fam = mk_family(predecessor="alphafamily:sha256:" + "9" * 64)
    path = fresh(tmp_path)
    result = afr.append_alpha_factory_records(path, [fam])
    assert not result.is_valid and result.error_codes[0] == "LINEAGE_INVALID"


# ── R032 exact duplicate idempotent ──────────────────────────────────────────
def test_exact_duplicate_is_idempotent(tmp_path):
    path = fresh(tmp_path)
    src, cand = mk_source(), mk_candidate()
    first = afr.append_alpha_factory_records(path, [src, cand])
    head_before = first.snapshot.head_entry_hash
    again = afr.append_alpha_factory_records(path, [src, cand])
    assert again.status == "REGISTRY_APPEND_IDEMPOTENT"
    assert again.snapshot.total_rows == 2
    assert again.snapshot.head_entry_hash == head_before
    assert set(again.idempotent_record_ids) == {src.source_reference_id, cand.candidate_id}


def test_in_batch_exact_duplicate_collapses(tmp_path):
    path = fresh(tmp_path)
    src = mk_source()
    result = afr.append_alpha_factory_records(path, [src, src])
    assert result.is_valid and result.snapshot.total_rows == 1


# ── R033 same-id conflict atomic reject ──────────────────────────────────────
def test_mutated_record_rejected_atomically(tmp_path):
    path = fresh(tmp_path)
    cand = mk_candidate()
    afr.append_alpha_factory_records(path, [cand])
    forged = dataclasses.replace(cand, title="TAMPERED")  # keeps candidate_id, changes content
    result = afr.append_alpha_factory_records(path, [forged])
    assert not result.is_valid
    assert result.error_codes[0] in {"IDENTITY_DERIVATION_MISMATCH", "REGISTRY_IDENTITY_CONFLICT"}
    reload = afr.load_and_verify_alpha_factory_registry(path)
    assert reload.snapshot.total_rows == 1


# ── R034 novelty global uniqueness (existing + projected) ────────────────────
def test_novelty_duplicate_against_existing_history(tmp_path):
    path = fresh(tmp_path)
    cand = mk_candidate()
    afr.append_alpha_factory_records(path, [cand])
    twin = af.build_opportunity_candidate(
        candidate_input(
            scope_key="nfl-2026", mechanism_hint="hint cold-scoring",
            novelty_dimensions={"subject_keys": ["nfl"], "scope_key": "nfl-2026", "mechanism_key": "cold-scoring"},
            title="A DIFFERENT WORDING", thesis="different", research_question="different?",
        )
    ).record
    assert twin.novelty_fingerprint == cand.novelty_fingerprint and twin.candidate_id != cand.candidate_id
    result = afr.append_alpha_factory_records(path, [twin])
    assert not result.is_valid and result.error_codes[0] == "NOVELTY_DUPLICATE"


def test_novelty_duplicate_within_same_batch(tmp_path):
    path = fresh(tmp_path)
    a = mk_candidate()
    b = af.build_opportunity_candidate(
        candidate_input(
            scope_key="nfl-2026", mechanism_hint="hint cold-scoring",
            novelty_dimensions={"subject_keys": ["nfl"], "scope_key": "nfl-2026", "mechanism_key": "cold-scoring"},
            title="Different", thesis="d", research_question="d?",
        )
    ).record
    result = afr.append_alpha_factory_records(path, [a, b])
    assert not result.is_valid and result.error_codes[0] == "NOVELTY_DUPLICATE"
    assert afr.load_and_verify_alpha_factory_registry(path).snapshot.total_rows == 0


# ── R035 mechanism global uniqueness ─────────────────────────────────────────
def test_mechanism_conflict_against_existing_history(tmp_path):
    path = fresh(tmp_path)
    fam = mk_family()
    afr.append_alpha_factory_records(path, [fam])
    twin = mk_family(name="Different name")  # same mechanism_key + dims → same fingerprint
    assert twin.mechanism_fingerprint == fam.mechanism_fingerprint and twin.hypothesis_family_id != fam.hypothesis_family_id
    result = afr.append_alpha_factory_records(path, [twin])
    assert not result.is_valid and result.error_codes[0] == "MECHANISM_CONFLICT"


# ── R036 batch atomicity ─────────────────────────────────────────────────────
def test_one_bad_record_rolls_back_whole_batch(tmp_path):
    path = fresh(tmp_path)
    src, cand = mk_source(), mk_candidate()
    afr.append_alpha_factory_records(path, [src])
    head_before = afr.load_and_verify_alpha_factory_registry(path).snapshot.head_entry_hash
    # Batch: one good candidate + one unresolvable episode.
    orphan_ep = af.build_research_episode(
        episode_input(
            candidate_id="alphacandidate:sha256:" + "0" * 64,
            hypothesis_family_id="alphafamily:sha256:" + "1" * 64,
            source_reference_ids=[src.source_reference_id],
        )
    ).record
    result = afr.append_alpha_factory_records(path, [cand, orphan_ep])
    assert not result.is_valid
    after = afr.load_and_verify_alpha_factory_registry(path)
    assert after.snapshot.total_rows == 1
    assert after.snapshot.head_entry_hash == head_before


# ── Finding A/B: independent-id forgery helpers ───────────────────────────────
import dataclasses  # noqa: E402
import hashlib as _hashlib  # noqa: E402
import json as _json  # noqa: E402

from tests.data_layer.analytical_research.test_alpha_factory_identity import (  # noqa: E402
    independent_id,
    _KIND_PREFIX_ID,
)


def forge(record, **overrides):
    """Override fields and recompute the content ID so the record is identity-consistent.

    The result matches its own content ID but may be semantically invalid, proving
    semantic rejection rather than a mere identity mismatch.
    """
    _kind, _prefix, id_field = _KIND_PREFIX_ID[type(record)]
    mutated = dataclasses.replace(record, **overrides)
    return dataclasses.replace(mutated, **{id_field: independent_id(mutated)})


def _append_one(tmp_path, record, name="forge.sqlite3"):
    path = fresh(tmp_path, name)
    return afr.append_alpha_factory_records(path, [record])


# ── S-series: identity-consistent but semantically invalid records rejected ───
def test_s01_supportive_empty_evidence_for_rejected(tmp_path):
    ep = mk_episode(mk_candidate(), mk_family(), mk_source(), state="RESEARCH_SUPPORTIVE")
    r = _append_one(tmp_path, forge(ep, evidence_for=()))
    assert not r.is_valid and r.error_codes[0] == "RESULT_EVIDENCE_INVALID"


def test_s02_hermes_null_receipt_rejected(tmp_path):
    ep = af.build_research_episode(
        episode_input(producer_type="HERMES_CONTROLLED_RESEARCH", producer_receipt_ref="rcpt-1")
    ).record
    r = _append_one(tmp_path, forge(ep, producer_receipt_ref=None))
    assert not r.is_valid and r.error_codes[0] == "RESULT_EVIDENCE_INVALID"


def test_s03_human_no_source_refs_rejected(tmp_path):
    ep = mk_episode(mk_candidate(), mk_family(), mk_source())
    r = _append_one(tmp_path, forge(ep, source_reference_ids=()))
    assert not r.is_valid and r.error_codes[0] == "RESULT_EVIDENCE_INVALID"


def test_s04_execution_uneconomic_no_det_refs_rejected(tmp_path):
    ep = mk_episode(mk_candidate(), mk_family(), mk_source(), state="EXECUTION_UNECONOMIC")
    r = _append_one(tmp_path, forge(ep, deterministic_evidence_refs=()))
    assert not r.is_valid and r.error_codes[0] == "RESULT_EVIDENCE_INVALID"


def test_s05_non_reopen_with_reopened_rejected(tmp_path):
    ep = mk_episode(mk_candidate(), mk_family(), mk_source())
    r = _append_one(tmp_path, forge(ep, reopened_episode_id="alphaepisode:sha256:" + "d" * 64))
    assert not r.is_valid and r.error_codes[0] == "REOPEN_INVALID"


def test_s06_reopen_without_material_change_rejected(tmp_path):
    ep = mk_episode(mk_candidate(), mk_family(), mk_source(), state="REOPEN_TRIGGERED",
                    reopened="alphaepisode:sha256:" + "d" * 64)
    r = _append_one(tmp_path, forge(ep, material_change_basis=()))
    assert not r.is_valid and r.error_codes[0] == "RESULT_EVIDENCE_INVALID"


def test_s07_invalid_research_as_of_rejected(tmp_path):
    ep = mk_episode(mk_candidate(), mk_family(), mk_source())
    r = _append_one(tmp_path, forge(ep, research_as_of="not-a-timestamp"))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s08_duplicate_evidence_text_rejected(tmp_path):
    ep = mk_episode(mk_candidate(), mk_family(), mk_source())
    r = _append_one(tmp_path, forge(ep, evidence_for=("dup", "dup")))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s09_unsorted_source_refs_rejected(tmp_path):
    ep = mk_episode(mk_candidate(), mk_family(), mk_source())
    r = _append_one(tmp_path, forge(ep, source_reference_ids=("id-b", "id-a")))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s10_human_review_non_bool_rejected(tmp_path):
    ep = mk_episode(mk_candidate(), mk_family(), mk_source())
    r = _append_one(tmp_path, forge(ep, human_review_required=1))
    assert not r.is_valid and r.error_codes[0] == "FIELD_TYPE_INVALID"


def test_s11_candidate_scope_disagreement_rejected(tmp_path):
    cand = mk_candidate()
    r = _append_one(tmp_path, forge(cand, scope_key="a-different-scope"))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s12_candidate_novelty_extra_key_rejected(tmp_path):
    cand = mk_candidate()
    bad = _json.dumps(
        {"subject_keys": ["nfl"], "scope_key": "nfl-2026", "mechanism_key": "cold-scoring", "extra": 1},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    r = _append_one(tmp_path, forge(cand, novelty_dimensions_json=bad))
    assert not r.is_valid and r.error_codes[0] in {"FIELD_VALUE_INVALID", "REGISTRY_IDENTITY_CONFLICT"}


def test_s13_candidate_unsorted_subject_refs_rejected(tmp_path):
    cand = mk_candidate()
    r = _append_one(tmp_path, forge(cand, subject_refs=("z-sub", "a-sub")))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s14_candidate_human_review_non_bool_rejected(tmp_path):
    cand = mk_candidate()
    r = _append_one(tmp_path, forge(cand, human_review_required="yes"))
    assert not r.is_valid and r.error_codes[0] == "FIELD_TYPE_INVALID"


def test_s15_family_pathlike_predecessor_rejected(tmp_path):
    fam = mk_family()
    r = _append_one(tmp_path, forge(fam, predecessor_family_id="../evil"))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s16_family_noncanonical_mechanism_json_rejected(tmp_path):
    fam = mk_family()
    r = _append_one(tmp_path, forge(fam, mechanism_dimensions_json='{"b":1,"a":2}'))
    assert not r.is_valid and r.error_codes[0] in {"FIELD_VALUE_INVALID", "REGISTRY_IDENTITY_CONFLICT"}


def test_s17_family_invalid_provenance_rejected(tmp_path):
    fam = mk_family()
    r = _append_one(tmp_path, forge(fam, creation_provenance="   "))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s18_family_human_review_non_bool_rejected(tmp_path):
    fam = mk_family()
    r = _append_one(tmp_path, forge(fam, human_review_required=0))
    assert not r.is_valid and r.error_codes[0] == "FIELD_TYPE_INVALID"


def test_s19_source_blockchain_wrong_class_rejected(tmp_path):
    src = af.build_research_source_reference(
        source_input(source_kind="PUBLIC_BLOCKCHAIN", source_class="PUBLIC_BLOCKCHAIN", source_locator="tx:abc")
    ).record
    r = _append_one(tmp_path, forge(src, source_class="OFFICIAL"))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s20_source_repo_evidence_wrong_class_rejected(tmp_path):
    src = af.build_research_source_reference(
        source_input(source_kind="REPO_EVIDENCE_ID", source_class="REPO_EVIDENCE", source_locator="evidence-9")
    ).record
    r = _append_one(tmp_path, forge(src, source_class="NEWS"))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s21_source_https_blockchain_class_rejected(tmp_path):
    src = mk_source()
    r = _append_one(tmp_path, forge(src, source_class="PUBLIC_BLOCKCHAIN"))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s22_source_invalid_observed_at_rejected(tmp_path):
    src = mk_source()
    r = _append_one(tmp_path, forge(src, observed_at="2026-13-99T99:99:99Z"))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s23_source_invalid_content_sha_rejected(tmp_path):
    src = mk_source()
    r = _append_one(tmp_path, forge(src, content_sha256="XYZ"))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s24_source_noncanonical_https_locator_rejected(tmp_path):
    src = mk_source()
    r = _append_one(tmp_path, forge(src, source_locator="https://DOCS.Polymarket.com/Rules"))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_s25_valid_records_append_and_load(tmp_path):
    path = fresh(tmp_path)
    src, cand, fam = mk_source(), mk_candidate(), mk_family()
    ep = mk_episode(cand, fam, src)
    r = afr.append_alpha_factory_records(path, [src, cand, fam, ep])
    assert r.is_valid and r.snapshot.total_rows == 4
    assert afr.load_and_verify_alpha_factory_registry(path).is_valid


# ── Blocker B2: identity-self-consistent load-time semantic-corruption oracle ──
# Independent test-side canonical JSON / entry hash / record mapping — these never
# call production _semantic_preimage/_digest/_entry_hash/record_to_mapping, so the
# oracle proves semantic revalidation (not identity or hash mismatch) blocks load.
_KIND_FOR_TYPE = {t: k for k, t, _idf in afr.RECORD_KIND_TYPES}
_ID_FIELD_FOR_KIND = {k: idf for k, _t, idf in afr.RECORD_KIND_TYPES}


def _indep_canon(value) -> str:
    return _json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _indep_entry_hash(sequence, kind, record_id, payload_sha, previous):
    preimage = {
        "sequence_number": sequence, "record_kind": kind, "record_id": record_id,
        "payload_sha256": payload_sha, "previous_entry_hash": previous,
    }
    wrapped = {"alpha_registry_entry.identity_preimage": preimage}
    return "alpharegistryentry:sha256:" + _hashlib.sha256(_indep_canon(wrapped).encode("utf-8")).hexdigest()


def _indep_mapping(record) -> dict:
    return {
        field.name: (list(getattr(record, field.name)) if isinstance(getattr(record, field.name), tuple) else getattr(record, field.name))
        for field in dataclasses.fields(record)
    }


def _with_recomputed_id(record):
    """Return (record, mapping) with the content-addressed id recomputed after mutation."""
    _kind, _prefix, id_field = _KIND_PREFIX_ID[type(record)]
    fixed = dataclasses.replace(record, **{id_field: independent_id(record)})
    return fixed, _indep_mapping(fixed)


def _insert_chain(path, records_in_order):
    """Insert records as a self-consistent hash chain built entirely test-side."""
    conn = sqlite3.connect(path)
    try:
        previous = None
        for sequence, record in enumerate(records_in_order):
            kind = _KIND_FOR_TYPE[type(record)]
            mapping = _indep_mapping(record)
            record_id = mapping[_ID_FIELD_FOR_KIND[kind]]
            payload = _indep_canon(mapping)
            payload_sha = _hashlib.sha256(payload.encode("utf-8")).hexdigest()
            entry_hash = _indep_entry_hash(sequence, kind, record_id, payload_sha, previous)
            # Prove cryptographic + identity self-consistency before load.
            assert _hashlib.sha256(payload.encode("utf-8")).hexdigest() == payload_sha
            assert record_id == independent_id(record)
            conn.execute(
                "INSERT INTO alpha_registry_records(sequence_number,record_kind,record_id,payload_json,payload_sha256,previous_entry_hash,entry_hash) VALUES (?,?,?,?,?,?,?)",
                (sequence, kind, record_id, payload, payload_sha, previous, entry_hash),
            )
            previous = entry_hash
        conn.commit()
    finally:
        conn.close()


def test_load_semantic_corruption_episode_is_tamper(tmp_path):
    path = fresh(tmp_path)
    # Valid supporting graph so no cross-record reference failure can mask the oracle.
    src, cand, fam = mk_source(), mk_candidate(), mk_family()
    valid_ep = mk_episode(cand, fam, src)
    # Mutate ONE semantic field, then recompute the content id from the mutated record.
    mutated = dataclasses.replace(valid_ep, falsification_checks_performed=())
    fixed_ep, _mapping = _with_recomputed_id(mutated)
    assert fixed_ep.research_episode_id == independent_id(mutated)          # EPI-04
    assert fixed_ep.research_episode_id != valid_ep.research_episode_id     # EPI-05
    _insert_chain(path, [src, cand, fam, fixed_ep])
    r = afr.load_and_verify_alpha_factory_registry(path)
    assert not r.is_valid and r.error_codes[0] == "REGISTRY_INTEGRITY_TAMPER"


def test_load_semantic_corruption_non_episode_is_tamper(tmp_path):
    path = fresh(tmp_path)
    fam = mk_family()
    mutated = dataclasses.replace(fam, creation_provenance="   ")  # invalid whitespace-only
    fixed_fam, _mapping = _with_recomputed_id(mutated)
    assert fixed_fam.hypothesis_family_id == independent_id(mutated)
    assert fixed_fam.hypothesis_family_id != fam.hypothesis_family_id
    _insert_chain(path, [fixed_fam])
    r = afr.load_and_verify_alpha_factory_registry(path)
    assert not r.is_valid and r.error_codes[0] == "REGISTRY_INTEGRITY_TAMPER"


def test_load_corruption_control_valid_chain_loads(tmp_path):
    # Control: the same independent raw-insertion path with VALID records loads cleanly,
    # proving the tamper result above is caused only by the injected semantic defect.
    path = fresh(tmp_path)
    src, cand, fam = mk_source(), mk_candidate(), mk_family()
    ep = mk_episode(cand, fam, src)
    _insert_chain(path, [src, cand, fam, ep])
    r = afr.load_and_verify_alpha_factory_registry(path)
    assert r.is_valid and r.snapshot.total_rows == 4


# ── Finding C: exhaustive registry error mapping (E-series) ───────────────────
def test_e01_mapper_keyset_exact():
    assert set(afr._ALPHA_TO_REGISTRY_ERROR) == set(af.ALPHA_ERROR_CODES)


def test_e02_mapper_values_are_registry_codes():
    for code, mapped in afr._ALPHA_TO_REGISTRY_ERROR.items():
        assert mapped in afr.ALPHA_REGISTRY_ERROR_CODES, code


def test_e03_unknown_code_maps_to_internal():
    assert afr._map_alpha_error("SOME_FUTURE_CODE") == "INTERNAL_VALIDATION_FAILED"


def test_e04_reject_closes_unknown_code():
    assert afr._reject("not-a-real-code").error_codes == ("INTERNAL_VALIDATION_FAILED",)


def test_e06_identity_mismatch_maps_to_conflict(tmp_path):
    cand = mk_candidate()
    wrong = dataclasses.replace(cand, candidate_id="alphacandidate:sha256:" + "0" * 64)
    r = _append_one(tmp_path, wrong)
    assert not r.is_valid and r.error_codes[0] == "REGISTRY_IDENTITY_CONFLICT"


def test_e07_schema_unsupported_maps_to_field_value_invalid(tmp_path):
    cand = mk_candidate()
    r = _append_one(tmp_path, forge(cand, schema_id="wrong-schema-id"))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_e08_forbidden_content_maps_to_field_value_invalid(tmp_path):
    fam = mk_family()
    r = _append_one(tmp_path, forge(fam, mechanism_dimensions_json='{"api_key":"x"}'))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_e09_lane_invalid_maps_to_field_value_invalid(tmp_path):
    cand = mk_candidate()
    r = _append_one(tmp_path, forge(cand, evidence_lanes=("NOT_A_LANE",)))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_e10_result_state_invalid_maps_to_field_value_invalid(tmp_path):
    ep = mk_episode(mk_candidate(), mk_family(), mk_source())
    r = _append_one(tmp_path, forge(ep, result_state="BOGUS_STATE"))
    assert not r.is_valid and r.error_codes[0] == "FIELD_VALUE_INVALID"


def test_e11_same_id_different_payload_conflict(tmp_path):
    path = fresh(tmp_path)
    cand = mk_candidate()
    afr.append_alpha_factory_records(path, [cand])
    tampered = dataclasses.replace(cand, title="DIFFERENT")  # same id, different content
    r = afr.append_alpha_factory_records(path, [tampered])
    assert not r.is_valid and r.error_codes[0] == "REGISTRY_IDENTITY_CONFLICT"


def test_e13_public_result_only_closed_codes_no_echo(tmp_path):
    cand = mk_candidate()
    r = _append_one(tmp_path, forge(cand, title="   "))
    assert not r.is_valid
    assert all(code in afr.ALPHA_REGISTRY_ERROR_CODES for code in r.error_codes)
    assert r.snapshot is None and r.inserted_record_ids == () and r.idempotent_record_ids == ()


# ── Blocker B3: exact frozen Alpha->registry error mapping oracle ─────────────
_EXPECTED_ERROR_MAP = {
    "SCHEMA_UNSUPPORTED": "FIELD_VALUE_INVALID",
    "FIELD_MISSING": "FIELD_VALUE_INVALID",
    "FIELD_TYPE_INVALID": "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID": "FIELD_VALUE_INVALID",
    "FORBIDDEN_CONTENT": "FIELD_VALUE_INVALID",
    "IDENTITY_DERIVATION_MISMATCH": "REGISTRY_IDENTITY_CONFLICT",
    "REFERENCE_INVALID": "REFERENCE_INVALID",
    "LANE_INVALID": "FIELD_VALUE_INVALID",
    "RESULT_STATE_INVALID": "FIELD_VALUE_INVALID",
    "NOVELTY_DUPLICATE": "NOVELTY_DUPLICATE",
    "MECHANISM_CONFLICT": "MECHANISM_CONFLICT",
    "LINEAGE_INVALID": "LINEAGE_INVALID",
    "LINEAGE_CYCLE": "LINEAGE_CYCLE",
    "REOPEN_INVALID": "REOPEN_INVALID",
    "RESULT_EVIDENCE_INVALID": "RESULT_EVIDENCE_INVALID",
    "LIMIT_EXCEEDED": "LIMIT_EXCEEDED",
    "INTERNAL_VALIDATION_FAILED": "INTERNAL_VALIDATION_FAILED",
}


def test_map01_expected_keyset_equals_alpha_error_codes():
    assert set(_EXPECTED_ERROR_MAP) == set(af.ALPHA_ERROR_CODES)


def test_map02_production_table_equals_frozen_expected_table():
    assert afr._ALPHA_TO_REGISTRY_ERROR == _EXPECTED_ERROR_MAP


@pytest.mark.parametrize("alpha_code,registry_code", sorted(_EXPECTED_ERROR_MAP.items()))
def test_map02b_each_alpha_code_maps_to_exact_registry_code(alpha_code, registry_code):
    assert afr._map_alpha_error(alpha_code) == registry_code


def test_map03_unknown_code_maps_to_internal():
    assert afr._map_alpha_error("A_FUTURE_UNMAPPED_CODE") == "INTERNAL_VALIDATION_FAILED"


def test_map04_reject_final_closure_cannot_expose_unknown():
    assert afr._reject("A_FUTURE_UNMAPPED_CODE").error_codes == ("INTERNAL_VALIDATION_FAILED",)


def test_map05_every_expected_value_is_registry_code():
    for value in _EXPECTED_ERROR_MAP.values():
        assert value in afr.ALPHA_REGISTRY_ERROR_CODES
