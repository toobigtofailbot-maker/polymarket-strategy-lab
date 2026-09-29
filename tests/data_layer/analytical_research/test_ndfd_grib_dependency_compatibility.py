"""S10-NDFD-GRIB-01 optional NDFD GRIB2 decoder dependency compatibility proof.

This is a dependency compatibility proof, not a weather adapter. It decodes one committed
official NDFD CONUS PoP12 GRIB2 message (``tests/fixtures/ndfd_grib/ndfd_pop12_reference.grib2``)
with the exact optional ``ndfd-grib`` extra (``eccodes==2.48.0``; ``eccodeslib==2.48.0.26`` on
non-Windows) and compares it against a frozen oracle. It makes zero external requests.

Collection discipline: the optional decoder is only installed by the dedicated hosted
``ndfd-grib-compat`` jobs (ubuntu-24.04 / windows-2022, Python 3.12). Pin, fixture-identity,
structural fail-closed and boundary tests always run. Decoder-dependent tests are defined only
when ``eccodes`` is importable or when ``NDFD_GRIB_STRICT=1``; the dedicated jobs set strict mode,
so a missing or broken decoder fails there instead of being skipped. Environments without the
optional extra (the general compatibility matrix, local Python 3.14) collect no decoder test and
therefore report no skip.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import pathlib
import platform
import socket
import struct
import sys
import tomllib

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "fixtures" / "ndfd_grib" / "ndfd_pop12_reference.grib2"

NDFD_GRIB_STRICT = os.environ.get("NDFD_GRIB_STRICT") == "1"
DECODER_AVAILABLE = importlib.util.find_spec("eccodes") is not None
DECODER_TESTS_DEFINED = DECODER_AVAILABLE or NDFD_GRIB_STRICT

# Exact optional extra (S10-NDFD-GRIB-01 Section 3); pyproject must declare exactly these.
EXPECTED_NDFD_GRIB_EXTRA = [
    'eccodes==2.48.0; python_version == "3.12"',
    'eccodeslib==2.48.0.26; python_version == "3.12" and platform_system != "Windows"',
]
EXPECTED_ECCODES_VERSION = "2.48.0"
EXPECTED_ECCODESLIB_VERSION = "2.48.0.26"

# Unchanged project-wide facts.
EXPECTED_REQUIRES_PYTHON = ">=3.12,<3.15"
EXPECTED_BASE_DEPENDENCIES = [
    "pyarrow==25.0.1",
    "duckdb==1.5.5",
    "polars==1.44.1",
    "nautilus_trader==1.231.0",
    "polymarket-client==0.10.0",
    "websockets==15.0.1",
]
EXPECTED_OTHER_EXTRAS = {
    "test": ["pytest>=8.0"],
    "cockpit": ["fastapi==0.141.1", "uvicorn==0.52.4"],
}

# Frozen fixture identity. Official source: s3://noaa-ndfd-pds (NOAA Open Data Dissemination,
# anonymous), key wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031046, retrieved 2026-09-28 (UTC
# 2026-09-29T02:31:32Z), ETag/MD5 2ab91bd586b1b677c44d6365a193a522. The committed fixture is the
# first GRIB2 message of that object: byte offset 80, length 453433, inner WMO header
# "YDUB12 KWBN 031046".
SOURCE_OBJECT_KEY = "wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031046"
SOURCE_OBJECT_SIZE = 2660227
SOURCE_OBJECT_SHA256 = "50ab9671f38381bb4799d8b7bb92fe82ab2af734506ca86925650a347852f5d4"
FIXTURE_SOURCE_OFFSET = 80
FIXTURE_LENGTH = 453433
FIXTURE_SHA256 = "ecdac869039c2342f8a8ff8c57aa4fef602728e3257d0de7af5c091047c719ea"

# Frozen decode oracle (ecCodes 2.48.0; identical on every supported target).
EXPECTED_HEADER = {
    "edition": 2,
    "centre": 8,
    "discipline": 0,
    "parameterCategory": 1,
    "parameterNumber": 8,
    "gridDefinitionTemplateNumber": 30,
    "productDefinitionTemplateNumber": 9,
    "dataRepresentationTemplateNumber": 3,
    "orderOfSpatialDifferencing": 2,
    "bitsPerValue": 8,
    "numberOfDataPoints": 2953665,
    "Nx": 2145,
    "Ny": 1377,
    "dataDate": 20260903,
    "dataTime": 1100,
    "significanceOfReferenceTime": 1,
    "forecastTime": 0,
    "indicatorOfUnitOfTimeRange": 1,
    "typeOfStatisticalProcessing": 1,
    "lengthOfTimeRange": 12,
    "indicatorOfUnitForTimeRange": 1,
    "yearOfEndOfOverallTimeInterval": 2026,
    "monthOfEndOfOverallTimeInterval": 9,
    "dayOfEndOfOverallTimeInterval": 3,
    "hourOfEndOfOverallTimeInterval": 12,
    "minuteOfEndOfOverallTimeInterval": 0,
    "validityDate": 20260903,
    "validityTime": 1200,
    "probabilityType": 1,
    "scaledValueOfUpperLimit": 254,
    "scaleFactorOfUpperLimit": 3,
    "numberOfMissing": 1454641,
    "totalLength": 453433,
}
EXPECTED_MISSING_VALUE = 9999.0
EXPECTED_VALID_COUNT = 1499024
EXPECTED_VALID_SUM = 33754239
EXPECTED_VALUES_SHA256 = "35820fcfc50abd547ab1cfa7ed720e31957f2ac00fa0a31888b926915a6b878a"
# (index, latitude, longitude) of grid points; coordinates are compared within 1e-6 degrees.
EXPECTED_COORDINATES = (
    (0, 20.191999, 238.445999),
    (2144, 20.331772952268977, 290.7918404717691),
    (1846511, 40.77584402255292, 286.02916800705515),
    (2953664, 50.10554671914976, 299.114442270779),
)
# Fixed compatibility point: nearest grid point to 40.7789N 73.9692W (Central Park, KNYC).
ORACLE_QUERY = (40.7789, -73.9692)
ORACLE_INDEX = 1846511
ORACLE_VALUE = 99.0
EXPECTED_FINGERPRINT = "0b5e478b2fff21519adbe12a993f0f3106f449343640f0fb521e4e8f792653ec"

REJECTION_CODES = frozenset(
    {"EMPTY", "BAD_MAGIC", "BAD_EDITION", "LENGTH_MISMATCH", "MISSING_END_SECTION", "DECODER_REJECTED"}
)


class NdfdFixtureRejected(Exception):
    """Closed, no-echo rejection: the message is exactly one code from REJECTION_CODES."""

    def __init__(self, code: str) -> None:
        assert code in REJECTION_CODES
        super().__init__(code)
        self.code = code


def _validate_grib2_structure(data: bytes) -> None:
    """Fail closed before decoding: exactly one complete GRIB edition-2 message.

    ecCodes' message API is lenient (it decodes a message missing its ``7777`` end section and
    returns a handle for bad magic), so the structural check is mandatory.
    """
    if not data:
        raise NdfdFixtureRejected("EMPTY")
    if len(data) < 16 or data[:4] != b"GRIB":
        raise NdfdFixtureRejected("BAD_MAGIC")
    if data[7] != 2:
        raise NdfdFixtureRejected("BAD_EDITION")
    if struct.unpack(">Q", data[8:16])[0] != len(data):
        raise NdfdFixtureRejected("LENGTH_MISMATCH")
    if data[-4:] != b"7777":
        raise NdfdFixtureRejected("MISSING_END_SECTION")


def test_pyproject_declares_exact_ndfd_grib_optional_pins() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["optional-dependencies"]["ndfd-grib"] == EXPECTED_NDFD_GRIB_EXTRA
    assert set(project["optional-dependencies"]) == {"test", "cockpit", "ndfd-grib"}
    assert not (ROOT / "uv.lock").exists() and not (ROOT / "poetry.lock").exists()
    assert not (ROOT / "requirements.txt").exists() and not (ROOT / "pylock.toml").exists()


def test_base_dependencies_python_range_and_other_extras_unchanged() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["requires-python"] == EXPECTED_REQUIRES_PYTHON
    assert project["dependencies"] == EXPECTED_BASE_DEPENDENCIES
    for name, pins in EXPECTED_OTHER_EXTRAS.items():
        assert project["optional-dependencies"][name] == pins, name


def test_fixture_bytes_match_frozen_identity() -> None:
    data = FIXTURE.read_bytes()
    assert len(data) == FIXTURE_LENGTH
    assert hashlib.sha256(data).hexdigest() == FIXTURE_SHA256
    _validate_grib2_structure(data)
    # Exactly one self-contained message: the section-0 total length covers every byte.
    assert struct.unpack(">Q", data[8:16])[0] == FIXTURE_LENGTH


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
def test_malformed_fixture_bytes_fail_closed_structurally(mutation: str, code: str) -> None:
    data = FIXTURE.read_bytes()
    mutated = {
        "empty": b"",
        "truncate_header": data[:12],
        "bad_magic": b"XXXX" + data[4:],
        "bad_edition": data[:7] + b"\x01" + data[8:],
        "truncate_data": data[:200000],
        "truncate_end_section": data[:-4],
        "bad_length_field": data[:8] + struct.pack(">Q", len(data) + 1) + data[16:],
        "bad_end_section": data[:-4] + b"7770",
    }[mutation]
    with pytest.raises(NdfdFixtureRejected) as excinfo:
        _validate_grib2_structure(mutated)
    assert excinfo.value.code == code
    # No echo: the diagnostic is exactly the closed code (no bytes, path or value).
    assert str(excinfo.value) == code
    assert str(FIXTURE) not in str(excinfo.value)


def test_production_adapter_structural_codes_match_oracle() -> None:
    """S10-QUAL-DATA-01: the production adapter enforces the same closed structural codes."""
    from src.data_layer.analytical_research import nws_ndfd_history

    data = FIXTURE.read_bytes()
    nws_ndfd_history.validate_grib2_structure(data)
    assert set(nws_ndfd_history.STRUCTURE_CODES) | {"DECODER_REJECTED"} == REJECTION_CODES
    for mutated in (b"", data[:12], b"XXXX" + data[4:], data[:7] + b"" + data[8:], data[:-4],
                    data[:-4] + b"7770"):
        with pytest.raises(NdfdFixtureRejected) as oracle:
            _validate_grib2_structure(mutated)
        with pytest.raises(nws_ndfd_history.NdfdError) as production:
            nws_ndfd_history.validate_grib2_structure(mutated)
        assert production.value.code == oracle.value.code
    header = nws_ndfd_history.parse_pop12_header(data)
    assert (header.reference_time, header.valid_end) == ("2026-09-03T11:00:00Z", "2026-09-03T12:00:00Z")


def test_decoder_presence_matches_capability_mode() -> None:
    if NDFD_GRIB_STRICT:
        # Dedicated hosted ndfd-grib-compat job: decoder must be present and exact.
        assert DECODER_AVAILABLE
        assert sys.version_info[:2] == (3, 12)
    if DECODER_AVAILABLE:
        assert importlib.metadata.version("eccodes") == EXPECTED_ECCODES_VERSION
        if platform.system() != "Windows":
            assert importlib.metadata.version("eccodeslib") == EXPECTED_ECCODESLIB_VERSION
    else:
        # Optional capability absent: nothing decoder-dependent is collected in this environment.
        assert not NDFD_GRIB_STRICT
        assert DECODER_TESTS_DEFINED is False


_FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "subprocess", "urllib", "http", "requests", "httpx", "aiohttp", "ftplib", "boto3",
        "botocore", "cfgrib", "xarray", "grib2io", "pygrib", "ecmwflibs", "polymarket",
        "src", "tools",
    }
)
# S10-QUAL-DATA-01: the only permitted repository import is the offline production NDFD adapter.
_PRODUCTION_ADAPTER = "src.data_layer.analytical_research.nws_ndfd_history"


def test_module_imports_no_network_subprocess_decoder_or_trading_surface() -> None:
    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names if alias.name != _PRODUCTION_ADAPTER)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "src.data_layer.analytical_research" and [a.name for a in node.names] == ["nws_ndfd_history"]:
                continue
            roots.add(node.module.split(".")[0])
    assert not roots & _FORBIDDEN_IMPORT_ROOTS, sorted(roots & _FORBIDDEN_IMPORT_ROOTS)
    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    for needle in ("os.environ[", "getenv(", "os.system(", "Popen(", "pip install", "setup.py"):
        assert needle not in source.replace('"' + needle + '"', ""), needle


if DECODER_TESTS_DEFINED:
    import numpy as np

    def _decode(data: bytes) -> dict[str, object]:
        """Structurally validate then decode one message; any decoder error fails closed."""
        import eccodes
        from gribapi.errors import GribInternalError

        _validate_grib2_structure(data)
        try:
            handle = eccodes.codes_new_from_message(data)
        except GribInternalError:
            raise NdfdFixtureRejected("DECODER_REJECTED") from None
        try:
            header = {key: int(eccodes.codes_get_long(handle, key)) for key in EXPECTED_HEADER}
            values = np.asarray(eccodes.codes_get_values(handle), dtype="<f8")
            latitudes = np.asarray(eccodes.codes_get_array(handle, "latitudes"), dtype="<f8")
            longitudes = np.asarray(eccodes.codes_get_array(handle, "longitudes"), dtype="<f8")
            missing_value = float(eccodes.codes_get_double(handle, "missingValue"))
            nearest = eccodes.codes_grib_find_nearest(handle, *ORACLE_QUERY)[0]
        except GribInternalError:
            raise NdfdFixtureRejected("DECODER_REJECTED") from None
        finally:
            eccodes.codes_release(handle)
        return {
            "header": header,
            "values": values,
            "latitudes": latitudes,
            "longitudes": longitudes,
            "missing_value": missing_value,
            "nearest": nearest,
        }

    def _fingerprint(decoded: dict[str, object]) -> str:
        """Canonical bounded decode fingerprint: integer header oracle plus exact value digest.

        Values are integer percentages (or the 9999 missing sentinel) so their float64
        little-endian bytes are platform-exact; projected coordinates are excluded from the
        digest and compared with a tolerance instead.
        """
        values = decoded["values"]
        valid = values[values != decoded["missing_value"]]
        payload = {
            "header": decoded["header"],
            "missing_value": decoded["missing_value"],
            "valid_count": int(valid.size),
            "valid_sum": int(valid.sum()),
            "values_sha256": hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest(),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @pytest.fixture(scope="module")
    def decoded() -> dict[str, object]:
        return _decode(FIXTURE.read_bytes())

    def test_eccodes_binding_and_library_versions_exact() -> None:
        import eccodes

        assert sys.version_info[:2] == (3, 12)
        assert importlib.metadata.version("eccodes") == EXPECTED_ECCODES_VERSION
        assert eccodes.codes_get_api_version() == EXPECTED_ECCODES_VERSION
        if platform.system() == "Windows":
            # The cp312 win_amd64 eccodes wheel bundles the library; no eccodeslib is installed.
            with pytest.raises(importlib.metadata.PackageNotFoundError):
                importlib.metadata.version("eccodeslib")
        else:
            assert importlib.metadata.version("eccodeslib") == EXPECTED_ECCODESLIB_VERSION

    def test_eccodes_selfcheck_succeeds(capsys: pytest.CaptureFixture[str]) -> None:
        from eccodes.__main__ import selfcheck

        selfcheck()
        output = capsys.readouterr().out
        assert f"Found: ecCodes v{EXPECTED_ECCODES_VERSION}." in output
        assert "Your system is ready." in output

    def test_fixture_decodes_single_ndfd_pop12_message(decoded: dict[str, object]) -> None:
        header = decoded["header"]
        assert header["edition"] == 2 and header["totalLength"] == FIXTURE_LENGTH
        assert (header["discipline"], header["parameterCategory"], header["parameterNumber"]) == (0, 1, 8)
        # PoP12: probability (type 1, above upper limit) that 12 h accumulation exceeds 0.254 mm.
        assert header["probabilityType"] == 1
        assert header["scaledValueOfUpperLimit"] / 10 ** header["scaleFactorOfUpperLimit"] == 0.254
        assert decoded["values"].shape == (EXPECTED_HEADER["numberOfDataPoints"],)

    def test_reference_and_valid_time_semantics(decoded: dict[str, object]) -> None:
        header = decoded["header"]
        # Reference time 2026-09-03T11:00Z, significance 1 (start of forecast).
        assert (header["dataDate"], header["dataTime"], header["significanceOfReferenceTime"]) == (
            20260903, 1100, 1)
        # Explicit section-4 end of the overall 12 h accumulation interval: 2026-09-03T12:00Z.
        end = tuple(header[f"{part}OfEndOfOverallTimeInterval"] for part in (
            "year", "month", "day", "hour", "minute"))
        assert end == (2026, 9, 3, 12, 0)
        assert (header["validityDate"], header["validityTime"]) == (20260903, 1200)
        assert (header["typeOfStatisticalProcessing"], header["lengthOfTimeRange"]) == (1, 12)
        assert (header["indicatorOfUnitForTimeRange"], header["forecastTime"]) == (1, 0)

    def test_grid_product_data_representation_templates(decoded: dict[str, object]) -> None:
        header = decoded["header"]
        assert header["gridDefinitionTemplateNumber"] == 30  # Lambert conformal
        assert header["productDefinitionTemplateNumber"] == 9  # probability, time interval
        assert header["dataRepresentationTemplateNumber"] == 3  # complex packing + spatial diff
        assert header["orderOfSpatialDifferencing"] == 2
        assert header == EXPECTED_HEADER

    def test_grid_coordinates_decode(decoded: dict[str, object]) -> None:
        latitudes, longitudes = decoded["latitudes"], decoded["longitudes"]
        assert latitudes.shape == longitudes.shape == (EXPECTED_HEADER["Nx"] * EXPECTED_HEADER["Ny"],)
        for index, latitude, longitude in EXPECTED_COORDINATES:
            assert abs(float(latitudes[index]) - latitude) < 1e-6, index
            assert abs(float(longitudes[index]) - longitude) < 1e-6, index

    def test_fixed_point_value_oracle(decoded: dict[str, object]) -> None:
        values = decoded["values"]
        assert decoded["missing_value"] == EXPECTED_MISSING_VALUE
        assert int(decoded["nearest"]["index"]) == ORACLE_INDEX
        assert float(decoded["nearest"]["value"]) == ORACLE_VALUE
        assert float(values[ORACLE_INDEX]) == ORACLE_VALUE
        assert (ORACLE_INDEX % EXPECTED_HEADER["Nx"], ORACLE_INDEX // EXPECTED_HEADER["Nx"]) == (1811, 860)
        valid = values[values != EXPECTED_MISSING_VALUE]
        assert int(valid.size) == EXPECTED_VALID_COUNT
        assert int((values == EXPECTED_MISSING_VALUE).sum()) == EXPECTED_HEADER["numberOfMissing"]
        assert float(valid.min()) == 0.0 and float(valid.max()) == 100.0
        assert bool(np.all(valid == np.round(valid)))

    def test_decode_fingerprint_is_deterministic(decoded: dict[str, object]) -> None:
        values_sha = hashlib.sha256(np.ascontiguousarray(decoded["values"]).tobytes()).hexdigest()
        assert values_sha == EXPECTED_VALUES_SHA256
        first = _fingerprint(decoded)
        second = _fingerprint(_decode(FIXTURE.read_bytes()))
        assert first == second == EXPECTED_FINGERPRINT
        valid = decoded["values"][decoded["values"] != EXPECTED_MISSING_VALUE]
        assert int(valid.sum()) == EXPECTED_VALID_SUM

    @pytest.mark.parametrize("cut", [4, 16, 100, 1000, 200000])
    def test_truncated_fixture_fails_closed_in_decoder(cut: int) -> None:
        import eccodes
        from gribapi.errors import GribInternalError

        data = FIXTURE.read_bytes()[:cut]
        # Through the validated decode path: structural rejection, closed code only.
        with pytest.raises(NdfdFixtureRejected) as excinfo:
            _decode(data)
        assert str(excinfo.value) in REJECTION_CODES
        # Directly in ecCodes (structural guard bypassed): the library itself refuses.
        with pytest.raises(GribInternalError):
            handle = eccodes.codes_new_from_message(data)
            try:
                eccodes.codes_get_values(handle)
            finally:
                eccodes.codes_release(handle)

    def test_decode_makes_no_network_connection(monkeypatch: pytest.MonkeyPatch) -> None:
        def _refuse(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("network access attempted during offline decode")

        monkeypatch.setattr(socket.socket, "connect", _refuse)
        monkeypatch.setattr(socket.socket, "connect_ex", _refuse)
        monkeypatch.setattr(socket, "create_connection", _refuse)
        monkeypatch.setattr(socket, "getaddrinfo", _refuse)
        decoded_offline = _decode(FIXTURE.read_bytes())
        assert _fingerprint(decoded_offline) == EXPECTED_FINGERPRINT

    def test_production_adapter_decodes_committed_fixture() -> None:
        """S10-QUAL-DATA-01: the PRODUCTION adapter decodes the committed official fixture to the
        frozen oracle (structural guard, lazy exact-version ecCodes, PoP12 semantics, nearest grid)."""
        from src.data_layer.analytical_research import nws_ndfd_history

        station = nws_ndfd_history.StationMetadata("KNYC", ORACLE_QUERY[0], ORACLE_QUERY[1], "America/New_York", "Central Park")
        first = nws_ndfd_history.decode_pop12_message(FIXTURE.read_bytes(), [station])
        second = nws_ndfd_history.decode_pop12_message(FIXTURE.read_bytes(), [station])
        assert first == second
        assert first.header.reference_time == "2026-09-03T11:00:00Z"
        assert (first.header.valid_start, first.header.valid_end) == ("2026-09-03T00:00:00Z", "2026-09-03T12:00:00Z")
        decoder_header = dict(first.decoder_header)
        for key in ("discipline", "parameterCategory", "parameterNumber", "productDefinitionTemplateNumber",
                    "lengthOfTimeRange", "Nx", "Ny", "numberOfDataPoints", "totalLength"):
            assert decoder_header[key] == EXPECTED_HEADER[key], key
        value = first.station_values[0]
        assert value.grid_index == ORACLE_INDEX and value.pop12_percent == int(ORACLE_VALUE)
        assert value.distance_km < 3.0
        with pytest.raises(nws_ndfd_history.NdfdError) as excinfo:
            nws_ndfd_history.decode_pop12_message(FIXTURE.read_bytes()[:-4], [station])
        assert excinfo.value.code == "LENGTH_MISMATCH"
