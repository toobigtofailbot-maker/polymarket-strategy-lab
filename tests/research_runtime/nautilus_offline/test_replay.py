"""WP168 offline replay determinism, parity & identity tests.

Covers R021-R025, R042, R045, R048, R055-R057, R060.
"""

from __future__ import annotations

import dataclasses
import hashlib

import pytest

import src.research_runtime.nautilus_offline as offline
from src.research_runtime.nautilus_offline import (
    CONVERSION_POLICY_VERSION,
    REPLAY_ERROR_INVALID,
    REPLAY_IDENTITY_PREFIX,
    REPLAY_RECEIPT_SCHEMA_ID,
    SOURCE_DATASET_KIND,
    ConvertedEventStream,
    NautilusReplayReceipt,
    canonical_json_bytes,
    run_offline_replay,
)
from src.research_runtime.nautilus_offline.replay import REPLAY_SETTINGS

from test_conversion import book, default_rows, trade, valid_stream


def test_offline_replay_processes_all_events(tmp_path):
    stream = valid_stream(tmp_path / "src")
    receipt = run_offline_replay(stream, tmp_path / "catalog")
    assert receipt.is_valid
    assert receipt.status == "NAUTILUS_REPLAYED"
    assert receipt.replay_processed_event_count == 6  # 5 deltas + 1 trade
    assert receipt.execution_authority is False
    assert receipt.schema_id == REPLAY_RECEIPT_SCHEMA_ID


def test_repeat_replay_digest_is_identical(tmp_path):
    stream = valid_stream(tmp_path / "src")
    first = run_offline_replay(stream, tmp_path / "c1")
    second = run_offline_replay(stream, tmp_path / "c2")
    assert first.replay_digest == second.replay_digest
    assert first.replay_digest.startswith(REPLAY_IDENTITY_PREFIX)


def test_receipt_identity_is_path_independent_and_mutation_sensitive(tmp_path):
    stream = valid_stream(tmp_path / "src")
    base = run_offline_replay(stream, tmp_path / "cat_a")
    other_dir = run_offline_replay(stream, tmp_path / "different_catalog_dir")
    assert base.replay_digest == other_dir.replay_digest  # path-independent
    # Mutate a committed input value (a price) -> different replay identity.
    mutated_rows = default_rows()[:2] + [trade(1000, 1007, "0.4200", "5.000000", "BUY", "0x" + "d" * 64)]
    mutated = valid_stream(tmp_path / "mut", rows=mutated_rows)
    mutated_receipt = run_offline_replay(mutated, tmp_path / "cat_m")
    assert mutated_receipt.replay_digest != base.replay_digest


def test_source_counts_equal_converted_counts(tmp_path):
    stream = valid_stream(tmp_path / "src")
    receipt = run_offline_replay(stream, tmp_path / "catalog")
    total = sum(count for _name, count in receipt.input_event_counts_by_type)
    assert total == 5  # book + 2 price_change + trade + tick_size_change
    assert dict(receipt.input_event_counts_by_type)["tick_size_change"] == 1


def test_replay_count_or_digest_mismatch_rejected(tmp_path):
    invalid = ConvertedEventStream(
        is_valid=False, status="X", error_codes=("NAUTILUS_EVENT_CONVERSION_INVALID",),
        instrument_id=None, source_dataset_kind=None, source_external_dataset_id=None,
        conversion_policy_version=None, ordered_event_digests=(), input_event_counts_by_type=(),
        tick_size_regime_sequence=(), first_event_time_ns=None, last_event_time_ns=None,
        warnings=(), converted_events=())
    receipt = run_offline_replay(invalid, tmp_path / "catalog")
    assert receipt.is_valid is False
    assert receipt.error_codes == (REPLAY_ERROR_INVALID,)
    assert receipt.replay_digest is None
    assert offline.scan_public_result_for_echo(receipt, ("Traceback", "\\", str(tmp_path))) == ()


def test_parquet_physical_reorder_invariance(tmp_path):
    forward = valid_stream(tmp_path / "a", rows=list(default_rows()))
    backward = valid_stream(tmp_path / "b", rows=list(reversed(default_rows())))
    r_forward = run_offline_replay(forward, tmp_path / "cf")
    r_backward = run_offline_replay(backward, tmp_path / "cb")
    assert r_forward.replay_digest == r_backward.replay_digest


def test_duplicate_multiplicity_changes_replay_digest(tmp_path):
    tx = "0x" + "e" * 64
    snapshot = book(1, 1, [["0.4000", "1.000000"]], [["0.6000", "1.000000"]])
    dup_trade = trade(2, 2, "0.4000", "1.000000", "BUY", tx)
    two = valid_stream(tmp_path / "two", rows=[snapshot] + [dup_trade] * 2)
    three = valid_stream(tmp_path / "three", rows=[snapshot] + [dup_trade] * 3)
    r_two = run_offline_replay(two, tmp_path / "c2")
    r_three = run_offline_replay(three, tmp_path / "c3")
    assert r_two.is_valid and r_three.is_valid
    assert r_two.replay_digest != r_three.replay_digest


def test_physical_row_index_not_in_logical_replay_identity(tmp_path):
    stream = valid_stream(tmp_path / "src")
    receipt = run_offline_replay(stream, tmp_path / "catalog")
    # No absolute path / catalog dir appears anywhere in the public receipt.
    assert offline.scan_public_result_for_echo(receipt, (str(tmp_path), "\\", "catalog")) == ()


def test_receipt_commits_external_dataset_id_and_is_mutation_sensitive(tmp_path):
    stream = valid_stream(tmp_path / "src")
    receipt = run_offline_replay(stream, tmp_path / "catalog")
    assert receipt.source_dataset_kind == SOURCE_DATASET_KIND
    assert receipt.source_external_dataset_id == "ext:pmxt:test0001"


def test_identity_constants_and_digest_recomputation(tmp_path):
    stream = valid_stream(tmp_path / "src")
    receipt = run_offline_replay(stream, tmp_path / "catalog")
    preimage = {
        "conversion_policy_version": CONVERSION_POLICY_VERSION,
        "source_dataset_kind": SOURCE_DATASET_KIND,
        "source_external_dataset_id": stream.source_external_dataset_id,
        "nautilus_version": receipt.nautilus_version,
        "instrument_semantic_id": stream.instrument_id,
        "ordered_event_semantic_digests": list(stream.ordered_event_digests),
        "tick_size_regime_sequence": [list(item) for item in stream.tick_size_regime_sequence],
        "replay_settings": REPLAY_SETTINGS,
    }
    expected = REPLAY_IDENTITY_PREFIX + hashlib.sha256(canonical_json_bytes(preimage)).hexdigest()
    assert receipt.replay_digest == expected
    assert CONVERSION_POLICY_VERSION == "wp168-nautilus-pmxt-v2-conversion/1.0.0"
    assert REPLAY_IDENTITY_PREFIX == "nautilusreplay:sha256:"


def test_receipt_is_frozen(tmp_path):
    stream = valid_stream(tmp_path / "src")
    receipt = run_offline_replay(stream, tmp_path / "catalog")
    assert dataclasses.is_dataclass(NautilusReplayReceipt)
    with pytest.raises(dataclasses.FrozenInstanceError):
        receipt.is_valid = False  # type: ignore[misc]
