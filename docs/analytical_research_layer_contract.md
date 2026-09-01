# Analytical Research, External History & Materialization Foundation Contract (WP167)

This document is the canonical contract for the WP167 analytical research plane:
the first scalable local/offline analytical layer on top of the merged
deterministic point-in-time (PIT) evidence system. It is advisory research
infrastructure only and has no execution authority.

## Canonical authority is unchanged

Canonical PIT authority is unchanged. The WP156–WP166 SQLite records and
manifests remain the sole canonical integrity authority. WP167 introduces no
SQLite migration, no manifest or dataset-snapshot-reference migration, no
canonical record serialization change, and no predecessor identity-hash change.
The analytical package reads canonical evidence exclusively through the merged
WP163 public API (`load_and_verify_point_in_time_record_store` and
`materialize_dataset_snapshot_reference`) and never writes a canonical store.

## Derived Parquet is analytical materialization only

Analytical Parquet is derived materialization only. Derived research datasets are
produced from verified canonical PIT data and can never silently become canonical
repo truth. Derived Parquet partitions are written only to a caller-supplied
output directory (pytest `tmp_path` in tests) and are never committed; no
`local_data/` path and no generated artifact is tracked.

## External history is provenance-separated research evidence

External pmxt v2 history is external research evidence only, classified through an
`ExternalDatasetDescriptor` with a `source_class`. The representative source used
to prove the generic boundary is the pmxt Polymarket Orderbook Archive v2, always
classified `THIRD_PARTY_NATIVE_FRAME_ARCHIVE`. A request to describe pmxt v2 as a
native official capture is refused. External history can never silently become
canonical repo truth and is kept provenance-separated from canonical PIT data.

## PyArrow, DuckDB, and Polars responsibilities

- PyArrow owns explicit analytical schemas, stable Arrow interchange,
  canonical-to-derived table construction, deterministic Parquet writing for
  repo-derived canonical PIT data, and Parquet schema inspection for external
  history.
- DuckDB owns SQL over Parquet: read-only relational analytical access with
  COUNT, grouped counts, deterministic filters, and timestamp min/max cross
  checks. WP167 implements no Hermes SQL tool and never executes model-generated
  SQL.
- Polars owns lazy `scan_parquet` transforms: deterministic projection, grouping,
  filtering, and timestamp handling as the future feature/label substrate.

## Logical identity versus physical identity

Logical analytical dataset identity is never defined by physical Parquet file
bytes. A logical dataset identity is derived from the analytical schema and
version, the source kind, the canonical `DatasetSnapshotReference` id (or external
`ExternalDatasetDescriptor` id), the materializer/importer semantic version, and
the ordered per-table row counts and deterministic streaming logical row digests
computed in explicit canonical row order. The same logical input yields the same
logical dataset id on Windows and Linux, while the physical Parquet bytes are
allowed to differ. Physical materialization evidence — the relative file path,
exact file SHA-256, byte length, schema fingerprint, and library/Python versions
— is recorded separately from the logical identity. No absolute local path,
environment value, username, hostname, wall-clock creation time, secret, or raw
exception string ever enters an identity or a result.

## pmxt is local-only with no downloader

The pmxt v2 adapter accepts only explicitly supplied local Parquet file paths. It
performs no URL retrieval, no HTTP, no Polymarket API call, and no object-store
SDK call. There is no downloader and no product runtime network. Real pmxt files
are large, so validation is metadata-first and bounded: schema is inspected
without whole-file materialization and rows are scanned in bounded batches of at
most 131072 rows; DuckDB and Polars scan the verified source files directly rather
than rewriting them.

## Boundaries this WP does not cross

WP167 adds no NautilusTrader, no public WebSocket runtime, no Data API activity or
wallet ingestion, no Hermes runtime, no strategy, no paper trading, no
credentials or authenticated endpoints, no execution or live trading, and no
scheduler, daemon, or bot loop. There is no product network. The exact three new
direct runtime dependencies are `pyarrow==25.0.1`, `duckdb==1.5.5`, and
`polars==1.44.1`, and the Python support floor moves to `>=3.12,<3.15`.

## Hosted CI is compatibility evidence, not deployment

Hosted CI is compatibility evidence, not deployment. The `.github/workflows/ci.yml`
matrix runs on ubuntu-24.04 and windows-2022 with Python 3.12 and 3.14 to prove
that the pinned dependencies install and the analytical package behaves
identically across platforms. It uses no secrets, no product API, and no external
archive download. DuckDB-dependent tests are executed without skips under strict
hosted CI; where the local DuckDB native module is blocked by Windows Smart App
Control the DuckDB proofs are skipped locally with an explicit reason and executed
in hosted CI instead.

## Successor boundary

The next work package is WP168 — NautilusTrader Offline Kernel, ParquetDataCatalog
& Replay Foundation. WP168 is separately gated and is not authorized by WP167.
Additional external adapters (pmxt v1, Jon Becker, Kalshi, OpenMarket), a public
WebSocket collector, the public Data API activity plane, an experiment registry,
and an automated external downloader all remain separately gated successors.
