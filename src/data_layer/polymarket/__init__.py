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
from .market_truth import (
    AcquisitionLimits,
    AcquisitionReceipt,
    BookApplyResult,
    BookFramePlan,
    BookStateTransition,
    Checkpoint,
    MarketTruthError,
    MarketTruthRuntimeConfig,
    NormalizedObservation,
    PitPromotionResult,
    PublicPageResult,
    RawEnvelope,
    SubscriptionControlResult,
    SubscriptionUpdate,
    build_point_in_time_observation,
    canonical_json_bytes,
    make_raw_envelope,
    normalize_public_record,
    normalize_websocket_message,
)
from .market_truth_store import MarketTruthStore
from .market_truth_websocket import (
    MarketBookState,
    SubscriptionController,
    run_market_websocket,
)
from .market_truth_data_api import PublicMarketDataClient, collect_public_page
from .market_truth_onchain import (
    collect_order_filled_logs,
    decode_order_filled_v2,
    validate_public_rpc_url,
)
from .market_truth_runtime import run_market_truth_runtime

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
    # WP169 public market-truth realtime data plane.
    "AcquisitionLimits",
    "AcquisitionReceipt",
    "BookApplyResult",
    "BookFramePlan",
    "BookStateTransition",
    "Checkpoint",
    "MarketTruthError",
    "MarketTruthRuntimeConfig",
    "NormalizedObservation",
    "PitPromotionResult",
    "PublicPageResult",
    "RawEnvelope",
    "SubscriptionControlResult",
    "SubscriptionUpdate",
    "build_point_in_time_observation",
    "canonical_json_bytes",
    "make_raw_envelope",
    "normalize_public_record",
    "normalize_websocket_message",
    "MarketTruthStore",
    "MarketBookState",
    "SubscriptionController",
    "run_market_websocket",
    "PublicMarketDataClient",
    "collect_public_page",
    "collect_order_filled_logs",
    "decode_order_filled_v2",
    "validate_public_rpc_url",
    "run_market_truth_runtime",
]
