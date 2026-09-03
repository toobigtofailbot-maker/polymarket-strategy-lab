"""WP168 deterministic Nautilus ParquetDataCatalog adoption (offline, fail-closed).

Builds a local Nautilus ParquetDataCatalog from a converted event stream and reads it back
for a round-trip parity check. The catalog directory is caller-provided and excluded from
logical identity; the catalog is derived physical evidence, never canonical truth. No
downloader, no network; closed catalog error codes with no raw path/exception echo.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

from .conversion import ConvertedEventStream, stream_identity_digest

CATALOG_BUILD_STATUS_OK = "NAUTILUS_CATALOG_BUILT"
CATALOG_BUILD_STATUS_REJECTED = "NAUTILUS_CATALOG_BUILD_REJECTED"
CATALOG_QUERY_STATUS_OK = "NAUTILUS_CATALOG_QUERIED"
CATALOG_QUERY_STATUS_REJECTED = "NAUTILUS_CATALOG_QUERY_REJECTED"
CATALOG_WRITE_ERROR = "NAUTILUS_CATALOG_WRITE_INVALID"
CATALOG_QUERY_ERROR = "NAUTILUS_CATALOG_QUERY_INVALID"


@dataclass(frozen=True)
class CatalogBuildResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    instrument_registered: bool
    written_delta_count: int
    written_trade_count: int
    catalog_dir: str | None
    stream_ref_digest: str | None


@dataclass(frozen=True)
class CatalogQueryResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    queried_delta_count: int
    queried_trade_count: int
    round_trip_matches: bool


def _build_rejected() -> CatalogBuildResult:
    return CatalogBuildResult(
        is_valid=False,
        status=CATALOG_BUILD_STATUS_REJECTED,
        error_codes=(CATALOG_WRITE_ERROR,),
        instrument_registered=False,
        written_delta_count=0,
        written_trade_count=0,
        catalog_dir=None,
        stream_ref_digest=None,
    )


def _query_rejected() -> CatalogQueryResult:
    return CatalogQueryResult(
        is_valid=False,
        status=CATALOG_QUERY_STATUS_REJECTED,
        error_codes=(CATALOG_QUERY_ERROR,),
        queried_delta_count=0,
        queried_trade_count=0,
        round_trip_matches=False,
    )


def build_catalog(stream: ConvertedEventStream, catalog_dir: pathlib.Path) -> CatalogBuildResult:
    """Register the instrument then market data in a local catalog. Never raises/echoes."""
    from nautilus_trader.model.data import OrderBookDelta, TradeTick
    from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog

    try:
        if type(stream) is not ConvertedEventStream or not stream.is_valid:
            return _build_rejected()
        if not isinstance(catalog_dir, pathlib.Path):
            return _build_rejected()
        events = stream.converted_events
        if not events:
            return _build_rejected()
        instrument = events[0]
        data = events[1:]
        deltas = [obj for obj in data if isinstance(obj, OrderBookDelta)]
        trades = [obj for obj in data if isinstance(obj, TradeTick)]

        catalog_dir.mkdir(parents=True, exist_ok=True)
        catalog = ParquetDataCatalog(str(catalog_dir))
        catalog.write_data([instrument])  # instrument definition registered before data
        if deltas:
            catalog.write_data(deltas)
        if trades:
            catalog.write_data(trades)

        return CatalogBuildResult(
            is_valid=True,
            status=CATALOG_BUILD_STATUS_OK,
            error_codes=(),
            instrument_registered=True,
            written_delta_count=len(deltas),
            written_trade_count=len(trades),
            catalog_dir=str(catalog_dir),
            stream_ref_digest=stream_identity_digest(stream),
        )
    except Exception:
        return _build_rejected()


def query_catalog(build_result: CatalogBuildResult) -> CatalogQueryResult:
    """Read the built catalog back and report round-trip parity. Never raises/echoes."""
    from nautilus_trader.model.data import OrderBookDelta, TradeTick
    from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog

    try:
        if type(build_result) is not CatalogBuildResult or not build_result.is_valid:
            return _query_rejected()
        if not build_result.catalog_dir:
            return _query_rejected()
        catalog = ParquetDataCatalog(build_result.catalog_dir)
        queried_deltas = catalog.query(data_cls=OrderBookDelta)
        queried_trades = catalog.query(data_cls=TradeTick)
        delta_count = len(queried_deltas)
        trade_count = len(queried_trades)
        matches = (
            delta_count == build_result.written_delta_count
            and trade_count == build_result.written_trade_count
        )
        return CatalogQueryResult(
            is_valid=True,
            status=CATALOG_QUERY_STATUS_OK,
            error_codes=(),
            queried_delta_count=delta_count,
            queried_trade_count=trade_count,
            round_trip_matches=matches,
        )
    except Exception:
        return _query_rejected()
