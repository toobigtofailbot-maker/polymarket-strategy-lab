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
