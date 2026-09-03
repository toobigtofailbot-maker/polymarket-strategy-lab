"""WP168 NautilusTrader offline kernel, ParquetDataCatalog & deterministic replay.

Local, offline, read-only-against-canonical research runtime that translates verified WP167
pmxt-v2 external history into NautilusTrader instruments/market-data events, registers them in
a local ParquetDataCatalog, and replays them deterministically into a repo-controlled
NautilusReplayReceipt. No live/auth clients, no Polymarket extra, no Redis, no network, no
strategy/order/fill/paper/live authority. See docs/nautilus_offline_kernel_contract.md.
"""

from __future__ import annotations

from .catalog import (
    CATALOG_QUERY_ERROR,
    CATALOG_WRITE_ERROR,
    CatalogBuildResult,
    CatalogQueryResult,
    build_catalog,
    query_catalog,
)
from .conversion import (
    CONVERSION_ERROR,
    CONVERSION_POLICY_VERSION,
    EVENT_KIND_RANK,
    SOURCE_DATASET_KIND,
    ConvertedEventStream,
    PmxtV2ReplaySource,
    canonical_json_bytes,
    convert_pmxt_v2_events,
    scan_public_result_for_echo,
    stream_identity_digest,
)
from .instruments import (
    FEE_METADATA_UNKNOWN_WARNING,
    INSTRUMENT_MAPPING_ERROR,
    POLYMARKET_VENUE,
    BinaryOptionMappingResult,
    BinaryOptionMarketContext,
    build_binary_option,
)
from .replay import (
    REPLAY_ERROR_INVALID,
    REPLAY_ERROR_PARITY_INVALID,
    REPLAY_IDENTITY_PREFIX,
    REPLAY_RECEIPT_SCHEMA_ID,
    REPLAY_RECEIPT_SCHEMA_VERSION,
    NautilusReplayReceipt,
    run_offline_replay,
)
from .runtime_compatibility import (
    NAUTILUS_REQUIRED_VERSION,
    RUNTIME_ERROR_DEPENDENCY_VERSION_INVALID,
    RUNTIME_ERROR_IMPORT_UNAVAILABLE,
    RUNTIME_ERROR_UNSUPPORTED,
    RUNTIME_STATUS_SUPPORTED,
    NautilusRuntimeCompatibilityResult,
    evaluate_offline_runtime,
)

# Fixed product error precedence (distinct from the WP-spec guard's schema diagnostics).
PRODUCT_ERROR_PRECEDENCE = (
    RUNTIME_ERROR_UNSUPPORTED,
    RUNTIME_ERROR_DEPENDENCY_VERSION_INVALID,
    RUNTIME_ERROR_IMPORT_UNAVAILABLE,
    INSTRUMENT_MAPPING_ERROR,
    CONVERSION_ERROR,
    CATALOG_WRITE_ERROR,
    CATALOG_QUERY_ERROR,
    REPLAY_ERROR_INVALID,
    REPLAY_ERROR_PARITY_INVALID,
)

__all__ = [
    "NautilusRuntimeCompatibilityResult",
    "evaluate_offline_runtime",
    "NAUTILUS_REQUIRED_VERSION",
    "RUNTIME_STATUS_SUPPORTED",
    "RUNTIME_ERROR_UNSUPPORTED",
    "RUNTIME_ERROR_DEPENDENCY_VERSION_INVALID",
    "RUNTIME_ERROR_IMPORT_UNAVAILABLE",
    "BinaryOptionMarketContext",
    "BinaryOptionMappingResult",
    "build_binary_option",
    "POLYMARKET_VENUE",
    "INSTRUMENT_MAPPING_ERROR",
    "FEE_METADATA_UNKNOWN_WARNING",
    "PmxtV2ReplaySource",
    "ConvertedEventStream",
    "convert_pmxt_v2_events",
    "CONVERSION_POLICY_VERSION",
    "SOURCE_DATASET_KIND",
    "EVENT_KIND_RANK",
    "CONVERSION_ERROR",
    "canonical_json_bytes",
    "scan_public_result_for_echo",
    "stream_identity_digest",
    "CatalogBuildResult",
    "CatalogQueryResult",
    "build_catalog",
    "query_catalog",
    "CATALOG_WRITE_ERROR",
    "CATALOG_QUERY_ERROR",
    "NautilusReplayReceipt",
    "run_offline_replay",
    "REPLAY_RECEIPT_SCHEMA_ID",
    "REPLAY_RECEIPT_SCHEMA_VERSION",
    "REPLAY_IDENTITY_PREFIX",
    "REPLAY_ERROR_INVALID",
    "REPLAY_ERROR_PARITY_INVALID",
    "PRODUCT_ERROR_PRECEDENCE",
]
