"""S10-QUAL-DATA-01 PendulumFlow v3 offline parser and validator.

PendulumFlow v3 is a THIRD-PARTY native frame archive of the public Polymarket market feed:
one union Parquet file plus one ``manifest.json`` per UTC hour. This module validates those
artifacts from bytes that the S10-QUAL-DATA-01 operator has already acquired. It performs NO
network access, constructs no client and never writes files.

It owns:

- manifest schema/bounds validation (two observed shapes: rebuilt ``derived_from`` hours and
  ``served_verbatim`` union hours);
- product byte-range / row-group bound validation and product SHA-256 verification;
- Parquet tail/footer bound validation and column-chunk range targeting inside one product;
- product-specific coverage classification (FULL / PARTIAL / SINGLE-BY-DESIGN /
  SINGLE-BY-DEFECT) from the manifest witness accounting plus the archive's own audit page;
- event-family row normalization with ``timestamp_received`` (capture availability) kept
  distinct from the venue ``timestamp``;
- deterministic ordering by ``timestamp_received`` (never by ``sequence`` or file order).

Source authority is fixed: ``THIRD_PARTY_NATIVE_FRAME_ARCHIVE`` with B0 source authority
``EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION``. Nothing here is canonical PIT evidence. Errors are
closed codes only and never echo raw bytes, paths or values.
"""

from __future__ import annotations

import hashlib
import html
import io
import re
import struct
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Mapping, Sequence

PROVIDER_ID = "pendulumflow"
DATASET_NAME = "v3"
SOURCE_CLASS = "THIRD_PARTY_NATIVE_FRAME_ARCHIVE"
B0_SOURCE_AUTHORITY = "EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION"
LIVE_START_HOUR = "2026-08-18/06"

REQUIRED_EVENT_FAMILIES = (
    "new_market",
    "market_resolved",
    "best_bid_ask",
    "last_trade_price",
    "tick_size_change",
)
# Products present in every observed union hour; ``book`` and ``price_change`` are validated for
# bounds but never read by default.
ALL_PRODUCTS = REQUIRED_EVENT_FAMILIES + ("book", "price_change")

COVERAGE_CLASSES = ("FULL", "SINGLE-BY-DESIGN", "SINGLE-BY-DEFECT", "PARTIAL")
ADMISSIBLE_COVERAGE_CLASSES = frozenset({"FULL", "SINGLE-BY-DESIGN"})
_COVERAGE_RANK = {name: index for index, name in enumerate(COVERAGE_CLASSES)}

MANIFEST_SHAPES = ("DERIVED_REBUILT_HOUR", "SERVED_VERBATIM_UNION_HOUR")

PENDULUMFLOW_ERROR_CODES = (
    "V3_HOUR_INVALID",
    "V3_MANIFEST_INVALID",
    "V3_PRODUCT_MISSING",
    "V3_BYTE_RANGE_INVALID",
    "V3_ROW_GROUPS_INVALID",
    "V3_WITNESS_ACCOUNTING_INVALID",
    "V3_COVERAGE_UNCLASSIFIED",
    "V3_AUDIT_INVALID",
    "V3_PRODUCT_SHA256_MISMATCH",
    "V3_PARQUET_TAIL_INVALID",
    "V3_COLUMN_CHUNK_OUT_OF_RANGE",
    "V3_RANGE_NOT_RETAINED",
    "V3_ROW_INVALID",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_HOUR_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})/(\d{2})$")
_WITNESS_RE = re.compile(r"^[a-z]{1,16}$")
_AUDIT_HOUR_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})T(\d{2})\b")
_DIGITS_RE = re.compile(r"^[0-9]{1,100}$")
_PARQUET_MAGIC = b"PAR1"
_MAX_FOOTER_BYTES = 64 * 1024 * 1024


class PendulumFlowError(ValueError):
    """Closed, no-echo rejection. ``str(error)`` is exactly the closed code."""

    def __init__(self, code: str) -> None:
        if code not in PENDULUMFLOW_ERROR_CODES:
            code = "V3_MANIFEST_INVALID"
        super().__init__(code)
        self.code = code


# ── Hours and object names ────────────────────────────────────────────────────


def hour_key(moment: datetime) -> str:
    """Return the ``YYYY-MM-DD/HH`` partition key of the UTC hour containing ``moment``."""

    if moment.tzinfo is None:
        raise PendulumFlowError("V3_HOUR_INVALID")
    utc = moment.astimezone(timezone.utc)
    return f"{utc:%Y-%m-%d}/{utc:%H}"


def hour_start(hour: str) -> datetime:
    match = _HOUR_RE.fullmatch(hour) if isinstance(hour, str) else None
    if match is None:
        raise PendulumFlowError("V3_HOUR_INVALID")
    try:
        year, month, day, hh = (int(part) for part in match.groups())
        return datetime(year, month, day, hh, tzinfo=timezone.utc)
    except ValueError:
        raise PendulumFlowError("V3_HOUR_INVALID") from None


def hours_between(start: datetime, end: datetime) -> tuple[str, ...]:
    """Every hour key intersecting the closed UTC interval ``[start, end]``, ascending."""

    if end < start:
        return ()
    cursor = start.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    keys: list[str] = []
    while cursor <= end:
        keys.append(hour_key(cursor))
        cursor += timedelta(hours=1)
    return tuple(keys)


def manifest_object_path(hour: str) -> str:
    hour_start(hour)
    return f"v3/{hour}/manifest.json"


def parquet_object_name(hour: str) -> str:
    start = hour_start(hour)
    return f"{start:%Y-%m-%d}T{start:%H}.parquet"


def parquet_object_path(hour: str) -> str:
    return f"v3/{hour}/{parquet_object_name(hour)}"


# ── Manifest validation ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class V3Product:
    name: str
    byte_start: int
    byte_end: int  # exclusive
    row_group_first: int
    row_group_last: int  # inclusive
    row_count: int
    sha256: str
    columns: tuple[str, ...]


@dataclass(frozen=True)
class V3Manifest:
    hour: str
    shape: str
    file_name: str
    file_bytes: int
    file_sha256: str
    layout: str
    products: tuple[V3Product, ...]
    witnesses_expected: tuple[str, ...]
    contributors_by_product: tuple[tuple[str, tuple[str, ...]], ...]
    declared_class_by_product: tuple[tuple[str, str | None], ...]
    merger_git_sha: str | None

    def product(self, name: str) -> V3Product:
        for item in self.products:
            if item.name == name:
                return item
        raise PendulumFlowError("V3_PRODUCT_MISSING")

    def contributors(self, name: str) -> tuple[str, ...]:
        return dict(self.contributors_by_product).get(name, ())

    def declared_class(self, name: str) -> str | None:
        return dict(self.declared_class_by_product).get(name)


def _int(value: object, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise PendulumFlowError("V3_MANIFEST_INVALID")
    return value


def _sha(value: object) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise PendulumFlowError("V3_MANIFEST_INVALID")
    return value


def _pair(value: object, code: str) -> tuple[int, int]:
    if type(value) is not list or len(value) != 2:
        raise PendulumFlowError(code)
    first, second = value
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (first, second)):
        raise PendulumFlowError(code)
    return first, second


def _product(name: str, raw: object, file_bytes: int) -> V3Product:
    if not isinstance(raw, Mapping):
        raise PendulumFlowError("V3_PRODUCT_MISSING")
    start, end = _pair(raw.get("byte_range"), "V3_BYTE_RANGE_INVALID")
    # Half-open [start, end) strictly inside the Parquet body: after the leading magic and
    # before the trailing footer-length + magic.
    if not (len(_PARQUET_MAGIC) <= start < end <= file_bytes - 8):
        raise PendulumFlowError("V3_BYTE_RANGE_INVALID")
    first, last = _pair(raw.get("row_groups"), "V3_ROW_GROUPS_INVALID")
    if not (0 <= first <= last):
        raise PendulumFlowError("V3_ROW_GROUPS_INVALID")
    columns = raw.get("columns")
    if type(columns) is not list or not columns or not all(isinstance(c, str) and c for c in columns):
        raise PendulumFlowError("V3_MANIFEST_INVALID")
    return V3Product(
        name=name,
        byte_start=start,
        byte_end=end,
        row_group_first=first,
        row_group_last=last,
        row_count=_int(raw.get("row_count")),
        sha256=_sha(raw.get("sha256")),
        columns=tuple(columns),
    )


def _witness_block(manifest: Mapping[str, object]) -> tuple[str, Mapping[str, object], object, str | None]:
    if manifest.get("served_verbatim") is True:
        shape = "SERVED_VERBATIM_UNION_HOUR"
        block: Mapping[str, object] = manifest
        merger = manifest.get("merger_git_sha")
    else:
        derived = manifest.get("derived_from")
        if not isinstance(derived, Mapping) or not isinstance(derived.get("source_manifest"), Mapping):
            raise PendulumFlowError("V3_WITNESS_ACCOUNTING_INVALID")
        shape = "DERIVED_REBUILT_HOUR"
        block = derived["source_manifest"]  # type: ignore[assignment]
        merger = block.get("merger_git_sha")
    witnesses = block.get("witnesses")
    accounting = block.get("ab_accounting")
    if not isinstance(witnesses, str) or not _WITNESS_RE.fullmatch(witnesses):
        raise PendulumFlowError("V3_WITNESS_ACCOUNTING_INVALID")
    if len(set(witnesses)) != len(witnesses) or not isinstance(accounting, Mapping):
        raise PendulumFlowError("V3_WITNESS_ACCOUNTING_INVALID")
    merger_sha = merger if isinstance(merger, str) and re.fullmatch(r"[0-9a-f]{7,40}", merger) else None
    return shape, accounting, witnesses, merger_sha


def _contributors(entry: object) -> tuple[str, ...]:
    """Machines that contributed at least one row to one product (``rows_<m>`` > 0)."""

    if not isinstance(entry, Mapping):
        raise PendulumFlowError("V3_WITNESS_ACCOUNTING_INVALID")
    counts: dict[str, int] = {}
    by_domain = entry.get("rows_by_domain")
    if by_domain is not None:
        if not isinstance(by_domain, Mapping):
            raise PendulumFlowError("V3_WITNESS_ACCOUNTING_INVALID")
        for machine, value in by_domain.items():
            if not (isinstance(machine, str) and _WITNESS_RE.fullmatch(machine)):
                raise PendulumFlowError("V3_WITNESS_ACCOUNTING_INVALID")
            counts[machine] = _int(value)
    for key, value in entry.items():
        match = re.fullmatch(r"rows_([a-z])", key)
        if match:
            machine = match.group(1)
            count = _int(value)
            if machine in counts and counts[machine] != count:
                raise PendulumFlowError("V3_WITNESS_ACCOUNTING_INVALID")
            counts[machine] = count
    if not counts:
        raise PendulumFlowError("V3_WITNESS_ACCOUNTING_INVALID")
    return tuple(sorted(machine for machine, count in counts.items() if count > 0))


def validate_manifest(manifest: object, expected_hour: str) -> V3Manifest:
    """Validate one hour's ``manifest.json`` object fail-closed."""

    hour_start(expected_hour)
    if not isinstance(manifest, Mapping):
        raise PendulumFlowError("V3_MANIFEST_INVALID")
    if manifest.get("hour") != expected_hour:
        raise PendulumFlowError("V3_HOUR_INVALID")
    file_name = manifest.get("file")
    if file_name != parquet_object_name(expected_hour):
        raise PendulumFlowError("V3_MANIFEST_INVALID")
    file_bytes = _int(manifest.get("bytes"), minimum=16)
    file_sha256 = _sha(manifest.get("sha256"))
    layout = manifest.get("layout")
    if layout != "union-event-sorted-v1":
        raise PendulumFlowError("V3_MANIFEST_INVALID")
    raw_products = manifest.get("products")
    if not isinstance(raw_products, Mapping):
        raise PendulumFlowError("V3_MANIFEST_INVALID")
    for name in REQUIRED_EVENT_FAMILIES:
        if name not in raw_products:
            raise PendulumFlowError("V3_PRODUCT_MISSING")
    products = tuple(
        _product(name, raw_products[name], file_bytes) for name in sorted(raw_products)
    )
    # Products must not overlap in bytes or row groups.
    by_bytes = sorted(products, key=lambda p: p.byte_start)
    for left, right in zip(by_bytes, by_bytes[1:]):
        if right.byte_start < left.byte_end:
            raise PendulumFlowError("V3_BYTE_RANGE_INVALID")
    by_groups = sorted(products, key=lambda p: p.row_group_first)
    for left, right in zip(by_groups, by_groups[1:]):
        if right.row_group_first <= left.row_group_last:
            raise PendulumFlowError("V3_ROW_GROUPS_INVALID")
    shape, accounting, witnesses, merger = _witness_block(manifest)
    contributors: list[tuple[str, tuple[str, ...]]] = []
    declared: list[tuple[str, str | None]] = []
    for product in products:
        entry = accounting.get(product.name)
        if entry is None:
            if product.name in REQUIRED_EVENT_FAMILIES:
                raise PendulumFlowError("V3_WITNESS_ACCOUNTING_INVALID")
            continue
        contributors.append((product.name, _contributors(entry)))
        declared_class = entry.get("class") if isinstance(entry, Mapping) else None
        if declared_class is not None and declared_class not in COVERAGE_CLASSES:
            raise PendulumFlowError("V3_COVERAGE_UNCLASSIFIED")
        declared.append((product.name, declared_class))
    return V3Manifest(
        hour=expected_hour,
        shape=shape,
        file_name=file_name,
        file_bytes=file_bytes,
        file_sha256=file_sha256,
        layout=layout,
        products=products,
        witnesses_expected=tuple(witnesses),
        contributors_by_product=tuple(contributors),
        declared_class_by_product=tuple(declared),
        merger_git_sha=merger,
    )


# ── Coverage classification ───────────────────────────────────────────────────


@dataclass(frozen=True)
class V3AuditSnapshot:
    partial_hours: frozenset[str]
    measured_on: str
    published_hours: int
    measured_hours: int


def _audit_text(raw_html: str) -> str:
    stripped = re.sub(r"<(script|style)\b.*?</\1>", " ", raw_html, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", stripped))
    return re.sub(r"\s+", " ", text)


def parse_audit_page(raw: bytes) -> V3AuditSnapshot:
    """Parse the archive's own audit page: the named PARTIAL hours and the measurement date.

    The published tally ``Hours published measured complete partial could not classify`` must
    agree with the number of named partial hours, otherwise the page is rejected.
    """

    try:
        text = _audit_text(raw.decode("utf-8"))
    except (UnicodeDecodeError, AttributeError):
        raise PendulumFlowError("V3_AUDIT_INVALID") from None
    tally = re.search(
        r"Hours published measured complete partial could not classify\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)",
        text,
    )
    start = text.find("The partial hours, named")
    end = text.find("Machines expected is the manifest", start)
    measured = re.search(r"Measured on (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00)", text[end:] if end > 0 else "")
    if tally is None or start < 0 or end < 0 or measured is None:
        raise PendulumFlowError("V3_AUDIT_INVALID")
    published, measured_hours, _complete, partial_count, unclassified = (
        int(part.replace(",", "")) for part in tally.groups()
    )
    segment = text[start:end]
    hours = frozenset(f"{date}/{hh}" for date, hh in _AUDIT_HOUR_RE.findall(segment))
    if len(hours) != partial_count or unclassified != 0:
        raise PendulumFlowError("V3_AUDIT_INVALID")
    moment = datetime.fromisoformat(measured.group(1)).astimezone(timezone.utc)
    return V3AuditSnapshot(
        partial_hours=hours,
        measured_on=moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        published_hours=published,
        measured_hours=measured_hours,
    )


def classify_product_coverage(manifest: V3Manifest, product: str, audit: V3AuditSnapshot) -> str:
    """Product-specific coverage class; the most conservative of every applicable signal.

    1. an hour named partial by the archive audit is PARTIAL;
    2. an hour not yet measured by the audit (on/after its measurement time) is unclassified;
    3. manifest witness accounting: >=2 contributing machines FULL; exactly one contributor is
       SINGLE-BY-DESIGN when only that machine was set up to record the hour, otherwise
       SINGLE-BY-DEFECT; zero contributors is unclassified;
    4. a source-declared per-product ``class`` can only make the result more conservative.
    """

    if manifest.hour in audit.partial_hours:
        return "PARTIAL"
    # The archive publishes consecutive hours from LIVE_START_HOUR and measures the oldest
    # ``measured_hours`` of them; any later hour is "audit pending", never assumed complete.
    index = int((hour_start(manifest.hour) - hour_start(LIVE_START_HOUR)).total_seconds() // 3600)
    if index < 0 or index >= audit.measured_hours:
        raise PendulumFlowError("V3_COVERAGE_UNCLASSIFIED")
    contributors = manifest.contributors(product)
    if len(contributors) >= 2:
        derived = "FULL"
    elif len(contributors) == 1:
        expected = manifest.witnesses_expected
        derived = "SINGLE-BY-DESIGN" if len(expected) == 1 and contributors[0] in expected else "SINGLE-BY-DEFECT"
    else:
        raise PendulumFlowError("V3_COVERAGE_UNCLASSIFIED")
    declared = manifest.declared_class(product)
    if declared is not None and _COVERAGE_RANK[declared] > _COVERAGE_RANK[derived]:
        return declared
    return derived


def coverage_quality(coverage_class: str) -> tuple[tuple[str, ...], str]:
    """Map a coverage class onto the common DQ flags and replay-fidelity ceiling."""

    if coverage_class in ADMISSIBLE_COVERAGE_CLASSES:
        return ("OK",), "FAITHFUL"
    if coverage_class in ("PARTIAL", "SINGLE-BY-DEFECT"):
        return ("PARTIALLY_OBSERVED",), "PARTIAL"
    raise PendulumFlowError("V3_COVERAGE_UNCLASSIFIED")


# ── Byte verification and Parquet targeting ───────────────────────────────────


def verify_product_bytes(product: V3Product, data: bytes) -> str:
    """Verify one complete product byte range against its manifest SHA-256."""

    if not isinstance(data, (bytes, bytearray)) or len(data) != product.byte_end - product.byte_start:
        raise PendulumFlowError("V3_PRODUCT_SHA256_MISMATCH")
    digest = hashlib.sha256(data).hexdigest()
    if digest != product.sha256:
        raise PendulumFlowError("V3_PRODUCT_SHA256_MISMATCH")
    return digest


def parse_parquet_tail(tail: bytes, file_bytes: int) -> tuple[int, int]:
    """Return ``(footer_start, footer_length)`` from the final 8 bytes of a Parquet file."""

    if not isinstance(tail, (bytes, bytearray)) or len(tail) != 8 or bytes(tail[4:]) != _PARQUET_MAGIC:
        raise PendulumFlowError("V3_PARQUET_TAIL_INVALID")
    length = struct.unpack("<I", bytes(tail[:4]))[0]
    if not (0 < length <= _MAX_FOOTER_BYTES) or length > file_bytes - 12:
        raise PendulumFlowError("V3_PARQUET_TAIL_INVALID")
    return file_bytes - 8 - length, length


PARQUET_SPECULATIVE_TAIL_BYTES = 64 * 1024  # PyArrow reads at least this much of the tail on open


def footer_fetch_range(file_bytes: int, footer_start: int) -> tuple[int, int]:
    """Byte range to retain for opening a Parquet file: the whole footer and at least the final
    64 KiB PyArrow reads speculatively (the 8-byte tail is retained separately)."""

    start = min(footer_start, max(0, file_bytes - PARQUET_SPECULATIVE_TAIL_BYTES))
    return start, file_bytes - 8


class RangeBackedFile(io.RawIOBase):
    """Read-only seekable file serving only byte ranges the caller already retained.

    It never fetches anything; a read touching an unretained byte fails closed with
    ``V3_RANGE_NOT_RETAINED``. This lets PyArrow parse a Parquet footer and read targeted
    column chunks from verified local range bytes.
    """

    def __init__(self, size: int, ranges: Sequence[tuple[int, bytes]]) -> None:
        super().__init__()
        self._size = size
        merged: list[tuple[int, bytearray]] = []
        for start, data in sorted(((s, bytes(d)) for s, d in ranges), key=lambda item: item[0]):
            if merged and start <= merged[-1][0] + len(merged[-1][1]):
                base, buffer = merged[-1]
                overlap = base + len(buffer) - start
                if overlap < len(data):
                    buffer.extend(data[overlap:])
            else:
                merged.append((start, bytearray(data)))
        self._ranges = [(start, bytes(buffer)) for start, buffer in merged]
        self._pos = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = 0) -> int:
        base = {0: 0, 1: self._pos, 2: self._size}.get(whence)
        if base is None or base + offset < 0:
            raise PendulumFlowError("V3_RANGE_NOT_RETAINED")
        self._pos = base + offset
        return self._pos

    def readinto(self, buffer) -> int:  # type: ignore[override]
        want = min(len(buffer), max(0, self._size - self._pos))
        if want == 0:
            return 0
        for start, data in self._ranges:
            if start <= self._pos and self._pos + want <= start + len(data):
                offset = self._pos - start
                buffer[:want] = data[offset : offset + want]
                self._pos += want
                return want
        raise PendulumFlowError("V3_RANGE_NOT_RETAINED")


def open_parquet(file_bytes: int, ranges: Sequence[tuple[int, bytes]]):
    """Open a PyArrow ParquetFile over retained ranges only (footer must be retained)."""

    import pyarrow.parquet as pq  # noqa: PLC0415  (base dependency, imported lazily)

    try:
        return pq.ParquetFile(RangeBackedFile(file_bytes, ranges), pre_buffer=False)
    except PendulumFlowError:
        raise
    except Exception:
        raise PendulumFlowError("V3_PARQUET_TAIL_INVALID") from None


def _chunk_bounds(column_meta) -> tuple[int, int]:
    start = column_meta.data_page_offset
    dictionary = column_meta.dictionary_page_offset
    if column_meta.has_dictionary_page and dictionary is not None and 0 < dictionary < start:
        start = dictionary
    return start, start + column_meta.total_compressed_size


def product_row_groups_for_markets(parquet_file, product: V3Product, condition_ids: Sequence[bytes]) -> tuple[int, ...]:
    """Row groups of one product whose ``market`` min/max statistics can hold a target id."""

    metadata = parquet_file.metadata
    if product.row_group_last >= metadata.num_row_groups:
        raise PendulumFlowError("V3_ROW_GROUPS_INVALID")
    names = [metadata.schema.column(i).path for i in range(metadata.num_columns)]
    try:
        market_index = names.index("market")
    except ValueError:
        raise PendulumFlowError("V3_ROW_GROUPS_INVALID") from None
    targets = sorted(set(condition_ids))
    selected: list[int] = []
    for group in range(product.row_group_first, product.row_group_last + 1):
        stats = metadata.row_group(group).column(market_index).statistics
        if stats is None or not stats.has_min_max:
            selected.append(group)  # cannot exclude safely; read it
            continue
        low, high = stats.min, stats.max
        if any(low <= target <= high for target in targets):
            selected.append(group)
    return tuple(selected)


def column_chunk_ranges(parquet_file, product: V3Product, group: int, columns: Sequence[str]) -> tuple[tuple[int, int], ...]:
    """Coalesced byte ranges of the named column chunks of one row group, bound-checked
    against the product's declared byte range and row-group span."""

    if not (product.row_group_first <= group <= product.row_group_last):
        raise PendulumFlowError("V3_ROW_GROUPS_INVALID")
    row_group = parquet_file.metadata.row_group(group)
    paths = [row_group.column(i).path_in_schema for i in range(row_group.num_columns)]
    spans: list[tuple[int, int]] = []
    for column in columns:
        matches = [i for i, path in enumerate(paths) if path == column or path.startswith(column + ".")]
        if not matches:
            raise PendulumFlowError("V3_COLUMN_CHUNK_OUT_OF_RANGE")
        for index in matches:
            start, end = _chunk_bounds(row_group.column(index))
            if not (product.byte_start <= start < end <= product.byte_end):
                raise PendulumFlowError("V3_COLUMN_CHUNK_OUT_OF_RANGE")
            spans.append((start, end))
    spans.sort()
    merged: list[list[int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return tuple((start, end) for start, end in merged)


# ── Row normalization ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class V3Event:
    family: str
    hour: str
    row_group: int
    condition_id: str
    asset_id: str | None
    market_id: str | None
    timestamp_received: str  # capture availability (microseconds, UTC)
    venue_timestamp: str  # exchange timestamp (milliseconds, UTC)
    fields: tuple[tuple[str, str | None], ...]

    def field(self, name: str) -> str | None:
        return dict(self.fields).get(name)

    def to_mapping(self) -> dict[str, object]:
        return {
            "family": self.family,
            "hour": self.hour,
            "row_group": self.row_group,
            "condition_id": self.condition_id,
            "asset_id": self.asset_id,
            "market_id": self.market_id,
            "timestamp_received": self.timestamp_received,
            "venue_timestamp": self.venue_timestamp,
            "fields": [list(pair) for pair in self.fields],
        }


def _utc_text(value: object, *, micro: bool) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise PendulumFlowError("V3_ROW_INVALID")
    utc = value.astimezone(timezone.utc)
    if micro:
        return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def normalize_condition_id(value: object) -> str:
    if isinstance(value, (bytes, bytearray)) and len(value) == 32:
        return "0x" + bytes(value).hex()
    if isinstance(value, str) and re.fullmatch(r"0x[0-9a-fA-F]{64}", value):
        return value.lower()
    raise PendulumFlowError("V3_ROW_INVALID")


def normalize_asset_id(value: object) -> str:
    if isinstance(value, (bytes, bytearray)):
        try:
            value = bytes(value).decode("ascii")
        except UnicodeDecodeError:
            raise PendulumFlowError("V3_ROW_INVALID") from None
    if isinstance(value, str) and _DIGITS_RE.fullmatch(value):
        return value
    raise PendulumFlowError("V3_ROW_INVALID")


def _decimal_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise PendulumFlowError("V3_ROW_INVALID")
        return format(value.normalize(), "f")  # canonical: no trailing zeros, no exponent
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    raise PendulumFlowError("V3_ROW_INVALID")


def _string(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise PendulumFlowError("V3_ROW_INVALID")


_FAMILY_FIELDS = {
    "best_bid_ask": ("best_bid", "best_ask", "spread"),
    "last_trade_price": ("price", "size", "side", "fee_rate_bps"),
    "tick_size_change": ("old_tick_size", "new_tick_size"),
    "new_market": ("question", "slug"),
    "market_resolved": ("winning_asset_id", "winning_outcome"),
}

READ_COLUMNS = {
    "best_bid_ask": ("timestamp_received", "timestamp", "market", "asset_id", "best_bid", "best_ask", "spread"),
    "last_trade_price": ("timestamp_received", "timestamp", "market", "asset_id", "price", "size", "side", "fee_rate_bps"),
    "tick_size_change": ("timestamp_received", "timestamp", "market", "asset_id", "old_tick_size", "new_tick_size"),
    "new_market": ("timestamp_received", "timestamp", "market", "id", "assets_ids", "outcomes", "question", "slug"),
    "market_resolved": ("timestamp_received", "timestamp", "market", "id", "assets_ids", "winning_asset_id", "winning_outcome"),
}


def normalize_row(family: str, hour: str, row_group: int, row: Mapping[str, object]) -> V3Event:
    """Normalize one decoded row of an event family (closed code on any malformed field)."""

    if family not in _FAMILY_FIELDS:
        raise PendulumFlowError("V3_ROW_INVALID")
    condition_id = normalize_condition_id(row.get("market"))
    received = _utc_text(row.get("timestamp_received"), micro=True)
    venue = _utc_text(row.get("timestamp"), micro=False)
    asset_id: str | None = None
    market_id: str | None = None
    fields: list[tuple[str, str | None]] = []
    if family in ("best_bid_ask", "last_trade_price", "tick_size_change"):
        asset_id = normalize_asset_id(row.get("asset_id"))
    if family in ("new_market", "market_resolved"):
        market_id = _string(row.get("id"))
        if market_id is None or not _DIGITS_RE.fullmatch(market_id):
            raise PendulumFlowError("V3_ROW_INVALID")
        assets = row.get("assets_ids")
        if type(assets) is not list or not assets:
            raise PendulumFlowError("V3_ROW_INVALID")
        fields.append(("assets_ids", ",".join(normalize_asset_id(a) for a in assets)))
        if family == "new_market":
            outcomes = row.get("outcomes")
            if type(outcomes) is not list or len(outcomes) != len(assets) or not all(isinstance(o, str) for o in outcomes):
                raise PendulumFlowError("V3_ROW_INVALID")
            fields.append(("outcomes", "\u001f".join(outcomes)))
    for name in _FAMILY_FIELDS[family]:
        value = row.get(name)
        if name == "winning_asset_id":
            fields.append((name, normalize_asset_id(value) if value is not None else None))
        elif name in ("question", "slug", "side", "winning_outcome"):
            fields.append((name, _string(value)))
        else:
            fields.append((name, _decimal_text(value)))
    return V3Event(
        family=family,
        hour=hour,
        row_group=row_group,
        condition_id=condition_id,
        asset_id=asset_id,
        market_id=market_id,
        timestamp_received=received,
        venue_timestamp=venue,
        fields=tuple(sorted(fields)),
    )


def event_sort_key(event: V3Event) -> tuple[object, ...]:
    """Deterministic observability order: capture receive time first, never ``sequence``."""

    return (
        event.timestamp_received,
        event.family,
        event.condition_id,
        event.asset_id or "",
        event.venue_timestamp,
        event.fields,
    )


def order_events(events: Sequence[V3Event]) -> tuple[V3Event, ...]:
    return tuple(sorted(events, key=event_sort_key))


def dedupe_events(events: Sequence[V3Event]) -> tuple[V3Event, ...]:
    """Collapse byte-identical witness copies of the same row (all fields and both clocks
    equal); distinct receive times are kept as distinct observations."""

    seen: set[tuple[object, ...]] = set()
    kept: list[V3Event] = []
    for event in order_events(events):
        key = (event.family, event.condition_id, event.asset_id, event.market_id,
               event.timestamp_received, event.venue_timestamp, event.fields)
        if key not in seen:
            seen.add(key)
            kept.append(event)
    return tuple(kept)
