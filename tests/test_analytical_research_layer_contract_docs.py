"""Focused docs tests for the WP167 analytical research layer contract.

These assertions keep the canonical contract document honest about the WP167
boundaries: canonical authority unchanged, derived Parquet only, provenance-
separated external history, PyArrow/DuckDB/Polars responsibilities, logical vs
physical identity, pmxt local-only with no downloader, no Nautilus/network/
strategy/Hermes/paper/execution/live, hosted CI as compatibility evidence, and the
WP168 successor boundary.
"""

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "docs" / "analytical_research_layer_contract.md"


def _read() -> str:
    # Normalize whitespace so assertions are insensitive to line wrapping.
    return " ".join(CONTRACT.read_text(encoding="utf-8").split())


def test_contract_doc_exists():
    assert CONTRACT.is_file()


def test_canonical_authority_is_unchanged():
    text = _read()
    assert "Canonical PIT authority is unchanged." in text
    assert "no SQLite migration" in text
    assert "sole canonical integrity authority" in text


def test_derived_parquet_is_materialization_only():
    text = _read()
    assert "Analytical Parquet is derived materialization only." in text
    assert "never silently become canonical repo truth" in text


def test_external_history_is_provenance_separated():
    text = _read()
    assert "External pmxt v2 history is external research evidence only" in text
    assert "THIRD_PARTY_NATIVE_FRAME_ARCHIVE" in text
    assert "native official capture is refused" in text


def test_engine_responsibilities_are_documented():
    text = _read()
    assert "PyArrow owns" in text
    assert "DuckDB owns" in text
    assert "Polars owns" in text
    assert "no Hermes SQL tool and never executes model-generated" in text


def test_logical_vs_physical_identity_is_documented():
    text = _read()
    assert "Logical analytical dataset identity is never defined by physical Parquet file" in text
    assert "same logical dataset id on Windows and Linux" in text
    assert "physical Parquet bytes are allowed to differ" in text


def test_pmxt_is_local_only_with_no_downloader():
    text = _read()
    assert "explicitly supplied local Parquet file paths" in text
    assert "There is no downloader and no product runtime network." in text
    assert "131072" in text


def test_forbidden_boundaries_are_documented():
    text = _read()
    for phrase in (
        "no NautilusTrader",
        "no public WebSocket runtime",
        "no Data API",
        "no Hermes runtime",
        "no strategy",
        "no paper trading",
        "no credentials",
        "no execution or live trading",
        "no scheduler",
    ):
        assert phrase in text
    assert "pyarrow==25.0.1" in text
    assert "duckdb==1.5.5" in text
    assert "polars==1.44.1" in text
    assert ">=3.12,<3.15" in text


def test_hosted_ci_is_compatibility_evidence():
    text = _read()
    assert "Hosted CI is compatibility evidence, not deployment." in text
    assert "ubuntu-24.04 and windows-2022" in text
    assert "Windows Smart App Control" in text


def test_successor_boundary_is_wp168():
    text = _read()
    assert "WP168" in text
    assert "separately gated" in text
