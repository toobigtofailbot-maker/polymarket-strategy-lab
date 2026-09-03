"""WP168 contract-doc conformance tests (R039, R051).

Assert docs/nautilus_offline_kernel_contract.md exactly describes the frozen public API and
every public dataclass field, carries the literal identity constants and error taxonomy, and
keeps WP169/WP170 separately gated — with no ellipsis or reviewer-refinement escape language.
"""

from __future__ import annotations

import dataclasses
import pathlib

import src.research_runtime.nautilus_offline as offline

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = (ROOT / "docs" / "nautilus_offline_kernel_contract.md").read_text(encoding="utf-8")

PUBLIC_SIGNATURES = (
    "evaluate_offline_runtime() -> NautilusRuntimeCompatibilityResult",
    "build_binary_option(context: BinaryOptionMarketContext) -> BinaryOptionMappingResult",
    "convert_pmxt_v2_events(source: PmxtV2ReplaySource, context: BinaryOptionMarketContext) -> ConvertedEventStream",
    "build_catalog(stream: ConvertedEventStream, catalog_dir: pathlib.Path) -> CatalogBuildResult",
    "query_catalog(build_result: CatalogBuildResult) -> CatalogQueryResult",
    "run_offline_replay(stream: ConvertedEventStream, catalog_dir: pathlib.Path) -> NautilusReplayReceipt",
)

PUBLIC_DATACLASSES = (
    offline.NautilusRuntimeCompatibilityResult,
    offline.BinaryOptionMarketContext,
    offline.BinaryOptionMappingResult,
    offline.PmxtV2ReplaySource,
    offline.ConvertedEventStream,
    offline.CatalogBuildResult,
    offline.CatalogQueryResult,
    offline.NautilusReplayReceipt,
)


def test_contract_lists_every_public_function_signature() -> None:
    for signature in PUBLIC_SIGNATURES:
        assert signature in CONTRACT, signature


def test_contract_lists_every_public_dataclass_field() -> None:
    for cls in PUBLIC_DATACLASSES:
        assert cls.__name__ in CONTRACT, cls.__name__
        for field in dataclasses.fields(cls):
            assert f"`{field.name}`" in CONTRACT, f"{cls.__name__}.{field.name}"


def test_contract_has_no_ellipsis_or_refinement_escape() -> None:
    # No reviewer-refinement / implementation-choice escape anywhere in the contract.
    for banned in ("may be refined", "may refine", "implementation may choose"):
        assert banned not in CONTRACT, banned
    # No placeholder ellipsis or open-ended argument list inside a public signature.
    for signature in PUBLIC_SIGNATURES:
        assert "..." not in signature


def test_contract_freezes_identity_constants() -> None:
    assert "wp168-nautilus-pmxt-v2-conversion/1.0.0" in CONTRACT
    assert "polymarket-nautilus-offline-replay-receipt" in CONTRACT
    assert "nautilusreplay:sha256:" in CONTRACT
    assert "WP167_EXTERNAL_DATASET_DESCRIPTOR" in CONTRACT


def test_contract_lists_error_taxonomy_and_successor_gate() -> None:
    for code in (
        "NAUTILUS_RUNTIME_UNSUPPORTED",
        "NAUTILUS_DEPENDENCY_VERSION_INVALID",
        "NAUTILUS_IMPORT_UNAVAILABLE",
        "NAUTILUS_INSTRUMENT_MAPPING_INVALID",
        "NAUTILUS_EVENT_CONVERSION_INVALID",
        "NAUTILUS_CATALOG_WRITE_INVALID",
        "NAUTILUS_CATALOG_QUERY_INVALID",
        "NAUTILUS_REPLAY_INVALID",
        "NAUTILUS_REPLAY_PARITY_INVALID",
    ):
        assert code in CONTRACT, code
    assert "WP169" in CONTRACT and "WP170" in CONTRACT
    assert "separately gated" in CONTRACT
    assert "install" in CONTRACT and "not vendored" in CONTRACT


def test_contract_states_offline_replay_only_boundary() -> None:
    assert "event-replay proof only" in CONTRACT
    assert "no paper/live" in CONTRACT
    assert "execution_authority" in CONTRACT
