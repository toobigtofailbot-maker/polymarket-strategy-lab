"""WP168 BinaryOption mapping tests (R007-R009, R061 partial, R062)."""

from __future__ import annotations

import dataclasses

import pytest

from nautilus_trader.model.currencies import USDC
from nautilus_trader.model.instruments import BinaryOption

import src.research_runtime.nautilus_offline as offline
from src.research_runtime.nautilus_offline.conversion import _scan_public_result_for_echo
from src.research_runtime.nautilus_offline import (
    FEE_METADATA_UNKNOWN_WARNING,
    INSTRUMENT_MAPPING_ERROR,
    BinaryOptionMappingResult,
    BinaryOptionMarketContext,
    build_binary_option,
)

MARKET = "0x" + "a" * 64
TOKEN = "92544998123698303655208967887569360731013655782348975589292031774495159624905"


def _context(**overrides) -> BinaryOptionMarketContext:
    base = dict(
        condition_id=MARKET,
        outcome_token_id=TOKEN,
        outcome_label="Yes",
        description="Will the outcome be Yes?",
        activation_ns=0,
        expiration_ns=1_800_000_000_000_000_000,
        price_increment="0.001",
        size_increment="0.01",
        maker_fee="0",
        taker_fee="0",
        ts_event_ns=0,
        ts_init_ns=0,
    )
    base.update(overrides)
    return BinaryOptionMarketContext(**base)


def test_binary_option_identity_is_deterministic_and_path_independent() -> None:
    first = build_binary_option(_context())
    second = build_binary_option(_context())
    assert first.is_valid and second.is_valid
    assert first.instrument_id == f"{MARKET}-{TOKEN}.POLYMARKET"
    assert first.instrument_id == second.instrument_id


def test_instrument_uses_usdc_and_exact_precision() -> None:
    result = build_binary_option(_context(price_increment="0.001", size_increment="0.01"))
    assert result.is_valid
    assert isinstance(result.binary_option, BinaryOption)
    assert result.binary_option.quote_currency == USDC
    assert result.binary_option.price_precision == 3
    assert result.binary_option.size_precision == 2
    assert result.price_increment == "0.001"
    assert result.size_increment == "0.01"


def test_missing_or_malformed_market_identity_is_rejected() -> None:
    for bad in (
        _context(condition_id="0x" + "A" * 64),   # uppercase hex not canonical
        _context(condition_id="0x" + "a" * 63),    # wrong length
        _context(outcome_token_id="12x3"),          # non-decimal token
        _context(outcome_token_id=""),              # empty token
    ):
        result = build_binary_option(bad)
        assert result.is_valid is False
        assert result.error_codes == (INSTRUMENT_MAPPING_ERROR,)
        assert result.instrument_id is None
        assert result.binary_option is None
        assert _scan_public_result_for_echo(result, ("Traceback", "0x" + "A" * 64)) == ()


def test_binary_option_absent_value_policy() -> None:
    # expiration_ns None -> fail closed.
    assert build_binary_option(_context(expiration_ns=None)).is_valid is False
    # missing outcome_label -> fail closed.
    assert build_binary_option(_context(outcome_label="")).is_valid is False
    # activation_ns None -> 0 (accepted).
    activated = build_binary_option(_context(activation_ns=None))
    assert activated.is_valid is True
    assert activated.binary_option.activation_ns == 0
    # fee None -> Decimal(0) placeholder + FEE_METADATA_UNKNOWN warning.
    fee_unknown = build_binary_option(_context(maker_fee=None, taker_fee=None))
    assert fee_unknown.is_valid is True
    assert FEE_METADATA_UNKNOWN_WARNING in fee_unknown.warnings
    # description None -> empty string only; Nautilus rejects empty -> fail closed (never fabricated).
    assert build_binary_option(_context(description=None)).is_valid is False


def test_mapping_result_is_frozen_and_fields_classified() -> None:
    result = build_binary_option(_context())
    assert dataclasses.is_dataclass(BinaryOptionMappingResult)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.is_valid = False  # type: ignore[misc]
    expected = {
        "is_valid", "status", "error_codes", "instrument_id",
        "price_increment", "size_increment", "warnings", "binary_option",
    }
    assert {f.name for f in dataclasses.fields(BinaryOptionMappingResult)} == expected
