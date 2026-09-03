"""WP168 bounded offline NautilusTrader replay + repo-controlled replay receipt.

Loads one BinaryOption instrument and the canonical ordered market-data stream into a bounded
Nautilus BacktestEngine and replays it deterministically. Produces a frozen, path-independent,
mutation-sensitive NautilusReplayReceipt. No strategy, order, execution client, or fill/P&L
claim: this is an event-replay proof only. Closed replay error codes, no raw echo.
"""

from __future__ import annotations

import hashlib
import pathlib
from dataclasses import dataclass

from .conversion import (
    CONVERSION_POLICY_VERSION,
    SOURCE_DATASET_KIND,
    ConvertedEventStream,
    canonical_json_bytes,
)

REPLAY_RECEIPT_SCHEMA_ID = "polymarket-nautilus-offline-replay-receipt"
REPLAY_RECEIPT_SCHEMA_VERSION = "1.0.0"
REPLAY_IDENTITY_PREFIX = "nautilusreplay:sha256:"

REPLAY_STATUS_OK = "NAUTILUS_REPLAYED"
REPLAY_STATUS_REJECTED = "NAUTILUS_REPLAY_REJECTED"
REPLAY_ERROR_INVALID = "NAUTILUS_REPLAY_INVALID"
REPLAY_ERROR_PARITY_INVALID = "NAUTILUS_REPLAY_PARITY_INVALID"

# Deterministic offline-replay settings committed into the replay identity.
REPLAY_SETTINGS = {
    "book_type": "L2_MBP",
    "oms_type": "NETTING",
    "account_type": "CASH",
    "engine": "BacktestEngine",
    "add_data_sort": True,
}


@dataclass(frozen=True)
class NautilusReplayReceipt:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    schema_id: str
    schema_version: str
    source_dataset_kind: str
    source_external_dataset_id: str | None
    conversion_policy_version: str | None
    nautilus_version: str | None
    instrument_id: str | None
    input_event_counts_by_type: tuple[tuple[str, int], ...]
    first_event_time_ns: int | None
    last_event_time_ns: int | None
    tick_size_regime_sequence: tuple[tuple[str, str, int], ...]
    replay_processed_event_count: int
    replay_digest: str | None
    warnings: tuple[str, ...]
    execution_authority: bool = False


def _rejected(code: str) -> NautilusReplayReceipt:
    return NautilusReplayReceipt(
        is_valid=False,
        status=REPLAY_STATUS_REJECTED,
        error_codes=(code,),
        schema_id=REPLAY_RECEIPT_SCHEMA_ID,
        schema_version=REPLAY_RECEIPT_SCHEMA_VERSION,
        source_dataset_kind=SOURCE_DATASET_KIND,
        source_external_dataset_id=None,
        conversion_policy_version=None,
        nautilus_version=None,
        instrument_id=None,
        input_event_counts_by_type=(),
        first_event_time_ns=None,
        last_event_time_ns=None,
        tick_size_regime_sequence=(),
        replay_processed_event_count=0,
        replay_digest=None,
        warnings=(),
        execution_authority=False,
    )


def _replay_digest(stream: ConvertedEventStream, nautilus_version: str) -> str:
    preimage = {
        "conversion_policy_version": CONVERSION_POLICY_VERSION,
        "source_dataset_kind": SOURCE_DATASET_KIND,
        "source_external_dataset_id": stream.source_external_dataset_id,
        "nautilus_version": nautilus_version,
        "instrument_semantic_id": stream.instrument_id,
        "ordered_event_semantic_digests": list(stream.ordered_event_digests),
        "tick_size_regime_sequence": [list(item) for item in stream.tick_size_regime_sequence],
        "replay_settings": REPLAY_SETTINGS,
    }
    return REPLAY_IDENTITY_PREFIX + hashlib.sha256(canonical_json_bytes(preimage)).hexdigest()


def run_offline_replay(
    stream: ConvertedEventStream, catalog_dir: pathlib.Path
) -> NautilusReplayReceipt:
    """Run a bounded deterministic offline replay and return the frozen receipt."""
    import nautilus_trader as nt
    from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.common.actor import Actor, ActorConfig
    from nautilus_trader.model.currencies import USDC
    from nautilus_trader.model.data import OrderBookDelta, TradeTick
    from nautilus_trader.model.enums import AccountType, BookType, OmsType
    from nautilus_trader.model.identifiers import Venue
    from nautilus_trader.model.objects import Money

    try:
        if type(stream) is not ConvertedEventStream or not stream.is_valid:
            return _rejected(REPLAY_ERROR_INVALID)
        if not isinstance(catalog_dir, pathlib.Path):
            return _rejected(REPLAY_ERROR_INVALID)
        events = stream.converted_events
        if not events:
            return _rejected(REPLAY_ERROR_INVALID)
        instrument = events[0]
        data = [obj for obj in events[1:] if isinstance(obj, (OrderBookDelta, TradeTick))]
        expected_count = len(data)
        if expected_count == 0:
            return _rejected(REPLAY_ERROR_INVALID)

        processed = {"count": 0}

        class _ReplayCounter(Actor):
            def on_start(self) -> None:
                self.subscribe_order_book_deltas(instrument.id)
                self.subscribe_trade_ticks(instrument.id)

            def on_order_book_deltas(self, _deltas) -> None:
                # One deltas batch may carry several individual OrderBookDelta records.
                processed["count"] += len(_deltas.deltas)

            def on_trade_tick(self, _tick) -> None:
                processed["count"] += 1

        engine = BacktestEngine(config=BacktestEngineConfig(trader_id="WP168-REPLAY-001", logging=None))
        engine.add_venue(
            venue=Venue("POLYMARKET"),
            oms_type=OmsType.NETTING,
            account_type=AccountType.CASH,
            base_currency=None,
            starting_balances=[Money(1_000, USDC)],
            book_type=BookType.L2_MBP,
        )
        engine.add_instrument(instrument)
        engine.add_actor(_ReplayCounter(config=ActorConfig()))
        engine.add_data(sorted(data, key=lambda obj: obj.ts_init))
        engine.run()
        engine.dispose()

        if processed["count"] != expected_count:
            return _rejected(REPLAY_ERROR_PARITY_INVALID)

        nautilus_version = nt.__version__
        return NautilusReplayReceipt(
            is_valid=True,
            status=REPLAY_STATUS_OK,
            error_codes=(),
            schema_id=REPLAY_RECEIPT_SCHEMA_ID,
            schema_version=REPLAY_RECEIPT_SCHEMA_VERSION,
            source_dataset_kind=SOURCE_DATASET_KIND,
            source_external_dataset_id=stream.source_external_dataset_id,
            conversion_policy_version=CONVERSION_POLICY_VERSION,
            nautilus_version=nautilus_version,
            instrument_id=stream.instrument_id,
            input_event_counts_by_type=stream.input_event_counts_by_type,
            first_event_time_ns=stream.first_event_time_ns,
            last_event_time_ns=stream.last_event_time_ns,
            tick_size_regime_sequence=stream.tick_size_regime_sequence,
            replay_processed_event_count=expected_count,
            replay_digest=_replay_digest(stream, nautilus_version),
            warnings=stream.warnings,
            execution_authority=False,
        )
    except Exception:
        return _rejected(REPLAY_ERROR_INVALID)
