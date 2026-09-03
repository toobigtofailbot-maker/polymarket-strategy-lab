"""WP168 deterministic Polymarket BinaryOption mapping (offline, fail-closed).

Maps a frozen, validated :class:`BinaryOptionMarketContext` into a NautilusTrader
``BinaryOption`` on venue ``POLYMARKET`` with collateral ``USDC``. Identity is deterministic
from ``condition_id`` + ``outcome_token_id`` and path-independent. No network, no guessed
metadata, no fabricated outcome/description; the absent-value policy is frozen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from nautilus_trader.model.currencies import USDC
from nautilus_trader.model.enums import AssetClass
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import BinaryOption
from nautilus_trader.model.objects import Price, Quantity

POLYMARKET_VENUE = "POLYMARKET"
INSTRUMENT_MAPPING_STATUS_OK = "NAUTILUS_INSTRUMENT_MAPPED"
INSTRUMENT_MAPPING_STATUS_REJECTED = "NAUTILUS_INSTRUMENT_MAPPING_REJECTED"
INSTRUMENT_MAPPING_ERROR = "NAUTILUS_INSTRUMENT_MAPPING_INVALID"
FEE_METADATA_UNKNOWN_WARNING = "FEE_METADATA_UNKNOWN"

_CONDITION_ID_RE = re.compile(r"^0x[0-9a-f]{64}$")
_TOKEN_ID_RE = re.compile(r"^[0-9]+$")


@dataclass(frozen=True)
class BinaryOptionMarketContext:
    condition_id: str
    outcome_token_id: str
    outcome_label: str
    description: str | None
    activation_ns: int | None
    expiration_ns: int | None
    price_increment: str
    size_increment: str
    maker_fee: str | None
    taker_fee: str | None
    ts_event_ns: int
    ts_init_ns: int


@dataclass(frozen=True)
class BinaryOptionMappingResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    instrument_id: str | None
    price_increment: str | None
    size_increment: str | None
    warnings: tuple[str, ...]
    binary_option: object | None


def _rejected() -> BinaryOptionMappingResult:
    return BinaryOptionMappingResult(
        is_valid=False,
        status=INSTRUMENT_MAPPING_STATUS_REJECTED,
        error_codes=(INSTRUMENT_MAPPING_ERROR,),
        instrument_id=None,
        price_increment=None,
        size_increment=None,
        warnings=(),
        binary_option=None,
    )


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _decimal_text(value: object) -> Decimal | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def build_binary_option(context: BinaryOptionMarketContext) -> BinaryOptionMappingResult:
    """Return the closed BinaryOption mapping result. Never raises, never echoes."""
    if type(context) is not BinaryOptionMarketContext:
        return _rejected()

    if not (isinstance(context.condition_id, str) and _CONDITION_ID_RE.fullmatch(context.condition_id)):
        return _rejected()
    if not (isinstance(context.outcome_token_id, str) and _TOKEN_ID_RE.fullmatch(context.outcome_token_id)):
        return _rejected()
    if not (isinstance(context.outcome_label, str) and context.outcome_label):
        return _rejected()
    if context.description is not None and not isinstance(context.description, str):
        return _rejected()
    if not (_is_int(context.ts_event_ns) and _is_int(context.ts_init_ns)):
        return _rejected()
    if context.activation_ns is not None and not _is_int(context.activation_ns):
        return _rejected()
    # Frozen absent-value policy: expiration must be present source truth.
    if context.expiration_ns is None or not _is_int(context.expiration_ns):
        return _rejected()

    price_increment = _decimal_text(context.price_increment)
    size_increment = _decimal_text(context.size_increment)
    if price_increment is None or size_increment is None:
        return _rejected()
    if price_increment <= 0 or size_increment <= 0:
        return _rejected()

    warnings: list[str] = []
    maker_fee = context.maker_fee
    taker_fee = context.taker_fee
    if maker_fee is None or taker_fee is None:
        warnings.append(FEE_METADATA_UNKNOWN_WARNING)
    maker_decimal = Decimal("0") if maker_fee is None else _decimal_text(maker_fee)
    taker_decimal = Decimal("0") if taker_fee is None else _decimal_text(taker_fee)
    if maker_decimal is None or taker_decimal is None:
        return _rejected()

    try:
        price_inc = Price.from_str(context.price_increment)
        size_inc = Quantity.from_str(context.size_increment)
        raw_symbol = Symbol(f"{context.condition_id}-{context.outcome_token_id}")
        instrument_id = InstrumentId(symbol=raw_symbol, venue=Venue(POLYMARKET_VENUE))
        activation_ns = 0 if context.activation_ns is None else int(context.activation_ns)
        binary_option = BinaryOption(
            instrument_id=instrument_id,
            raw_symbol=raw_symbol,
            outcome=context.outcome_label,
            description=context.description or "",
            asset_class=AssetClass.ALTERNATIVE,
            currency=USDC,
            price_precision=price_inc.precision,
            price_increment=price_inc,
            size_precision=size_inc.precision,
            size_increment=size_inc,
            activation_ns=activation_ns,
            expiration_ns=int(context.expiration_ns),
            max_quantity=None,
            min_quantity=size_inc,
            maker_fee=maker_decimal,
            taker_fee=taker_decimal,
            ts_event=int(context.ts_event_ns),
            ts_init=int(context.ts_init_ns),
        )
    except Exception:
        return _rejected()

    return BinaryOptionMappingResult(
        is_valid=True,
        status=INSTRUMENT_MAPPING_STATUS_OK,
        error_codes=(),
        instrument_id=str(instrument_id),
        price_increment=str(price_inc),
        size_increment=str(size_inc),
        warnings=tuple(warnings),
        binary_option=binary_option,
    )
