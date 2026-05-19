"""Tests for offline snapshot_deduplication.py helpers."""

from __future__ import annotations

from copy import deepcopy

from src.data_layer.polymarket.snapshot_deduplication import (
    deduplicate_market_records,
    deduplicate_order_book_records,
    market_record_key,
    order_book_record_key,
    summarize_deduplication,
)
from tests.data_layer.polymarket.test_snapshot_quality import (
    _market_record,
    _order_book_record,
)


def test_exact_duplicate_market_records_are_removed():
    first = _market_record()
    duplicate = deepcopy(first)

    result = deduplicate_market_records([first, duplicate])

    assert result.input_count == 2
    assert result.output_count == 1
    assert result.exact_duplicate_count == 1
    assert result.records == [first]
    assert result.decisions[1].action == "drop_exact_duplicate"
    assert result.decisions[1].duplicate_of_index == 0


def test_conflicting_market_records_are_retained_and_reported():
    first = _market_record()
    conflict = deepcopy(first)
    conflict.question = "Different local question text?"

    result = deduplicate_market_records([first, conflict])

    assert result.output_count == 2
    assert result.exact_duplicate_count == 0
    assert result.conflict_count == 1
    assert result.conflicts[0].input_indexes == [0, 1]
    assert result.records == [first, conflict]


def test_exact_duplicate_order_book_records_are_removed():
    first = _order_book_record()
    first.bids = [{"price": "0.41", "size": "10"}]
    first.asks = [{"price": "0.42", "size": "11"}]
    duplicate = deepcopy(first)

    result = deduplicate_order_book_records([first, duplicate])

    assert result.output_count == 1
    assert result.exact_duplicate_count == 1
    assert result.records == [first]
    assert result.decisions[1].action == "drop_exact_duplicate"


def test_conflicting_order_book_records_are_retained_and_reported():
    first = _order_book_record()
    first.bids = [{"price": "0.41", "size": "10"}]
    conflict = deepcopy(first)
    conflict.bids = [{"price": "0.40", "size": "12"}]

    result = deduplicate_order_book_records([first, conflict])

    assert result.output_count == 2
    assert result.conflict_count == 1
    assert result.conflicts[0].input_indexes == [0, 1]
    assert result.records == [first, conflict]


def test_deduplication_is_deterministic():
    first = _market_record("market-1")
    duplicate = deepcopy(first)
    conflict = deepcopy(first)
    conflict.category = "politics"
    other = _market_record("market-2")
    records = [first, duplicate, conflict, other]

    result_a = deduplicate_market_records(records)
    result_b = deduplicate_market_records(records)

    assert result_a.to_dict() == result_b.to_dict()
    assert [record.market_id for record in result_a.records] == [
        "market-1",
        "market-1",
        "market-2",
    ]


def test_original_input_list_and_records_are_not_mutated():
    records = [_market_record("market-1"), _market_record("market-2")]
    before = [record.to_dict() for record in records]
    original_list = list(records)

    deduplicate_market_records(records)

    assert records == original_list
    assert [record.to_dict() for record in records] == before


def test_record_keys_are_stable_tuples():
    market = _market_record(token_ids=["token-b", "token-a"], outcome_labels=["No", "Yes"])
    book = _order_book_record()
    book.bids = [{"size": "10", "price": "0.41"}]

    assert market_record_key(market) == (
        "snap_001",
        "market-1",
        "2026-01-01T00:00:00+00:00",
        "cond-market-1",
        ("token-b", "token-a"),
        ("No", "Yes"),
    )
    assert order_book_record_key(book)[0:3] == (
        "snap_001",
        "token-market-1-yes",
        "2026-01-01T00:00:00+00:00",
    )


def test_summary_is_sanitized_and_records_conflicts_retained():
    first = _market_record()
    conflict = deepcopy(first)
    conflict.market_status = "closed"

    summary = summarize_deduplication(deduplicate_market_records([first, conflict]))

    assert summary["record_type"] == "market"
    assert summary["conflict_count"] == 1
    assert summary["conflicts_retained"] is True
    assert summary["research_only"] is True
