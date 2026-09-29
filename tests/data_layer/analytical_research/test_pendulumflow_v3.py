"""S10-QUAL-DATA-01 PendulumFlow v3 offline parser/validator tests (R006-R008).

Hermetic: synthetic union-schema Parquet hours are written with PyArrow into memory; no
network. ``build_v3_hour`` is reused by the operator tests.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.data_layer.analytical_research import pendulumflow_v3 as v3

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "src" / "data_layer" / "analytical_research" / "pendulumflow_v3.py"

D94 = pa.decimal128(9, 4)
D186 = pa.decimal128(18, 6)
UNION_SCHEMA = pa.schema([
    ("event_type", pa.string()),
    ("timestamp_received", pa.timestamp("us", tz="UTC")),
    ("sequence", pa.uint64()),
    ("timestamp", pa.timestamp("ms", tz="UTC")),
    ("market", pa.binary()),
    ("asset_id", pa.binary()),
    ("best_bid", D94), ("best_ask", D94), ("spread", D94),
    ("price", D94), ("size", D186), ("side", pa.string()), ("fee_rate_bps", pa.uint16()),
    ("transaction_hash", pa.binary()),
    ("id", pa.string()), ("assets_ids", pa.list_(pa.binary())),
    ("winning_asset_id", pa.binary()), ("winning_outcome", pa.string()),
    ("outcomes", pa.list_(pa.string())), ("question", pa.string()), ("slug", pa.string()),
    ("old_tick_size", D94), ("new_tick_size", D94),
])
FAMILY_ORDER = ("best_bid_ask", "last_trade_price", "market_resolved", "new_market", "tick_size_change")
FAMILY_COLUMNS = {
    "best_bid_ask": ["timestamp_received", "sequence", "timestamp", "market", "asset_id", "best_bid", "best_ask", "spread"],
    "last_trade_price": ["timestamp_received", "sequence", "timestamp", "market", "asset_id", "price", "size", "side", "fee_rate_bps", "transaction_hash"],
    "market_resolved": ["timestamp_received", "sequence", "timestamp", "market", "id", "assets_ids", "winning_asset_id", "winning_outcome"],
    "new_market": ["timestamp_received", "sequence", "timestamp", "market", "id", "assets_ids", "outcomes", "question", "slug"],
    "tick_size_change": ["timestamp_received", "sequence", "timestamp", "market", "asset_id", "old_tick_size", "new_tick_size"],
}


def cid(n: int) -> bytes:
    return bytes([n]) * 32


def ts(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _filler_row(family: str) -> dict[str, object]:
    base = {"timestamp_received": ts("2026-08-19T11:00:00Z"), "sequence": 1, "timestamp": ts("2026-08-19T11:00:00Z"),
            "market": b"\xff" * 32}
    if family == "best_bid_ask":
        base.update(asset_id=b"999", best_bid=Decimal("0.1"), best_ask=Decimal("0.2"), spread=Decimal("0.1"))
    elif family == "last_trade_price":
        base.update(asset_id=b"999", price=Decimal("0.1"), size=Decimal("1"), side="BUY", fee_rate_bps=0, transaction_hash=b"\x00")
    elif family == "market_resolved":
        base.update(id="1", assets_ids=[b"998", b"999"], winning_asset_id=b"999", winning_outcome="No")
    elif family == "new_market":
        base.update(id="1", assets_ids=[b"998", b"999"], outcomes=["Yes", "No"], question="Filler?", slug="filler")
    else:
        base.update(asset_id=b"999", old_tick_size=Decimal("0.01"), new_tick_size=Decimal("0.001"))
    return base


def build_v3_hour(hour: str, rows: dict[str, list[dict[str, object]]], *, row_group_size: int = 1_000_000,
                  witnesses: str = "ab", contributors: dict[str, list[str]] | None = None,
                  declared_class: str | None = None, served_verbatim: bool = True) -> tuple[bytes, dict[str, object]]:
    """Write one synthetic union-schema v3 hour; returns ``(parquet_bytes, manifest)``."""

    sink = io.BytesIO()
    writer = pq.ParquetWriter(sink, UNION_SCHEMA, compression="snappy")
    group_counts: dict[str, int] = {}
    for family in FAMILY_ORDER:
        family_rows = sorted(rows.get(family) or [_filler_row(family)], key=lambda r: (r["market"], str(r.get("asset_id")), r["timestamp"]))
        columns = {name: [] for name in UNION_SCHEMA.names}
        for row in family_rows:
            for name in UNION_SCHEMA.names:
                columns[name].append(family if name == "event_type" else row.get(name))
        table = pa.table(columns, schema=UNION_SCHEMA)
        writer.write_table(table, row_group_size=row_group_size)
        group_counts[family] = -(-len(family_rows) // row_group_size)
    writer.close()
    data = sink.getvalue()
    metadata = pq.ParquetFile(io.BytesIO(data)).metadata
    products: dict[str, object] = {}
    group = 0
    for family in FAMILY_ORDER:
        first, last = group, group + group_counts[family] - 1
        starts, ends = [], []
        for g in range(first, last + 1):
            rg = metadata.row_group(g)
            for c in range(rg.num_columns):
                col = rg.column(c)
                start = col.dictionary_page_offset if col.has_dictionary_page and col.dictionary_page_offset else col.data_page_offset
                starts.append(start)
                ends.append(start + col.total_compressed_size)
        start, end = min(starts), max(ends)
        products[family] = {
            "byte_range": [start, end], "row_groups": [first, last],
            "row_count": sum(metadata.row_group(g).num_rows for g in range(first, last + 1)),
            "sha256": hashlib.sha256(data[start:end]).hexdigest(), "columns": FAMILY_COLUMNS[family],
            "order_by": ["market", "asset_id", "timestamp", "sequence"],
        }
        group = last + 1
    date_part, hh = hour.split("/")
    accounting = {}
    for family in FAMILY_ORDER:
        machines = (contributors or {}).get(family, list(witnesses))
        entry: dict[str, object] = {"rows_by_domain": {m: (5 if m in machines else 0) for m in witnesses}}
        if declared_class:
            entry["class"] = declared_class
        accounting[family] = entry
    manifest: dict[str, object] = {
        "hour": hour, "file": f"{date_part}T{hh}.parquet", "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(), "layout": "union-event-sorted-v1", "products": products,
    }
    if served_verbatim:
        manifest.update(served_verbatim=True, witnesses=witnesses, ab_accounting=accounting, merger_git_sha="fcbb28046152741ae3754e951659977da4c8b36e")
    else:
        manifest["derived_from"] = {"source_manifest": {"witnesses": witnesses, "ab_accounting": {
            f: {f"rows_{m}": v for m, v in accounting[f]["rows_by_domain"].items()} for f in FAMILY_ORDER}}}
    return data, manifest


def audit_html(partial_hours: list[str], measured_hours: int = 981, published: int = 1002) -> bytes:
    partial_cells = "".join(f"<tr><td>{h.replace('/', 'T')}</td><td>44/60</td><td>a</td></tr>" for h in partial_hours)
    return (
        "<html><body><p>Hours published measured complete partial could not classify</p>"
        f"<table><tr><td>{published:,}</td><td>{measured_hours}</td><td>{measured_hours - len(partial_hours)}</td>"
        f"<td>{len(partial_hours)}</td><td>0</td></tr></table>"
        f"<p>The partial hours, named below.</p><table>{partial_cells}</table>"
        "<p>Machines expected is the manifest's witnesses field.</p>"
        "<p>Measured on 2026-09-28T05:25:06+00:00 by a separate program.</p></body></html>"
    ).encode("utf-8")


def bba_row(market: int, asset: str, received: str, venue: str, bid: str = "0.40", ask: str = "0.45") -> dict[str, object]:
    return {"timestamp_received": ts(received), "sequence": 7, "timestamp": ts(venue), "market": cid(market),
            "asset_id": asset.encode(), "best_bid": Decimal(bid), "best_ask": Decimal(ask),
            "spread": Decimal(ask) - Decimal(bid)}


HOUR = "2026-08-19/12"


@pytest.fixture(scope="module")
def hour_artifacts() -> tuple[bytes, dict[str, object]]:
    rows = {"best_bid_ask": [
        bba_row(m, str(10_000_000 + m * 7919 + k), f"2026-08-19T12:{k // 60:02d}:{k % 60:02d}.{(m * 37 + k) % 999999:06d}Z",
                f"2026-08-19T12:{k // 60:02d}:{k % 60:02d}.{(m * 11 + k) % 999:03d}Z",
                bid=f"0.{(m * 13 + k) % 90 + 10:02d}", ask=f"0.{(m * 17 + k) % 90 + 10:02d}")
        for m in range(1, 40) for k in range(0, 240)
    ]}
    return build_v3_hour(HOUR, rows, row_group_size=1200)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("not_mapping", "V3_MANIFEST_INVALID"),
        ("wrong_hour", "V3_HOUR_INVALID"),
        ("wrong_file", "V3_MANIFEST_INVALID"),
        ("missing_product", "V3_PRODUCT_MISSING"),
        ("range_beyond_file", "V3_BYTE_RANGE_INVALID"),
        ("range_inverted", "V3_BYTE_RANGE_INVALID"),
        ("range_overlap", "V3_BYTE_RANGE_INVALID"),
        ("row_groups_overlap", "V3_ROW_GROUPS_INVALID"),
        ("bad_sha", "V3_MANIFEST_INVALID"),
        ("bool_bytes", "V3_MANIFEST_INVALID"),
        ("bad_witnesses", "V3_WITNESS_ACCOUNTING_INVALID"),
        ("unknown_class", "V3_COVERAGE_UNCLASSIFIED"),
        ("bad_layout", "V3_MANIFEST_INVALID"),
    ],
)
def test_manifest_validation_fail_closed(hour_artifacts, mutation: str, code: str) -> None:
    data, manifest = hour_artifacts
    v3.validate_manifest(manifest, HOUR)  # the untouched manifest is valid
    bad = copy.deepcopy(manifest)
    products = bad["products"]
    if mutation == "not_mapping":
        bad = ["not", "a", "manifest"]
    elif mutation == "wrong_hour":
        bad["hour"] = "2026-08-19/13"
    elif mutation == "wrong_file":
        bad["file"] = "2026-08-19T13.parquet"
    elif mutation == "missing_product":
        del products["best_bid_ask"]
    elif mutation == "range_beyond_file":
        products["tick_size_change"]["byte_range"][1] = len(data) + 10
    elif mutation == "range_inverted":
        products["new_market"]["byte_range"] = [500, 400]
    elif mutation == "range_overlap":
        products["last_trade_price"]["byte_range"][0] = products["best_bid_ask"]["byte_range"][1] - 1
    elif mutation == "row_groups_overlap":
        products["last_trade_price"]["row_groups"][0] = products["best_bid_ask"]["row_groups"][1]
    elif mutation == "bad_sha":
        products["new_market"]["sha256"] = "XYZ"
    elif mutation == "bool_bytes":
        bad["bytes"] = True
    elif mutation == "bad_witnesses":
        bad["witnesses"] = "AB!"
    elif mutation == "unknown_class":
        bad["ab_accounting"]["best_bid_ask"]["class"] = "MOSTLY_FINE"
    elif mutation == "bad_layout":
        bad["layout"] = "other"
    with pytest.raises(v3.PendulumFlowError) as excinfo:
        v3.validate_manifest(bad, HOUR)
    assert excinfo.value.code == code
    assert str(excinfo.value) == code  # closed code only, no echo


def test_product_sha256_and_parquet_tail_fail_closed(hour_artifacts) -> None:
    data, manifest = hour_artifacts
    parsed = v3.validate_manifest(manifest, HOUR)
    product = parsed.product("new_market")
    good = data[product.byte_start:product.byte_end]
    assert v3.verify_product_bytes(product, good) == product.sha256
    for bad in (good[:-1], b"\x00" + good[1:], b""):
        with pytest.raises(v3.PendulumFlowError) as excinfo:
            v3.verify_product_bytes(product, bad)
        assert excinfo.value.code == "V3_PRODUCT_SHA256_MISMATCH"
    start, length = v3.parse_parquet_tail(data[-8:], len(data))
    assert start + length == len(data) - 8
    for tail in (data[-8:-4] + b"PAR2", b"\x00" * 8, data[-7:]):
        with pytest.raises(v3.PendulumFlowError) as excinfo:
            v3.parse_parquet_tail(tail, len(data))
        assert excinfo.value.code == "V3_PARQUET_TAIL_INVALID"


def test_event_timestamps_remain_distinct() -> None:
    early_venue = bba_row(1, "101", "2026-08-19T12:05:00.000100Z", "2026-08-19T12:04:00Z")
    late_venue = bba_row(1, "101", "2026-08-19T12:03:00.000200Z", "2026-08-19T12:04:30Z")
    late_venue["sequence"] = 1  # sequence is provenance only and never an ordering key
    early_venue["sequence"] = 99
    events = [v3.normalize_row("best_bid_ask", HOUR, 0, row) for row in (early_venue, late_venue)]
    first = events[0]
    assert first.timestamp_received == "2026-08-19T12:05:00.000100Z"
    assert first.venue_timestamp == "2026-08-19T12:04:00.000Z"
    assert first.timestamp_received != first.venue_timestamp
    assert "sequence" not in dict(first.fields)
    ordered = v3.order_events(events)
    # Observability order follows timestamp_received even though the venue clock is reversed.
    assert [e.timestamp_received for e in ordered] == ["2026-08-19T12:03:00.000200Z", "2026-08-19T12:05:00.000100Z"]
    assert ordered[0].venue_timestamp > ordered[1].venue_timestamp
    assert ordered[0].condition_id == "0x" + "01" * 32 and ordered[0].asset_id == "101"
    duplicate = v3.normalize_row("best_bid_ask", HOUR, 0, early_venue)
    assert len(v3.dedupe_events(events + [duplicate])) == 2


@pytest.mark.parametrize(
    ("row_patch", "family"),
    [
        ({"market": b"\x01" * 31}, "best_bid_ask"),
        ({"asset_id": b"12a"}, "best_bid_ask"),
        ({"timestamp_received": datetime(2026, 8, 19, 12)}, "best_bid_ask"),
        ({"best_bid": 0.4}, "best_bid_ask"),
        ({"id": "abc", "assets_ids": [b"1"], "outcomes": ["Yes"], "question": "q", "slug": "s"}, "new_market"),
        ({"id": "5", "assets_ids": [b"1", b"2"], "outcomes": ["Yes"], "question": "q", "slug": "s"}, "new_market"),
    ],
)
def test_row_normalization_rejects_malformed_fields(row_patch: dict[str, object], family: str) -> None:
    row = {**bba_row(1, "101", "2026-08-19T12:01:00Z", "2026-08-19T12:01:00Z"), **row_patch}
    with pytest.raises(v3.PendulumFlowError) as excinfo:
        v3.normalize_row(family, HOUR, 0, row)
    assert excinfo.value.code == "V3_ROW_INVALID"


def test_coverage_class_admission() -> None:
    audit = v3.parse_audit_page(audit_html(["2026-08-20/17"]))
    assert audit.partial_hours == frozenset({"2026-08-20/17"})
    assert audit.measured_hours == 981 and audit.measured_on == "2026-09-28T05:25:06Z"
    cases = [
        ("2026-08-20/12", {"witnesses": "ab"}, "FULL"),
        ("2026-08-20/15", {"witnesses": "b", "served_verbatim": False}, "SINGLE-BY-DESIGN"),
        ("2026-08-20/16", {"witnesses": "ab", "contributors": {f: ["a"] for f in FAMILY_ORDER}}, "SINGLE-BY-DEFECT"),
        ("2026-08-20/17", {"witnesses": "ab"}, "PARTIAL"),
        ("2026-08-20/13", {"witnesses": "ab", "declared_class": "SINGLE-BY-DEFECT"}, "SINGLE-BY-DEFECT"),
    ]
    for hour, options, expected in cases:
        _data, manifest = build_v3_hour(hour, {}, **options)
        parsed = v3.validate_manifest(manifest, hour)
        klass = v3.classify_product_coverage(parsed, "best_bid_ask", audit)
        assert klass == expected, hour
        dq, fidelity = v3.coverage_quality(klass)
        if expected in ("FULL", "SINGLE-BY-DESIGN"):
            assert klass in v3.ADMISSIBLE_COVERAGE_CLASSES and dq == ("OK",) and fidelity == "FAITHFUL"
        else:
            assert klass not in v3.ADMISSIBLE_COVERAGE_CLASSES
            assert dq == ("PARTIALLY_OBSERVED",) and fidelity == "PARTIAL"
    # An hour the audit has not yet measured is never assumed complete.
    late = "2026-09-28/05"
    _data, manifest = build_v3_hour(late, {})
    with pytest.raises(v3.PendulumFlowError) as excinfo:
        v3.classify_product_coverage(v3.validate_manifest(manifest, late), "best_bid_ask", audit)
    assert excinfo.value.code == "V3_COVERAGE_UNCLASSIFIED"
    # Zero contributors cannot be classified.
    _data, manifest = build_v3_hour("2026-08-20/12", {}, contributors={f: [] for f in FAMILY_ORDER})
    with pytest.raises(v3.PendulumFlowError):
        v3.classify_product_coverage(v3.validate_manifest(manifest, "2026-08-20/12"), "best_bid_ask", audit)


def test_audit_page_tally_must_match_named_hours() -> None:
    raw = audit_html(["2026-08-18/06", "2026-08-18/13"]).replace(b"<td>2</td><td>0</td>", b"<td>3</td><td>0</td>")
    with pytest.raises(v3.PendulumFlowError) as excinfo:
        v3.parse_audit_page(raw)
    assert excinfo.value.code == "V3_AUDIT_INVALID"
    with pytest.raises(v3.PendulumFlowError):
        v3.parse_audit_page(b"<html>nothing here</html>")


def test_targeted_row_group_reads_only_needed_chunks(hour_artifacts) -> None:
    data, manifest = hour_artifacts
    parsed = v3.validate_manifest(manifest, HOUR)
    start, _length = v3.parse_parquet_tail(data[-8:], len(data))
    begin, end = v3.footer_fetch_range(len(data), start)
    assert begin <= start and end == len(data) - 8
    retained = [(len(data) - 8, data[-8:]), (begin, data[begin:end])]
    parquet = v3.open_parquet(len(data), retained)
    product = parsed.product("best_bid_ask")
    groups = v3.product_row_groups_for_markets(parquet, product, [cid(20)])
    assert len(groups) == 1 and product.row_group_first <= groups[0] <= product.row_group_last
    ranges = v3.column_chunk_ranges(parquet, product, groups[0], v3.READ_COLUMNS["best_bid_ask"])
    total = sum(e - b for b, e in ranges)
    assert all(product.byte_start <= b < e <= product.byte_end for b, e in ranges)
    assert total < product.byte_end - product.byte_start  # never the whole product
    with pytest.raises(v3.PendulumFlowError) as excinfo:
        parquet.read_row_group(groups[0], columns=list(v3.READ_COLUMNS["best_bid_ask"]))
    assert excinfo.value.code == "V3_RANGE_NOT_RETAINED"
    retained += [(b, data[b:e]) for b, e in ranges]
    table = v3.open_parquet(len(data), retained).read_row_group(groups[0], columns=list(v3.READ_COLUMNS["best_bid_ask"]))
    events = [v3.normalize_row("best_bid_ask", HOUR, groups[0], row) for row in table.to_pylist()]
    assert any(e.condition_id == "0x" + "14" * 32 for e in events)
    with pytest.raises(v3.PendulumFlowError):
        v3.column_chunk_ranges(parquet, product, product.row_group_last + 1, ["market"])


def test_source_class_constants_are_external_never_canonical() -> None:
    assert v3.SOURCE_CLASS == "THIRD_PARTY_NATIVE_FRAME_ARCHIVE"
    assert v3.B0_SOURCE_AUTHORITY == "EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION"
    source = MODULE.read_text(encoding="utf-8")
    assert "SOURCE_KIND_CANONICAL_PIT" not in source
    assert "DatasetSnapshotReference" not in source


def test_module_is_offline() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert not roots & {"urllib", "http", "requests", "httpx", "socket", "subprocess", "aiohttp", "boto3", "websockets"}
    assert "open(" not in MODULE.read_text(encoding="utf-8").replace("open_parquet(", "")
