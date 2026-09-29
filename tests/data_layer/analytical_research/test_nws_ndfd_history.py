"""S10-QUAL-DATA-01 NDFD PoP12 offline adapter tests (R009-R011, R013).

Hermetic and decoder-free: structural checks, deterministic multi-message slicing, header
pre-parse, the four clocks, vintage windows and station binding run against the committed
official S10-NDFD-GRIB-01 fixture without ecCodes. The production decode path itself is proven
by the strict ndfd-grib jobs in test_ndfd_grib_dependency_compatibility.py.
"""

from __future__ import annotations

import ast
import struct
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.data_layer.analytical_research import nws_ndfd_history as ndfd

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "fixtures" / "ndfd_grib" / "ndfd_pop12_reference.grib2"
MODULE = ROOT / "src" / "data_layer" / "analytical_research" / "nws_ndfd_history.py"
KEY = "wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031046"


@pytest.fixture(scope="module")
def message() -> bytes:
    return FIXTURE.read_bytes()


def _wmo(message: bytes, *messages: bytes, gap: bytes = b"\r\r\nYDUB12 KWBN 031046\r\r\n") -> bytes:
    body = b"\x01\r\r\n001" + gap + message
    for extra in messages:
        body += b"\r\r\n\x03\x01\r\r\n002" + gap + extra
    return body + b"\r\r\n\x03"


def _section4_offset(message: bytes) -> int:
    position = 16
    while True:
        length = struct.unpack(">I", message[position:position + 4])[0]
        if message[position + 4] == 4:
            return position
        position += length


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("empty", "EMPTY"),
        ("truncate_header", "BAD_MAGIC"),
        ("bad_magic", "BAD_MAGIC"),
        ("bad_edition", "BAD_EDITION"),
        ("truncate_data", "LENGTH_MISMATCH"),
        ("truncate_end_section", "LENGTH_MISMATCH"),
        ("bad_length_field", "LENGTH_MISMATCH"),
        ("bad_end_section", "MISSING_END_SECTION"),
    ],
)
def test_grib_structure_rejects_malformed(message: bytes, mutation: str, code: str) -> None:
    ndfd.validate_grib2_structure(message)
    mutated = {
        "empty": b"",
        "truncate_header": message[:12],
        "bad_magic": b"XXXX" + message[4:],
        "bad_edition": message[:7] + b"\x01" + message[8:],
        "truncate_data": message[:200000],
        "truncate_end_section": message[:-4],
        "bad_length_field": message[:8] + struct.pack(">Q", len(message) + 1) + message[16:],
        "bad_end_section": message[:-4] + b"7770",
    }[mutation]
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.validate_grib2_structure(mutated)
    assert excinfo.value.code == code
    assert str(excinfo.value) == code
    assert str(FIXTURE) not in str(excinfo.value)
    assert set(ndfd.STRUCTURE_CODES) <= set(ndfd.NDFD_ERROR_CODES)


def test_multi_message_slicing_deterministic(message: bytes) -> None:
    second = message[:-4] + b"7777"  # identical valid message
    obj = _wmo(message, second)
    first_run = ndfd.scan_messages(obj)
    second_run = ndfd.scan_messages(bytes(obj))
    assert first_run == second_run
    assert [s.index for s in first_run] == [0, 1]
    assert all(s.length == len(message) for s in first_run)
    assert first_run[0].offset < first_run[1].offset
    assert ndfd.message_bytes(obj, first_run[1]) == second
    # Ambiguous or truncated structure fails closed.
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.scan_messages(_wmo(message, gap=b"x" * 400))
    assert excinfo.value.code == "BOUNDARY_AMBIGUOUS"
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.scan_messages(_wmo(message)[:-400])
    assert excinfo.value.code == "TRUNCATED"
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.scan_messages(b"\x01\r\r\nno grib here\r\r\n\x03")
    assert excinfo.value.code == "NO_MESSAGES"
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.scan_messages(_wmo(message) + b"z" * 600)
    assert excinfo.value.code == "BOUNDARY_AMBIGUOUS"
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.scan_messages(b"")
    assert excinfo.value.code == "EMPTY"


def test_pop12_header_semantics(message: bytes) -> None:
    header = ndfd.parse_pop12_header(message)
    assert header.parameter == (0, 1, 8) and header.template == 9
    assert header.probability_type == 1
    assert header.upper_limit_scaled_value / 10 ** header.upper_limit_scale_factor == pytest.approx(0.254)
    assert header.length_of_time_range_hours == 12
    offset = _section4_offset(message)
    wrong_parameter = bytearray(message)
    wrong_parameter[offset + 10] = 9  # parameterNumber
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.parse_pop12_header(bytes(wrong_parameter))
    assert excinfo.value.code == "NOT_POP12"
    wrong_length = bytearray(message)
    wrong_length[offset + 62:offset + 66] = struct.pack(">I", 6)
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.parse_pop12_header(bytes(wrong_length))
    assert excinfo.value.code == "INTERVAL_INVALID"


def test_pop12_four_clocks_distinct(message: bytes) -> None:
    listing = (
        '<?xml version="1.0" encoding="UTF-8"?><ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        "<Name>noaa-ndfd-pds</Name><Prefix>wmo/pop12/2026/09/03/</Prefix><KeyCount>3</KeyCount><IsTruncated>false</IsTruncated>"
        f"<Contents><Key>{KEY}</Key><LastModified>2026-09-03T10:51:56.000Z</LastModified><Size>2660227</Size></Contents>"
        "<Contents><Key>wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031216</Key><LastModified>2026-09-03T12:18:01.000Z</LastModified><Size>2060482</Size></Contents>"
        "<Contents><Key>wmo/pop12/2026/09/03/YDAZ98_KWBN_202609031046</Key><LastModified>2026-09-03T10:50:00.000Z</LastModified><Size>1000</Size></Contents>"
        "</ListBucketResult>"
    ).encode("utf-8")
    objects = ndfd.parse_s3_listing(listing, "wmo/pop12/2026/09/03/")
    assert [o.key for o in objects] == [KEY, "wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031216"]  # CONUS only
    item = objects[0]
    header = ndfd.parse_pop12_header(message)
    clocks = {
        "bulletin": item.bulletin_time,
        "public_availability": item.public_available_time,
        "reference": header.reference_time,
        "valid_end": header.valid_end,
    }
    assert clocks == {
        "bulletin": "2026-09-03T10:46:00Z",
        "public_availability": "2026-09-03T10:51:56Z",
        "reference": "2026-09-03T11:00:00Z",
        "valid_end": "2026-09-03T12:00:00Z",
    }
    assert len(set(clocks.values())) == 4
    assert header.valid_start == "2026-09-03T00:00:00Z"
    assert item.availability_basis == "S3_OBJECT_LAST_MODIFIED_CONSERVATIVE_BOUND"
    # Availability, not the bulletin/reference/valid time, decides eligibility.
    checkpoint = datetime(2026, 9, 3, 12, 10, tzinfo=timezone.utc)
    assert ndfd.select_vintage(objects, checkpoint, timedelta(hours=48)) == item
    early = datetime(2026, 9, 3, 10, 50, tzinfo=timezone.utc)  # after bulletin, before LastModified
    assert ndfd.select_vintage(objects, early, timedelta(hours=48)) is None
    late = datetime(2026, 9, 3, 12, 20, tzinfo=timezone.utc)
    assert ndfd.select_vintage(objects, late, timedelta(hours=48)).key.endswith("1216")
    # The 48 h window is closed on both ends.
    assert ndfd.select_vintage(objects, datetime(2026, 9, 5, 10, 51, 56, tzinfo=timezone.utc), timedelta(hours=48)).key.endswith("1216")
    assert ndfd.select_vintage(objects, datetime(2026, 9, 5, 12, 18, 2, tzinfo=timezone.utc), timedelta(hours=48)) is None
    # A LastModified earlier than the bulletin time is impossible and rejected.
    impossible = listing.replace(b"2026-09-03T10:51:56.000Z", b"2026-09-03T10:40:00.000Z")
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.parse_s3_listing(impossible, "wmo/pop12/2026/09/03/")
    assert excinfo.value.code == "AVAILABILITY_INVALID"
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.parse_s3_listing(listing.replace(b"<IsTruncated>false", b"<IsTruncated>true"), "wmo/pop12/2026/09/03/")
    assert excinfo.value.code == "LISTING_INVALID"
    with pytest.raises(ndfd.NdfdError):
        ndfd.parse_s3_listing(listing, "wmo/pop12/2026/09/04/")
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.parse_object_key("wmo/pop12/2026/09/03/YDUZ98_KWBN_202609041046")
    assert excinfo.value.code == "OBJECT_NAME_INVALID"


def test_intervals_overlapping_climate_day(message: bytes) -> None:
    header = ndfd.parse_pop12_header(message)
    start, end = ndfd.climate_day_window(date(2026, 9, 3), -300)
    assert (start, end) == (datetime(2026, 9, 3, 5, tzinfo=timezone.utc), datetime(2026, 9, 4, 5, tzinfo=timezone.utc))
    assert ndfd.intervals_overlapping([header], start, end) == (0,)
    other_start, other_end = ndfd.climate_day_window(date(2026, 9, 4), -300)
    assert ndfd.intervals_overlapping([header], other_start, other_end) == ()


def _station_doc(station: str = "KNYC", tz: str = "America/New_York") -> dict[str, object]:
    return {"geometry": {"type": "Point", "coordinates": [-73.96667, 40.78333]},
            "properties": {"stationIdentifier": station, "timeZone": tz, "name": "New York City, Central Park"}}


def test_station_binding_and_offset_fail_closed() -> None:
    station = ndfd.parse_nws_station(_station_doc(), "KNYC")
    assert (station.latitude, station.longitude, station.time_zone) == (40.78333, -73.96667, "America/New_York")
    assert ndfd.standard_utc_offset_minutes("America/New_York", date(2026, 8, 19)) == -300  # EST, not EDT
    assert ndfd.standard_utc_offset_minutes("America/Phoenix", date(2026, 8, 19)) == -420
    assert ndfd.standard_utc_offset_minutes("America/Los_Angeles", date(2026, 8, 19)) == -480
    nearest = {"index": 1846511, "lat": 40.77584402255292, "lon": 286.02916800705515, "value": 99.0}
    first = ndfd.bind_station_to_grid(station, nearest)
    second = ndfd.bind_station_to_grid(station, dict(nearest))
    assert first == second
    assert first.grid_index == 1846511 and first.distance_km < 3.0
    assert first.grid_longitude == pytest.approx(-73.970832, abs=1e-5)
    for document, code in (
        (_station_doc("KLGA"), "STATION_ID_MISMATCH"),
        ({"properties": {}}, "STATION_METADATA_INVALID"),
        ({**_station_doc(), "geometry": {"type": "Point", "coordinates": [-73.9]}}, "STATION_METADATA_INVALID"),
        ({**_station_doc(), "properties": {"stationIdentifier": "KNYC", "name": "x"}}, "STATION_METADATA_INVALID"),
    ):
        with pytest.raises(ndfd.NdfdError) as excinfo:
            ndfd.parse_nws_station(document, "KNYC")
        assert excinfo.value.code == code
    for zone in ("Not/AZone", "", "../../etc"):
        with pytest.raises(ndfd.NdfdError) as excinfo:
            ndfd.standard_utc_offset_minutes(zone, date(2026, 8, 19))
        assert excinfo.value.code == "STATION_OFFSET_UNDERIVABLE"
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.bind_station_to_grid(station, {**nearest, "lat": 41.5})  # > 10 km away
    assert excinfo.value.code == "GRID_BINDING_INVALID"
    with pytest.raises(ndfd.NdfdError):
        ndfd.bind_station_to_grid(station, {"index": -1, "lat": 40.7, "lon": -73.9})
    with pytest.raises(ndfd.NdfdError):
        ndfd.parse_nws_station(_station_doc(), "knyc")


def test_decoder_is_lazy_and_fails_closed_without_eccodes(monkeypatch: pytest.MonkeyPatch, message: bytes) -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    top_level = {alias.name.split(".")[0] for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
    top_level |= {node.module.split(".")[0] for node in tree.body if isinstance(node, ast.ImportFrom) and node.module}
    assert "eccodes" not in top_level and "gribapi" not in top_level
    all_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            all_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            all_roots.add(node.module.split(".")[0])
    assert not all_roots & {"urllib", "http", "requests", "httpx", "socket", "subprocess", "boto3", "cfgrib", "xarray", "pygrib"}
    monkeypatch.setitem(sys.modules, "eccodes", None)
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.require_decoder(strict_python312=False)
    assert excinfo.value.code in ("DECODER_UNAVAILABLE", "DECODER_VERSION_MISMATCH")
    with pytest.raises(ndfd.NdfdError):
        ndfd.decode_pop12_message(message, [], strict_python312=False)
    # Structural rejection happens before any decoder import is attempted.
    with pytest.raises(ndfd.NdfdError) as excinfo:
        ndfd.decode_pop12_message(message[:-4], [])
    assert excinfo.value.code == "LENGTH_MISMATCH"
