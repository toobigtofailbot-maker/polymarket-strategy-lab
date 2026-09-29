"""S10-QUAL-DATA-01 official historical NDFD PoP12 offline adapter.

Decodes NOAA NDFD CONUS PoP12 GRIB2 objects (``noaa-ndfd-pds`` ``wmo/pop12/.../YDUZ98_KWBN_*``)
from bytes the S10-QUAL-DATA-01 operator already acquired, and binds rule stations to the NDFD
grid. It performs NO network access and never writes files.

Structural guard (mandatory before ecCodes sees any bytes): non-empty, ``GRIB`` magic,
edition 2, section-0 declared total length equal to the exact slice length, final ``7777``.
ecCodes' message API is lenient (it decodes a message missing its end section and returns a
handle for bad magic), so the guard is not optional.

Multi-message objects are scanned deterministically: find the ``GRIB`` boundary within a
bounded WMO header gap, read the edition-2 total length, slice exactly one declared message,
validate it, continue after it. Ambiguous or truncated structure is a closed error.

Four clocks are preserved separately and never substituted for one another:

1. WMO bulletin/product time (from the WMO file name);
2. public availability time (the object's public ``LastModified`` — a conservative bound);
3. GRIB reference time (section 1);
4. forecast valid interval (section 4 end of overall interval minus the statistical length).

ecCodes is imported lazily only on actual decode paths, so this module imports in base
Python 3.14 environments without the optional ``ndfd-grib`` extra. Errors are closed codes and
never echo bytes, paths or values.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import math
import re
import struct
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Mapping, Sequence

SOURCE_CLASS = "OFFICIAL_HISTORICAL_EXPORT"
PROVIDER_ID = "noaa-ndfd"
DATASET_NAME = "noaa-ndfd-pds-wmo-pop12"
BUCKET_HOST = "noaa-ndfd-pds.s3.amazonaws.com"
OBJECT_PREFIX = "wmo/pop12/"
PRODUCT_FILE_PREFIX = "YDUZ98_KWBN_"  # CONUS PoP12, NDFD days 1-3
AVAILABILITY_BASIS = "S3_OBJECT_LAST_MODIFIED_CONSERVATIVE_BOUND"

EXPECTED_ECCODES_VERSION = "2.48.0"
EXPECTED_ECCODESLIB_VERSION = "2.48.0.26"

# Closed structural codes (names shared with the S10-NDFD-GRIB-01 compatibility oracle).
STRUCTURE_CODES = ("EMPTY", "BAD_MAGIC", "BAD_EDITION", "LENGTH_MISMATCH", "MISSING_END_SECTION")
NDFD_ERROR_CODES = STRUCTURE_CODES + (
    "TRUNCATED",
    "BOUNDARY_AMBIGUOUS",
    "NO_MESSAGES",
    "HEADER_TRUNCATED",
    "NOT_POP12",
    "INTERVAL_INVALID",
    "DECODER_UNAVAILABLE",
    "DECODER_VERSION_MISMATCH",
    "DECODER_REJECTED",
    "HEADER_DECODE_MISMATCH",
    "OBJECT_NAME_INVALID",
    "LISTING_INVALID",
    "AVAILABILITY_INVALID",
    "STATION_METADATA_INVALID",
    "STATION_ID_MISMATCH",
    "STATION_OFFSET_UNDERIVABLE",
    "GRID_BINDING_INVALID",
)

MAX_HEADER_GAP_BYTES = 256  # WMO abbreviated heading / SOH / ETX framing between messages
MAX_MESSAGES_PER_OBJECT = 64
MAX_GRID_BINDING_KM = 10.0  # sanity bound: NDFD CONUS grid spacing is ~2.5 km
POP12_UPPER_LIMIT_MM = 0.254
MISSING_VALUE = 9999.0

_OBJECT_KEY_RE = re.compile(r"^wmo/pop12/(\d{4})/(\d{2})/(\d{2})/YDUZ98_KWBN_(\d{12})$")
_STATION_RE = re.compile(r"^K[A-Z0-9]{3}$")


class NdfdError(ValueError):
    """Closed, no-echo rejection. ``str(error)`` is exactly the closed code."""

    def __init__(self, code: str) -> None:
        if code not in NDFD_ERROR_CODES:
            code = "DECODER_REJECTED"
        super().__init__(code)
        self.code = code


def _utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Structure and slicing ─────────────────────────────────────────────────────


def validate_grib2_structure(data: bytes) -> None:
    """Fail closed unless ``data`` is exactly one complete GRIB edition-2 message."""

    if not data:
        raise NdfdError("EMPTY")
    if len(data) < 16 or bytes(data[:4]) != b"GRIB":
        raise NdfdError("BAD_MAGIC")
    if data[7] != 2:
        raise NdfdError("BAD_EDITION")
    if struct.unpack(">Q", bytes(data[8:16]))[0] != len(data):
        raise NdfdError("LENGTH_MISMATCH")
    if bytes(data[-4:]) != b"7777":
        raise NdfdError("MISSING_END_SECTION")


@dataclass(frozen=True)
class MessageSlice:
    index: int
    offset: int
    length: int
    sha256: str


def scan_messages(data: bytes) -> tuple[MessageSlice, ...]:
    """Deterministically slice a multi-message WMO object into declared GRIB2 messages."""

    if not data:
        raise NdfdError("EMPTY")
    slices: list[MessageSlice] = []
    position = 0
    while True:
        found = data.find(b"GRIB", position)
        if found < 0:
            if not slices:
                raise NdfdError("NO_MESSAGES")
            if len(data) - position > MAX_HEADER_GAP_BYTES:
                raise NdfdError("BOUNDARY_AMBIGUOUS")
            break
        if found - position > MAX_HEADER_GAP_BYTES:
            raise NdfdError("BOUNDARY_AMBIGUOUS")
        if len(data) - found < 16:
            raise NdfdError("TRUNCATED")
        if data[found + 7] != 2:
            raise NdfdError("BAD_EDITION")
        length = struct.unpack(">Q", bytes(data[found + 8 : found + 16]))[0]
        if length < 16 or found + length > len(data):
            raise NdfdError("TRUNCATED")
        message = bytes(data[found : found + length])
        validate_grib2_structure(message)
        slices.append(MessageSlice(len(slices), found, length, hashlib.sha256(message).hexdigest()))
        if len(slices) > MAX_MESSAGES_PER_OBJECT:
            raise NdfdError("BOUNDARY_AMBIGUOUS")
        position = found + length
    return tuple(slices)


def message_bytes(data: bytes, piece: MessageSlice) -> bytes:
    message = bytes(data[piece.offset : piece.offset + piece.length])
    validate_grib2_structure(message)
    if hashlib.sha256(message).hexdigest() != piece.sha256:
        raise NdfdError("LENGTH_MISMATCH")
    return message


# ── Header pre-parse (no decoder) ─────────────────────────────────────────────


@dataclass(frozen=True)
class Pop12Header:
    reference_time: str
    significance_of_reference_time: int
    forecast_time: int
    valid_start: str
    valid_end: str
    length_of_time_range_hours: int
    parameter: tuple[int, int, int]  # discipline, category, number
    template: int
    probability_type: int
    upper_limit_scale_factor: int
    upper_limit_scaled_value: int

    def to_mapping(self) -> dict[str, object]:
        return {
            "reference_time": self.reference_time,
            "significance_of_reference_time": self.significance_of_reference_time,
            "forecast_time": self.forecast_time,
            "valid_start": self.valid_start,
            "valid_end": self.valid_end,
            "length_of_time_range_hours": self.length_of_time_range_hours,
            "parameter": list(self.parameter),
            "template": self.template,
            "probability_type": self.probability_type,
            "upper_limit_scale_factor": self.upper_limit_scale_factor,
            "upper_limit_scaled_value": self.upper_limit_scaled_value,
        }


def _sections(message: bytes) -> dict[int, bytes]:
    found: dict[int, bytes] = {}
    position = 16
    while position + 5 <= len(message):
        if bytes(message[position : position + 4]) == b"7777":
            break
        length = struct.unpack(">I", bytes(message[position : position + 4]))[0]
        number = message[position + 4]
        if length < 5 or position + length > len(message):
            raise NdfdError("HEADER_TRUNCATED")
        found.setdefault(number, bytes(message[position : position + length]))
        if number == 4:
            break
        position += length
    if 1 not in found or 4 not in found:
        raise NdfdError("HEADER_TRUNCATED")
    return found


def parse_pop12_header(message: bytes) -> Pop12Header:
    """Parse section 0/1/4 of one PoP12 message without the decoder and validate PoP12
    semantics (discipline 0, category 1, number 8, template 4.9, probability above 0.254 mm,
    12-hour accumulation interval)."""

    if len(message) < 16 or bytes(message[:4]) != b"GRIB" or message[7] != 2:
        raise NdfdError("BAD_MAGIC")
    discipline = message[6]
    sections = _sections(message)
    s1, s4 = sections[1], sections[4]
    if len(s1) < 21 or len(s4) < 66:
        raise NdfdError("HEADER_TRUNCATED")
    significance = s1[11]
    try:
        reference = datetime(struct.unpack(">H", s1[12:14])[0], s1[14], s1[15], s1[16], s1[17], s1[18], tzinfo=timezone.utc)
    except ValueError:
        raise NdfdError("INTERVAL_INVALID") from None
    template = struct.unpack(">H", s4[7:9])[0]
    category, number = s4[9], s4[10]
    time_unit = s4[17]
    forecast_time = struct.unpack(">I", s4[18:22])[0]
    probability_type = s4[36]
    upper_scale = s4[42]
    upper_value = struct.unpack(">I", s4[43:47])[0]
    try:
        end = datetime(struct.unpack(">H", s4[47:49])[0], s4[49], s4[50], s4[51], s4[52], s4[53], tzinfo=timezone.utc)
    except ValueError:
        raise NdfdError("INTERVAL_INVALID") from None
    ranges = s4[54]
    statistical = s4[59]
    range_unit = s4[61]
    length = struct.unpack(">I", s4[62:66])[0]
    if (discipline, category, number, template) != (0, 1, 8, 9):
        raise NdfdError("NOT_POP12")
    if probability_type != 1 or not math.isclose(upper_value / 10 ** upper_scale, POP12_UPPER_LIMIT_MM):
        raise NdfdError("NOT_POP12")
    if ranges != 1 or statistical != 1 or range_unit != 1 or time_unit != 1 or length != 12:
        raise NdfdError("INTERVAL_INVALID")
    start = end - timedelta(hours=length)
    return Pop12Header(
        reference_time=_utc(reference),
        significance_of_reference_time=significance,
        forecast_time=forecast_time,
        valid_start=_utc(start),
        valid_end=_utc(end),
        length_of_time_range_hours=length,
        parameter=(discipline, category, number),
        template=template,
        probability_type=probability_type,
        upper_limit_scale_factor=upper_scale,
        upper_limit_scaled_value=upper_value,
    )


# ── Object identity, listing and the four clocks ──────────────────────────────


@dataclass(frozen=True)
class NdfdObject:
    key: str
    bulletin_time: str  # clock 1: WMO bulletin/product time from the file name
    public_available_time: str  # clock 2: conservative public availability bound
    availability_basis: str
    byte_length: int

    def to_mapping(self) -> dict[str, object]:
        return {
            "key": self.key,
            "bulletin_time": self.bulletin_time,
            "public_available_time": self.public_available_time,
            "availability_basis": self.availability_basis,
            "byte_length": self.byte_length,
        }


def parse_object_key(key: str) -> datetime:
    match = _OBJECT_KEY_RE.fullmatch(key) if isinstance(key, str) else None
    if match is None:
        raise NdfdError("OBJECT_NAME_INVALID")
    year, month, day, stamp = match.groups()
    try:
        bulletin = datetime.strptime(stamp, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
    except ValueError:
        raise NdfdError("OBJECT_NAME_INVALID") from None
    if (bulletin.year, bulletin.month, bulletin.day) != (int(year), int(month), int(day)):
        raise NdfdError("OBJECT_NAME_INVALID")
    return bulletin


def day_prefix(day: date) -> str:
    return f"{OBJECT_PREFIX}{day:%Y/%m/%d}/"


def parse_s3_listing(raw: bytes, prefix: str) -> tuple[NdfdObject, ...]:
    """Parse one S3 ListObjectsV2 page for ``prefix`` and keep only CONUS PoP12 objects."""

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise NdfdError("LISTING_INVALID") from None
    namespace = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    if root.tag != f"{namespace}ListBucketResult":
        raise NdfdError("LISTING_INVALID")
    if (root.findtext(f"{namespace}Prefix") or "") != prefix:
        raise NdfdError("LISTING_INVALID")
    if (root.findtext(f"{namespace}IsTruncated") or "").lower() != "false":
        raise NdfdError("LISTING_INVALID")
    objects: list[NdfdObject] = []
    for item in root.findall(f"{namespace}Contents"):
        key = item.findtext(f"{namespace}Key") or ""
        if not key.startswith(prefix + PRODUCT_FILE_PREFIX):
            continue
        bulletin = parse_object_key(key)
        modified_text = item.findtext(f"{namespace}LastModified") or ""
        size_text = item.findtext(f"{namespace}Size") or ""
        try:
            modified = datetime.fromisoformat(modified_text.replace("Z", "+00:00"))
            size = int(size_text)
        except ValueError:
            raise NdfdError("LISTING_INVALID") from None
        if modified.tzinfo is None or size <= 0:
            raise NdfdError("LISTING_INVALID")
        if modified < bulletin:
            raise NdfdError("AVAILABILITY_INVALID")
        objects.append(NdfdObject(key, _utc(bulletin), _utc(modified), AVAILABILITY_BASIS, size))
    return tuple(sorted(objects, key=lambda o: o.key))


def select_vintage(objects: Sequence[NdfdObject], checkpoint: datetime, lookback: timedelta) -> NdfdObject | None:
    """Latest object whose public availability lies in ``[checkpoint - lookback, checkpoint]``.

    Availability is the conservative ``LastModified`` bound — never the bulletin, reference
    or valid time.
    """

    low = checkpoint - lookback
    eligible = [
        item for item in objects
        if low <= datetime.fromisoformat(item.public_available_time.replace("Z", "+00:00")) <= checkpoint
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda item: (item.public_available_time, item.key))


def intervals_overlapping(headers: Sequence[Pop12Header], window_start: datetime, window_end: datetime) -> tuple[int, ...]:
    """Indexes of PoP12 periods overlapping ``[window_start, window_end)`` (the climate day)."""

    selected = []
    for index, header in enumerate(headers):
        start = datetime.fromisoformat(header.valid_start.replace("Z", "+00:00"))
        end = datetime.fromisoformat(header.valid_end.replace("Z", "+00:00"))
        if start < window_end and end > window_start:
            selected.append(index)
    return tuple(selected)


# ── Station binding ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StationMetadata:
    station_id: str
    latitude: float
    longitude: float
    time_zone: str
    name: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "station_id": self.station_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "time_zone": self.time_zone,
            "name": self.name,
        }


def parse_nws_station(document: object, expected_station: str) -> StationMetadata:
    """Validate an ``api.weather.gov/stations/{id}`` document (spatial reference only)."""

    if not isinstance(expected_station, str) or not _STATION_RE.fullmatch(expected_station):
        raise NdfdError("STATION_METADATA_INVALID")
    if not isinstance(document, Mapping):
        raise NdfdError("STATION_METADATA_INVALID")
    properties = document.get("properties")
    geometry = document.get("geometry")
    if not isinstance(properties, Mapping) or not isinstance(geometry, Mapping):
        raise NdfdError("STATION_METADATA_INVALID")
    if properties.get("stationIdentifier") != expected_station:
        raise NdfdError("STATION_ID_MISMATCH")
    coordinates = geometry.get("coordinates")
    if geometry.get("type") != "Point" or type(coordinates) is not list or len(coordinates) != 2:
        raise NdfdError("STATION_METADATA_INVALID")
    longitude, latitude = coordinates
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (latitude, longitude)):
        raise NdfdError("STATION_METADATA_INVALID")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise NdfdError("STATION_METADATA_INVALID")
    time_zone = properties.get("timeZone")
    name = properties.get("name")
    if not isinstance(time_zone, str) or not time_zone or not isinstance(name, str):
        raise NdfdError("STATION_METADATA_INVALID")
    return StationMetadata(expected_station, float(latitude), float(longitude), time_zone, name)


def standard_utc_offset_minutes(time_zone: str, target_day: date) -> int:
    """Explicit standard (non-DST) UTC offset of ``time_zone`` using stdlib ``zoneinfo`` only.

    The offset must be identical at the target date and at mid-January and mid-July of the
    same year; otherwise it is not an unambiguous standard offset and the sample is excluded.
    """

    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # noqa: PLC0415
    except ImportError:
        raise NdfdError("STATION_OFFSET_UNDERIVABLE") from None
    try:
        zone = ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        raise NdfdError("STATION_OFFSET_UNDERIVABLE") from None
    offsets = set()
    for probe in (target_day, date(target_day.year, 1, 15), date(target_day.year, 7, 15)):
        local = datetime(probe.year, probe.month, probe.day, 12, tzinfo=zone)
        utcoffset, dst = local.utcoffset(), local.dst()
        if utcoffset is None or dst is None:
            raise NdfdError("STATION_OFFSET_UNDERIVABLE")
        offsets.add(int((utcoffset - dst).total_seconds() // 60))
    if len(offsets) != 1:
        raise NdfdError("STATION_OFFSET_UNDERIVABLE")
    offset = offsets.pop()
    if offset % 15 != 0 or not (-14 * 60 <= offset <= 14 * 60):
        raise NdfdError("STATION_OFFSET_UNDERIVABLE")
    return offset


def climate_day_window(target_day: date, standard_offset_minutes: int) -> tuple[datetime, datetime]:
    """UTC ``[start, end)`` of the local-standard-time climate day (midnight to midnight LST)."""

    start = datetime(target_day.year, target_day.month, target_day.day, tzinfo=timezone.utc) - timedelta(
        minutes=standard_offset_minutes
    )
    return start, start + timedelta(hours=24)


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(((lon2 - lon1 + 180.0) % 360.0) - 180.0)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1.0, math.sqrt(a)))


@dataclass(frozen=True)
class GridBinding:
    station_id: str
    grid_index: int
    grid_latitude: float
    grid_longitude: float
    distance_km: float

    def to_mapping(self) -> dict[str, object]:
        return {
            "station_id": self.station_id,
            "grid_index": self.grid_index,
            "grid_latitude": round(self.grid_latitude, 6),
            "grid_longitude": round(self.grid_longitude, 6),
            "distance_km": round(self.distance_km, 3),
        }


def bind_station_to_grid(station: StationMetadata, nearest: Mapping[str, object]) -> GridBinding:
    """Deterministic binding from an ecCodes nearest-grid result (index, lat, lon)."""

    try:
        index = int(nearest["index"])  # type: ignore[arg-type]
        latitude = float(nearest["lat"])  # type: ignore[arg-type]
        longitude = float(nearest["lon"])  # type: ignore[arg-type]
    except (KeyError, TypeError, ValueError):
        raise NdfdError("GRID_BINDING_INVALID") from None
    if index < 0 or not math.isfinite(latitude) or not math.isfinite(longitude):
        raise NdfdError("GRID_BINDING_INVALID")
    longitude = ((longitude + 180.0) % 360.0) - 180.0
    distance = great_circle_km(station.latitude, station.longitude, latitude, longitude)
    if distance > MAX_GRID_BINDING_KM:
        raise NdfdError("GRID_BINDING_INVALID")
    return GridBinding(station.station_id, index, latitude, longitude, distance)


# ── Decoder (lazy ecCodes) ────────────────────────────────────────────────────


_DECODE_KEYS = (
    "edition", "discipline", "parameterCategory", "parameterNumber", "productDefinitionTemplateNumber",
    "probabilityType", "scaledValueOfUpperLimit", "scaleFactorOfUpperLimit", "typeOfStatisticalProcessing",
    "lengthOfTimeRange", "indicatorOfUnitForTimeRange", "dataDate", "dataTime",
    "yearOfEndOfOverallTimeInterval", "monthOfEndOfOverallTimeInterval", "dayOfEndOfOverallTimeInterval",
    "hourOfEndOfOverallTimeInterval", "minuteOfEndOfOverallTimeInterval", "gridDefinitionTemplateNumber",
    "Nx", "Ny", "numberOfDataPoints", "totalLength",
)


def require_decoder(strict_python312: bool = True):
    """Import ecCodes lazily and require the merged S10-NDFD-GRIB-01 versions."""

    if strict_python312 and sys.version_info[:2] != (3, 12):
        raise NdfdError("DECODER_VERSION_MISMATCH")
    try:
        import eccodes  # noqa: PLC0415  (optional ndfd-grib extra; lazy by contract)
    except Exception:
        raise NdfdError("DECODER_UNAVAILABLE") from None
    try:
        version = importlib.metadata.version("eccodes")
    except importlib.metadata.PackageNotFoundError:
        raise NdfdError("DECODER_UNAVAILABLE") from None
    if version != EXPECTED_ECCODES_VERSION or eccodes.codes_get_api_version() != EXPECTED_ECCODES_VERSION:
        raise NdfdError("DECODER_VERSION_MISMATCH")
    if sys.platform != "win32":
        try:
            if importlib.metadata.version("eccodeslib") != EXPECTED_ECCODESLIB_VERSION:
                raise NdfdError("DECODER_VERSION_MISMATCH")
        except importlib.metadata.PackageNotFoundError:
            raise NdfdError("DECODER_VERSION_MISMATCH") from None
    return eccodes


@dataclass(frozen=True)
class StationValue:
    station_id: str
    grid_index: int
    grid_latitude: float
    grid_longitude: float
    distance_km: float
    pop12_percent: int | None  # None when the grid point carries the missing sentinel

    def to_mapping(self) -> dict[str, object]:
        return {
            "station_id": self.station_id,
            "grid_index": self.grid_index,
            "grid_latitude": round(self.grid_latitude, 6),
            "grid_longitude": round(self.grid_longitude, 6),
            "distance_km": round(self.distance_km, 3),
            "pop12_percent": self.pop12_percent,
        }


@dataclass(frozen=True)
class DecodedPop12:
    header: Pop12Header
    decoder_header: tuple[tuple[str, int], ...]
    station_values: tuple[StationValue, ...]


def decode_pop12_message(
    message: bytes,
    stations: Sequence[StationMetadata],
    *,
    strict_python312: bool = True,
) -> DecodedPop12:
    """Structurally validate, pre-parse, then decode one PoP12 message with ecCodes and read
    the nearest grid point for every station. The decoder header must equal the pre-parse."""

    validate_grib2_structure(message)
    header = parse_pop12_header(message)
    eccodes = require_decoder(strict_python312)
    try:
        from gribapi.errors import GribInternalError  # noqa: PLC0415
    except Exception:
        raise NdfdError("DECODER_UNAVAILABLE") from None
    try:
        handle = eccodes.codes_new_from_message(bytes(message))
    except GribInternalError:
        raise NdfdError("DECODER_REJECTED") from None
    try:
        decoded = {key: int(eccodes.codes_get_long(handle, key)) for key in _DECODE_KEYS}
        missing = float(eccodes.codes_get_double(handle, "missingValue"))
        values: list[StationValue] = []
        for station in stations:
            nearest = eccodes.codes_grib_find_nearest(handle, station.latitude, station.longitude)[0]
            binding = bind_station_to_grid(station, nearest)
            raw = float(nearest["value"])
            if raw == missing:
                percent = None
            elif raw != round(raw) or not (0 <= raw <= 100):
                raise NdfdError("DECODER_REJECTED")
            else:
                percent = int(raw)
            values.append(StationValue(station.station_id, binding.grid_index, binding.grid_latitude,
                                       binding.grid_longitude, binding.distance_km, percent))
    except GribInternalError:
        raise NdfdError("DECODER_REJECTED") from None
    finally:
        eccodes.codes_release(handle)
    end = datetime(decoded["yearOfEndOfOverallTimeInterval"], decoded["monthOfEndOfOverallTimeInterval"],
                   decoded["dayOfEndOfOverallTimeInterval"], decoded["hourOfEndOfOverallTimeInterval"],
                   decoded["minuteOfEndOfOverallTimeInterval"], tzinfo=timezone.utc)
    data_date, data_time = decoded["dataDate"], decoded["dataTime"]
    reference = datetime(data_date // 10000, data_date // 100 % 100, data_date % 100,
                         data_time // 100, data_time % 100, tzinfo=timezone.utc)
    if (
        decoded["edition"] != 2
        or (decoded["discipline"], decoded["parameterCategory"], decoded["parameterNumber"]) != header.parameter
        or decoded["productDefinitionTemplateNumber"] != header.template
        or decoded["lengthOfTimeRange"] != header.length_of_time_range_hours
        or _utc(end) != header.valid_end
        or _utc(reference) != header.reference_time
        or decoded["totalLength"] != len(message)
    ):
        raise NdfdError("HEADER_DECODE_MISMATCH")
    return DecodedPop12(header, tuple(sorted(decoded.items())), tuple(values))
