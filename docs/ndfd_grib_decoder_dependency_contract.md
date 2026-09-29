# S10-NDFD-GRIB-01 — NDFD GRIB2 Decoder Dependency Contract

## Status and authority

- WP: `S10-NDFD-GRIB-01` — NDFD GRIB2 Decoder Dependency Enablement
- Governance track: RUNTIME; risk level 3; exact 19-path scope (Side14 same-WP amendment)
- Capability: optional offline NDFD GRIB2 decoding only (`S10_NDFD_GRIB_DECODER_READY`)
- Product impact: NONE. No `src/` change, no product/runtime network, no weather adapter.
- Canonical evidence: NONE. The committed fixture is a compatibility oracle only and is never
  canonical market or weather research evidence.
- Credentials / scheduler / Hermes / strategy / paper / execution / live: NONE
- Gate C: NOT AUTHORIZED; capital/orders: USD 0 / 0
- Merge: NOT AUTHORIZED by the executor

This contract resolves only the decoder blocker recorded by the S10-QUAL-DATA-01 source probe
(`SOURCE_COMPATIBILITY_BLOCKED:NDFD_DEPENDENCY_REQUIRED`): raw historical NDFD GRIB2 was
reachable but the repository had no decoder for GRIB2 template 5.3 complex packing with spatial
differencing.

## Exact optional dependency

`pyproject.toml` gains exactly one optional extra:

```toml
ndfd-grib = [
  'eccodes==2.48.0; python_version == "3.12"',
  'eccodeslib==2.48.0.26; python_version == "3.12" and platform_system != "Windows"',
]
```

- `eccodes==2.48.0` is the ECMWF Python interface (Apache-2.0). The CPython 3.12 `win_amd64`
  wheel bundles the ecCodes 2.48.0 library, so Windows installs no `eccodeslib`.
- `eccodeslib==2.48.0.26` is the ECMWF ecCodes 2.48.0 binary-library wheel for non-Windows
  targets; it pulls `eckitlib==2.1.1.26` as a transitive binary dependency. Transitive runtime
  dependencies of the binding are `numpy`, `attrs`, `cffi` (with `pycparser`) and `findlibs`.
- The family is installed from binary wheels only (`--only-binary=eccodes,eccodeslib,eckitlib`).
  No source build and no vendored or copied ecCodes source exists in this repository.
- Unchanged: `requires-python = ">=3.12,<3.15"`, the six base direct pins, and the `test` and
  `cockpit` extras. No lock or requirements file is added.
- Not adopted: cfgrib, xarray, grib2io, NCEPLIBS-g2c, ecmwflibs, degrib, wgrib2, conda, any
  custom GRIB decoder, any runtime extension download.

## Supported decoder matrix

| Target | Status |
|---|---|
| ubuntu-24.04 / CPython 3.12 | `NDFD_GRIB_SUPPORTED` (hosted `ndfd-grib-compat` job) |
| windows-2022 / CPython 3.12 | `NDFD_GRIB_SUPPORTED` (hosted `ndfd-grib-compat` job) |
| Python 3.13, Python 3.14, macOS, ARM | `NDFD_GRIB_NOT_CLAIMED` |

"Not claimed" applies only to this optional research capability. Global project Python support
remains 3.12–3.14 and the general 4-way compatibility matrix is unchanged.

## Fixed compatibility fixture

`tests/fixtures/ndfd_grib/ndfd_pop12_reference.grib2`

| Field | Frozen value |
|---|---|
| Official source | NOAA open data bucket `noaa-ndfd-pds` (anonymous; https://registry.opendata.aws/noaa-ndfd/) |
| Object key | `wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031046` |
| Retrieval date | 2026-09-28 (one anonymous GET at 2026-09-29T02:31:32Z) |
| Object size / ETag (MD5) | 2660227 bytes / `2ab91bd586b1b677c44d6365a193a522` |
| Object SHA-256 | `50ab9671f38381bb4799d8b7bb92fe82ab2af734506ca86925650a347852f5d4` |
| Object structure | outer WMO bulletin `YDUZ98 KWBN 031046`; six GRIB2 messages (PoP12 periods) |
| Fixture extraction | first GRIB2 message: byte offset 80, length 453433 |
| Inner WMO header | `YDUB12 KWBN 031046` (issuance 2026-09-03T10:46Z) |
| Fixture SHA-256 | `ecdac869039c2342f8a8ff8c57aa4fef602728e3257d0de7af5c091047c719ea` |

The object is the exact sample identified by the prior S10-QUAL-DATA-01 probe. Only the first
self-contained message is committed; the full raw object is not.

## Frozen decode oracle (ecCodes 2.48.0)

| Field | Value |
|---|---|
| GRIB edition | 2; centre 8 (US NWS) |
| Parameter | discipline 0, category 1, number 8; product template 4.9 probability type 1 (above upper limit 0.254 mm = scaled 254 / factor 3) — NDFD PoP12 |
| Grid definition template | 3.30 Lambert conformal; Nx 2145, Ny 1377; 2953665 points |
| Data representation template | 5.3 complex packing with spatial differencing (order 2), 8 bits per value |
| Reference time | 2026-09-03T11:00Z (`dataDate` 20260903, `dataTime` 1100, significance 1) |
| Statistical interval | accumulation (type 1), length 12 h, `forecastTime` 0 h |
| End of overall time interval | 2026-09-03T12:00Z (`validityDate` 20260903, `validityTime` 1200) |
| Missing | `missingValue` 9999; 1454641 missing points; 1499024 valid points (integers 0–100, sum 33754239) |
| Fixed point oracle | nearest grid point to 40.7789N 73.9692W (KNYC) = index 1846511 (i 1811, j 860), 40.775844N 286.029168E, value 99 |
| Values SHA-256 | `35820fcfc50abd547ab1cfa7ed720e31957f2ac00fa0a31888b926915a6b878a` (float64 little-endian) |
| Canonical decode fingerprint | `0b5e478b2fff21519adbe12a993f0f3106f449343640f0fb521e4e8f792653ec` |

The canonical fingerprint is SHA-256 of sorted-key compact JSON over the integer header oracle,
the missing value, the valid count/sum and the values SHA-256. Values are integers (or the
missing sentinel) so they are platform-exact. Projected latitudes/longitudes are excluded from the
fingerprint and compared within 1e-6 degrees because floating projection arithmetic may differ in
the last unit of precision between platforms.

Decoder semantics the successor must respect:

- NDFD's explicit section-4 end-of-overall-time-interval (2026-09-03T12:00Z) is not equal to
  reference time + `forecastTime` + `lengthOfTimeRange`; ecCodes derives `validityDate` /
  `validityTime` from the explicit end fields while `stepRange` reports `0-12`. The explicit end
  fields and `lengthOfTimeRange` are authoritative for the PoP12 period.
- `codes_new_from_message` is lenient: it still decodes a message whose `7777` end section is
  missing and returns a handle for bytes without the `GRIB` magic. Any consumer must validate
  the GRIB2 structure (magic, edition 2, section-0 total length equal to the byte count,
  trailing `7777`) before decoding. Truncation inside the header or data sections is refused by
  ecCodes itself.

## Test and CI contract

- Focused test: `tests/data_layer/analytical_research/test_ndfd_grib_dependency_compatibility.py`
  (committed fixture only; zero external requests; no subprocess decoder; closed no-echo
  rejection codes `EMPTY`, `BAD_MAGIC`, `BAD_EDITION`, `LENGTH_MISMATCH`, `MISSING_END_SECTION`,
  `DECODER_REJECTED`).
- Contract-doc test: `tests/test_ndfd_grib_decoder_dependency_contract_docs.py`.
- Collection discipline: pin, fixture-identity, structural fail-closed and boundary tests run
  everywhere. Decoder-dependent tests are defined only when ecCodes is importable or when
  `NDFD_GRIB_STRICT=1`. The dedicated hosted jobs set strict mode, so a missing decoder fails;
  environments without the optional extra collect no decoder test and report no skip.
- Hosted CI (`.github/workflows/ci.yml`): `ndfd-grib-compat` on ubuntu-24.04 and windows-2022
  with Python 3.12 installs the base closure plus the extra read from `pyproject.toml`, runs
  `pip check`, exact-version assertions, `python -m eccodes selfcheck` and the focused tests
  with zero skips permitted. `ndfd-grib-dependency-audit` runs `pip-audit` on ubuntu-24.04 /
  Python 3.12 over the same resolved closure. Existing jobs are unchanged. No job downloads
  NDFD data; no secrets, product API, schedule or trading.

## Successor boundary

S10-QUAL-DATA-01 may be redrafted/resumed next and may then use this optional ecCodes capability
to implement the real historical NDFD adapter. S10-QUAL-DATA-01 remains unimplemented by this WP.
No QualificationCandidate exists yet; no real qualification gate receipt exists yet;
WP170/WP172/WP173 remain not started for this weather candidate. Gate C: NOT AUTHORIZED; live
disabled; capital/orders USD 0 / 0. Merge: NOT AUTHORIZED.
