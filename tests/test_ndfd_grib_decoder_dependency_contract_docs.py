"""S10-NDFD-GRIB-01 contract-doc consistency: dependency, fixture, authority and matrix."""

from __future__ import annotations

import hashlib
import json
import pathlib
import tomllib


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "ndfd_grib_decoder_dependency_contract.md"
STATUS = ROOT / "docs" / "status_entries" / "S10-NDFD-GRIB-01.md"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
SPEC = ROOT / "docs" / "wp_specs" / "S10-NDFD-GRIB-01" / "wp_spec.json"
FIXTURE = ROOT / "tests" / "fixtures" / "ndfd_grib" / "ndfd_pop12_reference.grib2"

PINS = [
    'eccodes==2.48.0; python_version == "3.12"',
    'eccodeslib==2.48.0.26; python_version == "3.12" and platform_system != "Windows"',
]
FIXTURE_SHA256 = "ecdac869039c2342f8a8ff8c57aa4fef602728e3257d0de7af5c091047c719ea"
SOURCE_SHA256 = "50ab9671f38381bb4799d8b7bb92fe82ab2af734506ca86925650a347852f5d4"
FINGERPRINT = "0b5e478b2fff21519adbe12a993f0f3106f449343640f0fb521e4e8f792653ec"


def _flat(path: pathlib.Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_contract_states_exact_pins_matching_pyproject() -> None:
    contract = CONTRACT.read_text(encoding="utf-8")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["optional-dependencies"]["ndfd-grib"] == PINS
    for pin in PINS:
        assert f"'{pin}'" in contract, pin
    flat = _flat(CONTRACT)
    assert '`requires-python = ">=3.12,<3.15"`' in flat
    assert "No lock or requirements file is added." in flat
    assert "No source build and no vendored or copied ecCodes source" in flat
    for rejected in ("cfgrib", "xarray", "grib2io", "NCEPLIBS-g2c", "ecmwflibs", "wgrib2", "conda"):
        assert rejected in flat, rejected


def test_contract_fixture_identity_matches_committed_bytes() -> None:
    flat = _flat(CONTRACT)
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA256
    for text in (
        FIXTURE_SHA256, SOURCE_SHA256, FINGERPRINT, "`noaa-ndfd-pds`",
        "`wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031046`", "byte offset 80, length 453433",
        "`YDUB12 KWBN 031046`", "2026-09-28", "3.30 Lambert conformal", "5.3 complex packing",
        "product template 4.9", "2026-09-03T11:00Z", "2026-09-03T12:00Z", "index 1846511",
        "value 99",
    ):
        assert text in flat, text
    assert "never canonical market or weather research evidence" in flat


def test_contract_matrix_and_authority_are_bounded() -> None:
    flat = _flat(CONTRACT)
    for text in (
        "| ubuntu-24.04 / CPython 3.12 | `NDFD_GRIB_SUPPORTED`",
        "| windows-2022 / CPython 3.12 | `NDFD_GRIB_SUPPORTED`",
        "| Python 3.13, Python 3.14, macOS, ARM | `NDFD_GRIB_NOT_CLAIMED` |",
        "Global project Python support remains 3.12–3.14",
        "No `src/` change, no product/runtime network, no weather adapter.",
        "Gate C: NOT AUTHORIZED", "Merge: NOT AUTHORIZED",
        "S10-QUAL-DATA-01 remains unimplemented by this WP",
        "No QualificationCandidate exists yet",
    ):
        assert text in flat, text
    for claim in ("Gate C: AUTHORIZED", "Merge: AUTHORIZED", "NDFD_GRIB_SUPPORTED` (macOS"):
        assert claim not in flat, claim


def test_workflow_declares_dedicated_strict_ndfd_jobs() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    ndfd = workflow[workflow.index("  ndfd-grib-compat:"): workflow.index("  cockpit-frontend:")]
    assert "os: [ubuntu-24.04, windows-2022]" in ndfd
    assert 'python-version: "3.12"' in ndfd
    assert 'NDFD_GRIB_STRICT: "1"' in ndfd
    assert ndfd.count("--only-binary=eccodes,eccodeslib,eckitlib") == 2
    assert "optional-dependencies']['ndfd-grib']" in ndfd
    assert "python -m pip check" in ndfd
    assert "python -m eccodes selfcheck" in ndfd
    assert "test_ndfd_grib_dependency_compatibility.py" in ndfd
    assert '[0-9]+ skipped' in ndfd
    assert "  ndfd-grib-dependency-audit:" in ndfd and "python -m pip_audit" in ndfd
    for forbidden in ("secrets.", "schedule:", "curl ", "wget ", "noaa-ndfd-pds"):
        assert forbidden not in ndfd, forbidden
    # The existing general matrix and dependency audit are preserved.
    assert 'python: ["3.12", "3.14"]' in workflow
    assert "  dependency-audit:" in workflow and "  compatibility:" in workflow


def test_status_fragment_and_spec_are_consistent() -> None:
    flat = _flat(STATUS)
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert spec["identity"]["wp_id"] == "S10-NDFD-GRIB-01"
    assert len(spec["scope"]["required_changed_files"]) == 19
    assert not any(path.startswith("src/") for path in spec["scope"]["required_changed_files"])
    for key in ("dependencies", "workflow_files", "docs", "tests"):
        assert spec["authority"][key] is True, key
    for key in ("network", "credentials", "source_runtime", "paper", "execution", "live", "strategy"):
        assert spec["authority"][key] is False, key
    assert spec["successor_boundary"]["next_wp"] == "S10-QUAL-DATA-01"
    for text in (
        FINGERPRINT, FIXTURE_SHA256, "Exact changed-file scope: 19", "Merge authorized: NO",
        "Gate C: NOT AUTHORIZED", "S10-QUAL-DATA-01: NOT IMPLEMENTED by this WP",
    ):
        assert text in flat, text
