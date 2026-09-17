"""WP168 NautilusTrader offline kernel, ParquetDataCatalog & deterministic replay.

Local, offline, read-only-against-canonical research runtime that translates verified WP167
pmxt-v2 external history into NautilusTrader instruments/market-data events, registers them in
a local ParquetDataCatalog, and replays them deterministically into a repo-controlled
NautilusReplayReceipt. No live/auth clients, no Polymarket extra, no Redis, no network, no
strategy/order/fill/paper/live authority. See docs/nautilus_offline_kernel_contract.md.

The frozen WP168 public API is the six functions and eight dataclasses listed in ``__all__``.
WP175D adds an additive, non-breaking external historical research bridge: the
``build_pmxt_v2_research_lineage`` builder with ``PmxtV2ResearchLineage`` /
``PmxtV2ResearchLineageMember``, and the ``build_pmxt_v2_dataset_binding`` /
``build_pmxt_v2_research_dataset_manifest`` bridge functions. Every other symbol
(helpers, error-code constants, identity constants) is internal; import it from its owning
submodule where a test genuinely needs it. Helper functions are private.
"""

from __future__ import annotations

# Public API only. Internal constants live on the submodules and are imported directly by
# tests when needed; they are intentionally not part of the package-root public surface.
from .catalog import CatalogBuildResult, CatalogQueryResult, build_catalog, query_catalog
from .conversion import (
    ConvertedEventStream,
    PmxtV2ReplaySource,
    PmxtV2ResearchLineage,
    PmxtV2ResearchLineageMember,
    build_pmxt_v2_research_lineage,
    convert_pmxt_v2_events,
)
from .experiment_bridge import (
    build_pmxt_v2_dataset_binding,
    build_pmxt_v2_research_dataset_manifest,
)
from .instruments import (
    BinaryOptionMappingResult,
    BinaryOptionMarketContext,
    build_binary_option,
)
from .replay import NautilusReplayReceipt, run_offline_replay
from .runtime_compatibility import (
    NautilusRuntimeCompatibilityResult,
    evaluate_offline_runtime,
)

# Internal error-code / identity constants (module attributes only — deliberately absent from
# __all__ and never exposed as public API). Helper functions remain private on their submodules.
from .catalog import CATALOG_QUERY_ERROR, CATALOG_WRITE_ERROR  # noqa: E402
from .conversion import (  # noqa: E402
    CONVERSION_ERROR,
    CONVERSION_POLICY_VERSION,
    EVENT_KIND_RANK,
    SOURCE_DATASET_KIND,
)
from .instruments import (  # noqa: E402
    FEE_METADATA_UNKNOWN_WARNING,
    INSTRUMENT_MAPPING_ERROR,
    POLYMARKET_VENUE,
)
from .replay import (  # noqa: E402
    REPLAY_ERROR_INVALID,
    REPLAY_ERROR_PARITY_INVALID,
    REPLAY_IDENTITY_PREFIX,
    REPLAY_RECEIPT_SCHEMA_ID,
    REPLAY_RECEIPT_SCHEMA_VERSION,
)
from .runtime_compatibility import (  # noqa: E402
    NAUTILUS_REQUIRED_VERSION,
    RUNTIME_ERROR_DEPENDENCY_VERSION_INVALID,
    RUNTIME_ERROR_IMPORT_UNAVAILABLE,
    RUNTIME_ERROR_UNSUPPORTED,
    RUNTIME_STATUS_SUPPORTED,
)

# Fixed product error precedence (internal; distinct from the WP-spec guard's schema codes).
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
    # Public functions (exact frozen signatures).
    "evaluate_offline_runtime",
    "build_binary_option",
    "convert_pmxt_v2_events",
    "build_catalog",
    "query_catalog",
    "run_offline_replay",
    # Public project-owned dataclasses.
    "NautilusRuntimeCompatibilityResult",
    "BinaryOptionMarketContext",
    "BinaryOptionMappingResult",
    "PmxtV2ReplaySource",
    "ConvertedEventStream",
    "CatalogBuildResult",
    "CatalogQueryResult",
    "NautilusReplayReceipt",
]

# WP175D external historical research bridge public surface. These are additive,
# non-breaking exports: they are importable module attributes (the narrow public
# bridge) but intentionally NOT part of the frozen WP168 ``__all__`` tuple, which the
# WP168 contract pins to exactly the six functions and eight dataclasses above. This
# mirrors how the internal constants above are exported as attributes without joining
# ``__all__``.
WP175D_BRIDGE_PUBLIC_API = (
    "build_pmxt_v2_research_lineage",
    "build_pmxt_v2_dataset_binding",
    "build_pmxt_v2_research_dataset_manifest",
    "PmxtV2ResearchLineage",
    "PmxtV2ResearchLineageMember",
)
