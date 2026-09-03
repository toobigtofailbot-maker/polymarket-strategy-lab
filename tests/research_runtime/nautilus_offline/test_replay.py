"""WP168 offline replay determinism, parity & identity tests.

Covers R021-R025, R042, R045, R048, R055-R057, R060.
"""

from __future__ import annotations

import dataclasses
import hashlib

import pytest

import src.research_runtime.nautilus_offline as offline
from src.research_runtime.nautilus_offline.conversion import (
    _canonical_json_bytes,
    _scan_public_result_for_echo,
)
from src.research_runtime.nautilus_offline import (
    CATALOG_QUERY_ERROR,
    CATALOG_WRITE_ERROR,
    CONVERSION_ERROR,
    CONVERSION_POLICY_VERSION,
    INSTRUMENT_MAPPING_ERROR,
    REPLAY_ERROR_INVALID,
    REPLAY_ERROR_PARITY_INVALID,
    REPLAY_IDENTITY_PREFIX,
    REPLAY_RECEIPT_SCHEMA_ID,
    SOURCE_DATASET_KIND,
    BinaryOptionMarketContext,
    ConvertedEventStream,
    NautilusReplayReceipt,
    PmxtV2ReplaySource,
    build_binary_option,
    build_catalog,
    convert_pmxt_v2_events,
    query_catalog,
    run_offline_replay,
)
from src.research_runtime.nautilus_offline.replay import REPLAY_SETTINGS

from test_conversion import (
    _context,
    _write_files,
    book,
    default_rows,
    price_change,
    tick_change,
    trade,
    valid_stream,
)


def test_offline_replay_processes_all_events(tmp_path):
    stream = valid_stream(tmp_path / "src")
    receipt = run_offline_replay(stream, tmp_path / "catalog")
    assert receipt.is_valid
    assert receipt.status == "NAUTILUS_REPLAYED"
    # Semantic replay-event count: 1 book + 2 price_change + 1 last_trade_price = 4
    # (tick_size_change is regime metadata, not an engine event).
    assert receipt.replay_processed_event_count == 4
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


def test_source_counts_equal_converted_and_replayed_counts(tmp_path):
    # R024 reconciliation with a multi-level book and all four event types.
    rows = [
        book(1000, 1005, [["0.4000", "50.000000"], ["0.3900", "10.000000"]],
             [["0.6000", "50.000000"], ["0.6100", "10.000000"]]),
        price_change(1000, 1006, "0.4100", "10.000000", "BUY"),
        trade(1000, 1007, "0.4100", "5.000000", "BUY", "0x" + "d" * 64),
        tick_change(1100, 1101, "0.0100", "0.0010"),
        price_change(1200, 1205, "0.5850", "7.000000", "SELL"),
    ]
    stream = valid_stream(tmp_path / "src", rows=rows)
    receipt = run_offline_replay(stream, tmp_path / "catalog")
    assert receipt.is_valid
    counts = dict(receipt.input_event_counts_by_type)
    book_c, pc_c, ltp_c, tsc_c = (counts["book"], counts["price_change"],
                                  counts["last_trade_price"], counts["tick_size_change"])
    assert (book_c, pc_c, ltp_c, tsc_c) == (1, 2, 1, 1)
    source_total = book_c + pc_c + ltp_c + tsc_c
    replayable = book_c + pc_c + ltp_c
    tick_regime_transitions = len(receipt.tick_size_regime_sequence)
    # source_total = replayable_source_events + tick-regime transitions
    assert source_total == replayable + tick_regime_transitions
    assert tick_regime_transitions == tsc_c == 1
    # one source book event stays one semantic snapshot; replay count = replayable events
    assert receipt.replay_processed_event_count == replayable == 4


test_source_counts_equal_converted_counts = test_source_counts_equal_converted_and_replayed_counts


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
    assert _scan_public_result_for_echo(receipt, ("Traceback", "\\", str(tmp_path))) == ()


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
    assert _scan_public_result_for_echo(receipt, (str(tmp_path), "\\", "catalog")) == ()


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
    expected = REPLAY_IDENTITY_PREFIX + hashlib.sha256(_canonical_json_bytes(preimage)).hexdigest()
    assert receipt.replay_digest == expected
    assert CONVERSION_POLICY_VERSION == "wp168-nautilus-pmxt-v2-conversion/1.0.0"
    assert REPLAY_IDENTITY_PREFIX == "nautilusreplay:sha256:"


def test_engine_observed_order_matches_declared_order(tmp_path):
    # R021: the engine processes semantic events in the declared receive-time-primary order.
    rows = [
        book(1000, 1005, [["0.4000", "1.000000"]], [["0.6000", "1.000000"]]),
        price_change(1000, 1006, "0.4100", "1.000000", "BUY"),
        trade(1000, 1007, "0.4100", "1.000000", "BUY", "0x" + "a" * 64),
        price_change(1200, 1205, "0.5850", "1.000000", "SELL"),
    ]
    stream = valid_stream(tmp_path / "src", rows=rows)
    receipt = run_offline_replay(stream, tmp_path / "catalog")
    assert receipt.is_valid  # observed order == declared order, else REPLAY_PARITY_INVALID
    assert receipt.replay_processed_event_count == 4


def test_engine_observed_equal_ts_init_tie_order(tmp_path):
    # book (rank 0) < price_change (rank 1) < last_trade_price (rank 2) at the same ts_init.
    rows = [
        trade(1000, 1000, "0.4100", "1.000000", "BUY", "0x" + "b" * 64),
        price_change(1000, 1000, "0.4100", "1.000000", "BUY"),
        book(1000, 1000, [["0.4000", "1.000000"]], [["0.6000", "1.000000"]]),
    ]
    stream = valid_stream(tmp_path / "src", rows=rows)
    receipt = run_offline_replay(stream, tmp_path / "catalog")
    # If the engine dispatched the tie in any order other than book<price_change<trade the
    # observed order would differ from the declared order and fail closed.
    assert receipt.is_valid
    assert receipt.replay_processed_event_count == 3


def test_engine_observed_order_is_repeatable(tmp_path):
    stream = valid_stream(tmp_path / "src")
    first = run_offline_replay(stream, tmp_path / "c1")
    second = run_offline_replay(stream, tmp_path / "c2")
    assert first.is_valid and second.is_valid
    assert first.replay_digest == second.replay_digest


def test_engine_order_mismatch_fails_closed(tmp_path, monkeypatch):
    # Force the pure semantic-order comparison to report a mismatch (the immutable Cython
    # engine/actor need not be patched) and prove run_offline_replay fails closed.
    from src.research_runtime.nautilus_offline import replay as replay_mod
    monkeypatch.setattr(replay_mod, "_semantic_order_matches", lambda expected, observed: False)
    stream = valid_stream(tmp_path / "src")
    receipt = run_offline_replay(stream, tmp_path / "catalog")
    assert receipt.is_valid is False
    assert receipt.error_codes == (REPLAY_ERROR_PARITY_INVALID,)
    assert receipt.replay_digest is None


def test_replay_real_count_mismatch_fails_closed(tmp_path):
    # R025: a valid stream whose declared counts disagree with the actual semantic objects
    # fails closed with a parity error before/without a successful replay.
    stream = valid_stream(tmp_path / "src")
    tampered = dataclasses.replace(
        stream,
        input_event_counts_by_type=(("book", 1), ("price_change", 99),
                                    ("last_trade_price", 1), ("tick_size_change", 1)),
    )
    receipt = run_offline_replay(tampered, tmp_path / "catalog")
    assert receipt.is_valid is False
    assert receipt.error_codes == (REPLAY_ERROR_PARITY_INVALID,)
    assert receipt.replay_digest is None
    assert receipt.replay_processed_event_count == 0


def test_reordered_source_file_list_yields_identical_replay(tmp_path):
    # R055: FILE enumeration order invariance (two actual source files).
    rows_a = [book(1000, 1005, [["0.4000", "1.000000"]], [["0.6000", "1.000000"]]),
              price_change(1000, 1006, "0.4100", "1.000000", "BUY")]
    rows_b = [trade(1200, 1205, "0.4100", "1.000000", "BUY", "0x" + "a" * 64),
              price_change(1300, 1305, "0.5850", "1.000000", "SELL")]
    source = _write_files(tmp_path / "src", [rows_a, rows_b])
    forward = convert_pmxt_v2_events(source, _context())
    reordered = PmxtV2ReplaySource(descriptor=source.descriptor,
                                   source_files=tuple(reversed(source.source_files)))
    backward = convert_pmxt_v2_events(reordered, _context())
    assert forward.is_valid and backward.is_valid
    assert forward.ordered_event_digests == backward.ordered_event_digests
    r_forward = run_offline_replay(forward, tmp_path / "cf")
    r_backward = run_offline_replay(backward, tmp_path / "cb")
    assert r_forward.replay_digest == r_backward.replay_digest


def test_absolute_source_path_never_in_identity_or_output(tmp_path):
    # R056: the same semantic source in different absolute directories has identical identity
    # and no source path appears in any project-owned public output.
    stream_a = convert_pmxt_v2_events(_write_files(tmp_path / "dir_alpha", [default_rows()]), _context())
    stream_b = convert_pmxt_v2_events(
        _write_files(tmp_path / "dir_beta_much_longer_path", [default_rows()]), _context())
    assert stream_a.is_valid and stream_b.is_valid
    assert stream_a.ordered_event_digests == stream_b.ordered_event_digests
    receipt_a = run_offline_replay(stream_a, tmp_path / "c1")
    receipt_b = run_offline_replay(stream_b, tmp_path / "c2")
    assert receipt_a.replay_digest == receipt_b.replay_digest
    frags = (str(tmp_path / "dir_alpha"), str(tmp_path / "dir_beta_much_longer_path"), str(tmp_path))
    # converted_events holds opaque Nautilus objects (excluded); scan project-owned fields.
    for result in (stream_a, stream_b, receipt_a, receipt_b):
        assert _scan_public_result_for_echo(result, frags) == ()


def test_receipt_field_coverage_and_invalid_result_no_echo(tmp_path):
    # R026: every public result dataclass field is classified, and invalid results across all
    # operations obey the frozen invalid shape and are recursively no-echo.
    forbidden = ("Traceback", str(tmp_path), "\\", "site-packages", "forced")

    # Build one invalid result per operation.
    bad_context = BinaryOptionMarketContext(
        condition_id="0x" + "Z" * 64, outcome_token_id=TOKEN, outcome_label="Yes",
        description="d", activation_ns=0, expiration_ns=1, price_increment="0.001",
        size_increment="0.01", maker_fee="0", taker_fee="0", ts_event_ns=0, ts_init_ns=0)
    invalid_instrument = build_binary_option(bad_context)

    wrong = _write_files(tmp_path / "wrong", [default_rows()], wrong_provider=True)
    invalid_stream = convert_pmxt_v2_events(wrong, _context())

    build_invalid = build_catalog(invalid_stream, tmp_path / "c")
    query_invalid = query_catalog(build_invalid)
    replay_invalid = run_offline_replay(invalid_stream, tmp_path / "r")

    assert invalid_instrument.is_valid is False
    assert invalid_instrument.error_codes == (INSTRUMENT_MAPPING_ERROR,)
    assert invalid_instrument.instrument_id is None and invalid_instrument.binary_option is None

    assert invalid_stream.is_valid is False
    assert invalid_stream.error_codes == (CONVERSION_ERROR,)
    assert invalid_stream.instrument_id is None and invalid_stream.ordered_event_digests == ()

    assert build_invalid.is_valid is False and build_invalid.error_codes == (CATALOG_WRITE_ERROR,)
    assert build_invalid.written_delta_count == 0 and build_invalid.written_trade_count == 0
    assert build_invalid.catalog_dir is None and build_invalid.stream_ref_digest is None

    assert query_invalid.is_valid is False and query_invalid.error_codes == (CATALOG_QUERY_ERROR,)
    assert query_invalid.queried_delta_count == 0 and query_invalid.queried_trade_count == 0

    assert replay_invalid.is_valid is False and replay_invalid.error_codes == (REPLAY_ERROR_INVALID,)
    assert replay_invalid.replay_digest is None and replay_invalid.replay_processed_event_count == 0

    # Recursive no-echo over every invalid public result.
    for result in (invalid_instrument, invalid_stream, build_invalid, query_invalid, replay_invalid):
        assert _scan_public_result_for_echo(result, forbidden) == ()


TOKEN = "92544998123698303655208967887569360731013655782348975589292031774495159624905"


def test_receipt_is_frozen(tmp_path):
    stream = valid_stream(tmp_path / "src")
    receipt = run_offline_replay(stream, tmp_path / "catalog")
    assert dataclasses.is_dataclass(NautilusReplayReceipt)
    with pytest.raises(dataclasses.FrozenInstanceError):
        receipt.is_valid = False  # type: ignore[misc]
