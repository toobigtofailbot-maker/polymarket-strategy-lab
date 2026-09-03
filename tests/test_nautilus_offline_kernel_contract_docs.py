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


def test_public_api_and_dataclasses_are_exactly_frozen() -> None:
    # R051: the package-root public surface is exactly the six frozen functions and eight
    # frozen dataclasses; helper functions are private; signatures/fields/types are exact.
    import inspect

    frozen_functions = {
        "evaluate_offline_runtime",
        "build_binary_option",
        "convert_pmxt_v2_events",
        "build_catalog",
        "query_catalog",
        "run_offline_replay",
    }
    frozen_dataclasses = {
        "NautilusRuntimeCompatibilityResult",
        "BinaryOptionMarketContext",
        "BinaryOptionMappingResult",
        "PmxtV2ReplaySource",
        "ConvertedEventStream",
        "CatalogBuildResult",
        "CatalogQueryResult",
        "NautilusReplayReceipt",
    }
    assert set(offline.__all__) == frozen_functions | frozen_dataclasses
    assert len(offline.__all__) == 14

    # No private helper is root-exported.
    for helper in (
        "canonical_json_bytes", "_canonical_json_bytes",
        "scan_public_result_for_echo", "_scan_public_result_for_echo",
        "stream_identity_digest", "_stream_identity_digest",
        "stream_identity_preimage", "_stream_identity_preimage",
    ):
        assert helper not in offline.__all__
        assert not hasattr(offline, helper)

    expected_signatures = {
        "evaluate_offline_runtime": [],
        "build_binary_option": ["context"],
        "convert_pmxt_v2_events": ["source", "context"],
        "build_catalog": ["stream", "catalog_dir"],
        "query_catalog": ["build_result"],
        "run_offline_replay": ["stream", "catalog_dir"],
    }
    for name, params in expected_signatures.items():
        func = getattr(offline, name)
        assert callable(func)
        assert list(inspect.signature(func).parameters) == params, name

    expected_fields = {
        "NautilusRuntimeCompatibilityResult": {
            "is_valid": "bool", "status": "str", "error_codes": "tuple[str, ...]",
            "nautilus_version": "str | None", "python_version": "str",
            "advisory_only": "bool", "no_execution_authority": "bool"},
        "BinaryOptionMarketContext": {
            "condition_id": "str", "outcome_token_id": "str", "outcome_label": "str",
            "description": "str | None", "activation_ns": "int | None",
            "expiration_ns": "int | None", "price_increment": "str", "size_increment": "str",
            "maker_fee": "str | None", "taker_fee": "str | None", "ts_event_ns": "int",
            "ts_init_ns": "int"},
        "BinaryOptionMappingResult": {
            "is_valid": "bool", "status": "str", "error_codes": "tuple[str, ...]",
            "instrument_id": "str | None", "price_increment": "str | None",
            "size_increment": "str | None", "warnings": "tuple[str, ...]",
            "binary_option": "object | None"},
        "PmxtV2ReplaySource": {
            "descriptor": "ExternalDatasetDescriptor",
            "source_files": "tuple[PmxtV2SourceFile, ...]"},
        "ConvertedEventStream": {
            "is_valid": "bool", "status": "str", "error_codes": "tuple[str, ...]",
            "instrument_id": "str | None", "source_dataset_kind": "str | None",
            "source_external_dataset_id": "str | None", "conversion_policy_version": "str | None",
            "ordered_event_digests": "tuple[str, ...]",
            "input_event_counts_by_type": "tuple[tuple[str, int], ...]",
            "tick_size_regime_sequence": "tuple[tuple[str, str, int], ...]",
            "first_event_time_ns": "int | None", "last_event_time_ns": "int | None",
            "warnings": "tuple[str, ...]", "converted_events": "tuple[object, ...]"},
        "CatalogBuildResult": {
            "is_valid": "bool", "status": "str", "error_codes": "tuple[str, ...]",
            "instrument_registered": "bool", "written_delta_count": "int",
            "written_trade_count": "int", "catalog_dir": "str | None",
            "stream_ref_digest": "str | None"},
        "CatalogQueryResult": {
            "is_valid": "bool", "status": "str", "error_codes": "tuple[str, ...]",
            "queried_delta_count": "int", "queried_trade_count": "int",
            "round_trip_matches": "bool"},
        "NautilusReplayReceipt": {
            "is_valid": "bool", "status": "str", "error_codes": "tuple[str, ...]",
            "schema_id": "str", "schema_version": "str", "source_dataset_kind": "str",
            "source_external_dataset_id": "str | None", "conversion_policy_version": "str | None",
            "nautilus_version": "str | None", "instrument_id": "str | None",
            "input_event_counts_by_type": "tuple[tuple[str, int], ...]",
            "first_event_time_ns": "int | None", "last_event_time_ns": "int | None",
            "tick_size_regime_sequence": "tuple[tuple[str, str, int], ...]",
            "replay_processed_event_count": "int", "replay_digest": "str | None",
            "warnings": "tuple[str, ...]", "execution_authority": "bool"},
    }
    for name, fields in expected_fields.items():
        cls = getattr(offline, name)
        assert dataclasses.is_dataclass(cls), name
        assert cls.__dataclass_params__.frozen is True, name
        actual = {f.name: f.type for f in dataclasses.fields(cls)}
        assert actual == fields, name
        # public collection fields use immutable tuple shapes (no mutable list/dict).
        for field_name, type_str in fields.items():
            if "[" in type_str:
                assert type_str.startswith("tuple"), f"{name}.{field_name}"


def test_contract_states_offline_replay_only_boundary() -> None:
    assert "event-replay proof only" in CONTRACT
    assert "no paper/live" in CONTRACT
    assert "execution_authority" in CONTRACT
