"""Polymarket read-only public data adapter.

READ-ONLY PUBLIC DATA ONLY. No credentials. No trading authority.
No order placement. No wallet or private-key handling. No live mode.

See src/data_layer/polymarket/README.md for details.
"""

from .errors import (
    PolymarketEndpointNotVerifiedError,
    PolymarketHTTPError,
    PolymarketReadOnlyError,
    PolymarketResponseError,
)
from .models import (
    AdapterResult,
    MarketSummary,
    OrderBookLevel,
    OrderBookSnapshot,
    ReadOnlyRequestInfo,
)
from .public_client import PolymarketPublicClient

__all__ = [
    "PolymarketPublicClient",
    "MarketSummary",
    "OrderBookLevel",
    "OrderBookSnapshot",
    "ReadOnlyRequestInfo",
    "AdapterResult",
    "PolymarketReadOnlyError",
    "PolymarketHTTPError",
    "PolymarketResponseError",
    "PolymarketEndpointNotVerifiedError",
]
